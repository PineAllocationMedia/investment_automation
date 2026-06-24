import unittest

from src.stress_test_engine import compute_stress_tests


class StressTestTest(unittest.TestCase):
    def test_bear_market_loss_is_calculated(self):
        rows = [{"ticker": "MSFT", "current_value": 1000}, {"ticker": "VFV.TO", "current_value": 1000}]
        results = compute_stress_tests(rows, {}, {})
        bear = results[0]
        self.assertEqual(bear["scenario"], "Bear market normal")
        self.assertAlmostEqual(bear["estimated_loss_dollars"], 450)


if __name__ == "__main__":
    unittest.main()
