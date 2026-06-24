import tempfile
import unittest
from pathlib import Path

from src.allocation_change_engine import (
    build_allocation_change_rows,
    load_previous_allocation_baseline,
    save_allocation_snapshot,
)
from src.utils import save_json, today_iso


class AllocationChangeTest(unittest.TestCase):
    def test_change_rows_explain_increase_without_affecting_decision(self):
        allocations = [{"destination": "MSFT", "montant": 150, "pourcentage": 0.30, "raison": "Meilleur score"}]
        previous = {"MSFT": {"amount": 100, "percentage": 0.20, "reference_dates": ["2026-04-30"]}}
        analyses = {"MSFT": {"ticker": "MSFT", "capital_allocation_score_change": 5, "monitoring_status": "NORMAL"}}

        rows = build_allocation_change_rows(allocations, analyses, previous)

        self.assertEqual(rows[0]["change_status"], "INCREASED")
        self.assertIn("capital_allocation_score", rows[0]["main_explanation"])
        self.assertIn("Explication seulement", rows[0]["decision_impact"])

    def test_allocation_snapshot_can_be_reloaded_as_baseline(self):
        with tempfile.TemporaryDirectory() as tmp:
            reports_dir = Path(tmp)
            history_dir = reports_dir / "history"
            history_dir.mkdir()
            save_json(
                history_dir / "allocation_20260401_120000.json",
                {
                    "analysis_date": "2026-04-01",
                    "allocations": [{"ticker": "MSFT", "amount": 100, "percentage": 0.20}],
                },
            )
            baseline = load_previous_allocation_baseline(reports_dir)

            self.assertIn("MSFT", baseline)
            self.assertEqual(baseline["MSFT"]["amount"], 100)

    def test_same_day_history_is_not_used_as_distinct_baseline(self):
        with tempfile.TemporaryDirectory() as tmp:
            reports_dir = Path(tmp)
            history_dir = reports_dir / "history"
            history_dir.mkdir()
            save_json(
                history_dir / "allocation_today.json",
                {
                    "analysis_date": today_iso(),
                    "allocations": [{"ticker": "MSFT", "amount": 100, "percentage": 0.20}],
                },
            )

            self.assertEqual(load_previous_allocation_baseline(reports_dir), {})

    def test_save_allocation_snapshot_writes_latest_snapshot(self):
        with tempfile.TemporaryDirectory() as tmp:
            reports_dir = Path(tmp)
            save_allocation_snapshot(
                reports_dir,
                {"allocations": [{"destination": "MSFT", "montant": 100, "pourcentage": 0.20}]},
            )

            self.assertTrue((reports_dir / "latest_allocation_snapshot.json").exists())

    def test_allocation_baseline_uses_only_matching_analysis_mode(self):
        with tempfile.TemporaryDirectory() as tmp:
            reports_dir = Path(tmp)
            history_dir = reports_dir / "history"
            history_dir.mkdir()
            save_json(
                history_dir / "allocation_balanced_20260401_120000.json",
                {
                    "analysis_date": "2026-04-01",
                    "analysis_mode": "balanced",
                    "allocations": [{"ticker": "VFV.TO", "amount": 500, "percentage": 1.0}],
                },
            )
            save_json(
                history_dir / "allocation_high-cagr_20260402_120000.json",
                {
                    "analysis_date": "2026-04-02",
                    "analysis_mode": "high-cagr",
                    "allocations": [{"ticker": "MSFT", "amount": 400, "percentage": 0.80}],
                },
            )
            save_json(
                history_dir / "allocation_legacy_20260403_120000.json",
                {
                    "analysis_date": "2026-04-03",
                    "allocations": [{"ticker": "AAPL", "amount": 400, "percentage": 0.80}],
                },
            )

            baseline = load_previous_allocation_baseline(reports_dir, analysis_mode="high-cagr")

        self.assertIn("MSFT", baseline)
        self.assertNotIn("VFV.TO", baseline)
        self.assertNotIn("AAPL", baseline)

    def test_save_allocation_snapshot_writes_mode_specific_latest_snapshot(self):
        with tempfile.TemporaryDirectory() as tmp:
            reports_dir = Path(tmp)
            save_allocation_snapshot(
                reports_dir,
                {"allocations": [{"destination": "MSFT", "montant": 100, "pourcentage": 0.20}]},
                analysis_mode="high-cagr",
            )

            self.assertTrue((reports_dir / "latest_allocation_snapshot.json").exists())
            self.assertTrue((reports_dir / "latest_allocation_snapshot_high-cagr.json").exists())


if __name__ == "__main__":
    unittest.main()
