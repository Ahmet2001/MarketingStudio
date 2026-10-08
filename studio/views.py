"""Read-only views for people: what is this capability, and what would this workflow need.

Nothing here runs a workflow.
"""

from __future__ import annotations

import os
import shutil
from typing import Any

from . import portable
from .registry import Registry
from .workflow import analyze


def describe_capability(cap: dict[str, Any], origin: Any = None) -> str:
    lines = [f"{cap['id']}  v{cap['version']}  [{cap['status']}]", cap["description"], ""]
    if origin:
        lines.append(f"defined in: {origin}")
    for title, section in (("inputs", "inputs"), ("outputs", "outputs")):
        lines.append(f"{title}:")
        items = cap.get(section) or {}
        if not items:
            lines.append("  (none)")
        for name, spec in items.items():
            kind = spec["type"] + (f" ({'|'.join(map(str, spec['values']))})" if spec.get("values") else "")
            extra = ""
            if section == "inputs":
                extra = "  required" if spec.get("required") and "default" not in spec else (
                    f"  default {spec['default']!r}" if "default" in spec else "  optional")
            note = f"  - {spec['description']}" if spec.get("description") else ""
            lines.append(f"  {name}: {kind}{extra}{note}")
    req = cap.get("requires") or {}
    needs = [f"{label} {', '.join(req[key])}" for key, label in
             (("env", "env"), ("binaries", "programs"), ("packages", "python packages"), ("hardware", "hardware"))
             if req.get(key)]
    lines += ["", "needs: " + ("; ".join(needs) if needs else "nothing special")]
    perms = cap["permissions"]
    may = ", ".join(filter(None, [
        "use the network" if perms["network"] else "",
        "WRITE TO THE OUTSIDE WORLD (needs approval)" if perms["writes_external_state"] else "",
    ]))
    lines.append("may: " + (may or "run locally only"))
    cost = cap["cost"]["estimate_usd"]
    lines.append("cost: " + ("unknown" if cost is None else f"about ${cost:g}") + (f" ({cap['cost']['notes']})" if cap["cost"].get("notes") else ""))
    ex = cap["execution"]
    how = {"cli": lambda: "runs `" + " ".join(map(str, ex["command"])) + "`",
           "python": lambda: f"calls {ex['module']}.{ex['function']}",
           "http": lambda: "calls an http service",
           "workflow": lambda: f"runs the workflow {ex['definition']}"}[ex["type"]]()
    lines.append(f"runs by: {ex['type']}: {how}")
    if cap.get("failure_modes"):
        lines += ["can fail when:", *[f"  - {m}" for m in cap["failure_modes"]]]
    return "\n".join(lines)


def plan_workflow(doc: dict[str, Any], registry: Registry, *, allow_unknown: bool = False) -> dict[str, Any]:
    """What running this workflow would involve, checked against this machine. Runs nothing."""

    analysis = analyze(doc, registry, allow_unknown=allow_unknown)
    wf = doc["workflow"]
    steps = {s["id"]: s for s in wf["steps"]}
    plan: dict[str, Any] = {
        "name": wf.get("name"),
        "errors": analysis.errors,
        "warnings": analysis.warnings,
        "inputs": {n: ("required" if s.get("required") and "default" not in s else f"default {s.get('default')!r}" if "default" in s else "optional") for n, s in (wf.get("inputs") or {}).items()},
        "steps": [],
        "missing": [],
        "unknown_cost_steps": [],
        "total_cost_usd": 0.0,
    }
    if analysis.errors:
        return plan
    for sid in analysis.order:
        cap = analysis.caps[sid]
        entry: dict[str, Any] = {
            "id": sid, "capability": steps[sid]["capability"], "needs": analysis.needs[sid],
            "approval": analysis.approval[sid], "known": cap is not None,
        }
        if cap is not None:
            ex = cap["execution"]
            entry["kind"] = ex["type"]
            entry["status"] = cap["status"]
            entry["where"] = "inline (single-file engine)" if registry.origin[cap["id"]].suffix == ".py" else f"external ({registry.origin[cap['id']].parent})"
            req = cap.get("requires") or {}
            entry["missing"] = (
                [f"env {e}" for e in req.get("env", []) if not os.environ.get(e)]
                + [f"program {b}" for b in req.get("binaries", []) if not shutil.which(b)]
            )
            names = portable.package_names(req.get("packages", []))
            if names:
                interpreter = portable.python_command(ex["command"])[0] if ex["type"] == "cli" else None
                absent = portable.missing_packages(names, interpreter)
                entry["missing"] += [f"python package {n}" for n in (absent or [])]
            if ex["type"] == "http":
                entry["missing"].append("the local runner cannot execute http capabilities")
            cost = cap["cost"]["estimate_usd"]
            if cost is None:
                plan["unknown_cost_steps"].append(sid)
            else:
                plan["total_cost_usd"] += cost
            plan["missing"] += [f"step '{sid}': {m}" for m in entry["missing"]]
        else:
            plan["unknown_cost_steps"].append(sid)
        plan["steps"].append(entry)
    return plan


def format_plan(plan: dict[str, Any]) -> str:
    if plan["errors"]:
        return "\n".join(["NOT VALID:", *[f"  - {e}" for e in plan["errors"]]])
    lines = [f"{plan['name']}", "", "inputs:"]
    lines += [f"  {n}: {how}" for n, how in plan["inputs"].items()] or ["  (none)"]
    lines += ["", "steps, in the order they would run:"]
    for i, step in enumerate(plan["steps"], 1):
        flags = []
        if step["approval"]:
            flags.append("NEEDS APPROVAL")
        if step.get("status") and step["status"] != "working":
            flags.append(step["status"])
        if step.get("missing"):
            flags.append("MISSING: " + "; ".join(step["missing"]))
        after = f" (after {', '.join(step['needs'])})" if step["needs"] else ""
        where = f" - {step['where']}" if step.get("where") else " - not in the registry"
        lines.append(f"  {i}. {step['id']}: {step['capability']}{after}{where}" + (f"  [{'; '.join(flags)}]" if flags else ""))
    cost = plan["total_cost_usd"]
    unknown = plan["unknown_cost_steps"]
    lines += ["", "cost: " + (f"${cost:g} counted" if cost else "nothing counted") +
              (f", UNKNOWN for {', '.join(unknown)}" if unknown else "")]
    gated = [s["id"] for s in plan["steps"] if s["approval"]]
    lines.append("approval: " + (f"needed for {', '.join(gated)}; nothing after the first of them runs without it" if gated else "none needed"))
    lines.append("ready on this machine: " + ("yes" if not plan["missing"] else "NO"))
    lines += [f"  - {m}" for m in plan["missing"]]
    lines += [f"warning: {w}" for w in plan["warnings"]]
    return "\n".join(lines)
