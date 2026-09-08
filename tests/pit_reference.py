"""Independent oracle: execute unchanged decision statements from pinned main.py.

Never calls run_analysis. Excludes its operational statements, providers,
reporting and authority plumbing. Storage is replaced with synthetic facts.
This file is available only to the isolated test subprocess, never the CLI.
"""
import ast
import copy
from pathlib import Path

from pit_comparison.adapter import semantic_result


def reference(bundle, m):
    tree=ast.parse(Path(m.__file__).read_text())
    function=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='run_analysis')
    body=next(n.body for n in function.body if isinstance(n,ast.Try))
    def assignment(node,name):
        return isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id==name for target in node.targets for t in ast.walk(target))
    def index(name):
        return next(i for i,n in enumerate(body) if assignment(n,name))
    # Original acquisition-to-FX segment; every provider/storage acquisition is
    # a synthetic reader below. Original formulas, branches and loops unchanged.
    first=body[index('ticker_aliases'):index('runtime_input_audit')+1]
    calculation=body[index('weighted_portfolio'):index('thesis_reversal_rows')]
    final=body[index('allocation_warnings'):index('allocation_change_rows')]
    namespace=dict(vars(m))
    data={name:bundle.get(name) for name in bundle.data}
    class FrozenObservations:
        def fetch_all(self,*args,**kwargs):
            return copy.deepcopy(data['market']),copy.deepcopy(data['benchmarks']),[]
        def fetch_fx_rates_to_cad(self,*args,**kwargs):
            return copy.deepcopy(data['fx'])
        def fetch_ticker(self,ticker,**kwargs):
            return copy.deepcopy(data['regime_market'][ticker])
    namespace.update(capital=data['context']['capital_context']['amount'],mode=data['context']['investment_mode'],
        refresh_market_data=False,resolved_run_purpose='DIAGNOSTIC',effective_validation_warnings=[],
        MarketDataFetcher=FrozenObservations,load_friendly_manual_inputs=lambda path:copy.deepcopy(data['manual_inputs']),
        load_proxy_calibration_inputs=lambda path:[],load_ticker_memory=lambda path:copy.deepcopy(data['ticker_memory']),
        load_research_report_inputs=lambda *args,**kwargs:copy.deepcopy(data['research_facts']))
    # The application conditionally reads this optional file. Synthetic contract
    # always carries the explicit account-location input, even when empty.
    for node in first:
        if isinstance(node,ast.If) and 'account_locations.csv' in ast.unparse(node.test):
            node.test=ast.Constant(value=True)
    def execute(nodes):
        program=ast.fix_missing_locations(ast.Module(body=nodes,type_ignores=[]))
        exec(compile(program,'<pinned-synthetic-decision-oracle>','exec'),namespace)
    execute(first)
    namespace['effective_validation_warnings']=list(dict.fromkeys(data['context']['validation_warnings']+[str(r.get('message') or '') for r in namespace['runtime_input_audit']['advisories']]))
    execute(calculation)
    execute(final)
    return semantic_result({name:namespace[key] for name,key in (
        ('CORE_PORTFOLIO','analyses'),('WATCHLIST','watchlist_analyses'),('MARKET_SCANNER','market_analyses'),('DISCOVERY_IDEAS','discovery_analyses'))},
        namespace['allocation_result'],namespace['portfolio_risk'],namespace['tax_report'],namespace['weighted_portfolio'],namespace['mode'],namespace['capital'])
