"""Engines written as one Python file.

A file counts as an engine when it has a module-level ``CAPABILITY`` (one
capability) or ``CAPABILITIES`` (a list), written as a plain literal:

    from pathlib import Path

    CAPABILITY = {
        "id": "my.word_count",
        "description": "Counts the words in a text file.",
        "writes_external_state": False,
    }

    def word_count(source: Path) -> int:
        return len(source.read_text().split())

Everything else is derived from the function: inputs from its parameters
(annotation gives the type, a default makes it optional), the output from the
return annotation. The file is read with ``ast`` and never executed here, so
reading a source cannot run anyone's code.

Anything you leave out is assumed to be the risky answer: the capability may
use the network and may write to the outside world (so it needs approval)
until the file says otherwise.
"""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Any

TYPE_NAMES = {
    "str": "text", "int": "integer", "float": "number", "bool": "boolean",
    "list": "list", "dict": "object", "Path": "file:any", "pathlib.Path": "file:any",
    "Any": "any", "object": "any",
}
OPTIONAL_KEYS = {
    "title", "version", "status", "inputs", "outputs", "requires", "cost",
    "failure_modes", "network", "writes_external_state", "env", "binaries",
    "packages", "hardware", "estimate_usd", "function",
}
KNOWN_KEYS = OPTIONAL_KEYS | {"id", "description"}


class EngineFileError(ValueError):
    pass


def mentions_capability(source: str) -> bool:
    return "CAPABILITY" in source or "CAPABILITIES" in source


def _literal(node: ast.AST, where: str) -> Any:
    try:
        return ast.literal_eval(node)
    except (ValueError, SyntaxError) as error:
        raise EngineFileError(f"{where}: CAPABILITY must be a plain literal (no calls or names).") from error


def _type_of(annotation: ast.AST | None) -> tuple[str, list[Any] | None]:
    """Capability type for an annotation, and enum values when it is a Literal."""

    if annotation is None:
        return "any", None
    if isinstance(annotation, ast.Constant) and isinstance(annotation.value, str):
        try:
            annotation = ast.parse(annotation.value, mode="eval").body
        except SyntaxError:
            return "any", None
    if isinstance(annotation, ast.BinOp) and isinstance(annotation.op, ast.BitOr):
        for side in (annotation.left, annotation.right):
            if not (isinstance(side, ast.Constant) and side.value is None):
                return _type_of(side)
    if isinstance(annotation, ast.Subscript):
        head = ast.unparse(annotation.value)
        if head in {"Optional", "typing.Optional"}:
            return _type_of(annotation.slice)
        if head in {"Literal", "typing.Literal"}:
            values = ast.literal_eval(annotation.slice)
            return "enum", list(values if isinstance(values, tuple) else (values,))
        return TYPE_NAMES.get(head, "any"), None
    return TYPE_NAMES.get(ast.unparse(annotation), "any"), None


def _inputs(function: ast.FunctionDef, where: str) -> dict[str, dict[str, Any]]:
    args = function.args
    names = [a for a in args.posonlyargs + args.args + args.kwonlyargs if a.arg not in {"self", "cls"}]
    positional = args.posonlyargs + args.args
    defaults: dict[str, ast.AST] = {}
    for arg, default in zip(positional[len(positional) - len(args.defaults):], args.defaults):
        defaults[arg.arg] = default
    for arg, default in zip(args.kwonlyargs, args.kw_defaults):
        if default is not None:
            defaults[arg.arg] = default
    inputs: dict[str, dict[str, Any]] = {}
    for arg in names:
        kind, values = _type_of(arg.annotation)
        spec: dict[str, Any] = {"type": kind}
        if values is not None:
            spec["values"] = values
        if arg.arg in defaults:
            default = defaults[arg.arg]
            if not (isinstance(default, ast.Constant) and default.value is None):
                spec["default"] = _literal(default, f"{where}: default of '{arg.arg}'")
        else:
            spec["required"] = True
        inputs[arg.arg] = spec
    return inputs


def extract(path: Path) -> list[dict[str, Any]]:
    """Return the capabilities described by an engine file (empty if it has none)."""

    source = path.read_text(encoding="utf-8")
    if not mentions_capability(source):
        return []
    try:
        tree = ast.parse(source)
    except SyntaxError as error:
        raise EngineFileError(f"{path}: not valid Python ({error.msg} on line {error.lineno}).") from error

    declared: list[Any] | None = None
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            if node.targets[0].id == "CAPABILITY":
                declared = [_literal(node.value, str(path))]
            elif node.targets[0].id == "CAPABILITIES":
                declared = _literal(node.value, str(path))
    if declared is None:
        return []
    functions = {n.name: n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
    result: list[dict[str, Any]] = []
    for item in declared:
        where = f"{path}"
        if not isinstance(item, dict) or "id" not in item or "description" not in item:
            raise EngineFileError(f"{where}: each CAPABILITY needs at least 'id' and 'description'.")
        unknown = set(item) - KNOWN_KEYS
        if unknown:
            raise EngineFileError(f"{where} [{item['id']}]: unknown key(s) {sorted(unknown)}.")
        name = item.get("function")
        if name is None:
            suffix = str(item["id"]).rsplit(".", 1)[-1]
            plain = [n for n, f in functions.items() if isinstance(f, ast.FunctionDef) and not n.startswith("_")]
            name = suffix if suffix in functions else plain[0] if len(plain) == 1 and len(declared) == 1 else None
        function = functions.get(name) if name else None
        if not isinstance(function, ast.FunctionDef):
            raise EngineFileError(
                f"{where} [{item['id']}]: could not find its function. Add \"function\": \"<name>\" "
                "naming a plain (non-async) function in this file."
            )
        inputs = item.get("inputs") or _inputs(function, f"{where} [{item['id']}]")
        outputs = item.get("outputs")
        if outputs is None:
            kind, values = _type_of(function.returns)
            outputs = {"result": {"type": kind, **({"values": values} if values else {})}}
        result.append(
            {
                "id": item["id"],
                "version": item.get("version", "0.1.0"),
                "title": item.get("title", item["id"]),
                "description": item["description"],
                "status": item.get("status", "experimental"),
                "inputs": inputs,
                "outputs": outputs,
                "requires": item.get("requires")
                or {
                    "env": list(item.get("env", [])),
                    "binaries": list(item.get("binaries", [])),
                    "hardware": list(item.get("hardware", [])),
                    **({"packages": list(item["packages"])} if item.get("packages") else {}),
                },
                "permissions": {
                    "network": bool(item.get("network", True)),
                    "writes_external_state": bool(item.get("writes_external_state", True)),
                    "requires_approval": bool(item.get("writes_external_state", True)),
                },
                "cost": item.get("cost") or {"estimate_usd": item.get("estimate_usd"), "notes": "Declared in the engine file."},
                "execution": {"type": "python", "path": ".", "module": path.stem, "function": name},
                "failure_modes": list(item.get("failure_modes", [])),
            }
        )
    return result
