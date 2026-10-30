"""Synthetic-only contract checks for three fixed primary-source macro contexts."""
import unittest

from ai_native.historical_regime_context import prepare_historical_regime_context


class HistoricalRegimeContextTests(unittest.TestCase):
    def test_three_official_references_are_non_authorizing(self):
        for regime, domain in (
            ("US_2008_CREDIT_LIQUIDITY", "federalreserve.gov"),
            ("CA_2020_PANDEMIC_LIQUIDITY", "bankofcanada.ca"),
            ("CA_2022_INFLATION", "statcan.gc.ca"),
        ):
            with self.subTest(regime=regime):
                result = prepare_historical_regime_context(
                    regime_id=regime, analysis_as_of="2026-10-30")
                self.assertIn(domain, result["source_url"])
                self.assertEqual(result["asset_returns"], "NOT_SUPPLIED")
                self.assertEqual(result["shocks_derived"], "NO")
                self.assertEqual(result["historical_calibration"], "NOT_PERFORMED")
                self.assertEqual(result["policy_authority"], "NONE")

    def test_availability_cutoffs_are_conservative(self):
        for regime, cutoff in (
            ("US_2008_CREDIT_LIQUIDITY", "2008-09-22"),
            ("CA_2020_PANDEMIC_LIQUIDITY", "2020-05-30"),
            ("CA_2022_INFLATION", "2022-07-19"),
        ):
            with self.subTest(regime=regime), self.assertRaisesRegex(
                    ValueError, "REGIME_CONTEXT_SOURCE_POSTDATES_CUTOFF"):
                prepare_historical_regime_context(regime_id=regime,
                                                  analysis_as_of=cutoff)

    def test_bad_inputs_and_mutation_are_not_promoted(self):
        for regime, cutoff in (
            (None, "2026-10-30"),
            ("UNKNOWN", "2026-10-30"),
            ("CA_2022_INFLATION", "2026-02-30"),
            ("CA_2022_INFLATION", "2026-2-2"),
        ):
            with self.assertRaises(ValueError):
                prepare_historical_regime_context(regime_id=regime,
                                                  analysis_as_of=cutoff)
        first = prepare_historical_regime_context(
            regime_id="CA_2022_INFLATION", analysis_as_of="2026-10-30")
        first["source_url"] = "https://fake.invalid"
        second = prepare_historical_regime_context(
            regime_id="CA_2022_INFLATION", analysis_as_of="2026-10-30")
        self.assertIn("statcan.gc.ca", second["source_url"])


if __name__ == "__main__":
    unittest.main()
