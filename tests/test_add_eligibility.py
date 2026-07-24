import unittest

from src.add_eligibility_engine import compute_add_eligibility_status


class AddEligibilityTest(unittest.TestCase):
    def test_green_intact_position_allows_normal_add(self):
        result = compute_add_eligibility_status(
            {
                "ticker": "MSFT",
                "thesis_status": "INTACT",
                "liquidation_status": "GREEN",
                "data_reliability_level": "HIGH",
            }
        )

        self.assertEqual(result["add_eligibility_status"], "ADD_ALLOWED")
        self.assertEqual(result["add_eligibility_size"], "NORMAL")

    def test_yellow_technical_only_allows_small_add(self):
        result = compute_add_eligibility_status(
            {
                "ticker": "MSFT",
                "thesis_status": "INTACT",
                "liquidation_status": "YELLOW",
                "data_reliability_level": "HIGH",
                "expected_cagr_quality": "HIGH",
                "conviction_score": 85,
                "confirmed_fundamental_sell_signals": [],
                "technical_or_valuation_signals": ["Prix sous SMA 200."],
            }
        )

        self.assertEqual(result["add_eligibility_status"], "ADD_ALLOWED_SMALL")
        self.assertEqual(result["add_eligibility_size"], "LIMITED")

    def test_green_with_monitoring_watch_allows_small_add(self):
        result = compute_add_eligibility_status(
            {
                "ticker": "MSFT",
                "thesis_status": "INTACT",
                "liquidation_status": "GREEN",
                "monitoring_status": "WATCH",
                "data_reliability_level": "HIGH",
                "expected_cagr_quality": "HIGH",
                "conviction_score": 85,
                "confirmed_fundamental_sell_signals": [],
                "technical_or_valuation_signals": ["Prix sous SMA 200."],
            }
        )

        self.assertEqual(result["add_eligibility_status"], "ADD_ALLOWED_SMALL")
        self.assertEqual(result["add_eligibility_size"], "LIMITED")

    def test_confirmed_fundamental_signal_blocks_add(self):
        result = compute_add_eligibility_status(
            {
                "ticker": "MSFT",
                "thesis_status": "INTACT",
                "liquidation_status": "YELLOW",
                "data_reliability_level": "HIGH",
                "expected_cagr_quality": "HIGH",
                "conviction_score": 85,
                "confirmed_fundamental_sell_signals": ["Moat affaibli confirmé."],
            }
        )

        self.assertEqual(result["add_eligibility_status"], "DO_NOT_ADD")

    def test_unconfirmed_fundamental_warning_requires_manual_review(self):
        result = compute_add_eligibility_status(
            {
                "ticker": "MSFT",
                "thesis_status": "INTACT",
                "liquidation_status": "YELLOW",
                "data_reliability_level": "HIGH",
                "expected_cagr_quality": "HIGH",
                "conviction_score": 85,
                "technical_or_valuation_signals": ["Validation manuelle requise: marge sous pression possible."],
            }
        )

        self.assertEqual(result["add_eligibility_status"], "RESEARCH_REPORT_REQUIRED_BEFORE_ADD")


if __name__ == "__main__":
    unittest.main()
