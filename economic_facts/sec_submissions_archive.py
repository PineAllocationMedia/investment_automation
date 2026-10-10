"""Dedicated immutable SEC Submissions JSON evidence, under local trust only.

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

RECEIPT_SCHEMA_VERSION = "2026-09-21-sec-submissions-receipt-v1"
SOURCE_KIND = "SEC_SUBMISSIONS_JSON"
LIVE_ACQUISITION_CONTRACT_VERSION = "2026-09-21-sec-live-submissions-v1"
MAX_SUBMISSIONS_BYTES = 32 * 1024 * 1024
_MAX_RECEIPT_BYTES = 4096
_RECEIPT_DOMAIN = b"pam:sec-submissions-receipt:v1\0"
_HASH = re.compile(r"[0-9a-f]{64}")
_TIME = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]{1,6})?(?:Z|[+-][0-9]{2}:[0-9]{2})")


class SubmissionsArchiveError(ValueError):
    """Invalid evidence contract, unsafe archive path, or corrupt archive."""


def require(condition, message):
    if not condition:
        raise SubmissionsArchiveError(message)


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
        raise SubmissionsArchiveError("Invalid timestamp") from None


def validate_cik(cik):
    require(type(cik) is str and re.fullmatch(r"[0-9]{10}", cik) is not None,
            "CIK must be ten decimal digits")
    return cik


def validate_receipt_id(value):
    require(type(value) is str and _HASH.fullmatch(value), "Invalid receipt identity")
    return value


def validate_history_filename(cik, filename):
    validate_cik(cik)
    # PAM safety limit, not an SEC pagination width guarantee.
    require(type(filename) is str and len(filename) <= 128 and
            re.fullmatch(r"CIK" + cik + r"-submissions-[0-9]+\.json", filename),
            "Unsupported history filename")
    return filename


def endpoint_for(cik, history_filename=None):
    validate_cik(cik)
    filename = ("CIK" + cik + ".json" if history_filename is None else
                validate_history_filename(cik, history_filename))
    return "https://data.sec.gov/submissions/" + filename


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
    raise SubmissionsArchiveError("Nonfinite JSON constant")


@dataclass(frozen=True, slots=True)
class SubmissionsReceipt:
    schema_version: str
    source_kind: str
    cik: str
    resource_kind: str
    history_filename: str | None
    parent_receipt_id: str | None
    endpoint: str
    content_sha256: str
    byte_length: int
    captured_at: str
    acquisition_contract_version: str

    def __post_init__(self):
        require(self.schema_version == RECEIPT_SCHEMA_VERSION, "Unsupported receipt schema")
        require(self.source_kind == SOURCE_KIND, "Unsupported source kind")
        require(self.resource_kind in ("ROOT", "HISTORY"), "Unsupported resource kind")
        if self.resource_kind == "ROOT":
            require(self.history_filename is None and self.parent_receipt_id is None,
                    "Root cannot have parent/history selectors")
        else:
            validate_receipt_id(self.parent_receipt_id)
            validate_history_filename(self.cik, self.history_filename)
        require(self.endpoint == endpoint_for(self.cik, self.history_filename), "Endpoint/CIK mismatch")
        require(type(self.content_sha256) is str and _HASH.fullmatch(self.content_sha256), "Invalid object hash")
        require(type(self.byte_length) is int and 0 < self.byte_length <= MAX_SUBMISSIONS_BYTES, "Invalid byte length")
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
            raise SubmissionsArchiveError("Invalid receipt JSON") from None


class SecSubmissionsArchive:
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
            raise SubmissionsArchiveError("Missing or unsafe archive directory") from None

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
            raise SubmissionsArchiveError("Missing or unsafe archive file") from None

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
            existing = self._read(fd, name, MAX_SUBMISSIONS_BYTES if kind == "objects" else _MAX_RECEIPT_BYTES)
            same = existing == raw
            if not same and kind == "receipts":
                same = SubmissionsReceipt.from_bytes(existing) == SubmissionsReceipt.from_bytes(raw)
            require(same, "Existing archive content differs; overwrite forbidden")
            os.fsync(fd)
        except OSError:
            raise SubmissionsArchiveError("Atomic archive publication failed") from None
        finally:
            try:
                if temporary is not None:
                    os.unlink(temporary, dir_fd=fd)
            except OSError:
                raise SubmissionsArchiveError("Archive temporary cleanup failed") from None
            finally:
                os.close(fd)

    def _capture_live(self, raw, *, cik, captured_at, parent_receipt_id=None,
                      history_filename=None):
        """Private controlled publication; fictional tests may call this helper."""
        kind = "ROOT" if parent_receipt_id is None else "HISTORY"
        receipt = SubmissionsReceipt(
            RECEIPT_SCHEMA_VERSION, SOURCE_KIND, cik, kind, history_filename,
            parent_receipt_id, endpoint_for(cik, history_filename), digest(raw),
            len(raw), captured_at, LIVE_ACQUISITION_CONTRACT_VERSION)
        _parse_resource(raw, cik, kind)
        if kind == "HISTORY":
            self._verified_parent(receipt)
        self._publish("objects", receipt.content_sha256, raw)
        self._publish("receipts", receipt.receipt_id + ".json", receipt.to_bytes())
        return receipt

    def _verified_parent(self, receipt):
        parent = self.read_receipt(receipt.parent_receipt_id)
        require(parent.resource_kind == "ROOT" and parent.cik == receipt.cik,
                "History parent mismatch")
        source = _parse_resource(self.read_object(parent), parent.cik, "ROOT")
        require(any(dict(ref)["name"] == receipt.history_filename for ref in source.references),
                "History resource absent from parent")
        require(datetime.fromisoformat(receipt.captured_at.replace("Z", "+00:00")) >=
                datetime.fromisoformat(parent.captured_at.replace("Z", "+00:00")),
                "History capture precedes parent")
        return parent

    def read_object(self, receipt):
        require(type(receipt) is SubmissionsReceipt, "Typed receipt required")
        if receipt.resource_kind == "HISTORY":
            self._verified_parent(receipt)
        return self._read_member_object(receipt)

    def _read_member_object(self, receipt):
        """Internal read after the caller verifies the exact parent relationship.

        Replay verifies its one root once, avoiding repeated decoding of a large
        parent for each child. Membership, length and hash are still checked here.
        """
        require(type(receipt) is SubmissionsReceipt, "Typed receipt required")
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
            receipt = SubmissionsReceipt.from_bytes(self._read(fd, receipt_id + ".json", _MAX_RECEIPT_BYTES))
            require(receipt.receipt_id == receipt_id, "Receipt filename mismatch")
            return receipt
        finally:
            os.close(fd)


# Explicit PAM implementation limits; none are SEC completeness guarantees.
MAX_ROWS = 100_000
MAX_REFERENCES = 1_000
MAX_COLUMNS = 64
MAX_CELLS = 500_000
MAX_STRING_LENGTH = 16_384
MAX_METADATA_ITEMS = 1_000
MAX_JSON_DEPTH = 8
CORE_COLUMNS = frozenset(("accessionNumber", "filingDate", "reportDate",
                          "acceptanceDateTime", "form", "primaryDocument"))


class UnsupportedSubmissionsStructure(ValueError):
    """Unsupported or excessive source shape; no source values in errors."""


def _source_require(condition):
    if not condition:
        raise UnsupportedSubmissionsStructure("Unsupported Submissions structure")


def _scalar(value):
    # Floats are intentionally unsupported: interpreted SEC columns require no
    # fractional numbers. This also excludes overflowed JSON exponents.
    _source_require(value is None or type(value) in (str, int, bool))
    if type(value) is str:
        _source_require(len(value) <= MAX_STRING_LENGTH and
                        not any(0xD800 <= ord(c) <= 0xDFFF for c in value))
    if type(value) is int:
        _source_require(abs(value) <= 2**63 - 1)


def _keys(value, limit):
    _source_require(type(value) is dict and len(value) <= limit)
    for key in value:
        _source_require(type(key) is str and re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{0,63}", key))


def _date(value, *, empty=False):
    _source_require(type(value) is str)
    if empty and value == "":
        return
    _source_require(re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value))
    try:
        datetime.strptime(value, "%Y-%m-%d")
    except ValueError:
        raise UnsupportedSubmissionsStructure("Invalid source date") from None


def _columns(value):
    _keys(value, MAX_COLUMNS)
    _source_require(CORE_COLUMNS <= value.keys())
    _source_require(type(value["accessionNumber"]) is list)
    count = len(value["accessionNumber"])
    _source_require(count <= MAX_ROWS and count * len(value) <= MAX_CELLS)
    for column in value.values():
        _source_require(type(column) is list and len(column) == count)
        for scalar in column:
            _scalar(scalar)
    keys = sorted(value)
    rows = []
    for index in range(count):
        fields = {key: value[key][index] for key in keys}
        _source_require(type(fields["accessionNumber"]) is str and
                        re.fullmatch(r"[0-9]{10}-[0-9]{2}-[0-9]{6}", fields["accessionNumber"]))
        _date(fields["filingDate"])
        _date(fields["reportDate"], empty=True)
        _source_require(type(fields["form"]) is str and 0 < len(fields["form"]) <= 128)
        _source_require(type(fields["primaryDocument"]) is str)
        # Source acceptance is retained verbatim, never converted to availability.
        acceptance = fields["acceptanceDateTime"]
        _source_require(type(acceptance) is str and re.fullmatch(
            r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]{1,6})?Z",
            acceptance))
        try:
            datetime.fromisoformat(acceptance.replace("Z", "+00:00"))
        except ValueError:
            raise UnsupportedSubmissionsStructure("Invalid source acceptance time") from None
        rows.append(tuple(fields.items()))
    return tuple(rows)


def _metadata(value):
    """Only reviewed nested entity shapes; unfamiliar scalar metadata retained."""
    _keys(value, MAX_COLUMNS)
    for key, item in value.items():
        if key in ("tickers", "exchanges"):
            _source_require(type(item) is list and len(item) <= MAX_METADATA_ITEMS)
            for entry in item:
                _source_require(type(entry) is str)
                _scalar(entry)
        elif key == "addresses":
            _keys(item, 2)
            _source_require(set(item) <= {"mailing", "business"})
            for address in item.values():
                _keys(address, MAX_COLUMNS)
                for name, field in address.items():
                    _source_require(field is None or type(field) is str or
                                    (name == "isForeignLocation" and type(field) is int))
                    _scalar(field)
        elif key == "formerNames":
            _source_require(type(item) is list and len(item) <= MAX_METADATA_ITEMS)
            for former in item:
                _keys(former, 3)
                _source_require(set(former) == {"name", "from", "to"})
                for field in former.values():
                    _source_require(type(field) is str)
                    _scalar(field)
        else:
            _scalar(item)
    return canonical_json(value)


@dataclass(frozen=True, slots=True)
class _SourceInventory:
    rows: tuple
    references: tuple
    metadata_json: bytes


def _parse_resource(raw, cik, resource_kind):
    """Bounded shared source parser; exact archive bytes remain authoritative."""
    _source_require(type(raw) is bytes and 0 < len(raw) <= MAX_SUBMISSIONS_BYTES)
    # Scan nesting before json.loads so deeply nested input never reaches the
    # recursive decoder. Quotes/escapes are accounted for; JSON validates syntax.
    depth, quoted, escaped = 0, False, False
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
            _source_require(depth <= MAX_JSON_DEPTH)
        elif byte in (93, 125):
            depth -= 1
    try:
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=unique_pairs,
                           parse_constant=reject_constant)
        _keys(value, MAX_COLUMNS)
        if resource_kind == "HISTORY":
            return _SourceInventory(_columns(value), (), b"{}")
        _source_require(resource_kind == "ROOT")
        source_cik = value.get("cik")
        _source_require((type(source_cik) is int and 0 <= source_cik < 10**10) or
                        (type(source_cik) is str and re.fullmatch(r"[0-9]{1,10}", source_cik)))
        _source_require(str(source_cik).zfill(10) == validate_cik(cik))
        filings = value.get("filings")
        _source_require(type(filings) is dict and set(filings) == {"recent", "files"})
        rows = _columns(filings["recent"])
        files = filings["files"]
        _source_require(type(files) is list and len(files) <= MAX_REFERENCES)
        references, names = [], set()
        for reference in files:
            _keys(reference, MAX_COLUMNS)
            _source_require("name" in reference)
            name = validate_history_filename(cik, reference["name"])
            _source_require(name not in names)
            names.add(name)
            for field in reference.values():
                _scalar(field)
            if "filingCount" in reference:
                count = reference["filingCount"]
                _source_require(type(count) is int and 0 <= count <= 2**63 - 1)
            for key in ("filingFrom", "filingTo"):
                if key in reference:
                    _date(reference[key])
            if "filingFrom" in reference and "filingTo" in reference:
                _source_require(reference["filingFrom"] <= reference["filingTo"])
            references.append(tuple(sorted(reference.items())))
        metadata = _metadata({key: item for key, item in value.items() if key != "filings"})
        return _SourceInventory(rows, tuple(references), metadata)
    except (SubmissionsArchiveError, UnicodeError, ValueError, RecursionError):
        raise UnsupportedSubmissionsStructure("Unsupported Submissions structure") from None
