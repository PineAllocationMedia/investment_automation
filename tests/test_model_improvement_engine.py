import tempfile
import unittest
from datetime import date
from pathlib import Path

from src.mode_artifacts import mode_artifact_path
from src.model_improvement_engine import apply_safe_tuning, build_improvement_summary, build_improvement_suggestions
from src.model_tuning import create_model_tuning_template, load_model_tuning, tuning_value
from src.utils import write_csv_records


def fake_audit(**overrides):
    metrics = {
        "allocation_sample_count": 6,
        "confidence": "SOLID",
        "avg_vfv": 0.36,
        "avg_core": 0.55,
        "avg_allocation_turnover": 0.10,
        "primary_change_rate": 0.10,
        "avg_max_single": 0.30,
        "high_cycle_day_rate": 0.10,
        "extreme_cycle_day_rate": 0.0,
        "low_data_day_rate": 0.0,
        "avg_decision_quality": 75,
    }
    metrics.update(overrides)
    return {"metrics": metrics}


class ModelImprovementEngineTest(unittest.TestCase):
    def test_insufficient_history_never_auto_applies(self):
        suggestions = build_improvement_suggestions(
            fake_audit(allocation_sample_count=1),
            {"safe_auto_apply": {"min_distinct_allocation_dates": 4}},
            [],
            "high-cagr",
        )

        self.assertTrue(any(row["status"] == "WAIT_FOR_MORE_HISTORY" for row in suggestions))
        self.assertFalse(any(row["can_auto_apply"] for row in suggestions))

    def test_too_defensive_high_cagr_creates_safe_vfv_adjustment(self):
        suggestions = build_improvement_suggestions(
            fake_audit(avg_vfv=0.36, avg_core=0.50),
            {"safe_auto_apply": {"min_distinct_allocation_dates": 4}},
            [],
            "high-cagr",
        )
        vfv = [row for row in suggestions if row["parameter"] == "vfv_adjustment"]

        self.assertEqual(vfv[0]["safety_level"], "SAFE")
        self.assertTrue(vfv[0]["can_auto_apply"])
        self.assertLess(vfv[0]["suggested_delta"], 0)

    def test_underperformance_governor_can_block_safe_auto_apply(self):
        suggestions = build_improvement_suggestions(
            fake_audit(avg_vfv=0.36, avg_core=0.50),
            {"safe_auto_apply": {"min_distinct_allocation_dates": 4}},
            [],
            "high-cagr",
            {
                "status": "INSUFFICIENT_EVIDENCE",
                "correction_governor": "OBSERVE_ONLY",
                "can_auto_apply_safe_tuning": False,
                "max_safe_changes_allowed": 0,
                "preferred_excess_vs_sp500": -0.06,
                "process_issue_count": 1,
                "interpretation": "Historique trop court.",
                "recommended_posture": "Observer.",
                "rows": [],
            },
        )
        vfv = [row for row in suggestions if row["parameter"] == "vfv_adjustment"]

        self.assertEqual(vfv[0]["safety_level"], "SAFE")
        self.assertFalse(vfv[0]["can_auto_apply"])

    def test_source_health_block_disables_auto_apply_without_removing_suggestion(self):
        suggestions = build_improvement_suggestions(
            fake_audit(avg_vfv=0.36, avg_core=0.50),
            {"safe_auto_apply": {"min_distinct_allocation_dates": 4}},
            [],
            "high-cagr",
            source_health_context={
                "source_health_status": "CRITICAL_BLOCK",
                "source_health_score": 35,
                "source_health_weakest_source": "Yahoo/yfinance market data",
                "source_health_auto_tuning_gate": "BLOCK",
                "source_health_interpretation": "Source centrale critique.",
            },
        )
        vfv = [row for row in suggestions if row["parameter"] == "vfv_adjustment"]
        source = [row for row in suggestions if row["parameter"] == "source_health"]

        self.assertEqual(vfv[0]["safety_level"], "SAFE")
        self.assertFalse(vfv[0]["can_auto_apply"])
        self.assertEqual(source[0]["status"], "CRITICAL_BLOCK")

    def test_ticker_source_quality_is_info_only_in_improvement_audit(self):
        suggestions = build_improvement_suggestions(
            fake_audit(avg_vfv=0.36, avg_core=0.50),
            {"safe_auto_apply": {"min_distinct_allocation_dates": 4}},
            [],
            "high-cagr",
            ticker_source_context={
                "ticker_source_quality_status": "REVIEW",
                "ticker_source_quality_score": 64,
                "ticker_source_review_tickers": "MSFT",
                "ticker_source_interpretation": "Validation prioritaire.",
            },
        )
        ticker_quality = [row for row in suggestions if row["parameter"] == "ticker_source_quality"]
        vfv = [row for row in suggestions if row["parameter"] == "vfv_adjustment"]

        self.assertEqual(ticker_quality[0]["safety_level"], "INFO")
        self.assertFalse(ticker_quality[0]["can_auto_apply"])
        self.assertTrue(vfv[0]["can_auto_apply"])

    def test_proxy_bias_safe_signal_can_create_proxy_correction_suggestion(self):
        suggestions = build_improvement_suggestions(
            fake_audit(allocation_sample_count=6, avg_vfv=0.10, avg_core=0.80),
            {"safe_auto_apply": {"min_distinct_allocation_dates": 4}},
            [],
            "high-cagr",
            proxy_bias_rows=[
                {
                    "field": "roic_5y_avg",
                    "status": "BIAS_CANDIDATE_SAFE_SIGNAL",
                    "confidence": "HIGH",
                    "usable_sample_count": 8,
                    "sample_count": 8,
                    "suggested_factor": 1.12,
                    "mean_error_pct": -10.7,
                    "std_error_pct": 3.2,
                    "proxy_direction": "PROXY_TOO_LOW",
                }
            ],
        )

        proxy = [row for row in suggestions if row["parameter"] == "proxy_correction:roic_5y_avg"]

        self.assertEqual(proxy[0]["safety_level"], "SAFE")
        self.assertTrue(proxy[0]["can_auto_apply"])
        self.assertEqual(proxy[0]["status"], "PENDING_SAFE_APPLY")
        self.assertEqual(proxy[0]["proxy_correction_factor"], 1.12)

    def test_proxy_correction_audit_review_is_not_auto_applied(self):
        suggestions = build_improvement_suggestions(
            fake_audit(allocation_sample_count=6, avg_vfv=0.10, avg_core=0.80),
            {"safe_auto_apply": {"min_distinct_allocation_dates": 4}},
            [],
            "high-cagr",
            proxy_correction_audit_rows=[
                {
                    "field": "roic_5y_avg",
                    "status": "REVIEW_CONFLICTING_EVIDENCE",
                    "risk_level": "HIGH",
                    "factor": 1.12,
                    "confidence": "HIGH",
                    "sample_count": 8,
                    "bias_status": "BIAS_CANDIDATE_SAFE_SIGNAL",
                    "current_suggested_factor": 0.92,
                    "reason": "Signal opposé.",
                    "recommended_action": "Revue manuelle.",
                }
            ],
        )

        review = [row for row in suggestions if row["parameter"] == "proxy_correction_review"]

        self.assertEqual(review[0]["safety_level"], "MODERATE")
        self.assertFalse(review[0]["can_auto_apply"])
        self.assertEqual(review[0]["status"], "REVIEW_CONFLICTING_EVIDENCE")

    def test_improvement_summary_uses_underperformance_governor(self):
        suggestions = [
            {
                "safety_level": "SAFE",
                "can_auto_apply": True,
            }
        ]
        summary = build_improvement_summary(
            fake_audit(),
            suggestions,
            "12m",
            "high-cagr",
            {
                "status": "PROCESS_WARNING",
                "correction_governor": "THROTTLE_SAFE_TUNING",
                "can_auto_apply_safe_tuning": True,
                "max_safe_changes_allowed": 1,
            },
        )

        self.assertEqual(summary["status"], "READY_FOR_SAFE_TUNING")
        self.assertEqual(summary["correction_governor"], "THROTTLE_SAFE_TUNING")
        self.assertEqual(summary["max_safe_changes_allowed"], 1)

    def test_improvement_summary_uses_source_health_gate(self):
        summary = build_improvement_summary(
            fake_audit(),
            [{"safety_level": "SAFE", "can_auto_apply": True}],
            "12m",
            "high-cagr",
            source_health_context={
                "source_health_status": "CRITICAL_BLOCK",
                "source_health_score": 35,
                "source_health_weakest_source": "Yahoo/yfinance market data",
                "source_health_auto_tuning_gate": "BLOCK",
                "source_health_interpretation": "Source centrale critique.",
            },
        )

        self.assertEqual(summary["status"], "OBSERVE_ONLY")
        self.assertEqual(summary["source_health_auto_tuning_gate"], "BLOCK")

    def test_improvement_summary_reports_walk_forward_context(self):
        summary = build_improvement_summary(
            fake_audit(),
            [{"safety_level": "SAFE", "can_auto_apply": True, "overfit_gate_status": "PASS"}],
            "12m",
            "high-cagr",
            anti_overfitting_context={
                "walk_forward_status": "PASS",
                "walk_forward_simulated_periods": 6,
                "walk_forward_usable_periods": 6,
            },
        )

        self.assertEqual(summary["walk_forward_status"], "PASS")
        self.assertEqual(summary["walk_forward_simulated_periods"], 6)

    def test_apply_safe_tuning_ignores_moderate_and_applies_safe(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            reports = root / "reports"
            config = root / "config"
            data = root / "data"
            reports.mkdir()
            config.mkdir()
            data.mkdir()
            create_model_tuning_template(config / "model_tuning.yaml")
            write_csv_records(
                mode_artifact_path(reports / "latest_improvement_summary.csv", "high-cagr"),
                [
                    {
                        "date": date.today().isoformat(),
                        "mode": "high-cagr",
                        "period": "12m",
                        "status": "READY_FOR_SAFE_TUNING",
                        "safe_auto_applicable_count": 1,
                        "max_safe_changes_allowed": 3,
                    }
                ],
                ["date", "mode", "period", "status", "safe_auto_applicable_count", "max_safe_changes_allowed"],
            )
            write_csv_records(
                mode_artifact_path(reports / "latest_improvement_suggestions.csv", "high-cagr"),
                [
                    {
                        "suggestion_id": "safe",
                        "mode": "high-cagr",
                        "parameter": "vfv_adjustment",
                        "suggested_delta": -0.03,
                        "safety_level": "SAFE",
                        "can_auto_apply": True,
                        "status": "PENDING_SAFE_APPLY",
                        "overfit_gate_status": "PASS",
                        "reason": "safe test",
                    },
                    {
                        "suggestion_id": "moderate",
                        "mode": "high-cagr",
                        "parameter": "single_stock_cap_adjustment",
                        "suggested_delta": -0.02,
                        "safety_level": "MODERATE",
                        "can_auto_apply": False,
                        "status": "REVIEW_ONLY",
                        "overfit_gate_status": "NOT_APPLICABLE",
                        "reason": "moderate test",
                    },
                ],
                [
                    "suggestion_id",
                    "mode",
                    "parameter",
                    "suggested_delta",
                    "safety_level",
                    "can_auto_apply",
                    "status",
                    "overfit_gate_status",
                    "reason",
                ],
            )

            result = apply_safe_tuning(reports, config, data, mode="high-cagr")
            tuning = load_model_tuning(config / "model_tuning.yaml")

            self.assertEqual(len(result["applied"]), 1)
            self.assertEqual(tuning_value("high-cagr", "vfv_adjustment", tuning=tuning), -0.01)
            self.assertEqual(tuning_value("high-cagr", "single_stock_cap_adjustment", tuning=tuning), 0.0)
            self.assertTrue((data / "model_tuning_history.csv").exists())

    def test_apply_safe_tuning_respects_governor_max_changes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            reports = root / "reports"
            config = root / "config"
            data = root / "data"
            reports.mkdir()
            config.mkdir()
            data.mkdir()
            create_model_tuning_template(config / "model_tuning.yaml")
            write_csv_records(
                mode_artifact_path(reports / "latest_improvement_summary.csv", "high-cagr"),
                [
                    {
                        "date": date.today().isoformat(),
                        "mode": "high-cagr",
                        "status": "READY_FOR_SAFE_TUNING",
                        "safe_auto_applicable_count": 2,
                        "max_safe_changes_allowed": 1,
                    }
                ],
                ["date", "mode", "status", "safe_auto_applicable_count", "max_safe_changes_allowed"],
            )
            write_csv_records(
                mode_artifact_path(reports / "latest_improvement_suggestions.csv", "high-cagr"),
                [
                    {
                        "suggestion_id": "safe1",
                        "mode": "high-cagr",
                        "parameter": "vfv_adjustment",
                        "suggested_delta": -0.01,
                        "safety_level": "SAFE",
                        "can_auto_apply": True,
                        "status": "PENDING_SAFE_APPLY",
                        "overfit_gate_status": "PASS",
                        "reason": "safe test 1",
                    },
                    {
                        "suggestion_id": "safe2",
                        "mode": "high-cagr",
                        "parameter": "single_stock_cap_adjustment",
                        "suggested_delta": -0.02,
                        "safety_level": "SAFE",
                        "can_auto_apply": True,
                        "status": "PENDING_SAFE_APPLY",
                        "overfit_gate_status": "PASS",
                        "reason": "safe test 2",
                    },
                ],
                [
                    "suggestion_id",
                    "mode",
                    "parameter",
                    "suggested_delta",
                    "safety_level",
                    "can_auto_apply",
                    "status",
                    "overfit_gate_status",
                    "reason",
                ],
            )

            result = apply_safe_tuning(reports, config, data, mode="high-cagr")

            self.assertEqual(len(result["applied"]), 1)

    def test_apply_safe_tuning_requires_ready_summary_for_same_mode_today(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            reports = root / "reports"
            config = root / "config"
            data = root / "data"
            reports.mkdir()
            config.mkdir()
            data.mkdir()
            create_model_tuning_template(config / "model_tuning.yaml")
            write_csv_records(
                mode_artifact_path(reports / "latest_improvement_summary.csv", "high-cagr"),
                [
                    {
                        "date": "2020-01-01",
                        "mode": "high-cagr",
                        "status": "READY_FOR_SAFE_TUNING",
                        "safe_auto_applicable_count": 1,
                    }
                ],
                ["date", "mode", "status", "safe_auto_applicable_count"],
            )
            write_csv_records(
                mode_artifact_path(reports / "latest_improvement_suggestions.csv", "high-cagr"),
                [
                    {
                        "suggestion_id": "safe",
                        "mode": "high-cagr",
                        "parameter": "vfv_adjustment",
                        "suggested_delta": -0.01,
                        "safety_level": "SAFE",
                        "can_auto_apply": True,
                        "status": "PENDING_SAFE_APPLY",
                        "overfit_gate_status": "PASS",
                    }
                ],
                [
                    "suggestion_id",
                    "mode",
                    "parameter",
                    "suggested_delta",
                    "safety_level",
                    "can_auto_apply",
                    "status",
                    "overfit_gate_status",
                ],
            )

            result = apply_safe_tuning(reports, config, data, mode="high-cagr")
            tuning = load_model_tuning(config / "model_tuning.yaml")

            self.assertEqual(result["applied"], [])
            self.assertEqual(tuning_value("high-cagr", "vfv_adjustment", tuning=tuning), 0.0)

    def test_apply_safe_tuning_can_activate_proxy_correction_with_history(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            reports = root / "reports"
            config = root / "config"
            data = root / "data"
            reports.mkdir()
            config.mkdir()
            data.mkdir()
            create_model_tuning_template(config / "model_tuning.yaml")
            write_csv_records(
                mode_artifact_path(reports / "latest_improvement_summary.csv", "high-cagr"),
                [
                    {
                        "date": date.today().isoformat(),
                        "mode": "high-cagr",
                        "status": "READY_FOR_SAFE_TUNING",
                        "safe_auto_applicable_count": 1,
                        "max_safe_changes_allowed": 3,
                    }
                ],
                ["date", "mode", "status", "safe_auto_applicable_count", "max_safe_changes_allowed"],
            )
            write_csv_records(
                mode_artifact_path(reports / "latest_improvement_suggestions.csv", "high-cagr"),
                [
                    {
                        "suggestion_id": "proxy-safe",
                        "mode": "high-cagr",
                        "parameter": "proxy_correction:roic_5y_avg",
                        "current_value": 1.0,
                        "suggested_delta": 0.12,
                        "suggested_value": 1.12,
                        "safety_level": "SAFE",
                        "can_auto_apply": True,
                        "status": "PENDING_SAFE_APPLY",
                        "overfit_gate_status": "PASS",
                        "proxy_correction_field": "roic_5y_avg",
                        "proxy_correction_factor": 1.12,
                        "proxy_correction_confidence": "HIGH",
                        "proxy_correction_sample_count": 8,
                        "proxy_correction_mean_error_pct": -10.7,
                        "proxy_correction_std_error_pct": 3.2,
                        "reason": "proxy test",
                    }
                ],
                [
                    "suggestion_id",
                    "mode",
                    "parameter",
                    "current_value",
                    "suggested_delta",
                    "suggested_value",
                    "safety_level",
                    "can_auto_apply",
                    "status",
                    "overfit_gate_status",
                    "proxy_correction_field",
                    "proxy_correction_factor",
                    "proxy_correction_confidence",
                    "proxy_correction_sample_count",
                    "proxy_correction_mean_error_pct",
                    "proxy_correction_std_error_pct",
                    "reason",
                ],
            )

            result = apply_safe_tuning(reports, config, data, mode="high-cagr")
            corrections = (config / "proxy_corrections.yaml").read_text(encoding="utf-8")
            history = (data / "proxy_correction_history.csv").read_text(encoding="utf-8")

            self.assertEqual(len(result["applied"]), 1)
            self.assertIn("enabled: true", corrections)
            self.assertIn("roic_5y_avg", corrections)
            self.assertIn("1.12", corrections)
            self.assertIn("proxy_correction:roic_5y_avg", history)


if __name__ == "__main__":
    unittest.main()
