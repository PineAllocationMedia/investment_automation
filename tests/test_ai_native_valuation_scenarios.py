import copy
import unittest
from ai_native.valuation_scenarios import evaluate_valuation_scenarios


class ScenarioTests(unittest.TestCase):
    def setup_case(self, **changes):
        base = dict(analysis_id="SYN-01", analysis_as_of="2026-10-28", security_id="ABC:TSX",
                    currency="CAD", quoted_at="2026-10-28", quote_source_ref="S-QUOTE-1",
                    price_per_share="100.00", horizon_years=2,
                    security_basis_confirmed_by_caller=True,
                    currency_basis_confirmed_by_caller=True)
        rows = {}
        for label, value in (("BEAR", "81"), ("BASE", "121"), ("BULL", "144")):
            rows[label] = dict(valuation_method="OTHER_EXPLICIT", assumption_basis="PAM_ASSUMPTION",
                               rationale_ref=f"V-{label}", terminal_price_per_share=value,
                               terminal_value_ref=f"S-{label}", annual_distributions_per_share=None)
        base['scenarios'] = rows
        base.update(changes)
        return base

    def case(self, **changes):
        return evaluate_valuation_scenarios(**self.setup_case(**changes))

    def test_price_only_cagr_bear_base_bull(self):
        out = self.case()
        rows = out["scenarios_private"]
        self.assertEqual([rows[n]["scenario_return_pct_annual"] for n in ("BEAR", "BASE", "BULL")], ["-10.00", "10.00", "20.00"])
        self.assertTrue(all(v["return_measure"] == "PRICE_ONLY_CAGR_NOT_TOTAL_RETURN" for v in rows.values()))
        self.assertTrue(all("DISTRIBUTIONS_UNKNOWN_PRICE_RETURN_ONLY" in v["reason_codes"] for v in rows.values()))
        self.assertIn("NOT_ESTABLISHED", out["expected_return_status"])

    def test_explicit_zero_distributions_allow_full_irr(self):
        a = self.setup_case()
        for row in a["scenarios"].values():
            row["annual_distributions_per_share"] = [{"amount_per_share": "0.00", "source_ref": "S-DIST-0"}] * 2
        out = evaluate_valuation_scenarios(**a)
        self.assertEqual(out["scenarios_private"]["BASE"]["scenario_return_pct_annual"], "10.00")
        self.assertEqual(out["scenarios_private"]["BASE"]["return_measure"], "YEAR_END_CASHFLOW_IRR_CONDITIONAL")

    def test_irr_with_distributions_year_end(self):
        a = self.setup_case(horizon_years=1)
        for row in a["scenarios"].values():
            row["terminal_price_per_share"] = "100.00"
            row["annual_distributions_per_share"] = [{"amount_per_share": "10.00", "source_ref": "S-DIV"}]
        self.assertEqual(evaluate_valuation_scenarios(**a)["scenarios_private"]["BASE"]["scenario_return_pct_annual"], "10.00")

    def test_irr_timing_matters(self):
        a = self.setup_case(horizon_years=2)
        for row in a["scenarios"].values():
            row["terminal_price_per_share"] = "100"
            row["annual_distributions_per_share"] = [{"amount_per_share": "10", "source_ref": "S1"}, {"amount_per_share": "0", "source_ref": "S2"}]
        early = evaluate_valuation_scenarios(**a)["scenarios_private"]["BASE"]["scenario_return_pct_annual"]
        for row in a["scenarios"].values():
            row["annual_distributions_per_share"] = [{"amount_per_share": "0", "source_ref": "S1"}, {"amount_per_share": "10", "source_ref": "S2"}]
        late = evaluate_valuation_scenarios(**a)["scenarios_private"]["BASE"]["scenario_return_pct_annual"]
        self.assertGreater(float(early),float(late))

    def test_terminal_zero_full_loss(self):
        a = self.setup_case()
        for row in a["scenarios"].values():
            row["terminal_price_per_share"] = "0"
            row["annual_distributions_per_share"] = [{"amount_per_share": "0", "source_ref": "S0"}]*2
        self.assertEqual(evaluate_valuation_scenarios(**a)["scenarios_private"]["BEAR"]["scenario_return_pct_annual"], "-100.00")

    def test_basis_unconfirmed_cannot_calculate(self):
        a = self.case(security_basis_confirmed_by_caller=False)
        self.assertEqual(a["status"], "UNAVAILABLE_INCOMPATIBLE_BASIS")
        self.assertIsNone(a["scenarios_private"]["BASE"]["scenario_return_pct_annual"])

    def test_currency_basis_unconfirmed_cannot_calculate(self):
        a = self.case(currency_basis_confirmed_by_caller=False)
        self.assertEqual(a["status"], "UNAVAILABLE_INCOMPATIBLE_BASIS")

    def test_no_future_quotes(self):
        with self.assertRaisesRegex(ValueError, "QUOTE_AFTER"):
            self.case(quoted_at="2026-10-29")

    def test_no_implicit_probabilities_expected_return(self):
        out = self.case()
        self.assertIn("VFV_ER_UNAVAILABLE", out["benchmark_expected_return_status"])
        self.assertNotIn("probabilities", str(out))

    def test_negative_terminal_price_rejected(self):
        a = self.setup_case()
        a["scenarios"]["BASE"]["terminal_price_per_share"] = "-1"
        with self.assertRaises(ValueError):
            evaluate_valuation_scenarios(**a)

    def test_negative_dividend_rejected(self):
        a=self.setup_case()
        a["scenarios"]["BASE"]["annual_distributions_per_share"] = [{"amount_per_share": "-1", "source_ref": "X"}]*2
        with self.assertRaises(ValueError): evaluate_valuation_scenarios(**a)

    def test_nan_infinity_rejected(self):
        for val in ("NaN", "Infinity", "-Infinity", "bad", ""):
            with self.subTest(val=val), self.assertRaises(ValueError): self.case(price_per_share=val)

    def test_extreme_decimal_exponents_rejected(self):
        for raw in ("1e100000", "1e-100000"):
            with self.subTest(raw=raw), self.assertRaises(ValueError): self.case(price_per_share=raw)

    def test_zero_price_rejected(self):
        with self.assertRaises(ValueError): self.case(price_per_share="0")

    def test_missing_horizon_rejected(self):
        for n in (0,31,1.5,True,"2",None):
            with self.subTest(n=n), self.assertRaises(ValueError): self.case(horizon_years=n)

    def test_unknown_scenario_set_rejected(self):
        a = self.setup_case()
        del a["scenarios"]["BEAR"]
        with self.assertRaisesRegex(ValueError,"EXACT_BEAR_BASE_BULL"):
            evaluate_valuation_scenarios(**a)

    def test_missing_dividend_year_rejected(self):
        a=self.setup_case()
        a["scenarios"]["BASE"]["annual_distributions_per_share"] = [{"amount_per_share": "1", "source_ref": "S"}]
        with self.assertRaisesRegex(ValueError,"exactly one"):
            evaluate_valuation_scenarios(**a)

    def test_missing_dividend_source_rejected_even_if_zero(self):
        a=self.setup_case()
        a["scenarios"]["BASE"]["annual_distributions_per_share"] = [{"amount_per_share": "0", "source_ref": ""}]*2
        with self.assertRaises(ValueError): evaluate_valuation_scenarios(**a)

    def test_unrecognized_method_rejected(self):
        a=self.setup_case()
        a["scenarios"]["BASE"]["valuation_method"]="PE_AUTO"
        with self.assertRaisesRegex(ValueError,"valuation_method"):
            evaluate_valuation_scenarios(**a)

    def test_unrecognized_assumption_basis_rejected(self):
        a=self.setup_case()
        a["scenarios"]["BEAR"]["assumption_basis"]="VERIFIED_ALPHA"
        with self.assertRaisesRegex(ValueError,"assumption_basis"):
            evaluate_valuation_scenarios(**a)

    def test_missing_terminal_source_rejected(self):
        a=self.setup_case()
        a["scenarios"]["BEAR"]["terminal_value_ref"]=""
        with self.assertRaises(ValueError): evaluate_valuation_scenarios(**a)

    def test_data_not_mutated(self):
        data=self.setup_case()
        baseline=copy.deepcopy(data)
        evaluate_valuation_scenarios(**data)
        self.assertEqual(data,baseline)

    def test_same_security_class_unknown_is_not_verification(self):
        self.assertEqual(self.case()["source_authentication"],"NOT_PERFORMED")

    def test_new_security_has_no_inherited_policy(self):
        self.assertEqual(self.case()["trade_or_portfolio_authority"],"NONE")

    def test_reported_assumption_status_retained(self):
        self.assertEqual(self.case()["scenarios_private"]["BASE"]["assumption_basis"],"PAM_ASSUMPTION")

    def test_year_end_cashflow_root_two_years(self):
        a=self.setup_case()
        for row in a["scenarios"].values():
            row["terminal_price_per_share"]="100"
            row["annual_distributions_per_share"]=[{"amount_per_share":"10","source_ref":"S1"},{"amount_per_share":"10","source_ref":"S2"}]
        self.assertEqual(evaluate_valuation_scenarios(**a)["scenarios_private"]["BASE"]["scenario_return_pct_annual"],"10.00")

if __name__ == '__main__':unittest.main()
