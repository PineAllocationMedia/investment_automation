#!/usr/bin/env python3
"""Run PAM's existing validation architecture against one exact committed HEAD."""
from __future__ import annotations

import argparse
import ast
from dataclasses import dataclass
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from typing import Callable, Sequence


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from pit_comparison.source_export import static_identity  # noqa: E402
from scripts.ci_validation_plan import ValidationPlan, plan_validation  # noqa: E402
from src.dependency_reproducibility import dependency_environment  # noqa: E402


FULL_SHA = re.compile(r"[0-9a-f]{40}")
FINGERPRINT = re.compile(r"[0-9a-f]{64}")
TRUSTED_INTEGRATION_REF = "refs/remotes/origin/model-v2/expected-return-challenger"
SUMMARY_KEYS = (
    "PAM_PREFLIGHT_STATUS",
    "PAM_PREFLIGHT_BASE_SHA",
    "PAM_PREFLIGHT_TRUSTED_TARGET_SHA",
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
    trusted_target_sha: str = "UNRESOLVED"
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
                    self.trusted_target_sha,
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
    environment: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[bytes]:
    try:
        result = runner(
            list(command),
            cwd=root,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE if capture else None,
            stderr=subprocess.PIPE if capture else None,
            check=False,
            env=environment,
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


def require_clean_git(
    root: Path,
    *,
    step: str = "git-clean",
    runner: Runner = subprocess.run,
) -> None:
    status = _git_bytes(
        root,
        "status",
        "--porcelain=v1",
        "-z",
        "--untracked-files=all",
        step=step,
        runner=runner,
    )
    if status:
        raise PreflightError(step, "tracked, staged, or untracked changes are present")


def require_trusted_base(
    root: Path,
    supplied_base: str,
    *,
    runner: Runner = subprocess.run,
) -> tuple[str, str]:
    trusted_sha = resolve_commit(
        root,
        TRUSTED_INTEGRATION_REF,
        label="trusted-target",
        runner=runner,
    )
    supplied_sha = resolve_commit(root, supplied_base, label="base", runner=runner)
    if supplied_sha != trusted_sha:
        raise PreflightError(
            "base-trust",
            "supplied base does not equal the trusted local V2 integration target",
        )
    return supplied_sha, trusted_sha


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


def verify_python_environment(
    root: Path,
    *,
    version_info: Sequence[int] = sys.version_info,
) -> None:
    try:
        pinned = (root / ".python-version").read_text(encoding="utf-8").strip()
    except OSError as exc:
        raise PreflightError("python-environment", f"unable to read .python-version: {exc}") from exc
    match = re.fullmatch(r"(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)", pinned)
    if not match:
        raise PreflightError("python-environment", ".python-version must be exact major.minor.patch")
    expected = tuple(int(match.group(index)) for index in range(1, 4))
    if tuple(version_info[:3]) != expected:
        raise PreflightError(
            "python-environment",
            f"Python {'.'.join(map(str, expected))} is required",
        )
    environment = dependency_environment(root / "requirements.lock")
    if environment.get("dependency_status") != "MATCH":
        raise PreflightError(
            "python-environment",
            "locked dependency environment does not match requirements.lock",
        )


def create_detached_worktree(
    root: Path,
    candidate_sha: str,
    *,
    runner: Runner = subprocess.run,
) -> tuple[Path, tempfile.TemporaryDirectory[str]]:
    temporary = tempfile.TemporaryDirectory(
        prefix="pam-preflight-worktree-",
        dir=str(Path(tempfile.gettempdir()).resolve()),
    )
    worktree = Path(temporary.name) / "candidate"
    try:
        _git_bytes(
            root,
            "worktree",
            "add",
            "--detach",
            str(worktree),
            candidate_sha,
            step="worktree-create",
            runner=runner,
        )
    except BaseException:
        temporary.cleanup()
        raise
    return worktree, temporary


def remove_detached_worktree(
    root: Path,
    worktree: Path,
    temporary: tempfile.TemporaryDirectory[str],
    *,
    runner: Runner = subprocess.run,
) -> None:
    cleanup_error: PreflightError | None = None
    try:
        _git_bytes(
            root,
            "worktree",
            "remove",
            "--force",
            str(worktree),
            step="worktree-cleanup",
            runner=runner,
        )
    except PreflightError as exc:
        cleanup_error = exc
    try:
        temporary.cleanup()
    except OSError as exc:
        if cleanup_error is None:
            cleanup_error = PreflightError("worktree-cleanup", f"temporary cleanup failed: {exc}")
    if cleanup_error is not None:
        raise cleanup_error


def verify_exact_worktree(
    root: Path,
    candidate_sha: str,
    *,
    label: str,
    runner: Runner = subprocess.run,
) -> None:
    actual_sha = resolve_commit(root, "HEAD", label=f"{label}-head", runner=runner)
    if actual_sha != candidate_sha:
        raise PreflightError(label, "worktree HEAD does not equal the resolved candidate HEAD")
    detached = _git_bytes(
        root,
        "rev-parse",
        "--abbrev-ref",
        "HEAD",
        step=label,
        runner=runner,
    ).decode("ascii", errors="strict").strip()
    if detached != "HEAD":
        raise PreflightError(label, "validation worktree is not detached")
    require_clean_git(root, step=f"{label}-clean", runner=runner)


def run_python_validation(
    root: Path,
    plan: ValidationPlan,
    *,
    runner: Runner = subprocess.run,
) -> None:
    python = sys.executable
    environment = os.environ.copy()
    environment["TMPDIR"] = str(Path(tempfile.gettempdir()).resolve())
    print("PAM_PREFLIGHT_STEP=fast-validation-checks", flush=True)
    _run(
        (python, "-m", "unittest", "-q", *FAST_TEST_MODULES),
        root=root,
        step="fast-validation-checks",
        runner=runner,
        capture=False,
        environment=environment,
    )
    print("PAM_PREFLIGHT_STEP=compile", flush=True)
    _run(
        (python, "-m", "compileall", "-q", *COMPILE_TARGETS),
        root=root,
        step="compile",
        runner=runner,
        capture=False,
        environment=environment,
    )
    print("PAM_PREFLIGHT_STEP=discovered-suite", flush=True)
    _run(
        (python, "scripts/ci_unittest_runner.py", "--tier", plan.tier.name),
        root=root,
        step="discovered-suite",
        runner=runner,
        capture=False,
        environment=environment,
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
        state.base_sha, state.trusted_target_sha = require_trusted_base(
            root, base, runner=runner
        )
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
        worktree: Path | None = None
        temporary: tempfile.TemporaryDirectory[str] | None = None
        validation_error: BaseException | None = None
        cleanup_error: PreflightError | None = None
        try:
            worktree, temporary = create_detached_worktree(
                root, state.head_sha, runner=runner
            )
            verify_exact_worktree(
                worktree,
                state.head_sha,
                label="detached-candidate",
                runner=runner,
            )
            (
                state.model_rules_version,
                state.pit_fingerprint,
                state.determinism_fingerprint,
            ) = extract_protected_integrity(worktree)
            if plan.tier.name != "DOCS_ONLY":
                verify_python_environment(worktree)
                run_python_validation(worktree, plan, runner=runner)

            final_head = resolve_commit(root, "HEAD", label="final-head", runner=runner)
            if final_head != state.head_sha:
                raise PreflightError(
                    "final-source-head",
                    "original repository HEAD changed during validation",
                )
            require_clean_git(root, step="final-source-clean", runner=runner)
            verify_exact_worktree(
                worktree,
                state.head_sha,
                label="final-detached-candidate",
                runner=runner,
            )
        except BaseException as exc:
            validation_error = exc
        finally:
            if worktree is not None and temporary is not None:
                try:
                    remove_detached_worktree(root, worktree, temporary, runner=runner)
                except PreflightError as exc:
                    cleanup_error = exc
        if cleanup_error is not None:
            if validation_error is not None:
                raise PreflightError(
                    "worktree-cleanup",
                    f"{cleanup_error}; validation also failed: {validation_error}",
                ) from validation_error
            raise cleanup_error
        if validation_error is not None:
            raise validation_error
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
