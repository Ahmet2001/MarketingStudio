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
     "packages": ["PyYAML"]},
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
    assert bundle.manifest["requires"]["packages"] == ["PyYAML"]
    assert bundle.files()["requirements.txt"] == "PyYAML\n"
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


FAKE_GATE = (
    "import os\n"
    "async def request_tool_approval(action_id, description):\n"
    "    return action_id in os.environ.get('FAKE_APPROVED', '').split(',')\n"
)


def fake_host(tmp_path: Path) -> Path:
    """A folder that looks like the agent app's approval gate: it approves what FAKE_APPROVED lists."""
    root = tmp_path / "host"
    package = root / "MarketingApp" / "environments"
    package.mkdir(parents=True, exist_ok=True)
    (root / "MarketingApp" / "__init__.py").write_text("")
    (package / "__init__.py").write_text("")
    (package / "approval_runtime.py").write_text(FAKE_GATE)
    return root


def run_tool(tool_path: Path, call: str, env_extra: dict, tmp_path: Path, host: bool = False) -> dict:
    """Run a call on a generated tool in a clean interpreter. ``host`` puts a fake approval gate on the path."""
    code = textwrap.dedent(f'''
        import asyncio, importlib.util, json, inspect, sys
        if {host!r}:
            sys.path.insert(0, {str(fake_host(tmp_path))!r})
        spec = importlib.util.spec_from_file_location("the_tool", {str(tool_path)!r})
        module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        result = {call}
        if inspect.iscoroutine(result):
            result = asyncio.run(result)
        print(json.dumps(result, default=str))
    ''')
    env = {"PATH": "/usr/bin:/bin", "STUDIO_TOOL_HOME": str(tmp_path / "home"), **env_extra}
    done = subprocess.run([sys.executable, "-I", "-c", code], capture_output=True, text=True, env=env, cwd="/")
    assert done.returncode == 0, done.stderr
    return json.loads(done.stdout.strip().splitlines()[-1])


def test_agent_pack_files_and_signature(setup, tmp_path):
    _, registry, doc = setup
    files, notes = ADAPTERS["agent-pack"](build_bundle(doc, registry))
    assert set(files) == {"plugin.yaml", "tools/size_and_send.py", "env.example", "README.md", "requirements.txt"}  # the engine declares PyYAML
    plugin = yaml.safe_load(files["plugin.yaml"])
    assert plugin["type"] == "tool_pack" and plugin["tools"][0]["file"] == "tools/size_and_send.py"
    assert any("The model cannot approve" in n for n in notes)
    tool = files["tools/size_and_send.py"]
    assert not any(line.startswith("from __future__") for line in tool.splitlines())
    path = tmp_path / "tool.py"
    path.write_text(tool, encoding="utf-8")
    sig = run_tool(path, "{k: str(v.annotation.__name__) + ':' + str(v.default) for k, v in inspect.signature(module.size_and_send).parameters.items()}", {}, tmp_path)
    assert sig["file"].startswith("str:") and "empty" in sig["file"]
    assert sig["times"] == "int:1" and sig["loud"] == "bool:False"
    assert "approve" not in sig  # the model gets no argument to approve with
    assert run_tool(path, "inspect.iscoroutinefunction(module.size_and_send)", {}, tmp_path) is True
    doc_text = run_tool(path, "module.size_and_send.__doc__", {}, tmp_path)
    assert "you cannot grant that yourself" in doc_text


def test_agent_bundle_adds_an_agent_that_owns_the_tool(setup):
    _, registry, doc = setup
    pack_files, _ = ADAPTERS["agent-pack"](build_bundle(doc, registry))
    files, notes = ADAPTERS["agent-bundle"](build_bundle(doc, registry))
    assert set(files) == set(pack_files) | {"agents/size_and_send_agent.yaml", "prompts/size_and_send_agent.md"}
    assert files["tools/size_and_send.py"] == pack_files["tools/size_and_send.py"]  # the same tool file
    plugin = yaml.safe_load(files["plugin.yaml"])
    assert plugin["type"] == "agent_bundle" and plugin["agents"] == ["agents/size_and_send_agent.yaml"]
    agent = yaml.safe_load(files["agents/size_and_send_agent.yaml"])
    assert agent["name"] == "size_and_send_agent" and agent["type"] == "config" and agent["enabled"] is True
    assert agent["tools"] == ["size_and_send"] and agent["tool_mode"] == "custom"
    assert agent["system_prompt_file"] == "prompts/size_and_send_agent.md"
    # this workflow writes outside the machine, so the agent is told never to approve on its own
    assert "you cannot approve it yourself" in files["prompts/size_and_send_agent.md"]
    assert "restart it after installing" in files["README.md"] and any("restart the agent" in n for n in notes)


def test_agent_packs_list_the_python_packages_their_engines_need(tmp_path):
    engine = tmp_path / "engine.py"
    engine.write_text(
        'CAPABILITIES = [{"id": "p.size", "function": "size", "description": "d", "network": False,\n'
        '                 "writes_external_state": False, "packages": ["humanize>=4"]}]\n'
        "def size(n: int) -> str:\n    return str(n)\n", encoding="utf-8")
    doc = {"spec_version": "0.1", "workflow": {"id": "human_size", "name": "H", "inputs": {"n": {"type": "integer", "required": True}},
           "steps": [{"id": "a", "capability": "p.size", "with": {"n": "{{ inputs.n }}"}}], "outputs": {"s": "{{ steps.a.outputs.result }}"}}}
    bundle = build_bundle(doc, load_registry([tmp_path]))
    for target in ("agent-pack", "agent-bundle"):
        files, notes = ADAPTERS[target](bundle)
        assert files["requirements.txt"] == "humanize>=4\n"
        assert any("requirements.txt" in n for n in notes)


def test_agent_packs_without_packages_have_no_requirements_file(tmp_path):
    engine = tmp_path / "engine.py"
    engine.write_text(
        'CAPABILITIES = [{"id": "p.size", "function": "size", "description": "d", "network": False, "writes_external_state": False}]\n'
        "def size(n: int) -> str:\n    return str(n)\n", encoding="utf-8")
    doc = {"spec_version": "0.1", "workflow": {"id": "plain_size", "name": "P", "inputs": {"n": {"type": "integer", "required": True}},
           "steps": [{"id": "a", "capability": "p.size", "with": {"n": "{{ inputs.n }}"}}], "outputs": {"s": "{{ steps.a.outputs.result }}"}}}
    files, _ = ADAPTERS["agent-pack"](build_bundle(doc, load_registry([tmp_path])))
    assert "requirements.txt" not in files


def test_agent_bundle_refuses_a_name_that_cannot_be_an_agent(setup):
    _, registry, doc = setup
    doc["workflow"]["id"] = "x" * 60  # fine as a tool name, too long once "_agent" is added
    with pytest.raises(ValueError, match="agent name"):
        ADAPTERS["agent-bundle"](build_bundle(doc, registry))


def test_generated_tool_end_to_end(setup, tmp_path):
    _, registry, doc = setup
    files, _ = ADAPTERS["agent-pack"](build_bundle(doc, registry))
    path = tmp_path / "tool.py"
    path.write_text(files["tools/size_and_send.py"], encoding="utf-8")
    sent = tmp_path / "sent.txt"
    content = base64.b64encode(b"hello").decode()
    ref = json.dumps({"filename": "a.txt", "content_base64": content})
    call = f"module.size_and_send({ref!r}, prefix='n=')"

    # a host with no approval gate: the tool refuses, nothing runs
    first = run_tool(path, call, {"SENT_FILE": str(sent)}, tmp_path)
    assert first["status"] == "needs_approval" and first["gated_steps"][0]["step"] == "report"
    assert not sent.exists()

    # a gate that approves a different tool does not approve this one
    other = run_tool(path, call, {"SENT_FILE": str(sent), "FAKE_APPROVED": "something_else"}, tmp_path, host=True)
    assert other["status"] == "needs_approval" and not sent.exists()

    approved = {"SENT_FILE": str(sent), "FAKE_APPROVED": "size_and_send"}
    # a local path is refused by default
    second = run_tool(path, "module.size_and_send('/etc/hostname')", approved, tmp_path, host=True)
    assert second["status"] == "error" and "allowed folders" in second["error"]

    # http, private hosts and unresolved assets are refused
    for ref_bad, expect in [("http://example.com/x", "https"), ("https://localhost/x", "private"), ("asset:abc", "resolver")]:
        bad = run_tool(path, f"module.size_and_send({ref_bad!r})", approved, tmp_path, host=True)
        assert bad["status"] == "error" and expect in bad["error"], bad

    # the host approved this tool: the upload works and the side effect happens
    done = run_tool(path, call, approved, tmp_path, host=True)
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
    assert bundle.bases["x.cli"] == "external/ext" and bundle.manifest["external"][0]["folder"] == "external/ext"


def test_nothing_of_the_studio_machine_leaks_into_bundles_or_adapters(tmp_path):
    secret = tmp_path / "private_user_dir" / "ext"
    secret.mkdir(parents=True)
    (secret / "capability.yaml").write_text(yaml.safe_dump({"spec_version": "0.1", "capabilities": [{
        "id": "x.cli", "version": "0.1.0", "title": "x", "description": "x", "status": "working",
        "inputs": {}, "outputs": {"o": {"type": "text"}},
        "requires": {"env": [], "binaries": [], "hardware": []},
        "permissions": {"network": False, "writes_external_state": False, "requires_approval": False},
        "cost": {"estimate_usd": 0, "notes": ""},
        "execution": {"type": "cli", "cwd": ".", "command": ["true"], "outputs": {"o": "{output_dir}/o.txt"}},
        "failure_modes": []}]}), encoding="utf-8")
    doc = {"spec_version": "0.1", "workflow": {"id": "uses_cli", "name": "U", "inputs": {}, "steps": [{"id": "a", "capability": "x.cli"}], "outputs": {}}}
    bundle = build_bundle(doc, load_registry([secret]))
    texts = list(bundle.files().values()) + list(bundle.warnings)
    for name, adapter in ADAPTERS.items():
        files, notes = adapter(bundle)
        texts += list(files.values()) + notes
    assert texts and not [t for t in texts if "private_user_dir" in t or str(tmp_path) in t]


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


AGENT_STYLE_LOADER = '''
from __future__ import annotations
import inspect, json, sys, types

def load(path, name):
    # how the agent reads a custom tool: compile() inherits this file's future flags
    module = types.ModuleType("custom_tool_" + name)
    exec(compile(open(path, encoding="utf-8").read(), path, "exec"), module.__dict__)
    return getattr(module, name)
'''


def test_tool_keeps_real_types_when_the_agent_compiles_it_with_future_annotations(setup, tmp_path):
    _, registry, doc = setup
    files, _ = ADAPTERS["agent-pack"](build_bundle(doc, registry))
    tool = tmp_path / "tool.py"
    tool.write_text(files["tools/size_and_send.py"], encoding="utf-8")
    loader = tmp_path / "loader.py"
    loader.write_text(AGENT_STYLE_LOADER, encoding="utf-8")
    code = textwrap.dedent(f'''
        import sys, json, inspect
        sys.path.insert(0, {str(tmp_path)!r})
        import loader
        fn = loader.load({str(tool)!r}, "size_and_send")
        types = {{k: getattr(v.annotation, "__name__", str(v.annotation)) for k, v in inspect.signature(fn).parameters.items()}}
        print(json.dumps(types))
    ''')
    done = subprocess.run([sys.executable, "-I", "-c", code], capture_output=True, text=True, cwd="/")
    assert done.returncode == 0, done.stderr
    types = json.loads(done.stdout)
    assert types == {"file": "str", "prefix": "str", "times": "int", "loud": "bool"}


def test_the_model_cannot_approve_with_an_argument(setup, tmp_path):
    _, registry, doc = setup
    files, _ = ADAPTERS["agent-pack"](build_bundle(doc, registry))
    path = tmp_path / "tool.py"
    path.write_text(files["tools/size_and_send.py"], encoding="utf-8")
    ref = json.dumps({"filename": "a.txt", "content_base64": base64.b64encode(b"hi").decode()})
    sent = tmp_path / "sent.txt"
    # no `approve` argument exists, whatever the value
    for value in ("true", "True", True, 1, "yes"):
        done = subprocess.run(
            [sys.executable, "-I", "-c", textwrap.dedent(f'''
                import importlib.util
                spec = importlib.util.spec_from_file_location("t", {str(path)!r})
                module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
                import asyncio; asyncio.run(module.size_and_send({ref!r}, approve={value!r}))
            ''')],
            capture_output=True, text=True, env={"PATH": "/usr/bin:/bin", "SENT_FILE": str(sent), "STUDIO_TOOL_HOME": str(tmp_path / "h")}, cwd="/")
        assert done.returncode != 0 and "unexpected keyword argument 'approve'" in done.stderr, (value, done.stderr)
    assert not sent.exists()