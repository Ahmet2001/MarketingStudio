#!/usr/bin/env python3
"""Validate every capability.yaml in the repository against spec v0.1.

Usage: python scripts/validate_capabilities.py
Exit code 0 when all files are valid, 1 otherwise. Requires PyYAML.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
SKIP_DIRS = {"node_modules", ".venv", ".git", "__pycache__"}
ID_RE = re.compile(r"^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)+$")
SCALAR_TYPES = {"text", "integer", "number", "boolean", "enum", "url", "list", "object"}
STATUSES = {"working", "experimental", "planned"}
EXEC_TYPES = {"cli", "http", "python"}
REQUIRED = ["id", "version", "title", "description", "status", "inputs", "outputs",
            "requires", "permissions", "cost", "execution", "failure_modes"]


def valid_type(value: object) -> bool:
    return isinstance(value, str) and (value in SCALAR_TYPES or re.fullmatch(r"file:[a-z0-9]+", value) is not None)


def check_capability(cap: dict, where: str, errors: list[str]) -> None:
    for key in REQUIRED:
        if key not in cap:
            errors.append(f"{where}: missing '{key}'")
    cid = cap.get("id", "?")
    where = f"{where} [{cid}]"
    if "id" in cap and not ID_RE.match(str(cap["id"])):
        errors.append(f"{where}: id must be lowercase dot separated")
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
    perms = cap.get("permissions") or {}
    for key in ("network", "writes_external_state", "requires_approval"):
        if not isinstance(perms.get(key), bool):
            errors.append(f"{where}: permissions.{key} must be true or false")
    if perms.get("writes_external_state") and not perms.get("requires_approval"):
        errors.append(f"{where}: writes_external_state requires requires_approval: true")
    if "estimate_usd" not in (cap.get("cost") or {}):
        errors.append(f"{where}: cost.estimate_usd is required (null when unknown)")
    execution = cap.get("execution") or {}
    if execution.get("type") not in EXEC_TYPES:
        errors.append(f"{where}: execution.type must be one of {sorted(EXEC_TYPES)}")
    if execution.get("type") == "cli":
        cwd = ROOT / str(execution.get("cwd", ""))
        if not cwd.is_dir():
            errors.append(f"{where}: execution.cwd '{execution.get('cwd')}' does not exist")
        inputs = cap.get("inputs") or {}
        mapped = list(execution.get("positional") or []) + list((execution.get("flags") or {}).keys())
        for name in mapped:
            if name not in inputs:
                errors.append(f"{where}: execution maps unknown input '{name}'")
        for name in (cap.get("outputs") or {}):
            if name not in (execution.get("outputs") or {}):
                errors.append(f"{where}: output '{name}' has no execution.outputs path")
    if execution.get("type") == "python":
        module = str(execution.get("module", ""))
        func = str(execution.get("function", ""))
        source = ROOT / (module.replace(".", "/") + ".py")
        if not source.is_file():
            errors.append(f"{where}: module file {source.relative_to(ROOT)} not found")
        elif f"def {func}(" not in source.read_text(encoding="utf-8"):
            errors.append(f"{where}: function '{func}' not found in {source.relative_to(ROOT)}")


def main() -> int:
    files = [p for p in ROOT.rglob("capability.yaml") if not SKIP_DIRS & set(p.parts)]
    errors: list[str] = []
    seen: dict[str, Path] = {}
    total = 0
    for path in sorted(files):
        rel = path.relative_to(ROOT)
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict) or data.get("spec_version") != "0.1":
            errors.append(f"{rel}: spec_version must be '0.1'")
            continue
        for cap in data.get("capabilities") or []:
            total += 1
            cid = cap.get("id")
            if cid in seen:
                errors.append(f"{rel}: duplicate id '{cid}' (also in {seen[cid]})")
            seen[cid] = rel
            check_capability(cap, str(rel), errors)
    for line in errors:
        print("ERROR", line)
    print(f"{total} capabilities in {len(files)} files, {len(errors)} errors")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
