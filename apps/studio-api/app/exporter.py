"""Neutral workflow export.

Turns a saved Storyforge workflow (nodes and edges) into two plain files:

* ``workflow.yaml``   - the steps, how they connect, and the inputs they need
* ``capability.yaml`` - the workflow described as one capability (a tool)

The export knows about capabilities only. It has no knowledge of any agent,
runtime or other consumer; adapters that turn these files into something a
specific consumer understands live outside this module.

This module is pure: it imports no web framework and touches no database.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any

import yaml

from .config import WORKSPACE_ROOT

SPEC_VERSION = "0.1"
SKIP_DIRS = {"node_modules", ".venv", ".git", "__pycache__"}

# Bridge from the node subtypes the workflow editor stored to capabilities.
# `defaults` are capability inputs the mode implies.
MODE_CAPABILITIES: dict[str, tuple[str, dict[str, Any]]] = {
    "ai-photos": ("story.video.generate", {}),
    "reddit": ("story.video.generate", {"video_game_mode": True}),
    "real-images": ("documentary.video.generate", {"visual_source": "real"}),
    "documentary": ("documentary.video.generate", {"visual_source": "real"}),
}
DESTINATION_CAPABILITIES: dict[str, str | None] = {
    "youtube": "social.publish.youtube_video",
    "instagram": "social.publish.instagram_reel",
    "tiktok": None,
}
# Publish input name -> generator output name that should feed it.
PUBLISH_BINDINGS: dict[str, dict[str, str]] = {
    "social.publish.youtube_video": {"video_path": "video"},
    "social.publish.instagram_reel": {"video_url": "video"},
}
# Generator config keys that become workflow inputs when the capability has them.
GENERATOR_CONFIG_KEYS = ("topic", "language", "duration", "scenes", "niche")


class ExportError(ValueError):
    """The workflow cannot be exported as described."""


def load_registry(root: Path = WORKSPACE_ROOT) -> dict[str, dict[str, Any]]:
    registry: dict[str, dict[str, Any]] = {}
    for path in sorted(root.rglob("capability.yaml")):
        if SKIP_DIRS & set(path.parts):
            continue
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        for capability in data.get("capabilities") or []:
            registry[capability["id"]] = capability
    return registry


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
    return slug or "workflow"


def _types_compatible(produced: str, accepted: str) -> bool:
    return produced == accepted


def _reachable(start: str, edges: list[dict[str, Any]]) -> list[str]:
    targets: dict[str, list[str]] = {}
    for edge in edges:
        targets.setdefault(edge["source"], []).append(edge["target"])
    order: list[str] = []
    pending = [start]
    while pending:
        node_id = pending.pop(0)
        if node_id in order:
            continue
        order.append(node_id)
        pending.extend(targets.get(node_id, []))
    return order


def _union(steps: list[dict[str, Any]], key: str) -> list[str]:
    values: list[str] = []
    for step in steps:
        for item in (step.get("requires") or {}).get(key, []):
            if item not in values:
                values.append(item)
    return values


def build_export(
    workflow: dict[str, Any],
    registry: dict[str, dict[str, Any]] | None = None,
) -> tuple[dict[str, str], list[str]]:
    """Return ``({filename: text}, warnings)`` or raise ``ExportError``."""

    registry = registry if registry is not None else load_registry()
    warnings: list[str] = []
    nodes = {node["id"]: node for node in workflow["nodes"]}
    if len(nodes) != len(workflow["nodes"]):
        raise ExportError("Workflow node IDs must be unique.")
    generators = [n for n in workflow["nodes"] if n["kind"] == "content-generator"]
    if len(generators) != 1:
        raise ExportError("A workflow needs exactly one content generator.")
    generator = generators[0]
    for edge in workflow["edges"]:
        if edge["source"] not in nodes or edge["target"] not in nodes:
            raise ExportError("Every connection must reference an existing node.")
    reachable = [nodes[i] for i in _reachable(generator["id"], workflow["edges"])]

    # ---- generate step ----------------------------------------------------
    mode = generator["subtype"]
    if mode not in MODE_CAPABILITIES:
        raise ExportError(f"No capability exists for content generator '{mode}'.")
    gen_id, mode_defaults = MODE_CAPABILITIES[mode]
    gen_cap = registry.get(gen_id)
    if gen_cap is None:
        raise ExportError(f"Capability '{gen_id}' is not in the registry.")

    config = generator.get("config") or {}
    workflow_inputs: dict[str, dict[str, Any]] = {}
    gen_with: dict[str, Any] = dict(mode_defaults)
    for key in GENERATOR_CONFIG_KEYS:
        if key not in gen_cap["inputs"]:
            if config.get(key) not in (None, ""):
                warnings.append(
                    f"'{key}' is set on the generator but '{gen_id}' has no such input; dropped."
                )
            continue
        spec = dict(gen_cap["inputs"][key])
        value = config.get(key)
        if key == "topic":
            spec["required"] = True
            if value:
                spec["default"] = value
                spec["required"] = False
        elif value not in (None, ""):
            spec["default"] = value
        workflow_inputs[key] = spec
        gen_with[key] = "{{ inputs.%s }}" % key
    if config.get("skip_research") and "skip_research" in gen_cap["inputs"]:
        gen_with["skip_research"] = True

    steps: list[dict[str, Any]] = [
        {"id": "generate", "capability": gen_id, "with": gen_with}
    ]
    used_caps = [gen_cap]
    outputs: dict[str, dict[str, Any]] = {}
    output_refs: dict[str, str] = {}
    for name, spec in gen_cap["outputs"].items():
        outputs[name] = dict(spec)
        output_refs[name] = "{{ steps.generate.outputs.%s }}" % name

    # ---- scheduler: not part of a tool ------------------------------------
    for node in reachable:
        if node["kind"] == "scheduler":
            warnings.append(
                f"Scheduler '{node['label']}' was dropped: when to run is decided by whoever calls the tool."
            )

    # ---- destination ------------------------------------------------------
    destinations = [n for n in reachable if n["kind"] == "app-connection"]
    if len(destinations) > 1:
        raise ExportError("Use at most one destination in a workflow path.")
    if destinations:
        destination = destinations[0]["subtype"]
        pub_id = DESTINATION_CAPABILITIES.get(destination)
        if pub_id is None:
            raise ExportError(f"No publish capability exists for destination '{destination}'.")
        pub_cap = registry.get(pub_id)
        if pub_cap is None:
            raise ExportError(f"Capability '{pub_id}' is not in the registry.")
        bindings = PUBLISH_BINDINGS[pub_id]
        pub_with: dict[str, Any] = {}
        for input_name, output_name in bindings.items():
            produced = gen_cap["outputs"][output_name]["type"]
            accepted = pub_cap["inputs"][input_name]["type"]
            if not _types_compatible(produced, accepted):
                raise ExportError(
                    f"'{pub_id}' needs '{input_name}' as {accepted}, but "
                    f"'{gen_id}' produces '{output_name}' as {produced}. "
                    "An extra step that converts one into the other is missing."
                )
            pub_with[input_name] = "{{ steps.generate.outputs.%s }}" % output_name
        for name, spec in pub_cap["inputs"].items():
            if name in bindings:
                continue
            input_key = name if name not in workflow_inputs else f"publish_{name}"
            workflow_inputs[input_key] = dict(spec)
            pub_with[name] = "{{ inputs.%s }}" % input_key
        steps.append(
            {
                "id": "publish",
                "capability": pub_id,
                "needs": ["generate"],
                "approval": "required",
                "with": pub_with,
            }
        )
        used_caps.append(pub_cap)
        for name, spec in pub_cap["outputs"].items():
            key = name if name not in outputs else f"publish_{name}"
            outputs[key] = dict(spec)
            output_refs[key] = "{{ steps.publish.outputs.%s }}" % name

    # ---- documents --------------------------------------------------------
    slug = slugify(workflow["name"])
    description = (
        f"Runs: {gen_cap['title']}"
        + (f", then: {used_caps[1]['title']}" if len(used_caps) > 1 else "")
        + f" as one step (workflow '{workflow['name']}')."
    )
    workflow_doc = {
        "spec_version": SPEC_VERSION,
        "workflow": {
            "id": slug,
            "name": workflow["name"],
            "version": "0.1.0",
            "inputs": workflow_inputs,
            "steps": steps,
            "outputs": output_refs,
        },
    }

    costs = [c["cost"]["estimate_usd"] for c in used_caps]
    total_cost = None if any(c is None for c in costs) else sum(costs)
    writes = any(c["permissions"]["writes_external_state"] for c in used_caps)
    capability_doc = {
        "spec_version": SPEC_VERSION,
        "capabilities": [
            {
                "id": f"workflow.{slug}",
                "version": "0.1.0",
                "title": workflow["name"],
                "description": description,
                "status": "experimental",
                "inputs": workflow_inputs,
                "outputs": outputs,
                "requires": {
                    "env": _union(used_caps, "env"),
                    "binaries": _union(used_caps, "binaries"),
                    "hardware": _union(used_caps, "hardware"),
                },
                "permissions": {
                    "network": any(c["permissions"]["network"] for c in used_caps),
                    "writes_external_state": writes,
                    "requires_approval": writes
                    or any(c["permissions"]["requires_approval"] for c in used_caps),
                },
                "cost": {
                    "estimate_usd": total_cost,
                    "notes": "Sum of the steps. Unknown (null) when any step has no measured cost.",
                },
                "execution": {"type": "workflow", "definition": "workflow.yaml"},
                "failure_modes": [
                    f"[{cap['id']}] {mode_text}"
                    for cap in used_caps
                    for mode_text in cap["failure_modes"]
                ],
            }
        ],
    }
    header = "# Generated by the workflow exporter. Edit the source workflow, not this file.\n"
    files = {
        "workflow.yaml": header + yaml.safe_dump(workflow_doc, sort_keys=False, allow_unicode=True),
        "capability.yaml": header + yaml.safe_dump(capability_doc, sort_keys=False, allow_unicode=True),
    }
    return files, warnings


def write_export(files: dict[str, str], out_dir: Path) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    written = []
    for name, text in files.items():
        path = out_dir / name
        path.write_text(text, encoding="utf-8")
        written.append(path)
    return written


def main(argv: list[str] | None = None) -> int:
    import argparse

    from .repository import get_workflow

    parser = argparse.ArgumentParser(description="Export a saved workflow as workflow.yaml and capability.yaml.")
    parser.add_argument("workflow_id")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    workflow = get_workflow(args.workflow_id)
    if workflow is None:
        print(f"Workflow {args.workflow_id} not found.", file=sys.stderr)
        return 1
    try:
        files, warnings = build_export(workflow)
    except ExportError as error:
        print(f"Cannot export: {error}", file=sys.stderr)
        return 1
    for path in write_export(files, args.out):
        print(path)
    for warning in warnings:
        print(f"warning: {warning}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
