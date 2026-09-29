"""Immutable exact-byte Yahoo Chart quote evidence under local process trust.

The archive preserves one fixed request profile.  Receipts are integrity records,
not remotely signed credentials or commercial-use permissions.  Only the reviewed
acquisition path publishes LIVE bytes; tests may use the private fixture helper.
"""
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import stat
from urllib.parse import quote


RECEIPT_SCHEMA_VERSION = "2026-09-28-yahoo-quote-receipt-v1"
SOURCE_KIND = "YAHOO_FINANCE"
RESOURCE_KIND = "YAHOO_FINANCE_CHART_CURRENT_QUOTE"
ENDPOINT_ORIGIN = "https://query1.finance.yahoo.com"
ENDPOINT_PATH_PREFIX = "/v8/finance/chart/"
PARAMETER_PROFILE = "range=5d&interval=1d&events=div%2Csplits&includePrePost=false"
ENDPOINT_PROFILE_ID = "YAHOO_FINANCE_CHART_CURRENT_QUOTE_V1"
LIVE_ACQUISITION_CONTRACT_VERSION = "2026-09-28-yahoo-chart-current-quote-acquisition-v1"
MAX_BODY_BYTES = 2 * 1024 * 1024
_MAX_RECEIPT_BYTES = 8192
_RECEIPT_DOMAIN = b"pam:yahoo-quote-receipt:v1\0"
_HASH = re.compile(r"[0-9a-f]{64}")
_SYMBOL = re.compile(r"[A-Z][A-Z0-9.-]{0,14}", re.ASCII)
_TIME = re.compile(
    r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}"
    r"(?:\.[0-9]{1,6})?(?:Z|[+-][0-9]{2}:[0-9]{2})"
)


class YahooQuoteArchiveError(ValueError):
    """Invalid request/archive contract or corrupt immutable evidence."""


def require(condition, message):
    if not condition:
        raise YahooQuoteArchiveError(message)


def canonical_symbol(value):
    require(type(value) is str and _SYMBOL.fullmatch(value) is not None,
            "Canonical uppercase Yahoo symbol required")
    return value


def canonical_endpoint(symbol):
    symbol = canonical_symbol(symbol)
    return (ENDPOINT_ORIGIN + ENDPOINT_PATH_PREFIX + quote(symbol, safe=".-")
            + "?" + PARAMETER_PROFILE)


def canonical_timestamp(value):
    require(type(value) is str and _TIME.fullmatch(value) is not None,
            "Explicit-offset timestamp required")
    require(not value.endswith("-00:00"), "Unknown offset is not a capture time")
    if not value.endswith("Z"):
        require(int(value[-5:-3]) < 24 and int(value[-2:]) < 60, "Invalid offset")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    except (ValueError, OverflowError):
        raise YahooQuoteArchiveError("Invalid timestamp") from None


def digest(raw):
    require(type(raw) is bytes, "Exact bytes required")
    return hashlib.sha256(raw).hexdigest()


def canonical_json(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True, allow_nan=False).encode("ascii")


def _unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, "Duplicate JSON key")
        result[key] = value
    return result


def _reject_constant(value):
    raise YahooQuoteArchiveError("Nonfinite JSON constant")


@dataclass(frozen=True, slots=True)
class YahooQuoteReceipt:
    schema_version: str
    source_kind: str
    resource_kind: str
    requested_symbol: str
    endpoint: str
    endpoint_profile_id: str
    parameter_profile: str
    content_sha256: str
    byte_length: int
    captured_at: str
    acquisition_contract_version: str

    def __post_init__(self):
        require(self.schema_version == RECEIPT_SCHEMA_VERSION, "Unsupported receipt schema")
        require(self.source_kind == SOURCE_KIND, "Unsupported source kind")
        require(self.resource_kind == RESOURCE_KIND, "Unsupported resource kind")
        canonical_symbol(self.requested_symbol)
        require(self.endpoint == canonical_endpoint(self.requested_symbol), "Noncanonical endpoint")
        require(self.endpoint_profile_id == ENDPOINT_PROFILE_ID, "Unsupported endpoint profile")
        require(self.parameter_profile == PARAMETER_PROFILE, "Unsupported parameter profile")
        require(type(self.content_sha256) is str and _HASH.fullmatch(self.content_sha256),
                "Invalid object hash")
        require(type(self.byte_length) is int and 0 < self.byte_length <= MAX_BODY_BYTES,
                "Invalid byte length")
        object.__setattr__(self, "captured_at", canonical_timestamp(self.captured_at))
        require(self.acquisition_contract_version == LIVE_ACQUISITION_CONTRACT_VERSION,
                "Unsupported acquisition contract")

    @property
    def receipt_id(self):
        return digest(_RECEIPT_DOMAIN + canonical_json(asdict(self)))

    def to_bytes(self):
        return canonical_json({**asdict(self), "receipt_id": self.receipt_id})

    @classmethod
    def from_bytes(cls, raw):
        require(type(raw) is bytes and len(raw) <= _MAX_RECEIPT_BYTES, "Invalid receipt bytes")
        try:
            value = json.loads(raw, object_pairs_hook=_unique_pairs,
                               parse_constant=_reject_constant)
            require(type(value) is dict and set(value) == set(cls.__dataclass_fields__) | {"receipt_id"},
                    "Closed receipt keys required")
            receipt = cls(**{key: value[key] for key in cls.__dataclass_fields__})
            require(value["receipt_id"] == receipt.receipt_id, "Receipt identity mismatch")
            return receipt
        except (TypeError, UnicodeError, ValueError, RecursionError):
            raise YahooQuoteArchiveError("Invalid receipt JSON") from None


class YahooQuoteArchive:
    """No-clobber content-addressed objects and deterministic receipts."""

    def __init__(self, root):
        self.root = Path(root)
        require(".." not in self.root.parts and "\x00" not in str(self.root), "Unsafe archive root")

    def _directory(self, kind, *, create=False):
        require(kind in ("objects", "receipts"), "Unknown archive directory")
        absolute = Path(os.path.abspath(self.root))
        fd = os.open("/", os.O_RDONLY | os.O_DIRECTORY)
        try:
            for component in (*absolute.parts[1:], kind):
                if create:
                    try:
                        os.mkdir(component, 0o700, dir_fd=fd)
                        os.fsync(fd)
                    except FileExistsError:
                        pass
                child = os.open(component, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                                dir_fd=fd)
                os.close(fd)
                fd = child
            return fd
        except OSError:
            os.close(fd)
            raise YahooQuoteArchiveError("Missing or unsafe archive directory") from None

    @staticmethod
    def _read(fd, name, limit):
        try:
            handle = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=fd)
            with os.fdopen(handle, "rb") as stream:
                metadata = os.fstat(stream.fileno())
                require(stat.S_ISREG(metadata.st_mode) and metadata.st_nlink == 1,
                        "Archive entries must be regular single-link files")
                require(metadata.st_size <= limit, "Oversized archive entry")
                raw = stream.read(limit + 1)
                require(len(raw) <= limit, "Oversized archive entry")
                return raw
        except OSError:
            raise YahooQuoteArchiveError("Missing or unsafe archive file") from None

    def _publish(self, kind, name, raw):
        fd = self._directory(kind, create=True)
        temporary = None
        try:
            for index in range(1000):
                candidate = ".pending-" + str(index)
                try:
                    handle = os.open(candidate, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                                     0o600, dir_fd=fd)
                    temporary = candidate
                    break
                except FileExistsError:
                    continue
            else:
                raise YahooQuoteArchiveError("Archive temporary limit exceeded")
            with os.fdopen(handle, "wb") as stream:
                stream.write(raw)
                stream.flush()
                os.fchmod(stream.fileno(), 0o444)
                os.fsync(stream.fileno())
            try:
                os.link(temporary, name, src_dir_fd=fd, dst_dir_fd=fd, follow_symlinks=False)
            except FileExistsError:
                pass
            os.unlink(temporary, dir_fd=fd)
            temporary = None
            limit = MAX_BODY_BYTES if kind == "objects" else _MAX_RECEIPT_BYTES
            existing = self._read(fd, name, limit)
            same = existing == raw
            if not same and kind == "receipts":
                same = YahooQuoteReceipt.from_bytes(existing) == YahooQuoteReceipt.from_bytes(raw)
            require(same, "Existing archive content differs; overwrite forbidden")
            os.fsync(fd)
        except OSError:
            raise YahooQuoteArchiveError("Atomic archive publication failed") from None
        finally:
            try:
                if temporary is not None:
                    os.unlink(temporary, dir_fd=fd)
            except OSError:
                raise YahooQuoteArchiveError("Archive temporary cleanup failed") from None
            finally:
                os.close(fd)

    def _capture_live(self, raw, *, symbol, captured_at):
        """Private acquisition/fixture publication; never caller authority."""
        require(type(raw) is bytes and 0 < len(raw) <= MAX_BODY_BYTES, "Invalid source bytes")
        symbol = canonical_symbol(symbol)
        receipt = YahooQuoteReceipt(
            RECEIPT_SCHEMA_VERSION, SOURCE_KIND, RESOURCE_KIND, symbol,
            canonical_endpoint(symbol), ENDPOINT_PROFILE_ID, PARAMETER_PROFILE,
            digest(raw), len(raw), captured_at, LIVE_ACQUISITION_CONTRACT_VERSION,
        )
        self._publish("objects", receipt.content_sha256, raw)
        self._publish("receipts", receipt.receipt_id + ".json", receipt.to_bytes())
        return receipt

    def read_receipt(self, receipt_id):
        require(type(receipt_id) is str and _HASH.fullmatch(receipt_id), "Invalid receipt identity")
        fd = self._directory("receipts")
        try:
            receipt = YahooQuoteReceipt.from_bytes(
                self._read(fd, receipt_id + ".json", _MAX_RECEIPT_BYTES))
            require(receipt.receipt_id == receipt_id, "Receipt filename mismatch")
            return receipt
        finally:
            os.close(fd)

    def read_object(self, receipt):
        require(type(receipt) is YahooQuoteReceipt, "Typed receipt required")
        require(self.read_receipt(receipt.receipt_id) == receipt, "Receipt is not in this archive")
        fd = self._directory("objects")
        try:
            raw = self._read(fd, receipt.content_sha256, receipt.byte_length)
            require(len(raw) == receipt.byte_length and digest(raw) == receipt.content_sha256,
                    "Source object length/hash corruption")
            return raw
        finally:
            os.close(fd)
