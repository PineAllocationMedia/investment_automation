"""Append-only exact-byte SEC-style snapshots, not authenticated filing documents.

The caller supplies capture time. This offline API verifies integrity, not the
truth of that timestamp or the origin of the bytes. Never use filing dates to
backdate receipts. sec_acquisition owns the separate internal LIVE route.
"""
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import stat

RECEIPT_SCHEMA_VERSION = "2026-09-10-sec-capture-receipt-v1"
SOURCE_KIND = "SEC_COMPANYFACTS_SNAPSHOT"
ACQUISITION_CONTRACT_VERSION = "2026-09-10-offline-supplied-companyfacts-v1"
LIVE_ACQUISITION_CONTRACT_VERSION = "2026-09-11-sec-live-companyfacts-v1"
_SUPPORTED_ACQUISITION_CONTRACTS = (ACQUISITION_CONTRACT_VERSION,
                                    LIVE_ACQUISITION_CONTRACT_VERSION)
_HASH = re.compile(r"[0-9a-f]{64}")
_TIME = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|[+-]\d{2}:\d{2})")


class ArchiveError(ValueError):
    """Invalid evidence contract, unsafe archive path, or corrupt archive."""


def require(condition, message):
    if not condition:
        raise ArchiveError(message)


def canonical_timestamp(value):
    require(type(value) is str and _TIME.fullmatch(value) is not None,
            "Explicit-offset timestamp required")
    require(not value.endswith("-00:00"), "Unknown offset is not a capture time")
    if not value.endswith("Z"):
        require(int(value[-5:-3]) < 24 and int(value[-2:]) < 60, "Invalid offset")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    except (ValueError, OverflowError) as exc:
        raise ArchiveError("Invalid timestamp") from exc


def validate_cik(cik):
    require(type(cik) is str and re.fullmatch(r"[0-9]{10}", cik) is not None,
            "CIK must be ten decimal digits")
    return cik


def endpoint_for(cik):
    return "https://data.sec.gov/api/xbrl/companyfacts/CIK" + validate_cik(cik) + ".json"


def digest(raw):
    require(type(raw) is bytes, "Exact bytes required")
    return hashlib.sha256(raw).hexdigest()


def canonical_json(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True, allow_nan=False).encode("ascii")


def unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, "Duplicate JSON key")
        result[key] = value
    return result


def reject_constant(value):
    raise ArchiveError("Nonfinite JSON constant: " + value)


@dataclass(frozen=True, slots=True)
class CaptureReceipt:
    schema_version: str
    source_kind: str
    cik: str
    endpoint: str
    content_sha256: str
    byte_length: int
    captured_at: str
    source_locator: str
    acquisition_contract_version: str

    def __post_init__(self):
        require(self.schema_version == RECEIPT_SCHEMA_VERSION, "Unsupported receipt schema")
        require(self.source_kind == SOURCE_KIND, "Unsupported source kind")
        require(self.endpoint == endpoint_for(self.cik), "Endpoint/CIK mismatch")
        require(type(self.content_sha256) is str and _HASH.fullmatch(self.content_sha256), "Invalid object hash")
        require(type(self.byte_length) is int and self.byte_length >= 0, "Invalid byte length")
        object.__setattr__(self, "captured_at", canonical_timestamp(self.captured_at))
        require(type(self.source_locator) is str and bool(self.source_locator.strip())
                and self.source_locator == self.source_locator.strip(), "Source locator required")
        require(self.acquisition_contract_version in _SUPPORTED_ACQUISITION_CONTRACTS,
                "Unsupported acquisition contract")

    @property
    def receipt_id(self):
        return digest(canonical_json(asdict(self)))

    def to_bytes(self):
        return canonical_json({**asdict(self), "receipt_id": self.receipt_id})

    @classmethod
    def from_bytes(cls, raw):
        try:
            value = json.loads(raw, object_pairs_hook=unique_pairs, parse_constant=reject_constant)
            require(type(value) is dict and set(value) == set(cls.__dataclass_fields__) | {"receipt_id"},
                    "Closed receipt keys required")
            receipt = cls(**{key: value[key] for key in cls.__dataclass_fields__})
            require(value["receipt_id"] == receipt.receipt_id, "Receipt identity mismatch")
            return receipt
        except (TypeError, UnicodeError, json.JSONDecodeError) as exc:
            raise ArchiveError("Invalid receipt JSON") from exc


@dataclass(frozen=True, slots=True)
class CaptureView:
    cik: str
    cutoff: str
    receipts: tuple[CaptureReceipt, ...]
    latest_receipt_ids: tuple[str, ...]
    coverage: str = "ARCHIVE_CAPTURE_VIEW_ONLY"


class SecArchive:
    """Caller-chosen archive root; metadata is never interpreted as a path.

    Object/receipt files are published atomically with a no-clobber hard link
    after fsync. Directory-descriptor operations reject archive symlinks.
    Read APIs create nothing. The archive is integrity checked, not tamper proof
    against an actor able to replace the entire archive and its trust anchors.
    """

    def __init__(self, root):
        self.root = Path(root)

    def _directory(self, kind, *, create=False):
        require(kind in ("objects", "receipts"), "Unknown archive directory")
        # Walk from / without resolving symlinks, including the root itself.
        absolute = Path(os.path.abspath(self.root))
        fd = os.open("/", os.O_RDONLY | os.O_DIRECTORY)
        try:
            for component in (*absolute.parts[1:], kind):
                if create:
                    try:
                        os.mkdir(component, 0o700, dir_fd=fd)
                    except FileExistsError:
                        pass
                child = os.open(component, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
                os.close(fd)
                fd = child
            return fd
        except OSError as exc:
            os.close(fd)
            raise ArchiveError("Missing or unsafe archive directory") from exc

    @staticmethod
    def _read(fd, name):
        try:
            handle = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=fd)
            with os.fdopen(handle, "rb") as stream:
                metadata = os.fstat(stream.fileno())
                require(stat.S_ISREG(metadata.st_mode) and metadata.st_nlink == 1,
                        "Archive entries must be regular unlinked files")
                return stream.read()
        except OSError as exc:
            raise ArchiveError("Missing or unsafe archive file") from exc

    def _publish(self, kind, name, raw):
        fd = self._directory(kind, create=True)
        temporary = None
        try:
            # Temporary names are not evidence identities. O_EXCL handles races.
            index = 0
            while True:
                candidate = ".pending-" + str(index)
                try:
                    handle = os.open(candidate, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                                     0o600, dir_fd=fd)
                    temporary = candidate
                    break
                except FileExistsError:
                    index += 1
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
            existing = self._read(fd, name)
            same = existing == raw
            if not same and kind == "receipts":
                same = CaptureReceipt.from_bytes(existing) == CaptureReceipt.from_bytes(raw)
            require(same, "Existing archive content differs; overwrite forbidden")
            os.fsync(fd)
        except OSError as exc:
            raise ArchiveError("Atomic archive publication failed") from exc
        finally:
            if temporary is not None:
                os.unlink(temporary, dir_fd=fd)
            os.close(fd)

    def capture(self, raw, *, cik, captured_at, source_locator):
        """Public supplied-byte API: always the original OFFLINE contract."""
        return self._capture(raw, cik=cik, captured_at=captured_at, source_locator=source_locator,
                             acquisition_contract_version=ACQUISITION_CONTRACT_VERSION)

    def _capture_live(self, raw, *, cik, captured_at):
        """Internal publication capability for sec_acquisition's validated response.

        Private by convention under trusted local code, not remote attestation.
        """
        return self._capture(raw, cik=cik, captured_at=captured_at, source_locator=endpoint_for(cik),
                             acquisition_contract_version=LIVE_ACQUISITION_CONTRACT_VERSION)

    def _capture(self, raw, *, cik, captured_at, source_locator, acquisition_contract_version):
        receipt = CaptureReceipt(RECEIPT_SCHEMA_VERSION, SOURCE_KIND, cik, endpoint_for(cik),
                                 digest(raw), len(raw), captured_at, source_locator,
                                 acquisition_contract_version)
        self._publish("objects", receipt.content_sha256, raw)
        self._publish("receipts", receipt.receipt_id + ".json", receipt.to_bytes())
        return receipt

    def read_object(self, receipt):
        require(type(receipt) is CaptureReceipt, "Typed receipt required")
        # Require membership, not just a caller's self-consistent receipt.
        stored = self.read_receipt(receipt.receipt_id)
        require(stored == receipt, "Receipt is not in this archive")
        fd = self._directory("objects")
        try:
            raw = self._read(fd, receipt.content_sha256)
            require(len(raw) == receipt.byte_length and digest(raw) == receipt.content_sha256,
                    "Source object length/hash corruption")
            return raw
        finally:
            os.close(fd)

    def read_receipt(self, receipt_id):
        require(type(receipt_id) is str and _HASH.fullmatch(receipt_id), "Invalid receipt identity")
        fd = self._directory("receipts")
        try:
            receipt = CaptureReceipt.from_bytes(self._read(fd, receipt_id + ".json"))
            require(receipt.receipt_id == receipt_id, "Receipt filename mismatch")
            return receipt
        finally:
            os.close(fd)

    def captures_as_of(self, *, cik, cutoff):
        validate_cik(cik)
        cutoff = canonical_timestamp(cutoff)
        limit = datetime.fromisoformat(cutoff.replace("Z", "+00:00"))
        fd = self._directory("receipts")
        try:
            receipts = []
            for name in sorted(os.listdir(fd)):
                if name.startswith(".pending-"):
                    continue
                require(re.fullmatch(r"[0-9a-f]{64}\.json", name), "Unexpected receipt entry")
                receipt = CaptureReceipt.from_bytes(self._read(fd, name))
                require(name == receipt.receipt_id + ".json", "Receipt filename mismatch")
                if receipt.cik == cik and datetime.fromisoformat(receipt.captured_at.replace("Z", "+00:00")) <= limit:
                    receipts.append(receipt)
            receipts.sort(key=lambda r: (datetime.fromisoformat(r.captured_at.replace("Z", "+00:00")), r.receipt_id))
            # Verify only admitted objects; later source bytes cannot affect T.
            for receipt in receipts:
                self.read_object(receipt)
            latest = receipts[-1].captured_at if receipts else None
            return CaptureView(cik, cutoff, tuple(receipts),
                               tuple(r.receipt_id for r in receipts if r.captured_at == latest))
        finally:
            os.close(fd)
