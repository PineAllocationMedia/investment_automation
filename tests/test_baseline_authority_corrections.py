from unittest.mock import patch
from tests.identity_fixtures import production_identity
import subprocess
import tempfile
import unittest
from pathlib import Path

from src.baseline_identity import (
    VALIDATION_BASELINE_ID,
    baseline_forward_authority,
    baseline_observation_metadata,
)
from src.critical_input_engine import (
    audit_baseline_environment_authority,
    audit_runtime_critical_inputs,
    decision_capable_run,
)
from src.decision_manifest_engine import build_decision_manifest, git_tracked_state
from src.model_audit_engine import build_model_audit
from src.model_version import MODEL_RULES_VERSION
from src.utils import save_json
from src.validation_evidence import (
    EXPLICIT_DECISION_ELIGIBILITY_BASIS,
    LEGACY_PARTIALLY_RECOVERABLE_BASIS,
    evidence_maturity,
    walk_forward_period_has_strategy_validation_authority,
)
from src.walk_forward_backtest_engine import (
    WalkForwardInventoryConfig,
    build_walk_forward_coverage,
    build_walk_forward_inventory,
    build_walk_forward_simulation_summary,
)


class BaselineAuthorityCorrectionTest(unittest.TestCase):
    def setUp(self):
        lineage = patch("src.model_identity.MODEL_LINEAGE", "V1")
        lineage.start()
        self.addCleanup(lineage.stop)

    def test_capital_must_be_finite_numeric_and_strictly_positive(self):
        with tempfile.TemporaryDirectory() as directory:
            config = self._active_config(Path(directory))
            cases = [
                (None, "BASELINE_INVALID_CAPITAL_OBSERVATION"),
                ("", "BASELINE_INVALID_CAPITAL_OBSERVATION"),
                ("invalid", "BASELINE_INVALID_CAPITAL_OBSERVATION"),
                (0, "BASELINE_ZERO_CAPITAL_OBSERVATION"),
                (-1, "BASELINE_NONPOSITIVE_CAPITAL_OBSERVATION"),
            ]
            for capital, expected_status in cases:
                with self.subTest(capital=capital):
                    metadata = baseline_observation_metadata(
                        run_timestamp="2026-08-11T12:00:00",
                        run_purpose="SCHEDULED_DECISION",
                        capital=capital,
                        config_path=config,
                    )
                    self.assertFalse(metadata["baseline_forward_eligible"])
                    self.assertEqual(metadata["baseline_evidence_status"], expected_status)

            valid = baseline_observation_metadata(
                run_timestamp="2026-08-11T12:00:00",
                run_purpose="SCHEDULED_DECISION",
                capital=500,
                config_path=config,
            )
            self.assertTrue(valid["baseline_forward_eligible"])

    def test_pending_prestart_purpose_zero_and_legacy_cases_fail_closed(self):
        base = self._observation()
        cases = [
            ({"baseline_status": "PENDING_APPROVED_DEPLOYMENT", "baseline_started_at": ""}, False),
            ({"run_timestamp": "2026-08-09T12:00:00"}, False),
            ({"run_purpose": "DIAGNOSTIC"}, False),
            ({"run_purpose": "DEVELOPMENT_TEST"}, False),
            ({"run_purpose": "MAINTENANCE"}, False),
            ({"run_purpose": "MANUAL_DECISION", "capital": 0}, False),
            ({"eligibility_basis": LEGACY_PARTIALLY_RECOVERABLE_BASIS}, False),
            ({"run_succeeded": False}, False),
            ({"critical_input_passed": False}, False),
            ({"run_purpose": "MANUAL_DECISION"}, True),
        ]
        for changes, expected in cases:
            with self.subTest(changes=changes):
                result = baseline_forward_authority({**base, **changes})
                self.assertEqual(result["baseline_forward_eligible"], expected)

    def test_zero_capital_is_not_allocation_capable_but_static_runtime_is_auditable(self):
        self.assertFalse(decision_capable_run(capital=0, run_purpose="SCHEDULED_DECISION"))
        self.assertFalse(decision_capable_run(capital=0, run_purpose="MANUAL_DECISION"))
        self.assertTrue(decision_capable_run(capital=1, run_purpose="SCHEDULED_DECISION"))
        self.assertTrue(decision_capable_run(capital=1, run_purpose="MANUAL_DECISION"))
        audit = audit_runtime_critical_inputs(
            portfolio_rows=[],
            market_data={},
            capital=0,
            run_purpose="SCHEDULED_DECISION",
        )
        self.assertFalse(audit["decision_capable"])
        self.assertFalse(audit["hard_failures"])

    def test_dependency_and_git_drift_hard_fail_only_authoritative_candidate(self):
        for field, value, code in [
            ("dependency_status", "DRIFT", "BASELINE_DEPENDENCY_ENVIRONMENT_INVALID"),
            ("dependency_status", "LOCK_MISSING", "BASELINE_DEPENDENCY_ENVIRONMENT_INVALID"),
            ("git_tracked_worktree_clean", False, "BASELINE_TRACKED_GIT_STATE_INVALID"),
        ]:
            with self.subTest(field=field, value=value):
                metadata = baseline_forward_authority({**self._observation(), field: value})
                gate = audit_baseline_environment_authority(metadata)
                self.assertFalse(metadata["baseline_forward_eligible"])
                self.assertIn(code, {row["code"] for row in gate["hard_failures"]})

        diagnostic = baseline_forward_authority(
            {**self._observation(), "run_purpose": "DIAGNOSTIC", "capital": 0, "dependency_status": "DRIFT"}
        )
        self.assertFalse(audit_baseline_environment_authority(diagnostic)["hard_failures"])

    def test_git_tracked_state_clean_dirty_restored_and_untracked_ignored(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(["git", "init", "-q"], cwd=root, check=True)
            subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=root, check=True)
            subprocess.run(["git", "config", "user.name", "Test"], cwd=root, check=True)
            tracked = root / "source.py"
            tracked.write_text("value = 1\n", encoding="utf-8")
            subprocess.run(["git", "add", "source.py"], cwd=root, check=True)
            subprocess.run(["git", "commit", "-qm", "fixture"], cwd=root, check=True)

            clean = git_tracked_state(root)
            (root / "untracked.txt").write_text("operational\n", encoding="utf-8")
            untracked = git_tracked_state(root)
            tracked.write_text("value = 2\n", encoding="utf-8")
            dirty = git_tracked_state(root)
            tracked.write_text("value = 1\n", encoding="utf-8")
            restored = git_tracked_state(root)

        self.assertTrue(clean["git_tracked_worktree_clean"])
        self.assertTrue(untracked["git_tracked_worktree_clean"])
        self.assertFalse(dirty["git_tracked_worktree_clean"])
        self.assertNotEqual(dirty["git_tracked_diff_fingerprint"], clean["git_tracked_diff_fingerprint"])
        self.assertTrue(restored["git_tracked_worktree_clean"])
        self.assertEqual(restored["git_tracked_diff_fingerprint"], clean["git_tracked_diff_fingerprint"])

    def test_model_audit_keeps_two_generic_decisions_but_counts_one_baseline(self):
        with tempfile.TemporaryDirectory() as directory:
            reports = Path(directory)
            self._write_snapshot_pair(reports, "2026-08-09", baseline_eligible=False)
            self._write_snapshot_pair(reports, "2026-08-11", baseline_eligible=True)

            metrics = build_model_audit(
                reports,
                period="all",
                mode="high-cagr",
                current_model_rules_version=MODEL_RULES_VERSION,
            current_model_lineage="V1")["metrics"]

        self.assertEqual(metrics["current_version_decision_observation_count"], 2)
        self.assertEqual(metrics["baseline_forward_observation_count"], 1)
        self.assertEqual(metrics["baseline_evidence_maturity"], evidence_maturity(1))

    def test_non_authoritative_snapshot_cannot_increase_baseline_maturity(self):
        with tempfile.TemporaryDirectory() as directory:
            reports = Path(directory)
            self._write_snapshot_pair(reports, "2026-08-11", baseline_eligible=True)
            self._write_snapshot_pair(reports, "2026-08-12", baseline_eligible=False)
            metrics = build_model_audit(
                reports,
                period="all",
                mode="high-cagr",
                current_model_rules_version=MODEL_RULES_VERSION,
            current_model_lineage="V1")["metrics"]

        self.assertEqual(metrics["current_version_decision_observation_count"], 2)
        self.assertEqual(metrics["baseline_forward_observation_count"], 1)
        self.assertEqual(metrics["baseline_evidence_maturity"], evidence_maturity(1))

    def test_walk_forward_keeps_generic_authority_and_adds_baseline_maturity(self):
        period_rows = [
            self._period("2026-08-09", baseline_eligible=False),
            self._period("2026-08-11", baseline_eligible=True),
        ]
        summary = build_walk_forward_simulation_summary(
            period_rows,
            {"usable_walk_forward_periods": 2},
            WalkForwardInventoryConfig(mode="high-cagr", recommended_min_periods=6, model_lineage="V1"),
            "TEST",
        )

        self.assertTrue(all(walk_forward_period_has_strategy_validation_authority(row) for row in period_rows))
        self.assertEqual(summary["genuine_oos_periods"], 2)
        self.assertEqual(summary["baseline_forward_periods"], 1)
        self.assertEqual(summary["baseline_evidence_maturity"], evidence_maturity(1))

    def test_walk_forward_inventory_propagates_baseline_and_keeps_diagnostics_visible(self):
        with tempfile.TemporaryDirectory() as directory:
            reports = Path(directory)
            self._write_snapshot_pair(reports, "2026-08-09", baseline_eligible=False)
            self._write_snapshot_pair(reports, "2026-08-11", baseline_eligible=True)
            self._write_snapshot_pair(reports, "2026-08-13", baseline_eligible=False, purpose="DIAGNOSTIC")
            inventory = build_walk_forward_inventory(
                reports,
                WalkForwardInventoryConfig(mode="high-cagr", min_days_between_points=1, model_lineage="V1"),
            )
            coverage = build_walk_forward_coverage(
                inventory,
                WalkForwardInventoryConfig(mode="high-cagr", min_days_between_points=1, model_lineage="V1"),
            )

        by_date = {row["analysis_date"]: row for row in inventory}
        self.assertTrue(by_date["2026-08-11"]["baseline_forward_eligible"])
        self.assertFalse(by_date["2026-08-09"]["baseline_forward_eligible"])
        self.assertIn("2026-08-13", by_date)
        self.assertEqual(by_date["2026-08-13"]["run_purpose"], "DIAGNOSTIC")
        self.assertEqual(coverage["baseline_forward_eligible_snapshots"], 1)

    def test_manifest_exposes_tracked_git_state_without_changing_decision_fingerprint(self):
        common = {
            "project_root": Path(__file__).resolve().parents[1],
            "run_id": "run-1",
            "run_timestamp": "2026-08-11T12:00:00",
            "run_purpose": "MANUAL_DECISION",
            "mode": "high-cagr",
            "capital": 500,
            "analyses_by_universe": {},
            "allocation_result": {"allocations": []},
            "research_inputs": {},
            "market_data": {},
            "benchmark_data": {},
            "git_sha": "a" * 40,
            "dependency_payload": {
                "dependency_status": "MATCH",
                "dependency_fingerprint": "dependency",
                "dependency_lock_fingerprint": "lock",
            },
        }
        clean = build_decision_manifest(
            **common,
            git_state_payload={
                "git_tracked_worktree_clean": True,
                "git_tracked_diff_fingerprint": "clean",
                "git_tracked_state_status": "CLEAN",
            },
        )
        dirty = build_decision_manifest(
            **common,
            git_state_payload={
                "git_tracked_worktree_clean": False,
                "git_tracked_diff_fingerprint": "dirty",
                "git_tracked_state_status": "DIRTY",
            },
        )
        self.assertTrue(clean["git_tracked_worktree_clean"])
        self.assertEqual(clean["git_tracked_state_status"], "CLEAN")
        self.assertEqual(clean["decision_output_fingerprint"], dirty["decision_output_fingerprint"])
        self.assertNotEqual(clean["manifest_fingerprint"], dirty["manifest_fingerprint"])

    @staticmethod
    def _active_config(root: Path) -> Path:
        config = root / "baseline.yaml"
        config.write_text(
            "baseline_id: VALIDATION_BASELINE_V1\n"
            "baseline_started_at: '2026-08-10T00:00:00'\n"
            "baseline_status: ACTIVE\n",
            encoding="utf-8",
        )
        return config

    @staticmethod
    def _observation() -> dict:
        return {
            **production_identity(),
            "baseline_id": VALIDATION_BASELINE_ID,
            "baseline_status": "ACTIVE",
            "baseline_started_at": "2026-08-10T00:00:00",
            "run_timestamp": "2026-08-11T12:00:00",
            "run_purpose": "SCHEDULED_DECISION",
            "capital": 500,
            "run_succeeded": True,
            "critical_input_passed": True,
            "approved_config_active": True,
            "dependency_status": "MATCH",
            "git_tracked_worktree_clean": True,
            "eligibility_basis": EXPLICIT_DECISION_ELIGIBILITY_BASIS,
        }

    @classmethod
    def _write_snapshot_pair(
        cls,
        reports: Path,
        analysis_date: str,
        *,
        baseline_eligible: bool,
        purpose: str = "SCHEDULED_DECISION",
    ) -> None:
        history = reports / "history"
        history.mkdir(parents=True, exist_ok=True)
        timestamp = f"{analysis_date}T12:00:00"
        baseline = {
            **cls._observation(),
            "run_timestamp": timestamp,
            "run_purpose": purpose,
            "baseline_forward_eligible": baseline_eligible,
            "baseline_evidence_status": (
                "BASELINE_V1_FORWARD_OBSERVATION" if baseline_eligible else "PRE_BASELINE_OBSERVATION"
            ),
        }
        slug = analysis_date.replace("-", "")
        common = {
            **production_identity(),
            "created_at": timestamp,
            "analysis_date": analysis_date,
            "analysis_mode": "high-cagr",
            "model_rules_version": MODEL_RULES_VERSION,
            "run_purpose": purpose,
            "manifest_reference": f"reports/decision_manifests/{slug}.json",
            "manifest_fingerprint": f"manifest-{slug}",
            "run_id": slug,
            **baseline,
        }
        save_json(
            history / f"analysis_high-cagr_{slug}_120000.json",
            {**common, "analyses": [{"ticker": "MSFT", "universe": "CORE_PORTFOLIO", "score_total": 9.0}]},
        )
        save_json(
            history / f"allocation_high-cagr_{slug}_120000.json",
            {
                **common,
                "allocations": [{"destination": "MSFT", "montant": 500, "pourcentage": 1.0}],
                "decision_quality": {"decision_quality_score": 90},
            },
        )

    @staticmethod
    def _period(analysis_date: str, *, baseline_eligible: bool) -> dict:
        return {
            "evaluation_status": "SIMULATED",
            "run_purpose": "SCHEDULED_DECISION",
            "eligibility_basis": EXPLICIT_DECISION_ELIGIBILITY_BASIS,
            "evidence_class": "POINT_IN_TIME_WALK_FORWARD",
            "strategy_validation_authority": True,
            **production_identity(),
            "baseline_id": VALIDATION_BASELINE_ID,
            "baseline_forward_eligible": baseline_eligible,
            "analysis_date": analysis_date,
            "days_held": 2,
            "strategy_period_return": 0.01,
            "vfv_period_return": 0.005,
            "excess_return_vs_vfv": 0.005,
        }


if __name__ == "__main__":
    unittest.main()
