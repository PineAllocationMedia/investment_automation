"""Offline replay of one SEC CIK/ticker/exchange association snapshot.

Rows remain source claims.  CIK is an SEC identifier, ticker is a source value,
and exchange text is not a MIC, currency, listing qualification, or identity.
"""
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from enum import StrEnum
import json
import re
import unicodedata

from .sec_ticker_exchange_archive import (
    MAX_BODY_BYTES, SecTickerExchangeArchive, SecTickerExchangeArchiveError,
    SecTickerExchangeReceipt, canonical_json, digest, reject_constant,
    unique_pairs, validate_receipt_id,
)

SNAPSHOT_CONTRACT_VERSION = "2026-09-26-sec-ticker-exchange-snapshot-v1"
FIELDS = ("cik", "name", "ticker", "exchange")
MAX_ROWS = 100_000
MAX_NAME_LENGTH = 4096
MAX_TICKER_LENGTH = 128
MAX_EXCHANGE_LENGTH = 512
MAX_JSON_DEPTH = 4


class UnsupportedSecTickerExchangeStructure(ValueError):
    """Unsupported source variant or exceeded safety bound; no partial replay."""


class SecTickerExchangeSnapshotRequestError(ValueError):
    """Invalid explicit receipt selection."""


class SecTickerExchangeSnapshotStatus(StrEnum):
    CAPTURED_SEC_TICKER_EXCHANGE_SNAPSHOT = "CAPTURED_SEC_TICKER_EXCHANGE_SNAPSHOT"
    SOURCE_AMBIGUITY = "SOURCE_AMBIGUITY"


def _require(condition, message):
    if not condition:
        raise UnsupportedSecTickerExchangeStructure(message)


def _identity(domain, value):
    return digest(("pam:sec-ticker-exchange:" + domain + ":v1\0").encode("ascii") +
                  canonical_json(value))


def _safe_text(value, maximum, *, token=False):
    _require(type(value) is str and 0 < len(value) <= maximum and bool(value.strip()),
             "Invalid source string")
    _require(not any(0xD800 <= ord(c) <= 0xDFFF for c in value),
             "Unsupported source surrogate")
    if token:
        _require(not any(c.isspace() or unicodedata.category(c) in
                         {"Cc", "Cf", "Cs", "Zl", "Zp"} for c in value),
                 "Ticker must be a source token")


@dataclass(frozen=True, slots=True)
class _ParsedSnapshot:
    rows: tuple[tuple[int, str, str, str], ...]


def _parse_snapshot(raw):
    """Validate only the reviewed exact top-level and four-cell row shape."""
    _require(type(raw) is bytes and 0 < len(raw) <= MAX_BODY_BYTES, "Invalid source byte count")
    depth = 0
    quoted = escaped = False
    for byte in raw:
        if quoted:
            if escaped:
                escaped = False
            elif byte == 92:
                escaped = True
            elif byte == 34:
                quoted = False
        elif byte == 34:
            quoted = True
        elif byte in (91, 123):
            depth += 1
            _require(depth <= MAX_JSON_DEPTH, "JSON nesting bound exceeded")
        elif byte in (93, 125):
            depth -= 1
    try:
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=unique_pairs,
                           parse_constant=reject_constant)
        _require(type(value) is dict and set(value) == {"fields", "data"},
                 "Exact top-level keys required")
        _require(type(value["fields"]) is list and tuple(value["fields"]) == FIELDS,
                 "Exact field vector required")
        data = value["data"]
        _require(type(data) is list and len(data) <= MAX_ROWS, "Invalid row collection")
        rows = []
        for source_row in data:
            _require(type(source_row) is list and len(source_row) == 4,
                     "Every source row must have four cells")
            cik, name, ticker, exchange = source_row
            _require(type(cik) is int and 0 < cik <= 9_999_999_999,
                     "CIK must be a positive SEC integer")
            _safe_text(name, MAX_NAME_LENGTH)
            _safe_text(ticker, MAX_TICKER_LENGTH, token=True)
            _safe_text(exchange, MAX_EXCHANGE_LENGTH)
            rows.append((cik, name, ticker, exchange))
        return _ParsedSnapshot(tuple(rows))
    except (SecTickerExchangeArchiveError, TypeError, UnicodeError, ValueError,
            RecursionError, OverflowError):
        raise UnsupportedSecTickerExchangeStructure("Unsupported SEC association structure") from None


@dataclass(frozen=True, slots=True)
class SecTickerExchangeSnapshotRequest:
    receipt_id: str

    def __post_init__(self):
        try:
            validate_receipt_id(self.receipt_id)
        except SecTickerExchangeArchiveError:
            raise SecTickerExchangeSnapshotRequestError("Invalid receipt selector") from None


@dataclass(frozen=True, slots=True)
class SecTickerExchangeRow:
    receipt_id: str
    position: int
    source_cik: int
    normalized_sec_cik: str
    source_company_name: str
    source_ticker: str
    source_exchange: str

    @property
    def semantic_id(self):
        return _identity("row", (self.source_cik, self.source_company_name,
                                 self.source_ticker, self.source_exchange))

    @property
    def occurrence_id(self):
        return _identity("occurrence", asdict(self))


@dataclass(frozen=True, slots=True)
class SecTickerExchangeSnapshotAssessment:
    contract_version: str
    status: SecTickerExchangeSnapshotStatus
    receipt: SecTickerExchangeReceipt
    rows: tuple[SecTickerExchangeRow, ...]
    duplicate_semantic_ids: tuple[str, ...]
    ambiguous_tickers: tuple[str, ...]

    @property
    def row_count(self):
        return len(self.rows)

    @property
    def semantic_id(self):
        # Exact duplicate multiplicity cannot strengthen association semantics;
        # every duplicate occurrence remains bound by evidence identity.
        return _identity("snapshot-semantics", {
            "contract": self.contract_version,
            "status": self.status,
            "rows": sorted({row.semantic_id for row in self.rows}),
            "duplicate_semantic_ids": self.duplicate_semantic_ids,
            "ambiguous_tickers": self.ambiguous_tickers,
        })

    @property
    def evidence_id(self):
        return _identity("snapshot-evidence", {
            "semantic_id": self.semantic_id,
            "receipt_id": self.receipt.receipt_id,
            "content_sha256": self.receipt.content_sha256,
            "captured_at": self.receipt.captured_at,
            "occurrences": [row.occurrence_id for row in self.rows],
        })


def replay_sec_ticker_exchange_snapshot(
    archive: SecTickerExchangeArchive,
    request: SecTickerExchangeSnapshotRequest,
) -> SecTickerExchangeSnapshotAssessment:
    """Replay one explicit receipt with no network, clock, write, or discovery."""
    if (type(archive) is not SecTickerExchangeArchive or
            type(request) is not SecTickerExchangeSnapshotRequest):
        raise SecTickerExchangeSnapshotRequestError("Typed archive/request required")
    receipt = archive.read_receipt(request.receipt_id)
    source = _parse_snapshot(archive.read_object(receipt))
    rows = tuple(SecTickerExchangeRow(
        receipt.receipt_id, position, cik, str(cik).zfill(10), name, ticker, exchange)
        for position, (cik, name, ticker, exchange) in enumerate(source.rows))
    semantic_counts = Counter(row.semantic_id for row in rows)
    duplicates = tuple(sorted(key for key, count in semantic_counts.items() if count > 1))
    ticker_ciks = defaultdict(set)
    for row in rows:
        ticker_ciks[row.source_ticker].add(row.source_cik)
    ambiguous_tickers = tuple(sorted(ticker for ticker, ciks in ticker_ciks.items()
                                     if len(ciks) > 1))
    status = (SecTickerExchangeSnapshotStatus.SOURCE_AMBIGUITY
              if duplicates or ambiguous_tickers else
              SecTickerExchangeSnapshotStatus.CAPTURED_SEC_TICKER_EXCHANGE_SNAPSHOT)
    return SecTickerExchangeSnapshotAssessment(
        SNAPSHOT_CONTRACT_VERSION, status, receipt, rows, duplicates, ambiguous_tickers)
