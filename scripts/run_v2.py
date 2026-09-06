#!/usr/bin/env python3
"""Restricted, in-process V2 launcher. It never launches production scripts."""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import sys


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime-root", type=Path)
    parser.add_argument("--forbid-root", action="append", type=Path, default=[])
    parser.add_argument("command", nargs=argparse.REMAINDER, help="main.py command and arguments")
    args = parser.parse_args(argv)
    if not args.command:
        parser.error("a command is required (use runtime-info to inspect paths without writes)")
    os.environ["INVESTMENT_AUTOMATION_RUNTIME_PROFILE"] = "v2-restricted"
    if args.runtime_root is not None:
        os.environ["INVESTMENT_AUTOMATION_RUNTIME_ROOT"] = str(args.runtime_root)
    if args.forbid_root:
        existing = os.environ.get("INVESTMENT_AUTOMATION_FORBIDDEN_ROOTS", "")
        os.environ["INVESTMENT_AUTOMATION_FORBIDDEN_ROOTS"] = os.pathsep.join(
            [value for value in [existing, *(str(p) for p in args.forbid_root)] if value]
        )
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from src.runtime_context import RuntimeIsolationError
    from main import main as application_main
    try:
        return application_main(args.command)
    except RuntimeIsolationError as exc:
        parser.exit(2, f"{exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())
