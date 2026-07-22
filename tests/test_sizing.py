import unittest

from tests.helpers import full_strong_analysis
from src.drift_engine import compute_drift_status
from src.sizing_engine import compute_capital_allocation_score, compute_winner_accelerated


class SizingTest(unittest.TestCase):
    def test_winner_accelerated_is_true_for_strong_profile(self):
        analysis = full_strong_analysis("MSFT")
        winner = compute_winner_accelerated(analysis)
        self.assertTrue(winner["winner_accelerated"])

    def test_capital_allocation_score_is_high_for_strong_profile(self):
        analysis = full_strong_analysis("MSFT")
        result = compute_capital_allocation_score(analysis, {"concentration_by_sector": {}, "top3_weight": 0})
        self.assertGreaterEqual(result["capital_allocation_score"], 70)
        self.assertGreaterEqual(result["business_quality_score"], 80)
        self.assertGreaterEqual(result["high_cagr_potential_score"], 80)
        self.assertIn("capital_allocation_confidence_range", result)
        self.assertLess(result["capital_allocation_score_low"], result["capital_allocation_score"])
        self.assertGreaterEqual(result["capital_allocation_score_high"], result["capital_allocation_score"])

    def test_high_cagr_score_penalizes_good_but_low_growth_business(self):
        analysis = full_strong_analysis("MSFT")
        analysis["eps_growth_estimated_3_5y"] = 3
        analysis["eps_growth_5y"] = 4
        analysis["sector_cagr_estimated"] = 4
        analysis["expected_cagr_quality"] = "LOW"
        result = compute_capital_allocation_score(analysis, {"concentration_by_sector": {}, "top3_weight": 0})
        self.assertGreater(result["business_quality_score"], result["high_cagr_potential_score"])

    def test_capital_score_penalizes_low_reliability_auto_estimates(self):
        analysis = full_strong_analysis("MSFT")
        base = compute_capital_allocation_score(analysis, {"concentration_by_sector": {}, "top3_weight": 0})
        analysis["data_reliability_score"] = 55
        analysis["auto_estimate_dependency"] = "HIGH"
        penalized = compute_capital_allocation_score(analysis, {"concentration_by_sector": {}, "top3_weight": 0})
        self.assertLess(penalized["capital_allocation_score"], base["capital_allocation_score"])
        self.assertIn("dépendance élevée aux estimations automatiques", str(penalized["capital_allocation_components"]["penalties"]))

    def test_capital_score_uses_score_evidence_penalty(self):
        analysis = full_strong_analysis("MSFT")
        base = compute_capital_allocation_score(analysis, {"concentration_by_sector": {}, "top3_weight": 0})
        analysis["score_evidence_level"] = "ESTIMATE_HEAVY"
        analysis["score_evidence_penalty"] = 7
        analysis["score_estimate_gap"] = 3
        penalized = compute_capital_allocation_score(analysis, {"concentration_by_sector": {}, "top3_weight": 0})

        self.assertLess(penalized["capital_allocation_score"], base["capital_allocation_score"])
        self.assertIn("preuve du score ESTIMATE_HEAVY", str(penalized["capital_allocation_components"]["penalties"]))
        self.assertIn(penalized["capital_allocation_confidence_label"], {"WIDE", "VERY_WIDE"})

    def test_confidence_range_does_not_change_central_capital_score(self):
        analysis = full_strong_analysis("MSFT")
        base = compute_capital_allocation_score(analysis, {"concentration_by_sector": {}, "top3_weight": 0})
        with_range_inputs = compute_capital_allocation_score(
            {
                **analysis,
                "score_confidence_range": "8.00-9.00",
                "conviction_confidence_range": "80.00-90.00",
                "capital_allocation_confidence_range": "70.00-80.00",
            },
            {"concentration_by_sector": {}, "top3_weight": 0},
        )

        self.assertEqual(with_range_inputs["capital_allocation_score"], base["capital_allocation_score"])

    def test_capital_score_penalizes_hot_cycle_risk(self):
        analysis = full_strong_analysis("LRCX")
        base = compute_capital_allocation_score(analysis, {"concentration_by_sector": {}, "top3_weight": 0})
        analysis["cycle_bubble_risk_level"] = "HIGH"
        analysis["cycle_bubble_penalty"] = 12
        penalized = compute_capital_allocation_score(analysis, {"concentration_by_sector": {}, "top3_weight": 0})

        self.assertLess(penalized["capital_allocation_score"], base["capital_allocation_score"])
        self.assertIn("risque cycle/bulle/tendance HIGH", str(penalized["capital_allocation_components"]["penalties"]))

    def test_capital_score_penalizes_possible_peak_earnings(self):
        analysis = full_strong_analysis("WDC")
        base = compute_capital_allocation_score(analysis, {"concentration_by_sector": {}, "top3_weight": 0})
        analysis["cycle_normalized_status"] = "POSSIBLE_PEAK_EARNINGS"
        penalized = compute_capital_allocation_score(analysis, {"concentration_by_sector": {}, "top3_weight": 0})

        self.assertLess(penalized["capital_allocation_score"], base["capital_allocation_score"])
        self.assertIn("profits possiblement au-dessus du cycle normalisé", str(penalized["capital_allocation_components"]["penalties"]))

    def test_capital_score_uses_market_regime_adjustment_without_hard_block(self):
        analysis = full_strong_analysis("MSFT")
        base = compute_capital_allocation_score(analysis, {"concentration_by_sector": {}, "top3_weight": 0})
        analysis["market_regime_allocation_adjustment"] = -3
        penalized = compute_capital_allocation_score(analysis, {"concentration_by_sector": {}, "top3_weight": 0})

        self.assertLess(penalized["capital_allocation_score"], base["capital_allocation_score"])
        self.assertGreaterEqual(penalized["capital_allocation_score"], 70)
        self.assertEqual(penalized["capital_allocation_components"]["market_regime_allocation_adjustment"], -3)

    def test_total_return_layer_rewards_durable_reinvested_dividend_moderately(self):
        analysis = full_strong_analysis("MA")
        base = compute_capital_allocation_score(analysis, {"concentration_by_sector": {}, "top3_weight": 0})
        analysis["dividend_yield"] = 0.012
        analysis["payout_ratio"] = 0.25
        analysis["debt_to_equity"] = 60
        improved = compute_capital_allocation_score(analysis, {"concentration_by_sector": {}, "top3_weight": 0})

        self.assertGreater(improved["capital_allocation_score"], base["capital_allocation_score"])
        self.assertEqual(improved["shareholder_return_profile"], "LOW_YIELD_GROWTH_COMPOUNDER")
        self.assertGreater(improved["shareholder_return_adjustment"], 0)

    def test_total_return_layer_penalizes_likely_yield_trap(self):
        analysis = full_strong_analysis("HIGHYIELD")
        base = compute_capital_allocation_score(analysis, {"concentration_by_sector": {}, "top3_weight": 0})
        analysis["dividend_yield"] = 0.075
        analysis["payout_ratio"] = 1.1
        analysis["debt_to_equity"] = 210
        analysis["eps_growth_estimated_3_5y"] = 2
        analysis["eps_growth_5y"] = 1
        penalized = compute_capital_allocation_score(analysis, {"concentration_by_sector": {}, "top3_weight": 0})

        self.assertLess(penalized["capital_allocation_score"], base["capital_allocation_score"])
        self.assertEqual(penalized["shareholder_return_profile"], "YIELD_TRAP_RISK")
        self.assertLess(penalized["shareholder_return_adjustment"], 0)

    def test_cash_flow_layer_rewards_real_cash_conversion(self):
        analysis = full_strong_analysis("MSFT")
        base = compute_capital_allocation_score(analysis, {"concentration_by_sector": {}, "top3_weight": 0})
        analysis.update(
            {
                "operating_cash_flow": 120,
                "capital_expenditures": 20,
                "free_cash_flow": 100,
                "total_revenue": 400,
                "net_income": 90,
                "total_debt": 50,
                "total_cash": 80,
                "free_cash_flow_growth": 0.16,
            }
        )
        improved = compute_capital_allocation_score(analysis, {"concentration_by_sector": {}, "top3_weight": 0})

        self.assertGreater(improved["capital_allocation_score"], base["capital_allocation_score"])
        self.assertEqual(improved["cash_flow_quality_status"], "EXCELLENT_CASH_COMPOUNDER")

    def test_cash_flow_layer_penalizes_weak_conversion(self):
        analysis = full_strong_analysis("WEAKCASH")
        base = compute_capital_allocation_score(analysis, {"concentration_by_sector": {}, "top3_weight": 0})
        analysis.update(
            {
                "operating_cash_flow": 25,
                "capital_expenditures": 40,
                "total_revenue": 500,
                "net_income": 80,
                "total_debt": 600,
                "total_cash": 50,
                "free_cash_flow_growth": -0.30,
            }
        )
        penalized = compute_capital_allocation_score(analysis, {"concentration_by_sector": {}, "top3_weight": 0})

        self.assertLess(penalized["capital_allocation_score"], base["capital_allocation_score"])
        self.assertIn(penalized["cash_flow_quality_status"], {"WEAK_CASH_CONVERSION", "CASH_FLOW_STRESS"})

    def test_shareholder_discipline_layer_rewards_buybacks_and_low_dilution(self):
        analysis = full_strong_analysis("AAPL")
        base = compute_capital_allocation_score(analysis, {"concentration_by_sector": {}, "top3_weight": 0})
        analysis.update(
            {
                "share_count_cagr_3y": -0.03,
                "share_count_growth_1y": -0.02,
                "buyback_yield": 0.04,
                "sbc_to_revenue": 0.02,
                "fcf_per_share_growth": 0.12,
            }
        )
        improved = compute_capital_allocation_score(analysis, {"concentration_by_sector": {}, "top3_weight": 0})

        self.assertGreater(improved["capital_allocation_score"], base["capital_allocation_score"])
        self.assertEqual(improved["shareholder_discipline_status"], "SHAREHOLDER_FRIENDLY")

    def test_shareholder_discipline_layer_penalizes_uncompensated_dilution(self):
        analysis = full_strong_analysis("DILUTE")
        base = compute_capital_allocation_score(analysis, {"concentration_by_sector": {}, "top3_weight": 0})
        analysis.update(
            {
                "share_count_cagr_3y": 0.16,
                "share_count_growth_1y": 0.18,
                "sbc_to_revenue": 0.22,
                "fcf_per_share_growth": -0.12,
            }
        )
        penalized = compute_capital_allocation_score(analysis, {"concentration_by_sector": {}, "top3_weight": 0})

        self.assertLess(penalized["capital_allocation_score"], base["capital_allocation_score"])
        self.assertEqual(penalized["shareholder_discipline_status"], "HIGH_DILUTION_RISK")

    def test_malcovered_valid_ticker_gets_limited_not_wrong_ticker_penalty(self):
        analysis = full_strong_analysis("CSU.TO")
        analysis["score_missing_data_count"] = 5
        analysis["ticker_validation_status"] = "ALIAS_USED"
        analysis["ticker_coverage_status"] = "NEEDS_BNCD_OR_MANUAL_CONFIRMATION"
        result = compute_capital_allocation_score(analysis, {"concentration_by_sector": {}, "top3_weight": 0})

        penalties = str(result["capital_allocation_components"]["penalties"])
        self.assertIn("données gratuites mal couvertes", penalties)
        self.assertNotIn("ticker ou données de marché à valider", penalties)

    def test_wrong_ticker_gets_blocking_penalty(self):
        analysis = full_strong_analysis("CCO")
        analysis["ticker_validation_status"] = "POSSIBLE_WRONG_TICKER"
        result = compute_capital_allocation_score(analysis, {"concentration_by_sector": {}, "top3_weight": 0})

        self.assertIn("ticker ou données de marché à valider", str(result["capital_allocation_components"]["penalties"]))

    def test_drift_rule_blocks_above_forty_percent(self):
        analysis = full_strong_analysis("MSFT")
        analysis["position_weight"] = 0.45
        drift = compute_drift_status(analysis)
        self.assertEqual(drift["drift_status"], "NO_ADD_ABOVE_40")


if __name__ == "__main__":
    unittest.main()
