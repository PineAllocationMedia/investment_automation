"""Extract narrow class-scoped Section-12 rights-topic source passages.

This downstream D4D2B layer freshly replays D4D2A, independently parses the
exact eligible document payloads, and preserves exact visible blocks under a
closed COMMON STOCK source-heading profile.  Topics classify source passages;
they are not interpreted legal rights, durable class identities, completeness,
Property-4 qualification, or admission.
"""
from dataclasses import dataclass
from enum import StrEnum
from html.parser import HTMLParser
import re

from .sec_direct_section12_description_source import (
    SecDirectSection12DescriptionAssessment,
    SecDirectSection12DescriptionRequest,
    SecDirectSection12DescriptionStatus,
    SecDocumentRepresentation,
    identify_sec_direct_section12_description_sources,
)
from .sec_filing_archive import SecFilingArchive, canonical_json, digest


CONTRACT_VERSION = "2026-09-27-sec-section12-rights-source-claims-v1"
BLOCK_PROFILE_VERSION = "2026-09-27-sec-rights-visible-block-profile-v1"
CLASS_SCOPE_PROFILE_VERSION = "2026-09-27-sec-common-stock-source-scope-v1"
TOPIC_PROFILE_VERSION = "2026-09-27-sec-capital-stock-rights-topics-v1"

MAX_ELEMENTS = 100_000
MAX_BLOCKS = 25_000
MAX_BLOCK_CHARACTERS = 16_384
MAX_VISIBLE_CHARACTERS = 2_000_000

_RECEIPT_ID = re.compile(r"[0-9a-f]{64}", re.ASCII)
_CLASS_TOKEN = r"[A-Z0-9]"
_COMMON_CLASS_HEADING = re.compile(
    r"(?:COMMON STOCK|CLASS " + _CLASS_TOKEN + r" COMMON STOCK)", re.ASCII)
_MALFORMED_COMMON_CLASS_HEADING = re.compile(r"CLASS .+ COMMON STOCK", re.ASCII)
_BOUNDARY_HEADINGS = (
    re.compile(r"PREFERRED STOCK", re.ASCII),
    re.compile(r"CLASS " + _CLASS_TOKEN + r" PREFERRED STOCK", re.ASCII),
    re.compile(r"DEBT SECURITIES", re.ASCII),
    re.compile(r"WARRANTS", re.ASCII),
    re.compile(r"DEPOSITARY SHARES", re.ASCII),
)
_ASCII_UPPER = str.maketrans("abcdefghijklmnopqrstuvwxyz", "ABCDEFGHIJKLMNOPQRSTUVWXYZ")


class SecSection12RightsSourceClaimsRequestError(ValueError):
    """Invalid explicit receipt request or untyped public arguments."""


class SecSection12RightsSourceClaimsStatus(StrEnum):
    CAPTURED_SECTION12_RIGHTS_SOURCE_CLAIMS = (
        "CAPTURED_SECTION12_RIGHTS_SOURCE_CLAIMS"
    )
    NO_SUPPORTED_COMMON_STOCK_SCOPE = "NO_SUPPORTED_COMMON_STOCK_SCOPE"
    NO_SUPPORTED_RIGHTS_SOURCE_CLAIMS = "NO_SUPPORTED_RIGHTS_SOURCE_CLAIMS"
    UNSUPPORTED_RIGHTS_EXTRACTION_PROFILE = (
        "UNSUPPORTED_RIGHTS_EXTRACTION_PROFILE"
    )
    SOURCE_AMBIGUITY = "SOURCE_AMBIGUITY"
    UPSTREAM_DIRECT_SOURCE_UNAVAILABLE = "UPSTREAM_DIRECT_SOURCE_UNAVAILABLE"


class SecSection12RightsSourceIssue(StrEnum):
    UPSTREAM_NO_DIRECT_SUPPORTED_DESCRIPTION_SOURCE = (
        "UPSTREAM_NO_DIRECT_SUPPORTED_DESCRIPTION_SOURCE"
    )
    UPSTREAM_SOURCE_AMBIGUITY = "UPSTREAM_SOURCE_AMBIGUITY"
    UPSTREAM_UNSUPPORTED_DOCUMENT_REPRESENTATION = (
        "UPSTREAM_UNSUPPORTED_DOCUMENT_REPRESENTATION"
    )
    UPSTREAM_UNSUPPORTED_FILING_FORM = "UPSTREAM_UNSUPPORTED_FILING_FORM"
    UNSUPPORTED_RIGHTS_EXTRACTION_REPRESENTATION = (
        "UNSUPPORTED_RIGHTS_EXTRACTION_REPRESENTATION"
    )
    MALFORMED_OR_AMBIGUOUS_BLOCK_STRUCTURE = (
        "MALFORMED_OR_AMBIGUOUS_BLOCK_STRUCTURE"
    )
    UNSUPPORTED_COMMON_STOCK_HEADING_STRUCTURE = (
        "UNSUPPORTED_COMMON_STOCK_HEADING_STRUCTURE"
    )
    SOURCE_SAFETY_BOUND_EXCEEDED = "SOURCE_SAFETY_BOUND_EXCEEDED"


class SecSection12RightsSourceTopic(StrEnum):
    DIVIDEND = "DIVIDEND"
    VOTING = "VOTING"
    LIQUIDATION = "LIQUIDATION"
    FURTHER_CALLS_OR_ASSESSMENTS = "FURTHER_CALLS_OR_ASSESSMENTS"
    PREEMPTIVE = "PREEMPTIVE"
    CONVERSION = "CONVERSION"
    REDEMPTION = "REDEMPTION"
    SINKING_FUND = "SINKING_FUND"


class SecSection12RightsTopicAnchor(StrEnum):
    DIVIDEND = "DIVIDEND"
    DIVIDENDS = "DIVIDENDS"
    VOTING = "VOTING"
    VOTE = "VOTE"
    VOTES = "VOTES"
    LIQUIDATION = "LIQUIDATION"
    DISSOLUTION = "DISSOLUTION"
    WINDING_UP = "WINDING_UP"
    WINDING_HYPHEN_UP = "WINDING_HYPHEN_UP"
    FURTHER_CALLS = "FURTHER_CALLS"
    ASSESSMENT = "ASSESSMENT"
    ASSESSMENTS = "ASSESSMENTS"
    NONASSESSABLE = "NONASSESSABLE"
    NON_HYPHEN_ASSESSABLE = "NON_HYPHEN_ASSESSABLE"
    PREEMPTIVE = "PREEMPTIVE"
    PRE_HYPHEN_EMPTIVE = "PRE_HYPHEN_EMPTIVE"
    CONVERSION = "CONVERSION"
    CONVERT = "CONVERT"
    CONVERTIBLE = "CONVERTIBLE"
    REDEMPTION = "REDEMPTION"
    REDEEM = "REDEEM"
    REDEEMABLE = "REDEEMABLE"
    SINKING_FUND = "SINKING_FUND"


_TOPIC_ANCHORS = (
    (SecSection12RightsTopicAnchor.DIVIDEND,
     SecSection12RightsSourceTopic.DIVIDEND, "DIVIDEND"),
    (SecSection12RightsTopicAnchor.DIVIDENDS,
     SecSection12RightsSourceTopic.DIVIDEND, "DIVIDENDS"),
    (SecSection12RightsTopicAnchor.VOTING,
     SecSection12RightsSourceTopic.VOTING, "VOTING"),
    (SecSection12RightsTopicAnchor.VOTE,
     SecSection12RightsSourceTopic.VOTING, "VOTE"),
    (SecSection12RightsTopicAnchor.VOTES,
     SecSection12RightsSourceTopic.VOTING, "VOTES"),
    (SecSection12RightsTopicAnchor.LIQUIDATION,
     SecSection12RightsSourceTopic.LIQUIDATION, "LIQUIDATION"),
    (SecSection12RightsTopicAnchor.DISSOLUTION,
     SecSection12RightsSourceTopic.LIQUIDATION, "DISSOLUTION"),
    (SecSection12RightsTopicAnchor.WINDING_UP,
     SecSection12RightsSourceTopic.LIQUIDATION, "WINDING UP"),
    (SecSection12RightsTopicAnchor.WINDING_HYPHEN_UP,
     SecSection12RightsSourceTopic.LIQUIDATION, "WINDING-UP"),
    (SecSection12RightsTopicAnchor.FURTHER_CALLS,
     SecSection12RightsSourceTopic.FURTHER_CALLS_OR_ASSESSMENTS, "FURTHER CALLS"),
    (SecSection12RightsTopicAnchor.ASSESSMENT,
     SecSection12RightsSourceTopic.FURTHER_CALLS_OR_ASSESSMENTS, "ASSESSMENT"),
    (SecSection12RightsTopicAnchor.ASSESSMENTS,
     SecSection12RightsSourceTopic.FURTHER_CALLS_OR_ASSESSMENTS, "ASSESSMENTS"),
    (SecSection12RightsTopicAnchor.NONASSESSABLE,
     SecSection12RightsSourceTopic.FURTHER_CALLS_OR_ASSESSMENTS, "NONASSESSABLE"),
    (SecSection12RightsTopicAnchor.NON_HYPHEN_ASSESSABLE,
     SecSection12RightsSourceTopic.FURTHER_CALLS_OR_ASSESSMENTS, "NON-ASSESSABLE"),
    (SecSection12RightsTopicAnchor.PREEMPTIVE,
     SecSection12RightsSourceTopic.PREEMPTIVE, "PREEMPTIVE"),
    (SecSection12RightsTopicAnchor.PRE_HYPHEN_EMPTIVE,
     SecSection12RightsSourceTopic.PREEMPTIVE, "PRE-EMPTIVE"),
    (SecSection12RightsTopicAnchor.CONVERSION,
     SecSection12RightsSourceTopic.CONVERSION, "CONVERSION"),
    (SecSection12RightsTopicAnchor.CONVERT,
     SecSection12RightsSourceTopic.CONVERSION, "CONVERT"),
    (SecSection12RightsTopicAnchor.CONVERTIBLE,
     SecSection12RightsSourceTopic.CONVERSION, "CONVERTIBLE"),
    (SecSection12RightsTopicAnchor.REDEMPTION,
     SecSection12RightsSourceTopic.REDEMPTION, "REDEMPTION"),
    (SecSection12RightsTopicAnchor.REDEEM,
     SecSection12RightsSourceTopic.REDEMPTION, "REDEEM"),
    (SecSection12RightsTopicAnchor.REDEEMABLE,
     SecSection12RightsSourceTopic.REDEMPTION, "REDEEMABLE"),
    (SecSection12RightsTopicAnchor.SINKING_FUND,
     SecSection12RightsSourceTopic.SINKING_FUND, "SINKING FUND"),
)


def _identity(domain, value):
    return digest(("pam:sec-section12-rights-source-claims:" + domain + ":v1\0").encode(
        "ascii") + canonical_json(value))


@dataclass(frozen=True, slots=True)
class SecSection12RightsSourceClaimsRequest:
    filing_receipt_id: str

    def __post_init__(self):
        if (type(self.filing_receipt_id) is not str
                or _RECEIPT_ID.fullmatch(self.filing_receipt_id) is None):
            raise SecSection12RightsSourceClaimsRequestError(
                "Exact filing receipt ID required")


@dataclass(frozen=True, slots=True)
class SecSection12RightsSourceIssueOccurrence:
    document_semantic_id: str
    document_evidence_id: str
    issue: SecSection12RightsSourceIssue


@dataclass(frozen=True, slots=True)
class SecSection12SourceClassScope:
    document_semantic_id: str
    document_evidence_id: str
    exact_class_heading: str
    normalized_class_heading: str
    class_heading_block_ordinal: int
    first_body_block_ordinal: int | None
    final_body_block_ordinal: int | None
    body_block_ordinals: tuple[int, ...]
    ordered_block_content_sha256s: tuple[str, ...]
    passage_semantic_ids: tuple[str, ...]
    issues: tuple[SecSection12RightsSourceIssue, ...]

    @property
    def semantic_id(self):
        return _identity("class-scope-semantics", {
            "contract": CONTRACT_VERSION,
            "block_profile": BLOCK_PROFILE_VERSION,
            "class_scope_profile": CLASS_SCOPE_PROFILE_VERSION,
            "document_semantic_id": self.document_semantic_id,
            "exact_class_heading": self.exact_class_heading,
            "normalized_class_heading": self.normalized_class_heading,
            "heading_block_ordinal": self.class_heading_block_ordinal,
            "body_block_ordinals": self.body_block_ordinals,
            "ordered_block_content_sha256s": self.ordered_block_content_sha256s,
            "issues": self.issues,
        })

    @property
    def source_class_scope_id(self):
        """Document-local source scope only; never a durable class identity."""
        return self.semantic_id

    @property
    def evidence_id(self):
        return _identity("class-scope-evidence", {
            "semantic_id": self.semantic_id,
            "document_evidence_id": self.document_evidence_id,
        })


@dataclass(frozen=True, slots=True)
class SecSection12RightsSourcePassage:
    document_semantic_id: str
    document_evidence_id: str
    source_class_scope_id: str
    source_class_heading: str
    block_ordinal: int
    structural_element_kind: str
    exact_source_text: str
    source_text_sha256: str
    matched_topics: tuple[SecSection12RightsSourceTopic, ...]
    matched_topic_anchor_ids: tuple[SecSection12RightsTopicAnchor, ...]
    issues: tuple[SecSection12RightsSourceIssue, ...]

    @property
    def semantic_id(self):
        return _identity("passage-semantics", {
            "contract": CONTRACT_VERSION,
            "topic_profile": TOPIC_PROFILE_VERSION,
            "source_class_scope_id": self.source_class_scope_id,
            "block_ordinal": self.block_ordinal,
            "structural_element_kind": self.structural_element_kind,
            "source_text_sha256": self.source_text_sha256,
            "matched_topics": self.matched_topics,
            "matched_topic_anchor_ids": self.matched_topic_anchor_ids,
            "issues": self.issues,
        })

    @property
    def evidence_id(self):
        return _identity("passage-evidence", {
            "semantic_id": self.semantic_id,
            "document_evidence_id": self.document_evidence_id,
            "exact_source_text": self.exact_source_text,
        })


@dataclass(frozen=True, slots=True)
class SecSection12RightsSourceClaimsAssessment:
    contract_version: str
    upstream_assessment: SecDirectSection12DescriptionAssessment
    class_scopes: tuple[SecSection12SourceClassScope, ...]
    passages: tuple[SecSection12RightsSourcePassage, ...]
    source_issues: tuple[SecSection12RightsSourceIssueOccurrence, ...]
    status: SecSection12RightsSourceClaimsStatus
    issues: tuple[SecSection12RightsSourceIssue, ...]

    @property
    def semantic_id(self):
        return _identity("assessment-semantics", {
            "contract": self.contract_version,
            "upstream_semantic_id": self.upstream_assessment.semantic_id,
            "class_scopes": [scope.semantic_id for scope in self.class_scopes],
            "passages": [passage.semantic_id for passage in self.passages],
            "source_issues": [
                (item.document_semantic_id, item.issue) for item in self.source_issues
            ],
            "status": self.status,
            "issues": self.issues,
        })

    @property
    def evidence_id(self):
        return _identity("assessment-evidence", {
            "semantic_id": self.semantic_id,
            "upstream_evidence_id": self.upstream_assessment.evidence_id,
            "class_scopes": [scope.evidence_id for scope in self.class_scopes],
            "passages": [passage.evidence_id for passage in self.passages],
            "source_issues": [
                (item.document_evidence_id, item.issue) for item in self.source_issues
            ],
        })


@dataclass(frozen=True, slots=True)
class _VisibleBlock:
    ordinal: int
    structural_element_kind: str
    exact_text: str

    @property
    def text_sha256(self):
        return digest(self.exact_text.encode("utf-8"))


class _BlockAmbiguity(ValueError):
    def __init__(self, issue=SecSection12RightsSourceIssue.MALFORMED_OR_AMBIGUOUS_BLOCK_STRUCTURE):
        self.issue = issue
        super().__init__(issue.value)


_VOID_TAGS = frozenset((
    "area", "base", "br", "col", "embed", "hr", "img", "input", "link",
    "meta", "param", "source", "track", "wbr",
))
_EXCLUDED_TAGS = frozenset((
    "head", "script", "style", "noscript", "template", "svg", "math", "canvas",
))
_BLOCK_TAGS = frozenset((
    "h1", "h2", "h3", "h4", "h5", "h6", "p", "li", "td", "th",
    "caption", "blockquote", "div", "section", "article",
))
_ATOMIC_BLOCK_TAGS = frozenset(("h1", "h2", "h3", "h4", "h5", "h6", "p", "caption"))


class _StrictVisibleBlockParser(HTMLParser):
    """Balanced bounded HTML/XHTML block parser, never browser repair."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack = []
        self.blocks = []
        self.seen_root = False
        self.closed_root = False
        self.seen_body = False
        self.in_body = False
        self.xhtml = False
        self.seen_declaration = False
        self.element_count = 0
        self.visible_character_count = 0

    def _fail(self, issue=SecSection12RightsSourceIssue.MALFORMED_OR_AMBIGUOUS_BLOCK_STRUCTURE):
        raise _BlockAmbiguity(issue)

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
        self.element_count += 1
        if self.element_count > MAX_ELEMENTS:
            self._fail(SecSection12RightsSourceIssue.SOURCE_SAFETY_BOUND_EXCEEDED)
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
            if self.seen_body or len(self.stack) != 1 or self.stack[0]["tag"] != "html":
                self._fail()
            self.seen_body = True
            self.in_body = True
        inherited = self.stack[-1]["excluded"] if self.stack else False
        excluded = inherited or tag in _EXCLUDED_TAGS
        active_blocks = [frame for frame in self.stack if frame["parts"] is not None]
        if self.in_body and not excluded and tag in {"br", "hr"} and active_blocks:
            for frame in active_blocks:
                frame["parts"].append(" ")
            active_blocks[-1]["own_parts"].append(" ")
        is_block = self.in_body and not excluded and tag in _BLOCK_TAGS
        if is_block:
            if active_blocks and active_blocks[-1]["tag"] in _ATOMIC_BLOCK_TAGS:
                self._fail()
            for frame in active_blocks:
                frame["nested_block"] = True
        if tag not in _VOID_TAGS:
            self.stack.append({
                "tag": tag,
                "excluded": excluded,
                "parts": [] if is_block else None,
                "own_parts": [] if is_block else None,
                "nested_block": False,
            })

    def handle_startendtag(self, tag, attrs):
        if tag not in _VOID_TAGS:
            self._fail()
        self.handle_starttag(tag, attrs)

    def handle_endtag(self, tag):
        if tag in _VOID_TAGS or not self.stack or self.stack[-1]["tag"] != tag:
            self._fail()
        frame = self.stack.pop()
        if frame["parts"] is not None:
            exact_text = "".join(frame["parts"])
            own_text = "".join(frame["own_parts"])
            if frame["nested_block"]:
                if own_text.strip():
                    self._fail()
            elif exact_text.strip():
                if len(exact_text) > MAX_BLOCK_CHARACTERS or len(self.blocks) >= MAX_BLOCKS:
                    self._fail(SecSection12RightsSourceIssue.SOURCE_SAFETY_BOUND_EXCEEDED)
                self.blocks.append(_VisibleBlock(
                    len(self.blocks), frame["tag"], exact_text))
        if tag == "body":
            self.in_body = False
        if tag == "html":
            if self.stack or not self.seen_body:
                self._fail()
            self.closed_root = True

    def handle_data(self, data):
        excluded = self.stack[-1]["excluded"] if self.stack else False
        if self.in_body and not excluded:
            self.visible_character_count += len(data)
            if self.visible_character_count > MAX_VISIBLE_CHARACTERS:
                self._fail(SecSection12RightsSourceIssue.SOURCE_SAFETY_BOUND_EXCEEDED)
            active_blocks = [frame for frame in self.stack if frame["parts"] is not None]
            if not active_blocks:
                if data.strip():
                    self._fail()
                return
            for frame in active_blocks:
                frame["parts"].append(data)
            active_blocks[-1]["own_parts"].append(data)
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


def _normalize_for_matching(text):
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


def _blocks_from_payload(payload):
    try:
        text = payload.decode("utf-8-sig")
    except UnicodeError:
        raise _BlockAmbiguity(
            SecSection12RightsSourceIssue.UNSUPPORTED_RIGHTS_EXTRACTION_REPRESENTATION
        ) from None
    if any((ord(character) < 32 and character not in "\t\n\r")
           or 127 <= ord(character) <= 159 for character in text):
        raise _BlockAmbiguity(
            SecSection12RightsSourceIssue.UNSUPPORTED_RIGHTS_EXTRACTION_REPRESENTATION)
    parser = _StrictVisibleBlockParser()
    try:
        parser.feed(text)
        parser.close()
    except _BlockAmbiguity:
        raise
    except (TypeError, ValueError):
        raise _BlockAmbiguity() from None
    representation = (SecDocumentRepresentation.UTF8_XHTML if parser.xhtml
                      else SecDocumentRepresentation.UTF8_HTML)
    return representation, tuple(parser.blocks)


def _is_boundary(normalized):
    return (_COMMON_CLASS_HEADING.fullmatch(normalized) is not None
            or any(pattern.fullmatch(normalized) for pattern in _BOUNDARY_HEADINGS))


def _matched_anchors(normalized):
    return tuple((anchor, topic) for anchor, topic, phrase in _TOPIC_ANCHORS
                 if _contains_exact_phrase(normalized, phrase))


def _scope_and_passages(candidate, blocks):
    headings = []
    for index, block in enumerate(blocks):
        normalized = _normalize_for_matching(block.exact_text)
        if _COMMON_CLASS_HEADING.fullmatch(normalized):
            headings.append((index, block, normalized))
        elif _MALFORMED_COMMON_CLASS_HEADING.fullmatch(normalized):
            raise _BlockAmbiguity(
                SecSection12RightsSourceIssue.UNSUPPORTED_COMMON_STOCK_HEADING_STRUCTURE)

    scopes = []
    passages = []
    for heading_index, heading, normalized_heading in headings:
        end = len(blocks)
        for index in range(heading_index + 1, len(blocks)):
            if _is_boundary(_normalize_for_matching(blocks[index].exact_text)):
                end = index
                break
        body = blocks[heading_index + 1:end]
        scope_seed = _identity("class-scope-semantics", {
            "contract": CONTRACT_VERSION,
            "block_profile": BLOCK_PROFILE_VERSION,
            "class_scope_profile": CLASS_SCOPE_PROFILE_VERSION,
            "document_semantic_id": candidate.semantic_id,
            "exact_class_heading": heading.exact_text,
            "normalized_class_heading": normalized_heading,
            "heading_block_ordinal": heading.ordinal,
            "body_block_ordinals": tuple(item.ordinal for item in body),
            "ordered_block_content_sha256s": tuple(
                item.text_sha256 for item in (heading, *body)),
            "issues": (),
        })
        scope_passages = []
        for block in body:
            matches = _matched_anchors(_normalize_for_matching(block.exact_text))
            if not matches:
                continue
            anchors = tuple(anchor for anchor, _ in matches)
            topics = tuple(sorted({topic for _, topic in matches}, key=lambda item: item.value))
            passage = SecSection12RightsSourcePassage(
                candidate.semantic_id,
                candidate.evidence_id,
                scope_seed,
                heading.exact_text,
                block.ordinal,
                block.structural_element_kind,
                block.exact_text,
                block.text_sha256,
                topics,
                anchors,
                (),
            )
            scope_passages.append(passage)
            passages.append(passage)
        scopes.append(SecSection12SourceClassScope(
            candidate.semantic_id,
            candidate.evidence_id,
            heading.exact_text,
            normalized_heading,
            heading.ordinal,
            body[0].ordinal if body else None,
            body[-1].ordinal if body else None,
            tuple(item.ordinal for item in body),
            tuple(item.text_sha256 for item in (heading, *body)),
            tuple(item.semantic_id for item in scope_passages),
            (),
        ))
    return tuple(scopes), tuple(passages)


_UPSTREAM_ISSUES = {
    SecDirectSection12DescriptionStatus.NO_DIRECT_SUPPORTED_DESCRIPTION_SOURCE:
        SecSection12RightsSourceIssue.UPSTREAM_NO_DIRECT_SUPPORTED_DESCRIPTION_SOURCE,
    SecDirectSection12DescriptionStatus.SOURCE_AMBIGUITY:
        SecSection12RightsSourceIssue.UPSTREAM_SOURCE_AMBIGUITY,
    SecDirectSection12DescriptionStatus.UNSUPPORTED_DOCUMENT_REPRESENTATION:
        SecSection12RightsSourceIssue.UPSTREAM_UNSUPPORTED_DOCUMENT_REPRESENTATION,
    SecDirectSection12DescriptionStatus.UNSUPPORTED_FILING_FORM:
        SecSection12RightsSourceIssue.UPSTREAM_UNSUPPORTED_FILING_FORM,
}


def extract_sec_section12_rights_source_claims(
    archive: SecFilingArchive,
    request: SecSection12RightsSourceClaimsRequest,
) -> SecSection12RightsSourceClaimsAssessment:
    """Freshly replay D4D2A and extract exact source passages, without rights values."""
    if (type(archive) is not SecFilingArchive
            or type(request) is not SecSection12RightsSourceClaimsRequest):
        raise SecSection12RightsSourceClaimsRequestError(
            "Exact typed archive/request required")

    upstream = identify_sec_direct_section12_description_sources(
        archive, SecDirectSection12DescriptionRequest(request.filing_receipt_id))
    if upstream.status is not (
            SecDirectSection12DescriptionStatus.CAPTURED_DIRECT_SECTION12_DESCRIPTION_SOURCES):
        issue = _UPSTREAM_ISSUES[upstream.status]
        return SecSection12RightsSourceClaimsAssessment(
            CONTRACT_VERSION, upstream, (), (), (),
            SecSection12RightsSourceClaimsStatus.UPSTREAM_DIRECT_SOURCE_UNAVAILABLE,
            (issue,),
        )

    raw = archive.read_object(upstream.inventory.receipt)
    scopes = []
    passages = []
    source_issues = []
    for candidate in upstream.candidates:
        if candidate.representation is SecDocumentRepresentation.UTF8_TEXT:
            source_issues.append(SecSection12RightsSourceIssueOccurrence(
                candidate.semantic_id, candidate.evidence_id,
                SecSection12RightsSourceIssue.UNSUPPORTED_RIGHTS_EXTRACTION_REPRESENTATION))
            continue
        document = upstream.inventory.documents[candidate.document_ordinal]
        if (document.semantic_id != candidate.document_semantic_id
                or document.evidence_id != candidate.document_evidence_id
                or document.byte_start != candidate.payload_byte_start
                or document.byte_length != candidate.payload_byte_length
                or document.content_sha256 != candidate.payload_sha256):
            raise AssertionError("D4D2A/D4D1 document provenance mismatch")
        payload = raw[document.byte_start:document.byte_start + document.byte_length]
        if len(payload) != document.byte_length or digest(payload) != document.content_sha256:
            raise AssertionError("D4D1 document payload mismatch")
        try:
            representation, blocks = _blocks_from_payload(payload)
            if representation is not candidate.representation:
                raise AssertionError("D4D2A representation mismatch")
            source_scopes, source_passages = _scope_and_passages(candidate, blocks)
            scopes.extend(source_scopes)
            passages.extend(source_passages)
        except _BlockAmbiguity as error:
            source_issues.append(SecSection12RightsSourceIssueOccurrence(
                candidate.semantic_id, candidate.evidence_id, error.issue))

    issues = tuple(sorted({item.issue for item in source_issues}, key=lambda item: item.value))
    ambiguity_issues = {
        SecSection12RightsSourceIssue.MALFORMED_OR_AMBIGUOUS_BLOCK_STRUCTURE,
        SecSection12RightsSourceIssue.UNSUPPORTED_COMMON_STOCK_HEADING_STRUCTURE,
        SecSection12RightsSourceIssue.SOURCE_SAFETY_BOUND_EXCEEDED,
    }
    if ambiguity_issues.intersection(issues):
        status = SecSection12RightsSourceClaimsStatus.SOURCE_AMBIGUITY
    elif SecSection12RightsSourceIssue.UNSUPPORTED_RIGHTS_EXTRACTION_REPRESENTATION in issues:
        status = SecSection12RightsSourceClaimsStatus.UNSUPPORTED_RIGHTS_EXTRACTION_PROFILE
    elif passages:
        status = SecSection12RightsSourceClaimsStatus.CAPTURED_SECTION12_RIGHTS_SOURCE_CLAIMS
    elif not scopes:
        status = SecSection12RightsSourceClaimsStatus.NO_SUPPORTED_COMMON_STOCK_SCOPE
    else:
        status = SecSection12RightsSourceClaimsStatus.NO_SUPPORTED_RIGHTS_SOURCE_CLAIMS
    return SecSection12RightsSourceClaimsAssessment(
        CONTRACT_VERSION, upstream, tuple(scopes), tuple(passages),
        tuple(source_issues), status, issues)
