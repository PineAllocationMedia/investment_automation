"""Dedicated immutable SEC complete-submission evidence, under local trust only.

Only reviewed acquisition calls the private publication helper. There is no
public supplied-byte capture API. Receipts/hashes are integrity records, not
credentials; an attacker controlling the archive and code is outside this model.
No discovery, historical view, qualification or economic admission exists here.
"""
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import stat

RECEIPT_SCHEMA_VERSION = "2026-09-20-sec-filing-receipt-v1"
SOURCE_KIND = "SEC_COMPLETE_SUBMISSION_TEXT"
LIVE_ACQUISITION_CONTRACT_VERSION = "2026-09-20-sec-live-filing-v1"
MAX_FILING_BYTES = 32 * 1024 * 1024
_MAX_RECEIPT_BYTES = 4096
_RECEIPT_DOMAIN = b"pam:sec-complete-submission-receipt:v1\0"
_HASH = re.compile(r"[0-9a-f]{64}")
_TIME = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]{1,6})?(?:Z|[+-][0-9]{2}:[0-9]{2})")


class FilingArchiveError(ValueError):
    """Invalid evidence contract, unsafe archive path, or corrupt archive."""


def require(condition, message):
    if not condition:
        raise FilingArchiveError(message)


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
        raise FilingArchiveError("Invalid timestamp") from None


def validate_cik(cik):
    require(type(cik) is str and re.fullmatch(r"[0-9]{10}", cik) is not None,
            "CIK must be ten decimal digits")
    return cik


def validate_accession(accession):
    require(type(accession) is str and
            re.fullmatch(r"[0-9]{10}-[0-9]{2}-[0-9]{6}", accession) is not None,
            "Canonical accession required")
    return accession


def endpoint_for(cik, accession):
    validate_cik(cik)
    validate_accession(accession)
    # Accession prefix can identify a filing agent, NOT the registrant.
    return ("https://www.sec.gov/Archives/edgar/data/" + str(int(cik)) + "/"
            + accession.replace("-", "") + "/" + accession + ".txt")


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
    raise FilingArchiveError("Nonfinite JSON constant")


@dataclass(frozen=True, slots=True)
class FilingReceipt:
    schema_version: str
    source_kind: str
    cik: str
    accession: str
    endpoint: str
    content_sha256: str
    byte_length: int
    captured_at: str
    acquisition_contract_version: str

    def __post_init__(self):
        require(self.schema_version == RECEIPT_SCHEMA_VERSION, "Unsupported receipt schema")
        require(self.source_kind == SOURCE_KIND, "Unsupported source kind")
        require(self.endpoint == endpoint_for(self.cik, self.accession), "Endpoint/CIK mismatch")
        require(type(self.content_sha256) is str and _HASH.fullmatch(self.content_sha256), "Invalid object hash")
        require(type(self.byte_length) is int and 0 < self.byte_length <= MAX_FILING_BYTES, "Invalid byte length")
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
            value = json.loads(raw, object_pairs_hook=unique_pairs, parse_constant=reject_constant)
            require(type(value) is dict and set(value) == set(cls.__dataclass_fields__) | {"receipt_id"},
                    "Closed receipt keys required")
            receipt = cls(**{key: value[key] for key in cls.__dataclass_fields__})
            require(value["receipt_id"] == receipt.receipt_id, "Receipt identity mismatch")
            return receipt
        except (TypeError, UnicodeError, ValueError, RecursionError):
            raise FilingArchiveError("Invalid receipt JSON") from None


class SecFilingArchive:
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
        except OSError:
            os.close(fd)
            raise FilingArchiveError("Missing or unsafe archive directory") from None

    @staticmethod
    def _read(fd, name, limit):
        try:
            handle = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=fd)
            with os.fdopen(handle, "rb") as stream:
                metadata = os.fstat(stream.fileno())
                require(stat.S_ISREG(metadata.st_mode) and metadata.st_nlink == 1,
                        "Archive entries must be regular unlinked files")
                require(metadata.st_size <= limit, "Oversized archive entry")
                raw = stream.read(limit + 1)
                require(len(raw) <= limit, "Oversized archive entry")
                return raw
        except OSError:
            raise FilingArchiveError("Missing or unsafe archive file") from None

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
            existing = self._read(fd, name, MAX_FILING_BYTES if kind == "objects" else _MAX_RECEIPT_BYTES)
            same = existing == raw
            if not same and kind == "receipts":
                same = FilingReceipt.from_bytes(existing) == FilingReceipt.from_bytes(raw)
            require(same, "Existing archive content differs; overwrite forbidden")
            os.fsync(fd)
        except OSError:
            raise FilingArchiveError("Atomic archive publication failed") from None
        finally:
            try:
                if temporary is not None:
                    os.unlink(temporary, dir_fd=fd)
            except OSError:
                raise FilingArchiveError("Archive temporary cleanup failed") from None
            finally:
                os.close(fd)

    def _capture_live(self, raw, *, cik, accession, captured_at):
        """Private reviewed-acquisition publication; not an authority credential.

        Tests may patch transport or call this helper with fictional bytes. Such
        fixtures are mechanical tests, never independently admitted evidence.
        """
        receipt = FilingReceipt(RECEIPT_SCHEMA_VERSION, SOURCE_KIND, cik, accession,
                                endpoint_for(cik, accession), digest(raw), len(raw),
                                captured_at, LIVE_ACQUISITION_CONTRACT_VERSION)
        self._publish("objects", receipt.content_sha256, raw)
        self._publish("receipts", receipt.receipt_id + ".json", receipt.to_bytes())
        return receipt

    def read_object(self, receipt):
        require(type(receipt) is FilingReceipt, "Typed receipt required")
        # Require membership, not just a caller's self-consistent receipt.
        stored = self.read_receipt(receipt.receipt_id)
        require(stored == receipt, "Receipt is not in this archive")
        fd = self._directory("objects")
        try:
            raw = self._read(fd, receipt.content_sha256, receipt.byte_length)
            require(len(raw) == receipt.byte_length and digest(raw) == receipt.content_sha256,
                    "Source object length/hash corruption")
            return raw
        finally:
            os.close(fd)

    def read_receipt(self, receipt_id):
        require(type(receipt_id) is str and _HASH.fullmatch(receipt_id), "Invalid receipt identity")
        fd = self._directory("receipts")
        try:
            receipt = FilingReceipt.from_bytes(self._read(fd, receipt_id + ".json", _MAX_RECEIPT_BYTES))
            require(receipt.receipt_id == receipt_id, "Receipt filename mismatch")
            return receipt
        finally:
            os.close(fd)
