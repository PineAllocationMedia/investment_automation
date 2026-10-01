"""Bounded Vanguard VFV acquisition with no route override or fallback."""
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import StrEnum
from html.parser import HTMLParser
import http.client
from pathlib import Path
import re
import ssl
import time
import urllib.error
import urllib.request
from urllib.parse import urljoin, urlsplit

from .vanguard_vfv_archive import (
    MAX_DOCUMENT_BYTES,
    MAX_PRODUCT_PAGE_BYTES,
    VFV_ETF_FACTS_URL,
    VFV_FACTSHEET_URL,
    VFV_PRODUCT_PAGE_URL,
    VanguardVFVArchive,
    VanguardVFVArchiveError,
    VanguardVFVArtifactFamily,
    VanguardVFVArtifactReceipt,
)


VANGUARD_VFV_ACQUISITION_VERSION = (
    "2026-09-30-vanguard-vfv-current-acquisition-v1"
)
SOCKET_TIMEOUT_SECONDS = 15
RESPONSE_DEADLINE_SECONDS = 30
MAX_HEADER_COUNT = 64
MAX_HEADER_BYTES = 32 * 1024
_CHUNK_BYTES = 64 * 1024
_USER_AGENT = "Mozilla/5.0 (compatible; PAM-VFV-Capture/1.0)"


class VanguardVFVAcquisitionReason(StrEnum):
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
    PRODUCT_RELATION_UNAVAILABLE = "PRODUCT_RELATION_UNAVAILABLE"
    DOCUMENT_PROFILE_REJECTED = "DOCUMENT_PROFILE_REJECTED"
    ARCHIVE_INTEGRITY_ERROR = "ARCHIVE_INTEGRITY_ERROR"


class VanguardVFVAcquisitionError(ValueError):
    def __init__(self, reason, *, status=None):
        self.reason = reason
        self.status = status
        suffix = f" (HTTP {status})" if status is not None else ""
        super().__init__(reason.value + suffix)


@dataclass(frozen=True, slots=True)
class VanguardVFVAcquisitionResult:
    receipt: VanguardVFVArtifactReceipt
    request_started_at: str
    response_completed_at: str


class _RejectRedirects(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        fp.close()
        raise VanguardVFVAcquisitionError(
            VanguardVFVAcquisitionReason.REDIRECT_REJECTED, status=code) from None


class _RelatedDocumentParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self._href = None
        self._text = []
        self.links = []

    def handle_starttag(self, tag, attrs):
        if tag.lower() == "a" and self._href is None:
            values = [value for name, value in attrs if name.lower() == "href"]
            if len(values) == 1 and type(values[0]) is str:
                self._href = values[0]
                self._text = []

    def handle_data(self, data):
        if self._href is not None:
            self._text.append(data)

    def handle_endtag(self, tag):
        if tag.lower() == "a" and self._href is not None:
            label = " ".join("".join(self._text).split())
            self.links.append((label, self._href))
            self._href = None
            self._text = []


def _open_response(request):
    # Ambient proxies and environment routing are not evidence inputs.
    opener = urllib.request.build_opener(
        urllib.request.ProxyHandler({}),
        urllib.request.HTTPSHandler(context=ssl.create_default_context()),
        _RejectRedirects(),
    )
    return opener.open(request, timeout=SOCKET_TIMEOUT_SECONDS)


def _timestamp():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _ordered_timestamps(*values):
    try:
        parsed = tuple(datetime.fromisoformat(value.replace("Z", "+00:00"))
                       for value in values)
    except (AttributeError, ValueError):
        return False
    return parsed == tuple(sorted(parsed))


def _check_status(status):
    if status == 200:
        return
    if 300 <= status < 400:
        reason = VanguardVFVAcquisitionReason.REDIRECT_REJECTED
    elif status == 429:
        reason = VanguardVFVAcquisitionReason.RATE_LIMITED
    else:
        reason = VanguardVFVAcquisitionReason.HTTP_ERROR
    raise VanguardVFVAcquisitionError(reason, status=status) from None


def _single_header(headers, name):
    values = headers.get_all(name, [])
    if len(values) > 1:
        raise VanguardVFVAcquisitionError(
            VanguardVFVAcquisitionReason.INVALID_RESPONSE)
    return values[0] if values else None


def _validate_headers(headers):
    items = list(headers.raw_items())
    if len(items) > MAX_HEADER_COUNT:
        raise VanguardVFVAcquisitionError(
            VanguardVFVAcquisitionReason.RESPONSE_HEADERS_TOO_LARGE)
    size = 0
    try:
        for name, value in items:
            if type(name) is not str or type(value) is not str:
                raise VanguardVFVAcquisitionError(
                    VanguardVFVAcquisitionReason.INVALID_RESPONSE)
            size += (len(name.encode("ascii", "strict"))
                     + len(value.encode("latin-1", "strict")) + 4)
    except UnicodeError:
        raise VanguardVFVAcquisitionError(
            VanguardVFVAcquisitionReason.INVALID_RESPONSE) from None
    if size > MAX_HEADER_BYTES:
        raise VanguardVFVAcquisitionError(
            VanguardVFVAcquisitionReason.RESPONSE_HEADERS_TOO_LARGE)


def _read_body(response, *, artifact_family, deadline):
    _validate_headers(response.headers)
    content_type = (_single_header(response.headers, "Content-Type") or "").strip()
    if artifact_family is VanguardVFVArtifactFamily.PRODUCT_PAGE:
        valid_type = re.fullmatch(
            r'text/html(?:\s*;\s*charset\s*=\s*(?:utf-8|"utf-8"))?\s*',
            content_type, re.IGNORECASE)
        limit = MAX_PRODUCT_PAGE_BYTES
    else:
        valid_type = re.fullmatch(r'application/pdf\s*', content_type, re.IGNORECASE)
        limit = MAX_DOCUMENT_BYTES
    if valid_type is None:
        raise VanguardVFVAcquisitionError(
            VanguardVFVAcquisitionReason.INVALID_CONTENT_TYPE)
    encoding = _single_header(response.headers, "Content-Encoding")
    if encoding is not None and encoding.strip().lower() != "identity":
        raise VanguardVFVAcquisitionError(
            VanguardVFVAcquisitionReason.INVALID_RESPONSE)
    length = _single_header(response.headers, "Content-Length")
    declared = None
    if length is not None:
        if re.fullmatch(r"[0-9]{1,20}", length.strip()) is None:
            raise VanguardVFVAcquisitionError(
                VanguardVFVAcquisitionReason.INVALID_RESPONSE)
        declared = int(length)
        if declared > limit:
            raise VanguardVFVAcquisitionError(
                VanguardVFVAcquisitionReason.RESPONSE_TOO_LARGE)
    transfer = _single_header(response.headers, "Transfer-Encoding")
    if transfer is not None and (transfer.strip().lower() != "chunked"
                                 or declared is not None):
        raise VanguardVFVAcquisitionError(
            VanguardVFVAcquisitionReason.INVALID_RESPONSE)
    body = bytearray()
    while True:
        if time.monotonic() >= deadline:
            raise VanguardVFVAcquisitionError(VanguardVFVAcquisitionReason.TIMEOUT)
        chunk = response.read1(min(_CHUNK_BYTES, limit + 1 - len(body)))
        if time.monotonic() >= deadline:
            raise VanguardVFVAcquisitionError(VanguardVFVAcquisitionReason.TIMEOUT)
        if not chunk:
            break
        body.extend(chunk)
        if len(body) > limit:
            raise VanguardVFVAcquisitionError(
                VanguardVFVAcquisitionReason.RESPONSE_TOO_LARGE)
    if not body or (declared is not None and declared != len(body)):
        raise VanguardVFVAcquisitionError(
            VanguardVFVAcquisitionReason.INVALID_RESPONSE)
    raw = bytes(body)
    if artifact_family is not VanguardVFVArtifactFamily.PRODUCT_PAGE \
            and not raw.startswith(b"%PDF-"):
        raise VanguardVFVAcquisitionError(
            VanguardVFVAcquisitionReason.INVALID_RESPONSE)
    return raw


def _resolve_document(raw, artifact_family):
    if artifact_family not in (
        VanguardVFVArtifactFamily.ETF_FACTS,
        VanguardVFVArtifactFamily.FACTSHEET,
    ):
        raise VanguardVFVAcquisitionError(
            VanguardVFVAcquisitionReason.CONFIGURATION_ERROR)
    try:
        text = raw.decode("utf-8", "strict")
        parser = _RelatedDocumentParser()
        parser.feed(text)
        parser.close()
    except (UnicodeError, ValueError):
        raise VanguardVFVAcquisitionError(
            VanguardVFVAcquisitionReason.PRODUCT_RELATION_UNAVAILABLE) from None
    label = ("ETF facts" if artifact_family is VanguardVFVArtifactFamily.ETF_FACTS
             else "Factsheet")
    targets = {
        urljoin(VFV_PRODUCT_PAGE_URL, href)
        for link_label, href in parser.links
        if link_label.casefold() == label.casefold()
    }
    if len(targets) != 1:
        raise VanguardVFVAcquisitionError(
            VanguardVFVAcquisitionReason.PRODUCT_RELATION_UNAVAILABLE)
    target = targets.pop()
    expected = (VFV_ETF_FACTS_URL
                if artifact_family is VanguardVFVArtifactFamily.ETF_FACTS
                else VFV_FACTSHEET_URL)
    parts = urlsplit(target)
    if (target != expected or parts.scheme != "https"
            or parts.hostname != "fund-docs.vanguard.com"
            or parts.port is not None or parts.username or parts.password
            or parts.query or parts.fragment):
        raise VanguardVFVAcquisitionError(
            VanguardVFVAcquisitionReason.DOCUMENT_PROFILE_REJECTED)
    return target


def _acquire(*, archive, endpoint, artifact_family, parent_receipt_id=None):
    request = urllib.request.Request(endpoint, method="GET", headers={
        "User-Agent": _USER_AGENT,
        "Accept": ("text/html" if artifact_family is VanguardVFVArtifactFamily.PRODUCT_PAGE
                   else "application/pdf"),
        "Accept-Encoding": "identity",
    })
    started = _timestamp()
    deadline = time.monotonic() + RESPONSE_DEADLINE_SECONDS
    try:
        with _open_response(request) as response:
            _check_status(response.status)
            if response.geturl() != endpoint:
                raise VanguardVFVAcquisitionError(
                    VanguardVFVAcquisitionReason.REDIRECT_REJECTED)
            raw = _read_body(response, artifact_family=artifact_family,
                             deadline=deadline)
            completed = _timestamp()
    except VanguardVFVAcquisitionError:
        raise
    except urllib.error.HTTPError as exc:
        status = exc.code
        exc.close()
        _check_status(status)
        raise VanguardVFVAcquisitionError(
            VanguardVFVAcquisitionReason.HTTP_ERROR, status=status) from None
    except TimeoutError:
        raise VanguardVFVAcquisitionError(
            VanguardVFVAcquisitionReason.TIMEOUT) from None
    except urllib.error.URLError as exc:
        reason = (VanguardVFVAcquisitionReason.TIMEOUT
                  if isinstance(exc.reason, TimeoutError)
                  else VanguardVFVAcquisitionReason.NETWORK_ERROR)
        raise VanguardVFVAcquisitionError(reason) from None
    except (OSError, http.client.HTTPException):
        raise VanguardVFVAcquisitionError(
            VanguardVFVAcquisitionReason.NETWORK_ERROR) from None
    retrieved = _timestamp()
    if not _ordered_timestamps(started, completed, retrieved):
        raise VanguardVFVAcquisitionError(
            VanguardVFVAcquisitionReason.CONFIGURATION_ERROR)
    try:
        receipt = archive._capture(
            raw,
            artifact_family=artifact_family,
            source_url=endpoint,
            content_type=("text/html"
                          if artifact_family is VanguardVFVArtifactFamily.PRODUCT_PAGE
                          else "application/pdf"),
            retrieved_at=retrieved,
            artifact_date=None,
            parent_product_receipt_id=parent_receipt_id,
        )
    except (VanguardVFVArchiveError, OSError):
        raise VanguardVFVAcquisitionError(
            VanguardVFVAcquisitionReason.ARCHIVE_INTEGRITY_ERROR) from None
    return VanguardVFVAcquisitionResult(receipt, started, completed)


def acquire_vanguard_vfv_product_page(
    *, archive_root: str | Path,
) -> VanguardVFVAcquisitionResult:
    """Capture the fixed canonical Vanguard product-9563 page."""
    try:
        archive = VanguardVFVArchive(archive_root)
    except (TypeError, ValueError):
        raise VanguardVFVAcquisitionError(
            VanguardVFVAcquisitionReason.CONFIGURATION_ERROR) from None
    return _acquire(
        archive=archive,
        endpoint=VFV_PRODUCT_PAGE_URL,
        artifact_family=VanguardVFVArtifactFamily.PRODUCT_PAGE,
    )


def acquire_vanguard_vfv_document(
    *, archive_root: str | Path, product_page_receipt_id: str,
    artifact_family: VanguardVFVArtifactFamily,
) -> VanguardVFVAcquisitionResult:
    """Resolve one reviewed document only from one exact captured product page."""
    if type(artifact_family) is not VanguardVFVArtifactFamily or artifact_family not in (
        VanguardVFVArtifactFamily.ETF_FACTS,
        VanguardVFVArtifactFamily.FACTSHEET,
    ):
        raise VanguardVFVAcquisitionError(
            VanguardVFVAcquisitionReason.CONFIGURATION_ERROR)
    try:
        archive = VanguardVFVArchive(archive_root)
        product = archive.read_receipt(product_page_receipt_id)
        if product.artifact_family is not VanguardVFVArtifactFamily.PRODUCT_PAGE:
            raise VanguardVFVArchiveError("Exact product receipt required")
        raw = archive.read_object(product)
    except (TypeError, ValueError, VanguardVFVArchiveError):
        raise VanguardVFVAcquisitionError(
            VanguardVFVAcquisitionReason.ARCHIVE_INTEGRITY_ERROR) from None
    endpoint = _resolve_document(raw, artifact_family)
    return _acquire(
        archive=archive,
        endpoint=endpoint,
        artifact_family=artifact_family,
        parent_receipt_id=product.receipt_id,
    )
