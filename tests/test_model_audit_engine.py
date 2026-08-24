import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from src.model_audit_engine import build_model_audit, run_model_audit
from src.utils import save_json


class ModelAuditEngineTest(unittest.TestCase):
    def test_model_audit_collapses_same_day_snapshots(self):
        with TemporaryDirectory() as folder:
            reports = Path(folder)
            history = reports / "history"
            history.mkdir()
            save_json(
                history / "allocation_20260501_090000.json",
                {
                    "analysis_date": "2026-05-01",
                    "created_at": "2026-05-01T09:00:00",
                    "model_rules_version": "v1",
                    "allocations": [
                        {"ticker": "VFV.TO", "amount": 50, "percentage": 0.10},
                        {"ticker": "MSFT", "amount": 450, "percentage": 0.90},
                    ],
                    "decision_quality": {"decision_quality_score": 82, "decision_quality_level": "HIGH"},
                },
            )
            save_json(
                history / "allocation_20260501_180000.json",
                {
                    "analysis_date": "2026-05-01",
                    "created_at": "2026-05-01T18:00:00",
                    "model_rules_version": "v1",
                    "allocations": [
                        {"ticker": "VFV.TO", "amount": 50, "percentage": 0.10},
                        {"ticker": "GOOGL", "amount": 450, "percentage": 0.90},
                    ],
                    "decision_quality": {"decision_quality_score": 78, "decision_quality_level": "HIGH"},
                },
            )
            save_json(
                history / "allocation_20260515_090000.json",
                {
                    "analysis_date": "2026-05-15",
                    "created_at": "2026-05-15T09:00:00",
                    "model_rules_version": "v1",
                    "allocations": [
                        {"ticker": "VFV.TO", "amount": 100, "percentage": 0.20},
                        {"ticker": "GOOGL", "amount": 400, "percentage": 0.80},
                    ],
                    "decision_quality": {"decision_quality_score": 76, "decision_quality_level": "HIGH"},
                },
            )

            audit = build_model_audit(reports, period="all", current_model_rules_version="v1")

        metrics = audit["metrics"]
        self.assertEqual(metrics["sample_count"], 2)
        self.assertEqual(metrics["same_day_collapsed_count"], 1)
        self.assertEqual(metrics["primary_tickers"], ["GOOGL", "GOOGL"])
        self.assertEqual(metrics["confidence"], "PRELIMINARY")
        self.assertEqual(metrics["threshold_review"]["status"], "INSUFFICIENT_HISTORY")

    def test_model_audit_writes_outputs_even_with_short_history(self):
        with TemporaryDirectory() as folder:
            reports = Path(folder)
            history = reports / "history"
            history.mkdir()
            save_json(
                history / "allocation_20260501_090000.json",
                {
                    "analysis_date": "2026-05-01",
                    "created_at": "2026-05-01T09:00:00",
                    "model_rules_version": "v1",
                    "allocations": [{"ticker": "VFV.TO", "amount": 500, "percentage": 1.0}],
                    "decision_quality": {"decision_quality_score": 45, "decision_quality_level": "LOW"},
                },
            )

            audit = run_model_audit(reports, period="all", current_model_rules_version="v1")

            self.assertTrue((reports / "latest_model_audit.md").exists())
            self.assertTrue((reports / "latest_model_audit.html").exists())
            self.assertTrue((reports / "latest_model_audit.csv").exists())

        self.assertEqual(audit["metrics"]["health_status"], "DATA_TOO_SHORT")

    def test_model_audit_includes_threshold_review_without_auto_change(self):
        with TemporaryDirectory() as folder:
            reports = Path(folder)
            history = reports / "history"
            history.mkdir()
            for index, month in enumerate(["01", "02", "03", "04"], start=1):
                save_json(
                    history / f"allocation_2026{month}01_090000.json",
                    {
                        "analysis_date": f"2026-{month}-01",
                        "created_at": f"2026-{month}-01T09:00:00",
                        "model_rules_version": "v1",
                        "allocations": [
                            {"ticker": "VFV.TO", "amount": 200, "percentage": 0.40},
                            {"ticker": "MSFT", "amount": 150, "percentage": 0.30},
                            {"ticker": "GOOGL", "amount": 150, "percentage": 0.30},
                        ],
                        "decision_quality": {"decision_quality_score": 70, "decision_quality_level": "MEDIUM"},
                    },
                )

            audit = build_model_audit(reports, period="all", current_model_rules_version="v1")

        self.assertEqual(audit["metrics"]["threshold_review"]["status"], "SLIGHTLY_TOO_DEFENSIVE")
        threshold_rows = [row for row in audit["rows"] if row["section"] == "Revue des seuils"]
        self.assertTrue(any(row["metric"] == "Modification automatique des règles" for row in threshold_rows))
        self.assertTrue(any(row["metric"] == "Seuils VFV / redirection" for row in threshold_rows))

    def test_model_audit_filters_snapshots_by_mode(self):
        with TemporaryDirectory() as folder:
            reports = Path(folder)
            history = reports / "history"
            history.mkdir()
            save_json(
                history / "allocation_balanced_20260501_090000.json",
                {
                    "analysis_date": "2026-05-01",
                    "created_at": "2026-05-01T09:00:00",
                    "analysis_mode": "balanced",
                    "model_rules_version": "v1",
                    "allocations": [{"ticker": "VFV.TO", "amount": 500, "percentage": 1.0}],
                },
            )
            save_json(
                history / "allocation_high-cagr_20260502_090000.json",
                {
                    "analysis_date": "2026-05-02",
                    "created_at": "2026-05-02T09:00:00",
                    "analysis_mode": "high-cagr",
                    "model_rules_version": "v1",
                    "allocations": [{"ticker": "MSFT", "amount": 500, "percentage": 1.0}],
                },
            )

            audit = build_model_audit(
                reports,
                period="all",
                mode="high-cagr",
                current_model_rules_version="v1",
            )

        metrics = audit["metrics"]
        self.assertEqual(metrics["mode"], "high-cagr")
        self.assertEqual(metrics["dates"], ["2026-05-02"])
        self.assertEqual(metrics["primary_tickers"], ["MSFT"])


if __name__ == "__main__":
    unittest.main()
