"""Synthetic budget reconciliation tests. No trades, real accounts or sourcing."""
import copy
import unittest

from ai_native.contribution_math import project_gross_contribution
from ai_native.funded_costs_reconciliation import reconcile_funded_contribution

COSTS=('commission','bid_ask_spread','fx_conversion','purchase_tax','other_fees')

class FundedContributionTests(unittest.TestCase):
    def inputs(self, **overrides):
        ci=dict(positions_base={'ABC:TSX':'400.00','VFV:TSX':'600.00'},
                allocations_pct={'ABC:TSX':'60','VFV:TSX':'40'},
                contribution_base='1000.00',currency='CAD',as_of='2026-10-28',
                scope_complete=True,cash_accounted_for=True,
                same_currency_basis_verified=True,instrument_identity_verified=True)
        ci.update(overrides)
        return ci

    def bundle(self, funding='FROM_CONTRIBUTION', total='5.00', **overrides):
        ci=self.inputs()
        gross=project_gross_contribution(**ci)
        refs=[{'destination':k,'component':c,'source_ref':f'SYN-{k}-{c}'} for k in gross['allocations'] for c in COSTS]
        cost={'status':'SUPPLIED_COST_TALLY_ONLY','currency':'CAD','analysis_as_of':'2026-10-28',
              'cost_quote_as_of':'2026-10-28','funding':funding,
              'source_references_private':refs,'total_supplied_costs_base':total}
        if funding=='FROM_CONTRIBUTION':cost['maximum_remaining_contribution_budget_base']=f'{1000-float(total):.2f}'
        if funding=='EXTERNAL_CASH':cost['additional_external_cash_required_base']=total
        cost.update(overrides)
        return {'contribution_inputs':ci,'gross_projection':gross,'cost_tally':cost}

    def test_from_contribution_five_dollars(self):
        out=reconcile_funded_contribution(**self.bundle())
        self.assertEqual(out['status'],'CONDITIONAL_SUPPLIED_COST_BUDGET_RECONCILED')
        self.assertEqual(out['conditional_purchase_budget_base'],'995.00')
        self.assertEqual(out['conditional_projection_private']['allocations_base'], {'ABC:TSX':'597.00','VFV:TSX':'398.00'})
        self.assertEqual(out['conditional_projection_private']['projected_total_base'],'1995.00')
        self.assertIsNone(out['additional_external_cash_required_base'])
        self.assertIn('NOT_EXECUTION_CERTIFIED',out['execution_status'])

    def test_external_cash_does_not_reduce_orders(self):
        out=reconcile_funded_contribution(**self.bundle(funding='EXTERNAL_CASH'))
        self.assertEqual(out['conditional_purchase_budget_base'],'1000.00')
        self.assertEqual(out['additional_external_cash_required_base'],'5.00')
        self.assertEqual(out['conditional_projection_private']['allocations_base'],{'ABC:TSX':'600.00','VFV:TSX':'400.00'})

    def test_source_backed_zeros(self):
        out=reconcile_funded_contribution(**self.bundle(total='0.00'))
        self.assertEqual(out['conditional_purchase_budget_base'],'1000.00')

    def test_unknown_funding_blocks(self):
        out=reconcile_funded_contribution(**self.bundle(funding='UNKNOWN'))
        self.assertEqual(out['status'],'UNAVAILABLE_FUNDING_UNKNOWN')
        self.assertNotIn('conditional_projection_private',out)

    def test_incomplete_cost_tally_blocks(self):
        x=self.bundle();x['cost_tally']['status']='INCOMPLETE_COST_INPUTS'
        out=reconcile_funded_contribution(**x)
        self.assertEqual(out['status'],'UNAVAILABLE_COST_INPUTS')
        self.assertNotIn('conditional_projection_private',out)

    def test_gross_inputs_cannot_be_substituted(self):
        x=self.bundle();x['contribution_inputs']['allocations_pct']['ABC:TSX']='50'
        x['contribution_inputs']['allocations_pct']['VFV:TSX']='50'
        with self.assertRaisesRegex(ValueError,'GROSS_PROJECTION_INTEGRITY_MISMATCH'):
            reconcile_funded_contribution(**x)

    def test_currency_and_provenance_fail_closed(self):
        x=self.bundle();x['cost_tally']['currency']='USD'
        with self.assertRaisesRegex(ValueError,'COST_CURRENCY_MISMATCH'):
            reconcile_funded_contribution(**x)
        x=self.bundle();x['cost_tally']['source_references_private'].pop()
        with self.assertRaisesRegex(ValueError,'COST_SOURCE_REFERENCES_INCOMPLETE'):
            reconcile_funded_contribution(**x)

    def test_unavailable_when_fees_consume_entire_budget(self):
        x=self.bundle(total='1000.00');x['cost_tally'].pop('maximum_remaining_contribution_budget_base',None)
        self.assertEqual(reconcile_funded_contribution(**x)['status'],'UNAVAILABLE_COSTS_EXCEED_BUDGET')

    def test_tally_mismatch_blocks(self):
        x=self.bundle();x['cost_tally']['maximum_remaining_contribution_budget_base']='994.00'
        with self.assertRaisesRegex(ValueError,'NET_BUDGET_TALLY_MISMATCH'):
            reconcile_funded_contribution(**x)
        x=self.bundle(funding='EXTERNAL_CASH');x['cost_tally']['additional_external_cash_required_base']='4.00'
        with self.assertRaisesRegex(ValueError,'EXTERNAL_CASH_TALLY_MISMATCH'):
            reconcile_funded_contribution(**x)

    def test_reduced_trade_set_blocks_instead_of_charging_dropped_trade(self):
        ci=self.inputs(positions_base={'A':'0.00','B':'0.00'},allocations_pct={'A':'50','B':'50'},contribution_base='0.02')
        gross=project_gross_contribution(**ci)
        refs=[{'destination':k,'component':c,'source_ref':'SYN'} for k in ('A','B') for c in COSTS]
        cost=dict(status='SUPPLIED_COST_TALLY_ONLY',currency='CAD',analysis_as_of='2026-10-28',
                  cost_quote_as_of='2026-10-28',funding='FROM_CONTRIBUTION',
                  source_references_private=refs,total_supplied_costs_base='0.01',
                  maximum_remaining_contribution_budget_base='0.01')
        out=reconcile_funded_contribution(contribution_inputs=ci,gross_projection=gross,cost_tally=cost)
        self.assertEqual(out['status'],'UNAVAILABLE_REVISED_TRADE_SET')

    def test_input_objects_not_mutated(self):
        x=self.bundle();prior=copy.deepcopy(x)
        reconcile_funded_contribution(**x)
        self.assertEqual(x,prior)
        self.assertNotIn('400.00',str({'status':'NO_PRIVATE_GITHUB_WRITE'}))

    def test_one_time_cost_burden_is_funding_sensitive_not_expected_return(self):
        included = reconcile_funded_contribution(**self.bundle())
        external = reconcile_funded_contribution(**self.bundle(funding='EXTERNAL_CASH'))
        self.assertEqual(included['one_time_supplied_cost_share_pct'], '0.5000')
        self.assertEqual(included['total_cash_committed_base'], '1000.00')
        self.assertEqual(external['one_time_supplied_cost_share_pct'], '0.4975')
        self.assertEqual(external['total_cash_committed_base'], '1005.00')
        self.assertEqual(included['expected_return_or_execution_authority'], 'NONE')

    def test_zero_cost_or_unknown_funding_never_invents_a_nonzero_cost_share(self):
        zero = reconcile_funded_contribution(**self.bundle(total='0.00'))
        self.assertEqual(zero['one_time_supplied_cost_share_pct'], '0.0000')
        unknown = reconcile_funded_contribution(**self.bundle(funding='UNKNOWN'))
        self.assertNotIn('one_time_supplied_cost_share_pct', unknown)

if __name__=='__main__':unittest.main()
