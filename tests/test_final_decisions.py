import unittest

from main import apply_final_decisions


class FinalDecisionTest(unittest.TestCase):
    def test_allocation_and_sell_decisions_are_separate(self):
        analyses = {
            "MSFT": {
                "ticker": "MSFT",
                "thesis_status": "INTACT",
                "liquidation_status": "YELLOW",
                "sell_decision": "WATCH",
                "recommended_action": "WATCH",
                "add_eligibility_status": "ADD_ALLOWED_SMALL",
            }
        }

        apply_final_decisions(analyses, [{"destination": "MSFT", "montant": 100}])

        self.assertEqual(analyses["MSFT"]["allocation_decision"], "BUY / ADD")
        self.assertEqual(analyses["MSFT"]["sell_decision"], "WATCH")
        self.assertEqual(analyses["MSFT"]["final_position_action"], "ADD_WITH_MONITORING")

    def test_monitoring_alert_keeps_sell_decision_hold_but_marks_add_with_monitoring(self):
        analyses = {
            "MSFT": {
                "ticker": "MSFT",
                "thesis_status": "INTACT",
                "liquidation_status": "GREEN",
                "sell_decision": "HOLD",
                "recommended_action": "HOLD",
                "monitoring_status": "WATCH",
                "monitoring_reasons": ["Alerte technique: prix sous SMA 200."],
                "add_eligibility_status": "ADD_ALLOWED_SMALL",
            }
        }

        apply_final_decisions(analyses, [{"destination": "MSFT", "montant": 100}])

        self.assertEqual(analyses["MSFT"]["sell_decision"], "HOLD")
        self.assertEqual(analyses["MSFT"]["final_position_action"], "ADD_WITH_MONITORING")

    def test_sell_review_takes_priority_over_no_new_allocation(self):
        analyses = {
            "BAM": {
                "ticker": "BAM",
                "thesis_status": "WEAKENING",
                "liquidation_status": "ORANGE",
                "sell_decision": "REVIEW_TRIM_25",
                "recommended_action": "REVIEW_TRIM_25",
                "add_eligibility_status": "DO_NOT_ADD",
            }
        }

        apply_final_decisions(analyses, [])

        self.assertEqual(analyses["BAM"]["allocation_decision"], "DO_NOT_ADD")
        self.assertEqual(analyses["BAM"]["sell_decision"], "REVIEW_TRIM_25")
        self.assertEqual(analyses["BAM"]["final_position_action"], "REVIEW_TRIM_25")

    def test_deep_averaging_down_block_changes_add_side_only(self):
        analyses = {
            "MSFT": {
                "ticker": "MSFT",
                "thesis_status": "INTACT",
                "liquidation_status": "GREEN",
                "sell_decision": "HOLD",
                "recommended_action": "HOLD",
                "add_eligibility_status": "ADD_ALLOWED",
                "deep_averaging_down_blocked": True,
                "deep_averaging_down_reason": (
                    "DEEP AVERAGING DOWN BLOCKED: combined position return -25.00% <= -20%; "
                    "evidence reliability=MEDIUM."
                ),
            }
        }

        apply_final_decisions(analyses, [])

        self.assertEqual(analyses["MSFT"]["allocation_decision"], "DO_NOT_ADD")
        self.assertIn("combined position return -25.00%", analyses["MSFT"]["allocation_decision_reason"])
        self.assertEqual(analyses["MSFT"]["sell_decision"], "HOLD")
        self.assertEqual(analyses["MSFT"]["final_position_action"], "DO_NOT_ADD")


if __name__ == "__main__":
    unittest.main()
