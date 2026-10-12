"""Descriptive D1 operating-profit comparison, source replay before arithmetic.

REUSE the existing exact rational primitive and canonical Decimal identity
encoding; no dependency, acquisition, model rule or production integration.
"""
from dataclasses import asdict, dataclass
from decimal import Decimal
from enum import Enum
import sys
from typing import ClassVar

from src.current_annual_operating_income_to_positive_revenue import (
    OperatingIncomeToRevenueRatio, _ratio_from_decimals,
)
from src.current_annual_operating_income_to_positive_two_point_average_assets import _identity

CONCEPTS = ('RevenueFromContractWithCustomerExcludingAssessedTax', 'OperatingIncomeLoss')

CONTRACT_IDENTITY = 'STAGE_D_D1_TWO_PERIOD_OPERATING_PROFIT_CONTINUITY_DIAGNOSTIC_V1'
CONTRACT_VERSION = '2026-10-12-d1-two-period-operating-profit-continuity-diagnostic-v1'
METHODOLOGY_VERSION = '2026-10-12-d1-exact-two-period-reported-operating-profit-comparison-v1'
IDENTITY_VERSION = '2026-10-12-d1-analytical-identities-v1'
ANALYSIS_KIND = 'TWO_PERIOD_REPORTED_OPERATING_PROFIT_CONTINUITY'
AUTHORITY = 'DURABILITY_D1_REPORTED_OPERATING_PROFIT_COMPARISON_ONLY'
LIMITATIONS = (
    'ONLY_TWO_SOURCE_REPORTED_ANNUAL_OPERATING_PROFIT_OBSERVATIONS',
    'ONLY_POSITIVE_REVENUE_DENOMINATORS_FOR_RATIO_COMPARISON',
    'NO_MOAT_SWITCHING_COST_NETWORK_EFFECT_OR_PRICING_POWER',
    'NO_STRUCTURAL_RESILIENCE_NORMALIZED_PROFITABILITY_OR_BUSINESS_MODEL_SUPERIORITY',
    'NO_FUTURE_POSITIVE_OPERATING_INCOME_OR_EXPECTED_MARGIN',
    'NO_FULL_CYCLE_DURABILITY_OR_REINVESTMENT_RUNWAY',
    'NO_OVERALL_QUALITY_OR_AGGREGATE_DURABILITY_SCORE',
    'NO_CONFIDENCE_OR_EXPECTED_RETURN_CHANGE',
    'NO_PR5C_ORDINARY_COMPOUNDER_OR_SECURITY_ELIGIBILITY',
    'NO_RECOMMENDATION_RANKING_SIZING_ALLOCATION_OR_EXECUTION',
    'NO_PRODUCTION_DEPLOYMENT_OR_V2_PROMOTION',
    'NO_PIT_OR_HISTORICAL_AS_OF_AUTHORITY',
    'V1_FROZEN_OPERATIONAL_AUTHORITY_V2_CHALLENGER',
)


class D1DiagnosticError(ValueError):
    """Invalid analytical contract/input, never a descriptive negative result."""


class D1DiagnosticStatus(str, Enum):
    AVAILABLE = 'AVAILABLE'
    NOT_APPLICABLE = 'NOT_APPLICABLE'
    UNAVAILABLE = 'UNAVAILABLE'
    UNSUPPORTED = 'UNSUPPORTED'
    SOURCE_CONFLICT = 'SOURCE_CONFLICT'


class D1DiagnosticReason(str, Enum):
    UPSTREAM_EVIDENCE_UNAVAILABLE = 'UPSTREAM_EVIDENCE_UNAVAILABLE'
    UPSTREAM_EVIDENCE_UNSUPPORTED = 'UPSTREAM_EVIDENCE_UNSUPPORTED'
    UPSTREAM_SOURCE_CONFLICT = 'UPSTREAM_SOURCE_CONFLICT'
    PRIOR_REVENUE_ZERO_DENOMINATOR = 'PRIOR_REVENUE_ZERO_DENOMINATOR'
    CURRENT_REVENUE_ZERO_DENOMINATOR = 'CURRENT_REVENUE_ZERO_DENOMINATOR'
    PRIOR_REVENUE_NEGATIVE_NOT_POSITIVE_DENOMINATOR = 'PRIOR_REVENUE_NEGATIVE_NOT_POSITIVE_DENOMINATOR'
    CURRENT_REVENUE_NEGATIVE_NOT_POSITIVE_DENOMINATOR = 'CURRENT_REVENUE_NEGATIVE_NOT_POSITIVE_DENOMINATOR'


class OperatingIncomeSign(str, Enum):
    POSITIVE = 'POSITIVE'
    ZERO = 'ZERO'
    NEGATIVE = 'NEGATIVE'


class OperatingIncomeContinuity(str, Enum):
    POSITIVE_IN_BOTH_PERIODS = 'POSITIVE_IN_BOTH_PERIODS'
    POSITIVE_ONLY_IN_PRIOR_PERIOD = 'POSITIVE_ONLY_IN_PRIOR_PERIOD'
    POSITIVE_ONLY_IN_CURRENT_PERIOD = 'POSITIVE_ONLY_IN_CURRENT_PERIOD'
    POSITIVE_IN_NEITHER_PERIOD = 'POSITIVE_IN_NEITHER_PERIOD'


class RatioDirection(str, Enum):
    INCREASED = 'INCREASED'
    UNCHANGED = 'UNCHANGED'
    DECREASED = 'DECREASED'


S = D1DiagnosticStatus
R = D1DiagnosticReason


@dataclass(frozen=True, slots=True)
class D1TwoPeriodOperatingProfitContinuityResultV1:
    status: D1DiagnosticStatus
    reasons: tuple[D1DiagnosticReason, ...]
    upstream_status: Enum
    upstream_reasons: tuple[Enum, ...]
    upstream_qualification_semantic_id: str
    upstream_qualification_evidence_id: str
    source_cik: str
    prior_period_start: str | None
    prior_period_end: str | None
    current_period_start: str | None
    current_period_end: str | None
    prior_revenue: Decimal | None
    prior_operating_income: Decimal | None
    current_revenue: Decimal | None
    current_operating_income: Decimal | None
    prior_operating_income_sign: OperatingIncomeSign | None
    current_operating_income_sign: OperatingIncomeSign | None
    operating_income_sign_continuity: OperatingIncomeContinuity | None
    prior_operating_income_to_revenue_ratio: OperatingIncomeToRevenueRatio | None
    current_operating_income_to_revenue_ratio: OperatingIncomeToRevenueRatio | None
    ratio_difference: OperatingIncomeToRevenueRatio | None
    ratio_direction: RatioDirection | None
    contract_identity: ClassVar[str] = CONTRACT_IDENTITY
    contract_version: ClassVar[str] = CONTRACT_VERSION
    methodology_version: ClassVar[str] = METHODOLOGY_VERSION
    identity_version: ClassVar[str] = IDENTITY_VERSION
    analysis_kind: ClassVar[str] = ANALYSIS_KIND
    authority: ClassVar[str] = AUTHORITY
    limitations: ClassVar[tuple[str, ...]] = LIMITATIONS
    namespace: ClassVar[str] = 'us-gaap'
    concepts: ClassVar[tuple[str, ...]] = CONCEPTS
    accounting_basis: ClassVar[str] = 'US_GAAP'
    unit: ClassVar[str] = 'USD'
    temporal_mode: ClassVar[str] = 'CURRENT_CAPTURE_BOUND_ONLY'

    @property
    def semantic_id(self):
        result = asdict(self)
        del result['upstream_qualification_evidence_id']
        return _identity(IDENTITY_VERSION + ':semantic', {
            'contract_identity': CONTRACT_IDENTITY, 'contract_version': CONTRACT_VERSION,
            'identity_version': IDENTITY_VERSION, 'methodology': METHODOLOGY_VERSION,
            'kind': ANALYSIS_KIND, 'result': result, 'namespace': self.namespace,
            'concepts': CONCEPTS, 'basis': self.accounting_basis, 'unit': self.unit,
            'temporal': self.temporal_mode, 'authority': AUTHORITY, 'limitations': LIMITATIONS,
        })

    @property
    def evidence_id(self):
        return _identity(IDENTITY_VERSION + ':evidence', {
            'semantic_id': self.semantic_id,
            'upstream_evidence_id': self.upstream_qualification_evidence_id,
        })


def _canonical_upstream_module(qualification):
    name = 'economic_facts.sec_current_annual_issuer_two_period_revenue_operating_income'
    module = sys.modules.get(name)
    if (module is None or type(qualification).__module__ != name
            or type(qualification) is not getattr(
                module, 'CurrentAnnualIssuerTwoPeriodRevenueOperatingIncomeQualificationV1', None)):
        raise D1DiagnosticError('Exact native two-period issuer qualification required')
    return module


def _sign(value):
    return (OperatingIncomeSign.POSITIVE if value > 0 else
            OperatingIncomeSign.ZERO if value == 0 else OperatingIncomeSign.NEGATIVE)


def analyze_d1_two_period_operating_profit_continuity_v1(qualification):
    """Authenticate/replay the complete source; evaluate its reconstructed facts."""
    upstream = _canonical_upstream_module(qualification)
    verified = upstream._verified_comparative_snapshot(qualification)
    signs = (None, None)
    continuity = None
    ratios = (None, None)
    difference = direction = None
    established = verified.status is upstream.S.COMPARATIVE_ISSUER_REPORTED_FACTS_ESTABLISHED
    if established:
        signs = (_sign(verified.prior_operating_income), _sign(verified.current_operating_income))
        continuity = {
            (True, True): OperatingIncomeContinuity.POSITIVE_IN_BOTH_PERIODS,
            (True, False): OperatingIncomeContinuity.POSITIVE_ONLY_IN_PRIOR_PERIOD,
            (False, True): OperatingIncomeContinuity.POSITIVE_ONLY_IN_CURRENT_PERIOD,
            (False, False): OperatingIncomeContinuity.POSITIVE_IN_NEITHER_PERIOD,
        }[tuple(s is OperatingIncomeSign.POSITIVE for s in signs)]
        reasons = []
        for value, zero, negative in (
            (verified.prior_revenue, R.PRIOR_REVENUE_ZERO_DENOMINATOR,
             R.PRIOR_REVENUE_NEGATIVE_NOT_POSITIVE_DENOMINATOR),
            (verified.current_revenue, R.CURRENT_REVENUE_ZERO_DENOMINATOR,
             R.CURRENT_REVENUE_NEGATIVE_NOT_POSITIVE_DENOMINATOR),
        ):
            if value <= 0:
                reasons.append(zero if value == 0 else negative)
        status = S.NOT_APPLICABLE if reasons else S.AVAILABLE
        reasons = tuple(sorted(reasons, key=lambda r: r.value))
        if status is S.AVAILABLE:
            prior = _ratio_from_decimals(verified.prior_operating_income, verified.prior_revenue)
            current = _ratio_from_decimals(verified.current_operating_income, verified.current_revenue)
            ratios = (prior, current)
            difference = OperatingIncomeToRevenueRatio(
                current.numerator * prior.denominator - prior.numerator * current.denominator,
                prior.denominator * current.denominator,
            )
            direction = (RatioDirection.INCREASED if difference.numerator > 0 else
                         RatioDirection.UNCHANGED if difference.numerator == 0 else RatioDirection.DECREASED)
    else:
        status, reason = {
            upstream.S.EVIDENCE_UNAVAILABLE: (S.UNAVAILABLE, R.UPSTREAM_EVIDENCE_UNAVAILABLE),
            upstream.S.EVIDENCE_UNSUPPORTED: (S.UNSUPPORTED, R.UPSTREAM_EVIDENCE_UNSUPPORTED),
            upstream.S.SOURCE_CONFLICT: (S.SOURCE_CONFLICT, R.UPSTREAM_SOURCE_CONFLICT),
        }[verified.status]
        reasons = (reason,)
    return D1TwoPeriodOperatingProfitContinuityResultV1(
        status, reasons, verified.status, verified.reasons, verified.semantic_id, verified.evidence_id,
        verified.source_cik,
        verified.prior_period_start if established else None,
        verified.prior_period_end if established else None,
        verified.current_period_start if established else None,
        verified.current_period_end if established else None,
        verified.prior_revenue, verified.prior_operating_income,
        verified.current_revenue, verified.current_operating_income,
        *signs, continuity, *ratios, difference, direction,
    )
