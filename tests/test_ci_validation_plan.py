import unittest

from scripts.ci_validation_plan import ValidationTier, plan_validation


class CIValidationPlanTests(unittest.TestCase):
    def assert_tier(self, paths, expected):
        self.assertEqual(plan_validation(paths).tier, expected)

    def test_reviewed_examples(self):
        cases = (
            (["README.md"], ValidationTier.DOCS_ONLY),
            (["PAM_ROADMAP.md", "DECISIONS.md"], ValidationTier.DOCS_ONLY),
            (["economic_facts/new_fact.py"], ValidationTier.STANDARD),
            (
                ["economic_facts/new_fact.py", "tests/test_new_fact.py"],
                ValidationTier.STANDARD,
            ),
            (["src/expected_return_engine.py"], ValidationTier.FULL_PIT),
            (["main.py"], ValidationTier.FULL_PIT),
            (["pit_comparison/runner.py"], ValidationTier.FULL_PIT),
            (["tests/test_pit_adapter_equivalence.py"], ValidationTier.FULL_PIT),
            (["requirements.lock"], ValidationTier.FULL_PIT),
            ([".github/workflows/ci.yml"], ValidationTier.FULL_PIT),
            (["scripts/ci_validation_plan.py"], ValidationTier.FULL_PIT),
            (["unknown/new_engine.py"], ValidationTier.FULL_PIT),
            (["README.md", "economic_facts/new_fact.py"], ValidationTier.STANDARD),
            (["economic_facts/new_fact.py", "src/scoring.py"], ValidationTier.FULL_PIT),
            ([], ValidationTier.FULL_PIT),
        )
        for paths, expected in cases:
            with self.subTest(paths=paths):
                self.assert_tier(paths, expected)

    def test_ordinary_fixture_module_is_standard(self):
        self.assert_tier(
            ["tests/sec_new_source_fixtures.py"], ValidationTier.STANDARD
        )

    def test_analysis_capabilities_reviewed_surface_is_standard(self):
        cases = (
            (["analysis_capabilities/contracts.py"], ValidationTier.STANDARD),
            (
                [
                    "analysis_capabilities/new_contract.py",
                    "tests/test_new_contract.py",
                ],
                ValidationTier.STANDARD,
            ),
            (
                [
                    "analysis_capabilities/contracts.py",
                    "docs/contracts/v2/capabilities/CAPABILITY_CONTRACT_FOUNDATION.md",
                ],
                ValidationTier.STANDARD,
            ),
            (
                [
                    "analysis_capabilities/contracts.py",
                    "economic_facts/new_fact.py",
                ],
                ValidationTier.STANDARD,
            ),
            (
                ["analysis_capabilities/contracts.py", "src/scoring.py"],
                ValidationTier.FULL_PIT,
            ),
            (
                ["analysis_capabilities/contracts.py", "pit_comparison/runner.py"],
                ValidationTier.FULL_PIT,
            ),
            (
                ["analysis_capabilities/contracts.py", "requirements.lock"],
                ValidationTier.FULL_PIT,
            ),
            (["analysis_capability/contracts.py"], ValidationTier.FULL_PIT),
            (["analysis_capabilities_extra/contracts.py"], ValidationTier.FULL_PIT),
        )
        for paths, expected in cases:
            with self.subTest(paths=paths):
                self.assert_tier(paths, expected)

    def test_unknown_or_ambiguous_paths_fail_to_full_pit(self):
        for path in (
            "new_package/engine.py",
            ".github/workflows/other.yml",
            "scripts/new_ci_helper.py",
            "config/new_rule.yaml",
            "../outside.py",
            "bad\npath.py",
        ):
            with self.subTest(path=path):
                self.assert_tier([path], ValidationTier.FULL_PIT)

    def test_rename_input_keeps_sensitive_source_visible(self):
        # `git diff --no-renames --name-only` supplies both paths for a rename.
        self.assert_tier(
            ["src/old_engine.py", "docs/old_engine.md"],
            ValidationTier.FULL_PIT,
        )

    def test_changed_files_are_deduplicated_and_sorted(self):
        plan = plan_validation(["z.md", "a.md", "z.md"])
        self.assertEqual(plan.changed_files, ("a.md", "z.md"))
        self.assertFalse(plan.heavy_pit_required)


if __name__ == "__main__":
    unittest.main()
