"""Starting files for people: a single-file engine, or a workflow built from capabilities."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

from .registry import Registry
from .workflow import ID_RE, analyze, compatible

ENGINE = '''"""{description}"""

from pathlib import Path  # remove if you do not take a file

# Everything the factory needs to know about this engine. The file is read, never run, when it is loaded.
CAPABILITY = {{
    "id": "{cid}",
    "description": "{description}",
    # Say True only if it is true. Anything left out is assumed risky (network yes, writes outside yes).
    "network": False,
    "writes_external_state": False,
    # "packages": ["requests"],      # Python packages it needs, checked before a run
    # "env": ["MY_API_KEY"],         # environment variables it needs
}}


def {function}(text: str, times: int = 1) -> str:
    """The parameters are the inputs (the annotation is the type, a default makes it optional).
    The return annotation is the output, named "result"."""
    return text * times
'''


def new_engine(path: Path, cid: str, description: str) -> str:
    if path.exists():
        raise FileExistsError(f"{path} already exists; not overwriting it.")
    if not re.fullmatch(r"[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)+", cid):
        raise ValueError("the capability id must be lowercase and dot separated, like 'team.thing'")
    function = re.sub(r"\W", "_", cid.rsplit(".", 1)[-1])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(ENGINE.format(cid=cid, description=description, function=function), encoding="utf-8")
    return function


def _unique(base: str, taken: set[str]) -> str:
    name, n = base, 2
    while name in taken:
        name, n = f"{base}_{n}", n + 1
    return name


def new_workflow(path: Path, wid: str, uses: list[str], registry: Registry) -> tuple[dict[str, Any], list[str]]:
    """Build a workflow that runs the given capabilities in order.

    A step input is wired to an earlier step's output only when the choice is
    unambiguous (same name, or the only output of that type); everything else
    becomes a workflow input for you to fill in or rewire. Returns the document
    and a list of notes about what it guessed.
    """

    if path.exists():
        raise FileExistsError(f"{path} already exists; not overwriting it.")
    if not ID_RE.match(wid):
        raise ValueError("the workflow id must be lowercase letters, digits and underscores, starting with a letter")
    unknown = [u for u in uses if u not in registry]
    if unknown:
        raise ValueError("not in the registry: " + ", ".join(unknown))
    inputs: dict[str, Any] = {}
    steps: list[dict[str, Any]] = []
    notes: list[str] = []
    produced: list[tuple[str, str, str]] = []  # (step id, output name, type)
    for cid in uses:
        cap = registry[cid]
        sid = _unique(re.sub(r"\W", "_", cid.rsplit(".", 1)[-1]), {s["id"] for s in steps})
        with_: dict[str, Any] = {}
        for name, spec in cap["inputs"].items():
            if not spec.get("required") or "default" in spec:
                continue  # leave optional inputs at their defaults; add them by hand if wanted
            same_name = [p for p in produced if p[1] == name and compatible(p[2], spec["type"])]
            same_type = [p for p in produced if p[2] == spec["type"]]
            pick = same_name[-1] if same_name else (same_type[0] if len(same_type) == 1 else None)
            if pick:
                with_[name] = "{{ steps.%s.outputs.%s }}" % (pick[0], pick[1])
                notes.append(f"{sid}.{name} <- {pick[0]}.{pick[1]}")
            else:
                key = name if name not in inputs else f"{sid}_{name}"
                inputs[key] = {k: v for k, v in spec.items() if k in {"type", "required", "values", "description"}}
                with_[name] = "{{ inputs.%s }}" % key
        steps.append({"id": sid, "capability": cid, **({"with": with_} if with_ else {})})
        produced += [(sid, out, spec["type"]) for out, spec in cap["outputs"].items()]
    last = steps[-1]["id"]
    outputs = {name: "{{ steps.%s.outputs.%s }}" % (last, name) for name in registry[uses[-1]]["outputs"]}
    doc = {
        "spec_version": "0.1",
        "workflow": {"id": wid, "name": wid.replace("_", " ").capitalize(), "version": "0.1.0",
                     "inputs": inputs, "steps": steps, "outputs": outputs},
    }
    errors = analyze(doc, registry).errors
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "# Written by `studio new workflow`. Check the wiring: it only connected what was unambiguous.\n"
        + yaml.safe_dump(doc, sort_keys=False, allow_unicode=True), encoding="utf-8")
    return doc, notes + [f"problem: {e}" for e in errors]
