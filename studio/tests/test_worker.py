import json
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest

from studio import load_registry
from studio.adapters import ADAPTERS
from studio.bundle import build_bundle

ENGINE = '''
CAPABILITIES = [
    {"id": "w.double", "function": "double", "description": "Doubles.", "network": False, "writes_external_state": False},
    {"id": "w.notify", "function": "notify", "description": "Notifies.", "network": True, "writes_external_state": True},
]

def double(n: int) -> int:
    return n * 2

def notify(text: str) -> str:
    import os
    with open(os.environ["NOTIFY_FILE"], "a") as handle:
        handle.write(text)
    return "ok"
'''


def make(tmp_path, gated=True):
    folder = tmp_path / "eng"
    folder.mkdir(exist_ok=True)
    (folder / "engine.py").write_text(ENGINE, encoding="utf-8")
    reg = load_registry([folder])
    steps = [{"id": "d", "capability": "w.double", "with": {"n": "{{ inputs.n }}"}}]
    outputs = {"doubled": "{{ steps.d.outputs.result }}"}
    if gated:
        steps.append({"id": "tell", "capability": "w.notify", "with": {"text": "{{ steps.d.outputs.result | as text }}"}})
    doc = {"spec_version": "0.1", "workflow": {"id": "double_job", "name": "Double", "inputs": {"n": {"type": "integer", "required": True}},
                                               "steps": steps, "outputs": outputs}}
    return build_bundle(doc, reg)


def write(files, out: Path):
    for name, text in files.items():
        (out / name).parent.mkdir(parents=True, exist_ok=True)
        (out / name).write_text(text, encoding="utf-8")


def env(tmp_path, **extra):
    return {"PATH": "/usr/bin:/bin", "STUDIO_TOOL_HOME": str(tmp_path / "home"), "NOTIFY_FILE": str(tmp_path / "notified"), **extra}


def run(cmd, tmp_path, stdin=None, **extra):
    return subprocess.run(cmd, input=stdin, capture_output=True, text=True, env=env(tmp_path, **extra), cwd=str(tmp_path / "w"))


def test_job_handler_as_a_python_import_and_as_a_process(tmp_path):
    bundle = make(tmp_path, gated=False)
    files, notes = ADAPTERS["job-handler"](bundle)
    assert set(files) == {"handler.py", "job.schema.json", "README.md"}
    (tmp_path / "w").mkdir()
    write(files, tmp_path / "w")
    code = "import handler, json; print(json.dumps(handler.handle({'n': 4})))"
    done = run([sys.executable, "-I", "-c", "import sys; sys.path.insert(0, '.'); " + code], tmp_path)
    assert json.loads(done.stdout)["outputs"] == {"doubled": 8}
    cli = run([sys.executable, "-I", "handler.py"], tmp_path, stdin=json.dumps({"inputs": {"n": 5}}))
    assert cli.returncode == 0 and json.loads(cli.stdout)["outputs"] == {"doubled": 10}
    bad = run([sys.executable, "-I", "handler.py"], tmp_path, stdin=json.dumps({"inputs": {"n": 1}, "extra": 1}))
    assert bad.returncode == 1 and "unexpected field" in json.loads(bad.stdout)["error"]
    wrong = run([sys.executable, "-I", "handler.py"], tmp_path, stdin=json.dumps({"inputs": {"n": "x"}}))
    assert json.loads(wrong.stdout)["status"] == "failed"


def test_handler_approval_is_per_step_and_blocks_everything_until_given(tmp_path):
    files, _ = ADAPTERS["job-handler"](make(tmp_path))
    (tmp_path / "w").mkdir()
    write(files, tmp_path / "w")
    first = json.loads(run([sys.executable, "-I", "handler.py"], tmp_path, stdin=json.dumps({"inputs": {"n": 2}})).stdout)
    assert first["status"] == "awaiting_approval" and first["gated_steps"][0]["step"] == "tell"
    assert not (tmp_path / "notified").exists()
    ok = json.loads(run([sys.executable, "-I", "handler.py"], tmp_path,
                        stdin=json.dumps({"inputs": {"n": 2}, "approved_steps": ["tell"]})).stdout)
    assert ok["status"] == "done" and (tmp_path / "notified").read_text() == "4"


def test_worker_with_the_file_queue_end_to_end(tmp_path):
    files, notes = ADAPTERS["worker"](make(tmp_path))
    assert "migrations/001_double_job_jobs.sql" in files and "Dockerfile" in files
    assert any("Approval is held by the queue" in n for n in notes)
    out = tmp_path / "w"
    write(files, out)
    queue = out / "queue" / "queued"
    queue.mkdir(parents=True)
    (queue / "a.json").write_text(json.dumps({"payload": {"inputs": {"n": 3}}}))
    (queue / "bad.json").write_text(json.dumps({"payload": {"inputs": {"n": 1}, "evil": True}}))
    cmd = [sys.executable, "-I", "worker.py", "--once"]
    done = run(cmd, tmp_path, WORKER_DIR=str(out / "queue"), WORKER_POLL_MS="200")
    assert done.returncode == 0, done.stderr
    held = json.loads((out / "queue" / "awaiting_approval" / "a.json").read_text())
    assert held["results"]["status"] == "awaiting_approval" and not (tmp_path / "notified").exists()
    failed = json.loads((out / "queue" / "failed" / "bad.json").read_text())
    assert "unexpected field" in failed["error"]

    # an operator approves the step and puts the job back
    held["approved_steps"] = ["tell"]
    (queue / "a.json").write_text(json.dumps(held))
    (out / "queue" / "awaiting_approval" / "a.json").unlink()
    run(cmd, tmp_path, WORKER_DIR=str(out / "queue"))
    result = json.loads((out / "queue" / "done" / "a.json").read_text())
    assert result["status"] == "done" and result["results"]["outputs"] == {"doubled": 6}
    assert (tmp_path / "notified").read_text() == "6"
    assert not list((out / "queue" / "processing").iterdir())


def test_secrets_are_removed_from_stored_results(tmp_path):
    files, _ = ADAPTERS["worker"](make(tmp_path, gated=False))
    out = tmp_path / "w"
    write(files, out)
    (out / "queue" / "queued").mkdir(parents=True)
    (out / "queue" / "queued" / "s.json").write_text(json.dumps({"payload": {"inputs": {"n": "not a number SUPERSECRETVALUE123"}}}))
    run([sys.executable, "-I", "worker.py", "--once"], tmp_path, WORKER_DIR=str(out / "queue"), MY_API_KEY="SUPERSECRETVALUE123")
    stored = json.loads((out / "queue" / "failed" / "s.json").read_text())
    written = json.dumps([stored["results"], stored["error"]])
    assert "SUPERSECRETVALUE123" not in written and "[redacted]" in written


class FakePostgrest(BaseHTTPRequestHandler):
    jobs: list = []
    log: list = []

    def _body(self):
        length = int(self.headers.get("Content-Length") or 0)
        return json.loads(self.rfile.read(length) or b"{}")

    def _send(self, payload):
        data = json.dumps(payload).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_POST(self):
        FakePostgrest.log.append(("POST", self.path, self.headers.get("apikey")))
        queued = [j for j in FakePostgrest.jobs if j["status"] == "queued"]
        if queued:
            queued[0]["status"] = "processing"
            self._send(queued[0])
        else:
            self._send(None)

    def do_PATCH(self):
        body = self._body()
        job_id = self.path.split("id=eq.")[1]
        FakePostgrest.log.append(("PATCH", self.path, body.get("status")))
        next(j for j in FakePostgrest.jobs if j["id"] == job_id).update(body)
        self._send(None)

    def log_message(self, *args):
        pass


def test_worker_with_a_supabase_style_queue(tmp_path):
    files, _ = ADAPTERS["worker"](make(tmp_path, gated=False))
    out = tmp_path / "w"
    write(files, out)
    FakePostgrest.jobs = [{"id": "j1", "status": "queued", "payload": {"inputs": {"n": 7}}, "approved_steps": []}]
    FakePostgrest.log = []
    server = HTTPServer(("127.0.0.1", 0), FakePostgrest)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        done = run([sys.executable, "-I", "worker.py", "--once"], tmp_path, WORKER_BACKEND="supabase",
                   SUPABASE_URL=f"http://127.0.0.1:{server.server_port}", SUPABASE_SECRET_KEY="service-key-123456")
    finally:
        server.shutdown()
    assert done.returncode == 0, done.stderr
    job = FakePostgrest.jobs[0]
    assert job["status"] == "done" and job["results"]["outputs"] == {"doubled": 14}
    assert ("POST", "/rest/v1/rpc/claim_double_job_job", "service-key-123456") in FakePostgrest.log or any(
        entry[0] == "POST" and "rpc/claim_" in entry[1] for entry in FakePostgrest.log)


def test_migration_matches_the_conventions(tmp_path):
    files, _ = ADAPTERS["worker"](make(tmp_path))
    sql = files["migrations/001_double_job_jobs.sql"]
    for needle in ["create table if not exists double_job_jobs", "'awaiting_approval'", "approved_steps jsonb",
                   "for update skip locked", "enable row level security", "grant insert (owner_ref, payload)"]:
        assert needle in sql, needle
    assert "claim_double_job_job" in sql


def _talk(tmp_path, messages):
    stdin = "".join(json.dumps(m) + "\n" for m in messages)
    done = run([sys.executable, "-I", "server.py"], tmp_path, stdin=stdin)
    assert done.returncode == 0, done.stderr
    return [json.loads(line) for line in done.stdout.splitlines()]


def test_mcp_server_speaks_the_protocol_and_gates_approval(tmp_path):
    files, notes = ADAPTERS["mcp"](make(tmp_path))
    assert {"server.py", "handler.py", "mcp.json", "README.md"} <= set(files)
    assert any("stdio" in n for n in notes) and any("approve" in n for n in notes)
    (tmp_path / "w").mkdir()
    write(files, tmp_path / "w")
    call = lambda i, args: {"jsonrpc": "2.0", "id": i, "method": "tools/call", "params": {"name": "double_job", "arguments": args}}
    replies = _talk(tmp_path, [
        {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-03-26", "capabilities": {}}},
        {"jsonrpc": "2.0", "method": "notifications/initialized"},
        {"jsonrpc": "2.0", "id": 2, "method": "ping"},
        {"jsonrpc": "2.0", "id": 3, "method": "tools/list"},
        call(4, {"n": 4}),
        call(5, {"n": 4, "approve": "false"}),
        call(6, {"n": 4, "approve": True}),
        call(7, {"n": "x"}),
        {"jsonrpc": "2.0", "id": 8, "method": "tools/call", "params": {"name": "other", "arguments": {}}},
        {"jsonrpc": "2.0", "id": 9, "method": "nope"},
    ])
    by_id = {r["id"]: r for r in replies}
    assert len(replies) == 9  # the notification got no answer
    assert by_id[1]["result"]["protocolVersion"] == "2025-03-26"
    assert by_id[2]["result"] == {}
    tool = by_id[3]["result"]["tools"][0]
    assert tool["name"] == "double_job" and "approve" in tool["inputSchema"]["properties"]
    assert tool["inputSchema"]["required"] == ["n"] and tool["annotations"]["destructiveHint"] is True
    text = lambda i: json.loads(by_id[i]["result"]["content"][0]["text"])
    assert text(4)["status"] == "awaiting_approval"
    assert text(5)["status"] == "awaiting_approval"  # the text 'false' is not approval
    assert text(6)["status"] == "done" and text(6)["outputs"] == {"doubled": 8}
    assert (tmp_path / "notified").read_text() == "8"  # written once, by the approved call only
    assert text(7)["status"] == "awaiting_approval"  # gated steps are checked before inputs are parsed
    assert by_id[8]["error"]["code"] == -32602 and by_id[9]["error"]["code"] == -32601


def test_mcp_server_protects_stdout_and_survives_bad_lines(tmp_path):
    files, _ = ADAPTERS["mcp"](make(tmp_path, gated=False))
    (tmp_path / "w").mkdir()
    write(files, tmp_path / "w")
    done = run([sys.executable, "-I", "server.py"], tmp_path, stdin='not json\n[1]\n\n' + json.dumps(
        {"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": "double_job", "arguments": {"n": 2}}}) + "\n")
    lines = [json.loads(line) for line in done.stdout.splitlines()]
    assert [l.get("error", {}).get("code") for l in lines[:2]] == [-32700, -32700]
    assert json.loads(lines[2]["result"]["content"][0]["text"])["outputs"] == {"doubled": 4}
