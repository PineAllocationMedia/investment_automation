from email.message import Message
import inspect
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from economic_facts import vanguard_vfv_acquisition as acquisition
from economic_facts.vanguard_vfv_archive import (
    MAX_DOCUMENT_BYTES,
    VFV_ETF_FACTS_URL,
    VFV_FACTSHEET_URL,
    VFV_PRODUCT_PAGE_URL,
    VanguardVFVArchive,
    VanguardVFVArtifactFamily,
)
from tests.vfv_current_evidence_fixtures import product_html


class Response:
    def __init__(self, raw, *, status=200, content_type="text/html", url=None,
                 headers=None):
        self.raw = raw
        self.status = status
        self.offset = 0
        self.url = url
        self.headers = Message()
        self.headers["Content-Type"] = content_type
        self.headers["Content-Length"] = str(len(raw))
        for key, value in headers or ():
            self.headers[key] = value

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def geturl(self):
        return self.url

    def read1(self, size):
        chunk = self.raw[self.offset:self.offset + size]
        self.offset += len(chunk)
        return chunk


class VanguardVFVAcquisitionTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve() / "vfv"

    def acquire_product(self, response=None):
        response = response or Response(product_html(), url=VFV_PRODUCT_PAGE_URL)
        if response.url is None:
            response.url = VFV_PRODUCT_PAGE_URL
        with patch.object(acquisition, "_open_response", return_value=response) as opened, \
             patch.object(acquisition, "_timestamp", side_effect=(
                 "2026-09-30T22:00:00Z", "2026-09-30T22:00:01Z",
                 "2026-09-30T22:00:02Z")):
            result = acquisition.acquire_vanguard_vfv_product_page(
                archive_root=self.root)
        return result, opened.call_args.args[0]

    def publish_product(self, raw=None):
        archive = VanguardVFVArchive(self.root)
        return archive._capture_fixture(
            raw or product_html(),
            artifact_family=VanguardVFVArtifactFamily.PRODUCT_PAGE,
            source_url=VFV_PRODUCT_PAGE_URL,
            content_type="text/html",
            retrieved_at="2026-09-30T22:00:00Z",
        )

    def acquire_document(self, family, raw=b"%PDF-1.7\nfixture", product=None,
                         response=None):
        product = product or self.publish_product()
        endpoint = (VFV_ETF_FACTS_URL
                    if family is VanguardVFVArtifactFamily.ETF_FACTS
                    else VFV_FACTSHEET_URL)
        response = response or Response(
            raw, content_type="application/pdf", url=endpoint)
        if response.url is None:
            response.url = endpoint
        with patch.object(acquisition, "_open_response", return_value=response) as opened, \
             patch.object(acquisition, "_timestamp", side_effect=(
                 "2026-09-30T22:05:00Z", "2026-09-30T22:05:01Z",
                 "2026-09-30T22:05:02Z")):
            result = acquisition.acquire_vanguard_vfv_document(
                archive_root=self.root,
                product_page_receipt_id=product.receipt_id,
                artifact_family=family,
            )
        return result, opened.call_args.args[0]

    def test_product_uses_fixed_canonical_endpoint_and_exact_bytes(self):
        result, request = self.acquire_product()
        self.assertEqual(request.full_url, VFV_PRODUCT_PAGE_URL)
        self.assertEqual(request.method, "GET")
        self.assertEqual(request.get_header("Accept"), "text/html")
        self.assertEqual(request.get_header("Accept-encoding"), "identity")
        self.assertEqual(
            VanguardVFVArchive(self.root).read_object(result.receipt), product_html())
        self.assertIs(result.receipt.artifact_family,
                      VanguardVFVArtifactFamily.PRODUCT_PAGE)

    def test_public_signatures_exclude_route_date_values_and_success_overrides(self):
        product = inspect.signature(acquisition.acquire_vanguard_vfv_product_page)
        self.assertEqual(tuple(product.parameters), ("archive_root",))
        document = inspect.signature(acquisition.acquire_vanguard_vfv_document)
        self.assertEqual(tuple(document.parameters), (
            "archive_root", "product_page_receipt_id", "artifact_family"))
        for keyword in ("ticker", "product_id", "url", "date", "price", "qualified"):
            with self.assertRaises(TypeError):
                acquisition.acquire_vanguard_vfv_product_page(
                    archive_root=self.root, **{keyword: object()})

    def test_documents_are_bound_to_exact_captured_product_relationships(self):
        for family, endpoint in (
            (VanguardVFVArtifactFamily.ETF_FACTS, VFV_ETF_FACTS_URL),
            (VanguardVFVArtifactFamily.FACTSHEET, VFV_FACTSHEET_URL),
        ):
            with self.subTest(family=family):
                root = self.root.parent / family.value
                self.root = root
                result, request = self.acquire_document(family)
                self.assertEqual(request.full_url, endpoint)
                self.assertEqual(result.receipt.parent_product_receipt_id,
                                 VanguardVFVArchive(root).read_receipt(
                                     result.receipt.parent_product_receipt_id).receipt_id)

    def test_missing_arbitrary_or_redirecting_document_relation_has_no_fallback(self):
        for raw, reason in (
            (product_html(factsheet_url=""),
             acquisition.VanguardVFVAcquisitionReason.DOCUMENT_PROFILE_REJECTED),
            (product_html(factsheet_url="https://example.com/VFV.pdf"),
             acquisition.VanguardVFVAcquisitionReason.DOCUMENT_PROFILE_REJECTED),
            (b"<html><body>VFV</body></html>",
             acquisition.VanguardVFVAcquisitionReason.PRODUCT_RELATION_UNAVAILABLE),
        ):
            with self.subTest(reason=reason):
                root = self.root.parent / (reason.value + str(len(raw)))
                self.root = root
                product = self.publish_product(raw)
                with self.assertRaises(acquisition.VanguardVFVAcquisitionError) as caught:
                    acquisition.acquire_vanguard_vfv_document(
                        archive_root=root,
                        product_page_receipt_id=product.receipt_id,
                        artifact_family=VanguardVFVArtifactFamily.FACTSHEET)
                self.assertIs(caught.exception.reason, reason)

    def test_https_host_profile_and_closed_document_family(self):
        source = inspect.getsource(acquisition)
        self.assertIn('parts.scheme != "https"', source)
        self.assertIn('parts.hostname != "fund-docs.vanguard.com"', source)
        self.assertNotIn("TMX", source)
        self.assertNotIn("yfinance", source)
        self.assertNotIn("Yahoo", source)
        with self.assertRaises(acquisition.VanguardVFVAcquisitionError):
            acquisition.acquire_vanguard_vfv_document(
                archive_root=self.root,
                product_page_receipt_id="0" * 64,
                artifact_family=VanguardVFVArtifactFamily.PRODUCT_PAGE)
        with self.assertRaises(acquisition.VanguardVFVAcquisitionError):
            acquisition.acquire_vanguard_vfv_document(
                archive_root=self.root,
                product_page_receipt_id="0" * 64,
                artifact_family="ETF_FACTS")

    def test_redirect_status_and_final_url_escape_rejected(self):
        for response in (
            Response(product_html(), status=302, url=VFV_PRODUCT_PAGE_URL),
            Response(product_html(), url=VFV_PRODUCT_PAGE_URL + "?escape=1"),
        ):
            with patch.object(acquisition, "_open_response", return_value=response), \
                 patch.object(acquisition, "_timestamp", return_value="2026-09-30T22:00:00Z"):
                with self.assertRaises(acquisition.VanguardVFVAcquisitionError) as caught:
                    acquisition.acquire_vanguard_vfv_product_page(archive_root=self.root)
            self.assertIs(caught.exception.reason,
                          acquisition.VanguardVFVAcquisitionReason.REDIRECT_REJECTED)

    def test_content_type_pdf_magic_size_headers_and_timeout_controls(self):
        wrong = Response(product_html(), content_type="application/json",
                         url=VFV_PRODUCT_PAGE_URL)
        with patch.object(acquisition, "_open_response", return_value=wrong), \
             patch.object(acquisition, "_timestamp", return_value="2026-09-30T22:00:00Z"):
            with self.assertRaises(acquisition.VanguardVFVAcquisitionError) as caught:
                acquisition.acquire_vanguard_vfv_product_page(archive_root=self.root)
        self.assertIs(caught.exception.reason,
                      acquisition.VanguardVFVAcquisitionReason.INVALID_CONTENT_TYPE)

        parent = self.publish_product()
        response = Response(b"not-pdf", content_type="application/pdf",
                            url=VFV_FACTSHEET_URL)
        with self.assertRaises(acquisition.VanguardVFVAcquisitionError) as caught:
            self.acquire_document(VanguardVFVArtifactFamily.FACTSHEET,
                                  product=parent, response=response)
        self.assertIs(caught.exception.reason,
                      acquisition.VanguardVFVAcquisitionReason.INVALID_RESPONSE)

        huge = Response(b"%PDF-x", content_type="application/pdf",
                        url=VFV_ETF_FACTS_URL)
        huge.headers.replace_header("Content-Length", str(MAX_DOCUMENT_BYTES + 1))
        with self.assertRaises(acquisition.VanguardVFVAcquisitionError) as caught:
            self.acquire_document(VanguardVFVArtifactFamily.ETF_FACTS,
                                  product=parent, response=huge)
        self.assertIs(caught.exception.reason,
                      acquisition.VanguardVFVAcquisitionReason.RESPONSE_TOO_LARGE)

        with patch.object(acquisition.time, "monotonic", side_effect=(0, 31)), \
             patch.object(acquisition, "_open_response", return_value=Response(
                 product_html(), url=VFV_PRODUCT_PAGE_URL)), \
             patch.object(acquisition, "_timestamp", return_value="2026-09-30T22:00:00Z"):
            with self.assertRaises(acquisition.VanguardVFVAcquisitionError) as caught:
                acquisition.acquire_vanguard_vfv_product_page(archive_root=self.root)
        self.assertIs(caught.exception.reason,
                      acquisition.VanguardVFVAcquisitionReason.TIMEOUT)

        with patch.object(acquisition, "_open_response", return_value=Response(
                product_html(), url=VFV_PRODUCT_PAGE_URL)), \
             patch.object(acquisition, "_timestamp", side_effect=(
                 "2026-09-30T22:00:02Z", "2026-09-30T22:00:01Z",
                 "2026-09-30T22:00:00Z")):
            with self.assertRaises(acquisition.VanguardVFVAcquisitionError) as caught:
                acquisition.acquire_vanguard_vfv_product_page(archive_root=self.root)
        self.assertIs(caught.exception.reason,
                      acquisition.VanguardVFVAcquisitionReason.CONFIGURATION_ERROR)

    def test_proxy_environment_isolation_and_no_retry_or_fallback(self):
        source = inspect.getsource(acquisition._open_response)
        self.assertIn("urllib.request.ProxyHandler({})", source)
        self.assertIn("ssl.create_default_context()", source)
        whole = inspect.getsource(acquisition)
        for forbidden in ("yfinance", "query1.finance.yahoo.com", "tmx.com",
                          "previousClose"):
            self.assertNotIn(forbidden, whole)


if __name__ == "__main__":
    unittest.main()
