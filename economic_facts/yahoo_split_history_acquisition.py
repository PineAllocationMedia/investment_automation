"""One fixed Yahoo Chart split-history HTTPS request; no retry or fallback."""
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import StrEnum
import http.client
from pathlib import Path
import re
import ssl
import time
import urllib.error
import urllib.request

from .yahoo_split_history_archive import (
    MAX_BODY_BYTES,
    YahooSplitHistoryArchive,
    YahooSplitHistoryArchiveError,
    YahooSplitHistoryReceipt,
    canonical_endpoint,
    canonical_epoch,
    canonical_symbol,
    canonical_timestamp,
)

SOCKET_TIMEOUT_SECONDS = 15
RESPONSE_DEADLINE_SECONDS = 30
MAX_HEADER_COUNT = 64
MAX_HEADER_BYTES = 32 * 1024
_CHUNK_BYTES = 64 * 1024
_USER_AGENT = "Mozilla/5.0 (compatible; PAM-SplitHistoryCapture/1.0)"


class YahooSplitHistoryAcquisitionReason(StrEnum):
    CONFIGURATION_ERROR = "CONFIGURATION_ERROR"
    HTTP_ERROR = "HTTP_ERROR"
    RATE_LIMITED = "RATE_LIMITED"
    REDIRECT_REJECTED = "REDIRECT_REJECTED"
    TIMEOUT = "TIMEOUT"
    NETWORK_ERROR = "NETWORK_ERROR"
    RESPONSE_TOO_LARGE = "RESPONSE_TOO_LARGE"
    RESPONSE_HEADERS_TOO_LARGE = "RESPONSE_HEADERS_TOO_LARGE"
    INVALID_CONTENT_TYPE = "INVALID_CONTENT_TYPE"
    INVALID_RESPONSE = "INVALID_RESPONSE"
    ARCHIVE_INTEGRITY_ERROR = "ARCHIVE_INTEGRITY_ERROR"


class YahooSplitHistoryAcquisitionError(ValueError):
    def __init__(self, reason, *, status=None):
        self.reason = reason
        self.status = status
        super().__init__(reason.value + (f" (HTTP {status})" if status is not None else ""))


@dataclass(frozen=True, slots=True)
class YahooSplitHistoryAcquisitionResult:
    receipt: YahooSplitHistoryReceipt
    request_started_at: str
    response_completed_at: str


class _RejectRedirects(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        fp.close()
        raise YahooSplitHistoryAcquisitionError(
            YahooSplitHistoryAcquisitionReason.REDIRECT_REJECTED, status=code)


def _open_response(request):
    opener = urllib.request.build_opener(
        urllib.request.ProxyHandler({}),
        urllib.request.HTTPSHandler(context=ssl.create_default_context()),
        _RejectRedirects(),
    )
    return opener.open(request, timeout=SOCKET_TIMEOUT_SECONDS)


def _timestamp():
    try:
        return canonical_timestamp(datetime.now(timezone.utc).isoformat())
    except (YahooSplitHistoryArchiveError, ValueError, OverflowError):
        raise YahooSplitHistoryAcquisitionError(
            YahooSplitHistoryAcquisitionReason.CONFIGURATION_ERROR) from None


def _check_status(status):
    if status == 200:
        return
    if 300 <= status < 400:
        reason = YahooSplitHistoryAcquisitionReason.REDIRECT_REJECTED
    elif status == 429:
        reason = YahooSplitHistoryAcquisitionReason.RATE_LIMITED
    else:
        reason = YahooSplitHistoryAcquisitionReason.HTTP_ERROR
    raise YahooSplitHistoryAcquisitionError(reason, status=status)


def _single_header(headers, name):
    values = headers.get_all(name, [])
    if len(values) > 1:
        raise YahooSplitHistoryAcquisitionError(
            YahooSplitHistoryAcquisitionReason.INVALID_RESPONSE)
    return values[0] if values else None


def _read_body(response, deadline):
    items = list(response.headers.raw_items())
    try:
        if len(items) > MAX_HEADER_COUNT:
            raise YahooSplitHistoryAcquisitionError(
                YahooSplitHistoryAcquisitionReason.RESPONSE_HEADERS_TOO_LARGE)
        size = sum(len(name.encode("ascii", "strict"))
                   + len(value.encode("latin-1", "strict")) + 4
                   for name, value in items)
    except UnicodeError:
        raise YahooSplitHistoryAcquisitionError(
            YahooSplitHistoryAcquisitionReason.INVALID_RESPONSE) from None
    if size > MAX_HEADER_BYTES:
        raise YahooSplitHistoryAcquisitionError(
            YahooSplitHistoryAcquisitionReason.RESPONSE_HEADERS_TOO_LARGE)
    content_type = _single_header(response.headers, "Content-Type") or ""
    if re.fullmatch(
        r'application/json(?:\s*;\s*charset\s*=\s*(?:utf-8|"utf-8"))?\s*',
        content_type, flags=re.IGNORECASE,
    ) is None:
        raise YahooSplitHistoryAcquisitionError(
            YahooSplitHistoryAcquisitionReason.INVALID_CONTENT_TYPE)
    encoding = _single_header(response.headers, "Content-Encoding")
    if encoding is not None and encoding.strip().lower() != "identity":
        raise YahooSplitHistoryAcquisitionError(
            YahooSplitHistoryAcquisitionReason.INVALID_RESPONSE)
    length = _single_header(response.headers, "Content-Length")
    declared = None
    if length is not None:
        if re.fullmatch(r"[0-9]{1,20}", length.strip()) is None:
            raise YahooSplitHistoryAcquisitionError(
                YahooSplitHistoryAcquisitionReason.INVALID_RESPONSE)
        declared = int(length)
        if declared > MAX_BODY_BYTES:
            raise YahooSplitHistoryAcquisitionError(
                YahooSplitHistoryAcquisitionReason.RESPONSE_TOO_LARGE)
    body = bytearray()
    while True:
        if time.monotonic() >= deadline:
            raise YahooSplitHistoryAcquisitionError(
                YahooSplitHistoryAcquisitionReason.TIMEOUT)
        chunk = response.read1(min(_CHUNK_BYTES, MAX_BODY_BYTES + 1 - len(body)))
        if not chunk:
            break
        body.extend(chunk)
        if len(body) > MAX_BODY_BYTES:
            raise YahooSplitHistoryAcquisitionError(
                YahooSplitHistoryAcquisitionReason.RESPONSE_TOO_LARGE)
    if not body or (declared is not None and declared != len(body)):
        raise YahooSplitHistoryAcquisitionError(
            YahooSplitHistoryAcquisitionReason.INVALID_RESPONSE)
    return bytes(body)


def acquire_yahoo_split_history(
    *, symbol: str, start_epoch: int, end_epoch: int, archive_root: str | Path,
) -> YahooSplitHistoryAcquisitionResult:
    """Capture one exact explicit-interval Chart split response."""
    try:
        symbol = canonical_symbol(symbol)
        start_epoch = canonical_epoch(start_epoch, "start")
        end_epoch = canonical_epoch(end_epoch, "end")
        endpoint = canonical_endpoint(symbol, start_epoch, end_epoch)
        archive = YahooSplitHistoryArchive(archive_root)
    except (TypeError, ValueError):
        raise YahooSplitHistoryAcquisitionError(
            YahooSplitHistoryAcquisitionReason.CONFIGURATION_ERROR) from None
    request = urllib.request.Request(endpoint, method="GET", headers={
        "User-Agent": _USER_AGENT,
        "Accept": "application/json",
        "Accept-Encoding": "identity",
    })
    started = _timestamp()
    deadline = time.monotonic() + RESPONSE_DEADLINE_SECONDS
    try:
        with _open_response(request) as response:
            _check_status(response.status)
            if response.geturl() != endpoint:
                raise YahooSplitHistoryAcquisitionError(
                    YahooSplitHistoryAcquisitionReason.REDIRECT_REJECTED)
            raw = _read_body(response, deadline)
            completed = _timestamp()
    except YahooSplitHistoryAcquisitionError:
        raise
    except urllib.error.HTTPError as exc:
        status = exc.code
        exc.close()
        _check_status(status)
        raise YahooSplitHistoryAcquisitionError(
            YahooSplitHistoryAcquisitionReason.HTTP_ERROR, status=status) from None
    except TimeoutError:
        raise YahooSplitHistoryAcquisitionError(
            YahooSplitHistoryAcquisitionReason.TIMEOUT) from None
    except urllib.error.URLError as exc:
        reason = (YahooSplitHistoryAcquisitionReason.TIMEOUT
                  if isinstance(exc.reason, TimeoutError)
                  else YahooSplitHistoryAcquisitionReason.NETWORK_ERROR)
        raise YahooSplitHistoryAcquisitionError(reason) from None
    except (OSError, http.client.HTTPException):
        raise YahooSplitHistoryAcquisitionError(
            YahooSplitHistoryAcquisitionReason.NETWORK_ERROR) from None
    captured = _timestamp()
    times = tuple(datetime.fromisoformat(value.replace("Z", "+00:00"))
                  for value in (started, completed, captured))
    if times != tuple(sorted(times)):
        raise YahooSplitHistoryAcquisitionError(
            YahooSplitHistoryAcquisitionReason.CONFIGURATION_ERROR)
    try:
        receipt = archive._capture_live(
            raw, symbol=symbol, start_epoch=start_epoch, end_epoch=end_epoch,
            captured_at=captured)
    except (YahooSplitHistoryArchiveError, OSError):
        raise YahooSplitHistoryAcquisitionError(
            YahooSplitHistoryAcquisitionReason.ARCHIVE_INTEGRITY_ERROR) from None
    return YahooSplitHistoryAcquisitionResult(receipt, started, completed)
