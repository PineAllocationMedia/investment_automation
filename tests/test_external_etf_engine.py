import unittest

from src.external_etf_engine import score_external_etf_candidate


class ExternalEtfEngineTest(unittest.TestCase):
    def test_balanced_accepts_conservative_or_balanced_external_etf(self):
        row = score_external_etf_candidate(
            {
                "ticker": "XBAL.TO",
                "universe": "MARKET_SCANNER",
                "asset_type": "ETF_BALANCED_ALLOCATION",
                "current_price": 28,
                "price_above_sma_200": True,
                "stock_return_1y": 0.05,
                "drawdown_from_12m_high": -0.04,
            },
            "balanced",
            {},
        )

        self.assertEqual(row["external_etf_allocation_status"], "ELIGIBLE_EXTERNAL_ETF_ALLOCATION")
        self.assertEqual(row["add_eligibility_status"], "ADD_ALLOWED")
        self.assertGreaterEqual(row["external_etf_score"], 72)

    def test_high_cagr_disables_external_etf_allocation(self):
        row = score_external_etf_candidate(
            {
                "ticker": "QQQ",
                "universe": "MARKET_SCANNER",
                "asset_type": "ETF_NASDAQ_100",
                "current_price": 500,
                "price_above_sma_200": True,
                "stock_return_1y": 0.20,
            },
            "high-cagr",
            {},
        )

        self.assertEqual(row["external_etf_allocation_status"], "DISABLED_FOR_HIGH_CAGR")
        self.assertEqual(row["add_eligibility_status"], "ETF_HOLD_ONLY")

    def test_speculative_external_etf_is_rejected(self):
        row = score_external_etf_candidate(
            {
                "ticker": "FBTC.TO",
                "universe": "MARKET_SCANNER",
                "current_price": 40,
                "price_above_sma_200": True,
                "stock_return_1y": 0.50,
            },
            "rational-aggressive",
            {},
        )

        self.assertEqual(row["external_etf_allocation_status"], "REJECTED_EXTERNAL_ETF")
        self.assertEqual(row["add_eligibility_status"], "ETF_HOLD_ONLY")

    def test_growth_etf_is_penalized_when_portfolio_is_already_tech_heavy(self):
        clean = score_external_etf_candidate(
            {
                "ticker": "QQQ",
                "universe": "MARKET_SCANNER",
                "asset_type": "ETF_NASDAQ_100",
                "current_price": 500,
                "price_above_sma_200": True,
                "stock_return_1y": 0.15,
            },
            "rational-aggressive",
            {"tech_ai_semi_weight": 0.10},
        )
        tech_heavy = score_external_etf_candidate(
            {
                "ticker": "QQQ",
                "universe": "MARKET_SCANNER",
                "asset_type": "ETF_NASDAQ_100",
                "current_price": 500,
                "price_above_sma_200": True,
                "stock_return_1y": 0.15,
            },
            "rational-aggressive",
            {"tech_ai_semi_weight": 0.55},
        )

        self.assertLess(tech_heavy["external_etf_score"], clean["external_etf_score"])

    def test_external_etf_without_price_is_not_allocated(self):
        row = score_external_etf_candidate(
            {
                "ticker": "XBAL.TO",
                "universe": "MARKET_SCANNER",
                "asset_type": "ETF_BALANCED_ALLOCATION",
                "current_price": None,
            },
            "family-office",
            {},
        )

        self.assertEqual(row["external_etf_allocation_status"], "INSUFFICIENT_ETF_DATA")
        self.assertEqual(row["add_eligibility_status"], "ETF_HOLD_ONLY")


if __name__ == "__main__":
    unittest.main()
