"""T-bounded SEC/Nasdaq source corroboration; never economic identity.

This adapter freshly replays D4B, D4C1, and D2C.  It can establish only that
their reviewed CURRENT source claims agree on one exact SEC CIK / Nasdaq symbol
relationship by the D1 boundary.  It grants no durable issuer, security, class,
listing, currency, continuity, or admission authority.
"""
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from .nasdaq_listed_archive import NasdaqListedArchive
from .nasdaq_listed_snapshot import (
    NasdaqListedSnapshotAssessment,
    NasdaqListedSnapshotRequest,
    SnapshotRequestError,
    replay_nasdaq_listed_snapshot,
)
from .sec_archive import SecArchive
from .sec_filing_archive import SecFilingArchive, canonical_json, digest
from .sec_property4_temporal_boundary import (
    BoundaryAssessmentStatus,
    SecProperty4TemporalBoundaryAssessment,
    SecProperty4TemporalBoundaryRequest,
    assess_sec_property4_temporal_boundary,
)
from .sec_registered_securities import ExtractionStatus
from .sec_submissions_archive import SecSubmissionsArchive
from .sec_ticker_exchange_archive import SecTickerExchangeArchive
from .sec_ticker_exchange_snapshot import (
    SecTickerExchangeSnapshotAssessment,
    SecTickerExchangeSnapshotRequest,
    SecTickerExchangeSnapshotRequestError,
    replay_sec_ticker_exchange_snapshot,
)


BRIDGE_CONTRACT_VERSION = "2026-09-26-sec-current-registered-listing-bridge-v1"
SEC_NASDAQ_REGISTERED_LISTING_BRIDGE_V1 = "SEC_NASDAQ_REGISTERED_LISTING_BRIDGE_V1"
_SUPPORTED_EXCHANGE_PAIR = ("NASDAQ", "Nasdaq")


class SecCurrentRegisteredListingBridgeRequestError(ValueError):
    """Malformed explicit evidence selection or incorrect typed input."""


class BridgeAssessmentStatus(StrEnum):
    CURRENT_SOURCE_BRIDGE_ESTABLISHED = "CURRENT_SOURCE_BRIDGE_ESTABLISHED"
    INCOMPLETE_SOURCE_BRIDGE = "INCOMPLETE_SOURCE_BRIDGE"
    SOURCE_CONFLICT = "SOURCE_CONFLICT"
    CURRENT_AUTHORITY_UNAVAILABLE = "CURRENT_AUTHORITY_UNAVAILABLE"
    UNSUPPORTED_SOURCE_PROFILE = "UNSUPPORTED_SOURCE_PROFILE"
    NO_SUPPORTED_REGISTERED_LISTING_CANDIDATE = "NO_SUPPORTED_REGISTERED_LISTING_CANDIDATE"


class BridgeIssue(StrEnum):
    D4B_CURRENT_BOUNDARY_UNAVAILABLE = "D4B_CURRENT_BOUNDARY_UNAVAILABLE"
    D4B_BOUNDARY_EVIDENCE_INCOMPLETE = "D4B_BOUNDARY_EVIDENCE_INCOMPLETE"
    D4B_SOURCE_CONFLICT = "D4B_SOURCE_CONFLICT"
    SEC_ASSOCIATION_CAPTURE_AFTER_BOUNDARY = "SEC_ASSOCIATION_CAPTURE_AFTER_BOUNDARY"
    NASDAQ_CAPTURE_AFTER_BOUNDARY = "NASDAQ_CAPTURE_AFTER_BOUNDARY"
    D3A_REGISTERED_SECURITY_INCOMPLETE = "D3A_REGISTERED_SECURITY_INCOMPLETE"
    D3A_REGISTERED_SECURITY_CONFLICT = "D3A_REGISTERED_SECURITY_CONFLICT"
    D3A_NO_SUPPORTED_REGISTERED_SECURITY = "D3A_NO_SUPPORTED_REGISTERED_SECURITY"
    UNSUPPORTED_D3A_EXCHANGE_PROFILE = "UNSUPPORTED_D3A_EXCHANGE_PROFILE"
    NO_MATCHING_SEC_ASSOCIATION = "NO_MATCHING_SEC_ASSOCIATION"
    AMBIGUOUS_SEC_ASSOCIATION = "AMBIGUOUS_SEC_ASSOCIATION"
    SEC_TICKER_CROSS_CIK_AMBIGUITY = "SEC_TICKER_CROSS_CIK_AMBIGUITY"
    NO_MATCHING_NASDAQ_SYMBOL = "NO_MATCHING_NASDAQ_SYMBOL"
    AMBIGUOUS_NASDAQ_SYMBOL = "AMBIGUOUS_NASDAQ_SYMBOL"
    NASDAQ_TEST_ISSUE = "NASDAQ_TEST_ISSUE"
    MULTIPLE_INCOMPATIBLE_BRIDGE_CANDIDATES = "MULTIPLE_INCOMPATIBLE_BRIDGE_CANDIDATES"


_CONFLICT_ISSUES = frozenset((
    BridgeIssue.D4B_SOURCE_CONFLICT,
    BridgeIssue.D3A_REGISTERED_SECURITY_CONFLICT,
    BridgeIssue.AMBIGUOUS_SEC_ASSOCIATION,
    BridgeIssue.SEC_TICKER_CROSS_CIK_AMBIGUITY,
    BridgeIssue.AMBIGUOUS_NASDAQ_SYMBOL,
    BridgeIssue.MULTIPLE_INCOMPATIBLE_BRIDGE_CANDIDATES,
))


def _identity(domain, value):
    return digest(("pam:sec-current-registered-listing-bridge:" + domain + ":v1\0").encode("ascii")
                  + canonical_json(value))


def _instant(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


@dataclass(frozen=True, slots=True)
class SecCurrentRegisteredListingBridgeRequest:
    temporal_boundary_request: SecProperty4TemporalBoundaryRequest
    sec_ticker_exchange_receipt_id: str
    nasdaq_listed_receipt_id: str

    def __post_init__(self):
        if type(self.temporal_boundary_request) is not SecProperty4TemporalBoundaryRequest:
            raise SecCurrentRegisteredListingBridgeRequestError(
                "Exact temporal-boundary request required")
        try:
            SecTickerExchangeSnapshotRequest(self.sec_ticker_exchange_receipt_id)
            NasdaqListedSnapshotRequest(self.nasdaq_listed_receipt_id)
        except (SecTickerExchangeSnapshotRequestError, SnapshotRequestError):
            raise SecCurrentRegisteredListingBridgeRequestError(
                "Valid exact auxiliary receipt selectors required") from None


@dataclass(frozen=True, slots=True)
class CurrentRegisteredListingBridgeEvidence:
    """One source-corroboration candidate, not a durable listing or security."""

    source_cik: str
    profile: str
    source_symbol: str
    d3a_titles: tuple[str, ...]
    d3a_source_security_scope_ids: tuple[str, ...]
    d3a_filing_source_scopes: tuple[tuple[str, str], ...]
    supporting_accessions: tuple[str, ...]
    supporting_temporal_filing_semantic_ids: tuple[str, ...]
    supporting_temporal_filing_evidence_ids: tuple[str, ...]
    supporting_d3a_semantic_ids: tuple[str, ...]
    supporting_d3a_evidence_ids: tuple[str, ...]
    supporting_filing_receipt_ids: tuple[str, ...]
    sec_association_row_semantic_id: str | None
    sec_association_occurrence_ids: tuple[str, ...]
    nasdaq_row_semantic_id: str | None
    nasdaq_occurrence_id: str | None
    status: BridgeAssessmentStatus
    issues: tuple[BridgeIssue, ...]

    @property
    def semantic_id(self):
        return _identity("candidate-semantics", {
            "contract": BRIDGE_CONTRACT_VERSION,
            "source_cik": self.source_cik,
            "profile": self.profile,
            "source_symbol": self.source_symbol,
            "d3a_titles": self.d3a_titles,
            "d3a_source_security_scope_ids": self.d3a_source_security_scope_ids,
            "sec_association_row_semantic_id": self.sec_association_row_semantic_id,
            "nasdaq_row_semantic_id": self.nasdaq_row_semantic_id,
            "status": self.status,
            "issues": self.issues,
        })

    @property
    def evidence_id(self):
        return _identity("candidate-evidence", {
            "semantic_id": self.semantic_id,
            "supporting_temporal_filing_evidence_ids":
                self.supporting_temporal_filing_evidence_ids,
            "supporting_d3a_evidence_ids": self.supporting_d3a_evidence_ids,
            "supporting_filing_receipt_ids": self.supporting_filing_receipt_ids,
            "sec_association_occurrence_ids": self.sec_association_occurrence_ids,
            "nasdaq_occurrence_id": self.nasdaq_occurrence_id,
        })


@dataclass(frozen=True, slots=True)
class SecCurrentRegisteredListingBridgeAssessment:
    contract_version: str
    status: BridgeAssessmentStatus
    profile: str
    current_authority_boundary: str | None
    temporal_boundary: SecProperty4TemporalBoundaryAssessment
    sec_ticker_exchange_snapshot: SecTickerExchangeSnapshotAssessment
    nasdaq_listed_snapshot: NasdaqListedSnapshotAssessment
    candidates: tuple[CurrentRegisteredListingBridgeEvidence, ...]
    issues: tuple[BridgeIssue, ...]

    @property
    def semantic_id(self):
        return _identity("assessment-semantics", {
            "contract": self.contract_version,
            "status": self.status,
            "profile": self.profile,
            "current_authority_boundary": self.current_authority_boundary,
            "d4b_semantic_id": self.temporal_boundary.semantic_id,
            "candidates": [candidate.semantic_id for candidate in self.candidates],
            "issues": self.issues,
        })

    @property
    def evidence_id(self):
        return _identity("assessment-evidence", {
            "semantic_id": self.semantic_id,
            "d4b_evidence_id": self.temporal_boundary.evidence_id,
            "sec_snapshot_evidence_id": self.sec_ticker_exchange_snapshot.evidence_id,
            "nasdaq_snapshot_evidence_id": self.nasdaq_listed_snapshot.evidence_id,
            "candidates": [candidate.evidence_id for candidate in self.candidates],
        })


@dataclass(frozen=True, slots=True)
class _EligibleClaimEvidence:
    symbol: str
    title: str
    source_security_scope_id: str
    accession: str
    temporal_filing_semantic_id: str
    temporal_filing_evidence_id: str
    d3a_semantic_id: str
    d3a_evidence_id: str
    filing_receipt_id: str


def _discover_claims(boundary):
    claims = []
    issues = set()
    for filing in boundary.filings:
        for capture in filing.controlled_captures_by_boundary:
            d3a = capture.registered_security_claims
            if d3a is None:
                issues.add(BridgeIssue.D3A_NO_SUPPORTED_REGISTERED_SECURITY)
                continue
            if d3a.status is ExtractionStatus.SOURCE_CONFLICT:
                issues.add(BridgeIssue.D3A_REGISTERED_SECURITY_CONFLICT)
                continue
            if d3a.status is ExtractionStatus.INCOMPLETE_REGISTERED_SECURITY_CLAIMS:
                issues.add(BridgeIssue.D3A_REGISTERED_SECURITY_INCOMPLETE)
                continue
            if d3a.status is ExtractionStatus.NO_SUPPORTED_REGISTERED_SECURITY_CLAIMS:
                issues.add(BridgeIssue.D3A_NO_SUPPORTED_REGISTERED_SECURITY)
                continue
            local = []
            for claim in d3a.claims:
                eligible_shape = (
                    not claim.issues
                    and len(claim.titles) == 1
                    and len(claim.trading_symbols) == 1
                    and not claim.no_trading_symbol_flags
                    and len(claim.exchange_names) == 1
                    and bool(claim.source_security_scope_id)
                )
                if not eligible_shape:
                    issues.add(BridgeIssue.D3A_REGISTERED_SECURITY_INCOMPLETE)
                    continue
                if claim.exchange_names[0] != _SUPPORTED_EXCHANGE_PAIR[0]:
                    issues.add(BridgeIssue.UNSUPPORTED_D3A_EXCHANGE_PROFILE)
                    continue
                local.append((claim.titles[0], claim.trading_symbols[0],
                              claim.source_security_scope_id))
            # Within one filing, multiple distinct supported source scopes are not
            # silently collapsed into one security merely because their ticker agrees.
            if len(set(local)) > 1:
                issues.add(BridgeIssue.MULTIPLE_INCOMPATIBLE_BRIDGE_CANDIDATES)
            for title, symbol, scope_id in local:
                claims.append(_EligibleClaimEvidence(
                    symbol, title, scope_id, filing.accession, filing.temporal_filing_semantic_id,
                    filing.temporal_filing_evidence_id, d3a.semantic_id, d3a.evidence_id,
                    capture.receipt.receipt_id,
                ))
    if len({claim.symbol for claim in claims}) > 1:
        issues.add(BridgeIssue.MULTIPLE_INCOMPATIBLE_BRIDGE_CANDIDATES)
    return tuple(claims), issues


def _candidate_status(issues):
    if issues & _CONFLICT_ISSUES:
        return BridgeAssessmentStatus.SOURCE_CONFLICT
    if BridgeIssue.UNSUPPORTED_D3A_EXCHANGE_PROFILE in issues:
        return BridgeAssessmentStatus.UNSUPPORTED_SOURCE_PROFILE
    if issues:
        return BridgeAssessmentStatus.INCOMPLETE_SOURCE_BRIDGE
    return BridgeAssessmentStatus.CURRENT_SOURCE_BRIDGE_ESTABLISHED


def _build_candidate(source_cik, symbol, claim_evidence, sec_snapshot, nasdaq_snapshot,
                     boundary, global_issues):
    issues = set(global_issues)
    sec_semantic_id = None
    sec_occurrences = ()
    nasdaq_semantic_id = None
    nasdaq_occurrence_id = None
    if boundary is not None and _instant(sec_snapshot.receipt.captured_at) <= _instant(boundary):
        target_rows = tuple(row for row in sec_snapshot.rows
                            if row.normalized_sec_cik == source_cik
                            and row.source_ticker == symbol
                            and row.source_exchange == _SUPPORTED_EXCHANGE_PAIR[1])
        if symbol in sec_snapshot.ambiguous_tickers:
            issues.add(BridgeIssue.SEC_TICKER_CROSS_CIK_AMBIGUITY)
        semantic_ids = {row.semantic_id for row in target_rows}
        if not target_rows:
            issues.add(BridgeIssue.NO_MATCHING_SEC_ASSOCIATION)
        elif len(semantic_ids) != 1:
            issues.add(BridgeIssue.AMBIGUOUS_SEC_ASSOCIATION)
        else:
            sec_semantic_id = next(iter(semantic_ids))
            sec_occurrences = tuple(sorted(row.occurrence_id for row in target_rows))
    else:
        issues.add(BridgeIssue.SEC_ASSOCIATION_CAPTURE_AFTER_BOUNDARY)

    if boundary is not None and _instant(nasdaq_snapshot.receipt.captured_at) <= _instant(boundary):
        target_rows = tuple(row for row in nasdaq_snapshot.rows
                            if dict(row.fields)["Symbol"] == symbol)
        if not target_rows:
            issues.add(BridgeIssue.NO_MATCHING_NASDAQ_SYMBOL)
        elif len(target_rows) != 1:
            issues.add(BridgeIssue.AMBIGUOUS_NASDAQ_SYMBOL)
        else:
            target = target_rows[0]
            if dict(target.fields)["Test Issue"] != "N":
                issues.add(BridgeIssue.NASDAQ_TEST_ISSUE)
            else:
                nasdaq_semantic_id = target.semantic_id
                nasdaq_occurrence_id = target.occurrence_id
    else:
        issues.add(BridgeIssue.NASDAQ_CAPTURE_AFTER_BOUNDARY)

    ordered = tuple(sorted(issues))
    return CurrentRegisteredListingBridgeEvidence(
        source_cik,
        SEC_NASDAQ_REGISTERED_LISTING_BRIDGE_V1,
        symbol,
        tuple(sorted({item.title for item in claim_evidence})),
        tuple(sorted({item.source_security_scope_id for item in claim_evidence})),
        tuple(sorted({(item.accession, item.source_security_scope_id)
                      for item in claim_evidence})),
        tuple(sorted({item.accession for item in claim_evidence})),
        tuple(sorted({item.temporal_filing_semantic_id for item in claim_evidence})),
        tuple(sorted({item.temporal_filing_evidence_id for item in claim_evidence})),
        tuple(sorted({item.d3a_semantic_id for item in claim_evidence})),
        tuple(sorted({item.d3a_evidence_id for item in claim_evidence})),
        tuple(sorted({item.filing_receipt_id for item in claim_evidence})),
        sec_semantic_id,
        sec_occurrences,
        nasdaq_semantic_id,
        nasdaq_occurrence_id,
        _candidate_status(set(ordered)),
        ordered,
    )


def assess_sec_current_registered_listing_bridge(
    current_archive: SecArchive,
    submissions_archive: SecSubmissionsArchive,
    filing_archive: SecFilingArchive,
    ticker_exchange_archive: SecTickerExchangeArchive,
    nasdaq_listed_archive: NasdaqListedArchive,
    request: SecCurrentRegisteredListingBridgeRequest,
) -> SecCurrentRegisteredListingBridgeAssessment:
    """Freshly replay the exact five archives and assess the closed Nasdaq profile."""
    if (type(current_archive) is not SecArchive
            or type(submissions_archive) is not SecSubmissionsArchive
            or type(filing_archive) is not SecFilingArchive
            or type(ticker_exchange_archive) is not SecTickerExchangeArchive
            or type(nasdaq_listed_archive) is not NasdaqListedArchive
            or type(request) is not SecCurrentRegisteredListingBridgeRequest):
        raise SecCurrentRegisteredListingBridgeRequestError(
            "Exact typed archives/request required")

    boundary = assess_sec_property4_temporal_boundary(
        current_archive, submissions_archive, filing_archive,
        request.temporal_boundary_request,
    )
    sec_snapshot = replay_sec_ticker_exchange_snapshot(
        ticker_exchange_archive,
        SecTickerExchangeSnapshotRequest(request.sec_ticker_exchange_receipt_id),
    )
    nasdaq_snapshot = replay_nasdaq_listed_snapshot(
        nasdaq_listed_archive,
        NasdaqListedSnapshotRequest(request.nasdaq_listed_receipt_id),
    )

    issues = set()
    if boundary.status is BoundaryAssessmentStatus.CURRENT_AUTHORITY_UNAVAILABLE:
        issues.add(BridgeIssue.D4B_CURRENT_BOUNDARY_UNAVAILABLE)
    elif boundary.status is BoundaryAssessmentStatus.SOURCE_CONFLICT:
        issues.add(BridgeIssue.D4B_SOURCE_CONFLICT)
    elif boundary.status is not BoundaryAssessmentStatus.BOUNDARY_EVIDENCE_ESTABLISHED:
        issues.add(BridgeIssue.D4B_BOUNDARY_EVIDENCE_INCOMPLETE)

    current_boundary = boundary.current_authority_boundary
    if current_boundary is not None:
        if _instant(sec_snapshot.receipt.captured_at) > _instant(current_boundary):
            issues.add(BridgeIssue.SEC_ASSOCIATION_CAPTURE_AFTER_BOUNDARY)
        if _instant(nasdaq_snapshot.receipt.captured_at) > _instant(current_boundary):
            issues.add(BridgeIssue.NASDAQ_CAPTURE_AFTER_BOUNDARY)

    claim_evidence, claim_issues = _discover_claims(boundary)
    issues.update(claim_issues)
    by_symbol = {}
    for evidence in claim_evidence:
        by_symbol.setdefault(evidence.symbol, []).append(evidence)
    candidates = tuple(
        _build_candidate(boundary.source_cik, symbol, tuple(by_symbol[symbol]),
                         sec_snapshot, nasdaq_snapshot, current_boundary, issues)
        for symbol in sorted(by_symbol)
    )
    issues.update(issue for candidate in candidates for issue in candidate.issues)

    if boundary.status is BoundaryAssessmentStatus.CURRENT_AUTHORITY_UNAVAILABLE:
        status = BridgeAssessmentStatus.CURRENT_AUTHORITY_UNAVAILABLE
    elif issues & _CONFLICT_ISSUES:
        status = BridgeAssessmentStatus.SOURCE_CONFLICT
    elif boundary.status is BoundaryAssessmentStatus.NO_RELEVANT_PERIODIC_FILINGS:
        status = BridgeAssessmentStatus.NO_SUPPORTED_REGISTERED_LISTING_CANDIDATE
    elif boundary.status is not BoundaryAssessmentStatus.BOUNDARY_EVIDENCE_ESTABLISHED:
        status = BridgeAssessmentStatus.INCOMPLETE_SOURCE_BRIDGE
    elif len(candidates) == 1 and candidates[0].status is BridgeAssessmentStatus.CURRENT_SOURCE_BRIDGE_ESTABLISHED:
        status = BridgeAssessmentStatus.CURRENT_SOURCE_BRIDGE_ESTABLISHED
    elif BridgeIssue.UNSUPPORTED_D3A_EXCHANGE_PROFILE in issues:
        status = BridgeAssessmentStatus.UNSUPPORTED_SOURCE_PROFILE
    elif candidates:
        status = BridgeAssessmentStatus.INCOMPLETE_SOURCE_BRIDGE
    else:
        status = BridgeAssessmentStatus.NO_SUPPORTED_REGISTERED_LISTING_CANDIDATE

    return SecCurrentRegisteredListingBridgeAssessment(
        BRIDGE_CONTRACT_VERSION,
        status,
        SEC_NASDAQ_REGISTERED_LISTING_BRIDGE_V1,
        current_boundary,
        boundary,
        sec_snapshot,
        nasdaq_snapshot,
        candidates,
        tuple(sorted(issues)),
    )
