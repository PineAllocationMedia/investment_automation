"""Exact bounded CURRENT annual OCF less PP&E cash-payments diagnostic.

The public boundary consumes two already-qualified canonical evidence objects.
It performs no acquisition, archive access, requalification, scoring, or
economic interpretation beyond exact signed subtraction.
"""
from __future__ import annotations

from dataclasses import dataclass, fields, is_dataclass
from datetime import date, datetime, timezone
from decimal import Decimal
from enum import Enum, StrEnum
import hashlib
import json
import re
import sys


CONTRACT_VERSION = (
    "2026-10-09-current-annual-ocf-less-ppe-acquisition-cash-payments-"
    "diagnostic-v1"
)
METHODOLOGY_VERSION = (
    "2026-10-09-exact-base-ten-ocf-minus-ppe-cash-payments-v1"
)


class CurrentAnnualOCFLessPPEAcquisitionCashPaymentsError(ValueError):
    """Wrong public type or contradictory canonical upstream object."""


class CurrentAnnualOCFLessPPEAcquisitionCashPaymentsAnalysisKind(StrEnum):
    CURRENT_ANNUAL_OCF_LESS_PPE_ACQUISITION_CASH_PAYMENTS = (
        "CURRENT_ANNUAL_OCF_LESS_PPE_ACQUISITION_CASH_PAYMENTS"
    )


class CurrentAnnualOCFLessPPEAcquisitionCashPaymentsStatus(StrEnum):
    AVAILABLE = "AVAILABLE"
    UNAVAILABLE = "UNAVAILABLE"
    UNSUPPORTED = "UNSUPPORTED"
    SOURCE_CONFLICT = "SOURCE_CONFLICT"


class CurrentAnnualOCFLessPPEAcquisitionCashPaymentsReason(StrEnum):
    UPSTREAM_OCF_EVIDENCE_UNAVAILABLE = "UPSTREAM_OCF_EVIDENCE_UNAVAILABLE"
    UPSTREAM_PPE_EVIDENCE_UNAVAILABLE = "UPSTREAM_PPE_EVIDENCE_UNAVAILABLE"
    UPSTREAM_OCF_EVIDENCE_UNSUPPORTED = "UPSTREAM_OCF_EVIDENCE_UNSUPPORTED"
    UPSTREAM_PPE_EVIDENCE_UNSUPPORTED = "UPSTREAM_PPE_EVIDENCE_UNSUPPORTED"
    UPSTREAM_OCF_SOURCE_CONFLICT = "UPSTREAM_OCF_SOURCE_CONFLICT"
    UPSTREAM_PPE_SOURCE_CONFLICT = "UPSTREAM_PPE_SOURCE_CONFLICT"
    NO_COMMON_SUPPORTING_ANNUAL_FILING_ACCESSION = (
        "NO_COMMON_SUPPORTING_ANNUAL_FILING_ACCESSION"
    )
    COMMON_SUPPORTING_FILING_METADATA_CONFLICT = (
        "COMMON_SUPPORTING_FILING_METADATA_CONFLICT"
    )


class CurrentAnnualOCFLessPPEAcquisitionCashPaymentsAuthority(StrEnum):
    QUALITY_CURRENT_ANNUAL_OCF_LESS_PPE_ACQUISITION_CASH_PAYMENTS_DIAGNOSTIC_ONLY = (
        "QUALITY_CURRENT_ANNUAL_OCF_LESS_PPE_ACQUISITION_CASH_PAYMENTS_"
        "DIAGNOSTIC_ONLY"
    )


class CurrentAnnualOCFLessPPEAcquisitionCashPaymentsLimitation(StrEnum):
    NO_UNIVERSAL_OR_GAAP_FREE_CASH_FLOW_CLAIM = (
        "NO_UNIVERSAL_OR_GAAP_FREE_CASH_FLOW_CLAIM"
    )
    NO_OWNER_EARNINGS_CLAIM = "NO_OWNER_EARNINGS_CLAIM"
    NO_DISTRIBUTABLE_CASH_CLAIM = "NO_DISTRIBUTABLE_CASH_CLAIM"
    NO_TOTAL_CAPEX_OR_TOTAL_REINVESTMENT_CLAIM = (
        "NO_TOTAL_CAPEX_OR_TOTAL_REINVESTMENT_CLAIM"
    )
    NO_MAINTENANCE_OR_GROWTH_CAPEX_CLASSIFICATION = (
        "NO_MAINTENANCE_OR_GROWTH_CAPEX_CLASSIFICATION"
    )
    NO_SOFTWARE_INTANGIBLE_OR_LEASE_INVESTMENT_COVERAGE = (
        "NO_SOFTWARE_INTANGIBLE_OR_LEASE_INVESTMENT_COVERAGE"
    )
    NO_ACQUISITION_OR_MA_SPENDING_COVERAGE = (
        "NO_ACQUISITION_OR_MA_SPENDING_COVERAGE"
    )
    NO_REINVESTMENT_OR_CAPITAL_ALLOCATION_QUALITY_JUDGMENT = (
        "NO_REINVESTMENT_OR_CAPITAL_ALLOCATION_QUALITY_JUDGMENT"
    )
    NO_HISTORICAL_CASH_FLOW_TREND = "NO_HISTORICAL_CASH_FLOW_TREND"
    NO_CROSS_COMPANY_OR_CROSS_SECTOR_COMPARABILITY = (
        "NO_CROSS_COMPANY_OR_CROSS_SECTOR_COMPARABILITY"
    )
    NO_GOOD_OR_BAD_THRESHOLD = "NO_GOOD_OR_BAD_THRESHOLD"
    NO_QUALITY_SCORE_GRADE_WEIGHT_AGGREGATE_OR_RANKING = (
        "NO_QUALITY_SCORE_GRADE_WEIGHT_AGGREGATE_OR_RANKING"
    )
    NO_DURABILITY_CONCLUSION = "NO_DURABILITY_CONCLUSION"
    NO_EXPECTED_RETURN_OR_CONFIDENCE_MODIFICATION = (
        "NO_EXPECTED_RETURN_OR_CONFIDENCE_MODIFICATION"
    )
    NO_RECOMMENDATION_SIZING_ALLOCATION_OR_EXECUTION = (
        "NO_RECOMMENDATION_SIZING_ALLOCATION_OR_EXECUTION"
    )
    NO_PRODUCTION_DEPLOYMENT_OR_V2_PROMOTION_AUTHORITY = (
        "NO_PRODUCTION_DEPLOYMENT_OR_V2_PROMOTION_AUTHORITY"
    )
    NO_HISTORICAL_AS_OF_OR_PIT_AUTHORITY = (
        "NO_HISTORICAL_AS_OF_OR_PIT_AUTHORITY"
    )


_ANALYSIS_KIND = (
    CurrentAnnualOCFLessPPEAcquisitionCashPaymentsAnalysisKind.
    CURRENT_ANNUAL_OCF_LESS_PPE_ACQUISITION_CASH_PAYMENTS
)
_AUTHORITY = (
    CurrentAnnualOCFLessPPEAcquisitionCashPaymentsAuthority.
    QUALITY_CURRENT_ANNUAL_OCF_LESS_PPE_ACQUISITION_CASH_PAYMENTS_DIAGNOSTIC_ONLY
)
_LIMITATIONS = tuple(CurrentAnnualOCFLessPPEAcquisitionCashPaymentsLimitation)
_HASH_LENGTH = 64
_CIK_PATTERN = re.compile(r"[0-9]{10}")
_ACCESSION_PATTERN = re.compile(r"[0-9]{10}-[0-9]{2}-[0-9]{6}")
_OCF_UPSTREAM_MODULE_NAME = (
    "economic_facts.sec_current_annual_operating_cash_flow_net_income"
)
_PPE_UPSTREAM_MODULE_NAME = (
    "economic_facts.sec_current_annual_ppe_acquisition_cash_payments"
)


class _EvidenceCarrier:
    __slots__ = ("_evidence_fingerprint",)


@dataclass(frozen=True, slots=True)
class CurrentAnnualOCFLessPPEAcquisitionCashPaymentsResult(_EvidenceCarrier):
    contract_version: str
    methodology_version: str
    analysis_kind: CurrentAnnualOCFLessPPEAcquisitionCashPaymentsAnalysisKind
    status: CurrentAnnualOCFLessPPEAcquisitionCashPaymentsStatus
    reasons: tuple[CurrentAnnualOCFLessPPEAcquisitionCashPaymentsReason, ...]
    upstream_ocf_status: Enum
    upstream_ocf_reasons: tuple[Enum, ...]
    upstream_ppe_status: Enum
    upstream_ppe_reasons: tuple[Enum, ...]
    source_cik: str | None
    period_start: str | None
    period_end: str | None
    accounting_namespace: str
    accounting_basis: str
    unit: str
    operating_cash_flow_concept: str
    ppe_acquisition_cash_payments_concept: str
    operating_cash_flow: Decimal | None
    ppe_acquisition_cash_payments: Decimal | None
    ocf_less_ppe_acquisition_cash_payments: Decimal | None
    upstream_ocf_qualification_semantic_id: str
    upstream_ocf_qualification_evidence_id: str
    upstream_ppe_qualification_semantic_id: str
    upstream_ppe_qualification_evidence_id: str
    common_supporting_accessions: tuple[str, ...]
    authority: CurrentAnnualOCFLessPPEAcquisitionCashPaymentsAuthority
    limitations: tuple[CurrentAnnualOCFLessPPEAcquisitionCashPaymentsLimitation, ...]

    @property
    def semantic_id(self) -> str:
        return _identity(
            "current-annual-ocf-less-ppe-cash-payments-semantics",
            {
                "contract_version": self.contract_version,
                "methodology_version": self.methodology_version,
                "analysis_kind": self.analysis_kind,
                "status": self.status,
                "reasons": self.reasons,
                "source_cik": self.source_cik,
                "period_start": self.period_start,
                "period_end": self.period_end,
                "accounting_namespace": self.accounting_namespace,
                "accounting_basis": self.accounting_basis,
                "unit": self.unit,
                "operating_cash_flow_concept": self.operating_cash_flow_concept,
                "ppe_acquisition_cash_payments_concept": (
                    self.ppe_acquisition_cash_payments_concept
                ),
                "operating_cash_flow": _exact_decimal_semantics(
                    self.operating_cash_flow
                ),
                "ppe_acquisition_cash_payments": _exact_decimal_semantics(
                    self.ppe_acquisition_cash_payments
                ),
                "ocf_less_ppe_acquisition_cash_payments": (
                    _exact_decimal_semantics(
                        self.ocf_less_ppe_acquisition_cash_payments
                    )
                ),
                "authority": self.authority,
                "limitations": self.limitations,
            },
        )

    @property
    def evidence_id(self) -> str:
        try:
            fingerprint = self._evidence_fingerprint
        except AttributeError as exc:
            raise CurrentAnnualOCFLessPPEAcquisitionCashPaymentsError(
                "Complete upstream evidence fingerprint required"
            ) from exc
        if not _is_hash(fingerprint):
            raise CurrentAnnualOCFLessPPEAcquisitionCashPaymentsError(
                "Canonical upstream evidence fingerprint required"
            )
        return _identity(
            "current-annual-ocf-less-ppe-cash-payments-evidence",
            {"semantic_id": self.semantic_id, "evidence_fingerprint": fingerprint},
        )

    def to_dict(self) -> dict:
        payload = _canonical(self)
        payload["semantic_id"] = self.semantic_id
        payload["evidence_id"] = self.evidence_id
        return {
            "current_annual_ocf_less_ppe_acquisition_cash_payments": payload
        }


def _canonical(value):
    if isinstance(value, Enum):
        return value.value
    if type(value) is Decimal:
        return _exact_decimal_semantics(value)
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
    raise CurrentAnnualOCFLessPPEAcquisitionCashPaymentsError(
        "Unsupported diagnostic identity value"
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
        raise CurrentAnnualOCFLessPPEAcquisitionCashPaymentsError(
            "Exact finite analytical Decimal required"
        )
    numerator, denominator = value.as_integer_ratio()
    return {"numerator": numerator, "denominator": denominator}


def _is_hash(value) -> bool:
    return (
        type(value) is str
        and len(value) == _HASH_LENGTH
        and all(character in "0123456789abcdef" for character in value)
    )


def _valid_date(value) -> bool:
    if type(value) is not str:
        return False
    try:
        return date.fromisoformat(value).isoformat() == value
    except ValueError:
        return False


def _valid_period(start, end) -> bool:
    if start is None or end is None:
        return start is None and end is None
    return _valid_date(start) and _valid_date(end) and start <= end


def _valid_timestamp(value) -> bool:
    if type(value) is not str or not value or value != value.strip():
        return False
    if not value.endswith("Z"):
        return False
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        canonical = parsed.astimezone(timezone.utc).isoformat().replace(
            "+00:00", "Z"
        )
    except (ValueError, OverflowError):
        return False
    return parsed.tzinfo is not None and canonical == value


def _ordered_unique(values) -> bool:
    return values == tuple(sorted(set(values)))


def _canonical_upstream_module(qualification, *, is_ocf: bool):
    qualification_type = type(qualification)
    module_name = (
        _OCF_UPSTREAM_MODULE_NAME if is_ocf else _PPE_UPSTREAM_MODULE_NAME
    )
    type_name = (
        "CurrentAnnualOperatingCashFlowNetIncomeQualification"
        if is_ocf
        else "CurrentAnnualPPEAcquisitionCashPaymentsQualification"
    )
    module = sys.modules.get(qualification_type.__module__)
    if (
        qualification_type.__module__ != module_name
        or module is None
        or getattr(module, type_name, None) is not qualification_type
    ):
        raise CurrentAnnualOCFLessPPEAcquisitionCashPaymentsError(
            "Exact canonical qualification runtime types required"
        )
    return module


def _validate_profile_state(qualification, module) -> None:
    profile = module.upstream
    status = qualification.upstream_profile_status
    reasons = qualification.upstream_profile_reasons
    reason = profile.ProfileReason
    if (
        type(status) is not profile.OrdinaryCompounderProfileStatus
        or type(reasons) is not tuple
        or any(type(item) is not reason for item in reasons)
        or reasons != tuple(sorted(set(reasons), key=lambda item: item.value))
    ):
        raise CurrentAnnualOCFLessPPEAcquisitionCashPaymentsError(
            "Canonical native ordinary-compounder profile state required"
        )
    unavailable = frozenset({
        reason.PR5C_NOT_ESTABLISHED,
        reason.SIC_MISSING_OR_INVALID,
        reason.SIC_DESCRIPTION_MISSING_OR_INVALID,
        reason.POSITIVE_FIVE_PERIOD_ROUTE_NOT_ESTABLISHED,
        reason.REPORTING_SUBJECT_STABILITY_NOT_ESTABLISHED,
        reason.MIXED_STRUCTURE_UNRESOLVED,
    })
    decision_derived = frozenset({
        reason.POSITIVE_FIVE_PERIOD_ROUTE_NOT_ESTABLISHED,
        reason.REPORTING_SUBJECT_STABILITY_NOT_ESTABLISHED,
        reason.MIXED_STRUCTURE_UNRESOLVED,
        reason.UNSUPPORTED_SIC_PROFILE,
    })
    if status is profile.OrdinaryCompounderProfileStatus.ORDINARY_COMPOUNDER_PROFILE_ESTABLISHED:
        coherent = reasons == ()
    elif status is profile.OrdinaryCompounderProfileStatus.PROFILE_UNAVAILABLE:
        coherent = bool(reasons) and set(reasons) <= unavailable
    elif status is profile.OrdinaryCompounderProfileStatus.PROFILE_UNSUPPORTED:
        coherent = (
            reason.UNSUPPORTED_SIC_PROFILE in reasons
            and reason.REPLAY_IDENTITY_MISMATCH not in reasons
        )
    elif status is profile.OrdinaryCompounderProfileStatus.SOURCE_CONFLICT:
        coherent = (
            reason.REPLAY_IDENTITY_MISMATCH in reasons
            and reason.UNSUPPORTED_SIC_PROFILE not in reasons
        )
    else:
        coherent = False
    if (
        reason.SIC_DESCRIPTION_MISSING_OR_INVALID in reasons
        and set(reasons) & decision_derived
    ):
        coherent = False
    if (
        status is profile.OrdinaryCompounderProfileStatus.PROFILE_UNAVAILABLE
        and reason.POSITIVE_FIVE_PERIOD_ROUTE_NOT_ESTABLISHED in reasons
    ):
        coherent = False
    if not coherent:
        raise CurrentAnnualOCFLessPPEAcquisitionCashPaymentsError(
            "Contradictory native ordinary-compounder profile state"
        )


def _validate_common_shape(qualification, module, *, is_ocf: bool) -> None:
    expected_type = (
        module.CurrentAnnualOperatingCashFlowNetIncomeQualification
        if is_ocf
        else module.CurrentAnnualPPEAcquisitionCashPaymentsQualification
    )
    status_type = (
        module.CurrentAnnualOperatingCashFlowNetIncomeStatus
        if is_ocf
        else module.CurrentAnnualPPEAcquisitionCashPaymentsStatus
    )
    reason_type = (
        module.CurrentAnnualOperatingCashFlowNetIncomeReason
        if is_ocf
        else module.CurrentAnnualPPEAcquisitionCashPaymentsReason
    )
    if type(qualification) is not expected_type:
        raise CurrentAnnualOCFLessPPEAcquisitionCashPaymentsError(
            "Exact canonical qualification runtime types required"
        )
    concept_ok = (
        qualification.operating_cash_flow_concept
        == module.OPERATING_CASH_FLOW_CONCEPT
        and qualification.net_income_concept == module.NET_INCOME_CONCEPT
        if is_ocf
        else qualification.concept == module.PPE_ACQUISITION_CASH_PAYMENTS_CONCEPT
    )
    limitation_type = (
        module.CurrentAnnualOperatingCashFlowNetIncomeLimitation
        if is_ocf
        else module.CurrentAnnualPPEAcquisitionCashPaymentsLimitation
    )
    if (
        qualification.contract_version != module.CONTRACT_VERSION
        or qualification.qualifier_version != module.QUALIFIER_VERSION
        or qualification.evidence_kind != module.EVIDENCE_KIND
        or qualification.accounting_namespace != module.NAMESPACE
        or qualification.accounting_basis != module.ACCOUNTING_BASIS
        or qualification.unit != module.REVIEWED_UNIT
        or not concept_ok
        or qualification.authority != module.AUTHORITY
        or qualification.limitations != tuple(limitation_type)
        or type(qualification.status) is not status_type
        or type(qualification.reasons) is not tuple
        or any(type(item) is not reason_type for item in qualification.reasons)
        or qualification.reasons
        != tuple(sorted(set(qualification.reasons), key=lambda item: item.value))
    ):
        raise CurrentAnnualOCFLessPPEAcquisitionCashPaymentsError(
            "Canonical upstream qualification contract required"
        )
    _validate_profile_state(qualification, module)
    route = (
        qualification.route_local_issuer_key,
        qualification.route_local_security_key,
    )
    receipt = (
        qualification.capture_receipt_id,
        qualification.source_object_hash,
        qualification.captured_at,
        qualification.capture_source_locator,
    )
    route_ok = all(value is None for value in route) or all(
        _is_hash(value) for value in route
    )
    receipt_ok = all(value is None for value in receipt) or (
        _is_hash(receipt[0])
        and _is_hash(receipt[1])
        and _valid_timestamp(receipt[2])
        and type(receipt[3]) is str
        and bool(receipt[3])
        and receipt[3] == receipt[3].strip()
    )
    cik_ok = qualification.source_cik is None or (
        type(qualification.source_cik) is str
        and _CIK_PATTERN.fullmatch(qualification.source_cik) is not None
    )
    if (
        not route_ok
        or not receipt_ok
        or not cik_ok
        or not _valid_period(qualification.period_start, qualification.period_end)
        or any(not _is_hash(value) for value in (
            qualification.upstream_profile_semantic_id,
            qualification.upstream_comparability_semantic_id,
            qualification.upstream_profile_evidence_id,
            qualification.upstream_comparability_evidence_id,
        ))
    ):
        raise CurrentAnnualOCFLessPPEAcquisitionCashPaymentsError(
            "Canonical upstream identity and provenance shape required"
        )


def _validate_filing(filing, module, *, is_ocf: bool) -> None:
    filing_type = (
        module.OperatingCashFlowNetIncomeSupportingFiling
        if is_ocf
        else module.PPEAcquisitionCashPaymentsSupportingFiling
    )
    observation_groups = (
        (
            filing.operating_cash_flow_observation_ids,
            filing.net_income_observation_ids,
        )
        if is_ocf
        else (filing.observation_ids,)
    )
    if (
        type(filing) is not filing_type
        or type(filing.accession) is not str
        or _ACCESSION_PATTERN.fullmatch(filing.accession) is None
        or type(filing.forms) is not tuple
        or len(filing.forms) != 1
        or filing.forms[0] not in ("10-K", "10-K/A")
        or type(filing.filed_dates) is not tuple
        or len(filing.filed_dates) != 1
        or not _valid_date(filing.filed_dates[0])
        or type(filing.fiscal_years) is not tuple
        or len(filing.fiscal_years) != 1
        or type(filing.fiscal_years[0]) is not int
        or any(
            type(group) is not tuple
            or not group
            or not _ordered_unique(group)
            or any(not _is_hash(value) for value in group)
            for group in observation_groups
        )
        or (
            is_ocf
            and bool(set(observation_groups[0]) & set(observation_groups[1]))
        )
    ):
        raise CurrentAnnualOCFLessPPEAcquisitionCashPaymentsError(
            "Canonical selected supporting-filing provenance required"
        )


def _validate_established(qualification, module, *, is_ocf: bool) -> None:
    profile = module.upstream
    value_groups = (
        (
            qualification.operating_cash_flow,
            qualification.net_income,
            qualification.selected_operating_cash_flow_observation_ids,
            qualification.selected_net_income_observation_ids,
        )
        if is_ocf
        else (
            qualification.ppe_acquisition_cash_payments,
            qualification.selected_observation_ids,
        )
    )
    values = value_groups[:2] if is_ocf else value_groups[:1]
    selected_groups = value_groups[2:] if is_ocf else value_groups[1:]
    if (
        qualification.reasons != ()
        or qualification.upstream_profile_status is not
        profile.OrdinaryCompounderProfileStatus.ORDINARY_COMPOUNDER_PROFILE_ESTABLISHED
        or qualification.upstream_profile_reasons != ()
        or qualification.source_cik is None
        or qualification.period_start is None
        or qualification.period_end is None
        or any(type(value) is not Decimal or not value.is_finite() for value in values)
        or not all(_is_hash(value) for value in (
            qualification.route_local_issuer_key,
            qualification.route_local_security_key,
            qualification.capture_receipt_id,
            qualification.source_object_hash,
        ))
        or not _valid_timestamp(qualification.captured_at)
        or type(qualification.capture_source_locator) is not str
        or not qualification.capture_source_locator
        or any(
            type(group) is not tuple
            or not group
            or not _ordered_unique(group)
            or any(not _is_hash(item) for item in group)
            for group in selected_groups
        )
        or (is_ocf and bool(set(selected_groups[0]) & set(selected_groups[1])))
        or type(qualification.supporting_accessions) is not tuple
        or not qualification.supporting_accessions
        or not _ordered_unique(qualification.supporting_accessions)
        or any(
            type(item) is not str or _ACCESSION_PATTERN.fullmatch(item) is None
            for item in qualification.supporting_accessions
        )
        or type(qualification.supporting_filings) is not tuple
        or len(qualification.supporting_filings)
        != len(qualification.supporting_accessions)
    ):
        raise CurrentAnnualOCFLessPPEAcquisitionCashPaymentsError(
            "Contradictory established upstream qualification"
        )
    for filing in qualification.supporting_filings:
        _validate_filing(filing, module, is_ocf=is_ocf)
    if tuple(filing.accession for filing in qualification.supporting_filings) != (
        qualification.supporting_accessions
    ):
        raise CurrentAnnualOCFLessPPEAcquisitionCashPaymentsError(
            "Supporting accessions and filings must partition identically"
        )
    flattened = []
    if is_ocf:
        flattened = [
            tuple(sorted(
                observation
                for filing in qualification.supporting_filings
                for observation in getattr(filing, attribute)
            ))
            for attribute in (
                "operating_cash_flow_observation_ids",
                "net_income_observation_ids",
            )
        ]
    else:
        flattened = [tuple(sorted(
            observation
            for filing in qualification.supporting_filings
            for observation in filing.observation_ids
        ))]
    if any(actual != expected for actual, expected in zip(
        flattened, selected_groups, strict=True
    )):
        raise CurrentAnnualOCFLessPPEAcquisitionCashPaymentsError(
            "Selected observations must exactly partition supporting filings"
        )


def _validate_non_established(qualification, module, *, is_ocf: bool) -> None:
    numeric = (
        (qualification.operating_cash_flow, qualification.net_income)
        if is_ocf
        else (qualification.ppe_acquisition_cash_payments,)
    )
    selected = (
        (
            qualification.selected_operating_cash_flow_observation_ids,
            qualification.selected_net_income_observation_ids,
        )
        if is_ocf
        else (qualification.selected_observation_ids,)
    )
    if (
        not qualification.reasons
        or any(value is not None for value in numeric)
        or any(value != () for value in selected)
        or qualification.supporting_accessions != ()
        or qualification.supporting_filings != ()
    ):
        raise CurrentAnnualOCFLessPPEAcquisitionCashPaymentsError(
            "Canonical non-established upstream qualification required"
        )
    status_type = (
        module.CurrentAnnualOperatingCashFlowNetIncomeStatus
        if is_ocf
        else module.CurrentAnnualPPEAcquisitionCashPaymentsStatus
    )
    reason = (
        module.CurrentAnnualOperatingCashFlowNetIncomeReason
        if is_ocf
        else module.CurrentAnnualPPEAcquisitionCashPaymentsReason
    )
    profile = module.upstream
    status = qualification.status
    reasons = qualification.reasons
    route_present = all(_is_hash(value) for value in (
        qualification.route_local_issuer_key,
        qualification.route_local_security_key,
    )) and qualification.period_start is not None and qualification.period_end is not None
    receipt_present = (
        _is_hash(qualification.capture_receipt_id)
        and _is_hash(qualification.source_object_hash)
        and _valid_timestamp(qualification.captured_at)
        and type(qualification.capture_source_locator) is str
        and bool(qualification.capture_source_locator)
    )
    if reasons == (reason.UPSTREAM_PROFILE_UNAVAILABLE,):
        coherent = (
            status is status_type.EVIDENCE_UNAVAILABLE
            and qualification.upstream_profile_status is
            profile.OrdinaryCompounderProfileStatus.PROFILE_UNAVAILABLE
        )
    elif reasons == (reason.UPSTREAM_PROFILE_UNSUPPORTED,):
        coherent = (
            status is status_type.EVIDENCE_UNSUPPORTED
            and qualification.upstream_profile_status is
            profile.OrdinaryCompounderProfileStatus.PROFILE_UNSUPPORTED
        )
    elif reasons == (reason.UPSTREAM_SOURCE_CONFLICT,):
        coherent = (
            status is status_type.SOURCE_CONFLICT
            and qualification.upstream_profile_status is
            profile.OrdinaryCompounderProfileStatus.SOURCE_CONFLICT
        )
    else:
        if is_ocf:
            operating_paths = (
                None,
                reason.OPERATING_CASH_FLOW_UNAVAILABLE,
                reason.EXACT_USD_UNIT_UNAVAILABLE,
                reason.FINITE_OPERATING_CASH_FLOW_VALUE_UNAVAILABLE,
                reason.EXACT_ANNUAL_PERIOD_PRESENTATION_UNAVAILABLE,
            )
            income_paths = (
                None,
                reason.NET_INCOME_UNAVAILABLE,
                reason.EXACT_USD_UNIT_UNAVAILABLE,
                reason.FINITE_NET_INCOME_VALUE_UNAVAILABLE,
                reason.EXACT_ANNUAL_PERIOD_PRESENTATION_UNAVAILABLE,
            )
            unavailable_families = {
                tuple(sorted(
                    {
                        item
                        for item in (operating_reason, income_reason)
                        if item is not None
                    },
                    key=lambda item: item.value,
                ))
                for operating_reason in operating_paths
                for income_reason in income_paths
                if operating_reason is not None or income_reason is not None
            }
            unavailable_families.add(
                (reason.NO_COMMON_ANNUAL_FILING_ACCESSION,)
            )
            conflict_families = {
                (reason.CANONICAL_ROUTE_IDENTITY_CONFLICT,),
                (reason.CAPTURE_REPLAY_CONFLICT,),
                (reason.SOURCE_CIK_CONFLICT,),
                (reason.COMPETING_OPERATING_CASH_FLOW_VALUES,),
                (reason.COMPETING_NET_INCOME_VALUES,),
                tuple(sorted((
                    reason.COMPETING_OPERATING_CASH_FLOW_VALUES,
                    reason.COMPETING_NET_INCOME_VALUES,
                ), key=lambda item: item.value)),
                (reason.COMMON_FILING_METADATA_CONFLICT,),
            }
        else:
            unavailable_families = {
                (reason.PPE_ACQUISITION_CASH_PAYMENTS_UNAVAILABLE,),
                (reason.EXACT_USD_UNIT_UNAVAILABLE,),
                (
                    reason.
                    FINITE_PPE_ACQUISITION_CASH_PAYMENTS_VALUE_UNAVAILABLE,
                ),
                (reason.EXACT_ANNUAL_PERIOD_PRESENTATION_UNAVAILABLE,),
            }
            conflict_families = {
                (reason.CANONICAL_ROUTE_IDENTITY_CONFLICT,),
                (reason.CAPTURE_REPLAY_CONFLICT,),
                (reason.SOURCE_CIK_CONFLICT,),
                (reason.COMPETING_PPE_ACQUISITION_CASH_PAYMENTS_VALUES,),
                (reason.ANNUAL_FILING_METADATA_CONFLICT,),
            }
        established_profile = (
            qualification.upstream_profile_status is
            profile.OrdinaryCompounderProfileStatus.ORDINARY_COMPOUNDER_PROFILE_ESTABLISHED
            and qualification.upstream_profile_reasons == ()
        )
        if status is status_type.EVIDENCE_UNAVAILABLE:
            coherent = (
                reasons in unavailable_families
                and established_profile
                and route_present
                and receipt_present
            )
        elif status is status_type.SOURCE_CONFLICT:
            coherent = (
                reasons in conflict_families
                and established_profile
                and route_present
                and (
                    receipt_present
                    or reasons == (reason.CANONICAL_ROUTE_IDENTITY_CONFLICT,)
                )
            )
        else:
            coherent = False
    if not coherent:
        raise CurrentAnnualOCFLessPPEAcquisitionCashPaymentsError(
            "Factory-impossible upstream status/reason projection"
        )


def _upstream_identities(qualification, label: str) -> tuple[str, str]:
    try:
        semantic_id = qualification.semantic_id
        evidence_id = qualification.evidence_id
    except (TypeError, ValueError, ArithmeticError) as exc:
        raise CurrentAnnualOCFLessPPEAcquisitionCashPaymentsError(
            f"Canonical {label} qualification identities required"
        ) from exc
    if not _is_hash(semantic_id) or not _is_hash(evidence_id):
        raise CurrentAnnualOCFLessPPEAcquisitionCashPaymentsError(
            f"Canonical {label} qualification identities required"
        )
    return semantic_id, evidence_id


def _metadata_by_accession(qualification) -> dict[str, tuple[str, str, int]]:
    return {
        filing.accession: (
            filing.forms[0],
            filing.filed_dates[0],
            filing.fiscal_years[0],
        )
        for filing in qualification.supporting_filings
    }


def _exact_subtract(minuend: Decimal, subtrahend: Decimal) -> Decimal:
    """Subtract finite Decimals by integer coefficient/exponent alignment."""
    def coefficient_and_exponent(value: Decimal) -> tuple[int, int]:
        sign, digits, exponent = value.as_tuple()
        coefficient = int("".join(str(digit) for digit in digits) or "0")
        return (-coefficient if sign else coefficient), exponent

    left_coefficient, left_exponent = coefficient_and_exponent(minuend)
    right_coefficient, right_exponent = coefficient_and_exponent(subtrahend)
    common_exponent = min(left_exponent, right_exponent)
    coefficient = (
        left_coefficient * (10 ** (left_exponent - common_exponent))
        - right_coefficient * (10 ** (right_exponent - common_exponent))
    )
    if coefficient == 0:
        return Decimal(0)
    sign = int(coefficient < 0)
    digits = tuple(int(character) for character in str(abs(coefficient)))
    return Decimal((sign, digits, common_exponent))


def _context_value(left, right, label: str):
    if left is not None and right is not None and left != right:
        raise CurrentAnnualOCFLessPPEAcquisitionCashPaymentsError(
            f"Contradictory cross-foundation {label}"
        )
    return left if left is not None and right is not None else None


def _project_upstream_failure(qualification, module, *, is_ocf: bool):
    if is_ocf:
        status_type = module.CurrentAnnualOperatingCashFlowNetIncomeStatus
        mapping = {
            status_type.EVIDENCE_UNAVAILABLE: (
                CurrentAnnualOCFLessPPEAcquisitionCashPaymentsStatus.UNAVAILABLE,
                CurrentAnnualOCFLessPPEAcquisitionCashPaymentsReason.
                UPSTREAM_OCF_EVIDENCE_UNAVAILABLE,
            ),
            status_type.EVIDENCE_UNSUPPORTED: (
                CurrentAnnualOCFLessPPEAcquisitionCashPaymentsStatus.UNSUPPORTED,
                CurrentAnnualOCFLessPPEAcquisitionCashPaymentsReason.
                UPSTREAM_OCF_EVIDENCE_UNSUPPORTED,
            ),
            status_type.SOURCE_CONFLICT: (
                CurrentAnnualOCFLessPPEAcquisitionCashPaymentsStatus.SOURCE_CONFLICT,
                CurrentAnnualOCFLessPPEAcquisitionCashPaymentsReason.
                UPSTREAM_OCF_SOURCE_CONFLICT,
            ),
        }
    else:
        status_type = module.CurrentAnnualPPEAcquisitionCashPaymentsStatus
        mapping = {
            status_type.EVIDENCE_UNAVAILABLE: (
                CurrentAnnualOCFLessPPEAcquisitionCashPaymentsStatus.UNAVAILABLE,
                CurrentAnnualOCFLessPPEAcquisitionCashPaymentsReason.
                UPSTREAM_PPE_EVIDENCE_UNAVAILABLE,
            ),
            status_type.EVIDENCE_UNSUPPORTED: (
                CurrentAnnualOCFLessPPEAcquisitionCashPaymentsStatus.UNSUPPORTED,
                CurrentAnnualOCFLessPPEAcquisitionCashPaymentsReason.
                UPSTREAM_PPE_EVIDENCE_UNSUPPORTED,
            ),
            status_type.SOURCE_CONFLICT: (
                CurrentAnnualOCFLessPPEAcquisitionCashPaymentsStatus.SOURCE_CONFLICT,
                CurrentAnnualOCFLessPPEAcquisitionCashPaymentsReason.
                UPSTREAM_PPE_SOURCE_CONFLICT,
            ),
        }
    return mapping.get(qualification.status)


def analyze_current_annual_ocf_less_ppe_acquisition_cash_payments(
    ocf_qualification,
    ppe_qualification,
) -> CurrentAnnualOCFLessPPEAcquisitionCashPaymentsResult:
    """Report exact signed OCF minus PP&E cash payments for coherent evidence."""
    ocf_upstream = _canonical_upstream_module(
        ocf_qualification, is_ocf=True
    )
    ppe_upstream = _canonical_upstream_module(
        ppe_qualification, is_ocf=False
    )
    _validate_common_shape(ocf_qualification, ocf_upstream, is_ocf=True)
    _validate_common_shape(ppe_qualification, ppe_upstream, is_ocf=False)
    ocf_established = ocf_qualification.status is (
        ocf_upstream.CurrentAnnualOperatingCashFlowNetIncomeStatus.
        PAIRED_OPERATING_CASH_FLOW_NET_INCOME_ESTABLISHED
    )
    ppe_established = ppe_qualification.status is (
        ppe_upstream.CurrentAnnualPPEAcquisitionCashPaymentsStatus.
        PPE_ACQUISITION_CASH_PAYMENTS_ESTABLISHED
    )
    if ocf_established:
        _validate_established(ocf_qualification, ocf_upstream, is_ocf=True)
    else:
        _validate_non_established(ocf_qualification, ocf_upstream, is_ocf=True)
    if ppe_established:
        _validate_established(ppe_qualification, ppe_upstream, is_ocf=False)
    else:
        _validate_non_established(ppe_qualification, ppe_upstream, is_ocf=False)

    source_cik = _context_value(
        ocf_qualification.source_cik, ppe_qualification.source_cik, "source CIK"
    )
    period_start = _context_value(
        ocf_qualification.period_start,
        ppe_qualification.period_start,
        "annual period start",
    )
    period_end = _context_value(
        ocf_qualification.period_end,
        ppe_qualification.period_end,
        "annual period end",
    )

    common_accessions = ()
    operating_cash_flow = None
    ppe_cash_payments = None
    difference = None
    if ocf_established and ppe_established:
        if source_cik is None or period_start is None or period_end is None:
            raise CurrentAnnualOCFLessPPEAcquisitionCashPaymentsError(
                "Established inputs require complete shared issuer and period"
            )
        ocf_metadata = _metadata_by_accession(ocf_qualification)
        ppe_metadata = _metadata_by_accession(ppe_qualification)
        common_accessions = tuple(sorted(set(ocf_metadata) & set(ppe_metadata)))
        if not common_accessions:
            status = CurrentAnnualOCFLessPPEAcquisitionCashPaymentsStatus.UNAVAILABLE
            reasons = (
                CurrentAnnualOCFLessPPEAcquisitionCashPaymentsReason.
                NO_COMMON_SUPPORTING_ANNUAL_FILING_ACCESSION,
            )
        elif any(
            ocf_metadata[accession] != ppe_metadata[accession]
            for accession in common_accessions
        ):
            status = (
                CurrentAnnualOCFLessPPEAcquisitionCashPaymentsStatus.SOURCE_CONFLICT
            )
            reasons = (
                CurrentAnnualOCFLessPPEAcquisitionCashPaymentsReason.
                COMMON_SUPPORTING_FILING_METADATA_CONFLICT,
            )
        else:
            status = CurrentAnnualOCFLessPPEAcquisitionCashPaymentsStatus.AVAILABLE
            reasons = ()
            operating_cash_flow = ocf_qualification.operating_cash_flow
            ppe_cash_payments = (
                ppe_qualification.ppe_acquisition_cash_payments
            )
            difference = _exact_subtract(
                operating_cash_flow, ppe_cash_payments
            )
    else:
        failures = tuple(
            item
            for item in (
                None if ocf_established else _project_upstream_failure(
                    ocf_qualification, ocf_upstream, is_ocf=True
                ),
                None if ppe_established else _project_upstream_failure(
                    ppe_qualification, ppe_upstream, is_ocf=False
                ),
            )
            if item is not None
        )
        if not failures:
            raise CurrentAnnualOCFLessPPEAcquisitionCashPaymentsError(
                "Unknown upstream qualification state"
            )
        precedence = {
            CurrentAnnualOCFLessPPEAcquisitionCashPaymentsStatus.UNAVAILABLE: 0,
            CurrentAnnualOCFLessPPEAcquisitionCashPaymentsStatus.UNSUPPORTED: 1,
            CurrentAnnualOCFLessPPEAcquisitionCashPaymentsStatus.SOURCE_CONFLICT: 2,
        }
        status = max((item[0] for item in failures), key=precedence.__getitem__)
        reasons = tuple(sorted(
            {item[1] for item in failures}, key=lambda item: item.value
        ))

    ocf_semantic_id, ocf_evidence_id = _upstream_identities(
        ocf_qualification, "OCF"
    )
    ppe_semantic_id, ppe_evidence_id = _upstream_identities(
        ppe_qualification, "PP&E"
    )
    result = CurrentAnnualOCFLessPPEAcquisitionCashPaymentsResult(
        CONTRACT_VERSION,
        METHODOLOGY_VERSION,
        _ANALYSIS_KIND,
        status,
        reasons,
        ocf_qualification.status,
        ocf_qualification.reasons,
        ppe_qualification.status,
        ppe_qualification.reasons,
        source_cik,
        period_start,
        period_end,
        ocf_upstream.NAMESPACE,
        ocf_upstream.ACCOUNTING_BASIS,
        ocf_upstream.REVIEWED_UNIT,
        ocf_upstream.OPERATING_CASH_FLOW_CONCEPT,
        ppe_upstream.PPE_ACQUISITION_CASH_PAYMENTS_CONCEPT,
        operating_cash_flow,
        ppe_cash_payments,
        difference,
        ocf_semantic_id,
        ocf_evidence_id,
        ppe_semantic_id,
        ppe_evidence_id,
        common_accessions,
        _AUTHORITY,
        _LIMITATIONS,
    )
    fingerprint = _identity(
        "current-annual-ocf-less-ppe-cash-payments-upstream-evidence",
        {
            "ocf_qualification_semantic_id": ocf_semantic_id,
            "ocf_qualification_evidence_id": ocf_evidence_id,
            "ppe_qualification_semantic_id": ppe_semantic_id,
            "ppe_qualification_evidence_id": ppe_evidence_id,
            "ocf_qualification": ocf_qualification,
            "ppe_qualification": ppe_qualification,
            "common_supporting_accessions": common_accessions,
        },
    )
    object.__setattr__(result, "_evidence_fingerprint", fingerprint)
    return result
