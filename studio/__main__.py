"""Command line for the workflow factory.

    python -m studio capabilities [--sources DIR ...]
    python -m studio validate workflow.yaml [--sources DIR ...] [--allow-unknown]
    python -m studio export workflow.yaml --out DIR [--sources DIR ...] [--allow-unknown]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .registry import RegistryError, default_sources, load_registry
from .workflow import WorkflowError, analyze, build_files, load_workflow


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m studio", description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)

    def common(p: argparse.ArgumentParser) -> None:
        p.add_argument("--sources", nargs="+", type=Path, help="Directories or capability.yaml files. Default: $STUDIO_CAPABILITY_SOURCES, else this repository.")
        p.add_argument("--allow-unknown", action="store_true", help="Allow steps whose capability is not in the registry yet.")

    common(sub.add_parser("capabilities", help="List the capabilities found in the sources."))
    p_validate = sub.add_parser("validate", help="Check a workflow.")
    p_validate.add_argument("workflow", type=Path)
    common(p_validate)
    p_export = sub.add_parser("export", help="Write workflow.yaml and capability.yaml for a workflow.")
    p_export.add_argument("workflow", type=Path)
    p_export.add_argument("--out", type=Path, required=True)
    common(p_export)
    args = parser.parse_args(argv)

    try:
        registry = load_registry(args.sources)
    except RegistryError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1

    if args.command == "capabilities":
        for cid, cap in sorted(registry.items()):
            print(f"{cid:42} {cap.get('status', ''):13} {registry.origin[cid]}")
        print(f"{len(registry)} capabilities from {len(args.sources or default_sources())} source(s)")
        return 0

    try:
        doc = load_workflow(args.workflow)
    except WorkflowError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    if args.command == "validate":
        analysis = analyze(doc, registry, allow_unknown=args.allow_unknown)
        for line in analysis.errors:
            print(f"ERROR   {line}")
        for line in analysis.warnings:
            print(f"warning {line}")
        if not analysis.errors:
            print("valid. order: " + " -> ".join(analysis.order))
        return 1 if analysis.errors else 0

    try:
        files, warnings = build_files(doc, registry, allow_unknown=args.allow_unknown)
    except WorkflowError as error:
        for line in error.errors:
            print(f"ERROR   {line}", file=sys.stderr)
        return 1
    args.out.mkdir(parents=True, exist_ok=True)
    for name, text in files.items():
        (args.out / name).write_text(text, encoding="utf-8")
        print(args.out / name)
    for line in warnings:
        print(f"warning {line}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
