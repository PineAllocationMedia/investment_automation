#!/usr/bin/env python3
"""Classify a complete changed-file list into PAM's reviewed CI tiers."""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from enum import IntEnum
from pathlib import PurePosixPath
import sys
from typing import Iterable


class ValidationTier(IntEnum):
    DOCS_ONLY = 0
    STANDARD = 1
    FULL_PIT = 2


FULL_PIT_EXACT_PATHS = frozenset(
    {
        ".github/workflows/ci.yml",
        ".python-version",
        "main.py",
        "requirements.lock",
        "requirements.txt",
        "scripts/ci_unittest_runner.py",
        "scripts/ci_validation_plan.py",
        "tests/__init__.py",
        "tests/test_ci_unittest_runner.py",
        "tests/test_ci_validation_plan.py",
    }
)
FULL_PIT_PREFIXES = ("src/", "pit_comparison/")
FULL_PIT_TEST_PREFIXES = ("tests/pit_", "tests/test_pit_")


@dataclass(frozen=True)
class ValidationPlan:
    tier: ValidationTier
    changed_files: tuple[str, ...]

    @property
    def heavy_pit_required(self) -> bool:
        return self.tier is ValidationTier.FULL_PIT


def _is_valid_repo_path(path: str) -> bool:
    if not path or "\\" in path or any(ord(character) < 32 for character in path):
        return False
    parsed = PurePosixPath(path)
    return not parsed.is_absolute() and parsed.parts not in {(), (".",)} and ".." not in parsed.parts


def classify_path(path: str) -> ValidationTier:
    """Return the cheapest reviewed tier for one repository-relative path."""
    if not _is_valid_repo_path(path):
        return ValidationTier.FULL_PIT
    if path in FULL_PIT_EXACT_PATHS:
        return ValidationTier.FULL_PIT
    if path.startswith(FULL_PIT_PREFIXES) or path.startswith(FULL_PIT_TEST_PREFIXES):
        return ValidationTier.FULL_PIT
    if path.endswith(".md"):
        return ValidationTier.DOCS_ONLY
    if path.startswith("economic_facts/"):
        return ValidationTier.STANDARD
    if path.startswith("tests/") and path.endswith(".py"):
        name = PurePosixPath(path).name
        if name.startswith("test_") or name.endswith("_fixtures.py"):
            return ValidationTier.STANDARD
    return ValidationTier.FULL_PIT


def plan_validation(paths: Iterable[str]) -> ValidationPlan:
    changed_files = tuple(sorted(set(paths)))
    if not changed_files:
        return ValidationPlan(ValidationTier.FULL_PIT, ())
    return ValidationPlan(max(map(classify_path, changed_files)), changed_files)


def format_plan(plan: ValidationPlan) -> str:
    lines = [
        f"CI_VALIDATION_TIER={plan.tier.name}",
        f"CI_CHANGED_FILE_COUNT={len(plan.changed_files)}",
    ]
    lines.extend(f"CI_CHANGED_FILE={path}" for path in plan.changed_files)
    lines.append(f"CI_HEAVY_PIT_REQUIRED={'true' if plan.heavy_pit_required else 'false'}")
    return "\n".join(lines)


def _read_paths(*, nul_input: bool) -> list[str]:
    raw = sys.stdin.buffer.read()
    if nul_input:
        if raw and not raw.endswith(b"\0"):
            raise ValueError("NUL-delimited input must end with NUL")
        chunks = raw.split(b"\0")[:-1] if raw else []
    else:
        chunks = raw.splitlines()
    return [chunk.decode("utf-8", errors="strict") for chunk in chunks]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--nul-input",
        action="store_true",
        help="read a NUL-delimited changed-file list from standard input",
    )
    args = parser.parse_args()
    try:
        plan = plan_validation(_read_paths(nul_input=args.nul_input))
    except (UnicodeDecodeError, ValueError) as exc:
        plan = ValidationPlan(ValidationTier.FULL_PIT, ())
        print(f"CI_VALIDATION_INPUT_ERROR={exc}", file=sys.stderr)
    print(format_plan(plan))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
