"""Workflow factory core.

Reads capability descriptions from any number of sources, validates freely
written workflows against them, and exports a workflow as a capability.

Nothing here knows about a web framework, a database, an agent, or the
Marketing Assets Pool. Capabilities can come from any directory.
"""

from .registry import Registry, RegistryError, default_sources, load_registry
from .workflow import Analysis, WorkflowError, analyze, build_files, load_workflow

__all__ = [
    "Analysis",
    "Registry",
    "RegistryError",
    "WorkflowError",
    "analyze",
    "build_files",
    "default_sources",
    "load_registry",
    "load_workflow",
]
