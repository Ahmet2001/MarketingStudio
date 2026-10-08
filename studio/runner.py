"""Local runner for workflows.

Runs a validated workflow on this machine, one step at a time in dependency
order, by executing each step's capability according to its ``execution``:

* ``cli``      - start the command in ``cwd`` (relative to the capability file)
* ``python``   - import ``module`` (``path`` is added to ``sys.path``) and call ``function``
* ``workflow`` - run the referenced ``workflow.yaml`` as a nested run
* ``http``     - not supported here; reported as an error

It is deliberately plain: no queue, no retries, no parallelism. A step that
writes to the outside world only runs after it has been approved.
"""

from __future__ import annotations

import glob
import importlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from .registry import Registry
from .workflow import REF_RE, WorkflowError, analyze, load_workflow


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


def parse_input(spec: dict[str, Any], raw: Any) -> Any:
    """Turn a command-line string into the declared type."""

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
        return value if isinstance(value, str) else json.dumps(value) if isinstance(value, (list, dict)) else str(value)
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

    def lookup(match) -> Any:
        name, step, out, cast = match.groups()
        found = inputs[name] if name is not None else steps[step][out]
        return convert(found, cast) if cast else found

    matches = list(REF_RE.finditer(value))
    if not matches:
        return value
    if len(matches) == 1 and matches[0].group(0) == value.strip():
        return lookup(matches[0])
    return REF_RE.sub(lambda m: convert(lookup(m), "text"), value)


def _collect(pattern: str, out_type: str, step_dir: Path, exclude: list[str]) -> Any:
    matches = [
        Path(p)
        for p in glob.glob(pattern.replace("{output_dir}", str(step_dir)), recursive=True)
        if Path(p).is_file()
        and not set(Path(p).relative_to(step_dir).parts) & set(exclude)
    ]
    if not matches:
        raise RunError(f"no file matched {pattern.replace('{output_dir}', str(step_dir))}")
    chosen = max(matches, key=lambda p: (p.stat().st_mtime, p.stat().st_size))
    if out_type.startswith("file:"):
        return str(chosen)
    text = chosen.read_text(encoding="utf-8")
    return convert(text, out_type) if out_type != "text" else text


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
        raise RunError(f"working directory {cwd} does not exist.")
    log = step_dir / "step.log"
    with log.open("w", encoding="utf-8") as handle:
        process = subprocess.run(argv, cwd=cwd, stdout=handle, stderr=subprocess.STDOUT, text=True)
    if process.returncode != 0:
        tail = "\n".join(log.read_text(encoding="utf-8").splitlines()[-8:])
        raise RunError(f"{argv[0]} exited with {process.returncode}. Log: {log}\n{tail}")
    return {
        name: _collect(pattern, cap["outputs"][name]["type"], step_dir, ex.get("exclude") or [])
        for name, pattern in (ex.get("outputs") or {}).items()
    }


def _load_module(name: str, folder: Path):
    """Import a capability's module.

    A plain module (one file) is loaded from its own file under a name unique to
    that file, so two engines both called ``engine.py`` in different folders
    never share a cached module. Dotted names are imported as packages.
    """

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
        found = None
    if found is not None:
        return {
            name: str(value) if isinstance(value, Path) else value for name, value in found.items()
        }
    raise RunError(f"{ex['function']} returned something that does not match outputs {sorted(outputs)}.")


def run_workflow(
    doc: dict[str, Any],
    registry: Registry,
    inputs: dict[str, Any],
    workdir: Path,
    *,
    approve: Callable[[str, dict[str, Any]], bool] | None = None,
    log: Callable[[str], None] = lambda message: None,
    _depth: int = 0,
) -> RunResult:
    """Run a workflow. ``approve(step_id, capability)`` decides gated steps; the default refuses."""

    analysis = analyze(doc, registry)
    if analysis.errors:
        raise WorkflowError(analysis.errors)
    wf = doc["workflow"]
    specs = wf.get("inputs") or {}
    values: dict[str, Any] = {}
    for name, spec in specs.items():
        if name in inputs:
            values[name] = parse_input(spec, inputs[name])
        elif "default" in spec:
            values[name] = spec["default"]
        elif spec.get("required"):
            raise RunError(f"input '{name}' is required.")
    unknown = set(inputs) - set(specs)
    if unknown:
        raise RunError(f"unknown input(s): {', '.join(sorted(unknown))}.")

    steps = {s["id"]: s for s in wf["steps"]}
    missing: dict[str, list[str]] = {}
    for sid in analysis.order:
        needed = [e for e in (analysis.caps[sid].get("requires") or {}).get("env", []) if not os.environ.get(e)]
        needed += [b for b in (analysis.caps[sid].get("requires") or {}).get("binaries", []) if not shutil.which(b)]
        if needed:
            missing[sid] = needed
    if missing:
        raise RunError("missing before starting: " + "; ".join(f"step '{k}' needs {', '.join(v)}" for k, v in missing.items()))

    workdir.mkdir(parents=True, exist_ok=True)
    produced: dict[str, dict[str, Any]] = {}
    records: list[StepRecord] = []
    for sid in analysis.order:
        step = steps[sid]
        cap = analysis.caps[sid]
        record = StepRecord(sid, cap["id"])
        records.append(record)
        if analysis.approval[sid] and not (approve and approve(sid, cap)):
            record.status = "skipped"
            record.error = "approval required and not given"
            raise RunError(f"step '{sid}' ({cap['id']}) needs approval and did not get it. Nothing after it ran.")
        step_dir = workdir / sid
        step_dir.mkdir(parents=True, exist_ok=True)
        resolved = {k: _resolve(v, values, produced) for k, v in (step.get("with") or {}).items()}
        for name, spec in (cap.get("inputs") or {}).items():
            if name not in resolved and "default" in spec:
                resolved[name] = spec["default"]
        log(f"[{sid}] {cap['id']} ...")
        started = time.time()
        base = registry.origin[cap["id"]].parent
        try:
            kind = cap["execution"]["type"]
            if kind == "cli":
                outputs = _run_cli(cap, base, resolved, step_dir)
            elif kind == "python":
                outputs = _run_python(cap, base, resolved)
            elif kind == "workflow":
                nested = load_workflow(base / cap["execution"]["definition"])
                if _depth >= 8:
                    raise RunError("workflows are nested too deeply.")
                outputs = run_workflow(nested, registry, resolved, step_dir, approve=approve, log=log, _depth=_depth + 1).outputs
            else:
                raise RunError(f"the local runner cannot execute '{kind}' capabilities.")
        except RunError as error:
            record.status, record.error = "failed", str(error)
            record.seconds = time.time() - started
            raise RunError(f"step '{sid}' failed: {error}") from error
        record.status, record.outputs = "done", outputs
        record.seconds = time.time() - started
        produced[sid] = outputs
        log(f"[{sid}] done in {record.seconds:.1f}s")
    results = {name: _resolve(ref, values, produced) for name, ref in (wf.get("outputs") or {}).items()}
    return RunResult(results, records, workdir)
