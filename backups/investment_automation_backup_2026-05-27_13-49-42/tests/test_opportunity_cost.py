import unittest

from tests.helpers import strong_manual
from src.opportunity_cost_engine import compute_opportunity_cost_status


class OpportunityCostTest(unittest.TestCase):
    def test_clearly_better_than_vfv_requires_quality_and_clean_statuses(self):
        result = compute_opportunity_cost_status(
            strong_manual(),
            {"score_total": 8.5, "eps_growth_estimated_3_5y": 16},
            80,
            "HIGH",
            "INTACT",
            "GREEN",
            False,
        )
        self.assertEqual(result["opportunity_cost_status"], "CLEARLY_BETTER_THAN_VFV")

    def test_yellow_with_add_allowed_small_can_still_be_better_than_vfv(self):
        result = compute_opportunity_cost_status(
            strong_manual(),
            {"score_total": 8.5, "eps_growth_estimated_3_5y": 16},
            85,
            "HIGH",
            "INTACT",
            "YELLOW",
            False,
            "ADD_ALLOWED_SMALL",
        )

        self.assertEqual(result["opportunity_cost_status"], "CLEARLY_BETTER_THAN_VFV")


if __name__ == "__main__":
    unittest.main()
