from pathlib import Path
import tempfile
import unittest

from economic_facts.yahoo_split_history_archive import (
    ENDPOINT_PROFILE_ID,
    YahooSplitHistoryArchive,
    YahooSplitHistoryArchiveError,
    canonical_endpoint,
    parameter_profile,
)
from tests.yahoo_split_history_fixtures import split_chart_response


class YahooSplitHistoryArchiveTests(unittest.TestCase):
    def test_fixed_explicit_interval_profile_and_immutable_replay(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        archive = YahooSplitHistoryArchive(Path(temporary.name).resolve() / "archive")
        raw = split_chart_response()
        receipt = archive._capture_live(
            raw, symbol="FICT", start_epoch=1700000000, end_epoch=1800000000,
            captured_at="2027-01-16T12:00:00Z")
        self.assertEqual(receipt.endpoint_profile_id, ENDPOINT_PROFILE_ID)
        self.assertEqual(receipt.parameter_profile,
                         "period1=1700000000&period2=1800000000&interval=1d&events=splits&includePrePost=false")
        self.assertEqual(receipt.endpoint,
                         canonical_endpoint("FICT", 1700000000, 1800000000))
        self.assertEqual(archive.read_object(receipt), raw)
        self.assertEqual(parameter_profile(1700000000, 1800000000),
                         receipt.parameter_profile)
        with self.assertRaises(YahooSplitHistoryArchiveError):
            parameter_profile(1800000000, 1700000000)


if __name__ == "__main__":
    unittest.main()
