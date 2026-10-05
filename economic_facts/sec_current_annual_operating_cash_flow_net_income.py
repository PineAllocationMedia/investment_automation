"""CURRENT qualification for paired annual operating cash flow and net income.

The public boundary is one exact ``SecArchive`` plus one exact canonical
ordinary-compounder profile. The embedded route selects the issuer, annual
period, Companyfacts receipt, and immutable source object.
"""
from dataclasses import dataclass, fields, is_dataclass
from datetime import date
from decimal import Decimal
from enum import Enum, StrEnum
import hashlib
import json
import re

from .sec_archive import ArchiveError, CaptureReceipt, SecArchive
from .sec_current_eps_comparability_qualification import (
    ComparableEPSPeriodDecision,
    ComparabilityOutcome,
    PeriodOutcome,
    RealEPSComparabilityQualification,
)
from .sec_eps_series import ResolutionStatus
from .sec_operating_cash_flow_net_income import (
    NET_INCOME_CONCEPT,
    NAMESPACE,
    OPERATING_CASH_FLOW_CONCEPT,
    REVIEWED_UNIT,
    OperatingCashFlowNetIncomeObservation,
    extract_operating_cash_flow_net_income,
)
from . import sec_ordinary_compounder_profile as upstream


CONTRACT_VERSION = (
    "2026-10-05-current-annual-operating-cash-flow-net-income-qualification-v1"
)
QUALIFIER_VERSION = (
    "2026-10-05-paired-common-filing-exact-decimal-usd-qualification-v1"
)
EVIDENCE_KIND = (
    "CURRENT_ANNUAL_OPERATING_CASH_FLOW_NET_INCOME_QUALIFICATION"
)
ACCOUNTING_BASIS = "US_GAAP"
AUTHORITY = "QUALITY_CASH_CONVERSION_EVIDENCE_ONLY"


class CurrentAnnualOperatingCashFlowNetIncomeError(ValueError):
    """Wrong public type or contradictory canonical upstream object."""


class CurrentAnnualOperatingCashFlowNetIncomeStatus(StrEnum):
    PAIRED_OPERATING_CASH_FLOW_NET_INCOME_ESTABLISHED = (
        "PAIRED_OPERATING_CASH_FLOW_NET_INCOME_ESTABLISHED"
    )
    EVIDENCE_UNAVAILABLE = "EVIDENCE_UNAVAILABLE"
    EVIDENCE_UNSUPPORTED = "EVIDENCE_UNSUPPORTED"
    SOURCE_CONFLICT = "SOURCE_CONFLICT"


class CurrentAnnualOperatingCashFlowNetIncomeReason(StrEnum):
    UPSTREAM_PROFILE_UNAVAILABLE = "UPSTREAM_PROFILE_UNAVAILABLE"
    UPSTREAM_PROFILE_UNSUPPORTED = "UPSTREAM_PROFILE_UNSUPPORTED"
    UPSTREAM_SOURCE_CONFLICT = "UPSTREAM_SOURCE_CONFLICT"
    CANONICAL_ROUTE_IDENTITY_CONFLICT = "CANONICAL_ROUTE_IDENTITY_CONFLICT"
    CAPTURE_REPLAY_CONFLICT = "CAPTURE_REPLAY_CONFLICT"
    SOURCE_CIK_CONFLICT = "SOURCE_CIK_CONFLICT"
    OPERATING_CASH_FLOW_UNAVAILABLE = "OPERATING_CASH_FLOW_UNAVAILABLE"
    NET_INCOME_UNAVAILABLE = "NET_INCOME_UNAVAILABLE"
    EXACT_USD_UNIT_UNAVAILABLE = "EXACT_USD_UNIT_UNAVAILABLE"
    FINITE_OPERATING_CASH_FLOW_VALUE_UNAVAILABLE = (
        "FINITE_OPERATING_CASH_FLOW_VALUE_UNAVAILABLE"
    )
    FINITE_NET_INCOME_VALUE_UNAVAILABLE = (
        "FINITE_NET_INCOME_VALUE_UNAVAILABLE"
    )
    EXACT_ANNUAL_PERIOD_PRESENTATION_UNAVAILABLE = (
        "EXACT_ANNUAL_PERIOD_PRESENTATION_UNAVAILABLE"
    )
    NO_COMMON_ANNUAL_FILING_ACCESSION = "NO_COMMON_ANNUAL_FILING_ACCESSION"
    COMPETING_OPERATING_CASH_FLOW_VALUES = (
        "COMPETING_OPERATING_CASH_FLOW_VALUES"
    )
    COMPETING_NET_INCOME_VALUES = "COMPETING_NET_INCOME_VALUES"
    COMMON_FILING_METADATA_CONFLICT = "COMMON_FILING_METADATA_CONFLICT"


class CurrentAnnualOperatingCashFlowNetIncomeLimitation(StrEnum):
    ONLY_US_GAAP_NET_CASH_PROVIDED_BY_USED_IN_OPERATING_ACTIVITIES = (
        "ONLY_US_GAAP_NET_CASH_PROVIDED_BY_USED_IN_OPERATING_ACTIVITIES"
    )
    ONLY_US_GAAP_NET_INCOME_LOSS = "ONLY_US_GAAP_NET_INCOME_LOSS"
    NO_NON_GAAP_OR_NORMALIZED_EARNINGS_SUBSTITUTION = (
        "NO_NON_GAAP_OR_NORMALIZED_EARNINGS_SUBSTITUTION"
    )
    NO_FREE_CASH_FLOW_CLAIM = "NO_FREE_CASH_FLOW_CLAIM"
    NO_CAPEX_CLAIM = "NO_CAPEX_CLAIM"
    NO_CASH_CONVERSION_RATIO_OR_DIAGNOSTIC = (
        "NO_CASH_CONVERSION_RATIO_OR_DIAGNOSTIC"
    )
    NO_ACCRUALS_QUALITY_CONCLUSION = "NO_ACCRUALS_QUALITY_CONCLUSION"
    NO_WORKING_CAPITAL_CAUSAL_ATTRIBUTION = (
        "NO_WORKING_CAPITAL_CAUSAL_ATTRIBUTION"
    )
    NO_PROFITABILITY_QUALITY_CONCLUSION = (
        "NO_PROFITABILITY_QUALITY_CONCLUSION"
    )
    NO_HISTORICAL_CASH_CONVERSION_TREND = (
        "NO_HISTORICAL_CASH_CONVERSION_TREND"
    )
    NO_CROSS_SECTOR_COMPARABILITY = "NO_CROSS_SECTOR_COMPARABILITY"
    NO_DURABILITY_OR_PERSISTENCE_CONCLUSION = (
        "NO_DURABILITY_OR_PERSISTENCE_CONCLUSION"
    )
    NO_CONFIDENCE_CONCLUSION = "NO_CONFIDENCE_CONCLUSION"
    NO_EXPECTED_RETURN_EFFECT = "NO_EXPECTED_RETURN_EFFECT"
    NO_RECOMMENDATION_RANKING_ALLOCATION_OR_SIZING = (
        "NO_RECOMMENDATION_RANKING_ALLOCATION_OR_SIZING"
    )
    NO_EXECUTION_PRODUCTION_OR_V2_PROMOTION_AUTHORITY = (
        "NO_EXECUTION_PRODUCTION_OR_V2_PROMOTION_AUTHORITY"
    )
    NO_HISTORICAL_AS_OF_OR_PIT_AUTHORITY = (
        "NO_HISTORICAL_AS_OF_OR_PIT_AUTHORITY"
    )


_LIMITATIONS = tuple(CurrentAnnualOperatingCashFlowNetIncomeLimitation)
_HASH_LENGTH = 64
_ACCESSION_PATTERN = re.compile(r"[0-9]{10}-[0-9]{2}-[0-9]{6}")
_COMPARABILITY_CONTRACT_VERSION = (
    "2026-09-28-sec-current-eps-comparability-v1"
)
_COMPARABILITY_QUALIFIER_VERSION = (
    "2026-09-28-positive-five-period-presentation-v1"
)
_COMPARABILITY_MODE = "CURRENT_SEC_SINGLE_PRESENTATION_HISTORICAL_COMPARABILITY"


@dataclass(frozen=True, slots=True)
class OperatingCashFlowNetIncomeSupportingFiling:
    accession: str
    forms: tuple[str, ...]
    filed_dates: tuple[str, ...]
    fiscal_years: tuple[int, ...]
    operating_cash_flow_observation_ids: tuple[str, ...]
    net_income_observation_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class CurrentAnnualOperatingCashFlowNetIncomeQualification:
    contract_version: str
    qualifier_version: str
    evidence_kind: str
    status: CurrentAnnualOperatingCashFlowNetIncomeStatus
    reasons: tuple[CurrentAnnualOperatingCashFlowNetIncomeReason, ...]
    upstream_profile_status: upstream.OrdinaryCompounderProfileStatus
    upstream_profile_reasons: tuple[upstream.ProfileReason, ...]
    route_local_issuer_key: str | None
    route_local_security_key: str | None
    source_cik: str | None
    period_start: str | None
    period_end: str | None
    accounting_namespace: str
    accounting_basis: str
    operating_cash_flow_concept: str
    net_income_concept: str
    unit: str
    operating_cash_flow: Decimal | None
    net_income: Decimal | None
    upstream_profile_semantic_id: str
    upstream_comparability_semantic_id: str
    upstream_profile_evidence_id: str
    upstream_comparability_evidence_id: str
    capture_receipt_id: str | None
    source_object_hash: str | None
    captured_at: str | None
    capture_source_locator: str | None
    selected_operating_cash_flow_observation_ids: tuple[str, ...]
    selected_net_income_observation_ids: tuple[str, ...]
    supporting_accessions: tuple[str, ...]
    supporting_filings: tuple[OperatingCashFlowNetIncomeSupportingFiling, ...]
    authority: str
    limitations: tuple[CurrentAnnualOperatingCashFlowNetIncomeLimitation, ...]

    @property
    def semantic_id(self):
        return _identity(
            "current-annual-operating-cash-flow-net-income-semantics",
            {
                "contract_version": self.contract_version,
                "qualifier_version": self.qualifier_version,
                "evidence_kind": self.evidence_kind,
                "status": self.status,
                "reasons": self.reasons,
                "upstream_profile_status": self.upstream_profile_status,
                "upstream_profile_reasons": self.upstream_profile_reasons,
                "route_local_issuer_key": self.route_local_issuer_key,
                "route_local_security_key": self.route_local_security_key,
                "source_cik": self.source_cik,
                "upstream_profile_semantic_id": self.upstream_profile_semantic_id,
                "upstream_comparability_semantic_id": (
                    self.upstream_comparability_semantic_id
                ),
                "period_start": self.period_start,
                "period_end": self.period_end,
                "accounting_namespace": self.accounting_namespace,
                "accounting_basis": self.accounting_basis,
                "operating_cash_flow_concept": self.operating_cash_flow_concept,
                "net_income_concept": self.net_income_concept,
                "unit": self.unit,
                "operating_cash_flow": self.operating_cash_flow,
                "net_income": self.net_income,
                "authority": self.authority,
                "limitations": self.limitations,
            },
        )

    @property
    def evidence_id(self):
        return _identity(
            "current-annual-operating-cash-flow-net-income-evidence",
            {
                "semantic_id": self.semantic_id,
                "upstream_profile_evidence_id": self.upstream_profile_evidence_id,
                "upstream_comparability_evidence_id": (
                    self.upstream_comparability_evidence_id
                ),
                "capture_receipt_id": self.capture_receipt_id,
                "source_object_hash": self.source_object_hash,
                "captured_at": self.captured_at,
                "capture_source_locator": self.capture_source_locator,
                "selected_operating_cash_flow_observation_ids": (
                    self.selected_operating_cash_flow_observation_ids
                ),
                "selected_net_income_observation_ids": (
                    self.selected_net_income_observation_ids
                ),
                "supporting_accessions": self.supporting_accessions,
                "supporting_filings": self.supporting_filings,
            },
        )

    def to_dict(self):
        payload = _canonical(self)
        payload["semantic_id"] = self.semantic_id
        payload["evidence_id"] = self.evidence_id
        return {"current_annual_operating_cash_flow_net_income": payload}


def _canonical(value):
    if isinstance(value, Enum):
        return value.value
    if type(value) is Decimal:
        return _canonical_decimal(value)
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
    raise CurrentAnnualOperatingCashFlowNetIncomeError(
        "Unsupported paired-cash-flow identity value"
    )


def _canonical_decimal(value):
    """Project equal finite base-ten values identically without rounding."""
    if not value.is_finite():
        raise CurrentAnnualOperatingCashFlowNetIncomeError(
            "Finite Decimal identity value required"
        )
    sign, digits, exponent = value.as_tuple()
    digits = list(digits)
    if not any(digits):
        return {"sign": 0, "digits": [0], "exponent": 0}
    if exponent > 0:
        digits.extend([0] * exponent)
        exponent = 0
    while exponent < 0 and digits[-1] == 0:
        digits.pop()
        exponent += 1
    return {"sign": sign, "digits": digits, "exponent": exponent}


def _identity(domain, value):
    payload = json.dumps(
        _canonical(value),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    )
    return hashlib.sha256((domain + "\0" + payload).encode("utf-8")).hexdigest()


def _is_hash(value):
    return (
        type(value) is str
        and len(value) == _HASH_LENGTH
        and all(character in "0123456789abcdef" for character in value)
    )


def _ordered_reasons(reasons):
    return tuple(sorted(set(reasons), key=lambda item: item.value))


def _valid_date(value):
    if type(value) is not str:
        return False
    try:
        return date.fromisoformat(value).isoformat() == value
    except ValueError:
        return False


def _validate_profile_state_reasons(profile):
    reasons = profile.reasons
    reason = upstream.ProfileReason
    if reasons != tuple(sorted(set(reasons), key=lambda item: item.value)):
        raise CurrentAnnualOperatingCashFlowNetIncomeError(
            "Canonical native profile reasons required"
        )
    unavailable_reasons = frozenset({
        reason.PR5C_NOT_ESTABLISHED,
        reason.SIC_MISSING_OR_INVALID,
        reason.SIC_DESCRIPTION_MISSING_OR_INVALID,
        reason.POSITIVE_FIVE_PERIOD_ROUTE_NOT_ESTABLISHED,
        reason.REPORTING_SUBJECT_STABILITY_NOT_ESTABLISHED,
        reason.MIXED_STRUCTURE_UNRESOLVED,
    })
    decision_derived_reasons = frozenset({
        reason.POSITIVE_FIVE_PERIOD_ROUTE_NOT_ESTABLISHED,
        reason.REPORTING_SUBJECT_STABILITY_NOT_ESTABLISHED,
        reason.MIXED_STRUCTURE_UNRESOLVED,
        reason.UNSUPPORTED_SIC_PROFILE,
    })
    if profile.status is (
        upstream.OrdinaryCompounderProfileStatus.
        ORDINARY_COMPOUNDER_PROFILE_ESTABLISHED
    ):
        coherent = reasons == ()
    elif profile.status is upstream.OrdinaryCompounderProfileStatus.PROFILE_UNAVAILABLE:
        coherent = bool(reasons) and set(reasons) <= unavailable_reasons
    elif profile.status is upstream.OrdinaryCompounderProfileStatus.PROFILE_UNSUPPORTED:
        coherent = (
            reason.UNSUPPORTED_SIC_PROFILE in reasons
            and reason.REPLAY_IDENTITY_MISMATCH not in reasons
        )
    elif profile.status is upstream.OrdinaryCompounderProfileStatus.SOURCE_CONFLICT:
        coherent = (
            reason.REPLAY_IDENTITY_MISMATCH in reasons
            and reason.UNSUPPORTED_SIC_PROFILE not in reasons
        )
    else:
        coherent = False
    if (
        reason.SIC_DESCRIPTION_MISSING_OR_INVALID in reasons
        and set(reasons) & decision_derived_reasons
    ):
        coherent = False
    if (
        profile.status is upstream.OrdinaryCompounderProfileStatus.PROFILE_UNAVAILABLE
        and reason.POSITIVE_FIVE_PERIOD_ROUTE_NOT_ESTABLISHED in reasons
    ):
        coherent = False
    if not coherent:
        raise CurrentAnnualOperatingCashFlowNetIncomeError(
            "Canonical native profile status/reasons required"
        )


def _validate_profile_shape(profile):
    if (
        profile.contract_version != upstream.CONTRACT_VERSION
        or profile.qualifier_version != upstream.QUALIFIER_VERSION
        or profile.limitations != upstream.LIMITATIONS
    ):
        raise CurrentAnnualOperatingCashFlowNetIncomeError(
            "Canonical ordinary-compounder profile contract required"
        )
    if type(profile.status) is not upstream.OrdinaryCompounderProfileStatus:
        raise CurrentAnnualOperatingCashFlowNetIncomeError(
            "Unknown ordinary-compounder profile state"
        )
    if (
        type(profile.reasons) is not tuple
        or any(type(reason) is not upstream.ProfileReason for reason in profile.reasons)
        or type(profile.decisions) is not tuple
        or any(type(item) is not upstream.MethodProfileDecision
               for item in profile.decisions)
    ):
        raise CurrentAnnualOperatingCashFlowNetIncomeError(
            "Canonical ordinary-compounder profile details required"
        )
    if profile.sic is not None and type(profile.sic) is not int:
        raise CurrentAnnualOperatingCashFlowNetIncomeError(
            "Canonical ordinary-compounder SIC value required"
        )
    _validate_profile_state_reasons(profile)
    comparability = profile.upstream_comparability
    if type(comparability) is not RealEPSComparabilityQualification:
        raise CurrentAnnualOperatingCashFlowNetIncomeError(
            "Canonical embedded comparability required"
        )
    if (
        comparability.contract_version != _COMPARABILITY_CONTRACT_VERSION
        or comparability.qualifier_version != _COMPARABILITY_QUALIFIER_VERSION
        or comparability.qualification_mode != _COMPARABILITY_MODE
        or type(comparability.outcome) is not ComparabilityOutcome
        or type(comparability.reasons) is not tuple
    ):
        raise CurrentAnnualOperatingCashFlowNetIncomeError(
            "Canonical comparability contract required"
        )
    if any(not _is_hash(value) for value in (
        profile.semantic_id,
        profile.evidence_id,
        comparability.semantic_id,
        comparability.evidence_id,
    )):
        raise CurrentAnnualOperatingCashFlowNetIncomeError(
            "Canonical upstream identities required"
        )
    subject_cik = comparability.upstream_reporting_subject_source.source_cik
    if (
        type(profile.source_cik) is not str
        or re.fullmatch(r"[0-9]{10}", profile.source_cik) is None
        or profile.source_cik != subject_cik
        or (profile.profile is not None and profile.profile != upstream.PROFILE)
        or (
            profile.status is upstream.OrdinaryCompounderProfileStatus.
            ORDINARY_COMPOUNDER_PROFILE_ESTABLISHED
        ) != (profile.profile == upstream.PROFILE)
        or (profile.sic_description is not None and (
            type(profile.sic_description) is not str
            or not profile.sic_description
            or profile.sic_description != profile.sic_description.strip()
        ))
    ):
        raise CurrentAnnualOperatingCashFlowNetIncomeError(
            "Canonical ordinary-compounder profile context required"
        )
    metadata_present = profile.sic is not None and profile.sic_description is not None
    if metadata_present:
        if not _is_hash(profile.metadata_semantic_id) or not _is_hash(
            profile.metadata_evidence_id
        ):
            raise CurrentAnnualOperatingCashFlowNetIncomeError(
                "Canonical ordinary-compounder metadata identities required"
            )
    elif (
        profile.metadata_semantic_id is not None
        or profile.metadata_evidence_id is not None
    ):
        raise CurrentAnnualOperatingCashFlowNetIncomeError(
            "Impossible ordinary-compounder metadata identity surface"
        )
    expected_profiles = tuple(upstream.UnsupportedStructure)
    if metadata_present:
        if len(profile.decisions) != len(expected_profiles):
            raise CurrentAnnualOperatingCashFlowNetIncomeError(
                "Canonical method-profile decision inventory required"
            )
        for item, expected in zip(profile.decisions, expected_profiles, strict=True):
            if (
                type(item.profile) is not upstream.UnsupportedStructure
                or item.profile is not expected
                or type(item.decision) is not upstream.ProfileDecisionValue
                or type(item.reason) is not str
                or not item.reason
                or item.reason != item.reason.strip()
                or type(item.supporting_semantic_ids) is not tuple
                or any(not _is_hash(value) for value in item.supporting_semantic_ids)
                or type(item.supporting_evidence_ids) is not tuple
                or any(not _is_hash(value) for value in item.supporting_evidence_ids)
            ):
                raise CurrentAnnualOperatingCashFlowNetIncomeError(
                    "Canonical method-profile decisions required"
                )
    elif profile.decisions != ():
        raise CurrentAnnualOperatingCashFlowNetIncomeError(
            "Profile decisions require canonical SIC metadata"
        )
    return comparability


def _validate_established_profile(profile, comparability):
    security = comparability.upstream_security_eps
    if (
        profile.profile != upstream.PROFILE
        or profile.reasons != ()
        or type(profile.sic) is not int
        or not 100 <= profile.sic <= 9999
        or type(profile.sic_description) is not str
        or any(
            item.decision is not upstream.ProfileDecisionValue.EXCLUDED
            for item in profile.decisions
        )
        or comparability.outcome is not ComparabilityOutcome.COMPARABLE_REAL_EPS_ESTABLISHED
        or comparability.reasons != ()
        or not _is_hash(comparability.route_local_issuer_key)
        or not _is_hash(comparability.route_local_security_key)
        or comparability.route_local_issuer_key != security.route_local_issuer_key
        or comparability.route_local_security_key != security.route_local_security_key
    ):
        raise CurrentAnnualOperatingCashFlowNetIncomeError(
            "Contradictory established ordinary-compounder profile"
        )


def _target_period(comparability, *, require_established):
    periods = comparability.period_decisions
    if (
        type(periods) is not tuple
        or any(type(item) is not ComparableEPSPeriodDecision for item in periods)
    ):
        raise CurrentAnnualOperatingCashFlowNetIncomeError(
            "Canonical comparable periods required"
        )
    if not periods:
        if require_established:
            raise CurrentAnnualOperatingCashFlowNetIncomeError(
                "Established profile requires comparable annual periods"
            )
        return None, None
    try:
        period_dates = tuple(
            (date.fromisoformat(item.period_start), date.fromisoformat(item.period_end))
            for item in periods
        )
    except (TypeError, ValueError) as exc:
        raise CurrentAnnualOperatingCashFlowNetIncomeError(
            "Canonical annual period dates required"
        ) from exc
    ordered = tuple(sorted(periods, key=lambda item: item.period_end))
    if require_established and (
        comparability.outcome is not ComparabilityOutcome.COMPARABLE_REAL_EPS_ESTABLISHED
        or comparability.reasons != ()
        or len(ordered) != 5
        or ordered != periods
        or len({item.period_end for item in periods}) != 5
        or any(
            prior_start >= current_start or prior_end >= current_end
            for (prior_start, prior_end), (current_start, current_end)
            in zip(period_dates, period_dates[1:])
        )
        or any(
            item.outcome is not PeriodOutcome.EXACT_MATCH
            or item.reasons != ()
            or type(item.c3_value) is not Decimal
            or not item.c3_value.is_finite()
            or item.c3_value <= 0
            or type(item.presented_value) is not Decimal
            or item.presented_value != item.c3_value
            for item in ordered
        )
    ):
        raise CurrentAnnualOperatingCashFlowNetIncomeError(
            "Contradictory established comparability"
        )
    latest = ordered[-1]
    start, end = period_dates[-1]
    if start > end:
        raise CurrentAnnualOperatingCashFlowNetIncomeError(
            "Canonical annual period order required"
        )
    return latest.period_start, latest.period_end


def _route_context(profile, comparability):
    security = comparability.upstream_security_eps
    issuer_key = comparability.route_local_issuer_key
    security_key = comparability.route_local_security_key
    subject_cik = comparability.upstream_reporting_subject_source.source_cik
    conflict = (
        issuer_key != security.route_local_issuer_key
        or security_key != security.route_local_security_key
        or any(value is not None and not _is_hash(value)
               for value in (issuer_key, security_key))
        or profile.source_cik != subject_cik
    )
    try:
        current = (
            security.upstream_registered_listing_bridge.temporal_boundary
            .current_evidence
        )
        receipt = current.receipt
    except AttributeError:
        return issuer_key, security_key, subject_cik, None, True
    if receipt is not None and type(receipt) is not CaptureReceipt:
        return issuer_key, security_key, subject_cik, None, True
    if receipt is not None:
        series = current.resolution.series
        if (
            subject_cik != receipt.cik
            or current.request.cik != receipt.cik
            or current.request.receipt_id != receipt.receipt_id
            or current.resolution.status is not ResolutionStatus.RESOLVED_ISSUER_EVIDENCE
            or series is None
            or series.cik != receipt.cik
            or series.receipt_ids != (receipt.receipt_id,)
            or series.object_hashes != (receipt.content_sha256,)
        ):
            conflict = True
    return issuer_key, security_key, subject_cik, receipt, conflict


def _result(
    profile,
    comparability,
    *,
    status,
    reasons,
    period_start,
    period_end,
    source_cik,
    receipt=None,
    operating_cash_flow=None,
    net_income=None,
    operating_cash_flow_ids=(),
    net_income_ids=(),
    accessions=(),
    filings=(),
):
    if status is not (
        CurrentAnnualOperatingCashFlowNetIncomeStatus.
        PAIRED_OPERATING_CASH_FLOW_NET_INCOME_ESTABLISHED
    ):
        operating_cash_flow = None
        net_income = None
        operating_cash_flow_ids = ()
        net_income_ids = ()
        accessions = ()
        filings = ()
    return CurrentAnnualOperatingCashFlowNetIncomeQualification(
        CONTRACT_VERSION,
        QUALIFIER_VERSION,
        EVIDENCE_KIND,
        status,
        _ordered_reasons(reasons),
        profile.status,
        profile.reasons,
        comparability.route_local_issuer_key,
        comparability.route_local_security_key,
        source_cik,
        period_start,
        period_end,
        NAMESPACE,
        ACCOUNTING_BASIS,
        OPERATING_CASH_FLOW_CONCEPT,
        NET_INCOME_CONCEPT,
        REVIEWED_UNIT,
        operating_cash_flow,
        net_income,
        profile.semantic_id,
        comparability.semantic_id,
        profile.evidence_id,
        comparability.evidence_id,
        None if receipt is None else receipt.receipt_id,
        None if receipt is None else receipt.content_sha256,
        None if receipt is None else receipt.captured_at,
        None if receipt is None else receipt.source_locator,
        tuple(operating_cash_flow_ids),
        tuple(net_income_ids),
        tuple(accessions),
        tuple(filings),
        AUTHORITY,
        _LIMITATIONS,
    )


def _upstream_status(profile):
    mapping = {
        upstream.OrdinaryCompounderProfileStatus.PROFILE_UNAVAILABLE: (
            CurrentAnnualOperatingCashFlowNetIncomeStatus.EVIDENCE_UNAVAILABLE,
            CurrentAnnualOperatingCashFlowNetIncomeReason.UPSTREAM_PROFILE_UNAVAILABLE,
        ),
        upstream.OrdinaryCompounderProfileStatus.PROFILE_UNSUPPORTED: (
            CurrentAnnualOperatingCashFlowNetIncomeStatus.EVIDENCE_UNSUPPORTED,
            CurrentAnnualOperatingCashFlowNetIncomeReason.UPSTREAM_PROFILE_UNSUPPORTED,
        ),
        upstream.OrdinaryCompounderProfileStatus.SOURCE_CONFLICT: (
            CurrentAnnualOperatingCashFlowNetIncomeStatus.SOURCE_CONFLICT,
            CurrentAnnualOperatingCashFlowNetIncomeReason.UPSTREAM_SOURCE_CONFLICT,
        ),
    }
    return mapping.get(profile.status)


def _eligible(observation, *, concept, cik, period_start, period_end):
    return (
        type(observation) is OperatingCashFlowNetIncomeObservation
        and observation.source_cik == cik
        and observation.namespace == NAMESPACE
        and observation.concept == concept
        and observation.unit == REVIEWED_UNIT
        and type(observation.value) is Decimal
        and observation.value.is_finite()
        and observation.start == period_start
        and observation.end == period_end
        and type(observation.fy) is int
        and observation.fp == "FY"
        and observation.form in ("10-K", "10-K/A")
        and _valid_date(observation.filed)
        and type(observation.accession) is str
        and _ACCESSION_PATTERN.fullmatch(observation.accession) is not None
        and observation.metadata_limitations == ()
    )


def _supporting_filings(operating_rows, net_income_rows, accessions):
    filings = []
    for accession in accessions:
        operating = tuple(row for row in operating_rows if row.accession == accession)
        income = tuple(row for row in net_income_rows if row.accession == accession)
        rows = operating + income
        filings.append(OperatingCashFlowNetIncomeSupportingFiling(
            accession,
            tuple(sorted({row.form for row in rows})),
            tuple(sorted({row.filed for row in rows})),
            tuple(sorted({row.fy for row in rows})),
            tuple(sorted(row.observation_id for row in operating)),
            tuple(sorted(row.observation_id for row in income)),
        ))
    return tuple(filings)


def _validate_supporting_provenance(
    operating_rows,
    net_income_rows,
    accessions,
    filings,
):
    operating_ids = tuple(sorted(row.observation_id for row in operating_rows))
    net_income_ids = tuple(sorted(row.observation_id for row in net_income_rows))
    if (
        accessions != tuple(sorted(set(accessions)))
        or not accessions
        or len(filings) != len(accessions)
        or tuple(item.accession for item in filings) != accessions
        or operating_ids != tuple(sorted(set(operating_ids)))
        or net_income_ids != tuple(sorted(set(net_income_ids)))
        or set(operating_ids) & set(net_income_ids)
    ):
        raise CurrentAnnualOperatingCashFlowNetIncomeError(
            "Canonical selected observation partition required"
        )
    flattened_operating = []
    flattened_income = []
    for filing in filings:
        if (
            type(filing) is not OperatingCashFlowNetIncomeSupportingFiling
            or _ACCESSION_PATTERN.fullmatch(filing.accession) is None
            or len(filing.forms) != 1
            or filing.forms[0] not in ("10-K", "10-K/A")
            or len(filing.filed_dates) != 1
            or not _valid_date(filing.filed_dates[0])
            or len(filing.fiscal_years) != 1
            or type(filing.fiscal_years[0]) is not int
            or not filing.operating_cash_flow_observation_ids
            or filing.operating_cash_flow_observation_ids
            != tuple(sorted(set(filing.operating_cash_flow_observation_ids)))
            or not filing.net_income_observation_ids
            or filing.net_income_observation_ids
            != tuple(sorted(set(filing.net_income_observation_ids)))
            or set(filing.operating_cash_flow_observation_ids)
            & set(filing.net_income_observation_ids)
            or any(not _is_hash(value) for value in (
                filing.operating_cash_flow_observation_ids
                + filing.net_income_observation_ids
            ))
        ):
            raise CurrentAnnualOperatingCashFlowNetIncomeError(
                "Canonical supporting filing provenance required"
            )
        expected_operating = tuple(sorted(
            row.observation_id
            for row in operating_rows
            if row.accession == filing.accession
        ))
        expected_income = tuple(sorted(
            row.observation_id
            for row in net_income_rows
            if row.accession == filing.accession
        ))
        if (
            filing.operating_cash_flow_observation_ids != expected_operating
            or filing.net_income_observation_ids != expected_income
        ):
            raise CurrentAnnualOperatingCashFlowNetIncomeError(
                "Supporting filing observation partition mismatch"
            )
        flattened_operating.extend(filing.operating_cash_flow_observation_ids)
        flattened_income.extend(filing.net_income_observation_ids)
    if (
        tuple(sorted(flattened_operating)) != operating_ids
        or tuple(sorted(flattened_income)) != net_income_ids
        or len(flattened_operating) != len(set(flattened_operating))
        or len(flattened_income) != len(set(flattened_income))
    ):
        raise CurrentAnnualOperatingCashFlowNetIncomeError(
            "Exact selected observation partition required"
        )


def qualify_sec_current_annual_operating_cash_flow_net_income(
    archive: SecArchive,
    profile: upstream.OrdinaryCompounderMethodProfileQualification,
) -> CurrentAnnualOperatingCashFlowNetIncomeQualification:
    """Qualify one exact annual OCF/net-income pair without analysis."""
    if (
        type(archive) is not SecArchive
        or type(profile) is not upstream.OrdinaryCompounderMethodProfileQualification
    ):
        raise CurrentAnnualOperatingCashFlowNetIncomeError(
            "Exact SecArchive and OrdinaryCompounderMethodProfileQualification required"
        )
    comparability = _validate_profile_shape(profile)
    established = (
        profile.status is upstream.OrdinaryCompounderProfileStatus.
        ORDINARY_COMPOUNDER_PROFILE_ESTABLISHED
    )
    if established:
        _validate_established_profile(profile, comparability)
    period_start, period_end = _target_period(
        comparability, require_established=established
    )
    issuer_key, security_key, source_cik, receipt, route_conflict = _route_context(
        profile, comparability
    )
    mapped = _upstream_status(profile)
    if mapped is not None:
        if route_conflict:
            raise CurrentAnnualOperatingCashFlowNetIncomeError(
                "Impossible reconstructed non-established profile route"
            )
        status, reason = mapped
        return _result(
            profile,
            comparability,
            status=status,
            reasons=(reason,),
            period_start=period_start,
            period_end=period_end,
            source_cik=source_cik,
            receipt=receipt,
        )
    if not established:
        raise CurrentAnnualOperatingCashFlowNetIncomeError(
            "Unknown ordinary-compounder profile state"
        )
    if route_conflict or receipt is None or issuer_key is None or security_key is None:
        return _result(
            profile,
            comparability,
            status=CurrentAnnualOperatingCashFlowNetIncomeStatus.SOURCE_CONFLICT,
            reasons=(
                CurrentAnnualOperatingCashFlowNetIncomeReason.
                CANONICAL_ROUTE_IDENTITY_CONFLICT,
            ),
            period_start=period_start,
            period_end=period_end,
            source_cik=source_cik,
            receipt=receipt,
        )

    try:
        stored = archive.read_receipt(receipt.receipt_id)
        if stored != receipt:
            raise ArchiveError("Embedded receipt differs from archive receipt")
        raw = archive.read_object(stored)
        extraction = extract_operating_cash_flow_net_income(raw, stored)
    except (ArchiveError, OSError):
        return _result(
            profile,
            comparability,
            status=CurrentAnnualOperatingCashFlowNetIncomeStatus.SOURCE_CONFLICT,
            reasons=(
                CurrentAnnualOperatingCashFlowNetIncomeReason.CAPTURE_REPLAY_CONFLICT,
            ),
            period_start=period_start,
            period_end=period_end,
            source_cik=source_cik,
            receipt=receipt,
        )
    if extraction.source_cik != source_cik:
        return _result(
            profile,
            comparability,
            status=CurrentAnnualOperatingCashFlowNetIncomeStatus.SOURCE_CONFLICT,
            reasons=(CurrentAnnualOperatingCashFlowNetIncomeReason.SOURCE_CIK_CONFLICT,),
            period_start=period_start,
            period_end=period_end,
            source_cik=source_cik,
            receipt=receipt,
        )

    all_operating = tuple(
        row for row in extraction.observations
        if row.concept == OPERATING_CASH_FLOW_CONCEPT
    )
    all_income = tuple(
        row for row in extraction.observations
        if row.concept == NET_INCOME_CONCEPT
    )
    usd_operating = tuple(row for row in all_operating if row.unit == REVIEWED_UNIT)
    usd_income = tuple(row for row in all_income if row.unit == REVIEWED_UNIT)
    finite_operating = tuple(
        row for row in usd_operating
        if type(row.value) is Decimal and row.value.is_finite()
    )
    finite_income = tuple(
        row for row in usd_income
        if type(row.value) is Decimal and row.value.is_finite()
    )
    operating_rows = tuple(
        row for row in finite_operating
        if _eligible(
            row,
            concept=OPERATING_CASH_FLOW_CONCEPT,
            cik=source_cik,
            period_start=period_start,
            period_end=period_end,
        )
    )
    income_rows = tuple(
        row for row in finite_income
        if _eligible(
            row,
            concept=NET_INCOME_CONCEPT,
            cik=source_cik,
            period_start=period_start,
            period_end=period_end,
        )
    )

    unavailable = []
    if not all_operating:
        unavailable.append(
            CurrentAnnualOperatingCashFlowNetIncomeReason.EXACT_USD_UNIT_UNAVAILABLE
            if "OPERATING_CASH_FLOW_EXACT_USD_UNIT_UNAVAILABLE" in extraction.issues
            else CurrentAnnualOperatingCashFlowNetIncomeReason.
            OPERATING_CASH_FLOW_UNAVAILABLE
        )
    elif not usd_operating:
        unavailable.append(
            CurrentAnnualOperatingCashFlowNetIncomeReason.EXACT_USD_UNIT_UNAVAILABLE
        )
    elif not finite_operating:
        unavailable.append(
            CurrentAnnualOperatingCashFlowNetIncomeReason.
            FINITE_OPERATING_CASH_FLOW_VALUE_UNAVAILABLE
        )
    elif not operating_rows:
        unavailable.append(
            CurrentAnnualOperatingCashFlowNetIncomeReason.
            EXACT_ANNUAL_PERIOD_PRESENTATION_UNAVAILABLE
        )
    if not all_income:
        unavailable.append(
            CurrentAnnualOperatingCashFlowNetIncomeReason.EXACT_USD_UNIT_UNAVAILABLE
            if "NET_INCOME_EXACT_USD_UNIT_UNAVAILABLE" in extraction.issues
            else CurrentAnnualOperatingCashFlowNetIncomeReason.NET_INCOME_UNAVAILABLE
        )
    elif not usd_income:
        unavailable.append(
            CurrentAnnualOperatingCashFlowNetIncomeReason.EXACT_USD_UNIT_UNAVAILABLE
        )
    elif not finite_income:
        unavailable.append(
            CurrentAnnualOperatingCashFlowNetIncomeReason.
            FINITE_NET_INCOME_VALUE_UNAVAILABLE
        )
    elif not income_rows:
        unavailable.append(
            CurrentAnnualOperatingCashFlowNetIncomeReason.
            EXACT_ANNUAL_PERIOD_PRESENTATION_UNAVAILABLE
        )
    if unavailable:
        return _result(
            profile,
            comparability,
            status=CurrentAnnualOperatingCashFlowNetIncomeStatus.EVIDENCE_UNAVAILABLE,
            reasons=unavailable,
            period_start=period_start,
            period_end=period_end,
            source_cik=source_cik,
            receipt=receipt,
        )

    common = tuple(sorted(
        {row.accession for row in operating_rows}
        & {row.accession for row in income_rows}
    ))
    if not common:
        return _result(
            profile,
            comparability,
            status=CurrentAnnualOperatingCashFlowNetIncomeStatus.EVIDENCE_UNAVAILABLE,
            reasons=(
                CurrentAnnualOperatingCashFlowNetIncomeReason.
                NO_COMMON_ANNUAL_FILING_ACCESSION,
            ),
            period_start=period_start,
            period_end=period_end,
            source_cik=source_cik,
            receipt=receipt,
        )

    paired_operating = tuple(
        row for row in operating_rows if row.accession in common
    )
    paired_income = tuple(row for row in income_rows if row.accession in common)
    metadata_conflict = any(
        len({
            getattr(row, field)
            for row in paired_operating + paired_income
            if row.accession == accession
        }) != 1
        for accession in common
        for field in ("form", "filed", "fy")
    )
    if metadata_conflict:
        return _result(
            profile,
            comparability,
            status=CurrentAnnualOperatingCashFlowNetIncomeStatus.SOURCE_CONFLICT,
            reasons=(
                CurrentAnnualOperatingCashFlowNetIncomeReason.
                COMMON_FILING_METADATA_CONFLICT,
            ),
            period_start=period_start,
            period_end=period_end,
            source_cik=source_cik,
            receipt=receipt,
        )

    conflicts = []
    operating_values = {row.value for row in paired_operating}
    income_values = {row.value for row in paired_income}
    if len(operating_values) > 1:
        conflicts.append(
            CurrentAnnualOperatingCashFlowNetIncomeReason.
            COMPETING_OPERATING_CASH_FLOW_VALUES
        )
    if len(income_values) > 1:
        conflicts.append(
            CurrentAnnualOperatingCashFlowNetIncomeReason.
            COMPETING_NET_INCOME_VALUES
        )
    if conflicts:
        return _result(
            profile,
            comparability,
            status=CurrentAnnualOperatingCashFlowNetIncomeStatus.SOURCE_CONFLICT,
            reasons=conflicts,
            period_start=period_start,
            period_end=period_end,
            source_cik=source_cik,
            receipt=receipt,
        )

    operating_cash_flow = next(iter(operating_values))
    net_income = next(iter(income_values))
    selected_operating = tuple(
        row for row in paired_operating if row.value == operating_cash_flow
    )
    selected_income = tuple(row for row in paired_income if row.value == net_income)
    filings = _supporting_filings(selected_operating, selected_income, common)
    _validate_supporting_provenance(
        selected_operating, selected_income, common, filings
    )
    return _result(
        profile,
        comparability,
        status=(
            CurrentAnnualOperatingCashFlowNetIncomeStatus.
            PAIRED_OPERATING_CASH_FLOW_NET_INCOME_ESTABLISHED
        ),
        reasons=(),
        period_start=period_start,
        period_end=period_end,
        source_cik=source_cik,
        receipt=receipt,
        operating_cash_flow=operating_cash_flow,
        net_income=net_income,
        operating_cash_flow_ids=tuple(
            sorted(row.observation_id for row in selected_operating)
        ),
        net_income_ids=tuple(sorted(row.observation_id for row in selected_income)),
        accessions=common,
        filings=filings,
    )
