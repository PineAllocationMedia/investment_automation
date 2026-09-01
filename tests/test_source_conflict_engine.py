from __future__ import annotations

import unittest

from src.source_conflict_engine import (
    build_source_conflict_rows,
    classify_source_conflict,
    compact_source_conflict_rows,
    source_conflict_summary,
    summarize_conflict_profile,
)


class SourceConflictEngineTests(unittest.TestCase):
    def test_conflict_rows_make_official_source_conflicts_visible(self):
        rows = build_source_conflict_rows(
            {
                "CORE_PORTFOLIO": {
                    "MSFT": {
                        "ticker_display": "MSFT",
                        "universe": "CORE_PORTFOLIO",
                        "official_data_conflict_count": 3,
                        "official_data_conflicts": [
                            "profit_margins: yfinance=0.35, SEC=0.31",
                            "earnings_growth: yfinance=0.15, SEC=0.10",
                            "debt: yfinance=50B, SEC=55B",
                        ],
                        "official_source_policy": ["yfinance conservee car donnees plus fraiches"],
                    }
                }
            }
        )

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["severity"], "REVIEW")
        self.assertEqual(rows[0]["conflict_profile"], "MATERIAL_REVIEW")
        self.assertIn("MSFT", source_conflict_summary(rows))
        self.assertIn("Surveiller", rows[0]["recommended_action"])

    def test_compact_rows_are_non_blocking_when_no_conflict_exists(self):
        rows = compact_source_conflict_rows([])

        self.assertEqual(rows[0]["severity"], "AUCUNE_CONTRADICTION_VISIBLE")
        self.assertIn("Aucun conflit", rows[0]["recommended_action"])

    def test_technical_or_period_gaps_do_not_become_high_review_by_count_alone(self):
        rows = build_source_conflict_rows(
            {
                "CORE_PORTFOLIO": {
                    "APP": {
                        "ticker_display": "APP",
                        "universe": "CORE_PORTFOLIO",
                        "official_data_conflict_count": 5,
                        "official_data_conflicts": [
                            "capital_expenditures: yfinance=2.832e+07, SEC=4.776e+06, ecart=83%",
                            "free_cash_flow: yfinance=3.943e+09, SEC=2.094e+09, ecart=47%",
                            "fcf_per_share: yfinance=11.53, SEC=6.021, ecart=48%",
                            "total_revenue: yfinance=5.49e+09, SEC=4.88e+09, ecart=11%",
                            "share_repurchases: yfinance=2.1e+09, SEC=1.8e+09, ecart=14%",
                        ],
                    }
                }
            }
        )

        self.assertEqual(rows[0]["severity"], "WATCH")
        self.assertEqual(rows[0]["conflict_profile"], "TECHNICAL_OR_PERIOD_DIFFERENCE")
        self.assertLess(rows[0]["weighted_conflict_score"], 2)

    def test_directional_growth_conflict_stays_visible(self):
        conflict = "earnings_growth: yfinance=0.624, SEC=-0.0305, ecart=105%"
        classified = classify_source_conflict(conflict)
        profile = summarize_conflict_profile([conflict])

        self.assertEqual(classified["classification"], "DIRECTIONAL_REVIEW")
        self.assertEqual(profile["conflict_profile"], "DIRECTIONAL_REVIEW")
        self.assertEqual(profile["directional_conflict_count"], 1)

    def test_ftv_period_ambiguity_remains_visible_without_overwriting_source_policy(self):
        rows = build_source_conflict_rows(
            {
                "MARKET_SCANNER": {
                    "FTV": {
                        "ticker_display": "FTV",
                        "allocation_decision": "BUY",
                        "recommended_allocation_amount": 56.25,
                        "official_data_conflicts": [
                            "earnings_growth: yfinance=0.04, SEC=-0.3046, ecart=113%",
                            "return_on_assets: yfinance=0.03295, SEC=0.05, ecart=34%",
                            "revenue_growth: yfinance=0.079, SEC=-0.3326, ecart=124%",
                        ],
                        "official_source_policy": [
                            "Conflit source détecté: yfinance conservé pour éviter un écrasement ambigu."
                        ],
                    }
                }
            }
        )

        self.assertEqual(rows[0]["conflict_profile"], "DIRECTIONAL_REVIEW")
        self.assertEqual(rows[0]["directional_conflict_count"], 2)
        self.assertEqual(rows[0]["severity"], "HIGH_REVIEW")
        self.assertIn("yfinance conservé", rows[0]["source_policy"])
        self.assertIn("earnings_growth", rows[0]["conflicts"])
        self.assertIn("revenue_growth", rows[0]["conflicts"])


if __name__ == "__main__":
    unittest.main()
