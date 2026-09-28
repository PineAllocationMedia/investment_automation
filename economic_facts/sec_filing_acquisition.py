"""One controlled complete-submission capture; no qualification or admission.

The one-way C2 dependency deliberately shares its single per-user/process rate
gate, declared User-Agent, verified TLS, redirect rejection and proxy policy.
Only this route's MIME/body and filing-envelope preflight are different.
"""
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
import http.client
from pathlib import Path
import re
import time
import urllib.error
import urllib.request

from . import sec_acquisition as _sec
from .sec_filing_archive import (FilingArchiveError, FilingReceipt, MAX_FILING_BYTES,
                                 SecFilingArchive, endpoint_for)

SUPPORTED_FORMS = frozenset(("10-K", "10-K/A", "10-Q", "10-Q/A", "8-K", "8-K/A"))
_MAX_HEADER_BYTES = 256 * 1024
_MAX_DOCUMENTS = 1000
_CHUNK_BYTES = 64 * 1024


class FilingAcquisitionReason(StrEnum):
    CONFIGURATION_ERROR = "CONFIGURATION_ERROR"
    RATE_LIMITED = "RATE_LIMITED"
    HTTP_ERROR = "HTTP_ERROR"
    REDIRECT_REJECTED = "REDIRECT_REJECTED"
    TIMEOUT = "TIMEOUT"
    NETWORK_ERROR = "NETWORK_ERROR"
    RESPONSE_TOO_LARGE = "RESPONSE_TOO_LARGE"
    INVALID_CONTENT_TYPE = "INVALID_CONTENT_TYPE"
    INVALID_RESPONSE = "INVALID_RESPONSE"
    UNSUPPORTED_FILING_ENVELOPE = "UNSUPPORTED_FILING_ENVELOPE"
    FILING_SELECTOR_MISMATCH = "FILING_SELECTOR_MISMATCH"
    ARCHIVE_INTEGRITY_ERROR = "ARCHIVE_INTEGRITY_ERROR"


class SecFilingAcquisitionError(ValueError):
    """Closed category/status only; no source body, local path or contact."""

    def __init__(self, reason: FilingAcquisitionReason, *, status: int | None = None):
        self.reason = reason
        self.status = status
        super().__init__(reason.value + (f" (HTTP {status})" if status is not None else ""))


@dataclass(frozen=True, slots=True)
class FilingEnvelope:
    """Selector verification metadata only, never issuer/security authority."""
    cik: str
    accession: str
    form: str
    document_count: int


@dataclass(frozen=True, slots=True)
class SecFilingAcquisitionResult:
    receipt: FilingReceipt
    envelope: FilingEnvelope
    request_started_at: str
    response_completed_at: str


def _require(condition, reason=FilingAcquisitionReason.UNSUPPORTED_FILING_ENVELOPE):
    if not condition:
        raise SecFilingAcquisitionError(reason)


def _read_body(response, deadline):
    media_type = _sec._single_header(response.headers, "Content-Type") or ""
    _require(re.fullmatch(
        r'text/plain(?:\s*;\s*charset\s*=\s*(?:utf-8|us-ascii|"utf-8"|"us-ascii"))?\s*',
        media_type, re.IGNORECASE), FilingAcquisitionReason.INVALID_CONTENT_TYPE)
    encoding = _sec._single_header(response.headers, "Content-Encoding")
    _require(encoding is None or encoding.strip().lower() == "identity",
             FilingAcquisitionReason.INVALID_RESPONSE)
    length = _sec._single_header(response.headers, "Content-Length")
    declared = None
    if length is not None:
        _require(re.fullmatch(r"[0-9]{1,20}", length.strip()), FilingAcquisitionReason.INVALID_RESPONSE)
        declared = int(length)
        _require(declared <= MAX_FILING_BYTES, FilingAcquisitionReason.RESPONSE_TOO_LARGE)
    transfer = _sec._single_header(response.headers, "Transfer-Encoding")
    _require(transfer is None or (transfer.lower().strip() == "chunked" and declared is None),
             FilingAcquisitionReason.INVALID_RESPONSE)
    body = bytearray()
    while True:
        _require(time.monotonic() < deadline, FilingAcquisitionReason.TIMEOUT)
        chunk = response.read1(min(_CHUNK_BYTES, MAX_FILING_BYTES + 1 - len(body)))
        _require(time.monotonic() < deadline, FilingAcquisitionReason.TIMEOUT)
        if not chunk:
            break
        body.extend(chunk)
        _require(len(body) <= MAX_FILING_BYTES, FilingAcquisitionReason.RESPONSE_TOO_LARGE)
    _require(declared is None or len(body) == declared, FilingAcquisitionReason.INVALID_RESPONSE)
    return bytes(body)


def _field(lines, name, pattern):
    matches = [line[len(name):].strip() for line in lines if line.startswith(name)]
    _require(len(matches) == 1 and re.fullmatch(pattern, matches[0]) is not None)
    return matches[0]


def _preflight(raw, cik, accession):
    """Recognize one narrow modern envelope; embedded documents stay opaque.

    Normalization below is only for parsing. The archive receives original bytes.
    No HTML/XBRL interpretation, external references, dates-as-authority or class
    inference. Nonstandard/ambiguous envelopes fail closed, even if SEC-valid.
    """
    _require(type(raw) is bytes and bool(raw))
    # Cap the header scan and decode only the ASCII envelope, not document bytes.
    header_end = raw.find(b"</SEC-HEADER>", 0, _MAX_HEADER_BYTES)
    _require(header_end >= 0)
    try:
        header = raw[:header_end].decode("ascii").replace("\r\n", "\n")
    except UnicodeError:
        raise SecFilingAcquisitionError(FilingAcquisitionReason.UNSUPPORTED_FILING_ENVELOPE) from None
    lines = [line.rstrip(" \t") for line in header.split("\n")]
    _require(len(lines) > 3 and all(c in "\n\t" or 32 <= ord(c) <= 126 for c in header))
    for line, tag, suffix in ((lines[0], "SEC-DOCUMENT", r"txt"), (lines[1], "SEC-HEADER", r"hdr\.sgml")):
        match = re.fullmatch(r"<" + tag + r">([0-9]{10}-[0-9]{2}-[0-9]{6})\."
                             + suffix + r" : [0-9]{8}", line)
        _require(match is not None)
        _require(match[1] == accession, FilingAcquisitionReason.FILING_SELECTOR_MISMATCH)
    # The reviewed plain-text header has exactly one top-level FILER block.
    # Reject additional roles/contexts, including unfamiliar top-level blocks.
    top = [line for line in lines[2:] if line and not line[0].isspace()]
    top_patterns = (
        r"<ACCEPTANCE-DATETIME>[0-9]{14}", r"FILER:",
        r"ACCESSION NUMBER:[ \t]+[0-9]{10}-[0-9]{2}-[0-9]{6}",
        r"CONFORMED SUBMISSION TYPE:[ \t]+[A-Z0-9/-]+",
        r"PUBLIC DOCUMENT COUNT:[ \t]+[0-9]{1,4}",
        r"(?:CONFORMED PERIOD OF REPORT|FILED AS OF DATE|DATE AS OF CHANGE|EFFECTIVENESS DATE):[ \t]+[0-9]{8}",
        r"ITEM INFORMATION:[ \t]+[^<>]+",
    )
    _require(all(any(re.fullmatch(pattern, line) for pattern in top_patterns) for line in top))
    _require([line for line in top if line.endswith(":")] == ["FILER:"])
    _require(sum(line.strip() == "FILER:" for line in lines) == 1)
    filer_index = lines.index("FILER:")
    _require(all(not line or not line[0].isspace() for line in lines[2:filer_index]))
    _require(all(not line or line[0].isspace() for line in lines[filer_index + 1:]))
    _require(not any("<" in line or ">" in line for line in lines[2:]
                     if not line.startswith("<ACCEPTANCE-DATETIME>")))
    acceptance = [line for line in lines if line.startswith("<ACCEPTANCE-DATETIME>")]
    _require(len(acceptance) == 1 and
             re.fullmatch(r"<ACCEPTANCE-DATETIME>[0-9]{14}", acceptance[0]) is not None)
    selected = _field(top, "ACCESSION NUMBER:", r"[0-9]{10}-[0-9]{2}-[0-9]{6}")
    _require(selected == accession, FilingAcquisitionReason.FILING_SELECTOR_MISMATCH)
    form = _field(top, "CONFORMED SUBMISSION TYPE:", r"[A-Z0-9/-]+")
    _require(form in SUPPORTED_FORMS)
    count = int(_field(top, "PUBLIC DOCUMENT COUNT:", r"[0-9]{1,4}"))
    _require(1 <= count <= _MAX_DOCUMENTS)
    filer_lines = [line for line in lines[filer_index + 1:] if line]
    # Modern SEC section headings have one tab; field lines have two. Empty
    # optional fields (e.g. ORGANIZATION NAME) are not new filing contexts.
    _require(all(line.startswith("\t") for line in filer_lines))
    section_indices = [i for i, line in enumerate(filer_lines) if not line.startswith("\t\t")]
    filer = [line.strip() for line in filer_lines]
    sections = [filer[i] for i in section_indices]
    _require(sections.count("COMPANY DATA:") == sections.count("FILING VALUES:") == 1)
    _require(all(section in {"COMPANY DATA:", "FILING VALUES:", "BUSINESS ADDRESS:",
                             "MAIL ADDRESS:", "FORMER COMPANY:"} for section in sections))
    company_start = filer.index("COMPANY DATA:")
    company_end = next((i for i in section_indices if i > company_start), len(filer))
    source_cik = _field(filer[company_start + 1:company_end], "CENTRAL INDEX KEY:", r"[0-9]{10}")
    _require(_field(filer, "CENTRAL INDEX KEY:", r"[0-9]{10}") == source_cik)
    _require(source_cik == cik, FilingAcquisitionReason.FILING_SELECTOR_MISMATCH)
    filing_start = filer.index("FILING VALUES:")
    filing_end = next((i for i in section_indices if i > filing_start), len(filer))
    _require(_field(filer[filing_start + 1:filing_end], "FORM TYPE:", r"[A-Z0-9/-]+") == form)
    _require(_field(filer, "FORM TYPE:", r"[A-Z0-9/-]+") == form)

    # Require balanced, line-delimited document/text envelopes and exact count.
    # A delimiter-looking line inside a document is conservatively unsupported.
    tail = raw[header_end + len(b"</SEC-HEADER>"):].replace(b"\r\n", b"\n")
    _require(tail.startswith(b"\n") and tail.rstrip(b"\n").endswith(b"</SEC-DOCUMENT>"))
    tail = tail.rstrip(b"\n")[:-len(b"</SEC-DOCUMENT>")]
    cursor, documents, sequences, filenames = 0, [], set(), set()
    markers = []
    for marker in re.finditer(rb"(?m)^</?DOCUMENT>(?:\n|$)", tail):
        markers.append(marker)
        _require(len(markers) <= 2 * count)
    _require(len(markers) == 2 * count)
    for start, end in zip(markers[::2], markers[1::2]):
        _require(start[0] == b"<DOCUMENT>\n" and end[0].startswith(b"</DOCUMENT>"))
        _require(not tail[cursor:start.start()].strip())
        document = tail[start.end():end.start()]
        parts = document.split(b"\n<TEXT>\n")
        _require(len(parts) == 2 and parts[1].endswith(b"\n</TEXT>\n"))
        payload = parts[1][:-len(b"\n</TEXT>\n")]
        _require(bool(payload.strip()) and re.search(
            rb"(?m)^</?(?:SEC-DOCUMENT|SEC-HEADER|DOCUMENT|TEXT)>(?:[^\n]*)$", payload) is None)
        try:
            fields = parts[0].decode("ascii").split("\n")
        except UnicodeError:
            raise SecFilingAcquisitionError(FilingAcquisitionReason.UNSUPPORTED_FILING_ENVELOPE) from None
        _require(len(fields) in (3, 4))
        _require(all(fields[i].startswith(tag) for i, tag in
                     enumerate(("<TYPE>", "<SEQUENCE>", "<FILENAME>"))))
        _require(len(fields) == 3 or fields[3].startswith("<DESCRIPTION>"))
        document_type = _field(fields, "<TYPE>", r"[A-Za-z0-9._/-]+")
        sequence = _field(fields, "<SEQUENCE>", r"[1-9][0-9]{0,5}")
        filename = _field(fields, "<FILENAME>", r"[A-Za-z0-9][A-Za-z0-9_.-]*")
        _require(sequence not in sequences and filename not in filenames)
        sequences.add(sequence)
        filenames.add(filename)
        documents.append(document_type)
        _require(len(documents) <= count)
        cursor = end.end()
    _require(not tail[cursor:].strip() and len(documents) == count)
    _require(documents[0] == form and documents.count(form) == 1)
    return FilingEnvelope(cik, accession, form, count)


def _acquire(*, cik, accession, archive_root):
    try:
        endpoint = endpoint_for(cik, accession)
        archive = SecFilingArchive(archive_root)
        _require("\x00" not in str(archive.root), FilingAcquisitionReason.CONFIGURATION_ERROR)
    except (FilingArchiveError, TypeError, ValueError):
        raise SecFilingAcquisitionError(FilingAcquisitionReason.CONFIGURATION_ERROR) from None
    user_agent = _sec._user_agent()
    request = urllib.request.Request(endpoint, method="GET", headers={
        "User-Agent": user_agent, "Accept": "text/plain", "Accept-Encoding": "identity",
    })
    with _sec._rate_gate():
        started = _sec._timestamp()
        deadline = time.monotonic() + _sec.RESPONSE_DEADLINE_SECONDS
        try:
            with _sec._open_response(request) as response:
                _sec._check_status(response.status)
                _require(response.geturl() == endpoint, FilingAcquisitionReason.REDIRECT_REJECTED)
                raw = _read_body(response, deadline)
                completed = _sec._timestamp()
        except urllib.error.HTTPError as exc:
            status = exc.code
            exc.close()
            _sec._check_status(status)
            raise SecFilingAcquisitionError(FilingAcquisitionReason.HTTP_ERROR, status=status) from None
        except TimeoutError:
            raise SecFilingAcquisitionError(FilingAcquisitionReason.TIMEOUT) from None
        except urllib.error.URLError as exc:
            reason = (FilingAcquisitionReason.TIMEOUT if isinstance(exc.reason, TimeoutError)
                      else FilingAcquisitionReason.NETWORK_ERROR)
            raise SecFilingAcquisitionError(reason) from None
        except (OSError, http.client.HTTPException):
            raise SecFilingAcquisitionError(FilingAcquisitionReason.NETWORK_ERROR) from None
        envelope = _preflight(raw, cik, accession)
        captured = _sec._timestamp()
        times = [datetime.fromisoformat(value.replace("Z", "+00:00"))
                 for value in (started, completed, captured)]
        _require(times == sorted(times), FilingAcquisitionReason.CONFIGURATION_ERROR)
        try:
            receipt = archive._capture_live(raw, cik=cik, accession=accession, captured_at=captured)
        except (FilingArchiveError, OSError):
            raise SecFilingAcquisitionError(FilingAcquisitionReason.ARCHIVE_INTEGRITY_ERROR) from None
        return SecFilingAcquisitionResult(receipt, envelope, started, completed)


def acquire_sec_filing(*, cik: str, accession: str,
                       archive_root: str | Path) -> SecFilingAcquisitionResult:
    """One canonical request. No public bytes, time, transport or authority input."""
    try:
        return _acquire(cik=cik, accession=accession, archive_root=archive_root)
    except _sec.SecAcquisitionError as exc:
        # Translate only C2's closed safe categories; unexpected errors propagate.
        raise SecFilingAcquisitionError(FilingAcquisitionReason(exc.reason.value), status=exc.status) from None
