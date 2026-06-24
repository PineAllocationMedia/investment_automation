import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from src.history_engine import apply_history_context, compute_trend, load_previous_snapshot
from src.utils import save_json, today_iso


class HistoryEngineTest(unittest.TestCase):
    def test_detects_deterioration_from_previous_analysis(self):
        current = {
            "ticker": "MSFT",
            "score_total": 7.0,
            "conviction_score": 62,
            "thesis_status": "WEAKENING",
            "liquidation_status": "YELLOW",
            "expected_cagr_quality": "MEDIUM",
            "data_quality": "MEDIUM",
            "score_missing_data_count": 2,
        }
        previous = {
            "ticker": "MSFT",
            "score_total": 8.5,
            "conviction_score": 82,
            "thesis_status": "INTACT",
            "liquidation_status": "GREEN",
            "expected_cagr_quality": "HIGH",
            "data_quality": "HIGH",
            "score_missing_data_count": 0,
        }

        trend = compute_trend(current, previous)

        self.assertEqual(trend["trend_status"], "DETERIORATING")
        self.assertGreaterEqual(trend["trend_severity"], 2)

    def test_severe_deterioration_adds_watch_signal(self):
        current = {
            "ticker": "MSFT",
            "score_total": 7.0,
            "conviction_score": 62,
            "thesis_status": "WEAKENING",
            "liquidation_status": "GREEN",
            "expected_cagr_quality": "MEDIUM",
            "data_quality": "MEDIUM",
            "score_missing_data_count": 2,
            "signals_detected": [],
            "liquidation_reasons": [],
        }
        previous = {
            "ticker": "MSFT",
            "score_total": 8.5,
            "conviction_score": 82,
            "thesis_status": "INTACT",
            "liquidation_status": "GREEN",
            "expected_cagr_quality": "HIGH",
            "data_quality": "HIGH",
            "score_missing_data_count": 0,
        }

        analyses = {"MSFT": current}
        apply_history_context(analyses, {"MSFT": previous})

        self.assertEqual(analyses["MSFT"]["trend_status"], "DETERIORATING")
        self.assertIn("Deterioration detectee", analyses["MSFT"]["signals_detected"][0])

    def test_history_uses_distinct_previous_dates_and_ignores_same_day_runs(self):
        with TemporaryDirectory() as folder:
            reports_dir = Path(folder)
            history_dir = reports_dir / "history"
            history_dir.mkdir()
            today = today_iso()
            today_file_date = today.replace("-", "")
            save_json(
                history_dir / f"analysis_{today_file_date}_090000.json",
                {
                    "created_at": f"{today}T09:00:00",
                    "analysis_date": today,
                    "analyses": [{"ticker": "MSFT", "score_total": 1.0, "conviction_score": 10}],
                },
            )
            save_json(
                history_dir / "analysis_20260401_090000.json",
                {
                    "created_at": "2026-04-01T09:00:00",
                    "analysis_date": "2026-04-01",
                    "analyses": [{"ticker": "MSFT", "score_total": 8.0, "conviction_score": 80}],
                },
            )
            save_json(
                history_dir / "analysis_20260301_090000.json",
                {
                    "created_at": "2026-03-01T09:00:00",
                    "analysis_date": "2026-03-01",
                    "analyses": [{"ticker": "MSFT", "score_total": 10.0, "conviction_score": 100}],
                },
            )

            previous = load_previous_snapshot(reports_dir)

        self.assertEqual(previous["MSFT"]["history_reference_dates"], ["2026-04-01", "2026-03-01"])
        self.assertEqual(previous["MSFT"]["history_reference_count"], 2)
        self.assertAlmostEqual(previous["MSFT"]["score_total"], 9.0)
        self.assertAlmostEqual(previous["MSFT"]["conviction_score"], 90.0)

    def test_history_ignores_snapshots_from_incompatible_model_rules_version(self):
        with TemporaryDirectory() as folder:
            reports_dir = Path(folder)
            history_dir = reports_dir / "history"
            history_dir.mkdir()
            save_json(
                history_dir / "analysis_20260401_090000.json",
                {
                    "created_at": "2026-04-01T09:00:00",
                    "analysis_date": "2026-04-01",
                    "model_rules_version": "old-rules",
                    "analyses": [{"ticker": "MSFT", "score_total": 8.0, "conviction_score": 80}],
                },
            )
            save_json(
                history_dir / "analysis_20260402_090000.json",
                {
                    "created_at": "2026-04-02T09:00:00",
                    "analysis_date": "2026-04-02",
                    "model_rules_version": "new-rules",
                    "analyses": [{"ticker": "MSFT", "score_total": 9.0, "conviction_score": 90}],
                },
            )

            previous = load_previous_snapshot(reports_dir, current_model_rules_version="new-rules")

        self.assertEqual(previous["MSFT"]["history_reference_dates"], ["2026-04-02"])
        self.assertEqual(previous["MSFT"]["score_total"], 9.0)

    def test_history_uses_only_matching_analysis_mode_when_requested(self):
        with TemporaryDirectory() as folder:
            reports_dir = Path(folder)
            history_dir = reports_dir / "history"
            history_dir.mkdir()
            save_json(
                history_dir / "analysis_balanced_20260401_090000.json",
                {
                    "created_at": "2026-04-01T09:00:00",
                    "analysis_date": "2026-04-01",
                    "analysis_mode": "balanced",
                    "analyses": [{"ticker": "MSFT", "score_total": 5.0, "conviction_score": 50}],
                },
            )
            save_json(
                history_dir / "analysis_high-cagr_20260402_090000.json",
                {
                    "created_at": "2026-04-02T09:00:00",
                    "analysis_date": "2026-04-02",
                    "analysis_mode": "high-cagr",
                    "analyses": [{"ticker": "MSFT", "score_total": 9.0, "conviction_score": 90}],
                },
            )
            save_json(
                history_dir / "analysis_legacy_20260403_090000.json",
                {
                    "created_at": "2026-04-03T09:00:00",
                    "analysis_date": "2026-04-03",
                    "analyses": [{"ticker": "MSFT", "score_total": 1.0, "conviction_score": 10}],
                },
            )

            previous = load_previous_snapshot(reports_dir, analysis_mode="high-cagr")

        self.assertEqual(previous["MSFT"]["history_reference_dates"], ["2026-04-02"])
        self.assertEqual(previous["MSFT"]["score_total"], 9.0)

    def test_trend_report_contains_history_reference_dates(self):
        current = {
            "ticker": "MSFT",
            "score_total": 9.0,
            "conviction_score": 90,
            "thesis_status": "INTACT",
            "liquidation_status": "GREEN",
            "expected_cagr_quality": "HIGH",
            "data_quality": "HIGH",
            "score_missing_data_count": 0,
        }
        previous = {
            "ticker": "MSFT",
            "score_total": 8.8,
            "conviction_score": 88,
            "thesis_status": "INTACT",
            "liquidation_status": "GREEN",
            "expected_cagr_quality": "HIGH",
            "data_quality": "HIGH",
            "score_missing_data_count": 0,
            "history_reference_count": 2,
            "history_reference_dates": ["2026-04-01", "2026-03-01"],
        }

        trend = compute_trend(current, previous)

        self.assertEqual(trend["history_reference_count"], 2)
        self.assertEqual(trend["history_reference_dates"], ["2026-04-01", "2026-03-01"])
        self.assertIn("date(s) distincte(s)", " ".join(trend["trend_reasons"]))


if __name__ == "__main__":
    unittest.main()
