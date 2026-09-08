"""Synthetic observations only. Source fixtures contain code, never operational data."""
from __future__ import annotations

import base64
import copy
import json
import zlib
from pathlib import Path

from pit_comparison import PIT_BUNDLE_SCHEMA_VERSION, PIT_INPUT_CONTRACT_VERSION
from pit_comparison.bundle import CONFIG_NAMES, FAMILIES, MARKET_REQUIRED, canonical, digest, fingerprint
from pit_comparison.source_export import write_export

PIT = "2025-06-02T16:00:00+00:00"
TICKERS = ["MSFT", "INTU", "SHOP.TO", "COST", "GOOGL", "NVDA", "VFV.TO", "ZAG.TO"]
BENCHMARKS = ["UUP", "XLRE", "XBI", "KRE", "ITA", "FBTC","GDX", "KIE", "URA", "VNQ","SPY", "QQQ", "VFV.TO", "XLY", "IGV", "XLI", "SOXX", "IPAY", "XLV", "KCE", "XLK", "XLC", "XLP", "XLF", "XLB", "ICLN", "XLU", "XLE", "SMH", "IWM", "TLT", "HYG", "IEF", "BIL", "SHY", "GLD", "USO", "VIX", "^VIX", "^GSPC", "^TNX"]


def market(ticker):
    result = dict.fromkeys(sorted(MARKET_REQUIRED))
    result.update(current_price=105.0, currency="CAD" if ticker.endswith(".TO") else "USD", fetched_at="2025-06-02T15:00:00+00:00",
        source="synthetic_frozen_observation", quote_type="ETF" if ticker not in TICKERS[:6] else "EQUITY",
        long_name={"MSFT": "Microsoft Corporation", "INTU": "Intuit Inc.", "COST": "Costco Wholesale Corporation",
                   "GOOGL": "Alphabet Inc.", "NVDA": "NVIDIA Corporation", "SHOP.TO": "Shopify Inc."}.get(ticker, ticker),
        forward_pe=28, peg=1.6, sma_200=95, price_above_sma_200=True, stock_return_1y=.22,
        drawdown_from_12m_high=-.18, drawdown_from_8m_high=-.12, dividend_yield=.012,
        stock_cagr_3y=.15, stock_cagr_5y=.16, stock_cagr_10y=.14, cagr_5y=.08, cagr_10y=.09,
        profit_margins=.28, operating_margins=.32, gross_margins=.65, return_on_equity=.30,
        return_on_assets=.20, revenue_growth=.20, earnings_growth=.25, total_debt=1000., total_cash=5000.,
        market_cap=1e11, beta=1.0, forward_eps=4., trailing_eps=3., trailing_pe=35., number_of_analyst_opinions=12,
        sector_name="Technology", industry="Software", business_summary="Enterprise software subscriptions",
        country="Canada" if ticker.endswith(".TO") else "United States", news_red_flags=[], news_red_flag_count=0,
        data_source_notes=[], fundamental_fallback_fields=[], official_data_sources=[], official_fundamental_fields=[],
        official_confirmed_fields=[], official_data_conflicts=[], canadian_data_sources=[], canadian_fundamental_fields=[],
        canadian_confirmed_fields=[], canadian_data_conflicts=[], market_data_warning_flags=[], market_data_fetch_status="LIVE_SUCCESS",
        market_data_fallback_level="NONE", market_data_circuit_breaker_open=False, total_return_price_history=[])
    return result


def manual(ticker):
    facts = dict(roic_5y_avg=38., net_margin_stable_or_expanding=True, eps_growth_5y=25., moat_clear=True,
        eps_growth_estimated_3_5y=30., sector_cagr_estimated=20., forward_pe_manual=28., peg_manual=1.6,
        fair_value=150., current_price_manual=105., valuation_vs_5y_avg_ok=True,
        margin_or_profitability_under_pressure=False, forward_pe_growth_acceptable=True,
        management_quality_good=True, balance_sheet_strong=True, regulatory_risk_high=False,
        geopolitical_risk_high=False, single_product_dependency_high=False, manual_confidence_level="HIGH", notes="synthetic")
    for key in ("fraud", "moat_lost", "growth_broken", "roic_destroyed", "dangerous_debt", "obsolete_business", "destructive_management"):
        facts["catastrophic_" + key] = False
    return {**facts, "ticker": ticker, "manual_override_fields": sorted(facts), "manual_input_present": True}


def fixture_data(mode="rational-aggressive", scenario="mixed", capital=1000):
    config = {name: {} for name in sorted(CONFIG_NAMES)}
    config.update({"positions.yaml": {"positions": ["MSFT", "INTU", "COST"]},
        "benchmarks.yaml": {t: "IGV" for t in TICKERS[:6]},
        "watchlist.yaml": {"watchlist": []},
        "market_scanner.yaml": {"auto_discovery": {"enabled": True, "max_auto_candidates_for_analysis": 3}, "discovery_universe": []},
        "market_regime.yaml": {"enabled": False},
        "sectors.yaml": {"MSFT": "Technology", "INTU": "Technology", "SHOP.TO": "Technology"},
        "exposures.yaml": {t: {"cloud": True, "software": True, "ai": True} for t in TICKERS[:6]},
        "defensive_etfs.yaml": {"defensive_etfs": [{"ticker": "ZAG.TO", "name": "Synthetic bond ETF", "role": "broad_canadian_bonds", "modes": ["balanced", "family-office", "rational-aggressive"]}]}})
    data = {"context": {"validation_warnings": [], "investment_mode": mode, "capital_context": {"amount": capital, "currency": "CAD", "contribution_type": "SYNTHETIC"}},
        "portfolio": [{"ticker": "MSFT", "shares": 10., "average_cost": 80., "average_cost_currency": "USD", "account_type": "TFSA"},
                      {"ticker": "MSFT", "shares": 4., "average_cost": 90., "average_cost_currency": "CAD", "account_type": "RRSP"},
                      {"ticker": "SHOP.TO", "shares": 5., "average_cost": 70., "average_cost_currency": "CAD", "account_type": "NON_REGISTERED"}],
        "transactions": [{"date": "2025-05-01", "ticker": "MSFT", "account_type": "RRSP", "transaction_type": "BUY", "shares": 1, "price": 85, "price_currency": "USD", "fees": 1, "fees_currency": "CAD"}],
        "account_locations": [{"ticker": "MSFT", "account_type": "RRSP", "current_value": 500}],
        "universe": {"watchlist_rows": [{"ticker": "INTU", "manual_priority": "HIGH"}], "market_rows": [{"ticker": "GOOGL", "company_name": "Alphabet Inc."}],
                     "discovery_rows": [{"ticker": "NVDA", "company_name": "NVIDIA Corporation", "priority": 10}]},
        "market": {t: market(t) for t in TICKERS}, "benchmarks": {t: market(t) for t in BENCHMARKS}, "regime_market": {},
        "fx": {"CAD": 1., "USD": 1.35}, "manual_inputs": {t: manual(t) for t in TICKERS[:6]},
        "research_facts": {"MSFT": {"fair_value": 140., "moat_clear": True, "research_report_fields": ["fair_value", "moat_clear"],
            "research_report_extracted_fields": ["fair_value", "moat_clear"], "research_report_sources": ["Synthetic"],
            "research_report_dates": ["2025-05-01"], "research_report_field_dates": {"fair_value": "2025-05-01", "moat_clear": "2025-05-01"}}},
        "ticker_memory": {"MSFT": {"ticker": "MSFT", "sector": "Technology", "cloud": True}},
        "prior_state": {"status": "VERIFIED", "analysis": [], "allocation": []}, "config": config}
    for i, day in enumerate(("2025-05-30", "2025-05-29", "2025-05-28", "2025-05-27")):
        common = {"storage_role": "HISTORY", "observation_id": f"synthetic-{i}", "created_at": day + "T15:00:00+00:00", "analysis_date": day,
                  "analysis_mode": mode, "model_rules_version": "2026-08-23-allocation-room-integrity-v7"}
        data["prior_state"]["analysis"].append({**common, "rows": [{"ticker": "MSFT", "score_total": 9., "conviction_score": 88.,
            "capital_allocation_score": 84., "allocation_decision": "BUY / ADD", "final_position_action": "BUY / ADD",
            "thesis_status": "INTACT", "liquidation_status": "GREEN", "expected_cagr_quality": "HIGH"}]})
        data["prior_state"]["allocation"].append({**common, "rows": [{"ticker": "MSFT", "amount": 200., "percentage": 20., "reason": "synthetic continuity"}]})
    if scenario == "liquidation":
        data["manual_inputs"]["MSFT"]["catastrophic_fraud"] = True
        data["manual_inputs"]["SHOP.TO"]["catastrophic_growth_broken"] = True
    elif scenario == "winner":
        for row in data["portfolio"]:
            row["average_cost"] = 20.
    elif scenario == "tied":
        for ticker in ("INTU", "COST"):
            data["market"][ticker] = copy.deepcopy(data["market"]["MSFT"])
            data["manual_inputs"][ticker] = manual(ticker)
            config["sectors.yaml"][ticker] = "Technology"
    elif scenario == "drawdown":
        for t in TICKERS[:6]:
            data["market"][t].update(current_price=45., drawdown_from_12m_high=-.65, drawdown_from_8m_high=-.6, price_above_sma_200=False)
            data["manual_inputs"][t].update(current_price_manual=45., fair_value=160.)
    elif scenario == "missing":
        data["manual_inputs"] = {}
        data["research_facts"] = {}
        for t in TICKERS[:6]:
            for k in ("forward_eps", "return_on_equity", "return_on_assets", "forward_pe", "peg", "profit_margins"):
                data["market"][t][k] = None
    elif scenario == "concentration":
        data["portfolio"][0]["shares"] = 500
    elif scenario == "empty_history":
        data["prior_state"] = {"status": "VERIFIED_EMPTY", "analysis": [], "allocation": []}
    elif scenario == "latest_history":
        for kind in ("analysis", "allocation"):
            data["prior_state"][kind] = data["prior_state"][kind][:1]
            data["prior_state"][kind][0]["storage_role"] = "LATEST"
    elif scenario == "same_day":
        for kind in ("analysis", "allocation"):
            extra = copy.deepcopy(data["prior_state"][kind][0])
            extra.update(observation_id="synthetic-earlier", created_at="2025-05-30T12:00:00+00:00")
            data["prior_state"][kind].append(extra)
    elif scenario == "validation_notes":
        data["context"]["validation_warnings"] = ["Synthetic pre-decision input-quality observation"]
    elif scenario == "dated_research":
        data["manual_inputs"] = {}
        research = data["research_facts"]["MSFT"]
        research["research_report_freshness_policy_applied"] = True
        research["research_report_field_report_dates"] = {"fair_value": "2025-05-01", "moat_clear": "2025-05-01"}
    elif scenario == "zero_capital":
        data["context"]["capital_context"]["amount"] = 0
    elif scenario == "sizing_boundary":
        data["context"]["capital_context"]["amount"] = 99.99
    elif scenario == "proxy":
        data["manual_inputs"] = {}
        config["proxy_corrections.yaml"] = {"enabled": True, "corrections": {"roic_5y_avg": {"factor": 1.05, "status": "ACTIVE", "confidence": "HIGH", "sample_count": 30, "last_updated": "2025-05-01"}}}
    elif scenario == "regime":
        config["market_regime.yaml"] = {"enabled": True}
        data["regime_market"] = {t: market(t) for t in BENCHMARKS}
    source = {"observation_date": "2025-06-02", "published_at": "2025-06-02T14:00:00+00:00",
        "available_at": "2025-06-02T15:00:00+00:00", "captured_at": "2025-06-02T15:01:00+00:00",
        "availability_evidence": "Entirely synthetic controlled chronology", "source_version": "synthetic-v1",
        "source_sha256": fingerprint({"fixture": "synthetic-v1"}), "historical_version_verified": True}
    data["provenance"] = {family: copy.deepcopy(source) for family in FAMILIES if family != "provenance"}
    return data


def write_bundle(root, data=None, *, quality="COMPLETE_PIT", pretty=False):
    data = fixture_data() if data is None else copy.deepcopy(data)
    root = Path(root)
    root.mkdir(parents=True)
    (root / "inputs").mkdir()
    files = []
    for name in FAMILIES:
        payload = (json.dumps(data[name], indent=2, allow_nan=False) + "\n").encode() if pretty else canonical(data[name])
        path = f"inputs/{name}.json"
        (root / path).write_bytes(payload)
        files.append({"logical_id": name, "path": path, "byte_length": len(payload), "sha256": digest(payload)})
    manifest = {"bundle_schema_version": PIT_BUNDLE_SCHEMA_VERSION, "input_contract_version": PIT_INPUT_CONTRACT_VERSION,
        "effective_pit_at": PIT, "semantic_timezone": "America/Toronto", "created_at": "2026-01-01T00:00:00+00:00",
        "comparison_mode": "RETROSPECTIVE_PIT", **data["context"], "portfolio_snapshot_id": "sha256:" + fingerprint(data["portfolio"]),
        "allowed_data_cutoff": {"available_at_lte": PIT, "historical_revision_policy": "AS_AVAILABLE_AT_T"}, "pit_quality": quality,
        "history_policy": {"selection": "EXPLICIT_ADMISSIBLE_RECORDS", "status": data["prior_state"]["status"]},
        "provenance": {"logical_input": "provenance", "sha256": fingerprint(data["provenance"])},
        "logical_inputs": sorted(FAMILIES), "files": files,
        "explicit_absences": sorted(k for k in FAMILIES if data[k] == {} or data[k] == [])}
    manifest["input_identity"] = fingerprint({"contract": PIT_INPUT_CONTRACT_VERSION, "files": sorted(files, key=lambda r:r["logical_id"]), "effective_pit_at": PIT, "semantic_timezone": manifest["semantic_timezone"]})
    manifest["bundle_hash"] = fingerprint(manifest)
    manifest["bundle_id"] = "sha256:" + manifest["bundle_hash"]
    (root / "bundle_manifest.json").write_bytes(canonical(manifest))
    return manifest["bundle_hash"]


def fixture_export(repo, revision, destination, *, lineage):
    fixture = json.loads((Path(__file__).with_name("pit_source_revisions.json")).read_text())[lineage]
    if revision != fixture["commit"]:
        raise ValueError("Unexpected fixture revision")
    code = Path(__file__).resolve().parents[1]
    blobs = {}
    for name, record in fixture["files"].items():
        raw = zlib.decompress(base64.b64decode(record["content_zlib_base64"])) if "content_zlib_base64" in record else (code / name).read_bytes()
        if digest(raw) != record["sha256"]:
            raise ValueError("Pinned source fixture drift: " + name)
        blobs[name] = raw
    return write_export(destination, revision, fixture["tree"], lineage, blobs)
