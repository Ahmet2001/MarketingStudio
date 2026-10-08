"""The editor's local server: a thin JSON layer over the studio package.

It adds no workflow logic. Validation, planning, running, bundling and the
adapters are the studio functions; this file only carries documents to them and
results back. It listens on 127.0.0.1 and checks Host and Origin, because a page
in your browser must not be able to run workflows or write files through it.
"""

from __future__ import annotations

import base64
import io
import json
import threading
import time
import uuid
import zipfile
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

import yaml

from studio import RegistryError, WorkflowError, analyze, load_registry
from studio.adapters import ADAPTERS
from studio.bundle import BundleError, build_bundle
from studio.registry import SKIP_DIRS, Registry
from studio.runner import RunError, parse_input, run_workflow
from studio.views import plan_workflow
from studio.workflow import SPEC_VERSION

ROOT = Path(__file__).resolve().parents[1]
STATIC = Path(__file__).resolve().parent / "static"
LAYOUTS = Path(__file__).resolve().parent / "layouts"
TYPES = {".html": "text/html; charset=utf-8", ".js": "text/javascript; charset=utf-8", ".css": "text/css; charset=utf-8"}
MAX_BODY = 4_000_000


class ApiError(Exception):
    def __init__(self, message: str, status: int = 400) -> None:
        super().__init__(message)
        self.status = status


class Studio:
    """The state behind the API: where capabilities come from and which runs are going."""

    def __init__(self, sources: list[Path] | None, root: Path, layouts: Path = LAYOUTS) -> None:
        self.sources = sources
        self.root = root
        self.layouts = layouts
        self.registry: Registry = Registry()
        self.registry_error: str | None = None
        self.runs: dict[str, dict[str, Any]] = {}
        self.lock = threading.Lock()
        self.reload()

    def reload(self) -> None:
        try:
            self.registry, self.registry_error = load_registry(self.sources), None
        except RegistryError as error:
            self.registry, self.registry_error = Registry(), str(error)

    def need_registry(self) -> Registry:
        if self.registry_error:
            raise ApiError("capabilities could not be loaded: " + self.registry_error)
        return self.registry

    # ---- files -------------------------------------------------------
    def safe(self, relative: str) -> Path:
        path = (self.root / str(relative)).resolve()
        if path.suffix not in {".yaml", ".yml"} or not path.is_relative_to(self.root):
            raise ApiError("only .yaml files inside " + str(self.root) + " can be opened or saved.", 403)
        return path

    def workflows(self) -> list[str]:
        found = []
        for path in sorted(self.root.rglob("*.y*ml")):
            relative = path.relative_to(self.root)
            if path.suffix not in {".yaml", ".yml"} or SKIP_DIRS & set(relative.parts) or "runs" in relative.parts[:1]:
                continue
            try:
                text = path.read_text(encoding="utf-8")
                if "workflow:" in text and "spec_version" in text and isinstance(yaml.safe_load(text), dict):
                    found.append(str(relative))
            except (OSError, yaml.YAMLError, UnicodeDecodeError):
                continue
        return found

    def layout_file(self, relative: str) -> Path:
        return self.layouts / (relative.replace("/", "__") + ".json")

    # ---- api ---------------------------------------------------------
    def capabilities(self) -> dict[str, Any]:
        self.reload()
        items = []
        for cid, cap in sorted(self.registry.items()):
            items.append({
                "id": cid, "title": cap.get("title", cid), "description": cap.get("description", ""),
                "status": cap.get("status"), "inputs": cap.get("inputs") or {}, "outputs": cap.get("outputs") or {},
                "requires": cap.get("requires") or {}, "permissions": cap.get("permissions") or {},
                "cost": (cap.get("cost") or {}).get("estimate_usd"), "kind": cap["execution"]["type"],
                "origin": str(self.registry.origin[cid].name),
            })
        return {"capabilities": items, "error": self.registry_error, "root": str(self.root), "targets": sorted(ADAPTERS) + ["bundle"]}

    def validate(self, doc: Any, allow_unknown: bool = False) -> dict[str, Any]:
        analysis = analyze(doc, self.need_registry(), allow_unknown=allow_unknown)
        return {"errors": analysis.errors, "warnings": analysis.warnings, "order": analysis.order,
                "approval": analysis.approval, "output_types": analysis.output_types}

    def plan(self, doc: Any, allow_unknown: bool = False) -> dict[str, Any]:
        return json.loads(json.dumps(plan_workflow(doc, self.need_registry(), allow_unknown=allow_unknown), default=str))

    def export(self, doc: Any, target: str) -> dict[str, Any]:
        if target != "bundle" and target not in ADAPTERS:
            raise ApiError("unknown target: " + str(target))
        try:
            bundle = build_bundle(doc, self.need_registry())
            files, notes = (bundle.files(), bundle.warnings) if target == "bundle" else ADAPTERS[target](bundle)
        except WorkflowError as error:
            return {"errors": error.errors}
        except (BundleError, ValueError) as error:
            return {"errors": [str(error)]}
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
            for name, text in files.items():
                archive.writestr(name, text)
        return {"files": sorted(files), "notes": notes, "zip": base64.b64encode(buffer.getvalue()).decode(),
                "name": f"{doc['workflow']['id']}-{target}.zip"}

    def start_run(self, doc: Any, raw_inputs: dict[str, Any], approved: list[str]) -> dict[str, str]:
        registry = self.need_registry()
        analysis = analyze(doc, registry)
        if analysis.errors:
            raise ApiError("the workflow is not valid: " + "; ".join(analysis.errors))
        specs = doc["workflow"].get("inputs") or {}
        try:
            typed = {k: parse_input(specs[k], v) if k in specs else v for k, v in raw_inputs.items() if v not in (None, "")}
        except RunError as error:
            raise ApiError(str(error)) from error
        run_id = uuid.uuid4().hex[:10]
        workdir = self.root / "runs" / (datetime.now().strftime("%Y%m%d_%H%M%S") + "_" + run_id[:4])
        record = {"status": "running", "log": [], "outputs": None, "error": None, "folder": str(workdir.relative_to(self.root)), "started": time.time()}
        with self.lock:
            self.runs[run_id] = record

        def work() -> None:
            try:
                result = run_workflow(doc, registry, typed, workdir, approve=lambda step, cap: step in approved,
                                      log=lambda line: record["log"].append(str(line)))
                record["outputs"] = json.loads(json.dumps(result.outputs, default=str))
                record["status"] = "done"
            except Exception as error:  # report any failure to the page instead of dying silently
                record["error"], record["status"] = f"{type(error).__name__}: {error}", "failed"

        threading.Thread(target=work, daemon=True).start()
        return {"id": run_id}


def make_handler(studio: Studio, port: int):
    hosts = {f"127.0.0.1:{port}", f"localhost:{port}"}

    class Handler(BaseHTTPRequestHandler):
        server_version = "StudioUI"

        def log_message(self, *args: Any) -> None:  # keep the terminal for the user
            pass

        def _send(self, status: int, body: bytes, kind: str) -> None:
            self.send_response(status)
            self.send_header("Content-Type", kind)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def _json(self, data: Any, status: int = 200) -> None:
            self._send(status, json.dumps(data, ensure_ascii=False, default=str).encode(), "application/json")

        def _guard(self) -> None:
            if self.headers.get("Host") not in hosts:
                raise ApiError("unexpected Host header", 403)
            origin = self.headers.get("Origin")
            if origin and origin.split("://", 1)[-1] not in hosts:
                raise ApiError("cross-origin requests are refused", 403)

        def _body(self) -> dict[str, Any]:
            length = int(self.headers.get("Content-Length") or 0)
            if length > MAX_BODY:
                raise ApiError("request too large", 413)
            try:
                data = json.loads(self.rfile.read(length) or b"{}")
            except ValueError as error:
                raise ApiError("body is not JSON") from error
            if not isinstance(data, dict):
                raise ApiError("body must be a JSON object")
            return data

        def _dispatch(self, method: str) -> None:
            try:
                self._guard()
                url = urlparse(self.path)
                query = {k: v[0] for k, v in parse_qs(url.query).items()}
                if method == "GET" and not url.path.startswith("/api/"):
                    name = "index.html" if url.path in {"", "/"} else url.path.lstrip("/")
                    target = (STATIC / name).resolve()
                    if not target.is_file() or not target.is_relative_to(STATIC) or target.suffix not in TYPES:
                        raise ApiError("not found", 404)
                    return self._send(200, target.read_bytes(), TYPES[target.suffix])
                self._json(self._api(method, url.path, query))
            except ApiError as error:
                self._json({"error": str(error)}, error.status)
            except Exception as error:  # a bug must show up in the page, not as a dropped connection
                self._json({"error": f"{type(error).__name__}: {error}"}, 500)

        def _api(self, method: str, path: str, query: dict[str, str]) -> Any:
            if method == "GET":
                if path == "/api/capabilities":
                    return studio.capabilities()
                if path == "/api/workflows":
                    return {"workflows": studio.workflows()}
                if path == "/api/workflow":
                    file = studio.safe(query.get("path", ""))
                    if not file.is_file():
                        raise ApiError("no such file", 404)
                    try:
                        doc = yaml.safe_load(file.read_text(encoding="utf-8"))
                    except yaml.YAMLError as error:
                        raise ApiError("not valid YAML: " + str(error)) from error
                    layout = studio.layout_file(query["path"])
                    return {"doc": doc, "layout": json.loads(layout.read_text()) if layout.is_file() else {}}
                if path == "/api/run":
                    record = studio.runs.get(query.get("id", ""))
                    if not record:
                        raise ApiError("unknown run", 404)
                    return {**record, "log": record["log"][-400:]}
                raise ApiError("not found", 404)
            if method != "POST":
                raise ApiError("method not allowed", 405)
            body = self._body()
            doc = body.get("doc")
            if path == "/api/validate":
                return studio.validate(doc, bool(body.get("allow_unknown")))
            if path == "/api/plan":
                return studio.plan(doc, bool(body.get("allow_unknown")))
            if path == "/api/yaml":
                return {"text": yaml.safe_dump(doc, sort_keys=False, allow_unicode=True)}
            if path == "/api/parse":
                try:
                    parsed = yaml.safe_load(str(body.get("text", "")))
                except yaml.YAMLError as error:
                    raise ApiError("not valid YAML: " + str(error)) from error
                if not isinstance(parsed, dict):
                    raise ApiError("expected a YAML mapping")
                return {"doc": parsed}
            if path == "/api/export":
                return studio.export(doc, str(body.get("target", "")))
            if path == "/api/run":
                return studio.start_run(doc, body.get("inputs") or {}, list(body.get("approve") or []))
            if path == "/api/save":
                file = studio.safe(str(body.get("path", "")))
                if not isinstance(doc, dict) or doc.get("spec_version") != SPEC_VERSION or "workflow" not in doc:
                    raise ApiError("refusing to save something that is not a workflow document")
                file.parent.mkdir(parents=True, exist_ok=True)
                file.write_text(yaml.safe_dump(doc, sort_keys=False, allow_unicode=True), encoding="utf-8")
                layout = studio.layout_file(str(body["path"]))
                studio.layouts.mkdir(parents=True, exist_ok=True)
                layout.write_text(json.dumps(body.get("layout") or {}), encoding="utf-8")
                return {"saved": str(file.relative_to(studio.root))}
            raise ApiError("not found", 404)

        def do_GET(self) -> None:
            self._dispatch("GET")

        def do_POST(self) -> None:
            self._dispatch("POST")

    return Handler


def serve(port: int, sources: list[Path] | None, root: Path) -> None:
    studio = Studio(sources, root)
    server = ThreadingHTTPServer(("127.0.0.1", port), make_handler(studio, port))
    print(f"MarketingStudio editor: http://127.0.0.1:{port}  (workflows in {root})  Ctrl+C to stop")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
