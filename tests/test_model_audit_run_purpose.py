import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from src.anti_overfitting_gate_engine import build_anti_overfitting_context
from src.full_audit_engine import build_full_audit_metrics
from src.model_audit_engine import build_model_audit
from src.model_improvement_engine import build_improvement_suggestions
from src.utils import save_json
from src.validation_evidence import RunPurpose, VALIDATION_SCHEMA_VERSION
from src.walk_forward_backtest_engine import WalkForwardInventoryConfig, build_walk_forward_inventory


class ModelAuditRunPurposeTest(unittest.TestCase):
    def test_scheduled_decision_counts_in_primary_audit(self):
        with TemporaryDirectory() as folder:
            reports = Path(folder)
            self._write_allocation(reports, "2026-01-01", RunPurpose.SCHEDULED_DECISION.value, "MSFT")
            metrics = self._audit(reports)

        self.assertEqual(metrics["current_version_decision_observation_count"], 1)
        self.assertEqual(metrics["current_version_observation_count"], 1)
        self.assertEqual(metrics["allocation_sample_count"], 1)
        self.assertEqual(metrics["primary_tickers"], ["MSFT"])

    def test_manual_decision_counts_in_primary_audit(self):
        with TemporaryDirectory() as folder:
            reports = Path(folder)
            self._write_allocation(reports, "2026-01-01", RunPurpose.MANUAL_DECISION.value, "AAPL")
            metrics = self._audit(reports)

        self.assertEqual(metrics["current_version_decision_observation_count"], 1)
        self.assertEqual(metrics["allocation_sample_count"], 1)
        self.assertEqual(metrics["primary_tickers"], ["AAPL"])

    def test_diagnostic_is_auditable_but_not_primary(self):
        self._assert_explicit_non_decision(RunPurpose.DIAGNOSTIC.value)

    def test_development_test_is_auditable_but_not_primary(self):
        self._assert_explicit_non_decision(RunPurpose.DEVELOPMENT_TEST.value)

    def test_zero_capital_analysis_is_auditable_but_not_primary(self):
        self._assert_explicit_non_decision(RunPurpose.ZERO_CAPITAL_ANALYSIS.value)

    def test_maintenance_is_auditable_but_not_primary(self):
        self._assert_explicit_non_decision(RunPurpose.MAINTENANCE.value)

    def test_unknown_legacy_is_visible_but_not_primary(self):
        with TemporaryDirectory() as folder:
            reports = Path(folder)
            self._write_allocation(reports, "2026-01-01", None, "MSFT")
            metrics = self._audit(reports)

        self.assertEqual(metrics["total_history_observation_count"], 1)
        self.assertEqual(metrics["current_version_total_observation_count"], 1)
        self.assertEqual(metrics["current_version_unknown_purpose_observation_count"], 1)
        self.assertEqual(metrics["current_version_non_decision_observation_count"], 0)
        self.assertEqual(metrics["current_version_decision_observation_count"], 0)
        self.assertEqual(metrics["allocation_sample_count"], 0)

    def test_later_same_day_diagnostic_cannot_replace_scheduled_decision(self):
        with TemporaryDirectory() as folder:
            reports = Path(folder)
            self._write_allocation(
                reports,
                "2026-01-01",
                RunPurpose.SCHEDULED_DECISION.value,
                "MSFT",
                clock="090000",
            )
            self._write_allocation(
                reports,
                "2026-01-01",
                RunPurpose.DIAGNOSTIC.value,
                "AAPL",
                clock="180000",
            )
            metrics = self._audit(reports)

        self.assertEqual(metrics["total_history_observation_count"], 2)
        self.assertEqual(metrics["current_version_decision_observation_count"], 1)
        self.assertEqual(metrics["current_version_non_decision_observation_count"], 1)
        self.assertEqual(metrics["primary_tickers"], ["MSFT"])

    def test_turnover_and_stability_compare_only_genuine_decisions(self):
        with TemporaryDirectory() as folder:
            reports = Path(folder)
            self._write_allocation(reports, "2026-01-01", RunPurpose.SCHEDULED_DECISION.value, "MSFT")
            self._write_allocation(reports, "2026-01-05", RunPurpose.DIAGNOSTIC.value, "MSFT")
            self._write_allocation(reports, "2026-01-10", RunPurpose.DEVELOPMENT_TEST.value, "GOOGL")
            self._write_allocation(reports, "2026-01-15", RunPurpose.MAINTENANCE.value, "NVDA")
            self._write_allocation(reports, "2026-02-01", RunPurpose.SCHEDULED_DECISION.value, "AAPL")
            metrics = self._audit(reports)

        self.assertEqual(metrics["allocation_sample_count"], 2)
        self.assertEqual(metrics["primary_tickers"], ["MSFT", "AAPL"])
        self.assertEqual(metrics["primary_changes"], 1)
        self.assertEqual(metrics["primary_change_rate"], 1.0)
        self.assertEqual(metrics["avg_allocation_turnover"], 1.0)

    def test_many_diagnostics_and_one_decision_do_not_raise_maturity_or_confidence(self):
        with TemporaryDirectory() as folder:
            reports = Path(folder)
            self._write_allocation(reports, "2026-01-01", RunPurpose.SCHEDULED_DECISION.value, "MSFT")
            for index in range(2, 10):
                self._write_allocation(
                    reports,
                    f"2026-01-{index:02d}",
                    RunPurpose.DIAGNOSTIC.value,
                    "AAPL",
                )
            metrics = self._audit(reports)

        self.assertEqual(metrics["current_version_total_observation_count"], 9)
        self.assertEqual(metrics["current_version_decision_observation_count"], 1)
        self.assertEqual(metrics["current_version_non_decision_observation_count"], 8)
        self.assertEqual(metrics["evidence_maturity"], "INSUFFICIENT")
        self.assertEqual(metrics["confidence"], "VERY_LIMITED")
        self.assertEqual(metrics["health_status"], "DATA_TOO_SHORT")

    def test_old_version_decisions_remain_cross_version_diagnostic_only(self):
        with TemporaryDirectory() as folder:
            reports = Path(folder)
            self._write_allocation(
                reports,
                "2026-01-01",
                RunPurpose.SCHEDULED_DECISION.value,
                "AAPL",
                version="v1",
            )
            self._write_allocation(
                reports,
                "2026-02-01",
                RunPurpose.SCHEDULED_DECISION.value,
                "MSFT",
                version="v2",
            )
            metrics = self._audit(reports)

        self.assertEqual(metrics["current_version_decision_observation_count"], 1)
        self.assertEqual(metrics["cross_version_observation_count"], 1)
        self.assertEqual(metrics["cross_version_decision_observation_count"], 1)
        self.assertEqual(metrics["primary_tickers"], ["MSFT"])
        self.assertFalse(metrics["cross_version_diagnostic"]["ordinary_instability_counted"])

    def test_diagnostics_across_version_boundary_do_not_create_transition_instability(self):
        with TemporaryDirectory() as folder:
            reports = Path(folder)
            self._write_allocation(
                reports,
                "2026-01-01",
                RunPurpose.SCHEDULED_DECISION.value,
                "MSFT",
                version="v1",
            )
            self._write_allocation(
                reports,
                "2026-01-02",
                RunPurpose.DIAGNOSTIC.value,
                "AAPL",
                version="v2",
            )
            self._write_allocation(
                reports,
                "2026-01-03",
                RunPurpose.DEVELOPMENT_TEST.value,
                "GOOGL",
                version="v3",
            )
            self._write_allocation(
                reports,
                "2026-01-04",
                RunPurpose.SCHEDULED_DECISION.value,
                "MSFT",
                version="v1",
            )
            metrics = self._audit(reports, current_version="v1")

        self.assertEqual(metrics["version_transition_count"], 0)
        self.assertEqual(metrics["cross_version_decision_observation_count"], 0)
        self.assertEqual(metrics["cross_version_observation_count"], 2)
        self.assertEqual(metrics["cross_version_diagnostic"]["decision_observation_count"], 2)

    def test_full_audit_prefers_explicit_current_version_decision_count(self):
        metrics = build_full_audit_metrics(
            model_audit={
                "metrics": {
                    "health_status": "DATA_TOO_SHORT",
                    "health_score": 40,
                    "confidence": "VERY_LIMITED",
                    "sample_count": 1,
                    "allocation_sample_count": 1,
                    "span_days": 0,
                    "current_model_rules_version": "v2",
                    "current_version_decision_observation_count": 1,
                    "current_version_observation_count": 99,
                }
            },
            backtest_result={"summaries": []},
            backtest_error="",
            walk_forward_result={"summary": {}, "period_rows": []},
            walk_forward_error="",
            account_performance_rows=[],
            contribution_estimate={"confidence": "LOW", "monthly_capital": 500},
            selected_monthly_capital=500,
            period="all",
            years=[5],
            mode="high-cagr",
        )

        self.assertEqual(metrics["current_version_observation_count"], 1)
        self.assertEqual(metrics["current_version_decision_observation_count"], 1)
        self.assertEqual(metrics["current_version_evidence_maturity"], "INSUFFICIENT")
        self.assertEqual(metrics["validation_schema_version"], VALIDATION_SCHEMA_VERSION)

    def test_model_improvement_enough_history_cannot_be_satisfied_by_diagnostics(self):
        with TemporaryDirectory() as folder:
            reports = Path(folder)
            self._write_allocation(reports, "2026-01-01", RunPurpose.SCHEDULED_DECISION.value, "MSFT")
            for index in range(2, 8):
                self._write_allocation(
                    reports,
                    f"2026-01-{index:02d}",
                    RunPurpose.DIAGNOSTIC.value,
                    "AAPL",
                )
            audit = build_model_audit(
                reports,
                period="all",
                mode="high-cagr",
                current_model_rules_version="v2",
            )

        suggestions = build_improvement_suggestions(
            audit,
            {"safe_auto_apply": {"enabled": True, "min_distinct_allocation_dates": 4}},
            [],
            "high-cagr",
        )
        context = build_anti_overfitting_context(model_metrics=audit["metrics"])

        self.assertEqual(audit["metrics"]["allocation_sample_count"], 1)
        self.assertTrue(any(row["status"] == "WAIT_FOR_MORE_HISTORY" for row in suggestions))
        self.assertFalse(any(row["can_auto_apply"] for row in suggestions))
        self.assertEqual(context["sample_count"], 1)
        self.assertEqual(context["current_version_observations"], 1)
        self.assertEqual(context["current_version_decision_observations"], 1)

    def test_existing_walk_forward_run_purpose_timeline_is_unchanged(self):
        with TemporaryDirectory() as folder:
            reports = Path(folder)
            self._write_pair(reports, "2026-01-01", RunPurpose.SCHEDULED_DECISION.value, "MSFT")
            self._write_pair(reports, "2026-01-05", RunPurpose.DIAGNOSTIC.value, "AAPL")
            self._write_pair(reports, "2026-01-20", RunPurpose.SCHEDULED_DECISION.value, "MSFT")
            rows = build_walk_forward_inventory(
                reports,
                WalkForwardInventoryConfig(mode="high-cagr", min_days_between_points=14),
            )

        by_date = {row["analysis_date"]: row for row in rows}
        self.assertEqual(by_date["2026-01-01"]["next_analysis_date"], "2026-01-20")
        self.assertTrue(by_date["2026-01-01"]["usable_for_walk_forward"])
        self.assertFalse(by_date["2026-01-05"]["primary_timeline_eligible"])

    def _assert_explicit_non_decision(self, run_purpose: str) -> None:
        with TemporaryDirectory() as folder:
            reports = Path(folder)
            self._write_allocation(reports, "2026-01-01", run_purpose, "MSFT")
            metrics = self._audit(reports)

        self.assertEqual(metrics["total_history_observation_count"], 1)
        self.assertEqual(metrics["current_version_total_observation_count"], 1)
        self.assertEqual(metrics["current_version_non_decision_observation_count"], 1)
        self.assertEqual(metrics["current_version_unknown_purpose_observation_count"], 0)
        self.assertEqual(metrics["current_version_decision_observation_count"], 0)
        self.assertEqual(metrics["allocation_sample_count"], 0)

    @staticmethod
    def _audit(reports: Path, *, current_version: str = "v2") -> dict:
        return build_model_audit(
            reports,
            period="all",
            mode="high-cagr",
            current_model_rules_version=current_version,
        )["metrics"]

    @staticmethod
    def _write_allocation(
        reports: Path,
        day: str,
        run_purpose: str | None,
        ticker: str,
        *,
        version: str = "v2",
        clock: str = "090000",
    ) -> None:
        history = reports / "history"
        history.mkdir(parents=True, exist_ok=True)
        payload = {
            "analysis_date": day,
            "created_at": f"{day}T{clock[:2]}:{clock[2:4]}:00",
            "analysis_mode": "high-cagr",
            "model_rules_version": version,
            "allocations": [{"ticker": ticker, "amount": 500, "percentage": 1.0}],
        }
        if run_purpose is not None:
            payload["run_purpose"] = run_purpose
        save_json(history / f"allocation_high-cagr_{day.replace('-', '')}_{clock}.json", payload)

    @classmethod
    def _write_pair(cls, reports: Path, day: str, run_purpose: str, ticker: str) -> None:
        cls._write_allocation(reports, day, run_purpose, ticker, clock="090100")
        history = reports / "history"
        save_json(
            history / f"analysis_high-cagr_{day.replace('-', '')}_090000.json",
            {
                "analysis_date": day,
                "created_at": f"{day}T09:00:00",
                "analysis_mode": "high-cagr",
                "model_rules_version": "v2",
                "run_purpose": run_purpose,
                "analyses": [{"ticker": ticker, "universe": "CORE_PORTFOLIO"}],
            },
        )


if __name__ == "__main__":
    unittest.main()
