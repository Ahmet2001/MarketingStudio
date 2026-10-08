from pathlib import Path

import pytest
import yaml

from studio import (
    RegistryError,
    WorkflowError,
    analyze,
    build_files,
    load_registry,
    load_workflow,
)

ROOT = Path(__file__).resolve().parents[2]


def cap(cid, inputs=None, outputs=None, writes=False, env=(), cost=0):
    return {
        "id": cid, "version": "0.1.0", "title": cid, "description": cid, "status": "working",
        "inputs": inputs or {}, "outputs": outputs or {"out": {"type": "text"}},
        "requires": {"env": list(env), "binaries": [], "hardware": []},
        "permissions": {"network": True, "writes_external_state": writes, "requires_approval": writes},
        "cost": {"estimate_usd": cost, "notes": ""},
        "execution": {"type": "python", "module": "x", "function": "y"},
        "failure_modes": [f"{cid} fails"],
    }


def source(tmp_path, name, *caps):
    folder = tmp_path / name
    folder.mkdir()
    (folder / "capability.yaml").write_text(
        yaml.safe_dump({"spec_version": "0.1", "capabilities": list(caps)}), encoding="utf-8"
    )
    return folder


def wf(steps, inputs=None, outputs=None):
    return {
        "spec_version": "0.1",
        "workflow": {"id": "w", "name": "W", "inputs": inputs or {}, "steps": steps, "outputs": outputs or {}},
    }


@pytest.fixture
def registry(tmp_path):
    src = source(
        tmp_path, "mine",
        cap("my.research", {"q": {"type": "text", "required": True}}, {"notes": {"type": "text"}, "n": {"type": "integer"}}),
        cap("my.write", {"brief": {"type": "text", "required": True}}, {"draft": {"type": "text"}}),
        cap("my.post", {"text": {"type": "text", "required": True}}, {"id": {"type": "text"}}, writes=True, env=["MY_TOKEN"]),
        cap("my.count", {"n": {"type": "integer", "required": True}}, {"out": {"type": "integer"}}),
    )
    return load_registry([src])


def test_any_number_of_steps_and_branches(registry):
    doc = wf(
        [
            {"id": "a", "capability": "my.research", "with": {"q": "{{ inputs.q }}"}},
            {"id": "b", "capability": "my.write", "with": {"brief": "{{ steps.a.outputs.notes }}"}},
            {"id": "c", "capability": "my.write", "with": {"brief": "{{ steps.a.outputs.notes }}"}},
            {"id": "d", "capability": "my.write", "with": {"brief": "{{ steps.b.outputs.draft }}"}},
            {"id": "e", "capability": "my.post", "with": {"text": "{{ steps.c.outputs.draft }} / {{ steps.d.outputs.draft }}"}},
        ],
        {"q": {"type": "text", "required": True}},
        {"posted": "{{ steps.e.outputs.id }}"},
    )
    result = analyze(doc, registry)
    assert result.errors == []
    assert result.order.index("a") < result.order.index("b") < result.order.index("d") < result.order.index("e")
    assert set(result.needs["e"]) == {"c", "d"}


def test_capabilities_can_come_from_several_unrelated_sources(tmp_path):
    one = source(tmp_path, "one", cap("a.x"))
    two = source(tmp_path, "two", cap("b.y"))
    reg = load_registry([one, two])
    assert set(reg) == {"a.x", "b.y"}
    assert reg.origin["a.x"].parent == one


def test_same_id_in_two_sources_is_an_error(tmp_path):
    one = source(tmp_path, "one", cap("a.x"))
    two = source(tmp_path, "two", cap("a.x"))
    with pytest.raises(RegistryError, match="defined twice"):
        load_registry([one, two])


def test_unknown_capability_strict_and_lenient(registry):
    doc = wf([{"id": "a", "capability": "later.arrives", "with": {"x": 1}}])
    assert any("not in the registry" in e for e in analyze(doc, registry).errors)
    lenient = analyze(doc, registry, allow_unknown=True)
    assert lenient.errors == []
    assert lenient.approval["a"] is True
    files, warnings = build_files(doc, registry, allow_unknown=True)
    cap_doc = yaml.safe_load(files["capability.yaml"])["capabilities"][0]
    assert cap_doc["permissions"]["requires_approval"] is True
    assert cap_doc["cost"]["estimate_usd"] is None


def test_cycle_is_reported(registry):
    doc = wf(
        [
            {"id": "a", "capability": "my.write", "with": {"brief": "{{ steps.b.outputs.draft }}"}},
            {"id": "b", "capability": "my.write", "with": {"brief": "{{ steps.a.outputs.draft }}"}},
        ]
    )
    assert any("cycle" in e for e in analyze(doc, registry).errors)


def test_type_mismatch_and_any(registry):
    bad = wf(
        [
            {"id": "a", "capability": "my.research", "with": {"q": "x"}},
            {"id": "b", "capability": "my.count", "with": {"n": "{{ steps.a.outputs.notes }}"}},
        ]
    )
    assert any("needs integer" in e for e in analyze(bad, registry).errors)
    good = wf(
        [
            {"id": "a", "capability": "my.research", "with": {"q": "x"}},
            {"id": "b", "capability": "my.count", "with": {"n": "{{ steps.a.outputs.n }}"}},
        ]
    )
    assert analyze(good, registry).errors == []


def test_literals_unknown_keys_and_missing_required(registry):
    doc = wf([{"id": "a", "capability": "my.count", "with": {"n": "five", "zzz": 1}}])
    errors = analyze(doc, registry).errors
    assert any("not a valid integer" in e for e in errors)
    assert any("not an input" in e for e in errors)
    missing = wf([{"id": "a", "capability": "my.count"}])
    assert any("required input 'n'" in e for e in analyze(missing, registry).errors)


def test_approval_is_forced_and_cannot_be_disabled(registry):
    doc = wf([{"id": "p", "capability": "my.post", "with": {"text": "hi"}}])
    files, _ = build_files(doc, registry)
    step = yaml.safe_load(files["workflow.yaml"])["workflow"]["steps"][0]
    assert step["approval"] == "required"
    doc["workflow"]["steps"][0]["approval"] = "none"
    assert any("approval cannot be turned off" in e for e in analyze(doc, registry).errors)


def test_exported_workflow_is_a_capability_usable_as_a_step(tmp_path, registry):
    inner = wf(
        [
            {"id": "a", "capability": "my.research", "with": {"q": "{{ inputs.q }}"}},
            {"id": "b", "capability": "my.post", "with": {"text": "{{ steps.a.outputs.notes }}"}},
        ],
        {"q": {"type": "text", "required": True}},
        {"posted": "{{ steps.b.outputs.id }}"},
    )
    inner["workflow"]["id"] = "research_and_post"
    files, _ = build_files(inner, registry)
    out = tmp_path / "exported"
    out.mkdir()
    (out / "capability.yaml").write_text(files["capability.yaml"], encoding="utf-8")
    cap_doc = yaml.safe_load(files["capability.yaml"])["capabilities"][0]
    assert cap_doc["id"] == "workflow.research_and_post"
    assert cap_doc["requires"]["env"] == ["MY_TOKEN"]
    assert cap_doc["permissions"]["requires_approval"] is True
    assert cap_doc["outputs"]["posted"]["type"] == "text"
    registry2 = load_registry([tmp_path / "mine", out])
    outer = wf(
        [{"id": "x", "capability": "workflow.research_and_post", "with": {"q": "{{ inputs.topic }}"}}],
        {"topic": {"type": "text", "required": True}},
    )
    result = analyze(outer, registry2)
    assert result.errors == []
    assert result.approval["x"] is True


def test_shipped_examples_validate_against_the_repository():
    reg = load_registry([ROOT])
    for path in sorted((ROOT / "examples" / "workflows").glob("*.yaml")):
        result = analyze(load_workflow(path), reg)
        assert result.errors == [], path.name


def test_no_pool_specific_code():
    text = "\n".join(p.read_text(encoding="utf-8").lower() for p in (ROOT / "studio").glob("*.py"))
    for word in ("marketing-agent-assets", "marketingpool", "browseragent", "ethgent"):
        assert word not in text
