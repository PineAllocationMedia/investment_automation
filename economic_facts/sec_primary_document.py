"""Internal D2A complete-submission primary-document replay.

This verifies source-envelope linkage and returns an exact primary-document byte
slice.  It grants no XBRL, economic-identity, completeness, or admission authority.
"""
from dataclasses import asdict, dataclass
import re

from .sec_filing_archive import FilingReceipt, canonical_json, digest

_MAX_HEADER_BYTES = 256 * 1024
_MAX_DOCUMENTS = 1_000


class UnsupportedPrimaryDocumentSource(ValueError):
    """Unsupported or ambiguous D2A filing envelope."""


def _require(condition, message):
    if not condition:
        raise UnsupportedPrimaryDocumentSource(message)


def _identity(domain, value):
    # Preserve PR4D3A's published primary-document identity exactly.
    return digest(("pam:sec-registered-securities:" + domain + ":v1\0").encode("ascii")
                  + canonical_json(value))


@dataclass(frozen=True, slots=True)
class PrimaryDocumentProvenance:
    receipt_id: str
    cik: str
    accession: str
    form: str
    endpoint: str
    document_ordinal: int
    sequence: str
    filename: str
    byte_start: int
    byte_length: int
    content_sha256: str

    @property
    def evidence_id(self):
        return _identity("primary-document", asdict(self))


def _single_field(lines, prefix, pattern):
    values = [line[len(prefix):].strip() for line in lines if line.startswith(prefix)]
    _require(len(values) == 1 and re.fullmatch(pattern, values[0]),
             "Unsupported filing envelope field")
    return values[0]


def read_primary_document(raw, receipt, *, supported_forms):
    """Return verified primary provenance and its exact bytes for one D2A receipt.

    The grammar intentionally mirrors D2A's narrow modern complete-submission
    envelope.  Ignored exhibits remain opaque but all boundaries, selectors,
    parties, counts, and primary-form uniqueness are checked.
    """
    _require(type(raw) is bytes and type(receipt) is FilingReceipt,
             "Exact filing bytes and receipt required")
    _require(type(supported_forms) is frozenset and supported_forms
             and all(type(form) is str for form in supported_forms),
             "Exact supported form set required")
    end = raw.find(b"</SEC-HEADER>", 0, _MAX_HEADER_BYTES)
    _require(end >= 0, "Unsupported filing header")
    try:
        header = raw[:end].decode("ascii").replace("\r\n", "\n")
    except UnicodeError:
        raise UnsupportedPrimaryDocumentSource("Unsupported filing header encoding") from None
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
    index = lines.index("FILER:")
    _require(all(not line or not line[0].isspace() for line in lines[2:index])
             and all(not line or line.startswith("\t") for line in lines[index + 1:]),
             "Unsupported filer block")
    filer_lines = [line for line in lines[index + 1:] if line]
    section_indices = [i for i, line in enumerate(filer_lines) if not line.startswith("\t\t")]
    filer = [line.strip() for line in filer_lines]
    _require(all(filer[i] in {"COMPANY DATA:", "FILING VALUES:", "BUSINESS ADDRESS:",
                             "MAIL ADDRESS:", "FORMER COMPANY:"} for i in section_indices),
             "Unsupported filer section")
    _require(filer.count("COMPANY DATA:") == filer.count("FILING VALUES:") == 1,
             "Ambiguous filer sections")
    cik = _single_field(filer, "CENTRAL INDEX KEY:", r"[0-9]{10}")
    company_start = filer.index("COMPANY DATA:")
    company_end = next((i for i in section_indices if i > company_start), len(filer))
    _require(_single_field(filer[company_start + 1:company_end], "CENTRAL INDEX KEY:",
                           r"[0-9]{10}") == cik,
             "CIK outside company data")
    _require(cik == receipt.cik, "Filing CIK mismatch")
    _require(_single_field(top, "ACCESSION NUMBER:",
                           r"[0-9]{10}-[0-9]{2}-[0-9]{6}") == receipt.accession,
             "Filing accession mismatch")
    form = _single_field(top, "CONFORMED SUBMISSION TYPE:", r"[A-Z0-9/-]+")
    _require(form in supported_forms
             and _single_field(filer, "FORM TYPE:", r"[A-Z0-9/-]+") == form,
             "Unsupported semantic extraction form")
    filing_start = filer.index("FILING VALUES:")
    filing_end = next((i for i in section_indices if i > filing_start), len(filer))
    _require(_single_field(filer[filing_start + 1:filing_end], "FORM TYPE:",
                           r"[A-Z0-9/-]+") == form,
             "Form outside filing values")
    count = int(_single_field(top, "PUBLIC DOCUMENT COUNT:", r"[0-9]{1,4}"))
    _require(1 <= count <= _MAX_DOCUMENTS, "Unsupported document count")
    tail_start = end + len(b"</SEC-HEADER>")
    markers = []
    for marker in re.finditer(rb"(?m)^</?(?:DOCUMENT|TEXT|SEC-DOCUMENT)>\r?$",
                              raw[tail_start:]):
        markers.append(marker)
        _require(len(markers) <= 4 * count + 1, "Excess document delimiters")
    _require(len(markers) == 4 * count + 1, "Unbalanced document envelope")
    _require(markers[-1][0].rstrip(b"\r") == b"</SEC-DOCUMENT>"
             and not raw[tail_start + markers[-1].end():].strip(),
             "Invalid filing terminator")
    cursor, sequences, filenames, types, primary = tail_start, set(), set(), [], None
    for ordinal in range(count):
        a, b, c, d = markers[ordinal * 4:ordinal * 4 + 4]
        _require([m[0].rstrip(b"\r") for m in (a, b, c, d)] ==
                 [b"<DOCUMENT>", b"<TEXT>", b"</TEXT>", b"</DOCUMENT>"],
                 "Invalid document delimiters")
        _require(not raw[cursor:tail_start + a.start()].strip(),
                 "Unexpected envelope content")
        try:
            fields = raw[tail_start + a.end():tail_start + b.start()].decode(
                "ascii").strip("\r\n").splitlines()
        except UnicodeError:
            raise UnsupportedPrimaryDocumentSource("Unsupported document metadata") from None
        _require(len(fields) in (3, 4) and all(fields[i].startswith(tag) for i, tag in
                 enumerate(("<TYPE>", "<SEQUENCE>", "<FILENAME>")))
                 and (len(fields) == 3 or fields[3].startswith("<DESCRIPTION>")),
                 "Unsupported document metadata")
        kind = _single_field(fields, "<TYPE>", r"[A-Za-z0-9._/-]+")
        sequence = _single_field(fields, "<SEQUENCE>", r"[1-9][0-9]{0,5}")
        filename = _single_field(fields, "<FILENAME>", r"[A-Za-z0-9][A-Za-z0-9_.-]*")
        _require(sequence not in sequences and filename not in filenames,
                 "Duplicate document identity")
        sequences.add(sequence)
        filenames.add(filename)
        types.append(kind)
        start = tail_start + b.end() + 1
        stop = tail_start + c.start()
        _require(raw[start - 1:start] == b"\n", "Missing TEXT newline")
        stop -= 2 if raw[stop - 2:stop] == b"\r\n" else 1
        payload = raw[start:stop]
        _require(bool(payload.strip()), "Empty primary or exhibit document")
        _require(re.search(rb"(?m)^</?(?:SEC-DOCUMENT|SEC-HEADER|DOCUMENT|TEXT)>[^\n]*$",
                           payload) is None,
                 "Reserved delimiter inside document")
        _require(not raw[tail_start + c.end():tail_start + d.start()].strip(),
                 "Unexpected TEXT suffix")
        if ordinal == 0:
            provenance = PrimaryDocumentProvenance(
                receipt.receipt_id, cik, receipt.accession, form, receipt.endpoint,
                ordinal, sequence, filename, start, len(payload), digest(payload))
            primary = (provenance, payload)
        cursor = tail_start + d.end()
    _require(not raw[cursor:tail_start + markers[-1].start()].strip()
             and types[0] == form and types.count(form) == 1,
             "Ambiguous primary document")
    return primary
