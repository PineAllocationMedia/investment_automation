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
from economic_facts import sec_filing_acquisition as a
from economic_facts.sec_filing_acquisition import FilingAcquisitionReason as R, SecFilingAcquisitionError as Error
from economic_facts.sec_filing_archive import SecFilingArchive, FilingArchiveError, endpoint_for
from tests.sec_original_filing_fixtures import ACCESSION, CIK, T1, T2, document, filing

CONTACT = "administrator" + "@" + "fixture.invalid"
USER_AGENT = "FictionalFilingTests/1.0 " + CONTACT
NOW = datetime(2026, 9, 20, 12, tzinfo=timezone.utc)


class Response(io.BytesIO):
    def __init__(self, body=None, *, status=200, headers=None, url=None):
        super().__init__(filing() if body is None else body)
        self.status = status
        self.url = endpoint_for(CIK, ACCESSION) if url is None else url
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


class FilingAcquisitionTests(unittest.TestCase):
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

    def acquire(self, **changes):
        return a.acquire_sec_filing(**{**dict(cik=CIK, accession=ACCESSION, archive_root=self.root), **changes})

    def fail(self, reason, *, network=True, **changes):
        before = self.transport.call_count
        with self.assertRaises(Error) as caught:
            self.acquire(**changes)
        self.assertEqual(caught.exception.reason, reason)
        self.assertEqual(self.transport.call_count - before, int(network))
        self.assertFalse(self.root.exists())
        self.assertNotIn(CONTACT, str(caught.exception))
        return caught.exception

    def test_exact_request_and_replay(self):
        result = self.acquire()
        request = self.transport.call_args.args[0]
        self.assertEqual(request.full_url, endpoint_for(CIK, ACCESSION))
        self.assertEqual(request.get_method(), "GET")
        self.assertEqual(dict(request.header_items()), {
            "User-agent": USER_AGENT, "Accept": "text/plain", "Accept-encoding": "identity"})
        self.assertEqual(SecFilingArchive(self.root).read_object(result.receipt), filing())
        self.assertEqual(result.envelope, a.FilingEnvelope(CIK, ACCESSION, "10-K", 1))
        self.assertTrue(all(0 < size <= 65536 for size in self.response.sizes))
        with self.assertRaises(FrozenInstanceError):
            result.receipt = None

    def test_agent_prefix_does_not_select_registrant(self):
        self.assertNotEqual(ACCESSION[:10], CIK)
        self.assertEqual(self.acquire().receipt.cik, CIK)

    def test_invalid_cik_no_network(self):
        for cik in (None, 0, True, "1", "00000000000", "٠" * 10, "0000000000 ", "../x", CIK + "?x"):
            with self.subTest(cik=cik):
                self.fail(R.CONFIGURATION_ERROR, network=False, cik=cik)

    def test_invalid_accession_no_network(self):
        for accession in (None, 0, "", "1-26-1", ACCESSION + " ", " " + ACCESSION,
                          ACCESSION + "?x", ACCESSION + "#x", "../" + ACCESSION,
                          ACCESSION.replace("-", "/"), ACCESSION.replace("-", "%2d"),
                          ACCESSION.replace("0", "٠"), ACCESSION + "\n", "https://sec.gov/x"):
            with self.subTest(accession=accession):
                self.fail(R.CONFIGURATION_ERROR, network=False, accession=accession)

    def test_public_api_rejects_all_authority_injection(self):
        self.assertEqual(set(inspect.signature(a.acquire_sec_filing).parameters), {"cik", "accession", "archive_root"})
        for keyword in ("url", "raw", "captured_at", "clock", "transport", "retry_policy", "rate_policy",
                        "user_agent", "authority", "profile", "qualified", "published_at", "available_at", "form"):
            with self.subTest(keyword=keyword), self.assertRaises(TypeError):
                self.acquire(**{keyword: "caller assertion"})
        self.transport.assert_not_called()

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
            self.transport.side_effect = urllib.error.HTTPError(endpoint_for(CIK, ACCESSION), status, USER_AGENT, {}, stream)
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
            self.real_open_response(urllib.request.Request(endpoint_for(CIK, ACCESSION)))
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
            return filing()
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
        self.response.headers["Content-Length"] = str(a.MAX_FILING_BYTES + 1)
        self.fail(R.RESPONSE_TOO_LARGE)
        self.assertEqual(self.response.sizes, [])

    def test_streaming_limit_and_bounded_reads(self):
        self.transport.return_value = Response(filing() + b"xx")
        with patch.object(a, "MAX_FILING_BYTES", len(filing())):
            self.fail(R.RESPONSE_TOO_LARGE)
        self.assertEqual(self.transport.return_value.sizes, [len(filing()) + 1])

    def test_exact_maximum_allowed(self):
        self.response.headers["Content-Length"] = str(len(filing()))
        with patch.object(a, "MAX_FILING_BYTES", len(filing())):
            self.assertEqual(self.acquire().receipt.byte_length, len(filing()))

    def test_malformed_or_truncated_content_length(self):
        for value in ("-1", "abc", "1,2", "9" * 21, "0", str(len(filing()) + 1)):
            self.transport.return_value = Response(headers={"Content-Type": "text/plain", "Content-Length": value})
            self.fail(R.INVALID_RESPONSE)

    def test_closed_mime_policy(self):
        for value in (None, "text/html", "application/json", "application/octet-stream", "text/plain; charset=latin1",
                      "text/plain; anything=x", "text/plain, text/html"):
            self.transport.return_value = Response(headers={} if value is None else {"Content-Type": value})
            self.fail(R.INVALID_CONTENT_TYPE)

    def test_reviewed_mime_spellings(self):
        for value in ("text/plain", 'Text/Plain; charset="UTF-8"', "text/plain; charset=us-ascii"):
            self.transport.return_value = Response(headers={"Content-Type": value})
            self.assertEqual(self.acquire().receipt.byte_length, len(filing()))

    def test_compression_and_ambiguous_framing(self):
        for extra in ({"Content-Encoding": "gzip"}, {"Content-Encoding": "br"}, {"Transfer-Encoding": "gzip"},
                      {"Transfer-Encoding": "chunked", "Content-Length": str(len(filing()))}):
            self.transport.return_value = Response(headers={"Content-Type": "text/plain", **extra})
            self.fail(R.INVALID_RESPONSE)

    def test_chunked_entity_and_identity_encoding(self):
        self.response.headers["Transfer-Encoding"] = "chunked"
        self.response.headers["Content-Encoding"] = "identity"
        self.assertEqual(SecFilingArchive(self.root).read_object(self.acquire().receipt), filing())

    def test_duplicate_transport_headers(self):
        for key, value in (("Content-Type", "text/plain"), ("Content-Encoding", "identity"),
                           ("Content-Length", "2"), ("Transfer-Encoding", "chunked")):
            self.transport.return_value = Response()
            if key != "Content-Type":
                self.transport.return_value.headers[key] = value
            self.transport.return_value.headers[key] = value
            self.fail(R.INVALID_RESPONSE)

    def test_private_contact_never_added_to_evidence_or_logs(self):
        self.response.headers["ETag"] = USER_AGENT
        self.response.headers["Date"] = CONTACT
        with patch.object(sys, "stdout", io.StringIO()) as output, patch.object(sys, "stderr", io.StringIO()) as errors:
            result = self.acquire()
        self.assertEqual(output.getvalue() + errors.getvalue(), "")
        self.assertNotIn(CONTACT, json.dumps(asdict(result)))
        for path in self.root.rglob("*"):
            if path.is_file():
                self.assertNotIn(CONTACT.encode(), path.read_bytes())
        self.assertEqual(SecFilingArchive(self.root).read_object(result.receipt), filing())

    def test_controlled_chronology_never_uses_filing_or_http_dates(self):
        self.response.headers["Date"] = "Mon, 01 Jan 1990 00:00:00 GMT"
        self.response.headers["Last-Modified"] = "Mon, 01 Jan 1990 00:00:00 GMT"
        self.wall.side_effect = [NOW, NOW + timedelta(seconds=1), NOW + timedelta(seconds=2)]
        result = self.acquire()
        self.assertEqual(result.request_started_at, T1)
        self.assertEqual(result.response_completed_at, "2026-09-20T12:00:01Z")
        self.assertEqual(result.receipt.captured_at, T2)
        for value in (asdict(result), asdict(result.receipt), asdict(result.envelope)):
            self.assertTrue({"published_at", "available_at", "authority", "admitted", "coverage"}.isdisjoint(value))

    def test_clock_regression_or_naive_clock(self):
        self.wall.side_effect = [NOW, NOW - timedelta(seconds=1), NOW]
        self.fail(R.CONFIGURATION_ERROR)
        self.wall.side_effect = None
        self.wall.return_value = NOW.replace(tzinfo=None)
        self.fail(R.CONFIGURATION_ERROR, network=False)

    def test_recapture_changed_bytes_does_not_rewrite_history(self):
        first = self.acquire()
        second_bytes = filing(payload=b"Corrected fictional document")
        self.transport.return_value = Response(second_bytes)
        self.wall.return_value = NOW + timedelta(seconds=2)
        second = self.acquire()
        self.assertNotEqual(first.receipt.content_sha256, second.receipt.content_sha256)
        self.assertEqual(first.receipt.captured_at, T1)
        self.assertEqual(second.receipt.captured_at, T2)
        archive = SecFilingArchive(self.root)
        self.assertEqual(archive.read_object(first.receipt), filing())
        self.assertEqual(archive.read_object(second.receipt), second_bytes)

    def test_shared_gate_contention(self):
        with shared._rate_gate():
            self.fail(R.RATE_LIMITED, network=False)
        self.acquire()

    def test_cross_process_shared_gate_prevents_filing_request(self):
        code = '''
import sys
from pathlib import Path
from economic_facts import sec_acquisition as shared
from economic_facts.sec_filing_acquisition import acquire_sec_filing, SecFilingAcquisitionError
shared._state_directory = lambda: Path(sys.argv[1])
shared._open_response = lambda r: (_ for _ in ()).throw(AssertionError("network forbidden"))
try:
    acquire_sec_filing(cik="0000000000", accession="0000000001-26-000001", archive_root=sys.argv[2])
except SecFilingAcquisitionError as error:
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

    def test_gate_held_through_archive_publication(self):
        original = SecFilingArchive._capture_live
        def publish(archive, *args, **kwargs):
            with self.assertRaises(shared.SecAcquisitionError) as caught:
                shared.acquire_companyfacts(cik=CIK, archive_root=self.root.parent / "companyfacts")
            self.assertEqual(caught.exception.reason, shared.AcquisitionReason.RATE_LIMITED)
            return original(archive, *args, **kwargs)
        with patch.object(SecFilingArchive, "_capture_live", publish):
            self.acquire()
        self.assertEqual(self.transport.call_count, 1)

    def test_rate_spacing_failure_and_no_burst(self):
        for index in range(3):
            self.transport.return_value = Response(status=503 if index == 1 else 200)
            if index == 1:
                with self.assertRaises(Error):
                    self.acquire()
            else:
                self.acquire()
            self.now += 100
        self.assertEqual(self.sleeps, [0.25] * 3)

    def test_unsafe_gate_fails_before_network(self):
        self.state.mkdir()
        self.state.chmod(0o777)
        self.fail(R.CONFIGURATION_ERROR, network=False)

    def test_archive_error_is_not_ordinary_unavailability(self):
        with patch.object(SecFilingArchive, "_capture_live", side_effect=FilingArchiveError(USER_AGENT)):
            self.fail(R.ARCHIVE_INTEGRITY_ERROR)

    def test_programming_error_propagates(self):
        with patch.object(a, "_preflight", side_effect=RuntimeError("programming defect")):
            with self.assertRaisesRegex(RuntimeError, "programming defect"):
                self.acquire()
        self.assertFalse(self.root.exists())

    def test_all_supported_forms_and_opaque_exhibits(self):
        for form in sorted(a.SUPPORTED_FORMS):
            raw = filing(form=form, extra=document("EX-99.1", "2", "exhibit.txt", b"Opaque exhibit \xff bytes"))
            self.transport.return_value = Response(raw)
            result = self.acquire()
            self.assertEqual(result.envelope.form, form)
            self.assertEqual(result.envelope.document_count, 2)
            self.assertEqual(SecFilingArchive(self.root).read_object(result.receipt), raw)

    def test_crlf_is_parsed_but_original_is_archived(self):
        raw = filing().replace(b"\n", b"\r\n")
        self.transport.return_value = Response(raw)
        self.assertEqual(SecFilingArchive(self.root).read_object(self.acquire().receipt), raw)

    def test_modern_header_trailing_tabs_and_empty_optional_field(self):
        raw = filing().replace(b"FILER:\n", b"FILER:\t\n")
        raw = raw.replace(b"COMPANY DATA:\n", b"COMPANY DATA:\t\n")
        raw = raw.replace(b"\tFILING VALUES:\n", b"\t\tORGANIZATION NAME:\t\t\n\tFILING VALUES:\n")
        self.transport.return_value = Response(raw)
        result = self.acquire()
        self.assertEqual(result.envelope.cik, CIK)
        self.assertEqual(SecFilingArchive(self.root).read_object(result.receipt), raw)

    def test_unreviewed_header_suffix_rejected(self):
        for suffix in (b".hdr", b".html", b".hdrXsgml"):
            self.transport.return_value = Response(filing().replace(b".hdr.sgml", suffix))
            self.fail(R.UNSUPPORTED_FILING_ENVELOPE)

    def test_wrong_accession_or_registrant(self):
        for raw in (filing(accession="0000000002-26-000001"), filing(cik="0000000002"),
                    filing().replace(b"ACCESSION NUMBER:\t\t" + ACCESSION.encode(),
                                     b"ACCESSION NUMBER:\t\t0000000002-26-000001")):
            self.transport.return_value = Response(raw)
            self.fail(R.FILING_SELECTOR_MISMATCH)

    def test_unsupported_forms(self):
        for form in ("20-F", "6-K", "S-1", "4", "NT 10-K"):
            self.transport.return_value = Response(filing(form=form))
            self.fail(R.UNSUPPORTED_FILING_ENVELOPE)

    def test_ambiguous_joint_filer_and_other_roles(self):
        raw = filing()
        for replacement in (b"FILER:\nFILER:", b"SUBJECT COMPANY:\nFILER:", b"REPORTING-OWNER:\nFILER:",
                            b"ISSUER:\nFILER:", b"UNKNOWN ROLE:\nFILER:"):
            self.transport.return_value = Response(raw.replace(b"FILER:", replacement))
            self.fail(R.UNSUPPORTED_FILING_ENVELOPE)
        self.transport.return_value = Response(raw.replace(b"\tFILING VALUES:",
            b"\t\tCENTRAL INDEX KEY:\t0000000002\n\tFILING VALUES:"))
        self.fail(R.UNSUPPORTED_FILING_ENVELOPE)

    def test_malformed_or_superficial_source(self):
        bodies = (b"", b"<html>SEC-DOCUMENT ACCESSION NUMBER FILER</html>", b"{}", b"\xff", filing()[:-20],
                  filing() + filing(), b"prefix" + filing(), filing().replace(b"</SEC-HEADER>", b""),
                  filing().replace(b"<SEC-HEADER>", b"<IMS-HEADER>"),
                  filing().replace(b"<ACCEPTANCE-DATETIME>20260201153000", b""),
                  filing().replace(b"</DOCUMENT>", b""), filing().replace(b"</TEXT>", b""),
                  filing().replace(b"PUBLIC DOCUMENT COUNT:\t\t1", b"PUBLIC DOCUMENT COUNT:\t\t2"),
                  filing().replace(b"PUBLIC DOCUMENT COUNT:\t\t1", b"PUBLIC DOCUMENT COUNT:\t\t0"),
                  filing().replace(b"<TYPE>10-K", b"<TYPE>10-Q"),
                  filing().replace(b"FORM TYPE:\t\t10-K", b"FORM TYPE:\t\t10-Q"),
                  filing().replace(b"<FILENAME>fictional.htm", b"<FILENAME>../fictional.htm"),
                  filing().replace(b"<SEQUENCE>1", b"<SEQUENCE>1\n<SEQUENCE>2"),
                  filing(payload=b""), filing(payload=b"\n<DOCUMENT>\nforged"),
                  filing().replace(b"\tCOMPANY DATA:", b"\tUNKNOWN CONTEXT:"),
                  filing().replace(b"CENTRAL INDEX KEY:", b"CENTRAL INDEX KEYS:"))
        for index, raw in enumerate(bodies):
            with self.subTest(index=index):
                self.transport.return_value = Response(raw)
                self.fail(R.UNSUPPORTED_FILING_ENVELOPE)

    def test_duplicate_fields_or_documents_rejected(self):
        raw = filing()
        for line in (b"ACCESSION NUMBER:\t\t" + ACCESSION.encode(),
                     b"CONFORMED SUBMISSION TYPE:\t10-K", b"PUBLIC DOCUMENT COUNT:\t\t1"):
            self.transport.return_value = Response(raw.replace(line, line + b"\n" + line))
            self.fail(R.UNSUPPORTED_FILING_ENVELOPE)
        for extra in (document("10-K", "2", "other.htm"), document("EX-99.1", "1", "other.htm"),
                      document("EX-99.1", "2", "fictional.htm")):
            self.transport.return_value = Response(filing(extra=extra))
            self.fail(R.UNSUPPORTED_FILING_ENVELOPE)

    def test_header_size_bounded(self):
        with patch.object(a, "_MAX_HEADER_BYTES", 32):
            self.fail(R.UNSUPPORTED_FILING_ENVELOPE)

    def test_unknown_or_indented_top_level_context_is_unsupported(self):
        for inserted in (b"SUBJECT COMPANY: OTHER ISSUER\n", b"UNKNOWN: value\n",
                         b"\tACCESSION NUMBER:\t" + ACCESSION.encode() + b"\n"):
            self.transport.return_value = Response(filing().replace(b"FILER:\n", inserted + b"FILER:\n"))
            self.fail(R.UNSUPPORTED_FILING_ENVELOPE)

    def test_company_cik_cannot_be_borrowed_from_other_section(self):
        raw = filing().replace(b"\t\tCENTRAL INDEX KEY:\t" + CIK.encode() + b"\n", b"")
        raw = raw.replace(b"\tBUSINESS ADDRESS:\n", b"\tBUSINESS ADDRESS:\n\t\tCENTRAL INDEX KEY:\t" + CIK.encode() + b"\n")
        self.transport.return_value = Response(raw)
        self.fail(R.UNSUPPORTED_FILING_ENVELOPE)

    def test_document_count_and_delimiter_flood_fail_closed(self):
        raw = filing().replace(b"PUBLIC DOCUMENT COUNT:\t\t1", b"PUBLIC DOCUMENT COUNT:\t\t1001")
        for body in (raw, filing(payload=b"<DOCUMENT>\n" * 10000)):
            self.transport.return_value = Response(body)
            self.fail(R.UNSUPPORTED_FILING_ENVELOPE)

    def test_filing_evidence_cannot_enter_companyfacts_authority_route(self):
        from economic_facts.sec_archive import ArchiveError, SecArchive
        from economic_facts.sec_current_evidence import assess_sec_current_evidence
        from economic_facts.current_authority import CurrentAuthorityError
        result = self.acquire()
        with self.assertRaises(ArchiveError):
            SecArchive(self.root).read_receipt(result.receipt.receipt_id)
        with self.assertRaises(CurrentAuthorityError):
            assess_sec_current_evidence(SecFilingArchive(self.root), result)
        self.assertEqual(set(asdict(result)), {"receipt", "envelope", "request_started_at", "response_completed_at"})


class FilingDependencyTests(unittest.TestCase):
    def test_no_qualification_model_or_reverse_dependencies(self):
        root = Path(__file__).resolve().parents[1]
        allowed_relative = {"sec_acquisition", "sec_filing_archive"}
        for name in ("sec_filing_acquisition.py", "sec_filing_archive.py"):
            tree = ast.parse((root / "economic_facts" / name).read_text())
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom) and node.level:
                    self.assertTrue(node.module in allowed_relative or
                                    (node.module is None and {n.name for n in node.names} == {"sec_acquisition"}))
                if isinstance(node, (ast.Import, ast.ImportFrom)):
                    names = [n.name for n in node.names] + ([node.module or ""] if isinstance(node, ast.ImportFrom) else [])
                    for forbidden in ("src", "pit_comparison", "security_identity", "share_basis", "reporting_subject",
                                      "current_authority", "source_authority", "sec_current_evidence", "decimal"):
                        self.assertFalse(any(n == forbidden or n.startswith(forbidden + ".") for n in names))
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                    self.assertNotIn(node.func.id, {"float", "eval", "exec", "__import__"})
        files = [root / "main.py", *(root / "src").rglob("*.py"), *(root / "pit_comparison").rglob("*.py"),
                 *(root / "economic_facts").rglob("*.py"), *(root / "scripts").rglob("*.py")]
        for file in files:
            if file.name in {"sec_filing_acquisition.py", "sec_filing_archive.py"}:
                continue
            for node in ast.walk(ast.parse(file.read_text())):
                if isinstance(node, (ast.Import, ast.ImportFrom)):
                    names = [n.name for n in node.names] + ([node.module or ""] if isinstance(node, ast.ImportFrom) else [])
                    # D3A/D3B and their shared primary reader may read the archive,
                    # but none may depend on acquisition.
                    self.assertFalse(any("sec_filing_acquisition" in n for n in names), str(file))
                    if file.name not in {"sec_registered_securities.py", "sec_class_eps_claims.py",
                                         "sec_primary_document.py", "sec_filing_document_inventory.py",
                                         "sec_direct_section12_description_source.py",
                                         "sec_section12_rights_source_claims.py",
                                         "sec_reporting_subject_source_claims.py",
                                         "sec_share_basis_source_claims.py",
                                         "sec_property4_temporal_dossier.py",
                                         "sec_property4_temporal_boundary.py",
                                         "sec_current_registered_listing_bridge.py",
                                         "sec_current_common_stock_class_bridge.py",
                                         "sec_temporal_common_stock_source_series.py",
                                         "sec_current_security_eps_qualification.py"}:
                        self.assertFalse(any("sec_filing_archive" in n for n in names), str(file))

    def test_result_contains_only_capture_and_selector_metadata(self):
        self.assertEqual(set(a.SecFilingAcquisitionResult.__dataclass_fields__),
                         {"receipt", "envelope", "request_started_at", "response_completed_at"})
        self.assertEqual(set(a.FilingEnvelope.__dataclass_fields__), {"cik", "accession", "form", "document_count"})
