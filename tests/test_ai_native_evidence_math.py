import unittest
from ai_native.evidence_math import audit_calculation


class EvidenceMathTests(unittest.TestCase):
    def fact(self, **changes):
        v = {
            "id": "F1", "economic_issuer": "SYNTHETIC", "metric": "OPERATING_INCOME",
            "value": "25", "currency": "USD", "unit": "MILLIONS",
            "accounting_basis": "US_GAAP", "consolidation": "CONSOLIDATED",
            "period_start": "2025-01-01", "period_end": "2025-12-31",
            "observed_at": "2026-01-15", "source_url": "https://example.com/filing",
            "rights_status": "PERMITTED", "verification_status": "INDICATIVE",
        }
        v.update(changes)
        return v

    def check(self, operation, left=None, right=None, **kwargs):
        left = left or self.fact()
        right = right or self.fact(id="F2", metric="REVENUE", value="100")
        return audit_calculation(operation, left, right, as_of=kwargs.get("as_of", "2026-10-28"))

    def test_margin_calculates_without_upgrading_source(self):
        v = self.check("OPERATING_MARGIN")
        self.assertEqual((v["status"], v["value"]), ("FORMALLY_CALCULATED", "25.00"))
        self.assertEqual(v["source_verification"], "NOT_PERFORMED")
        self.assertFalse(v["decision_grade"])

    def test_negative_operating_income_margin(self):
        self.assertEqual(self.check("OPERATING_MARGIN", left=self.fact(value="-12"))["value"], "-12.00")

    def test_annual_revenue_growth_leap_year(self):
        prior = self.fact(id="P", metric="REVENUE", value="100", period_start="2024-01-01", period_end="2024-12-31", observed_at="2025-04-01")
        cur = self.fact(id="C", metric="REVENUE", value="120")
        v = self.check("REVENUE_GROWTH_YOY", left=cur, right=prior)
        self.assertEqual((v["status"], v["value"]), ("FORMALLY_CALCULATED", "20.00"))

    def test_growth_rejects_different_period_length_53w(self):
        prev = self.fact(id="P", metric="REVENUE", period_start="2023-12-31", period_end="2024-12-28")
        cur = self.fact(id="C", metric="REVENUE", period_start="2024-12-29", period_end="2026-01-03")
        v = self.check("REVENUE_GROWTH_YOY", left=cur, right=prev)
        self.assertIn("INCOMPARABLE_FISCAL_PERIOD_LENGTH", v["reason_codes"])

    def test_growth_rejects_gap_between_years(self):
        prev = self.fact(id="P", metric="REVENUE", period_start="2024-01-01", period_end="2024-12-31")
        cur = self.fact(id="C", metric="REVENUE", period_start="2025-01-03")
        self.assertIn("NONADJACENT_PERIODS", self.check("REVENUE_GROWTH_YOY", left=cur, right=prev)["reason_codes"])

    def test_gross_cfo_proxy_not_normalized_cash(self):
        l = self.fact(metric="CFO", value="80")
        r = self.fact(id="F2", metric="PPE_CASH_OUTFLOW", value="25")
        v = self.check("CFO_LESS_PPE", left=l, right=r)
        self.assertEqual(v["value"], "55.00")
        self.assertIn("NOT_NORMALIZED_FCF", v["metric"])

    def test_rejects_currency_and_accounting_mismatch(self):
        r = self.fact(id="F2", metric="REVENUE", currency="CAD", accounting_basis="IFRS")
        reasons = self.check("OPERATING_MARGIN", right=r)["reason_codes"]
        self.assertIn("CURRENCY_MISMATCH", reasons)
        self.assertIn("ACCOUNTING_BASIS_MISMATCH", reasons)

    def test_rejects_issuer_scope_and_period_mismatch(self):
        r = self.fact(id="F2", metric="REVENUE", economic_issuer="DIFFERENT", consolidation="PARENT", period_start="2024-01-01")
        codes = self.check("OPERATING_MARGIN", right=r)["reason_codes"]
        self.assertIn("ISSUER_MISMATCH", codes)
        self.assertIn("CONSOLIDATION_SCOPE_MISMATCH", codes)
        self.assertIn("PERIOD_MISMATCH", codes)

    def test_restricts_known_restricted_and_conflicted_source(self):
        r = self.fact(id="F2", metric="REVENUE", rights_status="RESTRICTED", verification_status="CONFLICTED")
        codes = self.check("OPERATING_MARGIN", right=r)["reason_codes"]
        self.assertIn("RESTRICTED_SOURCE_USE", codes)
        self.assertIn("UNRESOLVED_SOURCE_FACT", codes)

    def test_uncertain_rights_are_not_misrepresented(self):
        r = self.fact(id="F2", metric="REVENUE", rights_status="UNCERTAIN")
        self.assertEqual(self.check("OPERATING_MARGIN", right=r)["permission_caveat"], "SOURCE_USE_UNCERTAIN_REVIEW_REQUIRED")

    def test_observation_after_as_of_and_future_period_block(self):
        r = self.fact(id="F2", metric="REVENUE", observed_at="2026-11-01", period_end="2026-12-31")
        codes = self.check("OPERATING_MARGIN", right=r)["reason_codes"]
        self.assertIn("OBSERVATION_AFTER_ANALYSIS_CUTOFF", codes)
        self.assertIn("FINANCIAL_PERIOD_END_AFTER_ANALYSIS_CUTOFF", codes)

    def test_bad_values_and_dates_not_silently_coerced(self):
        for bad in ("NaN", "Infinity", "1e1000000x", ""):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                self.check("OPERATING_MARGIN", left=self.fact(value=bad))
        with self.assertRaises(ValueError):
            self.check("OPERATING_MARGIN", left=self.fact(period_start="2026-02-30"))

    def test_duplicate_fact_id_and_bad_metrics_block(self):
        res = self.check("OPERATING_MARGIN", right=self.fact(metric="REVENUE", value="100"))
        self.assertIn("DUPLICATE_FACT_ID", res["reason_codes"])
        res = self.check("OPERATING_MARGIN", right=self.fact(id="F2", metric="CFO"))
        self.assertIn("METRIC_MISMATCH", res["reason_codes"])


if __name__ == "__main__":
    unittest.main()
