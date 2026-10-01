"""Pure qualification for the reviewed, dated VFV FX/hedge evidence.

This module deliberately starts after acquisition and extraction.  It accepts
immutable typed source records, qualifies only the one reviewed disclosure
state, and grants no historical/PIT, forecast, or permanent-hedge authority.
"""
from __future__ import annotations

from dataclasses import dataclass, fields, is_dataclass
from datetime import date, datetime, timezone
from decimal import Decimal
from enum import Enum, StrEnum
import hashlib
import json
import re

from .source_authority import AvailabilitySemantics, PublicationSemantics


VFV_FX_HEDGE_EVIDENCE_CONTRACT_VERSION = (
    "2026-10-01-vfv-fx-hedge-evidence-v1"
)
VFV_FX_HEDGE_QUALIFICATION_VERSION = (
    "2026-10-01-vfv-fx-hedge-qualification-v1"
)
_HASH = re.compile(r"[0-9a-f]{64}")
_SUPPORTED_MEASUREMENT_DATE = "2026-06-30"


class VFVFXHedgeEvidenceError(ValueError):
    """Malformed programming contract; evidence absence uses closed status."""


class VFVFXHedgeEvidenceStatus(StrEnum):
    AVAILABLE = "AVAILABLE"
    UNAVAILABLE = "UNAVAILABLE"
    UNSUPPORTED = "UNSUPPORTED"
    SOURCE_CONFLICT = "SOURCE_CONFLICT"


class VFVFXHedgeEvidenceReason(StrEnum):
    REQUIRED_EVIDENCE_MISSING = "REQUIRED_EVIDENCE_MISSING"
    REQUIRED_DISCLOSURE_VALUE_UNAVAILABLE = (
        "REQUIRED_DISCLOSURE_VALUE_UNAVAILABLE"
    )
    SOURCE_SEMANTICS_UNSUPPORTED = "SOURCE_SEMANTICS_UNSUPPORTED"
    SOURCE_ASSERTIONS_CONFLICT = "SOURCE_ASSERTIONS_CONFLICT"
    SOURCE_CHRONOLOGY_INVALID = "SOURCE_CHRONOLOGY_INVALID"
    INSTRUMENT_IDENTITY_UNSUPPORTED = "INSTRUMENT_IDENTITY_UNSUPPORTED"
    LISTED_OR_BASE_CURRENCY_UNSUPPORTED = (
        "LISTED_OR_BASE_CURRENCY_UNSUPPORTED"
    )
    ECONOMIC_EXPOSURE_CURRENCY_UNSUPPORTED = (
        "ECONOMIC_EXPOSURE_CURRENCY_UNSUPPORTED"
    )
    MATERIAL_HEDGE_STATE_UNAVAILABLE = "MATERIAL_HEDGE_STATE_UNAVAILABLE"
    MATERIAL_HEDGE_STATE_UNSUPPORTED = "MATERIAL_HEDGE_STATE_UNSUPPORTED"
    MEASUREMENT_DATE_UNSUPPORTED = "MEASUREMENT_DATE_UNSUPPORTED"
    NET_USD_EXPOSURE_UNSUPPORTED = "NET_USD_EXPOSURE_UNSUPPORTED"


class VFVFXHedgeSourceRole(StrEnum):
    NET_CURRENCY_EXPOSURE_AFTER_CURRENCY_CONTRACTS = (
        "NET_CURRENCY_EXPOSURE_AFTER_CURRENCY_CONTRACTS"
    )
    OTHER = "OTHER"


class VFVMaterialHedgeState(StrEnum):
    MATERIALLY_UNHEDGED_USD_EXPOSURE_TO_CAD_AT_DISCLOSURE_DATE = (
        "MATERIALLY_UNHEDGED_USD_EXPOSURE_TO_CAD_AT_DISCLOSURE_DATE"
    )
    MATERIALLY_HEDGED_TO_CAD_AT_DISCLOSURE_DATE = (
        "MATERIALLY_HEDGED_TO_CAD_AT_DISCLOSURE_DATE"
    )
    UNKNOWN = "UNKNOWN"


class VFVFXExposureUnit(StrEnum):
    PERCENT_OF_NAV_AFTER_CURRENCY_CONTRACTS = (
        "PERCENT_OF_NAV_AFTER_CURRENCY_CONTRACTS"
    )


class VFVFXHedgeAuthorityScope(StrEnum):
    NONE = "NONE"
    CURRENT_CAPTURE_BOUND_DATE_BOUND = "CURRENT_CAPTURE_BOUND_DATE_BOUND"


class VFVFXHedgeConfidenceLevel(StrEnum):
    NONE = "NONE"
    LOW = "LOW"


class VFVFXHedgeEvidenceLimitation(StrEnum):
    RESEARCH_DIAGNOSTIC_ONLY = "RESEARCH_DIAGNOSTIC_ONLY"
    CAPTURE_BOUND_AVAILABILITY_ONLY = "CAPTURE_BOUND_AVAILABILITY_ONLY"
    DATE_BOUND_DISCLOSURE_STATE_ONLY = "DATE_BOUND_DISCLOSURE_STATE_ONLY"
    NO_PERMANENT_NO_HEDGING_MANDATE_AUTHORITY = (
        "NO_PERMANENT_NO_HEDGING_MANDATE_AUTHORITY"
    )
    NO_ZERO_CURRENCY_CONTRACTS_CLAIM = "NO_ZERO_CURRENCY_CONTRACTS_CLAIM"
    NO_HEDGE_RATIO_AFTER_2026_06_30_AUTHORITY = (
        "NO_HEDGE_RATIO_AFTER_2026_06_30_AUTHORITY"
    )
    NO_HISTORICAL_AS_OF_OR_PIT_AUTHORITY = (
        "NO_HISTORICAL_AS_OF_OR_PIT_AUTHORITY"
    )
    NO_FX_FORECAST_AUTHORITY = "NO_FX_FORECAST_AUTHORITY"
    NO_RECOMMENDATION_OR_ALLOCATION_AUTHORITY = (
        "NO_RECOMMENDATION_OR_ALLOCATION_AUTHORITY"
    )
    NO_PRODUCTION_OR_EXECUTION_AUTHORITY = (
        "NO_PRODUCTION_OR_EXECUTION_AUTHORITY"
    )


_LIMITATIONS = tuple(VFVFXHedgeEvidenceLimitation)


def _require_text(value: object, label: str) -> None:
    if type(value) is not str or not value or value != value.strip():
        raise VFVFXHedgeEvidenceError(
            f"{label}: nonempty trimmed string required")


def _parse_date(value: object, label: str) -> date:
    _require_text(value, label)
    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise VFVFXHedgeEvidenceError(f"{label}: ISO date required") from exc
    if parsed.isoformat() != value:
        raise VFVFXHedgeEvidenceError(f"{label}: canonical ISO date required")
    return parsed


def _parse_timestamp(value: object, label: str) -> datetime:
    _require_text(value, label)
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise VFVFXHedgeEvidenceError(
            f"{label}: offset-aware ISO timestamp required") from exc
    if parsed.tzinfo is None:
        raise VFVFXHedgeEvidenceError(
            f"{label}: offset-aware ISO timestamp required")
    return parsed.astimezone(timezone.utc)


@dataclass(frozen=True, slots=True)
class VFVFXHedgeEvidenceRecord:
    source_role: VFVFXHedgeSourceRole
    source_owner: str
    source_document_id: str
    source_reference: str
    content_sha256: str
    source_locator: str
    capture_id: str
    captured_at: str
    reviewed_at: str
    publication_semantics: PublicationSemantics
    availability_semantics: AvailabilitySemantics
    instrument_ticker: str
    instrument_isin: str
    listed_currency: str
    base_currency: str
    economic_exposure_currency: str | None
    material_hedge_state: VFVMaterialHedgeState
    measurement_date: str
    net_usd_exposure_percent_of_nav: Decimal | None
    exposure_unit: VFVFXExposureUnit

    def __post_init__(self):
        if type(self.source_role) is not VFVFXHedgeSourceRole:
            raise VFVFXHedgeEvidenceError("Closed source role required")
        if type(self.material_hedge_state) is not VFVMaterialHedgeState:
            raise VFVFXHedgeEvidenceError("Closed material hedge state required")
        if type(self.exposure_unit) is not VFVFXExposureUnit:
            raise VFVFXHedgeEvidenceError("Closed exposure unit required")
        if type(self.publication_semantics) is not PublicationSemantics:
            raise VFVFXHedgeEvidenceError("Typed publication semantics required")
        if type(self.availability_semantics) is not AvailabilitySemantics:
            raise VFVFXHedgeEvidenceError("Typed availability semantics required")
        for name in (
                "source_owner", "source_document_id", "source_reference",
                "source_locator", "instrument_ticker", "instrument_isin",
                "listed_currency", "base_currency", "measurement_date"):
            _require_text(getattr(self, name), name)
        if (type(self.content_sha256) is not str
                or _HASH.fullmatch(self.content_sha256) is None
                or type(self.capture_id) is not str
                or _HASH.fullmatch(self.capture_id) is None):
            raise VFVFXHedgeEvidenceError(
                "Exact content and capture SHA-256 identities required")
        _parse_timestamp(self.captured_at, "captured_at")
        _parse_timestamp(self.reviewed_at, "reviewed_at")
        _parse_date(self.measurement_date, "measurement_date")
        if self.economic_exposure_currency is not None:
            _require_text(
                self.economic_exposure_currency, "economic_exposure_currency")
        if self.net_usd_exposure_percent_of_nav is not None:
            value = self.net_usd_exposure_percent_of_nav
            if (type(value) is not Decimal or not value.is_finite()
                    or value < 0 or value > 100):
                raise VFVFXHedgeEvidenceError(
                    "Net USD exposure must be an exact Decimal percentage")


@dataclass(frozen=True, slots=True)
class _RecordSemanticProjection:
    source_role: VFVFXHedgeSourceRole
    instrument_ticker: str
    instrument_isin: str
    listed_currency: str
    base_currency: str
    economic_exposure_currency: str | None
    material_hedge_state: VFVMaterialHedgeState
    measurement_date: str
    net_usd_exposure_percent_of_nav: Decimal | None
    exposure_unit: VFVFXExposureUnit


def _record_semantics(record: VFVFXHedgeEvidenceRecord):
    return _RecordSemanticProjection(
        record.source_role,
        record.instrument_ticker,
        record.instrument_isin,
        record.listed_currency,
        record.base_currency,
        record.economic_exposure_currency,
        record.material_hedge_state,
        record.measurement_date,
        record.net_usd_exposure_percent_of_nav,
        record.exposure_unit,
    )


def _canonical(value):
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Decimal):
        return str(value)
    if is_dataclass(value):
        return {field.name: _canonical(getattr(value, field.name))
                for field in fields(value)}
    if isinstance(value, tuple):
        return [_canonical(item) for item in value]
    if isinstance(value, dict):
        return {key: _canonical(value[key]) for key in sorted(value)}
    if value is None or type(value) in (str, int, bool):
        return value
    raise VFVFXHedgeEvidenceError("Unsupported identity value")


def _identity(domain: str, value) -> str:
    payload = json.dumps(
        _canonical(value), sort_keys=True, separators=(",", ":"),
        ensure_ascii=True, allow_nan=False,
    )
    return hashlib.sha256((domain + "\0" + payload).encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class VFVFXHedgeEvidenceQualification:
    contract_version: str
    qualification_version: str
    status: VFVFXHedgeEvidenceStatus
    reasons: tuple[VFVFXHedgeEvidenceReason, ...]
    authority_scope: VFVFXHedgeAuthorityScope
    confidence: VFVFXHedgeConfidenceLevel
    instrument_ticker: str | None
    instrument_isin: str | None
    listed_currency: str | None
    base_currency: str | None
    economic_exposure_currency: str | None
    material_hedge_state: VFVMaterialHedgeState | None
    measurement_date: str | None
    net_usd_exposure_percent_of_nav: Decimal | None
    exposure_unit: VFVFXExposureUnit | None
    capture_ids: tuple[str, ...]
    latest_captured_at: str | None
    latest_reviewed_at: str | None
    source_records: tuple[VFVFXHedgeEvidenceRecord, ...]
    limitations: tuple[VFVFXHedgeEvidenceLimitation, ...]

    @property
    def semantic_id(self) -> str:
        semantic_records = tuple(sorted(
            {_identity("vfv-fx-hedge-record-semantics", _record_semantics(item))
             for item in self.source_records}
        ))
        return _identity("vfv-fx-hedge-qualification-semantics", {
            "contract_version": self.contract_version,
            "qualification_version": self.qualification_version,
            "status": self.status,
            "reasons": self.reasons,
            "authority_scope": self.authority_scope,
            "confidence": self.confidence,
            "instrument_ticker": self.instrument_ticker,
            "instrument_isin": self.instrument_isin,
            "listed_currency": self.listed_currency,
            "base_currency": self.base_currency,
            "economic_exposure_currency": self.economic_exposure_currency,
            "material_hedge_state": self.material_hedge_state,
            "measurement_date": self.measurement_date,
            "net_usd_exposure_percent_of_nav": (
                self.net_usd_exposure_percent_of_nav),
            "exposure_unit": self.exposure_unit,
            "source_semantics": semantic_records,
            "limitations": self.limitations,
        })

    @property
    def evidence_id(self) -> str:
        return _identity("vfv-fx-hedge-qualification-evidence", {
            "semantic_id": self.semantic_id,
            "capture_ids": self.capture_ids,
            "latest_captured_at": self.latest_captured_at,
            "latest_reviewed_at": self.latest_reviewed_at,
            "source_records": self.source_records,
        })

    def to_dict(self) -> dict:
        payload = _canonical(self)
        payload["semantic_id"] = self.semantic_id
        payload["evidence_id"] = self.evidence_id
        return {"vfv_fx_hedge_evidence": payload}


def _result(
    records: tuple[VFVFXHedgeEvidenceRecord, ...],
    *,
    status: VFVFXHedgeEvidenceStatus,
    reasons: tuple[VFVFXHedgeEvidenceReason, ...],
    record: VFVFXHedgeEvidenceRecord | None = None,
) -> VFVFXHedgeEvidenceQualification:
    captures = tuple(sorted({item.capture_id for item in records}))
    captured_at = tuple(_parse_timestamp(item.captured_at, "captured_at")
                        for item in records)
    reviewed_at = tuple(_parse_timestamp(item.reviewed_at, "reviewed_at")
                        for item in records)
    available = status is VFVFXHedgeEvidenceStatus.AVAILABLE
    return VFVFXHedgeEvidenceQualification(
        VFV_FX_HEDGE_EVIDENCE_CONTRACT_VERSION,
        VFV_FX_HEDGE_QUALIFICATION_VERSION,
        status,
        tuple(sorted(set(reasons), key=lambda item: item.value)),
        (VFVFXHedgeAuthorityScope.CURRENT_CAPTURE_BOUND_DATE_BOUND
         if available else VFVFXHedgeAuthorityScope.NONE),
        (VFVFXHedgeConfidenceLevel.LOW
         if available else VFVFXHedgeConfidenceLevel.NONE),
        record.instrument_ticker if available else None,
        record.instrument_isin if available else None,
        record.listed_currency if available else None,
        record.base_currency if available else None,
        record.economic_exposure_currency if available else None,
        record.material_hedge_state if available else None,
        record.measurement_date if available else None,
        record.net_usd_exposure_percent_of_nav if available else None,
        record.exposure_unit if available else None,
        captures,
        max(captured_at).isoformat() if captured_at else None,
        max(reviewed_at).isoformat() if reviewed_at else None,
        tuple(sorted(records, key=lambda item: (
            item.source_role.value, item.source_document_id,
            item.capture_id, item.source_locator))),
        _LIMITATIONS,
    )


def qualify_vfv_fx_hedge_evidence(
    records: tuple[VFVFXHedgeEvidenceRecord, ...],
) -> VFVFXHedgeEvidenceQualification:
    """Qualify only the exact reviewed, dated VFV USD-exposure conclusion."""
    if type(records) is not tuple or not all(
            type(item) is VFVFXHedgeEvidenceRecord for item in records):
        raise VFVFXHedgeEvidenceError(
            "Immutable typed VFV FX/hedge records required")
    if not records:
        return _result(
            (), status=VFVFXHedgeEvidenceStatus.UNAVAILABLE,
            reasons=(VFVFXHedgeEvidenceReason.REQUIRED_EVIDENCE_MISSING,),
        )

    semantic_projections = {_record_semantics(item) for item in records}
    if len(semantic_projections) != 1:
        return _result(
            records, status=VFVFXHedgeEvidenceStatus.SOURCE_CONFLICT,
            reasons=(VFVFXHedgeEvidenceReason.SOURCE_ASSERTIONS_CONFLICT,),
        )
    record = records[0]
    measurement = _parse_date(record.measurement_date, "measurement_date")
    chronology_invalid = any(
        _parse_timestamp(item.captured_at, "captured_at").date() < measurement
        or _parse_timestamp(item.reviewed_at, "reviewed_at")
        < _parse_timestamp(item.captured_at, "captured_at")
        for item in records
    )
    if chronology_invalid:
        return _result(
            records, status=VFVFXHedgeEvidenceStatus.SOURCE_CONFLICT,
            reasons=(VFVFXHedgeEvidenceReason.SOURCE_CHRONOLOGY_INVALID,),
        )

    unavailable = set()
    unsupported = set()
    if record.source_role is not (
            VFVFXHedgeSourceRole.
            NET_CURRENCY_EXPOSURE_AFTER_CURRENCY_CONTRACTS):
        unsupported.add(
            VFVFXHedgeEvidenceReason.SOURCE_SEMANTICS_UNSUPPORTED)
    if record.economic_exposure_currency is None \
            or record.net_usd_exposure_percent_of_nav is None:
        unavailable.add(
            VFVFXHedgeEvidenceReason.REQUIRED_DISCLOSURE_VALUE_UNAVAILABLE)
    if record.material_hedge_state is VFVMaterialHedgeState.UNKNOWN:
        unavailable.add(
            VFVFXHedgeEvidenceReason.MATERIAL_HEDGE_STATE_UNAVAILABLE)
    elif record.material_hedge_state is not (
            VFVMaterialHedgeState.
            MATERIALLY_UNHEDGED_USD_EXPOSURE_TO_CAD_AT_DISCLOSURE_DATE):
        unsupported.add(
            VFVFXHedgeEvidenceReason.MATERIAL_HEDGE_STATE_UNSUPPORTED)
    if (record.instrument_ticker != "VFV"
            or record.instrument_isin != "CA92205Y1051"):
        unsupported.add(
            VFVFXHedgeEvidenceReason.INSTRUMENT_IDENTITY_UNSUPPORTED)
    if record.listed_currency != "CAD" or record.base_currency != "CAD":
        unsupported.add(
            VFVFXHedgeEvidenceReason.LISTED_OR_BASE_CURRENCY_UNSUPPORTED)
    if (record.economic_exposure_currency is not None
            and record.economic_exposure_currency != "USD"):
        unsupported.add(
            VFVFXHedgeEvidenceReason.
            ECONOMIC_EXPOSURE_CURRENCY_UNSUPPORTED)
    if record.measurement_date != _SUPPORTED_MEASUREMENT_DATE:
        unsupported.add(
            VFVFXHedgeEvidenceReason.MEASUREMENT_DATE_UNSUPPORTED)
    if (record.net_usd_exposure_percent_of_nav is not None
            and record.net_usd_exposure_percent_of_nav != Decimal("100.0")):
        unsupported.add(
            VFVFXHedgeEvidenceReason.NET_USD_EXPOSURE_UNSUPPORTED)
    if (record.publication_semantics is not PublicationSemantics.UNKNOWN
            or record.availability_semantics is not
            AvailabilitySemantics.CAPTURE_BOUND):
        unsupported.add(
            VFVFXHedgeEvidenceReason.SOURCE_SEMANTICS_UNSUPPORTED)

    if unavailable:
        return _result(
            records, status=VFVFXHedgeEvidenceStatus.UNAVAILABLE,
            reasons=tuple(unavailable),
        )
    if unsupported:
        return _result(
            records, status=VFVFXHedgeEvidenceStatus.UNSUPPORTED,
            reasons=tuple(unsupported),
        )
    return _result(
        records, status=VFVFXHedgeEvidenceStatus.AVAILABLE,
        reasons=(), record=record,
    )
