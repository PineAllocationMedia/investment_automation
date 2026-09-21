"""Controlled Submissions JSON capture, sharing the existing SEC transport gate."""
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
import http.client
from pathlib import Path
import time
import urllib.error
import urllib.request

from . import sec_acquisition as _sec
from .sec_submissions_archive import (
    SecSubmissionsArchive, SubmissionsArchiveError, SubmissionsReceipt,
    UnsupportedSubmissionsStructure, _parse_resource, endpoint_for,
    validate_history_filename, validate_receipt_id,
)


class SubmissionsAcquisitionReason(StrEnum):
    CONFIGURATION_ERROR = "CONFIGURATION_ERROR"
    INVALID_REQUEST = "INVALID_REQUEST"
    RATE_LIMITED = "RATE_LIMITED"
    HTTP_ERROR = "HTTP_ERROR"
    REDIRECT_REJECTED = "REDIRECT_REJECTED"
    TIMEOUT = "TIMEOUT"
    NETWORK_ERROR = "NETWORK_ERROR"
    RESPONSE_TOO_LARGE = "RESPONSE_TOO_LARGE"
    INVALID_CONTENT_TYPE = "INVALID_CONTENT_TYPE"
    INVALID_RESPONSE = "INVALID_RESPONSE"
    UNSUPPORTED_STRUCTURE = "UNSUPPORTED_STRUCTURE"
    ARCHIVE_INTEGRITY_ERROR = "ARCHIVE_INTEGRITY_ERROR"


class SecSubmissionsAcquisitionError(ValueError):
    def __init__(self, reason: SubmissionsAcquisitionReason, *, status: int | None = None):
        self.reason = reason
        self.status = status
        super().__init__(reason.value + (f" (HTTP {status})" if status is not None else ""))


@dataclass(frozen=True, slots=True)
class SecSubmissionsAcquisitionResult:
    receipt: SubmissionsReceipt
    request_started_at: str
    response_completed_at: str


def _require(condition, reason):
    if not condition:
        raise SecSubmissionsAcquisitionError(reason)


def _archive(root):
    try:
        archive = SecSubmissionsArchive(root)
        _require("\x00" not in str(archive.root), SubmissionsAcquisitionReason.CONFIGURATION_ERROR)
        return archive
    except (TypeError, ValueError):
        raise SecSubmissionsAcquisitionError(SubmissionsAcquisitionReason.CONFIGURATION_ERROR) from None


def _capture(archive, cik, *, parent=None, filename=None):
    endpoint = endpoint_for(cik, filename)
    try:
        request = urllib.request.Request(endpoint, method="GET", headers={
            "User-Agent": _sec._user_agent(), "Accept": "application/json", "Accept-Encoding": "identity",
        })
        with _sec._rate_gate():
            started = _sec._timestamp()
            deadline = time.monotonic() + _sec.RESPONSE_DEADLINE_SECONDS
            try:
                with _sec._open_response(request) as response:
                    _sec._check_status(response.status)
                    _require(response.geturl() == endpoint, SubmissionsAcquisitionReason.REDIRECT_REJECTED)
                    raw = _sec._read_body(response, deadline)
                    completed = _sec._timestamp()
            except urllib.error.HTTPError as exc:
                status = exc.code
                exc.close()
                _sec._check_status(status)
                raise SecSubmissionsAcquisitionError(SubmissionsAcquisitionReason.HTTP_ERROR, status=status) from None
            except TimeoutError:
                raise SecSubmissionsAcquisitionError(SubmissionsAcquisitionReason.TIMEOUT) from None
            except urllib.error.URLError as exc:
                reason = (SubmissionsAcquisitionReason.TIMEOUT if isinstance(exc.reason, TimeoutError)
                          else SubmissionsAcquisitionReason.NETWORK_ERROR)
                raise SecSubmissionsAcquisitionError(reason) from None
            except (OSError, http.client.HTTPException):
                raise SecSubmissionsAcquisitionError(SubmissionsAcquisitionReason.NETWORK_ERROR) from None
            _parse_resource(raw, cik, "ROOT" if parent is None else "HISTORY")
            captured = _sec._timestamp()
            times = [datetime.fromisoformat(value.replace("Z", "+00:00"))
                     for value in (started, completed, captured)]
            _require(times == sorted(times), SubmissionsAcquisitionReason.CONFIGURATION_ERROR)
            if parent is not None:
                _require(times[0] >= datetime.fromisoformat(parent.captured_at.replace("Z", "+00:00")),
                         SubmissionsAcquisitionReason.CONFIGURATION_ERROR)
            receipt = archive._capture_live(raw, cik=cik, captured_at=captured,
                                            parent_receipt_id=None if parent is None else parent.receipt_id,
                                            history_filename=filename)
            return SecSubmissionsAcquisitionResult(receipt, started, completed)
    except _sec.SecAcquisitionError as exc:
        raise SecSubmissionsAcquisitionError(SubmissionsAcquisitionReason(exc.reason.value), status=exc.status) from None
    except UnsupportedSubmissionsStructure:
        raise SecSubmissionsAcquisitionError(SubmissionsAcquisitionReason.UNSUPPORTED_STRUCTURE) from None
    except SubmissionsArchiveError:
        raise SecSubmissionsAcquisitionError(SubmissionsAcquisitionReason.ARCHIVE_INTEGRITY_ERROR) from None


def acquire_sec_submissions(*, cik: str, archive_root: str | Path) -> SecSubmissionsAcquisitionResult:
    """Capture exactly one root; CIK is a selector, never identity proof."""
    try:
        endpoint_for(cik)
    except SubmissionsArchiveError:
        raise SecSubmissionsAcquisitionError(SubmissionsAcquisitionReason.CONFIGURATION_ERROR) from None
    return _capture(_archive(archive_root), cik)


def acquire_sec_submissions_history(*, archive_root: str | Path, parent_receipt_id: str,
                                    history_filename: str) -> SecSubmissionsAcquisitionResult:
    """Derive one endpoint from exact verified parent bytes before networking."""
    archive = _archive(archive_root)
    try:
        validate_receipt_id(parent_receipt_id)
    except SubmissionsArchiveError:
        raise SecSubmissionsAcquisitionError(SubmissionsAcquisitionReason.INVALID_REQUEST) from None
    try:
        parent = archive.read_receipt(parent_receipt_id)
        _require(parent.resource_kind == "ROOT", SubmissionsAcquisitionReason.INVALID_REQUEST)
        raw = archive.read_object(parent)
        source = _parse_resource(raw, parent.cik, "ROOT")
    except SubmissionsArchiveError:
        raise SecSubmissionsAcquisitionError(SubmissionsAcquisitionReason.ARCHIVE_INTEGRITY_ERROR) from None
    except UnsupportedSubmissionsStructure:
        raise SecSubmissionsAcquisitionError(SubmissionsAcquisitionReason.UNSUPPORTED_STRUCTURE) from None
    try:
        validate_history_filename(parent.cik, history_filename)
    except SubmissionsArchiveError:
        raise SecSubmissionsAcquisitionError(SubmissionsAcquisitionReason.INVALID_REQUEST) from None
    _require(any(dict(ref)["name"] == history_filename for ref in source.references),
             SubmissionsAcquisitionReason.INVALID_REQUEST)
    return _capture(archive, parent.cik, parent=parent, filename=history_filename)
