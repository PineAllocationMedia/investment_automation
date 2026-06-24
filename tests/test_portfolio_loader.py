import unittest

from src.portfolio_loader import (
    account_locations_from_portfolio_rows,
    enrich_portfolio_with_market_data,
    infer_quote_currency,
    load_portfolio,
)
from src.winner_protection_engine import compute_winner_protection


class PortfolioLoaderTest(unittest.TestCase):
    def test_average_cost_cad_is_loaded_and_acquisition_value_is_computed(self):
        rows = load_portfolio_fixture([{"ticker": "MSFT", "shares": "4", "average_cost_cad": "250"}])

        self.assertEqual(rows[0]["ticker"], "MSFT")
        self.assertEqual(rows[0]["shares"], 4.0)
        self.assertEqual(rows[0]["average_cost"], 250.0)
        self.assertEqual(rows[0]["average_cost_cad"], 250.0)
        self.assertEqual(rows[0]["average_cost_currency"], "CAD")
        self.assertEqual(rows[0]["acquisition_value"], 1000.0)

    def test_average_cost_currency_can_be_usd_and_is_converted_to_cad(self):
        rows = load_portfolio_fixture(
            [{"ticker": "MSFT", "shares": "4", "average_cost": "100", "average_cost_currency": "USD", "account_type": "TFSA"}]
        )
        market = {"MSFT": {"current_price": 150, "currency": "USD"}}

        enriched = enrich_portfolio_with_market_data(rows, market, {"CAD": 1.0, "USD": 1.35})

        self.assertEqual(enriched[0]["account_type"], "TFSA")
        self.assertEqual(enriched[0]["average_cost"], 100.0)
        self.assertEqual(enriched[0]["average_cost_currency"], "USD")
        self.assertEqual(enriched[0]["average_cost_cad"], 135.0)
        self.assertEqual(enriched[0]["acquisition_value"], 400.0)
        self.assertEqual(enriched[0]["acquisition_value_currency"], "USD")
        self.assertEqual(enriched[0]["acquisition_value_cad"], 540.0)
        self.assertEqual(enriched[0]["current_value"], 810.0)

    def test_current_value_is_calculated_in_cad_for_usd_quote(self):
        rows = [{"ticker": "MSFT", "shares": 4, "average_cost": 250, "average_cost_currency": "CAD", "acquisition_value": 1000}]
        market = {"MSFT": {"current_price": 300, "currency": "USD"}}

        enriched = enrich_portfolio_with_market_data(rows, market, {"CAD": 1.0, "USD": 1.35})

        self.assertEqual(enriched[0]["current_price_cad"], 405.0)
        self.assertEqual(enriched[0]["current_value"], 1620.0)
        self.assertEqual(enriched[0]["current_value_currency"], "CAD")
        self.assertEqual(enriched[0]["portfolio_valuation_source"], "shares_x_market_price_fx_to_CAD")

    def test_zero_share_candidate_stays_at_zero_current_value(self):
        rows = [{"ticker": "INTU", "shares": 0, "average_cost": None, "acquisition_value": None, "account_type": ""}]
        market = {"INTU": {"current_price": 700, "currency": "USD"}}

        enriched = enrich_portfolio_with_market_data(rows, market, {"CAD": 1.0, "USD": 1.35})

        self.assertEqual(enriched[0]["current_value"], 0.0)
        self.assertEqual(enriched[0]["portfolio_valuation_source"], "no_position")

    def test_missing_average_cost_comma_is_repaired_when_currency_and_account_are_shifted(self):
        rows = load_portfolio_fixture([{"ticker": "VFV.TO", "shares": "0.5569", "average_cost": "USD", "average_cost_currency": "TFSA2"}])

        self.assertIsNone(rows[0]["average_cost"])
        self.assertEqual(rows[0]["average_cost_currency"], None)
        self.assertEqual(rows[0]["account_type"], "TFSA2")

    def test_account_locations_can_be_derived_from_portfolio_rows(self):
        rows = [
            {"ticker": "MSFT", "account_type": "TFSA1", "current_value": 1200, "shares": 3},
            {"ticker": "MSFT", "account_type": "TFSA2", "current_value": 800, "shares": 2},
            {"ticker": "VFV.TO", "account_type": "FHSA", "current_value": 500, "shares": 1},
        ]

        locations = account_locations_from_portfolio_rows(rows)

        self.assertEqual(locations[0]["account_type"], "TFSA1")
        self.assertEqual(locations[0]["account_tax_category"], "TFSA")
        self.assertEqual(locations[0]["shares"], 3)
        self.assertEqual(locations[1]["account_type"], "TFSA2")
        self.assertEqual(locations[1]["account_tax_category"], "TFSA")
        self.assertEqual(locations[2]["account_type"], "FHSA")
        self.assertEqual(locations[2]["current_value"], 500)

    def test_account_locations_fallback_is_used_when_portfolio_account_type_is_blank(self):
        rows = [{"ticker": "MSFT", "account_type": "", "current_value": 1200}]
        fallback = [{"ticker": "MSFT", "account_type": "RRSP", "current_value": 1000}]

        locations = account_locations_from_portfolio_rows(rows, fallback)

        self.assertEqual(locations[0]["account_type"], "RRSP")

    def test_winner_protection_compares_cad_price_to_cad_cost(self):
        analysis = {
            "shares": 4,
            "average_cost": 185.19,
            "average_cost_currency": "USD",
            "average_cost_cad": 250,
            "acquisition_value": 740.76,
            "acquisition_value_currency": "USD",
            "acquisition_value_cad": 1000,
            "current_value": 1620,
            "current_price": 300,
            "quote_currency": "USD",
            "quote_to_cad_rate": 1.35,
            "liquidation_status": "GREEN",
            "thesis_status": "INTACT",
            "trend_status": "STABLE",
            "data_reliability_level": "HIGH",
            "auto_estimate_dependency": "LOW",
        }

        result = compute_winner_protection(analysis, {"personal_high_price": 420})

        self.assertEqual(result["current_price_cad"], 405.0)
        self.assertAlmostEqual(result["unrealized_gain_percent"], 0.62, places=2)

    def test_infer_quote_currency_defaults_canadian_suffix_to_cad(self):
        self.assertEqual(infer_quote_currency("CSU.TO"), "CAD")
        self.assertEqual(infer_quote_currency("TOI.V"), "CAD")
        self.assertEqual(infer_quote_currency("MSFT"), "USD")


def load_portfolio_fixture(rows):
    from pathlib import Path
    from tempfile import TemporaryDirectory

    from src.utils import write_csv_records

    with TemporaryDirectory() as directory:
        path = Path(directory) / "portfolio.csv"
        columns = sorted({key for row in rows for key in row})
        write_csv_records(path, rows, columns)
        return load_portfolio(path)


if __name__ == "__main__":
    unittest.main()
