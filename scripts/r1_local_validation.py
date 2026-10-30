"""Read-only, on-demand R1 regression runner for an authorized PAM checkout.

Usage: python -B -m scripts.r1_local_validation
       python -B -m scripts.r1_local_validation --candidate-head <PR_SHA> --base-sha <V2_SHA>
       python -B -m scripts.r1_local_validation --quick-stdlib-smoke

The optional QUICK mode uses Python >=3.11, NO pip and a critical subset of
real R1 synthetic tests in the same clean, SHA-checked authorized checkout.
It is UNPINNED and NOT equivalent to the full pinned regression or acceptance.

This is *focused synthetic regression*, NOT live-source authentication,
three-Project acceptance, policy approval, readiness, deployment or trading.
No network requests, package installation, GitHub writes or scheduling.
"""
from __future__ import annotations

import argparse
from collections.abc import Callable, Iterator
from pathlib import Path
import re
import subprocess
import sys
import unittest
from typing import TextIO


ROOT = Path(__file__).resolve().parents[1]
# An explicit subset of existing real R1 contracts, not a replacement suite.
# No optional package setup, browser, network, financial data or CI rerun.
QUICK_MODULES = (
    "tests.test_ai_native_r1_integrated_smoke",
    "tests.test_ai_native_r1_manual_cli",
    "tests.test_ai_native_session_bridge",
    "tests.test_ai_native_strategy_authority",
    "tests.test_ai_native_manual_review_queue",
    "tests.test_ai_native_portfolio_observation",
    "tests.test_ai_native_r1_portfolio_snapshots",
    "tests.test_ai_native_private_portfolio_transfer",
    "tests.test_ai_native_private_integrated_closeout",
    "tests.test_ai_native_integrated_followup_roundtrip",
    "tests.test_ai_native_screenshot_reentry",
    "tests.test_ai_native_candidate_deep_dive_draft",
    "tests.test_ai_native_guided_research_closeout",
    "tests.test_ai_native_guided_portfolio_closeout",
    "tests.test_ai_native_r1_private_displayed_weights",
    "tests.test_ai_native_r1_alternative_supplied_costs",
    "tests.test_ai_native_reporting",
)

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



def _checkout(root: Path, *, candidate_head: str | None = None,
              base_sha: str | None = None) -> tuple[str | None, str | None]:
    """Read-only local checkout integrity; never infer live GitHub freshness.

    The operator must fetch V2 explicitly beforehand. A local tracking ref is
    NOT a remote API verification. Print the exact HEAD so its parity can be
    independently compared with a freshly inspected GitHub target.
    """
    def git(*args: str) -> tuple[int, bytes] | None:
        try:
            process = subprocess.run(
                ("git", "-C", str(root), *args),
                stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL, check=False, timeout=10,
            )
        except (OSError, subprocess.TimeoutExpired):
            return None
        return (process.returncode, process.stdout)

    top = git("rev-parse", "--show-toplevel")
    if top is None or top[0] != 0:
        return ("CHECKOUT_GIT_UNAVAILABLE", None)
    try:
        actual_root = Path(top[1].decode("utf-8").strip()).resolve()
    except (UnicodeError, ValueError, OSError):
        return ("CHECKOUT_ROOT_INVALID", None)
    if actual_root != root.resolve():
        return ("CHECKOUT_ROOT_MISMATCH", None)
    candidate = candidate_head is not None or base_sha is not None
    if candidate and (not isinstance(candidate_head, str)
                      or not re.fullmatch(r"[0-9a-f]{40}", candidate_head)
                      or not isinstance(base_sha, str)
                      or not re.fullmatch(r"[0-9a-f]{40}", base_sha)):
        return ("CHECKOUT_CANDIDATE_SHAS_REQUIRED", None)
    branch = git("symbolic-ref", "--quiet", "--short", "HEAD")
    if branch is None or branch[0] != 0:
        return ("CHECKOUT_BRANCH_UNAVAILABLE", None)
    if candidate:
        if not branch[1].startswith((b"pm/", b"codex/")):
            return ("CHECKOUT_NOT_PR_CANDIDATE_BRANCH", None)
    elif branch[1] != b"model-v2/expected-return-challenger\n":
        return ("CHECKOUT_NOT_V2_BRANCH", None)
    clean = git("status", "--porcelain=v1", "-z", "--untracked-files=all")
    if clean is None or clean[0] != 0:
        return ("CHECKOUT_STATUS_UNAVAILABLE", None)
    if clean[1]:
        return ("CHECKOUT_HAS_CHANGES", None)
    current = git("rev-parse", "--verify", "HEAD^{commit}")
    target = git("rev-parse", "--verify",
                 "refs/remotes/origin/model-v2/expected-return-challenger^{commit}")
    if current is None or current[0] != 0:
        return ("CHECKOUT_HEAD_UNAVAILABLE", None)
    if target is None or target[0] != 0:
        return ("CHECKOUT_TRACKING_REF_UNAVAILABLE", None)
    head = current[1].decode("ascii", errors="replace").strip()
    tracking = target[1].decode("ascii", errors="replace").strip()
    if not re.fullmatch(r"[0-9a-f]{40}", head) or not re.fullmatch(r"[0-9a-f]{40}", tracking):
        return ("CHECKOUT_INVALID_SHA", None)
    if candidate:
        if head != candidate_head:
            return ("CHECKOUT_CANDIDATE_HEAD_MISMATCH", None)
        if tracking != base_sha:
            return ("CHECKOUT_CANDIDATE_BASE_MISMATCH", None)
        ancestry = git("merge-base", "--is-ancestor", base_sha, head)
        if ancestry != (0, b""):
            return ("CHECKOUT_CANDIDATE_NOT_BASE_DESCENDANT", None)
    elif head != tracking:
        return ("CHECKOUT_HEAD_DIFFERS_FROM_LOCAL_V2_TRACKING_REF", None)
    return (None, head)


def _discover(root: Path) -> unittest.TestSuite:
    return unittest.TestLoader().discover(
        start_dir=str(root / "tests"), pattern="test_ai_native_*.py",
        top_level_dir=str(root),
    )


def _discover_quick(root: Path) -> unittest.TestSuite:
    """Load exact source-backed contract modules, never skip import failures.

    Executed from an authenticated local checkout; TEST MODULE IMPORT ERRORS
    become failures in unittest rather than looking like a passing empty suite.
    """
    return unittest.TestLoader().loadTestsFromNames(QUICK_MODULES)


def _iter_tests(suite: unittest.TestSuite) -> Iterator[unittest.TestCase]:
    for item in suite:
        if isinstance(item, unittest.TestSuite):
            yield from _iter_tests(item)
        else:
            yield item


def validate(
    root: Path = ROOT, *, out: TextIO | None = None,
    checker: Callable[[Path], str | None] = _environment,
    checkout_checker: Callable[..., tuple[str | None, str | None]] = _checkout,
    candidate_head: str | None = None, base_sha: str | None = None,
    discoverer: Callable[[Path], unittest.TestSuite] = _discover,
    required: frozenset[str] = REQUIRED,
    minimum_modules: int = 40, minimum_cases: int = 100,
    quick: bool = False,
) -> int:
    """Fail closed on prerequisites, zero tests, import errors and failed tests.

    Injected callables exist for isolated runner unit tests; the CLI always
    uses the real environment check and unittest discovery.
    """
    stream = out if out is not None else sys.stdout
    root = root.resolve()

    def line(k: str, v: object) -> None:
        stream.write(f"{k}={v}\n")

    line("R1_SCOPE", ("UNPINNED_STDLIB_SYNTHETIC_SMOKE_NOT_ACCEPTANCE"
                       if quick else "SYNTHETIC_REGRESSION_ONLY_NOT_ACCEPTANCE"))
    line("R1_AUTHENTIC_SOURCES", "NOT_CHECKED")
    line("R1_PROJECTS", "NOT_INVOKED")
    line("R1_READINESS", "NOT_EVALUATED")
    line("R1_PYTHON_PIN_VERIFIED", "NO_QUICK_MODE" if quick else "CHECKED_BY_ENVIRONMENT_GATE")
    line("R1_DEPENDENCY_LOCK_VERIFIED", "NO_QUICK_MODE" if quick else "CHECKED_BY_ENVIRONMENT_GATE")
    # A fast local signal is useful when GitHub CI never gets a runner or a
    # device lacks the pinned Python/dependencies. Unpinned PASS != full PASS.
    reason = ("QUICK_REQUIRES_PYTHON_3_11_OR_NEWER"
              if quick and sys.version_info < (3, 11) else None)
    if not quick:
        reason = checker(root)
    if reason is not None:
        line("R1_VALIDATION", "BLOCKED_ENVIRONMENT")
        line("R1_REASON", reason)
        return 2
    candidate = candidate_head is not None or base_sha is not None
    if candidate:
        checkout_reason, checkout_sha = checkout_checker(
            root, candidate_head=candidate_head, base_sha=base_sha)
    else:
        checkout_reason, checkout_sha = checkout_checker(root)
    if checkout_reason is not None or checkout_sha is None:
        line("R1_VALIDATION", "BLOCKED_CHECKOUT")
        line("R1_REASON", checkout_reason or "CHECKOUT_HEAD_UNAVAILABLE")
        return 2
    line("R1_TESTED_HEAD_SHA", checkout_sha)
    line("R1_CHECKOUT_MODE", "PR_CANDIDATE" if candidate else "V2_INTEGRATION_BRANCH")
    if candidate:
        line("R1_CANDIDATE_BASE_SHA", base_sha)
    line("R1_HEAD_PROVENANCE", "LOCAL_TRACKING_REF_ONLY_COMPARE_TO_LIVE_GITHUB")
    directory = root / "tests"
    actual = {p.name for p in directory.glob("test_ai_native_*.py")}
    inventory = (frozenset(name.rsplit(".", 1)[-1] + ".py"
                           for name in QUICK_MODULES) if quick else required)
    missing = inventory - actual
    if missing or len(actual) < minimum_modules:
        line("R1_VALIDATION", "BLOCKED_TEST_INVENTORY")
        line("R1_REASON", "REQUIRED_R1_TESTS_MISSING" if missing else "R1_TEST_INVENTORY_TOO_SMALL")
        line("R1_MISSING_MODULES", ",".join(sorted(missing)))
        return 2
    try:
        suite = (_discover_quick(root) if quick and discoverer is _discover
                 else discoverer(root))
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
    if quick:
        line("R1_QUICK_SELECTED_MODULES", len(QUICK_MODULES))
        line("R1_QUICK_PINNED_REGRESSION_STATUS", "NOT_RUN")
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
    line("R1_VALIDATION", (
        ("PASS_UNPINNED_SYNTHETIC_SMOKE_ONLY" if successful
         else "FAIL_UNPINNED_SYNTHETIC_SMOKE") if quick
        else ("PASS_FOCUSED_TESTS_ONLY" if successful
              else "FAIL_FOCUSED_TESTS")))
    return 0 if successful else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate-head", metavar="FULL_PR_SHA")
    parser.add_argument("--base-sha", metavar="FULL_V2_BASE_SHA")
    parser.add_argument("--quick-stdlib-smoke", action="store_true",
                        help="run fixed critical R1 synthetic subset with Python "
                             ">=3.11, no dependency installation; UNPINNED, not acceptance")
    args = parser.parse_args()
    if (args.candidate_head is None) != (args.base_sha is None):
        parser.error("--candidate-head and --base-sha must be supplied together")
    return validate(candidate_head=args.candidate_head, base_sha=args.base_sha,
                    quick=args.quick_stdlib_smoke)


if __name__ == "__main__":
    raise SystemExit(main())
