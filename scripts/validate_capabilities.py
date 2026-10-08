#!/usr/bin/env python3
"""Validate the capability files in this repository (or in other sources).

Usage: python scripts/validate_capabilities.py [DIR ...]
Same check as `python -m studio check`. Exit code 0 when everything is valid.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from studio.check import check_capability as _check  # noqa: E402
from studio.__main__ import main as studio_main  # noqa: E402


def check_capability(cap: dict, where: str, errors: list[str]) -> None:
    """Kept for callers that collect errors into a list."""
    errors.extend(_check(cap, where, ROOT))


if __name__ == "__main__":
    extra = [str(p) for p in sys.argv[1:]]
    raise SystemExit(studio_main(["check", *(["--sources", *extra] if extra else [])]))
