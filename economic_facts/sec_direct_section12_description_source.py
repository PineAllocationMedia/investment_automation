"""Identify narrow direct SEC Section-12 securities-description sources.

This is deterministic source identification over one freshly replayed D4D1
inventory.  It does not extract rights, establish a class/security identity,
resolve incorporation by reference, determine Item 202 completeness, or grant
Property-4/admission authority.
"""
from dataclasses import dataclass
from enum import StrEnum
from html.parser import HTMLParser
import re

from .sec_filing_archive import SecFilingArchive, canonical_json, digest
from .sec_filing_document_inventory import (
    SecFilingDocumentInventoryAssessment,
    SecFilingDocumentInventoryRequest,
    replay_sec_filing_document_inventory,
)

CONTRACT_VERSION = "2026-09-27-sec-direct-section12-description-source-v1"
REPRESENTATION_PROFILE_VERSION = "2026-09-27-sec-visible-text-profile-v1"
SUPPORTED_FORMS = frozenset(("10-K", "10-K/A"))

# Closed reviewed family.  EX-40, EX-4., EX-4.A.B, separators other than the
# one dot and bounded hyphens, and non-ASCII tokens are deliberately excluded.
_EX4_TYPE = re.compile(
    r"EX-4(?:\.[A-Za-z0-9]{1,16}(?:-[A-Za-z0-9]{1,16}){0,3})?",
    re.ASCII,
)
_RECEIPT_ID = re.compile(r"[0-9a-f]{64}", re.ASCII)
_ASCII_UPPER = str.maketrans("abcdefghijklmnopqrstuvwxyz", "ABCDEFGHIJKLMNOPQRSTUVWXYZ")


class SecDirectSection12DescriptionRequestError(ValueError):
    """Invalid explicit filing-receipt request or untyped public arguments."""


class SecDirectSection12DescriptionStatus(StrEnum):
    CAPTURED_DIRECT_SECTION12_DESCRIPTION_SOURCES = (
        "CAPTURED_DIRECT_SECTION12_DESCRIPTION_SOURCES"
    )
    NO_DIRECT_SUPPORTED_DESCRIPTION_SOURCE = "NO_DIRECT_SUPPORTED_DESCRIPTION_SOURCE"
    UNSUPPORTED_FILING_FORM = "UNSUPPORTED_FILING_FORM"
    UNSUPPORTED_DOCUMENT_REPRESENTATION = "UNSUPPORTED_DOCUMENT_REPRESENTATION"
    SOURCE_AMBIGUITY = "SOURCE_AMBIGUITY"


class SecDirectSection12DescriptionIssue(StrEnum):
    UNSUPPORTED_FILING_FORM = "UNSUPPORTED_FILING_FORM"
    UNSUPPORTED_DOCUMENT_REPRESENTATION = "UNSUPPORTED_DOCUMENT_REPRESENTATION"
    MALFORMED_OR_AMBIGUOUS_DOCUMENT = "MALFORMED_OR_AMBIGUOUS_DOCUMENT"


class SecDirectSection12DescriptionSourceStatus(StrEnum):
    IDENTIFIED_DIRECT_SECTION12_DESCRIPTION_SOURCE = (
        "IDENTIFIED_DIRECT_SECTION12_DESCRIPTION_SOURCE"
    )


class SecDocumentRepresentation(StrEnum):
    UTF8_HTML = "UTF8_HTML"
    UTF8_XHTML = "UTF8_XHTML"
    UTF8_TEXT = "UTF8_TEXT"


class HeadingAnchor(StrEnum):
    DESCRIPTION_OF_REGISTRANTS_SECURITIES = (
        "DESCRIPTION_OF_REGISTRANTS_SECURITIES"
    )
    DESCRIPTION_OF_THE_REGISTRANTS_SECURITIES = (
        "DESCRIPTION_OF_THE_REGISTRANTS_SECURITIES"
    )
    DESCRIPTION_OF_REGISTRANTS_SECURITIES_CURLY_APOSTROPHE = (
        "DESCRIPTION_OF_REGISTRANTS_SECURITIES_CURLY_APOSTROPHE"
    )
    DESCRIPTION_OF_THE_REGISTRANTS_SECURITIES_CURLY_APOSTROPHE = (
        "DESCRIPTION_OF_THE_REGISTRANTS_SECURITIES_CURLY_APOSTROPHE"
    )


class Section12Anchor(StrEnum):
    REGISTERED_PURSUANT_TO_SECTION_12 = "REGISTERED_PURSUANT_TO_SECTION_12"
    REGISTERED_PURSUANT_TO_SECTION_12_B = "REGISTERED_PURSUANT_TO_SECTION_12_B"


_HEADING_ANCHORS = (
    (HeadingAnchor.DESCRIPTION_OF_REGISTRANTS_SECURITIES,
     "DESCRIPTION OF REGISTRANT'S SECURITIES"),
    (HeadingAnchor.DESCRIPTION_OF_THE_REGISTRANTS_SECURITIES,
     "DESCRIPTION OF THE REGISTRANT'S SECURITIES"),
    (HeadingAnchor.DESCRIPTION_OF_REGISTRANTS_SECURITIES_CURLY_APOSTROPHE,
     "DESCRIPTION OF REGISTRANT’S SECURITIES"),
    (HeadingAnchor.DESCRIPTION_OF_THE_REGISTRANTS_SECURITIES_CURLY_APOSTROPHE,
     "DESCRIPTION OF THE REGISTRANT’S SECURITIES"),
)
_SECTION12_ANCHORS = (
    (Section12Anchor.REGISTERED_PURSUANT_TO_SECTION_12,
     "REGISTERED PURSUANT TO SECTION 12 OF THE SECURITIES EXCHANGE ACT OF 1934"),
    (Section12Anchor.REGISTERED_PURSUANT_TO_SECTION_12_B,
     "REGISTERED PURSUANT TO SECTION 12(B) OF THE SECURITIES EXCHANGE ACT OF 1934"),
)


def _identity(domain, value):
    return digest(("pam:sec-direct-section12-description:" + domain + ":v1\0").encode(
        "ascii") + canonical_json(value))


@dataclass(frozen=True, slots=True)
class SecDirectSection12DescriptionRequest:
    filing_receipt_id: str

    def __post_init__(self):
        if (type(self.filing_receipt_id) is not str
                or _RECEIPT_ID.fullmatch(self.filing_receipt_id) is None):
            raise SecDirectSection12DescriptionRequestError(
                "Exact filing receipt ID required")


@dataclass(frozen=True, slots=True)
class SecDirectSection12DescriptionSource:
    filing_receipt_id: str
    cik: str
    accession: str
    filing_form: str
    document_semantic_id: str
    document_evidence_id: str
    document_ordinal: int
    document_type: str
    sequence: str
    filename: str
    description: str | None
    payload_byte_start: int
    payload_byte_length: int
    payload_sha256: str
    representation: SecDocumentRepresentation
    representation_profile_version: str
    visible_text_sha256: str
    normalized_match_text_sha256: str
    matched_heading_anchors: tuple[HeadingAnchor, ...]
    matched_section12_anchors: tuple[Section12Anchor, ...]
    source_status: SecDirectSection12DescriptionSourceStatus
    issues: tuple[SecDirectSection12DescriptionIssue, ...]

    @property
    def semantic_id(self):
        return _identity("candidate-semantics", {
            "contract": CONTRACT_VERSION,
            "filing": (self.cik, self.accession, self.filing_form),
            "document_semantic_id": self.document_semantic_id,
            "representation": self.representation,
            "representation_profile": self.representation_profile_version,
            "heading_anchors": self.matched_heading_anchors,
            "section12_anchors": self.matched_section12_anchors,
            "source_status": self.source_status,
            "issues": self.issues,
        })

    @property
    def evidence_id(self):
        return _identity("candidate-evidence", {
            "semantic_id": self.semantic_id,
            "document_evidence_id": self.document_evidence_id,
            "filing_receipt_id": self.filing_receipt_id,
            "payload": (self.payload_byte_start, self.payload_byte_length,
                        self.payload_sha256),
            "visible_text_sha256": self.visible_text_sha256,
            "normalized_match_text_sha256": self.normalized_match_text_sha256,
        })


@dataclass(frozen=True, slots=True)
class SecDirectSection12DescriptionAssessment:
    contract_version: str
    inventory: SecFilingDocumentInventoryAssessment
    filing_form: str
    candidates: tuple[SecDirectSection12DescriptionSource, ...]
    status: SecDirectSection12DescriptionStatus
    issues: tuple[SecDirectSection12DescriptionIssue, ...]

    @property
    def semantic_id(self):
        return _identity("assessment-semantics", {
            "contract": self.contract_version,
            "filing_form": self.filing_form,
            "inventory_semantic_id": self.inventory.semantic_id,
            "candidates": [candidate.semantic_id for candidate in self.candidates],
            "status": self.status,
            "issues": self.issues,
        })

    @property
    def evidence_id(self):
        return _identity("assessment-evidence", {
            "semantic_id": self.semantic_id,
            "inventory_evidence_id": self.inventory.evidence_id,
            "candidates": [candidate.evidence_id for candidate in self.candidates],
        })


class _UnsupportedRepresentation(ValueError):
    pass


class _SourceAmbiguity(ValueError):
    pass


_VOID_TAGS = frozenset((
    "area", "base", "br", "col", "embed", "hr", "img", "input", "link",
    "meta", "param", "source", "track", "wbr",
))
_EXCLUDED_TAGS = frozenset((
    "head", "script", "style", "noscript", "template", "svg", "math", "canvas",
))
_LAYOUT_BREAK_TAGS = frozenset((
    "address", "article", "aside", "blockquote", "br", "caption", "dd", "div",
    "dl", "dt", "fieldset", "figcaption", "figure", "footer", "form", "h1",
    "h2", "h3", "h4", "h5", "h6", "header", "hr", "li", "main", "nav",
    "ol", "p", "pre", "section", "table", "tbody", "td", "tfoot", "th",
    "thead", "tr", "ul",
))


class _StrictVisibleHTMLParser(HTMLParser):
    """Small balanced-document profile; not a browser or repair parser."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack = []
        self.text = []
        self.seen_root = False
        self.closed_root = False
        self.seen_body = False
        self.in_body = False
        self.xhtml = False
        self.seen_declaration = False

    def _fail(self):
        raise _SourceAmbiguity("Malformed or ambiguous HTML/XHTML")

    def _append_layout_space(self, tag, excluded):
        if self.in_body and not excluded and tag in _LAYOUT_BREAK_TAGS:
            self.text.append(" ")

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
        declaration = data[:-1].strip() if data.endswith("?") else data.strip()
        if re.fullmatch(
                r"xml\s+version=(?:'1\.0'|\"1\.0\")(?:\s+encoding=(?:'UTF-8'|\"UTF-8\"))?",
                declaration, re.IGNORECASE) is None:
            self._fail()
        self.seen_declaration = True

    def handle_starttag(self, tag, attrs):
        if self.closed_root or ":" in tag:
            self._fail()
        names = [name for name, _ in attrs]
        if len(names) != len(set(names)):
            self._fail()
        if not self.seen_root:
            if tag != "html" or self.stack:
                self._fail()
            self.seen_root = True
            namespace = dict(attrs).get("xmlns")
            if namespace not in (None, "http://www.w3.org/1999/xhtml"):
                self._fail()
            self.xhtml = namespace is not None
        elif not self.stack:
            self._fail()
        if tag == "body":
            if self.seen_body or len(self.stack) != 1 or self.stack[0][0] != "html":
                self._fail()
            self.seen_body = True
            self.in_body = True
        inherited = self.stack[-1][1] if self.stack else False
        excluded = inherited or tag in _EXCLUDED_TAGS
        self._append_layout_space(tag, excluded)
        if tag not in _VOID_TAGS:
            self.stack.append((tag, excluded))

    def handle_startendtag(self, tag, attrs):
        if tag not in _VOID_TAGS:
            self._fail()
        self.handle_starttag(tag, attrs)

    def handle_endtag(self, tag):
        if tag in _VOID_TAGS or not self.stack or self.stack[-1][0] != tag:
            self._fail()
        _, excluded = self.stack.pop()
        self._append_layout_space(tag, excluded)
        if tag == "body":
            self.in_body = False
        if tag == "html":
            if self.stack or not self.seen_body:
                self._fail()
            self.closed_root = True

    def handle_data(self, data):
        excluded = self.stack[-1][1] if self.stack else False
        if self.in_body and not excluded:
            self.text.append(data)
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


def _decode_utf8(payload):
    if payload.startswith((b"%PDF-", b"PK\x03\x04", b"\xd0\xcf\x11\xe0", b"{\\rtf")):
        raise _UnsupportedRepresentation("Binary/document container unsupported")
    try:
        text = payload.decode("utf-8-sig")
    except UnicodeError:
        raise _UnsupportedRepresentation("Only UTF-8/ASCII source supported") from None
    if any((ord(character) < 32 and character not in "\t\n\r")
           or 127 <= ord(character) <= 159 for character in text):
        raise _UnsupportedRepresentation("Binary/control content unsupported")
    return text


def _extract_visible_text(payload):
    text = _decode_utf8(payload)
    if "<" not in text and ">" not in text:
        return SecDocumentRepresentation.UTF8_TEXT, text
    parser = _StrictVisibleHTMLParser()
    try:
        parser.feed(text)
        parser.close()
    except _SourceAmbiguity:
        raise
    except (TypeError, ValueError):
        raise _SourceAmbiguity("Malformed or ambiguous HTML/XHTML") from None
    representation = (SecDocumentRepresentation.UTF8_XHTML if parser.xhtml
                      else SecDocumentRepresentation.UTF8_HTML)
    return representation, "".join(parser.text)


def _normalize_for_matching(text):
    # No Unicode normalization, punctuation removal, stemming, or word reordering.
    return re.sub(r"\s+", " ", text).strip().translate(_ASCII_UPPER)


def _contains_exact_phrase(text, phrase):
    start = 0
    while True:
        position = text.find(phrase, start)
        if position < 0:
            return False
        before = text[position - 1] if position else ""
        end = position + len(phrase)
        after = text[end] if end < len(text) else ""
        if (not before or not before.isascii() or not before.isalnum()) and (
                not after or not after.isascii() or not after.isalnum()):
            return True
        start = position + 1


def _candidate(inventory, document, representation, visible_text,
               normalized_text, headings, sections):
    return SecDirectSection12DescriptionSource(
        inventory.receipt.receipt_id,
        inventory.cik,
        inventory.accession,
        inventory.form,
        document.semantic_id,
        document.evidence_id,
        document.document_ordinal,
        document.document_type,
        document.sequence,
        document.filename,
        document.description,
        document.byte_start,
        document.byte_length,
        document.content_sha256,
        representation,
        REPRESENTATION_PROFILE_VERSION,
        digest(visible_text.encode("utf-8")),
        digest(normalized_text.encode("utf-8")),
        headings,
        sections,
        SecDirectSection12DescriptionSourceStatus.IDENTIFIED_DIRECT_SECTION12_DESCRIPTION_SOURCE,
        (),
    )


def identify_sec_direct_section12_description_sources(
    archive: SecFilingArchive,
    request: SecDirectSection12DescriptionRequest,
) -> SecDirectSection12DescriptionAssessment:
    """Freshly replay D4D1 and identify only direct, narrow annual sources."""
    if (type(archive) is not SecFilingArchive
            or type(request) is not SecDirectSection12DescriptionRequest):
        raise SecDirectSection12DescriptionRequestError(
            "Exact typed archive/request required")

    inventory = replay_sec_filing_document_inventory(
        archive, SecFilingDocumentInventoryRequest(request.filing_receipt_id))
    if inventory.form not in SUPPORTED_FORMS:
        return SecDirectSection12DescriptionAssessment(
            CONTRACT_VERSION, inventory, inventory.form, (),
            SecDirectSection12DescriptionStatus.UNSUPPORTED_FILING_FORM,
            (SecDirectSection12DescriptionIssue.UNSUPPORTED_FILING_FORM,),
        )

    raw = archive.read_object(inventory.receipt)
    candidates = []
    issues = set()
    for document in inventory.documents:
        if _EX4_TYPE.fullmatch(document.document_type) is None:
            continue
        payload = raw[document.byte_start:document.byte_start + document.byte_length]
        # D4D1's digest is the authoritative slice check.  This assertion catches
        # programming drift without inventing a second archive trust contract.
        if len(payload) != document.byte_length or digest(payload) != document.content_sha256:
            raise AssertionError("D4D1 document provenance mismatch")
        try:
            representation, visible_text = _extract_visible_text(payload)
        except _UnsupportedRepresentation:
            issues.add(SecDirectSection12DescriptionIssue.UNSUPPORTED_DOCUMENT_REPRESENTATION)
            continue
        except _SourceAmbiguity:
            issues.add(SecDirectSection12DescriptionIssue.MALFORMED_OR_AMBIGUOUS_DOCUMENT)
            continue
        normalized = _normalize_for_matching(visible_text)
        headings = tuple(anchor for anchor, phrase in _HEADING_ANCHORS
                         if _contains_exact_phrase(normalized, phrase))
        sections = tuple(anchor for anchor, phrase in _SECTION12_ANCHORS
                         if _contains_exact_phrase(normalized, phrase))
        if headings and sections:
            candidates.append(_candidate(
                inventory, document, representation, visible_text,
                normalized, headings, sections))

    ordered_issues = tuple(sorted(issues))
    if SecDirectSection12DescriptionIssue.MALFORMED_OR_AMBIGUOUS_DOCUMENT in issues:
        status = SecDirectSection12DescriptionStatus.SOURCE_AMBIGUITY
    elif SecDirectSection12DescriptionIssue.UNSUPPORTED_DOCUMENT_REPRESENTATION in issues:
        status = SecDirectSection12DescriptionStatus.UNSUPPORTED_DOCUMENT_REPRESENTATION
    elif candidates:
        status = SecDirectSection12DescriptionStatus.CAPTURED_DIRECT_SECTION12_DESCRIPTION_SOURCES
    else:
        status = SecDirectSection12DescriptionStatus.NO_DIRECT_SUPPORTED_DESCRIPTION_SOURCE
    return SecDirectSection12DescriptionAssessment(
        CONTRACT_VERSION, inventory, inventory.form, tuple(candidates), status,
        ordered_issues)
