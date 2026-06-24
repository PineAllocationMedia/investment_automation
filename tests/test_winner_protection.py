import unittest

from src.winner_protection_engine import apply_winner_protection, compute_winner_protection
from tests.helpers import full_strong_analysis


class WinnerProtectionTest(unittest.TestCase):
    def test_intact_winner_is_left_to_run(self):
        analysis = full_strong_analysis("MSFT")
        analysis.update(
            {
                "shares": 10,
                "average_cost": 100,
                "current_price": 250,
                "current_value": 2500,
                "liquidation_status": "GREEN",
                "thesis_status": "INTACT",
                "trend_status": "STABLE",
                "data_reliability_level": "HIGH",
                "auto_estimate_dependency": "LOW",
            }
        )

        result = compute_winner_protection(analysis, {"personal_high_price": 260})

        self.assertEqual(result["winner_protection_status"], "HOLD_RUN_WINNER")
        self.assertEqual(result["winner_protection_action"], "HOLD_RUN_WINNER")
        self.assertGreater(result["unrealized_gain_percent"], 1.0)

    def test_winner_pullback_without_fundamental_deterioration_does_not_trim(self):
        analysis = full_strong_analysis("MSFT")
        analysis.update(
            {
                "shares": 10,
                "average_cost": 100,
                "current_price": 210,
                "current_value": 2100,
                "liquidation_status": "GREEN",
                "thesis_status": "INTACT",
                "trend_status": "STABLE",
                "data_reliability_level": "HIGH",
                "auto_estimate_dependency": "LOW",
            }
        )

        result = compute_winner_protection(analysis, {"personal_high_price": 300})

        self.assertEqual(result["winner_protection_status"], "WATCH_WINNER_PULLBACK")
        self.assertEqual(result["winner_protection_action"], "WATCH")

    def test_confirmed_deterioration_can_trigger_trim_review(self):
        analysis = full_strong_analysis("MSFT")
        analysis.update(
            {
                "shares": 10,
                "average_cost": 100,
                "current_price": 190,
                "current_value": 1900,
                "liquidation_status": "YELLOW",
                "thesis_status": "WEAKENING",
                "trend_status": "DETERIORATING",
                "trend_severity": 2,
                "confirmed_fundamental_sell_signals": ["Fondamental confirme: marge sous pression."],
                "data_reliability_level": "HIGH",
                "auto_estimate_dependency": "LOW",
            }
        )

        result = compute_winner_protection(analysis, {"personal_high_price": 300})

        self.assertEqual(result["winner_protection_status"], "TRIM_25_REVIEW")
        self.assertEqual(result["winner_protection_action"], "REVIEW_TRIM_25")

    def test_sell_overlay_updates_liquidation_when_trim_review_is_triggered(self):
        analysis = full_strong_analysis("MSFT")
        analysis.update(
            {
                "shares": 10,
                "average_cost": 100,
                "current_price": 190,
                "current_value": 1900,
                "liquidation_status": "YELLOW",
                "thesis_status": "WEAKENING",
                "trend_status": "DETERIORATING",
                "trend_severity": 2,
                "confirmed_fundamental_sell_signals": ["Fondamental confirme: marge sous pression."],
                "data_reliability_level": "HIGH",
                "auto_estimate_dependency": "LOW",
            }
        )

        analyses = {"MSFT": analysis}
        apply_winner_protection(analyses, {"MSFT": {"personal_high_price": 300}})

        self.assertEqual(analyses["MSFT"]["liquidation_status"], "ORANGE")
        self.assertEqual(analyses["MSFT"]["sell_decision"], "REVIEW_TRIM_25")
        self.assertEqual(analyses["MSFT"]["mechanical_sell_signal"], "TRIM_25")


if __name__ == "__main__":
    unittest.main()
