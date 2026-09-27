"""Fictional responses exercising the shared reviewed SEC transport discipline."""
from contextlib import nullcontext
from dataclasses import FrozenInstanceError, asdict
from datetime import datetime, timedelta, timezone
from email.message import Message
import inspect
import io
import os
from pathlib import Path
import ssl
import tempfile
import unittest
from unittest.mock import Mock, patch
import urllib.error
import urllib.request

from economic_facts import sec_acquisition as shared
from economic_facts import sec_ticker_exchange_acquisition as a
from economic_facts.sec_ticker_exchange_acquisition import (
    SecTickerExchangeAcquisitionError as Error,
    SecTickerExchangeAcquisitionReason as R,
)
from economic_facts.sec_ticker_exchange_archive import (
    ENDPOINT, SecTickerExchangeArchive, SecTickerExchangeArchiveError,
)
from economic_facts.sec_ticker_exchange_snapshot import (
    SecTickerExchangeSnapshotRequest, replay_sec_ticker_exchange_snapshot,
)
from tests.sec_ticker_exchange_fixtures import T1, snapshot

USER_AGENT = "PAM Test Operations admin@example.com"
NOW = datetime(2026, 9, 26, 12, tzinfo=timezone.utc)
REAL_OPEN_RESPONSE = shared._open_response


class Response(io.BytesIO):
    def __init__(self, body=None, *, status=200, headers=None, url=ENDPOINT):
        super().__init__(snapshot() if body is None else body)
        self.status = status
        self.url = url
        self.headers = Message()
        for key, value in ({"Content-Type": "application/json"}
                           if headers is None else headers).items():
            self.headers[key] = value
        self.sizes = []

    def geturl(self):
        return self.url

    def read1(self, size=-1):
        self.sizes.append(size)
        return super().read(size)


class SecTickerExchangeAcquisitionTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve() / "archive"
        self.response = Response()
        self.transport = patch.object(shared, "_open_response", return_value=self.response)
        self.open_response = self.transport.start()
        self.addCleanup(self.transport.stop)
        self.gate = patch.object(shared, "_rate_gate", side_effect=lambda: nullcontext())
        self.rate_gate = self.gate.start()
        self.addCleanup(self.gate.stop)
        self.wall = patch.object(shared, "_utc_now", return_value=NOW)
        self.wall_clock = self.wall.start()
        self.addCleanup(self.wall.stop)
        self.env = patch.dict(os.environ, {shared.USER_AGENT_ENV: USER_AGENT})
        self.env.start()
        self.addCleanup(self.env.stop)

    def acquire(self, **changes):
        return a.acquire_sec_ticker_exchange_associations(
            **{"archive_root": self.root, **changes})

    def fail(self, reason, *, network=True):
        with self.assertRaises(Error) as caught:
            self.acquire()
        self.assertEqual(caught.exception.reason, reason)
        if network:
            self.assertEqual(self.open_response.call_count, 1)
        else:
            self.open_response.assert_not_called()
        self.assertFalse((self.root / "receipts").exists())
        return caught.exception

    def test_public_api_only_archive_root(self):
        parameters = inspect.signature(a.acquire_sec_ticker_exchange_associations).parameters
        self.assertEqual(set(parameters), {"archive_root"})
        self.assertEqual(parameters["archive_root"].kind, inspect.Parameter.KEYWORD_ONLY)
        for name in ("url", "endpoint", "raw", "source_bytes", "clock", "captured_at",
                     "ticker", "cik", "as_of", "qualified"):
            with self.subTest(name=name), self.assertRaises(TypeError):
                self.acquire(**{name: "forged"})

    def test_exact_request_endpoint_headers_one_attempt_and_chronology(self):
        self.wall_clock.side_effect = [NOW, NOW + timedelta(seconds=1),
                                       NOW + timedelta(seconds=2)]
        result = self.acquire()
        request = self.open_response.call_args.args[0]
        self.assertEqual(request.full_url, ENDPOINT)
        self.assertEqual(request.get_method(), "GET")
        self.assertEqual(dict(request.header_items()), {
            "User-agent": USER_AGENT, "Accept": "application/json",
            "Accept-encoding": "identity"})
        self.assertIsNone(request.data)
        self.assertEqual(self.open_response.call_count, 1)
        self.rate_gate.assert_called_once_with()
        self.assertEqual((result.request_started_at, result.response_completed_at,
                          result.receipt.captured_at),
                         (T1, "2026-09-26T12:00:01Z", "2026-09-26T12:00:02Z"))
        self.assertEqual(set(asdict(result)), {"receipt", "request_started_at",
                                               "response_completed_at"})
        with self.assertRaises(FrozenInstanceError):
            result.receipt = None

    def test_exact_bytes_archived_and_offline_replayable(self):
        raw = snapshot().replace(b'"data":', b'\n"data":')
        self.open_response.return_value = Response(raw)
        result = self.acquire()
        archive = SecTickerExchangeArchive(self.root)
        self.assertEqual(archive.read_object(result.receipt), raw)
        replay = replay_sec_ticker_exchange_snapshot(
            archive, SecTickerExchangeSnapshotRequest(result.receipt.receipt_id))
        self.assertEqual(replay.rows[0].source_ticker, "FICT")

    def test_reviewed_user_agent_required_before_network(self):
        with patch.dict(os.environ, {}, clear=True):
            self.fail(R.CONFIGURATION_ERROR, network=False)

    def test_shared_transport_disables_proxies_verifies_tls_and_bounds_socket(self):
        opener = Mock()
        request = urllib.request.Request(ENDPOINT)
        with patch.object(urllib.request, "build_opener", return_value=opener) as build, \
             patch.dict(os.environ, {"HTTPS_PROXY": "http://untrusted.invalid"}):
            REAL_OPEN_RESPONSE(request)
        handlers = build.call_args.args
        self.assertEqual(handlers[0].proxies, {})
        self.assertEqual(handlers[1]._context.verify_mode, ssl.CERT_REQUIRED)
        self.assertTrue(handlers[1]._context.check_hostname)
        opener.open.assert_called_once_with(request, timeout=15)

    def test_redirects_and_every_non_200_fail_without_retry(self):
        for status in (201, 204, 300, 301, 302, 307, 308, 403, 404, 429, 500, 503):
            with self.subTest(status=status):
                self.open_response.reset_mock()
                self.open_response.return_value = Response(status=status)
                reason = (R.REDIRECT_REJECTED if 300 <= status < 400 else
                          R.RATE_LIMITED if status == 429 else R.HTTP_ERROR)
                error = self.fail(reason)
                self.assertEqual(error.status, status)

    def test_legacy_or_changed_endpoint_redirect_rejected(self):
        for target in ("https://www.sec.gov/data/company_tickers_exchange.json",
                       "http://www.sec.gov/files/company_tickers_exchange.json",
                       "https://other.invalid/company_tickers_exchange.json"):
            with self.subTest(target=target):
                self.open_response.reset_mock()
                self.open_response.return_value = Response(url=target)
                self.fail(R.REDIRECT_REJECTED)

    def test_timeout_and_network_failures_closed_without_retry(self):
        cases = ((TimeoutError("private"), R.TIMEOUT),
                 (urllib.error.URLError(TimeoutError("private")), R.TIMEOUT),
                 (urllib.error.URLError("private"), R.NETWORK_ERROR),
                 (ssl.SSLCertVerificationError("private"), R.NETWORK_ERROR),
                 (ConnectionResetError("private"), R.NETWORK_ERROR))
        for error, reason in cases:
            with self.subTest(reason=reason):
                self.open_response.reset_mock()
                self.open_response.side_effect = error
                self.fail(reason)
                self.open_response.side_effect = None

    def test_response_deadline_checked_between_bounded_reads(self):
        moments = iter((0.0, 0.0, shared.RESPONSE_DEADLINE_SECONDS + 1))
        with patch.object(shared.time, "monotonic", side_effect=lambda: next(moments)):
            self.fail(R.TIMEOUT)
        self.assertTrue(all(0 < size <= shared._CHUNK_BYTES for size in self.response.sizes))

    def test_content_type_encoding_framing_and_size_guards(self):
        cases = (({"Content-Type": "text/plain"}, R.INVALID_CONTENT_TYPE),
                 ({"Content-Type": "application/json", "Content-Encoding": "gzip"},
                  R.INVALID_RESPONSE),
                 ({"Content-Type": "application/json", "Transfer-Encoding": "gzip"},
                  R.INVALID_RESPONSE),
                 ({"Content-Type": "application/json",
                   "Content-Length": str(shared.MAX_BODY_BYTES + 1)}, R.RESPONSE_TOO_LARGE))
        for headers, reason in cases:
            with self.subTest(headers=headers):
                self.open_response.reset_mock()
                self.open_response.return_value = Response(headers=headers)
                self.fail(reason)

    def test_json_utf8_content_type_and_identity_encoding_accepted(self):
        self.open_response.return_value = Response(headers={
            "Content-Type": 'Application/JSON; charset="UTF-8"',
            "Content-Encoding": "identity", "Content-Length": str(len(snapshot()))})
        self.assertEqual(self.acquire().receipt.byte_length, len(snapshot()))

    def test_duplicate_transport_headers_rejected(self):
        for name, value in (("Content-Type", "application/json"),
                            ("Content-Length", str(len(snapshot()))),
                            ("Content-Encoding", "identity"),
                            ("Transfer-Encoding", "chunked")):
            response = Response()
            if name != "Content-Type":
                response.headers[name] = value
            response.headers[name] = value
            self.open_response.reset_mock()
            self.open_response.return_value = response
            self.fail(R.INVALID_RESPONSE)

    def test_malformed_or_unsupported_source_never_published(self):
        bodies = (b"<html>blocked</html>", b"{", b"\xff", b"[]", b"null",
                  b'{"fields":["cik","name","ticker","exchange"],"data":{},"x":1}',
                  b'{"fields":["cik","name","ticker","exchange"],"data":[[0,"N","T","E"]]}',
                  b'{"fields":["cik","name","ticker","exchange"],"data":[],"x":NaN}',
                  b'{"fields":[],"fields":[],"data":[]}',
                  b"[" * 2000 + b"]" * 2000)
        for body in bodies:
            with self.subTest(body=body[:30]):
                self.open_response.reset_mock()
                self.open_response.return_value = Response(body)
                self.fail(R.UNSUPPORTED_SOURCE_VARIANT)

    def test_clock_regression_or_naive_clock_fails_closed(self):
        self.wall_clock.side_effect = [NOW, NOW - timedelta(seconds=1), NOW]
        self.fail(R.CONFIGURATION_ERROR)
        self.open_response.reset_mock()
        self.wall_clock.side_effect = None
        self.wall_clock.return_value = NOW.replace(tzinfo=None)
        self.fail(R.CONFIGURATION_ERROR, network=False)

    def test_archive_failure_is_typed(self):
        with patch.object(SecTickerExchangeArchive, "_capture_live",
                          side_effect=SecTickerExchangeArchiveError("private")):
            self.fail(R.ARCHIVE_INTEGRITY_ERROR)


if __name__ == "__main__":
    unittest.main()
