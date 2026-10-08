from pathlib import Path

import pytest

from studio import RegistryError, analyze, load_registry
from studio.engine_file import EngineFileError, extract
from studio.runner import run_workflow

ENGINE = '''
from pathlib import Path
from typing import Literal, Optional

CAPABILITY = {
    "id": "my.shape",
    "description": "Does a thing.",
    "network": False,
    "writes_external_state": False,
}

def shape(text: str, copies: int = 2, ratio: float = 1.5, flag: bool = False,
          mode: Literal["a", "b"] = "a", extra: Optional[str] = None, source: Path = None) -> str:
    return text * copies
'''


def write(tmp_path, body, name="engine.py"):
    path = tmp_path / name
    path.write_text(body, encoding="utf-8")
    return path


def test_inputs_and_output_come_from_the_function(tmp_path):
    cap = extract(write(tmp_path, ENGINE))[0]
    assert cap["inputs"]["text"] == {"type": "text", "required": True}
    assert cap["inputs"]["copies"] == {"type": "integer", "default": 2}
    assert cap["inputs"]["ratio"]["type"] == "number"
    assert cap["inputs"]["flag"] == {"type": "boolean", "default": False}
    assert cap["inputs"]["mode"] == {"type": "enum", "values": ["a", "b"], "default": "a"}
    assert cap["inputs"]["extra"] == {"type": "text"}
    assert cap["inputs"]["source"]["type"] == "file:any"
    assert cap["outputs"] == {"result": {"type": "text"}}
    assert cap["execution"] == {"type": "python", "path": ".", "module": "engine", "function": "shape"}


def test_unspecified_means_risky(tmp_path):
    body = 'CAPABILITY = {"id": "my.send", "description": "Sends."}\ndef send(text: str) -> str:\n    return text\n'
    cap = extract(write(tmp_path, body))[0]
    assert cap["permissions"] == {"network": True, "writes_external_state": True, "requires_approval": True}


def test_the_file_is_never_executed(tmp_path):
    marker = tmp_path / "ran"
    body = f'open({str(marker)!r}, "w").write("x")\n' + ENGINE
    extract(write(tmp_path, body))
    assert not marker.exists()


def test_non_literal_metadata_is_refused(tmp_path):
    body = 'import os\nCAPABILITY = {"id": "my.x", "description": os.getcwd()}\ndef x(): pass\n'
    with pytest.raises(EngineFileError, match="plain literal"):
        extract(write(tmp_path, body))


def test_unknown_key_and_missing_function_are_explained(tmp_path):
    with pytest.raises(EngineFileError, match="unknown key"):
        extract(write(tmp_path, 'CAPABILITY = {"id": "my.x", "description": "d", "colour": 1}\ndef x(): pass\n'))
    with pytest.raises(EngineFileError, match="could not find its function"):
        extract(write(tmp_path, 'CAPABILITIES = [{"id": "my.x", "description": "d"}, {"id": "my.y", "description": "d"}]\ndef a(): pass\ndef b(): pass\n', "two.py"))


def test_file_without_a_capability_is_ignored(tmp_path):
    assert extract(write(tmp_path, "def f():\n    return 1\n")) == []


def test_registry_finds_engine_files_and_the_runner_runs_them(tmp_path):
    folder = tmp_path / "mine"
    folder.mkdir()
    write(folder, ENGINE)
    reg = load_registry([folder], check_paths=True)
    assert "my.shape" in reg
    doc = {
        "spec_version": "0.1",
        "workflow": {
            "id": "w", "name": "W",
            "inputs": {"t": {"type": "text", "required": True}},
            "steps": [{"id": "s", "capability": "my.shape", "with": {"text": "{{ inputs.t }}", "copies": 3}}],
            "outputs": {"out": "{{ steps.s.outputs.result }}"},
        },
    }
    assert analyze(doc, reg).errors == []
    assert run_workflow(doc, reg, {"t": "ab"}, tmp_path / "r").outputs["out"] == "ababab"


def test_file_inputs_arrive_as_paths_and_check_catches_a_renamed_function(tmp_path):
    folder = tmp_path / "f"
    folder.mkdir()
    write(folder, 'from pathlib import Path\nCAPABILITY = {"id": "my.size", "description": "d", "network": False, "writes_external_state": False}\n'
                  'def size(source: Path) -> int:\n    assert isinstance(source, Path)\n    return source.stat().st_size\n')
    reg = load_registry([folder])
    data = tmp_path / "data.txt"
    data.write_text("12345")
    doc = {"spec_version": "0.1", "workflow": {"id": "w", "name": "W",
           "inputs": {"f": {"type": "file:any", "required": True}},
           "steps": [{"id": "s", "capability": "my.size", "with": {"source": "{{ inputs.f }}"}}],
           "outputs": {"n": "{{ steps.s.outputs.result }}"}}}
    assert run_workflow(doc, reg, {"f": str(data)}, tmp_path / "r").outputs["n"] == 5
    (folder / "engine.py").write_text(
        (folder / "engine.py").read_text().replace("def size(", "def other(") + "\ndef another():\n    pass\n",
        encoding="utf-8")
    with pytest.raises(RegistryError, match="could not find its function"):
        load_registry([folder])
