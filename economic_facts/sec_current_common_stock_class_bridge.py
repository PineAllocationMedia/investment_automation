"""Bridge one CURRENT D3A class claim to one same-filing D4D2B source scope.

This D4D3A adapter establishes only filing-local source correspondence.  It
freshly replays D4C2, D4D2B, and D3A and applies a closed common-stock title
grammar.  It never creates durable issuer/security/class identity, interprets
legal rights, proves inventory or continuity, or grants admission authority.
"""
from dataclasses import dataclass
from enum import StrEnum
import re

from .nasdaq_listed_archive import NasdaqListedArchive
from .sec_archive import SecArchive
from .sec_current_registered_listing_bridge import (
    BridgeAssessmentStatus,
    CurrentRegisteredListingBridgeEvidence,
    SecCurrentRegisteredListingBridgeAssessment,
    SecCurrentRegisteredListingBridgeRequest,
    assess_sec_current_registered_listing_bridge,
)
from .sec_filing_archive import SecFilingArchive, canonical_json, digest
from .sec_registered_securities import (
    ExtractionStatus,
    RegisteredSecurityContextClaims,
    SecRegisteredSecurityExtractionAssessment,
    SecRegisteredSecurityExtractionRequest,
    extract_sec_registered_security_claims,
)
from .sec_section12_rights_source_claims import (
    SecSection12RightsSourceClaimsAssessment,
    SecSection12RightsSourceClaimsRequest,
    SecSection12RightsSourceClaimsStatus,
    SecSection12RightsSourceIssue,
    SecSection12RightsSourceTopic,
    extract_sec_section12_rights_source_claims,
)
from .sec_submissions_archive import SecSubmissionsArchive
from .sec_ticker_exchange_archive import SecTickerExchangeArchive


CONTRACT_VERSION = "2026-09-27-sec-current-common-stock-class-bridge-v1"
SEC_NASDAQ_CURRENT_COMMON_STOCK_CLASS_SOURCE_BRIDGE_V1 = (
    "SEC_NASDAQ_CURRENT_COMMON_STOCK_CLASS_SOURCE_BRIDGE_V1"
)

_ASCII_UPPER = str.maketrans("abcdefghijklmnopqrstuvwxyz", "ABCDEFGHIJKLMNOPQRSTUVWXYZ")
_AMOUNT = r"[0-9]+(?:\.[0-9]{1,10})?"
_TITLE_PROFILE = re.compile(
    r"(?P<base>COMMON STOCK|CLASS [A-Z0-9] COMMON STOCK)"
    r"(?P<suffix>, (?:\$" + _AMOUNT + r" PAR VALUE(?: PER SHARE)?|"
    r"PAR VALUE \$" + _AMOUNT + r"(?: PER SHARE)?|NO PAR VALUE))?",
    re.ASCII,
)


class SecCurrentCommonStockClassBridgeRequestError(ValueError):
    """Invalid closed request or incorrect typed public input."""


class ClassBridgeAssessmentStatus(StrEnum):
    CURRENT_SOURCE_CLASS_BRIDGE_ESTABLISHED = "CURRENT_SOURCE_CLASS_BRIDGE_ESTABLISHED"
    INCOMPLETE_SOURCE_CLASS_BRIDGE = "INCOMPLETE_SOURCE_CLASS_BRIDGE"
    SOURCE_CONFLICT = "SOURCE_CONFLICT"
    UNSUPPORTED_CLASS_PROFILE = "UNSUPPORTED_CLASS_PROFILE"
    UPSTREAM_CURRENT_BRIDGE_UNAVAILABLE = "UPSTREAM_CURRENT_BRIDGE_UNAVAILABLE"
    UPSTREAM_RIGHTS_SOURCE_UNAVAILABLE = "UPSTREAM_RIGHTS_SOURCE_UNAVAILABLE"
    NO_SUPPORTED_CLASS_CANDIDATE = "NO_SUPPORTED_CLASS_CANDIDATE"


class ClassBridgeIssue(StrEnum):
    D4C2_CURRENT_BRIDGE_UNAVAILABLE = "D4C2_CURRENT_BRIDGE_UNAVAILABLE"
    D4C2_CURRENT_BRIDGE_CONFLICT = "D4C2_CURRENT_BRIDGE_CONFLICT"
    D4C2_UNSUPPORTED_SOURCE_PROFILE = "D4C2_UNSUPPORTED_SOURCE_PROFILE"
    D4C2_NO_SUPPORTED_CANDIDATE = "D4C2_NO_SUPPORTED_CANDIDATE"
    D4C2_SUCCESSFUL_CANDIDATE_COUNT_INVALID = (
        "D4C2_SUCCESSFUL_CANDIDATE_COUNT_INVALID"
    )
    D4D2B_RIGHTS_SOURCE_UNAVAILABLE = "D4D2B_RIGHTS_SOURCE_UNAVAILABLE"
    D4D2B_SOURCE_AMBIGUITY = "D4D2B_SOURCE_AMBIGUITY"
    D4D2B_UNSUPPORTED_SOURCE_PROFILE = "D4D2B_UNSUPPORTED_SOURCE_PROFILE"
    D4D2B_NO_SUPPORTED_COMMON_STOCK_SCOPE = (
        "D4D2B_NO_SUPPORTED_COMMON_STOCK_SCOPE"
    )
    D4D2B_NO_SUPPORTED_RIGHTS_SOURCE_CLAIMS = (
        "D4D2B_NO_SUPPORTED_RIGHTS_SOURCE_CLAIMS"
    )
    RIGHTS_RECEIPT_NOT_IN_CURRENT_BRIDGE = "RIGHTS_RECEIPT_NOT_IN_CURRENT_BRIDGE"
    RIGHTS_ACCESSION_NOT_IN_CURRENT_BRIDGE = "RIGHTS_ACCESSION_NOT_IN_CURRENT_BRIDGE"
    SOURCE_CIK_MISMATCH = "SOURCE_CIK_MISMATCH"
    D3A_REPLAY_DISAGREEMENT = "D3A_REPLAY_DISAGREEMENT"
    D3A_SELECTED_RECEIPT_UNAVAILABLE = "D3A_SELECTED_RECEIPT_UNAVAILABLE"
    D3A_REGISTERED_SECURITY_INCOMPLETE = "D3A_REGISTERED_SECURITY_INCOMPLETE"
    D3A_MULTIPLE_ELIGIBLE_CLASS_CLAIMS = "D3A_MULTIPLE_ELIGIBLE_CLASS_CLAIMS"
    D3A_TITLE_NOT_IN_D4C2_CANDIDATE = "D3A_TITLE_NOT_IN_D4C2_CANDIDATE"
    D3A_SCOPE_NOT_IN_D4C2_CANDIDATE = "D3A_SCOPE_NOT_IN_D4C2_CANDIDATE"
    D3A_SYMBOL_MISMATCH = "D3A_SYMBOL_MISMATCH"
    D3A_EXCHANGE_MISMATCH = "D3A_EXCHANGE_MISMATCH"
    UNSUPPORTED_D3A_COMMON_STOCK_TITLE_PROFILE = (
        "UNSUPPORTED_D3A_COMMON_STOCK_TITLE_PROFILE"
    )
    NO_MATCHING_RIGHTS_CLASS_SCOPE = "NO_MATCHING_RIGHTS_CLASS_SCOPE"
    AMBIGUOUS_RIGHTS_CLASS_SCOPE = "AMBIGUOUS_RIGHTS_CLASS_SCOPE"


_CONFLICT_ISSUES = frozenset((
    ClassBridgeIssue.D4C2_CURRENT_BRIDGE_CONFLICT,
    ClassBridgeIssue.D4C2_SUCCESSFUL_CANDIDATE_COUNT_INVALID,
    ClassBridgeIssue.D4D2B_SOURCE_AMBIGUITY,
    ClassBridgeIssue.SOURCE_CIK_MISMATCH,
    ClassBridgeIssue.D3A_REPLAY_DISAGREEMENT,
    ClassBridgeIssue.D3A_MULTIPLE_ELIGIBLE_CLASS_CLAIMS,
    ClassBridgeIssue.D3A_TITLE_NOT_IN_D4C2_CANDIDATE,
    ClassBridgeIssue.D3A_SCOPE_NOT_IN_D4C2_CANDIDATE,
    ClassBridgeIssue.D3A_SYMBOL_MISMATCH,
    ClassBridgeIssue.AMBIGUOUS_RIGHTS_CLASS_SCOPE,
))

_UNSUPPORTED_ISSUES = frozenset((
    ClassBridgeIssue.D4C2_UNSUPPORTED_SOURCE_PROFILE,
    ClassBridgeIssue.D4D2B_UNSUPPORTED_SOURCE_PROFILE,
    ClassBridgeIssue.D3A_EXCHANGE_MISMATCH,
    ClassBridgeIssue.UNSUPPORTED_D3A_COMMON_STOCK_TITLE_PROFILE,
))

_CURRENT_UPSTREAM_ISSUES = frozenset((
    ClassBridgeIssue.D4C2_CURRENT_BRIDGE_UNAVAILABLE,
    ClassBridgeIssue.D4C2_NO_SUPPORTED_CANDIDATE,
))

_RIGHTS_UPSTREAM_ISSUES = frozenset((
    ClassBridgeIssue.D4D2B_RIGHTS_SOURCE_UNAVAILABLE,
    ClassBridgeIssue.D4D2B_NO_SUPPORTED_COMMON_STOCK_SCOPE,
    ClassBridgeIssue.D4D2B_NO_SUPPORTED_RIGHTS_SOURCE_CLAIMS,
))


def _identity(domain, value):
    return digest(("pam:sec-current-common-stock-class-bridge:" + domain + ":v1\0").encode(
        "ascii") + canonical_json(value))


def _normalize_with_positions(value):
    """Return the permitted matching form and source positions for its characters."""
    normalized = []
    positions = []
    pending_space = None
    for index, character in enumerate(value):
        if character.isspace():
            if normalized and pending_space is None:
                pending_space = index
            continue
        if pending_space is not None:
            normalized.append(" ")
            positions.append(pending_space)
            pending_space = None
        normalized.append(character.translate(_ASCII_UPPER))
        positions.append(index)
    return "".join(normalized), tuple(positions)


def _normalize_for_matching(value):
    return _normalize_with_positions(value)[0]


def _parse_d3a_common_stock_title(value):
    """Parse only the finite reviewed source-title profile.

    Returns ``(canonical_base, exact_source_suffix)`` or ``None``.  The suffix
    remains an opaque source substring; no amount is parsed or interpreted.
    """
    if type(value) is not str:
        return None
    normalized, positions = _normalize_with_positions(value)
    match = _TITLE_PROFILE.fullmatch(normalized)
    if match is None:
        return None
    suffix = match.group("suffix")
    if suffix is None:
        return match.group("base"), None
    start, end = match.span("suffix")
    exact_suffix = value[positions[start]:positions[end - 1] + 1]
    return match.group("base"), exact_suffix


@dataclass(frozen=True, slots=True)
class SecCurrentCommonStockClassBridgeRequest:
    registered_listing_bridge_request: SecCurrentRegisteredListingBridgeRequest
    rights_claims_request: SecSection12RightsSourceClaimsRequest

    def __post_init__(self):
        if (type(self.registered_listing_bridge_request)
                is not SecCurrentRegisteredListingBridgeRequest
                or type(self.rights_claims_request)
                is not SecSection12RightsSourceClaimsRequest):
            raise SecCurrentCommonStockClassBridgeRequestError(
                "Exact nested D4C2 and D4D2B requests required")


@dataclass(frozen=True, slots=True)
class CurrentCommonStockClassBridgeEvidence:
    """One filing-local source correspondence; never durable class identity."""

    profile: str
    current_authority_boundary: str
    source_cik: str
    source_symbol: str
    filing_receipt_id: str
    accession: str
    exact_d3a_title: str
    canonical_source_class_label: str | None
    exact_d3a_title_suffix: str | None
    d3a_source_security_scope_id: str
    d3a_claim_semantic_id: str
    d3a_claim_evidence_id: str
    d3a_assessment_semantic_id: str
    d3a_assessment_evidence_id: str
    current_listing_bridge_candidate_semantic_id: str
    current_listing_bridge_candidate_evidence_id: str
    rights_claims_semantic_id: str
    rights_claims_evidence_id: str
    matching_scope_semantic_ids: tuple[str, ...]
    matching_scope_evidence_ids: tuple[str, ...]
    d4d2b_source_class_scope_id: str | None
    exact_d4d2b_class_heading: str | None
    passage_semantic_ids: tuple[str, ...]
    passage_evidence_ids: tuple[str, ...]
    source_block_ordinals: tuple[int, ...]
    source_topics: tuple[SecSection12RightsSourceTopic, ...]
    status: ClassBridgeAssessmentStatus
    issues: tuple[ClassBridgeIssue, ...]

    @property
    def semantic_id(self):
        return _identity("candidate-semantics", {
            "contract": CONTRACT_VERSION,
            "profile": self.profile,
            "current_authority_boundary": self.current_authority_boundary,
            "source_cik": self.source_cik,
            "source_symbol": self.source_symbol,
            "accession": self.accession,
            "d4c2_candidate_semantic_id":
                self.current_listing_bridge_candidate_semantic_id,
            "d3a_claim_semantic_id": self.d3a_claim_semantic_id,
            "exact_d3a_title": self.exact_d3a_title,
            "canonical_source_class_label": self.canonical_source_class_label,
            "exact_d3a_title_suffix": self.exact_d3a_title_suffix,
            "d3a_source_security_scope_id": self.d3a_source_security_scope_id,
            "rights_claims_semantic_id": self.rights_claims_semantic_id,
            "matching_scope_semantic_ids": self.matching_scope_semantic_ids,
            "exact_d4d2b_class_heading": self.exact_d4d2b_class_heading,
            "passage_semantic_ids": self.passage_semantic_ids,
            "source_topics": self.source_topics,
            "status": self.status,
            "issues": self.issues,
        })

    @property
    def evidence_id(self):
        return _identity("candidate-evidence", {
            "semantic_id": self.semantic_id,
            "d4c2_candidate_evidence_id":
                self.current_listing_bridge_candidate_evidence_id,
            "filing_receipt_id": self.filing_receipt_id,
            "d3a_claim_evidence_id": self.d3a_claim_evidence_id,
            "d3a_assessment_evidence_id": self.d3a_assessment_evidence_id,
            "rights_claims_evidence_id": self.rights_claims_evidence_id,
            "matching_scope_evidence_ids": self.matching_scope_evidence_ids,
            "passage_evidence_ids": self.passage_evidence_ids,
        })


@dataclass(frozen=True, slots=True)
class SecCurrentCommonStockClassBridgeAssessment:
    contract_version: str
    status: ClassBridgeAssessmentStatus
    profile: str
    current_authority_boundary: str | None
    current_listing_bridge: SecCurrentRegisteredListingBridgeAssessment
    rights_source_claims: SecSection12RightsSourceClaimsAssessment
    selected_d3a: SecRegisteredSecurityExtractionAssessment
    candidates: tuple[CurrentCommonStockClassBridgeEvidence, ...]
    issues: tuple[ClassBridgeIssue, ...]

    @property
    def semantic_id(self):
        return _identity("assessment-semantics", {
            "contract": self.contract_version,
            "status": self.status,
            "profile": self.profile,
            "current_authority_boundary": self.current_authority_boundary,
            "d4c2_assessment_semantic_id": self.current_listing_bridge.semantic_id,
            "d4d2b_assessment_semantic_id": self.rights_source_claims.semantic_id,
            "d3a_assessment_semantic_id": self.selected_d3a.semantic_id,
            "candidates": tuple(candidate.semantic_id for candidate in self.candidates),
            "issues": self.issues,
        })

    @property
    def evidence_id(self):
        return _identity("assessment-evidence", {
            "semantic_id": self.semantic_id,
            "d4c2_assessment_evidence_id": self.current_listing_bridge.evidence_id,
            "d4d2b_assessment_evidence_id": self.rights_source_claims.evidence_id,
            "d3a_assessment_evidence_id": self.selected_d3a.evidence_id,
            "candidates": tuple(candidate.evidence_id for candidate in self.candidates),
        })


def _ordered(issues):
    return tuple(sorted(issues, key=lambda issue: issue.value))


def _status(issues):
    issues = set(issues)
    if issues & _CONFLICT_ISSUES:
        return ClassBridgeAssessmentStatus.SOURCE_CONFLICT
    if issues & _UNSUPPORTED_ISSUES:
        return ClassBridgeAssessmentStatus.UNSUPPORTED_CLASS_PROFILE
    if issues & _CURRENT_UPSTREAM_ISSUES:
        return ClassBridgeAssessmentStatus.UPSTREAM_CURRENT_BRIDGE_UNAVAILABLE
    if issues & _RIGHTS_UPSTREAM_ISSUES:
        return ClassBridgeAssessmentStatus.UPSTREAM_RIGHTS_SOURCE_UNAVAILABLE
    if ClassBridgeIssue.NO_MATCHING_RIGHTS_CLASS_SCOPE in issues:
        return ClassBridgeAssessmentStatus.NO_SUPPORTED_CLASS_CANDIDATE
    if issues:
        return ClassBridgeAssessmentStatus.INCOMPLETE_SOURCE_CLASS_BRIDGE
    return ClassBridgeAssessmentStatus.CURRENT_SOURCE_CLASS_BRIDGE_ESTABLISHED


def _upstream_issues(current, rights):
    issues = set()
    if current.status is BridgeAssessmentStatus.SOURCE_CONFLICT:
        issues.add(ClassBridgeIssue.D4C2_CURRENT_BRIDGE_CONFLICT)
    elif current.status is BridgeAssessmentStatus.UNSUPPORTED_SOURCE_PROFILE:
        issues.add(ClassBridgeIssue.D4C2_UNSUPPORTED_SOURCE_PROFILE)
    elif current.status is BridgeAssessmentStatus.NO_SUPPORTED_REGISTERED_LISTING_CANDIDATE:
        issues.add(ClassBridgeIssue.D4C2_NO_SUPPORTED_CANDIDATE)
    elif current.status is not BridgeAssessmentStatus.CURRENT_SOURCE_BRIDGE_ESTABLISHED:
        issues.add(ClassBridgeIssue.D4C2_CURRENT_BRIDGE_UNAVAILABLE)

    if rights.status is SecSection12RightsSourceClaimsStatus.SOURCE_AMBIGUITY:
        issues.add(ClassBridgeIssue.D4D2B_SOURCE_AMBIGUITY)
    elif rights.status is (
            SecSection12RightsSourceClaimsStatus.UNSUPPORTED_RIGHTS_EXTRACTION_PROFILE):
        issues.add(ClassBridgeIssue.D4D2B_UNSUPPORTED_SOURCE_PROFILE)
    elif rights.status is SecSection12RightsSourceClaimsStatus.NO_SUPPORTED_COMMON_STOCK_SCOPE:
        issues.add(ClassBridgeIssue.D4D2B_NO_SUPPORTED_COMMON_STOCK_SCOPE)
    elif rights.status is SecSection12RightsSourceClaimsStatus.NO_SUPPORTED_RIGHTS_SOURCE_CLAIMS:
        issues.add(ClassBridgeIssue.D4D2B_NO_SUPPORTED_RIGHTS_SOURCE_CLAIMS)
    elif rights.status is not (
            SecSection12RightsSourceClaimsStatus.CAPTURED_SECTION12_RIGHTS_SOURCE_CLAIMS):
        if SecSection12RightsSourceIssue.UPSTREAM_SOURCE_AMBIGUITY in rights.issues:
            issues.add(ClassBridgeIssue.D4D2B_SOURCE_AMBIGUITY)
        elif ({
                SecSection12RightsSourceIssue.UPSTREAM_UNSUPPORTED_DOCUMENT_REPRESENTATION,
                SecSection12RightsSourceIssue.UPSTREAM_UNSUPPORTED_FILING_FORM,
        } & set(rights.issues)):
            issues.add(ClassBridgeIssue.D4D2B_UNSUPPORTED_SOURCE_PROFILE)
        else:
            issues.add(ClassBridgeIssue.D4D2B_RIGHTS_SOURCE_UNAVAILABLE)
    return issues


def _eligible_d3a_claims(assessment, issues):
    if assessment.status is ExtractionStatus.SOURCE_CONFLICT:
        issues.add(ClassBridgeIssue.D3A_REPLAY_DISAGREEMENT)
        return ()
    if assessment.status is ExtractionStatus.NO_SUPPORTED_REGISTERED_SECURITY_CLAIMS:
        issues.add(ClassBridgeIssue.D3A_SELECTED_RECEIPT_UNAVAILABLE)
        return ()
    if assessment.status is not ExtractionStatus.CAPTURED_REGISTERED_SECURITY_CLAIMS:
        issues.add(ClassBridgeIssue.D3A_REGISTERED_SECURITY_INCOMPLETE)
        return ()

    eligible = {}
    for claim in assessment.claims:
        shape = (not claim.issues and len(claim.titles) == 1
                 and len(claim.trading_symbols) == 1
                 and not claim.no_trading_symbol_flags
                 and len(claim.exchange_names) == 1
                 and bool(claim.source_security_scope_id))
        if not shape:
            issues.add(ClassBridgeIssue.D3A_REGISTERED_SECURITY_INCOMPLETE)
            continue
        if claim.exchange_names[0] != "NASDAQ":
            issues.add(ClassBridgeIssue.D3A_EXCHANGE_MISMATCH)
            continue
        key = (claim.titles[0], claim.trading_symbols[0],
               claim.source_security_scope_id)
        eligible.setdefault(key, claim)
    if len(eligible) > 1:
        issues.add(ClassBridgeIssue.D3A_MULTIPLE_ELIGIBLE_CLASS_CLAIMS)
    return tuple(eligible[key] for key in sorted(eligible))


def _claim_ids(assessment, claim):
    semantic = _identity("d3a-claim-semantics", {
        "d3a_assessment_semantic_id": assessment.semantic_id,
        "context_semantic_id": claim.context_semantic_id,
        "source_security_scope_id": claim.source_security_scope_id,
        "titles": claim.titles,
        "trading_symbols": claim.trading_symbols,
        "exchange_names": claim.exchange_names,
        "issues": claim.issues,
    })
    evidence = _identity("d3a-claim-evidence", {
        "semantic_id": semantic,
        "d3a_assessment_evidence_id": assessment.evidence_id,
        "context_refs": claim.context_refs,
        "occurrence_ids": claim.occurrence_ids,
    })
    return semantic, evidence


def _embedded_d3a_agrees(current, receipt_id, fresh):
    matches = []
    for filing in current.temporal_boundary.filings:
        for capture in filing.controlled_captures_by_boundary:
            if capture.receipt.receipt_id == receipt_id:
                matches.append(capture.registered_security_claims)
    if not matches:
        return None
    return (len(matches) == 1 and matches[0] is not None
            and matches[0].semantic_id == fresh.semantic_id
            and matches[0].evidence_id == fresh.evidence_id)


def _build_candidate(current_candidate: CurrentRegisteredListingBridgeEvidence,
                     current_boundary, rights, d3a, claim, issues):
    receipt = rights.upstream_assessment.inventory.receipt
    title = claim.titles[0]
    parsed = _parse_d3a_common_stock_title(title)
    canonical_label = parsed[0] if parsed is not None else None
    exact_suffix = parsed[1] if parsed is not None else None
    if parsed is None:
        issues.add(ClassBridgeIssue.UNSUPPORTED_D3A_COMMON_STOCK_TITLE_PROFILE)

    matching_scopes = ()
    selected_scope = None
    if canonical_label is not None:
        matching_scopes = tuple(
            scope for scope in rights.class_scopes
            if _normalize_for_matching(scope.exact_class_heading) == canonical_label
        )
        if not matching_scopes:
            issues.add(ClassBridgeIssue.NO_MATCHING_RIGHTS_CLASS_SCOPE)
        elif len(matching_scopes) > 1:
            issues.add(ClassBridgeIssue.AMBIGUOUS_RIGHTS_CLASS_SCOPE)
        else:
            selected_scope = matching_scopes[0]

    selected_passages = ()
    if selected_scope is not None:
        selected_passages = tuple(
            passage for passage in rights.passages
            if passage.source_class_scope_id == selected_scope.source_class_scope_id
        )
    topics = tuple(sorted(
        {topic for passage in selected_passages for topic in passage.matched_topics},
        key=lambda topic: topic.value,
    ))
    claim_semantic_id, claim_evidence_id = _claim_ids(d3a, claim)
    ordered_issues = _ordered(issues)
    candidate_status = _status(ordered_issues)
    return CurrentCommonStockClassBridgeEvidence(
        SEC_NASDAQ_CURRENT_COMMON_STOCK_CLASS_SOURCE_BRIDGE_V1,
        current_boundary,
        current_candidate.source_cik,
        current_candidate.source_symbol,
        receipt.receipt_id,
        receipt.accession,
        title,
        canonical_label,
        exact_suffix,
        claim.source_security_scope_id,
        claim_semantic_id,
        claim_evidence_id,
        d3a.semantic_id,
        d3a.evidence_id,
        current_candidate.semantic_id,
        current_candidate.evidence_id,
        rights.semantic_id,
        rights.evidence_id,
        tuple(scope.semantic_id for scope in matching_scopes),
        tuple(scope.evidence_id for scope in matching_scopes),
        selected_scope.source_class_scope_id if selected_scope is not None else None,
        selected_scope.exact_class_heading if selected_scope is not None else None,
        tuple(passage.semantic_id for passage in selected_passages),
        tuple(passage.evidence_id for passage in selected_passages),
        tuple(passage.block_ordinal for passage in selected_passages),
        topics,
        candidate_status,
        ordered_issues,
    )


def assess_sec_current_common_stock_class_bridge(
    current_archive: SecArchive,
    submissions_archive: SecSubmissionsArchive,
    filing_archive: SecFilingArchive,
    ticker_exchange_archive: SecTickerExchangeArchive,
    nasdaq_listed_archive: NasdaqListedArchive,
    request: SecCurrentCommonStockClassBridgeRequest,
) -> SecCurrentCommonStockClassBridgeAssessment:
    """Freshly replay the three source rails and assess same-filing correspondence."""
    if (type(current_archive) is not SecArchive
            or type(submissions_archive) is not SecSubmissionsArchive
            or type(filing_archive) is not SecFilingArchive
            or type(ticker_exchange_archive) is not SecTickerExchangeArchive
            or type(nasdaq_listed_archive) is not NasdaqListedArchive
            or type(request) is not SecCurrentCommonStockClassBridgeRequest):
        raise SecCurrentCommonStockClassBridgeRequestError(
            "Exact typed archives/request required")

    current = assess_sec_current_registered_listing_bridge(
        current_archive,
        submissions_archive,
        filing_archive,
        ticker_exchange_archive,
        nasdaq_listed_archive,
        request.registered_listing_bridge_request,
    )
    rights = extract_sec_section12_rights_source_claims(
        filing_archive, request.rights_claims_request)
    d3a = extract_sec_registered_security_claims(
        filing_archive,
        SecRegisteredSecurityExtractionRequest(
            request.rights_claims_request.filing_receipt_id),
    )

    receipt = rights.upstream_assessment.inventory.receipt
    if receipt.receipt_id != request.rights_claims_request.filing_receipt_id:
        raise AssertionError("D4D2B replay selected a different filing receipt")

    issues = _upstream_issues(current, rights)
    successful_current_candidates = tuple(
        candidate for candidate in current.candidates
        if candidate.status is BridgeAssessmentStatus.CURRENT_SOURCE_BRIDGE_ESTABLISHED
    )
    current_candidate = (successful_current_candidates[0]
                         if len(successful_current_candidates) == 1 else None)
    if (current.status is BridgeAssessmentStatus.CURRENT_SOURCE_BRIDGE_ESTABLISHED
            and len(successful_current_candidates) != 1):
        issues.add(ClassBridgeIssue.D4C2_SUCCESSFUL_CANDIDATE_COUNT_INVALID)

    replay_agreement = _embedded_d3a_agrees(current, receipt.receipt_id, d3a)
    if replay_agreement is False:
        issues.add(ClassBridgeIssue.D3A_REPLAY_DISAGREEMENT)
    eligible_claims = _eligible_d3a_claims(d3a, issues)

    if current_candidate is not None:
        if receipt.receipt_id not in current_candidate.supporting_filing_receipt_ids:
            issues.add(ClassBridgeIssue.RIGHTS_RECEIPT_NOT_IN_CURRENT_BRIDGE)
        if receipt.accession not in current_candidate.supporting_accessions:
            issues.add(ClassBridgeIssue.RIGHTS_ACCESSION_NOT_IN_CURRENT_BRIDGE)
        if receipt.cik != current_candidate.source_cik:
            issues.add(ClassBridgeIssue.SOURCE_CIK_MISMATCH)
    if (d3a.receipt.cik != receipt.cik
            or d3a.primary_document.cik != receipt.cik
            or d3a.receipt.accession != receipt.accession
            or d3a.primary_document.accession != receipt.accession):
        issues.add(ClassBridgeIssue.SOURCE_CIK_MISMATCH)

    candidates = ()
    upstream_positive = (
        current.status is BridgeAssessmentStatus.CURRENT_SOURCE_BRIDGE_ESTABLISHED
        and rights.status is
        SecSection12RightsSourceClaimsStatus.CAPTURED_SECTION12_RIGHTS_SOURCE_CLAIMS
    )
    if upstream_positive and current_candidate is not None and len(eligible_claims) == 1:
        claim = eligible_claims[0]
        if claim.trading_symbols[0] != current_candidate.source_symbol:
            issues.add(ClassBridgeIssue.D3A_SYMBOL_MISMATCH)
        if claim.titles[0] not in current_candidate.d3a_titles:
            issues.add(ClassBridgeIssue.D3A_TITLE_NOT_IN_D4C2_CANDIDATE)
        if (receipt.accession, claim.source_security_scope_id) not in (
                current_candidate.d3a_filing_source_scopes):
            issues.add(ClassBridgeIssue.D3A_SCOPE_NOT_IN_D4C2_CANDIDATE)
        candidate = _build_candidate(
            current_candidate, current.current_authority_boundary,
            rights, d3a, claim, issues)
        candidates = (candidate,)
        issues.update(candidate.issues)

    ordered_issues = _ordered(issues)
    status = _status(ordered_issues)
    if (status is ClassBridgeAssessmentStatus.CURRENT_SOURCE_CLASS_BRIDGE_ESTABLISHED
            and (len(candidates) != 1
                 or candidates[0].status is not
                 ClassBridgeAssessmentStatus.CURRENT_SOURCE_CLASS_BRIDGE_ESTABLISHED)):
        status = ClassBridgeAssessmentStatus.INCOMPLETE_SOURCE_CLASS_BRIDGE

    return SecCurrentCommonStockClassBridgeAssessment(
        CONTRACT_VERSION,
        status,
        SEC_NASDAQ_CURRENT_COMMON_STOCK_CLASS_SOURCE_BRIDGE_V1,
        current.current_authority_boundary,
        current,
        rights,
        d3a,
        candidates,
        ordered_issues,
    )
