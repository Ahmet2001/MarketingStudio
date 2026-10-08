import sys
from pathlib import Path

import pytest
import yaml

from studio import RegistryError, WorkflowError, analyze, load_registry
from studio.runner import RunError, run_workflow

PY = sys.executable


def write_capabilities(folder: Path, *caps) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "capability.yaml").write_text(
        yaml.safe_dump({"spec_version": "0.1", "capabilities": list(caps)}), encoding="utf-8"
    )


def base(cid, inputs, outputs, execution, writes=False):
    return {
        "id": cid, "version": "0.1.0", "title": cid, "description": cid, "status": "working",
        "inputs": inputs, "outputs": outputs,
        "requires": {"env": [], "binaries": [], "hardware": []},
        "permissions": {"network": False, "writes_external_state": writes, "requires_approval": writes},
        "cost": {"estimate_usd": 0, "notes": ""}, "execution": execution, "failure_modes": ["fails"],
    }


@pytest.fixture
def tools(tmp_path):
    folder = tmp_path / "tools"
    folder.mkdir()
    (folder / "shout.py").write_text(
        "import sys, pathlib\n"
        "text, out = sys.argv[1], pathlib.Path(sys.argv[3])\n"
        "(out / 'run1').mkdir(parents=True, exist_ok=True)\n"
        "(out / 'run1' / 'result.txt').write_text(text.upper())\n"
        "(out / 'run1' / 'count.txt').write_text(str(len(text)))\n"
        "(out / 'run1' / 'draft.txt').write_text('draft')\n",
        encoding="utf-8",
    )
    (folder / "fail.py").write_text("import sys; print('boom'); sys.exit(3)\n", encoding="utf-8")
    (folder / "calc.py").write_text(
        "def double(n):\n    return {'out': n * 2}\n"
        "def send(text):\n    open(__import__('os').environ['SENT'], 'a').write(text)\n    return {'id': 'sent'}\n",
        encoding="utf-8",
    )
    write_capabilities(
        folder,
        base("t.shout", {"text": {"type": "text", "required": True}},
             {"shouted": {"type": "text"}, "count": {"type": "text"}, "file": {"type": "file:txt"}},
             {"type": "cli", "cwd": ".", "command": [PY, "shout.py"], "positional": ["text"],
              "output_dir_flag": "--out",
              "outputs": {"shouted": "{output_dir}/**/result.txt", "count": "{output_dir}/**/count.txt",
                          "file": "{output_dir}/**/result.txt"}}),
        base("t.fail", {}, {"x": {"type": "text"}},
             {"type": "cli", "cwd": ".", "command": [PY, "fail.py"], "outputs": {"x": "{output_dir}/x"}}),
        base("t.double", {"n": {"type": "integer", "required": True}}, {"out": {"type": "integer"}},
             {"type": "python", "path": ".", "module": "calc", "function": "double"}),
        base("t.send", {"text": {"type": "text", "required": True}}, {"id": {"type": "text"}},
             {"type": "python", "path": ".", "module": "calc", "function": "send"}, writes=True),
    )
    return folder


def wf(steps, inputs=None, outputs=None, wid="w"):
    return {"spec_version": "0.1",
            "workflow": {"id": wid, "name": "W", "inputs": inputs or {}, "steps": steps, "outputs": outputs or {}}}


def test_cli_and_python_steps_with_a_cast(tools, tmp_path):
    reg = load_registry([tools])
    doc = wf(
        [
            {"id": "a", "capability": "t.shout", "with": {"text": "{{ inputs.word }}"}},
            {"id": "b", "capability": "t.double", "with": {"n": "{{ steps.a.outputs.count | as integer }}"}},
        ],
        {"word": {"type": "text", "required": True}},
        {"loud": "{{ steps.a.outputs.shouted }}", "twice": "{{ steps.b.outputs.out }}", "path": "{{ steps.a.outputs.file }}"},
    )
    assert analyze(doc, reg).errors == []
    result = run_workflow(doc, reg, {"word": "hello"}, tmp_path / "run")
    assert result.outputs["loud"] == "HELLO"
    assert result.outputs["twice"] == 10
    assert result.outputs["path"].endswith("result.txt") and Path(result.outputs["path"]).is_file()
    assert [s.status for s in result.steps] == ["done", "done"]


def test_mismatch_suggests_a_cast_and_cast_makes_it_pass(tools):
    reg = load_registry([tools])
    bad = wf([
        {"id": "a", "capability": "t.shout", "with": {"text": "x"}},
        {"id": "b", "capability": "t.double", "with": {"n": "{{ steps.a.outputs.count }}"}},
    ])
    errors = analyze(bad, reg).errors
    assert any("| as integer" in e for e in errors)


def test_a_file_cannot_be_cast_to_an_integer(tools):
    reg = load_registry([tools])
    doc = wf([
        {"id": "a", "capability": "t.shout", "with": {"text": "x"}},
        {"id": "b", "capability": "t.double", "with": {"n": "{{ steps.a.outputs.file | as integer }}"}},
    ])
    assert any("cannot be converted to integer" in e for e in analyze(doc, reg).errors)


def test_gated_step_does_not_run_without_approval(tools, tmp_path, monkeypatch):
    sent = tmp_path / "sent.txt"
    monkeypatch.setenv("SENT", str(sent))
    reg = load_registry([tools])
    doc = wf([{"id": "s", "capability": "t.send", "with": {"text": "hi"}}])
    with pytest.raises(RunError, match="needs approval"):
        run_workflow(doc, reg, {}, tmp_path / "r1")
    assert not sent.exists()
    run_workflow(doc, reg, {}, tmp_path / "r2", approve=lambda step, cap: True)
    assert sent.read_text() == "hi"


def test_failure_reports_the_step_and_its_log(tools, tmp_path):
    reg = load_registry([tools])
    doc = wf([{"id": "f", "capability": "t.fail"}])
    with pytest.raises(RunError, match=r"(?s)step 'f' failed.*exited with 3.*boom"):
        run_workflow(doc, reg, {}, tmp_path / "r")


def test_required_input_and_unknown_input(tools, tmp_path):
    reg = load_registry([tools])
    doc = wf([{"id": "a", "capability": "t.shout", "with": {"text": "{{ inputs.w }}"}}],
             {"w": {"type": "text", "required": True}})
    with pytest.raises(RunError, match="required"):
        run_workflow(doc, reg, {}, tmp_path / "r")
    with pytest.raises(RunError, match="unknown input"):
        run_workflow(doc, reg, {"w": "x", "zzz": "1"}, tmp_path / "r")


def test_missing_env_is_reported_before_anything_runs(tools, tmp_path):
    reg = load_registry([tools])
    reg["t.shout"]["requires"]["env"] = ["SURELY_NOT_SET_12345"]
    doc = wf([{"id": "a", "capability": "t.shout", "with": {"text": "x"}}])
    with pytest.raises(RunError, match="SURELY_NOT_SET_12345"):
        run_workflow(doc, reg, {}, tmp_path / "r")
    assert not (tmp_path / "r" / "a" / "run1").exists()


def test_a_workflow_runs_as_a_step_of_another(tools, tmp_path):
    from studio import build_files

    reg = load_registry([tools])
    inner = wf(
        [{"id": "a", "capability": "t.shout", "with": {"text": "{{ inputs.word }}"}}],
        {"word": {"type": "text", "required": True}},
        {"loud": "{{ steps.a.outputs.shouted }}"}, wid="loud",
    )
    files, _ = build_files(inner, reg)
    exported = tmp_path / "exported"
    exported.mkdir()
    for name, text in files.items():
        (exported / name).write_text(text, encoding="utf-8")
    reg2 = load_registry([tools, exported])
    outer = wf(
        [{"id": "x", "capability": "workflow.loud", "with": {"word": "{{ inputs.w }}"}}],
        {"w": {"type": "text", "required": True}}, {"result": "{{ steps.x.outputs.loud }}"},
    )
    assert run_workflow(outer, reg2, {"w": "abc"}, tmp_path / "r").outputs["result"] == "ABC"


def test_malformed_capability_in_any_source_is_rejected(tmp_path):
    bad = tmp_path / "bad"
    write_capabilities(bad, {"id": "oops", "title": "no other fields"})
    with pytest.raises(RegistryError) as info:
        load_registry([bad])
    message = str(info.value)
    assert "missing 'version'" in message and "id must be lowercase and dot separated" in message


def test_check_paths_catches_missing_files(tmp_path):
    folder = tmp_path / "x"
    write_capabilities(folder, base("t.gone", {}, {"o": {"type": "text"}},
                                    {"type": "python", "path": ".", "module": "nothing", "function": "f"}))
    load_registry([folder])  # structure is fine
    with pytest.raises(RegistryError, match="not found"):
        load_registry([folder], check_paths=True)
