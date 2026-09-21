"""Fictional responses; actual dedicated Nasdaq locking and archive mechanics."""
from dataclasses import FrozenInstanceError, asdict
from datetime import datetime, timedelta, timezone
from email.message import Message
import inspect
import io
import os
from pathlib import Path
import ssl
import subprocess
import sys
import tempfile
import traceback
import unittest
from unittest.mock import Mock, patch
import urllib.error
import urllib.request

from economic_facts import nasdaq_listed_acquisition as a
from economic_facts.nasdaq_listed_acquisition import NasdaqListedAcquisitionReason as R, NasdaqListedAcquisitionError as Error
from economic_facts.nasdaq_listed_archive import NasdaqListedArchive, NasdaqListedArchiveError, ENDPOINT
from economic_facts.nasdaq_listed_snapshot import replay_nasdaq_listed_snapshot, NasdaqListedSnapshotRequest, SnapshotStatus
from tests.nasdaq_listed_fixtures import T1, T2, directory, row

CONTACT = "private-path-or-body"
USER_AGENT = CONTACT
NOW = datetime(2026, 9, 21, 12, tzinfo=timezone.utc)


class Response(io.BytesIO):
    def __init__(self, body=None, *, status=200, headers=None, url=None):
        super().__init__(directory() if body is None else body)
        self.status = status
        self.url = ENDPOINT if url is None else url
        self.headers = Message()
        for key, value in ({"Content-Type": "text/plain"} if headers is None else headers).items():
            self.headers[key] = value
        self.sizes = []

    def geturl(self):
        return self.url

    def read1(self, size=-1):
        assert size > 0
        self.sizes.append(size)
        return super().read(size)


class NasdaqListedAcquisitionTests(unittest.TestCase):
    def test_configuration_error_precedes_network(self):
        for root in (None, 1, "private\x00path", self.root / ".." / "escape"):
            self.assert_failure(R.CONFIGURATION_ERROR, network=False, archive_root=root)

    def test_tls_proxy_socket_timeout_and_redirect_policy(self):
        opener = Mock()
        with patch.object(urllib.request, "build_opener", return_value=opener) as build, \
             patch.dict(os.environ, {"https_proxy": "http://untrusted.invalid"}):
            self.real_open_response(urllib.request.Request(ENDPOINT))
        handlers = build.call_args.args
        self.assertEqual(handlers[0].proxies, {})
        self.assertTrue(handlers[1]._context.check_hostname)
        self.assertEqual(handlers[1]._context.verify_mode, ssl.CERT_REQUIRED)
        self.assertEqual(opener.open.call_args.kwargs, {"timeout": 15})
        response = Response()
        with self.assertRaises(Error):
            handlers[2].redirect_request(None, response, 302, "", {}, "https://other.invalid")
        self.assertTrue(response.closed)

    def test_exact_fixed_request_bytes_and_capture_chronology(self):
        self.wall.side_effect = [NOW, NOW + timedelta(seconds=1), NOW + timedelta(seconds=2)]
        result = self.acquire()
        request = self.transport.call_args.args[0]
        self.assertEqual(request.full_url, "https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt")
        self.assertEqual(request.get_method(), "GET")
        self.assertEqual(dict(request.header_items()), {
            "User-agent": "PAM-NasdaqListedCapture/1.0", "Accept": "text/plain", "Accept-encoding": "identity"})
        self.assertIsNone(request.data)
        self.assertEqual(self.transport.call_count, 1)
        self.assertEqual(result.request_started_at, T1)
        self.assertEqual(result.response_completed_at, "2026-09-21T12:00:01Z")
        self.assertEqual(result.receipt.captured_at, "2026-09-21T12:00:02Z")
        self.assertEqual(NasdaqListedArchive(self.root).read_object(result.receipt), directory())
        self.assertEqual(set(asdict(result)), {"receipt", "request_started_at", "response_completed_at"})
        with self.assertRaises(FrozenInstanceError):
            result.receipt = None

    def test_public_api_has_only_archive_root(self):
        parameters = inspect.signature(a.acquire_nasdaq_listed).parameters
        self.assertEqual(set(parameters), {"archive_root"})
        self.assertEqual(parameters["archive_root"].kind, inspect.Parameter.KEYWORD_ONLY)
        for name in ("url", "hostname", "path", "raw", "bytes", "clock", "transport", "captured_at",
                     "source_creation_time", "as_of", "cik", "ticker", "issuer_identity", "share_class",
                     "listing_interval", "coverage_boundary", "authority", "complete", "retry_policy", "rate_policy"):
            with self.subTest(name=name), self.assertRaises(TypeError):
                self.acquire(**{name: True})
        self.transport.assert_not_called()

    def test_text_mime_and_encoding_contract(self):
        for media in ("text/plain", "text/plain; charset=utf-8", 'TEXT/PLAIN; charset="UTF-8"',
                      "text/plain; charset=us-ascii", 'text/plain; charset="us-ascii"'):
            self.transport.return_value = Response(headers={"Content-Type": media})
            self.acquire()
        for media in ("text/html", "application/json", "application/octet-stream", "", "text/plain, text/html",
                      "text/plain; charset=latin-1", "text/plain; charset=utf-8; charset=us-ascii"):
            self.transport.return_value = Response(headers={"Content-Type": media})
            with self.assertRaises(Error) as caught:
                self.acquire()
            self.assertEqual(caught.exception.reason, R.INVALID_CONTENT_TYPE)

    def test_declared_ascii_cannot_hide_utf8(self):
        body = directory([row(**{"Security Name": "Fictional Société"})])
        self.transport.return_value = Response(body, headers={"Content-Type": "text/plain; charset=us-ascii"})
        self.assert_failure(R.INVALID_RESPONSE)
        self.transport.return_value = Response(body, headers={"Content-Type": "text/plain; charset=utf-8"})
        self.assertEqual(NasdaqListedArchive(self.root).read_object(self.acquire().receipt), body)

    def test_compression_and_framing_fail_closed(self):
        for changes in ({"Content-Encoding": "gzip"}, {"Content-Encoding": "br"}, {"Content-Encoding": ""},
                        {"Transfer-Encoding": "gzip"}, {"Transfer-Encoding": "chunked, chunked"},
                        {"Transfer-Encoding": "chunked", "Content-Length": str(len(directory()))}):
            self.transport.return_value = Response(headers={"Content-Type": "text/plain", **changes})
            self.assert_failure(R.INVALID_RESPONSE)

    def test_chunked_entity_and_identity_encoding_supported(self):
        self.transport.return_value = Response(headers={"Content-Type": "text/plain", "Transfer-Encoding": "chunked",
                                                       "Content-Encoding": "identity"})
        self.acquire()

    def test_preflight_failure_publishes_nothing_and_hides_body(self):
        for raw in (b"", b"private-path-or-body", b"\xff", directory().splitlines(keepends=True)[0],
                    directory().replace(b"|Q|", b"|UNKNOWN|")):
            self.transport.return_value = Response(raw)
            self.assert_failure(R.UNSUPPORTED_SOURCE_VARIANT)

    def test_duplicate_snapshot_is_captured_but_conflicted_on_replay(self):
        self.transport.return_value = Response(directory([row(), row()]))
        receipt = self.acquire().receipt
        result = replay_nasdaq_listed_snapshot(NasdaqListedArchive(self.root), NasdaqListedSnapshotRequest(receipt.receipt_id))
        self.assertEqual(result.status, SnapshotStatus.SOURCE_CONFLICT)
        self.assertEqual(result.row_count, 2)

    def test_provider_gate_independent_of_sec_and_archive(self):
        from economic_facts import sec_acquisition as sec
        with patch.object(sec, "_state_directory", return_value=self.root.parent / "sec-gate"), sec._rate_gate():
            self.acquire()
        self.transport.return_value = Response()
        self.acquire(archive_root=self.root.parent / "second-archive")
        self.assertEqual(self.sleeps, [0.25, 1.0, 1.0])

    def test_gate_spacing_no_burst_credit_and_failure_releases(self):
        self.now += 10000
        self.transport.return_value = Response(status=503)
        self.assert_failure(R.HTTP_ERROR)
        self.transport.return_value = Response()
        self.acquire()
        self.transport.return_value = Response()
        self.acquire()
        self.assertEqual(self.sleeps, [1.0, 1.0, 1.0])

    def test_early_sleep_cannot_skip_spacing(self):
        self.patched(a.time, "sleep", side_effect=lambda remaining: self.sleep(min(remaining, 0.25)))
        self.acquire()
        self.assertEqual(self.sleeps, [0.25] * 4)

    def test_cross_process_contention_across_archive_roots(self):
        source = '''
import sys
from pathlib import Path
from unittest.mock import patch
from economic_facts import nasdaq_listed_acquisition as a
def no_network(request):
    raise AssertionError("network forbidden")
with patch.object(a, "_state_directory", return_value=Path(sys.argv[1])), patch.object(a, "_open_response", no_network):
    try:
        a.acquire_nasdaq_listed(archive_root=sys.argv[2])
    except a.NasdaqListedAcquisitionError as exc:
        assert exc.reason == a.NasdaqListedAcquisitionReason.RATE_LIMITED
    else:
        raise AssertionError("contention bypassed")
'''
        with a._rate_gate():
            result = subprocess.run([sys.executable, "-B", "-c", source, str(self.state), str(self.root)],
                                    capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.transport.assert_not_called()
        self.assertFalse(self.root.exists())

    def test_gate_held_during_receive_and_preflight(self):
        original = a._parse_snapshot
        def check_gate():
            with self.assertRaises(Error) as caught:
                with a._rate_gate():
                    pass
            self.assertEqual(caught.exception.reason, R.RATE_LIMITED)
        def receive(size):
            check_gate()
            return io.BytesIO.read(self.response, size)
        def parse(raw):
            check_gate()
            return original(raw)
        self.response.read1 = receive
        with patch.object(a, "_parse_snapshot", side_effect=parse):
            self.acquire()

    def test_unsafe_gate_permissions_and_owner(self):
        self.state.mkdir()
        for target in (self.state, self.state.parent):
            old = target.stat().st_mode
            target.chmod(0o777)
            self.assert_failure(R.CONFIGURATION_ERROR, network=False)
            target.chmod(old)
        with patch.object(a.os, "getuid", return_value=-1):
            self.assert_failure(R.CONFIGURATION_ERROR, network=False)
        lock = self.state / "gate.lock"
        lock.touch()
        lock.chmod(0o666)
        self.assert_failure(R.CONFIGURATION_ERROR, network=False)

    def test_gate_symlink_parent_and_nonregular_lock(self):
        outside = self.root.parent / "outside"
        outside.mkdir()
        self.state.symlink_to(outside, target_is_directory=True)
        self.assert_failure(R.CONFIGURATION_ERROR, network=False)
        self.state.unlink()
        alias = self.root.parent / "alias"
        alias.symlink_to(outside, target_is_directory=True)
        with patch.object(a, "_state_directory", return_value=alias / "gate"):
            self.assert_failure(R.CONFIGURATION_ERROR, network=False)
        self.assertEqual(list(outside.iterdir()), [])
        self.state.mkdir()
        lock = self.state / "gate.lock"
        external = outside / "lock"
        external.touch()
        for attack in ("symlink", "hardlink", "fifo", "directory"):
            if attack == "symlink":
                lock.symlink_to(external)
            elif attack == "hardlink":
                os.link(external, lock)
            elif attack == "fifo":
                os.mkfifo(lock)
            else:
                lock.mkdir()
            self.assert_failure(R.CONFIGURATION_ERROR, network=False)
            lock.rmdir() if attack == "directory" else lock.unlink()

    def test_gate_io_failure_safe(self):
        with patch.object(a, "_open_state_directory", side_effect=OSError(CONTACT)):
            self.assert_failure(R.CONFIGURATION_ERROR, network=False)

    def test_http_dates_never_backdate_capture(self):
        self.response.headers["Date"] = "Tue, 01 Jan 2000 00:00:00 GMT"
        self.response.headers["Last-Modified"] = "Tue, 01 Jan 2000 00:00:00 GMT"
        result = self.acquire()
        self.assertEqual(result.receipt.captured_at, T1)
        self.assertEqual(result.request_started_at, T1)

    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name).resolve() / "archive"
        self.state = self.root.parent / "gate"
        self.now = 100.0
        self.sleeps = []
        self.response = Response()
        self.real_open_response = a._open_response
        self.transport = self.patched(a, "_open_response", return_value=self.response)
        self.patched(a, "_state_directory", return_value=self.state)
        self.wall = self.patched(a, "_utc_now", return_value=NOW)
        self.patched(a.time, "monotonic", side_effect=lambda: self.now)
        self.patched(a.time, "sleep", side_effect=self.sleep)

    def acquire(self, **changes):
        return a.acquire_nasdaq_listed(**{"archive_root": self.root, **changes})

    def patched(self, obj, name, **kwargs):
        patcher = patch.object(obj, name, **kwargs)
        result = patcher.start()
        self.addCleanup(patcher.stop)
        return result

    def sleep(self, seconds):
        self.sleeps.append(seconds)
        self.now += seconds

    def assert_failure(self, reason, *, network=True, **changes):
        before = self.transport.call_count
        with self.assertRaises(Error) as caught:
            self.acquire(**changes)
        self.assertEqual(caught.exception.reason, reason)
        self.assertEqual(self.transport.call_count - before, int(network))
        self.assertFalse(self.root.exists())
        self.assertNotIn(CONTACT, str(caught.exception))
        return caught.exception

    def test_single_request_non200_statuses(self):
        for status in (201, 204, 301, 302, 303, 304, 307, 308, 403, 404, 429, 500, 503):
            self.transport.return_value = Response(status=status)
            reason = R.REDIRECT_REJECTED if 300 <= status < 400 else R.RATE_LIMITED if status == 429 else R.HTTP_ERROR
            with self.subTest(status=status):
                self.assertEqual(self.assert_failure(reason).status, status)

    def test_http_errors_close_body_and_hide_contact(self):
        for status in (302, 403, 429, 503):
            stream = io.BytesIO(USER_AGENT.encode())
            self.transport.side_effect = urllib.error.HTTPError(ENDPOINT, status, USER_AGENT, {}, stream)
            reason = R.REDIRECT_REJECTED if status == 302 else R.RATE_LIMITED if status == 429 else R.HTTP_ERROR
            self.assert_failure(reason)
            self.assertTrue(stream.closed)
            try:
                self.acquire()
            except Error:
                self.assertNotIn(CONTACT, traceback.format_exc())

    def test_changed_response_locator_rejected(self):
        self.transport.return_value = Response(url="https://other.invalid")
        self.assert_failure(R.REDIRECT_REJECTED)

    def test_network_and_timeout_errors_safe(self):
        for error, reason in ((TimeoutError(USER_AGENT), R.TIMEOUT),
                              (urllib.error.URLError(TimeoutError(USER_AGENT)), R.TIMEOUT),
                              (ssl.SSLCertVerificationError(USER_AGENT), R.NETWORK_ERROR),
                              (urllib.error.URLError(USER_AGENT), R.NETWORK_ERROR),
                              (ConnectionResetError(USER_AGENT), R.NETWORK_ERROR),
                              (a.http.client.IncompleteRead(b"private"), R.NETWORK_ERROR)):
            self.transport.side_effect = error
            self.assert_failure(reason)

    def test_read_timeout_closes_response(self):
        self.response.read1 = Mock(side_effect=TimeoutError(USER_AGENT))
        self.assert_failure(R.TIMEOUT)
        self.assertTrue(self.response.closed)

    def test_deadline_checked_after_receive(self):
        def slow(size):
            self.now += a.RESPONSE_DEADLINE_SECONDS
            return directory()
        self.response.read1 = slow
        self.assert_failure(R.TIMEOUT)

    def test_deadline_checked_before_receive(self):
        def slow_open(request):
            self.now += a.RESPONSE_DEADLINE_SECONDS
            return self.response
        self.transport.side_effect = slow_open
        self.assert_failure(R.TIMEOUT)
        self.assertEqual(self.response.sizes, [])

    def test_size_declared_rejected_before_read(self):
        self.response.headers["Content-Length"] = str(a.MAX_BODY_BYTES + 1)
        self.assert_failure(R.RESPONSE_TOO_LARGE)
        self.assertEqual(self.response.sizes, [])

    def test_streaming_limit_and_bounded_reads(self):
        self.transport.return_value = Response(directory() + b"xx")
        with patch.object(a, "MAX_BODY_BYTES", len(directory())):
            self.assert_failure(R.RESPONSE_TOO_LARGE)
        self.assertEqual(self.transport.return_value.sizes, [len(directory()) + 1])

    def test_exact_maximum_allowed(self):
        self.response.headers["Content-Length"] = str(len(directory()))
        with patch.object(a, "MAX_BODY_BYTES", len(directory())):
            self.assertEqual(self.acquire().receipt.byte_length, len(directory()))

    def test_malformed_or_truncated_content_length(self):
        for value in ("-1", "abc", "1,2", "9" * 21, "0", str(len(directory()) + 1)):
            self.transport.return_value = Response(headers={"Content-Type": "text/plain", "Content-Length": value})
            self.assert_failure(R.INVALID_RESPONSE)

    def test_clock_regression_or_naive_clock(self):
        self.wall.side_effect = [NOW, NOW - timedelta(seconds=1), NOW]
        self.assert_failure(R.CONFIGURATION_ERROR)
        self.wall.side_effect = None
        self.wall.return_value = NOW.replace(tzinfo=None)
        self.assert_failure(R.CONFIGURATION_ERROR, network=False)

    def test_shared_gate_contention(self):
        with a._rate_gate():
            self.assert_failure(R.RATE_LIMITED, network=False)
        self.acquire()

    def test_duplicate_and_ambiguous_headers(self):
        for key, value in (("Content-Type", "text/plain"), ("Content-Length", str(len(directory()))),
                           ("Content-Encoding", "identity"), ("Transfer-Encoding", "chunked")):
            self.transport.return_value = Response()
            if key != "Content-Type":
                self.transport.return_value.headers[key] = value
            self.transport.return_value.headers[key] = value
            self.assert_failure(R.INVALID_RESPONSE)
        for headers in ({"Content-Encoding": "gzip"}, {"Transfer-Encoding": "gzip"},
                        {"Transfer-Encoding": "chunked", "Content-Length": str(len(directory()))}):
            self.transport.return_value = Response(headers={"Content-Type": "text/plain", **headers})
            self.assert_failure(R.INVALID_RESPONSE)

    def test_gate_is_held_through_archive_publication(self):
        original = NasdaqListedArchive._capture_live
        def capture(archive, *args, **kwargs):
            with self.assertRaises(Error) as caught:
                with a._rate_gate():
                    pass
            self.assertEqual(caught.exception.reason.value, "RATE_LIMITED")
            return original(archive, *args, **kwargs)
        with patch.object(NasdaqListedArchive, "_capture_live", capture):
            self.acquire()

    def test_programming_errors_propagate(self):
        self.transport.side_effect = RuntimeError("programming defect")
        with self.assertRaises(RuntimeError):
            self.acquire()

    def test_archive_error_translation(self):
        with patch.object(NasdaqListedArchive, "_capture_live", side_effect=NasdaqListedArchiveError("private")):
            self.assert_failure(R.ARCHIVE_INTEGRITY_ERROR)
