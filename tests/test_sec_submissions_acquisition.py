"""Fictional exact submissions, patched transport, real shared rate mechanism."""
import ast
from dataclasses import FrozenInstanceError, asdict
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

from economic_facts import sec_acquisition as shared
from economic_facts import sec_submissions_acquisition as a
from economic_facts.sec_submissions_acquisition import SubmissionsAcquisitionReason as R, SecSubmissionsAcquisitionError as Error
from economic_facts.sec_submissions_archive import SecSubmissionsArchive, SubmissionsArchiveError, endpoint_for
from tests.sec_submissions_fixtures import CIK, T1, T2, NAME, NAME2, root, root_value, row, reference, columns, history, encode
from economic_facts import sec_submissions_archive as archive_module

CONTACT = "administrator" + "@" + "fixture.invalid"
USER_AGENT = "FictionalFilingTests/1.0 " + CONTACT
NOW = datetime(2026, 9, 20, 12, tzinfo=timezone.utc)


class Response(io.BytesIO):
    def __init__(self, body=None, *, status=200, headers=None, url=None):
        super().__init__(root() if body is None else body)
        self.status = status
        self.url = endpoint_for(CIK) if url is None else url
        self.headers = Message()
        for key, value in ({"Content-Type": "application/json"} if headers is None else headers).items():
            self.headers[key] = value
        self.sizes = []

    def geturl(self):
        return self.url

    def read1(self, size=-1):
        assert size > 0
        self.sizes.append(size)
        return super().read(size)


class SubmissionsAcquisitionTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name).resolve() / "archive"
        self.state = self.root.parent / "gate"
        self.now = 100.0
        self.sleeps = []
        self.response = Response()
        self.real_open_response = shared._open_response
        self.transport = self.patched(shared, "_open_response", return_value=self.response)
        self.patched(shared, "_state_directory", return_value=self.state)
        self.wall = self.patched(shared, "_utc_now", return_value=NOW)
        self.patched(shared.time, "monotonic", side_effect=lambda: self.now)
        self.patched(shared.time, "sleep", side_effect=self.sleep)
        env = patch.dict(shared.os.environ, {shared.USER_AGENT_ENV: USER_AGENT})
        env.start()
        self.addCleanup(env.stop)

    def patched(self, obj, name, **kwargs):
        patcher = patch.object(obj, name, **kwargs)
        result = patcher.start()
        self.addCleanup(patcher.stop)
        return result

    def sleep(self, seconds):
        self.sleeps.append(seconds)
        self.now += seconds

    def fail(self, reason, *, network=True, **changes):
        before = self.transport.call_count
        with self.assertRaises(Error) as caught:
            self.acquire(**changes)
        self.assertEqual(caught.exception.reason, reason)
        self.assertEqual(self.transport.call_count - before, int(network))
        self.assertFalse(self.root.exists())
        self.assertNotIn(CONTACT, str(caught.exception))
        return caught.exception

    def test_invalid_cik_no_network(self):
        for cik in (None, 0, True, "1", "00000000000", "٠" * 10, "0000000000 ", "../x", CIK + "?x"):
            with self.subTest(cik=cik):
                self.fail(R.CONFIGURATION_ERROR, network=False, cik=cik)

    def test_configuration_errors_precede_network(self):
        with patch.dict(shared.os.environ, {}, clear=True):
            self.fail(R.CONFIGURATION_ERROR, network=False)
        for value in (CONTACT, USER_AGENT + "\r\nX: y", "Mozilla/5.0 " + CONTACT):
            with patch.dict(shared.os.environ, {shared.USER_AGENT_ENV: value}):
                self.fail(R.CONFIGURATION_ERROR, network=False)
        for root in (None, 3, "bad\x00path"):
            self.fail(R.CONFIGURATION_ERROR, network=False, archive_root=root)

    def test_single_request_non200_statuses(self):
        for status in (201, 204, 301, 302, 303, 304, 307, 308, 403, 404, 429, 500, 503):
            self.transport.return_value = Response(status=status)
            reason = R.REDIRECT_REJECTED if 300 <= status < 400 else R.RATE_LIMITED if status == 429 else R.HTTP_ERROR
            with self.subTest(status=status):
                self.assertEqual(self.fail(reason).status, status)

    def test_http_errors_close_body_and_hide_contact(self):
        for status in (302, 403, 429, 503):
            stream = io.BytesIO(USER_AGENT.encode())
            self.transport.side_effect = urllib.error.HTTPError(endpoint_for(CIK), status, USER_AGENT, {}, stream)
            reason = R.REDIRECT_REJECTED if status == 302 else R.RATE_LIMITED if status == 429 else R.HTTP_ERROR
            self.fail(reason)
            self.assertTrue(stream.closed)
            try:
                self.acquire()
            except Error:
                self.assertNotIn(CONTACT, traceback.format_exc())

    def test_tls_proxy_timeout_and_redirect_policy_inherited(self):
        opener = Mock()
        with patch.object(urllib.request, "build_opener", return_value=opener) as build, \
             patch.dict(shared.os.environ, {"https_proxy": "http://untrusted.invalid"}):
            self.real_open_response(urllib.request.Request(endpoint_for(CIK)))
        handlers = build.call_args.args
        self.assertEqual(handlers[0].proxies, {})
        self.assertTrue(handlers[1]._context.check_hostname)
        self.assertEqual(handlers[1]._context.verify_mode, ssl.CERT_REQUIRED)
        self.assertEqual(opener.open.call_args.kwargs, {"timeout": 15})
        response = Response()
        with self.assertRaises(shared.SecAcquisitionError):
            handlers[2].redirect_request(None, response, 302, "", {}, "https://other.invalid")
        self.assertTrue(response.closed)
        self.assertIs(a._sec, shared)

    def test_changed_response_locator_rejected(self):
        self.transport.return_value = Response(url="https://other.invalid")
        self.fail(R.REDIRECT_REJECTED)

    def test_network_and_timeout_errors_safe(self):
        for error, reason in ((TimeoutError(USER_AGENT), R.TIMEOUT),
                              (urllib.error.URLError(TimeoutError(USER_AGENT)), R.TIMEOUT),
                              (ssl.SSLCertVerificationError(USER_AGENT), R.NETWORK_ERROR),
                              (urllib.error.URLError(USER_AGENT), R.NETWORK_ERROR),
                              (ConnectionResetError(USER_AGENT), R.NETWORK_ERROR),
                              (a.http.client.IncompleteRead(b"private"), R.NETWORK_ERROR)):
            self.transport.side_effect = error
            self.fail(reason)

    def test_read_timeout_closes_response(self):
        self.response.read1 = Mock(side_effect=TimeoutError(USER_AGENT))
        self.fail(R.TIMEOUT)
        self.assertTrue(self.response.closed)

    def test_deadline_checked_after_receive(self):
        def slow(size):
            self.now += shared.RESPONSE_DEADLINE_SECONDS
            return root()
        self.response.read1 = slow
        self.fail(R.TIMEOUT)

    def test_deadline_checked_before_receive(self):
        def slow_open(request):
            self.now += shared.RESPONSE_DEADLINE_SECONDS
            return self.response
        self.transport.side_effect = slow_open
        self.fail(R.TIMEOUT)
        self.assertEqual(self.response.sizes, [])

    def test_size_declared_rejected_before_read(self):
        self.response.headers["Content-Length"] = str(shared.MAX_BODY_BYTES + 1)
        self.fail(R.RESPONSE_TOO_LARGE)
        self.assertEqual(self.response.sizes, [])

    def test_streaming_limit_and_bounded_reads(self):
        self.transport.return_value = Response(root() + b"xx")
        with patch.object(shared, "MAX_BODY_BYTES", len(root())):
            self.fail(R.RESPONSE_TOO_LARGE)
        self.assertEqual(self.transport.return_value.sizes, [len(root()) + 1])

    def test_exact_maximum_allowed(self):
        self.response.headers["Content-Length"] = str(len(root()))
        with patch.object(shared, "MAX_BODY_BYTES", len(root())):
            self.assertEqual(self.acquire().receipt.byte_length, len(root()))

    def test_malformed_or_truncated_content_length(self):
        for value in ("-1", "abc", "1,2", "9" * 21, "0", str(len(root()) + 1)):
            self.transport.return_value = Response(headers={"Content-Type": "application/json", "Content-Length": value})
            self.fail(R.INVALID_RESPONSE)

    def test_closed_mime_policy(self):
        for value in (None, "text/html", "text/plain", "application/octet-stream", "application/json; charset=latin1",
                      "application/json; anything=x", "application/json, text/html"):
            self.transport.return_value = Response(headers={} if value is None else {"Content-Type": value})
            self.fail(R.INVALID_CONTENT_TYPE)

    def test_clock_regression_or_naive_clock(self):
        self.wall.side_effect = [NOW, NOW - timedelta(seconds=1), NOW]
        self.fail(R.CONFIGURATION_ERROR)
        self.wall.side_effect = None
        self.wall.return_value = NOW.replace(tzinfo=None)
        self.fail(R.CONFIGURATION_ERROR, network=False)

    def test_shared_gate_contention(self):
        with shared._rate_gate():
            self.fail(R.RATE_LIMITED, network=False)
        self.acquire()

    def test_cross_process_shared_gate_prevents_filing_request(self):
        code = '''
import sys
from pathlib import Path
from economic_facts import sec_acquisition as shared
from economic_facts.sec_submissions_acquisition import acquire_sec_submissions, SecSubmissionsAcquisitionError
shared._state_directory = lambda: Path(sys.argv[1])
shared._open_response = lambda r: (_ for _ in ()).throw(AssertionError("network forbidden"))
try:
    acquire_sec_submissions(cik="0000000000", archive_root=sys.argv[2])
except SecSubmissionsAcquisitionError as error:
    print(error.reason.value)
else:
    raise AssertionError("contention admitted")
'''
        with shared._rate_gate():
            child = subprocess.run([sys.executable, "-c", code, str(self.state), str(self.root)],
                                   capture_output=True, text=True, check=True, timeout=10)
        self.assertEqual(child.stdout.strip(), "RATE_LIMITED")
        self.assertFalse(self.root.exists())
        self.transport.assert_not_called()

    def acquire(self, **changes):
        return a.acquire_sec_submissions(**{**dict(cik=CIK, archive_root=self.root), **changes})

    def child(self, parent, filename=NAME):
        return a.acquire_sec_submissions_history(archive_root=self.root,
                                                parent_receipt_id=parent.receipt_id, history_filename=filename)

    def test_exact_request_headers_bytes_and_chronology(self):
        self.wall.side_effect = [NOW, NOW + timedelta(seconds=1), NOW + timedelta(seconds=2)]
        result = self.acquire()
        request = self.transport.call_args.args[0]
        self.assertEqual(request.full_url, "https://data.sec.gov/submissions/CIK0000000123.json")
        self.assertEqual(request.get_method(), "GET")
        self.assertEqual(dict(request.header_items()), {
            "User-agent": USER_AGENT, "Accept": "application/json", "Accept-encoding": "identity"})
        self.assertEqual(SecSubmissionsArchive(self.root).read_object(result.receipt), root())
        self.assertEqual(result.request_started_at, T1)
        self.assertEqual(result.response_completed_at, "2026-09-20T12:00:01Z")
        self.assertEqual(result.receipt.captured_at, T2)
        self.assertTrue(all(0 < size <= 65536 for size in self.response.sizes))
        self.assertEqual(set(asdict(result)), {"receipt", "request_started_at", "response_completed_at"})
        with self.assertRaises(FrozenInstanceError):
            result.receipt = None

    def test_public_signatures_exclude_injection(self):
        self.assertEqual(set(inspect.signature(a.acquire_sec_submissions).parameters), {"cik", "archive_root"})
        self.assertEqual(set(inspect.signature(a.acquire_sec_submissions_history).parameters),
                         {"archive_root", "parent_receipt_id", "history_filename"})
        for keyword in ("url", "raw", "clock", "transport", "captured_at", "as_of", "authority",
                        "complete", "qualified", "published_at", "user_agent", "retry_policy"):
            with self.subTest(keyword=keyword), self.assertRaises(TypeError):
                self.acquire(**{keyword: True})
        self.transport.assert_not_called()

    def test_child_exact_reference_endpoint_and_no_width_assumption(self):
        self.transport.return_value = Response(root(refs=[reference(NAME2)]))
        parent = self.acquire().receipt
        self.transport.return_value = Response(history(), url=endpoint_for(CIK, NAME2))
        child = self.child(parent, NAME2).receipt
        self.assertEqual(child.parent_receipt_id, parent.receipt_id)
        self.assertEqual(child.history_filename, NAME2)
        self.assertEqual(self.transport.call_args.args[0].full_url, endpoint_for(CIK, NAME2))
        self.assertEqual(self.transport.call_count, 2)
        self.assertEqual(SecSubmissionsArchive(self.root).read_object(child), history())

    def test_unsafe_absent_and_foreign_cik_filenames_fail_before_network(self):
        self.transport.return_value = Response(root(refs=[reference()]))
        parent = self.acquire().receipt
        self.transport.reset_mock()
        for name in (NAME2, "../" + NAME, "/" + NAME, NAME + "?x", NAME + "#x", NAME + " ",
                     NAME.replace("-", "%2d"), NAME.replace("0", "٠"), NAME.replace(CIK, "0000000124"),
                     "https://data.sec.gov/" + NAME, "x\\" + NAME, NAME + "\n", None, 1):
            with self.subTest(name=name), self.assertRaises(Error) as caught:
                self.child(parent, name)
            self.assertEqual(caught.exception.reason, R.INVALID_REQUEST)
        self.transport.assert_not_called()

    def test_invalid_missing_corrupt_parent_fail_before_network(self):
        for selector, reason in (("../x", R.INVALID_REQUEST), ("0" * 64, R.ARCHIVE_INTEGRITY_ERROR)):
            with self.assertRaises(Error) as caught:
                a.acquire_sec_submissions_history(archive_root=self.root, parent_receipt_id=selector, history_filename=NAME)
            self.assertEqual(caught.exception.reason, reason)
        self.transport.assert_not_called()
        self.transport.return_value = Response(root(refs=[reference()]))
        parent = self.acquire().receipt
        target = self.root / "objects" / parent.content_sha256
        target.chmod(0o600)
        target.write_bytes(b"corrupt")
        self.transport.reset_mock()
        with self.assertRaises(Error) as caught:
            self.child(parent)
        self.assertEqual(caught.exception.reason, R.ARCHIVE_INTEGRITY_ERROR)
        self.transport.assert_not_called()

    def test_duplicate_and_ambiguous_headers(self):
        for key, value in (("Content-Type", "application/json"), ("Content-Length", str(len(root()))),
                           ("Content-Encoding", "identity"), ("Transfer-Encoding", "chunked")):
            self.transport.return_value = Response()
            if key != "Content-Type":
                self.transport.return_value.headers[key] = value
            self.transport.return_value.headers[key] = value
            self.fail(R.INVALID_RESPONSE)
        for headers in ({"Content-Encoding": "gzip"}, {"Transfer-Encoding": "gzip"},
                        {"Transfer-Encoding": "chunked", "Content-Length": str(len(root()))}):
            self.transport.return_value = Response(headers={"Content-Type": "application/json", **headers})
            self.fail(R.INVALID_RESPONSE)

    def test_json_mime_allowed_variants(self):
        for value in ('application/json', 'Application/JSON; charset="UTF-8"', 'application/json; charset=utf-8'):
            self.transport.return_value = Response(headers={"Content-Type": value})
            self.acquire()

    def test_root_preflight_rejects_shapes_before_publication(self):
        bodies = [b'[]', b'{}', b'null', b'not json', b'\xff', b'{"cik":123,"cik":123}',
                  b'{"cik":NaN}', b'{"cik":Infinity}', b'{"cik":1e999}', b'[' * 100 + b']' * 100]
        for changes in ({"cik": 124}, {"cik": True}, {"cik": "٠" * 10}, {"filings": {}},
                        {"filings": {"recent": columns()}}, {"filings": {"files": []}},
                        {"newNested": {"attacker": []}}, {"addresses": []}):
            bodies.append(encode(root_value(**changes)))
        for raw in bodies:
            with self.subTest(raw=raw[:30]):
                self.transport.return_value = Response(raw)
                self.fail(R.UNSUPPORTED_STRUCTURE)

    def test_source_cik_integer_or_ascii_string(self):
        for cik in (123, "123", CIK):
            self.transport.return_value = Response(root(cik=cik))
            self.acquire()

    def test_column_validation_unknown_scalars_and_all_forms(self):
        forms = ["10-K/A", "8-K", "S-1", "15-12G", "DEF 14A", "4", "UNFAMILIAR FORM"]
        rows = [row(index + 1, form=form, newColumn="retained") for index, form in enumerate(forms)]
        raw = root(rows=rows)
        self.transport.return_value = Response(raw)
        self.assertEqual(SecSubmissionsArchive(self.root).read_object(self.acquire().receipt), raw)

    def test_incompatible_columns_and_accessions(self):
        values = []
        for bad in ([], None, ["bad"], [row()["accessionNumber"], row()["accessionNumber"]]):
            value = root_value()
            value["filings"]["recent"]["accessionNumber"] = bad
            values.append(value)
        for bad in ([{"nested": 1}], [["nested"]], [1.2]):
            value = root_value()
            value["filings"]["recent"]["unknown"] = bad
            values.append(value)
        for value in values:
            self.transport.return_value = Response(encode(value))
            self.fail(R.UNSUPPORTED_STRUCTURE)

    def test_reference_metadata_bounds_and_duplicates(self):
        for refs in ([reference("../evil")], [reference(), reference()],
                     [reference(filingCount=True)], [reference(filingCount=-1)],
                     [reference(filingFrom="2026-99-99")], [reference(filingTo="1999-01-01")],
                     [reference(newNested={})], [{}], ["filename"]):
            self.transport.return_value = Response(root(refs=refs))
            self.fail(R.UNSUPPORTED_STRUCTURE)

    def test_mechanical_resource_limits_fail_without_truncation(self):
        for constant, bound, raw in (("MAX_ROWS", 0, root()), ("MAX_REFERENCES", 0, root(refs=[reference()])),
                                    ("MAX_COLUMNS", 2, root()), ("MAX_STRING_LENGTH", 3, root()),
                                    ("MAX_METADATA_ITEMS", 0, root()), ("MAX_CELLS", 1, root()),
                                    ("MAX_JSON_DEPTH", 2, root())):
            self.transport.return_value = Response(raw)
            with patch.object(archive_module, constant, bound):
                self.fail(R.UNSUPPORTED_STRUCTURE)

    def test_child_preflight_failure_keeps_only_parent(self):
        self.transport.return_value = Response(root(refs=[reference()]))
        parent = self.acquire().receipt
        for body in (b'{}', root(), history([row(accessionNumber="bad")]),
                     encode({**columns(), "form": []})):
            self.transport.return_value = Response(body, url=endpoint_for(CIK, NAME))
            with self.assertRaises(Error) as caught:
                self.child(parent)
            self.assertEqual(caught.exception.reason, R.UNSUPPORTED_STRUCTURE)
        self.assertEqual(len(list((self.root / "receipts").iterdir())), 1)

    def test_gate_is_held_through_archive_publication(self):
        original = SecSubmissionsArchive._capture_live
        def capture(archive, *args, **kwargs):
            with self.assertRaises(shared.SecAcquisitionError) as caught:
                with shared._rate_gate():
                    pass
            self.assertEqual(caught.exception.reason.value, "RATE_LIMITED")
            return original(archive, *args, **kwargs)
        with patch.object(SecSubmissionsArchive, "_capture_live", capture):
            self.acquire()

    def test_programming_errors_propagate(self):
        self.transport.side_effect = RuntimeError("programming defect")
        with self.assertRaises(RuntimeError):
            self.acquire()

    def test_archive_error_translation(self):
        with patch.object(SecSubmissionsArchive, "_capture_live", side_effect=SubmissionsArchiveError("private")):
            self.fail(R.ARCHIVE_INTEGRITY_ERROR)

    def test_child_uses_shared_gate_and_rejects_nonroot_parent(self):
        self.transport.return_value = Response(root(refs=[reference()]))
        parent = self.acquire().receipt
        self.transport.return_value = Response(history(), url=endpoint_for(CIK, NAME))
        with shared._rate_gate(), self.assertRaises(Error) as caught:
            self.child(parent)
        self.assertEqual(caught.exception.reason, R.RATE_LIMITED)
        self.assertEqual(self.transport.call_count, 1)
        child = self.child(parent).receipt
        with self.assertRaises(Error) as caught:
            self.child(child)
        self.assertEqual(caught.exception.reason, R.INVALID_REQUEST)
        self.assertEqual(self.transport.call_count, 2)

    def test_child_clock_cannot_backdate_to_before_parent(self):
        self.transport.return_value = Response(root(refs=[reference()]))
        parent = self.acquire().receipt
        self.wall.return_value = NOW - timedelta(seconds=1)
        self.transport.return_value = Response(history(), url=endpoint_for(CIK, NAME))
        with self.assertRaises(Error) as caught:
            self.child(parent)
        self.assertEqual(caught.exception.reason, R.CONFIGURATION_ERROR)
        self.assertEqual(len(list((self.root / "receipts").iterdir())), 1)

    def test_source_dates_strings_numbers_and_nested_duplicates_fail_closed(self):
        for changes in ({"filingDate": "2026-02-30"}, {"reportDate": None},
                        {"acceptanceDateTime": "2026-02-01T15:30:00"},
                        {"acceptanceDateTime": "2026-02-30T15:30:00Z"},
                        {"form": ""}, {"form": False}, {"primaryDocument": None},
                        {"size": 2**63}, {"items": "x" * 16385}, {"items": "\ud800"}):
            self.transport.return_value = Response(root(rows=[row(**changes)]))
            self.fail(R.UNSUPPORTED_STRUCTURE)
        raw = root().replace(b'"size": [1200]', b'"size": [1200], "size": [1200]')
        self.transport.return_value = Response(raw)
        self.fail(R.UNSUPPORTED_STRUCTURE)

    def test_child_row_limit_and_no_c3_form_filter(self):
        self.transport.return_value = Response(root(refs=[reference()]))
        parent = self.acquire().receipt
        self.transport.return_value = Response(history([row(form="UNKNOWN")]), url=endpoint_for(CIK, NAME))
        self.child(parent)
        self.transport.return_value = Response(history([row(), row(2)]), url=endpoint_for(CIK, NAME))
        with patch.object(archive_module, "MAX_ROWS", 1), self.assertRaises(Error) as caught:
            self.child(parent)
        self.assertEqual(caught.exception.reason, R.UNSUPPORTED_STRUCTURE)

    def test_brackets_and_escaped_quotes_inside_strings_are_not_depth(self):
        self.transport.return_value = Response(root(description='[{' * 100 + '\\"escaped quote'))
        self.acquire()

    def test_unknown_metadata_shapes_and_bad_column_names_are_unsupported(self):
        for changes in ({"formerNames": [{"name": "missing dates"}]}, {"tickers": [1]},
                        {"addresses": {"unexpected": {}}}, {"unknown": []}):
            self.transport.return_value = Response(root(**changes))
            self.fail(R.UNSUPPORTED_STRUCTURE)
        value = root_value()
        value['filings']['recent']['bad/key'] = [1]
        self.transport.return_value = Response(encode(value))
        self.fail(R.UNSUPPORTED_STRUCTURE)
