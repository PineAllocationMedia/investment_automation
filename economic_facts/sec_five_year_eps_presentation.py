"""Strict extraction of one controlled SEC five-year diluted-EPS presentation.

The extractor is deliberately narrow.  It accepts only the primary HTML document
of one controlled Form 10-K or 10-K/A capture and a finite table grammar.  It
does not reconcile values, infer missing periods, parse PDFs, or grant economic
comparability authority.
"""
from dataclasses import asdict, dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from enum import StrEnum
from html.parser import HTMLParser
import re

from .sec_filing_archive import SecFilingArchive, canonical_json, digest
from .sec_filing_document_inventory import (
    SecFilingDocumentInventoryRequest,
    replay_sec_filing_document_inventory,
)


CONTRACT_VERSION = "2026-09-28-sec-five-year-eps-presentation-v1"
DOCUMENT_PROFILE_VERSION = "2026-09-28-primary-10k-html-five-year-table-v1"
MEASUREMENT_PROFILE = "US_GAAP_REPORTED_TOTAL_ENTITY_DILUTED_EPS_USD_PER_SHARE"
SUPPORTED_FORMS = frozenset(("10-K", "10-K/A"))
MAX_DOCUMENT_BYTES = 4_000_000
MAX_TABLES = 256
MAX_CELLS = 10_000

_RECEIPT_ID = re.compile(r"[0-9a-f]{64}")
_TABLE = re.compile(r"(?is)<table(?:\s[^>]*)?>.*?</table\s*>")
_YEAR = re.compile(r"(?:19|20)[0-9]{2}")
_CAPTION = re.compile(
    r"^YEARS? ENDED ([A-Z]+) ([0-9]{1,2})[,]?$", re.ASCII)
_NUMBER = re.compile(
    r"^\(?-?[$]?\s*[0-9]+(?:,[0-9]{3})*(?:\.[0-9]+)?\)?$", re.ASCII)
_MONTHS = {
    "JANUARY": 1, "FEBRUARY": 2, "MARCH": 3, "APRIL": 4,
    "MAY": 5, "JUNE": 6, "JULY": 7, "AUGUST": 8,
    "SEPTEMBER": 9, "OCTOBER": 10, "NOVEMBER": 11, "DECEMBER": 12,
}
_SUPPORTED_ROWS = frozenset((
    "DILUTED EARNINGS PER SHARE ATTRIBUTABLE TO COMMON STOCKHOLDERS",
    "DILUTED NET INCOME PER COMMON SHARE",
    "DILUTED EARNINGS PER COMMON SHARE",
))
_PROHIBITED_ROWS = (
    "ADJUSTED", "CORE", "OPERATING", "NORMALIZED", "NON-GAAP",
    "NON GAAP", "STREET", "CONTINUING OPERATIONS", "MANAGEMENT-ADJUSTED",
    "MANAGEMENT ADJUSTED",
)


class SecFiveYearEPSPresentationError(ValueError):
    """Invalid closed request, source representation, or public argument."""


class PresentationStatus(StrEnum):
    CAPTURED_FIVE_YEAR_DILUTED_EPS_PRESENTATION = (
        "CAPTURED_FIVE_YEAR_DILUTED_EPS_PRESENTATION"
    )
    PRESENTATION_UNAVAILABLE = "PRESENTATION_UNAVAILABLE"
    PRESENTATION_UNSUPPORTED = "PRESENTATION_UNSUPPORTED"
    SOURCE_CONFLICT = "SOURCE_CONFLICT"


class PresentationIssue(StrEnum):
    UNSUPPORTED_FILING_FORM = "UNSUPPORTED_FILING_FORM"
    UNSUPPORTED_DOCUMENT_PROFILE = "UNSUPPORTED_DOCUMENT_PROFILE"
    MALFORMED_HTML_TABLE = "MALFORMED_HTML_TABLE"
    NO_SUPPORTED_DILUTED_EPS_PRESENTATION = "NO_SUPPORTED_DILUTED_EPS_PRESENTATION"
    ADJUSTED_OR_NON_GAAP_EPS_ROW = "ADJUSTED_OR_NON_GAAP_EPS_ROW"
    BASIC_EPS_ONLY = "BASIC_EPS_ONLY"
    AMBIGUOUS_DILUTED_EPS_ROW = "AMBIGUOUS_DILUTED_EPS_ROW"
    PERIOD_COUNT_NOT_EXACTLY_FIVE = "PERIOD_COUNT_NOT_EXACTLY_FIVE"
    PERIOD_LABEL_UNSUPPORTED = "PERIOD_LABEL_UNSUPPORTED"
    DUPLICATE_PERIOD_ENDPOINT = "DUPLICATE_PERIOD_ENDPOINT"
    INVALID_EXACT_DECIMAL = "INVALID_EXACT_DECIMAL"
    MULTIPLE_CANDIDATE_PRESENTATIONS = "MULTIPLE_CANDIDATE_PRESENTATIONS"


@dataclass(frozen=True, slots=True)
class SecFiveYearEPSPresentationRequest:
    filing_receipt_id: str

    def __post_init__(self):
        if (type(self.filing_receipt_id) is not str
                or _RECEIPT_ID.fullmatch(self.filing_receipt_id) is None):
            raise SecFiveYearEPSPresentationError("Exact filing receipt ID required")


@dataclass(frozen=True, slots=True)
class PresentedDilutedEPSValue:
    period_label: str
    period_end: str
    exact_source_value: str
    value: Decimal
    column_ordinal: int


@dataclass(frozen=True, slots=True)
class SecFiveYearEPSPresentation:
    contract_version: str
    document_profile_version: str
    measurement_profile: str
    filing_receipt_id: str
    filing_captured_at: str
    source_cik: str
    accession: str
    form: str
    document_ordinal: int
    document_type: str
    document_filename: str
    document_semantic_id: str
    document_evidence_id: str
    table_byte_start: int | None
    table_byte_length: int | None
    table_sha256: str | None
    exact_table_html: str | None
    period_heading: str | None
    row_label: str | None
    values: tuple[PresentedDilutedEPSValue, ...]
    status: PresentationStatus
    issues: tuple[PresentationIssue, ...]
    limitations: tuple[str, ...]

    @property
    def semantic_id(self):
        return _identity("presentation-semantics", {
            "contract": self.contract_version,
            "document_profile": self.document_profile_version,
            "measurement_profile": self.measurement_profile,
            "source_cik": self.source_cik,
            "accession": self.accession,
            "form": self.form,
            "document_ordinal": self.document_ordinal,
            "document_type": self.document_type,
            "document_filename": self.document_filename,
            "document_semantic_id": self.document_semantic_id,
            "table_sha256": self.table_sha256,
            "period_heading": self.period_heading,
            "row_label": self.row_label,
            "values": [asdict(item) for item in self.values],
            "status": self.status,
            "issues": self.issues,
            "limitations": self.limitations,
        })

    @property
    def evidence_id(self):
        return _identity("presentation-evidence", {
            "semantic_id": self.semantic_id,
            "filing_receipt_id": self.filing_receipt_id,
            "filing_captured_at": self.filing_captured_at,
            "document_evidence_id": self.document_evidence_id,
            "table_byte_start": self.table_byte_start,
            "table_byte_length": self.table_byte_length,
            "exact_table_html": self.exact_table_html,
        })


@dataclass(frozen=True, slots=True)
class _Cell:
    kind: str
    text: str


class _TableParser(HTMLParser):
    _TEXT_TAGS = frozenset(("span", "div", "p", "strong", "b", "em", "i", "br"))

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.rows = []
        self._row = None
        self._cell_kind = None
        self._cell_text = []
        self.invalid = False
        self.cells = 0

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        attributes = dict(attrs)
        if tag == "table" and (self._row is not None or self.rows):
            self.invalid = True
        elif tag == "tr":
            if self._row is not None:
                self.invalid = True
            self._row = []
        elif tag in ("th", "td"):
            if (self._row is None or self._cell_kind is not None
                    or "rowspan" in attributes or "colspan" in attributes):
                self.invalid = True
            self._cell_kind = tag
            self._cell_text = []
        elif self._cell_kind is not None and tag not in self._TEXT_TAGS:
            self.invalid = True

    def handle_endtag(self, tag):
        tag = tag.lower()
        if tag in ("th", "td"):
            if self._cell_kind != tag or self._row is None:
                self.invalid = True
                return
            text = " ".join("".join(self._cell_text).split())
            self._row.append(_Cell(tag, text))
            self.cells += 1
            if self.cells > MAX_CELLS:
                self.invalid = True
            self._cell_kind = None
            self._cell_text = []
        elif tag == "tr":
            if self._row is None or self._cell_kind is not None:
                self.invalid = True
                return
            if self._row:
                self.rows.append(tuple(self._row))
            self._row = None

    def handle_data(self, data):
        if self._cell_kind is not None:
            self._cell_text.append(data)

    def close(self):
        super().close()
        if self._row is not None or self._cell_kind is not None:
            self.invalid = True


def _identity(domain, value):
    def project(item):
        if isinstance(item, StrEnum):
            return item.value
        if type(item) is Decimal:
            parts = item.as_tuple()
            return {"sign": parts.sign, "digits": list(parts.digits),
                    "exponent": parts.exponent}
        if type(item) is tuple:
            return [project(value) for value in item]
        if type(item) is list:
            return [project(value) for value in item]
        if type(item) is dict:
            return {key: project(value) for key, value in item.items()}
        return item
    return digest(("pam:sec-five-year-eps-presentation:" + domain + ":v1\0").encode(
        "ascii") + canonical_json(project(value)))


def _normalized(value):
    return " ".join(value.split()).upper()


def _decimal(value):
    raw = " ".join(value.split())
    if _NUMBER.fullmatch(raw) is None:
        return None
    negative_parentheses = raw.startswith("(") and raw.endswith(")")
    cleaned = raw.strip("()").replace("$", "").replace(",", "").replace(" ", "")
    if negative_parentheses:
        cleaned = "-" + cleaned
    try:
        result = Decimal(cleaned)
    except InvalidOperation:
        return None
    return result if result.is_finite() else None


def _candidate(rows):
    issues = set()
    if len(rows) < 2:
        return None, {PresentationIssue.MALFORMED_HTML_TABLE}
    supported_rows = []
    adjusted = False
    basic = False
    for index, row in enumerate(rows):
        if not row:
            continue
        label = _normalized(row[0].text)
        if "EARNINGS PER SHARE" in label or "INCOME PER" in label:
            adjusted = adjusted or any(term in label for term in _PROHIBITED_ROWS)
            basic = basic or ("BASIC" in label and "DILUTED" not in label)
        if label in _SUPPORTED_ROWS:
            supported_rows.append((index, row, label))
    if len(supported_rows) > 1:
        return None, {PresentationIssue.AMBIGUOUS_DILUTED_EPS_ROW}
    if not supported_rows:
        if adjusted:
            issues.add(PresentationIssue.ADJUSTED_OR_NON_GAAP_EPS_ROW)
        if basic:
            issues.add(PresentationIssue.BASIC_EPS_ONLY)
        return None, issues
    row_index, value_row, label = supported_rows[0]
    if len(value_row) != 6:
        return None, {PresentationIssue.PERIOD_COUNT_NOT_EXACTLY_FIVE}

    heading = None
    year_cells = None
    for header in rows[:row_index]:
        if len(header) != 6:
            continue
        normalized_heading = _normalized(header[0].text)
        if _CAPTION.fullmatch(normalized_heading) is None:
            continue
        if not all(_YEAR.fullmatch(cell.text.strip()) for cell in header[1:]):
            continue
        if year_cells is not None:
            return None, {PresentationIssue.PERIOD_LABEL_UNSUPPORTED}
        heading = normalized_heading
        year_cells = header[1:]
    if year_cells is None:
        return None, {PresentationIssue.PERIOD_LABEL_UNSUPPORTED}
    caption = _CAPTION.fullmatch(heading)
    month = _MONTHS.get(caption.group(1))
    day = int(caption.group(2))
    if month is None:
        return None, {PresentationIssue.PERIOD_LABEL_UNSUPPORTED}
    values = []
    for ordinal, (year_cell, value_cell) in enumerate(zip(year_cells, value_row[1:]), start=1):
        year = int(year_cell.text)
        try:
            period_end = date(year, month, day).isoformat()
        except ValueError:
            return None, {PresentationIssue.PERIOD_LABEL_UNSUPPORTED}
        value = _decimal(value_cell.text)
        if value is None:
            return None, {PresentationIssue.INVALID_EXACT_DECIMAL}
        values.append(PresentedDilutedEPSValue(
            year_cell.text.strip(), period_end, value_cell.text, value, ordinal))
    if len({item.period_end for item in values}) != 5:
        return None, {PresentationIssue.DUPLICATE_PERIOD_ENDPOINT}
    return (heading, label, tuple(values)), issues


def extract_sec_five_year_eps_presentation(
    filing_archive: SecFilingArchive,
    request: SecFiveYearEPSPresentationRequest,
) -> SecFiveYearEPSPresentation:
    """Extract exactly one supported five-period presentation from one receipt."""
    if (type(filing_archive) is not SecFilingArchive
            or type(request) is not SecFiveYearEPSPresentationRequest):
        raise SecFiveYearEPSPresentationError("Exact typed archive/request required")
    inventory = replay_sec_filing_document_inventory(
        filing_archive, SecFilingDocumentInventoryRequest(request.filing_receipt_id))
    primary = inventory.documents[0]
    limitations = (
        "PRESENTATION_COMPARABILITY_EVIDENCE_ONLY",
        "NO_CURRENT_QUOTE_BASIS",
        "NO_PDF_OCR_OR_BROWSER_REPAIR",
        "NO_C3_VALUE_REPLACEMENT",
        "NO_FINAL_ECONOMIC_ADMISSION",
    )
    if inventory.form not in SUPPORTED_FORMS or primary.document_type != inventory.form:
        return SecFiveYearEPSPresentation(
            CONTRACT_VERSION, DOCUMENT_PROFILE_VERSION, MEASUREMENT_PROFILE,
            inventory.receipt.receipt_id, inventory.receipt.captured_at,
            inventory.cik, inventory.accession, inventory.form, primary.document_ordinal,
            primary.document_type, primary.filename, primary.semantic_id, primary.evidence_id,
            None, None, None, None, None, None, (),
            PresentationStatus.PRESENTATION_UNSUPPORTED,
            (PresentationIssue.UNSUPPORTED_FILING_FORM,), limitations)
    raw = filing_archive.read_object(inventory.receipt)
    payload = raw[primary.byte_start:primary.byte_start + primary.byte_length]
    if len(payload) > MAX_DOCUMENT_BYTES:
        issues = (PresentationIssue.UNSUPPORTED_DOCUMENT_PROFILE,)
        text = None
    else:
        try:
            text = payload.decode("utf-8")
        except UnicodeError:
            text = None
        issues = () if text is not None else (PresentationIssue.UNSUPPORTED_DOCUMENT_PROFILE,)
    candidates = []
    observed_issues = set(issues)
    if text is not None:
        matches = tuple(_TABLE.finditer(text))
        if len(matches) > MAX_TABLES:
            observed_issues.add(PresentationIssue.UNSUPPORTED_DOCUMENT_PROFILE)
        else:
            for match in matches:
                parser = _TableParser()
                try:
                    parser.feed(match.group(0))
                    parser.close()
                except (ValueError, RecursionError):
                    parser.invalid = True
                if parser.invalid:
                    observed_issues.add(PresentationIssue.MALFORMED_HTML_TABLE)
                    continue
                candidate, candidate_issues = _candidate(tuple(parser.rows))
                observed_issues.update(candidate_issues)
                if candidate is not None:
                    prefix = text[:match.start()].encode("utf-8")
                    table_bytes = match.group(0).encode("utf-8")
                    candidates.append((candidate, primary.byte_start + len(prefix),
                                       table_bytes, match.group(0)))
    if len(candidates) > 1:
        status = PresentationStatus.SOURCE_CONFLICT
        observed_issues.add(PresentationIssue.MULTIPLE_CANDIDATE_PRESENTATIONS)
        selected = None
    elif len(candidates) == 1:
        status = PresentationStatus.CAPTURED_FIVE_YEAR_DILUTED_EPS_PRESENTATION
        selected = candidates[0]
        observed_issues = set()
    else:
        selected = None
        if observed_issues & {
            PresentationIssue.UNSUPPORTED_FILING_FORM,
            PresentationIssue.UNSUPPORTED_DOCUMENT_PROFILE,
            PresentationIssue.MALFORMED_HTML_TABLE,
            PresentationIssue.ADJUSTED_OR_NON_GAAP_EPS_ROW,
            PresentationIssue.BASIC_EPS_ONLY,
            PresentationIssue.AMBIGUOUS_DILUTED_EPS_ROW,
            PresentationIssue.PERIOD_COUNT_NOT_EXACTLY_FIVE,
            PresentationIssue.PERIOD_LABEL_UNSUPPORTED,
            PresentationIssue.DUPLICATE_PERIOD_ENDPOINT,
            PresentationIssue.INVALID_EXACT_DECIMAL,
        }:
            status = PresentationStatus.PRESENTATION_UNSUPPORTED
        else:
            status = PresentationStatus.PRESENTATION_UNAVAILABLE
        observed_issues.add(PresentationIssue.NO_SUPPORTED_DILUTED_EPS_PRESENTATION)
    if selected is None:
        table_start = table_length = table_hash = table_html = heading = row_label = None
        values = ()
    else:
        (heading, row_label, values), table_start, table_bytes, table_html = selected
        table_length = len(table_bytes)
        table_hash = digest(table_bytes)
    return SecFiveYearEPSPresentation(
        CONTRACT_VERSION, DOCUMENT_PROFILE_VERSION, MEASUREMENT_PROFILE,
        inventory.receipt.receipt_id, inventory.receipt.captured_at,
        inventory.cik, inventory.accession, inventory.form, primary.document_ordinal,
        primary.document_type, primary.filename, primary.semantic_id, primary.evidence_id,
        table_start, table_length, table_hash, table_html, heading, row_label, values,
        status, tuple(sorted(observed_issues, key=lambda item: item.value)), limitations)
