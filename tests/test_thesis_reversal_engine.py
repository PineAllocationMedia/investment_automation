import copy
import unittest

from src.thesis_reversal_engine import build_thesis_reversal_audit_rows, compact_thesis_reversal_summary


class ThesisReversalEngineTest(unittest.TestCase):
    def test_no_previous_history_returns_none(self):
        rows = build_thesis_reversal_audit_rows(
            {
                "CORE_PORTFOLIO": {
                    "MSFT": {
                        "ticker": "MSFT",
                        "thesis_status": "WEAKENING",
                        "history_reference_count": 0,
                    }
                }
            }
        )

        self.assertEqual(rows[0]["thesis_reversal_status"], "NONE")
        self.assertEqual(rows[0]["conclusion_basis"], "INSUFFICIENT_HISTORY")
        self.assertEqual(rows[0]["allocation_impact"], "NONE_AUDIT_ONLY")

    def test_intact_to_intact_returns_none(self):
        rows = build_thesis_reversal_audit_rows(
            {
                "CORE_PORTFOLIO": {
                    "MSFT": {
                        "ticker": "MSFT",
                        "previous_thesis_status": "INTACT",
                        "thesis_status": "INTACT",
                        "history_reference_count": 2,
                    }
                }
            }
        )

        self.assertEqual(rows[0]["thesis_reversal_status"], "NONE")
        self.assertEqual(rows[0]["manual_review_priority"], "LOW")

    def test_intact_to_weakening_with_confirmed_evidence_is_review(self):
        rows = build_thesis_reversal_audit_rows(
            {
                "CORE_PORTFOLIO": {
                    "AAPL": {
                        "ticker": "AAPL",
                        "previous_thesis_status": "INTACT",
                        "thesis_status": "WEAKENING",
                        "history_reference_count": 3,
                        "confirmed_fundamental_sell_signals": ["Fondamental confirmé: moat affaibli."],
                        "score_total_change": -1.2,
                        "conviction_score_change": -12,
                        "data_reliability_level": "HIGH",
                    }
                }
            }
        )

        self.assertEqual(rows[0]["thesis_reversal_status"], "REVIEW")
        self.assertEqual(rows[0]["thesis_reversal_severity"], 2)
        self.assertEqual(rows[0]["conclusion_basis"], "FUNDAMENTAL")
        self.assertFalse(rows[0]["data_quality_driven"])

    def test_intact_to_broken_is_high_severity(self):
        rows = build_thesis_reversal_audit_rows(
            {
                "CORE_PORTFOLIO": {
                    "BB": {
                        "ticker": "BB",
                        "previous_thesis_status": "INTACT",
                        "thesis_status": "BROKEN",
                        "history_reference_count": 4,
                        "confirmed_fundamental_sell_signals": ["Fondamental confirmé: croissance brisée."],
                        "data_reliability_level": "HIGH",
                    }
                }
            }
        )

        self.assertEqual(rows[0]["thesis_reversal_status"], "BROKEN")
        self.assertEqual(rows[0]["thesis_reversal_severity"], 3)
        self.assertEqual(rows[0]["manual_review_priority"], "CRITICAL")

    def test_weakening_to_broken_can_remain_review_when_data_quality_driven(self):
        rows = build_thesis_reversal_audit_rows(
            {
                "CORE_PORTFOLIO": {
                    "SHOP.TO": {
                        "ticker": "SHOP.TO",
                        "previous_thesis_status": "WEAKENING",
                        "thesis_status": "BROKEN",
                        "history_reference_count": 2,
                        "data_reliability_level": "LOW",
                        "score_evidence_level": "INSUFFICIENT_CONFIRMED",
                    }
                }
            }
        )

        self.assertEqual(rows[0]["thesis_reversal_status"], "REVIEW")
        self.assertTrue(rows[0]["data_quality_driven"])
        self.assertEqual(rows[0]["conclusion_basis"], "DATA_QUALITY_DRIVEN")

    def test_intact_to_uncertain_from_weak_data_is_watch(self):
        rows = build_thesis_reversal_audit_rows(
            {
                "CORE_PORTFOLIO": {
                    "CSU.TO": {
                        "ticker": "CSU.TO",
                        "previous_thesis_status": "INTACT",
                        "thesis_status": "UNCERTAIN",
                        "history_reference_count": 2,
                        "score_missing_data_count": 5,
                    }
                }
            }
        )

        self.assertEqual(rows[0]["thesis_reversal_status"], "WATCH")
        self.assertTrue(rows[0]["data_quality_driven"])

    def test_high_scores_with_deteriorating_thesis_flags_contradiction(self):
        rows = build_thesis_reversal_audit_rows(
            {
                "CORE_PORTFOLIO": {
                    "META": {
                        "ticker": "META",
                        "previous_thesis_status": "INTACT",
                        "thesis_status": "WEAKENING",
                        "history_reference_count": 2,
                        "confirmed_fundamental_sell_signals": ["Fondamental confirmé: marge sous pression."],
                        "score_total": 8.4,
                        "conviction_score": 82,
                        "capital_allocation_score": 76,
                    }
                }
            }
        )

        self.assertTrue(rows[0]["score_contradiction_flag"])
        self.assertIn("Contradiction", rows[0]["reason_fr"])

    def test_missing_fields_do_not_crash_and_do_not_mutate_analysis(self):
        analyses = {"CORE_PORTFOLIO": {"NANO.V": {"ticker": "NANO.V"}}}
        before = copy.deepcopy(analyses)

        rows = build_thesis_reversal_audit_rows(analyses)

        self.assertEqual(analyses, before)
        self.assertEqual(rows[0]["thesis_reversal_status"], "NONE")
        self.assertEqual(rows[0]["allocation_impact"], "NONE_AUDIT_ONLY")

    def test_compact_summary_limits_alerts_and_is_audit_only(self):
        rows = [
            {"ticker": "A", "thesis_reversal_status": "WATCH"},
            {"ticker": "B", "thesis_reversal_status": "REVIEW"},
            {"ticker": "C", "thesis_reversal_status": "BROKEN"},
            {"ticker": "D", "thesis_reversal_status": "NONE"},
        ]

        summary = compact_thesis_reversal_summary(rows, limit=2)

        self.assertIn("A=WATCH", summary)
        self.assertIn("B=REVIEW", summary)
        self.assertIn("Audit-only", summary)
        self.assertNotIn("D=NONE", summary)


if __name__ == "__main__":
    unittest.main()
