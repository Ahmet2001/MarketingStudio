import base64
import inspect
import json
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest
import yaml

from studio import load_registry
from studio.adapters import ADAPTERS
from studio.bundle import BundleError, build_bundle
from studio.portable import FilePolicy, RunError, load_bundle, resolve_file, run

ENGINE = '''
from pathlib import Path

CAPABILITIES = [
    {"id": "t.size", "function": "size", "description": "File size.", "network": False, "writes_external_state": False,
     "packages": ["requests"]},
    {"id": "t.send", "function": "send", "description": "Sends a message.", "network": True, "writes_external_state": True},
]

def size(source: Path) -> int:
    assert isinstance(source, Path)
    return source.stat().st_size

def send(text: str) -> str:
    import os
    with open(os.environ["SENT_FILE"], "a") as handle:
        handle.write(text)
    return "sent"
'''


@pytest.fixture
def setup(tmp_path):
    folder = tmp_path / "mine"
    folder.mkdir()
    (folder / "engine.py").write_text(ENGINE, encoding="utf-8")
    registry = load_registry([folder])
    doc = {
        "spec_version": "0.1",
        "workflow": {
            "id": "size_and_send", "name": "Size and send", "description": "Measures a file and reports it.",
            "inputs": {
                "file": {"type": "file:any", "required": True},
                "prefix": {"type": "text", "default": "size="},
                "times": {"type": "integer", "default": 1},
                "loud": {"type": "boolean", "default": False},
            },
            "steps": [
                {"id": "measure", "capability": "t.size", "with": {"source": "{{ inputs.file }}"}},
                {"id": "report", "capability": "t.send", "with": {"text": "{{ inputs.prefix }}{{ steps.measure.outputs.result }}"}},
            ],
            "outputs": {"bytes": "{{ steps.measure.outputs.result }}", "status": "{{ steps.report.outputs.result }}"},
        },
    }
    return tmp_path, registry, doc


def test_bundle_contents_and_manifest(setup):
    _, registry, doc = setup
    bundle = build_bundle(doc, registry)
    assert set(bundle.files()) >= {"manifest.json", "workflow.json", "capabilities.json", "bases.json", "portable.py", "requirements.txt"}
    assert len(bundle.engines) == 2 or len(bundle.engines) == 1
    assert bundle.manifest["gated_steps"] == [{"step": "report", "capability": "t.send"}]
    assert bundle.manifest["requires"]["packages"] == ["requests"]
    assert bundle.files()["requirements.txt"] == "requests\n"
    assert bundle.manifest["external"] == []


def test_portable_runner_has_no_dependencies():
    source = (Path(__file__).resolve().parents[1] / "portable.py").read_text(encoding="utf-8")
    imports = {l.split()[1].split(".")[0] for l in source.splitlines() if l.startswith(("import ", "from ")) and "__future__" not in l}
    stdlib = set(sys.stdlib_module_names)
    assert imports <= stdlib, imports - stdlib


def test_bundle_runs_from_its_folder_without_studio(setup, tmp_path):
    _, registry, doc = setup
    out = tmp_path / "bundle"
    for name, text in build_bundle(doc, registry).files().items():
        (out / name).parent.mkdir(parents=True, exist_ok=True)
        (out / name).write_text(text, encoding="utf-8")
    data = tmp_path / "data.txt"
    data.write_text("12345")
    sent = tmp_path / "sent.txt"
    env = {"PATH": "/usr/bin:/bin", "SENT_FILE": str(sent), "STUDIO_FILE_ROOTS": str(tmp_path)}
    cmd = [sys.executable, str(out / "portable.py"), str(out), "--input", f"file={data}", "--approve", "report", "--workdir", str(tmp_path / "w")]
    done = subprocess.run(cmd, capture_output=True, text=True, env=env, cwd="/")
    assert done.returncode == 0, done.stderr
    assert "bytes: 5" in done.stdout
    assert sent.read_text() == "size=5"


def run_tool(tool_path: Path, call: str, env_extra: dict, tmp_path: Path) -> dict:
    code = textwrap.dedent(f'''
        import importlib.util, json, inspect
        spec = importlib.util.spec_from_file_location("the_tool", {str(tool_path)!r})
        module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        print(json.dumps({call}, default=str))
    ''')
    env = {"PATH": "/usr/bin:/bin", "STUDIO_TOOL_HOME": str(tmp_path / "home"), **env_extra}
    done = subprocess.run([sys.executable, "-I", "-c", code], capture_output=True, text=True, env=env, cwd="/")
    assert done.returncode == 0, done.stderr
    return json.loads(done.stdout.strip().splitlines()[-1])


def test_agent_pack_files_and_signature(setup, tmp_path):
    _, registry, doc = setup
    files, notes = ADAPTERS["agent-pack"](build_bundle(doc, registry))
    assert set(files) == {"plugin.yaml", "tools/size_and_send.py", "env.example", "README.md"}
    plugin = yaml.safe_load(files["plugin.yaml"])
    assert plugin["type"] == "tool_pack" and plugin["tools"][0]["file"] == "tools/size_and_send.py"
    assert any("not by the agent" in n for n in notes)
    tool = files["tools/size_and_send.py"]
    assert not any(line.startswith("from __future__") for line in tool.splitlines())
    path = tmp_path / "tool.py"
    path.write_text(tool, encoding="utf-8")
    sig = run_tool(path, "{k: str(v.annotation.__name__) + ':' + str(v.default) for k, v in inspect.signature(module.size_and_send).parameters.items()}", {}, tmp_path)
    assert sig["file"].startswith("str:") and "empty" in sig["file"]
    assert sig["times"] == "int:1" and sig["loud"] == "bool:False" and sig["approve"] == "bool:False"
    assert run_tool(path, "inspect.iscoroutinefunction(module.size_and_send)", {}, tmp_path) is False
    doc_text = run_tool(path, "module.size_and_send.__doc__", {}, tmp_path)
    assert "Ask the user to confirm" in doc_text


def test_generated_tool_end_to_end(setup, tmp_path):
    _, registry, doc = setup
    files, _ = ADAPTERS["agent-pack"](build_bundle(doc, registry))
    path = tmp_path / "tool.py"
    path.write_text(files["tools/size_and_send.py"], encoding="utf-8")
    sent = tmp_path / "sent.txt"
    env = {"SENT_FILE": str(sent)}
    content = base64.b64encode(b"hello").decode()
    ref = json.dumps({"filename": "a.txt", "content_base64": content})

    # without approval nothing runs
    first = run_tool(path, f"module.size_and_send({ref!r}, prefix='n=')", env, tmp_path)
    assert first["status"] == "needs_approval" and first["gated_steps"][0]["step"] == "report"
    assert not sent.exists()

    # a local path is refused by default
    second = run_tool(path, "module.size_and_send('/etc/hostname', approve=True)", env, tmp_path)
    assert second["status"] == "error" and "allowed folders" in second["error"]

    # http, private hosts and unresolved assets are refused
    for ref_bad, expect in [("http://example.com/x", "https"), ("https://localhost/x", "private"), ("asset:abc", "resolver")]:
        bad = run_tool(path, f"module.size_and_send({ref_bad!r}, approve=True)", env, tmp_path)
        assert bad["status"] == "error" and expect in bad["error"], bad

    # approved base64 upload works and the side effect happens
    done = run_tool(path, f"module.size_and_send({ref!r}, prefix='n=', approve=True)", env, tmp_path)
    assert done["status"] == "ok", done
    assert done["outputs"]["bytes"] == 5
    assert sent.read_text() == "n=5"


def test_tool_schema_adapter(setup):
    _, registry, doc = setup
    files, _ = ADAPTERS["tool-schema"](build_bundle(doc, registry))
    tool = json.loads(files["anthropic_tool.json"])
    schema = tool["input_schema"]
    assert tool["name"] == "size_and_send"
    assert schema["required"] == ["file"]
    assert "oneOf" in schema["properties"]["file"]
    assert schema["properties"]["times"] == {"type": "integer", "default": 1}
    assert schema["properties"]["approve"]["type"] == "boolean"
    openai = json.loads(files["openai_tool.json"])
    assert openai["function"]["parameters"] == schema


def test_external_capabilities_are_recorded_not_copied(tmp_path):
    folder = tmp_path / "ext"
    folder.mkdir()
    (folder / "capability.yaml").write_text(yaml.safe_dump({"spec_version": "0.1", "capabilities": [{
        "id": "x.cli", "version": "0.1.0", "title": "x", "description": "x", "status": "working",
        "inputs": {}, "outputs": {"o": {"type": "text"}},
        "requires": {"env": [], "binaries": [], "hardware": []},
        "permissions": {"network": False, "writes_external_state": False, "requires_approval": False},
        "cost": {"estimate_usd": 0, "notes": ""},
        "execution": {"type": "cli", "cwd": ".", "command": ["true"], "outputs": {"o": "{output_dir}/o.txt"}},
        "failure_modes": []}]}), encoding="utf-8")
    reg = load_registry([folder])
    doc = {"spec_version": "0.1", "workflow": {"id": "uses_cli", "name": "U", "inputs": {}, "steps": [{"id": "a", "capability": "x.cli"}], "outputs": {}}}
    bundle = build_bundle(doc, reg)
    assert bundle.engines == {}
    assert bundle.manifest["external"][0]["override_env"] == "STUDIO_DIR_X_CLI"
    assert any("must exist on the machine" in w for w in bundle.warnings)


def test_http_capabilities_and_bad_names_are_refused(setup, tmp_path):
    _, registry, doc = setup
    registry["t.size"]["execution"] = {"type": "http", "base_url": "http://x", "operations": [{"name": "a", "method": "GET", "path": "/"}]}
    with pytest.raises(BundleError, match="http capability"):
        build_bundle(doc, registry)
    registry2 = load_registry([tmp_path / "mine"])
    doc["workflow"]["id"] = "ab"
    with pytest.raises(ValueError, match="cannot be an agent tool name"):
        ADAPTERS["agent-pack"](build_bundle(doc, registry2))


def test_resolve_file_limits(tmp_path):
    policy = FilePolicy(max_bytes=10)
    with pytest.raises(RunError, match="larger"):
        resolve_file({"filename": "a", "content_base64": base64.b64encode(b"x" * 11).decode()}, "f", tmp_path, policy)
    with pytest.raises(RunError, match="base64"):
        resolve_file({"filename": "a", "content_base64": "!!!"}, "f", tmp_path, policy)
    path = resolve_file({"filename": "../../evil name.txt", "content_base64": base64.b64encode(b"ok").decode()}, "f", tmp_path, policy)
    assert Path(path).parent == tmp_path and Path(path).read_text() == "ok"
    policy2 = FilePolicy(roots=[tmp_path], asset_resolver=lambda ident: tmp_path / "x.txt")
    (tmp_path / "x.txt").write_text("1")
    assert resolve_file("asset:42", "f", tmp_path, policy2) == str(tmp_path / "x.txt")
    assert resolve_file(str(tmp_path / "x.txt"), "f", tmp_path, policy2) == str((tmp_path / "x.txt").resolve())
    with pytest.raises(RunError, match="allowed folders"):
        resolve_file("/etc/hostname", "f", tmp_path, policy2)
