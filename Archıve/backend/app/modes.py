from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ModeDefinition:
    id: str
    name: str
    available: bool
    engine: str


MODES: dict[str, ModeDefinition] = {
    "ai-photos": ModeDefinition(
        id="ai-photos",
        name="Storyteller with AI photos",
        available=True,
        engine="storyteller",
    ),
    "reddit": ModeDefinition(
        id="reddit",
        name="Storyteller with Reddit video",
        available=True,
        engine="storyteller",
    ),
    "real-images": ModeDefinition(
        id="real-images",
        name="Storyteller with real images",
        available=True,
        engine="explainer",
    ),
    "documentary": ModeDefinition(
        id="documentary",
        name="Historical documentary",
        available=True,
        engine="explainer",
    ),
    "stock-explainer": ModeDefinition(
        id="stock-explainer",
        name="Stock footage explainer",
        available=False,
        engine="planned",
    ),
    "avatar": ModeDefinition(
        id="avatar",
        name="AI avatar presenter",
        available=False,
        engine="planned",
    ),
}
