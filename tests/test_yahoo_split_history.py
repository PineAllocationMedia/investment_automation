from dataclasses import FrozenInstanceError
from pathlib import Path
import tempfile
import unittest

from economic_facts import yahoo_split_history as split_history
from economic_facts.yahoo_split_history_archive import YahooSplitHistoryArchive
from tests.yahoo_split_history_fixtures import split_chart_response, split_event


class YahooSplitHistoryTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.archive = YahooSplitHistoryArchive(Path(temporary.name).resolve() / "splits")
        self.start = 1700000000
        self.end = 1800000000

    def capture(self, raw=None, **changes):
        values = dict(symbol="FICT", start_epoch=self.start, end_epoch=self.end,
                      captured_at="2027-01-16T12:00:00Z")
        values.update(changes)
        return self.archive._capture_live(
            split_chart_response() if raw is None else raw, **values)

    def test_empty_complete_interval_is_positive_evidence(self):
        result = split_history.extract_yahoo_split_history(
            self.archive, self.capture().receipt_id)
        self.assertIs(result.status,
                      split_history.SplitHistoryStatus.SPLIT_HISTORY_EXTRACTED)
        self.assertEqual(result.events, ())
        self.assertEqual(result.returned_symbol, "FICT")
        self.assertEqual(result.license_status, "UNKNOWN")
        self.assertEqual(result.use_status, "REVIEW_REQUIRED")
        with self.assertRaises(FrozenInstanceError):
            result.status = split_history.SplitHistoryStatus.SOURCE_CONFLICT

    def test_exact_integral_ratio_and_identity(self):
        event = split_event(1750000000, 3, 2)
        result = split_history.extract_yahoo_split_history(
            self.archive, self.capture(split_chart_response(events=(event,))).receipt_id)
        self.assertIs(result.status,
                      split_history.SplitHistoryStatus.SPLIT_HISTORY_EXTRACTED)
        self.assertEqual((result.events[0].numerator, result.events[0].denominator),
                         (3, 2))
        self.assertEqual(result.events[0].split_ratio_source, "3:2")
        self.assertRegex(result.semantic_id, r"^[0-9a-f]{64}$")
        self.assertRegex(result.evidence_id, r"^[0-9a-f]{64}$")

    def test_ratio_symbol_date_and_shape_fail_closed(self):
        cases = (
            (split_chart_response(symbol="OTHER"),
             split_history.SplitHistoryStatus.SOURCE_CONFLICT),
            (split_chart_response(events=(split_event(1750000000, 2, 1, ratio="3:1"),)),
             split_history.SplitHistoryStatus.SOURCE_CONFLICT),
            (split_chart_response(events=(split_event(self.end + 1, 2, 1),)),
             split_history.SplitHistoryStatus.SPLIT_HISTORY_UNSUPPORTED),
            (split_chart_response(result_count=2),
             split_history.SplitHistoryStatus.SOURCE_CONFLICT),
        )
        for raw, expected in cases:
            with self.subTest(expected=expected):
                result = split_history.extract_yahoo_split_history(
                    self.archive, self.capture(raw).receipt_id)
                self.assertIs(result.status, expected)


if __name__ == "__main__":
    unittest.main()
