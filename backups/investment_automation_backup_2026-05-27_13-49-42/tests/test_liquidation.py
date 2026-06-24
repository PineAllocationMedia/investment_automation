import unittest

from tests.helpers import strong_benchmark, strong_manual, strong_market
from src.liquidation_engine import apply_history_sell_discipline, compute_liquidation_status
from src.scoring import compute_fundamental_score


class LiquidationTest(unittest.TestCase):
    def test_green_when_four_of_five_conditions_are_true(self):
        manual = strong_manual()
        market = strong_market()
        score = compute_fundamental_score("MSFT", manual, market, strong_benchmark())
        result = compute_liquidation_status(manual, score, "INTACT", market, strong_benchmark())
        self.assertEqual(result["liquidation_status"], "GREEN")
        self.assertEqual(result["recommended_action"], "HOLD")

    def test_weak_valuation_signal_becomes_monitoring_alert_not_sell_signal(self):
        manual = strong_manual()
        market = strong_market()
        score = compute_fundamental_score("MSFT", manual, market, strong_benchmark())
        score["peg"] = 2.8
        result = compute_liquidation_status(manual, score, "INTACT", market, strong_benchmark())
        self.assertEqual(result["liquidation_status"], "GREEN")
        self.assertEqual(result["sell_decision"], "HOLD")
        self.assertEqual(result["monitoring_status"], "WATCH")

    def test_technical_signals_alone_do_not_trigger_trim(self):
        manual = strong_manual()
        market = strong_market()
        market["price_above_sma_200"] = False
        market["stock_return_1y"] = -0.25
        score = compute_fundamental_score("MSFT", manual, market, strong_benchmark())
        score["peg"] = 3.5

        result = compute_liquidation_status(manual, score, "INTACT", market, strong_benchmark())

        self.assertEqual(result["liquidation_status"], "GREEN")
        self.assertEqual(result["sell_decision"], "HOLD")
        self.assertEqual(result["monitoring_status"], "WATCH")
        self.assertEqual(result["mechanical_sell_signal"], "NONE")

    def test_low_relevance_negative_benchmark_alone_does_not_create_sell_signal(self):
        manual = strong_manual()
        market = strong_market()
        market["stock_return_1y"] = -0.05
        benchmark = strong_benchmark()
        benchmark["benchmark_5y_cagr"] = -0.05
        benchmark["benchmark_return_1y"] = 0.25
        benchmark["benchmark_relevance_level"] = "LOW"
        benchmark["benchmark_relevance_score"] = 0.25
        score = compute_fundamental_score("AAPL", manual, market, benchmark)

        result = compute_liquidation_status(manual, score, "INTACT", market, benchmark)

        self.assertEqual(result["liquidation_status"], "GREEN")
        self.assertEqual(result["technical_or_valuation_signals"], [])

    def test_orange_requires_confirmed_fundamental_signals(self):
        manual = strong_manual()
        manual["margin_or_profitability_under_pressure"] = True
        manual["moat_clear"] = False
        market = strong_market()
        market["price_above_sma_200"] = False
        market["stock_return_1y"] = -0.20
        score = compute_fundamental_score("MSFT", manual, market, strong_benchmark())
        score["eps_growth_estimated_3_5y"] = 4
        score["peg"] = 3.5
        result = compute_liquidation_status(manual, score, "WEAKENING", market, strong_benchmark())
        self.assertEqual(result["liquidation_status"], "ORANGE")
        self.assertEqual(result["recommended_action"], "REVIEW_TRIM_50")
        self.assertEqual(result["mechanical_sell_signal"], "TRIM_50")
        self.assertTrue(result["sell_review_required"])

    def test_unconfirmed_auto_fundamental_signals_do_not_trigger_trim(self):
        manual = strong_manual()
        manual["margin_or_profitability_under_pressure"] = True
        manual["moat_clear"] = False
        manual["auto_estimated_fields"] = ["margin_or_profitability_under_pressure", "moat_clear", "eps_growth_estimated_3_5y"]
        market = strong_market()
        score = compute_fundamental_score("MSFT", manual, market, strong_benchmark())
        score["eps_growth_estimated_3_5y"] = 4
        result = compute_liquidation_status(
            manual,
            score,
            "WEAKENING",
            market,
            strong_benchmark(),
            {"data_reliability_level": "MEDIUM", "auto_estimate_dependency": "HIGH"},
        )
        self.assertEqual(result["liquidation_status"], "YELLOW")
        self.assertEqual(result["mechanical_sell_signal"], "NONE")
        self.assertIn("Validation manuelle requise", " ".join(result["signals_detected"]))

    def test_history_can_escalate_one_confirmed_fundamental_signal_to_trim_25(self):
        manual = strong_manual()
        manual["margin_or_profitability_under_pressure"] = True
        score = compute_fundamental_score("MSFT", manual, strong_market(), strong_benchmark())
        result = compute_liquidation_status(
            manual,
            score,
            "WEAKENING",
            strong_market(),
            strong_benchmark(),
            {"data_reliability_level": "HIGH", "auto_estimate_dependency": "LOW"},
        )
        analysis = {
            **result,
            "ticker": "MSFT",
            "trend_status": "DETERIORATING",
            "trend_severity": 2,
            "data_reliability_level": "HIGH",
            "auto_estimate_dependency": "LOW",
        }

        apply_history_sell_discipline({"MSFT": analysis})

        self.assertEqual(analysis["liquidation_status"], "ORANGE")
        self.assertEqual(analysis["recommended_action"], "REVIEW_TRIM_25")
        self.assertEqual(analysis["mechanical_sell_signal"], "TRIM_25")

    def test_red_requires_three_extreme_conditions(self):
        manual = strong_manual()
        manual["catastrophic_fraud"] = True
        manual["catastrophic_moat_lost"] = True
        manual["catastrophic_dangerous_debt"] = True
        result = compute_liquidation_status(manual, {}, "BROKEN", strong_market(), strong_benchmark())
        self.assertEqual(result["liquidation_status"], "RED")
        self.assertEqual(result["recommended_action"], "LIQUIDATE_URGENT_REVIEW")


if __name__ == "__main__":
    unittest.main()
