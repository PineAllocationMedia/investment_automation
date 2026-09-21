"""Private fixture publication tests; no LIVE observation is made."""
from dataclasses import FrozenInstanceError, asdict, replace
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from economic_facts import nasdaq_listed_archive as a
from tests.nasdaq_listed_fixtures import T1, T2, directory, row


class NasdaqListedArchiveTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve() / "archive"
        self.archive = a.NasdaqListedArchive(self.root)

    def capture(self, raw=None, **changes):
        args = dict(captured_at=T1)
        args.update(changes)
        return self.archive._capture_live(directory() if raw is None else raw, **args)

    def overwrite(self, path, raw):
        path.chmod(0o600)
        path.write_bytes(raw)

    def test_exact_byte_replay(self):
        raw = directory().replace(b"\n", b"\r\n")
        receipt = self.capture(raw)
        self.assertEqual(self.archive.read_object(receipt), raw)
        self.assertEqual(receipt.content_sha256, hashlib.sha256(raw).hexdigest())
        self.assertEqual(receipt.byte_length, len(raw))
        self.assertEqual(self.archive.read_receipt(receipt.receipt_id), receipt)

    def test_fixed_endpoint(self):
        self.assertEqual(self.capture().endpoint,
                         "https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt")

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
        changed = directory([row("OTHER")])
        second = self.capture(changed, captured_at=T2)
        self.assertNotEqual(first.content_sha256, second.content_sha256)
        self.assertEqual(self.archive.read_object(first), directory())
        self.assertEqual(self.archive.read_object(second), changed)

    def test_identity_domain_and_path_independence(self):
        first = self.capture()
        other = a.NasdaqListedArchive(self.root.parent / "other")
        second = other._capture_live(directory(), captured_at=T1)
        self.assertEqual(first, second)
        self.assertEqual(first.receipt_id,
                         a.digest(b"pam:nasdaq-listed-receipt:v1\0" + a.canonical_json(asdict(first))))
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
            with self.subTest(key=key), self.assertRaises(a.NasdaqListedArchiveError):
                replace(receipt, **{key: value})
        payload = json.loads(receipt.to_bytes())
        for key in ("published_at", "available_at", "authority", "qualified"):
            with self.subTest(key=key), self.assertRaises(a.NasdaqListedArchiveError):
                a.NasdaqListedReceipt.from_bytes(json.dumps({**payload, key: True}).encode())

    def test_bad_receipt_serializations(self):
        for raw in (b"[]", b"null", b"{}", b"\xff", b'{"cik":0,"cik":1}', b'{"x":NaN}',
                    b"[" * 1100 + b"]" * 1100, b" " * 4097):
            with self.subTest(raw=raw[:20]), self.assertRaises(a.NasdaqListedArchiveError):
                a.NasdaqListedReceipt.from_bytes(raw)

    def test_timestamps_canonical_and_not_naive(self):
        self.assertEqual(self.capture(), self.capture(captured_at="2026-09-21T08:00:00-04:00"))
        for value in (T1[:-1], "2026-09-21", "2026-09-21T12:00:00-00:00", "2026-09-21T12:00:00+24:00",
                      "2026-02-30T12:00:00Z", "٢٠٢٦-09-20T12:00:00Z", None):
            with self.subTest(value=value), self.assertRaises(a.NasdaqListedArchiveError):
                self.capture(captured_at=value)

    def test_missing_archive_reads_create_nothing(self):
        with self.assertRaises(a.NasdaqListedArchiveError):
            self.archive.read_receipt("0" * 64)
        self.assertFalse(self.root.exists())

    def test_missing_receipt_and_detached_self_authored_receipt(self):
        receipt = self.capture()
        with self.assertRaises(a.NasdaqListedArchiveError):
            self.archive.read_object(replace(receipt, captured_at=T2))
        (self.root / "receipts" / (receipt.receipt_id + ".json")).unlink()
        with self.assertRaises(a.NasdaqListedArchiveError):
            self.archive.read_object(receipt)

    def test_wrong_archive_or_untyped_receipt(self):
        receipt = self.capture()
        with self.assertRaises(a.NasdaqListedArchiveError):
            a.NasdaqListedArchive(self.root.parent / "other").read_object(receipt)
        with self.assertRaises(a.NasdaqListedArchiveError):
            self.archive.read_object(asdict(receipt))

    def test_corrupt_or_misnamed_receipt(self):
        receipt = self.capture()
        target = self.root / "receipts" / (receipt.receipt_id + ".json")
        self.overwrite(target, replace(receipt, captured_at=T2).to_bytes())
        with self.assertRaises(a.NasdaqListedArchiveError):
            self.archive.read_receipt(receipt.receipt_id)
        with self.assertRaises(a.NasdaqListedArchiveError):
            self.capture()
        payload = json.loads(receipt.to_bytes())
        payload["byte_length"] += 1
        self.overwrite(target, json.dumps(payload).encode())
        with self.assertRaises(a.NasdaqListedArchiveError):
            self.archive.read_object(receipt)

    def test_object_length_and_hash_corruption(self):
        receipt = self.capture()
        target = self.root / "objects" / receipt.content_sha256
        for raw in (directory()[:-1], directory() + b"x", b"x" * len(directory())):
            self.overwrite(target, raw)
            with self.assertRaises(a.NasdaqListedArchiveError):
                self.archive.read_object(receipt)
        with self.assertRaises(a.NasdaqListedArchiveError):
            self.capture()
        self.assertEqual(target.read_bytes(), b"x" * len(directory()))

    def test_missing_object(self):
        receipt = self.capture()
        (self.root / "objects" / receipt.content_sha256).unlink()
        with self.assertRaises(a.NasdaqListedArchiveError):
            self.archive.read_object(receipt)

    def test_path_attacks_fail_before_read(self):
        for value in ("../escape", "/escape", "0" * 64 + "?x", "٠" * 64, None):
            with self.subTest(value=value), self.assertRaises(a.NasdaqListedArchiveError):
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
                with self.assertRaises(a.NasdaqListedArchiveError):
                    self.capture()
                target.unlink()
        self.assertEqual(list(outside.iterdir()), [])

    def test_symlink_ancestor_rejected(self):
        outside = self.root.parent / "outside"
        outside.mkdir()
        self.root.symlink_to(outside, target_is_directory=True)
        with self.assertRaises(a.NasdaqListedArchiveError):
            a.NasdaqListedArchive(self.root / "child")._capture_live(
                directory(), captured_at=T1)
        self.assertEqual(list(outside.iterdir()), [])

    def test_symlink_hardlink_fifo_directory_entries_rejected(self):
        receipt = self.capture()
        for kind, name, raw in (("objects", receipt.content_sha256, directory()),
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
                    with self.assertRaises(a.NasdaqListedArchiveError):
                        self.archive.read_object(receipt)
                    if attack == "directory":
                        target.rmdir()
                    else:
                        target.unlink()
                    target.write_bytes(raw)

    def test_atomic_link_failure_no_partial_publication(self):
        with patch.object(a.os, "link", side_effect=OSError("private failure")), self.assertRaises(a.NasdaqListedArchiveError):
            self.capture()
        self.assertEqual(list((self.root / "objects").iterdir()), [])
        self.assertFalse((self.root / "receipts").exists())
        self.capture()

    def test_fsync_failure_before_link_leaves_no_evidence(self):
        with patch.object(a.os, "fsync", side_effect=OSError("private failure")), self.assertRaises(a.NasdaqListedArchiveError):
            self.capture()
        self.assertFalse(any(self.root.rglob("*.json")))
        self.assertFalse((self.root / "receipts").exists())

    def test_receipt_failure_leaves_only_unreferenced_object(self):
        original = a.NasdaqListedArchive._publish
        def publish(archive, kind, name, raw):
            if kind == "receipts":
                raise a.NasdaqListedArchiveError("fixture failure")
            return original(archive, kind, name, raw)
        with patch.object(a.NasdaqListedArchive, "_publish", publish), self.assertRaises(a.NasdaqListedArchiveError):
            self.capture()
        self.assertEqual((self.root / "objects" / a.digest(directory())).read_bytes(), directory())
        self.assertFalse((self.root / "receipts").exists())

    def test_no_public_capture_or_history_authority(self):
        self.assertEqual({name for name in vars(a.NasdaqListedArchive) if not name.startswith("_")},
                         {"read_receipt", "read_object"})
        self.assertEqual(set(a.NasdaqListedReceipt.__dataclass_fields__), {
            "schema_version", "source_kind", "resource_kind", "endpoint", "content_sha256",
            "byte_length", "captured_at", "acquisition_contract_version"})

    def test_read_bounds_before_allocating(self):
        receipt = self.capture()
        for kind, name, size in (("receipts", receipt.receipt_id + ".json", 4097),
                                  ("objects", receipt.content_sha256, receipt.byte_length + 1)):
            path = self.root / kind / name
            original = path.read_bytes()
            self.overwrite(path, b"x" * size)
            with self.assertRaises(a.NasdaqListedArchiveError):
                self.archive.read_object(receipt)
            self.overwrite(path, original)

    def test_bounded_read_requests(self):
        receipt = self.capture()
        reads = []
        real = a.os.fdopen
        class Stream:
            def __init__(self, handle, mode):
                self.inner = real(handle, mode)
            def __enter__(self):
                return self
            def __exit__(self, *args):
                self.inner.close()
            def fileno(self):
                return self.inner.fileno()
            def read(self, size):
                reads.append(size)
                return self.inner.read(size)
        with patch.object(a.os, "fdopen", Stream):
            self.archive.read_object(receipt)
        self.assertEqual(reads, [4097, receipt.byte_length + 1])

    def test_directory_fsync_failure_does_not_report_success(self):
        self.capture()
        real = a.os.fsync
        import stat
        def fail_directory(fd):
            if stat.S_ISDIR(a.os.fstat(fd).st_mode):
                raise OSError("private path")
            real(fd)
        with patch.object(a.os, "fsync", side_effect=fail_directory), self.assertRaises(a.NasdaqListedArchiveError):
            self.capture(captured_at=T2)
        self.assertEqual(self.archive.read_object(self.capture()), directory())

    def test_path_parent_components_and_invalid_body_bounds(self):
        with self.assertRaises(a.NasdaqListedArchiveError):
            a.NasdaqListedArchive(self.root / "alias" / ".." / "escape")
        for raw in (b"", bytearray(directory())):
            with self.assertRaises(a.NasdaqListedArchiveError):
                self.capture(raw)
        with patch.object(a, "MAX_BODY_BYTES", 2), self.assertRaises(a.NasdaqListedArchiveError):
            self.capture()
        self.assertFalse(self.root.exists())
