"""Standard-library-only workflow runner.

This file has no dependency on the rest of ``studio`` or on any package, so it
can be copied next to a workflow and run anywhere Python 3.10+ is available.
Exported bundles and generated tools embed it verbatim.

It runs an already validated workflow (steps carry ``needs`` and ``approval``)
against capability descriptions, one step at a time in dependency order.

Execution types: ``cli`` (run a command), ``python`` (call a function) and
``workflow`` (run a nested workflow supplied by ``nested_loader``).
``http`` capabilities are not executed here.

File inputs of the workflow may be given as a reference:

* ``https://...``                  downloaded (public hosts only, size limited)
* ``{"filename": ..., "content_base64": ...}``  written to the run folder
* ``asset:<id>``                   resolved by a callable you supply
* a local path                     only inside the allowed folders
"""

from __future__ import annotations

import base64
import binascii
import glob
import importlib
import importlib.util
import ipaddress
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

REF_RE = re.compile(
    r"\{\{\s*(?:inputs\.([A-Za-z0-9_]+)|steps\.([A-Za-z0-9_]+)\.outputs\.([A-Za-z0-9_]+))"
    r"(?:\s*\|\s*as\s+([a-z0-9:]+))?\s*\}\}"
)
DEFAULT_MAX_BYTES = 100 * 1024 * 1024


class RunError(RuntimeError):
    """A step failed, was not approved, or could not be started."""


@dataclass
class StepRecord:
    id: str
    capability: str
    status: str = "pending"  # pending | done | failed | skipped
    outputs: dict[str, Any] = field(default_factory=dict)
    seconds: float = 0.0
    error: str = ""


@dataclass
class RunResult:
    outputs: dict[str, Any]
    steps: list[StepRecord]
    workdir: Path


@dataclass
class FilePolicy:
    """What a caller may hand us as a file input."""

    roots: list[Path] = field(default_factory=list)  # local folders that may be read
    allow_any_path: bool = False  # trusted callers only (a person at a terminal)
    asset_resolver: Callable[[str], str | Path] | None = None
    max_bytes: int = DEFAULT_MAX_BYTES

    @classmethod
    def from_env(cls) -> "FilePolicy":
        raw = os.environ.get("STUDIO_FILE_ROOTS", "")
        limit = os.environ.get("STUDIO_MAX_FILE_MB")
        return cls(
            roots=[Path(p).expanduser().resolve() for p in raw.split(os.pathsep) if p.strip()],
            max_bytes=int(float(limit) * 1024 * 1024) if limit else DEFAULT_MAX_BYTES,
        )


# ---------------------------------------------------------------- values
def parse_input(spec: dict[str, Any], raw: Any) -> Any:
    """Turn a command-line style string into the declared type."""

    if not isinstance(raw, str):
        return raw
    kind = spec["type"]
    try:
        if kind == "integer":
            return int(raw)
        if kind == "number":
            return float(raw)
        if kind == "boolean":
            if raw.lower() in {"true", "1", "yes"}:
                return True
            if raw.lower() in {"false", "0", "no"}:
                return False
            raise ValueError(raw)
        if kind in {"list", "object"}:
            return json.loads(raw)
        if kind == "enum" and raw not in spec.get("values", []):
            raise ValueError(raw)
    except ValueError as error:
        raise RunError(f"'{raw}' is not a valid {kind}.") from error
    return raw


def convert(value: Any, target: str) -> Any:
    """Apply ``| as <target>`` to a runtime value."""

    if target == "text":
        if isinstance(value, str):
            return value
        return json.dumps(value) if isinstance(value, (list, dict)) else str(value)
    if isinstance(value, str):
        try:
            if target == "integer":
                return int(value.strip())
            if target == "number":
                return float(value.strip())
            if target == "boolean":
                return value.strip().lower() in {"true", "1", "yes"}
            if target in {"list", "object"}:
                return json.loads(value)
        except ValueError as error:
            raise RunError(f"Cannot convert {value!r} to {target}.") from error
    return value


def _resolve(value: Any, inputs: dict[str, Any], steps: dict[str, dict[str, Any]]) -> Any:
    if not isinstance(value, str):
        return value

    def lookup(match: re.Match[str]) -> Any:
        name, step, out, cast = match.groups()
        found = inputs[name] if name is not None else steps[step][out]
        return convert(found, cast) if cast else found

    matches = list(REF_RE.finditer(value))
    if not matches:
        return value
    if len(matches) == 1 and matches[0].group(0) == value.strip():
        return lookup(matches[0])
    return REF_RE.sub(lambda m: convert(lookup(m), "text"), value)


# ---------------------------------------------------------------- file inputs
def _safe_name(name: str, fallback: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", Path(str(name)).name).strip("._")
    return cleaned[:120] or fallback


def _check_public_host(host: str) -> None:
    try:
        addresses = {info[4][0] for info in socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)}
    except socket.gaierror as error:
        raise RunError(f"cannot look up {host}: {error}") from error
    for address in addresses:
        if not ipaddress.ip_address(address.split("%")[0]).is_global:
            raise RunError(f"{host} points to a private or local address and is not allowed.")


class _PublicHttpsOnly(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # type: ignore[override]
        parsed = urllib.parse.urlparse(newurl)
        if parsed.scheme != "https" or not parsed.hostname:
            raise RunError("a download redirected to something that is not https.")
        _check_public_host(parsed.hostname)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _download(url: str, target: Path, limit: int) -> None:
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme != "https" or not parsed.hostname:
        raise RunError("only https addresses can be downloaded.")
    _check_public_host(parsed.hostname)
    opener = urllib.request.build_opener(_PublicHttpsOnly)
    total = 0
    try:
        with opener.open(urllib.request.Request(url, headers={"User-Agent": "studio-runner"}), timeout=60) as response:
            with target.open("wb") as handle:
                while chunk := response.read(1024 * 256):
                    total += len(chunk)
                    if total > limit:
                        raise RunError(f"the download is larger than the {limit // (1024 * 1024)} MB limit.")
                    handle.write(chunk)
    except (urllib.error.URLError, TimeoutError) as error:
        target.unlink(missing_ok=True)
        raise RunError(f"could not download {url}: {error}") from error
    except RunError:
        target.unlink(missing_ok=True)
        raise


def resolve_file(value: Any, name: str, dest: Path, policy: FilePolicy) -> str:
    """Turn a file reference into a path on this machine."""

    dest.mkdir(parents=True, exist_ok=True)
    if isinstance(value, str) and value.strip().startswith("{"):
        try:
            value = json.loads(value)
        except ValueError:
            pass
    if isinstance(value, dict):
        content = value.get("content_base64")
        if content is None:
            raise RunError(f"file input '{name}': an object needs 'filename' and 'content_base64'.")
        try:
            data = base64.b64decode(content, validate=True)
        except (binascii.Error, ValueError) as error:
            raise RunError(f"file input '{name}': content_base64 is not valid base64.") from error
        if len(data) > policy.max_bytes:
            raise RunError(f"file input '{name}' is larger than the {policy.max_bytes // (1024 * 1024)} MB limit.")
        target = dest / f"{name}_{_safe_name(value.get('filename', ''), 'upload.bin')}"
        target.write_bytes(data)
        return str(target)
    if not isinstance(value, str) or not value.strip():
        raise RunError(f"file input '{name}' needs a reference (https address, base64 object, asset id or path).")
    text = value.strip()
    if text.startswith("https://"):
        target = dest / f"{name}_{_safe_name(Path(urllib.parse.urlparse(text).path).name, 'download')}"
        _download(text, target, policy.max_bytes)
        return str(target)
    if text.startswith("http://"):
        raise RunError(f"file input '{name}': only https addresses are accepted.")
    if text.startswith("asset:"):
        if policy.asset_resolver is None:
            raise RunError(f"file input '{name}': asset references need an asset resolver, and none is configured.")
        return str(policy.asset_resolver(text[len("asset:"):]))
    path = Path(text).expanduser()
    try:
        resolved = path.resolve(strict=True)
    except OSError as error:
        raise RunError(f"file input '{name}': {text!r} does not exist.") from error
    if not resolved.is_file():
        raise RunError(f"file input '{name}': {text!r} is not a file.")
    if not policy.allow_any_path and not any(resolved.is_relative_to(root) for root in policy.roots):
        raise RunError(
            f"file input '{name}': local paths are only accepted inside the allowed folders "
            "(set STUDIO_FILE_ROOTS), or pass an https address or base64 content instead."
        )
    return str(resolved)


# ---------------------------------------------------------------- step execution
def _collect(pattern: str, out_type: str, step_dir: Path, exclude: list[str]) -> Any:
    matches = [
        Path(p)
        for p in glob.glob(pattern.replace("{output_dir}", str(step_dir)), recursive=True)
        if Path(p).is_file() and not set(Path(p).relative_to(step_dir).parts) & set(exclude)
    ]
    if not matches:
        raise RunError(f"no file matched {pattern.replace('{output_dir}', str(step_dir))}")
    chosen = max(matches, key=lambda p: (p.stat().st_mtime, p.stat().st_size))
    if out_type.startswith("file:"):
        return str(chosen)
    text = chosen.read_text(encoding="utf-8")
    return text if out_type == "text" else convert(text, out_type)


def _base_for(cap: dict[str, Any], bases: dict[str, Path]) -> Path:
    override = os.environ.get("STUDIO_DIR_" + re.sub(r"\W", "_", cap["id"]).upper())
    return Path(override) if override else bases[cap["id"]]


def _run_cli(cap: dict[str, Any], base: Path, values: dict[str, Any], step_dir: Path) -> dict[str, Any]:
    ex = cap["execution"]
    argv = [str(part) for part in ex["command"]]
    for name in ex.get("positional") or []:
        if values.get(name) not in (None, ""):
            argv.append(str(values[name]))
    for name, flag in (ex.get("flags") or {}).items():
        value = values.get(name)
        if value is None or value == "":
            continue
        if isinstance(value, bool):
            if value:
                argv.append(flag)
        else:
            argv += [flag, str(value)]
    if ex.get("output_dir_flag"):
        argv += [ex["output_dir_flag"], str(step_dir)]
    cwd = (base / ex.get("cwd", ".")).resolve()
    if not cwd.is_dir():
        variable = "STUDIO_DIR_" + re.sub(r"\W", "_", cap["id"]).upper()
        raise RunError(
            f"working directory {cwd} does not exist on this machine. "
            f"Set {variable} to the folder that holds this engine."
        )
    log = step_dir / "step.log"
    with log.open("w", encoding="utf-8") as handle:
        try:
            process = subprocess.run(argv, cwd=cwd, stdout=handle, stderr=subprocess.STDOUT, text=True)
        except OSError as error:
            raise RunError(f"could not start {argv[0]}: {error}") from error
    if process.returncode != 0:
        tail = "\n".join(log.read_text(encoding="utf-8").splitlines()[-8:])
        raise RunError(f"{argv[0]} exited with {process.returncode}. Log: {log}\n{tail}")
    return {
        name: _collect(pattern, cap["outputs"][name]["type"], step_dir, ex.get("exclude") or [])
        for name, pattern in (ex.get("outputs") or {}).items()
    }


def _load_module(name: str, folder: Path):
    """A plain module is loaded from its own file under a name unique to that file."""

    candidate = folder / (name.replace(".", "/") + ".py")
    if "." in name or not candidate.is_file():
        return importlib.import_module(name)
    unique = "_studio_engine_" + str(abs(hash(str(candidate))))
    if unique in sys.modules:
        return sys.modules[unique]
    spec = importlib.util.spec_from_file_location(unique, candidate)
    module = importlib.util.module_from_spec(spec)
    sys.modules[unique] = module
    try:
        spec.loader.exec_module(module)
    except BaseException:
        sys.modules.pop(unique, None)
        raise
    return module


def _run_python(cap: dict[str, Any], base: Path, values: dict[str, Any]) -> dict[str, Any]:
    ex = cap["execution"]
    path = str((base / ex.get("path", ".")).resolve())
    added = path not in sys.path
    if added:
        sys.path.insert(0, path)
    try:
        function = getattr(_load_module(ex["module"], Path(path)), ex["function"])
        specs = cap.get("inputs") or {}
        kwargs = {
            k: Path(v) if specs.get(k, {}).get("type", "").startswith("file:") and isinstance(v, str) else v
            for k, v in values.items()
            if v is not None
        }
        result = function(**kwargs)
    except (ImportError, AttributeError) as error:
        raise RunError(f"cannot load {ex['module']}.{ex['function']}: {error}") from error
    finally:
        if added and path in sys.path:
            sys.path.remove(path)
    outputs = cap["outputs"]
    if isinstance(result, dict) and set(outputs) <= set(result):
        found = {name: result[name] for name in outputs}
    elif len(outputs) == 1:
        found = {next(iter(outputs)): result}
    else:
        raise RunError(f"{ex['function']} returned something that does not match outputs {sorted(outputs)}.")
    return {name: str(value) if isinstance(value, Path) else value for name, value in found.items()}


def order_steps(steps: list[dict[str, Any]]) -> list[str]:
    """Dependency order, keeping declaration order among independent steps."""

    pending = {s["id"]: set(s.get("needs") or []) for s in steps}
    order: list[str] = []
    while pending:
        ready = [s["id"] for s in steps if s["id"] in pending and not pending[s["id"]]]
        if not ready:
            raise RunError("the steps form a cycle: " + ", ".join(sorted(pending)))
        for sid in ready:
            order.append(sid)
            del pending[sid]
            for other in pending.values():
                other.discard(sid)
    return order


def run(
    workflow: dict[str, Any],
    capabilities: dict[str, dict[str, Any]],
    bases: dict[str, Path],
    inputs: dict[str, Any],
    workdir: Path,
    *,
    approve: Callable[[str, dict[str, Any]], bool] | None = None,
    log: Callable[[str], None] = lambda message: None,
    files: FilePolicy | None = None,
    nested_loader: Callable[[dict[str, Any]], dict[str, Any]] | None = None,
    _depth: int = 0,
) -> RunResult:
    """Run a validated workflow.

    ``workflow`` is the inner ``workflow`` mapping with ``needs`` and
    ``approval`` already filled in on every step. ``approve(step_id, capability)``
    decides steps marked ``approval: required``; the default refuses them.
    """

    specs = workflow.get("inputs") or {}
    unknown = set(inputs) - set(specs)
    if unknown:
        raise RunError(f"unknown input(s): {', '.join(sorted(unknown))}.")
    workdir.mkdir(parents=True, exist_ok=True)
    values: dict[str, Any] = {}
    for name, spec in specs.items():
        if name in inputs:
            value = parse_input(spec, inputs[name])
            if _depth == 0 and spec["type"].startswith("file:"):
                value = resolve_file(value, name, workdir / "_inputs", files or FilePolicy())
            values[name] = value
        elif "default" in spec:
            values[name] = spec["default"]
        elif spec.get("required"):
            raise RunError(f"input '{name}' is required.")

    steps = {s["id"]: s for s in workflow["steps"]}
    order = order_steps(workflow["steps"])
    missing = []
    for sid in order:
        cap = capabilities[steps[sid]["capability"]]
        needed = [e for e in (cap.get("requires") or {}).get("env", []) if not os.environ.get(e)]
        needed += [b for b in (cap.get("requires") or {}).get("binaries", []) if not shutil.which(b)]
        if needed:
            missing.append(f"step '{sid}' needs {', '.join(needed)}")
    if missing:
        raise RunError("missing before starting: " + "; ".join(missing))

    produced: dict[str, dict[str, Any]] = {}
    records: list[StepRecord] = []
    for sid in order:
        step = steps[sid]
        cap = capabilities[step["capability"]]
        record = StepRecord(sid, cap["id"])
        records.append(record)
        if step.get("approval") == "required" and not (approve and approve(sid, cap)):
            record.status, record.error = "skipped", "approval required and not given"
            raise RunError(f"step '{sid}' ({cap['id']}) needs approval and did not get it. Nothing after it ran.")
        step_dir = workdir / sid
        step_dir.mkdir(parents=True, exist_ok=True)
        resolved = {k: _resolve(v, values, produced) for k, v in (step.get("with") or {}).items()}
        for name, spec in (cap.get("inputs") or {}).items():
            if name not in resolved and "default" in spec:
                resolved[name] = spec["default"]
        log(f"[{sid}] {cap['id']} ...")
        started = time.time()
        try:
            kind = cap["execution"]["type"]
            base = _base_for(cap, bases)
            if kind == "cli":
                outputs = _run_cli(cap, base, resolved, step_dir)
            elif kind == "python":
                outputs = _run_python(cap, base, resolved)
            elif kind == "workflow":
                if nested_loader is None or _depth >= 8:
                    raise RunError("nested workflows are not available here, or are nested too deeply.")
                outputs = run(
                    nested_loader(cap), capabilities, bases, resolved, step_dir,
                    approve=approve, log=log, nested_loader=nested_loader, _depth=_depth + 1,
                ).outputs
            else:
                raise RunError(f"the runner cannot execute '{kind}' capabilities.")
        except RunError as error:
            record.status, record.error = "failed", str(error)
            record.seconds = time.time() - started
            raise RunError(f"step '{sid}' failed: {error}") from error
        record.status, record.outputs = "done", outputs
        record.seconds = time.time() - started
        produced[sid] = outputs
        log(f"[{sid}] done in {record.seconds:.1f}s")
    results = {name: _resolve(ref, values, produced) for name, ref in (workflow.get("outputs") or {}).items()}
    return RunResult(results, records, workdir)


# ---------------------------------------------------------------- bundles
def load_bundle(folder: Path) -> tuple[dict[str, Any], dict[str, dict[str, Any]], dict[str, Path], dict[str, Any]]:
    """Read a bundle folder: ``(workflow, capabilities, bases, manifest)``."""

    folder = Path(folder)
    read = lambda name: json.loads((folder / name).read_text(encoding="utf-8"))  # noqa: E731
    bases = {cid: (Path(p) if Path(p).is_absolute() else folder / p) for cid, p in read("bases.json").items()}
    return read("workflow.json"), read("capabilities.json"), bases, read("manifest.json")


def main(argv: list[str] | None = None) -> int:
    """``python portable.py [BUNDLE_DIR] --input name=value ... [--approve STEP ...]``"""

    import argparse

    parser = argparse.ArgumentParser(description="Run an exported workflow bundle.")
    parser.add_argument("bundle", nargs="?", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--input", action="append", default=[], metavar="NAME=VALUE")
    parser.add_argument("--approve", nargs="+", default=[], metavar="STEP")
    parser.add_argument("--approve-all", action="store_true")
    parser.add_argument("--workdir", type=Path)
    args = parser.parse_args(argv)
    workflow, capabilities, bases, manifest = load_bundle(args.bundle)
    given = dict(item.partition("=")[::2] for item in args.input)
    workdir = args.workdir or Path("runs") / time.strftime("%Y%m%d_%H%M%S")
    try:
        result = run(
            workflow, capabilities, bases, given, workdir,
            approve=lambda step, cap: args.approve_all or step in args.approve,
            log=print, files=FilePolicy.from_env(),
        )
    except RunError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    for name, value in result.outputs.items():
        print(f"{name}: {value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
