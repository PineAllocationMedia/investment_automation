"""Bounded Stage-C diagnostic for annual OCF relative to positive net income.

The module consumes one exact canonical paired OCF/net-income qualification and
reports only the exact signed OCF / net-income relationship when net income is
strictly positive.  It performs no acquisition, requalification, scoring,
forecasting, or downstream action.
"""
from __future__ import annotations

from dataclasses import dataclass, fields, is_dataclass
from datetime import date, datetime, timezone
from decimal import Decimal
from enum import Enum, StrEnum
from math import gcd
import hashlib
import json
import re
import sys


CONTRACT_VERSION = (
    "2026-10-05-current-annual-ocf-to-positive-net-income-diagnostic-v1"
)
METHODOLOGY_VERSION = (
    "2026-10-05-exact-rational-ocf-per-positive-net-income-v1"
)


class CurrentAnnualOCFToPositiveNetIncomeError(ValueError):
    """Wrong public input type or contradictory canonical upstream object."""


class CurrentAnnualOCFToPositiveNetIncomeAnalysisKind(StrEnum):
    CURRENT_ANNUAL_OCF_TO_POSITIVE_NET_INCOME = (
        "CURRENT_ANNUAL_OCF_TO_POSITIVE_NET_INCOME"
    )


class CurrentAnnualOCFToPositiveNetIncomeStatus(StrEnum):
    AVAILABLE = "AVAILABLE"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    UNAVAILABLE = "UNAVAILABLE"
    UNSUPPORTED = "UNSUPPORTED"
    SOURCE_CONFLICT = "SOURCE_CONFLICT"


class CurrentAnnualOCFToPositiveNetIncomeReason(StrEnum):
    UPSTREAM_EVIDENCE_UNAVAILABLE = "UPSTREAM_EVIDENCE_UNAVAILABLE"
    UPSTREAM_EVIDENCE_UNSUPPORTED = "UPSTREAM_EVIDENCE_UNSUPPORTED"
    UPSTREAM_SOURCE_CONFLICT = "UPSTREAM_SOURCE_CONFLICT"
    NET_INCOME_ZERO_DENOMINATOR = "NET_INCOME_ZERO_DENOMINATOR"
    NET_INCOME_NEGATIVE_NOT_POSITIVE_EARNINGS = (
        "NET_INCOME_NEGATIVE_NOT_POSITIVE_EARNINGS"
    )


class CurrentAnnualOCFToPositiveNetIncomeAuthority(StrEnum):
    QUALITY_CURRENT_ANNUAL_OCF_NET_INCOME_RELATIONSHIP_DIAGNOSTIC_ONLY = (
        "QUALITY_CURRENT_ANNUAL_OCF_NET_INCOME_RELATIONSHIP_DIAGNOSTIC_ONLY"
    )


class CurrentAnnualOCFToPositiveNetIncomeLimitation(StrEnum):
    ONLY_POSITIVE_NET_INCOME_DENOMINATOR = (
        "ONLY_POSITIVE_NET_INCOME_DENOMINATOR"
    )
    NO_GOOD_BAD_OR_MINIMUM_RATIO = "NO_GOOD_BAD_OR_MINIMUM_RATIO"
    NO_RATIO_MAGNITUDE_QUALITY_ORDERING = (
        "NO_RATIO_MAGNITUDE_QUALITY_ORDERING"
    )
    NO_NEAR_ZERO_DENOMINATOR_STABILITY_CLAIM = (
        "NO_NEAR_ZERO_DENOMINATOR_STABILITY_CLAIM"
    )
    NO_ACCRUALS_QUALITY_CONCLUSION = "NO_ACCRUALS_QUALITY_CONCLUSION"
    NO_WORKING_CAPITAL_CAUSAL_ATTRIBUTION = (
        "NO_WORKING_CAPITAL_CAUSAL_ATTRIBUTION"
    )
    NO_EARNINGS_MANIPULATION_OR_FRAUD_CONCLUSION = (
        "NO_EARNINGS_MANIPULATION_OR_FRAUD_CONCLUSION"
    )
    NO_FREE_CASH_FLOW_OR_CAPEX_CLAIM = "NO_FREE_CASH_FLOW_OR_CAPEX_CLAIM"
    NO_OWNER_EARNINGS_CLAIM = "NO_OWNER_EARNINGS_CLAIM"
    NO_PROFITABILITY_QUALITY_CONCLUSION = (
        "NO_PROFITABILITY_QUALITY_CONCLUSION"
    )
    NO_HISTORICAL_CASH_CONVERSION_TREND = (
        "NO_HISTORICAL_CASH_CONVERSION_TREND"
    )
    NO_CROSS_ISSUER_OR_CROSS_SECTOR_COMPARABILITY = (
        "NO_CROSS_ISSUER_OR_CROSS_SECTOR_COMPARABILITY"
    )
    NO_DURABILITY_OR_FORWARD_PERSISTENCE_CLAIM = (
        "NO_DURABILITY_OR_FORWARD_PERSISTENCE_CLAIM"
    )
    NO_AGGREGATE_QUALITY_SCORE_GRADE_OR_WEIGHT = (
        "NO_AGGREGATE_QUALITY_SCORE_GRADE_OR_WEIGHT"
    )
    NO_EXPECTED_RETURN_EFFECT = "NO_EXPECTED_RETURN_EFFECT"
    NO_CONFIDENCE_SUBSTITUTION = "NO_CONFIDENCE_SUBSTITUTION"
    NO_RECOMMENDATION_RANKING_ALLOCATION_OR_SIZING = (
        "NO_RECOMMENDATION_RANKING_ALLOCATION_OR_SIZING"
    )
    NO_EXECUTION_PRODUCTION_OR_V2_PROMOTION_AUTHORITY = (
        "NO_EXECUTION_PRODUCTION_OR_V2_PROMOTION_AUTHORITY"
    )
    NO_HISTORICAL_AS_OF_OR_PIT_AUTHORITY = (
        "NO_HISTORICAL_AS_OF_OR_PIT_AUTHORITY"
    )


_ANALYSIS_KIND = (
    CurrentAnnualOCFToPositiveNetIncomeAnalysisKind.
    CURRENT_ANNUAL_OCF_TO_POSITIVE_NET_INCOME
)
_AUTHORITY = (
    CurrentAnnualOCFToPositiveNetIncomeAuthority.
    QUALITY_CURRENT_ANNUAL_OCF_NET_INCOME_RELATIONSHIP_DIAGNOSTIC_ONLY
)
_LIMITATIONS = tuple(CurrentAnnualOCFToPositiveNetIncomeLimitation)
_HASH_LENGTH = 64
_ACCESSION_PATTERN = re.compile(r"[0-9]{10}-[0-9]{2}-[0-9]{6}")
_UPSTREAM_MODULE_NAME = (
    "economic_facts.sec_current_annual_operating_cash_flow_net_income"
)


@dataclass(frozen=True, slots=True)
class OperatingCashFlowToNetIncomeRatio:
    """Canonical reduced signed rational OCF-to-net-income relationship."""

    numerator: int
    denominator: int

    def __post_init__(self) -> None:
        if type(self.numerator) is not int or type(self.denominator) is not int:
            raise CurrentAnnualOCFToPositiveNetIncomeError(
                "Canonical integer ratio required"
            )
        if self.denominator == 0:
            raise CurrentAnnualOCFToPositiveNetIncomeError(
                "Canonical nonzero ratio denominator required"
            )
        numerator = self.numerator
        denominator = self.denominator
        if denominator < 0:
            numerator = -numerator
            denominator = -denominator
        divisor = gcd(numerator, denominator)
        object.__setattr__(self, "numerator", numerator // divisor)
        object.__setattr__(self, "denominator", denominator // divisor)


class _StableAnalyticalInputCarrier:
    __slots__ = ("_analytical_input_semantic_fingerprint",)


@dataclass(frozen=True, slots=True)
class CurrentAnnualOCFToPositiveNetIncomeResult(
    _StableAnalyticalInputCarrier
):
    contract_version: str
    methodology_version: str
    analysis_kind: CurrentAnnualOCFToPositiveNetIncomeAnalysisKind
    status: CurrentAnnualOCFToPositiveNetIncomeStatus
    reasons: tuple[CurrentAnnualOCFToPositiveNetIncomeReason, ...]
    upstream_status: Enum
    upstream_reasons: tuple[Enum, ...]
    route_local_issuer_key: str | None
    route_local_security_key: str | None
    source_cik: str | None
    period_start: str | None
    period_end: str | None
    upstream_qualification_semantic_id: str
    upstream_qualification_evidence_id: str
    operating_cash_flow_to_net_income_ratio: (
        OperatingCashFlowToNetIncomeRatio | None
    )
    authority: CurrentAnnualOCFToPositiveNetIncomeAuthority
    limitations: tuple[CurrentAnnualOCFToPositiveNetIncomeLimitation, ...]

    @property
    def semantic_id(self) -> str:
        try:
            analytical_input_semantic_fingerprint = (
                self._analytical_input_semantic_fingerprint
            )
        except AttributeError as exc:
            raise CurrentAnnualOCFToPositiveNetIncomeError(
                "Stable analytical-input semantics required"
            ) from exc
        if not _is_hash(analytical_input_semantic_fingerprint):
            raise CurrentAnnualOCFToPositiveNetIncomeError(
                "Canonical analytical-input semantic fingerprint required"
            )
        return _identity(
            "current-annual-ocf-to-positive-net-income-semantics",
            {
                "contract_version": self.contract_version,
                "methodology_version": self.methodology_version,
                "analysis_kind": self.analysis_kind,
                "status": self.status,
                "reasons": self.reasons,
                "upstream_status": self.upstream_status,
                "upstream_reasons": self.upstream_reasons,
                "route_local_issuer_key": self.route_local_issuer_key,
                "route_local_security_key": self.route_local_security_key,
                "source_cik": self.source_cik,
                "period_start": self.period_start,
                "period_end": self.period_end,
                "analytical_input_semantic_fingerprint": (
                    analytical_input_semantic_fingerprint
                ),
                "operating_cash_flow_to_net_income_ratio": (
                    self.operating_cash_flow_to_net_income_ratio
                ),
                "authority": self.authority,
                "limitations": self.limitations,
            },
        )

    @property
    def evidence_id(self) -> str:
        return _identity(
            "current-annual-ocf-to-positive-net-income-evidence",
            {
                "semantic_id": self.semantic_id,
                "upstream_qualification_evidence_id": (
                    self.upstream_qualification_evidence_id
                ),
            },
        )

    def to_dict(self) -> dict:
        payload = _canonical(self)
        payload["semantic_id"] = self.semantic_id
        payload["evidence_id"] = self.evidence_id
        return {"current_annual_ocf_to_positive_net_income": payload}


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
    raise CurrentAnnualOCFToPositiveNetIncomeError(
        "Unsupported OCF-to-net-income diagnostic identity value"
    )


def _identity(domain: str, value) -> str:
    payload = json.dumps(
        _canonical(value),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    )
    return hashlib.sha256((domain + "\0" + payload).encode("utf-8")).hexdigest()


def _exact_decimal_semantics(value: Decimal | None):
    if value is None:
        return None
    if type(value) is not Decimal or not value.is_finite():
        raise CurrentAnnualOCFToPositiveNetIncomeError(
            "Exact finite analytical Decimal required"
        )
    numerator, denominator = value.as_integer_ratio()
    return {"numerator": numerator, "denominator": denominator}


def _analytical_input_semantic_fingerprint(
    qualification,
    *,
    status,
    reasons,
) -> str:
    return _identity(
        "current-annual-ocf-to-positive-net-income-input-semantics",
        {
            "contract_version": CONTRACT_VERSION,
            "methodology_version": METHODOLOGY_VERSION,
            "analysis_kind": _ANALYSIS_KIND,
            "status": status,
            "reasons": reasons,
            "upstream_contract_version": qualification.contract_version,
            "upstream_qualifier_version": qualification.qualifier_version,
            "upstream_evidence_kind": qualification.evidence_kind,
            "upstream_status": qualification.status,
            "upstream_reasons": qualification.reasons,
            "upstream_profile_status": qualification.upstream_profile_status,
            "upstream_profile_reasons": qualification.upstream_profile_reasons,
            "route_local_issuer_key": qualification.route_local_issuer_key,
            "route_local_security_key": qualification.route_local_security_key,
            "source_cik": qualification.source_cik,
            "period_start": qualification.period_start,
            "period_end": qualification.period_end,
            "accounting_namespace": qualification.accounting_namespace,
            "accounting_basis": qualification.accounting_basis,
            "operating_cash_flow_concept": (
                qualification.operating_cash_flow_concept
            ),
            "net_income_concept": qualification.net_income_concept,
            "unit": qualification.unit,
            "operating_cash_flow": _exact_decimal_semantics(
                qualification.operating_cash_flow
            ),
            "net_income": _exact_decimal_semantics(
                qualification.net_income
            ),
            "upstream_authority": qualification.authority,
            "upstream_limitations": qualification.limitations,
        },
    )


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


def _canonical_upstream_module(qualification):
    qualification_type = type(qualification)
    module = sys.modules.get(qualification_type.__module__)
    if (
        qualification_type.__module__ != _UPSTREAM_MODULE_NAME
        or module is None
        or getattr(
            module,
            "CurrentAnnualOperatingCashFlowNetIncomeQualification",
            None,
        ) is not qualification_type
    ):
        raise CurrentAnnualOCFToPositiveNetIncomeError(
            "Exact CurrentAnnualOperatingCashFlowNetIncomeQualification required"
        )
    return module


def _validate_supporting_filing(filing, upstream) -> None:
    if (
        type(filing) is not upstream.OperatingCashFlowNetIncomeSupportingFiling
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
        or type(filing.operating_cash_flow_observation_ids) is not tuple
        or not filing.operating_cash_flow_observation_ids
        or filing.operating_cash_flow_observation_ids
        != tuple(sorted(set(filing.operating_cash_flow_observation_ids)))
        or any(
            not _is_hash(item)
            for item in filing.operating_cash_flow_observation_ids
        )
        or type(filing.net_income_observation_ids) is not tuple
        or not filing.net_income_observation_ids
        or filing.net_income_observation_ids
        != tuple(sorted(set(filing.net_income_observation_ids)))
        or any(not _is_hash(item) for item in filing.net_income_observation_ids)
        or set(filing.operating_cash_flow_observation_ids)
        & set(filing.net_income_observation_ids)
    ):
        raise CurrentAnnualOCFToPositiveNetIncomeError(
            "Canonical established supporting filing required"
        )


def _validate_profile_state_reasons(qualification, upstream) -> None:
    profile_upstream = upstream.upstream
    status = qualification.upstream_profile_status
    reasons = qualification.upstream_profile_reasons
    reason = profile_upstream.ProfileReason
    if reasons != tuple(sorted(set(reasons), key=lambda item: item.value)):
        raise CurrentAnnualOCFToPositiveNetIncomeError(
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
        raise CurrentAnnualOCFToPositiveNetIncomeError(
            "Canonical native profile status/reasons required"
        )


def _validate_shape(qualification, upstream) -> None:
    profile_upstream = upstream.upstream
    if (
        qualification.contract_version != upstream.CONTRACT_VERSION
        or qualification.qualifier_version != upstream.QUALIFIER_VERSION
        or qualification.evidence_kind != upstream.EVIDENCE_KIND
        or qualification.accounting_namespace != upstream.NAMESPACE
        or qualification.accounting_basis != upstream.ACCOUNTING_BASIS
        or qualification.operating_cash_flow_concept
        != upstream.OPERATING_CASH_FLOW_CONCEPT
        or qualification.net_income_concept != upstream.NET_INCOME_CONCEPT
        or qualification.unit != upstream.REVIEWED_UNIT
        or qualification.authority != upstream.AUTHORITY
        or qualification.limitations != tuple(
            upstream.CurrentAnnualOperatingCashFlowNetIncomeLimitation
        )
    ):
        raise CurrentAnnualOCFToPositiveNetIncomeError(
            "Canonical OCF/net-income qualification contract required"
        )
    if type(qualification.status) is not (
        upstream.CurrentAnnualOperatingCashFlowNetIncomeStatus
    ):
        raise CurrentAnnualOCFToPositiveNetIncomeError(
            "Unknown OCF/net-income qualification status"
        )
    if (
        type(qualification.reasons) is not tuple
        or any(
            type(reason) is not
            upstream.CurrentAnnualOperatingCashFlowNetIncomeReason
            for reason in qualification.reasons
        )
        or qualification.reasons != tuple(
            sorted(set(qualification.reasons), key=lambda item: item.value)
        )
    ):
        raise CurrentAnnualOCFToPositiveNetIncomeError(
            "Canonical native OCF/net-income reasons required"
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
        raise CurrentAnnualOCFToPositiveNetIncomeError(
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
        raise CurrentAnnualOCFToPositiveNetIncomeError(
            "Canonical OCF/net-income identity and route context required"
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
    operating_cash_flow_paths = (
        None,
        reason.OPERATING_CASH_FLOW_UNAVAILABLE,
        reason.EXACT_USD_UNIT_UNAVAILABLE,
        reason.FINITE_OPERATING_CASH_FLOW_VALUE_UNAVAILABLE,
        reason.EXACT_ANNUAL_PERIOD_PRESENTATION_UNAVAILABLE,
    )
    net_income_paths = (
        None,
        reason.NET_INCOME_UNAVAILABLE,
        reason.EXACT_USD_UNIT_UNAVAILABLE,
        reason.FINITE_NET_INCOME_VALUE_UNAVAILABLE,
        reason.EXACT_ANNUAL_PERIOD_PRESENTATION_UNAVAILABLE,
    )
    return frozenset(
        tuple(sorted(
            {
                item
                for item in (operating_reason, net_income_reason)
                if item is not None
            },
            key=lambda item: item.value,
        ))
        for operating_reason in operating_cash_flow_paths
        for net_income_reason in net_income_paths
        if operating_reason is not None or net_income_reason is not None
    )


def _local_conflict_reason_families(reason) -> frozenset[tuple]:
    competing_both = tuple(sorted(
        (
            reason.COMPETING_OPERATING_CASH_FLOW_VALUES,
            reason.COMPETING_NET_INCOME_VALUES,
        ),
        key=lambda item: item.value,
    ))
    return frozenset({
        (reason.CANONICAL_ROUTE_IDENTITY_CONFLICT,),
        (reason.CAPTURE_REPLAY_CONFLICT,),
        (reason.SOURCE_CIK_CONFLICT,),
        (reason.COMMON_FILING_METADATA_CONFLICT,),
        (reason.COMPETING_OPERATING_CASH_FLOW_VALUES,),
        (reason.COMPETING_NET_INCOME_VALUES,),
        competing_both,
    })


def _upstream_identities(qualification) -> tuple[str, str]:
    try:
        semantic_id = qualification.semantic_id
        evidence_id = qualification.evidence_id
    except (TypeError, ValueError, ArithmeticError) as exc:
        raise CurrentAnnualOCFToPositiveNetIncomeError(
            "Canonical upstream OCF/net-income identities required"
        ) from exc
    if not _is_hash(semantic_id) or not _is_hash(evidence_id):
        raise CurrentAnnualOCFToPositiveNetIncomeError(
            "Canonical upstream OCF/net-income identities required"
        )
    return semantic_id, evidence_id


def _validate_established(
    qualification,
    upstream,
) -> tuple[Decimal, Decimal]:
    profile_upstream = upstream.upstream
    operating_cash_flow = qualification.operating_cash_flow
    net_income = qualification.net_income
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
        or type(operating_cash_flow) is not Decimal
        or not operating_cash_flow.is_finite()
        or type(net_income) is not Decimal
        or not net_income.is_finite()
        or not _is_hash(qualification.capture_receipt_id)
        or not _is_hash(qualification.source_object_hash)
        or not qualification.captured_at
        or not qualification.capture_source_locator
    ):
        raise CurrentAnnualOCFToPositiveNetIncomeError(
            "Contradictory established OCF/net-income qualification"
        )

    operating_ids = qualification.selected_operating_cash_flow_observation_ids
    income_ids = qualification.selected_net_income_observation_ids
    accessions = qualification.supporting_accessions
    filings = qualification.supporting_filings
    if (
        type(operating_ids) is not tuple
        or not operating_ids
        or operating_ids != tuple(sorted(set(operating_ids)))
        or any(not _is_hash(item) for item in operating_ids)
        or type(income_ids) is not tuple
        or not income_ids
        or income_ids != tuple(sorted(set(income_ids)))
        or any(not _is_hash(item) for item in income_ids)
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
        raise CurrentAnnualOCFToPositiveNetIncomeError(
            "Canonical established OCF/net-income evidence surfaces required"
        )
    for filing in filings:
        _validate_supporting_filing(filing, upstream)
    flattened_operating_ids = tuple(
        observation_id
        for filing in filings
        for observation_id in filing.operating_cash_flow_observation_ids
    )
    flattened_income_ids = tuple(
        observation_id
        for filing in filings
        for observation_id in filing.net_income_observation_ids
    )
    if (
        tuple(item.accession for item in filings) != accessions
        or set(operating_ids) & set(income_ids)
        or len(flattened_operating_ids) != len(set(flattened_operating_ids))
        or len(flattened_income_ids) != len(set(flattened_income_ids))
        or tuple(sorted(flattened_operating_ids)) != operating_ids
        or tuple(sorted(flattened_income_ids)) != income_ids
    ):
        raise CurrentAnnualOCFToPositiveNetIncomeError(
            "Coherent established OCF/net-income provenance required"
        )
    return operating_cash_flow, net_income


def _validate_non_established(qualification, upstream) -> None:
    if (
        not qualification.reasons
        or qualification.operating_cash_flow is not None
        or qualification.net_income is not None
        or qualification.selected_operating_cash_flow_observation_ids != ()
        or qualification.selected_net_income_observation_ids != ()
        or qualification.supporting_accessions != ()
        or qualification.supporting_filings != ()
    ):
        raise CurrentAnnualOCFToPositiveNetIncomeError(
            "Canonical non-established OCF/net-income qualification required"
        )
    status = qualification.status
    reasons = qualification.reasons
    reason = upstream.CurrentAnnualOperatingCashFlowNetIncomeReason
    upstream_status = upstream.CurrentAnnualOperatingCashFlowNetIncomeStatus
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
        raise CurrentAnnualOCFToPositiveNetIncomeError(
            "Canonical non-established status/reason/profile path required"
        )


def _ratio_from_decimals(
    operating_cash_flow: Decimal,
    net_income: Decimal,
) -> OperatingCashFlowToNetIncomeRatio:
    cash_numerator, cash_denominator = operating_cash_flow.as_integer_ratio()
    income_numerator, income_denominator = net_income.as_integer_ratio()
    numerator = cash_numerator * income_denominator
    denominator = cash_denominator * income_numerator
    divisor = gcd(numerator, denominator)
    return OperatingCashFlowToNetIncomeRatio(
        numerator // divisor,
        denominator // divisor,
    )


def analyze_current_annual_ocf_to_positive_net_income(
    qualification,
) -> CurrentAnnualOCFToPositiveNetIncomeResult:
    """Report exact OCF per positive net-income dollar for qualified evidence."""
    upstream = _canonical_upstream_module(qualification)
    _validate_shape(qualification, upstream)
    upstream_status = qualification.status
    upstream_status_type = upstream.CurrentAnnualOperatingCashFlowNetIncomeStatus

    ratio = None
    if upstream_status is (
        upstream_status_type.PAIRED_OPERATING_CASH_FLOW_NET_INCOME_ESTABLISHED
    ):
        operating_cash_flow, net_income = _validate_established(
            qualification, upstream
        )
        if net_income > 0:
            status = CurrentAnnualOCFToPositiveNetIncomeStatus.AVAILABLE
            reasons = ()
            ratio = _ratio_from_decimals(operating_cash_flow, net_income)
        elif net_income == 0:
            status = CurrentAnnualOCFToPositiveNetIncomeStatus.NOT_APPLICABLE
            reasons = (
                CurrentAnnualOCFToPositiveNetIncomeReason.
                NET_INCOME_ZERO_DENOMINATOR,
            )
        else:
            status = CurrentAnnualOCFToPositiveNetIncomeStatus.NOT_APPLICABLE
            reasons = (
                CurrentAnnualOCFToPositiveNetIncomeReason.
                NET_INCOME_NEGATIVE_NOT_POSITIVE_EARNINGS,
            )
    else:
        _validate_non_established(qualification, upstream)
        mapping = {
            upstream_status_type.EVIDENCE_UNAVAILABLE: (
                CurrentAnnualOCFToPositiveNetIncomeStatus.UNAVAILABLE,
                CurrentAnnualOCFToPositiveNetIncomeReason.
                UPSTREAM_EVIDENCE_UNAVAILABLE,
            ),
            upstream_status_type.EVIDENCE_UNSUPPORTED: (
                CurrentAnnualOCFToPositiveNetIncomeStatus.UNSUPPORTED,
                CurrentAnnualOCFToPositiveNetIncomeReason.
                UPSTREAM_EVIDENCE_UNSUPPORTED,
            ),
            upstream_status_type.SOURCE_CONFLICT: (
                CurrentAnnualOCFToPositiveNetIncomeStatus.SOURCE_CONFLICT,
                CurrentAnnualOCFToPositiveNetIncomeReason.
                UPSTREAM_SOURCE_CONFLICT,
            ),
        }
        try:
            status, reason = mapping[upstream_status]
        except KeyError as exc:
            raise CurrentAnnualOCFToPositiveNetIncomeError(
                "Unknown OCF/net-income qualification status"
            ) from exc
        reasons = (reason,)

    upstream_semantic_id, upstream_evidence_id = _upstream_identities(
        qualification
    )
    analytical_input_semantic_fingerprint = (
        _analytical_input_semantic_fingerprint(
            qualification,
            status=status,
            reasons=reasons,
        )
    )
    result = CurrentAnnualOCFToPositiveNetIncomeResult(
        CONTRACT_VERSION,
        METHODOLOGY_VERSION,
        _ANALYSIS_KIND,
        status,
        reasons,
        qualification.status,
        qualification.reasons,
        qualification.route_local_issuer_key,
        qualification.route_local_security_key,
        qualification.source_cik,
        qualification.period_start,
        qualification.period_end,
        upstream_semantic_id,
        upstream_evidence_id,
        ratio,
        _AUTHORITY,
        _LIMITATIONS,
    )
    object.__setattr__(
        result,
        "_analytical_input_semantic_fingerprint",
        analytical_input_semantic_fingerprint,
    )
    return result
