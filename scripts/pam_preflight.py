#!/usr/bin/env python3
"""Run PAM's existing validation architecture against one exact committed HEAD."""
from __future__ import annotations

import argparse
import ast
from dataclasses import dataclass
from pathlib import Path
import re
import subprocess
import sys
from typing import Callable, Sequence


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from pit_comparison.source_export import static_identity  # noqa: E402
from scripts.ci_validation_plan import ValidationPlan, plan_validation  # noqa: E402
from src.dependency_reproducibility import dependency_environment  # noqa: E402


FULL_SHA = re.compile(r"[0-9a-f]{40}")
FINGERPRINT = re.compile(r"[0-9a-f]{64}")
SUMMARY_KEYS = (
    "PAM_PREFLIGHT_STATUS",
    "PAM_PREFLIGHT_BASE_SHA",
    "PAM_PREFLIGHT_HEAD_SHA",
    "PAM_PREFLIGHT_GIT_CLEAN",
    "CI_VALIDATION_TIER",
    "CI_CHANGED_FILE_COUNT",
    "CI_HEAVY_PIT_REQUIRED",
    "PAM_MODEL_RULES_VERSION",
    "PAM_PIT_FINGERPRINT",
    "PAM_DETERMINISM_FINGERPRINT",
)
COMPILE_TARGETS = (
    "main.py",
    "src",
    "scripts",
    "tests",
    "economic_facts",
    "pit_comparison",
)
FAST_TEST_MODULES = (
    "tests.test_ci_validation_plan",
    "tests.test_ci_unittest_runner",
    "tests.test_pam_preflight",
)


class PreflightError(RuntimeError):
    """A required preflight control could not complete successfully."""

    def __init__(self, step: str, message: str):
        super().__init__(message)
        self.step = step


@dataclass
class PreflightState:
    status: str = "FAIL"
    base_sha: str = "UNRESOLVED"
    head_sha: str = "UNRESOLVED"
    git_clean: str = "false"
    tier: str = "UNRESOLVED"
    changed_file_count: str = "UNRESOLVED"
    heavy_pit_required: str = "UNRESOLVED"
    model_rules_version: str = "UNRESOLVED"
    pit_fingerprint: str = "UNRESOLVED"
    determinism_fingerprint: str = "UNRESOLVED"

    def summary(self) -> dict[str, str]:
        return dict(
            zip(
                SUMMARY_KEYS,
                (
                    self.status,
                    self.base_sha,
                    self.head_sha,
                    self.git_clean,
                    self.tier,
                    self.changed_file_count,
                    self.heavy_pit_required,
                    self.model_rules_version,
                    self.pit_fingerprint,
                    self.determinism_fingerprint,
                ),
                strict=True,
            )
        )


Runner = Callable[..., subprocess.CompletedProcess[bytes]]


def _run(
    command: Sequence[str],
    *,
    root: Path,
    step: str,
    runner: Runner = subprocess.run,
    capture: bool = True,
) -> subprocess.CompletedProcess[bytes]:
    try:
        result = runner(
            list(command),
            cwd=root,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE if capture else None,
            stderr=subprocess.PIPE if capture else None,
            check=False,
        )
    except OSError as exc:
        raise PreflightError(step, f"unable to execute {command[0]}: {exc}") from exc
    if result.returncode != 0:
        detail = ""
        if capture and result.stderr:
            detail = result.stderr.decode("utf-8", errors="replace").strip()
        suffix = f": {detail}" if detail else ""
        raise PreflightError(step, f"command failed ({result.returncode}){suffix}")
    return result


def _git_bytes(
    root: Path,
    *arguments: str,
    step: str,
    runner: Runner = subprocess.run,
) -> bytes:
    return _run(
        ("git", "--no-pager", "-C", str(root), *arguments),
        root=root,
        step=step,
        runner=runner,
    ).stdout


def verify_repository(root: Path, *, runner: Runner = subprocess.run) -> None:
    try:
        top = _git_bytes(root, "rev-parse", "--show-toplevel", step="repository", runner=runner)
        top_path = Path(top.decode("utf-8", errors="strict").strip()).resolve()
    except (UnicodeDecodeError, ValueError) as exc:
        raise PreflightError("repository", "Git returned an invalid repository root") from exc
    if top_path != root.resolve():
        raise PreflightError("repository", f"expected repository root {root.resolve()}, got {top_path}")


def resolve_commit(root: Path, revision: str, *, label: str, runner: Runner = subprocess.run) -> str:
    if not revision or "\x00" in revision or "\n" in revision or "\r" in revision:
        raise PreflightError(label, f"invalid {label} revision")
    raw = _git_bytes(
        root,
        "rev-parse",
        "--verify",
        "--end-of-options",
        f"{revision}^{{commit}}",
        step=label,
        runner=runner,
    )
    try:
        sha = raw.decode("ascii", errors="strict").strip()
    except UnicodeDecodeError as exc:
        raise PreflightError(label, f"Git returned a non-ASCII {label} SHA") from exc
    if not FULL_SHA.fullmatch(sha):
        raise PreflightError(label, f"Git returned an invalid {label} SHA")
    return sha


def require_clean_git(root: Path, *, runner: Runner = subprocess.run) -> None:
    status = _git_bytes(
        root,
        "status",
        "--porcelain=v1",
        "-z",
        "--untracked-files=all",
        step="git-clean",
        runner=runner,
    )
    if status:
        raise PreflightError("git-clean", "tracked, staged, or untracked changes are present")


def changed_paths(
    root: Path,
    base_sha: str,
    head_sha: str,
    *,
    runner: Runner = subprocess.run,
) -> list[str]:
    raw = _git_bytes(
        root,
        "diff",
        "--no-renames",
        "--name-only",
        "-z",
        base_sha,
        head_sha,
        step="changed-paths",
        runner=runner,
    )
    if raw and not raw.endswith(b"\0"):
        raise PreflightError("changed-paths", "Git returned malformed NUL-delimited paths")
    try:
        return [item.decode("utf-8", errors="strict") for item in raw.split(b"\0")[:-1]] if raw else []
    except UnicodeDecodeError as exc:
        raise PreflightError("changed-paths", "changed paths are not valid UTF-8") from exc


def select_plan(paths: Sequence[str]) -> ValidationPlan:
    try:
        plan = plan_validation(paths)
    except Exception as exc:
        raise PreflightError("validation-plan", f"planner failed: {exc}") from exc
    if plan.tier.name not in {"DOCS_ONLY", "STANDARD", "FULL_PIT"}:
        raise PreflightError("validation-plan", "planner returned an unsupported tier")
    return plan


def run_git_integrity(
    root: Path,
    base_sha: str,
    head_sha: str,
    *,
    runner: Runner = subprocess.run,
) -> None:
    for arguments, step in (
        (("diff", "--check", base_sha, head_sha), "git-diff-check"),
        (("diff", "--cached", "--check"), "git-cached-check"),
        (("show", "--format=", "--check", head_sha), "git-show-check"),
    ):
        _git_bytes(root, *arguments, step=step, runner=runner)


def _named_function(tree: ast.AST, name: str, *, source: Path) -> ast.FunctionDef:
    matches = [node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef) and node.name == name]
    if len(matches) != 1:
        raise PreflightError("protected-integrity", f"expected one {name} in {source}")
    return matches[0]


def _asserted_fingerprint(
    source: Path,
    function_name: str,
    first_argument_matches: Callable[[ast.expr], bool],
) -> str:
    try:
        tree = ast.parse(source.read_bytes(), filename=str(source))
    except (OSError, SyntaxError) as exc:
        raise PreflightError("protected-integrity", f"unable to parse {source}: {exc}") from exc
    function = _named_function(tree, function_name, source=source)
    matches: list[str] = []
    for node in ast.walk(function):
        if not isinstance(node, ast.Call) or len(node.args) < 2:
            continue
        if not (
            isinstance(node.func, ast.Attribute)
            and node.func.attr == "assertEqual"
            and first_argument_matches(node.args[0])
            and isinstance(node.args[1], ast.Constant)
            and isinstance(node.args[1].value, str)
            and FINGERPRINT.fullmatch(node.args[1].value)
        ):
            continue
        matches.append(node.args[1].value)
    if len(matches) != 1:
        raise PreflightError(
            "protected-integrity",
            f"expected one protected fingerprint assertion in {source}",
        )
    return matches[0]


def extract_protected_integrity(root: Path) -> tuple[str, str, str]:
    model_path = root / "src" / "model_version.py"
    try:
        model_rules = static_identity(model_path.read_bytes(), "MODEL_RULES_VERSION")
    except (OSError, ValueError) as exc:
        raise PreflightError("protected-integrity", f"invalid model rules identity: {exc}") from exc

    def aggregate_call(node: ast.expr) -> bool:
        return (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "fingerprint"
            and len(node.args) == 1
            and isinstance(node.args[0], ast.Name)
            and node.args[0].id == "fingerprints"
        )

    def first_fingerprint(node: ast.expr) -> bool:
        return (
            isinstance(node, ast.Subscript)
            and isinstance(node.value, ast.Name)
            and node.value.id == "fingerprints"
            and isinstance(node.slice, ast.Constant)
            and node.slice.value == 0
        )

    pit = _asserted_fingerprint(
        root / "tests" / "test_pit_adapter_equivalence.py",
        "test_comprehensive_original_oracle_and_v1_v2_equivalence",
        aggregate_call,
    )
    determinism = _asserted_fingerprint(
        root / "tests" / "test_pit_comparison.py",
        "test_pair_authority_provenance_and_reproducibility",
        first_fingerprint,
    )
    return model_rules, pit, determinism


def verify_python_environment(root: Path) -> None:
    try:
        pinned = (root / ".python-version").read_text(encoding="utf-8").strip()
    except OSError as exc:
        raise PreflightError("python-environment", f"unable to read .python-version: {exc}") from exc
    match = re.fullmatch(r"(\d+)\.(\d+)(?:\.\d+)?", pinned)
    if not match:
        raise PreflightError("python-environment", "invalid .python-version")
    expected_major_minor = (int(match.group(1)), int(match.group(2)))
    if sys.version_info[:2] != expected_major_minor:
        raise PreflightError(
            "python-environment",
            f"Python {expected_major_minor[0]}.{expected_major_minor[1]} is required",
        )
    environment = dependency_environment(root / "requirements.lock")
    if environment.get("dependency_status") != "MATCH":
        raise PreflightError(
            "python-environment",
            "locked dependency environment does not match requirements.lock",
        )


def run_python_validation(
    root: Path,
    plan: ValidationPlan,
    *,
    runner: Runner = subprocess.run,
) -> None:
    python = sys.executable
    print("PAM_PREFLIGHT_STEP=fast-validation-checks", flush=True)
    _run(
        (python, "-m", "unittest", "-q", *FAST_TEST_MODULES),
        root=root,
        step="fast-validation-checks",
        runner=runner,
        capture=False,
    )
    print("PAM_PREFLIGHT_STEP=compile", flush=True)
    _run(
        (python, "-m", "compileall", "-q", *COMPILE_TARGETS),
        root=root,
        step="compile",
        runner=runner,
        capture=False,
    )
    print("PAM_PREFLIGHT_STEP=discovered-suite", flush=True)
    _run(
        (python, "scripts/ci_unittest_runner.py", "--tier", plan.tier.name),
        root=root,
        step="discovered-suite",
        runner=runner,
        capture=False,
    )


def format_summary(state: PreflightState) -> str:
    summary = state.summary()
    return "\n".join(f"{key}={summary[key]}" for key in SUMMARY_KEYS)


def execute(
    base: str | None,
    *,
    root: Path = REPOSITORY_ROOT,
    runner: Runner = subprocess.run,
) -> tuple[int, PreflightState, PreflightError | None]:
    state = PreflightState()
    try:
        if not base:
            raise PreflightError("base", "--base is required")
        verify_repository(root, runner=runner)
        state.base_sha = resolve_commit(root, base, label="base", runner=runner)
        state.head_sha = resolve_commit(root, "HEAD", label="head", runner=runner)
        require_clean_git(root, runner=runner)
        state.git_clean = "true"
        paths = changed_paths(root, state.base_sha, state.head_sha, runner=runner)
        plan = select_plan(paths)
        state.tier = plan.tier.name
        state.changed_file_count = str(len(plan.changed_files))
        state.heavy_pit_required = "true" if plan.heavy_pit_required else "false"
        print(f"PAM_PREFLIGHT_CHANGED_FILES={len(plan.changed_files)}", flush=True)
        for path in plan.changed_files:
            print(f"PAM_PREFLIGHT_CHANGED_FILE={path}", flush=True)
        run_git_integrity(root, state.base_sha, state.head_sha, runner=runner)
        (
            state.model_rules_version,
            state.pit_fingerprint,
            state.determinism_fingerprint,
        ) = extract_protected_integrity(root)
        if plan.tier.name != "DOCS_ONLY":
            verify_python_environment(root)
            run_python_validation(root, plan, runner=runner)
        state.status = "PASS"
        return 0, state, None
    except PreflightError as exc:
        return 1, state, exc
    except KeyboardInterrupt:
        return 130, state, PreflightError("interrupted", "preflight interrupted")
    except Exception as exc:
        return 1, state, PreflightError("internal", f"unexpected error: {exc}")


def parse_args(arguments: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", help="explicit Git ref or SHA to compare with committed HEAD")
    return parser.parse_args(arguments)


def main(arguments: Sequence[str] | None = None) -> int:
    args = parse_args(arguments)
    code, state, error = execute(args.base)
    if error is not None:
        print(f"PAM preflight failed at {error.step}: {error}", file=sys.stderr, flush=True)
    print(format_summary(state), flush=True)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
