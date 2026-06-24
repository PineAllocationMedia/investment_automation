from __future__ import annotations

import unittest

from src.validation_priority_engine import build_validation_priority_rows
from tests.helpers import full_strong_analysis


def analysis_row(ticker: str, universe: str, allocated: bool = False) -> dict:
    row = full_strong_analysis(ticker)
    row.update(
        {
            "ticker": ticker,
            "ticker_display": ticker,
            "universe": universe,
            "company_name": f"{ticker} Inc.",
            "manual_required_criteria": ["fair_value"],
            "auto_estimated_fields": ["fair_value", "eps_growth_estimated_3_5y", "roic_5y_avg"],
            "score_evidence_level": "ESTIMATE_HEAVY",
            "auto_estimate_dependency": "HIGH",
            "capital_allocation_score": 72,
            "allocation_decision": "BUY / ADD" if allocated else "ELIGIBLE_BUT_NOT_SELECTED",
            "final_position_action": "BUY / ADD" if allocated else "WATCH",
            "ticker_validation_status": "OK",
        }
    )
    return row


class ValidationPriorityTests(unittest.TestCase):
    def test_allocated_core_missing_fair_value_ranks_high(self):
        rows = build_validation_priority_rows(
            {
                "CORE_PORTFOLIO": {"MSFT": analysis_row("MSFT", "CORE_PORTFOLIO", allocated=True)},
                "MARKET_SCANNER": {"AAPL": analysis_row("AAPL", "MARKET_SCANNER")},
            }
        )

        self.assertEqual(rows[0]["ticker"], "MSFT")
        self.assertEqual(rows[0]["field"], "fair_value")
        self.assertIn(rows[0]["priority"], {"TRES_HAUTE", "HAUTE"})
        self.assertTrue(rows[0]["bncd_report_needed"])

    def test_existing_research_report_stops_bncd_recommendation(self):
        rows = build_validation_priority_rows(
            {"CORE_PORTFOLIO": {"CSU.TO": analysis_row("CSU.TO", "CORE_PORTFOLIO", allocated=True)}},
            existing_reports={"CSU.TO": {"research_report_fields": ["fair_value", "moat_clear"]}},
        )

        self.assertTrue(rows)
        self.assertFalse(rows[0]["bncd_report_needed"])
        self.assertIn("rapport local existe", rows[0]["suggested_action"].lower())


if __name__ == "__main__":
    unittest.main()
