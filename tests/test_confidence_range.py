import unittest

from src.confidence_range_engine import compute_conviction_confidence_range


class ConfidenceRangeTest(unittest.TestCase):
    def test_conviction_range_is_tighter_for_high_reliability(self):
        tight = compute_conviction_confidence_range(
            85,
            {"data_reliability_level": "HIGH", "auto_estimate_dependency": "LOW"},
            {"score_evidence_level": "CONFIRMED", "score_estimate_gap": 0.3},
        )
        wide = compute_conviction_confidence_range(
            85,
            {"data_reliability_level": "LOW", "auto_estimate_dependency": "HIGH"},
            {"score_evidence_level": "ESTIMATE_HEAVY", "score_estimate_gap": 3.0},
        )

        tight_width = tight["conviction_confidence_high"] - tight["conviction_confidence_low"]
        wide_width = wide["conviction_confidence_high"] - wide["conviction_confidence_low"]
        self.assertLess(tight_width, wide_width)
        self.assertIn(wide["conviction_confidence_label"], {"WIDE", "VERY_WIDE"})


if __name__ == "__main__":
    unittest.main()
