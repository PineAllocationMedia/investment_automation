import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd

from src.backtest_engine import BACKTEST_SUMMARY_COLUMNS, run_backtests_from_latest_reports
from src.mode_artifacts import mode_artifact_path
from src.model_improvement_engine import apply_safe_tuning
from src.utils import save_json, write_csv_records
from src.walk_forward_backtest_engine import run_walk_forward_backtest
from tests.helpers import full_strong_analysis


def _score_row(ticker: str) -> dict:
    row = full_strong_analysis(ticker)
    row.update(
        {
            "ticker": ticker,
            "capital_allocation_score": 90,
            "thesis_status": "INTACT",
            "liquidation_status": "GREEN",
            "add_eligibility_status": "ADD_ALLOWED",
            "data_reliability_level": "HIGH",
            "final_position_action": "BUY / ADD",
            "quote_currency": "CAD",
        }
    )
    return row


class ModeScopedArtifactsTest(unittest.TestCase):
    def test_backtest_refuses_missing_mode_specific_scores(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            reports = root / "reports"
            data = root / "data"
            reports.mkdir()
            data.mkdir()
            write_csv_records(reports / "latest_scores.csv", [_score_row("MSFT")], ["ticker"])
            write_csv_records(reports / "latest_scores_balanced.csv", [_score_row("MSFT")], ["ticker"])

            with self.assertRaisesRegex(RuntimeError, "Missing mode-specific scores for high-cagr"):
                run_backtests_from_latest_reports(reports, data, years=[1], mode="high-cagr")

    def test_backtest_writes_mode_specific_outputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            reports = root / "reports"
            data = root / "data"
            reports.mkdir()
            data.mkdir()
            rows = [_score_row("MSFT"), {"ticker": "VFV.TO", "quote_currency": "CAD"}]
            write_csv_records(mode_artifact_path(reports / "latest_scores.csv", "high-cagr"), rows, list(rows[0].keys()))
            write_csv_records(
                mode_artifact_path(reports / "latest_decision_quality.csv", "high-cagr"),
                [{"vfv_mandatory_percent": 0.05}],
                ["vfv_mandatory_percent"],
            )
            prices = pd.DataFrame(
                {
                    "MSFT": [100 + i for i in range(18)],
                    "VFV.TO": [80 + i * 0.5 for i in range(18)],
                },
                index=pd.date_range("2025-01-31", periods=18, freq="ME"),
            )
            prices.attrs["price_return_basis"] = "TEST"

            with patch("src.backtest_engine.fetch_price_history_cad", return_value=prices):
                result = run_backtests_from_latest_reports(reports, data, years=[1], mode="high-cagr")

            self.assertTrue(result["summaries"])
            self.assertTrue((reports / "latest_backtest_summary.csv").exists())
            self.assertTrue(mode_artifact_path(reports / "latest_backtest_summary.csv", "high-cagr").exists())
            suffix_rows = pd.read_csv(mode_artifact_path(reports / "latest_backtest_summary.csv", "high-cagr"))
            self.assertEqual(list(suffix_rows.columns), BACKTEST_SUMMARY_COLUMNS)

    def test_walk_forward_filters_snapshots_by_mode_and_writes_suffix(self):
        with tempfile.TemporaryDirectory() as tmp:
            reports = Path(tmp) / "reports"
            data = Path(tmp) / "data"
            history = reports / "history"
            history.mkdir(parents=True)
            data.mkdir()
            _write_snapshot_pair(history, "balanced", "2026-01-01", "MSFT")
            _write_snapshot_pair(history, "high-cagr", "2026-01-02", "AAPL")

            result = run_walk_forward_backtest(reports, data, mode="high-cagr")

            self.assertTrue(result["inventory_rows"])
            self.assertTrue(all(row["mode"] == "high-cagr" for row in result["inventory_rows"]))
            self.assertTrue((reports / "latest_walk_forward_summary.csv").exists())
            self.assertTrue(mode_artifact_path(reports / "latest_walk_forward_summary.csv", "high-cagr").exists())

    def test_apply_safe_tuning_ignores_generic_or_other_mode_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            reports = root / "reports"
            config = root / "config"
            data = root / "data"
            reports.mkdir()
            config.mkdir()
            data.mkdir()
            write_csv_records(
                reports / "latest_improvement_summary.csv",
                [{"date": "2026-07-01", "mode": "balanced", "status": "READY_FOR_SAFE_TUNING"}],
                ["date", "mode", "status"],
            )
            write_csv_records(
                reports / "latest_improvement_suggestions.csv",
                [{"mode": "balanced", "parameter": "vfv_adjustment", "safety_level": "SAFE", "can_auto_apply": True}],
                ["mode", "parameter", "safety_level", "can_auto_apply"],
            )

            result = apply_safe_tuning(reports, config, data, mode="high-cagr")

            self.assertEqual(result["applied"], [])
            self.assertIn("PROPOSAL_ONLY", result["message"])


def _write_snapshot_pair(history: Path, mode: str, analysis_date: str, ticker: str) -> None:
    common = {
        "analysis_date": analysis_date,
        "created_at": f"{analysis_date}T10:00:00",
        "analysis_mode": mode,
        "model_rules_version": "test",
    }
    save_json(
        history / f"analysis_{mode}_{analysis_date}.json",
        {**common, "analyses": [{"ticker": ticker, "score_total": 9}]},
    )
    save_json(
        history / f"allocation_{mode}_{analysis_date}.json",
        {**common, "allocations": [{"ticker": ticker, "amount": 100, "percentage": 1.0}]},
    )


if __name__ == "__main__":
    unittest.main()
