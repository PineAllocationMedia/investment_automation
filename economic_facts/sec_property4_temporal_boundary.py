"""Bind exact SEC temporal evidence to a replayed CURRENT capture boundary.

This adapter establishes only whether PAM controlled-captured exact filing bytes
no later than the D1 CURRENT boundary.  It does not establish publication,
historical public availability, completeness, economic identity, continuity, or
admission.  Source acceptance, filing/report dates, D2A capture time, and the D1
boundary remain separate concepts.
"""
from dataclasses import asdict, dataclass
from datetime import datetime
from enum import StrEnum

from .current_authority import AssessmentStatus, CurrentAuthorityAssessment
from .sec_archive import SecArchive
from .sec_current_evidence import SecCurrentEvidenceAssessment, assess_sec_current_evidence
from .sec_eps_series import ResolutionMode, ResolutionStatus, SeriesResolutionRequest
from .sec_filing_archive import SecFilingArchive, canonical_json, digest
from .sec_property4_temporal_dossier import (
    DossierIssue,
    DossierStatus,
    FilingCaptureEvidence,
    SecProperty4TemporalDossier,
    SecProperty4TemporalDossierRequest,
    SecProperty4TemporalDossierRequestError,
    TemporalFilingEvidence,
    build_sec_property4_temporal_dossier,
)
from .sec_submissions_archive import SecSubmissionsArchive
from .source_authority import PublicationSemantics


BOUNDARY_CONTRACT_VERSION = "2026-09-26-sec-property4-temporal-boundary-v1"


class SecProperty4TemporalBoundaryRequestError(ValueError):
    """Malformed or impossible explicit evidence selection."""


class SecProperty4TemporalBoundaryContractError(ValueError):
    """Freshly replayed upstream output violates its reviewed contract."""


class BoundaryAssessmentStatus(StrEnum):
    BOUNDARY_EVIDENCE_ESTABLISHED = "BOUNDARY_EVIDENCE_ESTABLISHED"
    INCOMPLETE_BOUNDARY_EVIDENCE = "INCOMPLETE_BOUNDARY_EVIDENCE"
    SOURCE_CONFLICT = "SOURCE_CONFLICT"
    CURRENT_AUTHORITY_UNAVAILABLE = "CURRENT_AUTHORITY_UNAVAILABLE"
    NO_RELEVANT_PERIODIC_FILINGS = "NO_RELEVANT_PERIODIC_FILINGS"


class BoundaryIssue(StrEnum):
    D1_CURRENT_AUTHORITY_UNAVAILABLE = "D1_CURRENT_AUTHORITY_UNAVAILABLE"
    D4A_TEMPORAL_DOSSIER_INCOMPLETE = "D4A_TEMPORAL_DOSSIER_INCOMPLETE"
    D4A_SOURCE_CONFLICT = "D4A_SOURCE_CONFLICT"
    NO_CAPTURE_BY_CURRENT_BOUNDARY = "NO_CAPTURE_BY_CURRENT_BOUNDARY"
    SOURCE_ACCEPTANCE_AFTER_CURRENT_BOUNDARY = "SOURCE_ACCEPTANCE_AFTER_CURRENT_BOUNDARY"
    CAPTURE_PRECEDES_SOURCE_ACCEPTANCE = "CAPTURE_PRECEDES_SOURCE_ACCEPTANCE"
    NO_RELEVANT_PERIODIC_FILINGS = "NO_RELEVANT_PERIODIC_FILINGS"


class SourceEventBoundaryRelation(StrEnum):
    ON_OR_BEFORE_CURRENT_BOUNDARY = "ON_OR_BEFORE_CURRENT_BOUNDARY"
    AFTER_CURRENT_BOUNDARY = "AFTER_CURRENT_BOUNDARY"
    CURRENT_BOUNDARY_UNAVAILABLE = "CURRENT_BOUNDARY_UNAVAILABLE"


class FilingBoundaryStatus(StrEnum):
    CONTROLLED_CAPTURE_BY_BOUNDARY = "CONTROLLED_CAPTURE_BY_BOUNDARY"
    NO_CONTROLLED_CAPTURE_BY_BOUNDARY = "NO_CONTROLLED_CAPTURE_BY_BOUNDARY"
    POST_BOUNDARY_SOURCE_EVENT = "POST_BOUNDARY_SOURCE_EVENT"
    SOURCE_CONFLICT = "SOURCE_CONFLICT"
    CURRENT_AUTHORITY_UNAVAILABLE = "CURRENT_AUTHORITY_UNAVAILABLE"


def _identity(domain, value):
    return digest(("pam:sec-property4-temporal-boundary:" + domain + ":v1\0").encode("ascii")
                  + canonical_json(value))


def _instant(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


@dataclass(frozen=True, slots=True)
class SecProperty4TemporalBoundaryRequest:
    current_request: SeriesResolutionRequest
    parent_submissions_receipt_id: str
    child_submissions_receipt_ids: tuple[str, ...] = ()
    filing_receipt_ids: tuple[str, ...] = ()

    def __post_init__(self):
        if type(self.current_request) is not SeriesResolutionRequest:
            raise SecProperty4TemporalBoundaryRequestError(
                "Exact SeriesResolutionRequest required")
        try:
            SecProperty4TemporalDossierRequest(
                self.parent_submissions_receipt_id,
                self.child_submissions_receipt_ids,
                self.filing_receipt_ids,
            )
        except SecProperty4TemporalDossierRequestError:
            raise SecProperty4TemporalBoundaryRequestError(
                "Valid exact temporal-dossier selectors required") from None


@dataclass(frozen=True, slots=True)
class SourceAcceptanceBoundaryEvidence:
    occurrence_id: str
    acceptance_timestamp: str
    relation: SourceEventBoundaryRelation


@dataclass(frozen=True, slots=True)
class TemporalBoundaryFilingEvidence:
    """T-bounded view of one D4A accession; never an identity qualifier."""

    accession: str
    temporal_filing_semantic_id: str
    temporal_filing_evidence_id: str
    source_acceptance_events: tuple[SourceAcceptanceBoundaryEvidence, ...]
    controlled_captures_by_boundary: tuple[FilingCaptureEvidence, ...]
    post_boundary_captures: tuple[FilingCaptureEvidence, ...]
    unclassified_captures: tuple[FilingCaptureEvidence, ...]
    semantic_capture_claims_observed_by_boundary: tuple[str, ...]
    upstream_issues: tuple[DossierIssue, ...]
    status: FilingBoundaryStatus
    issues: tuple[BoundaryIssue, ...]

    @property
    def semantic_id(self):
        return _identity("filing-semantics", {
            "accession": self.accession,
            "temporal_filing_semantic_id": self.temporal_filing_semantic_id,
            "source_events": [(event.acceptance_timestamp, event.relation)
                              for event in self.source_acceptance_events],
            "semantic_capture_claims_observed_by_boundary":
                self.semantic_capture_claims_observed_by_boundary,
            "upstream_issues": self.upstream_issues,
            "status": self.status,
            "issues": self.issues,
        })

    @property
    def evidence_id(self):
        return _identity("filing-evidence", {
            "semantic_id": self.semantic_id,
            "temporal_filing_evidence_id": self.temporal_filing_evidence_id,
            "source_events": [asdict(event) for event in self.source_acceptance_events],
            "controlled_captures_by_boundary": [capture.evidence_id
                                                  for capture in self.controlled_captures_by_boundary],
            "post_boundary_captures": [capture.evidence_id
                                        for capture in self.post_boundary_captures],
            "unclassified_captures": [capture.evidence_id
                                       for capture in self.unclassified_captures],
        })


@dataclass(frozen=True, slots=True)
class SecProperty4TemporalBoundaryAssessment:
    contract_version: str
    status: BoundaryAssessmentStatus
    source_cik: str
    current_evidence: SecCurrentEvidenceAssessment
    temporal_dossier: SecProperty4TemporalDossier
    current_authority_boundary: str | None
    series_evidence_horizon_start: str | None
    series_evidence_horizon_end: str | None
    filings: tuple[TemporalBoundaryFilingEvidence, ...]
    issues: tuple[BoundaryIssue, ...]

    @property
    def semantic_id(self):
        return _identity("assessment-semantics", {
            "contract": self.contract_version,
            "status": self.status,
            "source_cik": self.source_cik,
            "d1_semantic_hash": self.current_evidence.semantic_hash,
            "current_authority_boundary": self.current_authority_boundary,
            "series_evidence_horizon_start": self.series_evidence_horizon_start,
            "series_evidence_horizon_end": self.series_evidence_horizon_end,
            "d4a_semantic_id": self.temporal_dossier.semantic_id,
            "filings": [filing.semantic_id for filing in self.filings],
            "issues": self.issues,
        })

    @property
    def evidence_id(self):
        return _identity("assessment-evidence", {
            "semantic_id": self.semantic_id,
            "d1_evidence_hash": self.current_evidence.evidence_hash,
            "d4a_evidence_id": self.temporal_dossier.evidence_id,
            "filings": [filing.evidence_id for filing in self.filings],
        })


def _require_d1_contract(assessment, request):
    if (type(assessment) is not SecCurrentEvidenceAssessment
            or assessment.request != request
            or type(assessment.current_authority) is not CurrentAuthorityAssessment):
        raise SecProperty4TemporalBoundaryContractError("Invalid D1 replay result")
    authority = assessment.current_authority
    if authority.status is AssessmentStatus.EVIDENCE_ESTABLISHED:
        series = assessment.resolution.series
        if not (
            request.mode is ResolutionMode.CURRENT_AS_REPORTED
            and assessment.receipt is not None
            and assessment.resolution.status is ResolutionStatus.RESOLVED_ISSUER_EVIDENCE
            and series is not None
            and authority.current_authority_boundary is not None
            and authority.current_authority_boundary == authority.observed_available_by
            and authority.current_authority_boundary == series.authority_as_of
            and authority.current_authority_boundary == assessment.receipt.captured_at
            and authority.publication is PublicationSemantics.UNKNOWN
        ):
            raise SecProperty4TemporalBoundaryContractError("Inconsistent established D1 boundary")
    elif authority.status is AssessmentStatus.UNAVAILABLE:
        if not (authority.current_authority_boundary is None
                and authority.observed_available_by is None
                and not authority.established_claims):
            raise SecProperty4TemporalBoundaryContractError("Inconsistent unavailable D1 result")
    else:
        raise SecProperty4TemporalBoundaryContractError("Unknown D1 status")


def _event(occurrence, boundary):
    acceptance = dict(occurrence.fields)["acceptanceDateTime"]
    relation = (SourceEventBoundaryRelation.CURRENT_BOUNDARY_UNAVAILABLE
                if boundary is None else
                SourceEventBoundaryRelation.ON_OR_BEFORE_CURRENT_BOUNDARY
                if _instant(acceptance) <= _instant(boundary) else
                SourceEventBoundaryRelation.AFTER_CURRENT_BOUNDARY)
    return SourceAcceptanceBoundaryEvidence(occurrence.occurrence_id, acceptance, relation)


def _filing_boundary(filing: TemporalFilingEvidence, boundary):
    events = tuple(_event(occurrence, boundary) for occurrence in filing.inventory_occurrences)
    if boundary is None:
        return TemporalBoundaryFilingEvidence(
            filing.accession, filing.semantic_id, filing.evidence_id, events, (), (), filing.captures,
            (), filing.issues, FilingBoundaryStatus.CURRENT_AUTHORITY_UNAVAILABLE, (),
        )

    boundary_time = _instant(boundary)
    controlled = tuple(capture for capture in filing.captures
                       if _instant(capture.receipt.captured_at) <= boundary_time)
    post = tuple(capture for capture in filing.captures
                 if _instant(capture.receipt.captured_at) > boundary_time)
    issues = set()
    on_or_before = any(event.relation is SourceEventBoundaryRelation.ON_OR_BEFORE_CURRENT_BOUNDARY
                       for event in events)
    after = any(event.relation is SourceEventBoundaryRelation.AFTER_CURRENT_BOUNDARY
                for event in events)
    if after:
        issues.add(BoundaryIssue.SOURCE_ACCEPTANCE_AFTER_CURRENT_BOUNDARY)
    acceptance_times = tuple(_instant(event.acceptance_timestamp) for event in events)
    if any(_instant(capture.receipt.captured_at) < acceptance
           for capture in filing.captures for acceptance in acceptance_times):
        issues.add(BoundaryIssue.CAPTURE_PRECEDES_SOURCE_ACCEPTANCE)
    if on_or_before and not controlled:
        issues.add(BoundaryIssue.NO_CAPTURE_BY_CURRENT_BOUNDARY)

    if BoundaryIssue.CAPTURE_PRECEDES_SOURCE_ACCEPTANCE in issues:
        status = FilingBoundaryStatus.SOURCE_CONFLICT
    elif not on_or_before:
        status = FilingBoundaryStatus.POST_BOUNDARY_SOURCE_EVENT
    elif controlled:
        status = FilingBoundaryStatus.CONTROLLED_CAPTURE_BY_BOUNDARY
    else:
        status = FilingBoundaryStatus.NO_CONTROLLED_CAPTURE_BY_BOUNDARY
    semantic_claims = tuple(sorted({capture.semantic_id for capture in controlled}))
    return TemporalBoundaryFilingEvidence(
        filing.accession, filing.semantic_id, filing.evidence_id, events, controlled, post, (),
        semantic_claims, filing.issues, status, tuple(sorted(issues)),
    )


def assess_sec_property4_temporal_boundary(
    current_archive: SecArchive,
    submissions_archive: SecSubmissionsArchive,
    filing_archive: SecFilingArchive,
    request: SecProperty4TemporalBoundaryRequest,
) -> SecProperty4TemporalBoundaryAssessment:
    """Replay D1 then D4A and construct a non-economic, T-bounded evidence view."""
    if (type(current_archive) is not SecArchive
            or type(submissions_archive) is not SecSubmissionsArchive
            or type(filing_archive) is not SecFilingArchive
            or type(request) is not SecProperty4TemporalBoundaryRequest):
        raise SecProperty4TemporalBoundaryRequestError("Exact typed archives/request required")

    current = assess_sec_current_evidence(current_archive, request.current_request)
    _require_d1_contract(current, request.current_request)
    dossier = build_sec_property4_temporal_dossier(
        submissions_archive,
        filing_archive,
        SecProperty4TemporalDossierRequest(
            request.parent_submissions_receipt_id,
            tuple(sorted(request.child_submissions_receipt_ids)),
            tuple(sorted(request.filing_receipt_ids)),
        ),
    )
    if dossier.source_cik != request.current_request.cik:
        raise SecProperty4TemporalBoundaryRequestError(
            "D4A source CIK must exactly match the D1 request CIK")

    authority = current.current_authority
    boundary = authority.current_authority_boundary
    filings = tuple(_filing_boundary(filing, boundary) for filing in dossier.filings)
    issues = {issue for filing in filings for issue in filing.issues}
    if dossier.status is DossierStatus.SOURCE_CONFLICT:
        issues.add(BoundaryIssue.D4A_SOURCE_CONFLICT)
    elif dossier.status is DossierStatus.INCOMPLETE_TEMPORAL_EVIDENCE_DOSSIER:
        issues.add(BoundaryIssue.D4A_TEMPORAL_DOSSIER_INCOMPLETE)
    elif dossier.status is DossierStatus.NO_RELEVANT_PERIODIC_FILINGS:
        issues.add(BoundaryIssue.NO_RELEVANT_PERIODIC_FILINGS)
    if authority.status is AssessmentStatus.UNAVAILABLE:
        issues.add(BoundaryIssue.D1_CURRENT_AUTHORITY_UNAVAILABLE)

    if (dossier.status is DossierStatus.SOURCE_CONFLICT
            or BoundaryIssue.CAPTURE_PRECEDES_SOURCE_ACCEPTANCE in issues):
        status = BoundaryAssessmentStatus.SOURCE_CONFLICT
    elif dossier.status is DossierStatus.INCOMPLETE_TEMPORAL_EVIDENCE_DOSSIER:
        status = BoundaryAssessmentStatus.INCOMPLETE_BOUNDARY_EVIDENCE
    elif dossier.status is DossierStatus.NO_RELEVANT_PERIODIC_FILINGS:
        status = BoundaryAssessmentStatus.NO_RELEVANT_PERIODIC_FILINGS
    elif authority.status is AssessmentStatus.UNAVAILABLE:
        status = BoundaryAssessmentStatus.CURRENT_AUTHORITY_UNAVAILABLE
    elif BoundaryIssue.NO_CAPTURE_BY_CURRENT_BOUNDARY in issues:
        status = BoundaryAssessmentStatus.INCOMPLETE_BOUNDARY_EVIDENCE
    else:
        status = BoundaryAssessmentStatus.BOUNDARY_EVIDENCE_ESTABLISHED

    series = current.resolution.series
    horizon_start = series.periods[0].period_start if series is not None else None
    horizon_end = series.periods[-1].period_end if series is not None else None
    return SecProperty4TemporalBoundaryAssessment(
        BOUNDARY_CONTRACT_VERSION, status, dossier.source_cik, current, dossier, boundary,
        horizon_start, horizon_end, filings, tuple(sorted(issues)),
    )
