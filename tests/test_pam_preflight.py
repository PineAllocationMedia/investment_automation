from __future__ import annotations

import contextlib
import io
import os
from pathlib import Path
import socket
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from scripts import pam_preflight
from scripts.ci_validation_plan import ValidationTier


def git(root: Path, *arguments: str, check: bool = True) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        ["git", "-C", str(root), *arguments],
        check=check,
        capture_output=True,
        env={
            **os.environ,
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_AUTHOR_NAME": "PAM Preflight Test",
            "GIT_AUTHOR_EMAIL": "preflight@example.invalid",
            "GIT_COMMITTER_NAME": "PAM Preflight Test",
            "GIT_COMMITTER_EMAIL": "preflight@example.invalid",
        },
    )


class SyntheticRepository:
    def __init__(self, root: Path):
        self.root = root
        git(root, "init", "-q")
        self.write("README.md", "base\n")
        self.write(".python-version", "3.12.13\n")
        self.write("src/model_version.py", 'MODEL_RULES_VERSION = "rules-v1"\n')
        self.write(
            "tests/test_pit_adapter_equivalence.py",
            """def test_comprehensive_original_oracle_and_v1_v2_equivalence(self):
    fingerprints = []
    self.assertEqual(fingerprint(fingerprints), '1111111111111111111111111111111111111111111111111111111111111111')
""",
        )
        self.write(
            "tests/test_pit_comparison.py",
            """def test_pair_authority_provenance_and_reproducibility(self):
    fingerprints = []
    self.assertEqual(fingerprints[0], '2222222222222222222222222222222222222222222222222222222222222222')
""",
        )
        self.commit("base")
        self.base = self.sha()
        self.set_trusted(self.base)

    def write(self, relative: str, content: str) -> None:
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def commit(self, message: str) -> None:
        git(self.root, "add", ".")
        git(self.root, "commit", "-qm", message)

    def sha(self) -> str:
        return git(self.root, "rev-parse", "HEAD").stdout.decode().strip()

    def set_trusted(self, revision: str) -> None:
        git(self.root, "update-ref", pam_preflight.TRUSTED_INTEGRATION_REF, revision)


class PamPreflightTests(unittest.TestCase):
    def temporary_repository(self):
        temporary = tempfile.TemporaryDirectory(prefix="pam-preflight-test-")
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name).resolve()
        return SyntheticRepository(root)

    def test_missing_base_fails_closed(self):
        code, state, error = pam_preflight.execute(None)
        self.assertNotEqual(code, 0)
        self.assertEqual(state.status, "FAIL")
        self.assertEqual(error.step, "base")

    def test_invalid_unresolvable_base_fails_closed(self):
        repo = self.temporary_repository()
        code, state, error = pam_preflight.execute("does-not-exist", root=repo.root)
        self.assertNotEqual(code, 0)
        self.assertEqual(state.base_sha, "UNRESOLVED")
        self.assertEqual(error.step, "base")

    def test_trusted_target_equal_to_supplied_base_is_accepted(self):
        repo = self.temporary_repository()
        supplied, trusted = pam_preflight.require_trusted_base(repo.root, repo.base)
        self.assertEqual((supplied, trusted), (repo.base, repo.base))

    def test_valid_supplied_commit_different_from_trusted_target_is_rejected(self):
        repo = self.temporary_repository()
        repo.write("later.md", "later\n")
        repo.commit("later")
        with self.assertRaises(pam_preflight.PreflightError) as raised:
            pam_preflight.require_trusted_base(repo.root, repo.sha())
        self.assertEqual(raised.exception.step, "base-trust")

    def test_sensitive_ancestor_cannot_be_selected_to_downgrade_later_docs(self):
        repo = self.temporary_repository()
        repo.write("src/sensitive.py", "SENSITIVE = True\n")
        repo.commit("sensitive source")
        sensitive_sha = repo.sha()
        repo.write("later.md", "later docs\n")
        repo.commit("later docs")
        with patch("scripts.pam_preflight.plan_validation") as planner:
            code, state, error = pam_preflight.execute(sensitive_sha, root=repo.root)
        self.assertNotEqual(code, 0)
        self.assertEqual(state.status, "FAIL")
        self.assertEqual(error.step, "base-trust")
        planner.assert_not_called()

    def test_missing_trusted_integration_ref_fails_closed(self):
        repo = self.temporary_repository()
        git(repo.root, "update-ref", "-d", pam_preflight.TRUSTED_INTEGRATION_REF)
        with self.assertRaises(pam_preflight.PreflightError) as raised:
            pam_preflight.require_trusted_base(repo.root, repo.base)
        self.assertEqual(raised.exception.step, "trusted-target")

    def test_unresolvable_trusted_integration_ref_fails_closed(self):
        repo = self.temporary_repository()
        git(repo.root, "update-ref", "-d", pam_preflight.TRUSTED_INTEGRATION_REF)
        git(
            repo.root,
            "symbolic-ref",
            pam_preflight.TRUSTED_INTEGRATION_REF,
            "refs/heads/missing-trusted-target",
        )
        with self.assertRaises(pam_preflight.PreflightError) as raised:
            pam_preflight.require_trusted_base(repo.root, repo.base)
        self.assertEqual(raised.exception.step, "trusted-target")

    def test_empty_diff_fails_toward_full_pit(self):
        repo = self.temporary_repository()
        paths = pam_preflight.changed_paths(repo.root, repo.base, repo.base)
        self.assertEqual(paths, [])
        self.assertEqual(pam_preflight.select_plan(paths).tier, ValidationTier.FULL_PIT)

    def test_canonical_tier_routing_is_reused(self):
        cases = (
            (["README.md"], ValidationTier.DOCS_ONLY),
            (["economic_facts/fact.py"], ValidationTier.STANDARD),
            (["tests/test_ordinary.py"], ValidationTier.STANDARD),
            (["src/engine.py"], ValidationTier.FULL_PIT),
            (["unknown/tool.py"], ValidationTier.FULL_PIT),
        )
        for paths, expected in cases:
            with self.subTest(paths=paths):
                self.assertEqual(pam_preflight.select_plan(paths).tier, expected)

    def test_rename_safe_diff_exposes_old_and_new_paths(self):
        repo = self.temporary_repository()
        repo.write("src/old_engine.py", "VALUE = 1\n")
        repo.commit("add source")
        base = repo.sha()
        (repo.root / "docs").mkdir(exist_ok=True)
        git(repo.root, "mv", "src/old_engine.py", "docs/old_engine.md")
        repo.commit("rename source to docs")
        paths = pam_preflight.changed_paths(repo.root, base, repo.sha())
        self.assertEqual(paths, ["docs/old_engine.md", "src/old_engine.py"])
        self.assertEqual(pam_preflight.select_plan(paths).tier, ValidationTier.FULL_PIT)

    def test_dirty_unstaged_worktree_fails(self):
        repo = self.temporary_repository()
        repo.write("README.md", "dirty\n")
        with self.assertRaisesRegex(pam_preflight.PreflightError, "changes are present"):
            pam_preflight.require_clean_git(repo.root)

    def test_staged_changes_fail(self):
        repo = self.temporary_repository()
        repo.write("staged.md", "staged\n")
        git(repo.root, "add", "staged.md")
        with self.assertRaisesRegex(pam_preflight.PreflightError, "changes are present"):
            pam_preflight.require_clean_git(repo.root)

    def test_untracked_file_fails(self):
        repo = self.temporary_repository()
        repo.write("untracked.md", "untracked\n")
        with self.assertRaisesRegex(pam_preflight.PreflightError, "changes are present"):
            pam_preflight.require_clean_git(repo.root)

    def test_failed_git_integrity_check_fails(self):
        repo = self.temporary_repository()

        def failing_runner(command, **kwargs):
            if command[4:6] == ["diff", "--check"]:
                return subprocess.CompletedProcess(command, 2, b"", b"synthetic whitespace error")
            return subprocess.run(command, **kwargs)

        with self.assertRaisesRegex(pam_preflight.PreflightError, "synthetic whitespace error"):
            pam_preflight.run_git_integrity(
                repo.root, repo.base, repo.base, runner=failing_runner
            )

    def test_planner_failure_fails_closed(self):
        with patch("scripts.pam_preflight.plan_validation", side_effect=RuntimeError("broken")):
            with self.assertRaisesRegex(pam_preflight.PreflightError, "planner failed"):
                pam_preflight.select_plan(["README.md"])

    def test_runner_failure_fails_closed(self):
        calls = []

        def failing_runner(command, **kwargs):
            calls.append(command)
            return subprocess.CompletedProcess(
                command,
                1 if len(calls) == 3 else 0,
                b"",
                b"synthetic runner failure" if len(calls) == 3 else b"",
            )

        plan = pam_preflight.select_plan(["economic_facts/fact.py"])
        with contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaisesRegex(pam_preflight.PreflightError, "command failed") as raised:
                pam_preflight.run_python_validation(Path.cwd(), plan, runner=failing_runner)
        self.assertEqual(raised.exception.step, "discovered-suite")
        self.assertEqual(len(calls), 3)

    def test_python_validation_uses_physical_temp_root(self):
        environments = []

        def successful_runner(command, **kwargs):
            environments.append(kwargs["env"])
            return subprocess.CompletedProcess(command, 0, b"", b"")

        plan = pam_preflight.select_plan(["economic_facts/fact.py"])
        with contextlib.redirect_stdout(io.StringIO()):
            pam_preflight.run_python_validation(Path.cwd(), plan, runner=successful_runner)
        expected = str(Path(tempfile.gettempdir()).resolve())
        self.assertEqual(len(environments), 3)
        self.assertTrue(all(environment["TMPDIR"] == expected for environment in environments))

    def test_protected_integrity_is_extracted_from_canonical_surfaces(self):
        repo = self.temporary_repository()
        self.assertEqual(
            pam_preflight.extract_protected_integrity(repo.root),
            ("rules-v1", "1" * 64, "2" * 64),
        )

    def test_malformed_protected_integrity_fails_closed(self):
        repo = self.temporary_repository()
        repo.write("src/model_version.py", "MODEL_RULES_VERSION = dynamic_value\n")
        with self.assertRaises(pam_preflight.PreflightError) as raised:
            pam_preflight.extract_protected_integrity(repo.root)
        self.assertEqual(raised.exception.step, "protected-integrity")

    def test_exact_python_version_is_accepted(self):
        repo = self.temporary_repository()
        repo.write("requirements.lock", "synthetic==1\n")
        with patch(
            "scripts.pam_preflight.dependency_environment",
            return_value={"dependency_status": "MATCH"},
        ):
            pam_preflight.verify_python_environment(
                repo.root, version_info=(3, 12, 13)
            )

    def test_same_python_major_minor_with_wrong_patch_is_rejected(self):
        repo = self.temporary_repository()
        with self.assertRaisesRegex(pam_preflight.PreflightError, "3.12.13"):
            pam_preflight.verify_python_environment(
                repo.root, version_info=(3, 12, 14)
            )

    def test_wrong_python_minor_is_rejected(self):
        repo = self.temporary_repository()
        with self.assertRaisesRegex(pam_preflight.PreflightError, "3.12.13"):
            pam_preflight.verify_python_environment(
                repo.root, version_info=(3, 13, 13)
            )

    def test_malformed_non_exact_python_pin_is_rejected(self):
        repo = self.temporary_repository()
        for malformed in ("3.12\n", "03.12.13\n", "3.12.13.1\n"):
            with self.subTest(malformed=malformed):
                repo.write(".python-version", malformed)
                with self.assertRaisesRegex(pam_preflight.PreflightError, "major.minor.patch"):
                    pam_preflight.verify_python_environment(
                        repo.root, version_info=(3, 12, 13)
                    )

    def test_original_head_change_during_validation_prevents_pass(self):
        repo = self.temporary_repository()
        repo.write("economic_facts/fact.py", "VALUE = 1\n")
        repo.commit("ordinary candidate")

        def mutate_original(_validation_root, _plan, *, runner):
            repo.write("late.md", "late commit\n")
            repo.commit("concurrent commit")

        with patch("scripts.pam_preflight.verify_python_environment"), patch(
            "scripts.pam_preflight.run_python_validation", side_effect=mutate_original
        ):
            code, state, error = pam_preflight.execute(repo.base, root=repo.root)
        self.assertNotEqual(code, 0)
        self.assertEqual(state.status, "FAIL")
        self.assertEqual(error.step, "final-source-head")

    def test_original_dirty_change_during_validation_prevents_pass(self):
        repo = self.temporary_repository()
        repo.write("economic_facts/fact.py", "VALUE = 1\n")
        repo.commit("ordinary candidate")

        def dirty_original(_validation_root, _plan, *, runner):
            repo.write("untracked-during-validation.md", "dirty\n")

        with patch("scripts.pam_preflight.verify_python_environment"), patch(
            "scripts.pam_preflight.run_python_validation", side_effect=dirty_original
        ):
            code, state, error = pam_preflight.execute(repo.base, root=repo.root)
        self.assertNotEqual(code, 0)
        self.assertEqual(state.status, "FAIL")
        self.assertEqual(error.step, "final-source-clean")

    def test_detached_candidate_head_mismatch_prevents_pass(self):
        repo = self.temporary_repository()
        repo.write("candidate.md", "candidate\n")
        repo.commit("candidate")
        original_create = pam_preflight.create_detached_worktree

        def create_wrong_candidate(root, _candidate_sha, *, runner):
            return original_create(root, repo.base, runner=runner)

        with patch(
            "scripts.pam_preflight.create_detached_worktree",
            side_effect=create_wrong_candidate,
        ):
            code, state, error = pam_preflight.execute(repo.base, root=repo.root)
        self.assertNotEqual(code, 0)
        self.assertEqual(state.status, "FAIL")
        self.assertEqual(error.step, "detached-candidate")

    def test_detached_candidate_dirty_change_prevents_pass(self):
        repo = self.temporary_repository()
        repo.write("economic_facts/fact.py", "VALUE = 1\n")
        repo.commit("ordinary candidate")

        def dirty_detached(validation_root, _plan, *, runner):
            (validation_root / "README.md").write_text("dirty detached\n", encoding="utf-8")

        with patch("scripts.pam_preflight.verify_python_environment"), patch(
            "scripts.pam_preflight.run_python_validation", side_effect=dirty_detached
        ):
            code, state, error = pam_preflight.execute(repo.base, root=repo.root)
        self.assertNotEqual(code, 0)
        self.assertEqual(state.status, "FAIL")
        self.assertEqual(error.step, "final-detached-candidate-clean")

    def test_successful_exact_head_validation_preserves_original_branch(self):
        repo = self.temporary_repository()
        repo.write("candidate.md", "candidate docs\n")
        repo.commit("candidate docs")
        branch_before = git(repo.root, "symbolic-ref", "--short", "HEAD").stdout
        head_before = repo.sha()
        code, state, error = pam_preflight.execute(repo.base, root=repo.root)
        branch_after = git(repo.root, "symbolic-ref", "--short", "HEAD").stdout
        worktrees = git(repo.root, "worktree", "list", "--porcelain").stdout.decode()
        self.assertEqual((code, error), (0, None))
        self.assertEqual(state.status, "PASS")
        self.assertEqual(state.head_sha, head_before)
        self.assertEqual(repo.sha(), head_before)
        self.assertEqual(branch_after, branch_before)
        self.assertEqual(worktrees.count("worktree "), 1)

    def test_worktree_cleanup_failure_prevents_pass(self):
        repo = self.temporary_repository()
        repo.write("candidate.md", "candidate docs\n")
        repo.commit("candidate docs")
        original_remove = pam_preflight.remove_detached_worktree

        def remove_then_report_failure(root, worktree, temporary, *, runner):
            original_remove(root, worktree, temporary, runner=runner)
            raise pam_preflight.PreflightError(
                "worktree-cleanup", "synthetic cleanup failure"
            )

        with patch(
            "scripts.pam_preflight.remove_detached_worktree",
            side_effect=remove_then_report_failure,
        ):
            code, state, error = pam_preflight.execute(repo.base, root=repo.root)
        self.assertNotEqual(code, 0)
        self.assertEqual(state.status, "FAIL")
        self.assertEqual(error.step, "worktree-cleanup")

    def test_summary_order_and_output_are_deterministic(self):
        state = pam_preflight.PreflightState(
            status="PASS",
            base_sha="a" * 40,
            trusted_target_sha="a" * 40,
            head_sha="b" * 40,
            git_clean="true",
            tier="FULL_PIT",
            changed_file_count="4",
            heavy_pit_required="true",
            model_rules_version="rules-v1",
            pit_fingerprint="1" * 64,
            determinism_fingerprint="2" * 64,
        )
        first = pam_preflight.format_summary(state)
        self.assertEqual(first, pam_preflight.format_summary(state))
        self.assertEqual(
            [line.split("=", 1)[0] for line in first.splitlines()],
            list(pam_preflight.SUMMARY_KEYS),
        )

    def test_no_caller_controlled_tier_downgrade(self):
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):
                pam_preflight.parse_args(["--base", "HEAD", "--tier", "DOCS_ONLY"])

    def test_docs_only_execution_has_no_network_dependency(self):
        repo = self.temporary_repository()
        repo.write("contract.md", "docs only\n")
        repo.commit("docs")

        def deny_network(*_args, **_kwargs):
            raise AssertionError("network access attempted")

        with contextlib.redirect_stdout(io.StringIO()):
            with patch.object(socket, "create_connection", side_effect=deny_network), patch.object(
                socket, "getaddrinfo", side_effect=deny_network
            ):
                code, state, error = pam_preflight.execute(repo.base, root=repo.root)
        self.assertEqual((code, error), (0, None))
        self.assertEqual(state.status, "PASS")
        self.assertEqual(state.tier, "DOCS_ONLY")


if __name__ == "__main__":
    unittest.main()
