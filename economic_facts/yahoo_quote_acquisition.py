"""One fixed Yahoo Chart HTTPS request with no cache, retry, or fallback."""
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

from .yahoo_quote_archive import (
    MAX_BODY_BYTES,
    YahooQuoteArchive,
    YahooQuoteArchiveError,
    YahooQuoteReceipt,
    canonical_endpoint,
    canonical_symbol,
    canonical_timestamp,
)


SOCKET_TIMEOUT_SECONDS = 15
RESPONSE_DEADLINE_SECONDS = 30
MAX_HEADER_COUNT = 64
MAX_HEADER_BYTES = 32 * 1024
_CHUNK_BYTES = 64 * 1024
_USER_AGENT = "Mozilla/5.0 (compatible; PAM-QuoteCapture/1.0)"


class YahooQuoteAcquisitionReason(StrEnum):
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


class YahooQuoteAcquisitionError(ValueError):
    """Closed status only; response bodies and provider messages are not exposed."""

    def __init__(self, reason, *, status=None):
        self.reason = reason
        self.status = status
        super().__init__(reason.value + (f" (HTTP {status})" if status is not None else ""))


@dataclass(frozen=True, slots=True)
class YahooQuoteAcquisitionResult:
    receipt: YahooQuoteReceipt
    request_started_at: str
    response_completed_at: str


class _RejectRedirects(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        fp.close()
        raise YahooQuoteAcquisitionError(
            YahooQuoteAcquisitionReason.REDIRECT_REJECTED, status=code) from None


def _open_response(request):
    # Explicitly ignore ambient proxy/environment configuration.
    opener = urllib.request.build_opener(
        urllib.request.ProxyHandler({}),
        urllib.request.HTTPSHandler(context=ssl.create_default_context()),
        _RejectRedirects(),
    )
    return opener.open(request, timeout=SOCKET_TIMEOUT_SECONDS)


def _timestamp():
    try:
        return canonical_timestamp(datetime.now(timezone.utc).isoformat())
    except (YahooQuoteArchiveError, ValueError, OverflowError):
        raise YahooQuoteAcquisitionError(YahooQuoteAcquisitionReason.CONFIGURATION_ERROR) from None


def _check_status(status):
    if status == 200:
        return
    if 300 <= status < 400:
        reason = YahooQuoteAcquisitionReason.REDIRECT_REJECTED
    elif status == 429:
        reason = YahooQuoteAcquisitionReason.RATE_LIMITED
    else:
        reason = YahooQuoteAcquisitionReason.HTTP_ERROR
    raise YahooQuoteAcquisitionError(reason, status=status) from None


def _single_header(headers, name):
    values = headers.get_all(name, [])
    if len(values) > 1:
        raise YahooQuoteAcquisitionError(YahooQuoteAcquisitionReason.INVALID_RESPONSE)
    return values[0] if values else None


def _validate_headers(headers):
    items = list(headers.raw_items())
    if len(items) > MAX_HEADER_COUNT:
        raise YahooQuoteAcquisitionError(YahooQuoteAcquisitionReason.RESPONSE_HEADERS_TOO_LARGE)
    size = 0
    for name, value in items:
        if type(name) is not str or type(value) is not str:
            raise YahooQuoteAcquisitionError(YahooQuoteAcquisitionReason.INVALID_RESPONSE)
        size += len(name.encode("ascii", "strict")) + len(value.encode("latin-1", "strict")) + 4
    if size > MAX_HEADER_BYTES:
        raise YahooQuoteAcquisitionError(YahooQuoteAcquisitionReason.RESPONSE_HEADERS_TOO_LARGE)


def _read_body(response, deadline):
    try:
        _validate_headers(response.headers)
    except UnicodeError:
        raise YahooQuoteAcquisitionError(YahooQuoteAcquisitionReason.INVALID_RESPONSE) from None
    content_type = _single_header(response.headers, "Content-Type") or ""
    if not re.fullmatch(
        r'application/json(?:\s*;\s*charset\s*=\s*(?:utf-8|"utf-8"))?\s*',
        content_type,
        flags=re.IGNORECASE,
    ):
        raise YahooQuoteAcquisitionError(YahooQuoteAcquisitionReason.INVALID_CONTENT_TYPE)
    encoding = _single_header(response.headers, "Content-Encoding")
    if encoding is not None and encoding.strip().lower() != "identity":
        raise YahooQuoteAcquisitionError(YahooQuoteAcquisitionReason.INVALID_RESPONSE)
    length = _single_header(response.headers, "Content-Length")
    declared = None
    if length is not None:
        if re.fullmatch(r"[0-9]{1,20}", length.strip()) is None:
            raise YahooQuoteAcquisitionError(YahooQuoteAcquisitionReason.INVALID_RESPONSE)
        declared = int(length)
        if declared > MAX_BODY_BYTES:
            raise YahooQuoteAcquisitionError(YahooQuoteAcquisitionReason.RESPONSE_TOO_LARGE)
    transfer = _single_header(response.headers, "Transfer-Encoding")
    if transfer is not None and (transfer.lower().strip() != "chunked" or declared is not None):
        raise YahooQuoteAcquisitionError(YahooQuoteAcquisitionReason.INVALID_RESPONSE)
    body = bytearray()
    while True:
        if time.monotonic() >= deadline:
            raise YahooQuoteAcquisitionError(YahooQuoteAcquisitionReason.TIMEOUT)
        chunk = response.read1(min(_CHUNK_BYTES, MAX_BODY_BYTES + 1 - len(body)))
        if time.monotonic() >= deadline:
            raise YahooQuoteAcquisitionError(YahooQuoteAcquisitionReason.TIMEOUT)
        if not chunk:
            break
        body.extend(chunk)
        if len(body) > MAX_BODY_BYTES:
            raise YahooQuoteAcquisitionError(YahooQuoteAcquisitionReason.RESPONSE_TOO_LARGE)
    if not body or (declared is not None and declared != len(body)):
        raise YahooQuoteAcquisitionError(YahooQuoteAcquisitionReason.INVALID_RESPONSE)
    return bytes(body)


def acquire_yahoo_current_quote(
    *, symbol: str, archive_root: str | Path,
) -> YahooQuoteAcquisitionResult:
    """Capture exactly one fixed-profile Chart response for one canonical symbol."""
    try:
        symbol = canonical_symbol(symbol)
        endpoint = canonical_endpoint(symbol)
        archive = YahooQuoteArchive(archive_root)
    except (TypeError, ValueError):
        raise YahooQuoteAcquisitionError(YahooQuoteAcquisitionReason.CONFIGURATION_ERROR) from None
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
                raise YahooQuoteAcquisitionError(YahooQuoteAcquisitionReason.REDIRECT_REJECTED)
            raw = _read_body(response, deadline)
            completed = _timestamp()
    except YahooQuoteAcquisitionError:
        raise
    except urllib.error.HTTPError as exc:
        status = exc.code
        exc.close()
        _check_status(status)
        raise YahooQuoteAcquisitionError(
            YahooQuoteAcquisitionReason.HTTP_ERROR, status=status) from None
    except TimeoutError:
        raise YahooQuoteAcquisitionError(YahooQuoteAcquisitionReason.TIMEOUT) from None
    except urllib.error.URLError as exc:
        reason = (YahooQuoteAcquisitionReason.TIMEOUT
                  if isinstance(exc.reason, TimeoutError)
                  else YahooQuoteAcquisitionReason.NETWORK_ERROR)
        raise YahooQuoteAcquisitionError(reason) from None
    except (OSError, http.client.HTTPException):
        raise YahooQuoteAcquisitionError(YahooQuoteAcquisitionReason.NETWORK_ERROR) from None
    captured = _timestamp()
    times = tuple(datetime.fromisoformat(value.replace("Z", "+00:00"))
                  for value in (started, completed, captured))
    if times != tuple(sorted(times)):
        raise YahooQuoteAcquisitionError(YahooQuoteAcquisitionReason.CONFIGURATION_ERROR)
    try:
        receipt = archive._capture_live(raw, symbol=symbol, captured_at=captured)
    except (YahooQuoteArchiveError, OSError):
        raise YahooQuoteAcquisitionError(YahooQuoteAcquisitionReason.ARCHIVE_INTEGRITY_ERROR) from None
    return YahooQuoteAcquisitionResult(receipt, started, completed)
