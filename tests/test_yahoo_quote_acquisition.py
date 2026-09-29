from email.message import Message
import inspect
from pathlib import Path
import tempfile
import unittest
import urllib.error
from unittest.mock import patch

from economic_facts import yahoo_quote_acquisition as acquisition
from economic_facts.yahoo_quote_archive import MAX_BODY_BYTES, YahooQuoteArchive
from tests.yahoo_quote_fixtures import chart_response


class Response:
    def __init__(self, raw=None, *, status=200, content_type="application/json",
                 url=None, headers=None):
        self.raw = chart_response() if raw is None else raw
        self.status = status
        self.offset = 0
        self.url = url
        self.headers = Message()
        self.headers["Content-Type"] = content_type
        self.headers["Content-Length"] = str(len(self.raw))
        if headers:
            for key, value in headers:
                self.headers[key] = value

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def geturl(self):
        return self.url

    def read1(self, size):
        chunk = self.raw[self.offset:self.offset + size]
        self.offset += len(chunk)
        return chunk


class YahooQuoteAcquisitionTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve() / "quotes"
        self.endpoint = (
            "https://query1.finance.yahoo.com/v8/finance/chart/FICT"
            "?range=5d&interval=1d&events=div%2Csplits&includePrePost=false"
        )

    def acquire(self, response=None):
        response = Response(url=self.endpoint) if response is None else response
        if response.url is None:
            response.url = self.endpoint
        with patch.object(acquisition, "_open_response", return_value=response) as opened, \
             patch.object(acquisition, "_timestamp", side_effect=(
                 "2026-02-25T12:00:00Z", "2026-02-25T12:00:01Z",
                 "2026-02-25T12:00:02Z")):
            result = acquisition.acquire_yahoo_current_quote(
                symbol="FICT", archive_root=self.root)
        return result, opened.call_args.args[0]

    def test_exact_request_and_archive_publication(self):
        result, request = self.acquire()
        self.assertEqual(request.full_url, self.endpoint)
        self.assertEqual(request.method, "GET")
        self.assertEqual(request.get_header("Accept"), "application/json")
        self.assertEqual(request.get_header("Accept-encoding"), "identity")
        self.assertIn("PAM-QuoteCapture", request.get_header("User-agent"))
        self.assertEqual(result.receipt.requested_symbol, "FICT")
        self.assertEqual(YahooQuoteArchive(self.root).read_object(result.receipt), chart_response())

    def test_public_signature_has_no_bytes_transport_clock_or_capture_time(self):
        signature = inspect.signature(acquisition.acquire_yahoo_current_quote)
        self.assertEqual(tuple(signature.parameters), ("symbol", "archive_root"))
        self.assertTrue(all(item.kind is inspect.Parameter.KEYWORD_ONLY
                            for item in signature.parameters.values()))
        for keyword in ("raw", "price", "currency", "captured_at", "transport", "qualified"):
            with self.assertRaises(TypeError):
                acquisition.acquire_yahoo_current_quote(
                    symbol="FICT", archive_root=self.root, **{keyword: object()})

    def test_redirect_and_wrong_final_url_rejected(self):
        response = Response(status=302, url=self.endpoint)
        with patch.object(acquisition, "_open_response", return_value=response), \
             patch.object(acquisition, "_timestamp", return_value="2026-02-25T12:00:00Z"):
            with self.assertRaises(acquisition.YahooQuoteAcquisitionError) as caught:
                acquisition.acquire_yahoo_current_quote(symbol="FICT", archive_root=self.root)
        self.assertIs(caught.exception.reason, acquisition.YahooQuoteAcquisitionReason.REDIRECT_REJECTED)

        response = Response(url="https://query1.finance.yahoo.com/other")
        with patch.object(acquisition, "_open_response", return_value=response), \
             patch.object(acquisition, "_timestamp", return_value="2026-02-25T12:00:00Z"):
            with self.assertRaises(acquisition.YahooQuoteAcquisitionError) as caught:
                acquisition.acquire_yahoo_current_quote(symbol="FICT", archive_root=self.root)
        self.assertIs(caught.exception.reason, acquisition.YahooQuoteAcquisitionReason.REDIRECT_REJECTED)

    def test_content_type_size_and_header_bounds(self):
        cases = (
            (Response(content_type="text/html", url=self.endpoint),
             acquisition.YahooQuoteAcquisitionReason.INVALID_CONTENT_TYPE),
            (Response(raw=b"x" * (MAX_BODY_BYTES + 1), url=self.endpoint),
             acquisition.YahooQuoteAcquisitionReason.RESPONSE_TOO_LARGE),
        )
        for response, reason in cases:
            with self.subTest(reason=reason), \
                 patch.object(acquisition, "_open_response", return_value=response), \
                 patch.object(acquisition, "_timestamp", return_value="2026-02-25T12:00:00Z"):
                with self.assertRaises(acquisition.YahooQuoteAcquisitionError) as caught:
                    acquisition.acquire_yahoo_current_quote(symbol="FICT", archive_root=self.root)
                self.assertIs(caught.exception.reason, reason)

        headers = [(f"X-{index}", "x") for index in range(acquisition.MAX_HEADER_COUNT + 1)]
        response = Response(url=self.endpoint, headers=headers)
        with patch.object(acquisition, "_open_response", return_value=response), \
             patch.object(acquisition, "_timestamp", return_value="2026-02-25T12:00:00Z"):
            with self.assertRaises(acquisition.YahooQuoteAcquisitionError) as caught:
                acquisition.acquire_yahoo_current_quote(symbol="FICT", archive_root=self.root)
        self.assertIs(caught.exception.reason,
                      acquisition.YahooQuoteAcquisitionReason.RESPONSE_HEADERS_TOO_LARGE)

    def test_http_timeout_and_network_fail_closed_without_retry(self):
        cases = (
            (urllib.error.HTTPError(self.endpoint, 429, "", Message(), None),
             acquisition.YahooQuoteAcquisitionReason.RATE_LIMITED),
            (urllib.error.HTTPError(self.endpoint, 500, "", Message(), None),
             acquisition.YahooQuoteAcquisitionReason.HTTP_ERROR),
            (TimeoutError(), acquisition.YahooQuoteAcquisitionReason.TIMEOUT),
            (urllib.error.URLError(OSError("offline")),
             acquisition.YahooQuoteAcquisitionReason.NETWORK_ERROR),
        )
        for failure, reason in cases:
            with self.subTest(reason=reason), \
                 patch.object(acquisition, "_open_response", side_effect=failure) as opened, \
                 patch.object(acquisition, "_timestamp", return_value="2026-02-25T12:00:00Z"):
                with self.assertRaises(acquisition.YahooQuoteAcquisitionError) as caught:
                    acquisition.acquire_yahoo_current_quote(symbol="FICT", archive_root=self.root)
                self.assertIs(caught.exception.reason, reason)
                self.assertEqual(opened.call_count, 1)

    def test_proxy_environment_is_explicitly_disabled(self):
        source = inspect.getsource(acquisition._open_response)
        self.assertIn("ProxyHandler({})", source)
        self.assertIn("ssl.create_default_context()", source)
        self.assertNotIn("requests", source)


if __name__ == "__main__":
    unittest.main()
