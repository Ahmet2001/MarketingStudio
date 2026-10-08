import importlib.util
from pathlib import Path

import pytest
import yaml

from app.exporter import ExportError, build_export, load_registry

ROOT = Path(__file__).resolve().parents[3]
_spec = importlib.util.spec_from_file_location(
    "validate_capabilities", ROOT / "scripts" / "validate_capabilities.py"
)
validator = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(validator)


def node(node_id, kind, subtype, config=None, label=None):
    return {
        "id": node_id,
        "kind": kind,
        "subtype": subtype,
        "label": label or node_id,
        "x": 0,
        "y": 0,
        "config": config or {},
    }


def workflow(nodes, edges=(), name="Daily mystery"):
    return {
        "id": "w1",
        "name": name,
        "nodes": nodes,
        "edges": [
            {"id": f"{a}-{b}", "source": a, "target": b} for a, b in edges
        ],
    }


@pytest.fixture(scope="module")
def registry():
    return load_registry()


def parse(files):
    return yaml.safe_load(files["workflow.yaml"])["workflow"], yaml.safe_load(
        files["capability.yaml"]
    )["capabilities"][0]


def test_generator_only_becomes_one_step_tool(registry):
    wf = workflow(
        [node("g", "content-generator", "ai-photos", {"duration": 30, "scenes": 4, "niche": "mystery"})]
    )
    files, warnings = build_export(wf, registry)
    flow, cap = parse(files)
    assert [s["capability"] for s in flow["steps"]] == ["story.video.generate"]
    assert cap["id"] == "workflow.daily_mystery"
    assert cap["inputs"]["topic"]["required"] is True
    assert cap["inputs"]["duration"]["default"] == 30
    assert cap["permissions"]["writes_external_state"] is False
    assert {"GEMINI_API_KEY", "ELEVENLABS_API_KEY"} <= set(cap["requires"]["env"])
    assert warnings == []


def test_scheduler_is_dropped_with_warning(registry):
    wf = workflow(
        [
            node("g", "content-generator", "ai-photos"),
            node("s", "scheduler", "delay", {"delay_minutes": 5}, label="Schedule"),
        ],
        [("g", "s")],
    )
    files, warnings = build_export(wf, registry)
    flow, _ = parse(files)
    assert len(flow["steps"]) == 1
    assert any("Scheduler" in w for w in warnings)


def test_youtube_destination_requires_approval(registry):
    wf = workflow(
        [
            node("g", "content-generator", "reddit"),
            node("d", "app-connection", "youtube"),
        ],
        [("g", "d")],
    )
    files, _ = build_export(wf, registry)
    flow, cap = parse(files)
    assert [s["capability"] for s in flow["steps"]] == [
        "story.video.generate",
        "social.publish.youtube_video",
    ]
    publish = flow["steps"][1]
    assert publish["approval"] == "required"
    assert publish["with"]["video_path"] == "{{ steps.generate.outputs.video }}"
    assert flow["steps"][0]["with"]["video_game_mode"] is True
    assert "title" in cap["inputs"]
    assert cap["permissions"]["writes_external_state"] is True
    assert cap["permissions"]["requires_approval"] is True
    assert "YOUTUBE_REFRESH_TOKEN" in cap["requires"]["env"]
    assert cap["cost"]["estimate_usd"] is None


def test_type_mismatch_is_refused(registry):
    wf = workflow(
        [
            node("g", "content-generator", "ai-photos"),
            node("d", "app-connection", "instagram"),
        ],
        [("g", "d")],
    )
    with pytest.raises(ExportError, match="file:mp4"):
        build_export(wf, registry)


def test_destination_without_capability_is_refused(registry):
    wf = workflow(
        [
            node("g", "content-generator", "ai-photos"),
            node("d", "app-connection", "tiktok"),
        ],
        [("g", "d")],
    )
    with pytest.raises(ExportError, match="tiktok"):
        build_export(wf, registry)


def test_unavailable_generator_is_refused(registry):
    with pytest.raises(ExportError, match="avatar"):
        build_export(workflow([node("g", "content-generator", "avatar")]), registry)


def test_generated_capability_passes_the_validator(registry):
    wf = workflow(
        [
            node("g", "content-generator", "documentary"),
            node("d", "app-connection", "youtube"),
        ],
        [("g", "d")],
    )
    files, _ = build_export(wf, registry)
    _, cap = parse(files)
    errors: list[str] = []
    validator.check_capability(cap, "export", errors)
    assert errors == []


def test_export_has_no_consumer_specific_content(registry):
    wf = workflow([node("g", "content-generator", "ai-photos")])
    files, _ = build_export(wf, registry)
    text = "\n".join(files.values()).lower()
    for word in ("browseragent", "ethgent", "plugin.yaml", "agent pack"):
        assert word not in text
