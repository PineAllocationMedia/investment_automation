#!/usr/bin/env python3
"""Partition unittest discovery around the exact heavyweight PIT module."""
from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path
import sys
import unittest
from typing import Iterable, Iterator


HEAVY_MODULE = "tests.test_pit_adapter_equivalence"


class PartitionError(RuntimeError):
    pass


def iter_tests(suite: unittest.TestSuite) -> Iterator[unittest.TestCase]:
    for item in suite:
        if isinstance(item, unittest.TestSuite):
            yield from iter_tests(item)
        else:
            yield item


def _module_name(test: unittest.TestCase) -> str:
    return test.__class__.__module__


def is_heavy_test(test: unittest.TestCase) -> bool:
    return _module_name(test) == HEAVY_MODULE


def partition_tests(
    tests: Iterable[unittest.TestCase],
) -> tuple[list[unittest.TestCase], list[unittest.TestCase]]:
    full = list(tests)
    standard = [test for test in full if not is_heavy_test(test)]
    heavy = [test for test in full if is_heavy_test(test)]
    standard_ids = [test.id() for test in standard]
    heavy_ids = [test.id() for test in heavy]
    full_ids = [test.id() for test in full]
    overlap = set(standard_ids) & set(heavy_ids)
    if overlap:
        raise PartitionError(f"Standard/heavy overlap: {sorted(overlap)}")
    if Counter(standard_ids + heavy_ids) != Counter(full_ids):
        raise PartitionError("Standard/heavy union does not equal full discovery")
    if not heavy:
        raise PartitionError(f"Expected heavyweight module is empty: {HEAVY_MODULE}")
    return standard, heavy


def discover_partition(
    repository_root: Path | None = None,
) -> tuple[list[unittest.TestCase], list[unittest.TestCase]]:
    root = (repository_root or Path(__file__).resolve().parents[1]).resolve()
    suite = unittest.defaultTestLoader.discover(
        str(root / "tests"), pattern="test*.py", top_level_dir=str(root)
    )
    return partition_tests(iter_tests(suite))


def print_counts(standard: list[unittest.TestCase], heavy: list[unittest.TestCase]) -> None:
    print(f"CI_TEST_COUNT_STANDARD={len(standard)}", flush=True)
    print(f"CI_TEST_COUNT_HEAVY={len(heavy)}", flush=True)
    print(f"CI_TEST_COUNT_TOTAL={len(standard) + len(heavy)}", flush=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tier", choices=("STANDARD", "FULL_PIT"))
    parser.add_argument("--list-only", action="store_true")
    args = parser.parse_args()
    if not args.list_only and args.tier is None:
        parser.error("--tier is required unless --list-only is used")
    try:
        standard, heavy = discover_partition()
    except (ImportError, OSError, PartitionError) as exc:
        print(f"CI_TEST_PARTITION_ERROR={exc}", file=sys.stderr, flush=True)
        return 2
    print_counts(standard, heavy)
    if args.list_only:
        return 0
    selected = standard if args.tier == "STANDARD" else standard + heavy
    print(f"CI_TEST_EXECUTION_TIER={args.tier}", flush=True)
    result = unittest.TextTestRunner(verbosity=1).run(unittest.TestSuite(selected))
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
