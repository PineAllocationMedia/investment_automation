"""VFV-only immutable exact-byte archive for one reviewed Vanguard route.

Receipts are local integrity records.  They are not provider signatures, legal
permission, publication timestamps, or authority to publish arbitrary bytes.
Only the acquisition module publishes live evidence; tests may use the private
fixture helper.
"""
from dataclasses import asdict, dataclass
from datetime import date, datetime
from enum import StrEnum
import hashlib
import json
import os
from pathlib import Path
import re
import stat
from urllib.parse import urlsplit


VANGUARD_VFV_ARTIFACT_RECEIPT_VERSION = (
    "2026-09-30-vanguard-vfv-artifact-receipt-v1"
)
VANGUARD_VFV_ACQUISITION_VERSION = (
    "2026-09-30-vanguard-vfv-current-acquisition-v1"
)
SOURCE_OWNER = "VANGUARD_CANADA"
VFV_PRODUCT_PAGE_URL = (
    "https://www.vanguard.ca/en/product/etf/equity/9563/"
    "vanguard-sp-500-index-etf"
)
VFV_FACTSHEET_URL = (
    "https://fund-docs.vanguard.com/"
    "VFV_SandP_500_Index_ETF_9563_FS_EN_CA.pdf"
)
VFV_ETF_FACTS_URL = (
    "https://fund-docs.vanguard.com/"
    "VFV_SnP_500_Index_ETF_ETF_9563_EN_FACTS.pdf"
)
MAX_PRODUCT_PAGE_BYTES = 4 * 1024 * 1024
MAX_DOCUMENT_BYTES = 16 * 1024 * 1024
_MAX_RECEIPT_BYTES = 16 * 1024
_HASH = re.compile(r"[0-9a-f]{64}")
_DATE = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")
_TIMESTAMP = re.compile(
    r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}"
    r"(?:\.[0-9]{1,6})?(?:Z|[+-][0-9]{2}:[0-9]{2})"
)
_RECEIPT_DOMAIN = b"pam:vanguard-vfv-artifact-receipt:v1\0"


class VanguardVFVArtifactFamily(StrEnum):
    PRODUCT_PAGE = "PRODUCT_PAGE"
    ETF_FACTS = "ETF_FACTS"
    FACTSHEET = "FACTSHEET"


class VanguardVFVArchiveError(ValueError):
    """Invalid archive contract or corrupt immutable evidence."""


def _require(condition, message):
    if not condition:
        raise VanguardVFVArchiveError(message)


def _digest(raw):
    _require(type(raw) is bytes, "Exact bytes required")
    return hashlib.sha256(raw).hexdigest()


def _canonical_json(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True, allow_nan=False).encode("ascii")


def _unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        _require(key not in result, "Duplicate JSON key")
        result[key] = value
    return result


def _reject_constant(_value):
    raise VanguardVFVArchiveError("Nonfinite JSON constant")


def _timestamp(value):
    _require(type(value) is str and _TIMESTAMP.fullmatch(value) is not None,
             "Exact offset-aware retrieved_at required")
    _require(not value.endswith("-00:00"), "Unknown offset is not a retrieval time")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (ValueError, OverflowError):
        raise VanguardVFVArchiveError("Invalid retrieved_at") from None
    _require(parsed.utcoffset() is not None, "Offset-aware retrieved_at required")
    return value


def _artifact_date(value):
    if value is None:
        return None
    _require(type(value) is str and _DATE.fullmatch(value) is not None,
             "Artifact date must be an exact date or null")
    try:
        date.fromisoformat(value)
    except ValueError:
        raise VanguardVFVArchiveError("Invalid artifact date") from None
    return value


def _expected_url(family):
    if family is VanguardVFVArtifactFamily.PRODUCT_PAGE:
        return VFV_PRODUCT_PAGE_URL
    if family is VanguardVFVArtifactFamily.ETF_FACTS:
        return VFV_ETF_FACTS_URL
    if family is VanguardVFVArtifactFamily.FACTSHEET:
        return VFV_FACTSHEET_URL
    raise VanguardVFVArchiveError("Closed artifact family required")


def _expected_content_type(family):
    return ("text/html" if family is VanguardVFVArtifactFamily.PRODUCT_PAGE
            else "application/pdf")


@dataclass(frozen=True, slots=True)
class VanguardVFVArtifactReceipt:
    schema_version: str
    source_owner: str
    artifact_family: VanguardVFVArtifactFamily
    source_url: str
    content_type: str
    content_sha256: str
    byte_length: int
    artifact_date: str | None
    retrieved_at: str
    acquisition_contract_version: str
    parent_product_receipt_id: str | None

    def __post_init__(self):
        _require(self.schema_version == VANGUARD_VFV_ARTIFACT_RECEIPT_VERSION,
                 "Unsupported receipt schema")
        _require(self.source_owner == SOURCE_OWNER, "Unsupported source owner")
        _require(type(self.artifact_family) is VanguardVFVArtifactFamily,
                 "Closed artifact family required")
        _require(self.source_url == _expected_url(self.artifact_family),
                 "Noncanonical Vanguard VFV source URL")
        parts = urlsplit(self.source_url)
        _require(parts.scheme == "https" and not parts.username and not parts.password
                 and parts.port is None and not parts.fragment,
                 "Reviewed HTTPS source URL required")
        _require(self.content_type == _expected_content_type(self.artifact_family),
                 "Unexpected artifact content type")
        _require(type(self.content_sha256) is str
                 and _HASH.fullmatch(self.content_sha256) is not None,
                 "Invalid content hash")
        limit = (MAX_PRODUCT_PAGE_BYTES
                 if self.artifact_family is VanguardVFVArtifactFamily.PRODUCT_PAGE
                 else MAX_DOCUMENT_BYTES)
        _require(type(self.byte_length) is int and 0 < self.byte_length <= limit,
                 "Invalid artifact byte length")
        object.__setattr__(self, "artifact_date", _artifact_date(self.artifact_date))
        object.__setattr__(self, "retrieved_at", _timestamp(self.retrieved_at))
        _require(self.acquisition_contract_version == VANGUARD_VFV_ACQUISITION_VERSION,
                 "Unsupported acquisition contract")
        if self.artifact_family is VanguardVFVArtifactFamily.PRODUCT_PAGE:
            _require(self.parent_product_receipt_id is None,
                     "Product page cannot have a parent receipt")
        else:
            _require(type(self.parent_product_receipt_id) is str
                     and _HASH.fullmatch(self.parent_product_receipt_id) is not None,
                     "Document requires exact parent product receipt")

    @property
    def receipt_id(self):
        projected = asdict(self)
        projected["artifact_family"] = self.artifact_family.value
        return _digest(_RECEIPT_DOMAIN + _canonical_json(projected))

    def to_bytes(self):
        projected = asdict(self)
        projected["artifact_family"] = self.artifact_family.value
        return _canonical_json({**projected, "receipt_id": self.receipt_id})

    @classmethod
    def from_bytes(cls, raw):
        _require(type(raw) is bytes and len(raw) <= _MAX_RECEIPT_BYTES,
                 "Invalid receipt bytes")
        try:
            value = json.loads(raw, object_pairs_hook=_unique_pairs,
                               parse_constant=_reject_constant)
            _require(type(value) is dict
                     and set(value) == set(cls.__dataclass_fields__) | {"receipt_id"},
                     "Closed receipt keys required")
            fields = {key: value[key] for key in cls.__dataclass_fields__}
            fields["artifact_family"] = VanguardVFVArtifactFamily(
                fields["artifact_family"])
            receipt = cls(**fields)
            _require(value["receipt_id"] == receipt.receipt_id,
                     "Receipt identity mismatch")
            return receipt
        except (KeyError, TypeError, UnicodeError, ValueError, RecursionError):
            raise VanguardVFVArchiveError("Invalid receipt JSON") from None


class VanguardVFVArchive:
    """No-clobber content-addressed objects and deterministic receipts."""

    def __init__(self, root):
        self.root = Path(root)
        _require(".." not in self.root.parts and "\x00" not in str(self.root),
                 "Unsafe archive root")

    def _directory(self, kind, *, create=False):
        _require(kind in ("objects", "receipts"), "Unknown archive directory")
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
            raise VanguardVFVArchiveError(
                "Missing or unsafe archive directory") from None

    @staticmethod
    def _read(fd, name, limit):
        try:
            handle = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK,
                             dir_fd=fd)
            with os.fdopen(handle, "rb") as stream:
                metadata = os.fstat(stream.fileno())
                _require(stat.S_ISREG(metadata.st_mode) and metadata.st_nlink == 1,
                         "Archive entries must be regular single-link files")
                _require(metadata.st_size <= limit, "Oversized archive entry")
                raw = stream.read(limit + 1)
                _require(len(raw) <= limit, "Oversized archive entry")
                return raw
        except OSError:
            raise VanguardVFVArchiveError(
                "Missing or unsafe archive file") from None

    def _publish(self, kind, name, raw):
        fd = self._directory(kind, create=True)
        temporary = None
        try:
            for index in range(1000):
                candidate = f".pending-{index}"
                try:
                    handle = os.open(
                        candidate,
                        os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                        0o600,
                        dir_fd=fd,
                    )
                    temporary = candidate
                    break
                except FileExistsError:
                    continue
            else:
                raise VanguardVFVArchiveError("Archive temporary limit exceeded")
            with os.fdopen(handle, "wb") as stream:
                stream.write(raw)
                stream.flush()
                os.fchmod(stream.fileno(), 0o444)
                os.fsync(stream.fileno())
            try:
                os.link(temporary, name, src_dir_fd=fd, dst_dir_fd=fd,
                        follow_symlinks=False)
            except FileExistsError:
                pass
            os.unlink(temporary, dir_fd=fd)
            temporary = None
            limit = MAX_DOCUMENT_BYTES if kind == "objects" else _MAX_RECEIPT_BYTES
            existing = self._read(fd, name, limit)
            _require(existing == raw,
                     "Existing archive content differs; overwrite forbidden")
            os.fsync(fd)
        except OSError:
            raise VanguardVFVArchiveError(
                "Atomic archive publication failed") from None
        finally:
            try:
                if temporary is not None:
                    os.unlink(temporary, dir_fd=fd)
            except OSError:
                raise VanguardVFVArchiveError(
                    "Archive temporary cleanup failed") from None
            finally:
                os.close(fd)

    def _capture(self, raw, *, artifact_family, source_url, content_type,
                 retrieved_at, artifact_date=None, parent_product_receipt_id=None):
        """Private live/fixture publication; never arbitrary public authority."""
        _require(type(raw) is bytes and raw, "Exact nonempty source bytes required")
        _require(type(artifact_family) is VanguardVFVArtifactFamily,
                 "Closed artifact family required")
        limit = (MAX_PRODUCT_PAGE_BYTES
                 if artifact_family is VanguardVFVArtifactFamily.PRODUCT_PAGE
                 else MAX_DOCUMENT_BYTES)
        _require(len(raw) <= limit, "Artifact exceeds reviewed size limit")
        if artifact_family is not VanguardVFVArtifactFamily.PRODUCT_PAGE:
            parent = self.read_receipt(parent_product_receipt_id)
            _require(parent.artifact_family is VanguardVFVArtifactFamily.PRODUCT_PAGE,
                     "Document parent must be exact product receipt")
        receipt = VanguardVFVArtifactReceipt(
            VANGUARD_VFV_ARTIFACT_RECEIPT_VERSION,
            SOURCE_OWNER,
            artifact_family,
            source_url,
            content_type,
            _digest(raw),
            len(raw),
            artifact_date,
            retrieved_at,
            VANGUARD_VFV_ACQUISITION_VERSION,
            parent_product_receipt_id,
        )
        self._publish("objects", receipt.content_sha256, raw)
        self._publish("receipts", receipt.receipt_id + ".json", receipt.to_bytes())
        return receipt

    def _capture_fixture(self, raw, **kwargs):
        """Private deterministic test support; not authoritative publication API."""
        return self._capture(raw, **kwargs)

    def read_receipt(self, receipt_id):
        _require(type(receipt_id) is str and _HASH.fullmatch(receipt_id) is not None,
                 "Invalid receipt identity")
        fd = self._directory("receipts")
        try:
            receipt = VanguardVFVArtifactReceipt.from_bytes(
                self._read(fd, receipt_id + ".json", _MAX_RECEIPT_BYTES))
            _require(receipt.receipt_id == receipt_id, "Receipt filename mismatch")
            return receipt
        finally:
            os.close(fd)

    def read_object(self, receipt):
        _require(type(receipt) is VanguardVFVArtifactReceipt,
                 "Typed receipt required")
        _require(self.read_receipt(receipt.receipt_id) == receipt,
                 "Receipt is not in this archive")
        fd = self._directory("objects")
        try:
            raw = self._read(fd, receipt.content_sha256, receipt.byte_length)
            _require(len(raw) == receipt.byte_length
                     and _digest(raw) == receipt.content_sha256,
                     "Source object length/hash corruption")
            return raw
        finally:
            os.close(fd)
