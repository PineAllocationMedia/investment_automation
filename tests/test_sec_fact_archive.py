import ast
from dataclasses import FrozenInstanceError, replace
import hashlib
import json
import os
from pathlib import Path
import socket
import tempfile
import unittest
from unittest.mock import patch

from economic_facts.sec_archive import (ArchiveError, CaptureReceipt, SecArchive,
                                        canonical_timestamp, digest, endpoint_for)
from economic_facts.sec_diluted_eps import inspect_archive
from tests.sec_filing_fixtures import CIK, T1, T2, BETWEEN, amendment, raw, row, source


class SecArchiveTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve() / "archive"
        self.archive = SecArchive(self.root)

    def capture(self, content=None, captured_at=T1, **changes):
        arguments = dict(cik=CIK, captured_at=captured_at, source_locator=endpoint_for(CIK))
        arguments.update(changes)
        return self.archive.capture(raw() if content is None else content, **arguments)

    def overwrite(self, path, content):
        path.chmod(0o600)
        path.write_bytes(content)

    def test_exact_bytes_and_hash(self):
        content = b' {"fictional":true} \n'
        receipt = self.capture(content)
        self.assertEqual(receipt.content_sha256, hashlib.sha256(content).hexdigest())
        self.assertEqual(receipt.byte_length, len(content))
        self.assertEqual(self.archive.read_object(receipt), content)
        self.assertNotEqual(digest(content), digest(content.strip()))

    def test_idempotent_capture(self):
        first = self.capture()
        self.assertEqual(first, self.capture())
        self.assertEqual(len(list((self.root / "objects").iterdir())), 1)
        self.assertEqual(len(list((self.root / "receipts").iterdir())), 1)

    def test_multiple_receipts_same_object(self):
        first, second = self.capture(), self.capture(captured_at=T2)
        self.assertEqual(first.content_sha256, second.content_sha256)
        self.assertNotEqual(first.receipt_id, second.receipt_id)
        self.assertEqual(len(list((self.root / "objects").iterdir())), 1)
        self.assertEqual(len(self.archive.captures_as_of(cik=CIK, cutoff=T2).receipts), 2)

    def test_different_bytes_never_overwrite_existing_object(self):
        content = raw()
        self.root.joinpath("objects").mkdir(parents=True)
        target = self.root / "objects" / digest(content)
        target.write_bytes(b"incompatible bytes")
        with self.assertRaises(ArchiveError):
            self.capture(content)
        self.assertEqual(target.read_bytes(), b"incompatible bytes")
        self.assertFalse((self.root / "receipts").exists())

    def test_object_corruption_fails_read(self):
        receipt = self.capture()
        self.overwrite(self.root / "objects" / receipt.content_sha256, b"corrupt")
        with self.assertRaises(ArchiveError):
            self.archive.read_object(receipt)
        with self.assertRaises(ArchiveError):
            self.archive.captures_as_of(cik=CIK, cutoff=T1)

    def test_receipt_is_closed_and_immutable(self):
        receipt = self.capture()
        with self.assertRaises(FrozenInstanceError):
            receipt.cik = "0000000001"
        payload = json.loads(receipt.to_bytes())
        payload["published_at"] = T1
        with self.assertRaises(ArchiveError):
            CaptureReceipt.from_bytes(json.dumps(payload).encode())

    def test_receipt_identity_semantics_and_reordered_serialization(self):
        receipt = self.capture()
        value = json.loads(receipt.to_bytes())
        reordered = json.dumps(dict(reversed(list(value.items()))), indent=4).encode()
        self.assertEqual(CaptureReceipt.from_bytes(reordered).receipt_id, receipt.receipt_id)
        self.assertNotEqual(replace(receipt, source_locator="fixture:another-location").receipt_id, receipt.receipt_id)
        target = self.root / "receipts" / (receipt.receipt_id + ".json")
        self.overwrite(target, reordered)
        self.assertEqual(self.capture(), receipt)
        self.assertEqual(target.read_bytes(), reordered)

    def test_equivalent_offsets_canonicalize(self):
        self.assertEqual(self.capture(), self.capture(captured_at="2025-03-01T07:00:00-05:00"))

    def test_naive_or_invalid_timestamps_rejected(self):
        for value in ("2025-03-01", "2025-03-01T12:00:00", "2025-03-01T12:00:00-00:00",
                      "2025-03-01T12:00:00+24:00", "2025-03-01T12:00:00+00:90", "2025-02-30T12:00:00Z"):
            with self.subTest(value=value), self.assertRaises(ArchiveError):
                self.capture(captured_at=value)
        self.assertFalse(self.root.exists())

    def test_future_capture_excluded_even_with_old_filed_dates(self):
        receipt = self.capture(captured_at=T2)
        view = self.archive.captures_as_of(cik=CIK, cutoff=BETWEEN)
        self.assertEqual(view.receipts, ())
        self.assertEqual(view.latest_receipt_ids, ())
        self.assertEqual(self.archive.captures_as_of(cik=CIK, cutoff=T2).receipts, (receipt,))

    def test_restatement_as_of_regression(self):
        first = self.capture(raw(source([row()])))
        before = inspect_archive(self.archive, cik=CIK, cutoff=BETWEEN)
        original_bytes = self.archive.read_object(first)
        second = self.capture(raw(source([amendment()])), captured_at=T2)
        self.assertEqual(before, inspect_archive(self.archive, cik=CIK, cutoff=BETWEEN))
        after = inspect_archive(self.archive, cik=CIK, cutoff=T2)
        self.assertEqual(len(after.extractions), 2)
        self.assertEqual([str(e.observations[0].value) for e in after.extractions], ["2", "1.75"])
        self.assertEqual(after.capture_view.latest_receipt_ids, (second.receipt_id,))
        self.assertEqual(after.status, "AMBIGUOUS")
        self.assertEqual(self.archive.read_object(first), original_bytes)
        self.assertEqual(before.capture_view.coverage, "ARCHIVE_CAPTURE_VIEW_ONLY")

    def test_latest_capture_ties_preserve_both(self):
        first = self.capture()
        second = self.capture(raw(source([amendment()])))
        view = self.archive.captures_as_of(cik=CIK, cutoff=T1)
        self.assertEqual(set(view.latest_receipt_ids), {first.receipt_id, second.receipt_id})

    def test_fractional_capture_order_is_chronological(self):
        first = self.capture()
        second = self.capture(captured_at="2025-03-01T12:00:00.500000Z")
        view = self.archive.captures_as_of(cik=CIK, cutoff="2025-03-01T12:00:01Z")
        self.assertEqual(view.receipts, (first, second))

    def test_archive_location_and_insertion_order_do_not_change_inspection(self):
        second_archive = SecArchive(self.root.parent / "other-archive")
        captures = ((raw(source([row()])), T1), (raw(source([amendment()])), T2))
        for content, captured_at in captures:
            self.capture(content, captured_at=captured_at)
        for content, captured_at in reversed(captures):
            second_archive.capture(content, cik=CIK, captured_at=captured_at, source_locator=endpoint_for(CIK))
        self.assertEqual(inspect_archive(self.archive, cik=CIK, cutoff=T2),
                         inspect_archive(second_archive, cik=CIK, cutoff=T2))

    def test_cik_and_hash_path_traversal_rejected(self):
        for cik in ("../escape", "/tmp/escape", "0000/00000", 0):
            with self.subTest(cik=cik), self.assertRaises(ArchiveError):
                self.capture(cik=cik)
        with self.assertRaises(ArchiveError):
            self.archive.read_receipt("../escape")
        self.assertFalse(self.root.exists())

    def test_locator_is_metadata_not_path(self):
        receipt = self.capture(source_locator="../../outside/file")
        self.assertEqual(receipt.source_locator, "../../outside/file")
        self.assertEqual({p.name for p in self.root.iterdir()}, {"objects", "receipts"})

    def test_root_and_child_symlinks_rejected(self):
        outside = self.root.parent / "outside"
        outside.mkdir()
        self.root.symlink_to(outside, target_is_directory=True)
        with self.assertRaises(ArchiveError):
            self.capture()
        self.root.unlink()
        self.root.mkdir()
        (self.root / "objects").symlink_to(outside, target_is_directory=True)
        with self.assertRaises(ArchiveError):
            self.capture()
        self.assertEqual(list(outside.iterdir()), [])

    def test_object_symlink_and_hardlink_rejected(self):
        receipt = self.capture()
        target = self.root / "objects" / receipt.content_sha256
        outside = self.root.parent / "outside"
        outside.write_bytes(raw())
        target.unlink()
        target.symlink_to(outside)
        with self.assertRaises(ArchiveError):
            self.archive.read_object(receipt)
        target.unlink()
        os.link(outside, target)
        with self.assertRaises(ArchiveError):
            self.archive.read_object(receipt)

    def test_receipt_symlink_rejected(self):
        receipt = self.capture()
        target = self.root / "receipts" / (receipt.receipt_id + ".json")
        outside = self.root.parent / "outside"
        outside.write_bytes(receipt.to_bytes())
        target.unlink()
        target.symlink_to(outside)
        with self.assertRaises(ArchiveError):
            self.archive.captures_as_of(cik=CIK, cutoff=T1)

    def test_atomic_publication_failure_leaves_no_partial_object(self):
        with patch("economic_facts.sec_archive.os.link", side_effect=OSError("simulated failure")):
            with self.assertRaises(ArchiveError):
                self.capture()
        self.assertEqual(list((self.root / "objects").iterdir()), [])
        self.assertFalse((self.root / "receipts").exists())
        self.capture()

    def test_receipt_hash_corruption_and_duplicate_keys(self):
        receipt = self.capture()
        payload = json.loads(receipt.to_bytes())
        payload["byte_length"] += 1
        with self.assertRaises(ArchiveError):
            CaptureReceipt.from_bytes(json.dumps(payload).encode())
        with self.assertRaises(ArchiveError):
            CaptureReceipt.from_bytes(b'{"cik":"0","cik":"1"}')

    def test_unstored_receipt_does_not_grant_membership(self):
        receipt = self.capture()
        with self.assertRaises(ArchiveError):
            self.archive.read_object(replace(receipt, captured_at=T2))

    def test_later_object_bytes_are_not_read_by_earlier_inspection(self):
        self.capture()
        before = inspect_archive(self.archive, cik=CIK, cutoff=BETWEEN)
        later = self.capture(raw(source([amendment()])), captured_at=T2)
        self.overwrite(self.root / "objects" / later.content_sha256, b"corrupt future object")
        self.assertEqual(before, inspect_archive(self.archive, cik=CIK, cutoff=BETWEEN))
        with self.assertRaises(ArchiveError):
            inspect_archive(self.archive, cik=CIK, cutoff=T2)

    def test_other_issuer_capture_not_selected(self):
        first = self.capture()
        self.capture(cik="0000000001")
        self.assertEqual(self.archive.captures_as_of(cik=CIK, cutoff=T1).receipts, (first,))

    def test_receipt_tampering_cannot_overwrite(self):
        receipt = self.capture()
        target = self.root / "receipts" / (receipt.receipt_id + ".json")
        value = json.loads(receipt.to_bytes())
        value["captured_at"] = T2
        tampered = json.dumps(value).encode()
        self.overwrite(target, tampered)
        with self.assertRaises(ArchiveError):
            self.capture()
        self.assertEqual(target.read_bytes(), tampered)

    def test_missing_archive_inspection_does_not_create_files(self):
        with self.assertRaises(ArchiveError):
            self.archive.captures_as_of(cik=CIK, cutoff=T1)
        self.assertFalse(self.root.exists())

    def test_no_network_or_runtime_dependency(self):
        with patch.object(socket.socket, "connect", side_effect=AssertionError("network")), \
             patch.object(socket, "getaddrinfo", side_effect=AssertionError("network")):
            self.capture()
            inspect_archive(self.archive, cik=CIK, cutoff=T1)
        package = Path(__file__).resolve().parents[1] / "economic_facts"
        allowed = {"dataclasses", "datetime", "decimal", "hashlib", "json", "os", "pathlib", "re", "stat"}
        # The offline archive/extractor remain pure; PR4C2 separately checks
        # the explicit network module's one-way archive dependency.
        for file in (package / "__init__.py", package / "sec_archive.py", package / "sec_diluted_eps.py"):
            tree = ast.parse(file.read_text())
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    self.assertTrue(all(alias.name in allowed for alias in node.names))
                elif isinstance(node, ast.ImportFrom):
                    self.assertTrue(node.module in allowed or (node.level == 1 and node.module == "sec_archive"))
                elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                    self.assertNotIn(node.func.id, {"eval", "exec", "__import__", "compile"})

    def test_model_and_transport_have_no_reverse_dependency(self):
        checkout = Path(__file__).resolve().parents[1]
        files = [checkout / "main.py", *(checkout / "src").glob("*.py"),
                 *(checkout / "pit_comparison").glob("*.py")]
        bounded_projection = checkout / "src" / "bounded_confidence_projection.py"
        for file in files:
            if file in {
                    checkout / "src" / "expected_return_pr5d_bundle.py",
                    checkout / "src" / "vfv_forward_expected_return.py",
                    checkout / "src" /
                    "company_vfv_expected_return_comparator.py",
                    bounded_projection}:
                continue
            for node in ast.walk(ast.parse(file.read_text())):
                if isinstance(node, ast.Import):
                    self.assertFalse(any(alias.name.startswith("economic_facts") for alias in node.names))
                elif isinstance(node, ast.ImportFrom):
                    self.assertFalse((node.module or "").startswith("economic_facts"))
