"""Controlled SEC reporting-subject source claims; never continuity authority.

This source-only layer freshly replays one captured Submissions history and exact
D2A filing receipts.  It preserves filing metadata signals and narrowly reviewed
explicit text claims.  Silence, CIK sameness, names, dates, and filing continuity
never become an accounting reporting-subject conclusion.
"""
from dataclasses import asdict, dataclass
from enum import StrEnum
from html.parser import HTMLParser
import re

from .sec_filing_archive import FilingReceipt, SecFilingArchive, canonical_json, digest
from .sec_filing_document_inventory import (
    SecFilingDocumentInventoryAssessment,
    SecFilingDocumentInventoryRequest,
    UnsupportedSecFilingDocumentInventorySource,
    replay_sec_filing_document_inventory,
)
from .sec_submissions_archive import SecSubmissionsArchive
from .sec_submissions_inventory import (
    FilingOccurrence,
    InventoryStatus,
    SecSubmissionsInventoryAssessment,
    SecSubmissionsInventoryRequest,
    replay_sec_submissions_inventory,
)


CONTRACT_VERSION = "2026-09-27-sec-reporting-subject-source-foundation-v1"
CLAIM_PROFILE_VERSION = "2026-09-27-sec-reporting-subject-explicit-claims-v1"
DOCUMENT_PROFILE_VERSION = "2026-09-27-sec-reporting-subject-documents-v1"
SUPPORTED_FORMS = frozenset(("10-K", "10-K/A", "10-Q", "10-Q/A", "8-K", "8-K/A"))
MAX_FILING_RECEIPTS = 10_000
MAX_ELEMENTS = 100_000
MAX_BLOCKS = 25_000
MAX_BLOCK_CHARACTERS = 32_768
MAX_VISIBLE_CHARACTERS = 4_000_000

_RECEIPT_ID = re.compile(r"[0-9a-f]{64}", re.ASCII)
_ASCII_UPPER = str.maketrans("abcdefghijklmnopqrstuvwxyz", "ABCDEFGHIJKLMNOPQRSTUVWXYZ")
_EXHIBIT_99 = re.compile(r"EX-99(?:\.[0-9]{1,3})?", re.ASCII)


class SecReportingSubjectSourceRequestError(ValueError):
    """Invalid explicit receipt selection or untyped public argument."""


class ReportingSubjectSourceStatus(StrEnum):
    CAPTURED_REPORTING_SUBJECT_SOURCE_SET = "CAPTURED_REPORTING_SUBJECT_SOURCE_SET"
    INCOMPLETE_REPORTING_SUBJECT_SOURCE_SET = "INCOMPLETE_REPORTING_SUBJECT_SOURCE_SET"
    SOURCE_CONFLICT = "SOURCE_CONFLICT"
    UNSUPPORTED_SOURCE_PROFILE = "UNSUPPORTED_SOURCE_PROFILE"


class ReportingSubjectSignalKind(StrEnum):
    ACQUISITION_DISPOSITION_SIGNAL = "ACQUISITION_DISPOSITION_SIGNAL"
    CERTIFYING_ACCOUNTANT_CHANGE_SIGNAL = "CERTIFYING_ACCOUNTANT_CHANGE_SIGNAL"
    CHANGE_IN_CONTROL_SIGNAL = "CHANGE_IN_CONTROL_SIGNAL"
    FISCAL_YEAR_CHANGE_SIGNAL = "FISCAL_YEAR_CHANGE_SIGNAL"
    SHELL_STATUS_CHANGE_SIGNAL = "SHELL_STATUS_CHANGE_SIGNAL"
    FINANCIAL_STATEMENTS_EXHIBITS_SIGNAL = "FINANCIAL_STATEMENTS_EXHIBITS_SIGNAL"


class ReportingSubjectClaimKind(StrEnum):
    PREDECESSOR_REFERENCE = "PREDECESSOR_REFERENCE"
    SUCCESSOR_REFERENCE = "SUCCESSOR_REFERENCE"
    PREDECESSOR_SUCCESSOR_TRANSITION = "PREDECESSOR_SUCCESSOR_TRANSITION"
    ACCOUNTING_ACQUIRER_REFERENCE = "ACCOUNTING_ACQUIRER_REFERENCE"
    ACCOUNTING_ACQUIRER_BECOMES_REPORTING_ENTITY = (
        "ACCOUNTING_ACQUIRER_BECOMES_REPORTING_ENTITY"
    )
    REVERSE_ACQUISITION_REFERENCE = "REVERSE_ACQUISITION_REFERENCE"
    REVERSE_RECAPITALIZATION_REFERENCE = "REVERSE_RECAPITALIZATION_REFERENCE"
    CONTINUING_REPORTING_ENTITY_REFERENCE = "CONTINUING_REPORTING_ENTITY_REFERENCE"
    PREDECESSOR_PERIOD_LABEL = "PREDECESSOR_PERIOD_LABEL"
    SUCCESSOR_PERIOD_LABEL = "SUCCESSOR_PERIOD_LABEL"
    CARVE_OUT_FINANCIAL_STATEMENTS_REFERENCE = "CARVE_OUT_FINANCIAL_STATEMENTS_REFERENCE"
    COMBINED_FINANCIAL_STATEMENTS_REFERENCE = "COMBINED_FINANCIAL_STATEMENTS_REFERENCE"
    UNINTERPRETED_RESTRUCTURING_LANGUAGE = "UNINTERPRETED_RESTRUCTURING_LANGUAGE"


class ReportingSubjectSourceIssue(StrEnum):
    D2B_REFERENCE_CLOSURE_INCOMPLETE = "D2B_REFERENCE_CLOSURE_INCOMPLETE"
    D2B_INVENTORY_CONFLICT = "D2B_INVENTORY_CONFLICT"
    MISSING_RELEVANT_FILING_CAPTURE = "MISSING_RELEVANT_FILING_CAPTURE"
    D2B_D2A_FORM_MISMATCH = "D2B_D2A_FORM_MISMATCH"
    DIFFERING_CAPTURE_BYTES = "DIFFERING_CAPTURE_BYTES"
    UNSUPPORTED_DOCUMENT_INVENTORY = "UNSUPPORTED_DOCUMENT_INVENTORY"
    UNSUPPORTED_DOCUMENT_REPRESENTATION = "UNSUPPORTED_DOCUMENT_REPRESENTATION"
    MALFORMED_OR_AMBIGUOUS_TEXT = "MALFORMED_OR_AMBIGUOUS_TEXT"
    SOURCE_SAFETY_BOUND_EXCEEDED = "SOURCE_SAFETY_BOUND_EXCEEDED"
    UNREVIEWED_8K_ITEM_METADATA = "UNREVIEWED_8K_ITEM_METADATA"
    UNINTERPRETED_RESTRUCTURING_LANGUAGE = "UNINTERPRETED_RESTRUCTURING_LANGUAGE"
    INCOMPATIBLE_SUBJECT_LABELS = "INCOMPATIBLE_SUBJECT_LABELS"


_ITEM_SIGNALS = {
    "2.01": ReportingSubjectSignalKind.ACQUISITION_DISPOSITION_SIGNAL,
    "4.01": ReportingSubjectSignalKind.CERTIFYING_ACCOUNTANT_CHANGE_SIGNAL,
    "5.01": ReportingSubjectSignalKind.CHANGE_IN_CONTROL_SIGNAL,
    "5.03": ReportingSubjectSignalKind.FISCAL_YEAR_CHANGE_SIGNAL,
    "5.06": ReportingSubjectSignalKind.SHELL_STATUS_CHANGE_SIGNAL,
    "9.01": ReportingSubjectSignalKind.FINANCIAL_STATEMENTS_EXHIBITS_SIGNAL,
}

_LIMITATIONS = (
    "ABSENCE_OF_A_TRANSITION_CLAIM_IS_NOT_CONTINUITY_EVIDENCE",
    "CAPTURED_REFERENCE_CLOSURE_IS_NOT_HISTORICAL_OR_EVENT_COMPLETENESS",
    "CIK_IS_NOT_ACCOUNTING_REPORTING_SUBJECT_IDENTITY",
    "NO_REPORTING_SUBJECT_CONTINUITY_CONCLUSION",
    "NO_C3_BLOCKER_DISCHARGE",
)


def _identity(domain, value):
    return digest(("pam:sec-reporting-subject-source:" + domain + ":v1\0").encode("ascii")
                  + canonical_json(value))


@dataclass(frozen=True, slots=True)
class SecReportingSubjectSourceRequest:
    parent_submissions_receipt_id: str
    child_submissions_receipt_ids: tuple[str, ...] = ()
    filing_receipt_ids: tuple[str, ...] = ()

    def __post_init__(self):
        values = (self.parent_submissions_receipt_id, *self.child_submissions_receipt_ids,
                  *self.filing_receipt_ids)
        if (type(self.parent_submissions_receipt_id) is not str
                or type(self.child_submissions_receipt_ids) is not tuple
                or type(self.filing_receipt_ids) is not tuple
                or len(self.filing_receipt_ids) > MAX_FILING_RECEIPTS
                or any(type(value) is not str or _RECEIPT_ID.fullmatch(value) is None
                       for value in values)
                or len(set(self.child_submissions_receipt_ids)) != len(
                    self.child_submissions_receipt_ids)
                or len(set(self.filing_receipt_ids)) != len(self.filing_receipt_ids)):
            raise SecReportingSubjectSourceRequestError("Exact unique receipt selectors required")


@dataclass(frozen=True, slots=True)
class ReportingSubjectFilingSignal:
    filing_occurrence_id: str
    filing_semantic_id: str
    accession: str
    form: str
    raw_items: str
    item_code: str
    kind: ReportingSubjectSignalKind

    @property
    def semantic_id(self):
        return _identity("filing-signal-semantics", {
            "filing_semantic_id": self.filing_semantic_id,
            "accession": self.accession,
            "form": self.form,
            "raw_items": self.raw_items,
            "item_code": self.item_code,
            "kind": self.kind,
        })

    @property
    def evidence_id(self):
        return _identity("filing-signal-evidence", {
            "semantic_id": self.semantic_id,
            "filing_occurrence_id": self.filing_occurrence_id,
        })


@dataclass(frozen=True, slots=True)
class ReportingSubjectSourceLabel:
    exact_source_label: str
    normalized_source_label: str
    role: str
    source_local_id: str


@dataclass(frozen=True, slots=True)
class ReportingSubjectClaimEvidence:
    filing_receipt_id: str
    filing_captured_at: str
    document_evidence_id: str
    document_byte_start: int
    document_byte_length: int


@dataclass(frozen=True, slots=True)
class ReportingSubjectSourceClaim:
    kind: ReportingSubjectClaimKind
    accession: str
    event_key: str
    document_semantic_id: str
    document_ordinal: int
    block_ordinal: int
    structural_element_kind: str
    exact_source_passage: str
    source_passage_sha256: str
    subject_labels: tuple[ReportingSubjectSourceLabel, ...]
    evidence_occurrences: tuple[ReportingSubjectClaimEvidence, ...]

    @property
    def semantic_id(self):
        return _identity("claim-semantics", {
            "contract": CONTRACT_VERSION,
            "profile": CLAIM_PROFILE_VERSION,
            "kind": self.kind,
            "accession": self.accession,
            "event_key": self.event_key,
            "document_semantic_id": self.document_semantic_id,
            "document_ordinal": self.document_ordinal,
            "block_ordinal": self.block_ordinal,
            "structural_element_kind": self.structural_element_kind,
            "source_passage_sha256": self.source_passage_sha256,
            "subject_labels": [asdict(label) for label in self.subject_labels],
        })

    @property
    def evidence_id(self):
        return _identity("claim-evidence", {
            "semantic_id": self.semantic_id,
            "exact_source_passage": self.exact_source_passage,
            "occurrences": [asdict(item) for item in self.evidence_occurrences],
        })


@dataclass(frozen=True, slots=True)
class ReportingSubjectSourceIssueOccurrence:
    issue: ReportingSubjectSourceIssue
    accession: str | None
    filing_receipt_id: str | None
    document_evidence_id: str | None
    exact_source_text: str | None


@dataclass(frozen=True, slots=True)
class ReportingSubjectFilingCapture:
    receipt: FilingReceipt
    document_inventory: SecFilingDocumentInventoryAssessment | None
    claim_semantic_ids: tuple[str, ...]
    issues: tuple[ReportingSubjectSourceIssue, ...]

    @property
    def semantic_id(self):
        return _identity("filing-capture-semantics", {
            "cik": self.receipt.cik,
            "accession": self.receipt.accession,
            "content_sha256": self.receipt.content_sha256,
            "document_inventory": (None if self.document_inventory is None else
                                   self.document_inventory.semantic_id),
            "claims": self.claim_semantic_ids,
            "issues": self.issues,
        })

    @property
    def evidence_id(self):
        return _identity("filing-capture-evidence", {
            "semantic_id": self.semantic_id,
            "receipt": asdict(self.receipt),
            "receipt_id": self.receipt.receipt_id,
            "document_inventory": (None if self.document_inventory is None else
                                   self.document_inventory.evidence_id),
        })


@dataclass(frozen=True, slots=True)
class ReportingSubjectFilingSource:
    accession: str
    occurrences: tuple[FilingOccurrence, ...]
    captures: tuple[ReportingSubjectFilingCapture, ...]
    signal_semantic_ids: tuple[str, ...]
    claim_semantic_ids: tuple[str, ...]
    issues: tuple[ReportingSubjectSourceIssue, ...]

    @property
    def semantic_id(self):
        return _identity("filing-source-semantics", {
            "accession": self.accession,
            "occurrences": sorted(item.semantic_id for item in self.occurrences),
            "captures": sorted(set(item.semantic_id for item in self.captures)),
            "signals": self.signal_semantic_ids,
            "claims": self.claim_semantic_ids,
            "issues": self.issues,
        })

    @property
    def evidence_id(self):
        return _identity("filing-source-evidence", {
            "semantic_id": self.semantic_id,
            "occurrences": sorted(item.occurrence_id for item in self.occurrences),
            "captures": sorted(item.evidence_id for item in self.captures),
        })


@dataclass(frozen=True, slots=True)
class SecReportingSubjectSourceAssessment:
    contract_version: str
    claim_profile_version: str
    document_profile_version: str
    source_cik: str
    submissions_inventory: SecSubmissionsInventoryAssessment
    filing_universe: tuple[ReportingSubjectFilingSource, ...]
    filing_signals: tuple[ReportingSubjectFilingSignal, ...]
    explicit_claims: tuple[ReportingSubjectSourceClaim, ...]
    source_issues: tuple[ReportingSubjectSourceIssueOccurrence, ...]
    conflicts: tuple[ReportingSubjectSourceIssueOccurrence, ...]
    status: ReportingSubjectSourceStatus
    limitations: tuple[str, ...]

    @property
    def semantic_id(self):
        issue_semantics = sorted(set((
            item.issue.value,
            item.accession or "",
            "" if item.exact_source_text is None else
            digest(item.exact_source_text.encode("utf-8")),
        ) for item in self.source_issues))
        conflict_semantics = sorted(set((
            item.issue.value,
            item.accession or "",
            "" if item.exact_source_text is None else
            digest(item.exact_source_text.encode("utf-8")),
        ) for item in self.conflicts))
        return _identity("assessment-semantics", {
            "contract": self.contract_version,
            "claim_profile": self.claim_profile_version,
            "document_profile": self.document_profile_version,
            "source_cik": self.source_cik,
            "submissions_inventory": self.submissions_inventory.semantic_id,
            "filing_universe": [item.semantic_id for item in self.filing_universe],
            "signals": sorted(item.semantic_id for item in self.filing_signals),
            "claims": sorted(item.semantic_id for item in self.explicit_claims),
            "issues": issue_semantics,
            "conflicts": conflict_semantics,
            "status": self.status,
            "limitations": self.limitations,
        })

    @property
    def evidence_id(self):
        return _identity("assessment-evidence", {
            "semantic_id": self.semantic_id,
            "submissions_inventory": self.submissions_inventory.evidence_id,
            "filing_universe": [item.evidence_id for item in self.filing_universe],
            "signals": sorted(item.evidence_id for item in self.filing_signals),
            "claims": sorted(item.evidence_id for item in self.explicit_claims),
            "issues": [asdict(item) for item in self.source_issues],
            "conflicts": [asdict(item) for item in self.conflicts],
        })


@dataclass(frozen=True, slots=True)
class _VisibleBlock:
    ordinal: int
    kind: str
    exact_text: str


class _TextProfileError(ValueError):
    def __init__(self, issue):
        self.issue = issue
        super().__init__(issue.value)


_VOID_TAGS = frozenset((
    "area", "base", "br", "col", "embed", "hr", "img", "input", "link",
    "meta", "param", "source", "track", "wbr",
))
_EXCLUDED_TAGS = frozenset((
    "head", "script", "style", "noscript", "template", "svg", "math", "canvas",
    "ix:header", "ix:hidden", "ix:references", "ix:resources", "ix:exclude",
))
_VISIBLE_IX_TAGS = frozenset((
    "ix:nonnumeric", "ix:nonfraction", "ix:fraction", "ix:continuation", "ix:footnote",
))
_BLOCK_TAGS = frozenset((
    "h1", "h2", "h3", "h4", "h5", "h6", "p", "li", "td", "th", "caption",
    "blockquote", "div", "section", "article",
))
_ATOMIC_BLOCK_TAGS = frozenset(("h1", "h2", "h3", "h4", "h5", "h6", "p", "caption"))


class _StrictVisibleBlockParser(HTMLParser):
    """Bounded balanced HTML parser; malformed input is not browser-repaired."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack = []
        self.blocks = []
        self.seen_root = False
        self.closed_root = False
        self.seen_body = False
        self.in_body = False
        self.elements = 0
        self.visible_characters = 0
        self.seen_declaration = False

    def _fail(self, issue=ReportingSubjectSourceIssue.MALFORMED_OR_AMBIGUOUS_TEXT):
        raise _TextProfileError(issue)

    def handle_decl(self, declaration):
        if (self.seen_root or self.seen_declaration
                or declaration.strip().lower() != "doctype html"):
            self._fail()
        self.seen_declaration = True

    def unknown_decl(self, data):
        self._fail()

    def handle_pi(self, data):
        if self.seen_root or self.seen_declaration or not data.lower().startswith("xml "):
            self._fail()
        self.seen_declaration = True

    def handle_starttag(self, tag, attrs):
        self.elements += 1
        if self.elements > MAX_ELEMENTS:
            self._fail(ReportingSubjectSourceIssue.SOURCE_SAFETY_BOUND_EXCEEDED)
        inherited = self.stack[-1]["excluded"] if self.stack else False
        if (self.closed_root
                or (":" in tag and not inherited and tag not in _VISIBLE_IX_TAGS
                    and tag not in _EXCLUDED_TAGS)):
            self._fail()
        names = [name for name, _ in attrs]
        if len(names) != len(set(names)):
            self._fail()
        if not self.seen_root:
            if tag != "html" or self.stack:
                self._fail()
            self.seen_root = True
        elif not self.stack:
            self._fail()
        if tag == "body":
            if self.seen_body or len(self.stack) != 1 or self.stack[0]["tag"] != "html":
                self._fail()
            self.seen_body = True
            self.in_body = True
        excluded = inherited or tag in _EXCLUDED_TAGS
        active = [frame for frame in self.stack if frame["parts"] is not None]
        if self.in_body and not excluded and tag in {"br", "hr"} and active:
            for frame in active:
                frame["parts"].append(" ")
            active[-1]["own"].append(" ")
        is_block = self.in_body and not excluded and tag in _BLOCK_TAGS
        if is_block:
            if active and active[-1]["tag"] in _ATOMIC_BLOCK_TAGS:
                self._fail()
            for frame in active:
                frame["nested"] = True
        if tag not in _VOID_TAGS:
            self.stack.append({"tag": tag, "excluded": excluded,
                               "parts": [] if is_block else None,
                               "own": [] if is_block else None, "nested": False})

    def handle_startendtag(self, tag, attrs):
        if tag not in _VOID_TAGS:
            self._fail()
        self.handle_starttag(tag, attrs)

    def handle_endtag(self, tag):
        if tag in _VOID_TAGS or not self.stack or self.stack[-1]["tag"] != tag:
            self._fail()
        frame = self.stack.pop()
        if frame["parts"] is not None:
            text = "".join(frame["parts"])
            if frame["nested"] and "".join(frame["own"]).strip():
                self._fail()
            if not frame["nested"] and text.strip():
                if len(text) > MAX_BLOCK_CHARACTERS or len(self.blocks) >= MAX_BLOCKS:
                    self._fail(ReportingSubjectSourceIssue.SOURCE_SAFETY_BOUND_EXCEEDED)
                self.blocks.append(_VisibleBlock(len(self.blocks), frame["tag"], text))
        if tag == "body":
            self.in_body = False
        if tag == "html":
            if self.stack or not self.seen_body:
                self._fail()
            self.closed_root = True

    def handle_data(self, data):
        excluded = self.stack[-1]["excluded"] if self.stack else False
        if self.in_body and not excluded:
            self.visible_characters += len(data)
            if self.visible_characters > MAX_VISIBLE_CHARACTERS:
                self._fail(ReportingSubjectSourceIssue.SOURCE_SAFETY_BOUND_EXCEEDED)
            active = [frame for frame in self.stack if frame["parts"] is not None]
            if not active:
                if data.strip():
                    self._fail()
                return
            for frame in active:
                frame["parts"].append(data)
            active[-1]["own"].append(data)
        elif data.strip() and not excluded:
            self._fail()

    def handle_comment(self, data):
        return

    def close(self):
        try:
            super().close()
        except (AssertionError, ValueError):
            self._fail()
        if self.stack or not self.seen_root or not self.seen_body or not self.closed_root:
            self._fail()


def _normalize(text):
    return re.sub(r"\s+", " ", text).strip().translate(_ASCII_UPPER)


def _blocks(payload):
    try:
        text = payload.decode("utf-8-sig")
    except UnicodeError:
        raise _TextProfileError(
            ReportingSubjectSourceIssue.UNSUPPORTED_DOCUMENT_REPRESENTATION) from None
    if (len(text) > MAX_VISIBLE_CHARACTERS * 2
            or any((ord(character) < 32 and character not in "\t\n\r")
                   or 127 <= ord(character) <= 159 for character in text)):
        raise _TextProfileError(
            ReportingSubjectSourceIssue.UNSUPPORTED_DOCUMENT_REPRESENTATION)
    if re.search(r"<html(?:\s|>)", text, re.IGNORECASE):
        parser = _StrictVisibleBlockParser()
        try:
            parser.feed(text)
            parser.close()
        except _TextProfileError:
            raise
        except (TypeError, ValueError):
            raise _TextProfileError(
                ReportingSubjectSourceIssue.MALFORMED_OR_AMBIGUOUS_TEXT) from None
        return tuple(parser.blocks)
    if "<" in text or ">" in text:
        raise _TextProfileError(
            ReportingSubjectSourceIssue.UNSUPPORTED_DOCUMENT_REPRESENTATION)
    values = [value for value in re.split(r"(?:\r?\n){2,}", text) if value.strip()]
    if not values and text.strip():
        values = [text]
    if (len(values) > MAX_BLOCKS or any(len(value) > MAX_BLOCK_CHARACTERS for value in values)):
        raise _TextProfileError(ReportingSubjectSourceIssue.SOURCE_SAFETY_BOUND_EXCEEDED)
    return tuple(_VisibleBlock(index, "text", value) for index, value in enumerate(values))


def _contains(normalized, phrase):
    return re.search(r"(?<![A-Z0-9])" + re.escape(phrase) + r"(?![A-Z0-9])",
                     normalized, re.ASCII) is not None


_LABEL_PATTERNS = (
    ("ACCOUNTING_ACQUIRER", re.compile(
        r"^(?:FOR ACCOUNTING PURPOSES,?\s+)?(?P<label>[A-Z][A-Z0-9&.,'() /-]{1,120}?)\s+"
        r"(?:WAS|IS|HAS BEEN)\s+(?:DETERMINED TO BE|IDENTIFIED AS|CONSIDERED|DEEMED)?\s*"
        r"(?:THE\s+)?ACCOUNTING ACQUIRER(?:\b|,)", re.ASCII)),
    ("PREDECESSOR", re.compile(
        r"^(?P<label>[A-Z][A-Z0-9&.,'() /-]{1,120}?)\s+"
        r"(?:WAS|IS|WILL BE)\s+(?:REFLECTED AS|CONSIDERED|DEEMED)?\s*"
        r"(?:THE\s+)?PREDECESSOR(?:\b|,)", re.ASCII)),
    ("SUCCESSOR", re.compile(
        r"^(?P<label>[A-Z][A-Z0-9&.,'() /-]{1,120}?)\s+"
        r"(?:WAS|IS|WILL BE|BECAME)\s+(?:REFLECTED AS|CONSIDERED|DEEMED)?\s*"
        r"(?:THE\s+)?SUCCESSOR(?:\b|,)", re.ASCII)),
)


def _labels(text, normalized, *, accession, document_semantic_id, kind):
    labels = []
    for role, pattern in _LABEL_PATTERNS:
        match = pattern.search(normalized)
        if match is None:
            continue
        normalized_label = re.sub(r"\s+", " ", match.group("label")).strip(" ,;:")
        if not normalized_label or len(normalized_label.split()) > 16:
            continue
        exact_match = re.search(re.escape(normalized_label), text, re.IGNORECASE)
        exact_label = (exact_match.group(0) if exact_match is not None else normalized_label)
        labels.append(ReportingSubjectSourceLabel(
            exact_label,
            normalized_label,
            role,
            _identity("source-local-label", {
                "contract": CONTRACT_VERSION,
                "accession": accession,
                "document_semantic_id": document_semantic_id,
                "normalized_source_label": normalized_label,
                "claim_kind": kind,
                "role": role,
            }),
        ))
    return tuple(labels)


def _claim_kinds(normalized):
    kinds = set()
    auditor_context = _contains(normalized, "AUDITOR") or _contains(normalized, "ACCOUNTANT")
    predecessor = _contains(normalized, "PREDECESSOR") and not auditor_context
    successor = _contains(normalized, "SUCCESSOR") and not auditor_context
    if predecessor:
        kinds.add(ReportingSubjectClaimKind.PREDECESSOR_REFERENCE)
    if successor:
        kinds.add(ReportingSubjectClaimKind.SUCCESSOR_REFERENCE)
    if predecessor and successor:
        kinds.add(ReportingSubjectClaimKind.PREDECESSOR_SUCCESSOR_TRANSITION)
    if _contains(normalized, "ACCOUNTING ACQUIRER"):
        kinds.add(ReportingSubjectClaimKind.ACCOUNTING_ACQUIRER_REFERENCE)
        if (_contains(normalized, "CONTINUING REPORTING ENTITY")
                or (_contains(normalized, "FINANCIAL STATEMENTS")
                    and re.search(r"\bBEC(?:OME|AME)\b.{0,80}\b(?:REGISTRANT|COMPANY)\b",
                                  normalized, re.ASCII))
                or (_contains(normalized, "CONSIDERED") and predecessor)
                or (_contains(normalized, "LEGAL SUCCESSOR") and
                    _contains(normalized, "REPORTING OBLIGATION"))):
            kinds.add(ReportingSubjectClaimKind.ACCOUNTING_ACQUIRER_BECOMES_REPORTING_ENTITY)
    if _contains(normalized, "REVERSE ACQUISITION") or _contains(normalized, "REVERSE MERGER"):
        kinds.add(ReportingSubjectClaimKind.REVERSE_ACQUISITION_REFERENCE)
    if _contains(normalized, "REVERSE RECAPITALIZATION"):
        kinds.add(ReportingSubjectClaimKind.REVERSE_RECAPITALIZATION_REFERENCE)
    if _contains(normalized, "CONTINUING REPORTING ENTITY"):
        kinds.add(ReportingSubjectClaimKind.CONTINUING_REPORTING_ENTITY_REFERENCE)
    if re.fullmatch(r"(?:THE\s+)?PREDECESSOR(?:\s+PERIOD)?", normalized, re.ASCII):
        kinds.add(ReportingSubjectClaimKind.PREDECESSOR_PERIOD_LABEL)
    if re.fullmatch(r"(?:THE\s+)?SUCCESSOR(?:\s+PERIOD)?", normalized, re.ASCII):
        kinds.add(ReportingSubjectClaimKind.SUCCESSOR_PERIOD_LABEL)
    if (_contains(normalized, "CARVE-OUT FINANCIAL STATEMENTS")
            or _contains(normalized, "CARVE OUT FINANCIAL STATEMENTS")):
        kinds.add(ReportingSubjectClaimKind.CARVE_OUT_FINANCIAL_STATEMENTS_REFERENCE)
    if _contains(normalized, "COMBINED FINANCIAL STATEMENTS"):
        kinds.add(ReportingSubjectClaimKind.COMBINED_FINANCIAL_STATEMENTS_REFERENCE)
    if (not kinds and ((_contains(normalized, "CHANGE IN REPORTING ENTITY"))
                       or (_contains(normalized, "RESTRUCTURING")
                           and _contains(normalized, "FINANCIAL STATEMENTS"))
                       or (_contains(normalized, "REORGANIZATION")
                           and _contains(normalized, "ACCOUNTING")))):
        kinds.add(ReportingSubjectClaimKind.UNINTERPRETED_RESTRUCTURING_LANGUAGE)
    return tuple(sorted(kinds, key=lambda item: item.value))


def _event_key(occurrences):
    fields = [dict(item.fields) for item in occurrences]
    forms = sorted({field["form"].removesuffix("/A") for field in fields})
    reports = sorted({field["reportDate"] for field in fields if field["reportDate"]})
    return "|".join((forms[0] if len(forms) == 1 else "CONFLICTING_FORM",
                     reports[0] if len(reports) == 1 else occurrences[0].semantic_id))


def _metadata_signals(occurrence):
    fields = dict(occurrence.fields)
    if fields["form"] not in {"8-K", "8-K/A"}:
        return (), None
    raw = fields.get("items")
    if raw is None or raw == "":
        return (), None
    if type(raw) is not str:
        return (), raw
    codes = re.findall(r"(?<![0-9])[0-9]\.[0-9]{2}(?![0-9])", raw, re.ASCII)
    residue = re.sub(r"[0-9]\.[0-9]{2}|[\s,;]+", "", raw)
    signals = tuple(ReportingSubjectFilingSignal(
        occurrence.occurrence_id, occurrence.semantic_id, fields["accessionNumber"],
        fields["form"], raw, code, _ITEM_SIGNALS[code])
        for code in codes if code in _ITEM_SIGNALS)
    unknown = tuple(code for code in codes if code not in _ITEM_SIGNALS)
    return signals, (raw if residue or unknown else None)


def _eligible_document(document):
    return document.document_ordinal == 0 or _EXHIBIT_99.fullmatch(document.document_type) is not None


def _extract_capture(archive, receipt, event_key):
    issues = []
    issue_occurrences = []
    try:
        inventory = replay_sec_filing_document_inventory(
            archive, SecFilingDocumentInventoryRequest(receipt.receipt_id))
    except UnsupportedSecFilingDocumentInventorySource:
        issue = ReportingSubjectSourceIssue.UNSUPPORTED_DOCUMENT_INVENTORY
        occurrence = ReportingSubjectSourceIssueOccurrence(
            issue, receipt.accession, receipt.receipt_id, None, None)
        return None, (), (issue,), (occurrence,)
    raw = archive.read_object(receipt)
    claims = []
    for document in inventory.documents:
        if not _eligible_document(document):
            continue
        payload = raw[document.byte_start:document.byte_start + document.byte_length]
        if len(payload) != document.byte_length or digest(payload) != document.content_sha256:
            raise AssertionError("D4D1 document provenance mismatch")
        try:
            blocks = _blocks(payload)
        except _TextProfileError as error:
            issues.append(error.issue)
            issue_occurrences.append(ReportingSubjectSourceIssueOccurrence(
                error.issue, receipt.accession, receipt.receipt_id,
                document.evidence_id, None))
            continue
        for block in blocks:
            normalized = _normalize(block.exact_text)
            for kind in _claim_kinds(normalized):
                labels = _labels(block.exact_text, normalized, accession=receipt.accession,
                                 document_semantic_id=document.semantic_id, kind=kind)
                evidence = ReportingSubjectClaimEvidence(
                    receipt.receipt_id, receipt.captured_at, document.evidence_id,
                    document.byte_start, document.byte_length)
                claims.append(ReportingSubjectSourceClaim(
                    kind, receipt.accession, event_key, document.semantic_id,
                    document.document_ordinal, block.ordinal, block.kind, block.exact_text,
                    digest(block.exact_text.encode("utf-8")), labels, (evidence,)))
                if kind is ReportingSubjectClaimKind.UNINTERPRETED_RESTRUCTURING_LANGUAGE:
                    issue = ReportingSubjectSourceIssue.UNINTERPRETED_RESTRUCTURING_LANGUAGE
                    issues.append(issue)
                    issue_occurrences.append(ReportingSubjectSourceIssueOccurrence(
                        issue, receipt.accession, receipt.receipt_id,
                        document.evidence_id, block.exact_text))
    return inventory, tuple(claims), tuple(sorted(set(issues), key=lambda item: item.value)), tuple(
        issue_occurrences)


def _merge_claims(claims):
    grouped = {}
    for claim in claims:
        key = (claim.kind, claim.accession, claim.event_key, claim.document_semantic_id,
               claim.document_ordinal, claim.block_ordinal, claim.structural_element_kind,
               claim.exact_source_passage, claim.source_passage_sha256, claim.subject_labels)
        grouped.setdefault(key, set()).update(claim.evidence_occurrences)
    return tuple(sorted((ReportingSubjectSourceClaim(
        *key, tuple(sorted(evidence, key=lambda item: (
            item.filing_receipt_id, item.document_evidence_id))))
        for key, evidence in grouped.items()), key=lambda item: item.semantic_id))


def build_sec_reporting_subject_source_foundation(
    submissions_archive: SecSubmissionsArchive,
    filing_archive: SecFilingArchive,
    request: SecReportingSubjectSourceRequest,
) -> SecReportingSubjectSourceAssessment:
    """Replay exact controlled sources and retain claims without deciding continuity."""
    if (type(submissions_archive) is not SecSubmissionsArchive
            or type(filing_archive) is not SecFilingArchive
            or type(request) is not SecReportingSubjectSourceRequest):
        raise SecReportingSubjectSourceRequestError("Exact typed archives/request required")
    inventory = replay_sec_submissions_inventory(
        submissions_archive,
        SecSubmissionsInventoryRequest(request.parent_submissions_receipt_id,
                                       tuple(sorted(request.child_submissions_receipt_ids))),
    )
    by_accession = {}
    for occurrence in inventory.occurrences:
        by_accession.setdefault(dict(occurrence.fields)["accessionNumber"], []).append(occurrence)
    relevant = {
        accession: tuple(occurrences) for accession, occurrences in by_accession.items()
        if any(dict(item.fields)["form"] in SUPPORTED_FORMS for item in occurrences)
    }

    selected = {}
    for receipt_id in sorted(request.filing_receipt_ids):
        receipt = filing_archive.read_receipt(receipt_id)
        if receipt.cik != inventory.parent.cik or receipt.accession not in relevant:
            raise SecReportingSubjectSourceRequestError(
                "Filing receipt is foreign to the selected source universe")
        selected.setdefault(receipt.accession, []).append(receipt)

    signals = []
    source_issues = []
    conflicts = []
    all_claims = []
    captures_by_accession = {}
    capture_issues_by_accession = {}
    signal_ids_by_accession = {}
    for accession, occurrences in sorted(relevant.items()):
        for occurrence in occurrences:
            found, unknown = _metadata_signals(occurrence)
            signals.extend(found)
            signal_ids_by_accession.setdefault(accession, []).extend(
                item.semantic_id for item in found)
            if unknown is not None:
                source_issues.append(ReportingSubjectSourceIssueOccurrence(
                    ReportingSubjectSourceIssue.UNREVIEWED_8K_ITEM_METADATA,
                    accession, None, None, str(unknown)))
        receipts = selected.get(accession, [])
        if not receipts:
            source_issues.append(ReportingSubjectSourceIssueOccurrence(
                ReportingSubjectSourceIssue.MISSING_RELEVANT_FILING_CAPTURE,
                accession, None, None, None))
            captures_by_accession[accession] = ()
            capture_issues_by_accession[accession] = (
                ReportingSubjectSourceIssue.MISSING_RELEVANT_FILING_CAPTURE,)
            continue
        content_hashes = {receipt.content_sha256 for receipt in receipts}
        accession_issues = set()
        if len(content_hashes) > 1:
            occurrence = ReportingSubjectSourceIssueOccurrence(
                ReportingSubjectSourceIssue.DIFFERING_CAPTURE_BYTES,
                accession, None, None, None)
            conflicts.append(occurrence)
            accession_issues.add(occurrence.issue)
        known_forms = {dict(item.fields)["form"] for item in occurrences}
        event_key = _event_key(occurrences)
        captures = []
        for receipt in receipts:
            document_inventory, claims, issues, occurrences_issues = _extract_capture(
                filing_archive, receipt, event_key)
            all_claims.extend(claims)
            source_issues.extend(occurrences_issues)
            accession_issues.update(issues)
            if document_inventory is not None and document_inventory.form not in known_forms:
                issue = ReportingSubjectSourceIssue.D2B_D2A_FORM_MISMATCH
                conflict = ReportingSubjectSourceIssueOccurrence(
                    issue, accession, receipt.receipt_id, None, None)
                conflicts.append(conflict)
                accession_issues.add(issue)
            captures.append(ReportingSubjectFilingCapture(
                receipt, document_inventory,
                tuple(sorted({claim.semantic_id for claim in claims})), issues))
        captures_by_accession[accession] = tuple(sorted(
            captures, key=lambda item: item.receipt.receipt_id))
        capture_issues_by_accession[accession] = tuple(sorted(
            accession_issues, key=lambda item: item.value))

    claims = _merge_claims(all_claims)
    claims_by_accession = {}
    for claim in claims:
        claims_by_accession.setdefault(claim.accession, []).append(claim.semantic_id)

    label_groups = {}
    for claim in claims:
        for label in claim.subject_labels:
            label_groups.setdefault((claim.event_key, label.role), set()).add(
                label.normalized_source_label)
    for (event_key, role), labels in sorted(label_groups.items()):
        if len(labels) > 1:
            conflicts.append(ReportingSubjectSourceIssueOccurrence(
                ReportingSubjectSourceIssue.INCOMPATIBLE_SUBJECT_LABELS,
                event_key, None, None, role + ": " + " | ".join(sorted(labels))))

    if inventory.status is InventoryStatus.INVENTORY_CONFLICT:
        conflicts.append(ReportingSubjectSourceIssueOccurrence(
            ReportingSubjectSourceIssue.D2B_INVENTORY_CONFLICT,
            None, None, None, None))
    elif inventory.status is InventoryStatus.CAPTURED_REFERENCE_CLOSURE_INCOMPLETE:
        source_issues.append(ReportingSubjectSourceIssueOccurrence(
            ReportingSubjectSourceIssue.D2B_REFERENCE_CLOSURE_INCOMPLETE,
            None, None, None, None))

    filing_universe = tuple(ReportingSubjectFilingSource(
        accession,
        tuple(sorted(occurrences, key=lambda item: item.occurrence_id)),
        captures_by_accession.get(accession, ()),
        tuple(sorted(signal_ids_by_accession.get(accession, ()))),
        tuple(sorted(claims_by_accession.get(accession, ()))),
        capture_issues_by_accession.get(accession, ()),
    ) for accession, occurrences in sorted(relevant.items()))

    issue_kinds = {item.issue for item in source_issues}
    unsupported = {
        ReportingSubjectSourceIssue.UNSUPPORTED_DOCUMENT_INVENTORY,
        ReportingSubjectSourceIssue.UNSUPPORTED_DOCUMENT_REPRESENTATION,
        ReportingSubjectSourceIssue.MALFORMED_OR_AMBIGUOUS_TEXT,
        ReportingSubjectSourceIssue.SOURCE_SAFETY_BOUND_EXCEEDED,
        ReportingSubjectSourceIssue.UNINTERPRETED_RESTRUCTURING_LANGUAGE,
    }
    incomplete = {
        ReportingSubjectSourceIssue.D2B_REFERENCE_CLOSURE_INCOMPLETE,
        ReportingSubjectSourceIssue.MISSING_RELEVANT_FILING_CAPTURE,
    }
    if conflicts:
        status = ReportingSubjectSourceStatus.SOURCE_CONFLICT
    elif issue_kinds & unsupported:
        status = ReportingSubjectSourceStatus.UNSUPPORTED_SOURCE_PROFILE
    elif issue_kinds & incomplete:
        status = ReportingSubjectSourceStatus.INCOMPLETE_REPORTING_SUBJECT_SOURCE_SET
    else:
        status = ReportingSubjectSourceStatus.CAPTURED_REPORTING_SUBJECT_SOURCE_SET
    return SecReportingSubjectSourceAssessment(
        CONTRACT_VERSION,
        CLAIM_PROFILE_VERSION,
        DOCUMENT_PROFILE_VERSION,
        inventory.parent.cik,
        inventory,
        filing_universe,
        tuple(sorted(signals, key=lambda item: item.evidence_id)),
        claims,
        tuple(sorted(source_issues, key=lambda item: (
            item.issue.value, item.accession or "", item.filing_receipt_id or "",
            item.document_evidence_id or "", item.exact_source_text or ""))),
        tuple(sorted(conflicts, key=lambda item: (
            item.issue.value, item.accession or "", item.filing_receipt_id or "",
            item.document_evidence_id or "", item.exact_source_text or ""))),
        status,
        _LIMITATIONS,
    )
