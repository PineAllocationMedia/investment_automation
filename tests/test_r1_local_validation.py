"""Synthetic, isolated contract checks for the local R1 regression runner."""
from __future__ import annotations
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from scripts.r1_local_validation import validate


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
