import base64
import io
import json
import threading
import time
import urllib.error
import urllib.request
import zipfile
from http.server import ThreadingHTTPServer
from pathlib import Path

import pytest
import yaml

from ui.server import Studio, make_handler

REPO = Path(__file__).resolve().parents[2]


@pytest.fixture()
def api(tmp_path):
    (tmp_path / "wf").mkdir()
    sources = [REPO / "examples" / "single_file", REPO / "examples" / "text_report"]
    studio = Studio(sources, tmp_path, tmp_path / "layouts")
    holder = {}
    server = ThreadingHTTPServer(("127.0.0.1", 0), lambda *a, **k: make_handler(studio, holder["port"])(*a, **k))
    holder["port"] = server.server_address[1]
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{holder['port']}"

    def call(path, body=None, headers=None, raw=False):
        request = urllib.request.Request(base + path, data=None if body is None else json.dumps(body).encode(), headers=headers or {})
        try:
            with urllib.request.urlopen(request) as response:
                data = response.read()
                return response.status, (data if raw else json.loads(data))
        except urllib.error.HTTPError as error:
            return error.code, json.loads(error.read() or b"{}")

    yield call, tmp_path, holder["port"]
    server.shutdown()


DOC = {"spec_version": "0.1", "workflow": {
    "id": "wc", "name": "WC", "inputs": {"source": {"type": "file:any", "required": True}},
    "steps": [{"id": "count", "capability": "demo.word_count", "with": {"source": "{{ inputs.source }}"}}],
    "outputs": {"n": "{{ steps.count.outputs.result }}"}}}


def test_static_page_and_capability_list(api):
    call, _, _ = api
    status, page = call("/", raw=True)
    assert status == 200 and b"<title>" in page
    status, data = call("/api/capabilities")
    ids = {c["id"] for c in data["capabilities"]}
    assert {"demo.word_count", "text.keywords", "text.report"} <= ids and "social.publish.x_post" not in ids
    assert "mcp" in data["targets"] and "bundle" in data["targets"]


def test_validate_plan_and_yaml_roundtrip(api):
    call, _, _ = api
    assert call("/api/validate", {"doc": DOC})[1]["errors"] == []
    bad = json.loads(json.dumps(DOC))
    bad["workflow"]["steps"][0]["with"]["source"] = "{{ inputs.nope }}"
    assert call("/api/validate", {"doc": bad})[1]["errors"]
    assert call("/api/plan", {"doc": DOC})[1]["errors"] == []
    text = call("/api/yaml", {"doc": DOC})[1]["text"]
    assert call("/api/parse", {"text": text})[1]["doc"] == DOC
    assert call("/api/parse", {"text": "a: [b"})[0] == 400


def test_save_open_list_and_path_safety(api):
    call, root, _ = api
    assert call("/api/save", {"path": "wf/one.yaml", "doc": DOC, "layout": {"count": [10, 20]}})[0] == 200
    assert yaml.safe_load((root / "wf/one.yaml").read_text()) == DOC
    assert call("/api/workflows")[1]["workflows"] == ["wf/one.yaml"]
    opened = call("/api/workflow?path=wf/one.yaml")[1]
    assert opened["doc"] == DOC and opened["layout"] == {"count": [10, 20]}
    for evil in ("../escape.yaml", "/etc/passwd.yaml", "wf/notes.txt"):
        assert call("/api/save", {"path": evil, "doc": DOC})[0] == 403
    assert call("/api/save", {"path": "wf/two.yaml", "doc": {"x": 1}})[0] == 400
    assert not (root.parent / "escape.yaml").exists()


def test_run_streams_a_result_and_gated_steps_need_approval(api):
    call, root, _ = api
    src = root / "in.txt"
    src.write_text("one two three")
    started = call("/api/run", {"doc": DOC, "inputs": {"source": str(src)}})[1]
    for _ in range(100):
        record = call("/api/run?id=" + started["id"])[1]
        if record["status"] != "running":
            break
        time.sleep(0.05)
    assert record["status"] == "done" and record["outputs"] == {"n": 3}
    status, error = call("/api/run", {"doc": DOC, "inputs": {}})  # the required file is missing
    assert status == 200
    for _ in range(100):
        failed = call("/api/run?id=" + error["id"])[1]
        if failed["status"] != "running":
            break
        time.sleep(0.05)
    assert failed["status"] == "failed" and "source" in failed["error"]


def test_export_returns_a_zip_for_every_target(api):
    call, _, _ = api
    for target in ("bundle", "mcp", "job-handler", "tool-schema"):
        data = call("/api/export", {"doc": DOC, "target": target})[1]
        names = zipfile.ZipFile(io.BytesIO(base64.b64decode(data["zip"]))).namelist()
        assert names and data["files"] == sorted(names)
    assert call("/api/export", {"doc": DOC, "target": "nope"})[0] == 400


def test_foreign_hosts_and_origins_are_refused(api):
    call, _, port = api
    assert call("/api/capabilities", headers={"Host": "evil.example"})[0] == 403
    assert call("/api/save", {"path": "wf/x.yaml", "doc": DOC}, headers={"Origin": "http://evil.example"})[0] == 403
    assert call("/api/capabilities", headers={"Origin": f"http://127.0.0.1:{port}"})[0] == 200
