"""Run a workflow written as a YAML file on this machine.

Validation and dependency analysis happen here (they need PyYAML and the
registry); the actual execution is ``portable.run``, which has no dependencies
and is the same code that ships inside exported bundles.
"""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any, Callable

from . import portable
from .portable import FilePolicy, RunError, RunResult, StepRecord, convert, parse_input  # noqa: F401
from .registry import Registry
from .workflow import WorkflowError, analyze, load_workflow


def resolved_workflow(doc: dict[str, Any], registry: Registry) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    """The inner workflow with ``needs`` and ``approval`` filled in, and the capabilities it uses."""

    analysis = analyze(doc, registry)
    if analysis.errors:
        raise WorkflowError(analysis.errors)
    wf = copy.deepcopy(doc["workflow"])
    for step in wf["steps"]:
        step["needs"] = analysis.needs[step["id"]]
        if analysis.approval[step["id"]]:
            step["approval"] = "required"
    return wf, {sid: cap for sid, cap in analysis.caps.items() if cap is not None}


def run_workflow(
    doc: dict[str, Any],
    registry: Registry,
    inputs: dict[str, Any],
    workdir: Path,
    *,
    approve: Callable[[str, dict[str, Any]], bool] | None = None,
    log: Callable[[str], None] = lambda message: None,
    files: FilePolicy | None = None,
) -> RunResult:
    """Validate and run. ``approve(step_id, capability)`` decides gated steps; the default refuses."""

    wf, _ = resolved_workflow(doc, registry)

    def nested_loader(cap: dict[str, Any]) -> dict[str, Any]:
        nested_doc = load_workflow(registry.origin[cap["id"]].parent / cap["execution"]["definition"])
        nested, _ = resolved_workflow(nested_doc, registry)
        return nested

    # Nested workflows can use any capability in the registry.
    capabilities = dict(registry)
    bases = {cid: registry.origin[cid].parent for cid in capabilities}
    return portable.run(
        wf, capabilities, bases, inputs, workdir,
        approve=approve, log=log, files=files or FilePolicy(allow_any_path=True), nested_loader=nested_loader,
    )
