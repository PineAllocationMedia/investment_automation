from dataclasses import FrozenInstanceError
from pathlib import Path
import inspect
import os
import tempfile
import unittest

from economic_facts import yahoo_quote_archive as archive
from tests.yahoo_quote_fixtures import CAPTURED_AT, chart_response


class YahooQuoteArchiveTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve() / "quotes"
        self.archive = archive.YahooQuoteArchive(self.root)

    def publish(self, raw=None, **changes):
        return self.archive._capture_live(
            chart_response() if raw is None else raw,
            symbol=changes.pop("symbol", "FICT"),
            captured_at=changes.pop("captured_at", CAPTURED_AT),
            **changes,
        )

    def test_exact_endpoint_profile_and_safe_symbols(self):
        self.assertEqual(
            archive.canonical_endpoint("FICT.A-1"),
            "https://query1.finance.yahoo.com/v8/finance/chart/FICT.A-1"
            "?range=5d&interval=1d&events=div%2Csplits&includePrePost=false",
        )
        for value in ("fict", "FICT/../../x", " FICT", "FICT?x", "", True, "A" * 16):
            with self.subTest(value=value), self.assertRaises(archive.YahooQuoteArchiveError):
                archive.canonical_symbol(value)
        self.assertTrue(archive.canonical_endpoint("FICT").startswith("https://"))

    def test_exact_object_receipt_replay_and_deterministic_identity(self):
        raw = chart_response()
        first = self.publish(raw)
        second = self.publish(raw)
        self.assertEqual(first, second)
        self.assertEqual(first.receipt_id, second.receipt_id)
        self.assertEqual(self.archive.read_receipt(first.receipt_id), first)
        self.assertEqual(self.archive.read_object(first), raw)
        self.assertEqual(first.content_sha256, archive.digest(raw))
        self.assertEqual(first.endpoint_profile_id, archive.ENDPOINT_PROFILE_ID)
        self.assertNotIn(b"123.4500", first.to_bytes())

    def test_capture_time_changes_receipt_not_object(self):
        raw = chart_response()
        first = self.publish(raw)
        second = self.publish(raw, captured_at="2026-02-25T12:00:01Z")
        self.assertEqual(first.content_sha256, second.content_sha256)
        self.assertNotEqual(first.receipt_id, second.receipt_id)

    def test_corrupt_object_and_receipt_fail_closed(self):
        receipt = self.publish()
        object_path = self.root / "objects" / receipt.content_sha256
        os.chmod(object_path, 0o600)
        object_path.write_bytes(b"corrupt")
        with self.assertRaises(archive.YahooQuoteArchiveError):
            self.archive.read_object(receipt)

        other_root = self.root.parent / "receipt-corruption"
        other_archive = archive.YahooQuoteArchive(other_root)
        other = other_archive._capture_live(
            chart_response(), symbol="FICT", captured_at="2026-02-25T12:00:01Z")
        receipt_path = other_root / "receipts" / (other.receipt_id + ".json")
        os.chmod(receipt_path, 0o600)
        receipt_path.write_bytes(b"{}")
        with self.assertRaises(archive.YahooQuoteArchiveError):
            other_archive.read_receipt(other.receipt_id)

    def test_overwrite_forbidden_and_records_frozen(self):
        receipt = self.publish()
        with self.assertRaises(archive.YahooQuoteArchiveError):
            self.archive._publish("receipts", receipt.receipt_id + ".json", b"{}")
        with self.assertRaises(FrozenInstanceError):
            receipt.requested_symbol = "OTHER"

    def test_receipt_rejects_duplicate_keys_and_unsafe_membership(self):
        with self.assertRaises(archive.YahooQuoteArchiveError):
            archive.YahooQuoteReceipt.from_bytes(b'{"schema_version":"x","schema_version":"y"}')
        receipt = self.publish()
        other = archive.YahooQuoteArchive(self.root.parent / "other")
        with self.assertRaises(archive.YahooQuoteArchiveError):
            other.read_object(receipt)

    def test_public_archive_has_no_capture_api(self):
        public = {name for name, _ in inspect.getmembers(archive.YahooQuoteArchive)
                  if not name.startswith("_")}
        self.assertEqual(public, {"read_object", "read_receipt"})


if __name__ == "__main__":
    unittest.main()
