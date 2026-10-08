import json
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from studio import analyze, load_registry
from studio.scaffold import new_engine, new_workflow
from studio.views import describe_capability, format_plan, plan_workflow

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def registry():
    return load_registry([ROOT / "examples" / "single_file", ROOT / "engines" / "story-video", ROOT / "connectors"])


def test_describe_lists_inputs_needs_and_risk(registry):
    text = describe_capability(registry["social.publish.youtube_video"], registry.origin["social.publish.youtube_video"])
    assert "title: text  required" in text and "WRITE TO THE OUTSIDE WORLD" in text and "YOUTUBE_CLIENT_ID" in text
    local = describe_capability(registry["demo.word_count"])
    assert "run locally only" in local and "source: file:any  required" in local


def doc(steps, inputs=None):
    return {"spec_version": "0.1", "workflow": {"id": "w", "name": "W", "inputs": inputs or {}, "steps": steps, "outputs": {}}}


def test_plan_reports_order_approval_and_what_is_missing(registry, monkeypatch):
    for name in ("GEMINI_API_KEY", "ELEVENLABS_API_KEY", "REPLICATE_API_TOKEN", "YOUTUBE_CLIENT_ID", "YOUTUBE_CLIENT_SECRET", "YOUTUBE_REFRESH_TOKEN"):
        monkeypatch.delenv(name, raising=False)
    wf = doc([
        {"id": "story", "capability": "story.video.generate", "with": {"topic": "x"}},
        {"id": "up", "capability": "social.publish.youtube_video", "with": {"video_path": "{{ steps.story.outputs.video }}", "title": "t"}},
    ])
    plan = plan_workflow(wf, registry)
    assert [s["id"] for s in plan["steps"]] == ["story", "up"]
    assert plan["steps"][1]["approval"] is True
    assert "step 'story': env GEMINI_API_KEY" in plan["missing"]
    assert plan["unknown_cost_steps"] == ["story"]
    text = format_plan(plan)
    assert "NEEDS APPROVAL" in text and "ready on this machine: NO" in text and "experimental" in text
    monkeypatch.setenv("GEMINI_API_KEY", "x")
    assert "step 'story': env GEMINI_API_KEY" not in plan_workflow(wf, registry)["missing"]


def test_plan_runs_nothing_and_reports_invalid_workflows(registry):
    bad = doc([{"id": "a", "capability": "no.such"}])
    plan = plan_workflow(bad, registry)
    assert plan["errors"] and "NOT VALID" in format_plan(plan)


def test_plan_counts_known_costs(registry):
    wf = doc([{"id": "a", "capability": "demo.word_count", "with": {"source": "x"}}])
    registry["demo.word_count"]["cost"]["estimate_usd"] = 0.25
    plan = plan_workflow(wf, registry)
    assert plan["total_cost_usd"] == 0.25 and plan["unknown_cost_steps"] == []


def test_new_engine_is_valid_and_never_overwrites(tmp_path):
    path = tmp_path / "e" / "summarize.py"
    assert new_engine(path, "demo.summarize", "Summarizes.") == "summarize"
    reg = load_registry([path.parent], check_paths=True)
    assert "demo.summarize" in reg and reg["demo.summarize"]["inputs"]["times"]["default"] == 1
    assert reg["demo.summarize"]["permissions"]["writes_external_state"] is False
    with pytest.raises(FileExistsError):
        new_engine(path, "demo.summarize", "again")
    with pytest.raises(ValueError):
        new_engine(tmp_path / "x.py", "NotAnId", "d")


def test_new_workflow_wires_only_what_is_unambiguous(tmp_path):
    reg = load_registry([ROOT / "examples" / "single_file"])
    path = tmp_path / "flow.yaml"
    document, notes = new_workflow(path, "count_then_headline", ["demo.word_count", "demo.headline"], reg)
    assert not [n for n in notes if n.startswith("problem")]
    steps = document["workflow"]["steps"]
    assert steps[1]["with"]["words"] == "{{ steps.word_count.outputs.result }}"
    assert steps[1]["with"]["text"] == "{{ inputs.text }}"
    assert set(document["workflow"]["inputs"]) == {"source", "text"}
    assert analyze(yaml.safe_load(path.read_text()), reg).errors == []
    with pytest.raises(FileExistsError):
        new_workflow(path, "count_then_headline", ["demo.word_count"], reg)
    with pytest.raises(ValueError, match="not in the registry"):
        new_workflow(tmp_path / "y.yaml", "y", ["nope.x"], reg)


def test_command_line_end_to_end(tmp_path):
    run = lambda *a: subprocess.run([sys.executable, "-m", "studio", *a], capture_output=True, text=True, cwd=ROOT)
    engine = tmp_path / "up.py"
    assert run("new", "engine", str(engine), "--id", "demo.up", "--description", "Repeats.").returncode == 0
    assert run("new", "engine", str(engine), "--id", "demo.up").returncode == 1  # exists
    out = run("describe", "demo.up", "--sources", str(tmp_path))
    assert out.returncode == 0 and "demo.up" in out.stdout
    assert "Did you mean" in run("describe", "word", "--sources", "examples/single_file").stderr
    flow = tmp_path / "f.yaml"
    assert run("new", "workflow", str(flow), "--id", "f", "--use", "demo.up", "--sources", str(tmp_path)).returncode == 0
    planned = run("plan", str(flow), "--sources", str(tmp_path), "--json")
    assert planned.returncode == 0 and json.loads(planned.stdout)["steps"][0]["capability"] == "demo.up"
    both = run("plan", str(flow), "--sources", str(tmp_path), "--sources", "examples/single_file")
    assert both.returncode == 0
