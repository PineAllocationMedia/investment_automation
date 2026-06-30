import unittest
from pathlib import Path

import pandas as pd

from src.benchmark_comparison_engine import (
    BenchmarkDefinition,
    benchmark_period_return,
    benchmark_price_tickers,
    build_backtest_benchmark_comparisons,
    build_walk_forward_benchmark_comparisons,
    simulate_monthly_benchmark,
)


class BenchmarkComparisonEngineTest(unittest.TestCase):
    def test_multiple_static_benchmarks_can_be_calculated(self):
        dates = pd.to_datetime(
            [
                "2025-07-28",
                "2025-08-28",
                "2025-09-28",
                "2025-10-28",
                "2025-11-28",
                "2025-12-28",
                *[f"2026-{month:02d}-28" for month in range(1, 13)],
            ]
        )
        prices = pd.DataFrame(
            {
                "VFV.TO": [100 + month for month in range(len(dates))],
                "XEQT.TO": [80 + month * 1.5 for month in range(len(dates))],
                "ZAG.TO": [50 + month * 0.1 for month in range(len(dates))],
            },
            index=dates,
        )
        definitions = [
            BenchmarkDefinition("VFV_100", "100 % VFV", "STATIC_WEIGHTS", {"VFV.TO": 1.0}, []),
            BenchmarkDefinition("CANADIAN_60_40", "60/40", "STATIC_WEIGHTS", {"XEQT.TO": 0.6, "ZAG.TO": 0.4}, []),
            BenchmarkDefinition(
                "SIMPLE_MOMENTUM",
                "Momentum",
                "SIMPLE_MOMENTUM",
                {},
                ["VFV.TO", "XEQT.TO"],
                lookback_months=3,
            ),
        ]
        summaries = [
            {"period_years": 1, "months": 12, "final_value": 6400, "money_weighted_annual_return": 0.08}
        ]
        monthly_rows = [{"period_years": 1, "date": date.date().isoformat()} for date in dates[-12:]]

        rows = build_backtest_benchmark_comparisons(summaries, monthly_rows, prices, 500, definitions)

        self.assertEqual({row["benchmark_id"] for row in rows}, {"VFV_100", "CANADIAN_60_40", "SIMPLE_MOMENTUM"})
        self.assertTrue(all(row["data_coverage_status"] == "AVAILABLE" for row in rows))
        self.assertTrue(all(row["benchmark_final_value"] for row in rows))

    def test_missing_benchmark_data_does_not_crash(self):
        dates = pd.to_datetime([f"2026-{month:02d}-28" for month in range(1, 13)])
        prices = pd.DataFrame({"VFV.TO": [100 + month for month in range(12)]}, index=dates)
        definition = BenchmarkDefinition("XEQT_100", "100 % XEQT", "STATIC_WEIGHTS", {"XEQT.TO": 1.0}, [])

        result = simulate_monthly_benchmark(prices, list(dates), 500, definition)

        self.assertEqual(result["data_coverage_status"], "INSUFFICIENT_PRICE_HISTORY")
        self.assertIn("XEQT.TO", result["unavailable_reason"])

    def test_momentum_benchmark_uses_only_prior_price_history(self):
        dates = pd.date_range("2026-01-01", "2026-03-31", freq="B")
        pre_decision_count = sum(date < pd.Timestamp("2026-03-02") for date in dates)
        aaa = []
        bbb = []
        for index, date in enumerate(dates):
            if date < pd.Timestamp("2026-03-02"):
                aaa.append(100 + index * 0.7)
                bbb.append(100.0)
            else:
                aaa.append(140.0)
                bbb.append(100 + (index - pre_decision_count) * 5.0)
        prices = pd.DataFrame({"AAA": aaa, "BBB": bbb}, index=dates)
        definition = BenchmarkDefinition("SIMPLE_MOMENTUM", "Momentum", "SIMPLE_MOMENTUM", {}, ["AAA", "BBB"], lookback_months=1)

        result = benchmark_period_return(prices, "2026-03-02", "2026-03-31", definition)

        self.assertEqual(result["data_coverage_status"], "AVAILABLE")
        self.assertEqual(result["selected_components"], "AAA:100%")
        self.assertLess(result["benchmark_period_return"], 0.05)

    def test_walk_forward_comparison_rows_are_deterministic(self):
        dates = pd.to_datetime(["2026-01-02", "2026-01-30"])
        prices = pd.DataFrame({"VFV.TO": [100.0, 102.0], "XEQT.TO": [100.0, 103.0]}, index=dates)
        period_rows = [
            {
                "mode": "high-cagr",
                "analysis_date": "2026-01-01",
                "next_analysis_date": "2026-01-31",
                "days_held": 30,
                "strategy_period_return": 0.04,
                "evaluation_status": "SIMULATED",
            }
        ]
        definitions = [
            BenchmarkDefinition("VFV_100", "100 % VFV", "STATIC_WEIGHTS", {"VFV.TO": 1.0}, []),
            BenchmarkDefinition("XEQT_100", "100 % XEQT", "STATIC_WEIGHTS", {"XEQT.TO": 1.0}, []),
        ]

        first = build_walk_forward_benchmark_comparisons(period_rows, prices, definitions)
        second = build_walk_forward_benchmark_comparisons(period_rows, prices, definitions)

        self.assertEqual(first, second)
        self.assertEqual(len(first), 2)
        self.assertEqual(first[0]["win_loss_vs_benchmark"], "WIN")

    def test_benchmark_price_tickers_are_config_driven(self):
        definitions = [
            BenchmarkDefinition("STATIC", "Static", "STATIC_WEIGHTS", {"AAA": 0.5, "BBB": 0.5}, []),
            BenchmarkDefinition("MOMENTUM", "Momentum", "SIMPLE_MOMENTUM", {}, ["CCC", "AAA"]),
        ]

        self.assertEqual(benchmark_price_tickers(definitions), ["AAA", "BBB", "CCC"])

    def test_no_statistical_optimizer_logic_is_introduced(self):
        source = Path("src/benchmark_comparison_engine.py").read_text(encoding="utf-8").lower()

        for forbidden in ["covariance", "correlation matrix", "pca", "eigenvalue", "mean-variance", "optimizer"]:
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
