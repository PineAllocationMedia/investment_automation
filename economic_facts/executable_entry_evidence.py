"""Source-neutral CURRENT evidence for one potentially executable purchase entry.

This pure qualifier starts after acquisition and authentication.  It preserves
independent route facts, fails the overall route closed, and deliberately performs
no order construction, pricing transformation, or Expected Return calculation.
"""
from __future__ import annotations

from dataclasses import dataclass, fields, is_dataclass
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum, StrEnum
import hashlib
import json
import re

from .source_authority import AvailabilitySemantics, PublicationSemantics, UseStatus


EXECUTABLE_ENTRY_EVIDENCE_CONTRACT_VERSION = (
    "2026-10-03-executable-entry-evidence-v1"
)
EXECUTABLE_ENTRY_EVIDENCE_SCHEMA_VERSION = (
    "2026-10-03-executable-entry-evidence-schema-v1"
)
EXECUTABLE_ENTRY_EVIDENCE_QUALIFICATION_VERSION = (
    "2026-10-03-executable-entry-evidence-qualification-v1"
)

_HASH = re.compile(r"[0-9a-f]{64}")
_CURRENCY = re.compile(r"[A-Z]{3}")
_EXECUTION_CONTEXT_ID = re.compile(r"execctx:[0-9a-f]{64}")
_TARGET_INSTRUMENT_ID = re.compile(r"instrument:[0-9a-f]{64}")


class ExecutableEntryEvidenceError(ValueError):
    """Malformed programming contract; evidence absence uses closed status."""


class ExecutableEntryStatus(StrEnum):
    AVAILABLE = "AVAILABLE"
    UNAVAILABLE = "UNAVAILABLE"
    UNSUPPORTED = "UNSUPPORTED"
    SOURCE_CONFLICT = "SOURCE_CONFLICT"


class ExecutableEntryReason(StrEnum):
    REQUIRED_EVIDENCE_MISSING = "REQUIRED_EVIDENCE_MISSING"
    ACCOUNT_INSTRUMENT_ELIGIBILITY_NOT_ESTABLISHED = (
        "ACCOUNT_INSTRUMENT_ELIGIBILITY_NOT_ESTABLISHED"
    )
    INSTRUMENT_NOT_ELIGIBLE = "INSTRUMENT_NOT_ELIGIBLE"
    INSTRUMENT_ROUTE_UNSUPPORTED = "INSTRUMENT_ROUTE_UNSUPPORTED"
    SETTLED_AVAILABLE_FUNDING_NOT_ESTABLISHED = (
        "SETTLED_AVAILABLE_FUNDING_NOT_ESTABLISHED"
    )
    EXACT_FUNDING_CURRENCY_UNAVAILABLE = "EXACT_FUNDING_CURRENCY_UNAVAILABLE"
    EXACT_TRANSACTION_CURRENCY_UNAVAILABLE = (
        "EXACT_TRANSACTION_CURRENCY_UNAVAILABLE"
    )
    COMMISSION_UNAVAILABLE = "COMMISSION_UNAVAILABLE"
    COMMISSION_SEMANTICS_UNSUPPORTED = "COMMISSION_SEMANTICS_UNSUPPORTED"
    COMMISSION_CURRENCY_CONFLICT = "COMMISSION_CURRENCY_CONFLICT"
    COMMISSION_AMOUNT_CONFLICT = "COMMISSION_AMOUNT_CONFLICT"
    SETTLEMENT_SEMANTICS_UNAVAILABLE = "SETTLEMENT_SEMANTICS_UNAVAILABLE"
    SETTLEMENT_SEMANTICS_UNSUPPORTED = "SETTLEMENT_SEMANTICS_UNSUPPORTED"
    SETTLEMENT_CYCLE_UNSUPPORTED = "SETTLEMENT_CYCLE_UNSUPPORTED"
    FX_EXECUTION_COST_EVIDENCE_UNAVAILABLE = (
        "FX_EXECUTION_COST_EVIDENCE_UNAVAILABLE"
    )
    EXECUTABLE_QUOTE_UNAVAILABLE = "EXECUTABLE_QUOTE_UNAVAILABLE"
    EXECUTABLE_QUOTE_AUTHORITY_INSUFFICIENT = (
        "EXECUTABLE_QUOTE_AUTHORITY_INSUFFICIENT"
    )
    QUOTE_BID_ASK_CONFLICT = "QUOTE_BID_ASK_CONFLICT"
    QUOTE_CURRENCY_CONFLICT = "QUOTE_CURRENCY_CONFLICT"
    QUOTE_CHRONOLOGY_CONFLICT = "QUOTE_CHRONOLOGY_CONFLICT"
    PROVENANCE_CHRONOLOGY_CONFLICT = "PROVENANCE_CHRONOLOGY_CONFLICT"
    SCOPE_IDENTITY_CONFLICT = "SCOPE_IDENTITY_CONFLICT"
    CURRENT_FRESHNESS_NOT_ESTABLISHED = "CURRENT_FRESHNESS_NOT_ESTABLISHED"


class CurrentEvidenceFreshness(StrEnum):
    CURRENT_SAME_RUN_CAPTURE = "CURRENT_SAME_RUN_CAPTURE"
    STALE = "STALE"
    NOT_ESTABLISHED = "NOT_ESTABLISHED"


class EligibilityState(StrEnum):
    ELIGIBLE = "ELIGIBLE"
    NOT_ESTABLISHED = "NOT_ESTABLISHED"
    NOT_ELIGIBLE = "NOT_ELIGIBLE"
    UNSUPPORTED_INSTRUMENT = "UNSUPPORTED_INSTRUMENT"


class FundingAvailabilityState(StrEnum):
    SETTLED_AND_AVAILABLE = "SETTLED_AND_AVAILABLE"
    UNSETTLED = "UNSETTLED"
    AVAILABILITY_NOT_ESTABLISHED = "AVAILABILITY_NOT_ESTABLISHED"


class CommissionSemantics(StrEnum):
    FLAT_PER_ORDER_TRANSACTION_CURRENCY = (
        "FLAT_PER_ORDER_TRANSACTION_CURRENCY"
    )
    OTHER = "OTHER"


class SettlementSemantics(StrEnum):
    POST_TRADE_REGULAR_WAY = "POST_TRADE_REGULAR_WAY"
    OTHER = "OTHER"


class SettlementCycle(StrEnum):
    T_PLUS_1 = "T_PLUS_1"
    OTHER = "OTHER"


class ExecutableQuoteAuthority(StrEnum):
    EXECUTABLE_BID_ASK = "EXECUTABLE_BID_ASK"
    INFORMATIONAL_OR_DISPLAY_ONLY = "INFORMATIONAL_OR_DISPLAY_ONLY"
    INDICATIVE_ONLY = "INDICATIVE_ONLY"
    OTHER = "OTHER"


class CurrencyPathState(StrEnum):
    FX_NOT_REQUIRED_SAME_CURRENCY = "FX_NOT_REQUIRED_SAME_CURRENCY"
    FX_REQUIRED_EXECUTION_COST_UNAVAILABLE = (
        "FX_REQUIRED_EXECUTION_COST_UNAVAILABLE"
    )


class ExecutableEntryAuthorityScope(StrEnum):
    NONE = "NONE"
    CURRENT_CAPTURE_BOUND_EVIDENCE_ONLY = (
        "CURRENT_CAPTURE_BOUND_EVIDENCE_ONLY"
    )


class ExecutableEntryLimitation(StrEnum):
    CURRENT_CAPTURE_BOUND_ONLY = "CURRENT_CAPTURE_BOUND_ONLY"
    NO_PIT_AUTHORITY = "NO_PIT_AUTHORITY"
    NO_HISTORICAL_AS_OF_AUTHORITY = "NO_HISTORICAL_AS_OF_AUTHORITY"
    NO_FIRST_PUBLICATION_AUTHORITY = "NO_FIRST_PUBLICATION_AUTHORITY"
    NO_BROKER_OR_PROVIDER_ACQUISITION_AUTHORITY = (
        "NO_BROKER_OR_PROVIDER_ACQUISITION_AUTHORITY"
    )
    NO_OWNER_SPECIFIC_LIVE_ROUTE = "NO_OWNER_SPECIFIC_LIVE_ROUTE"
    NO_ORDER_CONSTRUCTION = "NO_ORDER_CONSTRUCTION"
    NO_ORDER_SUBMISSION = "NO_ORDER_SUBMISSION"
    NO_EXECUTION_AUTHORITY = "NO_EXECUTION_AUTHORITY"
    NO_RECOMMENDATION = "NO_RECOMMENDATION"
    NO_ALLOCATION = "NO_ALLOCATION"
    NO_PRODUCTION_AUTHORITY = "NO_PRODUCTION_AUTHORITY"
    NO_DEPLOYMENT_AUTHORITY = "NO_DEPLOYMENT_AUTHORITY"
    NO_SEVEN_YEAR_CASH_EXPECTED_RETURN = "NO_SEVEN_YEAR_CASH_EXPECTED_RETURN"
    NO_EXECUTABLE_NET_EXPECTED_RETURN = "NO_EXECUTABLE_NET_EXPECTED_RETURN"
    NO_COMPANY_OR_VFV_VS_CASH_COMPARISON = (
        "NO_COMPANY_OR_VFV_VS_CASH_COMPARISON"
    )
    NO_AGGREGATE_ENTRY_FRICTION_CALCULATION = (
        "NO_AGGREGATE_ENTRY_FRICTION_CALCULATION"
    )
    NO_MARKET_IMPACT_OR_SLIPPAGE_MODEL = (
        "NO_MARKET_IMPACT_OR_SLIPPAGE_MODEL"
    )
    NO_QUANTITY_NOTIONAL_OR_ORDER_SIZE_AUTHORITY = (
        "NO_QUANTITY_NOTIONAL_OR_ORDER_SIZE_AUTHORITY"
    )
    NO_FRACTIONAL_OR_ODD_LOT_CAPABILITY_CLAIM = (
        "NO_FRACTIONAL_OR_ODD_LOT_CAPABILITY_CLAIM"
    )
    PUBLIC_DISPLAYED_QUOTE_NOT_EXECUTABLE_AUTHORITY = (
        "PUBLIC_DISPLAYED_QUOTE_NOT_EXECUTABLE_AUTHORITY"
    )
    PUBLIC_OBSERVABILITY_NOT_AUTOMATED_OR_COMMERCIAL_PERMISSION = (
        "PUBLIC_OBSERVABILITY_NOT_AUTOMATED_OR_COMMERCIAL_PERMISSION"
    )


_LIMITATIONS = tuple(ExecutableEntryLimitation)


def _require_text(value: object, label: str) -> None:
    if type(value) is not str or not value or value != value.strip():
        raise ExecutableEntryEvidenceError(
            f"{label}: nonempty trimmed string required"
        )


@dataclass(frozen=True, slots=True)
class _ParsedTimestamp:
    instant_utc: datetime


def _parse_timestamp(value: object, label: str) -> _ParsedTimestamp:
    _require_text(value, label)
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ExecutableEntryEvidenceError(
            f"{label}: offset-aware ISO timestamp required"
        ) from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ExecutableEntryEvidenceError(
            f"{label}: offset-aware ISO timestamp required"
        )
    return _ParsedTimestamp(parsed.astimezone(timezone.utc))


def _require_scope(
    execution_context_id: object, target_instrument_id: object
) -> None:
    if (
        type(execution_context_id) is not str
        or _EXECUTION_CONTEXT_ID.fullmatch(execution_context_id) is None
    ):
        raise ExecutableEntryEvidenceError(
            "execution_context_id: opaque execctx SHA-256 identity required"
        )
    if (
        type(target_instrument_id) is not str
        or _TARGET_INSTRUMENT_ID.fullmatch(target_instrument_id) is None
    ):
        raise ExecutableEntryEvidenceError(
            "target_instrument_id: opaque instrument SHA-256 identity required"
        )


def _require_currency(value: object, label: str) -> None:
    if value is not None and (
        type(value) is not str or _CURRENCY.fullmatch(value) is None
    ):
        raise ExecutableEntryEvidenceError(
            f"{label}: exact three-letter uppercase code or None required"
        )


def _require_optional_enum(value: object, enum_type: type[Enum], label: str) -> None:
    if value is not None and type(value) is not enum_type:
        raise ExecutableEntryEvidenceError(f"{label}: closed typed value required")


@dataclass(frozen=True, slots=True)
class EvidenceProvenance:
    schema_version: str
    source_owner: str
    source_descriptor: str
    source_locator: str
    receipt_id: str
    content_sha256: str
    capture_sha256: str
    retrieved_at: str
    publication_timestamp: str | None
    publication_semantics: PublicationSemantics
    availability_semantics: AvailabilitySemantics
    license_status: UseStatus
    use_status: UseStatus
    freshness: CurrentEvidenceFreshness

    def __post_init__(self):
        if self.schema_version != EXECUTABLE_ENTRY_EVIDENCE_SCHEMA_VERSION:
            raise ExecutableEntryEvidenceError("Unsupported evidence schema version")
        for name in ("source_owner", "source_descriptor", "source_locator"):
            _require_text(getattr(self, name), name)
        for name in ("receipt_id", "content_sha256", "capture_sha256"):
            value = getattr(self, name)
            if type(value) is not str or _HASH.fullmatch(value) is None:
                raise ExecutableEntryEvidenceError(
                    f"{name}: exact lowercase SHA-256 identity required"
                )
        _parse_timestamp(self.retrieved_at, "retrieved_at")
        if self.publication_timestamp is not None:
            _parse_timestamp(self.publication_timestamp, "publication_timestamp")
        if type(self.publication_semantics) is not PublicationSemantics:
            raise ExecutableEntryEvidenceError("Typed publication semantics required")
        if type(self.availability_semantics) is not AvailabilitySemantics:
            raise ExecutableEntryEvidenceError("Typed availability semantics required")
        if type(self.license_status) is not UseStatus:
            raise ExecutableEntryEvidenceError("Typed license status required")
        if type(self.use_status) is not UseStatus:
            raise ExecutableEntryEvidenceError("Typed use status required")
        if type(self.freshness) is not CurrentEvidenceFreshness:
            raise ExecutableEntryEvidenceError("Typed current freshness required")


@dataclass(frozen=True, slots=True)
class EligibilityEvidence:
    execution_context_id: str
    target_instrument_id: str
    state: EligibilityState
    transaction_currency: str | None
    provenance: EvidenceProvenance

    def __post_init__(self):
        _require_scope(self.execution_context_id, self.target_instrument_id)
        if type(self.state) is not EligibilityState:
            raise ExecutableEntryEvidenceError("Typed eligibility state required")
        _require_currency(self.transaction_currency, "transaction_currency")
        if type(self.provenance) is not EvidenceProvenance:
            raise ExecutableEntryEvidenceError("Typed eligibility provenance required")


@dataclass(frozen=True, slots=True)
class FundingEvidence:
    execution_context_id: str
    target_instrument_id: str
    state: FundingAvailabilityState
    funding_currency: str | None
    provenance: EvidenceProvenance

    def __post_init__(self):
        _require_scope(self.execution_context_id, self.target_instrument_id)
        if type(self.state) is not FundingAvailabilityState:
            raise ExecutableEntryEvidenceError("Typed funding state required")
        _require_currency(self.funding_currency, "funding_currency")
        if type(self.provenance) is not EvidenceProvenance:
            raise ExecutableEntryEvidenceError("Typed funding provenance required")


@dataclass(frozen=True, slots=True)
class CommissionEvidence:
    execution_context_id: str
    target_instrument_id: str
    amount: Decimal | None
    currency: str | None
    semantics: CommissionSemantics | None
    provenance: EvidenceProvenance

    def __post_init__(self):
        _require_scope(self.execution_context_id, self.target_instrument_id)
        if self.amount is not None and (
            type(self.amount) is not Decimal or not self.amount.is_finite()
        ):
            raise ExecutableEntryEvidenceError(
                "commission amount: finite exact Decimal or None required"
            )
        _require_currency(self.currency, "commission currency")
        _require_optional_enum(self.semantics, CommissionSemantics, "commission semantics")
        if type(self.provenance) is not EvidenceProvenance:
            raise ExecutableEntryEvidenceError("Typed commission provenance required")


@dataclass(frozen=True, slots=True)
class SettlementEvidence:
    execution_context_id: str
    target_instrument_id: str
    semantics: SettlementSemantics | None
    cycle: SettlementCycle | None
    provenance: EvidenceProvenance

    def __post_init__(self):
        _require_scope(self.execution_context_id, self.target_instrument_id)
        _require_optional_enum(self.semantics, SettlementSemantics, "settlement semantics")
        _require_optional_enum(self.cycle, SettlementCycle, "settlement cycle")
        if type(self.provenance) is not EvidenceProvenance:
            raise ExecutableEntryEvidenceError("Typed settlement provenance required")


@dataclass(frozen=True, slots=True)
class ExecutableQuoteEvidence:
    execution_context_id: str
    target_instrument_id: str
    bid: Decimal | None
    ask: Decimal | None
    currency: str | None
    market_timestamp: str | None
    authority: ExecutableQuoteAuthority | None
    execution_source_descriptor: str | None
    provenance: EvidenceProvenance

    def __post_init__(self):
        _require_scope(self.execution_context_id, self.target_instrument_id)
        for name in ("bid", "ask"):
            value = getattr(self, name)
            if value is not None and (
                type(value) is not Decimal or not value.is_finite()
            ):
                raise ExecutableEntryEvidenceError(
                    f"{name}: finite exact Decimal or None required"
                )
        _require_currency(self.currency, "quote currency")
        if self.market_timestamp is not None:
            _parse_timestamp(self.market_timestamp, "market_timestamp")
        _require_optional_enum(self.authority, ExecutableQuoteAuthority, "quote authority")
        if self.execution_source_descriptor is not None:
            _require_text(
                self.execution_source_descriptor, "execution_source_descriptor"
            )
        if type(self.provenance) is not EvidenceProvenance:
            raise ExecutableEntryEvidenceError("Typed quote provenance required")


@dataclass(frozen=True, slots=True)
class ExecutableEntryEvidenceRequest:
    execution_context_id: str
    target_instrument_id: str
    eligibility: EligibilityEvidence | None
    funding: FundingEvidence | None
    commission: CommissionEvidence | None
    settlement: SettlementEvidence | None
    executable_quote: ExecutableQuoteEvidence | None

    def __post_init__(self):
        _require_scope(self.execution_context_id, self.target_instrument_id)
        for name, expected_type in (
            ("eligibility", EligibilityEvidence),
            ("funding", FundingEvidence),
            ("commission", CommissionEvidence),
            ("settlement", SettlementEvidence),
            ("executable_quote", ExecutableQuoteEvidence),
        ):
            value = getattr(self, name)
            if value is not None and type(value) is not expected_type:
                raise ExecutableEntryEvidenceError(
                    f"{name}: exact typed evidence or None required"
                )


@dataclass(frozen=True, slots=True)
class EligibilityFact:
    execution_context_id: str
    target_instrument_id: str
    state: EligibilityState


@dataclass(frozen=True, slots=True)
class FundingAvailabilityFact:
    execution_context_id: str
    target_instrument_id: str
    state: FundingAvailabilityState


@dataclass(frozen=True, slots=True)
class CommissionFact:
    amount: Decimal
    currency: str
    semantics: CommissionSemantics


@dataclass(frozen=True, slots=True)
class SettlementFact:
    semantics: SettlementSemantics
    cycle: SettlementCycle


@dataclass(frozen=True, slots=True)
class CurrencyPathFact:
    funding_currency: str
    transaction_currency: str
    state: CurrencyPathState


@dataclass(frozen=True, slots=True)
class ExecutableQuoteFact:
    bid: Decimal
    ask: Decimal
    currency: str
    market_timestamp: str
    authority: ExecutableQuoteAuthority
    execution_source_descriptor: str


@dataclass(frozen=True, slots=True)
class ExecutableEntryFacts:
    eligibility: EligibilityFact | None
    funding_availability: FundingAvailabilityFact | None
    commission: CommissionFact | None
    settlement: SettlementFact | None
    currency_path: CurrencyPathFact | None
    executable_quote: ExecutableQuoteFact | None


@dataclass(frozen=True, slots=True)
class DimensionEvidence:
    claim_id: str
    provenance: EvidenceProvenance


@dataclass(frozen=True, slots=True)
class ExecutableEntryEvidenceBundle:
    eligibility: DimensionEvidence | None
    funding: DimensionEvidence | None
    commission: DimensionEvidence | None
    settlement: DimensionEvidence | None
    executable_quote: DimensionEvidence | None


def _canonical(value):
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value):
        return {
            field.name: _canonical(getattr(value, field.name))
            for field in fields(value)
        }
    if type(value) is Decimal:
        if not value.is_finite():
            raise ExecutableEntryEvidenceError("Nonfinite Decimal")
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
    raise ExecutableEntryEvidenceError("Unsupported deterministic identity value")


def _identity(domain: str, value) -> str:
    payload = json.dumps(
        _canonical(value),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    )
    return hashlib.sha256((domain + "\0" + payload).encode("utf-8")).hexdigest()


def _claim_material(record):
    return {
        field.name: getattr(record, field.name)
        for field in fields(record)
        if field.name != "provenance"
    }


def _dimension_evidence(record) -> DimensionEvidence | None:
    if record is None:
        return None
    return DimensionEvidence(
        _identity("executable-entry-dimension-claim", _claim_material(record)),
        record.provenance,
    )


def _evidence_bundle(
    request: ExecutableEntryEvidenceRequest,
) -> ExecutableEntryEvidenceBundle:
    return ExecutableEntryEvidenceBundle(
        _dimension_evidence(request.eligibility),
        _dimension_evidence(request.funding),
        _dimension_evidence(request.commission),
        _dimension_evidence(request.settlement),
        _dimension_evidence(request.executable_quote),
    )


@dataclass(frozen=True, slots=True)
class ExecutableEntryEvidenceQualification:
    contract_version: str
    qualification_version: str
    execution_context_id: str | None
    target_instrument_id: str | None
    status: ExecutableEntryStatus
    reasons: tuple[ExecutableEntryReason, ...]
    facts: ExecutableEntryFacts
    evidence: ExecutableEntryEvidenceBundle | None
    authority_scope: ExecutableEntryAuthorityScope
    limitations: tuple[ExecutableEntryLimitation, ...]

    @property
    def semantic_id(self) -> str:
        return _identity(
            "executable-entry-evidence-semantics",
            {
                "contract_version": self.contract_version,
                "qualification_version": self.qualification_version,
                "execution_context_id": self.execution_context_id,
                "target_instrument_id": self.target_instrument_id,
                "status": self.status,
                "reasons": self.reasons,
                "facts": self.facts,
                "authority_scope": self.authority_scope,
                "limitations": self.limitations,
            },
        )

    @property
    def evidence_id(self) -> str:
        return _identity(
            "executable-entry-evidence-provenance",
            {"semantic_id": self.semantic_id, "evidence": self.evidence},
        )

    def to_dict(self) -> dict:
        payload = _canonical(self)
        payload["semantic_id"] = self.semantic_id
        payload["evidence_id"] = self.evidence_id
        return {"executable_entry_evidence": payload}


_EMPTY_FACTS = ExecutableEntryFacts(None, None, None, None, None, None)


def _has_fact(facts: ExecutableEntryFacts) -> bool:
    return any(getattr(facts, field.name) is not None for field in fields(facts))


def _result(
    request: ExecutableEntryEvidenceRequest | None,
    *,
    status: ExecutableEntryStatus,
    reasons: set[ExecutableEntryReason] | tuple[ExecutableEntryReason, ...],
    facts: ExecutableEntryFacts = _EMPTY_FACTS,
) -> ExecutableEntryEvidenceQualification:
    return ExecutableEntryEvidenceQualification(
        EXECUTABLE_ENTRY_EVIDENCE_CONTRACT_VERSION,
        EXECUTABLE_ENTRY_EVIDENCE_QUALIFICATION_VERSION,
        request.execution_context_id if request is not None else None,
        request.target_instrument_id if request is not None else None,
        status,
        tuple(sorted(set(reasons), key=lambda item: item.value)),
        facts,
        _evidence_bundle(request) if request is not None else None,
        (
            ExecutableEntryAuthorityScope.CURRENT_CAPTURE_BOUND_EVIDENCE_ONLY
            if _has_fact(facts)
            else ExecutableEntryAuthorityScope.NONE
        ),
        _LIMITATIONS,
    )


def _scope_matches(record, request: ExecutableEntryEvidenceRequest) -> bool:
    return (
        record.execution_context_id == request.execution_context_id
        and record.target_instrument_id == request.target_instrument_id
    )


def _provenance_issues(
    provenance: EvidenceProvenance,
    *,
    conflicts: set[ExecutableEntryReason],
    unavailable: set[ExecutableEntryReason],
) -> bool:
    current = (
        provenance.freshness is CurrentEvidenceFreshness.CURRENT_SAME_RUN_CAPTURE
    )
    if not current:
        unavailable.add(ExecutableEntryReason.CURRENT_FRESHNESS_NOT_ESTABLISHED)
    retrieved = _parse_timestamp(provenance.retrieved_at, "retrieved_at")
    if provenance.publication_timestamp is not None and (
        _parse_timestamp(
            provenance.publication_timestamp, "publication_timestamp"
        ).instant_utc
        > retrieved.instant_utc
    ):
        conflicts.add(ExecutableEntryReason.PROVENANCE_CHRONOLOGY_CONFLICT)
        return False
    return current


def qualify_executable_entry_evidence(
    request: ExecutableEntryEvidenceRequest | None,
) -> ExecutableEntryEvidenceQualification:
    """Qualify independent current subfacts and one closed overall route."""
    if request is None:
        return _result(
            None,
            status=ExecutableEntryStatus.UNAVAILABLE,
            reasons=(ExecutableEntryReason.REQUIRED_EVIDENCE_MISSING,),
        )
    if type(request) is not ExecutableEntryEvidenceRequest:
        raise ExecutableEntryEvidenceError(
            "Typed ExecutableEntryEvidenceRequest or None required"
        )

    conflicts: set[ExecutableEntryReason] = set()
    unsupported: set[ExecutableEntryReason] = set()
    unavailable: set[ExecutableEntryReason] = set()
    fact_values = {
        "eligibility": None,
        "funding_availability": None,
        "commission": None,
        "settlement": None,
        "currency_path": None,
        "executable_quote": None,
    }

    records = (
        request.eligibility,
        request.funding,
        request.commission,
        request.settlement,
        request.executable_quote,
    )
    for record in records:
        if record is not None and not _scope_matches(record, request):
            conflicts.add(ExecutableEntryReason.SCOPE_IDENTITY_CONFLICT)

    eligibility_current = False
    if request.eligibility is None:
        unavailable.update(
            {
                ExecutableEntryReason.REQUIRED_EVIDENCE_MISSING,
                ExecutableEntryReason.ACCOUNT_INSTRUMENT_ELIGIBILITY_NOT_ESTABLISHED,
                ExecutableEntryReason.EXACT_TRANSACTION_CURRENCY_UNAVAILABLE,
            }
        )
    else:
        eligibility_current = _provenance_issues(
            request.eligibility.provenance,
            conflicts=conflicts,
            unavailable=unavailable,
        ) and _scope_matches(request.eligibility, request)
        if eligibility_current:
            if request.eligibility.state is EligibilityState.ELIGIBLE:
                fact_values["eligibility"] = EligibilityFact(
                    request.execution_context_id,
                    request.target_instrument_id,
                    EligibilityState.ELIGIBLE,
                )
            elif request.eligibility.state is EligibilityState.NOT_ESTABLISHED:
                unavailable.add(
                    ExecutableEntryReason.ACCOUNT_INSTRUMENT_ELIGIBILITY_NOT_ESTABLISHED
                )
            elif request.eligibility.state is EligibilityState.NOT_ELIGIBLE:
                unsupported.add(ExecutableEntryReason.INSTRUMENT_NOT_ELIGIBLE)
            else:
                unsupported.add(ExecutableEntryReason.INSTRUMENT_ROUTE_UNSUPPORTED)
            if request.eligibility.transaction_currency is None:
                unavailable.add(
                    ExecutableEntryReason.EXACT_TRANSACTION_CURRENCY_UNAVAILABLE
                )

    funding_current = False
    if request.funding is None:
        unavailable.update(
            {
                ExecutableEntryReason.REQUIRED_EVIDENCE_MISSING,
                ExecutableEntryReason.SETTLED_AVAILABLE_FUNDING_NOT_ESTABLISHED,
                ExecutableEntryReason.EXACT_FUNDING_CURRENCY_UNAVAILABLE,
            }
        )
    else:
        funding_current = _provenance_issues(
            request.funding.provenance,
            conflicts=conflicts,
            unavailable=unavailable,
        ) and _scope_matches(request.funding, request)
        if funding_current:
            if request.funding.state is FundingAvailabilityState.SETTLED_AND_AVAILABLE:
                fact_values["funding_availability"] = FundingAvailabilityFact(
                    request.execution_context_id,
                    request.target_instrument_id,
                    FundingAvailabilityState.SETTLED_AND_AVAILABLE,
                )
            else:
                unavailable.add(
                    ExecutableEntryReason.SETTLED_AVAILABLE_FUNDING_NOT_ESTABLISHED
                )
            if request.funding.funding_currency is None:
                unavailable.add(
                    ExecutableEntryReason.EXACT_FUNDING_CURRENCY_UNAVAILABLE
                )

    if request.commission is None:
        unavailable.update(
            {
                ExecutableEntryReason.REQUIRED_EVIDENCE_MISSING,
                ExecutableEntryReason.COMMISSION_UNAVAILABLE,
            }
        )
    else:
        commission_current = _provenance_issues(
            request.commission.provenance,
            conflicts=conflicts,
            unavailable=unavailable,
        ) and _scope_matches(request.commission, request)
        if commission_current:
            if request.commission.semantics is None:
                unavailable.add(ExecutableEntryReason.COMMISSION_UNAVAILABLE)
            elif (
                request.commission.semantics
                is not CommissionSemantics.FLAT_PER_ORDER_TRANSACTION_CURRENCY
            ):
                unsupported.add(
                    ExecutableEntryReason.COMMISSION_SEMANTICS_UNSUPPORTED
                )
            if request.commission.amount is None or request.commission.currency is None:
                unavailable.add(ExecutableEntryReason.COMMISSION_UNAVAILABLE)
            elif request.commission.amount < 0:
                conflicts.add(ExecutableEntryReason.COMMISSION_AMOUNT_CONFLICT)
            elif (
                request.commission.semantics
                is CommissionSemantics.FLAT_PER_ORDER_TRANSACTION_CURRENCY
            ):
                fact_values["commission"] = CommissionFact(
                    request.commission.amount,
                    request.commission.currency,
                    request.commission.semantics,
                )

    if request.settlement is None:
        unavailable.update(
            {
                ExecutableEntryReason.REQUIRED_EVIDENCE_MISSING,
                ExecutableEntryReason.SETTLEMENT_SEMANTICS_UNAVAILABLE,
            }
        )
    else:
        settlement_current = _provenance_issues(
            request.settlement.provenance,
            conflicts=conflicts,
            unavailable=unavailable,
        ) and _scope_matches(request.settlement, request)
        if settlement_current:
            if request.settlement.semantics is None or request.settlement.cycle is None:
                unavailable.add(
                    ExecutableEntryReason.SETTLEMENT_SEMANTICS_UNAVAILABLE
                )
            else:
                if (
                    request.settlement.semantics
                    is not SettlementSemantics.POST_TRADE_REGULAR_WAY
                ):
                    unsupported.add(
                        ExecutableEntryReason.SETTLEMENT_SEMANTICS_UNSUPPORTED
                    )
                if request.settlement.cycle is not SettlementCycle.T_PLUS_1:
                    unsupported.add(
                        ExecutableEntryReason.SETTLEMENT_CYCLE_UNSUPPORTED
                    )
                if (
                    request.settlement.semantics
                    is SettlementSemantics.POST_TRADE_REGULAR_WAY
                    and request.settlement.cycle is SettlementCycle.T_PLUS_1
                ):
                    fact_values["settlement"] = SettlementFact(
                        request.settlement.semantics,
                        request.settlement.cycle,
                    )

    transaction_currency = (
        request.eligibility.transaction_currency
        if request.eligibility is not None and eligibility_current
        else None
    )
    funding_currency = (
        request.funding.funding_currency
        if request.funding is not None and funding_current
        else None
    )
    if funding_currency is not None and transaction_currency is not None:
        currency_state = (
            CurrencyPathState.FX_NOT_REQUIRED_SAME_CURRENCY
            if funding_currency == transaction_currency
            else CurrencyPathState.FX_REQUIRED_EXECUTION_COST_UNAVAILABLE
        )
        fact_values["currency_path"] = CurrencyPathFact(
            funding_currency, transaction_currency, currency_state
        )
        if currency_state is CurrencyPathState.FX_REQUIRED_EXECUTION_COST_UNAVAILABLE:
            unavailable.add(
                ExecutableEntryReason.FX_EXECUTION_COST_EVIDENCE_UNAVAILABLE
            )

    if (
        fact_values["commission"] is not None
        and transaction_currency is not None
        and fact_values["commission"].currency != transaction_currency
    ):
        conflicts.add(ExecutableEntryReason.COMMISSION_CURRENCY_CONFLICT)
        fact_values["commission"] = None

    if request.executable_quote is None:
        unavailable.update(
            {
                ExecutableEntryReason.REQUIRED_EVIDENCE_MISSING,
                ExecutableEntryReason.EXECUTABLE_QUOTE_UNAVAILABLE,
            }
        )
    else:
        quote_current = _provenance_issues(
            request.executable_quote.provenance,
            conflicts=conflicts,
            unavailable=unavailable,
        ) and _scope_matches(request.executable_quote, request)
        quote = request.executable_quote
        if quote_current:
            complete = all(
                value is not None
                for value in (
                    quote.bid,
                    quote.ask,
                    quote.currency,
                    quote.market_timestamp,
                    quote.authority,
                    quote.execution_source_descriptor,
                )
            )
            if not complete:
                unavailable.add(ExecutableEntryReason.EXECUTABLE_QUOTE_UNAVAILABLE)
            if quote.authority is not ExecutableQuoteAuthority.EXECUTABLE_BID_ASK:
                unavailable.update(
                    {
                        ExecutableEntryReason.EXECUTABLE_QUOTE_UNAVAILABLE,
                        ExecutableEntryReason.EXECUTABLE_QUOTE_AUTHORITY_INSUFFICIENT,
                    }
                )
            valid_prices = (
                quote.bid is not None
                and quote.ask is not None
                and quote.bid > 0
                and quote.ask > 0
                and quote.bid <= quote.ask
            )
            if quote.bid is not None and quote.ask is not None and not valid_prices:
                conflicts.add(ExecutableEntryReason.QUOTE_BID_ASK_CONFLICT)
            chronology_valid = True
            if quote.market_timestamp is not None:
                chronology_valid = (
                    _parse_timestamp(
                        quote.market_timestamp, "market_timestamp"
                    ).instant_utc
                    <= _parse_timestamp(
                        quote.provenance.retrieved_at, "retrieved_at"
                    ).instant_utc
                )
                if not chronology_valid:
                    conflicts.add(ExecutableEntryReason.QUOTE_CHRONOLOGY_CONFLICT)
            currency_valid = True
            if quote.currency is not None and transaction_currency is not None:
                currency_valid = quote.currency == transaction_currency
                if not currency_valid:
                    conflicts.add(ExecutableEntryReason.QUOTE_CURRENCY_CONFLICT)
            if (
                complete
                and quote.authority is ExecutableQuoteAuthority.EXECUTABLE_BID_ASK
                and valid_prices
                and chronology_valid
                and currency_valid
                and transaction_currency is not None
            ):
                fact_values["executable_quote"] = ExecutableQuoteFact(
                    quote.bid,
                    quote.ask,
                    quote.currency,
                    quote.market_timestamp,
                    quote.authority,
                    quote.execution_source_descriptor,
                )

    facts = ExecutableEntryFacts(**fact_values)
    if conflicts:
        return _result(
            request,
            status=ExecutableEntryStatus.SOURCE_CONFLICT,
            reasons=conflicts,
            facts=facts,
        )
    if unsupported:
        return _result(
            request,
            status=ExecutableEntryStatus.UNSUPPORTED,
            reasons=unsupported,
            facts=facts,
        )
    if unavailable:
        return _result(
            request,
            status=ExecutableEntryStatus.UNAVAILABLE,
            reasons=unavailable,
            facts=facts,
        )
    return _result(
        request,
        status=ExecutableEntryStatus.AVAILABLE,
        reasons=(),
        facts=facts,
    )
