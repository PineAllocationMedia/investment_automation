import unittest

from tests.helpers import full_strong_analysis
from src.tax_location_engine import compute_tax_location_report


class TaxLocationTest(unittest.TestCase):
    def test_high_cagr_in_non_registered_gets_alert(self):
        analyses = {"MSFT": full_strong_analysis("MSFT")}
        accounts = [{"ticker": "MSFT", "account_type": "NON_REGISTERED", "current_value": 1000}]
        exposures = {"MSFT": {"currency": "USD"}}
        report = compute_tax_location_report(accounts, [], analyses, exposures)
        self.assertIn("haut CAGR", report[0]["alert"])

    def test_tfsa_numbered_accounts_are_treated_as_tfsa(self):
        analyses = {"MSFT": full_strong_analysis("MSFT")}
        accounts = [{"ticker": "MSFT", "account_type": "TFSA2", "current_value": 1000, "shares": 2}]
        exposures = {"MSFT": {"currency": "CAD"}}

        report = compute_tax_location_report(accounts, [], analyses, exposures)

        self.assertEqual(report[0]["account_type"], "TFSA2")
        self.assertEqual(report[0]["account_tax_category"], "TFSA")
        self.assertEqual(report[0]["shares"], 2)
        self.assertNotIn("moins optimal", report[0]["alert"])


if __name__ == "__main__":
    unittest.main()
