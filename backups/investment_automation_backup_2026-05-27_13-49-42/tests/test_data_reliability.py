import unittest
from datetime import date

from src.data_reliability_engine import (
    apply_reliability_cagr_cap,
    apply_reliability_confidence_cap,
    apply_reliability_conviction_cap,
    apply_reliability_opportunity_cap,
    compute_data_reliability,
    compute_research_report_freshness,
)


class DataReliabilityTest(unittest.TestCase):
    def test_strong_auto_inputs_keep_automation_without_bndc_dependency(self):
        manual = {
            "input_data_mode": "AUTO_ESTIMATED",
            "auto_source_quality": "HIGH",
            "manual_confidence_level": "HIGH",
            "auto_estimated_fields": [
                "roic_5y_avg",
                "net_margin_stable_or_expanding",
                "eps_growth_5y",
                "moat_clear",
                "eps_growth_estimated_3_5y",
                "sector_cagr_estimated",
                "fair_value",
                "valuation_vs_5y_avg_ok",
                "forward_pe_growth_acceptable",
                "management_quality_good",
                "balance_sheet_strong",
            ],
        }
        score = {"score_missing_data_count": 0}

        reliability = compute_data_reliability(manual, score)
        capped_manual = apply_reliability_confidence_cap(manual, reliability)
        capped_conviction = apply_reliability_conviction_cap({"conviction_score": 100, "conviction_category": "VERY_HIGH"}, reliability)
        capped_cagr = apply_reliability_cagr_cap({"expected_cagr_quality": "VERY_HIGH", "expected_cagr_reason": "Strong."}, reliability)
        capped_opportunity = apply_reliability_opportunity_cap(
            {"opportunity_cost_status": "CLEARLY_BETTER_THAN_VFV", "opportunity_cost_reason": "Strong."},
            reliability,
            "INTACT",
            "GREEN",
        )

        self.assertEqual(reliability["data_reliability_level"], "HIGH")
        self.assertEqual(reliability["auto_estimate_dependency"], "MEDIUM")
        self.assertEqual(reliability["automation_evidence_level"], "STRONG")
        self.assertEqual(capped_manual["manual_confidence_level"], "HIGH")
        self.assertEqual(capped_conviction["conviction_score"], 90)
        self.assertEqual(capped_cagr["expected_cagr_quality"], "HIGH")
        self.assertEqual(capped_opportunity["opportunity_cost_status"], "CLEARLY_BETTER_THAN_VFV")

    def test_weak_auto_inputs_still_require_validation(self):
        manual = {
            "input_data_mode": "AUTO_ESTIMATED",
            "auto_source_quality": "LOW",
            "manual_confidence_level": "HIGH",
            "auto_estimated_fields": [
                "eps_growth_estimated_3_5y",
                "fair_value",
                "moat_clear",
            ],
        }
        reliability = compute_data_reliability(manual, {"score_missing_data_count": 4})
        capped_conviction = apply_reliability_conviction_cap({"conviction_score": 100, "conviction_category": "VERY_HIGH"}, reliability)
        capped_cagr = apply_reliability_cagr_cap({"expected_cagr_quality": "VERY_HIGH", "expected_cagr_reason": "Strong."}, reliability)

        self.assertEqual(reliability["data_reliability_level"], "LOW")
        self.assertEqual(reliability["automation_evidence_level"], "WEAK")
        self.assertEqual(capped_conviction["conviction_score"], 55)
        self.assertEqual(capped_cagr["expected_cagr_quality"], "UNCERTAIN")

    def test_manual_or_confirmed_inputs_remain_high_reliability(self):
        manual = {
            "manual_confidence_level": "HIGH",
            "manual_override_fields": ["roic_5y_avg", "moat_clear", "fair_value"],
        }
        reliability = compute_data_reliability(manual, {"score_missing_data_count": 0})

        self.assertEqual(reliability["data_reliability_level"], "HIGH")
        self.assertEqual(reliability["auto_estimate_dependency"], "LOW")

    def test_sec_support_reduces_auto_dependency_without_overreacting_to_conflicts(self):
        manual = {
            "input_data_mode": "AUTO_ESTIMATED",
            "auto_source_quality": "HIGH",
            "manual_confidence_level": "HIGH",
            "auto_estimated_fields": [
                "roic_5y_avg",
                "net_margin_stable_or_expanding",
                "eps_growth_5y",
                "moat_clear",
                "eps_growth_estimated_3_5y",
                "sector_cagr_estimated",
                "fair_value",
                "valuation_vs_5y_avg_ok",
                "management_quality_good",
                "balance_sheet_strong",
            ],
            "official_supported_manual_fields": [
                "roic_5y_avg",
                "net_margin_stable_or_expanding",
                "eps_growth_5y",
                "eps_growth_estimated_3_5y",
                "balance_sheet_strong",
            ],
            "official_confirmed_manual_fields": ["net_margin_stable_or_expanding"],
            "official_data_conflicts": [
                "revenue_growth: yfinance=0.15, SEC=0.11, ecart=31%",
                "profit_margins: yfinance=0.32, SEC=0.25, ecart=28%",
            ],
        }

        reliability = compute_data_reliability(manual, {"score_missing_data_count": 0})

        self.assertEqual(reliability["data_reliability_level"], "HIGH")
        self.assertEqual(reliability["auto_estimate_dependency"], "LOW")
        self.assertEqual(reliability["official_evidence_level"], "OFFICIAL_SUPPORT")
        self.assertEqual(reliability["official_data_conflict_count"], 2)
        self.assertGreaterEqual(reliability["data_reliability_score"], 90)
        self.assertIn("roic_5y_avg", reliability["confirmed_critical_fields"])

    def test_sec_conflicts_only_are_a_light_warning_not_a_hard_block(self):
        manual = {
            "input_data_mode": "AUTO_ESTIMATED",
            "auto_source_quality": "HIGH",
            "auto_estimated_fields": [
                "roic_5y_avg",
                "net_margin_stable_or_expanding",
                "eps_growth_5y",
                "moat_clear",
                "eps_growth_estimated_3_5y",
                "sector_cagr_estimated",
                "fair_value",
                "valuation_vs_5y_avg_ok",
                "management_quality_good",
                "balance_sheet_strong",
            ],
            "official_data_conflicts": [
                "revenue_growth: yfinance=0.15, SEC=0.09, ecart=40%",
                "profit_margins: yfinance=0.30, SEC=0.20, ecart=33%",
                "total_debt: yfinance=10, SEC=15, ecart=50%",
            ],
        }

        reliability = compute_data_reliability(manual, {"score_missing_data_count": 0})

        self.assertEqual(reliability["data_reliability_level"], "HIGH")
        self.assertEqual(reliability["official_evidence_level"], "OFFICIAL_CONFLICTS_ONLY")
        self.assertGreaterEqual(reliability["data_reliability_score"], 85)

    def test_stale_research_report_reduces_reliability(self):
        manual = {
            "input_data_mode": "AUTO_WITH_RESEARCH_REPORT",
            "auto_source_quality": "HIGH",
            "manual_confidence_level": "HIGH",
            "auto_estimated_fields": ["eps_growth_5y"],
            "research_report_fields": ["fair_value", "moat_clear", "management_quality_good"],
            "research_report_sources": ["AAPL_2024-01-10_BNCD_Morningstar.pdf"],
            "research_report_dates": ["2024-01-10"],
        }

        freshness = compute_research_report_freshness(manual, today=date(2026, 4, 30))
        reliability = compute_data_reliability(manual, {"score_missing_data_count": 0})

        self.assertEqual(freshness["research_report_freshness_level"], "STALE")
        self.assertTrue(reliability["research_report_requires_fresh_validation"])
        self.assertLess(reliability["data_reliability_score"], 80)
        self.assertEqual(reliability["data_reliability_level"], "MEDIUM")

    def test_recent_research_report_has_no_freshness_penalty(self):
        manual = {
            "research_report_fields": ["fair_value", "moat_clear"],
            "research_report_sources": ["AAPL_2026-04-10_BNCD_Morningstar.pdf"],
            "research_report_dates": ["2026-04-10"],
        }

        freshness = compute_research_report_freshness(manual, today=date(2026, 4, 30))

        self.assertEqual(freshness["research_report_freshness_level"], "RECENT")
        self.assertEqual(freshness["research_report_freshness_penalty"], 0.0)


if __name__ == "__main__":
    unittest.main()
