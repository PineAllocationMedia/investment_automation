from dataclasses import FrozenInstanceError
import inspect
import os
from pathlib import Path
import tempfile
import unittest

from economic_facts import vanguard_vfv_archive as archive
from tests.vfv_current_evidence_fixtures import product_html


class VanguardVFVArchiveTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve() / "vfv"
        self.archive = archive.VanguardVFVArchive(self.root)

    def product(self, raw=None, **changes):
        return self.archive._capture_fixture(
            product_html() if raw is None else raw,
            artifact_family=archive.VanguardVFVArtifactFamily.PRODUCT_PAGE,
            source_url=archive.VFV_PRODUCT_PAGE_URL,
            content_type="text/html",
            retrieved_at=changes.pop("retrieved_at", "2026-09-30T18:00:00-04:00"),
            **changes,
        )

    def document(self, family, raw=b"%PDF-1.7\nfixture", **changes):
        parent = changes.pop("parent", self.product())
        url = (archive.VFV_ETF_FACTS_URL
               if family is archive.VanguardVFVArtifactFamily.ETF_FACTS
               else archive.VFV_FACTSHEET_URL)
        return self.archive._capture_fixture(
            raw,
            artifact_family=family,
            source_url=url,
            content_type="application/pdf",
            retrieved_at=changes.pop("retrieved_at", "2026-09-30T18:05:00-04:00"),
            parent_product_receipt_id=parent.receipt_id,
            **changes,
        )

    def test_exact_bytes_and_deterministic_receipt_identity(self):
        raw = product_html()
        first = self.product(raw)
        second = self.product(raw)
        self.assertEqual(first, second)
        self.assertEqual(first.receipt_id, second.receipt_id)
        self.assertEqual(self.archive.read_receipt(first.receipt_id), first)
        self.assertEqual(self.archive.read_object(first), raw)
        self.assertEqual(first.content_sha256,
                         __import__("hashlib").sha256(raw).hexdigest())
        self.assertEqual(first.byte_length, len(raw))

    def test_retrieval_time_changes_receipt_not_object_and_preserves_offset(self):
        raw = product_html()
        first = self.product(raw)
        second = self.product(raw, retrieved_at="2026-09-30T22:00:01Z")
        self.assertEqual(first.content_sha256, second.content_sha256)
        self.assertNotEqual(first.receipt_id, second.receipt_id)
        self.assertEqual(first.retrieved_at, "2026-09-30T18:00:00-04:00")

    def test_document_requires_exact_parent_and_artifact_date_is_not_retrieval(self):
        parent = self.product()
        receipt = self.document(
            archive.VanguardVFVArtifactFamily.FACTSHEET,
            parent=parent,
            artifact_date="2026-08-31",
        )
        self.assertEqual(receipt.parent_product_receipt_id, parent.receipt_id)
        self.assertEqual(receipt.artifact_date, "2026-08-31")
        undated = self.document(
            archive.VanguardVFVArtifactFamily.ETF_FACTS, parent=parent)
        self.assertIsNone(undated.artifact_date)
        with self.assertRaises(archive.VanguardVFVArchiveError):
            self.archive._capture_fixture(
                b"%PDF-1.7\nfixture",
                artifact_family=archive.VanguardVFVArtifactFamily.FACTSHEET,
                source_url=archive.VFV_FACTSHEET_URL,
                content_type="application/pdf",
                retrieved_at="2026-09-30T18:05:00-04:00",
                parent_product_receipt_id="0" * 64,
            )

    def test_closed_families_urls_content_types_and_parent_shape(self):
        for value in ("OTHER", "FACTSHEET", None, True):
            with self.subTest(value=value), self.assertRaises(
                    archive.VanguardVFVArchiveError):
                self.archive._capture_fixture(
                    b"x", artifact_family=value,
                    source_url=archive.VFV_PRODUCT_PAGE_URL,
                    content_type="text/html",
                    retrieved_at="2026-09-30T18:00:00Z")
        with self.assertRaises(archive.VanguardVFVArchiveError):
            self.archive._capture_fixture(
                product_html(),
                artifact_family=archive.VanguardVFVArtifactFamily.PRODUCT_PAGE,
                source_url=archive.VFV_PRODUCT_PAGE_URL + "?ticker=VFV",
                content_type="text/html",
                retrieved_at="2026-09-30T18:00:00Z")
        with self.assertRaises(archive.VanguardVFVArchiveError):
            self.archive._capture_fixture(
                product_html(),
                artifact_family=archive.VanguardVFVArtifactFamily.PRODUCT_PAGE,
                source_url=archive.VFV_PRODUCT_PAGE_URL,
                content_type="application/pdf",
                retrieved_at="2026-09-30T18:00:00Z")

    def test_no_clobber_corrupt_and_unsafe_path_behavior(self):
        receipt = self.product()
        with self.assertRaises(archive.VanguardVFVArchiveError):
            self.archive._publish("receipts", receipt.receipt_id + ".json", b"{}")
        object_path = self.root / "objects" / receipt.content_sha256
        os.chmod(object_path, 0o600)
        object_path.write_bytes(b"corrupt")
        with self.assertRaises(archive.VanguardVFVArchiveError):
            self.archive.read_object(receipt)
        with self.assertRaises(archive.VanguardVFVArchiveError):
            archive.VanguardVFVArchive(self.root / ".." / "escape")

    def test_symlink_archive_member_rejected(self):
        receipt = self.product()
        receipt_path = self.root / "receipts" / (receipt.receipt_id + ".json")
        original = receipt_path.read_bytes()
        os.chmod(receipt_path, 0o600)
        receipt_path.unlink()
        target = self.root / "outside"
        target.write_bytes(original)
        receipt_path.symlink_to(target)
        with self.assertRaises(archive.VanguardVFVArchiveError):
            self.archive.read_receipt(receipt.receipt_id)

    def test_receipt_closed_json_frozen_and_public_archive_is_replay_only(self):
        receipt = self.product()
        with self.assertRaises(FrozenInstanceError):
            receipt.source_url = "changed"
        with self.assertRaises(archive.VanguardVFVArchiveError):
            archive.VanguardVFVArtifactReceipt.from_bytes(
                b'{"schema_version":"x","schema_version":"y"}')
        public = {name for name, _ in inspect.getmembers(archive.VanguardVFVArchive)
                  if not name.startswith("_")}
        self.assertEqual(public, {"read_object", "read_receipt", "root"} - {"root"})


if __name__ == "__main__":
    unittest.main()
