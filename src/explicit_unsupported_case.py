"""Explain an already-established non-available Stage-B analytical state.

This module is a deterministic, read-only semantic adapter.  It does not
diagnose economics, create capabilities, calculate analytical values, or
derive confidence.
"""
from __future__ import annotations

from dataclasses import dataclass, fields, is_dataclass
from enum import Enum, StrEnum
import hashlib
import json

from economic_facts import cash_like_current_carry as cash_carry

from . import company_vfv_expected_return_comparator as company_vfv
from . import expected_return_pr5e_adapter as pr5e
from . import vfv_forward_expected_return as vfv_er


EXPLICIT_UNSUPPORTED_CASE_CONTRACT_VERSION = (
    "2026-10-04-stage-b-explicit-unsupported-case-v1"
)
EXPLICIT_UNSUPPORTED_CASE_REPRESENTATION_VERSION = (
    "2026-10-04-stage-b-explicit-unsupported-case-representation-v1"
)


class ExplicitUnsupportedCaseError(ValueError):
    """Malformed input type or unsupported canonical upstream state."""


class StageBAnalysisKind(StrEnum):
    COMPANY_EXPECTED_RETURN = "COMPANY_EXPECTED_RETURN"
    VFV_FORWARD_EXPECTED_RETURN = "VFV_FORWARD_EXPECTED_RETURN"
    COMPANY_VFV_EXPECTED_RETURN_COMPARATOR = (
        "COMPANY_VFV_EXPECTED_RETURN_COMPARATOR"
    )
    CASH_LIKE_CURRENT_CARRY = "CASH_LIKE_CURRENT_CARRY"


class StageBCapabilityStatus(StrEnum):
    UNAVAILABLE = "UNAVAILABLE"
    UNSUPPORTED = "UNSUPPORTED"
    SOURCE_CONFLICT = "SOURCE_CONFLICT"


class StageBNonAvailableCaseAuthority(StrEnum):
    CAPABILITY_STATUS_EXPLANATION_ONLY = (
        "CAPABILITY_STATUS_EXPLANATION_ONLY"
    )


class StageBNonAvailableCaseLimitation(StrEnum):
    NO_ANALYTICAL_NUMERIC_OUTPUT = "NO_ANALYTICAL_NUMERIC_OUTPUT"
    NO_CONFIDENCE_RECOMPUTATION_OR_HAIRCUT = (
        "NO_CONFIDENCE_RECOMPUTATION_OR_HAIRCUT"
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
    NO_PIT_OR_HISTORICAL_AS_OF_AUTHORITY_EXPANSION = (
        "NO_PIT_OR_HISTORICAL_AS_OF_AUTHORITY_EXPANSION"
    )
    NO_B2_CAPABILITY_CREATION = "NO_B2_CAPABILITY_CREATION"


_AUTHORITY = (
    StageBNonAvailableCaseAuthority.CAPABILITY_STATUS_EXPLANATION_ONLY
)
_LIMITATIONS = tuple(StageBNonAvailableCaseLimitation)


@dataclass(frozen=True, slots=True)
class StageBNonAvailableCase:
    contract_version: str
    representation_version: str
    analysis_kind: StageBAnalysisKind
    capability_status: StageBCapabilityStatus
    upstream_status: object
    upstream_reasons: tuple[object, ...]
    upstream_semantic_id: str
    upstream_evidence_id: str
    authority: StageBNonAvailableCaseAuthority
    limitations: tuple[StageBNonAvailableCaseLimitation, ...]

    @property
    def semantic_id(self) -> str:
        return _identity("stage-b-non-available-case-semantics", {
            "contract_version": self.contract_version,
            "representation_version": self.representation_version,
            "analysis_kind": self.analysis_kind,
            "capability_status": self.capability_status,
            "upstream_status": self.upstream_status,
            "upstream_reasons": self.upstream_reasons,
            "upstream_semantic_id": self.upstream_semantic_id,
            "authority": self.authority,
            "limitations": self.limitations,
        })

    @property
    def evidence_id(self) -> str:
        return _identity("stage-b-non-available-case-evidence", {
            "semantic_id": self.semantic_id,
            "upstream_evidence_id": self.upstream_evidence_id,
        })

    def to_dict(self) -> dict:
        payload = _canonical(self)
        payload["semantic_id"] = self.semantic_id
        payload["evidence_id"] = self.evidence_id
        return {"stage_b_non_available_case": payload}


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
    raise ExplicitUnsupportedCaseError(
        "Unsupported explicit-case identity value"
    )


def _identity(domain: str, value) -> str:
    payload = json.dumps(
        _canonical(value), sort_keys=True, separators=(",", ":"),
        ensure_ascii=True, allow_nan=False,
    )
    return hashlib.sha256((domain + "\0" + payload).encode("utf-8")).hexdigest()


def _case(
    *,
    analysis_kind: StageBAnalysisKind,
    upstream_status: object,
    upstream_reasons: tuple[object, ...],
    upstream_semantic_id: str,
    upstream_evidence_id: str,
) -> StageBNonAvailableCase:
    if type(upstream_reasons) is not tuple:
        raise ExplicitUnsupportedCaseError(
            "Canonical upstream reasons must be a tuple"
        )
    value = upstream_status.value if isinstance(upstream_status, Enum) else None
    try:
        capability_status = StageBCapabilityStatus(value)
    except ValueError as exc:
        raise ExplicitUnsupportedCaseError(
            "Unsupported upstream capability status"
        ) from exc
    return StageBNonAvailableCase(
        EXPLICIT_UNSUPPORTED_CASE_CONTRACT_VERSION,
        EXPLICIT_UNSUPPORTED_CASE_REPRESENTATION_VERSION,
        analysis_kind,
        capability_status,
        upstream_status,
        upstream_reasons,
        upstream_semantic_id,
        upstream_evidence_id,
        _AUTHORITY,
        _LIMITATIONS,
    )


def _project_company(
    company: pr5e.PR5EAdmissionResult,
) -> StageBNonAvailableCase | None:
    if company.status is pr5e.PR5EStatus.REAL_EXPECTED_RETURN_ADMITTED:
        return None
    if company.status not in {
            pr5e.PR5EStatus.UNAVAILABLE,
            pr5e.PR5EStatus.UNSUPPORTED,
            pr5e.PR5EStatus.SOURCE_CONFLICT}:
        raise ExplicitUnsupportedCaseError(
            "Unsupported PR5E admission status"
        )
    problem = company_vfv.identify_company_expected_return_problem(company)
    return _case(
        analysis_kind=StageBAnalysisKind.COMPANY_EXPECTED_RETURN,
        upstream_status=company.status,
        upstream_reasons=company.reasons,
        upstream_semantic_id=problem.semantic_id,
        upstream_evidence_id=problem.evidence_id,
    )


def _project_vfv(
    diagnostic: vfv_er.VFVForwardERDiagnostic,
) -> StageBNonAvailableCase | None:
    if diagnostic.status is vfv_er.VFVForwardERStatus.AVAILABLE:
        return None
    if diagnostic.status not in {
            vfv_er.VFVForwardERStatus.UNAVAILABLE,
            vfv_er.VFVForwardERStatus.UNSUPPORTED,
            vfv_er.VFVForwardERStatus.SOURCE_CONFLICT}:
        raise ExplicitUnsupportedCaseError("Unsupported VFV status")
    return _case(
        analysis_kind=StageBAnalysisKind.VFV_FORWARD_EXPECTED_RETURN,
        upstream_status=diagnostic.status,
        upstream_reasons=diagnostic.reasons,
        upstream_semantic_id=diagnostic.semantic_id,
        upstream_evidence_id=diagnostic.evidence_id,
    )


def _project_comparator(
    comparison: company_vfv.CompanyVFVComparisonResult,
) -> StageBNonAvailableCase | None:
    if comparison.status is company_vfv.CompanyVFVComparisonStatus.AVAILABLE:
        return None
    if comparison.status not in {
            company_vfv.CompanyVFVComparisonStatus.UNAVAILABLE,
            company_vfv.CompanyVFVComparisonStatus.UNSUPPORTED,
            company_vfv.CompanyVFVComparisonStatus.SOURCE_CONFLICT}:
        raise ExplicitUnsupportedCaseError("Unsupported comparator status")
    return _case(
        analysis_kind=(
            StageBAnalysisKind.COMPANY_VFV_EXPECTED_RETURN_COMPARATOR
        ),
        upstream_status=comparison.status,
        upstream_reasons=comparison.reasons,
        upstream_semantic_id=comparison.semantic_id,
        upstream_evidence_id=comparison.evidence_id,
    )


def _project_cash(
    qualification: cash_carry.CashLikeCurrentCarryQualification,
) -> StageBNonAvailableCase | None:
    if qualification.status is cash_carry.CashLikeCurrentCarryStatus.AVAILABLE:
        return None
    if qualification.status not in {
            cash_carry.CashLikeCurrentCarryStatus.UNAVAILABLE,
            cash_carry.CashLikeCurrentCarryStatus.UNSUPPORTED,
            cash_carry.CashLikeCurrentCarryStatus.SOURCE_CONFLICT}:
        raise ExplicitUnsupportedCaseError("Unsupported cash-carry status")
    return _case(
        analysis_kind=StageBAnalysisKind.CASH_LIKE_CURRENT_CARRY,
        upstream_status=qualification.status,
        upstream_reasons=qualification.reasons,
        upstream_semantic_id=qualification.semantic_id,
        upstream_evidence_id=qualification.evidence_id,
    )


def project_explicit_unsupported_case(
    analysis: object,
) -> StageBNonAvailableCase | None:
    """Return the explicit case for one canonical non-available analysis."""
    if type(analysis) is pr5e.PR5EAdmissionResult:
        return _project_company(analysis)
    if type(analysis) is vfv_er.VFVForwardERDiagnostic:
        return _project_vfv(analysis)
    if type(analysis) is company_vfv.CompanyVFVComparisonResult:
        return _project_comparator(analysis)
    if type(analysis) is cash_carry.CashLikeCurrentCarryQualification:
        return _project_cash(analysis)
    raise ExplicitUnsupportedCaseError(
        "Exact supported canonical analytical result required; mappings and "
        "detached or unrelated surfaces are not accepted"
    )
