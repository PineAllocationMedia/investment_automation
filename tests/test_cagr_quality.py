import unittest

from tests.helpers import strong_benchmark, strong_manual, strong_market
from src.cagr_quality_engine import compute_expected_cagr_quality, compute_quality_but_too_expensive
from src.scoring import compute_fundamental_score


class CagrQualityTest(unittest.TestCase):
    def test_expected_cagr_quality_is_very_high_for_exceptional_profile(self):
        manual = strong_manual()
        score = compute_fundamental_score("MSFT", manual, strong_market(), strong_benchmark())
        result = compute_expected_cagr_quality(manual, score, 90, "INTACT")
        self.assertEqual(result["expected_cagr_quality"], "VERY_HIGH")

    def test_quality_but_too_expensive_flags_extreme_peg(self):
        manual = strong_manual()
        manual["peg_manual"] = None
        market = strong_market()
        market["peg"] = 3.4
        score = compute_fundamental_score("MSFT", manual, market, strong_benchmark())
        score["score_total"] = 8
        result = compute_quality_but_too_expensive(manual, score)
        self.assertTrue(result["quality_but_too_expensive"])
        self.assertEqual(result["valuation_severity"], "MODERATELY_EXPENSIVE")

    def test_exceptional_quality_gets_limited_valuation_severity(self):
        manual = strong_manual()
        manual["valuation_vs_5y_avg_ok"] = False
        score = {
            "score_total": 8.8,
            "eps_growth_estimated_3_5y": 20,
            "roic_5y_avg": 24,
            "peg": 1.7,
            "forward_pe": 30,
            "price_to_fair_value": None,
        }

        result = compute_quality_but_too_expensive(manual, score)

        self.assertTrue(result["quality_but_too_expensive"])
        self.assertEqual(result["valuation_severity"], "EXPENSIVE_BUT_EXCEPTIONAL")

    def test_extreme_valuation_stays_blocking(self):
        manual = strong_manual()
        score = {
            "score_total": 9.0,
            "eps_growth_estimated_3_5y": 20,
            "roic_5y_avg": 24,
            "peg": 4.2,
            "forward_pe": 30,
        }

        result = compute_quality_but_too_expensive(manual, score)

        self.assertEqual(result["valuation_severity"], "EXTREMELY_EXPENSIVE")

    def test_high_company_quality_can_offset_weak_sector_proxy(self):
        manual = strong_manual()
        score = {
            "score_total": 8.0,
            "eps_growth_estimated_3_5y": 18,
            "roic_5y_avg": 30,
            "sector_cagr_estimated": 2,
            "price_to_fair_value": 1.0,
            "score_missing_data_count": 0,
        }

        result = compute_expected_cagr_quality(manual, score, 88, "INTACT")

        self.assertEqual(result["expected_cagr_quality"], "HIGH")

    def test_cyclical_or_financial_profile_caps_cagr_quality(self):
        manual = strong_manual()
        score = {
            "score_total": 9.5,
            "eps_growth_estimated_3_5y": 18,
            "roic_5y_avg": 30,
            "sector_cagr_estimated": 10,
            "price_to_fair_value": 1.0,
            "score_missing_data_count": 0,
            "business_profile": "RESOURCES",
        }

        result = compute_expected_cagr_quality(manual, score, 90, "INTACT")

        self.assertEqual(result["expected_cagr_quality"], "MEDIUM")
        self.assertEqual(result["expected_cagr_quality_raw"], "VERY_HIGH")


if __name__ == "__main__":
    unittest.main()
