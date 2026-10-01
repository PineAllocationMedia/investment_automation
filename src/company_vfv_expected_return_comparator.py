"""Bounded PR5E-company versus VFV Expected Return research comparator.

The comparator consumes already-built typed diagnostics.  It performs no
acquisition, analysis reconstruction, FX forecast, ranking, recommendation,
allocation, execution, or production action.
"""
from __future__ import annotations

from dataclasses import dataclass, fields, is_dataclass
from decimal import Decimal
from enum import Enum, StrEnum
import hashlib
import json
import math
import re

from economic_facts import vfv_fx_hedge_evidence as fx_evidence

from . import expected_return_pr5e_adapter as pr5e
from . import vfv_forward_expected_return as vfv_er
from .expected_return_approved_policy_v1 import (
    OWNER_APPROVED_POLICY_VERSION,
    OWNER_APPROVED_PROPOSAL_HASH,
    get_owner_approved_policy_proposal,
)
from .vfv_forward_er_policy import (
    VFV_FORWARD_ER_FX_BASIS,
    VFV_FORWARD_ER_HORIZON_YEARS,
    VFV_FORWARD_ER_METHODOLOGY_ID,
    VFV_FORWARD_ER_POLICY_ID,
    VFV_FORWARD_ER_RETURN_TYPE,
    get_approved_vfv_forward_er_policy,
)


COMPANY_VFV_COMPARISON_CONTRACT_VERSION = (
    "2026-10-01-company-vfv-expected-return-comparator-v1"
)
COMPANY_VFV_COMPARISON_BASIS_IDENTITY = (
    "2026-10-01-company-vfv-constant-fx-comparison-v1"
)
COMPANY_VFV_COMPARISON_BASIS_VERSION = (
    "2026-10-01-company-vfv-constant-fx-comparison-v1"
)
COMPANY_VFV_PROBLEM_IDENTITY_VERSION = (
    "2026-10-01-company-vfv-problem-identity-v2"
)
COMPANY_VFV_COMPARISON_AUTHORITY = "RESEARCH_DIAGNOSTIC_ONLY"
SAME_LABEL_SPREAD_SEMANTICS = (
    "SAME_LABEL_DETERMINISTIC_SCENARIO_SPREADS"
)
_SCENARIO_LABELS = ("bear", "base", "bull")
_COMPANY_METHODOLOGY_ID = "2026-09-08-normalized-eps-cashflow-irr-v1"
_COMPANY_REAL_FACTS_CONTRACT_VERSION = (
    "2026-09-30-pr5e-real-qualified-facts-v1"
)
_COMPANY_CONSTRUCTOR_VERSION = (
    "2026-09-09-qualified-history-constructor-v1"
)
_HASH = re.compile(r"[0-9a-f]{64}")


class CompanyVFVComparatorError(ValueError):
    """Malformed caller boundary; economic incompatibility uses closed status."""


class CompanyVFVComparisonStatus(StrEnum):
    AVAILABLE = "AVAILABLE"
    UNAVAILABLE = "UNAVAILABLE"
    UNSUPPORTED = "UNSUPPORTED"
    SOURCE_CONFLICT = "SOURCE_CONFLICT"


class CompanyVFVComparisonReason(StrEnum):
    COMPANY_UPSTREAM_UNAVAILABLE = "COMPANY_UPSTREAM_UNAVAILABLE"
    COMPANY_UPSTREAM_UNSUPPORTED = "COMPANY_UPSTREAM_UNSUPPORTED"
    COMPANY_UPSTREAM_SOURCE_CONFLICT = "COMPANY_UPSTREAM_SOURCE_CONFLICT"
    COMPANY_IDENTITY_MISMATCH = "COMPANY_IDENTITY_MISMATCH"
    COMPANY_ROUTE_UNSUPPORTED = "COMPANY_ROUTE_UNSUPPORTED"
    COMPANY_CURRENCY_BASIS_INCOMPATIBLE = (
        "COMPANY_CURRENCY_BASIS_INCOMPATIBLE"
    )
    COMPANY_ACCOUNTING_OR_PROFILE_UNSUPPORTED = (
        "COMPANY_ACCOUNTING_OR_PROFILE_UNSUPPORTED"
    )
    COMPANY_DISTRIBUTION_ROUTE_UNSUPPORTED = (
        "COMPANY_DISTRIBUTION_ROUTE_UNSUPPORTED"
    )
    COMPANY_RETURN_BASIS_INCOMPATIBLE = (
        "COMPANY_RETURN_BASIS_INCOMPATIBLE"
    )
    COMPANY_FX_BASIS_INCOMPATIBLE = "COMPANY_FX_BASIS_INCOMPATIBLE"
    COMPANY_HORIZON_INCOMPATIBLE = "COMPANY_HORIZON_INCOMPATIBLE"
    COMPANY_POLICY_IDENTITY_MISMATCH = "COMPANY_POLICY_IDENTITY_MISMATCH"
    COMPANY_DIAGNOSTIC_UNAVAILABLE = "COMPANY_DIAGNOSTIC_UNAVAILABLE"
    VFV_UPSTREAM_UNAVAILABLE = "VFV_UPSTREAM_UNAVAILABLE"
    VFV_UPSTREAM_UNSUPPORTED = "VFV_UPSTREAM_UNSUPPORTED"
    VFV_UPSTREAM_SOURCE_CONFLICT = "VFV_UPSTREAM_SOURCE_CONFLICT"
    VFV_IDENTITY_MISMATCH = "VFV_IDENTITY_MISMATCH"
    VFV_POLICY_IDENTITY_MISMATCH = "VFV_POLICY_IDENTITY_MISMATCH"
    VFV_METHODOLOGY_INCOMPATIBLE = "VFV_METHODOLOGY_INCOMPATIBLE"
    VFV_RETURN_BASIS_INCOMPATIBLE = "VFV_RETURN_BASIS_INCOMPATIBLE"
    VFV_FX_BASIS_INCOMPATIBLE = "VFV_FX_BASIS_INCOMPATIBLE"
    VFV_HORIZON_INCOMPATIBLE = "VFV_HORIZON_INCOMPATIBLE"
    FX_HEDGE_EVIDENCE_UNAVAILABLE = "FX_HEDGE_EVIDENCE_UNAVAILABLE"
    FX_HEDGE_EVIDENCE_UNSUPPORTED = "FX_HEDGE_EVIDENCE_UNSUPPORTED"
    FX_HEDGE_SOURCE_CONFLICT = "FX_HEDGE_SOURCE_CONFLICT"
    FX_HEDGE_IDENTITY_MISMATCH = "FX_HEDGE_IDENTITY_MISMATCH"
    FX_HEDGE_CURRENCY_BASIS_INCOMPATIBLE = (
        "FX_HEDGE_CURRENCY_BASIS_INCOMPATIBLE"
    )
    FX_HEDGE_STATE_INCOMPATIBLE = "FX_HEDGE_STATE_INCOMPATIBLE"
    SCENARIO_LABELS_INCOMPLETE = "SCENARIO_LABELS_INCOMPLETE"
    NUMERICAL_SPREAD_UNAVAILABLE = "NUMERICAL_SPREAD_UNAVAILABLE"


class CompanyVFVComparisonConfidence(StrEnum):
    NONE = "NONE"
    LOW = "LOW"


class CompanyVFVComparisonLimitation(StrEnum):
    CONSTANT_FX_ZERO_FUTURE_FX_CONTRIBUTION_ASSUMPTION = (
        "CONSTANT_FX_ZERO_FUTURE_FX_CONTRIBUTION_ASSUMPTION"
    )
    VFV_MATERIAL_UNDERLYING_USD_EXPOSURE = (
        "VFV_MATERIAL_UNDERLYING_USD_EXPOSURE"
    )
    VFV_MATERIALLY_UNHEDGED_TO_CAD_AT_2026_06_30_DISCLOSURE_STATE = (
        "VFV_MATERIALLY_UNHEDGED_TO_CAD_AT_2026_06_30_DISCLOSURE_STATE"
    )
    VFV_HEDGE_STATE_DATE_BOUND_NOT_PERMANENT = (
        "VFV_HEDGE_STATE_DATE_BOUND_NOT_PERMANENT"
    )
    ACTUAL_CAD_INVESTOR_RETURN_MAY_DIFFER_DUE_TO_CAD_USD_MOVEMENT = (
        "ACTUAL_CAD_INVESTOR_RETURN_MAY_DIFFER_DUE_TO_CAD_USD_MOVEMENT"
    )
    NO_FX_FORECAST = "NO_FX_FORECAST"
    NO_REALIZED_CAD_RETURN_CLAIM = "NO_REALIZED_CAD_RETURN_CLAIM"
    SAME_LABEL_SCENARIOS_ARE_NOT_COMMON_PROBABILISTIC_STATES = (
        "SAME_LABEL_SCENARIOS_ARE_NOT_COMMON_PROBABILISTIC_STATES"
    )
    RESEARCH_DIAGNOSTIC_ONLY = "RESEARCH_DIAGNOSTIC_ONLY"
    NOT_EXECUTABLE_RETURN = "NOT_EXECUTABLE_RETURN"
    NO_RECOMMENDATION_OR_ALLOCATION_AUTHORITY = (
        "NO_RECOMMENDATION_OR_ALLOCATION_AUTHORITY"
    )
    NO_PRODUCTION_OR_EXECUTION_AUTHORITY = (
        "NO_PRODUCTION_OR_EXECUTION_AUTHORITY"
    )
    NO_HISTORICAL_AS_OF_OR_PIT_AUTHORITY = (
        "NO_HISTORICAL_AS_OF_OR_PIT_AUTHORITY"
    )


_LIMITATIONS = tuple(CompanyVFVComparisonLimitation)


@dataclass(frozen=True, slots=True)
class CompanyVFVComparisonRequest:
    expected_company_problem_semantic_id: str
    expected_company_problem_evidence_id: str
    expected_vfv_semantic_id: str
    expected_vfv_evidence_id: str
    expected_vfv_fx_hedge_semantic_id: str
    expected_vfv_fx_hedge_evidence_id: str

    def __post_init__(self):
        for field in fields(self):
            value = getattr(self, field.name)
            if type(value) is not str or _HASH.fullmatch(value) is None:
                raise CompanyVFVComparatorError(
                    f"{field.name}: exact SHA-256 identity required")


@dataclass(frozen=True, slots=True)
class CompanyComparisonBasis:
    route_contract_version: str
    route_adapter_version: str
    constructor_version: str
    upstream_pr5d2_semantic_id: str
    methodology_id: str
    return_basis: str
    fx_basis: str
    horizon_years: int
    quote_currency: str
    quote_unit: str
    accounting_basis: str
    profile: str
    distribution_state: str
    approved_policy_version: str
    approved_proposal_hash: str
    selected_policy_hashes: tuple[tuple[str, str], ...]
    overall_confidence: str


@dataclass(frozen=True, slots=True)
class CompanyExpectedReturnProblemIdentity:
    identity_representation_version: str
    semantic_id: str
    evidence_id: str


@dataclass(frozen=True, slots=True)
class VFVComparisonBasis:
    contract_version: str
    semantic_id: str
    policy_id: str
    policy_hash: str
    methodology_id: str
    return_basis: str
    fx_basis: str
    horizon_years: int
    listed_currency: str
    base_currency: str
    overall_confidence: vfv_er.VFVForwardERConfidenceLevel


@dataclass(frozen=True, slots=True)
class VFVFXHedgeComparisonBasis:
    contract_version: str
    semantic_id: str
    instrument_ticker: str
    instrument_isin: str
    listed_currency: str
    base_currency: str
    economic_exposure_currency: str
    material_hedge_state: fx_evidence.VFVMaterialHedgeState
    measurement_date: str
    net_usd_exposure_percent_of_nav: Decimal
    exposure_unit: fx_evidence.VFVFXExposureUnit
    authority_scope: fx_evidence.VFVFXHedgeAuthorityScope


@dataclass(frozen=True, slots=True)
class SameLabelScenarioSpread:
    label: str
    company_annualized_return: float
    vfv_annualized_return: float
    spread: float
    semantics: str


@dataclass(frozen=True, slots=True)
class CompanyVFVComparisonResult:
    comparison_contract_version: str
    comparison_basis_identity: str
    comparison_basis_version: str
    comparison_semantics: str
    status: CompanyVFVComparisonStatus
    reasons: tuple[CompanyVFVComparisonReason, ...]
    authority: str
    company_problem_identity_version: str
    company_problem_semantic_id: str
    company_problem_evidence_id: str
    company_admission_semantic_id: str
    company_admission_evidence_id: str
    company_basis: CompanyComparisonBasis | None
    vfv_semantic_id: str
    vfv_evidence_id: str
    vfv_basis: VFVComparisonBasis | None
    vfv_fx_hedge_semantic_id: str
    vfv_fx_hedge_evidence_id: str
    vfv_fx_hedge_basis: VFVFXHedgeComparisonBasis | None
    scenario_spreads: tuple[SameLabelScenarioSpread, ...]
    local_comparator_confidence: CompanyVFVComparisonConfidence
    company_limitations: tuple[str, ...]
    vfv_inherited_limitations: tuple[object, ...]
    vfv_limitations: tuple[vfv_er.VFVForwardERLimitation, ...]
    vfv_fx_hedge_limitations: tuple[
        fx_evidence.VFVFXHedgeEvidenceLimitation, ...]
    limitations: tuple[CompanyVFVComparisonLimitation, ...]

    @property
    def semantic_id(self) -> str:
        return _identity("company-vfv-comparison-semantics", {
            "comparison_contract_version": self.comparison_contract_version,
            "comparison_basis_identity": self.comparison_basis_identity,
            "comparison_basis_version": self.comparison_basis_version,
            "comparison_semantics": self.comparison_semantics,
            "status": self.status,
            "reasons": self.reasons,
            "authority": self.authority,
            "company_problem_identity_version": (
                self.company_problem_identity_version),
            "company_problem_semantic_id": (
                self.company_problem_semantic_id),
            "company_basis": self.company_basis,
            "vfv_semantic_id": self.vfv_semantic_id,
            "vfv_basis": self.vfv_basis,
            "vfv_fx_hedge_semantic_id": self.vfv_fx_hedge_semantic_id,
            "vfv_fx_hedge_basis": self.vfv_fx_hedge_basis,
            "scenario_label_mapping": tuple(
                (label, label) for label in _SCENARIO_LABELS),
            "local_comparator_confidence": (
                self.local_comparator_confidence),
            "company_limitations": self.company_limitations,
            "vfv_inherited_limitations": self.vfv_inherited_limitations,
            "vfv_limitations": self.vfv_limitations,
            "vfv_fx_hedge_limitations": self.vfv_fx_hedge_limitations,
            "limitations": self.limitations,
        })

    @property
    def evidence_id(self) -> str:
        return _identity("company-vfv-comparison-evidence", {
            "semantic_id": self.semantic_id,
            "company_problem_evidence_id": (
                self.company_problem_evidence_id),
            "vfv_evidence_id": self.vfv_evidence_id,
            "vfv_fx_hedge_evidence_id": self.vfv_fx_hedge_evidence_id,
        })

    def to_dict(self) -> dict:
        payload = _canonical(self)
        payload["semantic_id"] = self.semantic_id
        payload["evidence_id"] = self.evidence_id
        return {"company_vfv_expected_return_comparison": payload}


def _canonical(value):
    if isinstance(value, Enum):
        return value.value
    if type(value) is float:
        if not math.isfinite(value):
            raise CompanyVFVComparatorError(
                "Non-finite output is not serializable")
        return value
    if is_dataclass(value):
        return {field.name: _canonical(getattr(value, field.name))
                for field in fields(value)}
    if isinstance(value, tuple):
        return [_canonical(item) for item in value]
    if isinstance(value, dict):
        return {key: _canonical(value[key]) for key in sorted(value)}
    if isinstance(value, Decimal):
        return str(value)
    return value


def _identity(domain: str, value) -> str:
    payload = json.dumps(
        _canonical(value), sort_keys=True, separators=(",", ":"),
        ensure_ascii=True, allow_nan=False,
    )
    return hashlib.sha256((domain + "\0" + payload).encode("utf-8")).hexdigest()


def _company_basis(
    company: pr5e.PR5EAdmissionResult,
) -> CompanyComparisonBasis | None:
    if (company.qualified_facts is None or company.construction is None
            or company.construction.diagnostic is None):
        return None
    diagnostic = company.construction.diagnostic
    roots = company.upstream_pr5d2
    return CompanyComparisonBasis(
        company.contract_version,
        company.adapter_version,
        company.construction.constructor_version,
        roots.semantic_id,
        diagnostic.methodology_version,
        diagnostic.return_basis,
        diagnostic.fx_basis,
        diagnostic.horizon_years,
        roots.quote_currency or "",
        roots.quote_unit or "",
        roots.accounting_basis or "",
        diagnostic.profile,
        ("VERIFIED_NONPAYER" if any(
            type(item) is pr5e.assumptions.VerifiedNonpayer
            for item in company.qualified_facts.roots) else "UNSUPPORTED"),
        roots.approved_policy_version or "",
        roots.approved_proposal_hash or "",
        company.construction.policy_hashes,
        diagnostic.overall_confidence,
    )


def identify_company_expected_return_problem(
    company: pr5e.PR5EAdmissionResult,
) -> CompanyExpectedReturnProblemIdentity:
    """Project PR5E onto stable comparator-owned problem/evidence identities."""
    if type(company) is not pr5e.PR5EAdmissionResult:
        raise CompanyVFVComparatorError("Exact PR5EAdmissionResult required")
    construction = company.construction
    diagnostic = None if construction is None else construction.diagnostic
    semantic = _identity("company-expected-return-problem-semantics", {
        "identity_representation_version": (
            COMPANY_VFV_PROBLEM_IDENTITY_VERSION),
        "status": company.status,
        "reasons": company.reasons,
        "company_basis": _company_basis(company),
        "pr5d2_semantic_id": company.upstream_pr5d2.semantic_id,
        "pr5e_contract_version": company.contract_version,
        "pr5e_adapter_version": company.adapter_version,
        "construction_status": (
            None if construction is None else construction.status),
        "construction_reasons": (
            () if construction is None else construction.reasons),
        "constructor_version": (
            None if construction is None else construction.constructor_version),
        "diagnostic_schema_version": (
            None if diagnostic is None else diagnostic.schema_version),
        "diagnostic_status": (
            None if diagnostic is None else diagnostic.status),
        "diagnostic_authority": (
            None if diagnostic is None else diagnostic.authority),
        "diagnostic_metric": (
            None if diagnostic is None else diagnostic.metric),
        "diagnostic_unavailable_reasons": (
            () if diagnostic is None else diagnostic.unavailable_reasons),
        "company_limitations": company.limitations,
    })
    evidence = _identity("company-expected-return-problem-evidence", {
        "semantic_id": semantic,
        "pr5d2_evidence_id": company.upstream_pr5d2.evidence_id,
    })
    return CompanyExpectedReturnProblemIdentity(
        COMPANY_VFV_PROBLEM_IDENTITY_VERSION, semantic, evidence)


def _vfv_basis(
    diagnostic: vfv_er.VFVForwardERDiagnostic,
) -> VFVComparisonBasis | None:
    if diagnostic.factual_inputs is None:
        return None
    facts = diagnostic.factual_inputs
    return VFVComparisonBasis(
        diagnostic.contract_version,
        diagnostic.semantic_id,
        diagnostic.policy_id,
        diagnostic.policy_hash,
        diagnostic.methodology_id,
        diagnostic.return_basis,
        diagnostic.fx_basis,
        diagnostic.horizon_years,
        facts.listed_currency,
        facts.base_currency,
        diagnostic.confidence.overall_vfv_er_confidence,
    )


def _fx_basis(
    evidence: fx_evidence.VFVFXHedgeEvidenceQualification,
) -> VFVFXHedgeComparisonBasis | None:
    values = (
        evidence.instrument_ticker, evidence.instrument_isin,
        evidence.listed_currency, evidence.base_currency,
        evidence.economic_exposure_currency, evidence.material_hedge_state,
        evidence.measurement_date, evidence.net_usd_exposure_percent_of_nav,
        evidence.exposure_unit, evidence.latest_captured_at,
        evidence.latest_reviewed_at,
    )
    if any(value is None for value in values):
        return None
    return VFVFXHedgeComparisonBasis(
        evidence.contract_version,
        evidence.semantic_id,
        evidence.instrument_ticker,
        evidence.instrument_isin,
        evidence.listed_currency,
        evidence.base_currency,
        evidence.economic_exposure_currency,
        evidence.material_hedge_state,
        evidence.measurement_date,
        evidence.net_usd_exposure_percent_of_nav,
        evidence.exposure_unit,
        evidence.authority_scope,
    )


def _result(
    company: pr5e.PR5EAdmissionResult,
    vfv: vfv_er.VFVForwardERDiagnostic,
    hedge: fx_evidence.VFVFXHedgeEvidenceQualification,
    *,
    status: CompanyVFVComparisonStatus,
    reasons: tuple[CompanyVFVComparisonReason, ...],
    spreads: tuple[SameLabelScenarioSpread, ...] = (),
) -> CompanyVFVComparisonResult:
    available = status is CompanyVFVComparisonStatus.AVAILABLE
    company_problem = identify_company_expected_return_problem(company)
    return CompanyVFVComparisonResult(
        COMPANY_VFV_COMPARISON_CONTRACT_VERSION,
        COMPANY_VFV_COMPARISON_BASIS_IDENTITY,
        COMPANY_VFV_COMPARISON_BASIS_VERSION,
        SAME_LABEL_SPREAD_SEMANTICS,
        status,
        tuple(sorted(set(reasons), key=lambda item: item.value)),
        COMPANY_VFV_COMPARISON_AUTHORITY,
        company_problem.identity_representation_version,
        company_problem.semantic_id,
        company_problem.evidence_id,
        company.admission_semantic_id,
        company.admission_evidence_id,
        _company_basis(company),
        vfv.semantic_id,
        vfv.evidence_id,
        _vfv_basis(vfv),
        hedge.semantic_id,
        hedge.evidence_id,
        _fx_basis(hedge),
        spreads if available else (),
        (CompanyVFVComparisonConfidence.LOW if available
         else CompanyVFVComparisonConfidence.NONE),
        company.limitations,
        vfv.inherited_limitations,
        vfv.limitations,
        hedge.limitations,
        _LIMITATIONS,
    )


def _company_policy_matches(company: pr5e.PR5EAdmissionResult) -> bool:
    if company.construction is None:
        return False
    approved = get_owner_approved_policy_proposal()
    proposal = approved.proposal
    expected_hashes = tuple(sorted((
        ("mature_growth", proposal.mature_policy.policy_hash),
        ("terminal_valuation", proposal.terminal_policy.policy_hash),
        ("distributions", proposal.nonpayer_distribution_policy.policy_hash),
    )))
    roots = company.upstream_pr5d2
    return (
        approved.proposal_hash == OWNER_APPROVED_PROPOSAL_HASH
        and proposal.proposal_id == OWNER_APPROVED_POLICY_VERSION
        and company.construction.policy_hashes == expected_hashes
        and roots.approved_policy_version == OWNER_APPROVED_POLICY_VERSION
        and roots.approved_proposal_hash == OWNER_APPROVED_PROPOSAL_HASH
        and roots.mature_policy_hash == proposal.mature_policy.policy_hash
        and roots.terminal_policy_hash == proposal.terminal_policy.policy_hash
        and roots.selected_nonpayer_distribution_policy_hash
        == proposal.nonpayer_distribution_policy.policy_hash
    )


def compare_company_vfv_expected_returns(
    company: pr5e.PR5EAdmissionResult,
    vfv: vfv_er.VFVForwardERDiagnostic,
    hedge: fx_evidence.VFVFXHedgeEvidenceQualification,
    request: CompanyVFVComparisonRequest,
) -> CompanyVFVComparisonResult:
    """Compare exact same-label annualized returns under the approved basis."""
    if type(company) is not pr5e.PR5EAdmissionResult:
        raise CompanyVFVComparatorError("Exact PR5EAdmissionResult required")
    if type(vfv) is not vfv_er.VFVForwardERDiagnostic:
        raise CompanyVFVComparatorError("Exact VFVForwardERDiagnostic required")
    if type(hedge) is not fx_evidence.VFVFXHedgeEvidenceQualification:
        raise CompanyVFVComparatorError(
            "Exact VFVFXHedgeEvidenceQualification required")
    if type(request) is not CompanyVFVComparisonRequest:
        raise CompanyVFVComparatorError(
            "Exact CompanyVFVComparisonRequest required")

    identity_reasons = []
    company_problem = identify_company_expected_return_problem(company)
    if (request.expected_company_problem_semantic_id
            != company_problem.semantic_id
            or request.expected_company_problem_evidence_id
            != company_problem.evidence_id):
        identity_reasons.append(
            CompanyVFVComparisonReason.COMPANY_IDENTITY_MISMATCH)
    if (request.expected_vfv_semantic_id != vfv.semantic_id
            or request.expected_vfv_evidence_id != vfv.evidence_id):
        identity_reasons.append(
            CompanyVFVComparisonReason.VFV_IDENTITY_MISMATCH)
    if (request.expected_vfv_fx_hedge_semantic_id != hedge.semantic_id
            or request.expected_vfv_fx_hedge_evidence_id != hedge.evidence_id):
        identity_reasons.append(
            CompanyVFVComparisonReason.FX_HEDGE_IDENTITY_MISMATCH)
    if identity_reasons:
        return _result(
            company, vfv, hedge,
            status=CompanyVFVComparisonStatus.SOURCE_CONFLICT,
            reasons=tuple(identity_reasons),
        )

    company_status_map = {
        pr5e.PR5EStatus.UNAVAILABLE: (
            CompanyVFVComparisonStatus.UNAVAILABLE,
            CompanyVFVComparisonReason.COMPANY_UPSTREAM_UNAVAILABLE),
        pr5e.PR5EStatus.UNSUPPORTED: (
            CompanyVFVComparisonStatus.UNSUPPORTED,
            CompanyVFVComparisonReason.COMPANY_UPSTREAM_UNSUPPORTED),
        pr5e.PR5EStatus.SOURCE_CONFLICT: (
            CompanyVFVComparisonStatus.SOURCE_CONFLICT,
            CompanyVFVComparisonReason.COMPANY_UPSTREAM_SOURCE_CONFLICT),
    }
    if company.status in company_status_map:
        status, reason = company_status_map[company.status]
        return _result(company, vfv, hedge, status=status, reasons=(reason,))
    vfv_status_map = {
        vfv_er.VFVForwardERStatus.UNAVAILABLE: (
            CompanyVFVComparisonStatus.UNAVAILABLE,
            CompanyVFVComparisonReason.VFV_UPSTREAM_UNAVAILABLE),
        vfv_er.VFVForwardERStatus.UNSUPPORTED: (
            CompanyVFVComparisonStatus.UNSUPPORTED,
            CompanyVFVComparisonReason.VFV_UPSTREAM_UNSUPPORTED),
        vfv_er.VFVForwardERStatus.SOURCE_CONFLICT: (
            CompanyVFVComparisonStatus.SOURCE_CONFLICT,
            CompanyVFVComparisonReason.VFV_UPSTREAM_SOURCE_CONFLICT),
    }
    if vfv.status in vfv_status_map:
        status, reason = vfv_status_map[vfv.status]
        return _result(company, vfv, hedge, status=status, reasons=(reason,))
    hedge_status_map = {
        fx_evidence.VFVFXHedgeEvidenceStatus.UNAVAILABLE: (
            CompanyVFVComparisonStatus.UNAVAILABLE,
            CompanyVFVComparisonReason.FX_HEDGE_EVIDENCE_UNAVAILABLE),
        fx_evidence.VFVFXHedgeEvidenceStatus.UNSUPPORTED: (
            CompanyVFVComparisonStatus.UNSUPPORTED,
            CompanyVFVComparisonReason.FX_HEDGE_EVIDENCE_UNSUPPORTED),
        fx_evidence.VFVFXHedgeEvidenceStatus.SOURCE_CONFLICT: (
            CompanyVFVComparisonStatus.SOURCE_CONFLICT,
            CompanyVFVComparisonReason.FX_HEDGE_SOURCE_CONFLICT),
    }
    if hedge.status in hedge_status_map:
        status, reason = hedge_status_map[hedge.status]
        return _result(company, vfv, hedge, status=status, reasons=(reason,))

    unsupported = set()
    unavailable = set()
    company_basis = _company_basis(company)
    if (company.status is not pr5e.PR5EStatus.REAL_EXPECTED_RETURN_ADMITTED
            or company_basis is None
            or company.contract_version != pr5e.CONTRACT_VERSION
            or company.adapter_version != pr5e.ADAPTER_VERSION
            or company.qualified_facts.contract_version
            != _COMPANY_REAL_FACTS_CONTRACT_VERSION
            or company.construction.constructor_version
            != _COMPANY_CONSTRUCTOR_VERSION
            or company_basis.methodology_id
            != _COMPANY_METHODOLOGY_ID):
        unsupported.add(
            CompanyVFVComparisonReason.COMPANY_ROUTE_UNSUPPORTED)
    else:
        diagnostic = company.construction.diagnostic
        roots = company.upstream_pr5d2
        if diagnostic.status not in {"AVAILABLE", "DEGRADED"}:
            unavailable.add(
                CompanyVFVComparisonReason.COMPANY_DIAGNOSTIC_UNAVAILABLE)
        if (roots.quote_currency != "USD" or diagnostic.currency != "USD"
                or roots.quote_unit != "CURRENCY_PER_SHARE"):
            unsupported.add(
                CompanyVFVComparisonReason.
                COMPANY_CURRENCY_BASIS_INCOMPATIBLE)
        if (roots.accounting_basis != "US_GAAP"
                or diagnostic.profile != "ORDINARY_COMPOUNDER"
                or roots.profile.profile != "ORDINARY_COMPOUNDER"):
            unsupported.add(
                CompanyVFVComparisonReason.
                COMPANY_ACCOUNTING_OR_PROFILE_UNSUPPORTED)
        company_roots = company.qualified_facts.roots
        if (sum(type(item) is pr5e.assumptions.VerifiedNonpayer
                for item in company_roots) != 1
                or any(type(item) is pr5e.assumptions.OrdinaryAnnualDividend
                       for item in company_roots)):
            unsupported.add(
                CompanyVFVComparisonReason.
                COMPANY_DISTRIBUTION_ROUTE_UNSUPPORTED)
        if diagnostic.return_basis != "NOMINAL_PRETAX_EQUITY_CASHFLOW_IRR":
            unsupported.add(
                CompanyVFVComparisonReason.COMPANY_RETURN_BASIS_INCOMPATIBLE)
        if diagnostic.fx_basis != "CONSTANT_FX":
            unsupported.add(
                CompanyVFVComparisonReason.COMPANY_FX_BASIS_INCOMPATIBLE)
        if diagnostic.horizon_years != 7:
            unsupported.add(
                CompanyVFVComparisonReason.COMPANY_HORIZON_INCOMPATIBLE)
        if not _company_policy_matches(company):
            unsupported.add(
                CompanyVFVComparisonReason.COMPANY_POLICY_IDENTITY_MISMATCH)

    vfv_basis = _vfv_basis(vfv)
    vfv_policy = get_approved_vfv_forward_er_policy()
    if vfv.status is not vfv_er.VFVForwardERStatus.AVAILABLE or vfv_basis is None:
        unavailable.add(CompanyVFVComparisonReason.VFV_UPSTREAM_UNAVAILABLE)
    else:
        if (vfv.policy_id != VFV_FORWARD_ER_POLICY_ID
                or vfv.policy_hash != vfv_policy.content_hash):
            unsupported.add(
                CompanyVFVComparisonReason.VFV_POLICY_IDENTITY_MISMATCH)
        if (vfv.methodology_id != VFV_FORWARD_ER_METHODOLOGY_ID
                or vfv.contract_version
                != vfv_er.VFV_FORWARD_ER_CONTRACT_VERSION):
            unsupported.add(
                CompanyVFVComparisonReason.VFV_METHODOLOGY_INCOMPATIBLE)
        if vfv.return_basis != VFV_FORWARD_ER_RETURN_TYPE:
            unsupported.add(
                CompanyVFVComparisonReason.VFV_RETURN_BASIS_INCOMPATIBLE)
        if vfv.fx_basis != VFV_FORWARD_ER_FX_BASIS:
            unsupported.add(
                CompanyVFVComparisonReason.VFV_FX_BASIS_INCOMPATIBLE)
        if vfv.horizon_years != VFV_FORWARD_ER_HORIZON_YEARS:
            unsupported.add(
                CompanyVFVComparisonReason.VFV_HORIZON_INCOMPATIBLE)

    hedge_basis = _fx_basis(hedge)
    if hedge.status is not fx_evidence.VFVFXHedgeEvidenceStatus.AVAILABLE \
            or hedge_basis is None:
        unavailable.add(
            CompanyVFVComparisonReason.FX_HEDGE_EVIDENCE_UNAVAILABLE)
    else:
        if (hedge.instrument_ticker != "VFV"
                or hedge.instrument_isin != "CA92205Y1051"
                or hedge.listed_currency != "CAD"
                or hedge.base_currency != "CAD"
                or hedge.economic_exposure_currency != "USD"):
            unsupported.add(
                CompanyVFVComparisonReason.
                FX_HEDGE_CURRENCY_BASIS_INCOMPATIBLE)
        if (hedge.material_hedge_state is not
                fx_evidence.VFVMaterialHedgeState.
                MATERIALLY_UNHEDGED_USD_EXPOSURE_TO_CAD_AT_DISCLOSURE_DATE
                or hedge.measurement_date != "2026-06-30"):
            unsupported.add(
                CompanyVFVComparisonReason.FX_HEDGE_STATE_INCOMPATIBLE)

    if unsupported:
        return _result(
            company, vfv, hedge,
            status=CompanyVFVComparisonStatus.UNSUPPORTED,
            reasons=tuple(unsupported),
        )
    if unavailable:
        return _result(
            company, vfv, hedge,
            status=CompanyVFVComparisonStatus.UNAVAILABLE,
            reasons=tuple(unavailable),
        )

    company_scenarios = company.construction.diagnostic.scenarios
    vfv_scenarios = vfv.scenarios
    if (len(company_scenarios) != 3 or len(vfv_scenarios) != 3
            or tuple(item.name for item in company_scenarios)
            != _SCENARIO_LABELS
            or tuple(item.name for item in vfv_scenarios)
            != _SCENARIO_LABELS):
        return _result(
            company, vfv, hedge,
            status=CompanyVFVComparisonStatus.UNAVAILABLE,
            reasons=(CompanyVFVComparisonReason.SCENARIO_LABELS_INCOMPLETE,),
        )
    numbers = tuple(
        value
        for company_scenario, vfv_scenario in zip(
            company_scenarios, vfv_scenarios)
        for value in (
            company_scenario.annualized_return,
            vfv_scenario.annualized_return,
        )
    )
    if any(type(value) is not float or not math.isfinite(value)
           for value in numbers):
        return _result(
            company, vfv, hedge,
            status=CompanyVFVComparisonStatus.UNAVAILABLE,
            reasons=(CompanyVFVComparisonReason.NUMERICAL_SPREAD_UNAVAILABLE,),
        )
    spreads = tuple(
        SameLabelScenarioSpread(
            company_scenario.name,
            company_scenario.annualized_return,
            vfv_scenario.annualized_return,
            company_scenario.annualized_return - vfv_scenario.annualized_return,
            SAME_LABEL_SPREAD_SEMANTICS,
        )
        for company_scenario, vfv_scenario in zip(
            company_scenarios, vfv_scenarios)
    )
    if any(not math.isfinite(item.spread) for item in spreads):
        return _result(
            company, vfv, hedge,
            status=CompanyVFVComparisonStatus.UNAVAILABLE,
            reasons=(CompanyVFVComparisonReason.NUMERICAL_SPREAD_UNAVAILABLE,),
        )
    return _result(
        company, vfv, hedge,
        status=CompanyVFVComparisonStatus.AVAILABLE,
        reasons=(), spreads=spreads,
    )
