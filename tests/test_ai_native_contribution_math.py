import unittest

from ai_native.contribution_math import project_gross_contribution


class GrossContributionTests(unittest.TestCase):
    def sample(self, **overrides):
        args = {
            "positions_base": {"ABC:TSX": "400.00", "VFV:TSX": "600.00"},
            "allocations_pct": {"ABC:TSX": "60", "VFV:TSX": "40"},
            "contribution_base": "1000.00", "currency": "CAD", "as_of": "2026-10-28",
            "scope_complete": True, "cash_accounted_for": True,
            "same_currency_basis_verified": True, "instrument_identity_verified": True,
        }
        args.update(overrides)
        return project_gross_contribution(**args)

    def test_conserves_gross_capital_and_weights(self):
        result = self.sample()
        self.assertEqual(result["status"], "GROSS_PROJECTION_ONLY")
        self.assertEqual(result["allocations"], {"ABC:TSX": "600.00", "VFV:TSX": "400.00"})
        self.assertEqual(result["projected_total"], "2000.00")
        self.assertEqual(result["projected_positions"], {"ABC:TSX": "1000.00", "VFV:TSX": "1000.00"})
        self.assertEqual(result["projected_weights_pct"]["VFV:TSX"], "50")
        self.assertEqual(result["net_execution_status"], "UNAVAILABLE_COSTS_NOT_ASSESSED")

    def test_missing_coverage_blocks_weight_calculation(self):
        result = self.sample(scope_complete=False, cash_accounted_for=False)
        self.assertEqual(result["status"], "UNAVAILABLE")
        self.assertIn("SCOPE_INCOMPLETE", result["reason_codes"])
        self.assertIn("CASH_UNKNOWN", result["reason_codes"])

    def test_unknown_or_malformed_currency_blocks_gross_projection(self):
        for value in ("UNKNOWN", "", "N/A", "$", "US", "CAD1", "CAD/USD", None):
            with self.subTest(currency=value):
                result = self.sample(currency=value)
                self.assertEqual(result["status"], "UNAVAILABLE")
                self.assertEqual(result["reason_codes"], ["ACCOUNT_CURRENCY_UNKNOWN"])
                self.assertNotIn("projected_positions", result)

    def test_lowercase_currency_normalized_without_broker_certification(self):
        result = self.sample(currency=" cad ")
        self.assertEqual(result["status"], "GROSS_PROJECTION_ONLY")
        self.assertEqual(result["currency"], "CAD")
        self.assertEqual(result["net_execution_status"], "UNAVAILABLE_COSTS_NOT_ASSESSED")

    def test_multiple_gaps_remain_separate_without_any_projection(self):
        result = self.sample(currency="UNKNOWN", scope_complete=False,
                             same_currency_basis_verified=False)
        self.assertEqual(result["status"], "UNAVAILABLE")
        self.assertEqual(result["reason_codes"], [
            "SCOPE_INCOMPLETE", "CURRENCY_BASIS_UNVERIFIED",
            "ACCOUNT_CURRENCY_UNKNOWN"])
        self.assertNotIn("allocations", result)

    def test_unverified_cross_currency_blocks(self):
        result = self.sample(same_currency_basis_verified=False)
        self.assertEqual(result["reason_codes"], ["CURRENCY_BASIS_UNVERIFIED"])

    def test_exact_hundred_percent_is_required(self):
        with self.assertRaisesRegex(ValueError, "exactly 100"):
            self.sample(allocations_pct={"ABC:TSX": "40", "VFV:TSX": "40"})

    def test_negative_or_overprecision_cash_is_refused(self):
        for value in ("-1.00", "1.005", "NaN", "Infinity"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.sample(contribution_base=value)

    def test_cent_rounding_is_conservative(self):
        result = self.sample(
            positions_base={"A": "0", "B": "0", "C": "0"},
            allocations_pct={"A": "33.33", "B": "33.33", "C": "33.34"},
            contribution_base="0.05",
        )
        self.assertEqual(result["allocations"], {"A": "0.02", "B": "0.01", "C": "0.02"})
        self.assertEqual(result["projected_total"], "0.05")
        self.assertEqual(result["current_weights_pct"], None)

    def test_new_instrument_is_allowed_with_complete_scoped_portfolio(self):
        result = self.sample(allocations_pct={"NEW:LSE": "100"})
        self.assertEqual(result["projected_positions"]["NEW:LSE"], "1000.00")
        self.assertEqual(result["projected_total"], "2000.00")

    def test_invalid_dates_and_unresolved_instrument_rejected(self):
        self.assertEqual(self.sample(as_of="2026-02-30")["status"], "UNAVAILABLE")
        self.assertIn("INSTRUMENT_IDENTITY_UNVERIFIED", self.sample(instrument_identity_verified=False)["reason_codes"])


if __name__ == "__main__":
    unittest.main()
