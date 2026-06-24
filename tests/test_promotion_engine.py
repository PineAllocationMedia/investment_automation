import unittest

from tests.helpers import full_strong_analysis
from src.promotion_engine import build_promotion_candidate_rows, classify_promotion_candidate


class PromotionEngineTest(unittest.TestCase):
    def promotion_ready(self, ticker: str):
        candidate = full_strong_analysis(ticker)
        candidate["score_total"] = 8.8
        candidate["conviction_score"] = 87
        candidate["expected_cagr_quality"] = "HIGH"
        candidate["data_quality"] = "HIGH"
        candidate["data_reliability_level"] = "HIGH"
        candidate["auto_estimate_dependency"] = "LOW"
        candidate["automation_evidence_level"] = "STRONG"
        candidate["score_missing_data_count"] = 0
        candidate["requires_manual_validation_for_large_allocation"] = False
        candidate["business_quality_score"] = 88
        candidate["high_cagr_potential_score"] = 88
        candidate["quality_cagr_intersection"] = 88
        candidate["cycle_bubble_risk_level"] = "MEDIUM"
        candidate["ticker_needs_attention"] = False
        return candidate

    def test_exceptional_external_candidate_is_promoted_to_manual_review(self):
        external = self.promotion_ready("NVDA")
        external["quality_but_too_expensive"] = False
        core = full_strong_analysis("MSFT")
        core["score_total"] = 7.5
        core["conviction_score"] = 70

        result = classify_promotion_candidate(
            external,
            {"MSFT": core},
            {"concentration_by_sector": {}, "tech_ai_semi_weight": 0.20},
            "WATCHLIST",
        )

        self.assertEqual(result["promotion_status"], "PROMOTE_TO_CORE_REVIEW")
        self.assertIn("portfolio.csv", result["next_step"])

    def test_external_candidate_stays_watch_only_if_below_core_leader_bar(self):
        external = self.promotion_ready("NVDA")
        external["business_quality_score"] = 85
        external["high_cagr_potential_score"] = 82
        external["quality_cagr_intersection"] = 82
        core = self.promotion_ready("MSFT")
        core["score_total"] = 9.5
        core["conviction_score"] = 95
        core["business_quality_score"] = 95
        core["high_cagr_potential_score"] = 95
        core["quality_cagr_intersection"] = 95

        result = classify_promotion_candidate(
            external,
            {"MSFT": core},
            {"concentration_by_sector": {}, "tech_ai_semi_weight": 0.20},
            "WATCHLIST",
        )

        self.assertEqual(result["promotion_status"], "STRONG_WATCH_ONLY")

    def test_core_comparable_external_candidate_can_still_be_promoted(self):
        external = self.promotion_ready("NVDA")
        core = self.promotion_ready("MSFT")

        result = classify_promotion_candidate(
            external,
            {"MSFT": core},
            {"concentration_by_sector": {}, "tech_ai_semi_weight": 0.20},
            "WATCHLIST",
        )

        self.assertEqual(result["promotion_status"], "PROMOTE_TO_CORE_REVIEW")

    def test_low_relevance_benchmark_blocks_normal_promotion(self):
        external = self.promotion_ready("ALNY")
        external["benchmark_relevance_level"] = "LOW"
        core = full_strong_analysis("MSFT")
        core["score_total"] = 7.5
        core["conviction_score"] = 70

        result = classify_promotion_candidate(
            external,
            {"MSFT": core},
            {"concentration_by_sector": {}, "tech_ai_semi_weight": 0.20},
            "MARKET_SCANNER",
        )

        self.assertEqual(result["promotion_status"], "WAIT_FOR_BETTER_DATA_OR_PRICE")
        self.assertIn("comparaison sectorielle faible", result["reason"])

    def test_expensive_external_candidate_is_not_promoted_yet(self):
        external = self.promotion_ready("NVDA")
        external["quality_but_too_expensive"] = True
        core = full_strong_analysis("MSFT")
        core["score_total"] = 7.5
        core["conviction_score"] = 70

        result = classify_promotion_candidate(
            external,
            {"MSFT": core},
            {"concentration_by_sector": {}, "tech_ai_semi_weight": 0.20},
            "MARKET_SCANNER",
        )

        self.assertEqual(result["promotion_status"], "WAIT_FOR_BETTER_DATA_OR_PRICE")
        self.assertIn("valorisation", result["reason"])

    def test_extreme_cycle_blocks_otherwise_strong_promotion(self):
        external = self.promotion_ready("NVDA")
        external["score_total"] = 9.5
        external["conviction_score"] = 95
        external["expected_cagr_quality"] = "VERY_HIGH"
        external["cycle_bubble_risk_level"] = "EXTREME"
        core = full_strong_analysis("MSFT")
        core["score_total"] = 7.5
        core["conviction_score"] = 70

        result = classify_promotion_candidate(
            external,
            {"MSFT": core},
            {"concentration_by_sector": {}, "tech_ai_semi_weight": 0.20},
            "MARKET_SCANNER",
        )

        self.assertEqual(result["promotion_status"], "WAIT_FOR_BETTER_DATA_OR_PRICE")
        self.assertIn("cycle", result["reason"])

    def test_promotion_report_keeps_only_top_three_manual_promotions(self):
        weak_core = full_strong_analysis("MSFT")
        weak_core["score_total"] = 7.0
        weak_core["conviction_score"] = 65
        watchlist = {}
        for index, ticker in enumerate(["NVDA", "ADBE", "INTU", "TSM"], start=1):
            candidate = self.promotion_ready(ticker)
            candidate["conviction_score"] = 100 - index
            watchlist[ticker] = candidate

        rows = build_promotion_candidate_rows(
            watchlist,
            {},
            {"MSFT": weak_core},
            {"concentration_by_sector": {}, "tech_ai_semi_weight": 0.20},
        )
        promoted = [row for row in rows if row["promotion_status"] == "PROMOTE_TO_CORE_REVIEW"]

        self.assertEqual(len(promoted), 3)


if __name__ == "__main__":
    unittest.main()
