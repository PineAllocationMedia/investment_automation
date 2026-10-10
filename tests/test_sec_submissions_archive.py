"""Private fixture publication tests; no LIVE observation is made."""
from dataclasses import FrozenInstanceError, asdict, replace
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from economic_facts import sec_submissions_archive as a
from tests.sec_submissions_fixtures import CIK, T1, T2, NAME, root, history, reference


class SubmissionsArchiveTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve() / "archive"
        self.archive = a.SecSubmissionsArchive(self.root)

    def capture(self, raw=None, **changes):
        args = dict(cik=CIK, captured_at=T1)
        args.update(changes)
        return self.archive._capture_live(root() if raw is None else raw, **args)

    def overwrite(self, path, raw):
        path.chmod(0o600)
        path.write_bytes(raw)

    def test_exact_byte_replay(self):
        raw = root().replace(b"\n", b"\r\n")
        receipt = self.capture(raw)
        self.assertEqual(self.archive.read_object(receipt), raw)
        self.assertEqual(receipt.content_sha256, hashlib.sha256(raw).hexdigest())
        self.assertEqual(receipt.byte_length, len(raw))
        self.assertEqual(self.archive.read_receipt(receipt.receipt_id), receipt)

    def test_foreign_location_reviewed_types_and_integer_boundaries(self):
        bound = 2**63 - 1
        for branch in ("mailing", "business"):
            for value in (None, "0", "foreign", 0, 1, 7, -7, bound, -bound):
                with self.subTest(branch=branch, value=value):
                    raw = root(addresses={branch: {"isForeignLocation": value}})
                    receipt = self.capture(raw)
                    self.assertEqual(self.archive.read_object(receipt), raw)
                    self.assertEqual(self.archive.read_receipt(receipt.receipt_id), receipt)
                    self.assertEqual(receipt.content_sha256, hashlib.sha256(raw).hexdigest())
                    self.assertEqual(receipt.byte_length, len(raw))

    def test_unreviewed_address_types_publish_nothing(self):
        bound = 2**63 - 1
        cases = [("isForeignLocation", value) for value in
                 (bound + 1, -bound - 1, True, False, 0.0, 7.0, [], {})]
        cases += [(name, 7) for name in
                  ("city", "street1", "zipCode", "stateOrCountry", "other",
                   "IsForeignLocation", "isForeignLocation ")]
        for branch in ("mailing", "business"):
            for name, value in cases:
                with self.subTest(branch=branch, name=name, value=value):
                    with self.assertRaises(a.UnsupportedSubmissionsStructure):
                        self.capture(root(addresses={branch: {name: value}}))
                    self.assertFalse(self.root.exists())
        for branch in ("other", "Mailing"):
            with self.subTest(branch=branch), self.assertRaises(a.UnsupportedSubmissionsStructure):
                self.capture(root(addresses={branch: {"isForeignLocation": 7}}))
            self.assertFalse(self.root.exists())

    def test_canonical_root_endpoint(self):
        self.assertEqual(a.endpoint_for(CIK), "https://data.sec.gov/submissions/CIK0000000123.json")

    def test_idempotent_publication(self):
        first = self.capture()
        self.assertEqual(first, self.capture())
        self.assertEqual(len(list((self.root / "receipts").iterdir())), 1)
        self.assertEqual(len(list((self.root / "objects").iterdir())), 1)

    def test_identical_recapture_keeps_new_receipt(self):
        first, second = self.capture(), self.capture(captured_at=T2)
        self.assertEqual(first.content_sha256, second.content_sha256)
        self.assertNotEqual(first.receipt_id, second.receipt_id)
        self.assertEqual(len(list((self.root / "objects").iterdir())), 1)
        self.assertEqual(len(list((self.root / "receipts").iterdir())), 2)

    def test_changed_recapture_preserves_both_originals(self):
        first = self.capture()
        changed = root(name="Corrected fictional source")
        second = self.capture(changed, captured_at=T2)
        self.assertNotEqual(first.content_sha256, second.content_sha256)
        self.assertEqual(self.archive.read_object(first), root())
        self.assertEqual(self.archive.read_object(second), changed)

    def test_identity_domain_and_path_independence(self):
        first = self.capture()
        other = a.SecSubmissionsArchive(self.root.parent / "other")
        second = other._capture_live(root(), cik=CIK, captured_at=T1)
        self.assertEqual(first, second)
        self.assertEqual(first.receipt_id,
                         a.digest(b"pam:sec-submissions-receipt:v1\0" + a.canonical_json(asdict(first))))
        self.assertNotEqual(first.receipt_id, a.digest(a.canonical_json(asdict(first))))

    def test_reordered_receipt_equivalent_without_overwrite(self):
        receipt = self.capture()
        raw = json.dumps(dict(reversed(list(json.loads(receipt.to_bytes()).items()))), indent=2).encode()
        target = self.root / "receipts" / (receipt.receipt_id + ".json")
        self.overwrite(target, raw)
        self.assertEqual(self.capture(), receipt)
        self.assertEqual(target.read_bytes(), raw)

    def test_receipt_closed_frozen_and_versioned(self):
        receipt = self.capture()
        with self.assertRaises(FrozenInstanceError):
            receipt.captured_at = T2
        for key, value in (("schema_version", "other"), ("source_kind", "SEC_COMPANYFACTS_SNAPSHOT"),
                           ("acquisition_contract_version", "OFFLINE"), ("endpoint", "https://other.invalid"),
                           ("byte_length", True), ("byte_length", 0), ("content_sha256", "../object")):
            with self.subTest(key=key), self.assertRaises(a.SubmissionsArchiveError):
                replace(receipt, **{key: value})
        payload = json.loads(receipt.to_bytes())
        for key in ("published_at", "available_at", "authority", "qualified"):
            with self.subTest(key=key), self.assertRaises(a.SubmissionsArchiveError):
                a.SubmissionsReceipt.from_bytes(json.dumps({**payload, key: True}).encode())

    def test_bad_receipt_serializations(self):
        for raw in (b"[]", b"null", b"{}", b"\xff", b'{"cik":0,"cik":1}', b'{"x":NaN}',
                    b"[" * 1100 + b"]" * 1100, b" " * 4097):
            with self.subTest(raw=raw[:20]), self.assertRaises(a.SubmissionsArchiveError):
                a.SubmissionsReceipt.from_bytes(raw)

    def test_timestamps_canonical_and_not_naive(self):
        self.assertEqual(self.capture(), self.capture(captured_at="2026-09-20T08:00:00-04:00"))
        for value in (T1[:-1], "2026-09-20", "2026-09-20T12:00:00-00:00", "2026-09-20T12:00:00+24:00",
                      "2026-02-30T12:00:00Z", "٢٠٢٦-09-20T12:00:00Z", None):
            with self.subTest(value=value), self.assertRaises(a.SubmissionsArchiveError):
                self.capture(captured_at=value)

    def test_missing_archive_reads_create_nothing(self):
        with self.assertRaises(a.SubmissionsArchiveError):
            self.archive.read_receipt("0" * 64)
        self.assertFalse(self.root.exists())

    def test_missing_receipt_and_detached_self_authored_receipt(self):
        receipt = self.capture()
        with self.assertRaises(a.SubmissionsArchiveError):
            self.archive.read_object(replace(receipt, captured_at=T2))
        (self.root / "receipts" / (receipt.receipt_id + ".json")).unlink()
        with self.assertRaises(a.SubmissionsArchiveError):
            self.archive.read_object(receipt)

    def test_wrong_archive_or_untyped_receipt(self):
        receipt = self.capture()
        with self.assertRaises(a.SubmissionsArchiveError):
            a.SecSubmissionsArchive(self.root.parent / "other").read_object(receipt)
        with self.assertRaises(a.SubmissionsArchiveError):
            self.archive.read_object(asdict(receipt))

    def test_corrupt_or_misnamed_receipt(self):
        receipt = self.capture()
        target = self.root / "receipts" / (receipt.receipt_id + ".json")
        self.overwrite(target, replace(receipt, captured_at=T2).to_bytes())
        with self.assertRaises(a.SubmissionsArchiveError):
            self.archive.read_receipt(receipt.receipt_id)
        with self.assertRaises(a.SubmissionsArchiveError):
            self.capture()
        payload = json.loads(receipt.to_bytes())
        payload["byte_length"] += 1
        self.overwrite(target, json.dumps(payload).encode())
        with self.assertRaises(a.SubmissionsArchiveError):
            self.archive.read_object(receipt)

    def test_object_length_and_hash_corruption(self):
        receipt = self.capture()
        target = self.root / "objects" / receipt.content_sha256
        for raw in (root()[:-1], root() + b"x", b"x" * len(root())):
            self.overwrite(target, raw)
            with self.assertRaises(a.SubmissionsArchiveError):
                self.archive.read_object(receipt)
        with self.assertRaises(a.SubmissionsArchiveError):
            self.capture()
        self.assertEqual(target.read_bytes(), b"x" * len(root()))

    def test_missing_object(self):
        receipt = self.capture()
        (self.root / "objects" / receipt.content_sha256).unlink()
        with self.assertRaises(a.SubmissionsArchiveError):
            self.archive.read_object(receipt)

    def test_path_attacks_fail_before_read(self):
        for value in ("../escape", "/escape", "0" * 64 + "?x", "٠" * 64, None):
            with self.subTest(value=value), self.assertRaises(a.SubmissionsArchiveError):
                self.archive.read_receipt(value)
        self.assertFalse(self.root.exists())

    def test_symlink_roots_and_children_rejected(self):
        outside = self.root.parent / "outside"
        outside.mkdir()
        for kind in (None, "objects", "receipts"):
            with self.subTest(kind=kind):
                if kind is None:
                    target = self.root
                else:
                    self.root.mkdir(exist_ok=True)
                    target = self.root / kind
                target.symlink_to(outside, target_is_directory=True)
                with self.assertRaises(a.SubmissionsArchiveError):
                    self.capture()
                target.unlink()
        self.assertEqual(list(outside.iterdir()), [])

    def test_symlink_ancestor_rejected(self):
        outside = self.root.parent / "outside"
        outside.mkdir()
        self.root.symlink_to(outside, target_is_directory=True)
        with self.assertRaises(a.SubmissionsArchiveError):
            a.SecSubmissionsArchive(self.root / "child")._capture_live(
                root(), cik=CIK, captured_at=T1)
        self.assertEqual(list(outside.iterdir()), [])

    def test_symlink_hardlink_fifo_directory_entries_rejected(self):
        receipt = self.capture()
        for kind, name, raw in (("objects", receipt.content_sha256, root()),
                                ("receipts", receipt.receipt_id + ".json", receipt.to_bytes())):
            target = self.root / kind / name
            outside = self.root.parent / (kind + "-outside")
            outside.write_bytes(raw)
            for attack in ("symlink", "hardlink", "fifo", "directory"):
                with self.subTest(kind=kind, attack=attack):
                    target.unlink()
                    if attack == "symlink":
                        target.symlink_to(outside)
                    elif attack == "hardlink":
                        os.link(outside, target)
                    elif attack == "fifo":
                        os.mkfifo(target)
                    else:
                        target.mkdir()
                    with self.assertRaises(a.SubmissionsArchiveError):
                        self.archive.read_object(receipt)
                    if attack == "directory":
                        target.rmdir()
                    else:
                        target.unlink()
                    target.write_bytes(raw)

    def test_atomic_link_failure_no_partial_publication(self):
        with patch.object(a.os, "link", side_effect=OSError("private failure")), self.assertRaises(a.SubmissionsArchiveError):
            self.capture()
        self.assertEqual(list((self.root / "objects").iterdir()), [])
        self.assertFalse((self.root / "receipts").exists())
        self.capture()

    def test_fsync_failure_before_link_leaves_no_evidence(self):
        with patch.object(a.os, "fsync", side_effect=OSError("private failure")), self.assertRaises(a.SubmissionsArchiveError):
            self.capture()
        self.assertEqual(list((self.root / "objects").iterdir()), [])
        self.assertFalse((self.root / "receipts").exists())

    def test_receipt_failure_leaves_only_unreferenced_object(self):
        original = a.SecSubmissionsArchive._publish
        def publish(archive, kind, name, raw):
            if kind == "receipts":
                raise a.SubmissionsArchiveError("fixture failure")
            return original(archive, kind, name, raw)
        with patch.object(a.SecSubmissionsArchive, "_publish", publish), self.assertRaises(a.SubmissionsArchiveError):
            self.capture()
        self.assertEqual((self.root / "objects" / a.digest(root())).read_bytes(), root())
        self.assertFalse((self.root / "receipts").exists())

    def test_no_public_capture_or_history_authority(self):
        self.assertEqual({name for name in vars(a.SecSubmissionsArchive) if not name.startswith("_")},
                         {"read_receipt", "read_object"})
        self.assertEqual(set(a.SubmissionsReceipt.__dataclass_fields__), {
            "schema_version", "source_kind", "cik", "resource_kind", "history_filename", "parent_receipt_id", "endpoint", "content_sha256",
            "byte_length", "captured_at", "acquisition_contract_version"})

    def test_root_history_tag_invariants(self):
        receipt = self.capture()
        for changes in ({"resource_kind": "OTHER"}, {"resource_kind": "HISTORY"},
                        {"history_filename": NAME}, {"parent_receipt_id": "a" * 64}):
            with self.subTest(changes=changes), self.assertRaises(a.SubmissionsArchiveError):
                replace(receipt, **changes)

    def child(self, parent, **changes):
        return self.capture(history(), parent_receipt_id=parent.receipt_id,
                            history_filename=NAME, captured_at=T2, **changes)

    def test_child_binds_exact_parent_while_objects_deduplicate(self):
        first = self.capture(root(refs=[reference()]))
        second = self.capture(root(refs=[reference()]), captured_at=T2)
        left, right = self.child(first), self.child(second)
        self.assertNotEqual(left.receipt_id, right.receipt_id)
        self.assertEqual(left.content_sha256, right.content_sha256)
        self.assertEqual(self.archive.read_object(left), history())
        self.assertEqual(left.parent_receipt_id, first.receipt_id)
        self.assertEqual(len(list((self.root / "objects").iterdir())), 2)

    def test_unreferenced_or_missing_parent_cannot_publish(self):
        parent = self.capture()
        for parent_id in (parent.receipt_id, "0" * 64):
            with self.assertRaises(a.SubmissionsArchiveError):
                self.capture(history(), parent_receipt_id=parent_id, history_filename=NAME)
        self.assertEqual(len(list((self.root / "objects").iterdir())), 1)

    def test_child_fails_if_parent_corrupt(self):
        parent = self.capture(root(refs=[reference()]))
        child = self.child(parent)
        self.overwrite(self.root / "objects" / parent.content_sha256, b"corrupt")
        with self.assertRaises(a.SubmissionsArchiveError):
            self.archive.read_object(child)

    def test_child_cannot_parent_another_child(self):
        parent = self.capture(root(refs=[reference()]))
        child = self.child(parent)
        with self.assertRaises(a.SubmissionsArchiveError):
            self.child(child)

    def test_capture_time_cannot_precede_parent(self):
        parent = self.capture(root(refs=[reference()]), captured_at=T2)
        with self.assertRaises(a.SubmissionsArchiveError):
            self.capture(history(), parent_receipt_id=parent.receipt_id, history_filename=NAME, captured_at=T1)

    def test_bounded_object_and_receipt_reads(self):
        receipt = self.capture()
        target = self.root / "receipts" / (receipt.receipt_id + ".json")
        self.overwrite(target, receipt.to_bytes() + b" " * 4096)
        with self.assertRaises(a.SubmissionsArchiveError):
            self.archive.read_receipt(receipt.receipt_id)
        with patch.object(a, "MAX_SUBMISSIONS_BYTES", 8), self.assertRaises(a.SubmissionsArchiveError):
            self.capture()

    def test_directory_fsync_failure_reports_failure_and_retry_recovers(self):
        original = a.os.fsync
        calls = []
        def fail_directory(fd):
            calls.append(fd)
            if len(calls) == 2:
                raise OSError("fixture directory fsync failure")
            return original(fd)
        with patch.object(a.os, "fsync", side_effect=fail_directory), self.assertRaises(a.SubmissionsArchiveError):
            self.capture()
        self.assertFalse((self.root / "receipts").exists())
        self.assertEqual(self.archive.read_object(self.capture()), root())
