"""Capability registry built from open, configurable sources.

A source is a directory (scanned recursively for ``capability.yaml``) or a
single capability file. Sources are listed by the operator:

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

import yaml

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
    if source.is_file():
        return [source]
    if not source.is_dir():
        raise RegistryError(f"Capability source '{source}' does not exist.")
    return sorted(
        path
        for path in source.rglob("capability.yaml")
        if not SKIP_DIRS & set(path.relative_to(source).parts)
    )


def load_registry(sources: Iterable[Path | str] | None = None) -> Registry:
    registry = Registry()
    for source in [Path(s) for s in sources] if sources else default_sources():
        for path in _files(source):
            try:
                data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            except yaml.YAMLError as error:
                raise RegistryError(f"{path}: not valid YAML ({error})") from error
            for capability in data.get("capabilities") or []:
                cid = capability.get("id")
                if not cid:
                    raise RegistryError(f"{path}: a capability has no id.")
                if cid in registry:
                    raise RegistryError(
                        f"Capability '{cid}' is defined twice: {registry.origin[cid]} and {path}."
                    )
                registry[cid] = capability
                registry.origin[cid] = path
    return registry
