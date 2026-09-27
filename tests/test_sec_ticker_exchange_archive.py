"""Immutable archive tests with fictional association bytes."""
from dataclasses import FrozenInstanceError, asdict, replace
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from economic_facts import sec_ticker_exchange_archive as a
from tests.sec_ticker_exchange_fixtures import T1, T2, snapshot


class SecTickerExchangeArchiveTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve() / "archive"
        self.archive = a.SecTickerExchangeArchive(self.root)

    def capture(self, raw=None, captured_at=T1):
        return self.archive._capture_live(snapshot() if raw is None else raw,
                                          captured_at=captured_at)

    @staticmethod
    def overwrite(path, raw):
        path.chmod(0o600)
        path.write_bytes(raw)

    def test_exact_bytes_digest_endpoint_and_typed_read(self):
        raw = snapshot().replace(b'"data":', b'\n"data":')
        receipt = self.capture(raw)
        self.assertEqual(self.archive.read_object(receipt), raw)
        self.assertEqual(receipt.content_sha256, hashlib.sha256(raw).hexdigest())
        self.assertEqual(receipt.byte_length, len(raw))
        self.assertEqual(receipt.endpoint, a.ENDPOINT)
        self.assertEqual(self.archive.read_receipt(receipt.receipt_id), receipt)

    def test_identical_recapture_one_object_distinct_receipts(self):
        first = self.capture()
        second = self.capture(captured_at=T2)
        self.assertEqual(first.content_sha256, second.content_sha256)
        self.assertNotEqual(first.receipt_id, second.receipt_id)
        self.assertEqual(len(list((self.root / "objects").iterdir())), 1)
        self.assertEqual(len(list((self.root / "receipts").iterdir())), 2)

    def test_changed_capture_preserves_both(self):
        first = self.capture()
        changed = snapshot([[7654321, "FICTIONAL BETA", "BETA", "NYSE"]])
        second = self.capture(changed, captured_at=T2)
        self.assertEqual(self.archive.read_object(first), snapshot())
        self.assertEqual(self.archive.read_object(second), changed)

    def test_idempotent_no_overwrite_and_path_independent_identity(self):
        first = self.capture()
        self.assertEqual(first, self.capture())
        other = a.SecTickerExchangeArchive(self.root.parent / "other")
        second = other._capture_live(snapshot(), captured_at=T1)
        self.assertEqual(first.receipt_id, second.receipt_id)
        self.assertEqual(first.receipt_id,
                         a.digest(b"pam:sec-ticker-exchange-receipt:v1\0" +
                                  a.canonical_json(asdict(first))))

    def test_receipt_closed_frozen_and_no_authority_fields(self):
        receipt = self.capture()
        with self.assertRaises(FrozenInstanceError):
            receipt.captured_at = T2
        for key, value in (("endpoint", "https://www.sec.gov/data/company_tickers_exchange.json"),
                           ("source_kind", "TRUSTED_IDENTITY"), ("byte_length", True),
                           ("byte_length", 0), ("content_sha256", "../object")):
            with self.subTest(key=key), self.assertRaises(a.SecTickerExchangeArchiveError):
                replace(receipt, **{key: value})
        payload = json.loads(receipt.to_bytes())
        for key in ("published_at", "available_at", "qualified", "identity"):
            with self.assertRaises(a.SecTickerExchangeArchiveError):
                a.SecTickerExchangeReceipt.from_bytes(json.dumps({**payload, key: True}).encode())

    def test_bad_receipt_json_duplicate_keys_and_nonfinite_rejected(self):
        for raw in (b"[]", b"{}", b"\xff", b'{"x":1,"x":2}', b'{"x":NaN}',
                    b"[" * 1100 + b"]" * 1100, b" " * 4097):
            with self.subTest(raw=raw[:20]), self.assertRaises(a.SecTickerExchangeArchiveError):
                a.SecTickerExchangeReceipt.from_bytes(raw)

    def test_timestamp_requires_real_explicit_offset_and_canonicalizes(self):
        self.assertEqual(self.capture(), self.capture(captured_at="2026-09-26T08:00:00-04:00"))
        for value in (T1[:-1], "2026-09-26", "2026-09-26T12:00:00-00:00",
                      "2026-02-30T12:00:00Z", None):
            with self.subTest(value=value), self.assertRaises(a.SecTickerExchangeArchiveError):
                self.capture(captured_at=value)

    def test_missing_reads_create_nothing_and_no_latest_api(self):
        with self.assertRaises(a.SecTickerExchangeArchiveError):
            self.archive.read_receipt("0" * 64)
        self.assertFalse(self.root.exists())
        self.assertEqual({name for name in vars(a.SecTickerExchangeArchive)
                          if not name.startswith("_")}, {"read_receipt", "read_object"})

    def test_detached_receipt_missing_object_and_corruption_rejected(self):
        receipt = self.capture()
        with self.assertRaises(a.SecTickerExchangeArchiveError):
            self.archive.read_object(replace(receipt, captured_at=T2))
        target = self.root / "objects" / receipt.content_sha256
        self.overwrite(target, b"x" * receipt.byte_length)
        with self.assertRaises(a.SecTickerExchangeArchiveError):
            self.archive.read_object(receipt)
        target.unlink()
        with self.assertRaises(a.SecTickerExchangeArchiveError):
            self.archive.read_object(receipt)

    def test_corrupt_or_misnamed_receipt_rejected(self):
        receipt = self.capture()
        target = self.root / "receipts" / (receipt.receipt_id + ".json")
        self.overwrite(target, replace(receipt, captured_at=T2).to_bytes())
        with self.assertRaises(a.SecTickerExchangeArchiveError):
            self.archive.read_receipt(receipt.receipt_id)

    def test_path_symlink_hardlink_fifo_and_directory_attacks_rejected(self):
        for selector in ("latest", "../escape", "/escape", "0" * 64 + "?x", None):
            with self.assertRaises(a.SecTickerExchangeArchiveError):
                self.archive.read_receipt(selector)
        receipt = self.capture()
        target = self.root / "objects" / receipt.content_sha256
        original = target.read_bytes()
        outside = self.root.parent / "outside"
        outside.write_bytes(original)
        for attack in ("symlink", "hardlink", "fifo", "directory"):
            target.unlink()
            if attack == "symlink":
                target.symlink_to(outside)
            elif attack == "hardlink":
                os.link(outside, target)
            elif attack == "fifo":
                os.mkfifo(target)
            else:
                target.mkdir()
            with self.subTest(attack=attack), self.assertRaises(a.SecTickerExchangeArchiveError):
                self.archive.read_object(receipt)
            target.rmdir() if attack == "directory" else target.unlink()
            target.write_bytes(original)

    def test_symlink_root_and_ancestor_rejected(self):
        outside = self.root.parent / "outside"
        outside.mkdir()
        self.root.symlink_to(outside, target_is_directory=True)
        with self.assertRaises(a.SecTickerExchangeArchiveError):
            self.capture()
        self.assertEqual(list(outside.iterdir()), [])

    def test_atomic_publication_failure_never_reports_success(self):
        with patch.object(a.os, "link", side_effect=OSError("private")), \
             self.assertRaises(a.SecTickerExchangeArchiveError):
            self.capture()
        self.assertEqual(list((self.root / "objects").iterdir()), [])
        self.assertFalse((self.root / "receipts").exists())

    def test_receipt_failure_can_leave_only_unreferenced_object(self):
        original = a.SecTickerExchangeArchive._publish
        def publish(archive, kind, name, raw):
            if kind == "receipts":
                raise a.SecTickerExchangeArchiveError("fixture")
            return original(archive, kind, name, raw)
        with patch.object(a.SecTickerExchangeArchive, "_publish", publish), \
             self.assertRaises(a.SecTickerExchangeArchiveError):
            self.capture()
        self.assertEqual((self.root / "objects" / a.digest(snapshot())).read_bytes(), snapshot())
        self.assertFalse((self.root / "receipts").exists())

    def test_body_type_size_and_root_path_bounds(self):
        for raw in (b"", bytearray(snapshot())):
            with self.assertRaises(a.SecTickerExchangeArchiveError):
                self.capture(raw)
        with patch.object(a, "MAX_BODY_BYTES", 2), self.assertRaises(a.SecTickerExchangeArchiveError):
            self.capture()
        with self.assertRaises(a.SecTickerExchangeArchiveError):
            a.SecTickerExchangeArchive(self.root / "alias" / ".." / "escape")


if __name__ == "__main__":
    unittest.main()
