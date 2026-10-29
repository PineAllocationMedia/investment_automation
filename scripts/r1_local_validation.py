"""Read-only, on-demand R1 regression runner for an authorized PAM checkout.

Usage: python -B -m scripts.r1_local_validation

This is *focused synthetic regression*, NOT live-source authentication,
three-Project acceptance, policy approval, readiness, deployment or trading.
No network requests, package installation, GitHub writes or scheduling.
"""
from __future__ import annotations

from collections.abc import Callable, Iterator
from pathlib import Path
import re
import sys
import unittest
from typing import TextIO


ROOT = Path(__file__).resolve().parents[1]
REQUIRED = frozenset({
    "test_ai_native_r1_integrated_smoke.py",
    "test_ai_native_r1_manual_cli.py",
    "test_ai_native_portfolio_exposure.py",
    "test_ai_native_r1_exposure_reporting.py",
    "test_ai_native_r1_portfolio_exposure_queue.py",
    "test_ai_native_r1_concentration_sensitivity.py",
    "test_ai_native_r1_cash_sensitivity.py",
})


def _environment(root: Path) -> str | None:
    """Require the *exact* repo-pinned Python and matching dependency lock."""
    try:
        pinned = (root / ".python-version").read_text(encoding="utf-8").strip()
    except OSError:
        return "PYTHON_PIN_UNAVAILABLE"
    if not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", pinned):
        return "PYTHON_PIN_INVALID"
    observed = ".".join(str(x) for x in sys.version_info[:3])
    if observed != pinned:
        return "PYTHON_VERSION_DRIFT"
    try:
        from src.dependency_reproducibility import dependency_environment
        status = dependency_environment(root / "requirements.lock")["dependency_status"]
    except (ImportError, OSError, KeyError, ValueError):
        return "DEPENDENCY_CHECK_UNAVAILABLE"
    if status != "MATCH":
        return "DEPENDENCY_LOCK_DRIFT"
    return None


def _discover(root: Path) -> unittest.TestSuite:
    return unittest.TestLoader().discover(
        start_dir=str(root / "tests"), pattern="test_ai_native_*.py",
        top_level_dir=str(root),
    )


def _iter_tests(suite: unittest.TestSuite) -> Iterator[unittest.TestCase]:
    for item in suite:
        if isinstance(item, unittest.TestSuite):
            yield from _iter_tests(item)
        else:
            yield item


def validate(
    root: Path = ROOT, *, out: TextIO | None = None,
    checker: Callable[[Path], str | None] = _environment,
    discoverer: Callable[[Path], unittest.TestSuite] = _discover,
    required: frozenset[str] = REQUIRED,
    minimum_modules: int = 40, minimum_cases: int = 100,
) -> int:
    """Fail closed on prerequisites, zero tests, import errors and failed tests.

    Injected callables exist for isolated runner unit tests; the CLI always
    uses the real environment check and unittest discovery.
    """
    stream = out if out is not None else sys.stdout
    root = root.resolve()

    def line(k: str, v: object) -> None:
        stream.write(f"{k}={v}\n")

    line("R1_SCOPE", "SYNTHETIC_REGRESSION_ONLY_NOT_ACCEPTANCE")
    line("R1_AUTHENTIC_SOURCES", "NOT_CHECKED")
    line("R1_PROJECTS", "NOT_INVOKED")
    line("R1_READINESS", "NOT_EVALUATED")
    reason = checker(root)
    if reason is not None:
        line("R1_VALIDATION", "BLOCKED_ENVIRONMENT")
        line("R1_REASON", reason)
        return 2
    directory = root / "tests"
    actual = {p.name for p in directory.glob("test_ai_native_*.py")}
    missing = required - actual
    if missing or len(actual) < minimum_modules:
        line("R1_VALIDATION", "BLOCKED_TEST_INVENTORY")
        line("R1_REASON", "REQUIRED_R1_TESTS_MISSING" if missing else "R1_TEST_INVENTORY_TOO_SMALL")
        line("R1_MISSING_MODULES", ",".join(sorted(missing)))
        return 2
    try:
        suite = discoverer(root)
        all_tests = list(_iter_tests(suite))
    except (ImportError, OSError, ValueError, TypeError) as exc:
        line("R1_VALIDATION", "BLOCKED_DISCOVERY")
        line("R1_REASON", type(exc).__name__)
        return 2
    tests: list[unittest.TestCase] = []
    seen: set[str] = set()
    for test in all_tests:
        name = test.id()
        if name not in seen:
            tests.append(test)
            seen.add(name)
    line("R1_TEST_MODULE_FILES", len(actual))
    line("R1_TEST_CASES_DISCOVERED", len(all_tests))
    line("R1_TEST_CASES_UNIQUE", len(tests))
    if len(tests) < minimum_cases:
        line("R1_VALIDATION", "BLOCKED_TEST_INVENTORY")
        line("R1_REASON", "R1_TEST_DISCOVERY_TOO_SMALL")
        return 2
    sys.dont_write_bytecode = True
    result = unittest.TextTestRunner(stream=stream, verbosity=1).run(
        unittest.TestSuite(tests))
    line("R1_TESTS_RUN", result.testsRun)
    line("R1_TEST_ERRORS", len(result.errors))
    line("R1_TEST_FAILURES", len(result.failures))
    line("R1_TEST_SKIPPED", len(result.skipped))
    successful = result.wasSuccessful() and result.testsRun > len(result.skipped)
    line("R1_VALIDATION", "PASS_FOCUSED_TESTS_ONLY" if successful
         else "FAIL_FOCUSED_TESTS")
    return 0 if successful else 1


def main() -> int:
    return validate()


if __name__ == "__main__":
    raise SystemExit(main())
