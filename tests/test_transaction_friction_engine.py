import unittest

from src.transaction_friction_engine import (
    add_friction_fields_to_backtest_summaries,
    build_theoretical_backtest_friction_rows,
    estimate_trade_friction,
)


class TransactionFrictionEngineTest(unittest.TestCase):
    def test_us_trade_gets_fx_drag_without_changing_trade_value(self):
        result = estimate_trade_friction(
            "MSFT",
            1000,
            {"quote_currency": "USD"},
            {
                "enabled": True,
                "commission_cad_per_trade": 0,
                "spread_bps_default": 10,
                "spread_bps_illiquid": 30,
                "fx_fee_bps": 150,
                "minimum_trade_value_cad": 25,
                "illiquid_tickers": [],
            },
        )

        self.assertTrue(result["is_fx_trade"])
        self.assertAlmostEqual(result["estimated_transaction_cost_cad"], 16.0)
        self.assertIn("FX_ESTIMATE", result["friction_assumption_status"])

    def test_backtest_friction_rows_add_net_fields_without_overwriting_gross(self):
        summaries = [{"period_years": 1, "strategy": "model-lite high-cagr", "total_contributed": 1000, "final_value": 1200}]
        allocations = [
            {"period_years": 1, "ticker": "MSFT", "amount": 900},
            {"period_years": 1, "ticker": "VFV.TO", "amount": 100},
        ]
        rows = build_theoretical_backtest_friction_rows(
            summaries,
            allocations,
            {"MSFT": {"quote_currency": "USD"}, "VFV.TO": {"quote_currency": "CAD"}},
        )
        enriched = add_friction_fields_to_backtest_summaries(summaries, rows)

        self.assertEqual(summaries[0]["final_value"], 1200)
        self.assertGreater(rows[0]["estimated_transaction_cost_cad"], 0)
        self.assertEqual(enriched[0]["gross_return"], 0.2)
        self.assertLess(enriched[0]["net_return_after_friction"], enriched[0]["gross_return"])


if __name__ == "__main__":
    unittest.main()
