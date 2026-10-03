"""Source-neutral CURRENT cash-like carry qualification.

This module starts after acquisition and authentication.  It accepts one typed,
capture-bound receipt and qualifies only current nominal carry for the reviewed
settled-cash-balance profile.  It performs no acquisition, forecasting,
comparison, recommendation, allocation, or execution work.
"""
from __future__ import annotations

from dataclasses import dataclass, fields, is_dataclass
from datetime import date, datetime, timezone
from decimal import Decimal
from enum import Enum, StrEnum
import hashlib
import json
import re

from .source_authority import AvailabilitySemantics, PublicationSemantics, UseStatus


CASH_LIKE_CURRENT_CARRY_CONTRACT_VERSION = (
    "2026-10-01-cash-like-current-carry-v1"
)
CASH_LIKE_CURRENT_CARRY_RECEIPT_VERSION = (
    "2026-10-01-cash-like-current-carry-receipt-v1"
)
CASH_LIKE_CURRENT_CARRY_QUALIFICATION_VERSION = (
    "2026-10-01-cash-like-current-carry-qualification-v1"
)
_HASH = re.compile(r"[0-9a-f]{64}")
_CURRENCY = re.compile(r"[A-Z]{3}")


class CashLikeCurrentCarryError(ValueError):
    """Malformed programming contract; evidence absence uses closed status."""


class CashLikeCurrentCarryStatus(StrEnum):
    AVAILABLE = "AVAILABLE"
    UNAVAILABLE = "UNAVAILABLE"
    UNSUPPORTED = "UNSUPPORTED"
    SOURCE_CONFLICT = "SOURCE_CONFLICT"


class CashLikeCurrentCarryReason(StrEnum):
    REQUIRED_RECEIPT_MISSING = "REQUIRED_RECEIPT_MISSING"
    CURRENT_FRESHNESS_NOT_ESTABLISHED = "CURRENT_FRESHNESS_NOT_ESTABLISHED"
    RATE_UNAVAILABLE = "RATE_UNAVAILABLE"
    EXACT_CURRENCY_UNAVAILABLE = "EXACT_CURRENCY_UNAVAILABLE"
    ACCOUNT_BALANCE_FORM_UNAVAILABLE = "ACCOUNT_BALANCE_FORM_UNAVAILABLE"
    ACCOUNT_BALANCE_FORM_UNSUPPORTED = "ACCOUNT_BALANCE_FORM_UNSUPPORTED"
    SETTLED_AVAILABLE_STATE_NOT_ESTABLISHED = (
        "SETTLED_AVAILABLE_STATE_NOT_ESTABLISHED"
    )
    RATE_SEMANTICS_UNAVAILABLE = "RATE_SEMANTICS_UNAVAILABLE"
    RATE_SEMANTICS_UNSUPPORTED = "RATE_SEMANTICS_UNSUPPORTED"
    ACCRUAL_SEMANTICS_UNAVAILABLE = "ACCRUAL_SEMANTICS_UNAVAILABLE"
    ACCRUAL_SEMANTICS_UNSUPPORTED = "ACCRUAL_SEMANTICS_UNSUPPORTED"
    PAYMENT_SEMANTICS_UNAVAILABLE = "PAYMENT_SEMANTICS_UNAVAILABLE"
    PAYMENT_SEMANTICS_UNSUPPORTED = "PAYMENT_SEMANTICS_UNSUPPORTED"
    COMPOUNDING_OR_DAY_COUNT_UNAVAILABLE = (
        "COMPOUNDING_OR_DAY_COUNT_UNAVAILABLE"
    )
    COMPOUNDING_OR_DAY_COUNT_UNSUPPORTED = (
        "COMPOUNDING_OR_DAY_COUNT_UNSUPPORTED"
    )
    EFFECTIVE_AS_OF_SEMANTICS_UNAVAILABLE = (
        "EFFECTIVE_AS_OF_SEMANTICS_UNAVAILABLE"
    )
    EFFECTIVE_AS_OF_SEMANTICS_UNSUPPORTED = (
        "EFFECTIVE_AS_OF_SEMANTICS_UNSUPPORTED"
    )
    TERM_PROFILE_UNAVAILABLE = "TERM_PROFILE_UNAVAILABLE"
    TERM_PROFILE_UNSUPPORTED = "TERM_PROFILE_UNSUPPORTED"
    RECURRING_EXPENSE_TREATMENT_UNAVAILABLE = (
        "RECURRING_EXPENSE_TREATMENT_UNAVAILABLE"
    )
    SOURCE_SEMANTICS_UNSUPPORTED = "SOURCE_SEMANTICS_UNSUPPORTED"
    CHRONOLOGY_CONFLICT = "CHRONOLOGY_CONFLICT"


class CashLikeBalanceForm(StrEnum):
    SETTLED_CASH_BALANCE = "SETTLED_CASH_BALANCE"
    CASH_LIKE_INSTRUMENT = "CASH_LIKE_INSTRUMENT"
    OTHER = "OTHER"


class CashLikeSettlementState(StrEnum):
    SETTLED_AND_AVAILABLE = "SETTLED_AND_AVAILABLE"
    UNSETTLED = "UNSETTLED"
    AVAILABILITY_NOT_ESTABLISHED = "AVAILABILITY_NOT_ESTABLISHED"


class CashLikeCurrentFreshness(StrEnum):
    CURRENT_SAME_RUN_CAPTURE = "CURRENT_SAME_RUN_CAPTURE"
    STALE = "STALE"
    NOT_ESTABLISHED = "NOT_ESTABLISHED"


class CashLikeRateType(StrEnum):
    NOMINAL_ANNUAL_RATE = "NOMINAL_ANNUAL_RATE"
    OTHER = "OTHER"


class CashLikeRateUnit(StrEnum):
    PERCENTAGE_POINTS_PER_YEAR = "PERCENTAGE_POINTS_PER_YEAR"
    OTHER = "OTHER"


class CashLikeAccrualSemantics(StrEnum):
    DAILY_ON_END_OF_DAY_SETTLED_BALANCE = (
        "DAILY_ON_END_OF_DAY_SETTLED_BALANCE"
    )
    OTHER = "OTHER"


class CashLikePaymentSemantics(StrEnum):
    PAID_MONTHLY = "PAID_MONTHLY"
    OTHER = "OTHER"


class CashLikeCompoundingSemantics(StrEnum):
    UNSPECIFIED_BY_SOURCE = "UNSPECIFIED_BY_SOURCE"
    NO_COMPOUNDING_STATED = "NO_COMPOUNDING_STATED"
    DAILY = "DAILY"
    MONTHLY = "MONTHLY"
    OTHER = "OTHER"


class CashLikeDayCountSemantics(StrEnum):
    UNSPECIFIED_BY_SOURCE = "UNSPECIFIED_BY_SOURCE"
    ACTUAL_365 = "ACTUAL_365"
    ACTUAL_360 = "ACTUAL_360"
    OTHER = "OTHER"


class CashLikeEffectiveSemantics(StrEnum):
    RATE_EFFECTIVE_FROM_DATE = "RATE_EFFECTIVE_FROM_DATE"
    CURRENT_AS_OF_DATE = "CURRENT_AS_OF_DATE"
    OTHER = "OTHER"


class CashLikeTermSemantics(StrEnum):
    NO_FIXED_TERM = "NO_FIXED_TERM"
    FIXED_MATURITY = "FIXED_MATURITY"
    UNSPECIFIED_BY_SOURCE = "UNSPECIFIED_BY_SOURCE"


class CashLikeRecurringExpenseTreatment(StrEnum):
    NO_RECURRING_INSTRUMENT_EXPENSE = "NO_RECURRING_INSTRUMENT_EXPENSE"
    ALREADY_REFLECTED_IN_STATED_RATE = "ALREADY_REFLECTED_IN_STATED_RATE"
    NOT_REFLECTED_IN_STATED_RATE = "NOT_REFLECTED_IN_STATED_RATE"
    UNSPECIFIED_BY_SOURCE = "UNSPECIFIED_BY_SOURCE"


class CashLikeCurrentCarryAuthorityScope(StrEnum):
    NONE = "NONE"
    CURRENT_CAPTURE_BOUND_ONLY = "CURRENT_CAPTURE_BOUND_ONLY"


class CashLikeCurrentCarryLimitation(StrEnum):
    CURRENT_CAPTURE_BOUND_ONLY = "CURRENT_CAPTURE_BOUND_ONLY"
    NO_PIT_AUTHORITY = "NO_PIT_AUTHORITY"
    NO_HISTORICAL_AS_OF_AUTHORITY = "NO_HISTORICAL_AS_OF_AUTHORITY"
    NO_FIRST_PUBLICATION_AUTHORITY = "NO_FIRST_PUBLICATION_AUTHORITY"
    NO_SEVEN_YEAR_CASH_EXPECTED_RETURN = "NO_SEVEN_YEAR_CASH_EXPECTED_RETURN"
    NO_COMPANY_OR_VFV_VS_CASH_COMPARISON = (
        "NO_COMPANY_OR_VFV_VS_CASH_COMPARISON"
    )
    NO_HOLDER_TAX_MODELING = "NO_HOLDER_TAX_MODELING"
    NO_RESERVE_ACTIVATION_OR_RELEASE_POLICY = (
        "NO_RESERVE_ACTIVATION_OR_RELEASE_POLICY"
    )
    NO_RECOMMENDATION_OR_ALLOCATION_AUTHORITY = (
        "NO_RECOMMENDATION_OR_ALLOCATION_AUTHORITY"
    )
    NO_EXECUTION_OR_PRODUCTION_AUTHORITY = (
        "NO_EXECUTION_OR_PRODUCTION_AUTHORITY"
    )
    NO_GENERIC_CASH_ETF_OR_TBILL_AUTHORITY = (
        "NO_GENERIC_CASH_ETF_OR_TBILL_AUTHORITY"
    )
    PUBLIC_OBSERVABILITY_DOES_NOT_ESTABLISH_AUTOMATED_OR_COMMERCIAL_INGESTION = (
        "PUBLIC_OBSERVABILITY_DOES_NOT_ESTABLISH_AUTOMATED_OR_COMMERCIAL_INGESTION"
    )


_LIMITATIONS = tuple(CashLikeCurrentCarryLimitation)


def _require_text(value: object, label: str) -> None:
    if type(value) is not str or not value or value != value.strip():
        raise CashLikeCurrentCarryError(
            f"{label}: nonempty trimmed string required")


def _parse_date(value: object, label: str) -> date:
    _require_text(value, label)
    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise CashLikeCurrentCarryError(f"{label}: ISO date required") from exc
    if parsed.isoformat() != value:
        raise CashLikeCurrentCarryError(
            f"{label}: canonical ISO date required")
    return parsed


@dataclass(frozen=True, slots=True)
class _ParsedTimestamp:
    instant_utc: datetime
    represented_calendar_date: date


def _parse_timestamp(value: object, label: str) -> _ParsedTimestamp:
    _require_text(value, label)
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise CashLikeCurrentCarryError(
            f"{label}: offset-aware ISO timestamp required") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise CashLikeCurrentCarryError(
            f"{label}: offset-aware ISO timestamp required")
    return _ParsedTimestamp(
        instant_utc=parsed.astimezone(timezone.utc),
        represented_calendar_date=parsed.date(),
    )


def _require_optional_enum(value: object, enum_type: type[Enum], label: str) -> None:
    if value is not None and type(value) is not enum_type:
        raise CashLikeCurrentCarryError(f"{label}: closed typed value required")


@dataclass(frozen=True, slots=True)
class CashLikeCurrentCarryClaim:
    balance_form: CashLikeBalanceForm | None
    settlement_state: CashLikeSettlementState
    native_accrual_currency: str | None
    rate: Decimal | None
    rate_type: CashLikeRateType | None
    rate_unit: CashLikeRateUnit | None
    accrual_semantics: CashLikeAccrualSemantics | None
    payment_semantics: CashLikePaymentSemantics | None
    compounding_semantics: CashLikeCompoundingSemantics | None
    day_count_semantics: CashLikeDayCountSemantics | None
    effective_date: str | None
    effective_semantics: CashLikeEffectiveSemantics | None
    term_semantics: CashLikeTermSemantics | None
    maturity_date: str | None
    recurring_expense_treatment: CashLikeRecurringExpenseTreatment | None

    def __post_init__(self):
        _require_optional_enum(self.balance_form, CashLikeBalanceForm,
                               "balance_form")
        if type(self.settlement_state) is not CashLikeSettlementState:
            raise CashLikeCurrentCarryError(
                "settlement_state: closed typed value required")
        if self.native_accrual_currency is not None:
            if (type(self.native_accrual_currency) is not str
                    or _CURRENCY.fullmatch(self.native_accrual_currency) is None):
                raise CashLikeCurrentCarryError(
                    "native_accrual_currency: exact three-letter uppercase code required")
        if self.rate is not None and (
                type(self.rate) is not Decimal or not self.rate.is_finite()):
            raise CashLikeCurrentCarryError(
                "rate: finite exact Decimal or None required")
        for name, enum_type in (
                ("rate_type", CashLikeRateType),
                ("rate_unit", CashLikeRateUnit),
                ("accrual_semantics", CashLikeAccrualSemantics),
                ("payment_semantics", CashLikePaymentSemantics),
                ("compounding_semantics", CashLikeCompoundingSemantics),
                ("day_count_semantics", CashLikeDayCountSemantics),
                ("effective_semantics", CashLikeEffectiveSemantics),
                ("term_semantics", CashLikeTermSemantics),
                ("recurring_expense_treatment",
                 CashLikeRecurringExpenseTreatment)):
            _require_optional_enum(getattr(self, name), enum_type, name)
        if self.effective_date is not None:
            _parse_date(self.effective_date, "effective_date")
        if self.maturity_date is not None:
            _parse_date(self.maturity_date, "maturity_date")


@dataclass(frozen=True, slots=True)
class CashLikeCurrentCarryReceipt:
    schema_version: str
    qualification_input_contract_version: str
    source_owner: str
    source_descriptor: str
    source_locator: str
    receipt_id: str
    content_or_account_state_sha256: str
    capture_sha256: str
    retrieved_at: str
    publication_timestamp: str | None
    publication_semantics: PublicationSemantics
    availability_semantics: AvailabilitySemantics
    license_status: UseStatus
    use_status: UseStatus
    freshness: CashLikeCurrentFreshness
    claim: CashLikeCurrentCarryClaim

    def __post_init__(self):
        if self.schema_version != CASH_LIKE_CURRENT_CARRY_RECEIPT_VERSION:
            raise CashLikeCurrentCarryError("Unsupported receipt schema version")
        if (self.qualification_input_contract_version
                != CASH_LIKE_CURRENT_CARRY_QUALIFICATION_VERSION):
            raise CashLikeCurrentCarryError(
                "Qualification input contract version mismatch")
        for name in ("source_owner", "source_descriptor", "source_locator"):
            _require_text(getattr(self, name), name)
        for name in (
                "receipt_id", "content_or_account_state_sha256", "capture_sha256"):
            value = getattr(self, name)
            if type(value) is not str or _HASH.fullmatch(value) is None:
                raise CashLikeCurrentCarryError(
                    f"{name}: exact lowercase SHA-256 identity required")
        _parse_timestamp(self.retrieved_at, "retrieved_at")
        if self.publication_timestamp is not None:
            _parse_timestamp(self.publication_timestamp,
                             "publication_timestamp")
        if type(self.publication_semantics) is not PublicationSemantics:
            raise CashLikeCurrentCarryError(
                "Typed publication semantics required")
        if type(self.availability_semantics) is not AvailabilitySemantics:
            raise CashLikeCurrentCarryError(
                "Typed availability semantics required")
        if type(self.license_status) is not UseStatus:
            raise CashLikeCurrentCarryError("Typed license status required")
        if type(self.use_status) is not UseStatus:
            raise CashLikeCurrentCarryError("Typed use status required")
        if type(self.freshness) is not CashLikeCurrentFreshness:
            raise CashLikeCurrentCarryError("Typed current freshness required")
        if type(self.claim) is not CashLikeCurrentCarryClaim:
            raise CashLikeCurrentCarryError("Typed carry claim required")


@dataclass(frozen=True, slots=True)
class CashLikeCurrentCarryFact:
    balance_form: CashLikeBalanceForm
    native_accrual_currency: str
    rate: Decimal
    rate_type: CashLikeRateType
    rate_unit: CashLikeRateUnit
    accrual_semantics: CashLikeAccrualSemantics
    payment_semantics: CashLikePaymentSemantics
    compounding_semantics: CashLikeCompoundingSemantics
    day_count_semantics: CashLikeDayCountSemantics
    effective_date: str
    effective_semantics: CashLikeEffectiveSemantics
    term_semantics: CashLikeTermSemantics
    maturity_date: str | None
    recurring_expense_treatment: CashLikeRecurringExpenseTreatment


@dataclass(frozen=True, slots=True)
class CashLikeCurrentCarryEvidence:
    receipt_schema_version: str
    qualification_input_contract_version: str
    receipt_id: str
    source_owner: str
    source_descriptor: str
    source_locator: str
    content_or_account_state_sha256: str
    capture_sha256: str
    retrieved_at: str
    publication_timestamp: str | None
    publication_semantics: PublicationSemantics
    availability_timestamp: str
    availability_semantics: AvailabilitySemantics
    license_status: UseStatus
    use_status: UseStatus
    freshness: CashLikeCurrentFreshness
    receipt_claim_id: str


def _canonical(value):
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value):
        return {field.name: _canonical(getattr(value, field.name))
                for field in fields(value)}
    if type(value) is Decimal:
        if not value.is_finite():
            raise CashLikeCurrentCarryError("Nonfinite Decimal")
        sign, digits, exponent = value.as_tuple()
        digits = list(digits)
        while len(digits) > 1 and digits[-1] == 0:
            digits.pop()
            exponent += 1
        if not any(digits):
            sign, digits, exponent = 0, [0], 0
        return {"decimal_tuple": [sign, digits, exponent]}
    if type(value) in (tuple, list):
        return [_canonical(item) for item in value]
    if type(value) is dict:
        return {key: _canonical(value[key]) for key in sorted(value)}
    if value is None or type(value) in (str, int, bool):
        return value
    raise CashLikeCurrentCarryError("Unsupported deterministic identity value")


def _identity(domain: str, value) -> str:
    payload = json.dumps(
        _canonical(value), sort_keys=True, separators=(",", ":"),
        ensure_ascii=True, allow_nan=False,
    )
    return hashlib.sha256((domain + "\0" + payload).encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class CashLikeCurrentCarryQualification:
    contract_version: str
    qualification_version: str
    status: CashLikeCurrentCarryStatus
    reasons: tuple[CashLikeCurrentCarryReason, ...]
    fact: CashLikeCurrentCarryFact | None
    evidence: CashLikeCurrentCarryEvidence | None
    authority_scope: CashLikeCurrentCarryAuthorityScope
    limitations: tuple[CashLikeCurrentCarryLimitation, ...]

    @property
    def semantic_id(self) -> str:
        return _identity("cash-like-current-carry-semantics", {
            "contract_version": self.contract_version,
            "qualification_version": self.qualification_version,
            "status": self.status,
            "reasons": self.reasons,
            "fact": self.fact,
            "authority_scope": self.authority_scope,
            "limitations": self.limitations,
        })

    @property
    def evidence_id(self) -> str:
        return _identity("cash-like-current-carry-evidence", {
            "semantic_id": self.semantic_id,
            "evidence": self.evidence,
        })

    def to_dict(self) -> dict:
        payload = _canonical(self)
        payload["semantic_id"] = self.semantic_id
        payload["evidence_id"] = self.evidence_id
        return {"cash_like_current_carry": payload}


def _evidence(receipt: CashLikeCurrentCarryReceipt):
    return CashLikeCurrentCarryEvidence(
        receipt.schema_version,
        receipt.qualification_input_contract_version,
        receipt.receipt_id,
        receipt.source_owner,
        receipt.source_descriptor,
        receipt.source_locator,
        receipt.content_or_account_state_sha256,
        receipt.capture_sha256,
        receipt.retrieved_at,
        receipt.publication_timestamp,
        receipt.publication_semantics,
        receipt.retrieved_at,
        receipt.availability_semantics,
        receipt.license_status,
        receipt.use_status,
        receipt.freshness,
        _identity("cash-like-current-carry-receipt-claim", receipt.claim),
    )


def _result(
    receipt: CashLikeCurrentCarryReceipt | None,
    *,
    status: CashLikeCurrentCarryStatus,
    reasons: set[CashLikeCurrentCarryReason] | tuple[CashLikeCurrentCarryReason, ...],
    fact: CashLikeCurrentCarryFact | None = None,
) -> CashLikeCurrentCarryQualification:
    return CashLikeCurrentCarryQualification(
        CASH_LIKE_CURRENT_CARRY_CONTRACT_VERSION,
        CASH_LIKE_CURRENT_CARRY_QUALIFICATION_VERSION,
        status,
        tuple(sorted(set(reasons), key=lambda item: item.value)),
        fact,
        _evidence(receipt) if receipt is not None else None,
        (CashLikeCurrentCarryAuthorityScope.CURRENT_CAPTURE_BOUND_ONLY
         if status is CashLikeCurrentCarryStatus.AVAILABLE
         else CashLikeCurrentCarryAuthorityScope.NONE),
        _LIMITATIONS,
    )


def qualify_cash_like_current_carry(
    receipt: CashLikeCurrentCarryReceipt | None,
) -> CashLikeCurrentCarryQualification:
    """Purely qualify one current capture; missing economics fail closed."""
    if receipt is None:
        return _result(
            None,
            status=CashLikeCurrentCarryStatus.UNAVAILABLE,
            reasons=(CashLikeCurrentCarryReason.REQUIRED_RECEIPT_MISSING,),
        )
    if type(receipt) is not CashLikeCurrentCarryReceipt:
        raise CashLikeCurrentCarryError(
            "Typed CashLikeCurrentCarryReceipt or None required")

    claim = receipt.claim
    conflicts: set[CashLikeCurrentCarryReason] = set()
    unsupported: set[CashLikeCurrentCarryReason] = set()
    unavailable: set[CashLikeCurrentCarryReason] = set()

    if claim.balance_form is None:
        unavailable.add(
            CashLikeCurrentCarryReason.ACCOUNT_BALANCE_FORM_UNAVAILABLE)
    elif claim.balance_form is not CashLikeBalanceForm.SETTLED_CASH_BALANCE:
        unsupported.add(
            CashLikeCurrentCarryReason.ACCOUNT_BALANCE_FORM_UNSUPPORTED)
    if claim.settlement_state is not CashLikeSettlementState.SETTLED_AND_AVAILABLE:
        unavailable.add(
            CashLikeCurrentCarryReason.SETTLED_AVAILABLE_STATE_NOT_ESTABLISHED)
    if receipt.freshness is not CashLikeCurrentFreshness.CURRENT_SAME_RUN_CAPTURE:
        unavailable.add(
            CashLikeCurrentCarryReason.CURRENT_FRESHNESS_NOT_ESTABLISHED)
    if claim.native_accrual_currency is None:
        unavailable.add(CashLikeCurrentCarryReason.EXACT_CURRENCY_UNAVAILABLE)
    if claim.rate is None:
        unavailable.add(CashLikeCurrentCarryReason.RATE_UNAVAILABLE)

    if claim.rate_type is None or claim.rate_unit is None:
        unavailable.add(CashLikeCurrentCarryReason.RATE_SEMANTICS_UNAVAILABLE)
    elif (claim.rate_type is not CashLikeRateType.NOMINAL_ANNUAL_RATE
          or claim.rate_unit is not CashLikeRateUnit.PERCENTAGE_POINTS_PER_YEAR):
        unsupported.add(CashLikeCurrentCarryReason.RATE_SEMANTICS_UNSUPPORTED)
    if claim.accrual_semantics is None:
        unavailable.add(CashLikeCurrentCarryReason.ACCRUAL_SEMANTICS_UNAVAILABLE)
    elif claim.accrual_semantics is not (
            CashLikeAccrualSemantics.DAILY_ON_END_OF_DAY_SETTLED_BALANCE):
        unsupported.add(CashLikeCurrentCarryReason.ACCRUAL_SEMANTICS_UNSUPPORTED)
    if claim.payment_semantics is None:
        unavailable.add(CashLikeCurrentCarryReason.PAYMENT_SEMANTICS_UNAVAILABLE)
    elif claim.payment_semantics is not CashLikePaymentSemantics.PAID_MONTHLY:
        unsupported.add(CashLikeCurrentCarryReason.PAYMENT_SEMANTICS_UNSUPPORTED)
    if (claim.compounding_semantics is None
            or claim.day_count_semantics is None):
        unavailable.add(
            CashLikeCurrentCarryReason.COMPOUNDING_OR_DAY_COUNT_UNAVAILABLE)
    elif (claim.compounding_semantics is CashLikeCompoundingSemantics.OTHER
          or claim.day_count_semantics is CashLikeDayCountSemantics.OTHER):
        unsupported.add(
            CashLikeCurrentCarryReason.COMPOUNDING_OR_DAY_COUNT_UNSUPPORTED)
    if claim.effective_date is None or claim.effective_semantics is None:
        unavailable.add(
            CashLikeCurrentCarryReason.EFFECTIVE_AS_OF_SEMANTICS_UNAVAILABLE)
    elif claim.effective_semantics is CashLikeEffectiveSemantics.OTHER:
        unsupported.add(
            CashLikeCurrentCarryReason.EFFECTIVE_AS_OF_SEMANTICS_UNSUPPORTED)
    if claim.term_semantics is None:
        unavailable.add(CashLikeCurrentCarryReason.TERM_PROFILE_UNAVAILABLE)
    elif (claim.term_semantics is not CashLikeTermSemantics.NO_FIXED_TERM
          or claim.maturity_date is not None):
        unsupported.add(CashLikeCurrentCarryReason.TERM_PROFILE_UNSUPPORTED)
    if claim.recurring_expense_treatment is None:
        unavailable.add(
            CashLikeCurrentCarryReason.RECURRING_EXPENSE_TREATMENT_UNAVAILABLE)
    if (receipt.publication_semantics is not PublicationSemantics.UNKNOWN
            or receipt.availability_semantics is not
            AvailabilitySemantics.CAPTURE_BOUND):
        unsupported.add(CashLikeCurrentCarryReason.SOURCE_SEMANTICS_UNSUPPORTED)

    retrieved = _parse_timestamp(receipt.retrieved_at, "retrieved_at")
    if (claim.effective_date is not None
            and _parse_date(claim.effective_date, "effective_date")
            > retrieved.represented_calendar_date):
        conflicts.add(CashLikeCurrentCarryReason.CHRONOLOGY_CONFLICT)
    if (receipt.publication_timestamp is not None
            and _parse_timestamp(receipt.publication_timestamp,
                                 "publication_timestamp").instant_utc
            > retrieved.instant_utc):
        conflicts.add(CashLikeCurrentCarryReason.CHRONOLOGY_CONFLICT)
    if (claim.maturity_date is not None and claim.effective_date is not None
            and _parse_date(claim.maturity_date, "maturity_date")
            < _parse_date(claim.effective_date, "effective_date")):
        conflicts.add(CashLikeCurrentCarryReason.CHRONOLOGY_CONFLICT)

    if conflicts:
        return _result(
            receipt, status=CashLikeCurrentCarryStatus.SOURCE_CONFLICT,
            reasons=conflicts)
    if unsupported:
        return _result(
            receipt, status=CashLikeCurrentCarryStatus.UNSUPPORTED,
            reasons=unsupported)
    if unavailable:
        return _result(
            receipt, status=CashLikeCurrentCarryStatus.UNAVAILABLE,
            reasons=unavailable)

    fact = CashLikeCurrentCarryFact(
        claim.balance_form,
        claim.native_accrual_currency,
        claim.rate,
        claim.rate_type,
        claim.rate_unit,
        claim.accrual_semantics,
        claim.payment_semantics,
        claim.compounding_semantics,
        claim.day_count_semantics,
        claim.effective_date,
        claim.effective_semantics,
        claim.term_semantics,
        claim.maturity_date,
        claim.recurring_expense_treatment,
    )
    return _result(
        receipt,
        status=CashLikeCurrentCarryStatus.AVAILABLE,
        reasons=(),
        fact=fact,
    )
