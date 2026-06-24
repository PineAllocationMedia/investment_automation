import unittest
from unittest.mock import patch

from src.fund_price_fallback_engine import fetch_fund_price_fallback


class FakeResponse:
    def __init__(self, *, json_data=None, text="", status_code=200):
        self._json_data = json_data
        self.text = text
        self.status_code = status_code

    def json(self):
        if isinstance(self._json_data, Exception):
            raise self._json_data
        return self._json_data


class FundPriceFallbackTest(unittest.TestCase):
    def test_yahoo_chart_fallback_extracts_price_and_trend(self):
        closes = list(range(100, 361))
        highs = [value + 1 for value in closes]

        def fake_get(url, **kwargs):
            self.assertIn("query1.finance.yahoo.com", url)
            return FakeResponse(
                json_data={
                    "chart": {
                        "result": [
                            {
                                "meta": {
                                    "regularMarketPrice": 360,
                                    "currency": "CAD",
                                    "instrumentType": "ETF",
                                    "shortName": "Test ETF",
                                },
                                "indicators": {"quote": [{"close": closes, "high": highs}]},
                            }
                        ],
                        "error": None,
                    }
                }
            )

        payload = fetch_fund_price_fallback("QQC.TO", is_fund_hint=True, getter=fake_get)

        self.assertEqual(payload["source"], "yahoo_chart_fallback")
        self.assertEqual(payload["current_price"], 360)
        self.assertEqual(payload["currency"], "CAD")
        self.assertEqual(payload["quote_type"], "ETF")
        self.assertIsNotNone(payload["sma_200"])
        self.assertIsNotNone(payload["stock_return_1y"])

    def test_official_fund_nav_fallback_handles_fbtc_when_chart_fails(self):
        def fake_get(url, **kwargs):
            if "query1.finance.yahoo.com" in url:
                raise RuntimeError("chart unavailable")
            return FakeResponse(text="<html><body>Net asset value NAV $52.45 as at close</body></html>")

        payload = fetch_fund_price_fallback("FBTC.TO", is_fund_hint=True, getter=fake_get)

        self.assertEqual(payload["source"], "official_fund_nav_fallback")
        self.assertEqual(payload["current_price"], 52.45)
        self.assertEqual(payload["long_name"], "Fidelity Advantage Bitcoin ETF")
        self.assertEqual(payload["currency"], "CAD")

    def test_data_fetcher_uses_fund_fallback_after_yfinance_failure(self):
        from src.data_fetcher import MarketDataFetcher

        fallback = {
            "source": "official_fund_nav_fallback",
            "current_price": 52.45,
            "currency": "CAD",
            "long_name": "Fidelity Advantage Bitcoin ETF",
            "quote_type": "ETF",
            "quote_type_display": "ETF",
            "data_source_notes": ["test fallback"],
        }
        fetcher = MarketDataFetcher()
        payload = fetcher._empty_payload("FBTC.TO")
        payload["source"] = "unavailable"

        with patch("src.data_fetcher.fetch_fund_price_fallback", return_value=fallback):
            fetcher._fill_from_fund_price_fallback("FBTC.TO", payload)

        self.assertEqual(payload["source"], "official_fund_nav_fallback")
        self.assertEqual(payload["current_price"], 52.45)
        self.assertEqual(payload["currency"], "CAD")
        self.assertIn("test fallback", payload["data_source_notes"])


if __name__ == "__main__":
    unittest.main()
