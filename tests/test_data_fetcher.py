import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

try:
    import pandas as pd
except ImportError:  # pragma: no cover
    pd = None

from src.data_fetcher import (
    MARKET_FIELDS,
    REFRESH_INTER_TICKER_DELAY_SECONDS,
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

    def test_fetch_ticker_retries_before_success_and_saves_last_known_good(self):
        class FlakyFetcher(MarketDataFetcher):
            def __init__(self, cache_dir: Path) -> None:
                super().__init__(cache_dir=cache_dir, retry_attempts=2, retry_base_delay_seconds=0)
                self.calls = 0

            def _fetch_with_yfinance(self, ticker: str) -> dict:
                self.calls += 1
                if self.calls == 1:
                    raise RuntimeError("temporary outage")
                return {"ticker": ticker, "source": "yfinance", "current_price": 101, "data_source_notes": ["test"]}

        with TemporaryDirectory() as tmp:
            fetcher = FlakyFetcher(Path(tmp))
            payload = fetcher.fetch_ticker("MSFT", refresh=True)

            self.assertEqual(fetcher.calls, 2)
            self.assertEqual(payload["market_data_fetch_status"], "LIVE_SUCCESS")
            self.assertEqual(payload["market_data_fetch_attempts"], 2)
            self.assertEqual(payload["market_data_fallback_level"], "NONE")
            self.assertEqual(payload["current_price"], 101)
            self.assertTrue((Path(tmp) / "last_known_good" / "MSFT.json").exists())

    def test_fetch_ticker_falls_back_to_stale_cache_after_retry_failure(self):
        class BrokenFetcher(MarketDataFetcher):
            def _fetch_with_yfinance(self, ticker: str) -> dict:
                raise RuntimeError("source down")

        with TemporaryDirectory() as tmp:
            cache_path = Path(tmp) / "MSFT.json"
            cache_path.write_text(
                '{"ticker":"MSFT","source":"yfinance","current_price":100,"cache_schema_version":9}',
                encoding="utf-8",
            )
            fetcher = BrokenFetcher(cache_dir=Path(tmp), retry_attempts=2, retry_base_delay_seconds=0)
            payload = fetcher.fetch_ticker("MSFT", refresh=True)

            self.assertEqual(payload["source"], "stale_cache")
            self.assertEqual(payload["current_price"], 100)
            self.assertEqual(payload["market_data_fetch_status"], "FALLBACK_STALE_CACHE")
            self.assertEqual(payload["market_data_fallback_level"], "STALE_CACHE")
            self.assertIn("FETCH_FAILED", payload["market_data_warning_flags"])

    def test_stale_cache_file_does_not_block_a_live_retry(self):
        class RecoveredFetcher(MarketDataFetcher):
            def __init__(self, cache_dir: Path) -> None:
                super().__init__(cache_dir=cache_dir, retry_attempts=1, retry_base_delay_seconds=0)
                self.calls = 0

            def _fetch_with_yfinance(self, ticker: str) -> dict:
                self.calls += 1
                return {"ticker": ticker, "source": "yfinance", "current_price": 110}

        with TemporaryDirectory() as tmp:
            cache_path = Path(tmp) / "MSFT.json"
            cache_path.write_text(
                '{"ticker":"MSFT","source":"stale_cache","current_price":100,"cache_schema_version":9}',
                encoding="utf-8",
            )
            fetcher = RecoveredFetcher(Path(tmp))
            payload = fetcher.fetch_ticker("MSFT", refresh=False)

            self.assertEqual(fetcher.calls, 1)
            self.assertEqual(payload["source"], "yfinance")
            self.assertEqual(payload["current_price"], 110)

    def test_fetch_ticker_falls_back_to_last_known_good_when_cache_missing(self):
        class BrokenFetcher(MarketDataFetcher):
            def _fetch_with_yfinance(self, ticker: str) -> dict:
                raise RuntimeError("source down")

        with TemporaryDirectory() as tmp:
            lkg_dir = Path(tmp) / "last_known_good"
            lkg_dir.mkdir(parents=True)
            (lkg_dir / "MSFT.json").write_text(
                '{"ticker":"MSFT","source":"yfinance","current_price":99,"cache_schema_version":9}',
                encoding="utf-8",
            )
            fetcher = BrokenFetcher(cache_dir=Path(tmp), retry_attempts=1, retry_base_delay_seconds=0)
            payload = fetcher.fetch_ticker("MSFT", refresh=True)

            self.assertEqual(payload["source"], "last_known_good")
            self.assertEqual(payload["current_price"], 99)
            self.assertEqual(payload["market_data_fetch_status"], "FALLBACK_LAST_KNOWN_GOOD")
            self.assertEqual(payload["market_data_fallback_level"], "LAST_KNOWN_GOOD")

    def test_circuit_breaker_skips_live_calls_after_failures(self):
        class BrokenFetcher(MarketDataFetcher):
            def __init__(self, cache_dir: Path) -> None:
                super().__init__(
                    cache_dir=cache_dir,
                    retry_attempts=1,
                    retry_base_delay_seconds=0,
                    circuit_breaker_failure_threshold=1,
                    circuit_breaker_cooldown_seconds=300,
                )
                self.calls = 0

            def _fetch_with_yfinance(self, ticker: str) -> dict:
                self.calls += 1
                raise RuntimeError("source down")

        with TemporaryDirectory() as tmp:
            fetcher = BrokenFetcher(Path(tmp))
            first = fetcher.fetch_ticker("MSFT", refresh=True)
            second = fetcher.fetch_ticker("AAPL", refresh=True)

            self.assertEqual(fetcher.calls, 1)
            self.assertEqual(first["market_data_fetch_status"], "UNAVAILABLE")
            self.assertEqual(second["market_data_fetch_status"], "UNAVAILABLE")
            self.assertTrue(second["market_data_circuit_breaker_open"])
            self.assertIn("CIRCUIT_OPEN", second["market_data_warning_flags"])

    def test_fetch_all_refresh_adds_inter_ticker_delay_without_affecting_cached_runs(self):
        class StubFetcher(MarketDataFetcher):
            def __init__(self, cache_dir: Path) -> None:
                super().__init__(cache_dir=cache_dir, retry_attempts=1, retry_base_delay_seconds=0)
                self.calls: list[tuple[str, bool]] = []

            def fetch_ticker(self, ticker: str, refresh: bool = False) -> dict:
                self.calls.append((ticker, refresh))
                return {"ticker": ticker, "current_price": 100}

            def required_fields_for_gap_report(self, ticker: str, payload: dict) -> list[str]:
                return []

        with TemporaryDirectory() as tmp:
            fetcher = StubFetcher(Path(tmp))
            with patch("src.data_fetcher.time.sleep") as sleep_mock:
                fetcher.fetch_all(["MSFT", "AAPL"], {"MSFT": "VFV.TO"}, refresh=True)

            self.assertGreater(len(fetcher.calls), 1)
            self.assertEqual(sleep_mock.call_count, len(fetcher.calls) - 1)
            self.assertTrue(all(call.args == (REFRESH_INTER_TICKER_DELAY_SECONDS,) for call in sleep_mock.call_args_list))
            self.assertEqual(fetcher.last_fetch_all_delay_info["delay_seconds"], REFRESH_INTER_TICKER_DELAY_SECONDS)

            fetcher.calls = []
            with patch("src.data_fetcher.time.sleep") as sleep_mock:
                fetcher.fetch_all(["MSFT", "AAPL"], {"MSFT": "VFV.TO"}, refresh=False)

            sleep_mock.assert_not_called()
            self.assertEqual(fetcher.last_fetch_all_delay_info, {})

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
