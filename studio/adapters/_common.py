"""Shared helpers for adapters."""

from __future__ import annotations

from typing import Any

from ..bundle import Bundle

FILE_FORMS = (
    "an https address, an object {\"filename\": ..., \"content_base64\": ...}, "
    "an asset id written as asset:<id>, or a local path in a folder the host allows"
)


def is_file(spec: dict[str, Any]) -> bool:
    return str(spec.get("type", "")).startswith("file:")


def ordered_inputs(bundle: Bundle) -> list[tuple[str, dict[str, Any]]]:
    """Required inputs first (a Python signature needs that), then optional ones."""

    items = list(bundle.manifest["inputs"].items())
    required = [i for i in items if i[1].get("required") and "default" not in i[1]]
    return required + [i for i in items if i not in required]


def gated(bundle: Bundle) -> list[dict[str, str]]:
    return bundle.manifest["gated_steps"]


APPROVE_TEXT = (
    "This workflow changes something outside the machine ({steps}). Ask the user to confirm "
    "first; call again with approve=true only after they said yes."
)


def approve_text(bundle: Bundle) -> str:
    return APPROVE_TEXT.format(steps=", ".join(f"{g['step']}: {g['capability']}" for g in gated(bundle)))
