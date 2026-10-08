"""Tool definitions for LLM function calling (Anthropic and OpenAI shapes)."""

from __future__ import annotations

import json
from typing import Any

from ..bundle import Bundle
from ._common import FILE_FORMS, approve_text, gated, is_file


def _property(spec: dict[str, Any]) -> dict[str, Any]:
    kind = spec["type"]
    prop: dict[str, Any]
    if is_file(spec):
        prop = {
            "oneOf": [
                {"type": "string", "description": "An https address, asset:<id>, or an allowed local path."},
                {
                    "type": "object",
                    "properties": {"filename": {"type": "string"}, "content_base64": {"type": "string"}},
                    "required": ["filename", "content_base64"],
                },
            ],
            "description": f"A file, given as {FILE_FORMS}.",
        }
    elif kind == "enum":
        prop = {"type": "string", "enum": list(spec.get("values", []))}
    elif kind in {"text", "url"}:
        prop = {"type": "string"}
    elif kind in {"integer", "number", "boolean"}:
        prop = {"type": kind}
    elif kind == "list":
        prop = {"type": "array"}
    elif kind == "object":
        prop = {"type": "object"}
    else:
        prop = {}
    if spec.get("description"):
        prop.setdefault("description", spec["description"])
    if "default" in spec:
        prop["default"] = spec["default"]
    return prop


def tool_schema(bundle: Bundle) -> tuple[dict[str, str], list[str]]:
    manifest = bundle.manifest
    properties = {name: _property(spec) for name, spec in manifest["inputs"].items()}
    required = [n for n, s in manifest["inputs"].items() if s.get("required") and "default" not in s]
    description = manifest["description"]
    if gated(bundle):
        properties["approve"] = {
            "type": "boolean",
            "default": False,
            "description": approve_text(bundle),
        }
    schema = {"type": "object", "properties": properties, "required": required}
    anthropic = {"name": manifest["id"], "description": description, "input_schema": schema}
    openai = {"type": "function", "function": {"name": manifest["id"], "description": description, "parameters": schema}}
    files = {
        "anthropic_tool.json": json.dumps(anthropic, indent=2, ensure_ascii=False) + "\n",
        "openai_tool.json": json.dumps(openai, indent=2, ensure_ascii=False) + "\n",
    }
    notes = [
        "This is a definition only: something on the other side must run the workflow when the tool is called "
        "(the bundle's portable.py can).",
    ]
    if gated(bundle):
        notes.append("Approval is a parameter the model is told to set only after asking the user; the caller must enforce it.")
    return files, notes
