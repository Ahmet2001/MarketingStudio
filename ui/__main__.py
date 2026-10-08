"""python -m ui [--port 8765] [--sources DIR ...] [--root DIR]"""

from __future__ import annotations

import argparse
from pathlib import Path

from .server import ROOT, serve


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m ui", description="Local workflow editor for MarketingStudio.")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--sources", nargs="+", type=Path, default=None, help="Capability folders or files (as for `studio --sources`).")
    parser.add_argument("--root", type=Path, default=ROOT, help="Folder whose workflow files may be opened and saved.")
    args = parser.parse_args(argv)
    serve(args.port, args.sources, args.root.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
