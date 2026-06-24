import unittest

from src.ticker_resolver import (
    apply_ticker_attention_flags,
    company_names_match,
    resolve_portfolio_rows,
    resolve_ticker,
    ticker_coverage_assessment,
)


class TickerResolverTest(unittest.TestCase):
    def test_alias_resolves_common_canadian_ticker(self):
        aliases = {"CSU": {"resolved_ticker": "CSU.TO", "intended_company_name": "Constellation Software Inc."}}
        self.assertEqual(resolve_ticker("CSU", aliases), "CSU.TO")

    def test_portfolio_rows_merge_alias_with_canonical_ticker(self):
        aliases = {"CSU": {"resolved_ticker": "CSU.TO", "intended_company_name": "Constellation Software Inc."}}
        metadata = {}
        rows = resolve_portfolio_rows(
            [{"ticker": "CSU", "current_value": 100}, {"ticker": "CSU.TO", "current_value": 50}],
            aliases,
            metadata,
            "portfolio",
        )
        self.assertEqual(rows[0]["ticker"], "CSU.TO")
        self.assertEqual(rows[0]["current_value"], 150.0)
        self.assertTrue(metadata["CSU.TO"]["ticker_alias_used"])

    def test_attention_star_when_major_manual_data_missing_and_alias_in_parentheses(self):
        analysis = {
            "ticker": "TOI.V",
            "current_price": 120,
            "score_missing_data_count": 4,
            "data_quality": "MEDIUM",
            "long_name": "Topicus.com Inc.",
        }
        metadata = {
            "input_tickers": ["TOI"],
            "resolved_ticker": "TOI.V",
            "ticker_alias_used": True,
            "intended_company_name": "Topicus.com Inc.",
            "alias_reasons": ["TOI sans suffixe correspond a une autre compagnie."],
        }
        apply_ticker_attention_flags(analysis, metadata)
        self.assertEqual(analysis["ticker_display"], "TOI.V (TOI)*")
        self.assertNotIn("TICKER_ALIAS_USED", analysis["ticker_issue_reasons"])
        self.assertIn("MANUAL_REQUIRED", analysis["ticker_issue_reasons"])

    def test_alias_only_uses_parentheses_without_attention_star(self):
        analysis = {
            "ticker": "SBGSY",
            "current_price": 50,
            "score_missing_data_count": 0,
            "data_quality": "HIGH",
            "long_name": "Schneider Electric S.E.",
        }
        metadata = {
            "input_tickers": ["SBGSY", "SCHN"],
            "resolved_ticker": "SBGSY",
            "ticker_alias_used": True,
            "intended_company_name": "Schneider Electric S.E.",
            "alias_reasons": ["Utilise l'ADR Schneider Electric comme approximation gratuite."],
        }

        apply_ticker_attention_flags(analysis, metadata)

        self.assertEqual(analysis["ticker_display"], "SBGSY (SCHN)")
        self.assertFalse(analysis["ticker_needs_attention"])
        self.assertEqual(analysis["ticker_issue_reasons"], [])

    def test_small_manual_gap_does_not_add_star_by_itself(self):
        analysis = {
            "ticker": "AAPL",
            "current_price": 250,
            "score_missing_data_count": 1,
            "data_quality": "HIGH",
            "long_name": "Apple Inc.",
        }
        apply_ticker_attention_flags(analysis, {"input_tickers": ["AAPL"]})
        self.assertEqual(analysis["ticker_display"], "AAPL")
        self.assertEqual(analysis["ticker_issue_reasons"], [])

    def test_company_name_mismatch_is_detectable(self):
        self.assertTrue(company_names_match("Cameco", "Cameco Corporation"))
        self.assertFalse(company_names_match("Topicus.com Inc.", "The Oncology Institute, Inc."))

    def test_known_company_short_names_match_yfinance_names(self):
        self.assertTrue(company_names_match("TSMC", "Taiwan Semiconductor Manufacturing Company Limited"))
        self.assertTrue(company_names_match("Ritchie Bros", "RB Global, Inc."))

    def test_company_mismatch_flags_possible_wrong_ticker_with_suggestion(self):
        analysis = {
            "ticker": "CCO",
            "current_price": 10,
            "long_name": "Clear Channel Outdoor Holdings, Inc.",
            "company_name": "Cameco Corporation",
            "currency": "CAD",
            "score_missing_data_count": 0,
            "data_quality": "HIGH",
        }

        apply_ticker_attention_flags(analysis, {"input_tickers": ["CCO"], "intended_company_name": "Cameco Corporation"})

        self.assertEqual(analysis["ticker_validation_status"], "POSSIBLE_WRONG_TICKER")
        self.assertEqual(analysis["ticker_coverage_status"], "POSSIBLE_WRONG_TICKER")
        self.assertIn("POSSIBLE_WRONG_TICKER", analysis["ticker_issue_reasons"])
        self.assertIn("CCO.TO", analysis["suggested_yahoo_tickers"])

    def test_low_free_data_coverage_is_separate_from_wrong_ticker(self):
        analysis = {
            "ticker": "CSU.TO",
            "current_price": 4200,
            "long_name": "Constellation Software Inc.",
            "company_name": "Constellation Software Inc.",
            "score_missing_data_count": 5,
            "data_quality": "LOW",
        }

        coverage = ticker_coverage_assessment(analysis, {"input_tickers": ["CSU"], "ticker_alias_used": True})

        self.assertEqual(coverage["ticker_validation_status"], "ALIAS_USED")
        self.assertEqual(coverage["ticker_coverage_status"], "NEEDS_BNCD_OR_MANUAL_CONFIRMATION")
        self.assertEqual(coverage["free_data_coverage_class"], "VALID_TICKER_POOR_FREE_COVERAGE")


if __name__ == "__main__":
    unittest.main()
