import unittest

from src.cash_flow_quality_engine import compute_cash_flow_quality


class CashFlowQualityTest(unittest.TestCase):
    def test_excellent_cash_compounder_gets_positive_adjustment(self):
        result = compute_cash_flow_quality(
            {
                "ticker": "MSFT",
                "business_profile": "QUALITY_GROWTH_COMPOUNDER",
                "operating_cash_flow": 120,
                "capital_expenditures": 20,
                "free_cash_flow": 100,
                "total_revenue": 400,
                "net_income": 90,
                "total_debt": 50,
                "total_cash": 80,
                "free_cash_flow_growth": 0.16,
            }
        )

        self.assertEqual(result["cash_flow_quality_status"], "EXCELLENT_CASH_COMPOUNDER")
        self.assertGreater(result["cash_flow_quality_adjustment"], 0)
        self.assertAlmostEqual(result["free_cash_flow_margin"], 0.25)
        self.assertLess(result["net_debt_to_fcf"], 0)

    def test_weak_cash_conversion_gets_negative_adjustment(self):
        result = compute_cash_flow_quality(
            {
                "ticker": "WEAK",
                "business_profile": "QUALITY_GROWTH_COMPOUNDER",
                "operating_cash_flow": 25,
                "capital_expenditures": 40,
                "total_revenue": 500,
                "net_income": 80,
                "total_debt": 600,
                "total_cash": 50,
                "free_cash_flow_growth": -0.30,
            }
        )

        self.assertIn(result["cash_flow_quality_status"], {"WEAK_CASH_CONVERSION", "CASH_FLOW_STRESS"})
        self.assertLess(result["cash_flow_quality_adjustment"], 0)

    def test_bank_cash_flow_is_marked_not_primary(self):
        result = compute_cash_flow_quality(
            {
                "ticker": "JPM",
                "business_profile": "BANK",
                "free_cash_flow": -100,
                "total_revenue": 1000,
                "net_income": 200,
            }
        )

        self.assertEqual(result["cash_flow_quality_status"], "CASH_FLOW_MODEL_NOT_PRIMARY")
        self.assertEqual(result["cash_flow_quality_adjustment"], 0)

    def test_missing_cash_flow_is_only_slightly_penalized(self):
        result = compute_cash_flow_quality({"ticker": "CSU.TO", "business_profile": "QUALITY_GROWTH_COMPOUNDER"})

        self.assertEqual(result["cash_flow_quality_status"], "CASH_FLOW_UNCERTAIN")
        self.assertEqual(result["cash_flow_quality_adjustment"], -1)


if __name__ == "__main__":
    unittest.main()
