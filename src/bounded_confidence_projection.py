"""Bounded projection of confidence already owned by canonical analyses.

This module is a deterministic, read-only semantic adapter.  It does not
calculate confidence, Expected Return, carry, spreads, execution costs, or any
other economic output.
"""
from __future__ import annotations

from dataclasses import dataclass, fields, is_dataclass
from enum import Enum, StrEnum
import hashlib
import json
import math

from economic_facts import cash_like_current_carry as cash_carry
from economic_facts.source_authority import (
    AvailabilitySemantics,
    PublicationSemantics,
)

from . import company_vfv_expected_return_comparator as company_vfv
from . import expected_return_assumptions as assumptions
from . import expected_return_engine as expected_return
from . import expected_return_pr5e_adapter as pr5e
from . import vfv_forward_expected_return as vfv_er


BOUNDED_CONFIDENCE_PROJECTION_CONTRACT_VERSION = (
    "2026-10-04-bounded-confidence-projection-v1"
)
BOUNDED_CONFIDENCE_PROJECTION_VERSION = (
    "2026-10-04-bounded-confidence-projection-representation-v1"
)


class BoundedConfidenceProjectionError(ValueError):
    """Malformed input type or structurally impossible canonical result."""


class BoundedConfidenceAnalysisKind(StrEnum):
    COMPANY_EXPECTED_RETURN = "COMPANY_EXPECTED_RETURN"
    VFV_FORWARD_EXPECTED_RETURN = "VFV_FORWARD_EXPECTED_RETURN"
    COMPANY_VFV_EXPECTED_RETURN_COMPARATOR = (
        "COMPANY_VFV_EXPECTED_RETURN_COMPARATOR"
    )
    CASH_LIKE_CURRENT_CARRY = "CASH_LIKE_CURRENT_CARRY"


class BoundedConfidenceCapabilityStatus(StrEnum):
    AVAILABLE = "AVAILABLE"
    UNAVAILABLE = "UNAVAILABLE"
    UNSUPPORTED = "UNSUPPORTED"
    SOURCE_CONFLICT = "SOURCE_CONFLICT"


class BoundedConfidenceRepresentation(StrEnum):
    NATIVE_CATEGORICAL = "NATIVE_CATEGORICAL"
    EVIDENCE_CONTEXT_ONLY = "EVIDENCE_CONTEXT_ONLY"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class BoundedConfidenceProjectionAuthority(StrEnum):
    CONFIDENCE_PROJECTION_ONLY = "CONFIDENCE_PROJECTION_ONLY"


class BoundedConfidenceProjectionLimitation(StrEnum):
    NO_NEW_CONFIDENCE_METHODOLOGY = "NO_NEW_CONFIDENCE_METHODOLOGY"
    NO_ANALYTICAL_NUMERIC_OUTPUT = "NO_ANALYTICAL_NUMERIC_OUTPUT"
    NO_EXPECTED_RETURN_RECALCULATION_OR_HAIRCUT = (
        "NO_EXPECTED_RETURN_RECALCULATION_OR_HAIRCUT"
    )
    NO_CAPABILITY_STATE_REINTERPRETATION = (
        "NO_CAPABILITY_STATE_REINTERPRETATION"
    )
    NO_RECOMMENDATION_RANKING_ALLOCATION_OR_SIZING = (
        "NO_RECOMMENDATION_RANKING_ALLOCATION_OR_SIZING"
    )
    NO_EXECUTION_OR_PRODUCTION_AUTHORITY = (
        "NO_EXECUTION_OR_PRODUCTION_AUTHORITY"
    )
    NO_V2_PROMOTION_AUTHORITY = "NO_V2_PROMOTION_AUTHORITY"
    NO_EXECUTABLE_NET_EXPECTED_RETURN = "NO_EXECUTABLE_NET_EXPECTED_RETURN"
    NO_PIT_OR_HISTORICAL_AS_OF_AUTHORITY_EXPANSION = (
        "NO_PIT_OR_HISTORICAL_AS_OF_AUTHORITY_EXPANSION"
    )


_AUTHORITY = (
    BoundedConfidenceProjectionAuthority.CONFIDENCE_PROJECTION_ONLY
)
_LIMITATIONS = tuple(BoundedConfidenceProjectionLimitation)


@dataclass(frozen=True, slots=True)
class CompanyExpectedReturnConfidenceDetail:
    component_confidence: expected_return.ConfidenceComponents
    overall_confidence: str
    assessments: tuple[assumptions.ConfidenceAssessment, ...]


@dataclass(frozen=True, slots=True)
class CashLikeCurrentCarryEvidenceContext:
    authority_scope: cash_carry.CashLikeCurrentCarryAuthorityScope
    freshness: cash_carry.CashLikeCurrentFreshness
    availability_semantics: AvailabilitySemantics
    publication_semantics: PublicationSemantics


@dataclass(frozen=True, slots=True)
class _CompanyAssessmentSemantics:
    component: str
    source_authority: str
    freshness: str
    completeness: str
    consistency: str
    assumption_dependence: str
    category: str


ConfidenceDetail = (
    CompanyExpectedReturnConfidenceDetail
    | vfv_er.VFVForwardERConfidence
    | company_vfv.CompanyVFVComparisonConfidence
    | CashLikeCurrentCarryEvidenceContext
    | None
)


@dataclass(frozen=True, slots=True)
class BoundedConfidenceProjection:
    contract_version: str
    projection_version: str
    analysis_kind: BoundedConfidenceAnalysisKind
    capability_status: BoundedConfidenceCapabilityStatus
    upstream_status: object
    upstream_reasons: tuple[object, ...]
    confidence_representation: BoundedConfidenceRepresentation
    upstream_semantic_id: str
    upstream_evidence_id: str
    detail: ConfidenceDetail
    authority: BoundedConfidenceProjectionAuthority
    limitations: tuple[BoundedConfidenceProjectionLimitation, ...]

    @property
    def semantic_id(self) -> str:
        return _identity("bounded-confidence-projection-semantics", {
            "contract_version": self.contract_version,
            "projection_version": self.projection_version,
            "analysis_kind": self.analysis_kind,
            "capability_status": self.capability_status,
            "upstream_status": self.upstream_status,
            "upstream_reasons": self.upstream_reasons,
            "confidence_representation": self.confidence_representation,
            "upstream_semantic_id": self.upstream_semantic_id,
            "detail": _semantic_detail(self.detail),
            "authority": self.authority,
            "limitations": self.limitations,
        })

    @property
    def evidence_id(self) -> str:
        company_assessments = (
            self.detail.assessments
            if type(self.detail) is CompanyExpectedReturnConfidenceDetail
            else None
        )
        return _identity("bounded-confidence-projection-evidence", {
            "semantic_id": self.semantic_id,
            "upstream_evidence_id": self.upstream_evidence_id,
            "company_confidence_assessments": company_assessments,
        })

    def to_dict(self) -> dict:
        payload = _canonical(self)
        payload["semantic_id"] = self.semantic_id
        payload["evidence_id"] = self.evidence_id
        return {"bounded_confidence_projection": payload}


def _canonical(value):
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value):
        return {
            field.name: _canonical(getattr(value, field.name))
            for field in fields(value)
        }
    if type(value) in (tuple, list):
        return [_canonical(item) for item in value]
    if type(value) is dict:
        return {key: _canonical(value[key]) for key in sorted(value)}
    if value is None or type(value) in (str, int, bool):
        return value
    raise BoundedConfidenceProjectionError(
        "Unsupported confidence-projection identity value")


def _identity(domain: str, value) -> str:
    payload = json.dumps(
        _canonical(value), sort_keys=True, separators=(",", ":"),
        ensure_ascii=True, allow_nan=False,
    )
    return hashlib.sha256((domain + "\0" + payload).encode("utf-8")).hexdigest()


def _semantic_detail(detail: ConfidenceDetail):
    if type(detail) is not CompanyExpectedReturnConfidenceDetail:
        return detail
    return {
        "component_confidence": detail.component_confidence,
        "overall_confidence": detail.overall_confidence,
        "assessments": tuple(
            _CompanyAssessmentSemantics(
                item.component,
                item.source_authority,
                item.freshness,
                item.completeness,
                item.consistency,
                item.assumption_dependence,
                item.category,
            )
            for item in detail.assessments
        ),
    }


def _projection(
    *,
    analysis_kind: BoundedConfidenceAnalysisKind,
    capability_status: BoundedConfidenceCapabilityStatus,
    upstream_status: object,
    upstream_reasons: tuple[object, ...],
    confidence_representation: BoundedConfidenceRepresentation,
    upstream_semantic_id: str,
    upstream_evidence_id: str,
    detail: ConfidenceDetail,
) -> BoundedConfidenceProjection:
    return BoundedConfidenceProjection(
        BOUNDED_CONFIDENCE_PROJECTION_CONTRACT_VERSION,
        BOUNDED_CONFIDENCE_PROJECTION_VERSION,
        analysis_kind,
        capability_status,
        upstream_status,
        upstream_reasons,
        confidence_representation,
        upstream_semantic_id,
        upstream_evidence_id,
        detail,
        _AUTHORITY,
        _LIMITATIONS,
    )


def _common_status(status: object) -> BoundedConfidenceCapabilityStatus:
    value = status.value if isinstance(status, Enum) else None
    try:
        return BoundedConfidenceCapabilityStatus(value)
    except ValueError as exc:
        raise BoundedConfidenceProjectionError(
            "Unsupported upstream capability status") from exc


def _validate_company_available(
    company: pr5e.PR5EAdmissionResult,
) -> tuple[
    expected_return.ExpectedReturnDiagnostic,
    tuple[assumptions.ConfidenceAssessment, ...],
]:
    construction = company.construction
    if (type(construction) is not assumptions.ConstructionResult
            or construction.status != "BUILT"
            or type(construction.diagnostic)
            is not expected_return.ExpectedReturnDiagnostic):
        raise BoundedConfidenceProjectionError(
            "Admitted company requires a built canonical construction")
    diagnostic = construction.diagnostic
    if diagnostic.status not in {"AVAILABLE", "DEGRADED"}:
        raise BoundedConfidenceProjectionError(
            "Admitted company requires AVAILABLE or DEGRADED diagnostic")
    if (type(diagnostic.scenarios) is not tuple
            or tuple(item.name for item in diagnostic.scenarios)
            != expected_return.SCENARIOS
            or any(type(item) is not expected_return.ScenarioResult
                   or type(item.annualized_return) is not float
                   or not math.isfinite(item.annualized_return)
                   for item in diagnostic.scenarios)):
        raise BoundedConfidenceProjectionError(
            "Admitted company requires complete numeric scenario structure")
    if type(diagnostic.confidence) is not expected_return.ConfidenceComponents:
        raise BoundedConfidenceProjectionError(
            "Admitted company requires canonical component confidence")
    if (type(diagnostic.overall_confidence) is not str
            or diagnostic.overall_confidence not in expected_return.CONFIDENCE_ORDER):
        raise BoundedConfidenceProjectionError(
            "Admitted company requires canonical overall confidence")
    assessments = construction.confidence
    if (type(assessments) is not tuple
            or len(assessments) != len(expected_return.COMPONENTS)
            or any(type(item) is not assumptions.ConfidenceAssessment
                   for item in assessments)
            or tuple(item.component for item in assessments)
            != expected_return.COMPONENTS):
        raise BoundedConfidenceProjectionError(
            "Admitted company requires canonical confidence assessments")
    return diagnostic, assessments


def _project_company(
    company: pr5e.PR5EAdmissionResult,
) -> BoundedConfidenceProjection:
    problem = company_vfv.identify_company_expected_return_problem(company)
    if company.status is pr5e.PR5EStatus.REAL_EXPECTED_RETURN_ADMITTED:
        diagnostic, assessments = _validate_company_available(company)
        return _projection(
            analysis_kind=(
                BoundedConfidenceAnalysisKind.COMPANY_EXPECTED_RETURN),
            capability_status=BoundedConfidenceCapabilityStatus.AVAILABLE,
            upstream_status=company.status,
            upstream_reasons=company.reasons,
            confidence_representation=(
                BoundedConfidenceRepresentation.NATIVE_CATEGORICAL),
            upstream_semantic_id=problem.semantic_id,
            upstream_evidence_id=problem.evidence_id,
            detail=CompanyExpectedReturnConfidenceDetail(
                diagnostic.confidence,
                diagnostic.overall_confidence,
                assessments,
            ),
        )
    if company.status not in {
            pr5e.PR5EStatus.UNAVAILABLE,
            pr5e.PR5EStatus.UNSUPPORTED,
            pr5e.PR5EStatus.SOURCE_CONFLICT}:
        raise BoundedConfidenceProjectionError(
            "Unsupported PR5E admission status")
    return _projection(
        analysis_kind=BoundedConfidenceAnalysisKind.COMPANY_EXPECTED_RETURN,
        capability_status=_common_status(company.status),
        upstream_status=company.status,
        upstream_reasons=company.reasons,
        confidence_representation=BoundedConfidenceRepresentation.NOT_APPLICABLE,
        upstream_semantic_id=problem.semantic_id,
        upstream_evidence_id=problem.evidence_id,
        detail=None,
    )


def _project_vfv(
    diagnostic: vfv_er.VFVForwardERDiagnostic,
) -> BoundedConfidenceProjection:
    available = diagnostic.status is vfv_er.VFVForwardERStatus.AVAILABLE
    if not available and diagnostic.status not in {
            vfv_er.VFVForwardERStatus.UNAVAILABLE,
            vfv_er.VFVForwardERStatus.UNSUPPORTED,
            vfv_er.VFVForwardERStatus.SOURCE_CONFLICT}:
        raise BoundedConfidenceProjectionError("Unsupported VFV status")
    if available and type(diagnostic.confidence) is not vfv_er.VFVForwardERConfidence:
        raise BoundedConfidenceProjectionError(
            "Available VFV diagnostic requires native confidence")
    return _projection(
        analysis_kind=BoundedConfidenceAnalysisKind.VFV_FORWARD_EXPECTED_RETURN,
        capability_status=(BoundedConfidenceCapabilityStatus.AVAILABLE
                           if available else _common_status(diagnostic.status)),
        upstream_status=diagnostic.status,
        upstream_reasons=diagnostic.reasons,
        confidence_representation=(
            BoundedConfidenceRepresentation.NATIVE_CATEGORICAL
            if available else BoundedConfidenceRepresentation.NOT_APPLICABLE),
        upstream_semantic_id=diagnostic.semantic_id,
        upstream_evidence_id=diagnostic.evidence_id,
        detail=diagnostic.confidence if available else None,
    )


def _project_comparator(
    comparison: company_vfv.CompanyVFVComparisonResult,
) -> BoundedConfidenceProjection:
    available = (
        comparison.status is company_vfv.CompanyVFVComparisonStatus.AVAILABLE
    )
    if not available and comparison.status not in {
            company_vfv.CompanyVFVComparisonStatus.UNAVAILABLE,
            company_vfv.CompanyVFVComparisonStatus.UNSUPPORTED,
            company_vfv.CompanyVFVComparisonStatus.SOURCE_CONFLICT}:
        raise BoundedConfidenceProjectionError("Unsupported comparator status")
    if (available and type(comparison.local_comparator_confidence)
            is not company_vfv.CompanyVFVComparisonConfidence):
        raise BoundedConfidenceProjectionError(
            "Available comparator requires native confidence")
    return _projection(
        analysis_kind=(BoundedConfidenceAnalysisKind.
                       COMPANY_VFV_EXPECTED_RETURN_COMPARATOR),
        capability_status=(BoundedConfidenceCapabilityStatus.AVAILABLE
                           if available else _common_status(comparison.status)),
        upstream_status=comparison.status,
        upstream_reasons=comparison.reasons,
        confidence_representation=(
            BoundedConfidenceRepresentation.NATIVE_CATEGORICAL
            if available else BoundedConfidenceRepresentation.NOT_APPLICABLE),
        upstream_semantic_id=comparison.semantic_id,
        upstream_evidence_id=comparison.evidence_id,
        detail=(comparison.local_comparator_confidence if available else None),
    )


def _project_cash(
    qualification: cash_carry.CashLikeCurrentCarryQualification,
) -> BoundedConfidenceProjection:
    available = (
        qualification.status is cash_carry.CashLikeCurrentCarryStatus.AVAILABLE
    )
    if not available and qualification.status not in {
            cash_carry.CashLikeCurrentCarryStatus.UNAVAILABLE,
            cash_carry.CashLikeCurrentCarryStatus.UNSUPPORTED,
            cash_carry.CashLikeCurrentCarryStatus.SOURCE_CONFLICT}:
        raise BoundedConfidenceProjectionError("Unsupported cash-carry status")
    detail = None
    if available:
        if type(qualification.evidence) is not cash_carry.CashLikeCurrentCarryEvidence:
            raise BoundedConfidenceProjectionError(
                "Available cash carry requires canonical evidence context")
        detail = CashLikeCurrentCarryEvidenceContext(
            qualification.authority_scope,
            qualification.evidence.freshness,
            qualification.evidence.availability_semantics,
            qualification.evidence.publication_semantics,
        )
    return _projection(
        analysis_kind=BoundedConfidenceAnalysisKind.CASH_LIKE_CURRENT_CARRY,
        capability_status=(BoundedConfidenceCapabilityStatus.AVAILABLE
                           if available else _common_status(qualification.status)),
        upstream_status=qualification.status,
        upstream_reasons=qualification.reasons,
        confidence_representation=(
            BoundedConfidenceRepresentation.EVIDENCE_CONTEXT_ONLY
            if available else BoundedConfidenceRepresentation.NOT_APPLICABLE),
        upstream_semantic_id=qualification.semantic_id,
        upstream_evidence_id=qualification.evidence_id,
        detail=detail,
    )


def project_bounded_confidence(analysis: object) -> BoundedConfidenceProjection:
    """Project one exact canonical analytical result without recalculation."""
    if type(analysis) is pr5e.PR5EAdmissionResult:
        return _project_company(analysis)
    if type(analysis) is vfv_er.VFVForwardERDiagnostic:
        return _project_vfv(analysis)
    if type(analysis) is company_vfv.CompanyVFVComparisonResult:
        return _project_comparator(analysis)
    if type(analysis) is cash_carry.CashLikeCurrentCarryQualification:
        return _project_cash(analysis)
    raise BoundedConfidenceProjectionError(
        "Exact supported canonical analytical result required; mappings and "
        "detached or unrelated surfaces are not accepted")
