import unittest

from src.canadian_data_fetcher import canadian_ticker_metadata, parse_stockanalysis_pages
from src.data_fetcher import MARKET_FIELDS, MarketDataFetcher


INCOME_HTML = """
<table>
  <tr><th>Year</th><th>2025</th><th>2024</th><th>2023</th><th>2022</th></tr>
  <tr><td>Revenue</td><td>1,200</td><td>1,000</td><td>850</td><td>700</td></tr>
  <tr><td>Gross Profit</td><td>800</td><td>600</td><td>500</td><td>420</td></tr>
  <tr><td>Operating Income</td><td>360</td><td>250</td><td>200</td><td>150</td></tr>
  <tr><td>Net Income</td><td>240</td><td>180</td><td>120</td><td>80</td></tr>
  <tr><td>Shares Outstanding</td><td>100</td><td>105</td><td>110</td><td>120</td></tr>
</table>
"""

BALANCE_HTML = """
<table>
  <tr><th>Year</th><th>2025</th><th>2024</th></tr>
  <tr><td>Total Assets</td><td>2,400</td><td>2,000</td></tr>
  <tr><td>Total Equity</td><td>1,200</td><td>1,000</td></tr>
  <tr><td>Cash & Equivalents</td><td>300</td><td>250</td></tr>
  <tr><td>Total Debt</td><td>500</td><td>550</td></tr>
</table>
"""

CASHFLOW_HTML = """
<table>
  <tr><th>Year</th><th>2025</th><th>2024</th><th>2023</th></tr>
  <tr><td>Operating Cash Flow</td><td>300</td><td>220</td><td>180</td></tr>
  <tr><td>Capital Expenditures</td><td>(50)</td><td>(40)</td><td>(35)</td></tr>
  <tr><td>Free Cash Flow</td><td>250</td><td>180</td><td>145</td></tr>
  <tr><td>Stock Based Compensation</td><td>12</td><td>10</td><td>8</td></tr>
  <tr><td>Share Repurchases</td><td>(30)</td><td>(20)</td><td>(15)</td></tr>
</table>
"""


class CanadianDataFetcherTest(unittest.TestCase):
    def test_canadian_ticker_metadata_detects_tsx_and_tsxv(self):
        self.assertEqual(canadian_ticker_metadata("CSU.TO")["exchange"], "tsx")
        self.assertEqual(canadian_ticker_metadata("TOI.V")["exchange"], "tsxv")

    def test_parse_stockanalysis_pages_extracts_core_ratios(self):
        parsed = parse_stockanalysis_pages(
            {"income": INCOME_HTML, "balance": BALANCE_HTML, "cashflow": CASHFLOW_HTML},
            ticker="CSU.TO",
        )

        self.assertTrue(parsed["available"])
        self.assertAlmostEqual(parsed["profit_margins"], 0.2)
        self.assertAlmostEqual(parsed["gross_margins"], 800 / 1200)
        self.assertAlmostEqual(parsed["operating_margins"], 0.3)
        self.assertAlmostEqual(parsed["revenue_growth"], 0.2)
        self.assertAlmostEqual(parsed["return_on_equity"], 0.2)
        self.assertAlmostEqual(parsed["free_cash_flow_margin"], 250 / 1200)
        self.assertAlmostEqual(parsed["net_debt_to_fcf"], (500 - 300) / 250)
        self.assertIn("free_cash_flow_margin", parsed["fields"])

    def test_data_fetcher_uses_canadian_fallback_without_overwriting_good_yfinance_values(self):
        fetcher = MarketDataFetcher()
        payload = {field: None for field in MARKET_FIELDS}
        payload.update(
            {
                "ticker": "CSU.TO",
                "source": "yfinance",
                "profit_margins": 0.21,
                "data_source_notes": [],
                "official_data_sources": [],
                "official_fundamental_fields": [],
                "official_confirmed_fields": [],
                "official_data_conflicts": [],
                "official_source_policy": [],
            }
        )
        fetcher.canadian_data.fetch_fundamentals = lambda *args, **kwargs: {
            "available": True,
            "source": "StockAnalysis Canadian financial pages",
            "coverage_status": "USABLE",
            "latest_period": "2025",
            "profit_margins": 0.205,
            "free_cash_flow_margin": 0.25,
            "total_revenue": 1200,
        }
        notes = []

        fetcher._fill_from_canadian_sources("CSU.TO", payload, notes)

        self.assertEqual(payload["profit_margins"], 0.21)
        self.assertEqual(payload["free_cash_flow_margin"], 0.25)
        self.assertEqual(payload["total_revenue"], 1200)
        self.assertIn("profit_margins", payload["canadian_confirmed_fields"])
        self.assertIn("free_cash_flow_margin", payload["canadian_fundamental_fields"])
        self.assertIn("StockAnalysis Canadian financial pages", payload["official_data_sources"])
        self.assertIn("free_cash_flow_margin", payload["official_fundamental_fields"])


if __name__ == "__main__":
    unittest.main()
