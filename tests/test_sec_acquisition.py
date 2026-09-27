"""Fictional bodies and private transport patches only; never contacts SEC."""
import ast
from dataclasses import FrozenInstanceError, asdict, replace
from datetime import datetime, timedelta, timezone
from email.message import Message
import inspect
import io
import json
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

from economic_facts import sec_acquisition as acquisition
from economic_facts.sec_acquisition import AcquisitionReason as Reason, SecAcquisitionError
from economic_facts.sec_archive import (ACQUISITION_CONTRACT_VERSION, ArchiveError, CaptureReceipt,
                                        LIVE_ACQUISITION_CONTRACT_VERSION, SecArchive, digest, endpoint_for)
from scripts import capture_sec_companyfacts as cli
from tests.sec_filing_fixtures import CIK, T1

CONTACT = "administrator" + "@" + "fixture.invalid"
USER_AGENT = "FictionalAcquisitionTests/1.0 " + CONTACT
BODY = b' { "cik": 0, "facts": {}, "filed": "1999-01-01" }\n'
NOW = datetime(2026, 9, 11, 15, 0, tzinfo=timezone.utc)


class FakeClock:
    def __init__(self):
        self.value = 100.0
        self.sleeps = []

    def monotonic(self):
        return self.value

    def sleep(self, seconds):
        self.sleeps.append(seconds)
        self.value += seconds


class Response(io.BytesIO):
    def __init__(self, body=BODY, *, status=200, headers=None, url=None):
        super().__init__(body)
        self.status = status
        self.headers = Message()
        for name, value in ({"Content-Type": "application/json"} if headers is None else headers).items():
            self.headers[name] = value
        self.url = endpoint_for(CIK) if url is None else url
        self.read_sizes = []

    def geturl(self):
        return self.url

    def read1(self, size=-1):
        assert size > 0, "Only bounded reads allowed"
        self.read_sizes.append(size)
        return super().read(size)


class SecAcquisitionTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve() / "archive"
        self.state = self.root.parent / "gate"
        self.clock = FakeClock()
        self.response = Response()
        self.transport = self.patch("_open_response", return_value=self.response)
        self.patch("_state_directory", return_value=self.state)
        self.wall_clock = self.patch("_utc_now", return_value=NOW)
        for target, replacement in (("monotonic", self.clock.monotonic), ("sleep", self.clock.sleep)):
            patcher = patch.object(acquisition.time, target, replacement)
            patcher.start()
            self.addCleanup(patcher.stop)
        patcher = patch.dict(acquisition.os.environ, {acquisition.USER_AGENT_ENV: USER_AGENT})
        patcher.start()
        self.addCleanup(patcher.stop)

    def patch(self, name, **kwargs):
        patcher = patch.object(acquisition, name, **kwargs)
        result = patcher.start()
        self.addCleanup(patcher.stop)
        return result

    def acquire(self, **kwargs):
        return acquisition.acquire_companyfacts(cik=CIK, archive_root=self.root, **kwargs)

    def fail(self, reason, *, network=True):
        before = self.transport.call_count
        with self.assertRaises(SecAcquisitionError) as caught:
            self.acquire()
        self.assertEqual(caught.exception.reason, reason)
        self.assertFalse(self.root.exists(), "Failure published archive evidence")
        self.assertEqual(self.transport.call_count - before, int(network), "Unexpected retry/request")
        self.assertNotIn(CONTACT, str(caught.exception))
        return caught.exception

    def test_missing_user_agent_fails_before_network(self):
        with patch.dict(acquisition.os.environ, {}, clear=True):
            self.fail(Reason.CONFIGURATION_ERROR, network=False)

    def test_invalid_user_agents_fail_before_network(self):
        values = ("", " ", "Fictional " + "local-user" + "@example.com", USER_AGENT + "\r\nX: y",
                  USER_AGENT + "\x00", USER_AGENT + "\t", "X" * 257 + CONTACT,
                  "Mozilla/5.0", "Mozilla/5.0 " + CONTACT, "Fictional/1.0", CONTACT,
                  "Fictional " + chr(127) + CONTACT, "Fictional é " + CONTACT)
        for value in values:
            # A plain mapping also exercises NUL rejection; the OS itself
            # refuses to put NUL in a real environment variable.
            with self.subTest(index=values.index(value)), patch.object(acquisition.os, "environ", {acquisition.USER_AGENT_ENV: value}):
                self.fail(Reason.CONFIGURATION_ERROR, network=False)

    def test_declared_user_agent_and_exact_request_headers(self):
        result = self.acquire()
        request = self.transport.call_args.args[0]
        self.assertEqual(request.full_url, "https://data.sec.gov/api/xbrl/companyfacts/CIK0000000000.json")
        self.assertEqual(request.get_method(), "GET")
        self.assertEqual(dict(request.header_items()), {"User-agent": USER_AGENT, "Accept": "application/json",
                                                        "Accept-encoding": "identity"})
        self.assertTrue(result.declared_user_agent_used)
        self.assertNotIn(CONTACT, repr(result))
        self.assertNotIn(CONTACT, json.dumps(asdict(result)))
        for path in self.root.rglob("*"):
            if path.is_file():
                self.assertNotIn(CONTACT.encode(), path.read_bytes())

    def test_invalid_ciks_fail_before_network(self):
        for cik in (0, True, None, "1", "00000000000", "../../file", "0000000000?x", "٠" * 10):
            with self.subTest(cik=cik), self.assertRaises(SecAcquisitionError) as caught:
                acquisition.acquire_companyfacts(cik=cik, archive_root=self.root)
            self.assertEqual(caught.exception.reason, Reason.CONFIGURATION_ERROR)
        self.transport.assert_not_called()
        self.assertFalse(self.root.exists())

    def test_public_api_has_no_authority_override(self):
        self.assertEqual(set(inspect.signature(acquisition.acquire_companyfacts).parameters), {"cik", "archive_root"})
        for keyword in ("url", "captured_at", "transport", "clock", "ssl_context", "user_agent"):
            with self.assertRaises(TypeError):
                self.acquire(**{keyword: "forged"})
        self.transport.assert_not_called()

    def test_redirects_and_every_non200_status_fail_without_retry(self):
        for status in (201, 204, 300, 301, 302, 303, 304, 307, 308, 403, 404, 429, 500, 503):
            reason = Reason.REDIRECT_REJECTED if 300 <= status < 400 else Reason.RATE_LIMITED if status == 429 else Reason.HTTP_ERROR
            with self.subTest(status=status):
                self.transport.return_value = Response(status=status)
                self.assertEqual(self.fail(reason).status, status)

    def test_urllib_http_errors_closed_without_body_read_or_identity_leak(self):
        for status in (302, 403, 404, 429, 500, 503):
            stream = io.BytesIO(b"access denied")
            self.transport.side_effect = urllib.error.HTTPError(endpoint_for(CIK), status, USER_AGENT, {}, stream)
            reason = Reason.REDIRECT_REJECTED if status == 302 else Reason.RATE_LIMITED if status == 429 else Reason.HTTP_ERROR
            self.fail(reason)
            self.assertTrue(stream.closed)
            try:
                self.acquire()
            except SecAcquisitionError:
                self.assertNotIn(CONTACT, traceback.format_exc())

    def test_redirect_handler_closes_and_never_builds_second_request(self):
        handler = acquisition._RejectRedirects()
        request = urllib.request.Request(endpoint_for(CIK))
        for target in ("https://other.invalid/body", "http://data.sec.gov/body", endpoint_for(CIK)):
            response = Response()
            with self.assertRaises(SecAcquisitionError) as caught:
                handler.redirect_request(request, response, 302, "moved", {}, target)
            self.assertEqual(caught.exception.reason, Reason.REDIRECT_REJECTED)
            self.assertTrue(response.closed)

    def test_changed_response_url_fails_before_publication(self):
        self.transport.return_value = Response(url="https://other.invalid/body")
        self.fail(Reason.REDIRECT_REJECTED)

    def test_tls_network_and_timeout_failures(self):
        cases = ((TimeoutError(USER_AGENT), Reason.TIMEOUT),
                 (urllib.error.URLError(TimeoutError(USER_AGENT)), Reason.TIMEOUT),
                 (ssl.SSLCertVerificationError(USER_AGENT), Reason.NETWORK_ERROR),
                 (urllib.error.URLError(USER_AGENT), Reason.NETWORK_ERROR),
                 (ConnectionResetError(USER_AGENT), Reason.NETWORK_ERROR),
                 (acquisition.http.client.IncompleteRead(b"partial"), Reason.NETWORK_ERROR))
        for error, reason in cases:
            with self.subTest(reason=reason):
                self.transport.side_effect = error
                self.fail(reason)

    def test_body_read_timeout_creates_no_evidence(self):
        self.response.read1 = Mock(side_effect=TimeoutError(USER_AGENT))
        self.fail(Reason.TIMEOUT)
        self.assertTrue(self.response.closed)

    def test_total_response_deadline_checked_between_reads(self):
        def slow_read(size):
            self.clock.value += acquisition.RESPONSE_DEADLINE_SECONDS
            return BODY
        self.response.read1 = slow_read
        self.fail(Reason.TIMEOUT)

    def test_exact_body_archived_and_linked_result_immutable(self):
        result = self.acquire()
        archive = SecArchive(self.root)
        receipt = archive.read_receipt(result.archive_receipt_id)
        self.assertEqual(archive.read_object(receipt), BODY)
        self.assertEqual(result.content_sha256, digest(BODY))
        self.assertEqual(result.byte_length, len(BODY))
        self.assertEqual(result.captured_at, receipt.captured_at)
        self.assertEqual(result.acquisition_contract_version, receipt.acquisition_contract_version)
        self.assertEqual(result.endpoint, receipt.endpoint)
        self.assertEqual(result.cik, receipt.cik)
        with self.assertRaises(FrozenInstanceError):
            result.captured_at = T1
        self.assertIsInstance(result.safe_response_metadata, tuple)
        self.assertIsInstance(result.safe_response_metadata[0], tuple)
        self.assertTrue(all(0 < size <= acquisition._CHUNK_BYTES for size in self.response.read_sizes))

    def test_content_length_rejected_before_read(self):
        self.response.headers["Content-Length"] = str(acquisition.MAX_BODY_BYTES + 1)
        self.fail(Reason.RESPONSE_TOO_LARGE)
        self.assertEqual(self.response.read_sizes, [])

    def test_streaming_limit_reads_maximum_plus_one(self):
        self.transport.return_value = Response(BODY + b" " * 20)
        with patch.object(acquisition, "MAX_BODY_BYTES", len(BODY)):
            self.fail(Reason.RESPONSE_TOO_LARGE)
        self.assertEqual(self.transport.return_value.read_sizes, [len(BODY) + 1])

    def test_exact_limit_and_matching_length_accepted(self):
        self.response.headers["Content-Length"] = str(len(BODY))
        with patch.object(acquisition, "MAX_BODY_BYTES", len(BODY)):
            self.assertEqual(self.acquire().byte_length, len(BODY))

    def test_invalid_or_truncated_content_length(self):
        for length in ("-1", "abc", "1,2", "9" * 21, str(len(BODY) + 1), "0"):
            with self.subTest(length=length):
                self.transport.return_value = Response(headers={"Content-Type": "application/json", "Content-Length": length})
                self.fail(Reason.INVALID_RESPONSE)

    def test_content_type_failures(self):
        for media_type in (None, "text/html", "text/plain", "application/octet-stream", "application/jsonp",
                           "application/json; charset=latin1", "application/json; unknown=x"):
            self.transport.return_value = Response(headers={} if media_type is None else {"Content-Type": media_type})
            self.fail(Reason.INVALID_CONTENT_TYPE)

    def test_json_content_type_optional_utf8_charset(self):
        self.response.headers.replace_header("Content-Type", 'Application/JSON; charset="UTF-8"')
        self.assertEqual(self.acquire().status, 200)

    def test_compression_and_ambiguous_framing_rejected(self):
        for extra in ({"Content-Encoding": "gzip"}, {"Transfer-Encoding": "gzip"},
                      {"Transfer-Encoding": "chunked", "Content-Length": str(len(BODY))}):
            self.transport.return_value = Response(headers={"Content-Type": "application/json", **extra})
            self.fail(Reason.INVALID_RESPONSE)

    def test_transfer_decoded_chunked_entity_accepted(self):
        self.response.headers["Transfer-Encoding"] = "chunked"
        self.assertEqual(self.acquire().content_sha256, digest(BODY))

    def test_duplicate_transport_headers_fail(self):
        for name, value in (("Content-Type", "application/json"), ("Content-Length", "2"),
                            ("Content-Encoding", "identity"), ("Transfer-Encoding", "chunked")):
            self.transport.return_value = Response()
            if name != "Content-Type":
                self.transport.return_value.headers[name] = value
            self.transport.return_value.headers[name] = value
            self.fail(Reason.INVALID_RESPONSE)

    def test_structural_failures_never_publish(self):
        bodies = (b"<html>access denied</html>", b'{"cik":0,"facts":', b"\xff", b"[]", b"null",
                  b'{"facts":{}}', b'{"cik":1,"facts":{}}', b'{"cik":true,"facts":{}}',
                  b'{"cik":0}', b'{"cik":0,"facts":[]}', b'{"cik":0,"facts":null}',
                  b'{"cik":0,"cik":0,"facts":{}}', b'{"cik":0,"facts":{"a":1,"a":2}}',
                  b'{"cik":0,"facts":{},"x":NaN}', b'{"cik":0,"facts":{},"x":Infinity}',
                  b'{"cik":0,"facts":{},"x":-Infinity}', b'{"cik":0,"facts":{},"x":1e999}',
                  b'{"cik":-1,"facts":{}}', b'{"cik":"00000000000","facts":{}}',
                  b'{"cik":0,"facts":{}} trailing', b"[" * 2000 + b"]" * 2000)
        for index, body in enumerate(bodies):
            with self.subTest(index=index):
                self.transport.return_value = Response(body)
                self.fail(Reason.INVALID_RESPONSE)

    def test_string_cik_and_absent_eps_accepted(self):
        self.transport.return_value = Response(b'{"cik":"0000000000","facts":{}}')
        self.assertEqual(self.acquire().cik, CIK)

    def test_internal_clocks_canonicalized_metadata_cannot_backdate(self):
        self.response.headers["Date"] = "Fri, 01 Jan 1999 00:00:00 GMT"
        self.response.headers["Last-Modified"] = "Fri, 01 Jan 1999 00:00:00 GMT"
        self.response.headers["captured_at"] = T1
        offset = timezone(timedelta(hours=-4))
        self.wall_clock.side_effect = [NOW, (NOW + timedelta(seconds=1)).astimezone(offset), NOW + timedelta(seconds=2)]
        result = self.acquire()
        self.assertEqual(result.request_started_at, "2026-09-11T15:00:00Z")
        self.assertEqual(result.response_completed_at, "2026-09-11T15:00:01Z")
        self.assertEqual(result.captured_at, "2026-09-11T15:00:02Z")
        self.assertNotIn("captured_at", dict(result.safe_response_metadata))
        self.assertEqual(dict(result.safe_response_metadata)["Date"], self.response.headers["Date"])
        self.assertEqual(SecArchive(self.root).read_receipt(result.archive_receipt_id).captured_at, result.captured_at)

    def test_clock_regression_or_naive_time_fails_closed(self):
        self.wall_clock.side_effect = [NOW, NOW - timedelta(seconds=1), NOW]
        self.fail(Reason.CONFIGURATION_ERROR)
        self.wall_clock.side_effect = None
        self.wall_clock.return_value = NOW.replace(tzinfo=None)
        self.fail(Reason.CONFIGURATION_ERROR, network=False)

    def test_safe_metadata_omits_unselected_unsafe_and_reflected_identity(self):
        for name, value in (("ETag", CONTACT), ("Last-Modified", "x\n"), ("Date", "x" * 1025),
                            ("Set-Cookie", "private"), ("Server", USER_AGENT)):
            self.response.headers[name] = value
        result = self.acquire()
        self.assertEqual(result.safe_response_metadata, (("Content-Type", "application/json"),))

    def test_etag_is_preserved_without_conditional_request(self):
        self.response.headers["ETag"] = '"fictional-version"'
        self.assertEqual(dict(self.acquire().safe_response_metadata)["ETag"], '"fictional-version"')
        self.assertNotIn("If-none-match", self.transport.call_args.args[0].headers)

    def test_live_and_offline_versions_and_closed_allowlist(self):
        live = SecArchive(self.root).read_receipt(self.acquire().archive_receipt_id)
        self.assertEqual(live.acquisition_contract_version, "2026-09-11-sec-live-companyfacts-v1")
        archive = SecArchive(self.root)
        offline = archive.capture(BODY, cik=CIK, captured_at=T1, source_locator=endpoint_for(CIK))
        self.assertEqual(offline.acquisition_contract_version, "2026-09-10-offline-supplied-companyfacts-v1")
        self.assertEqual(ACQUISITION_CONTRACT_VERSION, offline.acquisition_contract_version)
        for receipt in (live, offline):
            self.assertEqual(CaptureReceipt.from_bytes(receipt.to_bytes()), receipt)
        with self.assertRaises(ArchiveError):
            replace(live, acquisition_contract_version="arbitrary-live-version")
        for keyword in ("acquisition_contract_version", "live"):
            with self.assertRaises(TypeError):
                archive.capture(BODY, cik=CIK, captured_at=T1, source_locator=endpoint_for(CIK), **{keyword: LIVE_ACQUISITION_CONTRACT_VERSION})

    def test_identical_bytes_different_times_keep_two_receipts_one_object(self):
        first = self.acquire()
        self.transport.return_value = Response()
        self.wall_clock.return_value = NOW + timedelta(seconds=5)
        second = self.acquire()
        self.assertEqual(first.content_sha256, second.content_sha256)
        self.assertNotEqual(first.archive_receipt_id, second.archive_receipt_id)
        self.assertEqual(len(list((self.root / "objects").iterdir())), 1)
        self.assertEqual(len(list((self.root / "receipts").iterdir())), 2)
        for result in (first, second):
            archive = SecArchive(self.root)
            self.assertEqual(archive.read_object(archive.read_receipt(result.archive_receipt_id)), BODY)

    def test_live_object_corruption_still_fails_archive_read(self):
        result = self.acquire()
        target = self.root / "objects" / result.content_sha256
        target.chmod(0o600)
        target.write_bytes(b"corrupt")
        archive = SecArchive(self.root)
        with self.assertRaises(ArchiveError):
            archive.read_object(archive.read_receipt(result.archive_receipt_id))

    def test_archive_failure_is_typed_without_contact(self):
        with patch.object(SecArchive, "_capture_live", side_effect=ArchiveError(USER_AGENT)):
            self.fail(Reason.ARCHIVE_ERROR)

    def test_receipt_publication_failure_can_leave_valid_unreferenced_object(self):
        original = SecArchive._publish
        def fail_receipt(archive, kind, name, body):
            if kind == "receipts":
                raise ArchiveError("fixture failure")
            return original(archive, kind, name, body)
        with patch.object(SecArchive, "_publish", fail_receipt), self.assertRaises(SecAcquisitionError) as caught:
            self.acquire()
        self.assertEqual(caught.exception.reason, Reason.ARCHIVE_ERROR)
        self.assertEqual((self.root / "objects" / digest(BODY)).read_bytes(), BODY)
        self.assertFalse((self.root / "receipts").exists())

    def test_rate_spacing_has_no_burst_credit_and_covers_failed_attempts(self):
        starts = []
        def transport(request):
            starts.append(self.clock.value)
            if len(starts) == 2:
                raise urllib.error.URLError("fixture")
            return Response()
        self.transport.side_effect = transport
        self.acquire()
        with self.assertRaises(SecAcquisitionError):
            self.acquire()
        self.acquire()
        self.clock.value += 100  # Idle time does not buy a burst.
        self.acquire()
        self.assertEqual(self.clock.sleeps, [0.25] * 4)
        self.assertTrue(all(b - a >= 0.25 for a, b in zip(starts, starts[1:])))

    def test_early_sleep_return_does_not_skip_full_interval(self):
        def early(seconds):
            self.clock.value += min(seconds, 0.125)
        with patch.object(acquisition.time, "sleep", early):
            self.acquire()
        self.assertEqual(self.clock.value, 100.25)

    def test_gate_contention_fails_before_transport(self):
        with acquisition._rate_gate():
            self.fail(Reason.RATE_LIMITED, network=False)
        self.acquire()  # Contention did not damage the shared lock.

    def test_cross_process_gate_blocks_other_archive_root(self):
        code = '''
import sys
from pathlib import Path
from economic_facts import sec_acquisition as a
a._state_directory = lambda: Path(sys.argv[1])
a._open_response = lambda request: (_ for _ in ()).throw(AssertionError("network forbidden"))
try:
    a.acquire_companyfacts(cik="0000000000", archive_root=Path(sys.argv[2]))
except a.SecAcquisitionError as error:
    print(error.reason.value)
else:
    raise AssertionError("concurrent acquisition admitted")
'''
        other = self.root.parent / "other-archive"
        with acquisition._rate_gate():
            result = subprocess.run([sys.executable, "-c", code, str(self.state), str(other)],
                                    capture_output=True, text=True, check=True, timeout=10)
        self.assertEqual(result.stdout.strip(), "RATE_LIMITED")
        self.assertFalse(other.exists())
        self.transport.assert_not_called()

    def test_gate_symlink_and_unsafe_permissions_fail_before_network(self):
        self.state.mkdir()
        target = self.state / "elsewhere"
        target.touch()
        (self.state / "gate.lock").symlink_to(target)
        self.fail(Reason.CONFIGURATION_ERROR, network=False)
        (self.state / "gate.lock").unlink()
        self.state.chmod(0o777)
        self.fail(Reason.CONFIGURATION_ERROR, network=False)

    def test_gate_storage_failure_precedes_network(self):
        with patch.object(acquisition.os, "open", side_effect=OSError(USER_AGENT)):
            self.fail(Reason.CONFIGURATION_ERROR, network=False)

    def test_cli_safe_output_and_failure(self):
        output, errors = io.StringIO(), io.StringIO()
        with patch.object(sys, "stdout", output), patch.object(sys, "stderr", errors):
            self.assertEqual(cli.main(["--cik", CIK, "--archive-root", str(self.root)]), 0)
        value = json.loads(output.getvalue())
        self.assertEqual(set(value), {"success", "cik", "content_sha256", "receipt_id", "captured_at"})
        self.assertNotIn(CONTACT, output.getvalue() + errors.getvalue())
        with patch.dict(acquisition.os.environ, {}, clear=True), patch.object(sys, "stderr", errors):
            self.assertEqual(cli.main(["--cik", CIK, "--archive-root", str(self.root)]), 1)
        self.assertIn("CONFIGURATION_ERROR", errors.getvalue())

    def test_cli_rejects_additional_authority_inputs(self):
        for name in ("--url", "--captured-at", "--ticker", "--user-agent", "--universe"):
            with patch.object(sys, "stderr", io.StringIO()), self.assertRaises(SystemExit) as caught:
                cli.main(["--cik", CIK, "--archive-root", str(self.root), name, "forged"])
            self.assertEqual(caught.exception.code, 2)
        self.transport.assert_not_called()


class SecAcquisitionBoundaryTests(unittest.TestCase):
    def test_real_opener_retains_tls_verification_disables_proxies_and_bounds_timeout(self):
        request = urllib.request.Request(endpoint_for(CIK))
        opener = Mock()
        with patch.dict(acquisition.os.environ, {"HTTPS_PROXY": "http://proxy.invalid", "https_proxy": "http://proxy.invalid"}), \
             patch.object(urllib.request, "build_opener", return_value=opener) as builder:
            acquisition._open_response(request)
        handlers = builder.call_args.args
        self.assertEqual(handlers[0].proxies, {})
        context = handlers[1]._context
        self.assertEqual(context.verify_mode, ssl.CERT_REQUIRED)
        self.assertTrue(context.check_hostname)
        self.assertIsInstance(handlers[2], acquisition._RejectRedirects)
        opener.open.assert_called_once_with(request, timeout=15)

    def test_only_archive_dependency_and_no_model_consumers(self):
        root = Path(__file__).resolve().parents[1]
        allowed = {"dataclasses", "datetime", "enum", "fcntl", "http.client", "json", "math",
                   "os", "pathlib", "re", "ssl", "stat", "time", "urllib.error", "urllib.request", "contextlib"}
        tree = ast.parse((root / "economic_facts/sec_acquisition.py").read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                self.assertTrue(all(alias.name in allowed for alias in node.names))
            if isinstance(node, ast.ImportFrom):
                self.assertTrue((node.level == 1 and node.module == "sec_archive") or node.module in allowed)
        for directory in ("src", "pit_comparison", "economic_facts", "scripts"):
            for file in (root / directory).rglob("*.py"):
                if file.name in ("sec_acquisition.py", "capture_sec_companyfacts.py", "sec_filing_acquisition.py", "sec_submissions_acquisition.py",
                                  "sec_ticker_exchange_acquisition.py"):
                    continue
                for node in ast.walk(ast.parse(file.read_text())):
                    if isinstance(node, ast.Import):
                        self.assertFalse(any("sec_acquisition" in alias.name for alias in node.names), str(file))
                    if isinstance(node, ast.ImportFrom):
                        self.assertNotIn("sec_acquisition", node.module or "", str(file))
                        self.assertFalse(any(alias.name == "sec_acquisition" for alias in node.names), str(file))
