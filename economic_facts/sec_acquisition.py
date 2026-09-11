"""One canonical SEC request -> preflight -> exact-byte LIVE archive receipt.

No model admission or remote attestation. Public callers supply only CIK and
archive root; transport, clocks, authority and rate policy are private/fixed.
"""
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import StrEnum
import fcntl
import http.client
import json
import math
import os
from pathlib import Path
import re
import ssl
import stat
import time
import urllib.error
import urllib.request

from .sec_archive import (ArchiveError, LIVE_ACQUISITION_CONTRACT_VERSION, SecArchive,
                          canonical_timestamp, endpoint_for, reject_constant, unique_pairs)

USER_AGENT_ENV = "INVESTMENT_AUTOMATION_SEC_USER_AGENT"
MAX_USER_AGENT_LENGTH = 256
MAX_BODY_BYTES = 32 * 1024 * 1024
SOCKET_TIMEOUT_SECONDS = 15
RESPONSE_DEADLINE_SECONDS = 60
REQUEST_SPACING_SECONDS = 0.25  # Four/second, with no accumulated burst credit.
_CHUNK_BYTES = 64 * 1024
_CONTACT = re.compile(r"[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+")
_SAFE_HEADERS = ("Content-Type", "Date", "ETag", "Last-Modified")


class AcquisitionReason(StrEnum):
    CONFIGURATION_ERROR = "CONFIGURATION_ERROR"
    RATE_LIMITED = "RATE_LIMITED"
    HTTP_ERROR = "HTTP_ERROR"
    REDIRECT_REJECTED = "REDIRECT_REJECTED"
    TIMEOUT = "TIMEOUT"
    NETWORK_ERROR = "NETWORK_ERROR"
    RESPONSE_TOO_LARGE = "RESPONSE_TOO_LARGE"
    INVALID_CONTENT_TYPE = "INVALID_CONTENT_TYPE"
    INVALID_RESPONSE = "INVALID_RESPONSE"
    ARCHIVE_ERROR = "ARCHIVE_ERROR"


class SecAcquisitionError(ValueError):
    """Safe category/status only; never echo response bodies or contact identity."""

    def __init__(self, reason: AcquisitionReason, *, status: int | None = None):
        self.reason = reason
        self.status = status
        super().__init__(reason.value + (f" (HTTP {status})" if status is not None else ""))


@dataclass(frozen=True, slots=True)
class SecAcquisitionResult:
    endpoint: str
    cik: str
    status: int
    content_sha256: str
    byte_length: int
    request_started_at: str
    response_completed_at: str
    captured_at: str
    archive_receipt_id: str
    acquisition_contract_version: str
    declared_user_agent_used: bool
    safe_response_metadata: tuple[tuple[str, str], ...]


def _user_agent():
    value = os.environ.get(USER_AGENT_ENV, "")
    if (not value or value != value.strip() or len(value) > MAX_USER_AGENT_LENGTH
            or any(ord(c) < 32 or ord(c) > 126 for c in value)
            or "local-user@example.com" in value.lower()
            or value.lower().startswith(("mozilla/", "chrome/", "safari/", "edge/"))):
        raise SecAcquisitionError(AcquisitionReason.CONFIGURATION_ERROR)
    contact = _CONTACT.search(value)
    # Require both a named organization/application and an administrative email.
    if contact is None or not re.search(r"[A-Za-z]", value[:contact.start()].strip()):
        raise SecAcquisitionError(AcquisitionReason.CONFIGURATION_ERROR)
    return value


def _state_directory():
    # Deliberately independent of archive root, XDG and proxy configuration.
    return Path.home() / ".investment_automation" / "sec_acquisition"


@contextmanager
def _rate_gate():
    """One local user, all archives/processes. Contention fails without retry.

    Every lock holder waits a full interval BEFORE requesting, even on a fresh
    process or after a crash. Keep the lock through response/publication. Thus
    no wall-clock state, stale timestamp recovery or token bursts are needed.
    The stable lock inode must never be removed while acquisition is in use.
    """
    directory_fd = lock_fd = None
    try:
        directory = _state_directory()
        directory.mkdir(mode=0o700, parents=True, exist_ok=True)
        directory_fd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        metadata = os.fstat(directory_fd)
        if metadata.st_uid != os.getuid() or metadata.st_mode & 0o022:
            raise SecAcquisitionError(AcquisitionReason.CONFIGURATION_ERROR)
        lock_fd = os.open("gate.lock", os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW | os.O_NONBLOCK,
                          0o600, dir_fd=directory_fd)
        metadata = os.fstat(lock_fd)
        if (not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1
                or metadata.st_uid != os.getuid() or metadata.st_mode & 0o022):
            raise SecAcquisitionError(AcquisitionReason.CONFIGURATION_ERROR)
        try:
            fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise SecAcquisitionError(AcquisitionReason.RATE_LIMITED) from None
        ready = time.monotonic() + REQUEST_SPACING_SECONDS
        while (remaining := ready - time.monotonic()) > 0:
            time.sleep(remaining)
    except OSError:
        if lock_fd is not None:
            os.close(lock_fd)
            lock_fd = None
        if directory_fd is not None:
            os.close(directory_fd)
            directory_fd = None
        raise SecAcquisitionError(AcquisitionReason.CONFIGURATION_ERROR) from None
    except BaseException:
        if lock_fd is not None:
            os.close(lock_fd)
        if directory_fd is not None:
            os.close(directory_fd)
        raise
    try:
        yield
    finally:
        os.close(lock_fd)  # Closing releases flock, including on failure.
        os.close(directory_fd)


class _RejectRedirects(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        fp.close()
        raise SecAcquisitionError(AcquisitionReason.REDIRECT_REJECTED, status=code) from None


def _open_response(request):
    # No environment proxies, no global opener, default verified trust store.
    opener = urllib.request.build_opener(
        urllib.request.ProxyHandler({}),
        urllib.request.HTTPSHandler(context=ssl.create_default_context()),
        _RejectRedirects(),
    )
    return opener.open(request, timeout=SOCKET_TIMEOUT_SECONDS)


def _utc_now():
    return datetime.now(timezone.utc)


def _timestamp():
    try:
        return canonical_timestamp(_utc_now().isoformat())
    except (ArchiveError, ValueError, OverflowError):
        raise SecAcquisitionError(AcquisitionReason.CONFIGURATION_ERROR) from None


def _check_status(status):
    if status == 200:
        return
    reason = (AcquisitionReason.REDIRECT_REJECTED if 300 <= status < 400 else
              AcquisitionReason.RATE_LIMITED if status == 429 else AcquisitionReason.HTTP_ERROR)
    raise SecAcquisitionError(reason, status=status) from None


def _single_header(headers, name):
    values = headers.get_all(name, [])
    if len(values) > 1:
        raise SecAcquisitionError(AcquisitionReason.INVALID_RESPONSE)
    return values[0] if values else None


def _read_body(response, deadline):
    content_type = _single_header(response.headers, "Content-Type") or ""
    if not re.fullmatch(r'application/json(?:\s*;\s*charset\s*=\s*(?:utf-8|"utf-8"))?\s*',
                        content_type, flags=re.IGNORECASE):
        raise SecAcquisitionError(AcquisitionReason.INVALID_CONTENT_TYPE)
    encoding = _single_header(response.headers, "Content-Encoding")
    if encoding is not None and encoding.strip().lower() != "identity":
        raise SecAcquisitionError(AcquisitionReason.INVALID_RESPONSE)
    length = _single_header(response.headers, "Content-Length")
    declared = None
    if length is not None:
        if not re.fullmatch(r"[0-9]{1,20}", length.strip()):
            raise SecAcquisitionError(AcquisitionReason.INVALID_RESPONSE)
        declared = int(length)
        if declared > MAX_BODY_BYTES:
            raise SecAcquisitionError(AcquisitionReason.RESPONSE_TOO_LARGE)
    transfer = _single_header(response.headers, "Transfer-Encoding")
    if transfer is not None and (transfer.lower().strip() != "chunked" or declared is not None):
        raise SecAcquisitionError(AcquisitionReason.INVALID_RESPONSE)
    body = bytearray()
    while True:
        if time.monotonic() >= deadline:
            raise SecAcquisitionError(AcquisitionReason.TIMEOUT)
        # read1 performs at most one buffered/raw read, so progress is checked
        # between receives. No unbounded read or content decompression occurs.
        chunk = response.read1(min(_CHUNK_BYTES, MAX_BODY_BYTES + 1 - len(body)))
        if time.monotonic() >= deadline:
            raise SecAcquisitionError(AcquisitionReason.TIMEOUT)
        if not chunk:
            break
        body.extend(chunk)
        if len(body) > MAX_BODY_BYTES:
            raise SecAcquisitionError(AcquisitionReason.RESPONSE_TOO_LARGE)
    if declared is not None and len(body) != declared:
        raise SecAcquisitionError(AcquisitionReason.INVALID_RESPONSE)
    return bytes(body)


def _finite_float(value):
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("Nonfinite number")
    return number


def _preflight(raw, cik):
    try:
        source = json.loads(raw.decode("utf-8"), object_pairs_hook=unique_pairs,
                            parse_constant=reject_constant, parse_float=_finite_float)
        if type(source) is not dict or type(source.get("facts")) is not dict:
            raise ValueError("Companyfacts object required")
        source_cik = source.get("cik")
        if not ((type(source_cik) is int and 0 <= source_cik <= 9999999999)
                or (type(source_cik) is str and re.fullmatch(r"[0-9]{1,10}", source_cik))):
            raise ValueError("Invalid source CIK")
        if str(source_cik).zfill(10) != cik:
            raise ValueError("Wrong source CIK")
    except (ValueError, UnicodeError, RecursionError, OverflowError):
        raise SecAcquisitionError(AcquisitionReason.INVALID_RESPONSE) from None


def _safe_metadata(headers, user_agent):
    contact = _CONTACT.search(user_agent).group().lower()
    return tuple((name, value) for name in _SAFE_HEADERS
                 if (value := headers.get(name)) is not None
                 and len(value) <= 1024 and all(32 <= ord(c) <= 126 for c in value)
                 and contact not in value.lower() and user_agent.lower() not in value.lower())


def acquire_companyfacts(*, cik: str, archive_root: str | Path) -> SecAcquisitionResult:
    """Perform one request. No public timestamp, URL, transport or retry input."""
    try:
        endpoint = endpoint_for(cik)
    except ArchiveError:
        raise SecAcquisitionError(AcquisitionReason.CONFIGURATION_ERROR) from None
    user_agent = _user_agent()
    request = urllib.request.Request(endpoint, method="GET", headers={
        "User-Agent": user_agent, "Accept": "application/json", "Accept-Encoding": "identity",
    })
    with _rate_gate():
        request_started_at = _timestamp()
        deadline = time.monotonic() + RESPONSE_DEADLINE_SECONDS
        try:
            with _open_response(request) as response:
                _check_status(response.status)
                if response.geturl() != endpoint:
                    raise SecAcquisitionError(AcquisitionReason.REDIRECT_REJECTED)
                raw = _read_body(response, deadline)
                response_completed_at = _timestamp()
                metadata = _safe_metadata(response.headers, user_agent)
        except urllib.error.HTTPError as exc:
            status = exc.code
            exc.close()
            _check_status(status)
            raise SecAcquisitionError(AcquisitionReason.HTTP_ERROR, status=status) from None
        except TimeoutError:
            raise SecAcquisitionError(AcquisitionReason.TIMEOUT) from None
        except urllib.error.URLError as exc:
            reason = AcquisitionReason.TIMEOUT if isinstance(exc.reason, TimeoutError) else AcquisitionReason.NETWORK_ERROR
            raise SecAcquisitionError(reason) from None
        except (OSError, http.client.HTTPException):
            raise SecAcquisitionError(AcquisitionReason.NETWORK_ERROR) from None
        _preflight(raw, cik)
        captured_at = _timestamp()
        times = [datetime.fromisoformat(value.replace("Z", "+00:00")) for value in
                 (request_started_at, response_completed_at, captured_at)]
        if times != sorted(times):
            raise SecAcquisitionError(AcquisitionReason.CONFIGURATION_ERROR)
        try:
            receipt = SecArchive(archive_root)._capture_live(raw, cik=cik, captured_at=captured_at)
        except (ArchiveError, OSError, TypeError):
            raise SecAcquisitionError(AcquisitionReason.ARCHIVE_ERROR) from None
        return SecAcquisitionResult(endpoint, cik, 200, receipt.content_sha256, receipt.byte_length,
                                    request_started_at, response_completed_at, receipt.captured_at,
                                    receipt.receipt_id, LIVE_ACQUISITION_CONTRACT_VERSION, True, metadata)
