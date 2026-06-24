import unittest

from src.shareholder_discipline_engine import compute_shareholder_discipline


class ShareholderDisciplineTest(unittest.TestCase):
    def test_shareholder_friendly_business_gets_positive_adjustment(self):
        result = compute_shareholder_discipline(
            {
                "ticker": "AAPL",
                "share_count_cagr_3y": -0.03,
                "share_count_growth_1y": -0.02,
                "buyback_yield": 0.04,
                "sbc_to_revenue": 0.02,
                "fcf_per_share_growth": 0.12,
            }
        )

        self.assertEqual(result["shareholder_discipline_status"], "SHAREHOLDER_FRIENDLY")
        self.assertGreater(result["shareholder_discipline_adjustment"], 0)

    def test_high_dilution_without_compensation_gets_watch_risk(self):
        result = compute_shareholder_discipline(
            {
                "ticker": "DILUTE",
                "share_count_cagr_3y": 0.16,
                "share_count_growth_1y": 0.18,
                "sbc_to_revenue": 0.22,
                "fcf_per_share_growth": -0.12,
            }
        )

        self.assertEqual(result["shareholder_discipline_status"], "HIGH_DILUTION_RISK")
        self.assertEqual(result["shareholder_discipline_monitoring_status"], "WATCH")
        self.assertLess(result["shareholder_discipline_adjustment"], 0)

    def test_dilution_compensated_by_per_share_growth_is_not_panic_signal(self):
        result = compute_shareholder_discipline(
            {
                "ticker": "GROWTH",
                "share_count_cagr_3y": 0.09,
                "sbc_to_revenue": 0.08,
                "fcf_per_share_growth": 0.25,
            }
        )

        self.assertIn(result["shareholder_discipline_status"], {"ACCEPTABLE_DILUTION", "DILUTION_WATCH"})
        self.assertNotEqual(result["shareholder_discipline_status"], "HIGH_DILUTION_RISK")

    def test_missing_data_is_only_slightly_penalized(self):
        result = compute_shareholder_discipline({"ticker": "CSU.TO"})

        self.assertEqual(result["shareholder_discipline_status"], "DILUTION_DATA_UNCERTAIN")
        self.assertEqual(result["shareholder_discipline_adjustment"], -0.5)


if __name__ == "__main__":
    unittest.main()
