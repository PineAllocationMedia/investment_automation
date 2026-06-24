import tempfile
import unittest
from datetime import date
from pathlib import Path

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
                reports / "latest_improvement_summary.csv",
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
                reports / "latest_improvement_suggestions.csv",
                [
                    {
                        "suggestion_id": "safe",
                        "mode": "high-cagr",
                        "parameter": "vfv_adjustment",
                        "suggested_delta": -0.03,
                        "safety_level": "SAFE",
                        "can_auto_apply": True,
                        "status": "PENDING_SAFE_APPLY",
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
                reports / "latest_improvement_summary.csv",
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
                reports / "latest_improvement_suggestions.csv",
                [
                    {
                        "suggestion_id": "safe1",
                        "mode": "high-cagr",
                        "parameter": "vfv_adjustment",
                        "suggested_delta": -0.01,
                        "safety_level": "SAFE",
                        "can_auto_apply": True,
                        "status": "PENDING_SAFE_APPLY",
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
                reports / "latest_improvement_summary.csv",
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
                reports / "latest_improvement_suggestions.csv",
                [
                    {
                        "suggestion_id": "safe",
                        "mode": "high-cagr",
                        "parameter": "vfv_adjustment",
                        "suggested_delta": -0.01,
                        "safety_level": "SAFE",
                        "can_auto_apply": True,
                        "status": "PENDING_SAFE_APPLY",
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
                ],
            )

            result = apply_safe_tuning(reports, config, data, mode="high-cagr")
            tuning = load_model_tuning(config / "model_tuning.yaml")

            self.assertEqual(result["applied"], [])
            self.assertEqual(tuning_value("high-cagr", "vfv_adjustment", tuning=tuning), 0.0)


if __name__ == "__main__":
    unittest.main()
