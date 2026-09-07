from tests.identity_fixtures import production_identity
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from src.allocation_change_engine import save_allocation_snapshot
from src.anti_overfitting_gate_engine import build_anti_overfitting_context
from src.full_audit_engine import build_full_audit_metrics
from src.history_engine import save_current_snapshot
from src.model_audit_engine import build_model_audit
from src.utils import load_json, save_json
from src.validation_evidence import (
    AUTO_TUNING_POLICY,
    EVIDENCE_HIERARCHY,
    EvidenceClass,
    RunPurpose,
    evidence_maturity,
    resolve_analysis_run_purpose,
    validation_confidence_dimensions,
)
from src.walk_forward_backtest_engine import WalkForwardInventoryConfig, build_walk_forward_inventory


class ValidationArchitectureTest(unittest.TestCase):
    def test_canonical_evidence_hierarchy_orders_genuine_oos_above_mechanical(self):
        self.assertLess(
            EVIDENCE_HIERARCHY[EvidenceClass.POINT_IN_TIME_WALK_FORWARD.value],
            EVIDENCE_HIERARCHY[EvidenceClass.MECHANICAL_DIAGNOSTIC.value],
        )
        self.assertEqual(AUTO_TUNING_POLICY, "PROPOSAL_ONLY")

    def test_high_data_quality_does_not_create_high_strategy_confidence(self):
        dimensions = validation_confidence_dimensions(
            run_succeeded=True,
            source_health_score=95,
            current_version_observations=20,
            walk_forward_periods=1,
        )

        self.assertEqual(dimensions["data_integrity_confidence"], "HIGH")
        self.assertEqual(dimensions["strategy_validation_confidence"], "INSUFFICIENT")
        self.assertEqual(dimensions["walk_forward_period_count"], 1)

    def test_evidence_maturity_grows_without_claiming_statistical_validation(self):
        self.assertEqual(evidence_maturity(0), "INSUFFICIENT")
        self.assertEqual(evidence_maturity(4), "EARLY")
        self.assertEqual(evidence_maturity(6), "DEVELOPING")
        self.assertEqual(evidence_maturity(12), "SUBSTANTIAL")

    def test_untagged_analysis_fails_toward_transparency(self):
        self.assertEqual(resolve_analysis_run_purpose(None, capital=500), RunPurpose.UNKNOWN_LEGACY.value)
        self.assertEqual(resolve_analysis_run_purpose(None, capital=0), RunPurpose.ZERO_CAPITAL_ANALYSIS.value)
        self.assertEqual(
            resolve_analysis_run_purpose(RunPurpose.MANUAL_DECISION.value, capital=0),
            RunPurpose.MANUAL_DECISION.value,
        )

    def test_future_snapshots_store_run_purpose_additively(self):
        with TemporaryDirectory() as folder:
            reports = Path(folder)
            save_current_snapshot(
                reports,
                "high-cagr",
                {"MSFT": {"ticker": "MSFT", "score_total": 80}},
                run_purpose=RunPurpose.MANUAL_DECISION.value,
            )
            save_allocation_snapshot(
                reports,
                {"allocations": [{"ticker": "MSFT", "amount": 500, "percentage": 1.0}]},
                analysis_mode="high-cagr",
                run_purpose=RunPurpose.MANUAL_DECISION.value,
            )

            analysis = load_json(reports / "latest_analysis_snapshot.json")
            allocation = load_json(reports / "latest_allocation_snapshot.json")

        self.assertEqual(analysis["run_purpose"], RunPurpose.MANUAL_DECISION.value)
        self.assertEqual(allocation["run_purpose"], RunPurpose.MANUAL_DECISION.value)

    def test_diagnostic_runs_do_not_fragment_primary_decision_timeline(self):
        with TemporaryDirectory() as folder:
            reports = Path(folder)
            self._write_pair(reports, "2026-07-15", RunPurpose.SCHEDULED_DECISION.value)
            self._write_pair(reports, "2026-07-16", RunPurpose.DIAGNOSTIC.value)
            self._write_pair(reports, "2026-07-22", RunPurpose.DEVELOPMENT_TEST.value)
            self._write_pair(reports, "2026-07-30", RunPurpose.SCHEDULED_DECISION.value)

            rows = build_walk_forward_inventory(
                reports,
                WalkForwardInventoryConfig(mode="high-cagr", min_days_between_points=14, model_lineage="V1"),
            )

        by_date = {row["analysis_date"]: row for row in rows}
        self.assertEqual(by_date["2026-07-15"]["next_analysis_date"], "2026-07-30")
        self.assertTrue(by_date["2026-07-15"]["usable_for_walk_forward"])
        self.assertFalse(by_date["2026-07-16"]["primary_timeline_eligible"])
        self.assertFalse(by_date["2026-07-22"]["primary_timeline_eligible"])

    def test_zero_capital_analysis_remains_auditable_but_ineligible(self):
        with TemporaryDirectory() as folder:
            reports = Path(folder)
            self._write_pair(reports, "2026-07-01", RunPurpose.ZERO_CAPITAL_ANALYSIS.value)
            rows = build_walk_forward_inventory(reports, WalkForwardInventoryConfig(mode="high-cagr", model_lineage="V1"))

        self.assertEqual(rows[0]["run_purpose"], RunPurpose.ZERO_CAPITAL_ANALYSIS.value)
        self.assertFalse(rows[0]["primary_timeline_eligible"])

    def test_legacy_history_is_preserved_with_explicit_uncertainty_and_causal_spacing(self):
        with TemporaryDirectory() as folder:
            reports = Path(folder)
            for day in ["2026-07-01", "2026-07-02", "2026-07-03", "2026-07-20"]:
                self._write_pair(reports, day, None)
            rows = build_walk_forward_inventory(
                reports,
                WalkForwardInventoryConfig(mode="high-cagr", min_days_between_points=14, model_lineage="V1"),
            )

        eligible = [row for row in rows if row["primary_timeline_eligible"]]
        self.assertEqual([row["analysis_date"] for row in eligible], ["2026-07-01", "2026-07-20"])
        self.assertTrue(all(row["run_purpose"] == RunPurpose.UNKNOWN_LEGACY.value for row in rows))
        self.assertTrue(all(row["run_purpose_status"] == "LEGACY_UNCERTAINTY" for row in rows))

    def test_primary_periods_are_non_overlapping_and_not_double_counted(self):
        with TemporaryDirectory() as folder:
            reports = Path(folder)
            for day in ["2026-06-01", "2026-06-20", "2026-07-10"]:
                self._write_pair(reports, day, RunPurpose.SCHEDULED_DECISION.value)
            rows = build_walk_forward_inventory(
                reports,
                WalkForwardInventoryConfig(mode="high-cagr", min_days_between_points=14, model_lineage="V1"),
            )

        periods = [
            (row["analysis_date"], row["next_analysis_date"])
            for row in rows
            if row["usable_for_walk_forward"]
        ]
        self.assertEqual(periods, [("2026-06-01", "2026-06-20"), ("2026-06-20", "2026-07-10")])
        self.assertEqual(len(periods), len(set(periods)))

    def test_current_version_audit_excludes_old_versions_and_preserves_diagnostic(self):
        with TemporaryDirectory() as folder:
            reports = Path(folder)
            for day, version, ticker in [
                ("2026-01-01", "v1", "AAPL"),
                ("2026-02-01", "v1", "MSFT"),
                ("2026-03-01", "v2", "GOOGL"),
                ("2026-04-01", "v2", "GOOGL"),
            ]:
                self._write_allocation(reports, day, version, ticker)
            audit = build_model_audit(
                reports,
                period="all",
                mode="high-cagr",
                current_model_rules_version="v2",
            current_model_lineage="V1")

        metrics = audit["metrics"]
        self.assertEqual(metrics["current_version_observation_count"], 2)
        self.assertEqual(metrics["cross_version_observation_count"], 2)
        self.assertEqual(metrics["primary_tickers"], ["GOOGL", "GOOGL"])
        self.assertEqual(metrics["version_transition_count"], 1)
        self.assertFalse(metrics["cross_version_diagnostic"]["ordinary_instability_counted"])

    def test_short_current_version_history_does_not_borrow_old_history(self):
        with TemporaryDirectory() as folder:
            reports = Path(folder)
            for index in range(8):
                self._write_allocation(reports, f"2026-{index + 1:02d}-01", "v1", "MSFT")
            self._write_allocation(reports, "2026-09-01", "v2", "GOOGL")
            audit = build_model_audit(
                reports,
                period="all",
                mode="high-cagr",
                current_model_rules_version="v2",
            current_model_lineage="V1")

        self.assertEqual(audit["metrics"]["sample_count"], 1)
        self.assertEqual(audit["metrics"]["confidence"], "VERY_LIMITED")
        self.assertEqual(audit["metrics"]["total_history_observation_count"], 9)

    def test_same_day_version_transition_remains_visible(self):
        with TemporaryDirectory() as folder:
            reports = Path(folder)
            history = reports / "history"
            history.mkdir(parents=True)
            for clock, version, ticker in [("090000", "v1", "MSFT"), ("180000", "v2", "GOOGL")]:
                save_json(
                    history / f"allocation_high-cagr_20260823_{clock}.json",
                    {
                        **production_identity(),
                        "analysis_date": "2026-08-23",
                        "created_at": f"2026-08-23T{clock[:2]}:{clock[2:4]}:00",
                        "analysis_mode": "high-cagr",
                        "model_rules_version": version,
                        "run_purpose": RunPurpose.SCHEDULED_DECISION.value,
                        "allocations": [{"ticker": ticker, "amount": 500, "percentage": 1.0}],
                    },
                )
            audit = build_model_audit(
                reports,
                period="all",
                mode="high-cagr",
                current_model_rules_version="v2",
            current_model_lineage="V1")

        self.assertEqual(audit["metrics"]["total_history_observation_count"], 2)
        self.assertEqual(audit["metrics"]["current_version_observation_count"], 1)
        self.assertEqual(audit["metrics"]["cross_version_observation_count"], 1)

    def test_spectacular_mechanical_backtest_does_not_raise_strategy_confidence(self):
        strong = self._full_audit_metrics(backtest_excess=1_000_000, backtest_drawdown=-0.05)
        weak = self._full_audit_metrics(backtest_excess=-1_000_000, backtest_drawdown=-0.80)

        self.assertFalse(strong["backtest_positive_validation_authority"])
        self.assertEqual(strong["backtest_evidence_class"], EvidenceClass.MECHANICAL_DIAGNOSTIC.value)
        self.assertEqual(strong["strategy_validation_confidence"], weak["strategy_validation_confidence"])
        self.assertGreaterEqual(weak["mechanical_warning_penalty"], strong["mechanical_warning_penalty"])

    def test_mixed_version_walk_forward_cannot_create_tuning_confidence(self):
        context = build_anti_overfitting_context(
            model_metrics={
                **production_identity(), "current_model_lineage": "V1",
                "allocation_sample_count": 8,
                "current_model_rules_version": "v2",
                "current_version_observation_count": 2,
                "cross_version_observation_count": 6,
            },
            walk_forward_summary_rows=[{"status": "READY_FOR_WALK_FORWARD_REVIEW", "simulated_periods": 8}],
            walk_forward_period_rows=[
                {**production_identity(), "model_rules_version": "v1", "evaluation_status": "SIMULATED", "excess_return_vs_vfv": 0.50}
                for _ in range(8)
            ],
        )

        self.assertEqual(context["genuine_oos_periods"], 0)
        self.assertEqual(context["walk_forward_cross_version_period_count"], 8)
        self.assertEqual(context["evidence_maturity"], "INSUFFICIENT")

    @staticmethod
    def _write_pair(reports: Path, day: str, run_purpose: str | None) -> None:
        history = reports / "history"
        history.mkdir(parents=True, exist_ok=True)
        stamp = day.replace("-", "")
        common = {
            **production_identity(), "run_id": stamp, "manifest_fingerprint": stamp,
            "analysis_date": day,
            "created_at": f"{day}T09:00:00",
            "analysis_mode": "high-cagr",
            "model_rules_version": "v2",
        }
        if run_purpose is not None:
            common["run_purpose"] = run_purpose
        save_json(
            history / f"analysis_high-cagr_{stamp}_090000.json",
            {**common, "analyses": [{"ticker": "MSFT", "universe": "CORE_PORTFOLIO"}]},
        )
        save_json(
            history / f"allocation_high-cagr_{stamp}_090100.json",
            {**common, "created_at": f"{day}T09:01:00", "allocations": [{"ticker": "MSFT", "amount": 500, "percentage": 1.0}]},
        )

    @staticmethod
    def _write_allocation(reports: Path, day: str, version: str, ticker: str) -> None:
        history = reports / "history"
        history.mkdir(parents=True, exist_ok=True)
        stamp = day.replace("-", "")
        save_json(
            history / f"allocation_high-cagr_{stamp}_090000.json",
            {
                **production_identity(),
                "analysis_date": day,
                "created_at": f"{day}T09:00:00",
                "analysis_mode": "high-cagr",
                "model_rules_version": version,
                "run_purpose": RunPurpose.SCHEDULED_DECISION.value,
                "allocations": [{"ticker": ticker, "amount": 500, "percentage": 1.0}],
            },
        )

    @staticmethod
    def _full_audit_metrics(*, backtest_excess: float, backtest_drawdown: float) -> dict:
        return build_full_audit_metrics(
            model_audit={
                "metrics": {
                    **production_identity(), "current_model_lineage": "V1",
                    "health_status": "GOOD",
                    "health_score": 75,
                    "confidence": "VERY_LIMITED",
                    "sample_count": 2,
                    "allocation_sample_count": 2,
                    "span_days": 30,
                    "current_model_rules_version": "v2",
                    "current_version_observation_count": 2,
                    "cross_version_observation_count": 10,
                }
            },
            backtest_result={
                "summaries": [
                    {
                        "period_years": 20,
                        "excess_value_vs_vfv": backtest_excess,
                        "max_drawdown_on_capital_multiple": backtest_drawdown,
                        "money_weighted_annual_return": 1.0 if backtest_excess > 0 else -0.5,
                    }
                ]
            },
            backtest_error="",
            walk_forward_result={"summary": {"status": "NO_SIMULATED_PERIODS", "simulated_periods": 0}, "period_rows": []},
            walk_forward_error="",
            account_performance_rows=[],
            contribution_estimate={"confidence": "LOW", "monthly_capital": 500},
            selected_monthly_capital=500,
            period="all",
            years=[20],
            mode="high-cagr",
        )


if __name__ == "__main__":
    unittest.main()
