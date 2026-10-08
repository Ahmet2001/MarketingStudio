"""Adapters turn a bundle into the files one kind of consumer reads.

An adapter is a pure function ``(bundle) -> (files, notes)``: it reads nothing
but the bundle, writes nothing, and connects to nothing. ``files`` maps a path
to its text, ``notes`` lists what the target cannot do or what the person
installing it must know. Installing the result is a separate, deliberate step.
"""

from __future__ import annotations

from typing import Callable

from ..bundle import Bundle
from .agent_pack import agent_bundle, agent_pack
from .job_handler import job_handler
from .mcp_server import mcp_server
from .tool_schema import tool_schema
from .worker import worker

Adapter = Callable[[Bundle], tuple[dict[str, str], list[str]]]

ADAPTERS: dict[str, Adapter] = {
    "tool-schema": tool_schema,
    "agent-pack": agent_pack,
    "agent-bundle": agent_bundle,
    "job-handler": job_handler,
    "worker": worker,
    "mcp": mcp_server,
}

__all__ = ["ADAPTERS", "Adapter", "agent_bundle", "agent_pack", "job_handler", "mcp_server", "tool_schema", "worker"]
