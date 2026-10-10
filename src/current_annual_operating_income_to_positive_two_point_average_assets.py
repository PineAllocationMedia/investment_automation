"""Exact CURRENT operating income per positive two-point average reported Assets.

Consumes native public qualifications only; no source replay or requalification.
The two-point mean is an analytical approximation, never a sourced financial fact.
"""
from __future__ import annotations

from dataclasses import dataclass, fields, is_dataclass
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from enum import Enum, StrEnum
from math import gcd
import hashlib
import json
import re
import sys

CONTRACT_VERSION = "2026-10-10-current-annual-operating-income-to-positive-two-point-average-assets-diagnostic-v1"
METHODOLOGY_VERSION = "2026-10-10-exact-rational-operating-income-per-positive-two-point-average-assets-v1"


class CurrentAnnualOperatingIncomeToPositiveTwoPointAverageAssetsError(ValueError):
    """Invalid native public qualification or contradictory economic context."""


class CurrentAnnualOperatingIncomeToPositiveTwoPointAverageAssetsAnalysisKind(StrEnum):
    CURRENT_ANNUAL_OPERATING_INCOME_TO_POSITIVE_TWO_POINT_AVERAGE_ASSETS = "CURRENT_ANNUAL_OPERATING_INCOME_TO_POSITIVE_TWO_POINT_AVERAGE_ASSETS"


class CurrentAnnualOperatingIncomeToPositiveTwoPointAverageAssetsStatus(StrEnum):
    AVAILABLE = "AVAILABLE"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    UNAVAILABLE = "UNAVAILABLE"
    UNSUPPORTED = "UNSUPPORTED"
    SOURCE_CONFLICT = "SOURCE_CONFLICT"


class CurrentAnnualOperatingIncomeToPositiveTwoPointAverageAssetsReason(StrEnum):
    UPSTREAM_REVENUE_OPERATING_INCOME_EVIDENCE_UNAVAILABLE = "UPSTREAM_REVENUE_OPERATING_INCOME_EVIDENCE_UNAVAILABLE"
    UPSTREAM_OPENING_CLOSING_ASSETS_EVIDENCE_UNAVAILABLE = "UPSTREAM_OPENING_CLOSING_ASSETS_EVIDENCE_UNAVAILABLE"
    UPSTREAM_REVENUE_OPERATING_INCOME_EVIDENCE_UNSUPPORTED = "UPSTREAM_REVENUE_OPERATING_INCOME_EVIDENCE_UNSUPPORTED"
    UPSTREAM_OPENING_CLOSING_ASSETS_EVIDENCE_UNSUPPORTED = "UPSTREAM_OPENING_CLOSING_ASSETS_EVIDENCE_UNSUPPORTED"
    UPSTREAM_REVENUE_OPERATING_INCOME_SOURCE_CONFLICT = "UPSTREAM_REVENUE_OPERATING_INCOME_SOURCE_CONFLICT"
    UPSTREAM_OPENING_CLOSING_ASSETS_SOURCE_CONFLICT = "UPSTREAM_OPENING_CLOSING_ASSETS_SOURCE_CONFLICT"
    NO_COMMON_SUPPORTING_ANNUAL_FILING_ACCESSION = "NO_COMMON_SUPPORTING_ANNUAL_FILING_ACCESSION"
    COMMON_SUPPORTING_FILING_METADATA_CONFLICT = "COMMON_SUPPORTING_FILING_METADATA_CONFLICT"
    OPENING_ASSETS_ZERO_ENDPOINT = "OPENING_ASSETS_ZERO_ENDPOINT"
    OPENING_ASSETS_NEGATIVE_NOT_POSITIVE_ENDPOINT = "OPENING_ASSETS_NEGATIVE_NOT_POSITIVE_ENDPOINT"
    CLOSING_ASSETS_ZERO_ENDPOINT = "CLOSING_ASSETS_ZERO_ENDPOINT"
    CLOSING_ASSETS_NEGATIVE_NOT_POSITIVE_ENDPOINT = "CLOSING_ASSETS_NEGATIVE_NOT_POSITIVE_ENDPOINT"


class CurrentAnnualOperatingIncomeToPositiveTwoPointAverageAssetsAuthority(StrEnum):
    QUALITY_CURRENT_ANNUAL_OPERATING_INCOME_TO_POSITIVE_TWO_POINT_AVERAGE_ASSETS_DIAGNOSTIC_ONLY = "QUALITY_CURRENT_ANNUAL_OPERATING_INCOME_TO_POSITIVE_TWO_POINT_AVERAGE_ASSETS_DIAGNOSTIC_ONLY"


class CurrentAnnualOperatingIncomeToPositiveTwoPointAverageAssetsLimitation(StrEnum):
    ONLY_QUALIFIED_REPORTED_OPERATING_INCOME_AND_ASSETS = "ONLY_QUALIFIED_REPORTED_OPERATING_INCOME_AND_ASSETS"
    ONLY_POSITIVE_OPENING_AND_CLOSING_ASSETS = "ONLY_POSITIVE_OPENING_AND_CLOSING_ASSETS"
    TWO_POINT_MEAN_IS_ANALYTICAL_APPROXIMATION = "TWO_POINT_MEAN_IS_ANALYTICAL_APPROXIMATION"
    REVENUE_FOUNDATION_AVAILABILITY_BOUNDS_DIAGNOSTIC = "REVENUE_FOUNDATION_AVAILABILITY_BOUNDS_DIAGNOSTIC"
    NO_ROA = "NO_ROA"
    NO_ROE = "NO_ROE"
    NO_ROIC = "NO_ROIC"
    NO_INVESTED_CAPITAL_INTERPRETATION = "NO_INVESTED_CAPITAL_INTERPRETATION"
    NO_NOPAT_OR_TAX_ADJUSTMENT = "NO_NOPAT_OR_TAX_ADJUSTMENT"
    NO_DAILY_OR_TIME_WEIGHTED_AVERAGE_ASSETS = "NO_DAILY_OR_TIME_WEIGHTED_AVERAGE_ASSETS"
    NO_NORMALIZED_OR_ADJUSTED_OPERATING_INCOME = "NO_NORMALIZED_OR_ADJUSTED_OPERATING_INCOME"
    NO_ASSET_QUALITY_JUDGMENT = "NO_ASSET_QUALITY_JUDGMENT"
    NO_CAPITAL_ALLOCATION_EFFECTIVENESS = "NO_CAPITAL_ALLOCATION_EFFECTIVENESS"
    NO_LEVERAGE_LIQUIDITY_OR_SOLVENCY_CONCLUSION = "NO_LEVERAGE_LIQUIDITY_OR_SOLVENCY_CONCLUSION"
    NO_HISTORICAL_CAPITAL_EFFICIENCY_TREND = "NO_HISTORICAL_CAPITAL_EFFICIENCY_TREND"
    NO_FORWARD_PERSISTENCE = "NO_FORWARD_PERSISTENCE"
    NO_CROSS_COMPANY_OR_CROSS_SECTOR_COMPARABILITY = "NO_CROSS_COMPANY_OR_CROSS_SECTOR_COMPARABILITY"
    NO_QUALITY_SCORE_GRADE_AGGREGATION_THRESHOLD_RANKING_OR_WEIGHT = "NO_QUALITY_SCORE_GRADE_AGGREGATION_THRESHOLD_RANKING_OR_WEIGHT"
    NO_DURABILITY_CONCLUSION = "NO_DURABILITY_CONCLUSION"
    NO_EXPECTED_RETURN_OR_CONFIDENCE_EFFECT = "NO_EXPECTED_RETURN_OR_CONFIDENCE_EFFECT"
    NO_RECOMMENDATION_ALLOCATION_SIZING_OR_EXECUTION = "NO_RECOMMENDATION_ALLOCATION_SIZING_OR_EXECUTION"
    NO_PRODUCTION_DEPLOYMENT_OR_V2_PROMOTION = "NO_PRODUCTION_DEPLOYMENT_OR_V2_PROMOTION"
    NO_HISTORICAL_AS_OF_OR_PIT_AUTHORITY = "NO_HISTORICAL_AS_OF_OR_PIT_AUTHORITY"


_Error = CurrentAnnualOperatingIncomeToPositiveTwoPointAverageAssetsError
_Status = CurrentAnnualOperatingIncomeToPositiveTwoPointAverageAssetsStatus
_Reason = CurrentAnnualOperatingIncomeToPositiveTwoPointAverageAssetsReason
_ANALYSIS_KIND = CurrentAnnualOperatingIncomeToPositiveTwoPointAverageAssetsAnalysisKind.CURRENT_ANNUAL_OPERATING_INCOME_TO_POSITIVE_TWO_POINT_AVERAGE_ASSETS
_AUTHORITY = CurrentAnnualOperatingIncomeToPositiveTwoPointAverageAssetsAuthority.QUALITY_CURRENT_ANNUAL_OPERATING_INCOME_TO_POSITIVE_TWO_POINT_AVERAGE_ASSETS_DIAGNOSTIC_ONLY
_LIMITATIONS = tuple(CurrentAnnualOperatingIncomeToPositiveTwoPointAverageAssetsLimitation)
_HASH_LENGTH = 64
_ACCESSION_PATTERN = re.compile(r"[0-9]{10}-[0-9]{2}-[0-9]{6}")
_REVENUE_UPSTREAM_MODULE_NAME = "economic_facts.sec_current_annual_revenue_operating_income"
_ASSETS_UPSTREAM_MODULE_NAME = "economic_facts.sec_current_annual_opening_closing_assets"


@dataclass(frozen=True, slots=True)
class OperatingIncomeToTwoPointAverageAssetsRatio:
    """Canonical reduced signed rational; zero is always 0/1."""
    numerator: int
    denominator: int

    def __post_init__(self) -> None:
        if type(self.numerator) is not int or type(self.denominator) is not int or self.denominator == 0:
            raise _Error("Exact integers and a nonzero denominator required")
        n, d = self.numerator, self.denominator
        if d < 0:
            n, d = -n, -d
        divisor = gcd(n, d)
        object.__setattr__(self, "numerator", n // divisor)
        object.__setattr__(self, "denominator", d // divisor)


class _InputCarrier:
    __slots__ = ("_analytical_fingerprint", "_evidence_fingerprint")


@dataclass(frozen=True, slots=True)
class CurrentAnnualOperatingIncomeToPositiveTwoPointAverageAssetsResult(_InputCarrier):
    contract_version: str
    methodology_version: str
    analysis_kind: CurrentAnnualOperatingIncomeToPositiveTwoPointAverageAssetsAnalysisKind
    status: CurrentAnnualOperatingIncomeToPositiveTwoPointAverageAssetsStatus
    reasons: tuple[CurrentAnnualOperatingIncomeToPositiveTwoPointAverageAssetsReason, ...]
    upstream_revenue_operating_income_status: Enum
    upstream_revenue_operating_income_reasons: tuple[Enum, ...]
    upstream_opening_closing_assets_status: Enum
    upstream_opening_closing_assets_reasons: tuple[Enum, ...]
    source_cik: str | None
    period_start: str | None
    period_end: str | None
    opening_balance_date: str | None
    closing_balance_date: str | None
    accounting_namespace: str
    accounting_basis: str
    unit: str
    operating_income_concept: str
    assets_concept: str
    operating_income_to_two_point_average_assets_ratio: OperatingIncomeToTwoPointAverageAssetsRatio | None
    upstream_revenue_operating_income_qualification_semantic_id: str
    upstream_revenue_operating_income_qualification_evidence_id: str
    upstream_opening_closing_assets_qualification_semantic_id: str
    upstream_opening_closing_assets_qualification_evidence_id: str
    common_supporting_accessions: tuple[str, ...]
    authority: CurrentAnnualOperatingIncomeToPositiveTwoPointAverageAssetsAuthority
    limitations: tuple[CurrentAnnualOperatingIncomeToPositiveTwoPointAverageAssetsLimitation, ...]

    @property
    def semantic_id(self) -> str:
        fingerprint = getattr(self, "_analytical_fingerprint", None)
        if not _is_hash(fingerprint):
            raise _Error("Canonical analytical fingerprint required")
        excluded = {"common_supporting_accessions"} | {
            f.name for f in fields(self) if "qualification_" in f.name
        }
        return _identity("current-annual-operating-income-to-positive-two-point-average-assets-semantics", {
            **{f.name: getattr(self, f.name) for f in fields(self) if f.name not in excluded},
            "analytical_fingerprint": fingerprint,
        })

    @property
    def evidence_id(self) -> str:
        fingerprint = getattr(self, "_evidence_fingerprint", None)
        if not _is_hash(fingerprint):
            raise _Error("Canonical evidence fingerprint required")
        return _identity("current-annual-operating-income-to-positive-two-point-average-assets-evidence", {
            "semantic_id": self.semantic_id, "evidence_fingerprint": fingerprint,
        })

    def to_dict(self) -> dict:
        payload = _canonical(self)
        payload.update(semantic_id=self.semantic_id, evidence_id=self.evidence_id)
        return {"current_annual_operating_income_to_positive_two_point_average_assets": payload}


def _exact_decimal_semantics(value):
    if value is None:
        return None
    if type(value) is not Decimal or not value.is_finite():
        raise _Error("Exact finite Decimal required")
    n, d = value.as_integer_ratio()
    return {"numerator": n, "denominator": d}


def _canonical(value):
    if isinstance(value, Enum):
        return value.value
    if type(value) is Decimal:
        return _exact_decimal_semantics(value)
    if is_dataclass(value):
        return {f.name: _canonical(getattr(value, f.name)) for f in fields(value)}
    if type(value) in (tuple, list):
        return [_canonical(item) for item in value]
    if type(value) is dict:
        return {key: _canonical(value[key]) for key in sorted(value)}
    if value is None or type(value) in (str, int, bool):
        return value
    raise _Error("Unsupported public identity value")


def _identity(domain, value):
    payload = json.dumps(_canonical(value), sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)
    return hashlib.sha256((domain + "\0" + payload).encode("utf-8")).hexdigest()


def _is_hash(value) -> bool:
    return (
        type(value) is str
        and len(value) == _HASH_LENGTH
        and all(character in "0123456789abcdef" for character in value)
    )


def _valid_optional_nonempty_string(value) -> bool:
    return value is None or (
        type(value) is str and bool(value) and value == value.strip()
    )


def _valid_optional_timestamp(value) -> bool:
    if value is None:
        return True
    if (
        not _valid_optional_nonempty_string(value)
        or not value.endswith("Z")
    ):
        return False
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        canonical = (
            parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
        )
    except (ValueError, OverflowError):
        return False
    return parsed.tzinfo is not None and canonical == value


def _valid_period(start, end) -> bool:
    if start is None or end is None:
        return start is None and end is None
    if type(start) is not str or type(end) is not str:
        return False
    try:
        parsed_start = date.fromisoformat(start)
        parsed_end = date.fromisoformat(end)
    except ValueError:
        return False
    return (
        parsed_start.isoformat() == start
        and parsed_end.isoformat() == end
        and parsed_start <= parsed_end
    )


def _revenue_upstream_module(qualification):
    qualification_type = type(qualification)
    module = sys.modules.get(qualification_type.__module__)
    if (
        qualification_type.__module__ != _REVENUE_UPSTREAM_MODULE_NAME
        or module is None
        or getattr(
            module,
            "CurrentAnnualRevenueOperatingIncomeQualification",
            None,
        ) is not qualification_type
    ):
        raise CurrentAnnualOperatingIncomeToPositiveTwoPointAverageAssetsError(
            "Exact CurrentAnnualRevenueOperatingIncomeQualification required"
        )
    return module


def _validate_supporting_filing(filing, upstream) -> None:
    if (
        type(filing) is not upstream.RevenueOperatingIncomeSupportingFiling
        or type(filing.accession) is not str
        or _ACCESSION_PATTERN.fullmatch(filing.accession) is None
        or type(filing.forms) is not tuple
        or len(filing.forms) != 1
        or filing.forms != tuple(sorted(set(filing.forms)))
        or any(
            type(item) is not str or item not in ("10-K", "10-K/A")
            for item in filing.forms
        )
        or type(filing.filed_dates) is not tuple
        or len(filing.filed_dates) != 1
        or filing.filed_dates != tuple(sorted(set(filing.filed_dates)))
        or any(not _valid_period(item, item) for item in filing.filed_dates)
        or type(filing.fiscal_years) is not tuple
        or len(filing.fiscal_years) != 1
        or filing.fiscal_years != tuple(sorted(set(filing.fiscal_years)))
        or any(type(item) is not int for item in filing.fiscal_years)
        or type(filing.revenue_observation_ids) is not tuple
        or not filing.revenue_observation_ids
        or filing.revenue_observation_ids
        != tuple(sorted(set(filing.revenue_observation_ids)))
        or any(
            not _is_hash(item)
            for item in filing.revenue_observation_ids
        )
        or type(filing.operating_income_observation_ids) is not tuple
        or not filing.operating_income_observation_ids
        or filing.operating_income_observation_ids
        != tuple(sorted(set(filing.operating_income_observation_ids)))
        or any(not _is_hash(item) for item in filing.operating_income_observation_ids)
        or set(filing.revenue_observation_ids)
        & set(filing.operating_income_observation_ids)
    ):
        raise CurrentAnnualOperatingIncomeToPositiveTwoPointAverageAssetsError(
            "Canonical established supporting filing required"
        )


def _validate_profile_state_reasons(qualification, upstream) -> None:
    profile_upstream = upstream.upstream
    status = qualification.upstream_profile_status
    reasons = qualification.upstream_profile_reasons
    reason = profile_upstream.ProfileReason
    if reasons != tuple(sorted(set(reasons), key=lambda item: item.value)):
        raise CurrentAnnualOperatingIncomeToPositiveTwoPointAverageAssetsError(
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
    if status is (
        profile_upstream.OrdinaryCompounderProfileStatus.
        ORDINARY_COMPOUNDER_PROFILE_ESTABLISHED
    ):
        coherent = reasons == ()
    elif status is (
        profile_upstream.OrdinaryCompounderProfileStatus.PROFILE_UNAVAILABLE
    ):
        coherent = bool(reasons) and set(reasons) <= unavailable_reasons
    elif status is (
        profile_upstream.OrdinaryCompounderProfileStatus.PROFILE_UNSUPPORTED
    ):
        coherent = (
            reason.UNSUPPORTED_SIC_PROFILE in reasons
            and reason.REPLAY_IDENTITY_MISMATCH not in reasons
        )
    elif status is profile_upstream.OrdinaryCompounderProfileStatus.SOURCE_CONFLICT:
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
        status is
        profile_upstream.OrdinaryCompounderProfileStatus.PROFILE_UNAVAILABLE
        and reason.POSITIVE_FIVE_PERIOD_ROUTE_NOT_ESTABLISHED in reasons
    ):
        coherent = False
    if not coherent:
        raise CurrentAnnualOperatingIncomeToPositiveTwoPointAverageAssetsError(
            "Canonical native profile status/reasons required"
        )


def _validate_shape(qualification, upstream) -> None:
    profile_upstream = upstream.upstream
    string_fields = ("contract_version", "qualifier_version", "evidence_kind",
                     "accounting_namespace", "accounting_basis", "unit", "authority")
    if any(type(getattr(qualification, name)) is not str for name in string_fields):
        raise _Error("Exact native contract strings required")
    if type(qualification.limitations) is not tuple:
        raise _Error("Native limitation tuple required")
    limitation_type = upstream.CurrentAnnualRevenueOperatingIncomeLimitation
    if any(type(item) is not limitation_type for item in qualification.limitations):
        raise _Error("Native closed limitations required")
    if (
        qualification.contract_version != upstream.CONTRACT_VERSION
        or qualification.qualifier_version != upstream.QUALIFIER_VERSION
        or qualification.evidence_kind != upstream.EVIDENCE_KIND
        or qualification.accounting_namespace != upstream.NAMESPACE
        or qualification.accounting_basis != upstream.ACCOUNTING_BASIS
        or type(qualification.revenue_concept) is not str
        or type(qualification.operating_income_concept) is not str
        or qualification.revenue_concept
        != upstream.REVENUE_CONCEPT
        or qualification.operating_income_concept != upstream.OPERATING_INCOME_CONCEPT
        or qualification.unit != upstream.REVIEWED_UNIT
        or qualification.authority != upstream.AUTHORITY
        or qualification.limitations != tuple(
            upstream.CurrentAnnualRevenueOperatingIncomeLimitation
        )
    ):
        raise CurrentAnnualOperatingIncomeToPositiveTwoPointAverageAssetsError(
            "Canonical operating income/revenue qualification contract required"
        )
    if type(qualification.status) is not (
        upstream.CurrentAnnualRevenueOperatingIncomeStatus
    ):
        raise CurrentAnnualOperatingIncomeToPositiveTwoPointAverageAssetsError(
            "Unknown operating income/revenue qualification status"
        )
    if (
        type(qualification.reasons) is not tuple
        or any(
            type(reason) is not
            upstream.CurrentAnnualRevenueOperatingIncomeReason
            for reason in qualification.reasons
        )
        or qualification.reasons != tuple(
            sorted(set(qualification.reasons), key=lambda item: item.value)
        )
    ):
        raise CurrentAnnualOperatingIncomeToPositiveTwoPointAverageAssetsError(
            "Canonical native operating income/revenue reasons required"
        )
    if (
        type(qualification.upstream_profile_status) is not
        profile_upstream.OrdinaryCompounderProfileStatus
        or type(qualification.upstream_profile_reasons) is not tuple
        or any(
            type(reason) is not profile_upstream.ProfileReason
            for reason in qualification.upstream_profile_reasons
        )
    ):
        raise CurrentAnnualOperatingIncomeToPositiveTwoPointAverageAssetsError(
            "Canonical native profile state required"
        )
    _validate_profile_state_reasons(qualification, upstream)
    route_values = (
        qualification.route_local_issuer_key,
        qualification.route_local_security_key,
    )
    route_absent = all(value is None for value in route_values)
    route_present = all(_is_hash(value) for value in route_values)
    receipt_values = (
        qualification.capture_receipt_id,
        qualification.source_object_hash,
        qualification.captured_at,
        qualification.capture_source_locator,
    )
    receipt_absent = all(value is None for value in receipt_values)
    receipt_present = (
        _is_hash(qualification.capture_receipt_id)
        and _is_hash(qualification.source_object_hash)
        and _valid_optional_timestamp(qualification.captured_at)
        and qualification.captured_at is not None
        and _valid_optional_nonempty_string(
            qualification.capture_source_locator
        )
        and qualification.capture_source_locator is not None
    )
    if (
        not (route_absent or route_present)
        or not (receipt_absent or receipt_present)
        or any(
            not _is_hash(value)
            for value in (
                qualification.upstream_profile_semantic_id,
                qualification.upstream_comparability_semantic_id,
                qualification.upstream_profile_evidence_id,
                qualification.upstream_comparability_evidence_id,
            )
        )
        or type(qualification.source_cik) is not str
        or re.fullmatch(r"[0-9]{10}", qualification.source_cik) is None
        or not _valid_period(
            qualification.period_start, qualification.period_end
        )
    ):
        raise CurrentAnnualOperatingIncomeToPositiveTwoPointAverageAssetsError(
            "Canonical operating income/revenue identity and route context required"
        )


def _has_route_context(qualification) -> bool:
    return (
        _is_hash(qualification.route_local_issuer_key)
        and _is_hash(qualification.route_local_security_key)
        and qualification.period_start is not None
        and qualification.period_end is not None
    )


def _has_receipt_context(qualification) -> bool:
    return (
        _is_hash(qualification.capture_receipt_id)
        and _is_hash(qualification.source_object_hash)
        and qualification.captured_at is not None
        and qualification.capture_source_locator is not None
    )


def _preliminary_unavailable_reason_families(reason) -> frozenset[tuple]:
    revenue_paths = (
        None,
        reason.REVENUE_UNAVAILABLE,
        reason.EXACT_USD_UNIT_UNAVAILABLE,
        reason.FINITE_REVENUE_VALUE_UNAVAILABLE,
        reason.EXACT_ANNUAL_PERIOD_PRESENTATION_UNAVAILABLE,
    )
    operating_income_paths = (
        None,
        reason.OPERATING_INCOME_UNAVAILABLE,
        reason.EXACT_USD_UNIT_UNAVAILABLE,
        reason.FINITE_OPERATING_INCOME_VALUE_UNAVAILABLE,
        reason.EXACT_ANNUAL_PERIOD_PRESENTATION_UNAVAILABLE,
    )
    return frozenset(
        tuple(sorted(
            {
                item
                for item in (revenue_reason, operating_income_reason)
                if item is not None
            },
            key=lambda item: item.value,
        ))
        for revenue_reason in revenue_paths
        for operating_income_reason in operating_income_paths
        if revenue_reason is not None or operating_income_reason is not None
    )


def _local_conflict_reason_families(reason) -> frozenset[tuple]:
    competing_both = tuple(sorted(
        (
            reason.COMPETING_REVENUE_VALUES,
            reason.COMPETING_OPERATING_INCOME_VALUES,
        ),
        key=lambda item: item.value,
    ))
    return frozenset({
        (reason.CANONICAL_ROUTE_IDENTITY_CONFLICT,),
        (reason.CAPTURE_REPLAY_CONFLICT,),
        (reason.SOURCE_CIK_CONFLICT,),
        (reason.COMMON_FILING_METADATA_CONFLICT,),
        (reason.COMPETING_REVENUE_VALUES,),
        (reason.COMPETING_OPERATING_INCOME_VALUES,),
        competing_both,
    })


def _upstream_identities(qualification) -> tuple[str, str]:
    try:
        semantic_id = qualification.semantic_id
        evidence_id = qualification.evidence_id
    except (TypeError, ValueError, ArithmeticError) as exc:
        raise CurrentAnnualOperatingIncomeToPositiveTwoPointAverageAssetsError(
            "Canonical upstream operating income/revenue identities required"
        ) from exc
    if not _is_hash(semantic_id) or not _is_hash(evidence_id):
        raise CurrentAnnualOperatingIncomeToPositiveTwoPointAverageAssetsError(
            "Canonical upstream operating income/revenue identities required"
        )
    return semantic_id, evidence_id


def _validate_established(
    qualification,
    upstream,
) -> tuple[Decimal, Decimal]:
    profile_upstream = upstream.upstream
    revenue = qualification.revenue
    operating_income = qualification.operating_income
    if (
        qualification.reasons != ()
        or qualification.upstream_profile_status is not
        profile_upstream.OrdinaryCompounderProfileStatus.
        ORDINARY_COMPOUNDER_PROFILE_ESTABLISHED
        or qualification.upstream_profile_reasons != ()
        or not _is_hash(qualification.route_local_issuer_key)
        or not _is_hash(qualification.route_local_security_key)
        or qualification.source_cik is None
        or qualification.period_start is None
        or qualification.period_end is None
        or type(revenue) is not Decimal
        or not revenue.is_finite()
        or type(operating_income) is not Decimal
        or not operating_income.is_finite()
        or not _is_hash(qualification.capture_receipt_id)
        or not _is_hash(qualification.source_object_hash)
        or not qualification.captured_at
        or not qualification.capture_source_locator
    ):
        raise CurrentAnnualOperatingIncomeToPositiveTwoPointAverageAssetsError(
            "Contradictory established operating income/revenue qualification"
        )

    revenue_ids = qualification.selected_revenue_observation_ids
    operating_income_ids = qualification.selected_operating_income_observation_ids
    accessions = qualification.supporting_accessions
    filings = qualification.supporting_filings
    if (
        type(revenue_ids) is not tuple
        or not revenue_ids
        or revenue_ids != tuple(sorted(set(revenue_ids)))
        or any(not _is_hash(item) for item in revenue_ids)
        or type(operating_income_ids) is not tuple
        or not operating_income_ids
        or operating_income_ids != tuple(sorted(set(operating_income_ids)))
        or any(not _is_hash(item) for item in operating_income_ids)
        or type(accessions) is not tuple
        or not accessions
        or accessions != tuple(sorted(set(accessions)))
        or any(
            type(item) is not str
            or _ACCESSION_PATTERN.fullmatch(item) is None
            for item in accessions
        )
        or type(filings) is not tuple
        or len(filings) != len(accessions)
    ):
        raise CurrentAnnualOperatingIncomeToPositiveTwoPointAverageAssetsError(
            "Canonical established operating income/revenue evidence surfaces required"
        )
    for filing in filings:
        _validate_supporting_filing(filing, upstream)
    flattened_revenue_ids = tuple(
        observation_id
        for filing in filings
        for observation_id in filing.revenue_observation_ids
    )
    flattened_operating_income_ids = tuple(
        observation_id
        for filing in filings
        for observation_id in filing.operating_income_observation_ids
    )
    if (
        tuple(item.accession for item in filings) != accessions
        or set(revenue_ids) & set(operating_income_ids)
        or len(flattened_revenue_ids) != len(set(flattened_revenue_ids))
        or len(flattened_operating_income_ids) != len(set(flattened_operating_income_ids))
        or tuple(sorted(flattened_revenue_ids)) != revenue_ids
        or tuple(sorted(flattened_operating_income_ids)) != operating_income_ids
    ):
        raise CurrentAnnualOperatingIncomeToPositiveTwoPointAverageAssetsError(
            "Coherent established operating income/revenue provenance required"
        )
    return revenue, operating_income


def _validate_non_established(qualification, upstream) -> None:
    if (
        not qualification.reasons
        or qualification.revenue is not None
        or qualification.operating_income is not None
        or qualification.selected_revenue_observation_ids != ()
        or qualification.selected_operating_income_observation_ids != ()
        or qualification.supporting_accessions != ()
        or qualification.supporting_filings != ()
    ):
        raise CurrentAnnualOperatingIncomeToPositiveTwoPointAverageAssetsError(
            "Canonical non-established operating income/revenue qualification required"
        )
    status = qualification.status
    reasons = qualification.reasons
    reason = upstream.CurrentAnnualRevenueOperatingIncomeReason
    upstream_status = upstream.CurrentAnnualRevenueOperatingIncomeStatus
    profile_status = upstream.upstream.OrdinaryCompounderProfileStatus
    preliminary_unavailable = _preliminary_unavailable_reason_families(reason)
    local_unavailable = preliminary_unavailable | frozenset({
        (reason.NO_COMMON_ANNUAL_FILING_ACCESSION,),
    })
    local_conflicts = _local_conflict_reason_families(reason)
    route_context = _has_route_context(qualification)
    receipt_context = _has_receipt_context(qualification)
    if status is upstream_status.EVIDENCE_UNAVAILABLE:
        if reasons == (reason.UPSTREAM_PROFILE_UNAVAILABLE,):
            coherent = (
                qualification.upstream_profile_status is
                profile_status.PROFILE_UNAVAILABLE
            )
        else:
            coherent = (
                reasons in local_unavailable
                and qualification.upstream_profile_status is
                profile_status.ORDINARY_COMPOUNDER_PROFILE_ESTABLISHED
                and qualification.upstream_profile_reasons == ()
                and route_context
                and receipt_context
            )
    elif status is upstream_status.EVIDENCE_UNSUPPORTED:
        coherent = (
            reasons == (reason.UPSTREAM_PROFILE_UNSUPPORTED,)
            and qualification.upstream_profile_status is
            profile_status.PROFILE_UNSUPPORTED
        )
    elif status is upstream_status.SOURCE_CONFLICT:
        if reasons == (reason.UPSTREAM_SOURCE_CONFLICT,):
            coherent = (
                qualification.upstream_profile_status is
                profile_status.SOURCE_CONFLICT
            )
        else:
            coherent = (
                reasons in local_conflicts
                and qualification.upstream_profile_status is
                profile_status.ORDINARY_COMPOUNDER_PROFILE_ESTABLISHED
                and qualification.upstream_profile_reasons == ()
                and route_context
                and (
                    receipt_context
                    or reasons == (reason.CANONICAL_ROUTE_IDENTITY_CONFLICT,)
                )
            )
    else:
        coherent = False
    if not coherent:
        raise CurrentAnnualOperatingIncomeToPositiveTwoPointAverageAssetsError(
            "Canonical non-established status/reason/profile path required"
        )




def _assets_validate_supporting_filing(filing, upstream) -> None:
    if (
        type(filing) is not upstream.OpeningClosingAssetsSupportingFiling
        or type(filing.accession) is not str
        or _ACCESSION_PATTERN.fullmatch(filing.accession) is None
        or type(filing.forms) is not tuple
        or len(filing.forms) != 1
        or filing.forms != tuple(sorted(set(filing.forms)))
        or any(
            type(item) is not str or item not in ("10-K", "10-K/A")
            for item in filing.forms
        )
        or type(filing.filed_dates) is not tuple
        or len(filing.filed_dates) != 1
        or filing.filed_dates != tuple(sorted(set(filing.filed_dates)))
        or any(not _valid_period(item, item) for item in filing.filed_dates)
        or type(filing.fiscal_years) is not tuple
        or len(filing.fiscal_years) != 1
        or filing.fiscal_years != tuple(sorted(set(filing.fiscal_years)))
        or any(type(item) is not int for item in filing.fiscal_years)
        or type(filing.closing_assets_observation_ids) is not tuple
        or not filing.closing_assets_observation_ids
        or filing.closing_assets_observation_ids
        != tuple(sorted(set(filing.closing_assets_observation_ids)))
        or any(
            not _is_hash(item)
            for item in filing.closing_assets_observation_ids
        )
        or type(filing.opening_assets_observation_ids) is not tuple
        or not filing.opening_assets_observation_ids
        or filing.opening_assets_observation_ids
        != tuple(sorted(set(filing.opening_assets_observation_ids)))
        or any(not _is_hash(item) for item in filing.opening_assets_observation_ids)
        or set(filing.closing_assets_observation_ids)
        & set(filing.opening_assets_observation_ids)
    ):
        raise CurrentAnnualOperatingIncomeToPositiveTwoPointAverageAssetsError(
            "Canonical established supporting filing required"
        )


def _assets_validate_shape(qualification, upstream) -> None:
    profile_upstream = upstream.upstream
    string_fields = ("contract_version", "qualifier_version", "evidence_kind",
                     "accounting_namespace", "accounting_basis", "unit", "authority")
    if any(type(getattr(qualification, name)) is not str for name in string_fields):
        raise _Error("Exact native contract strings required")
    if type(qualification.limitations) is not tuple:
        raise _Error("Native limitation tuple required")
    limitation_type = upstream.CurrentAnnualOpeningClosingAssetsLimitation
    if any(type(item) is not limitation_type for item in qualification.limitations):
        raise _Error("Native closed limitations required")
    if (
        qualification.contract_version != upstream.CONTRACT_VERSION
        or qualification.qualifier_version != upstream.QUALIFIER_VERSION
        or qualification.evidence_kind != upstream.EVIDENCE_KIND
        or qualification.accounting_namespace != upstream.NAMESPACE
        or qualification.accounting_basis != upstream.ACCOUNTING_BASIS
        or type(qualification.concept) is not str
        or qualification.concept != upstream.ASSETS_CONCEPT
        or qualification.unit != upstream.REVIEWED_UNIT
        or qualification.authority != upstream.AUTHORITY
        or qualification.limitations != tuple(
            upstream.CurrentAnnualOpeningClosingAssetsLimitation
        )
    ):
        raise CurrentAnnualOperatingIncomeToPositiveTwoPointAverageAssetsError(
            "Canonical opening/closing Assets qualification contract required"
        )
    if type(qualification.status) is not (
        upstream.CurrentAnnualOpeningClosingAssetsStatus
    ):
        raise CurrentAnnualOperatingIncomeToPositiveTwoPointAverageAssetsError(
            "Unknown opening/closing Assets qualification status"
        )
    if (
        type(qualification.reasons) is not tuple
        or any(
            type(reason) is not
            upstream.CurrentAnnualOpeningClosingAssetsReason
            for reason in qualification.reasons
        )
        or qualification.reasons != tuple(
            sorted(set(qualification.reasons), key=lambda item: item.value)
        )
    ):
        raise CurrentAnnualOperatingIncomeToPositiveTwoPointAverageAssetsError(
            "Canonical native opening/closing Assets reasons required"
        )
    if (
        type(qualification.upstream_profile_status) is not
        profile_upstream.OrdinaryCompounderProfileStatus
        or type(qualification.upstream_profile_reasons) is not tuple
        or any(
            type(reason) is not profile_upstream.ProfileReason
            for reason in qualification.upstream_profile_reasons
        )
    ):
        raise CurrentAnnualOperatingIncomeToPositiveTwoPointAverageAssetsError(
            "Canonical native profile state required"
        )
    _validate_profile_state_reasons(qualification, upstream)
    route_values = (
        qualification.route_local_issuer_key,
        qualification.route_local_security_key,
    )
    route_absent = all(value is None for value in route_values)
    route_present = all(_is_hash(value) for value in route_values)
    receipt_values = (
        qualification.capture_receipt_id,
        qualification.source_object_hash,
        qualification.captured_at,
        qualification.capture_source_locator,
    )
    receipt_absent = all(value is None for value in receipt_values)
    receipt_present = (
        _is_hash(qualification.capture_receipt_id)
        and _is_hash(qualification.source_object_hash)
        and _valid_optional_timestamp(qualification.captured_at)
        and qualification.captured_at is not None
        and _valid_optional_nonempty_string(
            qualification.capture_source_locator
        )
        and qualification.capture_source_locator is not None
    )
    if (
        not (route_absent or route_present)
        or not (receipt_absent or receipt_present)
        or any(
            not _is_hash(value)
            for value in (
                qualification.upstream_profile_semantic_id,
                qualification.upstream_comparability_semantic_id,
                qualification.upstream_profile_evidence_id,
                qualification.upstream_comparability_evidence_id,
            )
        )
        or type(qualification.source_cik) is not str
        or re.fullmatch(r"[0-9]{10}", qualification.source_cik) is None
        or not _valid_period(
            qualification.period_start, qualification.period_end
        )
    ):
        raise CurrentAnnualOperatingIncomeToPositiveTwoPointAverageAssetsError(
            "Canonical opening/closing Assets identity and route context required"
        )


def _assets_preliminary_unavailable_reason_families(reason) -> frozenset[tuple]:
    closing_assets_paths = (
        None,
        reason.CLOSING_ASSETS_UNAVAILABLE,
        reason.EXACT_USD_UNIT_UNAVAILABLE,
        reason.FINITE_CLOSING_ASSETS_VALUE_UNAVAILABLE,
        reason.EXACT_OPENING_CLOSING_INSTANT_PRESENTATION_UNAVAILABLE,
    )
    opening_assets_paths = (
        None,
        reason.OPENING_ASSETS_UNAVAILABLE,
        reason.EXACT_USD_UNIT_UNAVAILABLE,
        reason.FINITE_OPENING_ASSETS_VALUE_UNAVAILABLE,
        reason.EXACT_OPENING_CLOSING_INSTANT_PRESENTATION_UNAVAILABLE,
    )
    return frozenset(
        tuple(sorted(
            {
                item
                for item in (closing_assets_reason, opening_assets_reason)
                if item is not None
            },
            key=lambda item: item.value,
        ))
        for closing_assets_reason in closing_assets_paths
        for opening_assets_reason in opening_assets_paths
        if closing_assets_reason is not None or opening_assets_reason is not None
    )


def _assets_local_conflict_reason_families(reason) -> frozenset[tuple]:
    competing_both = tuple(sorted(
        (
            reason.COMPETING_CLOSING_ASSETS_VALUES,
            reason.COMPETING_OPENING_ASSETS_VALUES,
        ),
        key=lambda item: item.value,
    ))
    return frozenset({
        (reason.CANONICAL_ROUTE_IDENTITY_CONFLICT,),
        (reason.CAPTURE_REPLAY_CONFLICT,),
        (reason.SOURCE_CIK_CONFLICT,),
        (reason.COMMON_FILING_METADATA_CONFLICT,),
        (reason.COMPETING_CLOSING_ASSETS_VALUES,),
        (reason.COMPETING_OPENING_ASSETS_VALUES,),
        competing_both,
    })


def _assets_validate_established(
    qualification,
    upstream,
) -> tuple[Decimal, Decimal]:
    profile_upstream = upstream.upstream
    closing_assets = qualification.closing_assets
    opening_assets = qualification.opening_assets
    if (
        qualification.reasons != ()
        or qualification.upstream_profile_status is not
        profile_upstream.OrdinaryCompounderProfileStatus.
        ORDINARY_COMPOUNDER_PROFILE_ESTABLISHED
        or qualification.upstream_profile_reasons != ()
        or not _is_hash(qualification.route_local_issuer_key)
        or not _is_hash(qualification.route_local_security_key)
        or qualification.source_cik is None
        or qualification.period_start is None
        or qualification.period_end is None
        or type(closing_assets) is not Decimal
        or not closing_assets.is_finite()
        or type(opening_assets) is not Decimal
        or not opening_assets.is_finite()
        or not _is_hash(qualification.capture_receipt_id)
        or not _is_hash(qualification.source_object_hash)
        or not qualification.captured_at
        or not qualification.capture_source_locator
    ):
        raise CurrentAnnualOperatingIncomeToPositiveTwoPointAverageAssetsError(
            "Contradictory established opening/closing Assets qualification"
        )

    closing_assets_ids = qualification.selected_closing_assets_observation_ids
    opening_assets_ids = qualification.selected_opening_assets_observation_ids
    accessions = qualification.supporting_accessions
    filings = qualification.supporting_filings
    if (
        type(closing_assets_ids) is not tuple
        or not closing_assets_ids
        or closing_assets_ids != tuple(sorted(set(closing_assets_ids)))
        or any(not _is_hash(item) for item in closing_assets_ids)
        or type(opening_assets_ids) is not tuple
        or not opening_assets_ids
        or opening_assets_ids != tuple(sorted(set(opening_assets_ids)))
        or any(not _is_hash(item) for item in opening_assets_ids)
        or type(accessions) is not tuple
        or not accessions
        or accessions != tuple(sorted(set(accessions)))
        or any(
            type(item) is not str
            or _ACCESSION_PATTERN.fullmatch(item) is None
            for item in accessions
        )
        or type(filings) is not tuple
        or len(filings) != len(accessions)
    ):
        raise CurrentAnnualOperatingIncomeToPositiveTwoPointAverageAssetsError(
            "Canonical established opening/closing Assets evidence surfaces required"
        )
    for filing in filings:
        _assets_validate_supporting_filing(filing, upstream)
    flattened_closing_assets_ids = tuple(
        observation_id
        for filing in filings
        for observation_id in filing.closing_assets_observation_ids
    )
    flattened_opening_assets_ids = tuple(
        observation_id
        for filing in filings
        for observation_id in filing.opening_assets_observation_ids
    )
    if (
        tuple(item.accession for item in filings) != accessions
        or set(closing_assets_ids) & set(opening_assets_ids)
        or len(flattened_closing_assets_ids) != len(set(flattened_closing_assets_ids))
        or len(flattened_opening_assets_ids) != len(set(flattened_opening_assets_ids))
        or tuple(sorted(flattened_closing_assets_ids)) != closing_assets_ids
        or tuple(sorted(flattened_opening_assets_ids)) != opening_assets_ids
    ):
        raise CurrentAnnualOperatingIncomeToPositiveTwoPointAverageAssetsError(
            "Coherent established opening/closing Assets provenance required"
        )
    _validate_assets_dates(qualification)
    _validate_assets_observations(qualification, upstream)
    return closing_assets, opening_assets


def _assets_validate_non_established(qualification, upstream) -> None:
    if (
        not qualification.reasons
        or qualification.selected_opening_observations != ()
        or qualification.selected_closing_observations != ()
        or qualification.closing_assets is not None
        or qualification.opening_assets is not None
        or qualification.selected_closing_assets_observation_ids != ()
        or qualification.selected_opening_assets_observation_ids != ()
        or qualification.supporting_accessions != ()
        or qualification.supporting_filings != ()
    ):
        raise CurrentAnnualOperatingIncomeToPositiveTwoPointAverageAssetsError(
            "Canonical non-established opening/closing Assets qualification required"
        )
    status = qualification.status
    reasons = qualification.reasons
    reason = upstream.CurrentAnnualOpeningClosingAssetsReason
    upstream_status = upstream.CurrentAnnualOpeningClosingAssetsStatus
    profile_status = upstream.upstream.OrdinaryCompounderProfileStatus
    preliminary_unavailable = _assets_preliminary_unavailable_reason_families(reason)
    local_unavailable = preliminary_unavailable | frozenset({
        (reason.NO_COMMON_ANNUAL_FILING_ACCESSION,),
        (reason.CANONICAL_OPENING_BALANCE_DATE_UNAVAILABLE,),
    })
    local_conflicts = _assets_local_conflict_reason_families(reason)
    route_context = _has_route_context(qualification)
    receipt_context = _has_receipt_context(qualification)
    if status is upstream_status.EVIDENCE_UNAVAILABLE:
        if reasons == (reason.UPSTREAM_PROFILE_UNAVAILABLE,):
            coherent = (
                qualification.upstream_profile_status is
                profile_status.PROFILE_UNAVAILABLE
            )
        else:
            coherent = (
                reasons in local_unavailable
                and qualification.upstream_profile_status is
                profile_status.ORDINARY_COMPOUNDER_PROFILE_ESTABLISHED
                and qualification.upstream_profile_reasons == ()
                and route_context
                and receipt_context
            )
    elif status is upstream_status.EVIDENCE_UNSUPPORTED:
        coherent = (
            reasons == (reason.UPSTREAM_PROFILE_UNSUPPORTED,)
            and qualification.upstream_profile_status is
            profile_status.PROFILE_UNSUPPORTED
        )
    elif status is upstream_status.SOURCE_CONFLICT:
        if reasons == (reason.UPSTREAM_SOURCE_CONFLICT,):
            coherent = (
                qualification.upstream_profile_status is
                profile_status.SOURCE_CONFLICT
            )
        else:
            coherent = (
                reasons in local_conflicts
                and qualification.upstream_profile_status is
                profile_status.ORDINARY_COMPOUNDER_PROFILE_ESTABLISHED
                and qualification.upstream_profile_reasons == ()
                and route_context
                and (
                    receipt_context
                    or reasons == (reason.CANONICAL_ROUTE_IDENTITY_CONFLICT,)
                )
            )
    else:
        coherent = False
    if not coherent:
        raise CurrentAnnualOperatingIncomeToPositiveTwoPointAverageAssetsError(
            "Canonical non-established status/reason/profile path required"
        )



def _assets_upstream_module(qualification):
    qualification_type = type(qualification)
    module = sys.modules.get(_ASSETS_UPSTREAM_MODULE_NAME)
    if (qualification_type.__module__ != _ASSETS_UPSTREAM_MODULE_NAME or module is None
            or getattr(module, "CurrentAnnualOpeningClosingAssetsQualification", None) is not qualification_type):
        raise _Error("Exact CurrentAnnualOpeningClosingAssetsQualification required")
    return module


def _validate_assets_dates(q):
    if any(value is not None and type(value) is not str for value in (q.opening_balance_date, q.closing_balance_date)):
        raise _Error("Exact balance date strings required")
    if q.period_start is None:
        if q.opening_balance_date is not None or q.closing_balance_date is not None:
            raise _Error("Balance dates without an annual period")
        return
    if q.closing_balance_date != q.period_end:
        raise _Error("Closing date must equal annual end")
    try:
        opening = (date.fromisoformat(q.period_start) - timedelta(days=1)).isoformat()
    except (ValueError, OverflowError) as exc:
        raise _Error("Representable adjacent opening date required") from exc
    boundary_unavailable = tuple(r.value for r in q.reasons) == ("CANONICAL_OPENING_BALANCE_DATE_UNAVAILABLE",)
    if boundary_unavailable and q.opening_balance_date is not None:
        raise _Error("Unavailable canonical boundary cannot carry an opening date")
    if q.opening_balance_date != opening:
        if (q.opening_balance_date is None and q.status.value == "EVIDENCE_UNAVAILABLE"
                and boundary_unavailable):
            return
        raise _Error("Opening date must precede annual start by one calendar day")


def _unique_row_pairs(pairs):
    row = {}
    for key, value in pairs:
        if key in row:
            raise _Error("Duplicate selected row JSON field")
        row[key] = value
    return row


def _reject_row_constant(value):
    raise _Error("Nonfinite selected row JSON constant: " + value)


def _validate_assets_observations(q, upstream):
    """Check supplied lossless public provenance; never extract or replay sources."""
    filings = {f.accession: f for f in q.supporting_filings}
    for rows, ids, amount, balance_date, filing_field in (
        (q.selected_opening_observations, q.selected_opening_assets_observation_ids,
         q.opening_assets, q.opening_balance_date, "opening_assets_observation_ids"),
        (q.selected_closing_observations, q.selected_closing_assets_observation_ids,
         q.closing_assets, q.closing_balance_date, "closing_assets_observation_ids"),
    ):
        if type(rows) is not tuple or not rows:
            raise _Error("Selected native Assets observations required")
        if any(type(row) is not upstream.AssetsLiabilitiesObservation for row in rows):
            raise _Error("Exact native Assets observation type required")
        if tuple(row.observation_id for row in rows) != ids:
            raise _Error("Selected Assets rows must match ordered observation identities")
        for row in rows:
            filing = filings.get(row.accession)
            if (
                not _is_hash(row.observation_id) or not _is_hash(row.semantic_id)
                or row.source_cik != q.source_cik or row.namespace != q.accounting_namespace
                or row.accounting_basis != q.accounting_basis or row.concept != q.concept
                or row.unit != q.unit or type(row.value) is not Decimal
                or not row.value.is_finite() or row.value != amount
                or row.start is not None or row.end != balance_date or row.fp != "FY"
                or type(row.fy) is not int or filing is None
                or row.observation_id not in getattr(filing, filing_field)
                or (row.form,) != filing.forms or (row.filed,) != filing.filed_dates
                or (row.fy,) != filing.fiscal_years
                or row.source_object_hash != q.source_object_hash
                or row.capture_receipt_id != q.capture_receipt_id or row.captured_at != q.captured_at
                or row.extraction_version != "2026-10-08-sec-assets-liabilities-extraction-v1"
                or type(row.source_locator) is not str
                or re.fullmatch(r"/facts/us-gaap/Assets/units/USD/[0-9]+", row.source_locator) is None
                or row.semantic_locator != "/facts/us-gaap/Assets/units/USD/sha256:" + row.semantic_id
                or type(row.row_json) is not str or not row.row_json.strip()
                or row.source_semantics != ("SEC_COMPANYFACTS_PRESENTATION", "CURRENT_CAPTURE_REPLAY")
                or row.metadata_limitations != ()
                or not _valid_optional_nonempty_string(row.frame)
            ):
                raise _Error("Contradictory selected Assets observation provenance")
            try:
                raw_row = json.loads(
                    row.row_json, parse_float=Decimal, object_pairs_hook=_unique_row_pairs,
                    parse_constant=_reject_row_constant,
                )
            except (ValueError, TypeError) as exc:
                raise _Error("Canonical selected row JSON required") from exc
            if (type(raw_row) is not dict or type(raw_row.get("val")) not in (int, Decimal)
                    or Decimal(raw_row["val"]) != amount
                    or raw_row.get("start") is not None or raw_row.get("end") != balance_date
                    or raw_row.get("fy") != row.fy or type(raw_row.get("fy")) is not int
                    or raw_row.get("fp") != row.fp or raw_row.get("form") != row.form
                    or raw_row.get("filed") != row.filed or raw_row.get("accn") != row.accession
                    or raw_row.get("frame") != row.frame):
                raise _Error("Selected row JSON contradicts its public projection")


def _ratio_from_decimals(income, opening, closing):
    in_, id_ = income.as_integer_ratio()
    on, od = opening.as_integer_ratio()
    cn, cd = closing.as_integer_ratio()
    return OperatingIncomeToTwoPointAverageAssetsRatio(
        2 * in_ * od * cd, id_ * (on * cd + cn * od),
    )


def _shared_context(left, right, label):
    if left is not None and right is not None and left != right:
        raise _Error("Contradictory " + label)
    return left if left is not None and right is not None else None


def analyze_current_annual_operating_income_to_positive_two_point_average_assets(
    revenue_operating_income, opening_closing_assets, /,
) -> CurrentAnnualOperatingIncomeToPositiveTwoPointAverageAssetsResult:
    """Consume two exact native qualified results and return one bounded ratio."""
    try:
        return _analyze(revenue_operating_income, opening_closing_assets)
    except _Error:
        raise
    except (AttributeError, TypeError, ValueError, ArithmeticError, IndexError, KeyError) as exc:
        raise _Error("Malformed public qualification contract") from exc

# These approved identities are local pins, not inferred from a future upstream module.
_PINNED_INPUT_CONTRACTS = (
    (
        '2026-10-07-current-annual-revenue-operating-income-qualification-v1',
        '2026-10-07-paired-common-filing-exact-decimal-usd-qualification-v1',
        'CURRENT_ANNUAL_REVENUE_OPERATING_INCOME_QUALIFICATION',
        'QUALITY_PROFITABILITY_EVIDENCE_ONLY',
        (
            'ONLY_US_GAAP_REVENUE_FROM_CONTRACT_WITH_CUSTOMER_EXCLUDING_ASSESSED_TAX',
            'ONLY_US_GAAP_OPERATING_INCOME_LOSS',
            'NO_TAXONOMY_SUBSTITUTION',
            'NO_NON_GAAP_OR_ADJUSTED_OPERATING_INCOME',
            'NO_OPERATING_MARGIN',
            'NO_GROSS_MARGIN',
            'NO_NET_MARGIN',
            'NO_GOOD_OR_BAD_PROFITABILITY',
            'NO_PROFITABILITY_QUALITY_CONCLUSION',
            'NO_MARGIN_STABILITY_OR_EXPANSION',
            'NO_PRICING_POWER_OR_COST_DISCIPLINE',
            'NO_ROIC_ROE_OR_ROA',
            'NO_FREE_CASH_FLOW_MARGIN',
            'NO_EARNINGS_QUALITY',
            'NO_HISTORICAL_PROFITABILITY_TREND',
            'NO_CROSS_ISSUER_COMPARABILITY',
            'NO_CROSS_SECTOR_COMPARABILITY',
            'NO_NORMALIZATION_OR_ADJUSTED_EARNINGS',
            'NO_MOAT_CONCLUSION',
            'NO_DURABILITY_OR_PERSISTENCE_CONCLUSION',
            'NO_CONFIDENCE_SCORE_OR_SUBSTITUTION',
            'NO_EXPECTED_RETURN_EFFECT',
            'NO_AGGREGATE_QUALITY_SCORE_GRADE_OR_WEIGHT',
            'NO_RECOMMENDATION_RANKING_ALLOCATION_OR_SIZING',
            'NO_EXECUTION_PRODUCTION_DEPLOYMENT_OR_V2_PROMOTION_AUTHORITY',
            'NO_HISTORICAL_AS_OF_OR_PIT_AUTHORITY',
        ),
    ),
    (
        '2026-10-10-current-annual-opening-closing-assets-qualification-v1',
        '2026-10-10-adjacent-common-filing-exact-decimal-usd-assets-instants-qualification-v1',
        'CURRENT_ANNUAL_OPENING_CLOSING_ASSETS_QUALIFICATION',
        'QUALITY_OPENING_CLOSING_ASSETS_EVIDENCE_ONLY',
        (
            'ONLY_US_GAAP_ASSETS',
            'NO_TAXONOMY_SUBSTITUTION',
            'NO_AVERAGE_ASSETS',
            'NO_ROA',
            'NO_ROE',
            'NO_ROIC',
            'NO_INVESTED_CAPITAL_INTERPRETATION',
            'NO_TANGIBLE_BOOK_VALUE',
            'NO_LIQUIDATION_VALUE',
            'NO_ASSET_QUALITY_JUDGMENT',
            'NO_CAPITAL_EFFICIENCY_JUDGMENT',
            'NO_ASSET_GROWTH_QUALITY_OR_HISTORICAL_TREND',
            'NO_LEVERAGE_LIQUIDITY_OR_SOLVENCY_CONCLUSION',
            'NO_CROSS_COMPANY_OR_CROSS_SECTOR_COMPARABILITY',
            'NO_QUALITY_SCORE_GRADE_RANKING_AGGREGATION_OR_WEIGHTING',
            'NO_DURABILITY_CONCLUSION',
            'NO_EXPECTED_RETURN_OR_CONFIDENCE_EFFECT',
            'NO_RECOMMENDATION_ALLOCATION_SIZING_OR_EXECUTION',
            'NO_PRODUCTION_DEPLOYMENT_OR_V2_PROMOTION',
            'NO_HISTORICAL_AS_OF_OR_PIT_AUTHORITY',
        ),
    ),
)


def _validate_pinned_input(q, index):
    actual = (q.contract_version, q.qualifier_version, q.evidence_kind, q.authority,
              tuple(item.value for item in q.limitations))
    if actual != _PINNED_INPUT_CONTRACTS[index]:
        raise _Error("Diagnostic-pinned upstream contract required")



def _analyze(income_q, assets_q):
    income_module = _revenue_upstream_module(income_q)
    assets_module = _assets_upstream_module(assets_q)
    _validate_shape(income_q, income_module)
    _validate_pinned_input(income_q, 0)
    _assets_validate_shape(assets_q, assets_module)
    _validate_pinned_input(assets_q, 1)
    established_income = income_q.status is income_module.CurrentAnnualRevenueOperatingIncomeStatus.PAIRED_REVENUE_OPERATING_INCOME_ESTABLISHED
    established_assets = assets_q.status is assets_module.CurrentAnnualOpeningClosingAssetsStatus.OPENING_CLOSING_ASSETS_ESTABLISHED
    if established_income:
        _validate_established(income_q, income_module)
    else:
        _validate_non_established(income_q, income_module)
    if established_assets:
        _assets_validate_established(assets_q, assets_module)
    else:
        _assets_validate_non_established(assets_q, assets_module)
        _validate_assets_dates(assets_q)
    source_cik = _shared_context(income_q.source_cik, assets_q.source_cik, "source CIK")
    start = _shared_context(income_q.period_start, assets_q.period_start, "annual start")
    end = _shared_context(income_q.period_end, assets_q.period_end, "annual end")
    reasons = []
    common = ()
    ratio = None
    if established_income and established_assets:
        left = {f.accession: (f.forms, f.filed_dates, f.fiscal_years) for f in income_q.supporting_filings}
        right = {f.accession: (f.forms, f.filed_dates, f.fiscal_years) for f in assets_q.supporting_filings}
        common = tuple(sorted(set(left) & set(right)))
        if not common:
            status = _Status.UNAVAILABLE
            reasons.append(_Reason.NO_COMMON_SUPPORTING_ANNUAL_FILING_ACCESSION)
        elif any(left[a] != right[a] for a in common):
            status = _Status.SOURCE_CONFLICT
            reasons.append(_Reason.COMMON_SUPPORTING_FILING_METADATA_CONFLICT)
        else:
            for amount, zero, negative in (
                (assets_q.opening_assets, _Reason.OPENING_ASSETS_ZERO_ENDPOINT,
                 _Reason.OPENING_ASSETS_NEGATIVE_NOT_POSITIVE_ENDPOINT),
                (assets_q.closing_assets, _Reason.CLOSING_ASSETS_ZERO_ENDPOINT,
                 _Reason.CLOSING_ASSETS_NEGATIVE_NOT_POSITIVE_ENDPOINT),
            ):
                if amount == 0:
                    reasons.append(zero)
                elif amount < 0:
                    reasons.append(negative)
            status = _Status.NOT_APPLICABLE if reasons else _Status.AVAILABLE
            if status is _Status.AVAILABLE:
                ratio = _ratio_from_decimals(income_q.operating_income, assets_q.opening_assets, assets_q.closing_assets)
    else:
        failures = []
        for q, established, prefix in (
            (income_q, established_income, "UPSTREAM_REVENUE_OPERATING_INCOME_"),
            (assets_q, established_assets, "UPSTREAM_OPENING_CLOSING_ASSETS_"),
        ):
            if established:
                continue
            reasons.append(_Reason(prefix + q.status.value))
            failures.append({"EVIDENCE_UNAVAILABLE": _Status.UNAVAILABLE,
                             "EVIDENCE_UNSUPPORTED": _Status.UNSUPPORTED,
                             "SOURCE_CONFLICT": _Status.SOURCE_CONFLICT}[q.status.value])
        precedence = {_Status.UNAVAILABLE: 0, _Status.UNSUPPORTED: 1, _Status.SOURCE_CONFLICT: 2}
        status = max(failures, key=precedence.__getitem__)
    reasons = tuple(sorted(set(reasons), key=lambda r: r.value))
    income_ids = _upstream_identities(income_q)
    assets_ids = _upstream_identities(assets_q)
    result = CurrentAnnualOperatingIncomeToPositiveTwoPointAverageAssetsResult(
        CONTRACT_VERSION, METHODOLOGY_VERSION, _ANALYSIS_KIND, status, reasons,
        income_q.status, income_q.reasons, assets_q.status, assets_q.reasons,
        source_cik, start, end, assets_q.opening_balance_date, assets_q.closing_balance_date,
        income_q.accounting_namespace, income_q.accounting_basis, income_q.unit,
        income_q.operating_income_concept, assets_q.concept, ratio,
        *income_ids, *assets_ids, common, _AUTHORITY, _LIMITATIONS,
    )
    analytical = {
        "operating_income": _exact_decimal_semantics(income_q.operating_income),
        "opening_assets": _exact_decimal_semantics(assets_q.opening_assets),
        "closing_assets": _exact_decimal_semantics(assets_q.closing_assets),
        "native_profile_states": (
            (income_q.upstream_profile_status, income_q.upstream_profile_reasons),
            (assets_q.upstream_profile_status, assets_q.upstream_profile_reasons),
        ),
    }
    object.__setattr__(result, "_analytical_fingerprint", _identity("two-point-average-assets-analytical-operands", analytical))
    object.__setattr__(result, "_evidence_fingerprint", _identity("two-point-average-assets-public-qualification-evidence", {
        "income_qualification": income_q, "assets_qualification": assets_q,
        "income_qualification_ids": income_ids, "assets_qualification_ids": assets_ids,
        "common_supporting_accessions": common,
    }))
    return result
