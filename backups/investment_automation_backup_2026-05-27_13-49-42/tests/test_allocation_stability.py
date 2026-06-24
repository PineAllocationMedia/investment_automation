import unittest

from src.allocation_stability_engine import apply_allocation_stability, compute_allocation_stability
from tests.helpers import full_strong_analysis


class AllocationStabilityTest(unittest.TestCase):
    def test_previous_allocation_gets_small_continuity_bonus_when_still_strong(self):
        analysis = full_strong_analysis("MSFT")
        analysis["capital_allocation_score"] = 82
        analysis["previous_capital_allocation_score"] = 81
        analysis["previous_allocation_decision"] = "BUY / ADD"
        analysis["trend_status"] = "STABLE"

        result = compute_allocation_stability(analysis)

        self.assertEqual(result["allocation_stability_status"], "SUPPORT_CONTINUITY")
        self.assertEqual(result["allocation_stability_adjustment"], 3.0)

    def test_deterioration_overrides_previous_allocation(self):
        analysis = full_strong_analysis("MSFT")
        analysis["capital_allocation_score"] = 78
        analysis["previous_capital_allocation_score"] = 85
        analysis["previous_allocation_decision"] = "BUY / ADD"
        analysis["trend_status"] = "DETERIORATING"
        analysis["trend_severity"] = 2

        result = compute_allocation_stability(analysis)

        self.assertEqual(result["allocation_stability_status"], "REDUCE_ON_DETERIORATION")
        self.assertLess(result["allocation_stability_adjustment"], 0)

    def test_new_leader_can_still_be_detected(self):
        analysis = full_strong_analysis("AVGO")
        analysis["capital_allocation_score"] = 86
        analysis["previous_capital_allocation_score"] = 74
        analysis["previous_allocation_decision"] = "NO_NEW_ALLOCATION"
        analysis["trend_status"] = "STABLE"

        result = compute_allocation_stability(analysis)

        self.assertEqual(result["allocation_stability_status"], "ALLOW_NEW_LEADER")
        self.assertEqual(result["allocation_stability_adjustment"], 1.0)

    def test_non_addable_position_is_not_protected_by_stability(self):
        analysis = full_strong_analysis("MSFT")
        analysis["capital_allocation_score"] = 90
        analysis["previous_capital_allocation_score"] = 90
        analysis["previous_allocation_decision"] = "BUY / ADD"
        analysis["thesis_status"] = "WEAKENING"

        result = compute_allocation_stability(analysis)

        self.assertEqual(result["allocation_stability_status"], "RESET_IF_NOT_ADDABLE")
        self.assertLess(result["allocation_stability_adjustment"], 0)

    def test_group_stability_requires_clear_edge_before_switching(self):
        previous_pick = full_strong_analysis("MSFT")
        challenger = full_strong_analysis("AVGO")
        previous_pick["capital_allocation_score"] = 84
        previous_pick["previous_allocation_decision"] = "BUY / ADD"
        previous_pick["trend_status"] = "STABLE"
        challenger["capital_allocation_score"] = 87
        challenger["trend_status"] = "STABLE"

        apply_allocation_stability({"MSFT": previous_pick, "AVGO": challenger})

        self.assertEqual(previous_pick["allocation_stability_status"], "CONTINUITY_IF_CLOSE")
        self.assertGreaterEqual(previous_pick["allocation_stability_adjustment"], 5.5)
        self.assertEqual(challenger["allocation_stability_status"], "CHALLENGER_NEEDS_CLEAR_EDGE")
        self.assertLess(challenger["allocation_stability_adjustment"], 0)

    def test_group_stability_allows_clear_new_leader(self):
        previous_pick = full_strong_analysis("MSFT")
        challenger = full_strong_analysis("AVGO")
        previous_pick["capital_allocation_score"] = 82
        previous_pick["previous_allocation_decision"] = "BUY / ADD"
        previous_pick["trend_status"] = "STABLE"
        challenger["capital_allocation_score"] = 92
        challenger["trend_status"] = "STABLE"

        apply_allocation_stability({"MSFT": previous_pick, "AVGO": challenger})

        self.assertEqual(challenger["allocation_stability_status"], "CLEAR_NEW_LEADER_ALLOWED")
        self.assertGreaterEqual(challenger["allocation_stability_adjustment"], 0)


if __name__ == "__main__":
    unittest.main()
