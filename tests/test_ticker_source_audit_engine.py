from __future__ import annotations

import unittest

from src.ticker_source_audit_engine import build_ticker_source_audit_context, ticker_source_audit_rows


class TickerSourceAuditEngineTests(unittest.TestCase):
    def test_core_ticker_review_and_core_conflicts_create_review_status(self):
        context = build_ticker_source_audit_context(
            ticker_memory_rows=[
                {
                    "ticker": "ABC.TO",
                    "source": "CORE_PORTFOLIO",
                    "ticker_memory_status": "NEEDS_TICKER_REVIEW",
                }
            ],
            source_conflict_rows=[
                {
                    "ticker": "MSFT",
                    "universe": "CORE_PORTFOLIO",
                    "severity": "HIGH_REVIEW",
                    "conflict_count": 4,
                },
                {
                    "ticker": "EXT",
                    "universe": "MARKET_SCANNER",
                    "severity": "HIGH_REVIEW",
                    "conflict_count": 8,
                },
            ],
            ticker_issue_rows=[],
        )

        self.assertEqual(context["ticker_source_quality_status"], "WATCH")
        self.assertLess(context["ticker_source_quality_score"], 90)
        self.assertIn("ABC.TO", context["ticker_source_review_tickers"])
        self.assertIn("MSFT", context["ticker_source_review_tickers"])
        self.assertNotIn("EXT", context["ticker_source_review_tickers"])
        self.assertEqual(context["ticker_review_tickers"], "ABC.TO")
        self.assertEqual(context["source_conflict_review_tickers"], "MSFT")

    def test_multiple_priority_issues_create_review_status(self):
        context = build_ticker_source_audit_context(
            ticker_issue_rows=[
                {"ticker_display": "BAD1", "ticker_validation_status": "NO_MARKET_DATA"},
                {"ticker_display": "BAD2", "ticker_coverage_status": "POSSIBLE_WRONG_TICKER"},
                {"ticker_display": "BAD3", "ticker_validation_status": "NO_MARKET_DATA"},
            ]
        )

        self.assertEqual(context["ticker_source_quality_status"], "REVIEW")
        rows = ticker_source_audit_rows(context)
        self.assertEqual(rows[0]["status"], "REVIEW")

    def test_empty_context_is_neutral_not_blocking(self):
        context = build_ticker_source_audit_context()

        self.assertEqual(context["ticker_source_quality_status"], "WATCH")
        self.assertEqual(context["ticker_source_quality_score"], 72.0)
        self.assertIn("aucune", context["ticker_source_guardrail"].lower() if context["ticker_source_quality_status"] == "OK" else "aucune modification automatique")


if __name__ == "__main__":
    unittest.main()
