import copy
import unittest
from ai_native.known_costs import tally_supplied_costs


class CostTallyTests(unittest.TestCase):
    def args(self, **updates):
        base = {"status":"GROSS_PROJECTION_ONLY","currency":"CAD","as_of":"2026-10-28","allocations":{"ABC:TSX":"600.00","VFV:TSX":"400.00"},"contribution":"1000.00"}
        sources = {x:{kind:{"amount_base":"0.00","source_ref":"S-DECLARED-ZERO"} for kind in ("commission","bid_ask_spread","fx_conversion","purchase_tax","other_fees")} for x in base["allocations"]}
        sources["ABC:TSX"]["commission"] = {"amount_base":"5.00","source_ref":"S-FEE-1"}
        args=dict(gross_projection=base,charges_by_destination=sources,cost_currency="CAD",cost_quote_as_of="2026-10-28",analysis_as_of="2026-10-28",funding="FROM_CONTRIBUTION")
        args.update(updates)
        return args

    def test_known_costs_from_contribution_do_not_fake_net_positions(self):
        out=tally_supplied_costs(**self.args())
        self.assertEqual(out["total_supplied_costs_base"],"5.00")
        self.assertEqual(out["maximum_remaining_contribution_budget_base"],"995.00")
        self.assertTrue(out["gross_allocation_funding_conflict"])
        self.assertEqual(out["net_economics_status"],"UNAVAILABLE_NOT_EXECUTION_CERTIFIED")
        self.assertNotIn("net_positions",out)

    def test_external_cash_not_double_subtracted(self):
        out=tally_supplied_costs(**self.args(funding="EXTERNAL_CASH"))
        self.assertEqual(out["additional_external_cash_required_base"],"5.00")
        self.assertNotIn("maximum_remaining_contribution_budget_base",out)

    def test_unknown_funding_no_net_budget(self):
        out=tally_supplied_costs(**self.args(funding="UNKNOWN"))
        self.assertNotIn("maximum_remaining_contribution_budget_base",out)

    def test_missing_component_stays_missing(self):
        a=self.args(); del a["charges_by_destination"]["ABC:TSX"]["fx_conversion"]
        out=tally_supplied_costs(**a)
        self.assertEqual(out["status"],"INCOMPLETE_COST_INPUTS")
        self.assertIn("ABC:TSX:fx_conversion",out["missing_components"])
        self.assertNotIn("total_supplied_costs_base",out)

    def test_zero_without_source_is_not_certified(self):
        a=self.args(); a["charges_by_destination"]["VFV:TSX"]["purchase_tax"]["source_ref"]=""
        out=tally_supplied_costs(**a)
        self.assertIn("VFV:TSX:purchase_tax:SOURCE_NOT_SUPPLIED",out["missing_components"])

    def test_mismatched_currency_denied(self):
        with self.assertRaisesRegex(ValueError,"CURRENCY_MISMATCH"):
            tally_supplied_costs(**self.args(cost_currency="USD"))

    def test_destination_scope_denied(self):
        a=self.args(); del a["charges_by_destination"]["VFV:TSX"]
        with self.assertRaisesRegex(ValueError,"DESTINATION_MISMATCH"):
            tally_supplied_costs(**a)

    def test_invalid_negative_nan_and_precision_denied(self):
        for amount in ["-0.10","NaN","Infinity","1.001"]:
            with self.subTest(amount=amount):
                a=self.args(); a["charges_by_destination"]["ABC:TSX"]["commission"]["amount_base"]=amount
                with self.assertRaises(ValueError):tally_supplied_costs(**a)

    def test_future_quote_denied(self):
        with self.assertRaisesRegex(ValueError,"FUTURE_COST_QUOTE"):
            tally_supplied_costs(**self.args(cost_quote_as_of="2026-10-29"))

    def test_unavailable_gross_denied(self):
        a=self.args();a["gross_projection"]["status"]="UNAVAILABLE"
        out=tally_supplied_costs(**a)
        self.assertEqual(out["status"],"UNAVAILABLE_GROSS_PROJECTION")

    def test_costs_exceed_contribution_not_investable(self):
        a=self.args();a["charges_by_destination"]["ABC:TSX"]["commission"]["amount_base"]="1000.00"
        out=tally_supplied_costs(**a)
        self.assertEqual(out["status"],"UNAVAILABLE_COSTS_EXCEED_CONTRIBUTION")
        self.assertNotIn("maximum_remaining_contribution_budget_base",out)

    def test_no_mutation(self):
        a=self.args(); before=copy.deepcopy(a)
        tally_supplied_costs(**a)
        self.assertEqual(a,before)


if __name__ == '__main__': unittest.main()
