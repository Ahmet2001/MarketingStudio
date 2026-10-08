"""The viewer's local server: a read-only JSON layer over the studio package.

It adds no workflow logic. Validation, planning, bundling and the adapters are
the studio functions; this file only carries documents to them and results back.
It writes nothing and runs nothing. It listens on 127.0.0.1 and checks Host and
Origin, so a page in your browser cannot read your workflow files through it.
"""

from __future__ import annotations

import base64
import io
import json
import zipfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

import yaml

from studio import RegistryError, WorkflowError, analyze, load_registry
from studio.adapters import ADAPTERS
from studio.bundle import BundleError, build_bundle
from studio.registry import SKIP_DIRS, Registry
from studio.views import plan_workflow

ROOT = Path(__file__).resolve().parents[1]
STATIC = Path(__file__).resolve().parent / "static"
TYPES = {".html": "text/html; charset=utf-8", ".js": "text/javascript; charset=utf-8", ".css": "text/css; charset=utf-8"}
MAX_SHOWN = 400_000  # characters of one file sent to the page; the zip always has the whole file

TARGETS = {
    "bundle": "The neutral export: workflow, contracts, the standard-library runner and single-file engines. Everything else is built from this.",
    "agent-pack": "A tool pack for BrowserAgent: plugin.yaml and one self-contained tools/<name>.py.",
    "agent-bundle": "agent-pack plus a small agent that owns the tool, so an agent app's orchestrator can delegate to the workflow once the pack is installed.",
    "tool-schema": "Tool definitions for LLM function calling, in Anthropic and OpenAI shapes. A definition only.",
    "job-handler": "One handler.py a worker you already run can call (import it, or pipe JSON to it).",
    "worker": "A standalone queue worker (file queue or Supabase), with a migration, Dockerfile and per-step approval.",
    "mcp": "A Model Context Protocol server over stdio that offers the workflow as one tool.",
}


class ApiError(Exception):
    def __init__(self, message: str, status: int = 400) -> None:
        super().__init__(message)
        self.status = status


class Viewer:
    """Where capabilities and workflow files come from."""

    def __init__(self, sources: list[Path] | None, root: Path) -> None:
        self.sources = sources
        self.root = root
        self.registry: Registry = Registry()
        self.registry_error: str | None = None
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

    def safe(self, relative: str) -> Path:
        path = (self.root / str(relative)).resolve()
        if path.suffix not in {".yaml", ".yml"} or not path.is_relative_to(self.root):
            raise ApiError("only .yaml files inside " + str(self.root) + " can be opened.", 403)
        return path

    def read(self, relative: str) -> tuple[dict[str, Any], str]:
        file = self.safe(relative)
        if not file.is_file():
            raise ApiError("no such file", 404)
        text = file.read_text(encoding="utf-8")
        try:
            doc = yaml.safe_load(text)
        except yaml.YAMLError as error:
            raise ApiError("not valid YAML: " + str(error)) from error
        if not isinstance(doc, dict) or not isinstance(doc.get("workflow"), dict):
            raise ApiError("this file has no 'workflow' section")
        return doc, text

    # ---- api ---------------------------------------------------------
    def workflows(self) -> list[dict[str, Any]]:
        registry = self.need_registry()
        found = []
        for path in sorted(self.root.rglob("*.y*ml")):
            relative = path.relative_to(self.root)
            if path.suffix not in {".yaml", ".yml"} or SKIP_DIRS & set(relative.parts) or relative.parts[0] == "runs":
                continue
            try:
                text = path.read_text(encoding="utf-8")
                if "workflow:" not in text or "spec_version" not in text:
                    continue
                doc = yaml.safe_load(text)
                wf = doc["workflow"]
                analysis = analyze(doc, registry)
            except (OSError, yaml.YAMLError, UnicodeDecodeError, KeyError, TypeError):
                continue
            found.append({
                "path": str(relative), "id": wf.get("id"), "name": wf.get("name"), "description": wf.get("description", ""),
                "inputs": len(wf.get("inputs") or {}), "steps": len(wf.get("steps") or []),
                "valid": not analysis.errors, "errors": len(analysis.errors),
                "gated": sum(1 for v in analysis.approval.values() if v),
            })
        return found

    def workflow(self, relative: str) -> dict[str, Any]:
        doc, text = self.read(relative)
        registry = self.need_registry()
        analysis = analyze(doc, registry)
        plan = json.loads(json.dumps(plan_workflow(doc, registry), default=str)) if not analysis.errors else None
        used = {s.get("capability") for s in doc["workflow"].get("steps") or [] if isinstance(s, dict)}
        return {
            "path": relative, "doc": doc, "yaml": text,
            "errors": analysis.errors, "warnings": analysis.warnings, "order": analysis.order,
            "approval": analysis.approval, "plan": plan,
            "capabilities": {cid: self._capability(cid) for cid in sorted(c for c in used if c in registry)},
        }

    def capabilities(self) -> dict[str, Any]:
        self.reload()
        return {"capabilities": [self._capability(cid) for cid in sorted(self.registry)], "error": self.registry_error,
                "root": str(self.root), "targets": [{"id": t, "about": TARGETS[t]} for t in ["bundle", *sorted(ADAPTERS)]]}

    def _capability(self, cid: str) -> dict[str, Any]:
        cap = self.registry[cid]
        return {
            "id": cid, "title": cap.get("title", cid), "description": cap.get("description", ""), "status": cap.get("status"),
            "inputs": cap.get("inputs") or {}, "outputs": cap.get("outputs") or {}, "requires": cap.get("requires") or {},
            "permissions": cap.get("permissions") or {}, "cost": (cap.get("cost") or {}).get("estimate_usd"),
            "kind": cap["execution"]["type"], "origin": self.registry.origin[cid].name,
        }

    def export(self, relative: str, target: str) -> dict[str, Any]:
        if target != "bundle" and target not in ADAPTERS:
            raise ApiError("unknown target: " + str(target))
        doc, _ = self.read(relative)
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
        return {
            "target": target, "notes": notes, "name": f"{doc['workflow']['id']}-{target}.zip",
            "files": [{"name": n, "size": len(t.encode()), "text": t[:MAX_SHOWN], "cut": len(t) > MAX_SHOWN} for n, t in sorted(files.items())],
            "zip": base64.b64encode(buffer.getvalue()).decode(),
        }


def make_handler(viewer: Viewer, port: int):
    hosts = {f"127.0.0.1:{port}", f"localhost:{port}"}

    class Handler(BaseHTTPRequestHandler):
        server_version = "StudioViewer"

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
            if length > 100_000:
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
                    return viewer.capabilities()
                if path == "/api/workflows":
                    return {"workflows": viewer.workflows()}
                if path == "/api/workflow":
                    return viewer.workflow(query.get("path", ""))
                raise ApiError("not found", 404)
            if method == "POST" and path == "/api/export":
                body = self._body()
                return viewer.export(str(body.get("path", "")), str(body.get("target", "")))
            raise ApiError("not found", 404)

        def do_GET(self) -> None:
            self._dispatch("GET")

        def do_POST(self) -> None:
            self._dispatch("POST")

    return Handler


def serve(port: int, sources: list[Path] | None, root: Path) -> None:
    viewer = Viewer(sources, root)
    server = ThreadingHTTPServer(("127.0.0.1", port), make_handler(viewer, port))
    print(f"MarketingStudio viewer: http://127.0.0.1:{port}  (workflows in {root})  Ctrl+C to stop")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
