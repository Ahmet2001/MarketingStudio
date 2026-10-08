"""Validate capability files from any source against spec v0.1."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

ID_RE = re.compile(r"^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)+$")
BASE_TYPES = {"any", "text", "integer", "number", "boolean", "enum", "url", "list", "object"}
STATUSES = {"working", "experimental", "planned"}
EXEC_TYPES = {"cli", "http", "python", "workflow"}
REQUIRED = ["id", "version", "title", "description", "status", "inputs", "outputs",
            "requires", "permissions", "cost", "execution", "failure_modes"]


def valid_type(value: object) -> bool:
    return isinstance(value, str) and (
        value in BASE_TYPES or re.fullmatch(r"file:[a-z0-9]+", value) is not None
    )


def check_capability(
    cap: dict[str, Any],
    where: str,
    base_dir: Path | None = None,
    *,
    check_paths: bool = False,
) -> list[str]:
    """Return the problems found in one capability.

    ``base_dir`` is the directory of the capability.yaml; ``cwd``, ``path`` and
    ``definition`` in ``execution`` are relative to it. With ``check_paths``
    the files they point to must exist.
    """

    errors: list[str] = []
    for key in REQUIRED:
        if key not in cap:
            errors.append(f"{where}: missing '{key}'")
    where = f"{where} [{cap.get('id', '?')}]"
    if "id" in cap and not ID_RE.match(str(cap["id"])):
        errors.append(f"{where}: id must be lowercase and dot separated, like 'team.thing'")
    if cap.get("status") not in STATUSES:
        errors.append(f"{where}: status must be one of {sorted(STATUSES)}")
    for section in ("inputs", "outputs"):
        for name, spec in (cap.get(section) or {}).items():
            if not isinstance(spec, dict) or not valid_type(spec.get("type")):
                errors.append(f"{where}: {section}.{name} has an invalid type")
            elif spec["type"] == "enum" and not spec.get("values"):
                errors.append(f"{where}: {section}.{name} is an enum without values")
    for key in ("env", "binaries", "hardware"):
        if not isinstance((cap.get("requires") or {}).get(key), list):
            errors.append(f"{where}: requires.{key} must be a list")
    packages = (cap.get("requires") or {}).get("packages", [])
    if not isinstance(packages, list) or not all(isinstance(p, str) for p in packages):
        errors.append(f"{where}: requires.packages must be a list of package names")
    perms = cap.get("permissions") or {}
    for key in ("network", "writes_external_state", "requires_approval"):
        if not isinstance(perms.get(key), bool):
            errors.append(f"{where}: permissions.{key} must be true or false")
    if perms.get("writes_external_state") and not perms.get("requires_approval"):
        errors.append(f"{where}: writes_external_state requires requires_approval: true")
    if "estimate_usd" not in (cap.get("cost") or {}):
        errors.append(f"{where}: cost.estimate_usd is required (null when unknown)")
    if not isinstance(cap.get("failure_modes"), list):
        errors.append(f"{where}: failure_modes must be a list")

    execution = cap.get("execution") or {}
    kind = execution.get("type")
    if kind not in EXEC_TYPES:
        errors.append(f"{where}: execution.type must be one of {sorted(EXEC_TYPES)}")
    base = base_dir or Path(".")
    if kind == "cli":
        if not isinstance(execution.get("command"), list) or not execution["command"]:
            errors.append(f"{where}: execution.command must be a non-empty list")
        inputs = cap.get("inputs") or {}
        mapped = list(execution.get("positional") or []) + list((execution.get("flags") or {}).keys())
        for name in mapped:
            if name not in inputs:
                errors.append(f"{where}: execution maps unknown input '{name}'")
        for name in cap.get("outputs") or {}:
            if name not in (execution.get("outputs") or {}):
                errors.append(f"{where}: output '{name}' has no execution.outputs path")
        if check_paths and not (base / execution.get("cwd", ".")).is_dir():
            errors.append(f"{where}: execution.cwd '{execution.get('cwd', '.')}' does not exist")
    elif kind == "workflow":
        if not execution.get("definition"):
            errors.append(f"{where}: execution.definition is required for workflow capabilities")
        elif check_paths and not (base / execution["definition"]).is_file():
            errors.append(f"{where}: workflow definition '{execution['definition']}' does not exist")
    elif kind == "python":
        module, func = str(execution.get("module", "")), str(execution.get("function", ""))
        if not module or not func:
            errors.append(f"{where}: execution.module and execution.function are required")
        elif check_paths:
            source = base / execution.get("path", ".") / (module.replace(".", "/") + ".py")
            if not source.is_file():
                errors.append(f"{where}: module file {source} not found")
            elif f"def {func}(" not in source.read_text(encoding="utf-8"):
                errors.append(f"{where}: function '{func}' not found in {source}")
    elif kind == "http":
        if not execution.get("operations"):
            errors.append(f"{where}: execution.operations is required for http capabilities")
    return errors


def check_file(path: Path, *, check_paths: bool = True) -> tuple[list[dict[str, Any]], list[str]]:
    """Return ``(capabilities, errors)`` for one capability.yaml."""

    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as error:
        return [], [f"{path}: not valid YAML ({error})"]
    if not isinstance(data, dict) or data.get("spec_version") != "0.1":
        return [], [f"{path}: spec_version must be '0.1'"]
    caps = data.get("capabilities")
    if not isinstance(caps, list) or not caps:
        return [], [f"{path}: 'capabilities' must be a non-empty list"]
    errors: list[str] = []
    for cap in caps:
        if not isinstance(cap, dict):
            errors.append(f"{path}: a capability is not a mapping")
            continue
        errors += check_capability(cap, str(path), path.parent, check_paths=check_paths)
    return [c for c in caps if isinstance(c, dict)], errors
