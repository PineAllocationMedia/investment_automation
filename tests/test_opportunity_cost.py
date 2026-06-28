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

    def test_exceptional_but_expensive_is_similar_not_worse_than_vfv(self):
        result = compute_opportunity_cost_status(
            strong_manual(),
            {
                "score_total": 8.8,
                "eps_growth_estimated_3_5y": 20,
                "valuation_severity": "EXPENSIVE_BUT_EXCEPTIONAL",
            },
            92,
            "VERY_HIGH",
            "INTACT",
            "GREEN",
            True,
            "ADD_ALLOWED",
        )

        self.assertEqual(result["opportunity_cost_status"], "SIMILAR_TO_VFV")

    def test_extremely_expensive_stays_worse_than_vfv(self):
        result = compute_opportunity_cost_status(
            strong_manual(),
            {
                "score_total": 9.0,
                "eps_growth_estimated_3_5y": 20,
                "valuation_severity": "EXTREMELY_EXPENSIVE",
            },
            95,
            "VERY_HIGH",
            "INTACT",
            "GREEN",
            True,
            "ADD_ALLOWED",
        )

        self.assertEqual(result["opportunity_cost_status"], "WORSE_THAN_VFV")

    def test_after_tax_yield_fields_are_reported_without_changing_quality_gate(self):
        result = compute_opportunity_cost_status(
            strong_manual(),
            {"score_total": 8.5, "eps_growth_estimated_3_5y": 16, "dividend_yield": 0.04},
            80,
            "HIGH",
            "INTACT",
            "GREEN",
            False,
            gross_yield=0.04,
            account_type="NON_REGISTERED",
            is_canadian_eligible_dividend=True,
            is_us_dividend=False,
            vfv_gross_yield=0.012,
            vfv_account_type="NON_REGISTERED",
        )

        self.assertEqual(result["opportunity_cost_status"], "CLEARLY_BETTER_THAN_VFV")
        self.assertEqual(result["gross_yield"], 0.04)
        self.assertIn("after_tax_yield_adjusted", result)
        self.assertIn("after-tax est. (approx.)", result["tax_adjustment_note"])
        self.assertIn("vfv_after_tax_yield_adjusted", result)


if __name__ == "__main__":
    unittest.main()
