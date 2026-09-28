"""Controlled SEC corporate-action/share-basis source claims.

This module is a source foundation only.  It freshly replays one exact captured
Submissions inventory and selected complete-submission receipts, then preserves
finite reviewed textual claims.  It never infers an event-free interval, complete
corporate-action history, unchanged share basis, or EPS comparability.
"""
from dataclasses import asdict, dataclass
from datetime import datetime
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


CONTRACT_VERSION = "2026-09-27-sec-share-basis-source-foundation-v1"
CLAIM_PROFILE_VERSION = "2026-09-27-sec-share-basis-explicit-claims-v1"
DOCUMENT_PROFILE_VERSION = "2026-09-27-sec-share-basis-documents-v1"
SUPPORTED_FORMS = frozenset(("10-K", "10-K/A", "10-Q", "10-Q/A", "8-K", "8-K/A"))
MAX_FILING_RECEIPTS = 10_000
MAX_RATIO_TERM = 10**12
MAX_ELEMENTS = 100_000
MAX_BLOCKS = 25_000
MAX_BLOCK_CHARACTERS = 32_768
MAX_VISIBLE_CHARACTERS = 4_000_000

_RECEIPT_ID = re.compile(r"[0-9a-f]{64}", re.ASCII)
_EXHIBIT_99 = re.compile(r"EX-99(?:\.[0-9]{1,3})?", re.ASCII)
_CLASS_LABEL = re.compile(
    r"\b(?:(CLASS\s+[A-Z0-9-]{1,16})\s+)?COMMON\s+STOCK\b", re.ASCII)
_CLASS_LABEL_EXACT = re.compile(
    r"\b(?:(class\s+[A-Z0-9-]{1,16})\s+)?common\s+stock\b",
    re.ASCII | re.IGNORECASE,
)
_RATIO_HYPHEN = re.compile(
    r"(?<![0-9])(?P<new>[0-9]{1,13})\s*[- ]FOR[- ]\s*(?P<old>[0-9]{1,13})(?![0-9])",
    re.ASCII,
)
_RATIO_EVERY = re.compile(
    r"\bEVERY\s+(?P<old>[0-9]{1,13})\s+(?:ISSUED\s+AND\s+OUTSTANDING\s+)?SHARES?"
    r"(?:\s+OF\s+[A-Z0-9 -]{1,80})?\s+(?:BECAME|BECOME|WAS|WERE|SHALL\s+BE|WILL\s+BE)"
    r"(?:\s+CONVERTED\s+INTO)?\s+(?P<new>[0-9]{1,13})\s+SHARES?\b",
    re.ASCII,
)
_RATIO_COLON = re.compile(r"(?<![0-9])[0-9]{1,13}\s*:\s*[0-9]{1,13}(?![0-9])", re.ASCII)
_DATE_TEXT = (
    r"(?:JANUARY|FEBRUARY|MARCH|APRIL|MAY|JUNE|JULY|AUGUST|SEPTEMBER|OCTOBER|"
    r"NOVEMBER|DECEMBER)\s+[0-9]{1,2},\s+[0-9]{4}|[0-9]{4}-[0-9]{2}-[0-9]{2}"
)
_EFFECTIVE_DATE = re.compile(
    r"(?<!MARKET\s)\bEFFECTIVE(?:\s+DATE)?\s+"
    r"(?:ON|OF|AS\s+OF|WAS|IS|WILL\s+BE)?\s*"
    rf"(?P<date>{_DATE_TEXT})\b", re.ASCII)
_MARKET_EFFECTIVE_DATE = re.compile(
    r"\bMARKET\s+EFFECTIVE(?:\s+DATE)?\s+"
    r"(?:ON|OF|AS\s+OF|WAS|IS|WILL\s+BE)?\s*"
    rf"(?P<date>{_DATE_TEXT})\b", re.ASCII)
_RECORD_DATE = re.compile(
    r"\bRECORD\s+DATE\s+(?:ON|OF|WAS|IS|WILL\s+BE)?\s*"
    rf"(?P<date>{_DATE_TEXT})\b", re.ASCII)
_DECLARATION_DATE = re.compile(
    r"\b(?:DECLARATION\s+DATE\s+(?:ON|OF|WAS|IS)?|DECLARED\s+ON|ANNOUNCED\s+ON)\s*"
    rf"(?P<date>{_DATE_TEXT})\b", re.ASCII)
_EX_DATE = re.compile(
    r"\bEX[- ]DATE\s+(?:ON|OF|WAS|IS|WILL\s+BE)?\s*"
    rf"(?P<date>{_DATE_TEXT})\b", re.ASCII)
_EFFECTIVE_DATE_MENTION = re.compile(
    r"(?<!MARKET\s)\b(?:EFFECTIVE\s+DATE|EFFECTIVE\s+(?:ON|AS\s+OF))\b", re.ASCII)
_MARKET_EFFECTIVE_DATE_MENTION = re.compile(
    r"\bMARKET\s+EFFECTIVE(?:\s+DATE)?\b", re.ASCII)
_RECORD_DATE_MENTION = re.compile(r"\bRECORD\s+DATE\b", re.ASCII)
_DECLARATION_DATE_MENTION = re.compile(
    r"\b(?:DECLARATION\s+DATE|DECLARED\s+ON|ANNOUNCED\s+ON)\b", re.ASCII)
_EX_DATE_MENTION = re.compile(r"\bEX[- ]DATE\b", re.ASCII)


class SecShareBasisSourceRequestError(ValueError):
    """Invalid explicit source selection or untyped public argument."""


class ShareBasisSourceStatus(StrEnum):
    CAPTURED_SHARE_BASIS_SOURCE_SET = "CAPTURED_SHARE_BASIS_SOURCE_SET"
    INCOMPLETE_SHARE_BASIS_SOURCE_SET = "INCOMPLETE_SHARE_BASIS_SOURCE_SET"
    SOURCE_CONFLICT = "SOURCE_CONFLICT"
    UNSUPPORTED_SOURCE_PROFILE = "UNSUPPORTED_SOURCE_PROFILE"


class ShareBasisSignalKind(StrEnum):
    MATERIAL_MODIFICATION_TO_RIGHTS_SIGNAL = "MATERIAL_MODIFICATION_TO_RIGHTS_SIGNAL"
    ARTICLES_OR_BYLAWS_AMENDMENT_SIGNAL = "ARTICLES_OR_BYLAWS_AMENDMENT_SIGNAL"
    OTHER_EVENTS_SIGNAL = "OTHER_EVENTS_SIGNAL"
    FINANCIAL_STATEMENTS_EXHIBITS_SIGNAL = "FINANCIAL_STATEMENTS_EXHIBITS_SIGNAL"


class CorporateActionKind(StrEnum):
    STOCK_SPLIT = "STOCK_SPLIT"
    REVERSE_STOCK_SPLIT = "REVERSE_STOCK_SPLIT"
    STOCK_DIVIDEND = "STOCK_DIVIDEND"
    SHARE_CLASS_CONVERSION = "SHARE_CLASS_CONVERSION"
    RECAPITALIZATION = "RECAPITALIZATION"
    MERGER_SECURITY_EXCHANGE = "MERGER_SECURITY_EXCHANGE"
    SPIN_OFF = "SPIN_OFF"
    SHARE_REDENOMINATION = "SHARE_REDENOMINATION"
    SHARE_CONSOLIDATION = "SHARE_CONSOLIDATION"
    OTHER_BASIS_AFFECTING_ACTION = "OTHER_BASIS_AFFECTING_ACTION"


class CorporateActionLifecycle(StrEnum):
    ANNOUNCED_OR_PROPOSED_REFERENCE = "ANNOUNCED_OR_PROPOSED_REFERENCE"
    APPROVED_REFERENCE = "APPROVED_REFERENCE"
    EFFECTIVE_OR_IMPLEMENTED_REFERENCE = "EFFECTIVE_OR_IMPLEMENTED_REFERENCE"
    CANCELLED_OR_NOT_IMPLEMENTED_REFERENCE = "CANCELLED_OR_NOT_IMPLEMENTED_REFERENCE"
    UNRESOLVED_LIFECYCLE = "UNRESOLVED_LIFECYCLE"


class SourceClaimLevel(StrEnum):
    LEXICAL_OR_PRESENTATION_REFERENCE = "LEXICAL_OR_PRESENTATION_REFERENCE"
    AFFIRMATIVE_LIFECYCLE_ACTION_CLAIM = "AFFIRMATIVE_LIFECYCLE_ACTION_CLAIM"


class SecurityClassSourceScope(StrEnum):
    NAMED_COMMON_CLASS_EXPLICIT = "NAMED_COMMON_CLASS_EXPLICIT"
    ISSUER_COMMON_STOCK_GENERIC = "ISSUER_COMMON_STOCK_GENERIC"
    MULTIPLE_CLASSES_OR_AMBIGUOUS = "MULTIPLE_CLASSES_OR_AMBIGUOUS"
    OTHER_SECURITY = "OTHER_SECURITY"
    UNRESOLVED = "UNRESOLVED"


class RetrospectivePresentationScope(StrEnum):
    NOT_APPLICABLE = "NOT_APPLICABLE"
    ALL_PERIODS_PRESENTED = "ALL_PERIODS_PRESENTED"
    SPECIFIC_PERIOD_REFERENCE = "SPECIFIC_PERIOD_REFERENCE"
    VAGUE_OR_UNRESOLVED = "VAGUE_OR_UNRESOLVED"


class ActionDateKind(StrEnum):
    DECLARATION_DATE = "DECLARATION_DATE"
    RECORD_DATE = "RECORD_DATE"
    EFFECTIVE_DATE = "EFFECTIVE_DATE"
    MARKET_EFFECTIVE_DATE = "MARKET_EFFECTIVE_DATE"
    EX_DATE = "EX_DATE"


class ShareBasisClaimKind(StrEnum):
    STOCK_SPLIT_REFERENCE = "STOCK_SPLIT_REFERENCE"
    REVERSE_STOCK_SPLIT_REFERENCE = "REVERSE_STOCK_SPLIT_REFERENCE"
    STOCK_DIVIDEND_REFERENCE = "STOCK_DIVIDEND_REFERENCE"
    SHARE_CLASS_CONVERSION_REFERENCE = "SHARE_CLASS_CONVERSION_REFERENCE"
    RECAPITALIZATION_REFERENCE = "RECAPITALIZATION_REFERENCE"
    MERGER_SECURITY_EXCHANGE_REFERENCE = "MERGER_SECURITY_EXCHANGE_REFERENCE"
    SPIN_OFF_REFERENCE = "SPIN_OFF_REFERENCE"
    SHARE_REDENOMINATION_REFERENCE = "SHARE_REDENOMINATION_REFERENCE"
    SHARE_CONSOLIDATION_REFERENCE = "SHARE_CONSOLIDATION_REFERENCE"
    OTHER_BASIS_AFFECTING_ACTION_REFERENCE = "OTHER_BASIS_AFFECTING_ACTION_REFERENCE"
    SPLIT_RATIO_REFERENCE = "SPLIT_RATIO_REFERENCE"
    ACTION_EFFECTIVE_DATE_REFERENCE = "ACTION_EFFECTIVE_DATE_REFERENCE"
    ACTION_MARKET_EFFECTIVE_DATE_REFERENCE = "ACTION_MARKET_EFFECTIVE_DATE_REFERENCE"
    ACTION_RECORD_DATE_REFERENCE = "ACTION_RECORD_DATE_REFERENCE"
    ACTION_DECLARATION_DATE_REFERENCE = "ACTION_DECLARATION_DATE_REFERENCE"
    ACTION_EX_DATE_REFERENCE = "ACTION_EX_DATE_REFERENCE"
    RETROACTIVE_SHARE_ADJUSTMENT_REFERENCE = "RETROACTIVE_SHARE_ADJUSTMENT_REFERENCE"
    RETROACTIVE_PER_SHARE_ADJUSTMENT_REFERENCE = (
        "RETROACTIVE_PER_SHARE_ADJUSTMENT_REFERENCE"
    )
    HISTORICAL_EPS_ADJUSTED_FOR_ACTION_REFERENCE = (
        "HISTORICAL_EPS_ADJUSTED_FOR_ACTION_REFERENCE"
    )
    COMMON_SHARE_BASIS_REFERENCE = "COMMON_SHARE_BASIS_REFERENCE"
    UNINTERPRETED_BASIS_AFFECTING_LANGUAGE = "UNINTERPRETED_BASIS_AFFECTING_LANGUAGE"


class ShareBasisSourceIssue(StrEnum):
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
    AMBIGUOUS_RATIO_ORIENTATION = "AMBIGUOUS_RATIO_ORIENTATION"
    INVALID_RATIO_TERMS = "INVALID_RATIO_TERMS"
    CONFLICTING_SOURCE_LOCAL_RATIOS = "CONFLICTING_SOURCE_LOCAL_RATIOS"
    CONFLICTING_SOURCE_LOCAL_EFFECTIVE_DATES = (
        "CONFLICTING_SOURCE_LOCAL_EFFECTIVE_DATES"
    )
    AMBIGUOUS_ACTION_DATE = "AMBIGUOUS_ACTION_DATE"
    UNINTERPRETED_BASIS_AFFECTING_LANGUAGE = "UNINTERPRETED_BASIS_AFFECTING_LANGUAGE"


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

    def _fail(self, issue=ShareBasisSourceIssue.MALFORMED_OR_AMBIGUOUS_TEXT):
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
            self._fail(ShareBasisSourceIssue.SOURCE_SAFETY_BOUND_EXCEEDED)
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
                    self._fail(ShareBasisSourceIssue.SOURCE_SAFETY_BOUND_EXCEEDED)
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
                self._fail(ShareBasisSourceIssue.SOURCE_SAFETY_BOUND_EXCEEDED)
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
    return re.sub(r"\s+", " ", text).strip().upper()


def _blocks(payload):
    try:
        text = payload.decode("utf-8-sig")
    except UnicodeError:
        raise _TextProfileError(
            ShareBasisSourceIssue.UNSUPPORTED_DOCUMENT_REPRESENTATION) from None
    if (len(text) > MAX_VISIBLE_CHARACTERS * 2
            or any((ord(character) < 32 and character not in "\t\n\r")
                   or 127 <= ord(character) <= 159 for character in text)):
        raise _TextProfileError(
            ShareBasisSourceIssue.UNSUPPORTED_DOCUMENT_REPRESENTATION)
    if re.search(r"<html(?:\s|>)", text, re.IGNORECASE):
        parser = _StrictVisibleBlockParser()
        try:
            parser.feed(text)
            parser.close()
        except _TextProfileError:
            raise
        except (TypeError, ValueError):
            raise _TextProfileError(
                ShareBasisSourceIssue.MALFORMED_OR_AMBIGUOUS_TEXT) from None
        return tuple(parser.blocks)
    if "<" in text or ">" in text:
        raise _TextProfileError(
            ShareBasisSourceIssue.UNSUPPORTED_DOCUMENT_REPRESENTATION)
    values = [value for value in re.split(r"(?:\r?\n){2,}", text) if value.strip()]
    if not values and text.strip():
        values = [text]
    if (len(values) > MAX_BLOCKS
            or any(len(value) > MAX_BLOCK_CHARACTERS for value in values)):
        raise _TextProfileError(ShareBasisSourceIssue.SOURCE_SAFETY_BOUND_EXCEEDED)
    return tuple(_VisibleBlock(index, "text", value) for index, value in enumerate(values))


_ITEM_SIGNALS = {
    "3.03": ShareBasisSignalKind.MATERIAL_MODIFICATION_TO_RIGHTS_SIGNAL,
    "5.03": ShareBasisSignalKind.ARTICLES_OR_BYLAWS_AMENDMENT_SIGNAL,
    "8.01": ShareBasisSignalKind.OTHER_EVENTS_SIGNAL,
    "9.01": ShareBasisSignalKind.FINANCIAL_STATEMENTS_EXHIBITS_SIGNAL,
}
_ACTION_CLAIMS = {
    CorporateActionKind.STOCK_SPLIT: ShareBasisClaimKind.STOCK_SPLIT_REFERENCE,
    CorporateActionKind.REVERSE_STOCK_SPLIT:
        ShareBasisClaimKind.REVERSE_STOCK_SPLIT_REFERENCE,
    CorporateActionKind.STOCK_DIVIDEND: ShareBasisClaimKind.STOCK_DIVIDEND_REFERENCE,
    CorporateActionKind.SHARE_CLASS_CONVERSION:
        ShareBasisClaimKind.SHARE_CLASS_CONVERSION_REFERENCE,
    CorporateActionKind.RECAPITALIZATION: ShareBasisClaimKind.RECAPITALIZATION_REFERENCE,
    CorporateActionKind.MERGER_SECURITY_EXCHANGE:
        ShareBasisClaimKind.MERGER_SECURITY_EXCHANGE_REFERENCE,
    CorporateActionKind.SPIN_OFF: ShareBasisClaimKind.SPIN_OFF_REFERENCE,
    CorporateActionKind.SHARE_REDENOMINATION:
        ShareBasisClaimKind.SHARE_REDENOMINATION_REFERENCE,
    CorporateActionKind.SHARE_CONSOLIDATION:
        ShareBasisClaimKind.SHARE_CONSOLIDATION_REFERENCE,
    CorporateActionKind.OTHER_BASIS_AFFECTING_ACTION:
        ShareBasisClaimKind.OTHER_BASIS_AFFECTING_ACTION_REFERENCE,
}
_LIMITATIONS = (
    "NO_UNCHANGED_SHARE_BASIS_CONCLUSION",
    "NO_SHARE_BASIS_COMPARABILITY_QUALIFICATION",
    "NO_SPLIT_BASIS_NOT_ESTABLISHED_DISCHARGE",
    "NO_ECONOMIC_COMPARABILITY_NOT_ESTABLISHED_DISCHARGE",
    "EMPTY_DETECTED_EVENT_INVENTORY_IS_NOT_NO_ACTION_EVIDENCE",
    "STABLE_CIK_TICKER_TITLE_SHARE_COUNT_OR_EPS_IS_NOT_DENOMINATION_CONTINUITY",
    "CAPTURED_REFERENCE_CLOSURE_IS_NOT_HISTORICAL_OR_EVENT_COMPLETENESS",
    "SOURCE_CLASS_LABELS_REQUIRE_FUTURE_PR5B_ROUTE_JOIN",
    "NO_PAID_NASDAQ_DAILY_LIST_AUTHORITY",
)


def _identity(domain, value):
    return digest(("pam:sec-share-basis-source:" + domain + ":v1\0").encode("ascii")
                  + canonical_json(value))


@dataclass(frozen=True, slots=True)
class SecShareBasisSourceRequest:
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
            raise SecShareBasisSourceRequestError("Exact unique receipt selectors required")


@dataclass(frozen=True, slots=True)
class ShareBasisFilingSignal:
    filing_occurrence_id: str
    filing_semantic_id: str
    accession: str
    form: str
    raw_items: str
    item_code: str
    kind: ShareBasisSignalKind

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
class ExactActionRatio:
    new_units: int
    old_units: int
    exact_source_terms: str


@dataclass(frozen=True, slots=True)
class ExactActionDate:
    kind: ActionDateKind
    exact_source_text: str
    normalized_date: str


@dataclass(frozen=True, slots=True)
class ShareBasisSourceClassLink:
    scope: SecurityClassSourceScope
    exact_source_labels: tuple[str, ...]
    normalized_source_labels: tuple[str, ...]
    source_local_id: str


@dataclass(frozen=True, slots=True)
class CorporateActionClaimEvidence:
    filing_receipt_id: str
    filing_captured_at: str
    document_evidence_id: str
    document_byte_start: int
    document_byte_length: int


@dataclass(frozen=True, slots=True)
class CorporateActionSourceClaim:
    kind: ShareBasisClaimKind
    action_kind: CorporateActionKind | None
    lifecycle: CorporateActionLifecycle
    claim_level: SourceClaimLevel
    accession: str
    source_local_action_key: str
    document_semantic_id: str
    document_ordinal: int
    block_ordinal: int
    structural_element_kind: str
    exact_source_passage: str
    source_passage_sha256: str
    class_link: ShareBasisSourceClassLink
    ratio: ExactActionRatio | None
    declaration_date: ExactActionDate | None
    effective_date: ExactActionDate | None
    market_effective_date: ExactActionDate | None
    record_date: ExactActionDate | None
    ex_date: ExactActionDate | None
    retrospective_scope: RetrospectivePresentationScope
    exact_period_reference: str | None
    evidence_occurrences: tuple[CorporateActionClaimEvidence, ...]

    @property
    def semantic_id(self):
        return _identity("claim-semantics", {
            "contract": CONTRACT_VERSION,
            "profile": CLAIM_PROFILE_VERSION,
            "kind": self.kind,
            "action_kind": self.action_kind,
            "lifecycle": self.lifecycle,
            "claim_level": self.claim_level,
            "accession": self.accession,
            "source_local_action_key": self.source_local_action_key,
            "document_semantic_id": self.document_semantic_id,
            "document_ordinal": self.document_ordinal,
            "block_ordinal": self.block_ordinal,
            "structural_element_kind": self.structural_element_kind,
            "source_passage_sha256": self.source_passage_sha256,
            "class_link": asdict(self.class_link),
            "ratio": None if self.ratio is None else asdict(self.ratio),
            "declaration_date": (None if self.declaration_date is None
                                 else asdict(self.declaration_date)),
            "effective_date": (None if self.effective_date is None
                               else asdict(self.effective_date)),
            "market_effective_date": (None if self.market_effective_date is None
                                      else asdict(self.market_effective_date)),
            "record_date": None if self.record_date is None else asdict(self.record_date),
            "ex_date": None if self.ex_date is None else asdict(self.ex_date),
            "retrospective_scope": self.retrospective_scope,
            "exact_period_reference": self.exact_period_reference,
        })

    @property
    def evidence_id(self):
        return _identity("claim-evidence", {
            "semantic_id": self.semantic_id,
            "exact_source_passage": self.exact_source_passage,
            "occurrences": [asdict(item) for item in self.evidence_occurrences],
        })


@dataclass(frozen=True, slots=True)
class ShareBasisSourceIssueOccurrence:
    issue: ShareBasisSourceIssue
    accession: str | None
    filing_receipt_id: str | None
    document_evidence_id: str | None
    exact_source_text: str | None


@dataclass(frozen=True, slots=True)
class ShareBasisFilingCapture:
    receipt: FilingReceipt
    document_inventory: SecFilingDocumentInventoryAssessment | None
    claim_semantic_ids: tuple[str, ...]
    issues: tuple[ShareBasisSourceIssue, ...]

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
class ShareBasisFilingSource:
    accession: str
    occurrences: tuple[FilingOccurrence, ...]
    captures: tuple[ShareBasisFilingCapture, ...]
    signal_semantic_ids: tuple[str, ...]
    claim_semantic_ids: tuple[str, ...]
    issues: tuple[ShareBasisSourceIssue, ...]

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
class SecShareBasisSourceAssessment:
    contract_version: str
    claim_profile_version: str
    document_profile_version: str
    source_cik: str
    submissions_inventory: SecSubmissionsInventoryAssessment
    filing_universe: tuple[ShareBasisFilingSource, ...]
    filing_signals: tuple[ShareBasisFilingSignal, ...]
    explicit_claims: tuple[CorporateActionSourceClaim, ...]
    source_issues: tuple[ShareBasisSourceIssueOccurrence, ...]
    conflicts: tuple[ShareBasisSourceIssueOccurrence, ...]
    status: ShareBasisSourceStatus
    limitations: tuple[str, ...]

    @property
    def semantic_id(self):
        issue_semantics = sorted(set((item.issue.value, item.accession or "",
            "" if item.exact_source_text is None else
            digest(item.exact_source_text.encode("utf-8"))) for item in self.source_issues))
        conflict_semantics = sorted(set((item.issue.value, item.accession or "",
            "" if item.exact_source_text is None else
            digest(item.exact_source_text.encode("utf-8"))) for item in self.conflicts))
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


def _contains(value, phrase):
    return re.search(r"(?<![A-Z0-9])" + re.escape(phrase) + r"(?![A-Z0-9])",
                     value, re.ASCII) is not None


def _action_kind(value):
    if _contains(value, "REVERSE STOCK SPLIT"):
        return CorporateActionKind.REVERSE_STOCK_SPLIT
    if _contains(value, "STOCK SPLIT") or _contains(value, "FORWARD SPLIT"):
        return CorporateActionKind.STOCK_SPLIT
    if _contains(value, "STOCK DIVIDEND"):
        return CorporateActionKind.STOCK_DIVIDEND
    if ((_contains(value, "CONVERTED INTO") or _contains(value, "CONVERSION"))
            and (_contains(value, "COMMON STOCK") or _contains(value, "COMMON SHARES"))):
        return CorporateActionKind.SHARE_CLASS_CONVERSION
    if _contains(value, "RECAPITALIZATION"):
        return CorporateActionKind.RECAPITALIZATION
    if ((_contains(value, "MERGER") or _contains(value, "BUSINESS COMBINATION"))
            and (_contains(value, "EXCHANGE") or _contains(value, "CONVERTED"))):
        return CorporateActionKind.MERGER_SECURITY_EXCHANGE
    if (_contains(value, "SPIN-OFF") or _contains(value, "SPIN OFF")
            or _contains(value, "SPINOFF")):
        return CorporateActionKind.SPIN_OFF
    if _contains(value, "REDENOMINATION") or _contains(value, "REDESIGNATION"):
        return CorporateActionKind.SHARE_REDENOMINATION
    if _contains(value, "SHARE CONSOLIDATION") or _contains(value, "CONSOLIDATION OF SHARES"):
        return CorporateActionKind.SHARE_CONSOLIDATION
    if (_contains(value, "SHARE BASIS") or _contains(value, "PER-SHARE PRESENTATION")
            or _contains(value, "PER SHARE PRESENTATION")):
        return CorporateActionKind.OTHER_BASIS_AFFECTING_ACTION
    return None


def _lifecycle(value, action_kind):
    if action_kind is None:
        return CorporateActionLifecycle.UNRESOLVED_LIFECYCLE
    negative = (
        r"\bDID\s+NOT\s+(?:APPROVE|AUTHORIZE|EFFECT|IMPLEMENT|COMPLETE|"
        r"PROCEED\s+WITH|BECOME\s+EFFECTIVE|OCCUR)\b",
        r"\bDID\s+NOT\s+(?:RECEIVE|OBTAIN)\s+APPROVAL\b",
        r"\b(?:WAS|WERE|IS|ARE)\s+(?:NOT|NEVER)\s+"
        r"(?:APPROVED|AUTHORIZED|EFFECTIVE|EFFECTED|IMPLEMENTED|COMPLETED)\b",
        r"\b(?:HAS|HAVE|HAD)\s+(?:NOT|NEVER)\s+BEEN\s+"
        r"(?:APPROVED|AUTHORIZED|EFFECTIVE|EFFECTED|IMPLEMENTED|COMPLETED)\b",
        r"\bWILL\s+(?:NOT|NEVER)\s+(?:(?:BE|BECOME)\s+)?"
        r"(?:APPROVED|AUTHORIZED|EFFECTIVE|EFFECTED|IMPLEMENTED|COMPLETED)\b",
        r"\bWILL\s+(?:NOT|NEVER)\s+"
        r"(?:APPROVE|AUTHORIZE|EFFECT|IMPLEMENT|COMPLETE|OCCUR)\b",
        r"\b(?:APPROVAL|AUTHORIZATION)\s+(?:WAS|WERE|IS|ARE)\s+"
        r"(?:NOT|NEVER)\s+(?:RECEIVED|OBTAINED|GRANTED)\b",
        r"\b(?:WAS|WERE)\s+REJECTED\b",
        r"\bCANCELLED\b", r"\bCANCELED\b", r"\bABANDONED\b",
    )
    if any(re.search(pattern, value, re.ASCII) for pattern in negative):
        return CorporateActionLifecycle.CANCELLED_OR_NOT_IMPLEMENTED_REFERENCE
    hypothetical = (
        r"\bMAY\s+(?:SEEK|PROPOSE|EFFECT|IMPLEMENT)\b", r"\bIF\s+APPROVED\b",
        r"\bPROPOSED\b", r"\bINTENDS?\s+TO\b", r"\bSUBJECT\s+TO\b",
        r"\bCONSIDER(?:ED|ING)?\b",
    )
    if any(re.search(pattern, value, re.ASCII) for pattern in hypothetical):
        return CorporateActionLifecycle.ANNOUNCED_OR_PROPOSED_REFERENCE
    effective = (
        r"\bBECAME\s+EFFECTIVE\b", r"\bWAS\s+EFFECTED\b", r"\bHAS\s+BEEN\s+EFFECTED\b",
        r"\bIMPLEMENTED\b", r"\bCOMPLETED\b", r"\bEFFECTIVE\s+(?:ON|AS\s+OF)\b",
        r"\bEFFECTED\s+A\b",
    )
    if any(re.search(pattern, value, re.ASCII) for pattern in effective):
        return CorporateActionLifecycle.EFFECTIVE_OR_IMPLEMENTED_REFERENCE
    if re.search(r"\b(?:APPROVED|AUTHORIZED)\b", value, re.ASCII):
        return CorporateActionLifecycle.APPROVED_REFERENCE
    return CorporateActionLifecycle.UNRESOLVED_LIFECYCLE


def _date(value):
    for pattern in ("%B %d, %Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(value.title(), pattern).date().isoformat()
        except ValueError:
            pass
    return None


def _dates(value, pattern, kind):
    results = []
    for match in pattern.finditer(value):
        exact = match.group("date")
        normalized = _date(exact)
        if normalized is not None:
            results.append(ExactActionDate(kind, exact, normalized))
    return tuple(dict.fromkeys(results))


def _ratios(value):
    results = []
    for pattern in (_RATIO_HYPHEN, _RATIO_EVERY):
        for match in pattern.finditer(value):
            new_units = int(match.group("new"))
            old_units = int(match.group("old"))
            results.append(ExactActionRatio(new_units, old_units, match.group(0)))
    return tuple(dict.fromkeys(results))


def _class_link(value, exact_text, accession, document_semantic_id, block_ordinal):
    matches = tuple(_CLASS_LABEL.finditer(value))
    exact_matches = tuple(_CLASS_LABEL_EXACT.finditer(exact_text))
    labels = tuple(dict.fromkeys(match.group(0) for match in exact_matches))
    normalized_labels = tuple(dict.fromkeys(match.group(0) for match in matches))
    named = tuple(dict.fromkeys(match.group(0) for match in matches if match.group(1)))
    if len(named) == 1 and len(labels) == 1:
        scope = SecurityClassSourceScope.NAMED_COMMON_CLASS_EXPLICIT
    elif len(set(named)) > 1:
        scope = SecurityClassSourceScope.MULTIPLE_CLASSES_OR_AMBIGUOUS
    elif labels:
        scope = SecurityClassSourceScope.ISSUER_COMMON_STOCK_GENERIC
    elif any(_contains(value, term) for term in ("PREFERRED STOCK", "WARRANT", "OPTION",
                                                  "CONVERTIBLE NOTE", "ADS", "ADR")):
        scope = SecurityClassSourceScope.OTHER_SECURITY
    else:
        scope = SecurityClassSourceScope.UNRESOLVED
    normalized = tuple(re.sub(r"\s+", " ", label).strip() for label in normalized_labels)
    return ShareBasisSourceClassLink(
        scope, labels, normalized,
        _identity("source-local-class-link", {
            "accession": accession,
            "document_semantic_id": document_semantic_id,
            "block_ordinal": block_ordinal,
            "scope": scope,
            "labels": normalized,
        }),
    )


def _retrospective(value):
    negative_adjustment = (
        r"\b(?:WAS|WERE|IS|ARE)\s+(?:NOT|NEVER)\s+"
        r"(?:RETROACTIVELY|RETROSPECTIVELY)\s+ADJUSTED\b",
        r"\b(?:HAS|HAVE|HAD)\s+(?:NOT|NEVER)\s+BEEN\s+"
        r"(?:RETROACTIVELY|RETROSPECTIVELY)\s+ADJUSTED\b",
        r"\b(?:WAS|WERE|IS|ARE|HAS|HAVE|HAD)\s+(?:NOT|NEVER)\s+"
        r"(?:BEEN\s+)?ADJUSTED\s+(?:RETROACTIVELY|RETROSPECTIVELY)\b",
        r"\bDID\s+NOT\s+(?:(?:RETROACTIVELY|RETROSPECTIVELY)\s+)?ADJUST\b",
        r"\bDID\s+NOT\s+RESTATE\b",
        r"\b(?:WAS|WERE|IS|ARE|HAS|HAVE|HAD)\s+(?:NOT|NEVER)\s+"
        r"(?:BEEN\s+)?RESTATED\s+TO\s+REFLECT\b",
    )
    if any(re.search(pattern, value, re.ASCII) for pattern in negative_adjustment):
        return (), RetrospectivePresentationScope.NOT_APPLICABLE, None
    adjusted = (_contains(value, "RETROACTIVELY ADJUSTED")
                or _contains(value, "RETROSPECTIVELY ADJUSTED")
                or _contains(value, "RESTATED TO REFLECT"))
    kinds = []
    if adjusted and (_contains(value, "SHARE AMOUNTS") or _contains(value, "SHARES")):
        kinds.append(ShareBasisClaimKind.RETROACTIVE_SHARE_ADJUSTMENT_REFERENCE)
    if adjusted and (_contains(value, "PER SHARE AMOUNTS")
                     or _contains(value, "PER-SHARE AMOUNTS")):
        kinds.append(ShareBasisClaimKind.RETROACTIVE_PER_SHARE_ADJUSTMENT_REFERENCE)
    if adjusted and (_contains(value, "EARNINGS PER SHARE") or _contains(value, "EPS")):
        kinds.append(ShareBasisClaimKind.HISTORICAL_EPS_ADJUSTED_FOR_ACTION_REFERENCE)
    if not kinds:
        return (), RetrospectivePresentationScope.NOT_APPLICABLE, None
    if (_contains(value, "ALL PERIODS PRESENTED")
            or _contains(value, "ALL HISTORICAL")
            or _contains(value, "ALL PRIOR PERIODS")):
        scope = RetrospectivePresentationScope.ALL_PERIODS_PRESENTED
    else:
        period = re.search(r"\b(?:YEAR|QUARTER|PERIOD)\s+ENDED\s+([^.;]{4,80})", value)
        if period is not None:
            scope = RetrospectivePresentationScope.SPECIFIC_PERIOD_REFERENCE
            return tuple(kinds), scope, period.group(0)
        scope = RetrospectivePresentationScope.VAGUE_OR_UNRESOLVED
    return tuple(kinds), scope, None


def _claim_parts(value):
    action = _action_kind(value)
    lifecycle = _lifecycle(value, action)
    kinds = []
    if action is not None:
        kinds.append(_ACTION_CLAIMS[action])
    ratios = _ratios(value)
    if ratios or _RATIO_COLON.search(value):
        kinds.append(ShareBasisClaimKind.SPLIT_RATIO_REFERENCE)
    declaration_dates = _dates(value, _DECLARATION_DATE, ActionDateKind.DECLARATION_DATE)
    effective_dates = _dates(value, _EFFECTIVE_DATE, ActionDateKind.EFFECTIVE_DATE)
    market_effective_dates = _dates(
        value, _MARKET_EFFECTIVE_DATE, ActionDateKind.MARKET_EFFECTIVE_DATE)
    record_dates = _dates(value, _RECORD_DATE, ActionDateKind.RECORD_DATE)
    ex_dates = _dates(value, _EX_DATE, ActionDateKind.EX_DATE)
    if declaration_dates or _DECLARATION_DATE_MENTION.search(value):
        kinds.append(ShareBasisClaimKind.ACTION_DECLARATION_DATE_REFERENCE)
    if effective_dates or _EFFECTIVE_DATE_MENTION.search(value):
        kinds.append(ShareBasisClaimKind.ACTION_EFFECTIVE_DATE_REFERENCE)
    if market_effective_dates or _MARKET_EFFECTIVE_DATE_MENTION.search(value):
        kinds.append(ShareBasisClaimKind.ACTION_MARKET_EFFECTIVE_DATE_REFERENCE)
    if record_dates or _RECORD_DATE_MENTION.search(value):
        kinds.append(ShareBasisClaimKind.ACTION_RECORD_DATE_REFERENCE)
    if ex_dates or _EX_DATE_MENTION.search(value):
        kinds.append(ShareBasisClaimKind.ACTION_EX_DATE_REFERENCE)
    retrospective, scope, period = _retrospective(value)
    kinds.extend(retrospective)
    if _contains(value, "COMMON STOCK") and any(
            _contains(value, term) for term in ("SHARE BASIS", "PER SHARE", "PER-SHARE",
                                                "SHARES OF COMMON STOCK")):
        kinds.append(ShareBasisClaimKind.COMMON_SHARE_BASIS_REFERENCE)
    uninterpreted = (not kinds and any(_contains(value, term) for term in (
        "RESTRUCTURING OF CAPITAL", "CHANGE IN SHARE DENOMINATION",
        "BASIS-AFFECTING", "BASIS AFFECTING")))
    if uninterpreted:
        kinds.append(ShareBasisClaimKind.UNINTERPRETED_BASIS_AFFECTING_LANGUAGE)
    return (tuple(dict.fromkeys(kinds)), action, lifecycle, ratios, declaration_dates,
            effective_dates, market_effective_dates, record_dates, ex_dates, scope, period)


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
    signals = tuple(ShareBasisFilingSignal(
        occurrence.occurrence_id, occurrence.semantic_id, fields["accessionNumber"],
        fields["form"], raw, code, _ITEM_SIGNALS[code])
        for code in codes if code in _ITEM_SIGNALS)
    unknown = tuple(code for code in codes if code not in _ITEM_SIGNALS)
    return signals, (raw if residue or unknown else None)


def _eligible_document(document):
    return (document.document_ordinal == 0
            or _EXHIBIT_99.fullmatch(document.document_type) is not None)


def _text_profile_issue(error):
    name = error.issue.value
    try:
        return ShareBasisSourceIssue(name)
    except ValueError:
        return ShareBasisSourceIssue.MALFORMED_OR_AMBIGUOUS_TEXT


def _extract_capture(archive, receipt):
    issues = []
    occurrences = []
    try:
        inventory = replay_sec_filing_document_inventory(
            archive, SecFilingDocumentInventoryRequest(receipt.receipt_id))
    except UnsupportedSecFilingDocumentInventorySource:
        issue = ShareBasisSourceIssue.UNSUPPORTED_DOCUMENT_INVENTORY
        return None, (), (issue,), (ShareBasisSourceIssueOccurrence(
            issue, receipt.accession, receipt.receipt_id, None, None),)
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
            issue = _text_profile_issue(error)
            issues.append(issue)
            occurrences.append(ShareBasisSourceIssueOccurrence(
                issue, receipt.accession, receipt.receipt_id, document.evidence_id, None))
            continue
        for block in blocks:
            value = _normalize(block.exact_text)
            (kinds, action, lifecycle, ratios, declaration_dates, effective_dates,
             market_effective_dates, record_dates, ex_dates, retrospective_scope,
             period) = _claim_parts(value)
            if not kinds:
                continue
            local_key = _identity("source-local-action", {
                "accession": receipt.accession,
                "document_semantic_id": document.semantic_id,
                "block_ordinal": block.ordinal,
                "action_kind": action,
            })
            block_issues = []
            if _RATIO_COLON.search(value) and not ratios:
                block_issues.append(ShareBasisSourceIssue.AMBIGUOUS_RATIO_ORIENTATION)
            if any(item.new_units <= 0 or item.old_units <= 0
                   or item.new_units > MAX_RATIO_TERM or item.old_units > MAX_RATIO_TERM
                   for item in ratios):
                block_issues.append(ShareBasisSourceIssue.INVALID_RATIO_TERMS)
            if len({(item.new_units, item.old_units) for item in ratios}) > 1:
                block_issues.append(ShareBasisSourceIssue.CONFLICTING_SOURCE_LOCAL_RATIOS)
            if (len({item.normalized_date for item in effective_dates}) > 1
                    or len({item.normalized_date for item in market_effective_dates}) > 1):
                block_issues.append(
                    ShareBasisSourceIssue.CONFLICTING_SOURCE_LOCAL_EFFECTIVE_DATES)
            if ((_DECLARATION_DATE_MENTION.search(value) and not declaration_dates)
                    or (_EFFECTIVE_DATE_MENTION.search(value) and not effective_dates)
                    or (_MARKET_EFFECTIVE_DATE_MENTION.search(value)
                        and not market_effective_dates)
                    or (_RECORD_DATE_MENTION.search(value) and not record_dates)
                    or (_EX_DATE_MENTION.search(value) and not ex_dates)):
                block_issues.append(ShareBasisSourceIssue.AMBIGUOUS_ACTION_DATE)
            if ShareBasisClaimKind.UNINTERPRETED_BASIS_AFFECTING_LANGUAGE in kinds:
                block_issues.append(
                    ShareBasisSourceIssue.UNINTERPRETED_BASIS_AFFECTING_LANGUAGE)
            class_link = _class_link(value, block.exact_text, receipt.accession,
                                     document.semantic_id, block.ordinal)
            evidence = CorporateActionClaimEvidence(
                receipt.receipt_id, receipt.captured_at, document.evidence_id,
                document.byte_start, document.byte_length)
            for kind in kinds:
                claim_level = (
                    SourceClaimLevel.AFFIRMATIVE_LIFECYCLE_ACTION_CLAIM
                    if (action is not None and lifecycle is not
                        CorporateActionLifecycle.UNRESOLVED_LIFECYCLE)
                    else SourceClaimLevel.LEXICAL_OR_PRESENTATION_REFERENCE
                )
                claims.append(CorporateActionSourceClaim(
                    kind, action, lifecycle, claim_level, receipt.accession, local_key,
                    document.semantic_id, document.document_ordinal, block.ordinal,
                    block.kind, block.exact_text,
                    digest(block.exact_text.encode("utf-8")), class_link,
                    ratios[0] if len(ratios) == 1 else None,
                    declaration_dates[0] if len(declaration_dates) == 1 else None,
                    effective_dates[0] if len(effective_dates) == 1 else None,
                    (market_effective_dates[0]
                     if len(market_effective_dates) == 1 else None),
                    record_dates[0] if len(record_dates) == 1 else None,
                    ex_dates[0] if len(ex_dates) == 1 else None,
                    retrospective_scope, period, (evidence,)))
            for issue in block_issues:
                issues.append(issue)
                occurrence = ShareBasisSourceIssueOccurrence(
                    issue, receipt.accession, receipt.receipt_id,
                    document.evidence_id, block.exact_text)
                if issue in {ShareBasisSourceIssue.CONFLICTING_SOURCE_LOCAL_RATIOS,
                             ShareBasisSourceIssue.CONFLICTING_SOURCE_LOCAL_EFFECTIVE_DATES}:
                    occurrences.append(occurrence)
                else:
                    occurrences.append(occurrence)
    return (inventory, tuple(claims), tuple(sorted(set(issues), key=lambda item: item.value)),
            tuple(occurrences))


def _merge_claims(claims):
    grouped = {}
    for claim in claims:
        key = (claim.kind, claim.action_kind, claim.lifecycle, claim.claim_level,
               claim.accession,
               claim.source_local_action_key, claim.document_semantic_id,
               claim.document_ordinal, claim.block_ordinal, claim.structural_element_kind,
               claim.exact_source_passage, claim.source_passage_sha256, claim.class_link,
               claim.ratio, claim.declaration_date, claim.effective_date,
               claim.market_effective_date, claim.record_date, claim.ex_date,
               claim.retrospective_scope, claim.exact_period_reference)
        grouped.setdefault(key, set()).update(claim.evidence_occurrences)
    return tuple(sorted((CorporateActionSourceClaim(
        *key, tuple(sorted(evidence, key=lambda item: (
            item.filing_receipt_id, item.document_evidence_id))))
        for key, evidence in grouped.items()), key=lambda item: item.semantic_id))


def build_sec_share_basis_source_foundation(
    submissions_archive: SecSubmissionsArchive,
    filing_archive: SecFilingArchive,
    request: SecShareBasisSourceRequest,
) -> SecShareBasisSourceAssessment:
    """Replay exact controlled sources; never decide basis comparability."""
    if (type(submissions_archive) is not SecSubmissionsArchive
            or type(filing_archive) is not SecFilingArchive
            or type(request) is not SecShareBasisSourceRequest):
        raise SecShareBasisSourceRequestError("Exact typed archives/request required")
    inventory = replay_sec_submissions_inventory(
        submissions_archive,
        SecSubmissionsInventoryRequest(request.parent_submissions_receipt_id,
                                       tuple(sorted(request.child_submissions_receipt_ids))),
    )
    by_accession = {}
    for occurrence in inventory.occurrences:
        by_accession.setdefault(dict(occurrence.fields)["accessionNumber"], []).append(occurrence)
    relevant = {accession: tuple(occurrences)
                for accession, occurrences in by_accession.items()
                if any(dict(item.fields)["form"] in SUPPORTED_FORMS
                       for item in occurrences)}

    selected = {}
    for receipt_id in sorted(request.filing_receipt_ids):
        receipt = filing_archive.read_receipt(receipt_id)
        if receipt.cik != inventory.parent.cik or receipt.accession not in relevant:
            raise SecShareBasisSourceRequestError(
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
                source_issues.append(ShareBasisSourceIssueOccurrence(
                    ShareBasisSourceIssue.UNREVIEWED_8K_ITEM_METADATA,
                    accession, None, None, str(unknown)))
        receipts = selected.get(accession, [])
        if not receipts:
            issue = ShareBasisSourceIssue.MISSING_RELEVANT_FILING_CAPTURE
            source_issues.append(ShareBasisSourceIssueOccurrence(
                issue, accession, None, None, None))
            captures_by_accession[accession] = ()
            capture_issues_by_accession[accession] = (issue,)
            continue
        accession_issues = set()
        if len({receipt.content_sha256 for receipt in receipts}) > 1:
            issue = ShareBasisSourceIssue.DIFFERING_CAPTURE_BYTES
            conflicts.append(ShareBasisSourceIssueOccurrence(
                issue, accession, None, None, None))
            accession_issues.add(issue)
        known_forms = {dict(item.fields)["form"] for item in occurrences}
        captures = []
        for receipt in receipts:
            document_inventory, claims, issues, issue_occurrences = _extract_capture(
                filing_archive, receipt)
            all_claims.extend(claims)
            for occurrence in issue_occurrences:
                if occurrence.issue in {
                    ShareBasisSourceIssue.CONFLICTING_SOURCE_LOCAL_RATIOS,
                    ShareBasisSourceIssue.CONFLICTING_SOURCE_LOCAL_EFFECTIVE_DATES,
                }:
                    conflicts.append(occurrence)
                else:
                    source_issues.append(occurrence)
            accession_issues.update(issues)
            if document_inventory is not None and document_inventory.form not in known_forms:
                issue = ShareBasisSourceIssue.D2B_D2A_FORM_MISMATCH
                conflicts.append(ShareBasisSourceIssueOccurrence(
                    issue, accession, receipt.receipt_id, None, None))
                accession_issues.add(issue)
            captures.append(ShareBasisFilingCapture(
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

    if inventory.status is InventoryStatus.INVENTORY_CONFLICT:
        conflicts.append(ShareBasisSourceIssueOccurrence(
            ShareBasisSourceIssue.D2B_INVENTORY_CONFLICT, None, None, None, None))
    elif inventory.status is InventoryStatus.CAPTURED_REFERENCE_CLOSURE_INCOMPLETE:
        source_issues.append(ShareBasisSourceIssueOccurrence(
            ShareBasisSourceIssue.D2B_REFERENCE_CLOSURE_INCOMPLETE,
            None, None, None, None))

    filing_universe = tuple(ShareBasisFilingSource(
        accession,
        tuple(sorted(occurrences, key=lambda item: item.occurrence_id)),
        captures_by_accession.get(accession, ()),
        tuple(sorted(signal_ids_by_accession.get(accession, ()))),
        tuple(sorted(claims_by_accession.get(accession, ()))),
        capture_issues_by_accession.get(accession, ()),
    ) for accession, occurrences in sorted(relevant.items()))

    issue_kinds = {item.issue for item in source_issues}
    unsupported = {
        ShareBasisSourceIssue.UNSUPPORTED_DOCUMENT_INVENTORY,
        ShareBasisSourceIssue.UNSUPPORTED_DOCUMENT_REPRESENTATION,
        ShareBasisSourceIssue.MALFORMED_OR_AMBIGUOUS_TEXT,
        ShareBasisSourceIssue.SOURCE_SAFETY_BOUND_EXCEEDED,
        ShareBasisSourceIssue.AMBIGUOUS_RATIO_ORIENTATION,
        ShareBasisSourceIssue.AMBIGUOUS_ACTION_DATE,
        ShareBasisSourceIssue.INVALID_RATIO_TERMS,
        ShareBasisSourceIssue.UNINTERPRETED_BASIS_AFFECTING_LANGUAGE,
    }
    incomplete = {
        ShareBasisSourceIssue.D2B_REFERENCE_CLOSURE_INCOMPLETE,
        ShareBasisSourceIssue.MISSING_RELEVANT_FILING_CAPTURE,
    }
    if conflicts:
        status = ShareBasisSourceStatus.SOURCE_CONFLICT
    elif issue_kinds & unsupported:
        status = ShareBasisSourceStatus.UNSUPPORTED_SOURCE_PROFILE
    elif issue_kinds & incomplete:
        status = ShareBasisSourceStatus.INCOMPLETE_SHARE_BASIS_SOURCE_SET
    else:
        status = ShareBasisSourceStatus.CAPTURED_SHARE_BASIS_SOURCE_SET
    sort_key = lambda item: (item.issue.value, item.accession or "",
                             item.filing_receipt_id or "", item.document_evidence_id or "",
                             item.exact_source_text or "")
    return SecShareBasisSourceAssessment(
        CONTRACT_VERSION, CLAIM_PROFILE_VERSION, DOCUMENT_PROFILE_VERSION,
        inventory.parent.cik, inventory, filing_universe,
        tuple(sorted(signals, key=lambda item: item.evidence_id)), claims,
        tuple(sorted(source_issues, key=sort_key)),
        tuple(sorted(conflicts, key=sort_key)), status, _LIMITATIONS)
