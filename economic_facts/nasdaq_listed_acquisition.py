"""One fixed Nasdaq Listed HTTPS request; provider gate, no qualification."""
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import StrEnum
import fcntl
import http.client
import os
from pathlib import Path
import re
import ssl
import stat
import time
import urllib.error
import urllib.request

from .nasdaq_listed_archive import (
    ENDPOINT, MAX_BODY_BYTES, NasdaqListedArchive, NasdaqListedArchiveError,
    NasdaqListedReceipt, canonical_timestamp,
)
from .nasdaq_listed_snapshot import UnsupportedNasdaqListedStructure, _parse_snapshot

SOCKET_TIMEOUT_SECONDS = 15
RESPONSE_DEADLINE_SECONDS = 60
REQUEST_SPACING_SECONDS = 1.0
_CHUNK_BYTES = 64 * 1024
_USER_AGENT = "PAM-NasdaqListedCapture/1.0"


class NasdaqListedAcquisitionReason(StrEnum):
    CONFIGURATION_ERROR = "CONFIGURATION_ERROR"
    RATE_LIMITED = "RATE_LIMITED"
    HTTP_ERROR = "HTTP_ERROR"
    REDIRECT_REJECTED = "REDIRECT_REJECTED"
    TIMEOUT = "TIMEOUT"
    NETWORK_ERROR = "NETWORK_ERROR"
    RESPONSE_TOO_LARGE = "RESPONSE_TOO_LARGE"
    INVALID_CONTENT_TYPE = "INVALID_CONTENT_TYPE"
    INVALID_RESPONSE = "INVALID_RESPONSE"
    UNSUPPORTED_SOURCE_VARIANT = "UNSUPPORTED_SOURCE_VARIANT"
    ARCHIVE_INTEGRITY_ERROR = "ARCHIVE_INTEGRITY_ERROR"


class NasdaqListedAcquisitionError(ValueError):
    """Closed category/status only. Never expose bodies, paths or provider messages."""

    def __init__(self, reason: NasdaqListedAcquisitionReason, *, status: int | None = None):
        self.reason = reason
        self.status = status
        super().__init__(reason.value + (f" (HTTP {status})" if status is not None else ""))


@dataclass(frozen=True, slots=True)
class NasdaqListedAcquisitionResult:
    receipt: NasdaqListedReceipt
    request_started_at: str
    response_completed_at: str


def _state_directory():
    # Separate from SEC, archive root, XDG settings and environment proxies.
    return Path.home() / ".investment_automation" / "nasdaq_trader_acquisition"


def _open_state_directory():
    """Descriptor-relative traversal, including ancestors; never follow symlinks."""
    directory = _state_directory()
    if not directory.is_absolute() or ".." in directory.parts:
        raise NasdaqListedAcquisitionError(NasdaqListedAcquisitionReason.CONFIGURATION_ERROR)
    fd = os.open("/", os.O_RDONLY | os.O_DIRECTORY)
    try:
        parts = directory.parts[1:]
        for index, component in enumerate(parts):
            # Only create the application/provider directories, never HOME.
            if index >= len(parts) - 2:
                try:
                    os.mkdir(component, 0o700, dir_fd=fd)
                    os.fsync(fd)
                except FileExistsError:
                    pass
            child = os.open(component, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd)
            fd = child
            if index >= len(parts) - 2:
                metadata = os.fstat(fd)
                if metadata.st_uid != os.getuid() or metadata.st_mode & 0o022:
                    raise NasdaqListedAcquisitionError(NasdaqListedAcquisitionReason.CONFIGURATION_ERROR)
        return fd
    except BaseException:
        os.close(fd)
        raise


@contextmanager
def _rate_gate():
    """Per-user/cross-process, one-second minimum wait with no burst credit.

    Hold the stable lock through response, preflight and publication. Contention
    fails immediately. Always wait a full interval after acquiring it, including
    after process restart/crash. There is no retry or wall-clock rate state.
    """
    directory_fd = lock_fd = None
    try:
        try:
            directory_fd = _open_state_directory()
            lock_fd = os.open("gate.lock", os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW | os.O_NONBLOCK,
                              0o600, dir_fd=directory_fd)
            metadata = os.fstat(lock_fd)
            if (not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1 or
                    metadata.st_uid != os.getuid() or metadata.st_mode & 0o022):
                raise NasdaqListedAcquisitionError(NasdaqListedAcquisitionReason.CONFIGURATION_ERROR)
            try:
                fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                raise NasdaqListedAcquisitionError(NasdaqListedAcquisitionReason.RATE_LIMITED) from None
            ready = time.monotonic() + REQUEST_SPACING_SECONDS
            while (remaining := ready - time.monotonic()) > 0:
                time.sleep(remaining)
        except OSError:
            raise NasdaqListedAcquisitionError(NasdaqListedAcquisitionReason.CONFIGURATION_ERROR) from None
        yield
    finally:
        if lock_fd is not None:
            os.close(lock_fd)
        if directory_fd is not None:
            os.close(directory_fd)


class _RejectRedirects(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        fp.close()
        raise NasdaqListedAcquisitionError(NasdaqListedAcquisitionReason.REDIRECT_REJECTED, status=code) from None


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
    except (NasdaqListedArchiveError, ValueError, OverflowError):
        raise NasdaqListedAcquisitionError(NasdaqListedAcquisitionReason.CONFIGURATION_ERROR) from None


def _check_status(status):
    if status == 200:
        return
    reason = (NasdaqListedAcquisitionReason.REDIRECT_REJECTED if 300 <= status < 400 else
              NasdaqListedAcquisitionReason.RATE_LIMITED if status == 429 else NasdaqListedAcquisitionReason.HTTP_ERROR)
    raise NasdaqListedAcquisitionError(reason, status=status) from None


def _single_header(headers, name):
    values = headers.get_all(name, [])
    if len(values) > 1:
        raise NasdaqListedAcquisitionError(NasdaqListedAcquisitionReason.INVALID_RESPONSE)
    return values[0] if values else None


def _read_body(response, deadline):
    content_type = _single_header(response.headers, "Content-Type") or ""
    if not re.fullmatch(r'text/plain(?:\s*;\s*charset\s*=\s*(?:utf-8|us-ascii|"utf-8"|"us-ascii"))?\s*',
                        content_type, flags=re.IGNORECASE):
        raise NasdaqListedAcquisitionError(NasdaqListedAcquisitionReason.INVALID_CONTENT_TYPE)
    encoding = _single_header(response.headers, "Content-Encoding")
    if encoding is not None and encoding.strip().lower() != "identity":
        raise NasdaqListedAcquisitionError(NasdaqListedAcquisitionReason.INVALID_RESPONSE)
    length = _single_header(response.headers, "Content-Length")
    declared = None
    if length is not None:
        if not re.fullmatch(r"[0-9]{1,20}", length.strip()):
            raise NasdaqListedAcquisitionError(NasdaqListedAcquisitionReason.INVALID_RESPONSE)
        declared = int(length)
        if declared > MAX_BODY_BYTES:
            raise NasdaqListedAcquisitionError(NasdaqListedAcquisitionReason.RESPONSE_TOO_LARGE)
    transfer = _single_header(response.headers, "Transfer-Encoding")
    if transfer is not None and (transfer.lower().strip() != "chunked" or declared is not None):
        raise NasdaqListedAcquisitionError(NasdaqListedAcquisitionReason.INVALID_RESPONSE)
    body = bytearray()
    while True:
        if time.monotonic() >= deadline:
            raise NasdaqListedAcquisitionError(NasdaqListedAcquisitionReason.TIMEOUT)
        # read1 performs at most one buffered/raw read, so progress is checked
        # between receives. No unbounded read or content decompression occurs.
        chunk = response.read1(min(_CHUNK_BYTES, MAX_BODY_BYTES + 1 - len(body)))
        if time.monotonic() >= deadline:
            raise NasdaqListedAcquisitionError(NasdaqListedAcquisitionReason.TIMEOUT)
        if not chunk:
            break
        body.extend(chunk)
        if len(body) > MAX_BODY_BYTES:
            raise NasdaqListedAcquisitionError(NasdaqListedAcquisitionReason.RESPONSE_TOO_LARGE)
    if declared is not None and len(body) != declared:
        raise NasdaqListedAcquisitionError(NasdaqListedAcquisitionReason.INVALID_RESPONSE)
    if "us-ascii" in content_type.lower() and not body.isascii():
        raise NasdaqListedAcquisitionError(NasdaqListedAcquisitionReason.INVALID_RESPONSE)
    return bytes(body)



def acquire_nasdaq_listed(*, archive_root: str | Path) -> NasdaqListedAcquisitionResult:
    """One fixed resource. Public callers supply only the local archive root."""
    try:
        archive = NasdaqListedArchive(archive_root)
    except (TypeError, ValueError):
        raise NasdaqListedAcquisitionError(NasdaqListedAcquisitionReason.CONFIGURATION_ERROR) from None
    request = urllib.request.Request(ENDPOINT, method="GET", headers={
        "User-Agent": _USER_AGENT, "Accept": "text/plain", "Accept-Encoding": "identity",
    })
    with _rate_gate():
        started = _timestamp()
        deadline = time.monotonic() + RESPONSE_DEADLINE_SECONDS
        try:
            with _open_response(request) as response:
                _check_status(response.status)
                if response.geturl() != ENDPOINT:
                    raise NasdaqListedAcquisitionError(NasdaqListedAcquisitionReason.REDIRECT_REJECTED)
                raw = _read_body(response, deadline)
                completed = _timestamp()
        except urllib.error.HTTPError as exc:
            status = exc.code
            exc.close()
            _check_status(status)
            raise NasdaqListedAcquisitionError(NasdaqListedAcquisitionReason.HTTP_ERROR, status=status) from None
        except TimeoutError:
            raise NasdaqListedAcquisitionError(NasdaqListedAcquisitionReason.TIMEOUT) from None
        except urllib.error.URLError as exc:
            reason = (NasdaqListedAcquisitionReason.TIMEOUT if isinstance(exc.reason, TimeoutError)
                      else NasdaqListedAcquisitionReason.NETWORK_ERROR)
            raise NasdaqListedAcquisitionError(reason) from None
        except (OSError, http.client.HTTPException):
            raise NasdaqListedAcquisitionError(NasdaqListedAcquisitionReason.NETWORK_ERROR) from None
        try:
            _parse_snapshot(raw)
        except UnsupportedNasdaqListedStructure:
            raise NasdaqListedAcquisitionError(NasdaqListedAcquisitionReason.UNSUPPORTED_SOURCE_VARIANT) from None
        captured = _timestamp()
        times = [datetime.fromisoformat(value.replace("Z", "+00:00"))
                 for value in (started, completed, captured)]
        if times != sorted(times):
            raise NasdaqListedAcquisitionError(NasdaqListedAcquisitionReason.CONFIGURATION_ERROR)
        try:
            receipt = archive._capture_live(raw, captured_at=captured)
        except (NasdaqListedArchiveError, OSError):
            raise NasdaqListedAcquisitionError(NasdaqListedAcquisitionReason.ARCHIVE_INTEGRITY_ERROR) from None
        return NasdaqListedAcquisitionResult(receipt, started, completed)
