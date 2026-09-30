"""Strict extraction for exact Yahoo Chart split events."""
from dataclasses import dataclass, fields, is_dataclass
from datetime import datetime, timezone
from enum import Enum, StrEnum
import hashlib
import json
import math
import re

from .yahoo_split_history_archive import (
    YahooSplitHistoryArchive,
    YahooSplitHistoryArchiveError,
    YahooSplitHistoryReceipt,
)

EXTRACTION_VERSION = "2026-09-29-yahoo-split-history-extraction-v1"
ROUTE_ID = "YAHOO_FINANCE_CHART_SPLIT_HISTORY_V1"
LICENSE_STATUS = "UNKNOWN"
USE_STATUS = "REVIEW_REQUIRED"
_HASH = re.compile(r"[0-9a-f]{64}")
_RATIO = re.compile(r"([1-9][0-9]*):([1-9][0-9]*)")


class YahooSplitHistoryError(ValueError):
    """Malformed caller request or archive integrity failure."""


class SplitHistoryStatus(StrEnum):
    SPLIT_HISTORY_EXTRACTED = "SPLIT_HISTORY_EXTRACTED"
    SPLIT_HISTORY_UNAVAILABLE = "SPLIT_HISTORY_UNAVAILABLE"
    SPLIT_HISTORY_UNSUPPORTED = "SPLIT_HISTORY_UNSUPPORTED"
    SOURCE_CONFLICT = "SOURCE_CONFLICT"


class SplitHistoryReason(StrEnum):
    SOURCE_UNAVAILABLE = "SOURCE_UNAVAILABLE"
    SOURCE_UNSUPPORTED = "SOURCE_UNSUPPORTED"
    SOURCE_CONFLICT = "SOURCE_CONFLICT"
    SYMBOL_MISMATCH = "SYMBOL_MISMATCH"
    MALFORMED_EVENT = "MALFORMED_EVENT"
    INVALID_RATIO = "INVALID_RATIO"
    RATIO_REPRESENTATION_CONFLICT = "RATIO_REPRESENTATION_CONFLICT"
    INVALID_EVENT_DATE = "INVALID_EVENT_DATE"
    EVENT_OUTSIDE_REQUESTED_INTERVAL = "EVENT_OUTSIDE_REQUESTED_INTERVAL"
    DUPLICATE_CONFLICTING_EVENT = "DUPLICATE_CONFLICTING_EVENT"


@dataclass(frozen=True, slots=True)
class YahooSplitEvent:
    symbol: str
    event_epoch: int
    event_timestamp: str
    split_ratio_source: str
    numerator: int
    denominator: int
    source_locator: str
    response_hash: str
    receipt_id: str

    @property
    def semantic_id(self):
        return _identity("split-event-semantics", {
            "symbol": self.symbol,
            "event_epoch": self.event_epoch,
            "event_timestamp": self.event_timestamp,
            "split_ratio_source": self.split_ratio_source,
            "numerator": self.numerator,
            "denominator": self.denominator,
        })

    @property
    def evidence_id(self):
        return _identity("split-event-evidence", {
            "semantic_id": self.semantic_id,
            "source_locator": self.source_locator,
            "response_hash": self.response_hash,
            "receipt_id": self.receipt_id,
        })


@dataclass(frozen=True, slots=True)
class YahooSplitHistoryExtraction:
    extraction_version: str
    route_id: str
    license_status: str
    use_status: str
    receipt: YahooSplitHistoryReceipt
    status: SplitHistoryStatus
    reasons: tuple[SplitHistoryReason, ...]
    returned_symbol: str | None
    events: tuple[YahooSplitEvent, ...]
    response_structure_locator: str

    @property
    def semantic_id(self):
        return _identity("split-history-semantics", {
            "version": self.extraction_version,
            "route": self.route_id,
            "requested_symbol": self.receipt.requested_symbol,
            "requested_start_epoch": self.receipt.requested_start_epoch,
            "requested_end_epoch": self.receipt.requested_end_epoch,
            "status": self.status,
            "reasons": self.reasons,
            "returned_symbol": self.returned_symbol,
            "events": [item.semantic_id for item in self.events],
        })

    @property
    def evidence_id(self):
        return _identity("split-history-evidence", {
            "semantic_id": self.semantic_id,
            "receipt_id": self.receipt.receipt_id,
            "response_hash": self.receipt.content_sha256,
            "captured_at": self.receipt.captured_at,
            "events": [item.evidence_id for item in self.events],
        })


def _project(value):
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value):
        return {field.name: _project(getattr(value, field.name)) for field in fields(value)}
    if type(value) in (tuple, list):
        return [_project(item) for item in value]
    if type(value) is dict:
        return {key: _project(item) for key, item in value.items()}
    if value is None or type(value) in (str, int, bool):
        return value
    raise YahooSplitHistoryError("Unsupported identity value")


def _identity(domain, value):
    raw = json.dumps(_project((EXTRACTION_VERSION, domain, value)), sort_keys=True,
                     separators=(",", ":"), ensure_ascii=True,
                     allow_nan=False).encode("ascii")
    return hashlib.sha256(raw).hexdigest()


def _unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise YahooSplitHistoryError("Duplicate JSON key")
        result[key] = value
    return result


def _reject_constant(value):
    raise YahooSplitHistoryError("Nonfinite JSON constant")


def _utc_epoch(value):
    if type(value) is not int:
        return None
    try:
        return datetime.fromtimestamp(value, timezone.utc).isoformat().replace("+00:00", "Z")
    except (ValueError, OverflowError, OSError):
        return None


def _integer_term(value):
    if type(value) is int and not isinstance(value, bool):
        return value if value > 0 else None
    if type(value) is float and math.isfinite(value) and value.is_integer():
        return int(value) if value > 0 else None
    return None


def _empty(receipt, status, reasons, symbol=None):
    return YahooSplitHistoryExtraction(
        EXTRACTION_VERSION, ROUTE_ID, LICENSE_STATUS, USE_STATUS, receipt,
        status, tuple(sorted(set(reasons), key=lambda item: item.value)),
        symbol, (), "/chart/result/0/events/splits",
    )


def extract_yahoo_split_history(
    archive: YahooSplitHistoryArchive, receipt_id: str,
) -> YahooSplitHistoryExtraction:
    """Replay one exact explicit-period split response."""
    if type(archive) is not YahooSplitHistoryArchive:
        raise YahooSplitHistoryError("Exact YahooSplitHistoryArchive required")
    try:
        receipt = archive.read_receipt(receipt_id)
        raw = archive.read_object(receipt)
    except YahooSplitHistoryArchiveError as exc:
        raise YahooSplitHistoryError("Split-history archive integrity failure") from exc
    try:
        document = json.loads(
            raw.decode("utf-8", "strict"), object_pairs_hook=_unique_pairs,
            parse_int=int, parse_float=float, parse_constant=_reject_constant,
        )
    except (UnicodeError, ValueError, TypeError, RecursionError, YahooSplitHistoryError):
        return _empty(receipt, SplitHistoryStatus.SPLIT_HISTORY_UNAVAILABLE,
                      (SplitHistoryReason.SOURCE_UNAVAILABLE,))
    chart = document.get("chart") if type(document) is dict else None
    if type(chart) is not dict or chart.get("error", object()) is not None:
        return _empty(receipt, SplitHistoryStatus.SPLIT_HISTORY_UNAVAILABLE,
                      (SplitHistoryReason.SOURCE_UNAVAILABLE,))
    result = chart.get("result")
    if type(result) is not list or len(result) != 1 or type(result[0]) is not dict:
        status = (SplitHistoryStatus.SOURCE_CONFLICT
                  if type(result) is list and len(result) > 1
                  else SplitHistoryStatus.SPLIT_HISTORY_UNAVAILABLE)
        reason = (SplitHistoryReason.SOURCE_CONFLICT
                  if status is SplitHistoryStatus.SOURCE_CONFLICT
                  else SplitHistoryReason.SOURCE_UNAVAILABLE)
        return _empty(receipt, status, (reason,))
    payload = result[0]
    meta = payload.get("meta")
    symbol = meta.get("symbol") if type(meta) is dict and type(meta.get("symbol")) is str else None
    if symbol != receipt.requested_symbol:
        return _empty(receipt, SplitHistoryStatus.SOURCE_CONFLICT,
                      (SplitHistoryReason.SYMBOL_MISMATCH,), symbol)
    events_container = payload.get("events", {})
    if events_container is None:
        events_container = {}
    if type(events_container) is not dict:
        return _empty(receipt, SplitHistoryStatus.SPLIT_HISTORY_UNAVAILABLE,
                      (SplitHistoryReason.SOURCE_UNAVAILABLE,), symbol)
    unexpected = set(events_container) - {"splits"}
    if unexpected:
        return _empty(receipt, SplitHistoryStatus.SPLIT_HISTORY_UNSUPPORTED,
                      (SplitHistoryReason.SOURCE_UNSUPPORTED,), symbol)
    splits = events_container.get("splits", {})
    if splits is None:
        splits = {}
    if type(splits) is not dict:
        return _empty(receipt, SplitHistoryStatus.SPLIT_HISTORY_UNAVAILABLE,
                      (SplitHistoryReason.SOURCE_UNAVAILABLE,), symbol)

    reasons = set()
    parsed = []
    for key, event in sorted(splits.items()):
        locator = "/chart/result/0/events/splits/" + str(key).replace("~", "~0").replace("/", "~1")
        if type(key) is not str or re.fullmatch(r"[0-9]{1,20}", key) is None or type(event) is not dict:
            reasons.add(SplitHistoryReason.MALFORMED_EVENT)
            continue
        epoch = event.get("date")
        timestamp = _utc_epoch(epoch)
        if timestamp is None or str(epoch) != key:
            reasons.add(SplitHistoryReason.INVALID_EVENT_DATE)
            continue
        if not (receipt.requested_start_epoch <= epoch < receipt.requested_end_epoch):
            reasons.add(SplitHistoryReason.EVENT_OUTSIDE_REQUESTED_INTERVAL)
            continue
        source_ratio = event.get("splitRatio")
        numerator = _integer_term(event.get("numerator"))
        denominator = _integer_term(event.get("denominator"))
        match = _RATIO.fullmatch(source_ratio) if type(source_ratio) is str else None
        if numerator is None or denominator is None or match is None:
            reasons.add(SplitHistoryReason.INVALID_RATIO)
            continue
        if (int(match.group(1)), int(match.group(2))) != (numerator, denominator):
            reasons.add(SplitHistoryReason.RATIO_REPRESENTATION_CONFLICT)
            continue
        parsed.append(YahooSplitEvent(
            symbol, epoch, timestamp, source_ratio, numerator, denominator,
            locator, receipt.content_sha256, receipt.receipt_id,
        ))
    by_epoch = {}
    for event in parsed:
        by_epoch.setdefault(event.event_epoch, set()).add(
            (event.numerator, event.denominator, event.split_ratio_source))
    if any(len(values) > 1 for values in by_epoch.values()):
        reasons.add(SplitHistoryReason.DUPLICATE_CONFLICTING_EVENT)
    if reasons:
        conflict_reasons = {
            SplitHistoryReason.RATIO_REPRESENTATION_CONFLICT,
            SplitHistoryReason.DUPLICATE_CONFLICTING_EVENT,
        }
        status = (SplitHistoryStatus.SOURCE_CONFLICT if reasons & conflict_reasons
                  else SplitHistoryStatus.SPLIT_HISTORY_UNSUPPORTED)
        return _empty(receipt, status, reasons, symbol)
    events = tuple(sorted(parsed, key=lambda item: (
        item.event_epoch, item.numerator, item.denominator, item.source_locator)))
    return YahooSplitHistoryExtraction(
        EXTRACTION_VERSION, ROUTE_ID, LICENSE_STATUS, USE_STATUS, receipt,
        SplitHistoryStatus.SPLIT_HISTORY_EXTRACTED, (), symbol, events,
        "/chart/result/0/events/splits",
    )
