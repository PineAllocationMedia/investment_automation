"""Exact offline inventory of documents embedded in one D2A filing capture.

This module verifies one explicitly selected complete-submission receipt and
cryptographically binds each physically embedded DOCUMENT payload.  TYPE and
DESCRIPTION are opaque source metadata.  No document is classified, followed,
executed, or interpreted as legal, security, class, listing, or admission
evidence.
"""
from dataclasses import asdict, dataclass
from enum import StrEnum
import re

from .sec_filing_archive import (
    FilingReceipt,
    SecFilingArchive,
    canonical_json,
    digest,
)

INVENTORY_CONTRACT_VERSION = "2026-09-26-sec-filing-document-inventory-v1"
SUPPORTED_FORMS = frozenset(("10-K", "10-K/A", "10-Q", "10-Q/A", "8-K", "8-K/A"))
_MAX_HEADER_BYTES = 256 * 1024
_MAX_DOCUMENTS = 1_000
_MAX_DESCRIPTION_BYTES = 4_096
_RECEIPT_ID = re.compile(r"[0-9a-f]{64}")


class SecFilingDocumentInventoryRequestError(ValueError):
    """Invalid explicit receipt selection or untyped replay arguments."""


class UnsupportedSecFilingDocumentInventorySource(ValueError):
    """Unsupported or ambiguous D2A complete-submission envelope."""


class SecFilingDocumentInventoryStatus(StrEnum):
    CAPTURED_FILING_DOCUMENT_INVENTORY = "CAPTURED_FILING_DOCUMENT_INVENTORY"


def _require(condition, message):
    if not condition:
        raise UnsupportedSecFilingDocumentInventorySource(message)


def _identity(domain, value):
    return digest(("pam:sec-filing-document-inventory:" + domain + ":v1\0").encode("ascii")
                  + canonical_json(value))


@dataclass(frozen=True, slots=True)
class SecFilingDocumentInventoryRequest:
    filing_receipt_id: str

    def __post_init__(self):
        if (type(self.filing_receipt_id) is not str
                or _RECEIPT_ID.fullmatch(self.filing_receipt_id) is None):
            raise SecFilingDocumentInventoryRequestError("Exact filing receipt ID required")


@dataclass(frozen=True, slots=True)
class SecFilingDocumentProvenance:
    filing_receipt_id: str
    cik: str
    accession: str
    filing_form: str
    document_ordinal: int
    document_type: str
    sequence: str
    filename: str
    description: str | None
    byte_start: int
    byte_length: int
    content_sha256: str

    @property
    def semantic_id(self):
        return _identity("document-semantics", {
            "cik": self.cik,
            "accession": self.accession,
            "filing_form": self.filing_form,
            "document_ordinal": self.document_ordinal,
            "document_type": self.document_type,
            "sequence": self.sequence,
            "filename": self.filename,
            "description": self.description,
            "content_sha256": self.content_sha256,
        })

    @property
    def evidence_id(self):
        return _identity("document-evidence", {
            "semantic_id": self.semantic_id,
            "receipt_id": self.filing_receipt_id,
            "byte_start": self.byte_start,
            "byte_length": self.byte_length,
            "content_sha256": self.content_sha256,
        })


@dataclass(frozen=True, slots=True)
class SecFilingDocumentInventoryAssessment:
    contract_version: str
    receipt: FilingReceipt
    cik: str
    accession: str
    form: str
    documents: tuple[SecFilingDocumentProvenance, ...]
    status: SecFilingDocumentInventoryStatus

    @property
    def semantic_id(self):
        return _identity("inventory-semantics", {
            "contract": self.contract_version,
            "cik": self.cik,
            "accession": self.accession,
            "form": self.form,
            "documents": [document.semantic_id for document in self.documents],
        })

    @property
    def evidence_id(self):
        return _identity("inventory-evidence", {
            "semantic_id": self.semantic_id,
            "receipt": asdict(self.receipt),
            "receipt_id": self.receipt.receipt_id,
            "documents": [document.evidence_id for document in self.documents],
        })


def _single_field(lines, prefix, pattern):
    values = [line[len(prefix):].strip() for line in lines if line.startswith(prefix)]
    _require(len(values) == 1 and re.fullmatch(pattern, values[0]),
             "Unsupported filing envelope field")
    return values[0]


def _exact_metadata_field(lines, prefix, pattern):
    values = [line[len(prefix):] for line in lines if line.startswith(prefix)]
    _require(len(values) == 1 and re.fullmatch(pattern, values[0]),
             "Unsupported exact document metadata")
    return values[0]


def _parse_inventory(raw, receipt):
    """Mirror D2A's reviewed envelope without interpreting document payloads."""
    _require(type(raw) is bytes and type(receipt) is FilingReceipt,
             "Exact filing bytes and receipt required")
    header_end = raw.find(b"</SEC-HEADER>", 0, _MAX_HEADER_BYTES)
    _require(header_end >= 0, "Unsupported filing header")
    try:
        header = raw[:header_end].decode("ascii").replace("\r\n", "\n")
    except UnicodeError:
        raise UnsupportedSecFilingDocumentInventorySource(
            "Unsupported filing header encoding") from None
    lines = [line.rstrip(" \t") for line in header.split("\n")]
    _require(len(lines) > 3 and all(c in "\n\t" or 32 <= ord(c) <= 126 for c in header),
             "Incomplete or unsupported filing header")
    for line, tag, suffix in ((lines[0], "SEC-DOCUMENT", "txt"),
                              (lines[1], "SEC-HEADER", r"hdr\.sgml")):
        _require(re.fullmatch("<" + tag + ">" + re.escape(receipt.accession) + r"\."
                              + suffix + r" : [0-9]{8}", line),
                 "Filing accession mismatch")
    top = [line for line in lines[2:] if line and not line[0].isspace()]
    top_patterns = (
        r"<ACCEPTANCE-DATETIME>[0-9]{14}", r"FILER:",
        r"ACCESSION NUMBER:[ \t]+[0-9]{10}-[0-9]{2}-[0-9]{6}",
        r"CONFORMED SUBMISSION TYPE:[ \t]+[A-Z0-9/-]+",
        r"PUBLIC DOCUMENT COUNT:[ \t]+[0-9]{1,4}",
        r"(?:CONFORMED PERIOD OF REPORT|FILED AS OF DATE|DATE AS OF CHANGE|EFFECTIVENESS DATE):[ \t]+[0-9]{8}",
        r"ITEM INFORMATION:[ \t]+[^<>]+",
    )
    _require(all(any(re.fullmatch(pattern, line) for pattern in top_patterns) for line in top),
             "Unsupported filing header context")
    _require(sum(line.startswith("<ACCEPTANCE-DATETIME>") for line in lines) == 1,
             "Ambiguous acceptance metadata")
    _require(not any("<" in line or ">" in line for line in lines[2:]
                     if not line.startswith("<ACCEPTANCE-DATETIME>")),
             "Unexpected header markup")
    _require([line for line in top if line.endswith(":")] == ["FILER:"],
             "Unsupported filing parties")
    filer_index = lines.index("FILER:")
    _require(all(not line or not line[0].isspace() for line in lines[2:filer_index])
             and all(not line or line.startswith("\t") for line in lines[filer_index + 1:]),
             "Unsupported filer block")
    filer_lines = [line for line in lines[filer_index + 1:] if line]
    section_indices = [index for index, line in enumerate(filer_lines)
                       if not line.startswith("\t\t")]
    filer = [line.strip() for line in filer_lines]
    _require(all(filer[index] in {"COMPANY DATA:", "FILING VALUES:",
                                  "BUSINESS ADDRESS:", "MAIL ADDRESS:",
                                  "FORMER COMPANY:"}
                 for index in section_indices), "Unsupported filer section")
    _require(filer.count("COMPANY DATA:") == filer.count("FILING VALUES:") == 1,
             "Ambiguous filer sections")
    cik = _single_field(filer, "CENTRAL INDEX KEY:", r"[0-9]{10}")
    company_start = filer.index("COMPANY DATA:")
    company_end = next((index for index in section_indices if index > company_start),
                       len(filer))
    _require(_single_field(filer[company_start + 1:company_end],
                           "CENTRAL INDEX KEY:", r"[0-9]{10}") == cik,
             "CIK outside company data")
    _require(cik == receipt.cik, "Filing CIK mismatch")
    _require(_single_field(top, "ACCESSION NUMBER:",
                           r"[0-9]{10}-[0-9]{2}-[0-9]{6}") == receipt.accession,
             "Filing accession mismatch")
    form = _single_field(top, "CONFORMED SUBMISSION TYPE:", r"[A-Z0-9/-]+")
    _require(form in SUPPORTED_FORMS, "Unsupported filing form")
    filing_start = filer.index("FILING VALUES:")
    filing_end = next((index for index in section_indices if index > filing_start), len(filer))
    _require(_single_field(filer[filing_start + 1:filing_end],
                           "FORM TYPE:", r"[A-Z0-9/-]+") == form
             and _single_field(filer, "FORM TYPE:", r"[A-Z0-9/-]+") == form,
             "Filing form mismatch")
    count = int(_single_field(top, "PUBLIC DOCUMENT COUNT:", r"[0-9]{1,4}"))
    _require(1 <= count <= _MAX_DOCUMENTS, "Unsupported document count")

    tail_start = header_end + len(b"</SEC-HEADER>")
    markers = []
    for marker in re.finditer(rb"(?m)^</?(?:DOCUMENT|TEXT|SEC-DOCUMENT)>\r?$",
                              raw[tail_start:]):
        markers.append(marker)
        _require(len(markers) <= 4 * count + 1, "Excess document delimiters")
    _require(len(markers) == 4 * count + 1, "Unbalanced document envelope")
    _require(markers[-1][0].rstrip(b"\r") == b"</SEC-DOCUMENT>"
             and not raw[tail_start + markers[-1].end():].strip(),
             "Invalid filing terminator")

    cursor, sequences, filenames, types, documents = tail_start, set(), set(), [], []
    for ordinal in range(count):
        document_start, text_start, text_end, document_end = markers[
            ordinal * 4:ordinal * 4 + 4]
        _require([marker[0].rstrip(b"\r") for marker in
                  (document_start, text_start, text_end, document_end)] ==
                 [b"<DOCUMENT>", b"<TEXT>", b"</TEXT>", b"</DOCUMENT>"],
                 "Invalid document delimiters")
        _require(not raw[cursor:tail_start + document_start.start()].strip(),
                 "Unexpected envelope content")
        metadata = raw[tail_start + document_start.end():tail_start + text_start.start()]
        try:
            fields = metadata.decode("ascii").strip("\r\n").splitlines()
        except UnicodeError:
            raise UnsupportedSecFilingDocumentInventorySource(
                "Unsupported document metadata") from None
        _require(len(fields) in (3, 4)
                 and all(fields[index].startswith(tag) for index, tag in
                         enumerate(("<TYPE>", "<SEQUENCE>", "<FILENAME>")))
                 and (len(fields) == 3 or fields[3].startswith("<DESCRIPTION>")),
                 "Unsupported document metadata")
        document_type = _exact_metadata_field(fields, "<TYPE>", r"[A-Za-z0-9._/-]+")
        sequence = _exact_metadata_field(fields, "<SEQUENCE>", r"[1-9][0-9]{0,5}")
        filename = _exact_metadata_field(fields, "<FILENAME>", r"[A-Za-z0-9][A-Za-z0-9_.-]*")
        description = None
        if len(fields) == 4:
            description = fields[3][len("<DESCRIPTION>"):]
            _require(len(description.encode("ascii")) <= _MAX_DESCRIPTION_BYTES
                     and all(character == "\t" or 32 <= ord(character) <= 126
                             for character in description),
                     "Unsupported document description")
        _require(sequence not in sequences and filename not in filenames,
                 "Duplicate document identity")
        sequences.add(sequence)
        filenames.add(filename)
        types.append(document_type)

        byte_start = tail_start + text_start.end() + 1
        byte_stop = tail_start + text_end.start()
        _require(raw[byte_start - 1:byte_start] == b"\n", "Missing TEXT newline")
        byte_stop -= 2 if raw[byte_stop - 2:byte_stop] == b"\r\n" else 1
        payload = raw[byte_start:byte_stop]
        _require(bool(payload.strip()), "Empty document payload")
        _require(re.search(rb"(?m)^</?(?:SEC-DOCUMENT|SEC-HEADER|DOCUMENT|TEXT)>[^\n]*$",
                           payload) is None, "Reserved delimiter inside document")
        _require(not raw[tail_start + text_end.end():tail_start + document_end.start()].strip(),
                 "Unexpected TEXT suffix")
        documents.append(SecFilingDocumentProvenance(
            receipt.receipt_id, cik, receipt.accession, form, ordinal,
            document_type, sequence, filename, description, byte_start,
            len(payload), digest(payload),
        ))
        cursor = tail_start + document_end.end()
    _require(not raw[cursor:tail_start + markers[-1].start()].strip()
             and types[0] == form and types.count(form) == 1,
             "Ambiguous primary document")
    return form, tuple(documents)


def replay_sec_filing_document_inventory(
    archive: SecFilingArchive,
    request: SecFilingDocumentInventoryRequest,
) -> SecFilingDocumentInventoryAssessment:
    """Replay one exact receipt with no network, writes, clocks, or discovery."""
    if (type(archive) is not SecFilingArchive
            or type(request) is not SecFilingDocumentInventoryRequest):
        raise SecFilingDocumentInventoryRequestError("Exact typed archive/request required")
    receipt = archive.read_receipt(request.filing_receipt_id)
    form, documents = _parse_inventory(archive.read_object(receipt), receipt)
    return SecFilingDocumentInventoryAssessment(
        INVENTORY_CONTRACT_VERSION,
        receipt,
        receipt.cik,
        receipt.accession,
        form,
        documents,
        SecFilingDocumentInventoryStatus.CAPTURED_FILING_DOCUMENT_INVENTORY,
    )
