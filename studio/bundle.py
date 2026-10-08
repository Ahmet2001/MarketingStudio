"""Self-contained bundles.

A bundle is a folder that runs without ``studio`` installed:

    manifest.json       what the workflow is, needs, and may do
    workflow.json       the validated steps (dependencies and approvals filled in)
    capabilities.json   the capabilities those steps use
    bases.json          where each capability's files live
    portable.py         the standard-library runner
    engines/            the source of every single-file engine the workflow uses
    requirements.txt    Python packages those engines declare

Two kinds of capability are handled differently:

* **inline**   - single-file engines. Their source is copied into the bundle, so
  they run anywhere.
* **external** - everything else (command-line engines, services). They are not
  copied; the bundle records where they were found and checks they exist on the
  machine that runs it. ``STUDIO_DIR_<CAPABILITY_ID>`` points at another folder.
"""

from __future__ import annotations

import copy
import hashlib
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .registry import Registry
from .runner import resolved_workflow
from .workflow import WorkflowError, analyze, build_capability

PORTABLE_SOURCE = Path(__file__).with_name("portable.py")


class BundleError(ValueError):
    """The workflow cannot be bundled."""


@dataclass
class Bundle:
    manifest: dict[str, Any]
    workflow: dict[str, Any]
    capabilities: dict[str, dict[str, Any]]
    bases: dict[str, str]
    engines: dict[str, str]
    warnings: list[str] = field(default_factory=list)

    @property
    def requirements(self) -> list[str]:
        return list(self.manifest["requires"].get("packages", []))

    def files(self) -> dict[str, str]:
        dump = lambda value: json.dumps(value, indent=2, ensure_ascii=False) + "\n"  # noqa: E731
        files = {
            "manifest.json": dump(self.manifest),
            "workflow.json": dump(self.workflow),
            "capabilities.json": dump(self.capabilities),
            "bases.json": dump(self.bases),
            "portable.py": PORTABLE_SOURCE.read_text(encoding="utf-8"),
            "requirements.txt": "".join(f"{p}\n" for p in self.requirements),
        }
        files.update(self.engines)
        return files


def env_override(capability_id: str) -> str:
    return "STUDIO_DIR_" + re.sub(r"\W", "_", capability_id).upper()


def _folder_name(source: Path, taken: dict[Path, str]) -> str:
    """The engine folder's own name; a hash suffix keeps two same-named folders apart."""

    if source not in taken:
        name = re.sub(r"[^\w.-]", "_", source.name) or "engine"
        if name in taken.values():
            name += "_" + hashlib.sha1(str(source).encode()).hexdigest()[:6]
        taken[source] = name
    return taken[source]


def build_bundle(doc: dict[str, Any], registry: Registry) -> Bundle:
    analysis = analyze(doc, registry)
    if analysis.errors:
        raise WorkflowError(analysis.errors)
    workflow, _ = resolved_workflow(doc, registry)
    capabilities: dict[str, dict[str, Any]] = {}
    bases: dict[str, str] = {}
    engines: dict[str, str] = {}
    inline: list[str] = []
    external: list[dict[str, str]] = []
    warnings: list[str] = []
    taken: dict[Path, str] = {}

    for step in workflow["steps"]:
        cid = step["capability"]
        if cid in capabilities:
            continue
        cap = copy.deepcopy(registry[cid])
        kind = cap["execution"]["type"]
        origin = registry.origin[cid]
        if kind == "workflow":
            raise BundleError(f"'{cid}' is itself a workflow; bundling nested workflows is not supported yet.")
        if kind == "http":
            raise BundleError(f"'{cid}' is an http capability; a bundle can only run command-line and Python capabilities.")
        capabilities[cid] = cap
        if origin.suffix == ".py":
            source = origin.read_text(encoding="utf-8")
            folder = "engines/" + hashlib.sha1(source.encode()).hexdigest()[:8]
            engines[f"{folder}/{origin.name}"] = source
            bases[cid] = folder
            inline.append(cid)
        else:
            # Only the folder's name is recorded, never where it lives on this machine.
            source = origin.parent.resolve()
            bases[cid] = "external/" + _folder_name(source, taken)
            external.append({"capability": cid, "folder": bases[cid], "override_env": env_override(cid)})

    capability = build_capability({"workflow": workflow}, analysis, registry)
    packages: list[str] = []
    for cap in capabilities.values():
        for pkg in (cap.get("requires") or {}).get("packages", []):
            if pkg not in packages:
                packages.append(pkg)
    requires = dict(capability["requires"])
    if packages:
        requires["packages"] = packages
    manifest = {
        "bundle_version": "0.1",
        "id": workflow["id"],
        "name": workflow["name"],
        "version": capability["version"],
        "description": capability["description"],
        "inputs": capability["inputs"],
        "outputs": capability["outputs"],
        "requires": requires,
        "permissions": capability["permissions"],
        "gated_steps": [
            {"step": s["id"], "capability": s["capability"]}
            for s in workflow["steps"]
            if s.get("approval") == "required"
        ],
        "inline": inline,
        "external": external,
    }
    for item in external:
        warnings.append(
            f"'{item['capability']}' is not copied into the bundle: it must exist on the machine that runs it "
            f"(expected in a folder named '{item['folder'].split('/', 1)[1]}'; "
            f"set {item['override_env']} to the folder that holds it)."
        )
    return Bundle(manifest, workflow, capabilities, bases, engines, warnings)
