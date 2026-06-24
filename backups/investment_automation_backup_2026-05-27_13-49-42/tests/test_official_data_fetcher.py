import unittest

from src.data_fetcher import MARKET_FIELDS, MarketDataFetcher
from src.official_data_fetcher import (
    is_sec_supported_ticker,
    parse_bank_of_canada_fx_payload,
    parse_sec_companyfacts,
)


class OfficialDataFetcherTest(unittest.TestCase):
    def test_parses_bank_of_canada_fx_payload(self):
        payload = {
            "observations": [
                {"d": "2026-05-12", "FXUSDCAD": {"v": "1.3600"}},
                {"d": "2026-05-13", "FXUSDCAD": {"v": "1.3725"}},
            ]
        }

        self.assertEqual(parse_bank_of_canada_fx_payload("FXUSDCAD", payload), 1.3725)

    def test_parses_sec_companyfacts_into_fundamental_fields(self):
        companyfacts = {
            "facts": {
                "us-gaap": {
                    "RevenueFromContractWithCustomerExcludingAssessedTax": {
                        "units": {
                            "USD": [
                                {"fy": 2023, "fp": "FY", "form": "10-K", "end": "2023-12-31", "filed": "2024-02-01", "val": 800},
                                {"fy": 2024, "fp": "FY", "form": "10-K", "end": "2024-12-31", "filed": "2025-02-01", "val": 1000},
                            ]
                        }
                    },
                    "NetIncomeLoss": {
                        "units": {
                            "USD": [
                                {"fy": 2023, "fp": "FY", "form": "10-K", "end": "2023-12-31", "filed": "2024-02-01", "val": 150},
                                {"fy": 2024, "fp": "FY", "form": "10-K", "end": "2024-12-31", "filed": "2025-02-01", "val": 200},
                            ]
                        }
                    },
                    "GrossProfit": {
                        "units": {"USD": [{"fy": 2024, "fp": "FY", "form": "10-K", "end": "2024-12-31", "filed": "2025-02-01", "val": 500}]}
                    },
                    "OperatingIncomeLoss": {
                        "units": {"USD": [{"fy": 2024, "fp": "FY", "form": "10-K", "end": "2024-12-31", "filed": "2025-02-01", "val": 300}]}
                    },
                    "NetCashProvidedByUsedInOperatingActivities": {
                        "units": {
                            "USD": [
                                {"fy": 2023, "fp": "FY", "form": "10-K", "end": "2023-12-31", "filed": "2024-02-01", "val": 190},
                                {"fy": 2024, "fp": "FY", "form": "10-K", "end": "2024-12-31", "filed": "2025-02-01", "val": 260},
                            ]
                        }
                    },
                    "PaymentsToAcquirePropertyPlantAndEquipment": {
                        "units": {
                            "USD": [
                                {"fy": 2023, "fp": "FY", "form": "10-K", "end": "2023-12-31", "filed": "2024-02-01", "val": 40},
                                {"fy": 2024, "fp": "FY", "form": "10-K", "end": "2024-12-31", "filed": "2025-02-01", "val": 60},
                            ]
                        }
                    },
                    "WeightedAverageNumberOfDilutedSharesOutstanding": {
                        "units": {
                            "shares": [
                                {"fy": 2023, "fp": "FY", "form": "10-K", "end": "2023-12-31", "filed": "2024-02-01", "val": 100},
                                {"fy": 2024, "fp": "FY", "form": "10-K", "end": "2024-12-31", "filed": "2025-02-01", "val": 90},
                            ]
                        }
                    },
                    "PaymentsForRepurchaseOfCommonStock": {
                        "units": {"USD": [{"fy": 2024, "fp": "FY", "form": "10-K", "end": "2024-12-31", "filed": "2025-02-01", "val": 30}]}
                    },
                    "ShareBasedCompensation": {
                        "units": {"USD": [{"fy": 2024, "fp": "FY", "form": "10-K", "end": "2024-12-31", "filed": "2025-02-01", "val": 25}]}
                    },
                    "Assets": {
                        "units": {"USD": [{"form": "10-K", "end": "2024-12-31", "filed": "2025-02-01", "val": 2000}]}
                    },
                    "StockholdersEquity": {
                        "units": {"USD": [{"form": "10-K", "end": "2024-12-31", "filed": "2025-02-01", "val": 1000}]}
                    },
                    "CashAndCashEquivalentsAtCarryingValue": {
                        "units": {"USD": [{"form": "10-K", "end": "2024-12-31", "filed": "2025-02-01", "val": 300}]}
                    },
                    "LongTermDebtCurrent": {
                        "units": {"USD": [{"form": "10-K", "end": "2024-12-31", "filed": "2025-02-01", "val": 50}]}
                    },
                    "LongTermDebtNoncurrent": {
                        "units": {"USD": [{"form": "10-K", "end": "2024-12-31", "filed": "2025-02-01", "val": 350}]}
                    },
                    "EarningsPerShareDiluted": {
                        "units": {"USD/shares": [{"fy": 2024, "fp": "FY", "form": "10-K", "end": "2024-12-31", "filed": "2025-02-01", "val": 5}]}
                    },
                }
            }
        }

        parsed = parse_sec_companyfacts(companyfacts)

        self.assertAlmostEqual(parsed["profit_margins"], 0.20)
        self.assertAlmostEqual(parsed["gross_margins"], 0.50)
        self.assertAlmostEqual(parsed["operating_margins"], 0.30)
        self.assertAlmostEqual(parsed["revenue_growth"], 0.25)
        self.assertAlmostEqual(parsed["earnings_growth"], 200 / 150 - 1)
        self.assertAlmostEqual(parsed["return_on_equity"], 0.20)
        self.assertAlmostEqual(parsed["return_on_assets"], 0.10)
        self.assertAlmostEqual(parsed["operating_cash_flow"], 260)
        self.assertAlmostEqual(parsed["capital_expenditures"], 60)
        self.assertAlmostEqual(parsed["free_cash_flow"], 200)
        self.assertAlmostEqual(parsed["free_cash_flow_margin"], 0.20)
        self.assertAlmostEqual(parsed["fcf_conversion"], 1.0)
        self.assertAlmostEqual(parsed["free_cash_flow_growth"], 200 / 150 - 1)
        self.assertAlmostEqual(parsed["diluted_average_shares"], 90)
        self.assertAlmostEqual(parsed["share_count_growth_1y"], -0.10)
        self.assertAlmostEqual(parsed["share_repurchases"], 30)
        self.assertAlmostEqual(parsed["stock_based_compensation"], 25)
        self.assertAlmostEqual(parsed["sbc_to_revenue"], 0.025)
        self.assertAlmostEqual(parsed["fcf_per_share"], 200 / 90)
        self.assertAlmostEqual(parsed["total_cash"], 300)
        self.assertAlmostEqual(parsed["total_debt"], 400)
        self.assertAlmostEqual(parsed["debt_to_equity"], 40)
        self.assertAlmostEqual(parsed["net_debt_to_fcf"], 0.5)
        self.assertEqual(parsed["diluted_eps_ttm_or_annual"], 5)
        self.assertEqual(parsed["sec_edgar_latest_fiscal_year"], 2024)

    def test_sec_ticker_filter_avoids_non_us_suffixes(self):
        self.assertTrue(is_sec_supported_ticker("MSFT"))
        self.assertTrue(is_sec_supported_ticker("BRK-B"))
        self.assertFalse(is_sec_supported_ticker("CSU.TO"))
        self.assertFalse(is_sec_supported_ticker("OR.PA"))

    def test_market_fetcher_prefers_bank_of_canada_fx_rate_when_available(self):
        fetcher = MarketDataFetcher()
        fetcher.official_data.fetch_bank_of_canada_fx_rate = lambda currency, refresh=False: {"rate": 1.37}
        fetcher._fetch_simple_fx_rate = lambda ticker: 1.11

        rates = fetcher.fetch_fx_rates_to_cad(["USD"])

        self.assertEqual(rates["USD"], 1.37)

    def test_market_fetcher_merges_sec_edgar_fundamentals(self):
        fetcher = MarketDataFetcher()
        fetcher.official_data.fetch_sec_fundamentals = lambda ticker: {
            "available": True,
            "source": "SEC EDGAR companyfacts",
            "profit_margins": 0.22,
            "revenue_growth": 0.18,
            "earnings_growth": 0.20,
            "diluted_eps_ttm_or_annual": 4,
            "sec_edgar_cik": 789019,
            "sec_edgar_company_name": "Microsoft Corporation",
            "sec_edgar_latest_filing_date": "2099-07-30",
            "sec_edgar_latest_fiscal_year": 2025,
        }
        payload = {field: None for field in MARKET_FIELDS}
        payload["current_price"] = 100
        payload["profit_margins"] = 0.10
        notes = []

        fetcher._fill_from_sec_edgar("MSFT", payload, notes)

        self.assertEqual(payload["profit_margins"], 0.10)
        self.assertEqual(payload["revenue_growth"], 0.18)
        self.assertEqual(payload["trailing_pe"], 25)
        self.assertEqual(payload["peg"], 1.25)
        self.assertEqual(payload["sec_edgar_cik"], 789019)
        self.assertIn("SEC EDGAR companyfacts", ", ".join(notes))
        self.assertIn("revenue_growth", payload["official_fundamental_fields"])
        self.assertIn("profit_margins", ", ".join(payload["official_data_conflicts"]))

    def test_sec_edgar_confirms_close_yfinance_fields_without_overwriting(self):
        fetcher = MarketDataFetcher()
        fetcher.official_data.fetch_sec_fundamentals = lambda ticker: {
            "available": True,
            "source": "SEC EDGAR companyfacts",
            "profit_margins": 0.205,
            "sec_edgar_latest_filing_date": "2099-07-30",
        }
        payload = {field: None for field in MARKET_FIELDS}
        payload["profit_margins"] = 0.20
        notes = []

        fetcher._fill_from_sec_edgar("MSFT", payload, notes)

        self.assertEqual(payload["profit_margins"], 0.20)
        self.assertIn("profit_margins", payload["official_confirmed_fields"])
        self.assertEqual(payload["official_data_conflicts"], [])

    def test_recent_sec_edgar_prioritizes_balance_sheet_fields(self):
        fetcher = MarketDataFetcher()
        fetcher.official_data.fetch_sec_fundamentals = lambda ticker: {
            "available": True,
            "source": "SEC EDGAR companyfacts",
            "total_debt": 400,
            "sec_edgar_latest_filing_date": "2099-07-30",
        }
        payload = {field: None for field in MARKET_FIELDS}
        payload["total_debt"] = 900
        notes = []

        fetcher._fill_from_sec_edgar("MSFT", payload, notes)

        self.assertEqual(payload["total_debt"], 400)
        self.assertIn("total_debt", payload["official_fundamental_fields"])


if __name__ == "__main__":
    unittest.main()
