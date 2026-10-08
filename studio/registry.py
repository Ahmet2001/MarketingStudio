"""Capability registry built from open, configurable sources.

A source is a directory (scanned recursively for ``capability.yaml`` and for
single-file engines, see ``engine_file``) or a single such file. Sources are listed by the operator:

* ``--sources`` on the command line, or
* the ``STUDIO_CAPABILITY_SOURCES`` environment variable (``os.pathsep`` separated), or
* by default, the repository this package lives in.

Any number of sources can be combined. No source is special: a shared pool, a
private folder and a single file all work the same way.

Sources are trusted by whoever configures them. A capability file describes
how something is executed, so only add sources you would run code from.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Iterable

from .check import check_capability, check_file
from .engine_file import EngineFileError, extract, mentions_capability

SKIP_DIRS = {"node_modules", ".venv", ".git", "__pycache__"}
ENV_SOURCES = "STUDIO_CAPABILITY_SOURCES"
REPO_ROOT = Path(__file__).resolve().parents[1]


class RegistryError(ValueError):
    """A source could not be read, or two sources define the same id."""


class Registry(dict):
    """``{capability id: capability}`` plus where each one came from."""

    def __init__(self) -> None:
        super().__init__()
        self.origin: dict[str, Path] = {}


def default_sources() -> list[Path]:
    raw = os.environ.get(ENV_SOURCES, "")
    paths = [Path(p).expanduser() for p in raw.split(os.pathsep) if p.strip()]
    return paths or [REPO_ROOT]


def _files(source: Path) -> list[Path]:
    """capability.yaml files and single-file engines (.py with a CAPABILITY)."""

    if source.is_file():
        return [source]
    if not source.is_dir():
        raise RegistryError(f"Capability source '{source}' does not exist.")
    found = [
        path
        for path in source.rglob("capability.yaml")
        if not SKIP_DIRS & set(path.relative_to(source).parts)
    ]
    for path in source.rglob("*.py"):
        if SKIP_DIRS & set(path.relative_to(source).parts):
            continue
        try:
            if mentions_capability(path.read_text(encoding="utf-8")):
                found.append(path)
        except (OSError, UnicodeDecodeError):
            continue
    return sorted(found)


def _read(path: Path, check_paths: bool) -> tuple[list[dict], list[str]]:
    if path.suffix == ".py":
        try:
            caps = extract(path)
        except EngineFileError as error:
            return [], [str(error)]
        errors: list[str] = []
        for cap in caps:
            errors += check_capability(cap, str(path), path.parent, check_paths=check_paths)
        return caps, errors
    return check_file(path, check_paths=check_paths)


def load_registry(
    sources: Iterable[Path | str] | None = None, *, check_paths: bool = False
) -> Registry:
    """Load every capability from the sources.

    Malformed files are rejected with every problem listed. ``check_paths``
    additionally requires the files an execution points to (cwd, module,
    workflow definition) to exist.
    """

    registry = Registry()
    problems: list[str] = []
    for source in [Path(s) for s in sources] if sources else default_sources():
        for path in _files(source):
            caps, errors = _read(path, check_paths)
            problems += errors
            for capability in caps:
                cid = capability.get("id")
                if not cid:
                    continue
                if cid in registry:
                    problems.append(
                        f"Capability '{cid}' is defined twice: {registry.origin[cid]} and {path}."
                    )
                    continue
                registry[cid] = capability
                registry.origin[cid] = path
    if problems:
        raise RegistryError("\n".join(problems))
    return registry
