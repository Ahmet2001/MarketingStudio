"""Command line for the workflow factory.

    python -m studio capabilities [--sources DIR ...]
    python -m studio validate workflow.yaml [--sources DIR ...] [--allow-unknown]
    python -m studio export workflow.yaml --out DIR [--sources DIR ...] [--allow-unknown]
    python -m studio check [--sources DIR ...]
    python -m studio bundle workflow.yaml --out DIR [--sources DIR ...]
    python -m studio adapt workflow.yaml --target agent-pack|tool-schema --out DIR [--sources DIR ...]
    python -m studio run workflow.yaml [--input name=value ...] [--approve STEP ...] [--workdir DIR]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from datetime import datetime

from .registry import RegistryError, default_sources, load_registry
from .runner import RunError, run_workflow
from .adapters import ADAPTERS
from .bundle import BundleError, build_bundle
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
    p_bundle = sub.add_parser("bundle", help="Write a self-contained folder that runs without studio installed.")
    p_bundle.add_argument("workflow", type=Path)
    p_bundle.add_argument("--out", type=Path, required=True)
    common(p_bundle)
    p_adapt = sub.add_parser("adapt", help="Write the files one kind of consumer reads (writes files only, installs nothing).")
    p_adapt.add_argument("workflow", type=Path)
    p_adapt.add_argument("--target", choices=sorted(ADAPTERS), required=True)
    p_adapt.add_argument("--out", type=Path, required=True)
    common(p_adapt)
    p_check = sub.add_parser("check", help="Check capability files in the sources, including that the files they point to exist.")
    common(p_check)
    p_run = sub.add_parser("run", help="Run a workflow on this machine.")
    p_run.add_argument("workflow", type=Path)
    p_run.add_argument("--input", action="append", default=[], metavar="NAME=VALUE")
    p_run.add_argument("--approve", nargs="+", default=[], metavar="STEP", help="Steps allowed to write to the outside world.")
    p_run.add_argument("--approve-all", action="store_true", help="Approve every gated step without asking.")
    p_run.add_argument("--workdir", type=Path, help="Where step outputs go. Default: ./runs/<time>.")
    common(p_run)
    args = parser.parse_args(argv)

    try:
        registry = load_registry(args.sources, check_paths=args.command == "check")
    except RegistryError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1

    if args.command == "check":
        print(f"{len(registry)} capabilities from {len(args.sources or default_sources())} source(s), no problems.")
        return 0

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
    if args.command in {"bundle", "adapt"}:
        try:
            bundle = build_bundle(doc, registry)
            if args.command == "bundle":
                files, notes = bundle.files(), bundle.warnings
            else:
                files, notes = ADAPTERS[args.target](bundle)
        except WorkflowError as error:
            for line in error.errors:
                print(f"ERROR   {line}", file=sys.stderr)
            return 1
        except (BundleError, ValueError) as error:
            print(f"error: {error}", file=sys.stderr)
            return 1
        for name, text in files.items():
            path = args.out / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
        print(f"wrote {len(files)} files to {args.out}")
        for line in notes:
            print(f"note: {line}")
        return 0

    if args.command == "run":
        analysis = analyze(doc, registry)
        if analysis.errors:
            for line in analysis.errors:
                print(f"ERROR   {line}", file=sys.stderr)
            return 1
        given = {}
        for item in args.input:
            name, sep, value = item.partition("=")
            if not sep:
                print(f"error: --input needs NAME=VALUE, got {item!r}", file=sys.stderr)
                return 1
            given[name] = value
        specs = doc["workflow"].get("inputs") or {}
        from .runner import parse_input
        try:
            typed = {k: parse_input(specs[k], v) if k in specs else v for k, v in given.items()}
        except RunError as error:
            print(f"error: {error}", file=sys.stderr)
            return 1

        def approve(step_id: str, cap: dict) -> bool:
            if args.approve_all or step_id in args.approve:
                return True
            if sys.stdin.isatty():
                answer = input(f"Step '{step_id}' ({cap['id']}) changes something outside this machine. Run it? [y/N] ")
                return answer.strip().lower() in {"y", "yes"}
            return False

        workdir = args.workdir or Path("runs") / datetime.now().strftime("%Y%m%d_%H%M%S")
        try:
            result = run_workflow(doc, registry, typed, workdir, approve=approve, log=print)
        except (RunError, WorkflowError) as error:
            print(f"error: {error}", file=sys.stderr)
            return 2
        for name, value in result.outputs.items():
            print(f"{name}: {value}")
        return 0

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
