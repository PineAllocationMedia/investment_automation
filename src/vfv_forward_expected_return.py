"""Bounded standalone VFV forward Expected Return research diagnostic.

Only a canonical qualified VFV CURRENT evidence result and the one fixed
CEO-approved policy may enter this boundary.  This is not a company comparator,
generic ETF model, benchmark forecast, recommendation, or executable return.
"""
from __future__ import annotations

from dataclasses import dataclass, fields, is_dataclass
from decimal import (
    Context,
    Clamped,
    Decimal,
    DivisionByZero,
    FloatOperation,
    Inexact,
    InvalidOperation,
    Overflow,
    ROUND_HALF_EVEN,
    Rounded,
    Subnormal,
    Underflow,
    localcontext,
)
from enum import Enum, StrEnum
import hashlib
import json
import math
import re

from economic_facts import vfv_current_evidence as current

from .annual_cashflow_irr import AnnualCashFlowIRRError, solve_annual_cashflow_irr
from .vfv_forward_er_policy import (
    VFV_FORWARD_ER_FX_BASIS,
    VFV_FORWARD_ER_HORIZON_YEARS,
    VFV_FORWARD_ER_METHODOLOGY_ID,
    VFV_FORWARD_ER_POLICY_ID,
    VFV_FORWARD_ER_RETURN_TYPE,
    get_approved_vfv_forward_er_policy,
)


VFV_FORWARD_ER_CONTRACT_VERSION = "2026-10-01-vfv-forward-er-diagnostic-v1"
VFV_FORWARD_ER_ANALYTICAL_BASIS = "VFV_NORMALIZED_UNIT_HOLDER_CASHFLOW"
VFV_FORWARD_ER_AUTHORITY = "RESEARCH_DIAGNOSTIC_ONLY"
VFV_PRINCIPAL_RESULT_SEMANTICS = (
    "VFV_INSTRUMENT_ER_NET_OF_WRAPPER_EXPENSES_PRE_EXECUTION"
)
_HASH = re.compile(r"[0-9a-f]{64}")


def _new_vfv_decimal_context() -> Context:
    """Fresh code-owned context matching Python's intended default semantics.

    Never clone the ambient context: caller precision, rounding, exponent range,
    flags, and traps are not analytical inputs and cannot affect VFV results.
    """
    return Context(
        prec=28,
        rounding=ROUND_HALF_EVEN,
        Emin=-999999,
        Emax=999999,
        capitals=1,
        clamp=0,
        flags={
            InvalidOperation: False,
            FloatOperation: False,
            DivisionByZero: False,
            Overflow: False,
            Underflow: False,
            Subnormal: False,
            Inexact: False,
            Rounded: False,
            Clamped: False,
        },
        traps={
            InvalidOperation: True,
            FloatOperation: False,
            DivisionByZero: True,
            Overflow: True,
            Underflow: False,
            Subnormal: False,
            Inexact: False,
            Rounded: False,
            Clamped: False,
        },
    )


class VFVForwardERError(ValueError):
    """Malformed caller contract; economic absence uses a closed result status."""


class VFVForwardERStatus(StrEnum):
    AVAILABLE = "AVAILABLE"
    UNAVAILABLE = "UNAVAILABLE"
    UNSUPPORTED = "UNSUPPORTED"
    SOURCE_CONFLICT = "SOURCE_CONFLICT"


class VFVForwardERReason(StrEnum):
    UPSTREAM_UNAVAILABLE = "UPSTREAM_UNAVAILABLE"
    UPSTREAM_UNSUPPORTED = "UPSTREAM_UNSUPPORTED"
    UPSTREAM_SOURCE_CONFLICT = "UPSTREAM_SOURCE_CONFLICT"
    UPSTREAM_IDENTITY_MISMATCH = "UPSTREAM_IDENTITY_MISMATCH"
    APPROVED_POLICY_ID_MISMATCH = "APPROVED_POLICY_ID_MISMATCH"
    APPROVED_POLICY_HASH_MISMATCH = "APPROVED_POLICY_HASH_MISMATCH"
    NON_VFV_INSTRUMENT_UNSUPPORTED = "NON_VFV_INSTRUMENT_UNSUPPORTED"
    ANALYTICAL_BASIS_UNSUPPORTED = "ANALYTICAL_BASIS_UNSUPPORTED"
    EVIDENCE_SHAPE_UNSUPPORTED = "EVIDENCE_SHAPE_UNSUPPORTED"
    REQUIRED_FACT_ABSENT = "REQUIRED_FACT_ABSENT"
    REQUIRED_EXPENSE_SEMANTICS_UNAVAILABLE = (
        "REQUIRED_EXPENSE_SEMANTICS_UNAVAILABLE"
    )
    FACT_SEMANTICS_UNSUPPORTED = "FACT_SEMANTICS_UNSUPPORTED"
    CURRENCY_BASIS_UNSUPPORTED = "CURRENCY_BASIS_UNSUPPORTED"
    FACT_VALUE_UNAVAILABLE = "FACT_VALUE_UNAVAILABLE"
    NUMERICAL_REPRESENTATION_UNAVAILABLE = (
        "NUMERICAL_REPRESENTATION_UNAVAILABLE"
    )


class VFVForwardERConfidenceLevel(StrEnum):
    NONE = "NONE"
    LOW = "LOW"


class VFVForwardEREvidenceAuthority(StrEnum):
    NONE = "NONE"
    CURRENT_CAPTURE_BOUND = "CURRENT_CAPTURE_BOUND"


class VFVForwardERAssumptionDependence(StrEnum):
    NONE = "NONE"
    MATERIAL_FIXED_POLICY = "MATERIAL_FIXED_POLICY"


class VFVForwardERCurrencyBasisStatus(StrEnum):
    NONE = "NONE"
    CONSTANT_TRANSLATION_POLICY_ONLY_NO_FX_AUTHORITY = (
        "CONSTANT_TRANSLATION_POLICY_ONLY_NO_FX_AUTHORITY"
    )


class VFVForwardERLimitation(StrEnum):
    RESEARCH_DIAGNOSTIC_ONLY = "RESEARCH_DIAGNOSTIC_ONLY"
    CURRENT_ONLY_UPSTREAM_FACTUAL_AUTHORITY = (
        "CURRENT_ONLY_UPSTREAM_FACTUAL_AUTHORITY"
    )
    CAPTURE_BOUND_UPSTREAM_AVAILABILITY = (
        "CAPTURE_BOUND_UPSTREAM_AVAILABILITY"
    )
    NO_PIT_AUTHORITY = "NO_PIT_AUTHORITY"
    NO_HISTORICAL_AS_OF_AUTHORITY = "NO_HISTORICAL_AS_OF_AUTHORITY"
    NO_UNDERLYING_EXPOSURE_CURRENCY_AUTHORITY = (
        "NO_UNDERLYING_EXPOSURE_CURRENCY_AUTHORITY"
    )
    NO_CURRENCY_HEDGE_STATUS_AUTHORITY = "NO_CURRENCY_HEDGE_STATUS_AUTHORITY"
    NO_FX_COMPARABILITY_AUTHORITY = "NO_FX_COMPARABILITY_AUTHORITY"
    ZERO_FX_CONTRIBUTION_IS_STANDALONE_ANALYTICAL_POLICY_ONLY = (
        "ZERO_FX_CONTRIBUTION_IS_STANDALONE_ANALYTICAL_POLICY_ONLY"
    )
    NO_ACTUAL_REALIZED_CAD_FX_RETURN_CLAIM = (
        "NO_ACTUAL_REALIZED_CAD_FX_RETURN_CLAIM"
    )
    NO_PROVIDER_FORWARD_ESTIMATE_AUTHORITY = (
        "NO_PROVIDER_FORWARD_ESTIMATE_AUTHORITY"
    )
    NO_UNDERLYING_BENCHMARK_ER_AUTHORITY = (
        "NO_UNDERLYING_BENCHMARK_ER_AUTHORITY"
    )
    NO_EXECUTABLE_NET_ER_AUTHORITY = "NO_EXECUTABLE_NET_ER_AUTHORITY"
    NO_COMPANY_VS_VFV_COMPARATOR_AUTHORITY = (
        "NO_COMPANY_VS_VFV_COMPARATOR_AUTHORITY"
    )
    NO_RECOMMENDATION_OR_ALLOCATION = "NO_RECOMMENDATION_OR_ALLOCATION"
    NO_EXECUTION_OR_PRODUCTION_AUTHORITY = (
        "NO_EXECUTION_OR_PRODUCTION_AUTHORITY"
    )
    NO_GENERIC_ETF_AUTHORITY = "NO_GENERIC_ETF_AUTHORITY"


_LIMITATIONS = tuple(VFVForwardERLimitation)


@dataclass(frozen=True, slots=True)
class VFVForwardERRequest:
    instrument: str
    analytical_basis: str
    expected_upstream_semantic_id: str
    expected_upstream_evidence_id: str
    expected_policy_id: str
    expected_policy_hash: str

    def __post_init__(self):
        for name in ("instrument", "analytical_basis", "expected_policy_id"):
            value = getattr(self, name)
            if type(value) is not str or not value or value != value.strip():
                raise VFVForwardERError(f"{name}: nonempty trimmed string required")
        for name in ("expected_upstream_semantic_id",
                     "expected_upstream_evidence_id", "expected_policy_hash"):
            value = getattr(self, name)
            if type(value) is not str or _HASH.fullmatch(value) is None:
                raise VFVForwardERError(f"{name}: exact SHA-256 identity required")


@dataclass(frozen=True, slots=True)
class VFVForwardERConfidence:
    evidence_authority: VFVForwardEREvidenceAuthority
    forward_assumption_dependence: VFVForwardERAssumptionDependence
    currency_basis_status: VFVForwardERCurrencyBasisStatus
    overall_vfv_er_confidence: VFVForwardERConfidenceLevel


@dataclass(frozen=True, slots=True)
class VFVForwardERFactualInputs:
    fund_name: str
    security_unit_type: str
    primary_listing_exchange: str
    ticker: str
    isin: str
    listed_currency: str
    base_currency: str
    current_market_price: Decimal
    current_market_price_effective_as_of: str
    trailing_weighted_fund_portfolio_pe: Decimal
    trailing_weighted_pe_effective_as_of: str
    trailing_12_month_distribution_yield_percent: Decimal
    trailing_yield_effective_as_of: str
    management_fee_percent: Decimal
    mer_percent: Decimal
    ter_percent: Decimal
    mer_effective_as_of: str
    ter_effective_as_of: str


@dataclass(frozen=True, slots=True)
class VFVForwardERScenarioResult:
    name: str
    fundamental_growth: Decimal
    terminal_weighted_pe: Decimal
    normalized_initial_unit_value: Decimal
    annual_distributions: tuple[Decimal, ...]
    terminal_normalized_unit_value: Decimal
    annualized_return: float
    result_semantics: str


@dataclass(frozen=True, slots=True)
class VFVForwardERDiagnostic:
    contract_version: str
    status: VFVForwardERStatus
    reasons: tuple[str, ...]
    authority: str
    upstream_semantic_id: str
    upstream_evidence_id: str
    policy_id: str
    policy_hash: str
    methodology_id: str
    horizon_years: int
    return_basis: str
    fx_basis: str
    analytical_basis: str
    factual_inputs: VFVForwardERFactualInputs | None
    wrapper_expense_factor: Decimal | None
    scenarios: tuple[VFVForwardERScenarioResult, ...]
    underlying_benchmark_economic_er: None
    vfv_executable_net_er: None
    confidence: VFVForwardERConfidence
    fact_evidence: tuple[current.VFVFactEvidence, ...]
    inherited_limitations: tuple[current.VFVCurrentEvidenceLimitation, ...]
    limitations: tuple[VFVForwardERLimitation, ...]

    @property
    def semantic_id(self) -> str:
        return _identity("vfv-forward-er-semantics", {
            "contract_version": self.contract_version,
            "status": self.status,
            "reasons": self.reasons,
            "authority": self.authority,
            "upstream_semantic_id": self.upstream_semantic_id,
            "policy_id": self.policy_id,
            "policy_hash": self.policy_hash,
            "methodology_id": self.methodology_id,
            "horizon_years": self.horizon_years,
            "return_basis": self.return_basis,
            "fx_basis": self.fx_basis,
            "analytical_basis": self.analytical_basis,
            "factual_inputs": self.factual_inputs,
            "wrapper_expense_factor": self.wrapper_expense_factor,
            "scenarios": self.scenarios,
            "confidence": self.confidence,
            "inherited_limitations": self.inherited_limitations,
            "limitations": self.limitations,
        })

    @property
    def evidence_id(self) -> str:
        return _identity("vfv-forward-er-evidence", {
            "semantic_id": self.semantic_id,
            "upstream_evidence_id": self.upstream_evidence_id,
            "fact_evidence": self.fact_evidence,
        })

    def to_dict(self) -> dict:
        payload = _canonical(self)
        payload["semantic_id"] = self.semantic_id
        payload["evidence_id"] = self.evidence_id
        return {"vfv_forward_expected_return": payload}


def _canonical(value):
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Decimal):
        return str(value)
    if type(value) is float:
        if not math.isfinite(value):
            raise VFVForwardERError("Non-finite output is not serializable")
        return value
    if is_dataclass(value):
        return {field.name: _canonical(getattr(value, field.name))
                for field in fields(value)}
    if isinstance(value, tuple):
        return [_canonical(item) for item in value]
    if isinstance(value, dict):
        return {key: _canonical(value[key]) for key in sorted(value)}
    return value


def _identity(domain: str, value) -> str:
    payload = json.dumps(_canonical(value), sort_keys=True,
                         separators=(",", ":"), ensure_ascii=True,
                         allow_nan=False)
    return hashlib.sha256((domain + "\0" + payload).encode("utf-8")).hexdigest()


def _none_confidence() -> VFVForwardERConfidence:
    return VFVForwardERConfidence(
        VFVForwardEREvidenceAuthority.NONE,
        VFVForwardERAssumptionDependence.NONE,
        VFVForwardERCurrencyBasisStatus.NONE,
        VFVForwardERConfidenceLevel.NONE,
    )


def _low_confidence() -> VFVForwardERConfidence:
    return VFVForwardERConfidence(
        VFVForwardEREvidenceAuthority.CURRENT_CAPTURE_BOUND,
        VFVForwardERAssumptionDependence.MATERIAL_FIXED_POLICY,
        (VFVForwardERCurrencyBasisStatus.
         CONSTANT_TRANSLATION_POLICY_ONLY_NO_FX_AUTHORITY),
        VFVForwardERConfidenceLevel.LOW,
    )


def _result(
    qualification: current.VFVCurrentEvidenceQualification,
    *,
    status: VFVForwardERStatus,
    reasons: tuple[str, ...],
    factual_inputs: VFVForwardERFactualInputs | None = None,
    wrapper_expense_factor: Decimal | None = None,
    scenarios: tuple[VFVForwardERScenarioResult, ...] = (),
) -> VFVForwardERDiagnostic:
    policy = get_approved_vfv_forward_er_policy()
    return VFVForwardERDiagnostic(
        VFV_FORWARD_ER_CONTRACT_VERSION,
        status,
        tuple(sorted(set(reasons))),
        VFV_FORWARD_ER_AUTHORITY,
        qualification.semantic_id,
        qualification.evidence_id,
        policy.policy_id,
        policy.content_hash,
        policy.methodology_id,
        policy.horizon_years,
        policy.return_type,
        policy.fx_basis,
        VFV_FORWARD_ER_ANALYTICAL_BASIS,
        factual_inputs,
        wrapper_expense_factor,
        scenarios,
        None,
        None,
        _low_confidence() if status is VFVForwardERStatus.AVAILABLE
        else _none_confidence(),
        qualification.fact_evidence,
        qualification.limitations,
        _LIMITATIONS,
    )


def _upstream_failure(
    qualification: current.VFVCurrentEvidenceQualification,
) -> VFVForwardERDiagnostic | None:
    mapping = {
        current.VFVCurrentEvidenceStatus.UNAVAILABLE: (
            VFVForwardERStatus.UNAVAILABLE,
            VFVForwardERReason.UPSTREAM_UNAVAILABLE,
        ),
        current.VFVCurrentEvidenceStatus.UNSUPPORTED: (
            VFVForwardERStatus.UNSUPPORTED,
            VFVForwardERReason.UPSTREAM_UNSUPPORTED,
        ),
        current.VFVCurrentEvidenceStatus.SOURCE_CONFLICT: (
            VFVForwardERStatus.SOURCE_CONFLICT,
            VFVForwardERReason.UPSTREAM_SOURCE_CONFLICT,
        ),
    }
    mapped = mapping.get(qualification.status)
    if mapped is None:
        return None
    status, reason = mapped
    reasons = (reason.value, *("UPSTREAM:" + item.value
                               for item in qualification.reasons))
    return _result(qualification, status=status, reasons=reasons)


def _factual_inputs(
    qualification: current.VFVCurrentEvidenceQualification,
) -> tuple[VFVForwardERFactualInputs | None, VFVForwardERStatus | None,
           VFVForwardERReason | None]:
    if any(value is None for value in (
            qualification.identity,
            qualification.market_observation,
            qualification.expenses,
            qualification.distributions,
            qualification.trailing_valuation)):
        return None, VFVForwardERStatus.UNAVAILABLE, \
            VFVForwardERReason.REQUIRED_FACT_ABSENT
    identity = qualification.identity
    market = qualification.market_observation
    expenses = qualification.expenses
    distributions = qualification.distributions
    valuation = qualification.trailing_valuation
    if (identity.ticker != "VFV" or identity.isin != "CA92205Y1051"
            or identity.security_unit_type != "ETF Units"):
        return None, VFVForwardERStatus.UNSUPPORTED, \
            VFVForwardERReason.FACT_SEMANTICS_UNSUPPORTED
    if identity.listed_currency != "CAD" or identity.base_currency != "CAD" \
            or market.currency != "CAD":
        return None, VFVForwardERStatus.UNSUPPORTED, \
            VFVForwardERReason.CURRENCY_BASIS_UNSUPPORTED
    if (market.unit is not current.VFVFactUnit.CAD_PER_ETF_UNIT
            or distributions.trailing_yield_unit is not current.VFVFactUnit.PERCENT
            or expenses.management_fee_unit is not current.VFVFactUnit.PERCENT
            or expenses.mer_unit is not current.VFVFactUnit.PERCENT
            or expenses.ter_unit is not current.VFVFactUnit.PERCENT
            or distributions.trailing_yield_semantics is not
            current.VFVTrailingYieldSemantics.
            ISSUER_TRAILING_12_MONTH_DISTRIBUTION_YIELD
            or valuation.metric_subject is not
            current.VFVValuationMetricSubject.FUND_PORTFOLIO
            or valuation.metric_semantics is not
            current.VFVValuationMetricSemantics.PROVIDER_TRAILING_WEIGHTED_P_E):
        return None, VFVForwardERStatus.UNSUPPORTED, \
            VFVForwardERReason.FACT_SEMANTICS_UNSUPPORTED
    supported_expense_semantics = {
        current.VFVExpensePeriodSemantics.ANNUALIZED_PERCENTAGE_AS_OF_DATE,
        current.VFVExpensePeriodSemantics.ANNUAL_RATE_AS_OF_DATE,
    }
    if (expenses.mer_period_semantics not in supported_expense_semantics
            or expenses.ter_period_semantics not in supported_expense_semantics
            or expenses.mer_annualized is not True
            or expenses.ter_annualized is not True):
        return None, VFVForwardERStatus.UNAVAILABLE, \
            VFVForwardERReason.REQUIRED_EXPENSE_SEMANTICS_UNAVAILABLE
    required_roles = {
        current.VFVFactRole.FUND_NAME,
        current.VFVFactRole.SECURITY_UNIT_TYPE,
        current.VFVFactRole.PRIMARY_LISTING_EXCHANGE,
        current.VFVFactRole.TICKER,
        current.VFVFactRole.ISIN,
        current.VFVFactRole.LISTED_CURRENCY,
        current.VFVFactRole.BASE_CURRENCY,
        current.VFVFactRole.MARKET_PRICE,
        current.VFVFactRole.MANAGEMENT_FEE,
        current.VFVFactRole.MER,
        current.VFVFactRole.TER,
        current.VFVFactRole.TRAILING_DISTRIBUTION_YIELD,
        current.VFVFactRole.WEIGHTED_PE,
    }
    roles = [item.role for item in qualification.fact_evidence]
    if any(roles.count(role) != 1 for role in required_roles):
        return None, VFVForwardERStatus.UNSUPPORTED, \
            VFVForwardERReason.EVIDENCE_SHAPE_UNSUPPORTED
    values = (
        market.market_price,
        valuation.weighted_pe,
        distributions.trailing_distribution_yield,
        expenses.management_fee,
        expenses.mer,
        expenses.ter,
    )
    if any(type(value) is not Decimal or not value.is_finite() for value in values):
        return None, VFVForwardERStatus.UNAVAILABLE, \
            VFVForwardERReason.FACT_VALUE_UNAVAILABLE
    if (market.market_price <= 0 or valuation.weighted_pe <= 0
            or distributions.trailing_distribution_yield < 0
            or expenses.management_fee < 0 or expenses.mer < 0
            or expenses.ter < 0 or expenses.mer >= 100 or expenses.ter >= 100):
        return None, VFVForwardERStatus.UNAVAILABLE, \
            VFVForwardERReason.FACT_VALUE_UNAVAILABLE
    return VFVForwardERFactualInputs(
        identity.fund_name,
        identity.security_unit_type,
        identity.primary_listing_exchange,
        identity.ticker,
        identity.isin,
        identity.listed_currency,
        identity.base_currency,
        market.market_price,
        market.field_effective_as_of,
        valuation.weighted_pe,
        valuation.field_effective_as_of,
        distributions.trailing_distribution_yield,
        distributions.trailing_yield_effective_as_of,
        expenses.management_fee,
        expenses.mer,
        expenses.ter,
        expenses.mer_effective_as_of,
        expenses.ter_effective_as_of,
    ), None, None


def calculate_vfv_forward_expected_return(
    qualification: current.VFVCurrentEvidenceQualification,
    request: VFVForwardERRequest,
) -> VFVForwardERDiagnostic:
    """Calculate the fixed-policy standalone VFV diagnostic or fail closed."""
    if type(qualification) is not current.VFVCurrentEvidenceQualification:
        raise VFVForwardERError(
            "Exact VFVCurrentEvidenceQualification required")
    if type(request) is not VFVForwardERRequest:
        raise VFVForwardERError("Exact VFVForwardERRequest required")
    policy = get_approved_vfv_forward_er_policy()

    if request.instrument != "VFV":
        return _result(
            qualification,
            status=VFVForwardERStatus.UNSUPPORTED,
            reasons=(VFVForwardERReason.NON_VFV_INSTRUMENT_UNSUPPORTED.value,),
        )
    if request.analytical_basis != VFV_FORWARD_ER_ANALYTICAL_BASIS:
        return _result(
            qualification,
            status=VFVForwardERStatus.UNSUPPORTED,
            reasons=(VFVForwardERReason.ANALYTICAL_BASIS_UNSUPPORTED.value,),
        )
    if (request.expected_upstream_semantic_id != qualification.semantic_id
            or request.expected_upstream_evidence_id != qualification.evidence_id):
        return _result(
            qualification,
            status=VFVForwardERStatus.SOURCE_CONFLICT,
            reasons=(VFVForwardERReason.UPSTREAM_IDENTITY_MISMATCH.value,),
        )
    upstream_failure = _upstream_failure(qualification)
    if upstream_failure is not None:
        return upstream_failure
    if qualification.status is not current.VFVCurrentEvidenceStatus.AVAILABLE:
        return _result(
            qualification,
            status=VFVForwardERStatus.UNSUPPORTED,
            reasons=(VFVForwardERReason.EVIDENCE_SHAPE_UNSUPPORTED.value,),
        )
    if request.expected_policy_id != policy.policy_id:
        return _result(
            qualification,
            status=VFVForwardERStatus.UNAVAILABLE,
            reasons=(VFVForwardERReason.APPROVED_POLICY_ID_MISMATCH.value,),
        )
    if request.expected_policy_hash != policy.content_hash:
        return _result(
            qualification,
            status=VFVForwardERStatus.UNAVAILABLE,
            reasons=(VFVForwardERReason.APPROVED_POLICY_HASH_MISMATCH.value,),
        )

    factual, failure_status, failure_reason = _factual_inputs(qualification)
    if failure_status is not None:
        return _result(
            qualification,
            status=failure_status,
            reasons=(failure_reason.value,),
        )

    try:
        with localcontext(_new_vfv_decimal_context()):
            y0 = (factual.trailing_12_month_distribution_yield_percent
                  / Decimal(100))
            mer = factual.mer_percent / Decimal(100)
            ter = factual.ter_percent / Decimal(100)
            q = (Decimal(1) - mer) * (Decimal(1) - ter)
            m0 = factual.trailing_weighted_fund_portfolio_pe
            scenarios = []
            for policy_scenario in policy.scenarios:
                compounded = ((Decimal(1) + policy_scenario.fundamental_growth)
                              * q)
                distributions = tuple(
                    y0 if year == 1 else y0 * (compounded ** (year - 1))
                    for year in range(1, policy.horizon_years + 1)
                )
                terminal = ((compounded ** policy.horizon_years)
                            * (policy_scenario.terminal_weighted_pe / m0))
                annualized_return = solve_annual_cashflow_irr(
                    float(policy.normalized_initial_unit_value),
                    tuple(float(value) for value in distributions),
                    float(terminal),
                )
                scenarios.append(VFVForwardERScenarioResult(
                    policy_scenario.name,
                    policy_scenario.fundamental_growth,
                    policy_scenario.terminal_weighted_pe,
                    policy.normalized_initial_unit_value,
                    distributions,
                    terminal,
                    annualized_return,
                    VFV_PRINCIPAL_RESULT_SEMANTICS,
                ))
        if not all(math.isfinite(item.annualized_return) for item in scenarios):
            raise AnnualCashFlowIRRError("Non-finite scenario return")
        if not (scenarios[0].annualized_return <= scenarios[1].annualized_return
                <= scenarios[2].annualized_return):
            raise AnnualCashFlowIRRError("Scenario returns cross")
    except (AnnualCashFlowIRRError, InvalidOperation, OverflowError, ValueError):
        return _result(
            qualification,
            status=VFVForwardERStatus.UNAVAILABLE,
            reasons=(VFVForwardERReason.
                     NUMERICAL_REPRESENTATION_UNAVAILABLE.value,),
            factual_inputs=factual,
        )

    return _result(
        qualification,
        status=VFVForwardERStatus.AVAILABLE,
        reasons=(),
        factual_inputs=factual,
        wrapper_expense_factor=q,
        scenarios=tuple(scenarios),
    )
