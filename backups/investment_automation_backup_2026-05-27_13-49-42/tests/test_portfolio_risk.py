import unittest

from src.portfolio_risk_engine import compute_portfolio_risk


class PortfolioRiskTest(unittest.TestCase):
    def test_concentration_alerts_are_reported(self):
        rows = [{"ticker": "MSFT", "current_value": 700}, {"ticker": "VFV.TO", "current_value": 300}]
        sectors = {"MSFT": "Cloud Computing", "VFV.TO": "S&P 500 ETF"}
        exposures = {
            "MSFT": {"region": "United States", "currency": "USD", "factor_exposure": ["technology", "cloud"]},
            "VFV.TO": {"region": "United States", "currency": "CAD", "factor_exposure": ["broad_market"]},
        }
        risk = compute_portfolio_risk(rows, sectors, exposures)
        self.assertGreater(risk["top3_weight"], 0.60)
        self.assertTrue(any(alert["risk_type"] == "action" for alert in risk["alerts"]))

    def test_zero_value_unknown_positions_do_not_pollute_concentration_tables(self):
        rows = [{"ticker": "MSFT", "current_value": 1000}, {"ticker": "UNKNOWN", "current_value": 0}]
        sectors = {"MSFT": "Cloud Computing"}
        exposures = {"MSFT": {"region": "United States", "currency": "USD", "factor_exposure": ["technology"]}}

        risk = compute_portfolio_risk(rows, sectors, exposures)

        self.assertNotIn("Unknown", risk["concentration_by_sector"])
        self.assertNotIn("Unknown", risk["concentration_by_region"])


if __name__ == "__main__":
    unittest.main()
