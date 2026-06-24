import unittest

from src.sell_validation_checklist_engine import sell_validation_checklist_rows


class SellValidationChecklistTest(unittest.TestCase):
    def test_confirmed_orange_trim_requires_manual_review(self):
        analyses = {
            "XYZ": {
                "ticker": "XYZ",
                "sell_status": "ORANGE",
                "liquidation_status": "ORANGE",
                "sell_decision": "REVIEW_TRIM_25",
                "mechanical_sell_signal": "TRIM_25",
                "confirmed_fundamental_sell_signals": [
                    "Fondamental confirmé: marge sous pression.",
                    "Fondamental confirmé: moat affaibli.",
                ],
                "technical_or_valuation_signals": ["Alerte technique: prix sous SMA 200."],
                "winner_protection_status": "NONE",
                "trend_status": "DETERIORATING",
                "trend_severity": 2,
                "data_reliability_score": 82,
            }
        }

        rows = sell_validation_checklist_rows(analyses)

        self.assertEqual(rows[0]["validation_level"], "CONFIRMED_TRIM_REVIEW")
        self.assertEqual(rows[0]["manual_action_required"], "YES")
        self.assertIn("Confirmée (2)", rows[0]["fundamental_evidence"])

    def test_technical_signal_only_is_watch_not_sell(self):
        analyses = {
            "ABC": {
                "ticker": "ABC",
                "sell_status": "GREEN",
                "liquidation_status": "GREEN",
                "sell_decision": "HOLD",
                "technical_or_valuation_signals": ["Alerte technique: prix sous SMA 200."],
                "monitoring_status": "WATCH",
                "winner_protection_status": "WATCH_WINNER_PULLBACK",
                "winner_protection_action": "WATCH",
                "winner_protection_reason": "Winner en correction normale.",
                "trend_status": "STABLE",
                "data_reliability_score": 78,
            }
        }

        rows = sell_validation_checklist_rows(analyses)

        self.assertEqual(rows[0]["validation_level"], "WATCH_ONLY_NO_SELL")
        self.assertEqual(rows[0]["manual_action_required"], "NO")
        self.assertIn("pas de vente automatique", rows[0]["checklist_summary"].lower())

    def test_inactive_green_position_is_hidden_by_default(self):
        analyses = {
            "MSFT": {
                "ticker": "MSFT",
                "sell_status": "GREEN",
                "liquidation_status": "GREEN",
                "sell_decision": "HOLD",
                "winner_protection_status": "HOLD_RUN_WINNER",
                "monitoring_status": "NORMAL",
            }
        }

        self.assertEqual(sell_validation_checklist_rows(analyses), [])
        self.assertEqual(len(sell_validation_checklist_rows(analyses, active_only=False)), 1)


if __name__ == "__main__":
    unittest.main()
