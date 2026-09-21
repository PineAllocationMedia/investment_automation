"""Offline structural replay of one captured directory; no identity qualification."""
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import datetime
from enum import StrEnum
import re
import unicodedata

from .nasdaq_listed_archive import (
    MAX_BODY_BYTES, NasdaqListedArchive, NasdaqListedArchiveError, NasdaqListedReceipt,
    canonical_json, digest, validate_receipt_id,
)

SNAPSHOT_CONTRACT_VERSION = "2026-09-21-nasdaq-listed-snapshot-v1"
MAX_ROWS = 100_000
MAX_COLUMNS = 64
MAX_FIELD_LENGTH = 4096
MAX_CELLS = 1_000_000
CORE_COLUMNS = ("Symbol", "Security Name", "Market Category", "Test Issue",
                "Financial Status", "Round Lot Size")
# These are source codes, not investment classifications or recommendations.
MARKET_CATEGORIES = frozenset(("Q", "G", "S"))
FINANCIAL_STATUSES = frozenset(("D", "E", "Q", "N", "G", "H", "J", "K"))


class UnsupportedNasdaqListedStructure(ValueError):
    """Unsupported source variant or exceeded PAM safety bound; no partial success."""


class SnapshotRequestError(ValueError):
    """Invalid explicit receipt selection."""


class SnapshotStatus(StrEnum):
    CAPTURED_NASDAQ_LISTED_SNAPSHOT = "CAPTURED_NASDAQ_LISTED_SNAPSHOT"
    SOURCE_CONFLICT = "SOURCE_CONFLICT"


def _require(condition, message):
    if not condition:
        raise UnsupportedNasdaqListedStructure(message)


def _identity(domain, value):
    return digest(("pam:nasdaq-listed:" + domain + ":v1\0").encode("ascii") + canonical_json(value))


@dataclass(frozen=True, slots=True)
class SourceCreationTime:
    """Minute precision, timezone unspecified by source; never a UTC timestamp."""
    text: str
    year: int
    month: int
    day: int
    hour: int
    minute: int


@dataclass(frozen=True, slots=True)
class _ParsedSnapshot:
    header: tuple[str, ...]
    rows: tuple[tuple[str, ...], ...]
    footer: str
    source_creation_time: SourceCreationTime


def _parse_snapshot(raw):
    """One contract for acquisition preflight and offline replay.

    Raw bytes remain unchanged. Extra columns (including ETF/NextShares) are
    uninterpreted strings. No economic instrument filter or identifier join.
    """
    _require(type(raw) is bytes and 0 < len(raw) <= MAX_BODY_BYTES, "Invalid source byte count")
    try:
        text = raw.decode("utf-8")
    except UnicodeError:
        raise UnsupportedNasdaqListedStructure("Unsupported source encoding") from None
    # Uniform LF or CRLF only. Forbid bare CR and mixed styles, including footer.
    if "\r" in text:
        _require(text.count("\n") == text.count("\r\n") == text.count("\r"),
                 "Ambiguous line endings")
        text = text.replace("\r\n", "\n")
    _require(all(c == "\n" or unicodedata.category(c) not in {"Cc", "Cf", "Cs", "Zl", "Zp"}
                 for c in text), "Unsupported control character")
    text = text.rstrip("\n")  # Only empty terminal lines, never field whitespace.
    _require(text.count("\n") <= MAX_ROWS + 1, "Row safety bound exceeded")
    lines = text.split("\n")
    _require(len(lines) >= 2 and all(lines), "Header and final footer required")
    _require(lines[0].count("|") < MAX_COLUMNS, "Column safety bound exceeded")
    header = tuple(lines[0].split("|"))
    _require(all(re.fullmatch(r"[A-Za-z][A-Za-z0-9 _-]{0,63}", name) and name == name.strip()
                 for name in header), "Unsupported column name")
    _require(len(set(header)) == len(header), "Duplicate column name")
    _require(set(CORE_COLUMNS) <= set(header), "Missing core column")
    count = len(lines) - 2
    _require(count <= MAX_ROWS and count * len(header) <= MAX_CELLS, "Row/cell safety bound exceeded")
    footer = lines[-1]
    # Official example and observed resource use mmddyyyyhh:mm, not seconds.
    match = re.fullmatch(r"File Creation Time: ([0-9]{2})([0-9]{2})([0-9]{4})([0-9]{2}):([0-9]{2})"
                         + re.escape("|" * (len(header) - 1)), footer)
    _require(match is not None, "Unsupported final footer")
    month, day, year, hour, minute = map(int, match.groups())
    try:
        datetime(year, month, day, hour, minute)  # Calendar validation only; no timezone conversion.
    except ValueError:
        raise UnsupportedNasdaqListedStructure("Invalid source creation time") from None
    creation = SourceCreationTime(footer.split("|", 1)[0], year, month, day, hour, minute)
    rows = []
    for line in lines[1:-1]:
        _require(line.count("|") == len(header) - 1, "Row field-count mismatch")
        values = tuple(line.split("|"))
        _require(all(len(value) <= MAX_FIELD_LENGTH for value in values), "Field safety bound exceeded")
        fields = dict(zip(header, values))
        # Structural token only: includes suffixes/dotted test symbols, without
        # imposing common-stock ticker length or establishing symbol identity.
        _require(re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9.$^_/-]{0,31}", fields["Symbol"]),
                 "Unsupported symbol structure")
        _require(bool(fields["Security Name"].strip()), "Empty security name")
        _require(fields["Market Category"] in MARKET_CATEGORIES, "Unsupported market category")
        _require(fields["Test Issue"] in {"Y", "N"}, "Unsupported test-issue value")
        _require(fields["Financial Status"] in FINANCIAL_STATUSES, "Unsupported financial status")
        _require(re.fullmatch(r"[0-9]{1,9}", fields["Round Lot Size"]) and
                 int(fields["Round Lot Size"]) > 0, "Unsupported round lot size")
        rows.append(values)
    return _ParsedSnapshot(header, tuple(rows), footer, creation)


@dataclass(frozen=True, slots=True)
class NasdaqListedSnapshotRequest:
    receipt_id: str

    def __post_init__(self):
        try:
            validate_receipt_id(self.receipt_id)
        except NasdaqListedArchiveError:
            raise SnapshotRequestError("Invalid receipt selector") from None


@dataclass(frozen=True, slots=True)
class NasdaqListedRow:
    receipt_id: str
    resource: str
    position: int  # Zero-based data-row position.
    source_line: int  # One-based file line; header is line 1.
    fields: tuple[tuple[str, str], ...]

    @property
    def semantic_id(self):
        return _identity("row", self.fields)

    @property
    def occurrence_id(self):
        return _identity("occurrence", asdict(self))


@dataclass(frozen=True, slots=True)
class NasdaqListedSnapshotAssessment:
    contract_version: str
    status: SnapshotStatus
    receipt: NasdaqListedReceipt
    source_creation_time: SourceCreationTime
    footer: str
    header: tuple[str, ...]
    rows: tuple[NasdaqListedRow, ...]
    conflicting_symbols: tuple[str, ...]

    @property
    def row_count(self):
        return len(self.rows)

    @property
    def semantic_id(self):
        return _identity("snapshot-semantics", {
            "contract": self.contract_version, "status": self.status,
            "header": self.header, "footer": self.footer,
            "creation": asdict(self.source_creation_time),
            "rows": [row.semantic_id for row in self.rows], "conflicts": self.conflicting_symbols,
        })

    @property
    def evidence_id(self):
        return _identity("snapshot-evidence", {
            "semantic_id": self.semantic_id, "receipt": self.receipt.receipt_id,
            "rows": [row.occurrence_id for row in self.rows],
        })


def replay_nasdaq_listed_snapshot(archive: NasdaqListedArchive,
                                  request: NasdaqListedSnapshotRequest) -> NasdaqListedSnapshotAssessment:
    """Verify one explicit stored receipt and bytes, without network, writes or clock.

    Unsafe/missing/corrupt storage raises NasdaqListedArchiveError. Unsupported
    source shapes raise UnsupportedNasdaqListedStructure. Duplicates retain all
    rows and return SOURCE_CONFLICT, even when the duplicated values agree.
    """
    if type(archive) is not NasdaqListedArchive or type(request) is not NasdaqListedSnapshotRequest:
        raise SnapshotRequestError("Typed archive/request required")
    receipt = archive.read_receipt(request.receipt_id)
    source = _parse_snapshot(archive.read_object(receipt))
    rows = tuple(NasdaqListedRow(receipt.receipt_id, receipt.endpoint, index, index + 2,
                                tuple(zip(source.header, values)))
                 for index, values in enumerate(source.rows))
    counts = Counter(dict(row.fields)["Symbol"] for row in rows)
    conflicts = tuple(sorted(symbol for symbol, count in counts.items() if count > 1))
    status = SnapshotStatus.SOURCE_CONFLICT if conflicts else SnapshotStatus.CAPTURED_NASDAQ_LISTED_SNAPSHOT
    return NasdaqListedSnapshotAssessment(SNAPSHOT_CONTRACT_VERSION, status, receipt,
                                           source.source_creation_time, source.footer,
                                           source.header, rows, conflicts)
