import tempfile
import unittest
from pathlib import Path

import pandas as pd

from src.utils import save_json
from src.walk_forward_backtest_engine import (
    WalkForwardInventoryConfig,
    build_walk_forward_coverage,
    build_walk_forward_inventory,
    build_walk_forward_regime_summary,
    build_walk_forward_simulation_summary,
    run_walk_forward_inventory,
    simulate_walk_forward_periods,
)


class WalkForwardBacktestEngineTest(unittest.TestCase):
    def test_inventory_uses_only_matching_mode_and_pairs_snapshots(self):
        with tempfile.TemporaryDirectory() as directory:
            reports = Path(directory)
            history = reports / "history"
            history.mkdir()
            save_json(
                history / "analysis_high-cagr_20260601_120000.json",
                {
                    "analysis_date": "2026-06-01",
                    "created_at": "2026-06-01T12:00:00",
                    "analysis_mode": "high-cagr",
                    "model_rules_version": "test",
                    "analyses": [{"ticker": "MSFT", "universe": "CORE_PORTFOLIO"}],
                },
            )
            save_json(
                history / "allocation_high-cagr_20260601_120100.json",
                {
                    "analysis_date": "2026-06-01",
                    "created_at": "2026-06-01T12:01:00",
                    "analysis_mode": "high-cagr",
                    "model_rules_version": "test",
                    "allocations": [{"ticker": "MSFT", "amount": 100, "percentage": 0.8}],
                },
            )
            save_json(
                history / "analysis_balanced_20260601_130000.json",
                {
                    "analysis_date": "2026-06-01",
                    "created_at": "2026-06-01T13:00:00",
                    "analysis_mode": "balanced",
                    "analyses": [{"ticker": "VFV.TO", "universe": "CORE_PORTFOLIO"}],
                },
            )
            save_json(
                history / "analysis_high-cagr_20260620_120000.json",
                {
                    "analysis_date": "2026-06-20",
                    "created_at": "2026-06-20T12:00:00",
                    "analysis_mode": "high-cagr",
                    "model_rules_version": "test",
                    "analyses": [{"ticker": "AAPL", "universe": "CORE_PORTFOLIO"}],
                },
            )
            save_json(
                history / "allocation_high-cagr_20260620_120100.json",
                {
                    "analysis_date": "2026-06-20",
                    "created_at": "2026-06-20T12:01:00",
                    "analysis_mode": "high-cagr",
                    "model_rules_version": "test",
                    "allocations": [{"ticker": "AAPL", "amount": 100, "percentage": 0.8}],
                },
            )

            rows = build_walk_forward_inventory(
                reports,
                WalkForwardInventoryConfig(mode="high-cagr", min_days_between_points=14, recommended_min_periods=2),
            )
            coverage = build_walk_forward_coverage(
                rows,
                WalkForwardInventoryConfig(mode="high-cagr", min_days_between_points=14, recommended_min_periods=2),
            )

        self.assertEqual([row["analysis_date"] for row in rows], ["2026-06-01", "2026-06-20"])
        self.assertTrue(rows[0]["usable_for_walk_forward"])
        self.assertEqual(rows[0]["days_to_next"], 19)
        self.assertEqual(rows[1]["exclusion_reason"], "OPEN_PERIOD_NO_NEXT_ANALYSIS_YET")
        self.assertEqual(coverage["usable_walk_forward_periods"], 1)

    def test_inventory_keeps_latest_snapshot_for_same_date(self):
        with tempfile.TemporaryDirectory() as directory:
            reports = Path(directory)
            history = reports / "history"
            history.mkdir()
            save_json(
                history / "analysis_high-cagr_20260601_090000.json",
                {
                    "analysis_date": "2026-06-01",
                    "created_at": "2026-06-01T09:00:00",
                    "analysis_mode": "high-cagr",
                    "analyses": [{"ticker": "OLD", "universe": "CORE_PORTFOLIO"}],
                },
            )
            save_json(
                history / "analysis_high-cagr_20260601_170000.json",
                {
                    "analysis_date": "2026-06-01",
                    "created_at": "2026-06-01T17:00:00",
                    "analysis_mode": "high-cagr",
                    "analyses": [{"ticker": "NEW", "universe": "CORE_PORTFOLIO"}],
                },
            )
            save_json(
                history / "allocation_high-cagr_20260601_170100.json",
                {
                    "analysis_date": "2026-06-01",
                    "created_at": "2026-06-01T17:01:00",
                    "analysis_mode": "high-cagr",
                    "allocations": [{"ticker": "NEW", "amount": 100, "percentage": 1.0}],
                },
            )

            rows = build_walk_forward_inventory(reports, WalkForwardInventoryConfig(mode="high-cagr"))

        self.assertEqual(len(rows), 1)
        self.assertIn("170000", rows[0]["analysis_snapshot_path"])

    def test_run_inventory_writes_outputs(self):
        with tempfile.TemporaryDirectory() as directory:
            reports = Path(directory)
            (reports / "history").mkdir()
            result = run_walk_forward_inventory(reports, mode="high-cagr")

            self.assertTrue((reports / "latest_walk_forward_inventory.csv").exists())
            self.assertTrue((reports / "latest_walk_forward_coverage.csv").exists())
            self.assertTrue((reports / "latest_walk_forward_inventory.md").exists())
            self.assertEqual(result["coverage"]["status"], "INSUFFICIENT_HISTORY")

    def test_simulation_compares_historical_allocation_to_vfv(self):
        with tempfile.TemporaryDirectory() as directory:
            reports = Path(directory)
            history = reports / "history"
            history.mkdir()
            allocation_path = history / "allocation_high-cagr_20260101_120000.json"
            save_json(
                allocation_path,
                {
                    "analysis_date": "2026-01-01",
                    "analysis_mode": "high-cagr",
                    "created_at": "2026-01-01T12:00:00",
                    "allocations": [
                        {"ticker": "AAPL", "amount": 50, "percentage": 0.5},
                        {"ticker": "VFV.TO", "amount": 50, "percentage": 0.5},
                    ],
                },
            )
            row = {
                "mode": "high-cagr",
                "analysis_date": "2026-01-01",
                "next_analysis_date": "2026-01-31",
                "days_to_next": 30,
                "allocation_count": 2,
                "allocated_tickers": "AAPL, VFV.TO",
                "allocation_snapshot_path": str(allocation_path),
                "usable_for_walk_forward": True,
            }
            prices = pd.DataFrame(
                {
                    "AAPL": [100.0, 110.0],
                    "VFV.TO": [100.0, 102.0],
                },
                index=pd.to_datetime(["2026-01-02", "2026-01-30"]),
            )

            result = simulate_walk_forward_periods(
                [row],
                prices,
                WalkForwardInventoryConfig(mode="high-cagr", min_days_between_points=14),
            )
            period = result["period_rows"][0]

        self.assertEqual(period["evaluation_status"], "SIMULATED")
        self.assertAlmostEqual(period["strategy_period_return"], 0.06)
        self.assertAlmostEqual(period["vfv_period_return"], 0.02)
        self.assertAlmostEqual(period["excess_return_vs_vfv"], 0.04)
        self.assertIn("net_strategy_period_return_after_friction", period)
        self.assertIn("friction_drag", period)
        self.assertLessEqual(period["net_strategy_period_return_after_friction"], period["strategy_period_return"])
        self.assertEqual(period["market_regime"], "VFV_POSITIVE")
        self.assertEqual(len(result["allocation_return_rows"]), 2)

    def test_regime_summary_flags_confirmed_weak_regime(self):
        period_rows = [
            {
                "evaluation_status": "SIMULATED",
                "market_regime": "VFV_WEAK",
                "strategy_period_return": -0.09,
                "vfv_period_return": -0.03,
                "excess_return_vs_vfv": -0.06,
            },
            {
                "evaluation_status": "SIMULATED",
                "market_regime": "VFV_WEAK",
                "strategy_period_return": -0.06,
                "vfv_period_return": -0.02,
                "excess_return_vs_vfv": -0.04,
            },
        ]

        rows = build_walk_forward_regime_summary(period_rows, WalkForwardInventoryConfig(mode="high-cagr"))

        self.assertEqual(rows[0]["market_regime"], "VFV_WEAK")
        self.assertEqual(rows[0]["regime_status"], "WEAK")

    def test_summary_includes_regime_coverage_status(self):
        period_rows = [
            {
                "evaluation_status": "SIMULATED",
                "market_regime": "VFV_POSITIVE",
                "strategy_period_return": 0.04,
                "vfv_period_return": 0.03,
                "excess_return_vs_vfv": 0.01,
                "days_held": 30,
            },
            {
                "evaluation_status": "SIMULATED",
                "market_regime": "VFV_WEAK",
                "strategy_period_return": -0.09,
                "vfv_period_return": -0.03,
                "excess_return_vs_vfv": -0.06,
                "days_held": 30,
            },
            {
                "evaluation_status": "SIMULATED",
                "market_regime": "VFV_WEAK",
                "strategy_period_return": -0.06,
                "vfv_period_return": -0.02,
                "excess_return_vs_vfv": -0.04,
                "days_held": 30,
            },
            {
                "evaluation_status": "SIMULATED",
                "market_regime": "VFV_FLAT",
                "strategy_period_return": 0.01,
                "vfv_period_return": 0.0,
                "excess_return_vs_vfv": 0.01,
                "days_held": 30,
            },
            {
                "evaluation_status": "SIMULATED",
                "market_regime": "VFV_POSITIVE",
                "strategy_period_return": 0.03,
                "vfv_period_return": 0.02,
                "excess_return_vs_vfv": 0.01,
                "days_held": 30,
            },
            {
                "evaluation_status": "SIMULATED",
                "market_regime": "VFV_FLAT",
                "strategy_period_return": 0.01,
                "vfv_period_return": 0.0,
                "excess_return_vs_vfv": 0.01,
                "days_held": 30,
            },
        ]
        regime_rows = build_walk_forward_regime_summary(period_rows, WalkForwardInventoryConfig(mode="high-cagr"))
        summary = build_walk_forward_simulation_summary(
            period_rows,
            {"usable_walk_forward_periods": 6},
            WalkForwardInventoryConfig(mode="high-cagr", recommended_min_periods=6),
            "TEST",
            regime_rows,
        )

        self.assertEqual(summary["regime_coverage_status"], "HAS_WEAK_REGIME")
        self.assertEqual(summary["weak_regimes"], "VFV_WEAK")

    def test_summary_excludes_period_with_too_much_missing_price_data(self):
        period_rows = [
            {
                "evaluation_status": "PRICE_DATA_TOO_INCOMPLETE",
                "strategy_period_return": 0.05,
                "vfv_period_return": 0.02,
                "excess_return_vs_vfv": 0.03,
                "days_held": 30,
            }
        ]
        coverage = {"usable_walk_forward_periods": 1}
        summary = build_walk_forward_simulation_summary(
            period_rows,
            coverage,
            WalkForwardInventoryConfig(mode="high-cagr", recommended_min_periods=6),
            "TEST",
        )

        self.assertEqual(summary["status"], "NO_SIMULATED_PERIODS")
        self.assertEqual(summary["simulated_periods"], 0)


if __name__ == "__main__":
    unittest.main()
