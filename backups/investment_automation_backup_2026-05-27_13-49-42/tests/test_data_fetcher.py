import unittest

try:
    import pandas as pd
except ImportError:  # pragma: no cover
    pd = None

from src.data_fetcher import (
    MARKET_FIELDS,
    MarketDataFetcher,
    benchmark_metrics_for,
    _merge_news_context_items,
    _parse_google_news_rss,
    _should_fetch_public_news_context,
)


@unittest.skipIf(pd is None, "pandas is required for statement fallback tests")
class DataFetcherFallbackTest(unittest.TestCase):
    def test_benchmark_metrics_prefer_adjusted_total_return_fields(self):
        row = benchmark_metrics_for(
            "MSFT",
            {"MSFT": "VFV.TO"},
            {
                "VFV.TO": {
                    "cagr_10y": 0.08,
                    "adjusted_cagr_10y": 0.095,
                    "stock_return_1y": 0.06,
                    "adjusted_stock_return_1y": 0.07,
                    "total_return_basis": "ADJUSTED_CLOSE_TOTAL_RETURN_PROXY",
                }
            },
        )

        self.assertEqual(row["benchmark_return_basis"], "ADJUSTED_CLOSE_TOTAL_RETURN_PROXY")
        self.assertAlmostEqual(row["benchmark_10y_cagr"], 0.095)
        self.assertAlmostEqual(row["benchmark_usable_cagr"], 0.095)
        self.assertAlmostEqual(row["benchmark_return_1y"], 0.07)

    def test_fills_missing_fundamentals_from_free_financial_statements(self):
        class FakeInstrument:
            income_stmt = pd.DataFrame(
                {
                    "2025": [1000, 200, 500, 300, 5, 90],
                    "2024": [800, 120, 400, 210, 4, 100],
                },
                index=["Total Revenue", "Net Income", "Gross Profit", "Operating Income", "Diluted EPS", "Diluted Average Shares"],
            )
            balance_sheet = pd.DataFrame(
                {
                    "2025": [2000, 1000, 300, 400],
                    "2024": [1800, 900, 250, 300],
                },
                index=["Total Assets", "Stockholders Equity", "Cash And Cash Equivalents", "Total Debt"],
            )
            cashflow = pd.DataFrame(
                {
                    "2025": [260, -60, -30, 25],
                    "2024": [180, -40, -10, 20],
                },
                index=["Operating Cash Flow", "Capital Expenditure", "Repurchase Of Capital Stock", "Stock Based Compensation"],
            )

        payload = {field: None for field in MARKET_FIELDS}
        payload["current_price"] = 50
        notes = []
        fallback_fields = []

        MarketDataFetcher()._fill_from_financial_statements(payload, FakeInstrument(), notes, fallback_fields)

        self.assertAlmostEqual(payload["profit_margins"], 0.20)
        self.assertAlmostEqual(payload["gross_margins"], 0.50)
        self.assertAlmostEqual(payload["operating_margins"], 0.30)
        self.assertAlmostEqual(payload["revenue_growth"], 0.25)
        self.assertAlmostEqual(payload["earnings_growth"], 200 / 120 - 1)
        self.assertAlmostEqual(payload["return_on_equity"], 200 / 950)
        self.assertAlmostEqual(payload["return_on_assets"], 200 / 1900)
        self.assertAlmostEqual(payload["debt_to_equity"], 40)
        self.assertAlmostEqual(payload["operating_cash_flow"], 260)
        self.assertAlmostEqual(payload["capital_expenditures"], 60)
        self.assertAlmostEqual(payload["free_cash_flow"], 200)
        self.assertAlmostEqual(payload["free_cash_flow_margin"], 0.20)
        self.assertAlmostEqual(payload["fcf_conversion"], 1.0)
        self.assertAlmostEqual(payload["net_debt_to_fcf"], 0.5)
        self.assertAlmostEqual(payload["diluted_average_shares"], 90)
        self.assertAlmostEqual(payload["share_count_growth_1y"], -0.10)
        self.assertAlmostEqual(payload["share_repurchases"], 30)
        self.assertAlmostEqual(payload["stock_based_compensation"], 25)
        self.assertAlmostEqual(payload["sbc_to_revenue"], 0.025)
        self.assertAlmostEqual(payload["fcf_per_share"], 200 / 90)
        self.assertAlmostEqual(payload["trailing_pe"], 10)
        self.assertAlmostEqual(payload["peg"], 0.15)
        self.assertIn("yfinance financial statements", ", ".join(notes))
        self.assertIn("peg", fallback_fields)

    def test_fast_info_can_estimate_market_cap_from_shares_and_price(self):
        payload = {field: None for field in MARKET_FIELDS}
        payload["current_price"] = 25
        notes = []
        fallback_fields = []

        MarketDataFetcher()._fill_from_fast_info(
            payload,
            {"shares": 1000, "currency": "USD"},
            notes,
            fallback_fields,
        )

        self.assertEqual(payload["market_cap"], 25_000)
        self.assertEqual(payload["currency"], "USD")
        self.assertIn("market_cap", fallback_fields)

    def test_old_cache_gets_display_defaults_when_refresh_fails(self):
        cached = {
            "ticker": "MSFT",
            "source": "yfinance",
            "current_price": 100,
            "sma_200": 90,
            "stock_return_1y": 0.10,
            "market_cap": 1_000_000_000,
        }

        payload = MarketDataFetcher()._cached_with_defaults("MSFT", cached, "Actualisation impossible")

        self.assertEqual(payload["source"], "stale_cache")
        self.assertEqual(payload["data_source_notes"], ["cache local yfinance"])
        self.assertGreater(payload["data_fill_rate"], 0)

    def test_google_news_rss_parser_extracts_headlines_and_source(self):
        raw = """<?xml version="1.0" encoding="UTF-8"?>
        <rss><channel><item>
          <title>Intuit shares fall after earnings - Reuters</title>
          <link>https://news.google.com/rss/articles/example</link>
          <pubDate>Thu, 21 May 2026 10:00:00 GMT</pubDate>
          <source url="https://www.reuters.com">Reuters</source>
        </item></channel></rss>"""

        rows = _parse_google_news_rss(raw)

        self.assertEqual(rows[0]["title"], "Intuit shares fall after earnings - Reuters")
        self.assertEqual(rows[0]["publisher"], "Reuters")
        self.assertIn("news.google.com", rows[0]["url"])

    def test_public_news_context_triggers_only_for_price_weakness_or_watch(self):
        self.assertTrue(_should_fetch_public_news_context({"drawdown_from_12m_high": -0.20}))
        self.assertTrue(_should_fetch_public_news_context({"price_above_sma_200": False}))
        self.assertFalse(_should_fetch_public_news_context({"drawdown_from_12m_high": -0.02, "price_above_sma_200": True}))

    def test_news_context_merge_tracks_channels_and_dedupes(self):
        payload = {field: None for field in MARKET_FIELDS}
        payload["news_context_headlines"] = []
        payload["news_context_sources"] = []
        payload["news_context_urls"] = []
        payload["news_context_published_at"] = []
        payload["news_context_source_channels"] = []
        _merge_news_context_items(
            payload,
            [
                {"title": "A headline", "publisher": "Reuters", "url": "https://example.com/a", "published_at": "today"},
                {"title": "A headline", "publisher": "Reuters", "url": "https://example.com/a", "published_at": "today"},
            ],
            channel="Google News RSS",
        )

        self.assertEqual(payload["news_context_headlines"], ["A headline"])
        self.assertEqual(payload["news_context_sources"], ["Reuters"])
        self.assertEqual(payload["news_context_source_channels"], ["Google News RSS"])


if __name__ == "__main__":
    unittest.main()
