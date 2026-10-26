"""Bounded D2 reported directions; authenticate Contract A before arithmetic."""
from dataclasses import asdict, dataclass
from decimal import Decimal
from enum import Enum
from fractions import Fraction
import sys
from typing import ClassVar

from src.current_annual_operating_income_to_positive_two_point_average_assets import _identity

CONTRACT_IDENTITY = 'STAGE_D_D2_TWO_PERIOD_REPORTED_TRAJECTORY_DIAGNOSTIC_V1'
CONTRACT_VERSION = '2026-10-26-d2-two-period-reported-trajectory-diagnostic-v1'
METHODOLOGY_VERSION = '2026-10-26-d2-exact-two-period-reported-trajectory-v1'
IDENTITY_VERSION = '2026-10-26-d2-analytical-identities-v1'
ANALYSIS_KIND = 'TWO_PERIOD_REPORTED_REVENUE_OPERATING_INCOME_TRAJECTORY'
AUTHORITY = 'DURABILITY_D2_TWO_PERIOD_REPORTED_TRAJECTORY_DIAGNOSTIC_ONLY'
CONCEPTS = ('RevenueFromContractWithCustomerExcludingAssessedTax', 'OperatingIncomeLoss')
LIMITATIONS = (
    'ONLY_TWO_SOURCE_REPORTED_ADJACENT_ANNUAL_OBSERVATIONS',
    'ONLY_BOTH_STRICTLY_POSITIVE_REVENUES_FOR_TRAJECTORY',
    'NO_RELATIVE_OPERATING_INCOME_GROWTH',
    'NO_ORGANIC_CONSTANT_CURRENCY_OR_NORMALIZED_GROWTH',
    'NO_OPERATIONAL_PERIMETER_OR_REPORTING_SUBJECT_CONTINUITY_CLAIM',
    'NO_FORWARD_PERSISTENCE_SUSTAINABLE_GROWTH_MOAT_OR_COMPETITIVE_ADVANTAGE',
    'NO_QUALITY_OR_AGGREGATE_DURABILITY_SCORE',
    'NO_CONFIDENCE_EXPECTED_RETURN_OR_INVESTMENT_ADMISSION_CHANGE',
    'NO_RECOMMENDATION_RANKING_SIZING_ALLOCATION_OR_EXECUTION',
    'NO_PRODUCTION_DEPLOYMENT_OR_V2_PROMOTION',
    'NO_PIT_OR_HISTORICAL_AS_OF_AUTHORITY',
    'NO_SOURCE_DATA_PUBLICATION_AUTHORITY',
    'UNAVAILABLE_IS_NOT_A_NEGATIVE_ISSUER_JUDGMENT',
    'V1_FROZEN_OPERATIONAL_AUTHORITY_V2_CHALLENGER',
)


class D2DiagnosticError(ValueError):
    """Invalid public input; never an ordinary descriptive status."""


class D2DiagnosticStatus(str, Enum):
    AVAILABLE = 'AVAILABLE'
    NOT_APPLICABLE = 'NOT_APPLICABLE'
    UNAVAILABLE = 'UNAVAILABLE'
    UNSUPPORTED = 'UNSUPPORTED'
    SOURCE_CONFLICT = 'SOURCE_CONFLICT'


class D2DiagnosticReason(str, Enum):
    UPSTREAM_EVIDENCE_UNAVAILABLE = 'UPSTREAM_EVIDENCE_UNAVAILABLE'
    UPSTREAM_EVIDENCE_UNSUPPORTED = 'UPSTREAM_EVIDENCE_UNSUPPORTED'
    UPSTREAM_SOURCE_CONFLICT = 'UPSTREAM_SOURCE_CONFLICT'
    PRIOR_REVENUE_ZERO = 'PRIOR_REVENUE_ZERO'
    CURRENT_REVENUE_ZERO = 'CURRENT_REVENUE_ZERO'
    PRIOR_REVENUE_NEGATIVE = 'PRIOR_REVENUE_NEGATIVE'
    CURRENT_REVENUE_NEGATIVE = 'CURRENT_REVENUE_NEGATIVE'


class ReportedDirection(str, Enum):
    INCREASED = 'INCREASED'
    UNCHANGED = 'UNCHANGED'
    DECREASED = 'DECREASED'


S = D2DiagnosticStatus
R = D2DiagnosticReason


@dataclass(frozen=True, slots=True)
class RevenueRelativeChange:
    """Exact reduced signed change; positive denominator and canonical zero."""
    numerator: int
    denominator: int

    def __post_init__(self):
        if (type(self.numerator) is not int or type(self.denominator) is not int
                or self.denominator == 0):
            raise D2DiagnosticError('Exact integers and nonzero denominator required')
        canonical = Fraction(self.numerator, self.denominator)
        object.__setattr__(self, 'numerator', canonical.numerator)
        object.__setattr__(self, 'denominator', canonical.denominator)


@dataclass(frozen=True, slots=True)
class D2TwoPeriodReportedTrajectoryResultV1:
    status: D2DiagnosticStatus
    reasons: tuple[D2DiagnosticReason, ...]
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
    revenue_direction: ReportedDirection | None
    operating_income_direction: ReportedDirection | None
    revenue_relative_change: RevenueRelativeChange | None
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
        raise D2DiagnosticError('Exact native two-period issuer qualification required')
    return module


def _direction(prior, current):
    return (ReportedDirection.INCREASED if current > prior else
            ReportedDirection.UNCHANGED if current == prior else ReportedDirection.DECREASED)


def analyze_d2_two_period_reported_trajectory_v1(qualification):
    """Replay the original bound source, then describe only reconstructed facts."""
    upstream = _canonical_upstream_module(qualification)
    verified = upstream._verified_comparative_snapshot(qualification)
    revenue_direction = operating_income_direction = relative_change = None
    established = verified.status is upstream.S.COMPARATIVE_ISSUER_REPORTED_FACTS_ESTABLISHED
    if established:
        reasons = []
        for value, zero, negative in (
            (verified.prior_revenue, R.PRIOR_REVENUE_ZERO, R.PRIOR_REVENUE_NEGATIVE),
            (verified.current_revenue, R.CURRENT_REVENUE_ZERO, R.CURRENT_REVENUE_NEGATIVE),
        ):
            if value <= 0:
                reasons.append(zero if value == 0 else negative)
        status = S.NOT_APPLICABLE if reasons else S.AVAILABLE
        reasons = tuple(sorted(reasons, key=lambda r: r.value))
        if status is S.AVAILABLE:
            revenue_direction = _direction(verified.prior_revenue, verified.current_revenue)
            operating_income_direction = _direction(
                verified.prior_operating_income, verified.current_operating_income)
            # Convert before subtraction: Decimal subtraction itself can round.
            prior = Fraction(verified.prior_revenue)
            change = (Fraction(verified.current_revenue) - prior) / prior
            relative_change = RevenueRelativeChange(change.numerator, change.denominator)
    else:
        status, reason = {
            upstream.S.EVIDENCE_UNAVAILABLE: (S.UNAVAILABLE, R.UPSTREAM_EVIDENCE_UNAVAILABLE),
            upstream.S.EVIDENCE_UNSUPPORTED: (S.UNSUPPORTED, R.UPSTREAM_EVIDENCE_UNSUPPORTED),
            upstream.S.SOURCE_CONFLICT: (S.SOURCE_CONFLICT, R.UPSTREAM_SOURCE_CONFLICT),
        }[verified.status]
        reasons = (reason,)
    return D2TwoPeriodReportedTrajectoryResultV1(
        status, reasons, verified.status, verified.reasons, verified.semantic_id, verified.evidence_id,
        verified.source_cik,
        verified.prior_period_start if established else None,
        verified.prior_period_end if established else None,
        verified.current_period_start if established else None,
        verified.current_period_end if established else None,
        verified.prior_revenue, verified.prior_operating_income,
        verified.current_revenue, verified.current_operating_income,
        revenue_direction, operating_income_direction, relative_change,
    )
