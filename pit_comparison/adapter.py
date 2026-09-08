"""Revision-aware orchestration; all investment formulas stay in selected source.

The input seams replace storage/provider acquisition, never scoring or gates.
"""
from __future__ import annotations

import copy
import importlib
import sys
from datetime import date, datetime
from functools import partial
from pathlib import Path
from zoneinfo import ZoneInfo

from .bundle import BundleError, fingerprint, timestamp


# main.py orchestration is supported only after explicit equivalence review.
SUPPORTED_MAIN_HASHES = {'c72b1b409f20be631d5a71263a111f68adb2e2af96deb28c7fb87cb482f08cd8', 'b3fc1a16d6a69dc21b79feadfaa6b706b574aed52ff5faf429e6927c634ab361'}


def bind_inputs(bundle, source, runtime, boundary):
    from .bundle import digest
    if digest((source / "main.py").read_bytes()) not in SUPPORTED_MAIN_HASHES:
        raise BundleError("Unsupported decision orchestration; adapter equivalence review required")
    import src.utils as u
    u.CONFIG_DIR = runtime / "effective_config"
    u.DATA_DIR = runtime / "virtual_data"
    u.REPORTS_DIR = runtime / "prior"
    u.CACHE_DIR = runtime / "scratch_cache"
    u.RESEARCH_REPORTS_DIR = u.DATA_DIR / "research_reports"
    u.BNCD_MORNINGSTAR_DIR = u.RESEARCH_REPORTS_DIR / "bncd_morningstar"
    semantic_now = timestamp(bundle.manifest["effective_pit_at"]).astimezone(ZoneInfo(bundle.manifest["semantic_timezone"])).replace(tzinfo=None)
    class PITDate(date):
        @classmethod
        def today(cls):
            return semantic_now.date()
    u.date = PITDate
    universe = bundle.get("universe")
    csv_inputs = {
        "portfolio.csv": bundle.get("portfolio"),
        "portfolio_transactions.csv": bundle.get("transactions"),
        "account_locations.csv": bundle.get("account_locations"),
        "watchlist.csv": universe["watchlist_rows"],
        "market_universe.csv": universe["market_rows"],
    }
    def frozen_csv(path):
        path = Path(path)
        if path.parent != u.DATA_DIR or path.name not in csv_inputs:
            boundary.deny("Undeclared CSV input: " + str(path))
        return copy.deepcopy(csv_inputs[path.name])
    u.read_csv_records = frozen_csv
    # Bind the existing leaf seam before its callers import aliases. Some
    # research callers explicitly pass today=None, so a partial is insufficient.
    evidence = importlib.import_module("src.evidence_provenance")
    original_field_freshness = evidence.field_freshness
    def pit_field_freshness(field, source_date, today=None):
        return original_field_freshness(field, source_date, today=today or semantic_now.date())
    evidence.field_freshness = pit_field_freshness
    # These modules use existing parameter seams; thresholds are untouched.
    freshness = importlib.import_module("src.data_freshness_engine")
    original_market_freshness = freshness.compute_market_data_freshness
    def pit_market_freshness(payload, now=None):
        # Native freshness strips the observation offset before subtracting.
        # Supply its existing now seam in that same offset, preserving elapsed
        # time for UTC observations and non-UTC semantic calendars alike.
        observed_zone = datetime.fromisoformat(payload["fetched_at"].replace("Z", "+00:00")).tzinfo
        clock = timestamp(bundle.manifest["effective_pit_at"]).astimezone(observed_zone).replace(tzinfo=None)
        return original_market_freshness(payload, now=now if now is not None else clock)
    freshness.compute_market_data_freshness = pit_market_freshness
    reliability = importlib.import_module("src.data_reliability_engine")
    reliability.compute_research_report_freshness = partial(reliability.compute_research_report_freshness, today=semantic_now.date())
    discovery = importlib.import_module("src.discovery_engine")
    discovery._load_or_fetch_auto_rows = lambda config, path, refresh=False: copy.deepcopy(universe["discovery_rows"])
    main = importlib.import_module("main")
    install_sentinels(boundary, main)
    return main


def install_sentinels(boundary, main):
    targets = {
        "src.data_fetcher": ["MarketDataFetcher"],
        "src.official_data_fetcher": ["OfficialDataFetcher"],
        "src.canadian_data_fetcher": ["CanadianDataFetcher"],
        "src.fund_price_fallback_engine": ["fetch_fund_price_fallback"],
        "src.discovery_engine": ["_fetch_auto_discovery_rows", "_fetch_public_table_source"],
        "src.instrument_profile_engine": ["build_instrument_profiles", "_optional_external_profile"],
        "src.research_reports": ["load_research_report_inputs"],
        "requests": ["request", "get", "post", "put", "delete", "patch", "head", "options"],
        "requests.sessions": ["Session"],
        "urllib.request": ["urlopen"],
    }
    original_objects = []
    for module_name, names in targets.items():
        module = importlib.import_module(module_name)
        for name in names:
            if hasattr(module, name):
                original_objects.append((getattr(module, name), boundary.sentinel(module_name + "." + name)))
    # Replace aliases already imported by model modules as well as definitions.
    for module_name, module in list(sys.modules.items()):
        if module_name == "main" or module_name.startswith(("src.", "requests", "urllib.request")):
            for name, value in list(vars(module).items()):
                for original, denied in original_objects:
                    if value is original:
                        setattr(module, name, denied)
    for name in ("run_analysis", "analyze_command", "main", "run_cache_maintenance", "generate_reports",
                 "run_walk_forward_backtest", "run_backtests_from_latest_reports", "sync_portfolio_state"):
        if hasattr(main, name):
            setattr(main, name, boundary.sentinel("main." + name))


def evaluate(bundle, m):
    """Same decision order as approved main.run_analysis, without operations."""
    ctx = bundle.get("context")
    mode, capital = ctx["investment_mode"], ctx["capital_context"]["amount"]
    bundle.get("config")  # actual loaders read its immutable JSON-as-YAML materialization
    bundle.get("provenance")
    bundle.get("prior_state")
    aliases = m.load_ticker_aliases(m.CONFIG_DIR / "ticker_aliases.yaml")
    metadata = {}
    positions = m.resolve_ticker_list(m.load_positions(), aliases, metadata, "config/positions.yaml")
    configured_benchmarks = m.resolve_keyed_config(m.load_yaml(m.CONFIG_DIR / "benchmarks.yaml"), aliases, metadata, "config/benchmarks.yaml")
    sectors = m.resolve_keyed_config(m.load_yaml(m.CONFIG_DIR / "sectors.yaml"), aliases, metadata, "config/sectors.yaml")
    exposures = m.resolve_keyed_config(m.load_yaml(m.CONFIG_DIR / "exposures.yaml"), aliases, metadata, "config/exposures.yaml")
    watchlist = m.load_and_resolve_universe(lambda: m.load_watchlist(m.CONFIG_DIR / "watchlist.yaml", m.DATA_DIR / "watchlist.csv"), aliases, metadata, "watchlist")
    market_universe = m.load_and_resolve_universe(lambda: m.load_market_universe(m.CONFIG_DIR / "market_scanner.yaml", m.DATA_DIR / "market_universe.csv"), aliases, metadata, "market_universe")
    defensive_config = m.load_defensive_etf_config(m.CONFIG_DIR / "defensive_etfs.yaml")
    defensive_tickers = m.defensive_etf_tickers_for_mode(defensive_config, mode)
    regime_config = m.load_market_regime_config(m.CONFIG_DIR / "market_regime.yaml")
    from src.critical_input_engine import _cost_basis_consistency_issues
    cost_issues = _cost_basis_consistency_issues(m.DATA_DIR / "portfolio.csv")
    if cost_issues:
        raise BundleError("Frozen cost-basis validation failed: " + str(cost_issues))
    raw_portfolio = m.load_portfolio(m.DATA_DIR / "portfolio.csv")
    raw_transactions = m.load_portfolio_transactions(m.DATA_DIR / "portfolio_transactions.csv")
    portfolio = m.resolve_portfolio_rows(raw_portfolio, aliases, metadata, "data/portfolio.csv")
    lots = m.resolve_portfolio_lot_rows(raw_portfolio, aliases, metadata, "data/portfolio.csv")
    transactions = m.resolve_portfolio_transaction_rows(raw_transactions, aliases, metadata, "data/portfolio_transactions.csv")
    accounts = m.resolve_account_location_rows(m.load_account_locations(m.DATA_DIR / "account_locations.csv"), aliases, metadata, "data/account_locations.csv")
    manual = m.resolve_manual_inputs(bundle.get("manual_inputs"), aliases, metadata, "data/manual_inputs_friendly.txt")
    proxies = m.load_proxy_corrections(m.CONFIG_DIR / "proxy_corrections.yaml")
    owned = {r["ticker"] for r in portfolio}
    core = sorted((owned | {"VFV.TO"}) if owned else (set(positions) | {"VFV.TO"}))
    watch = sorted((set(watchlist) | (set(positions) - set(core))) - set(core) - set(market_universe) - {"VFV.TO"})
    market_tickers = sorted(set(market_universe) - set(core) - {"VFV.TO"})
    exclusions = m.expand_exclusions_with_alias_inputs(set(core) | set(watchlist) | set(market_universe) | {"VFV.TO"}, aliases)
    discovery = m.load_and_resolve_universe(lambda: m.load_auto_discovery_universe(m.CONFIG_DIR / "market_scanner.yaml", m.DATA_DIR / "discovery_universe_cache.csv", exclusions, refresh=False), aliases, metadata, "discovery_universe")
    discovery = {t: r for t, r in discovery.items() if t not in exclusions}
    discovery_tickers = sorted(set(discovery) - set(core) - set(watchlist) - set(market_universe) - {"VFV.TO"})
    all_tickers = sorted(set(core) | set(watch) | set(market_tickers) | set(discovery_tickers) | set(defensive_tickers))
    memory = bundle.get("ticker_memory")
    research = bundle.get("research_facts")
    external_sectors, external_exposures = m.metadata_to_sector_exposure({**market_universe, **discovery})
    combined_sectors, combined_exposures = {**external_sectors, **sectors}, {**external_exposures, **exposures}
    benchmark_map, benchmark_sources = m.enrich_benchmark_map(configured_benchmarks, all_tickers)
    market, benchmarks = bundle.get("market"), bundle.get("benchmarks")
    regime_market = bundle.get("regime_market")
    from src.benchmark_relevance_engine import COMMON_BENCHMARK_TICKERS
    from src.market_regime_engine import market_regime_tickers
    require_keys(market, all_tickers, "market")
    require_keys(benchmarks, set(benchmark_map.values()) | COMMON_BENCHMARK_TICKERS, "benchmarks")
    require_keys(regime_market, market_regime_tickers(regime_config), "regime_market")
    regime = m.compute_market_regime(regime_market, regime_config)
    currencies = [m.infer_quote_currency(r["ticker"], market[r["ticker"]].get("currency")) for r in portfolio]
    currencies.extend(str(r.get("average_cost_currency") or r.get("acquisition_value_currency") or "").upper() for r in [*portfolio, *lots] if r.get("average_cost_currency") or r.get("acquisition_value_currency"))
    currencies.extend(m.portfolio_transaction_currencies(transactions))
    fx = bundle.get("fx")
    require_keys(fx, currencies, "fx")
    portfolio = m.enrich_portfolio_with_market_data(portfolio, market, fx)
    lots = m.enrich_portfolio_with_market_data(lots, market, fx)
    audit = m.audit_runtime_critical_inputs(portfolio_rows=portfolio, market_data=market, capital=capital, run_purpose="DIAGNOSTIC")
    if audit["hard_failures"]:
        raise BundleError("Critical portfolio/market inputs failed: " + str(audit["hard_failures"]))
    warnings = list(dict.fromkeys(ctx["validation_warnings"] + [str(r.get("message") or "") for r in audit["advisories"]]))
    weighted, _ = m.add_position_weights(portfolio)
    locations = m.account_locations_from_portfolio_rows(lots, accounts)
    weights = m.position_weight_map(weighted)
    values = {r["ticker"]: m.safe_float(r.get("current_value")) or 0.0 for r in weighted}
    details = {r["ticker"]: r for r in weighted}
    core_sectors = m.apply_ticker_memory_to_sector_map(m.enrich_sector_map(sectors, market, core), core, memory)
    core_exposures = m.apply_ticker_memory_to_exposure_map(m.enrich_exposure_map(exposures, market, core), core, memory)
    combined_sectors = m.apply_ticker_memory_to_sector_map(m.enrich_sector_map(combined_sectors, market, all_tickers), all_tickers, memory)
    combined_exposures = m.apply_ticker_memory_to_exposure_map(m.enrich_exposure_map(combined_exposures, market, all_tickers), all_tickers, memory)
    previous = m.load_previous_snapshot(m.REPORTS_DIR, current_model_rules_version=m.MODEL_RULES_VERSION, analysis_mode=mode)
    risk = m.compute_portfolio_risk(weighted, core_sectors, core_exposures)
    groups = {}
    specs = [("CORE_PORTFOLIO", core, None), ("WATCHLIST", watch, watchlist),
             ("MARKET_SCANNER", market_tickers, market_universe), ("DISCOVERY_IDEAS", discovery_tickers, discovery)]
    for name, tickers, universe in specs:
        is_core = name == "CORE_PORTFOLIO"
        groups[name] = m.build_position_analyses(tickers=tickers, manual_inputs=manual, market_data=market,
            benchmark_data=benchmarks, benchmark_map=benchmark_map, benchmark_sources=benchmark_sources,
            sectors=core_sectors if is_core else combined_sectors, exposures=core_exposures if is_core else combined_exposures,
            weights=weights if is_core else {}, current_values=values if is_core else {},
            portfolio_details=details if is_core else None, ticker_resolution_metadata=metadata,
            research_inputs=research, proxy_corrections=proxies)
        if universe is not None:
            for t, analysis in groups[name].items():
                analysis.update(universe.get(t, {}))
                analysis["universe"] = name
    analyses, watch_analyses, market_analyses, discovery_analyses = groups.values()
    defensive = m.build_defensive_etf_candidates(defensive_config, mode, market)
    defensive_validation = m.defensive_etf_analysis_map(defensive)
    for group in groups.values():
        m.apply_history_context(group, previous)
    for group in groups.values():
        m.apply_history_sell_discipline(group)
    m.apply_winner_protection(analyses, previous)
    m.apply_cycle_bubble_context(*groups.values(), risk)
    for function in (m.apply_cash_flow_quality_context, m.apply_shareholder_discipline_context,
                     m.apply_long_term_durability_context, m.apply_market_growth_thesis_context,
                     m.apply_quality_drawdown_context):
        function(*groups.values())
    for function in (m.apply_market_regime_context, m.apply_sector_euphoria_context):
        for name, group in groups.items():
            function(group, regime, mode=mode, universe=name)
    m.apply_double_counting_context(*groups.values(), mode=mode)
    m.apply_hidden_cluster_guardrails(*groups.values(), risk, mode=mode)
    m.refresh_add_and_opportunity_context(*groups.values())
    for group, classifier in ((watch_analyses, m.classify_watchlist_analysis), (market_analyses, m.classify_market_candidate), (discovery_analyses, m.classify_discovery_idea)):
        for analysis in group.values():
            analysis.update(classifier(analysis))
            m.apply_external_superiority_gate(analysis, analyses)
    m.apply_external_etf_candidate_context(mode, risk, watch_analyses, market_analyses, discovery_analyses)
    tax_initial = m.compute_tax_location_report(locations, weighted, analyses, core_exposures)
    penalties = m.tax_penalty_map(tax_initial)
    allocation_analyses = m.allocation_universe_for_mode(mode, *groups.values())
    m.apply_deep_averaging_down_context(allocation_analyses, mode=mode)
    for ticker, analysis in allocation_analyses.items():
        if ticker == "VFV.TO":
            m.apply_vfv_benchmark_role(analysis)
            continue
        if m.is_etf_asset_analysis(analysis):
            if not m.is_external_etf_allocation_candidate(analysis):
                m.apply_etf_asset_role(analysis)
            continue
        penalty = penalties.get(ticker, 0.0) if analysis.get("universe") == "CORE_PORTFOLIO" else 0.0
        analysis.update(m.compute_capital_allocation_score(analysis, risk, penalty))
    m.apply_allocation_stability(allocation_analyses, mode=mode)
    baseline = m.load_previous_allocation_baseline(m.REPORTS_DIR, current_model_rules_version=m.MODEL_RULES_VERSION, analysis_mode=mode)
    allocation = m.allocate_capital(capital, allocation_analyses, mode, defensive_etf_candidates=defensive, previous_baseline=baseline)
    m.apply_final_decisions(allocation_analyses, allocation.get("allocations", []))
    sensitivity = m.compute_allocation_sensitivity(capital, mode, allocation_analyses, allocation)
    tax = m.compute_tax_location_report(locations, weighted, analyses, core_exposures)
    warnings += m.validate_allocation_rules(allocation.get("allocations", []), {**allocation_analyses, **defensive_validation})
    allocation["decision_quality"] = m.compute_decision_quality(allocation_analyses, allocation, risk, warnings, mode=mode, allocation_sensitivity=sensitivity)
    m.annotate_allocations_with_decision_quality(allocation)
    return semantic_result(groups, allocation, risk, tax, weighted, mode, capital)


def require_keys(mapping, keys, family):
    missing = sorted(set(keys) - set(mapping))
    if missing:
        raise BundleError(f"Missing frozen {family}: {missing}")


def semantic_result(groups, allocation, risk, tax, weighted, mode, capital):
    # Full analyses/allocation retain current model metrics and reasons. Ranking
    # is a descriptive projection, never a new selection rule.
    from src.utils import safe_float
    rankings = {}
    for universe, rows in groups.items():
        ordered = sorted(rows.values(), key=lambda r: (-(safe_float(r.get("capital_allocation_score")) or 0), r["ticker"]))
        rankings[universe] = [{"ticker": r["ticker"], "score": r.get("capital_allocation_score"),
            "rank": 1 + sum((safe_float(other.get("capital_allocation_score")) or 0) > (safe_float(r.get("capital_allocation_score")) or 0) for other in ordered)} for r in ordered]
    return {"investment_mode": mode, "capital": capital, "analyses": groups,
            "allocation": allocation, "rankings": rankings, "concentration": risk,
            "tax": tax, "portfolio": weighted}
