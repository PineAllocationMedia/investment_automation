"""Controlled capture of the fixed SEC ticker/exchange association resource."""
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
import http.client
from pathlib import Path
import time
import urllib.error
import urllib.request

from . import sec_acquisition as _sec
from .sec_ticker_exchange_archive import (
    ENDPOINT, SecTickerExchangeArchive, SecTickerExchangeArchiveError,
    SecTickerExchangeReceipt,
)
from .sec_ticker_exchange_snapshot import (
    UnsupportedSecTickerExchangeStructure, _parse_snapshot,
)


class SecTickerExchangeAcquisitionReason(StrEnum):
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


class SecTickerExchangeAcquisitionError(ValueError):
    """Closed reason/status only; never source bodies, paths, or contact data."""

    def __init__(self, reason: SecTickerExchangeAcquisitionReason, *, status: int | None = None):
        self.reason = reason
        self.status = status
        super().__init__(reason.value + (f" (HTTP {status})" if status is not None else ""))


@dataclass(frozen=True, slots=True)
class SecTickerExchangeAcquisitionResult:
    receipt: SecTickerExchangeReceipt
    request_started_at: str
    response_completed_at: str


def acquire_sec_ticker_exchange_associations(
    *, archive_root: str | Path,
) -> SecTickerExchangeAcquisitionResult:
    """Perform one fixed reviewed SEC request and publish its exact bytes."""
    try:
        archive = SecTickerExchangeArchive(archive_root)
    except (TypeError, ValueError):
        raise SecTickerExchangeAcquisitionError(
            SecTickerExchangeAcquisitionReason.CONFIGURATION_ERROR) from None
    try:
        request = urllib.request.Request(ENDPOINT, method="GET", headers={
            "User-Agent": _sec._user_agent(),
            "Accept": "application/json",
            "Accept-Encoding": "identity",
        })
        with _sec._rate_gate():
            started = _sec._timestamp()
            deadline = time.monotonic() + _sec.RESPONSE_DEADLINE_SECONDS
            try:
                with _sec._open_response(request) as response:
                    _sec._check_status(response.status)
                    if response.geturl() != ENDPOINT:
                        raise SecTickerExchangeAcquisitionError(
                            SecTickerExchangeAcquisitionReason.REDIRECT_REJECTED)
                    raw = _sec._read_body(response, deadline)
                    completed = _sec._timestamp()
            except urllib.error.HTTPError as exc:
                status = exc.code
                exc.close()
                _sec._check_status(status)
                raise SecTickerExchangeAcquisitionError(
                    SecTickerExchangeAcquisitionReason.HTTP_ERROR, status=status) from None
            except TimeoutError:
                raise SecTickerExchangeAcquisitionError(
                    SecTickerExchangeAcquisitionReason.TIMEOUT) from None
            except urllib.error.URLError as exc:
                reason = (SecTickerExchangeAcquisitionReason.TIMEOUT
                          if isinstance(exc.reason, TimeoutError)
                          else SecTickerExchangeAcquisitionReason.NETWORK_ERROR)
                raise SecTickerExchangeAcquisitionError(reason) from None
            except (OSError, http.client.HTTPException):
                raise SecTickerExchangeAcquisitionError(
                    SecTickerExchangeAcquisitionReason.NETWORK_ERROR) from None
            try:
                _parse_snapshot(raw)
            except UnsupportedSecTickerExchangeStructure:
                raise SecTickerExchangeAcquisitionError(
                    SecTickerExchangeAcquisitionReason.UNSUPPORTED_SOURCE_VARIANT) from None
            captured = _sec._timestamp()
            times = [datetime.fromisoformat(value.replace("Z", "+00:00"))
                     for value in (started, completed, captured)]
            if times != sorted(times):
                raise SecTickerExchangeAcquisitionError(
                    SecTickerExchangeAcquisitionReason.CONFIGURATION_ERROR)
            try:
                receipt = archive._capture_live(raw, captured_at=captured)
            except (SecTickerExchangeArchiveError, OSError, TypeError):
                raise SecTickerExchangeAcquisitionError(
                    SecTickerExchangeAcquisitionReason.ARCHIVE_INTEGRITY_ERROR) from None
            return SecTickerExchangeAcquisitionResult(receipt, started, completed)
    except _sec.SecAcquisitionError as exc:
        raise SecTickerExchangeAcquisitionError(
            SecTickerExchangeAcquisitionReason(exc.reason.value), status=exc.status) from None
