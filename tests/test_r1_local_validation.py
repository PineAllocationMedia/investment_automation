"""Synthetic, isolated contract checks for the local R1 regression runner."""
from __future__ import annotations
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
import subprocess

from scripts.r1_local_validation import validate, _checkout


class HarnessTests(unittest.TestCase):
    def case(self, checked=None, suite=None, required=frozenset()):
        with TemporaryDirectory() as td:
            root = Path(td)
            (root / "tests").mkdir()
            (root / "tests" / "test_ai_native_synthetic.py").write_text(
                "# existing", encoding="utf-8")
            out = StringIO()
            result = validate(
                root, out=out, checker=lambda _: checked,
                checkout_checker=lambda _: (None, "a" * 40),
                discoverer=lambda _: suite or unittest.TestSuite(),
                required=required, minimum_modules=1, minimum_cases=1)
            return result, out.getvalue()

    def test_environment_block_never_runs(self):
        code, result = self.case(checked="PYTHON_VERSION_DRIFT")
        self.assertEqual(code, 2)
        self.assertIn("R1_VALIDATION=BLOCKED_ENVIRONMENT", result)
        self.assertIn("R1_READINESS=NOT_EVALUATED", result)

    def test_missing_required_module_blocks(self):
        code, result = self.case(required=frozenset({"test_ai_native_nonexistent.py"}))
        self.assertEqual(code, 2)
        self.assertIn("R1_VALIDATION=BLOCKED_TEST_INVENTORY", result)

    def test_zero_tests_does_not_pass(self):
        code, result = self.case()
        self.assertEqual(code, 2)
        self.assertIn("R1_TEST_DISCOVERY_TOO_SMALL", result)

    def test_focused_pass_is_not_acceptance(self):
        class Passing(unittest.TestCase):
            def test_good(self):
                self.assertTrue(True)
        code, result = self.case(suite=unittest.defaultTestLoader.loadTestsFromTestCase(Passing))
        self.assertEqual(code, 0)
        self.assertIn("R1_VALIDATION=PASS_FOCUSED_TESTS_ONLY", result)
        self.assertIn("R1_PROJECTS=NOT_INVOKED", result)

    def test_fail_is_diagnostic(self):
        class Failing(unittest.TestCase):
            def test_bad(self):
                self.assertEqual(1, 0)
        code, result = self.case(suite=unittest.defaultTestLoader.loadTestsFromTestCase(Failing))
        self.assertEqual(code, 1)
        self.assertIn("R1_VALIDATION=FAIL_FOCUSED_TESTS", result)

    def test_all_skipped_cannot_pass(self):
        class Skipped(unittest.TestCase):
            @unittest.skip("synthetic")
            def test_skip(self):
                pass
        code, result = self.case(suite=unittest.defaultTestLoader.loadTestsFromTestCase(Skipped))
        self.assertEqual(code, 1)
        self.assertIn("R1_VALIDATION=FAIL_FOCUSED_TESTS", result)

    def test_duplicate_test_id_is_deduplicated(self):
        class Case(unittest.TestCase):
            def test_ok(self):
                self.assertTrue(True)
        case = Case("test_ok")
        code, result = self.case(suite=unittest.TestSuite([case, case]))
        self.assertEqual(code, 0)
        self.assertIn("R1_TEST_CASES_DISCOVERED=2", result)
        self.assertIn("R1_TEST_CASES_UNIQUE=1", result)


class CheckoutIntegrityTests(unittest.TestCase):
    @staticmethod
    def git(root, *args):
        subprocess.run(("git", "-C", str(root), *args), check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def repository(self, root):
        self.git(root, "init", "-q", "-b", "model-v2/expected-return-challenger")
        (root / "contract.txt").write_text("initial", encoding="utf-8")
        self.git(root, "add", "contract.txt")
        self.git(root, "-c", "user.name=PAM Test", "-c", "user.email=pam-test@example.invalid",
                 "-c", "commit.gpgsign=false", "commit", "-q", "-m", "initial")
        self.git(root, "update-ref", "refs/remotes/origin/model-v2/expected-return-challenger", "HEAD")

    def test_checkout_requires_git(self):
        with TemporaryDirectory() as td:
            self.assertEqual(_checkout(Path(td))[0], "CHECKOUT_GIT_UNAVAILABLE")

    def test_checkout_accepts_clean_v2_local_head_only(self):
        with TemporaryDirectory() as td:
            root = Path(td)
            self.repository(root)
            reason, sha = _checkout(root)
            self.assertIsNone(reason)
            self.assertEqual(len(sha), 40)

    def test_dirty_checkout_refused(self):
        with TemporaryDirectory() as td:
            root = Path(td)
            self.repository(root)
            (root / "contract.txt").write_text("altered", encoding="utf-8")
            self.assertEqual(_checkout(root)[0], "CHECKOUT_HAS_CHANGES")

    def test_stale_local_tracking_ref_refused(self):
        with TemporaryDirectory() as td:
            root = Path(td)
            self.repository(root)
            (root / "contract.txt").write_text("second commit", encoding="utf-8")
            self.git(root, "add", "contract.txt")
            self.git(root, "-c", "user.name=PAM Test", "-c", "user.email=pam-test@example.invalid",
                     "-c", "commit.gpgsign=false", "commit", "-q", "-m", "second")
            self.assertEqual(_checkout(root)[0], "CHECKOUT_HEAD_DIFFERS_FROM_LOCAL_V2_TRACKING_REF")


class CandidateCheckoutTests(CheckoutIntegrityTests):
    """Candidate-mode Git evidence is local only; PR identity is human-checked."""

    def candidate(self, root):
        self.repository(root)
        base = subprocess.check_output(
            ("git", "-C", str(root), "rev-parse", "HEAD"), text=True).strip()
        self.git(root, "checkout", "-q", "-b", "pm/r1-candidate-check")
        (root / "contract.txt").write_text("candidate", encoding="utf-8")
        self.git(root, "add", "contract.txt")
        self.git(root, "-c", "user.name=PAM Test",
                 "-c", "user.email=pam-test@example.invalid",
                 "-c", "commit.gpgsign=false", "commit", "-q", "-m", "candidate")
        head = subprocess.check_output(
            ("git", "-C", str(root), "rev-parse", "HEAD"), text=True).strip()
        return base, head

    def test_clean_candidate_with_explicit_sha_and_trusted_base(self):
        with TemporaryDirectory() as td:
            root = Path(td)
            base, head = self.candidate(root)
            self.assertEqual(_checkout(root, candidate_head=head, base_sha=base),
                             (None, head))
            self.assertEqual(_checkout(root)[0], "CHECKOUT_NOT_V2_BRANCH")

    def test_wrong_candidate_sha_rejected(self):
        with TemporaryDirectory() as td:
            root = Path(td)
            base, head = self.candidate(root)
            self.assertEqual(_checkout(root, candidate_head=base, base_sha=base)[0],
                             "CHECKOUT_CANDIDATE_HEAD_MISMATCH")

    def test_wrong_base_ref_rejected(self):
        with TemporaryDirectory() as td:
            root = Path(td)
            base, head = self.candidate(root)
            self.assertEqual(_checkout(root, candidate_head=head, base_sha=head)[0],
                             "CHECKOUT_CANDIDATE_BASE_MISMATCH")

    def test_candidate_arguments_need_exact_pair(self):
        with TemporaryDirectory() as td:
            root = Path(td)
            base, head = self.candidate(root)
            self.assertEqual(_checkout(root, candidate_head=head)[0],
                             "CHECKOUT_CANDIDATE_SHAS_REQUIRED")
            self.assertEqual(_checkout(root, candidate_head="FAKE", base_sha=base)[0],
                             "CHECKOUT_CANDIDATE_SHAS_REQUIRED")

    def test_unrelated_branch_name_rejected_even_with_commit(self):
        with TemporaryDirectory() as td:
            root = Path(td)
            base, head = self.candidate(root)
            self.git(root, "branch", "-m", "feature/untrusted")
            self.assertEqual(_checkout(root, candidate_head=head, base_sha=base)[0],
                             "CHECKOUT_NOT_PR_CANDIDATE_BRANCH")

    def test_candidate_not_descending_from_v2_base_rejected(self):
        with TemporaryDirectory() as td:
            root = Path(td)
            base, _ = self.candidate(root)
            self.git(root, "checkout", "-q", "--orphan", "pm/unrelated")
            self.git(root, "rm", "-q", "-rf", "--", ".")
            (root / "contract.txt").write_text("independent", encoding="utf-8")
            self.git(root, "add", "contract.txt")
            self.git(root, "-c", "user.name=PAM Test",
                     "-c", "user.email=pam-test@example.invalid",
                     "-c", "commit.gpgsign=false", "commit", "-q", "-m", "independent")
            independent = subprocess.check_output(
                ("git", "-C", str(root), "rev-parse", "HEAD"), text=True).strip()
            self.assertEqual(
                _checkout(root, candidate_head=independent, base_sha=base)[0],
                "CHECKOUT_CANDIDATE_NOT_BASE_DESCENDANT")

    def test_validate_marks_candidate_and_reports_base_without_acceptance(self):
        with TemporaryDirectory() as td:
            root = Path(td)
            self.candidate(root)
            (root / "tests").mkdir()
            (root / "tests" / "test_ai_native_synthetic.py").write_text(
                "# fixture", encoding="utf-8")
            class Passing(unittest.TestCase):
                def test_ok(self):
                    self.assertTrue(True)
            out = StringIO()
            observed = {}
            def candidate_check(path, **kwargs):
                observed.update(kwargs)
                return (None, kwargs["candidate_head"])
            candidate = "a" * 40
            base = "b" * 40
            code = validate(
                root, out=out, checker=lambda _: None,
                checkout_checker=candidate_check, candidate_head=candidate,
                base_sha=base,
                discoverer=lambda _: unittest.defaultTestLoader.loadTestsFromTestCase(Passing),
                required=frozenset(), minimum_modules=1, minimum_cases=1)
            self.assertEqual(code, 0)
            self.assertEqual(observed, {"candidate_head": candidate, "base_sha": base})
            self.assertIn("R1_CHECKOUT_MODE=PR_CANDIDATE", out.getvalue())
            self.assertIn("R1_CANDIDATE_BASE_SHA=" + base, out.getvalue())
            self.assertIn("R1_SCOPE=SYNTHETIC_REGRESSION_ONLY_NOT_ACCEPTANCE",
                          out.getvalue())
