"""CURRENT issuer research diagnosis with independent immutable-source replay.

The public boundary does read-only archive I/O; arithmetic is exact and pure.
This new route does not alter the legacy pure analyzer or admit investments.
"""
from dataclasses import asdict, dataclass
from enum import Enum
from typing import ClassVar
import sys

from src.current_annual_operating_income_to_positive_revenue import (
    OperatingIncomeToRevenueRatio, _ratio_from_decimals, _identity,
)

CONTRACT_IDENTITY = 'CURRENT_ANNUAL_ISSUER_OPERATING_INCOME_TO_POSITIVE_REVENUE_DIAGNOSTIC_V1'
CONTRACT_VERSION = '2026-10-12-current-annual-issuer-operating-income-to-positive-revenue-diagnostic-v1'
ROUTE = 'CURRENT_ANNUAL_ISSUER_REPORTED_PROFITABILITY_NATIVE_V1'
ANALYSIS_KIND = 'CURRENT_ANNUAL_OPERATING_INCOME_TO_POSITIVE_REVENUE'
METHODOLOGY_VERSION = '2026-10-08-exact-rational-operating-income-per-positive-revenue-v1'
IDENTITY_VERSION = '2026-10-12-issuer-operating-income-positive-revenue-identities-v1'
AUTHORITY = 'QUALITY_CURRENT_ISSUER_OPERATING_INCOME_TO_POSITIVE_REVENUE_DIAGNOSTIC_ONLY'
LIMITATIONS = (
    'ONLY_CURRENT_ISSUER_RESEARCH_OPERATING_INCOME_TO_POSITIVE_REVENUE',
    'NO_ORDINARY_COMPOUNDER_ELIGIBILITY_SECURITY_CLASS_OR_INVESTMENT_ADMISSION',
    'NO_EPS_COMPARABILITY_CORPORATE_ACTION_OR_SHARE_BASIS_CONTINUITY',
    'NO_CROSS_PERIOD_LEGAL_ENTITY_OR_REPORTING_SUBJECT_CONTINUITY',
    'NO_COMPLETE_ISSUER_COVERAGE_OR_ABSOLUTELY_NEWEST_PERIOD_CLAIM',
    'NO_UNIVERSAL_TOTAL_REVENUE_OR_CROSS_ISSUER_SECTOR_COMPARABILITY',
    'NO_NORMALIZED_PROFITABILITY_OR_GOOD_BAD_OVERALL_QUALITY',
    'NO_AGGREGATE_QUALITY_SCORE_PRICING_POWER_OR_MOAT',
    'NO_HISTORICAL_TREND_DURABILITY_OR_PERSISTENCE',
    'NO_EXPECTED_RETURN_OR_CONFIDENCE_CHANGE',
    'NO_RANKING_RECOMMENDATION_ALLOCATION_SIZING_OR_EXECUTION',
    'NO_PRODUCTION_DEPLOYMENT_OR_V2_PROMOTION',
    'NO_PUBLICATION_TIME_HISTORICAL_AVAILABILITY_PIT_OR_HISTORICAL_AS_OF',
    'NO_STAGE_C_EXIT_CREDIT_WITHOUT_CEO_OPTION_A_SUPPLEMENT',
)


class IssuerDiagnosticError(ValueError):
    """Invalid native input type or unavailable canonical module."""


def _canonical_upstream_module(qualification):
    # Existing native analyzer convention: no eager reverse dependency from src
    # into evidence. Only the loaded exact native type can select this fixed module.
    module_name = 'economic_facts.sec_current_annual_issuer_revenue_operating_income'
    module = sys.modules.get(module_name)
    if (module is None or type(qualification).__module__ != module_name
            or type(qualification) is not getattr(
                module, 'CurrentAnnualIssuerRevenueOperatingIncomeQualificationV1', None)):
        raise IssuerDiagnosticError('Exact native issuer qualification required')
    return module


class IssuerDiagnosticStatus(str, Enum):
    AVAILABLE = 'AVAILABLE'
    NOT_APPLICABLE = 'NOT_APPLICABLE'
    UNAVAILABLE = 'UNAVAILABLE'
    UNSUPPORTED = 'UNSUPPORTED'
    SOURCE_CONFLICT = 'SOURCE_CONFLICT'


class IssuerDiagnosticReason(str, Enum):
    UPSTREAM_EVIDENCE_UNAVAILABLE = 'UPSTREAM_EVIDENCE_UNAVAILABLE'
    UPSTREAM_EVIDENCE_UNSUPPORTED = 'UPSTREAM_EVIDENCE_UNSUPPORTED'
    UPSTREAM_SOURCE_CONFLICT = 'UPSTREAM_SOURCE_CONFLICT'
    REVENUE_ZERO_DENOMINATOR = 'REVENUE_ZERO_DENOMINATOR'
    REVENUE_NEGATIVE_NOT_POSITIVE_DENOMINATOR = 'REVENUE_NEGATIVE_NOT_POSITIVE_DENOMINATOR'


S = IssuerDiagnosticStatus
R = IssuerDiagnosticReason


@dataclass(frozen=True, slots=True)
class CurrentAnnualIssuerOperatingIncomeToPositiveRevenueResultV1:
    status: IssuerDiagnosticStatus
    reasons: tuple[IssuerDiagnosticReason, ...]
    upstream_status: Enum
    upstream_reasons: tuple[Enum, ...]
    source_cik: str
    period_start: str | None
    period_end: str | None
    upstream_qualification_semantic_id: str
    upstream_qualification_evidence_id: str
    operating_income_to_revenue_ratio: OperatingIncomeToRevenueRatio | None
    contract_identity: ClassVar[str] = CONTRACT_IDENTITY
    contract_version: ClassVar[str] = CONTRACT_VERSION
    route: ClassVar[str] = ROUTE
    analysis_kind: ClassVar[str] = ANALYSIS_KIND
    methodology_version: ClassVar[str] = METHODOLOGY_VERSION
    identity_version: ClassVar[str] = IDENTITY_VERSION
    authority: ClassVar[str] = AUTHORITY
    limitations: ClassVar[tuple[str, ...]] = LIMITATIONS
    namespace: ClassVar[str] = 'us-gaap'
    concepts: ClassVar[tuple[str, ...]] = (
        'RevenueFromContractWithCustomerExcludingAssessedTax', 'OperatingIncomeLoss',
    )
    accounting_basis: ClassVar[str] = 'US_GAAP'
    unit: ClassVar[str] = 'USD'
    temporal_mode: ClassVar[str] = 'CURRENT_CAPTURE_BOUND_ONLY'

    @property
    def semantic_id(self):
        public = asdict(self)
        del public['upstream_qualification_evidence_id']
        # The verified upstream semantic ID commits to both exact facts (not
        # merely their quotient), native reasons and material conflict values.
        return _identity(IDENTITY_VERSION + ':semantic', {
            'contract': CONTRACT_VERSION, 'contract_identity': CONTRACT_IDENTITY,
            'route': ROUTE, 'analysis_kind': ANALYSIS_KIND,
            'methodology': METHODOLOGY_VERSION, 'result': public,
            'namespace': self.namespace, 'concepts': self.concepts,
            'basis': self.accounting_basis, 'unit': self.unit,
            'temporal': self.temporal_mode, 'authority': AUTHORITY,
            'limitations': LIMITATIONS,
        })

    @property
    def evidence_id(self):
        return _identity(IDENTITY_VERSION + ':evidence', {
            'semantic_id': self.semantic_id,
            'upstream_evidence_id': self.upstream_qualification_evidence_id,
        })


def analyze_current_annual_issuer_operating_income_to_positive_revenue_v1(qualification):
    """Verify the full native evidence once; calculate only from that replay."""
    upstream = _canonical_upstream_module(qualification)
    verified = upstream._verified_issuer_snapshot(qualification)
    ratio = None
    if verified.status is upstream.S.PAIRED_ISSUER_REPORTED_FACTS_ESTABLISHED:
        if verified.revenue > 0:
            status, reasons = S.AVAILABLE, ()
            ratio = _ratio_from_decimals(verified.operating_income, verified.revenue)
        elif verified.revenue == 0:
            status, reasons = S.NOT_APPLICABLE, (R.REVENUE_ZERO_DENOMINATOR,)
        else:
            status, reasons = S.NOT_APPLICABLE, (R.REVENUE_NEGATIVE_NOT_POSITIVE_DENOMINATOR,)
    else:
        status, reason = {
            upstream.S.EVIDENCE_UNAVAILABLE: (S.UNAVAILABLE, R.UPSTREAM_EVIDENCE_UNAVAILABLE),
            upstream.S.EVIDENCE_UNSUPPORTED: (S.UNSUPPORTED, R.UPSTREAM_EVIDENCE_UNSUPPORTED),
            upstream.S.SOURCE_CONFLICT: (S.SOURCE_CONFLICT, R.UPSTREAM_SOURCE_CONFLICT),
        }[verified.status]
        reasons = (reason,)
    return CurrentAnnualIssuerOperatingIncomeToPositiveRevenueResultV1(
        status, reasons, verified.status, verified.reasons, verified.source_cik,
        verified.period_start, verified.period_end, verified.semantic_id,
        verified.evidence_id, ratio,
    )
