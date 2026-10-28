"""Conditional funded-contribution budget check using only supplied purchase-costs.

Pure private arithmetic; no quote, tax evaluation, order sizing, execution or advice.
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any, Mapping

from .contribution_math import project_gross_contribution

_CENT = Decimal('0.01')
_COST_TYPES = frozenset({'commission','bid_ask_spread','fx_conversion','purchase_tax','other_fees'})


def _cash(value: Any, name: str) -> Decimal:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f'{name}: explicit monetary string required')
    try:
        amount = Decimal(value)
    except InvalidOperation as exc:
        raise ValueError(f'{name}: invalid amount') from exc
    if not amount.is_finite() or amount < 0 or amount != amount.quantize(_CENT):
        raise ValueError(f'{name}: invalid finite cents')
    return amount


def reconcile_funded_contribution(
    *,
    contribution_inputs: Mapping[str, Any],
    gross_projection: Mapping[str, Any],
    cost_tally: Mapping[str, Any],
) -> dict[str, Any]:
    """Reproject *supplied* new capital under a conditional fixed-cost assumption.

    A projection is never execution-ready. Costs are assumed unchanged when order
    amounts change; caller must re-quote size-dependent fees before actual action.
    """
    if not all(isinstance(x, Mapping) for x in (contribution_inputs, gross_projection, cost_tally)):
        raise ValueError('CONTRIBUTION_COST_INPUTS_MUST_BE_MAPPINGS')
    if gross_projection.get('status') != 'GROSS_PROJECTION_ONLY':
        return {'status':'UNAVAILABLE_GROSS_PROJECTION','execution_status':'UNAVAILABLE'}
    if cost_tally.get('status') != 'SUPPLIED_COST_TALLY_ONLY':
        return {'status':'UNAVAILABLE_COST_INPUTS','cost_status':cost_tally.get('status'),
                'execution_status':'UNAVAILABLE'}

    # Reject a mismatched, independently substituted gross projection.
    rebuilt = project_gross_contribution(**dict(contribution_inputs))
    if rebuilt != gross_projection:
        raise ValueError('GROSS_PROJECTION_INTEGRITY_MISMATCH')
    if cost_tally.get('currency') != gross_projection['currency']:
        raise ValueError('COST_CURRENCY_MISMATCH')
    if cost_tally.get('analysis_as_of') is None or cost_tally.get('cost_quote_as_of') is None:
        raise ValueError('COST_DATES_MISSING')

    originals = {k for k, v in gross_projection['allocations'].items() if _cash(v, f'gross:{k}') > 0}
    expected_refs = {(destination, kind) for destination in originals for kind in _COST_TYPES}
    refs = cost_tally.get('source_references_private')
    if not isinstance(refs, list) or any(not isinstance(row, Mapping) for row in refs):
        raise ValueError('COST_SOURCE_REFERENCES_MISSING')
    actual_refs = [(row.get('destination'), row.get('component')) for row in refs]
    if (len(actual_refs) != len(expected_refs) or set(actual_refs) != expected_refs
            or any(not isinstance(row.get('source_ref'), str) or not row['source_ref'].strip() for row in refs)):
        raise ValueError('COST_SOURCE_REFERENCES_INCOMPLETE')

    paid = _cash(cost_tally.get('total_supplied_costs_base'), 'total_supplied_costs_base')
    original_budget = _cash(gross_projection['contribution'], 'contribution')
    funding = cost_tally.get('funding')
    if funding == 'UNKNOWN':
        return {'status':'UNAVAILABLE_FUNDING_UNKNOWN','execution_status':'UNAVAILABLE'}
    if funding not in {'FROM_CONTRIBUTION', 'EXTERNAL_CASH'}:
        raise ValueError('FUNDING_INVALID')
    if funding == 'FROM_CONTRIBUTION':
        if paid >= original_budget:
            return {'status':'UNAVAILABLE_COSTS_EXCEED_BUDGET','execution_status':'UNAVAILABLE'}
        available = original_budget - paid
        if _cash(cost_tally.get('maximum_remaining_contribution_budget_base'),
                 'maximum_remaining_contribution_budget_base') != available:
            raise ValueError('NET_BUDGET_TALLY_MISMATCH')
        revised_inputs = dict(contribution_inputs)
        revised_inputs['contribution_base'] = f'{available:.2f}'
        projected = project_gross_contribution(**revised_inputs)
        if projected['status'] != 'GROSS_PROJECTION_ONLY':
            return {'status':'UNAVAILABLE_REVISED_PORTFOLIO_SCOPE','execution_status':'UNAVAILABLE'}
        revised_active = {k for k,v in projected['allocations'].items() if _cash(v,f'revised:{k}') > 0}
        if revised_active != originals:
            return {'status':'UNAVAILABLE_REVISED_TRADE_SET','execution_status':'UNAVAILABLE'}
        external_cash = None
    else:
        if _cash(cost_tally.get('additional_external_cash_required_base'),
                 'additional_external_cash_required_base') != paid:
            raise ValueError('EXTERNAL_CASH_TALLY_MISMATCH')
        available = original_budget
        projected = rebuilt
        external_cash = f'{paid:.2f}'

    return {
        'status':'CONDITIONAL_SUPPLIED_COST_BUDGET_RECONCILED',
        'funding':funding,
        'original_contribution_base':f'{original_budget:.2f}',
        'supplied_purchase_costs_base':f'{paid:.2f}',
        'conditional_purchase_budget_base':f'{available:.2f}',
        'additional_external_cash_required_base':external_cash,
        'conditional_projection_private':{
            'allocations_base':projected['allocations'],
            'projected_positions_base':projected['projected_positions'],
            'projected_total_base':projected['projected_total'],
            'projected_weights_pct':projected['projected_weights_pct'],
            'account_currency':projected['currency'],
            'portfolio_as_of':projected['as_of'],
        },
        'cost_assumption':'SUPPLIED_ABSOLUTE_COSTS_HELD_CONSTANT_AFTER_RESIZING_NOT_REQUOTED',
        'source_authentication':'NOT_PERFORMED_BY_CODE',
        'execution_status':'UNAVAILABLE_NOT_EXECUTION_CERTIFIED',
        'privacy':'PRIVATE_ONLY',
    }
