import base64
import io
import json
import threading
import urllib.error
import urllib.request
import zipfile
from http.server import ThreadingHTTPServer
from pathlib import Path

import pytest
import yaml

from ui.server import TARGETS, Viewer, make_handler

REPO = Path(__file__).resolve().parents[2]
DOC = {"spec_version": "0.1", "workflow": {
    "id": "word_counter", "name": "Word counter", "description": "Counts words.", "inputs": {"source": {"type": "file:any", "required": True}},
    "steps": [{"id": "count", "capability": "demo.word_count", "with": {"source": "{{ inputs.source }}"}}],
    "outputs": {"n": "{{ steps.count.outputs.result }}"}}}


@pytest.fixture()
def api(tmp_path):
    (tmp_path / "wf").mkdir()
    (tmp_path / "wf" / "one.yaml").write_text(yaml.safe_dump(DOC), encoding="utf-8")
    broken = json.loads(json.dumps(DOC))
    broken["workflow"]["steps"][0]["with"]["source"] = "{{ inputs.nope }}"
    (tmp_path / "wf" / "broken.yaml").write_text(yaml.safe_dump(broken), encoding="utf-8")
    (tmp_path / "wf" / "notes.yaml").write_text("just: a config file\n", encoding="utf-8")
    viewer = Viewer([REPO / "examples" / "single_file"], tmp_path)
    holder = {}
    server = ThreadingHTTPServer(("127.0.0.1", 0), lambda *a, **k: make_handler(viewer, holder["port"])(*a, **k))
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


def test_page_and_catalogue(api):
    call, _, _ = api
    status, page = call("/", raw=True)
    assert status == 200 and b"<title>" in page
    data = call("/api/capabilities")[1]
    assert {c["id"] for c in data["capabilities"]} == {"demo.word_count", "demo.headline"}
    assert [t["id"] for t in data["targets"]][0] == "bundle" and {t["id"] for t in data["targets"]} == set(TARGETS)


def test_workflow_list_marks_valid_and_broken_and_skips_other_yaml(api):
    call, _, _ = api
    found = {w["path"]: w for w in call("/api/workflows")[1]["workflows"]}
    assert set(found) == {"wf/one.yaml", "wf/broken.yaml"}
    assert found["wf/one.yaml"]["valid"] and found["wf/one.yaml"]["steps"] == 1
    assert not found["wf/broken.yaml"]["valid"] and found["wf/broken.yaml"]["errors"] >= 1


def test_workflow_detail_has_order_plan_and_capabilities(api):
    call, _, _ = api
    d = call("/api/workflow?path=wf/one.yaml")[1]
    assert d["errors"] == [] and d["order"] == ["count"] and d["plan"]["errors"] == []
    assert "demo.word_count" in d["capabilities"] and d["yaml"].startswith("spec_version")
    b = call("/api/workflow?path=wf/broken.yaml")[1]
    assert b["errors"] and b["plan"] is None


def test_export_shows_the_files_of_every_target_and_a_matching_zip(api):
    call, root, _ = api
    for target in TARGETS:
        data = call("/api/export", {"path": "wf/one.yaml", "target": target})[1]
        names = [f["name"] for f in data["files"]]
        assert names and all(f["text"] for f in data["files"] if f["size"])
        assert sorted(zipfile.ZipFile(io.BytesIO(base64.b64decode(data["zip"]))).namelist()) == names
    assert any(f["name"] == "server.py" for f in call("/api/export", {"path": "wf/one.yaml", "target": "mcp"})[1]["files"])
    assert call("/api/export", {"path": "wf/one.yaml", "target": "nope"})[0] == 400
    short = json.loads(json.dumps(DOC))
    short["workflow"]["id"] = "wc"
    (root / "wf" / "short.yaml").write_text(yaml.safe_dump(short), encoding="utf-8")
    refused = call("/api/export", {"path": "wf/short.yaml", "target": "agent-pack"})[1]
    assert "agent tool name" in refused["errors"][0]  # an adapter's refusal is shown, not hidden
    assert call("/api/export", {"path": "wf/broken.yaml", "target": "mcp"})[1]["errors"]


def test_only_yaml_inside_the_root_is_readable_and_nothing_can_be_written(api):
    call, root, port = api
    for evil in ("../x.yaml", "/etc/hosts", "wf/one.yaml/../../../etc/passwd", "wf/missing.yaml"):
        assert call("/api/workflow?path=" + evil)[0] in {403, 404}
    assert call("/api/workflow?path=wf/notes.yaml")[0] == 400
    assert call("/api/save", {"path": "wf/x.yaml", "doc": DOC})[0] == 404 and not (root / "wf" / "x.yaml").exists()
    assert call("/api/run", {"doc": DOC})[0] == 404


def test_foreign_hosts_and_origins_are_refused(api):
    call, _, port = api
    assert call("/api/capabilities", headers={"Host": "evil.example"})[0] == 403
    assert call("/api/export", {"path": "wf/one.yaml", "target": "mcp"}, headers={"Origin": "http://evil.example"})[0] == 403
    assert call("/api/capabilities", headers={"Origin": f"http://127.0.0.1:{port}"})[0] == 200
