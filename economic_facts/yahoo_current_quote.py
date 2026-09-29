"""Strict Yahoo Chart replay and PR5B-bound CURRENT quote qualification.

This module establishes one observed USD-per-current-traded-share proposition.
It intentionally does not bridge that traded share to PR5C's historical EPS
presentation basis and never constructs a PR4B1 ``ObservedPrice`` root.
"""
from dataclasses import dataclass, fields, is_dataclass
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum, StrEnum
import hashlib
import json
import re

from .nasdaq_listed_archive import NasdaqListedArchive
from .sec_archive import SecArchive
from .sec_current_security_eps_qualification import (
    QualificationStatus,
    SecCurrentSecurityEPSQualification,
    SecCurrentSecurityEPSQualificationRequest,
    qualify_sec_current_security_eps,
)
from .sec_filing_archive import SecFilingArchive
from .sec_submissions_archive import SecSubmissionsArchive
from .sec_ticker_exchange_archive import SecTickerExchangeArchive
from .source_authority import YAHOO_FINANCE_CHART_CURRENT_QUOTE_V1, get_source_route
from .yahoo_quote_archive import (
    LIVE_ACQUISITION_CONTRACT_VERSION,
    RECEIPT_SCHEMA_VERSION,
    YahooQuoteArchive,
    YahooQuoteArchiveError,
    YahooQuoteReceipt,
)


EXTRACTION_VERSION = "2026-09-28-yahoo-current-quote-extraction-v1"
QUALIFICATION_VERSION = "2026-09-28-yahoo-current-quote-qualification-v1"
PRICE_UNIT = "CURRENCY_PER_SHARE"
REVIEWED_VENUE_ID = "NASDAQ_GLOBAL_SELECT"
REVIEWED_YAHOO_VENUE = ("NMS", "NasdaqGS")
VENUE_PROFILE_VERSION = "2026-09-28-yahoo-nms-nasdaqgs-usd-equity-v1"
_HASH = re.compile(r"[0-9a-f]{64}")


class YahooCurrentQuoteError(ValueError):
    """Invalid closed request/type or archive integrity failure."""


class QuoteExtractionStatus(StrEnum):
    QUOTE_EXTRACTED = "QUOTE_EXTRACTED"
    QUOTE_UNAVAILABLE = "QUOTE_UNAVAILABLE"
    QUOTE_UNSUPPORTED = "QUOTE_UNSUPPORTED"
    SOURCE_CONFLICT = "SOURCE_CONFLICT"


class CurrentQuoteStatus(StrEnum):
    CURRENT_QUOTE_ESTABLISHED = "CURRENT_QUOTE_ESTABLISHED"
    QUOTE_UNAVAILABLE = "QUOTE_UNAVAILABLE"
    QUOTE_UNSUPPORTED = "QUOTE_UNSUPPORTED"
    SOURCE_CONFLICT = "SOURCE_CONFLICT"


class CurrentQuoteReason(StrEnum):
    PR5B_NOT_ESTABLISHED = "PR5B_NOT_ESTABLISHED"
    QUOTE_SOURCE_UNAVAILABLE = "QUOTE_SOURCE_UNAVAILABLE"
    QUOTE_SOURCE_UNSUPPORTED = "QUOTE_SOURCE_UNSUPPORTED"
    SYMBOL_MISMATCH = "SYMBOL_MISMATCH"
    VENUE_MISMATCH = "VENUE_MISMATCH"
    INSTRUMENT_TYPE_UNSUPPORTED = "INSTRUMENT_TYPE_UNSUPPORTED"
    CURRENCY_MISMATCH = "CURRENCY_MISMATCH"
    PRICE_INVALID = "PRICE_INVALID"
    PROVIDER_TIMESTAMP_INVALID = "PROVIDER_TIMESTAMP_INVALID"
    QUOTE_AFTER_CAPTURE = "QUOTE_AFTER_CAPTURE"
    SOURCE_CONFLICT = "SOURCE_CONFLICT"


class CurrentQuoteLimitation(StrEnum):
    QUOTE_TO_PR5C_BASIS_BRIDGE_NOT_ESTABLISHED = (
        "QUOTE_TO_PR5C_BASIS_BRIDGE_NOT_ESTABLISHED"
    )
    NO_FINAL_ECONOMIC_ADMISSION = "NO_FINAL_ECONOMIC_ADMISSION"
    NO_PR4B1_OBSERVED_PRICE_ROOT = "NO_PR4B1_OBSERVED_PRICE_ROOT"
    NO_EXPECTED_RETURN = "NO_EXPECTED_RETURN"
    NO_RECOMMENDATION_OR_ALLOCATION = "NO_RECOMMENDATION_OR_ALLOCATION"
    NO_HISTORICAL_AS_OF_AUTHORITY = "NO_HISTORICAL_AS_OF_AUTHORITY"
    NO_PROVIDER_FALLBACK = "NO_PROVIDER_FALLBACK"
    COMMERCIAL_REDISTRIBUTION_NOT_AUTHORIZED = (
        "COMMERCIAL_REDISTRIBUTION_NOT_AUTHORIZED"
    )
    CURRENT_PRIVATE_INTERNAL_RESEARCH_ONLY = "CURRENT_PRIVATE_INTERNAL_RESEARCH_ONLY"


@dataclass(frozen=True, slots=True)
class YahooCurrentQuoteExtraction:
    extraction_version: str
    receipt: YahooQuoteReceipt
    status: QuoteExtractionStatus
    reasons: tuple[CurrentQuoteReason, ...]
    returned_symbol: str | None
    exchange_name: str | None
    full_exchange_name: str | None
    reviewed_venue_id: str | None
    instrument_type: str | None
    currency: str | None
    price: Decimal | None
    price_source_text: str | None
    price_unit: str | None
    provider_market_epoch: int | None
    provider_market_timestamp: str | None
    response_structure_locator: str
    meta_sha256: str | None

    @property
    def semantic_id(self):
        return _identity("quote-extraction-semantics", {
            "version": self.extraction_version,
            "profile": self.receipt.endpoint_profile_id,
            "requested_symbol": self.receipt.requested_symbol,
            "status": self.status,
            "reasons": self.reasons,
            "returned_symbol": self.returned_symbol,
            "exchange_name": self.exchange_name,
            "full_exchange_name": self.full_exchange_name,
            "reviewed_venue_id": self.reviewed_venue_id,
            "instrument_type": self.instrument_type,
            "currency": self.currency,
            "price": self.price,
            "price_unit": self.price_unit,
            "provider_market_epoch": self.provider_market_epoch,
            "provider_market_timestamp": self.provider_market_timestamp,
            "locator": self.response_structure_locator,
        })

    @property
    def evidence_id(self):
        return _identity("quote-extraction-evidence", {
            "semantic_id": self.semantic_id,
            "receipt_id": self.receipt.receipt_id,
            "source_hash": self.receipt.content_sha256,
            "captured_at": self.receipt.captured_at,
            "endpoint": self.receipt.endpoint,
            "meta_sha256": self.meta_sha256,
        })


@dataclass(frozen=True, slots=True)
class YahooCurrentQuoteQualificationRequest:
    security_request: SecCurrentSecurityEPSQualificationRequest
    expected_security_semantic_id: str
    expected_security_evidence_id: str
    quote_receipt_id: str
    expected_quote_semantic_id: str
    expected_quote_evidence_id: str

    def __post_init__(self):
        if type(self.security_request) is not SecCurrentSecurityEPSQualificationRequest:
            raise YahooCurrentQuoteError("Exact PR5B selector request required")
        for value in (
            self.expected_security_semantic_id,
            self.expected_security_evidence_id,
            self.quote_receipt_id,
            self.expected_quote_semantic_id,
            self.expected_quote_evidence_id,
        ):
            if type(value) is not str or _HASH.fullmatch(value) is None:
                raise YahooCurrentQuoteError("Exact expected identity required")


@dataclass(frozen=True, slots=True)
class QualifiedCurrentQuote:
    contract_version: str
    route_id: str
    route_profile_hash: str
    route_factual_hash: str
    license_status: str
    use_status: str
    status: CurrentQuoteStatus
    reasons: tuple[CurrentQuoteReason, ...]
    price: Decimal | None
    currency: str | None
    unit: str | None
    symbol: str | None
    venue_id: str | None
    instrument_type: str | None
    provider_market_epoch: int | None
    provider_market_timestamp: str | None
    captured_at: str
    route_local_issuer_key: str | None
    route_local_security_key: str | None
    upstream_security: SecCurrentSecurityEPSQualification
    quote_extraction: YahooCurrentQuoteExtraction
    limitations: tuple[CurrentQuoteLimitation, ...]

    @property
    def semantic_id(self):
        return _identity("current-quote-qualification-semantics", {
            "contract": self.contract_version,
            "route": self.route_id,
            "route_factual_hash": self.route_factual_hash,
            "status": self.status,
            "reasons": self.reasons,
            "price": self.price,
            "currency": self.currency,
            "unit": self.unit,
            "symbol": self.symbol,
            "venue_id": self.venue_id,
            "instrument_type": self.instrument_type,
            "provider_market_epoch": self.provider_market_epoch,
            "provider_market_timestamp": self.provider_market_timestamp,
            "route_local_issuer_key": self.route_local_issuer_key,
            "route_local_security_key": self.route_local_security_key,
            "security_semantic_id": self.upstream_security.semantic_id,
            "quote_semantic_id": self.quote_extraction.semantic_id,
            "limitations": self.limitations,
        })

    @property
    def evidence_id(self):
        return _identity("current-quote-qualification-evidence", {
            "semantic_id": self.semantic_id,
            "route_profile_hash": self.route_profile_hash,
            "license_status": self.license_status,
            "use_status": self.use_status,
            "captured_at": self.captured_at,
            "security_evidence_id": self.upstream_security.evidence_id,
            "quote_evidence_id": self.quote_extraction.evidence_id,
            "receipt_id": self.quote_extraction.receipt.receipt_id,
            "source_hash": self.quote_extraction.receipt.content_sha256,
        })


def _project(value):
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value):
        return {field.name: _project(getattr(value, field.name)) for field in fields(value)}
    if type(value) is Decimal:
        if not value.is_finite():
            raise YahooCurrentQuoteError("Nonfinite Decimal")
        sign, digits, exponent = value.as_tuple()
        digits = list(digits)
        while len(digits) > 1 and digits[-1] == 0:
            digits.pop()
            exponent += 1
        if not any(digits):
            sign, digits, exponent = 0, [0], 0
        return {"decimal_tuple": [sign, digits, exponent]}
    if type(value) in (tuple, list):
        return [_project(item) for item in value]
    if type(value) is dict:
        return {key: _project(item) for key, item in value.items()}
    if value is None or type(value) in (str, int, bool):
        return value
    raise YahooCurrentQuoteError("Unsupported identity value")


def _identity(domain, value):
    raw = json.dumps(_project((QUALIFICATION_VERSION, domain, value)), sort_keys=True,
                     separators=(",", ":"), ensure_ascii=True,
                     allow_nan=False).encode("ascii")
    return hashlib.sha256(raw).hexdigest()


def _unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise YahooCurrentQuoteError("Duplicate JSON key")
        result[key] = value
    return result


def _reject_constant(value):
    raise YahooCurrentQuoteError("Nonfinite JSON constant")


def _utc_epoch(value):
    if type(value) is not int:
        return None
    try:
        parsed = datetime.fromtimestamp(value, timezone.utc)
    except (ValueError, OverflowError, OSError):
        return None
    return parsed.isoformat().replace("+00:00", "Z")


def _meta_hash(meta):
    raw = json.dumps(_project(meta), sort_keys=True, separators=(",", ":"),
                     ensure_ascii=True, allow_nan=False).encode("ascii")
    return hashlib.sha256(raw).hexdigest()


def _empty_extraction(receipt, status, *reasons):
    return YahooCurrentQuoteExtraction(
        EXTRACTION_VERSION, receipt, status,
        tuple(sorted(set(reasons), key=lambda item: item.value)),
        None, None, None, None, None, None, None, None, None, None, None,
        "/chart/result/0/meta", None,
    )


def _route_profile():
    profile = get_source_route(YAHOO_FINANCE_CHART_CURRENT_QUOTE_V1)
    if (
        profile.required_acquisition_contract != LIVE_ACQUISITION_CONTRACT_VERSION
        or profile.required_capture_contract != RECEIPT_SCHEMA_VERSION
        or profile.required_extraction_contract != EXTRACTION_VERSION
        or profile.required_resolution_contract != QUALIFICATION_VERSION
        or profile.required_resolver_version != VENUE_PROFILE_VERSION
    ):
        raise YahooCurrentQuoteError("Yahoo route contract pin mismatch")
    return profile


def extract_yahoo_current_quote(
    quote_archive: YahooQuoteArchive, receipt_id: str,
) -> YahooCurrentQuoteExtraction:
    """Replay one exact receipt; no latest selection or fallback field exists."""
    if type(quote_archive) is not YahooQuoteArchive:
        raise YahooCurrentQuoteError("Exact YahooQuoteArchive required")
    try:
        receipt = quote_archive.read_receipt(receipt_id)
        raw = quote_archive.read_object(receipt)
    except YahooQuoteArchiveError as exc:
        raise YahooCurrentQuoteError("Quote archive integrity failure") from exc
    try:
        document = json.loads(
            raw.decode("utf-8", "strict"), object_pairs_hook=_unique_pairs,
            parse_float=Decimal, parse_int=int, parse_constant=_reject_constant,
        )
    except (UnicodeError, ValueError, TypeError, RecursionError, YahooCurrentQuoteError):
        return _empty_extraction(
            receipt, QuoteExtractionStatus.QUOTE_UNAVAILABLE,
            CurrentQuoteReason.QUOTE_SOURCE_UNAVAILABLE,
        )
    if type(document) is not dict or type(document.get("chart")) is not dict:
        return _empty_extraction(
            receipt, QuoteExtractionStatus.QUOTE_UNAVAILABLE,
            CurrentQuoteReason.QUOTE_SOURCE_UNAVAILABLE,
        )
    chart = document["chart"]
    if "error" not in chart or chart["error"] is not None:
        return _empty_extraction(
            receipt, QuoteExtractionStatus.QUOTE_UNAVAILABLE,
            CurrentQuoteReason.QUOTE_SOURCE_UNAVAILABLE,
        )
    result = chart.get("result")
    if type(result) is not list or len(result) != 1 or type(result[0]) is not dict:
        status = (QuoteExtractionStatus.SOURCE_CONFLICT
                  if type(result) is list and len(result) > 1
                  else QuoteExtractionStatus.QUOTE_UNAVAILABLE)
        reason = (CurrentQuoteReason.SOURCE_CONFLICT
                  if status is QuoteExtractionStatus.SOURCE_CONFLICT
                  else CurrentQuoteReason.QUOTE_SOURCE_UNAVAILABLE)
        return _empty_extraction(receipt, status, reason)
    meta = result[0].get("meta")
    if type(meta) is not dict:
        return _empty_extraction(
            receipt, QuoteExtractionStatus.QUOTE_UNAVAILABLE,
            CurrentQuoteReason.QUOTE_SOURCE_UNAVAILABLE,
        )

    returned_symbol = meta.get("symbol") if type(meta.get("symbol")) is str else None
    currency = meta.get("currency") if type(meta.get("currency")) is str else None
    instrument_type = (meta.get("instrumentType")
                       if type(meta.get("instrumentType")) is str else None)
    exchange_name = meta.get("exchangeName") if type(meta.get("exchangeName")) is str else None
    full_exchange_name = (meta.get("fullExchangeName")
                          if type(meta.get("fullExchangeName")) is str else None)
    raw_price = meta.get("regularMarketPrice")
    price = None
    price_text = None
    if type(raw_price) in (int, Decimal):
        candidate = Decimal(raw_price)
        if candidate.is_finite() and candidate > 0:
            price = candidate
            price_text = str(raw_price)
    epoch = meta.get("regularMarketTime")
    provider_timestamp = _utc_epoch(epoch)

    reasons = set()
    if returned_symbol != receipt.requested_symbol:
        reasons.add(CurrentQuoteReason.SYMBOL_MISMATCH)
    if instrument_type != "EQUITY":
        reasons.add(CurrentQuoteReason.INSTRUMENT_TYPE_UNSUPPORTED)
    if (exchange_name, full_exchange_name) != REVIEWED_YAHOO_VENUE:
        reasons.add(CurrentQuoteReason.VENUE_MISMATCH)
    if currency != "USD":
        reasons.add(CurrentQuoteReason.CURRENCY_MISMATCH)
    if price is None:
        reasons.add(CurrentQuoteReason.PRICE_INVALID)
    if provider_timestamp is None:
        reasons.add(CurrentQuoteReason.PROVIDER_TIMESTAMP_INVALID)

    conflict = CurrentQuoteReason.SYMBOL_MISMATCH in reasons
    unsupported = bool(reasons & {
        CurrentQuoteReason.INSTRUMENT_TYPE_UNSUPPORTED,
        CurrentQuoteReason.VENUE_MISMATCH,
        CurrentQuoteReason.CURRENCY_MISMATCH,
    })
    unavailable = bool(reasons & {
        CurrentQuoteReason.PRICE_INVALID,
        CurrentQuoteReason.PROVIDER_TIMESTAMP_INVALID,
    })
    if unsupported:
        reasons.add(CurrentQuoteReason.QUOTE_SOURCE_UNSUPPORTED)
    if unavailable:
        reasons.add(CurrentQuoteReason.QUOTE_SOURCE_UNAVAILABLE)
    if conflict:
        status = QuoteExtractionStatus.SOURCE_CONFLICT
    elif unsupported:
        status = QuoteExtractionStatus.QUOTE_UNSUPPORTED
    elif unavailable:
        status = QuoteExtractionStatus.QUOTE_UNAVAILABLE
    else:
        status = QuoteExtractionStatus.QUOTE_EXTRACTED
    venue_id = REVIEWED_VENUE_ID if (exchange_name, full_exchange_name) == REVIEWED_YAHOO_VENUE else None
    return YahooCurrentQuoteExtraction(
        EXTRACTION_VERSION, receipt, status,
        tuple(sorted(reasons, key=lambda item: item.value)),
        returned_symbol, exchange_name, full_exchange_name, venue_id,
        instrument_type, currency, price, price_text,
        PRICE_UNIT if instrument_type == "EQUITY" else None,
        epoch if type(epoch) is int else None, provider_timestamp,
        "/chart/result/0/meta", _meta_hash(meta),
    )


def qualify_yahoo_current_quote(
    quote_archive: YahooQuoteArchive,
    current_archive: SecArchive,
    submissions_archive: SecSubmissionsArchive,
    filing_archive: SecFilingArchive,
    ticker_exchange_archive: SecTickerExchangeArchive,
    nasdaq_listed_archive: NasdaqListedArchive,
    request: YahooCurrentQuoteQualificationRequest,
) -> QualifiedCurrentQuote:
    """Freshly replay PR5B and one exact Yahoo receipt, then join by symbol."""
    if (type(quote_archive) is not YahooQuoteArchive
            or type(current_archive) is not SecArchive
            or type(submissions_archive) is not SecSubmissionsArchive
            or type(filing_archive) is not SecFilingArchive
            or type(ticker_exchange_archive) is not SecTickerExchangeArchive
            or type(nasdaq_listed_archive) is not NasdaqListedArchive
            or type(request) is not YahooCurrentQuoteQualificationRequest):
        raise YahooCurrentQuoteError("Exact typed archives/request required")
    security = qualify_sec_current_security_eps(
        current_archive, submissions_archive, filing_archive,
        ticker_exchange_archive, nasdaq_listed_archive, request.security_request,
    )
    quote = extract_yahoo_current_quote(quote_archive, request.quote_receipt_id)
    reasons = set(quote.reasons)
    if security.status is not QualificationStatus.CURRENT_SECURITY_EPS_QUALIFICATION_ESTABLISHED:
        reasons.add(CurrentQuoteReason.PR5B_NOT_ESTABLISHED)
    if (security.semantic_id != request.expected_security_semantic_id
            or security.evidence_id != request.expected_security_evidence_id
            or quote.semantic_id != request.expected_quote_semantic_id
            or quote.evidence_id != request.expected_quote_evidence_id):
        reasons.add(CurrentQuoteReason.SOURCE_CONFLICT)
    if (security.status is QualificationStatus.CURRENT_SECURITY_EPS_QUALIFICATION_ESTABLISHED
            and security.direct_listing.source_symbol != quote.returned_symbol):
        reasons.add(CurrentQuoteReason.SYMBOL_MISMATCH)
    try:
        provider_time = (None if quote.provider_market_timestamp is None else
                         datetime.fromisoformat(quote.provider_market_timestamp.replace("Z", "+00:00")))
        capture_time = datetime.fromisoformat(quote.receipt.captured_at.replace("Z", "+00:00"))
    except ValueError:
        provider_time = None
        capture_time = None
        reasons.add(CurrentQuoteReason.PROVIDER_TIMESTAMP_INVALID)
    if provider_time is not None and capture_time is not None and provider_time > capture_time:
        reasons.add(CurrentQuoteReason.QUOTE_AFTER_CAPTURE)

    if reasons & {
        CurrentQuoteReason.SOURCE_CONFLICT,
        CurrentQuoteReason.SYMBOL_MISMATCH,
        CurrentQuoteReason.QUOTE_AFTER_CAPTURE,
    }:
        status = CurrentQuoteStatus.SOURCE_CONFLICT
    elif reasons & {
        CurrentQuoteReason.QUOTE_SOURCE_UNSUPPORTED,
        CurrentQuoteReason.VENUE_MISMATCH,
        CurrentQuoteReason.INSTRUMENT_TYPE_UNSUPPORTED,
        CurrentQuoteReason.CURRENCY_MISMATCH,
    }:
        status = CurrentQuoteStatus.QUOTE_UNSUPPORTED
    elif reasons:
        status = CurrentQuoteStatus.QUOTE_UNAVAILABLE
    else:
        status = CurrentQuoteStatus.CURRENT_QUOTE_ESTABLISHED

    positive = status is CurrentQuoteStatus.CURRENT_QUOTE_ESTABLISHED
    profile = _route_profile()
    limitations = tuple(sorted(CurrentQuoteLimitation, key=lambda item: item.value))
    return QualifiedCurrentQuote(
        QUALIFICATION_VERSION,
        profile.route_id,
        profile.profile_hash,
        profile.factual_hash,
        profile.license_status.value,
        profile.use_status.value,
        status,
        tuple(sorted(reasons, key=lambda item: item.value)),
        quote.price if positive else None,
        quote.currency if positive else None,
        quote.price_unit if positive else None,
        quote.returned_symbol if positive else None,
        quote.reviewed_venue_id if positive else None,
        quote.instrument_type if positive else None,
        quote.provider_market_epoch if positive else None,
        quote.provider_market_timestamp if positive else None,
        quote.receipt.captured_at,
        security.route_local_issuer_key if positive else None,
        security.route_local_security_key if positive else None,
        security,
        quote,
        limitations,
    )
