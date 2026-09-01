from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from src.add_eligibility_engine import compute_add_eligibility_status
from src.allocation_change_engine import (
    build_allocation_change_rows,
    load_previous_allocation_baseline,
    save_allocation_snapshot,
)
from src.anomaly_detection_engine import detect_analysis_anomalies, update_anomaly_history
from src.allocation_sensitivity_engine import compute_allocation_sensitivity
from src.allocation_stability_engine import apply_allocation_stability
from src.allocation_engine import (
    allocate_capital,
    allocation_universe_for_mode,
    apply_deep_averaging_down_context,
)
from src.account_performance_engine import build_account_performance_rows
from src.audit_signal_engine import compute_full_audit_signal, compute_model_audit_signal
from src.asset_type_engine import (
    etf_asset_profile,
    etf_risk_exposure,
    etf_risk_sector,
    is_etf_asset,
    is_etf_asset_analysis,
    is_fallback_benchmark,
)
from src.auto_fundamentals import build_automated_manual_inputs, merge_automated_with_manual_overrides
from src.backtest_engine import run_backtests_from_latest_reports
from src.backup_engine import create_project_backup, list_project_backups
from src.baseline_identity import baseline_observation_metadata
from src.benchmark_relevance_engine import compute_benchmark_relevance, enrich_benchmark_map, infer_benchmark_from_context
from src.cache_management_engine import CACHE_HEALTH_COLUMNS, reset_expired_market_circuit_breakers, run_cache_maintenance
from src.cagr_quality_engine import compute_expected_cagr_quality, compute_quality_but_too_expensive
from src.cash_flow_quality_engine import compute_cash_flow_quality
from src.confidence_range_engine import compute_conviction_confidence_range
from src.conviction_engine import compute_conviction_score
from src.cycle_bubble_risk_engine import compute_cycle_bubble_risk
from src.csv_schema_engine import SCHEMA_REPAIR_COLUMNS, repair_safe_csv_schemas, validate_csv_schemas
from src.data_reliability_engine import (
    apply_reliability_cagr_cap,
    apply_reliability_confidence_cap,
    apply_reliability_conviction_cap,
    apply_reliability_opportunity_cap,
    compute_data_reliability,
)
from src.data_fetcher import MarketDataFetcher, benchmark_metrics_for
from src.data_freshness_engine import apply_market_freshness_to_reliability, compute_market_data_freshness
from src.decision_quality_engine import annotate_allocations_with_decision_quality, compute_decision_quality
from src.decision_manifest_engine import (
    build_decision_manifest,
    git_tracked_state,
    write_decision_manifest,
    write_failed_run_audit,
)
from src.defensive_etf_engine import (
    build_defensive_etf_candidates,
    defensive_etf_analysis_map,
    defensive_etf_tickers_for_mode,
    load_defensive_etf_config,
)
from src.double_counting_engine import apply_double_counting_context
from src.external_etf_engine import apply_external_etf_candidate_context, is_external_etf_allocation_candidate
from src.discovery_engine import build_discovery_maintenance_rows, classify_discovery_idea, load_auto_discovery_universe, load_discovery_universe
from src.drift_engine import compute_drift_status
from src.history_engine import apply_history_context, load_previous_snapshot, save_current_snapshot
from src.hidden_cluster_engine import apply_hidden_cluster_guardrails
from src.health_check_engine import HEALTH_CHECK_COLUMNS, health_summary, run_health_check
from src.critical_input_engine import (
    CriticalInputError,
    audit_baseline_environment_authority,
    audit_runtime_critical_inputs,
    audit_static_critical_inputs,
    merge_input_audits,
)
from src.dependency_reproducibility import dependency_environment
from src.instrument_profile_engine import build_instrument_profiles
from src.liquidation_engine import apply_history_sell_discipline, compute_liquidation_status
from src.long_term_durability_engine import compute_long_term_durability
from src.full_audit_engine import run_full_audit
from src.market_growth_thesis_engine import compute_market_growth_thesis
from src.market_regime_engine import (
    apply_market_regime_context,
    apply_sector_euphoria_context,
    compute_market_regime,
    create_market_regime_config_template,
    fetch_market_regime_data,
    load_market_regime_config,
)
from src.market_scanner import (
    create_market_universe_template,
    load_market_universe,
    classify_market_candidate,
    DEFAULT_COMPANY_NAMES,
)
from src.mode_artifacts import write_csv_records_mode_pair
from src.model_audit_engine import run_model_audit
from src.model_improvement_engine import apply_safe_tuning, run_improvement_audit
from src.model_tuning import create_model_tuning_template
from src.model_version import MODEL_RULES_VERSION
from src.validation_evidence import RunPurpose, resolve_analysis_run_purpose
from src.manual_inputs import (
    create_friendly_manual_template,
    load_friendly_manual_inputs,
)
from src.manual_input_sync import sync_proxy_calibration_to_friendly
from src.opportunity_cost_engine import compute_opportunity_cost_status
from src.portfolio_loader import (
    account_tax_category,
    account_locations_from_portfolio_rows,
    add_position_weights,
    create_empty_portfolio,
    create_portfolio_template,
    enrich_portfolio_with_market_data,
    infer_quote_currency,
    load_account_locations,
    load_portfolio,
    position_weight_map,
)
from src.portfolio_change_tracker import update_portfolio_change_history
from src.portfolio_inferred_transactions import update_inferred_transactions_from_changes
from src.portfolio_sync_engine import sync_portfolio_state_from_rows
from src.portfolio_transactions import (
    build_portfolio_transaction_report_rows,
    create_empty_portfolio_transactions,
    create_portfolio_transactions_template,
    load_portfolio_transactions,
    portfolio_transaction_currencies,
    summarize_portfolio_transactions,
)
from src.portfolio_risk_engine import compute_portfolio_risk
from src.proof_score_engine import compute_proof_score
from src.promotion_engine import external_core_fit_status, promotion_profile_alignment_status
from src.quality_drawdown_engine import apply_quality_drawdown_context
from src.shareholder_discipline_engine import compute_shareholder_discipline
from src.sell_validation_checklist_engine import sell_validation_checklist_rows
from src.proxy_calibration import (
    PROXY_CALIBRATION_FIELD_NAMES,
    build_proxy_calibration_report,
    build_proxy_calibration_summary,
    clear_proxy_calibration_values,
    create_proxy_calibration_history,
    create_proxy_calibration_field_guide,
    create_proxy_calibration_template,
    load_proxy_calibration_inputs,
    update_proxy_calibration_history,
)
from src.proxy_bias_engine import build_proxy_bias_report
from src.proxy_correction_engine import (
    build_proxy_correction_audit,
    create_proxy_correction_history,
    create_proxy_corrections_template,
    load_proxy_corrections,
)
from src.report_generator import generate_reports
from src.research_reports import (
    BNCD_MORNINGSTAR_DIR,
    RESEARCH_NEEDED_COLUMNS,
    RESEARCH_REPORTS_DIR,
    create_research_report_scaffold,
    load_research_report_inputs,
    merge_research_with_automated,
    research_needed_rows_from_reports,
    research_needed_rows_from_analysis_rows,
    research_status_rows,
    write_research_needed_csv,
    write_research_status_csv,
)
from src.run_logging_engine import (
    RUN_LOG_COLUMNS,
    apply_run_identity_metadata,
    append_run_log_history,
    build_analysis_run_log,
    build_health_check_run_log,
    build_walk_forward_run_log,
    make_run_id,
    write_universe_snapshot,
)
from src.scoring import compute_fundamental_score
from src.sizing_engine import compute_capital_allocation_score, compute_winner_accelerated
from src.score_stability_engine import SCORE_STABILITY_COLUMNS, compute_score_stability
from src.stress_test_engine import compute_stress_tests
from src.tax_location_engine import compute_after_tax_yield, compute_tax_location_report
from src.thesis_engine import compute_thesis_status
from src.thesis_reversal_engine import build_thesis_reversal_audit_rows
from src.ticker_resolver import (
    apply_ticker_attention_flags,
    load_and_resolve_universe,
    load_ticker_aliases,
    resolve_account_location_rows,
    resolve_keyed_config,
    resolve_manual_inputs,
    resolve_portfolio_lot_rows,
    resolve_portfolio_rows,
    resolve_portfolio_transaction_rows,
    resolve_ticker_list,
)
from src.ticker_memory_engine import (
    apply_ticker_memory_to_exposure_map,
    apply_ticker_memory_to_sector_map,
    build_ticker_memory_rows,
    load_ticker_memory,
    update_ticker_memory,
)
from src.utils import CACHE_DIR, CONFIG_DIR, DATA_DIR, PROJECT_ROOT, REPORTS_DIR, ensure_directories, load_yaml, normalize_ticker, safe_float, write_csv_records
from src.validation_priority_engine import build_validation_priority_rows
from src.validators import validate_allocation_rules, validate_capital, validate_input_files
from src.watchlist_engine import create_watchlist_template, load_watchlist, classify_watchlist_analysis, compute_data_quality
from src.walk_forward_backtest_engine import run_walk_forward_backtest
from src.walk_forward_signal_engine import compute_walk_forward_signal
from src.winner_protection_engine import apply_winner_protection


VALID_MODES = {"balanced", "rational-aggressive", "family-office", "high-cagr"}

# [DECISION 2026-07-04] Seuil d'inclusion des tickers DISCOVERY_IDEAS
# dans validation_priority_rows. Seuls les candidats ayant franchi les
# gates d'allocation (allocation_status in ELIGIBLE_BUT_NOT_SELECTED ou
# NO_NEW_ALLOCATION) ET un capital_allocation_score >= ce seuil génèrent
# des demandes de rapports BNCD/Morningstar. Évite de polluer la liste
# research-needed avec des candidats faibles parmi les 100+ tickers Discovery.
DISCOVERY_VALIDATION_PRIORITY_MIN_SCORE = 70
EXTERNAL_CANDIDATE_REPORT_CAP = 30
FAIR_VALUE_IMPLAUSIBLE_RATIO = 20.0


def expand_exclusions_with_alias_inputs(excluded_tickers: set[str], ticker_aliases: dict[str, dict[str, str]]) -> set[str]:
    expanded = {normalize_ticker(ticker) for ticker in excluded_tickers if normalize_ticker(ticker)}
    for input_ticker, alias in ticker_aliases.items():
        resolved = normalize_ticker(alias.get("resolved_ticker"))
        if resolved in expanded:
            expanded.add(normalize_ticker(input_ticker))
    return expanded


def _reject_implausible_fair_value(manual: dict[str, Any], market: dict[str, Any]) -> None:
    fair_value = safe_float(manual.get("fair_value"))
    if fair_value is None or fair_value <= 0:
        return
    if "fair_value" in set(manual.get("manual_override_fields") or []):
        return
    price = safe_float(market.get("current_price"))
    if price is None or price <= 0:
        return

    ratio = fair_value / price
    if ratio <= FAIR_VALUE_IMPLAUSIBLE_RATIO and ratio >= 1 / FAIR_VALUE_IMPLAUSIBLE_RATIO:
        return

    ticker = str(manual.get("ticker") or "").strip() or "UNKNOWN"
    manual.pop("fair_value", None)
    manual["research_report_fields"] = [
        field for field in manual.get("research_report_fields", []) if field != "fair_value"
    ]
    warnings = list(manual.get("research_report_extraction_warnings") or [])
    warnings.append(
        f"Fair value rejetée: {ticker} juste valeur {fair_value} vs "
        f"prix {price} (ratio {ratio:.1f}×) — écart implausible >20×, "
        f"probable corruption d'extraction; champ retiré avant scoring."
    )
    manual["research_report_extraction_warnings"] = warnings


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "init":
        init_project()
        print("Projet initialisé. Remplissez data/portfolio.csv. Le fichier manuel est optionnel.")
        return 0
    if args.command == "export-template":
        export_templates()
        print("Templates régénérés.")
        return 0
    if args.command == "validate-inputs":
        ensure_directories()
        errors = validate_input_files(PROJECT_ROOT)
        if errors:
            print("Validation échouée:")
            for error in errors:
                print(f"- {error}")
            return 1
        print("Validation réussie.")
        return 0
    if args.command == "research-needed":
        return research_needed_command(args)
    if args.command == "research-status":
        return research_status_command(args)
    if args.command == "health-check":
        return health_check_command(args)
    if args.command == "clear-proxy-calibration":
        return clear_proxy_calibration_command(args)
    if args.command == "backtest":
        return backtest_command(args)
    if args.command == "walk-forward-backtest":
        return walk_forward_backtest_command(args)
    if args.command == "backup":
        return backup_command(args)
    if args.command == "list-backups":
        return list_backups_command(args)
    if args.command == "model-audit":
        return model_audit_command(args)
    if args.command == "full-audit":
        return full_audit_command(args)
    if args.command == "improvement-audit":
        return improvement_audit_command(args)
    if args.command == "apply-safe-tuning":
        return apply_safe_tuning_command(args)
    if args.command == "sync-manual-inputs":
        return sync_manual_inputs_command(args)
    if args.command == "sync-portfolio":
        return sync_portfolio_command(args)
    if args.command == "analyze":
        return analyze_command(args)
    parser.print_help()
    return 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Agent local de gestion de portefeuille long terme.")
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("init", help="Crée les fichiers templates et fichiers CSV de départ.")
    subparsers.add_parser("export-template", help="Regénère les templates.")
    subparsers.add_parser("validate-inputs", help="Valide les fichiers CSV.")
    research_needed = subparsers.add_parser(
        "research-needed",
        help="Liste les entreprises pour lesquelles un rapport BNCD/Morningstar serait utile.",
    )
    research_needed.add_argument("--limit", type=int, default=30, help="Nombre maximal de lignes à afficher.")
    research_needed.add_argument("--refresh-market-data", action="store_true", help="Ignore le cache de marché pour cette vérification.")
    research_status = subparsers.add_parser(
        "research-status",
        help="Vérifie si les PDF/TXT BNCD/Morningstar sont visibles et lisibles.",
    )
    research_status.add_argument("--limit", type=int, default=50, help="Nombre maximal de fichiers à afficher.")
    health_check = subparsers.add_parser(
        "health-check",
        help="Vérifie l’état local du modèle, des CSV, dépendances, caches et rapports BNCD.",
    )
    health_check.add_argument("--limit", type=int, default=20, help="Nombre maximal d’alertes à afficher.")
    health_check.add_argument(
        "--repair-safe",
        action="store_true",
        help="Applique seulement les réparations mécaniques à faible risque: colonnes manquantes, fichiers CSV absents, lignes vides.",
    )
    health_check.add_argument(
        "--skip-portfolio-repair",
        action="store_true",
        help="Valide data/portfolio.csv sans le créer ni le réécrire pendant --repair-safe.",
    )
    subparsers.add_parser(
        "clear-proxy-calibration",
        help="Vide les vraies valeurs du fichier de calibration des proxies après recalibration.",
    )
    backtest = subparsers.add_parser(
        "backtest",
        help="Teste théoriquement la mécanique d'allocation contre VFV.TO avec prix historiques gratuits.",
    )
    backtest.add_argument("--years", type=int, nargs="+", default=[5, 10], help="Périodes à tester, ex: --years 5 10.")
    backtest.add_argument("--monthly-capital", type=float, default=500.0, help="Cotisation mensuelle simulée.")
    backtest.add_argument("--mode", choices=sorted(VALID_MODES), default="high-cagr")
    backtest.add_argument("--refresh-market-data", action="store_true", help="Retélécharge l'historique yfinance.")

    walk_forward = subparsers.add_parser(
        "walk-forward-backtest",
        help="Prépare l’inventaire hors-échantillon basé sur les snapshots historiques locaux.",
    )
    walk_forward.add_argument("--mode", choices=sorted(VALID_MODES), default="high-cagr")
    walk_forward.add_argument(
        "--min-days-between-points",
        type=int,
        default=14,
        help="Nombre minimal de jours entre deux snapshots pour compter une période walk-forward.",
    )
    walk_forward.add_argument(
        "--recommended-min-periods",
        type=int,
        default=6,
        help="Nombre minimal de périodes utilisables avant de considérer le walk-forward comme informatif.",
    )
    walk_forward.add_argument(
        "--refresh-market-data",
        action="store_true",
        help="Retélécharge les prix historiques utilisés pour la simulation walk-forward.",
    )

    backup = subparsers.add_parser(
        "backup",
        help="Crée une sauvegarde datée du modèle avant une grosse modification.",
    )
    backup.add_argument(
        "--include-cache",
        action="store_true",
        help="Inclut aussi data/cached_market_data. Non recommandé sauf besoin précis.",
    )
    subparsers.add_parser(
        "list-backups",
        help="Affiche les sauvegardes déjà créées.",
    )

    model_audit = subparsers.add_parser(
        "model-audit",
        help="Audite la stabilité et la cohérence du modèle à partir des analyses déjà sauvegardées.",
    )
    model_audit.add_argument("--period", default="12m", help="Période à auditer: 90d, 6m, 12m, 2y ou all.")
    model_audit.add_argument(
        "--mode",
        choices=sorted(VALID_MODES),
        default="high-cagr",
        help="Mode à auditer. Par défaut: high-cagr.",
    )

    full_audit = subparsers.add_parser(
        "full-audit",
        help="Crée un audit maître: cohérence, performance réelle, backtest et risque multi-cycle.",
    )
    full_audit.add_argument("--period", default="all", help="Période à auditer: 90d, 6m, 12m, 2y ou all.")
    full_audit.add_argument("--years", type=int, nargs="+", default=[5, 10], help="Backtests théoriques à inclure.")
    full_audit.add_argument("--mode", choices=sorted(VALID_MODES), default="high-cagr")
    full_audit.add_argument(
        "--monthly-capital",
        type=float,
        default=None,
        help="Optionnel. Si absent, l’audit utilise la cotisation moyenne détectée dans l’historique.",
    )
    full_audit.add_argument("--refresh-market-data", action="store_true", help="Retélécharge l'historique yfinance.")

    improvement_audit = subparsers.add_parser(
        "improvement-audit",
        help="Propose des micro-ajustements prudents du modèle sans les appliquer.",
    )
    improvement_audit.add_argument("--period", default="12m", help="Période à auditer: 90d, 6m, 12m, 2y ou all.")
    improvement_audit.add_argument("--mode", choices=sorted(VALID_MODES), default="high-cagr")

    apply_tuning = subparsers.add_parser(
        "apply-safe-tuning",
        help="Applique seulement les ajustements SAFE proposés par improvement-audit.",
    )
    apply_tuning.add_argument("--mode", choices=sorted(VALID_MODES), default="high-cagr")

    subparsers.add_parser(
        "sync-manual-inputs",
        help=(
            "Traduit proxy_calibration_input.csv en manual_inputs_friendly.txt. "
            "A relancer apres chaque mise a jour du fichier de calibration."
        ),
    )

    sync_portfolio = subparsers.add_parser(
        "sync-portfolio",
        help="Met à jour l'historique du portefeuille sans créer une nouvelle recommandation.",
    )
    sync_portfolio.add_argument(
        "--date",
        default=None,
        help="Date à inscrire dans l'historique, format YYYY-MM-DD. Par défaut: aujourd'hui.",
    )
    sync_portfolio.add_argument(
        "--refresh-market-data",
        action="store_true",
        help="Rafraîchit les prix utilisés pour estimer la valeur des changements.",
    )

    analyze = subparsers.add_parser("analyze", help="Lance l’analyse du portefeuille.")
    analyze.add_argument("--capital", type=float, default=0.0, help="Nouveau capital à allouer.")
    analyze.add_argument("--mode", choices=sorted(VALID_MODES), default="rational-aggressive")
    analyze.add_argument("--refresh-market-data", action="store_true", help="Ignore le cache de marché.")
    analyze.add_argument(
        "--run-purpose",
        choices=[purpose.value for purpose in RunPurpose if purpose is not RunPurpose.UNKNOWN_LEGACY],
        default=None,
        help="But auditable du run. Sans valeur, le snapshot reste UNKNOWN_LEGACY (ou ZERO_CAPITAL_ANALYSIS si capital nul).",
    )
    return parser


def init_project() -> None:
    ensure_directories()
    create_research_report_scaffold()
    export_templates()
    if not (DATA_DIR / "portfolio.csv").exists():
        create_empty_portfolio(DATA_DIR / "portfolio.csv")
    if not (DATA_DIR / "portfolio_transactions.csv").exists():
        create_empty_portfolio_transactions(DATA_DIR / "portfolio_transactions.csv")
    if not (DATA_DIR / "manual_inputs_friendly.txt").exists():
        create_friendly_manual_template(DATA_DIR / "manual_inputs_friendly.txt", load_default_manual_tickers())
    if not (DATA_DIR / "watchlist.csv").exists():
        create_watchlist_template(DATA_DIR / "watchlist.csv", [])
    if not (DATA_DIR / "market_universe.csv").exists():
        create_market_universe_template(DATA_DIR / "market_universe.csv", [])
    if not (DATA_DIR / "proxy_calibration.csv").exists():
        create_proxy_calibration_template(DATA_DIR / "proxy_calibration.csv")
    if not (DATA_DIR / "proxy_calibration_field_guide.csv").exists():
        create_proxy_calibration_field_guide(DATA_DIR / "proxy_calibration_field_guide.csv")
    if not (DATA_DIR / "proxy_calibration_history.csv").exists():
        create_proxy_calibration_history(DATA_DIR / "proxy_calibration_history.csv")
    if not (CONFIG_DIR / "model_tuning.yaml").exists():
        create_model_tuning_template(CONFIG_DIR / "model_tuning.yaml")
    if not (CONFIG_DIR / "market_regime.yaml").exists():
        create_market_regime_config_template(CONFIG_DIR / "market_regime.yaml")
    if not (CONFIG_DIR / "proxy_corrections.yaml").exists():
        create_proxy_corrections_template(CONFIG_DIR / "proxy_corrections.yaml")
    if not (DATA_DIR / "proxy_correction_history.csv").exists():
        create_proxy_correction_history(DATA_DIR / "proxy_correction_history.csv")


def export_templates() -> None:
    ensure_directories()
    create_research_report_scaffold()
    create_portfolio_template(DATA_DIR / "portfolio_template.csv")
    create_portfolio_transactions_template(DATA_DIR / "portfolio_transactions_template.csv")
    watchlist_tickers = load_yaml(CONFIG_DIR / "watchlist.yaml").get("watchlist", [])
    create_watchlist_template(DATA_DIR / "watchlist_template.csv", [normalize_ticker(ticker) for ticker in watchlist_tickers])
    market_rows = [
        {
            "ticker": normalize_ticker(item.get("ticker") if isinstance(item, dict) else item),
            "company_name": str(item.get("company_name") or "").strip()
            if isinstance(item, dict)
            else DEFAULT_COMPANY_NAMES.get(normalize_ticker(item), ""),
        }
        for item in load_yaml(CONFIG_DIR / "market_scanner.yaml").get("default_universe", [])
    ]
    create_market_universe_template(DATA_DIR / "market_universe_template.csv", market_rows)
    create_proxy_calibration_template(DATA_DIR / "proxy_calibration_template.csv")
    create_proxy_calibration_field_guide(DATA_DIR / "proxy_calibration_field_guide.csv")
    create_model_tuning_template(CONFIG_DIR / "model_tuning_template.yaml", overwrite=True)
    create_market_regime_config_template(CONFIG_DIR / "market_regime_template.yaml", overwrite=True)
    create_proxy_corrections_template(CONFIG_DIR / "proxy_corrections_template.yaml", overwrite=True)


def analyze_command(args: argparse.Namespace) -> int:
    ensure_directories()
    validation_errors = validate_capital(args.capital)
    if validation_errors:
        for error in validation_errors:
            print(error)
        return 1
    input_warnings = validate_input_files(PROJECT_ROOT)
    if input_warnings:
        print("Problèmes de validation détectés; les entrées critiques échoueront avant toute allocation.")

    try:
        result = run_analysis(
            capital=args.capital,
            mode=args.mode,
            refresh_market_data=args.refresh_market_data,
            validation_warnings=input_warnings,
            run_purpose=args.run_purpose,
        )
    except CriticalInputError as exc:
        print("Analyse annulée: entrée critique non fiable. Aucune allocation ni preuve forward créée.")
        for issue in exc.audit.get("hard_failures", []):
            print(f"- {issue.get('code')}: {issue.get('message')}")
        print(f"Audit d’échec: {REPORTS_DIR / 'latest_failed_run_audit.json'}")
        return 2
    print(f"Analyse terminée en mode {args.mode}.")
    print(f"Rapport Markdown: {REPORTS_DIR / 'latest_report.md'}")
    print(f"Rapport HTML: {REPORTS_DIR / 'latest_report.html'}")
    print(f"Journal d'exécution: {REPORTS_DIR / 'latest_run_log.csv'}")
    if result.get("allocations"):
        print("Allocation recommandée:")
        for row in result["allocations"]:
            print(f"- {row['destination']}: {row['montant']:.2f} $ ({row['bloc']})")
    return 0


def sync_manual_inputs_command(args: argparse.Namespace) -> int:
    """Translate proxy calibration into provenance-aware friendly inputs."""
    del args
    proxy_path = DATA_DIR / "proxy_calibration.csv"
    friendly_path = DATA_DIR / "manual_inputs_friendly.txt"
    log_path = DATA_DIR / "proxy_calibration_sync_log.json"

    if not proxy_path.exists():
        print(f"Fichier source introuvable: {proxy_path}")
        return 1

    try:
        sync_log = sync_proxy_calibration_to_friendly(proxy_path, friendly_path, log_path)
    except Exception as exc:
        print(f"Erreur de synchronisation {proxy_path}: {exc}")
        return 1

    print("sync-manual-inputs termine.")
    print(f"  Sections ecrites       : {sync_log['sections_written']}")
    print(f"  Tickers sans donnees   : {sync_log['skipped_no_data']}")
    if sync_log["stale_tickers"]:
        print(f"  Calibration perimee    : {', '.join(sync_log['stale_tickers'])}")
        print("    -> Valeurs preservees comme contexte, mais non autoritaires.")
    if sync_log["warning_tickers"]:
        print(f"  Proche de l'expiration : {', '.join(sync_log['warning_tickers'])}")
    if sync_log["no_date_tickers"]:
        print(f"  Sans source_date       : {', '.join(sync_log['no_date_tickers'])}")
        print("    -> Valeurs preservees comme contexte non autoritaire; ajouter source_date.")
    print(f"  Fichier de sortie      : {friendly_path}")
    print(f"  Journal de sync        : {log_path}")
    if sync_log["sections_written"] > 0:
        print()
        print("Relancer analyze pour appliquer les valeurs actuelles selon leur provenance.")

    return 0


def sync_portfolio_command(args: argparse.Namespace) -> int:
    ensure_directories()
    as_of_date = _validated_sync_date(args.date) if args.date else None
    if args.date and as_of_date is None:
        print("Date invalide. Utilise le format YYYY-MM-DD, par exemple 2026-05-28.")
        return 1

    if not (DATA_DIR / "portfolio.csv").exists():
        init_project()

    input_warnings = validate_input_files(PROJECT_ROOT)
    if input_warnings:
        print("Avertissements de validation détectés. La synchronisation continue avec prudence.")

    result = sync_portfolio_state(refresh_market_data=args.refresh_market_data, as_of_date=as_of_date)
    print(f"Synchronisation du portefeuille terminée pour la date {result['as_of_date']}.")
    print("Aucune nouvelle recommandation d'allocation n'a été créée.")
    if result["latest_change_count"] == 0:
        print("Aucun changement détecté depuis le dernier état sauvegardé.")
    else:
        print("Changements détectés:")
        for row in result["latest_changes"]:
            ticker = row.get("ticker")
            account = row.get("account_type")
            change_type = row.get("change_type")
            shares_change = row.get("shares_change")
            value = row.get("estimated_change_value_cad")
            value_text = f", valeur estimée {value} $" if value not in {None, ""} else ""
            print(f"- {ticker} / {account}: {change_type}, variation {shares_change} action(s){value_text}")
    print(f"Historique mis à jour: {DATA_DIR / 'portfolio_change_history.csv'}")
    print(f"Résumé CSV mis à jour: {REPORTS_DIR / 'latest_portfolio_changes.csv'}")
    if result.get("account_performance_count"):
        print(f"Performance par compte mise à jour: {REPORTS_DIR / 'latest_account_performance_vs_sp500.csv'}")
    return 0


def sync_portfolio_state(refresh_market_data: bool = False, as_of_date: str | None = None) -> dict[str, Any]:
    ticker_aliases = load_ticker_aliases(CONFIG_DIR / "ticker_aliases.yaml")
    ticker_resolution_metadata: dict[str, dict[str, Any]] = {}

    raw_portfolio_rows = load_portfolio(DATA_DIR / "portfolio.csv")
    raw_portfolio_transaction_rows = load_portfolio_transactions(DATA_DIR / "portfolio_transactions.csv")
    portfolio_rows = resolve_portfolio_rows(
        raw_portfolio_rows,
        ticker_aliases,
        ticker_resolution_metadata,
        "data/portfolio.csv",
    )
    portfolio_lot_rows = resolve_portfolio_lot_rows(
        raw_portfolio_rows,
        ticker_aliases,
        ticker_resolution_metadata,
        "data/portfolio.csv",
    )
    portfolio_transaction_rows = resolve_portfolio_transaction_rows(
        raw_portfolio_transaction_rows,
        ticker_aliases,
        ticker_resolution_metadata,
        "data/portfolio_transactions.csv",
    )
    tickers = sorted({row["ticker"] for row in [*portfolio_rows, *portfolio_lot_rows] if row.get("ticker")} | {"VFV.TO"})

    fetcher = MarketDataFetcher()
    market_data = {ticker: fetcher.fetch_ticker(ticker, refresh=refresh_market_data) for ticker in tickers}
    portfolio_currencies = [
        infer_quote_currency(row["ticker"], market_data.get(row["ticker"], {}).get("currency"))
        for row in portfolio_lot_rows
        if row.get("ticker")
    ]
    portfolio_currencies.extend(
        str(row.get("average_cost_currency") or row.get("acquisition_value_currency") or "").upper()
        for row in [*portfolio_rows, *portfolio_lot_rows]
        if row.get("average_cost_currency") or row.get("acquisition_value_currency")
    )
    portfolio_currencies.extend(portfolio_transaction_currencies(portfolio_transaction_rows))
    fx_rates_to_cad = fetcher.fetch_fx_rates_to_cad(portfolio_currencies, refresh=refresh_market_data)
    enriched_lot_rows = enrich_portfolio_with_market_data(portfolio_lot_rows, market_data, fx_rates_to_cad)
    portfolio_transaction_report_rows = build_portfolio_transaction_report_rows(portfolio_transaction_rows, fx_rates_to_cad)

    vfv_payload = market_data.get("VFV.TO") or {}
    sp500_proxy_return_price = safe_float(
        vfv_payload.get("total_return_price")
        or vfv_payload.get("adjusted_current_price")
        or vfv_payload.get("current_price")
    )
    return sync_portfolio_state_from_rows(
        enriched_lot_rows,
        DATA_DIR,
        REPORTS_DIR,
        market_data=market_data,
        portfolio_transaction_rows=portfolio_transaction_report_rows,
        sp500_proxy_price=sp500_proxy_return_price,
        sp500_proxy_price_basis=str(vfv_payload.get("total_return_basis") or "PRICE_CLOSE"),
        as_of_date=as_of_date,
    )


def _validated_sync_date(value: str | None) -> str | None:
    if value is None or str(value).strip() == "":
        return None
    text = str(value).strip()
    try:
        return datetime.strptime(text, "%Y-%m-%d").date().isoformat()
    except ValueError:
        return None


def research_needed_command(args: argparse.Namespace) -> int:
    ensure_directories()
    create_research_report_scaffold()
    rows = build_research_needed_rows_from_current_inputs(refresh_market_data=args.refresh_market_data)
    write_research_needed_csv(REPORTS_DIR / "latest_research_needed.csv", rows)
    if not rows:
        print("Aucun rapport BNCD/Morningstar prioritaire à chercher pour l’instant.")
        return 0
    print(f"Liste créée: {REPORTS_DIR / 'latest_research_needed.csv'}")
    print(f"Dossier où déposer les PDF: {BNCD_MORNINGSTAR_DIR}")
    print("Rapports BNCD/Morningstar à chercher en priorité:")
    for row in rows[: max(1, args.limit)]:
        print(
            f"- {row['ticker_display']} [{row['priority']} / {row.get('need_type', 'DATA')}]: {row['reason']} "
            f"-> fichier suggéré: {row['suggested_file_name']}"
        )
    print("")
    print("ATTENTION: classement dégradé.")
    print("Cette commande n'exécute pas le moteur d'allocation. Le score de potentiel")
    print("(ticker_potential_score) est donc sous-évalué et l'ordre diffère de celui")
    print("produit par `analyze`.")
    print("Pour le classement de référence, utiliser le fichier produit par `analyze`.")
    return 0


def backtest_command(args: argparse.Namespace) -> int:
    ensure_directories()
    if args.monthly_capital <= 0:
        print("Le capital mensuel doit être positif.")
        return 1
    try:
        result = run_backtests_from_latest_reports(
            reports_dir=REPORTS_DIR,
            data_dir=DATA_DIR,
            years=args.years,
            monthly_capital=args.monthly_capital,
            mode=args.mode,
            refresh_market_data=args.refresh_market_data,
        )
    except Exception as exc:
        print(f"Backtest impossible: {exc}")
        return 1

    print(f"Backtest terminé en mode {args.mode}.")
    print(f"Rapport: {REPORTS_DIR / 'latest_backtest_report.md'}")
    print(f"Résumé CSV: {REPORTS_DIR / 'latest_backtest_summary.csv'}")
    print(f"Benchmarks CSV: {REPORTS_DIR / 'latest_benchmark_comparison.csv'}")
    for row in result.get("summaries", []):
        annual = safe_float(row.get("money_weighted_annual_return"))
        annual_text = f"{annual:.2%}" if annual is not None else "N/D"
        print(
            f"- {row['period_years']} ans: valeur finale {row['final_value']:.2f} $, "
            f"VFV {row['vfv_final_value']:.2f} $, écart {row['excess_value_vs_vfv']:.2f} $, "
            f"rendement annualisé approx. {annual_text}"
        )
    return 0


def walk_forward_backtest_command(args: argparse.Namespace) -> int:
    ensure_directories()
    run_id = make_run_id("walk-forward-backtest", args.mode)
    result = run_walk_forward_backtest(
        REPORTS_DIR,
        DATA_DIR,
        mode=args.mode,
        min_days_between_points=args.min_days_between_points,
        recommended_min_periods=args.recommended_min_periods,
        refresh_market_data=args.refresh_market_data,
    )
    coverage = result.get("coverage") or {}
    summary = result.get("summary") or {}
    run_log_rows = build_walk_forward_run_log(
        run_id=run_id,
        mode=args.mode,
        refresh_market_data=args.refresh_market_data,
        result=result,
    )
    write_csv_records(REPORTS_DIR / "latest_run_log.csv", run_log_rows, RUN_LOG_COLUMNS)
    append_run_log_history(DATA_DIR / "run_log_history.csv", run_log_rows)
    print(f"Backtest walk-forward préparé en mode {args.mode}.")
    print(f"Rapport: {REPORTS_DIR / 'latest_walk_forward_report.md'}")
    print(f"Résumé CSV: {REPORTS_DIR / 'latest_walk_forward_coverage.csv'}")
    print(f"Inventaire CSV: {REPORTS_DIR / 'latest_walk_forward_inventory.csv'}")
    print(f"Périodes simulées: {REPORTS_DIR / 'latest_walk_forward_periods.csv'}")
    print(f"Benchmarks CSV: {REPORTS_DIR / 'latest_walk_forward_benchmark_comparison.csv'}")
    print(f"Journal d'exécution: {REPORTS_DIR / 'latest_run_log.csv'}")
    print(
        f"Statut: {coverage.get('status')} | "
        f"périodes utilisables: {coverage.get('usable_walk_forward_periods')} | "
        f"dates distinctes: {coverage.get('distinct_analysis_dates')}"
    )
    print(
        f"Simulation: {summary.get('status')} | "
        f"périodes simulées: {summary.get('simulated_periods')} | "
        f"base prix: {summary.get('price_return_basis')}"
    )
    print(str(summary.get("interpretation") or coverage.get("interpretation") or ""))
    return 0


def backup_command(args: argparse.Namespace) -> int:
    ensure_directories()
    backup = create_project_backup(PROJECT_ROOT, include_cache=args.include_cache)
    print("Sauvegarde créée avec succès.")
    print(f"Dossier: {backup['backup_path']}")
    print(f"Taille: {backup['total_size']} / fichiers: {backup['file_count']}")
    print("Note: la restauration automatique n’est pas activée pour éviter d’écraser vos fichiers par erreur.")
    print("Si vous voulez revenir à cette version, gardez ce dossier et demandez une restauration manuelle.")
    return 0


def list_backups_command(args: argparse.Namespace) -> int:
    ensure_directories()
    backups = list_project_backups(PROJECT_ROOT / "backups")
    if not backups:
        print("Aucune sauvegarde trouvée.")
        print("Pour en créer une: python3 main.py backup")
        return 0
    print("Sauvegardes disponibles:")
    for row in backups:
        print(f"- {row['name']} | {row['total_size']} | {row['path']}")
    return 0


def model_audit_command(args: argparse.Namespace) -> int:
    ensure_directories()
    audit = run_model_audit(REPORTS_DIR, period=args.period, mode=args.mode)
    metrics = audit.get("metrics", {})
    print("Audit du modèle créé.")
    print(f"Rapport Markdown: {REPORTS_DIR / 'latest_model_audit.md'}")
    print(f"Rapport HTML: {REPORTS_DIR / 'latest_model_audit.html'}")
    print(f"Résumé CSV: {REPORTS_DIR / 'latest_model_audit.csv'}")
    print(
        f"Santé du modèle: {metrics.get('health_status')} "
        f"({safe_float(metrics.get('health_score')) or 0:.0f}/100)"
    )
    print(
        f"Confiance de l’audit: {metrics.get('confidence')} "
        f"avec {metrics.get('sample_count', 0)} date(s) distincte(s), "
        f"dont {metrics.get('allocation_sample_count', 0)} avec allocation exploitable."
    )
    print(f"Mode audité: {metrics.get('mode') or args.mode}")
    return 0


def full_audit_command(args: argparse.Namespace) -> int:
    ensure_directories()
    if args.monthly_capital is not None and args.monthly_capital <= 0:
        print("Le capital mensuel optionnel doit être positif.")
        return 1
    audit = run_full_audit(
        reports_dir=REPORTS_DIR,
        data_dir=DATA_DIR,
        period=args.period,
        years=args.years,
        mode=args.mode,
        monthly_capital=args.monthly_capital,
        refresh_market_data=args.refresh_market_data,
    )
    metrics = audit.get("metrics", {})
    print("Audit maître créé.")
    print(f"Rapport Markdown: {REPORTS_DIR / 'latest_full_audit.md'}")
    print(f"Rapport HTML: {REPORTS_DIR / 'latest_full_audit.html'}")
    print(f"Résumé CSV: {REPORTS_DIR / 'latest_full_audit_summary.csv'}")
    print(
        f"Statut critère 7: {metrics.get('criterion7_status')} "
        f"({safe_float(metrics.get('criterion7_score')) or 0:.0f}/100)"
    )
    print(
        f"Cotisation mensuelle utilisée pour le backtest: "
        f"{safe_float(metrics.get('selected_monthly_capital')) or 0:.2f} $ "
        f"({(metrics.get('contribution_estimate') or {}).get('source')})"
    )
    if metrics.get("backtest_error"):
        print(f"Note: backtest non disponible: {metrics.get('backtest_error')}")
    return 0


def improvement_audit_command(args: argparse.Namespace) -> int:
    ensure_directories()
    create_model_tuning_template(CONFIG_DIR / "model_tuning.yaml")
    audit = run_improvement_audit(REPORTS_DIR, CONFIG_DIR, DATA_DIR, period=args.period, mode=args.mode)
    summary = audit.get("summary", {})
    print("Audit d’amélioration créé.")
    print(f"Rapport Markdown: {REPORTS_DIR / 'latest_improvement_suggestions.md'}")
    print(f"Rapport HTML: {REPORTS_DIR / 'latest_improvement_suggestions.html'}")
    print(f"Suggestions CSV: {REPORTS_DIR / 'latest_improvement_suggestions.csv'}")
    print(
        f"Mode audité: {summary.get('mode') or args.mode} | "
        f"Suggestions SAFE applicables: {summary.get('safe_auto_applicable_count', 0)} | "
        f"Statut: {summary.get('status', 'N/D')}"
    )
    return 0


def apply_safe_tuning_command(args: argparse.Namespace) -> int:
    ensure_directories()
    create_model_tuning_template(CONFIG_DIR / "model_tuning.yaml")
    result = apply_safe_tuning(REPORTS_DIR, CONFIG_DIR, DATA_DIR, mode=args.mode)
    print("Application sécuritaire du tuning terminée.")
    print(f"Ajustements appliqués: {len(result.get('applied', []))}")
    if not result.get("applied"):
        print(result.get("message") or "Aucun ajustement SAFE applicable.")
    else:
        print(f"Sauvegarde créée avant modification: {result.get('backup_path')}")
        for row in result["applied"]:
            print(f"- {row['mode']} {row['parameter']}: {row['previous_value']} -> {row['new_value']}")
    print(f"Historique: {DATA_DIR / 'model_tuning_history.csv'}")
    return 0


def build_research_needed_rows_from_current_inputs(refresh_market_data: bool = False) -> list[dict[str, Any]]:
    ticker_aliases = load_ticker_aliases(CONFIG_DIR / "ticker_aliases.yaml")
    ticker_resolution_metadata: dict[str, dict[str, Any]] = {}

    positions = resolve_ticker_list(load_positions(), ticker_aliases, ticker_resolution_metadata, "config/positions.yaml")
    configured_benchmark_map = resolve_keyed_config(
        load_yaml(CONFIG_DIR / "benchmarks.yaml"),
        ticker_aliases,
        ticker_resolution_metadata,
        "config/benchmarks.yaml",
    )
    sectors = resolve_keyed_config(load_yaml(CONFIG_DIR / "sectors.yaml"), ticker_aliases, ticker_resolution_metadata, "config/sectors.yaml")
    exposures = resolve_keyed_config(load_yaml(CONFIG_DIR / "exposures.yaml"), ticker_aliases, ticker_resolution_metadata, "config/exposures.yaml")
    watchlist_items = load_and_resolve_universe(
        lambda: load_watchlist(CONFIG_DIR / "watchlist.yaml", DATA_DIR / "watchlist.csv"),
        ticker_aliases,
        ticker_resolution_metadata,
        "watchlist",
    )
    market_universe = load_and_resolve_universe(
        lambda: load_market_universe(CONFIG_DIR / "market_scanner.yaml", DATA_DIR / "market_universe.csv"),
        ticker_aliases,
        ticker_resolution_metadata,
        "market_universe",
    )
    raw_portfolio_rows = load_portfolio(DATA_DIR / "portfolio.csv")
    raw_portfolio_transaction_rows = load_portfolio_transactions(DATA_DIR / "portfolio_transactions.csv")
    portfolio_rows = resolve_portfolio_rows(
        raw_portfolio_rows,
        ticker_aliases,
        ticker_resolution_metadata,
        "data/portfolio.csv",
    )
    portfolio_transaction_rows = resolve_portfolio_transaction_rows(
        raw_portfolio_transaction_rows,
        ticker_aliases,
        ticker_resolution_metadata,
        "data/portfolio_transactions.csv",
    )
    portfolio_lot_rows = resolve_portfolio_lot_rows(
        raw_portfolio_rows,
        ticker_aliases,
        ticker_resolution_metadata,
        "data/portfolio.csv",
    )
    manual_inputs = resolve_manual_inputs(
        load_friendly_manual_inputs(DATA_DIR / "manual_inputs_friendly.txt"),
        ticker_aliases,
        ticker_resolution_metadata,
        "data/manual_inputs_friendly.txt",
    )
    proxy_corrections = load_proxy_corrections(CONFIG_DIR / "proxy_corrections.yaml")

    owned_tickers = {row["ticker"] for row in portfolio_rows}
    core_tickers = sorted((owned_tickers | {"VFV.TO"}) if owned_tickers else (set(positions) | {"VFV.TO"}))
    configured_unowned_tickers = set(positions) - set(core_tickers)
    watchlist_tickers = sorted(
        (set(watchlist_items.keys()) | configured_unowned_tickers) - set(core_tickers) - set(market_universe.keys()) - {"VFV.TO"}
    )
    market_tickers = sorted(set(market_universe.keys()) - set(core_tickers) - {"VFV.TO"})
    all_tickers = sorted(set(core_tickers) | set(watchlist_tickers) | set(market_tickers))

    research_inputs = load_research_report_inputs(
        BNCD_MORNINGSTAR_DIR,
        RESEARCH_REPORTS_DIR / "research_index.csv",
        known_tickers=all_tickers,
    )
    external_sectors, external_exposures = metadata_to_sector_exposure(market_universe)
    combined_sectors = enrich_sector_map({**external_sectors, **sectors}, {}, all_tickers)
    combined_exposures = {**external_exposures, **exposures}
    benchmark_map, benchmark_sources = enrich_benchmark_map(configured_benchmark_map, all_tickers)

    fetcher = MarketDataFetcher()
    market_data, benchmark_data, _ = fetcher.fetch_all(all_tickers, benchmark_map, refresh=refresh_market_data)
    combined_sectors = enrich_sector_map(combined_sectors, market_data, all_tickers)
    combined_exposures = enrich_exposure_map(combined_exposures, market_data, all_tickers)

    portfolio_currencies = [infer_quote_currency(row["ticker"], market_data.get(row["ticker"], {}).get("currency")) for row in portfolio_rows]
    portfolio_currencies.extend(
        str(row.get("average_cost_currency") or row.get("acquisition_value_currency") or "").upper()
        for row in portfolio_rows
        if row.get("average_cost_currency") or row.get("acquisition_value_currency")
    )
    fx_rates_to_cad = fetcher.fetch_fx_rates_to_cad(portfolio_currencies, refresh=refresh_market_data)
    portfolio_rows = enrich_portfolio_with_market_data(portfolio_rows, market_data, fx_rates_to_cad)
    weighted_portfolio, _ = add_position_weights(portfolio_rows)
    weights = position_weight_map(weighted_portfolio)
    current_values = {row["ticker"]: safe_float(row.get("current_value")) or 0.0 for row in weighted_portfolio}
    portfolio_details = {row["ticker"]: row for row in weighted_portfolio}

    core_sectors = enrich_sector_map(sectors, market_data, core_tickers)
    core_exposures = enrich_exposure_map(exposures, market_data, core_tickers)
    core_analyses = build_position_analyses(
        tickers=core_tickers,
        manual_inputs=manual_inputs,
        market_data=market_data,
        benchmark_data=benchmark_data,
        benchmark_map=benchmark_map,
        benchmark_sources=benchmark_sources,
        sectors=core_sectors,
        exposures=core_exposures,
        weights=weights,
        current_values=current_values,
        portfolio_details=portfolio_details,
        ticker_resolution_metadata=ticker_resolution_metadata,
        research_inputs=research_inputs,
        proxy_corrections=proxy_corrections,
    )
    watchlist_analyses = build_position_analyses(
        tickers=watchlist_tickers,
        manual_inputs=manual_inputs,
        market_data=market_data,
        benchmark_data=benchmark_data,
        benchmark_map=benchmark_map,
        benchmark_sources=benchmark_sources,
        sectors=combined_sectors,
        exposures=combined_exposures,
        weights={},
        current_values={},
        ticker_resolution_metadata=ticker_resolution_metadata,
        research_inputs=research_inputs,
        proxy_corrections=proxy_corrections,
    )
    market_analyses = build_position_analyses(
        tickers=market_tickers,
        manual_inputs=manual_inputs,
        market_data=market_data,
        benchmark_data=benchmark_data,
        benchmark_map=benchmark_map,
        benchmark_sources=benchmark_sources,
        sectors=combined_sectors,
        exposures=combined_exposures,
        weights={},
        current_values={},
        ticker_resolution_metadata=ticker_resolution_metadata,
        research_inputs=research_inputs,
        proxy_corrections=proxy_corrections,
    )
    rows = research_needed_rows_from_analysis_rows(
        {
            "CORE_PORTFOLIO": core_analyses,
            "WATCHLIST": watchlist_analyses,
            "MARKET_SCANNER": market_analyses,
        },
        existing_reports=research_inputs,
    )
    latest_qualitative_rows = [
        row for row in research_needed_rows_from_reports(REPORTS_DIR) if "QUALITATIVE" in str(row.get("need_type") or "")
    ]
    return merge_research_needed_rows(rows, latest_qualitative_rows)


def merge_research_needed_rows(
    current_rows: list[dict[str, Any]],
    latest_qualitative_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    priority_rank = {"HIGH": 3, "MEDIUM": 2, "LOW": 1, "": 0}
    merged = {str(row.get("ticker") or ""): dict(row) for row in current_rows}
    for row in latest_qualitative_rows:
        ticker = str(row.get("ticker") or "")
        if not ticker:
            continue
        existing = merged.get(ticker)
        if not existing:
            inserted = dict(row)
            inserted["ticker_potential_score"] = 0.0
            merged[ticker] = inserted
            continue
        existing_types = {part for part in str(existing.get("need_type") or "").split("+") if part}
        row_types = {part for part in str(row.get("need_type") or "").split("+") if part}
        if existing_types == {"QUALITATIVE"} and row_types == {"QUALITATIVE"}:
            if priority_rank.get(str(row.get("priority") or ""), 0) >= priority_rank.get(str(existing.get("priority") or ""), 0):
                replacement = dict(row)
                replacement["ticker_potential_score"] = safe_float(existing.get("ticker_potential_score")) or 0.0
                merged[ticker] = replacement
            continue
        combined_types = sorted(existing_types | row_types)
        existing["need_type"] = "+".join(combined_types)
        if priority_rank.get(str(row.get("priority") or ""), 0) > priority_rank.get(str(existing.get("priority") or ""), 0):
            existing["priority"] = row.get("priority")
        existing["reason"] = _combine_sentences(existing.get("reason"), row.get("reason"))
        existing["suggested_action"] = _combine_sentences(existing.get("suggested_action"), row.get("suggested_action"))
        if not existing.get("suggested_file_name") and row.get("suggested_file_name"):
            existing["suggested_file_name"] = row.get("suggested_file_name")
    rank_for_sort = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    return sorted(
        merged.values(),
        key=lambda row: (
            -(safe_float(row.get("ticker_potential_score")) or 0.0),
            rank_for_sort.get(str(row.get("priority") or ""), 9),
            0 if str(row.get("universe")) == "CORE_PORTFOLIO" else 1,
            -(safe_float(row.get("missing_critical_count")) or 0.0),
            0 if "QUALITATIVE" in str(row.get("need_type") or "") else 1,
            str(row.get("ticker") or ""),
        ),
    )


def _combine_sentences(first: Any, second: Any) -> str:
    parts = []
    for value in [first, second]:
        text = str(value or "").strip()
        if text and text not in parts:
            parts.append(text)
    return " ".join(parts)


def clear_proxy_calibration_command(args: argparse.Namespace) -> int:
    ensure_directories()
    path = DATA_DIR / "proxy_calibration.csv"
    if not path.exists():
        create_proxy_calibration_template(path)
        print(f"Fichier créé: {path}")
        return 0
    cleared = clear_proxy_calibration_values(path)
    print(f"Calibration vidée: {path}")
    print(f"Lignes nettoyées: {cleared}")
    print("La structure du fichier est conservée; seules les vraies valeurs, sources, dates et notes ont été effacées.")
    return 0


def research_status_command(args: argparse.Namespace) -> int:
    ensure_directories()
    create_research_report_scaffold()
    rows = research_status_rows(
        BNCD_MORNINGSTAR_DIR,
        RESEARCH_REPORTS_DIR / "research_index.csv",
        known_tickers=load_known_research_tickers(),
    )
    output_path = REPORTS_DIR / "latest_research_status.csv"
    write_research_status_csv(output_path, rows)
    print(f"Dossier vérifié: {BNCD_MORNINGSTAR_DIR}")
    print(f"Rapport créé: {output_path}")
    if not rows:
        print("Aucun PDF/TXT/MD trouvé dans le dossier de rapports.")
        return 0

    ready_count = sum(1 for row in rows if row.get("status") == "READY")
    visible_count = len(rows)
    print(f"Fichiers visibles: {visible_count}")
    print(f"Fichiers prêts à être utilisés: {ready_count}")
    print("État des fichiers:")
    for row in rows[: max(1, args.limit)]:
        ticker = row.get("ticker_detected") or "ticker non détecté"
        fields = row.get("extracted_fields") or "aucun champ détecté"
        quality = row.get("text_quality_status") or "qualité inconnue"
        method = row.get("extraction_method") or "lecteur inconnu"
        print(f"- {row['file_name']}: {row['status']} | {ticker} | {quality}/{method} | {fields}")
    return 0


def health_check_command(args: argparse.Namespace) -> int:
    ensure_directories()
    create_research_report_scaffold()
    run_id = make_run_id("health-check")
    schema_rows = (
        repair_safe_csv_schemas(
            PROJECT_ROOT,
            skip_portfolio_repair=args.skip_portfolio_repair,
        )
        if args.repair_safe
        else validate_csv_schemas(PROJECT_ROOT)
    )
    schema_path = REPORTS_DIR / "latest_schema_repair.csv"
    write_csv_records(schema_path, schema_rows, SCHEMA_REPAIR_COLUMNS)
    cache_rows = run_cache_maintenance(CACHE_DIR, repair_safe=args.repair_safe)
    cache_path = REPORTS_DIR / "latest_cache_health.csv"
    write_csv_records(cache_path, cache_rows, CACHE_HEALTH_COLUMNS)
    rows = run_health_check(
        PROJECT_ROOT,
        known_tickers=load_known_research_tickers(),
        repair_safe=args.repair_safe,
        schema_rows=schema_rows,
        cache_rows=cache_rows,
    )
    output_path = REPORTS_DIR / "latest_health_check.csv"
    write_csv_records(output_path, rows, HEALTH_CHECK_COLUMNS)
    write_csv_records(
        REPORTS_DIR / "latest_storage_health.csv",
        [row for row in rows if str(row.get("check") or "").startswith("storage:")],
        HEALTH_CHECK_COLUMNS,
    )
    run_log_rows = build_health_check_run_log(
        run_id=run_id,
        repair_safe=args.repair_safe,
        health_rows=rows,
        cache_rows=cache_rows,
    )
    write_csv_records(REPORTS_DIR / "latest_run_log.csv", run_log_rows, RUN_LOG_COLUMNS)
    append_run_log_history(DATA_DIR / "run_log_history.csv", run_log_rows)
    summary = health_summary(rows)
    print(f"Health-check créé: {output_path}")
    print(f"Détail schémas CSV: {schema_path}")
    print(f"Santé du cache: {cache_path}")
    print(f"Journal d'exécution: {REPORTS_DIR / 'latest_run_log.csv'}")
    print(
        "Résumé: "
        f"PASS={summary.get('PASS', 0)} | "
        f"WARN={summary.get('WARN', 0)} | "
        f"FAIL={summary.get('FAIL', 0)} | "
        f"INFO={summary.get('INFO', 0)}"
    )
    alerts = [row for row in rows if row.get("status") in {"FAIL", "WARN"}]
    if not alerts:
        print("Aucune alerte majeure détectée.")
        return 0
    print("Alertes principales:")
    for row in alerts[: max(1, args.limit)]:
        print(f"- {row['status']} | {row['check']}: {row['details']} Action: {row['suggested_action']}")
    return 1 if any(row.get("status") == "FAIL" for row in alerts) else 0


def run_analysis(
    capital: float,
    mode: str = "rational-aggressive",
    refresh_market_data: bool = False,
    validation_warnings: list[str] | None = None,
    run_purpose: str | None = None,
) -> dict[str, Any]:
    # CONTEXT ENRICHMENT ORDER — DO NOT REORDER WITHOUT REVIEWING DEPENDENCIES
    # Each pass may read keys written by earlier passes. The order is:
    #  1. apply_history_context              -> sets previous_* keys
    #  2. apply_history_sell_discipline      -> reads history/trend keys
    #  3. apply_winner_protection            -> reads thesis/liquidation history
    #  4. apply_cycle_bubble_context         -> reads thesis, valuation and market data
    #  5. apply_cash_flow_quality_context    -> writes cash-flow quality keys
    #  6. apply_shareholder_discipline_context -> reads cash-flow quality keys
    #  7. apply_long_term_durability_context -> reads quality/conviction profile
    #  8. apply_market_growth_thesis_context -> reads sector/growth evidence
    #  9. apply_quality_drawdown_context     -> reads thesis_status and liquidation_status
    # 10. apply_market_regime_context        -> writes regime sizing context
    # 11. apply_sector_euphoria_context      -> reads market regime context
    # 12. apply_double_counting_context      -> reads overlapping quality/growth signals
    # 13. apply_hidden_cluster_guardrails    -> reads sector/factor exposures
    # 14. refresh_add_and_opportunity_context -> FINAL add/VFV decision refresh
    #
    # Changing this order can silently alter allocations. Document any change in DECISIONS.md.
    run_id = make_run_id("analyze", mode)
    run_timestamp = datetime.now().isoformat(timespec="seconds")
    resolved_run_purpose = resolve_analysis_run_purpose(run_purpose, capital=capital)
    static_input_audit = audit_static_critical_inputs(
        PROJECT_ROOT,
        capital=capital,
        run_purpose=resolved_run_purpose,
        mode=mode,
    )
    dependency_payload = dependency_environment(PROJECT_ROOT / "requirements.lock")
    tracked_git_payload = git_tracked_state(PROJECT_ROOT)
    approved_config_active = bool(
        str(load_yaml(CONFIG_DIR / "baseline.yaml").get("approved_config_fingerprint") or "").strip()
    ) and not any(
        row.get("code") == "BASELINE_CONFIG_FINGERPRINT_MISMATCH"
        for row in static_input_audit.get("hard_failures", [])
    )
    baseline_metadata = baseline_observation_metadata(
        run_timestamp=run_timestamp,
        run_purpose=resolved_run_purpose,
        capital=capital,
        config_path=CONFIG_DIR / "baseline.yaml",
        critical_input_passed=not bool(static_input_audit.get("hard_failures")),
        approved_config_active=approved_config_active,
        dependency_status=str(dependency_payload.get("dependency_status") or "UNKNOWN"),
        git_tracked_worktree_clean=tracked_git_payload.get("git_tracked_worktree_clean") is True,
        git_tracked_diff_fingerprint=str(tracked_git_payload.get("git_tracked_diff_fingerprint") or ""),
    )
    static_input_audit = merge_input_audits(
        static_input_audit,
        audit_baseline_environment_authority(baseline_metadata),
    )
    if static_input_audit.get("hard_failures"):
        write_failed_run_audit(
            reports_dir=REPORTS_DIR,
            project_root=PROJECT_ROOT,
            run_id=run_id,
            run_timestamp=run_timestamp,
            run_purpose=resolved_run_purpose,
            mode=mode,
            capital=capital,
            input_audit=static_input_audit,
        )
        raise CriticalInputError(static_input_audit)
    effective_validation_warnings = list(validation_warnings or [])
    effective_validation_warnings.extend(
        str(row.get("message") or "") for row in static_input_audit.get("advisories", [])
    )
    try:
        cache_health_rows = run_cache_maintenance(CACHE_DIR, repair_safe=True)
        circuit_breaker_reset_row = None
        if refresh_market_data:
            circuit_breaker_reset_row = reset_expired_market_circuit_breakers(CACHE_DIR)
            cache_health_rows.append(circuit_breaker_reset_row)
        ticker_aliases = load_ticker_aliases(CONFIG_DIR / "ticker_aliases.yaml")
        ticker_resolution_metadata: dict[str, dict[str, Any]] = {}

        positions = resolve_ticker_list(load_positions(), ticker_aliases, ticker_resolution_metadata, "config/positions.yaml")
        configured_benchmark_map = resolve_keyed_config(
            load_yaml(CONFIG_DIR / "benchmarks.yaml"),
            ticker_aliases,
            ticker_resolution_metadata,
            "config/benchmarks.yaml",
        )
        sectors = resolve_keyed_config(load_yaml(CONFIG_DIR / "sectors.yaml"), ticker_aliases, ticker_resolution_metadata, "config/sectors.yaml")
        exposures = resolve_keyed_config(load_yaml(CONFIG_DIR / "exposures.yaml"), ticker_aliases, ticker_resolution_metadata, "config/exposures.yaml")
        watchlist_items = load_and_resolve_universe(
            lambda: load_watchlist(CONFIG_DIR / "watchlist.yaml", DATA_DIR / "watchlist.csv"),
            ticker_aliases,
            ticker_resolution_metadata,
            "watchlist",
        )
        market_universe = load_and_resolve_universe(
            lambda: load_market_universe(CONFIG_DIR / "market_scanner.yaml", DATA_DIR / "market_universe.csv"),
            ticker_aliases,
            ticker_resolution_metadata,
            "market_universe",
        )
        defensive_etf_config = load_defensive_etf_config(CONFIG_DIR / "defensive_etfs.yaml")
        defensive_etf_tickers = defensive_etf_tickers_for_mode(defensive_etf_config, mode)
        market_regime_config = load_market_regime_config(CONFIG_DIR / "market_regime.yaml")

        raw_portfolio_rows = load_portfolio(DATA_DIR / "portfolio.csv")
        raw_portfolio_transaction_rows = load_portfolio_transactions(DATA_DIR / "portfolio_transactions.csv")
        portfolio_rows = resolve_portfolio_rows(
            raw_portfolio_rows,
            ticker_aliases,
            ticker_resolution_metadata,
            "data/portfolio.csv",
        )
        portfolio_lot_rows = resolve_portfolio_lot_rows(
            raw_portfolio_rows,
            ticker_aliases,
            ticker_resolution_metadata,
            "data/portfolio.csv",
        )
        portfolio_transaction_rows = resolve_portfolio_transaction_rows(
            raw_portfolio_transaction_rows,
            ticker_aliases,
            ticker_resolution_metadata,
            "data/portfolio_transactions.csv",
        )
        legacy_account_locations = []
        if (DATA_DIR / "account_locations.csv").exists():
            legacy_account_locations = resolve_account_location_rows(
                load_account_locations(DATA_DIR / "account_locations.csv"),
                ticker_aliases,
                ticker_resolution_metadata,
                "data/account_locations.csv",
            )
        manual_inputs = resolve_manual_inputs(
            load_friendly_manual_inputs(DATA_DIR / "manual_inputs_friendly.txt"),
            ticker_aliases,
            ticker_resolution_metadata,
            "data/manual_inputs_friendly.txt",
        )
        proxy_corrections = load_proxy_corrections(CONFIG_DIR / "proxy_corrections.yaml")
        proxy_calibration_inputs = load_proxy_calibration_inputs(DATA_DIR / "proxy_calibration.csv")

        owned_tickers = {row["ticker"] for row in portfolio_rows}
        core_tickers = sorted((owned_tickers | {"VFV.TO"}) if owned_tickers else (set(positions) | {"VFV.TO"}))
        configured_unowned_tickers = set(positions) - set(core_tickers)
        watchlist_tickers = sorted(
            (set(watchlist_items.keys()) | configured_unowned_tickers) - set(core_tickers) - set(market_universe.keys()) - {"VFV.TO"}
        )
        market_tickers = sorted(set(market_universe.keys()) - set(core_tickers) - {"VFV.TO"})
        discovery_exclusions = expand_exclusions_with_alias_inputs(
            set(core_tickers) | set(watchlist_items.keys()) | set(market_universe.keys()) | {"VFV.TO"},
            ticker_aliases,
        )
        discovery_universe = load_and_resolve_universe(
            lambda: load_auto_discovery_universe(
                CONFIG_DIR / "market_scanner.yaml",
                DATA_DIR / "discovery_universe_cache.csv",
                discovery_exclusions,
                refresh=refresh_market_data,
            ),
            ticker_aliases,
            ticker_resolution_metadata,
            "discovery_universe",
        )
        discovery_universe = {ticker: row for ticker, row in discovery_universe.items() if ticker not in discovery_exclusions}
        discovery_tickers = sorted(set(discovery_universe.keys()) - set(core_tickers) - set(watchlist_items.keys()) - set(market_universe.keys()) - {"VFV.TO"})
        all_tickers = sorted(
            set(core_tickers)
            | set(watchlist_tickers)
            | set(market_tickers)
            | set(discovery_tickers)
            | set(defensive_etf_tickers)
        )
        ticker_memory = load_ticker_memory(DATA_DIR / "ticker_memory.csv")
        research_inputs = load_research_report_inputs(
            BNCD_MORNINGSTAR_DIR,
            RESEARCH_REPORTS_DIR / "research_index.csv",
            known_tickers=all_tickers,
        )
        external_sectors, external_exposures = metadata_to_sector_exposure({**market_universe, **discovery_universe})
        combined_sectors = {**external_sectors, **sectors}
        combined_exposures = {**external_exposures, **exposures}
        benchmark_map, benchmark_sources = enrich_benchmark_map(configured_benchmark_map, all_tickers)

        fetcher = MarketDataFetcher()
        market_data, benchmark_data, market_gaps = fetcher.fetch_all(all_tickers, benchmark_map, refresh=refresh_market_data)
        refresh_delay_info = getattr(fetcher, "last_fetch_all_delay_info", {}) or {}
        market_regime_data = fetch_market_regime_data(fetcher, market_regime_config, refresh=refresh_market_data)
        market_regime = compute_market_regime(market_regime_data, market_regime_config)

        portfolio_currencies = [infer_quote_currency(row["ticker"], market_data.get(row["ticker"], {}).get("currency")) for row in portfolio_rows]
        portfolio_currencies.extend(
            str(row.get("average_cost_currency") or row.get("acquisition_value_currency") or "").upper()
            for row in [*portfolio_rows, *portfolio_lot_rows]
            if row.get("average_cost_currency") or row.get("acquisition_value_currency")
        )
        portfolio_currencies.extend(portfolio_transaction_currencies(portfolio_transaction_rows))
        fx_rates_to_cad = fetcher.fetch_fx_rates_to_cad(portfolio_currencies, refresh=refresh_market_data)
        portfolio_rows = enrich_portfolio_with_market_data(portfolio_rows, market_data, fx_rates_to_cad)
        portfolio_lot_rows = enrich_portfolio_with_market_data(portfolio_lot_rows, market_data, fx_rates_to_cad)
        runtime_input_audit = audit_runtime_critical_inputs(
            portfolio_rows=portfolio_rows,
            market_data=market_data,
            capital=capital,
            run_purpose=resolved_run_purpose,
        )
        critical_input_audit = merge_input_audits(static_input_audit, runtime_input_audit)
        baseline_metadata = baseline_observation_metadata(
            run_timestamp=run_timestamp,
            run_purpose=resolved_run_purpose,
            capital=capital,
            config_path=CONFIG_DIR / "baseline.yaml",
            critical_input_passed=not bool(critical_input_audit.get("hard_failures")),
            approved_config_active=approved_config_active,
            dependency_status=str(dependency_payload.get("dependency_status") or "UNKNOWN"),
            git_tracked_worktree_clean=tracked_git_payload.get("git_tracked_worktree_clean") is True,
            git_tracked_diff_fingerprint=str(tracked_git_payload.get("git_tracked_diff_fingerprint") or ""),
        )
        if critical_input_audit.get("hard_failures"):
            write_failed_run_audit(
                reports_dir=REPORTS_DIR,
                project_root=PROJECT_ROOT,
                run_id=run_id,
                run_timestamp=run_timestamp,
                run_purpose=resolved_run_purpose,
                mode=mode,
                capital=capital,
                input_audit=critical_input_audit,
            )
            raise CriticalInputError(critical_input_audit)
        effective_validation_warnings.extend(
            str(row.get("message") or "") for row in runtime_input_audit.get("advisories", [])
        )
        effective_validation_warnings = list(dict.fromkeys(item for item in effective_validation_warnings if item))
        portfolio_change_rows, portfolio_change_history_rows, portfolio_change_summary_rows = update_portfolio_change_history(
            portfolio_lot_rows,
            DATA_DIR / "portfolio_state_snapshot.csv",
            DATA_DIR / "portfolio_change_history.csv",
        )
        vfv_payload = market_data.get("VFV.TO") or {}
        sp500_proxy_return_price = safe_float(
            vfv_payload.get("total_return_price")
            or vfv_payload.get("adjusted_current_price")
            or vfv_payload.get("current_price")
        )
        portfolio_inferred_transaction_rows = update_inferred_transactions_from_changes(
            portfolio_change_history_rows,
            DATA_DIR / "portfolio_inferred_transactions.csv",
            sp500_proxy_price=sp500_proxy_return_price,
            sp500_proxy_price_basis=str(vfv_payload.get("total_return_basis") or "PRICE_CLOSE"),
        )
        portfolio_transaction_report_rows = build_portfolio_transaction_report_rows(portfolio_transaction_rows, fx_rates_to_cad)
        portfolio_transaction_summary_rows = summarize_portfolio_transactions(portfolio_transaction_report_rows)
        weighted_portfolio, _ = add_position_weights(portfolio_rows)
        account_locations = account_locations_from_portfolio_rows(portfolio_lot_rows, legacy_account_locations)
        weights = position_weight_map(weighted_portfolio)
        current_values = {row["ticker"]: safe_float(row.get("current_value")) or 0.0 for row in weighted_portfolio}
        portfolio_details = {row["ticker"]: row for row in weighted_portfolio}

        core_sectors = enrich_sector_map(sectors, market_data, core_tickers)
        core_exposures = enrich_exposure_map(exposures, market_data, core_tickers)
        combined_sectors = enrich_sector_map(combined_sectors, market_data, all_tickers)
        combined_exposures = enrich_exposure_map(combined_exposures, market_data, all_tickers)
        core_sectors = apply_ticker_memory_to_sector_map(core_sectors, core_tickers, ticker_memory)
        core_exposures = apply_ticker_memory_to_exposure_map(core_exposures, core_tickers, ticker_memory)
        combined_sectors = apply_ticker_memory_to_sector_map(combined_sectors, all_tickers, ticker_memory)
        combined_exposures = apply_ticker_memory_to_exposure_map(combined_exposures, all_tickers, ticker_memory)
        previous_snapshot = load_previous_snapshot(
            REPORTS_DIR,
            current_model_rules_version=MODEL_RULES_VERSION,
            analysis_mode=mode,
        )

        portfolio_risk = compute_portfolio_risk(weighted_portfolio, core_sectors, core_exposures)
        analyses = build_position_analyses(
            tickers=core_tickers,
            manual_inputs=manual_inputs,
            market_data=market_data,
            benchmark_data=benchmark_data,
            benchmark_map=benchmark_map,
            benchmark_sources=benchmark_sources,
            sectors=core_sectors,
            exposures=core_exposures,
            weights=weights,
            current_values=current_values,
            portfolio_details=portfolio_details,
            ticker_resolution_metadata=ticker_resolution_metadata,
            research_inputs=research_inputs,
            proxy_corrections=proxy_corrections,
        )
        watchlist_analyses = build_position_analyses(
            tickers=watchlist_tickers,
            manual_inputs=manual_inputs,
            market_data=market_data,
            benchmark_data=benchmark_data,
            benchmark_map=benchmark_map,
            benchmark_sources=benchmark_sources,
            sectors=combined_sectors,
            exposures=combined_exposures,
            weights={},
            current_values={},
            ticker_resolution_metadata=ticker_resolution_metadata,
            research_inputs=research_inputs,
            proxy_corrections=proxy_corrections,
        )
        for ticker, analysis in watchlist_analyses.items():
            analysis.update(watchlist_items.get(ticker, {}))
            analysis["universe"] = "WATCHLIST"

        market_analyses = build_position_analyses(
            tickers=market_tickers,
            manual_inputs=manual_inputs,
            market_data=market_data,
            benchmark_data=benchmark_data,
            benchmark_map=benchmark_map,
            benchmark_sources=benchmark_sources,
            sectors=combined_sectors,
            exposures=combined_exposures,
            weights={},
            current_values={},
            ticker_resolution_metadata=ticker_resolution_metadata,
            research_inputs=research_inputs,
            proxy_corrections=proxy_corrections,
        )
        for ticker, analysis in market_analyses.items():
            analysis.update(market_universe.get(ticker, {}))
            analysis["universe"] = "MARKET_SCANNER"

        discovery_analyses = build_position_analyses(
            tickers=discovery_tickers,
            manual_inputs=manual_inputs,
            market_data=market_data,
            benchmark_data=benchmark_data,
            benchmark_map=benchmark_map,
            benchmark_sources=benchmark_sources,
            sectors=combined_sectors,
            exposures=combined_exposures,
            weights={},
            current_values={},
            ticker_resolution_metadata=ticker_resolution_metadata,
            research_inputs=research_inputs,
            proxy_corrections=proxy_corrections,
        )
        for ticker, analysis in discovery_analyses.items():
            analysis.update(discovery_universe.get(ticker, {}))
            analysis["universe"] = "DISCOVERY_IDEAS"

        defensive_etf_candidates = build_defensive_etf_candidates(defensive_etf_config, mode, market_data)
        defensive_validation_analyses = defensive_etf_analysis_map(defensive_etf_candidates)

        apply_history_context(analyses, previous_snapshot)
        apply_history_context(watchlist_analyses, previous_snapshot)
        apply_history_context(market_analyses, previous_snapshot)
        apply_history_context(discovery_analyses, previous_snapshot)
        apply_history_sell_discipline(analyses)
        apply_history_sell_discipline(watchlist_analyses)
        apply_history_sell_discipline(market_analyses)
        apply_history_sell_discipline(discovery_analyses)
        apply_winner_protection(analyses, previous_snapshot)
        apply_cycle_bubble_context(analyses, watchlist_analyses, market_analyses, discovery_analyses, portfolio_risk)
        apply_cash_flow_quality_context(analyses, watchlist_analyses, market_analyses, discovery_analyses)
        apply_shareholder_discipline_context(analyses, watchlist_analyses, market_analyses, discovery_analyses)
        apply_long_term_durability_context(analyses, watchlist_analyses, market_analyses, discovery_analyses)
        apply_market_growth_thesis_context(analyses, watchlist_analyses, market_analyses, discovery_analyses)
        apply_quality_drawdown_context(analyses, watchlist_analyses, market_analyses, discovery_analyses)
        apply_market_regime_context(analyses, market_regime, mode=mode, universe="CORE_PORTFOLIO")
        apply_market_regime_context(watchlist_analyses, market_regime, mode=mode, universe="WATCHLIST")
        apply_market_regime_context(market_analyses, market_regime, mode=mode, universe="MARKET_SCANNER")
        apply_market_regime_context(discovery_analyses, market_regime, mode=mode, universe="DISCOVERY_IDEAS")
        apply_sector_euphoria_context(analyses, market_regime, mode=mode, universe="CORE_PORTFOLIO")
        apply_sector_euphoria_context(watchlist_analyses, market_regime, mode=mode, universe="WATCHLIST")
        apply_sector_euphoria_context(market_analyses, market_regime, mode=mode, universe="MARKET_SCANNER")
        apply_sector_euphoria_context(discovery_analyses, market_regime, mode=mode, universe="DISCOVERY_IDEAS")
        apply_double_counting_context(analyses, watchlist_analyses, market_analyses, discovery_analyses, mode=mode)
        apply_hidden_cluster_guardrails(analyses, watchlist_analyses, market_analyses, discovery_analyses, portfolio_risk, mode=mode)
        # Eligibility and VFV opportunity cost must be refreshed after every
        # context pass, because those passes can change sizing, risk, or monitoring
        # inputs used by the final add decision.
        refresh_add_and_opportunity_context(analyses, watchlist_analyses, market_analyses, discovery_analyses)

        for ticker, analysis in watchlist_analyses.items():
            analysis.update(classify_watchlist_analysis(analysis))
            apply_external_superiority_gate(analysis, analyses)

        for ticker, analysis in market_analyses.items():
            analysis.update(classify_market_candidate(analysis))
            apply_external_superiority_gate(analysis, analyses)

        for ticker, analysis in discovery_analyses.items():
            analysis.update(classify_discovery_idea(analysis))
            apply_external_superiority_gate(analysis, analyses)
        apply_external_etf_candidate_context(mode, portfolio_risk, watchlist_analyses, market_analyses, discovery_analyses)
        discovery_maintenance_rows = build_discovery_maintenance_rows(discovery_analyses, discovery_universe)

        tax_report_initial = compute_tax_location_report(account_locations, weighted_portfolio, analyses, core_exposures)
        tax_penalties = tax_penalty_map(tax_report_initial)
        allocation_analyses = allocation_universe_for_mode(
            mode,
            analyses,
            watchlist_analyses,
            market_analyses,
            discovery_analyses,
        )
        apply_deep_averaging_down_context(allocation_analyses, mode=mode)
        # Second ETF role check is intentional: allocation_universe_for_mode() can
        # include external/defensive ETF candidates, so this final guard prevents
        # ETF holdings from being sized like individual stocks.
        for ticker, analysis in allocation_analyses.items():
            if ticker == "VFV.TO":
                apply_vfv_benchmark_role(analysis)
                continue
            if is_etf_asset_analysis(analysis):
                if not is_external_etf_allocation_candidate(analysis):
                    apply_etf_asset_role(analysis)
                continue
            tax_penalty = tax_penalties.get(ticker, 0.0) if analysis.get("universe") == "CORE_PORTFOLIO" else 0.0
            analysis.update(compute_capital_allocation_score(analysis, portfolio_risk, tax_penalty))
        apply_allocation_stability(allocation_analyses, mode=mode)

        previous_baseline = load_previous_allocation_baseline(
            REPORTS_DIR,
            current_model_rules_version=MODEL_RULES_VERSION,
            analysis_mode=mode,
        )
        allocation_result = allocate_capital(
            capital,
            allocation_analyses,
            mode,
            defensive_etf_candidates=defensive_etf_candidates,
            previous_baseline=previous_baseline,
        )
        apply_final_decisions(allocation_analyses, allocation_result.get("allocations", []))
        allocation_sensitivity = compute_allocation_sensitivity(capital, mode, allocation_analyses, allocation_result)
        tax_report = compute_tax_location_report(account_locations, weighted_portfolio, analyses, core_exposures)
        thesis_reversal_rows = build_thesis_reversal_audit_rows(
            {
                "CORE_PORTFOLIO": analyses,
                "WATCHLIST": watchlist_analyses,
                "MARKET_SCANNER": market_analyses,
                "DISCOVERY_IDEAS": discovery_analyses,
            },
            sell_validation_checklist_rows(analyses, tax_report, active_only=False),
        )
        account_performance_rows = build_account_performance_rows(
            portfolio_lot_rows,
            market_data,
            DATA_DIR / "account_performance_history.csv",
            cash_flow_rows=portfolio_inferred_transaction_rows,
            transaction_rows=portfolio_transaction_report_rows,
        )
        stress_tests = compute_stress_tests(weighted_portfolio, core_exposures, core_sectors)
        reportable_market_gaps = [row for row in market_gaps if row.get("ticker") not in set(discovery_tickers)]
        data_gaps = merge_data_gaps(reportable_market_gaps, analyses, watchlist_analyses, market_analyses)
        _DISCOVERY_ELIGIBLE_STATUSES = {
            "ELIGIBLE_BUT_NOT_SELECTED",
            "NO_NEW_ALLOCATION",
        }
        discovery_for_validation = {
            ticker: analysis
            for ticker, analysis in discovery_analyses.items()
            if str(analysis.get("allocation_status") or analysis.get("allocation_decision") or "") in _DISCOVERY_ELIGIBLE_STATUSES
            and (safe_float(analysis.get("capital_allocation_score")) or 0.0) >= DISCOVERY_VALIDATION_PRIORITY_MIN_SCORE
        }
        validation_priority_rows = build_validation_priority_rows(
            {
                "CORE_PORTFOLIO": analyses,
                "WATCHLIST": watchlist_analyses,
                "MARKET_SCANNER": market_analyses,
                "DISCOVERY_IDEAS": discovery_for_validation,  # [DECISION 2026-07-04]
            },
            existing_reports=research_inputs,
        )
        allocation_warnings = validate_allocation_rules(
            allocation_result.get("allocations", []),
            {**allocation_analyses, **defensive_validation_analyses},
        )
        decision_quality = compute_decision_quality(
            allocation_analyses,
            allocation_result,
            portfolio_risk,
            effective_validation_warnings + allocation_warnings,
            mode=mode,
            allocation_sensitivity=allocation_sensitivity,
        )
        allocation_result["decision_quality"] = decision_quality
        annotate_allocations_with_decision_quality(allocation_result)
        allocation_change_rows = build_allocation_change_rows(
            allocation_result.get("allocations", []),
            allocation_analyses,
            previous_baseline,
        )
        proxy_calibration_report = build_proxy_calibration_report(
            [analyses, watchlist_analyses, market_analyses, discovery_analyses],
            proxy_calibration_inputs,
        )
        proxy_calibration_summary = build_proxy_calibration_summary(proxy_calibration_report)
        proxy_calibration_history_rows = update_proxy_calibration_history(
            DATA_DIR / "proxy_calibration_history.csv",
            proxy_calibration_report,
            run_id=run_id,
            mode=mode,
        )
        proxy_bias_rows = build_proxy_bias_report(proxy_calibration_history_rows)
        proxy_correction_audit_rows = build_proxy_correction_audit(proxy_corrections, proxy_bias_rows)
        ticker_memory_rows = update_ticker_memory(
            DATA_DIR / "ticker_memory.csv",
            build_ticker_memory_rows(
                {
                    "CORE_PORTFOLIO": analyses,
                    "WATCHLIST": watchlist_analyses,
                    "MARKET_SCANNER": market_analyses,
                    "DISCOVERY_IDEAS": discovery_analyses,
                },
                existing_memory=ticker_memory,
            ),
        )
        anomaly_rows = detect_analysis_anomalies(
            mode=mode,
            analyses=analyses,
            watchlist_analyses=watchlist_analyses,
            market_analyses=market_analyses,
            discovery_analyses=discovery_analyses,
            allocation_result=allocation_result,
            allocation_change_rows=allocation_change_rows,
            portfolio_risk=portfolio_risk,
            validation_priority_rows=validation_priority_rows,
        )
        anomaly_history_rows = update_anomaly_history(DATA_DIR / "anomaly_history.csv", anomaly_rows, mode=mode)
        cache_health_rows = run_cache_maintenance(CACHE_DIR, repair_safe=True)
        if circuit_breaker_reset_row:
            cache_health_rows.append(circuit_breaker_reset_row)
        full_audit_signal = compute_full_audit_signal(REPORTS_DIR, mode)
        model_audit_signal = compute_model_audit_signal(REPORTS_DIR, mode)
        tracked_git_payload = git_tracked_state(PROJECT_ROOT)
        baseline_metadata = baseline_observation_metadata(
            run_timestamp=run_timestamp,
            run_purpose=resolved_run_purpose,
            capital=capital,
            config_path=CONFIG_DIR / "baseline.yaml",
            critical_input_passed=not bool(critical_input_audit.get("hard_failures")),
            approved_config_active=approved_config_active,
            dependency_status=str(dependency_payload.get("dependency_status") or "UNKNOWN"),
            git_tracked_worktree_clean=tracked_git_payload.get("git_tracked_worktree_clean") is True,
            git_tracked_diff_fingerprint=str(tracked_git_payload.get("git_tracked_diff_fingerprint") or ""),
        )
        final_baseline_environment_audit = audit_baseline_environment_authority(baseline_metadata)
        if final_baseline_environment_audit.get("hard_failures"):
            critical_input_audit = merge_input_audits(critical_input_audit, final_baseline_environment_audit)
            write_failed_run_audit(
                reports_dir=REPORTS_DIR,
                project_root=PROJECT_ROOT,
                run_id=run_id,
                run_timestamp=run_timestamp,
                run_purpose=resolved_run_purpose,
                mode=mode,
                capital=capital,
                input_audit=critical_input_audit,
            )
            raise CriticalInputError(critical_input_audit)
        decision_manifest = build_decision_manifest(
            project_root=PROJECT_ROOT,
            run_id=run_id,
            run_timestamp=run_timestamp,
            run_purpose=resolved_run_purpose,
            mode=mode,
            capital=capital,
            analyses_by_universe={
                "CORE_PORTFOLIO": analyses,
                "WATCHLIST": watchlist_analyses,
                "MARKET_SCANNER": market_analyses,
                "DISCOVERY_IDEAS": discovery_analyses,
            },
            allocation_result=allocation_result,
            research_inputs=research_inputs,
            market_data=market_data,
            benchmark_data=benchmark_data,
            baseline_metadata=baseline_metadata,
            input_audit=critical_input_audit,
            dependency_payload=dependency_payload,
            git_state_payload=tracked_git_payload,
        )
        manifest_summary = write_decision_manifest(REPORTS_DIR, decision_manifest)
        allocation_result["baseline_identity"] = baseline_metadata
        allocation_result["decision_manifest"] = manifest_summary
        run_log_rows = build_analysis_run_log(
            run_id=run_id,
            mode=mode,
            capital=capital,
            refresh_market_data=refresh_market_data,
            universe_counts={
                "core": len(core_tickers),
                "watchlist": len(watchlist_tickers),
                "market": len(market_tickers),
                "discovery": len(discovery_tickers),
                "defensive_etf": len(defensive_etf_tickers),
            },
            validation_warnings=effective_validation_warnings,
            allocation_warnings=allocation_warnings,
            cache_health_rows=cache_health_rows,
            data_gaps=data_gaps,
            validation_priority_rows=validation_priority_rows,
            anomaly_rows=anomaly_rows,
            allocation_result=allocation_result,
            portfolio_risk=portfolio_risk,
            full_audit_signal=full_audit_signal,
            model_audit_signal=model_audit_signal,
            run_purpose=resolved_run_purpose,
            baseline_metadata=baseline_metadata,
            manifest_metadata=manifest_summary,
        )
        if circuit_breaker_reset_row:
            now = datetime.now()
            run_log_rows.append(
                {
                    "timestamp": now.isoformat(timespec="seconds"),
                    "date": now.date().isoformat(),
                    "run_id": run_id,
                    "command": "analyze",
                    "mode": mode,
                    "level": "INFO",
                    "component": "CACHE",
                    "event": "MARKET_CIRCUIT_BREAKER_RESET",
                    "ticker": "",
                    "message": str(circuit_breaker_reset_row.get("details") or "Circuit breakers marché vérifiés."),
                    "suggested_action": str(circuit_breaker_reset_row.get("suggested_action") or "Aucune action."),
                    "details": f"reset_count={circuit_breaker_reset_row.get('cleaned_count', 0)}; refresh_market_data={bool(refresh_market_data)}",
                }
            )
        if refresh_delay_info:
            now = datetime.now()
            run_log_rows.append(
                {
                    "timestamp": now.isoformat(timespec="seconds"),
                    "date": now.date().isoformat(),
                    "run_id": run_id,
                    "command": "analyze",
                    "mode": mode,
                    "level": "INFO",
                    "component": "DATA",
                    "event": "MARKET_REFRESH_INTER_TICKER_DELAY",
                    "ticker": "",
                    "message": str(refresh_delay_info.get("message") or "Délai inter-tickers actif lors du refresh."),
                    "suggested_action": "Aucune action.",
                    "details": (
                        f"delay_seconds={refresh_delay_info.get('delay_seconds')}; "
                        f"fetch_count={refresh_delay_info.get('fetch_count')}; refresh_market_data=True"
                    ),
                }
            )
        apply_run_identity_metadata(
            run_log_rows,
            run_purpose=resolved_run_purpose,
            baseline_metadata=baseline_metadata,
            manifest_metadata=manifest_summary,
        )
        walk_forward_signal = compute_walk_forward_signal(REPORTS_DIR, mode)
        instrument_profile_rows = build_instrument_profiles(
            allocation_result.get("allocations", []),
            {**analyses, **watchlist_analyses, **market_analyses, **discovery_analyses},
            cache_dir=CACHE_DIR / "instrument_profiles",
        )
        save_current_snapshot(
            REPORTS_DIR,
            mode,
            analyses,
            watchlist_analyses,
            market_analyses,
            discovery_analyses,
            run_purpose=resolved_run_purpose,
            baseline_metadata=baseline_metadata,
            manifest_reference=manifest_summary.get("manifest_reference", ""),
            manifest_fingerprint=manifest_summary.get("manifest_fingerprint", ""),
        )
        score_stability = compute_score_stability(REPORTS_DIR, mode, analyses)
        write_csv_records_mode_pair(
            REPORTS_DIR,
            "latest_score_stability.csv",
            mode,
            score_stability.get("ticker_rows", []),
            SCORE_STABILITY_COLUMNS,
        )

        _research_needed_rows = research_needed_rows_from_analysis_rows(
            {
                "CORE_PORTFOLIO": analyses,
                "WATCHLIST": watchlist_analyses,
                "MARKET_SCANNER": market_analyses,
                "DISCOVERY_IDEAS": discovery_for_validation,
            },
            existing_reports=research_inputs,
            limit=EXTERNAL_CANDIDATE_REPORT_CAP,
        )

        generate_reports(
            reports_dir=REPORTS_DIR,
            mode=mode,
            capital=capital,
            analyses=analyses,
            allocation_result=allocation_result,
            portfolio_risk=portfolio_risk,
            stress_tests=stress_tests,
            tax_report=tax_report,
            data_gaps=data_gaps,
            validation_warnings=effective_validation_warnings + allocation_warnings,
            watchlist_analyses=watchlist_analyses,
            market_analyses=market_analyses,
            market_universe=market_universe,
            discovery_analyses=discovery_analyses,
            discovery_universe=discovery_universe,
            discovery_maintenance_rows=discovery_maintenance_rows,
            proxy_calibration_report=proxy_calibration_report,
            proxy_calibration_summary=proxy_calibration_summary,
            proxy_calibration_history_rows=proxy_calibration_history_rows,
            proxy_bias_rows=proxy_bias_rows,
            proxy_correction_audit_rows=proxy_correction_audit_rows,
            allocation_change_rows=allocation_change_rows,
            allocation_sensitivity=allocation_sensitivity,
            validation_priority_rows=validation_priority_rows,
            research_needed_rows=_research_needed_rows,
            portfolio_change_rows=portfolio_change_rows,
            portfolio_change_history_rows=portfolio_change_history_rows,
            portfolio_change_summary_rows=portfolio_change_summary_rows,
            portfolio_transaction_rows=portfolio_transaction_report_rows,
            portfolio_transaction_summary_rows=portfolio_transaction_summary_rows,
            portfolio_inferred_transaction_rows=portfolio_inferred_transaction_rows,
            account_performance_rows=account_performance_rows,
            defensive_etf_candidates=defensive_etf_candidates,
            market_regime=market_regime,
            thesis_reversal_rows=thesis_reversal_rows,
            ticker_memory_rows=ticker_memory_rows,
            anomaly_rows=anomaly_rows,
            anomaly_history_rows=anomaly_history_rows,
            cache_health_rows=cache_health_rows,
            run_log_rows=run_log_rows,
            walk_forward_signal=walk_forward_signal,
            full_audit_signal=full_audit_signal,
            model_audit_signal=model_audit_signal,
            score_stability=score_stability,
            instrument_profile_rows=instrument_profile_rows,
        )
        write_csv_records_mode_pair(
            REPORTS_DIR,
            "latest_research_needed.csv",
            mode,
            _research_needed_rows,
            RESEARCH_NEEDED_COLUMNS,
        )
        save_allocation_snapshot(
            REPORTS_DIR,
            allocation_result,
            analysis_mode=mode,
            run_purpose=resolved_run_purpose,
            baseline_metadata=baseline_metadata,
            manifest_reference=manifest_summary.get("manifest_reference", ""),
            manifest_fingerprint=manifest_summary.get("manifest_fingerprint", ""),
        )
        write_universe_snapshot(
            analyses={**analyses, **watchlist_analyses, **market_analyses, **discovery_analyses},
            run_id=run_id,
            mode=mode,
            model_rules_version=MODEL_RULES_VERSION,
            reports_dir=REPORTS_DIR,
            run_purpose=resolved_run_purpose,
            baseline_metadata=baseline_metadata,
            manifest_reference=manifest_summary.get("manifest_reference", ""),
            manifest_fingerprint=manifest_summary.get("manifest_fingerprint", ""),
        )
        return {
            "allocations": allocation_result.get("allocations", []),
            "analyses": analyses,
            "watchlist_analyses": watchlist_analyses,
            "market_analyses": market_analyses,
            "discovery_analyses": discovery_analyses,
            "decision_quality": decision_quality,
            "proxy_calibration_report": proxy_calibration_report,
            "proxy_calibration_summary": proxy_calibration_summary,
            "allocation_change_rows": allocation_change_rows,
            "defensive_etf_candidates": defensive_etf_candidates,
            "market_regime": market_regime,
            "anomaly_rows": anomaly_rows,
            "cache_health_rows": cache_health_rows,
            "run_log_rows": run_log_rows,
            "baseline_identity": baseline_metadata,
            "decision_manifest": manifest_summary,
        }


    except CriticalInputError:
        raise
    except Exception as _run_analysis_exc:  # noqa: BLE001
        import traceback as _tb
        _emergency_entry = {
            "run_id": run_id,
            "timestamp": datetime.now().isoformat(),
            "mode": mode,
            "capital": capital,
            "status": "CRASH",
            "error_type": type(_run_analysis_exc).__name__,
            "error_message": str(_run_analysis_exc)[:500],
            "traceback_tail": _tb.format_exc()[-1500:],
        }
        try:
            _emergency_path = REPORTS_DIR / "latest_run_crash_log.json"
            import json as _json
            with open(_emergency_path, "w", encoding="utf-8") as _f:
                _json.dump(_emergency_entry, _f, indent=2, ensure_ascii=False)
        except Exception:
            pass
        raise

def apply_cycle_bubble_context(
    analyses: dict[str, dict[str, Any]],
    watchlist_analyses: dict[str, dict[str, Any]],
    market_analyses: dict[str, dict[str, Any]],
    discovery_analyses: dict[str, dict[str, Any]],
    portfolio_risk: dict[str, Any],
) -> None:
    for group in [analyses, watchlist_analyses, market_analyses, discovery_analyses]:
        for analysis in group.values():
            if analysis.get("ticker") == "VFV.TO" or is_etf_asset_analysis(analysis):
                continue
            analysis.update(compute_cycle_bubble_risk(analysis, portfolio_risk))


def apply_long_term_durability_context(*analysis_groups: dict[str, dict[str, Any]]) -> None:
    for group in analysis_groups:
        for analysis in group.values():
            if analysis.get("ticker") == "VFV.TO" or is_etf_asset_analysis(analysis):
                continue
            analysis.update(compute_long_term_durability(analysis))


def apply_market_growth_thesis_context(*analysis_groups: dict[str, dict[str, Any]]) -> None:
    for group in analysis_groups:
        for analysis in group.values():
            if analysis.get("ticker") == "VFV.TO" or is_etf_asset_analysis(analysis):
                continue
            analysis.update(compute_market_growth_thesis(analysis))


def apply_cash_flow_quality_context(*analysis_groups: dict[str, dict[str, Any]]) -> None:
    for group in analysis_groups:
        for analysis in group.values():
            if analysis.get("ticker") == "VFV.TO" or is_etf_asset_analysis(analysis):
                continue
            analysis.update(compute_cash_flow_quality(analysis))


def apply_shareholder_discipline_context(*analysis_groups: dict[str, dict[str, Any]]) -> None:
    for group in analysis_groups:
        for analysis in group.values():
            if analysis.get("ticker") == "VFV.TO" or is_etf_asset_analysis(analysis):
                continue
            result = compute_shareholder_discipline(analysis)
            analysis.update(result)
            if result.get("shareholder_discipline_monitoring_status") == "WATCH":
                reasons = analysis.get("monitoring_reasons")
                if not isinstance(reasons, list):
                    reasons = []
                reason = str(result.get("shareholder_discipline_reason") or "").strip()
                if reason and reason not in reasons:
                    reasons.append(reason)
                analysis["monitoring_reasons"] = reasons
                if analysis.get("monitoring_status") not in {"MANUAL_REVIEW", "CRITICAL"}:
                    analysis["monitoring_status"] = "WATCH"
                signals = analysis.get("technical_or_valuation_signals")
                if not isinstance(signals, list):
                    signals = []
                alert = "Alerte dilution/actionnaires: " + reason if reason else "Alerte dilution/actionnaires."
                if alert not in signals:
                    signals.append(alert)
                analysis["technical_or_valuation_signals"] = signals


def build_position_analyses(
    tickers: list[str],
    manual_inputs: dict[str, dict[str, Any]],
    market_data: dict[str, dict[str, Any]],
    benchmark_data: dict[str, dict[str, Any]],
    benchmark_map: dict[str, str],
    benchmark_sources: dict[str, str] | None,
    sectors: dict[str, str],
    exposures: dict[str, dict[str, Any]],
    weights: dict[str, float],
    current_values: dict[str, float] | None = None,
    portfolio_details: dict[str, dict[str, Any]] | None = None,
    ticker_resolution_metadata: dict[str, dict[str, Any]] | None = None,
    research_inputs: dict[str, dict[str, Any]] | None = None,
    proxy_corrections: dict[str, Any] | None = None,
) -> dict[str, dict[str, Any]]:
    analyses: dict[str, dict[str, Any]] = {}
    current_values = current_values or {}
    portfolio_details = portfolio_details or {}
    research_inputs = research_inputs or {}
    benchmark_sources = benchmark_sources or {}
    for ticker in tickers:
        market = market_data.get(ticker, {})
        exposure = exposures.get(ticker, {})
        benchmark_source = benchmark_sources.get(ticker, "CONFIGURED" if ticker in benchmark_map else "BROAD_MARKET_FALLBACK")
        if ticker not in benchmark_map:
            inferred_benchmark, _ = infer_benchmark_from_context(
                ticker=ticker,
                sector=sectors.get(ticker, "Unknown"),
                exposure=exposure,
                market=market,
            )
            if inferred_benchmark and inferred_benchmark in benchmark_data:
                benchmark_map[ticker] = inferred_benchmark
                benchmark_source = "AUTO_CONTEXT_INFERRED"
        benchmark = benchmark_metrics_for(ticker, benchmark_map, benchmark_data)
        benchmark.update(
            compute_benchmark_relevance(
                ticker=ticker,
                benchmark_ticker=benchmark.get("benchmark_ticker"),
                sector=sectors.get(ticker, "Unknown"),
                exposure=exposure,
                market=market,
                benchmark_source=benchmark_source,
            )
        )
        automated_manual = build_automated_manual_inputs(ticker, market, benchmark, proxy_corrections=proxy_corrections)
        raw_auto_proxy_values = {field: automated_manual.get(field) for field in PROXY_CALIBRATION_FIELD_NAMES}
        raw_auto_proxy_values["forward_pe_manual"] = market.get("forward_pe")
        raw_auto_proxy_values["peg_manual"] = automated_manual.get("peg_manual", market.get("peg"))
        raw_auto_proxy_source_notes = list(automated_manual.get("auto_source_notes") or [])
        if market.get("forward_pe") is not None:
            raw_auto_proxy_source_notes.append("forward_pe_manual: forward PE yfinance")
        if automated_manual.get("peg_manual") is not None:
            raw_auto_proxy_source_notes.append("peg_manual: PEG calibre utilise par le scoring")
        elif market.get("peg") is not None:
            raw_auto_proxy_source_notes.append("peg_manual: PEG yfinance")
        research_enriched = merge_research_with_automated(automated_manual, research_inputs.get(ticker))
        manual = merge_automated_with_manual_overrides(research_enriched, manual_inputs.get(ticker))
        if manual.get("manual_override_fields"):
            manual["research_report_fields"] = [
                field for field in manual.get("research_report_fields", []) if field not in set(manual.get("manual_override_fields", []))
            ]
        _reject_implausible_fair_value(manual, market)

        score = compute_fundamental_score(ticker, manual, market, benchmark)
        market_freshness = compute_market_data_freshness(market)
        reliability = apply_market_freshness_to_reliability(compute_data_reliability(manual, score), market_freshness)
        proof_score = compute_proof_score(manual, market, benchmark, score, reliability)
        manual = apply_reliability_confidence_cap(manual, reliability)
        thesis = compute_thesis_status(manual, score, market, benchmark)
        liquidation = compute_liquidation_status(manual, score, thesis["thesis_status"], market, benchmark, reliability)
        conviction = apply_reliability_conviction_cap(
            compute_conviction_score(manual, score, thesis["thesis_status"], market, benchmark),
            reliability,
        )
        conviction_range = compute_conviction_confidence_range(conviction["conviction_score"], reliability, proof_score)
        cagr_quality = apply_reliability_cagr_cap(
            compute_expected_cagr_quality(manual, score, conviction["conviction_score"], thesis["thesis_status"]),
            reliability,
        )
        expensive = compute_quality_but_too_expensive(manual, score)
        add_eligibility = compute_add_eligibility_status(
            {
                "ticker": ticker,
                **manual,
                **score,
                **thesis,
                **liquidation,
                **conviction,
                **cagr_quality,
                **reliability,
            }
        )
        account_type = str(portfolio_details.get(ticker, {}).get("account_type") or "")
        tax_flags = dividend_tax_flags(ticker, market, exposure)
        gross_yield = safe_float(market.get("dividend_yield")) or 0.0
        after_tax_yield = compute_after_tax_yield(
            ticker,
            gross_yield,
            account_type,
            tax_flags["is_canadian_eligible_dividend"],
            tax_flags["is_us_dividend"],
        )
        vfv_gross_yield = safe_float((market_data.get("VFV.TO") or {}).get("dividend_yield")) or 0.0
        opportunity = apply_reliability_opportunity_cap(
            compute_opportunity_cost_status(
                manual,
                {**score, **expensive, **market, "ticker": ticker, "account_type": account_type},
                conviction["conviction_score"],
                cagr_quality["expected_cagr_quality"],
                thesis["thesis_status"],
                liquidation["liquidation_status"],
                expensive["quality_but_too_expensive"],
                add_eligibility["add_eligibility_status"],
                gross_yield=gross_yield,
                account_type=account_type,
                is_canadian_eligible_dividend=tax_flags["is_canadian_eligible_dividend"],
                is_us_dividend=tax_flags["is_us_dividend"],
                vfv_gross_yield=vfv_gross_yield,
                vfv_account_type=account_type,
            ),
            reliability,
            thesis["thesis_status"],
            liquidation["liquidation_status"],
            add_eligibility["add_eligibility_status"],
        )

        analysis = {
            "ticker": ticker,
            **manual,
            **market,
            **benchmark,
            **score,
            **thesis,
            **liquidation,
            **conviction,
            **conviction_range,
            **cagr_quality,
            **expensive,
            **add_eligibility,
            **opportunity,
            **reliability,
            **proof_score,
            "position_weight": weights.get(ticker, 0.0),
            "current_value": current_values.get(ticker, 0.0),
            "current_value_cad": portfolio_details.get(ticker, {}).get("current_value_cad", current_values.get(ticker, 0.0)),
            "shares": portfolio_details.get(ticker, {}).get("shares"),
            "average_cost": portfolio_details.get(ticker, {}).get("average_cost"),
            "average_cost_cad": portfolio_details.get(ticker, {}).get("average_cost_cad"),
            "acquisition_value": portfolio_details.get(ticker, {}).get("acquisition_value"),
            "acquisition_value_cad": portfolio_details.get(ticker, {}).get("acquisition_value_cad"),
            "cost_basis_aggregation_status": portfolio_details.get(ticker, {}).get("cost_basis_aggregation_status"),
            "cost_basis_currencies": portfolio_details.get(ticker, {}).get("cost_basis_currencies"),
            "portfolio_valuation_source": portfolio_details.get(ticker, {}).get("portfolio_valuation_source"),
            "portfolio_valuation_warning": portfolio_details.get(ticker, {}).get("portfolio_valuation_warning"),
            "quote_currency": portfolio_details.get(ticker, {}).get("quote_currency"),
            "quote_to_cad_rate": portfolio_details.get(ticker, {}).get("quote_to_cad_rate"),
            "current_price_cad": portfolio_details.get(ticker, {}).get("current_price_cad"),
            "average_cost_currency": portfolio_details.get(ticker, {}).get("average_cost_currency"),
            "acquisition_value_currency": portfolio_details.get(ticker, {}).get("acquisition_value_currency"),
            "current_value_currency": portfolio_details.get(ticker, {}).get("current_value_currency"),
            "account_type": account_type,
            "account_tax_category": account_tax_category(account_type),
            "sector": sectors.get(ticker, "Unknown"),
            "region": exposure.get("region", "Unknown"),
            "currency": exposure.get("currency", "Unknown"),
            "gross_yield": gross_yield,
            "after_tax_yield_adjusted": after_tax_yield["after_tax_yield"],
            "tax_adjustment_factor": after_tax_yield["tax_adjustment_factor"],
            "tax_adjustment_note": after_tax_yield["tax_note"],
            "is_canadian_eligible_dividend": tax_flags["is_canadian_eligible_dividend"],
            "is_us_dividend": tax_flags["is_us_dividend"],
            "factor_exposure": exposure.get("factor_exposure", []),
            "universe": "CORE_PORTFOLIO",
            "catastrophic_flags": [field for field, value in manual.items() if field.startswith("catastrophic_") and value is True],
            "input_data_mode": manual.get("input_data_mode", "AUTO_ESTIMATED"),
            "auto_estimated_fields": manual.get("auto_estimated_fields", []),
            "auto_source_notes": manual.get("auto_source_notes", []),
            "proxy_correction_status": manual.get("proxy_correction_status", "NONE"),
            "proxy_correction_fields": manual.get("proxy_correction_fields", []),
            "proxy_corrections_applied": manual.get("proxy_corrections_applied", []),
            "raw_auto_proxy_values": raw_auto_proxy_values,
            "raw_auto_proxy_source_notes": raw_auto_proxy_source_notes,
            "auto_source_quality": manual.get("auto_source_quality"),
            "manual_override_fields": manual.get("manual_override_fields", []),
            "research_report_fields": manual.get("research_report_fields", []),
            "research_report_extracted_fields": manual.get("research_report_extracted_fields", []),
            "research_report_advisory_fields": manual.get("research_report_advisory_fields", []),
            "research_report_field_status": manual.get("research_report_field_status", {}),
            "research_report_field_reasons": manual.get("research_report_field_reasons", {}),
            "research_report_field_files": manual.get("research_report_field_files", {}),
            "research_report_field_providers": manual.get("research_report_field_providers", {}),
            "research_report_field_source_types": manual.get("research_report_field_source_types", {}),
            "research_report_field_report_dates": manual.get("research_report_field_report_dates", {}),
            "broker_target_price_12m": manual.get("broker_target_price_12m"),
            "research_report_price_to_fair_value": manual.get("price_to_fair_value"),
            "research_report_roic_current": manual.get("roic_current"),
            "research_report_roic_10y_avg": manual.get("roic_10y_avg"),
            "research_report_sources": manual.get("research_report_sources", []),
            "research_report_dates": manual.get("research_report_dates", []),
            "research_report_status": manual.get("research_report_status", ""),
            "research_report_error": manual.get("research_report_error", ""),
            "research_report_field_confidence": manual.get("research_report_field_confidence", {}),
            "research_report_text_quality_status": manual.get("research_report_text_quality_status", ""),
            "research_report_text_quality_score": manual.get("research_report_text_quality_score"),
            "research_report_extraction_method": manual.get("research_report_extraction_method", ""),
            "research_report_ocr_status": manual.get("research_report_ocr_status", ""),
            "research_report_text_characters": manual.get("research_report_text_characters"),
            "research_report_extraction_warnings": manual.get("research_report_extraction_warnings", []),
            "research_report_extraction_messages": manual.get("research_report_extraction_messages", []),
        }
        if is_fallback_benchmark(ticker):
            apply_vfv_benchmark_role(analysis)
        elif is_etf_asset(ticker, market, sectors.get(ticker, "Unknown")):
            apply_etf_asset_role(analysis)
        else:
            analysis["data_quality"] = compute_data_quality(analysis)
            analysis.update(compute_winner_accelerated(analysis))
            analysis.update(compute_drift_status(analysis))
        apply_ticker_attention_flags(analysis, (ticker_resolution_metadata or {}).get(ticker, {}))
        analysis["data_confidence_badge"] = compute_data_confidence_badge(analysis)
        analysis["canadian_tax_advantage_active"] = compute_canadian_tax_advantage_active(analysis)
        analyses[ticker] = analysis
    return analyses


def compute_data_confidence_badge(analysis: dict[str, Any]) -> str:
    if is_etf_asset_analysis(analysis):
        return "ETF_N/A"
    evidence = str(analysis.get("automation_evidence_level") or "").upper()
    forward_confidence = str(analysis.get("forward_eps_growth_confidence") or "").upper()
    reliability = str(analysis.get("data_reliability_level") or "").upper()
    fill_rate = safe_float(analysis.get("data_fill_rate")) or 0.0

    if evidence == "STRONG" or forward_confidence == "HIGH" or reliability == "HIGH":
        return "STRONG"
    if evidence == "MODERATE" or forward_confidence == "MEDIUM" or reliability == "MEDIUM":
        return "MODERATE"
    if evidence == "WEAK" or forward_confidence == "LOW" or fill_rate >= 0.70:
        return "WEAK"
    return "PROXY_ONLY"


def compute_canadian_tax_advantage_active(analysis: dict[str, Any]) -> bool:
    if is_etf_asset_analysis(analysis):
        return False
    ticker = normalize_ticker(analysis.get("ticker"))
    account_category = account_tax_category(analysis.get("account_type"))
    gross_yield = safe_float(analysis.get("gross_yield") or analysis.get("dividend_yield")) or 0.0
    active = (
        ticker.endswith((".TO", ".V"))
        and account_category == "NON_REGISTERED"
        and bool(analysis.get("is_canadian_eligible_dividend"))
        and gross_yield > 0
    )  # approximate tax advantage detection — not tax advice
    return active


def apply_vfv_benchmark_role(analysis: dict[str, Any]) -> None:
    profile = etf_asset_profile(analysis.get("ticker"), analysis, analysis.get("sector"))
    analysis.update(
        {
            "benchmark_role": True,
            "asset_type": profile["asset_type"],
            "asset_role": profile["asset_role"],
            "asset_name": profile["asset_name"],
            "asset_focus": profile["asset_focus"],
            "company_name_found": profile["company_name_found"],
            "sector": "S&P 500 ETF",
            "score_total": "BENCHMARK",
            "score_with_estimates": "BENCHMARK",
            "score_confirmed_only": "BENCHMARK",
            "score_possible_if_missing_data_positive": "BENCHMARK",
            "score_missing_data_count": 0,
            "score_estimate_gap": 0,
            "score_confidence_low": "BENCHMARK",
            "score_confidence_high": "BENCHMARK",
            "score_confidence_range": "BENCHMARK",
            "score_confidence_label": "BENCHMARK",
            "score_confidence_reason": "VFV.TO est un ETF de benchmark, donc la plage de confiance d’entreprise ne s’applique pas.",
            "score_evidence_level": "BENCHMARK",
            "score_evidence_penalty": 0,
            "score_evidence_reason": "VFV.TO est un ETF de benchmark, pas une entreprise à scorer par preuves fondamentales.",
            "criteria": {},
            "passed_criteria": [],
            "failed_criteria": [],
            "manual_required_criteria": [],
            "conviction_score": "BENCHMARK",
            "conviction_confidence_low": "BENCHMARK",
            "conviction_confidence_high": "BENCHMARK",
            "conviction_confidence_range": "BENCHMARK",
            "conviction_confidence_label": "BENCHMARK",
            "conviction_confidence_reason": "VFV.TO est un ETF de benchmark, donc la plage de conviction d’entreprise ne s’applique pas.",
            "capital_allocation_score": "BENCHMARK",
            "capital_allocation_score_low": "BENCHMARK",
            "capital_allocation_score_high": "BENCHMARK",
            "capital_allocation_confidence_range": "BENCHMARK",
            "capital_allocation_confidence_label": "BENCHMARK",
            "capital_allocation_confidence_reason": "VFV.TO est une destination de filet de sécurité, pas un score d’allocation d’entreprise.",
            "double_counting_risk_level": "BENCHMARK",
            "double_counting_overlap_score": 0,
            "double_counting_adjustment": 0,
            "double_counting_clusters": "",
            "double_counting_reason": "Non applicable à un ETF benchmark.",
            "hidden_cluster_risk_level": "BENCHMARK",
            "hidden_cluster_exposure": 0,
            "hidden_cluster_clusters": "",
            "hidden_cluster_adjustment": 0,
            "hidden_cluster_reason": "Non applicable à un ETF benchmark.",
            "hidden_cluster_guardrail": "VFV.TO sert de benchmark et filet de sécurité.",
            "hidden_cluster_exception_applied": False,
            "business_quality_score": "BENCHMARK",
            "high_cagr_potential_score": "BENCHMARK",
            "quality_cagr_intersection": "BENCHMARK",
            "cash_flow_quality_status": "BENCHMARK",
            "cash_flow_quality_score": "BENCHMARK",
            "cash_flow_quality_adjustment": "BENCHMARK",
            "cash_flow_quality_reason": "VFV.TO est un ETF benchmark, pas une entreprise à analyser par free cash flow.",
            "shareholder_discipline_status": "BENCHMARK",
            "shareholder_discipline_score": "BENCHMARK",
            "shareholder_discipline_adjustment": "BENCHMARK",
            "shareholder_discipline_reason": "VFV.TO est un ETF benchmark, pas une entreprise à analyser par dilution.",
            "expected_cagr_quality": "BENCHMARK",
            "opportunity_cost_status": "BENCHMARK_FALLBACK",
            "thesis_status": "BENCHMARK",
            "liquidation_status": "BENCHMARK",
            "sell_status": "BENCHMARK",
            "fundamental_sell_status": "BENCHMARK",
            "monitoring_status": "BENCHMARK",
            "monitoring_decision": "BENCHMARK",
            "monitoring_reasons": [],
            "long_term_durability_score": "BENCHMARK",
            "long_term_durability_status": "BENCHMARK",
            "long_term_durability_reason": "VFV.TO est un ETF benchmark, pas une entreprise à évaluer sur la durabilité business.",
            "add_eligibility_status": "BENCHMARK_FALLBACK",
            "add_eligibility_reason": "VFV.TO est le filet de sécurité et benchmark, pas une action à scorer.",
            "add_eligibility_size": "FALLBACK",
            "data_quality": "BENCHMARK",
            "data_reliability_score": "BENCHMARK",
            "data_reliability_level": "BENCHMARK",
            "auto_estimate_dependency": "BENCHMARK",
            "automation_evidence_level": "BENCHMARK",
            "data_reliability_reasons": ["ETF de benchmark, non évalué comme une entreprise."],
            "requires_manual_validation_for_large_allocation": False,
            "input_data_mode": "BENCHMARK_ETF",
            "auto_estimated_fields": [],
            "auto_source_notes": ["ETF benchmark: seules les données de marché sont utilisées."],
            "winner_accelerated": False,
            "quality_but_too_expensive": False,
            "mechanical_sell_signal": "NONE",
            "sell_review_required": False,
            "recommended_action": "ETF_BENCHMARK_FALLBACK",
            "sell_decision": "ETF_BENCHMARK_FALLBACK",
            "liquidation_decision": "ETF_BENCHMARK_FALLBACK",
            "confirmed_fundamental_sell_signals": [],
            "technical_or_valuation_signals": [],
            "sell_discipline": "ETF benchmark, aucune règle de vente d’entreprise.",
        }
    )


def apply_etf_asset_role(analysis: dict[str, Any]) -> None:
    profile = etf_asset_profile(analysis.get("ticker"), analysis, analysis.get("sector"))
    ticker = normalize_ticker(analysis.get("ticker"))
    focus = profile["asset_focus"]
    analysis.update(
        {
            "benchmark_role": False,
            "asset_type": profile["asset_type"],
            "asset_role": profile["asset_role"],
            "asset_name": profile["asset_name"],
            "asset_focus": focus,
            "company_name_found": profile["company_name_found"],
            "score_total": "ETF",
            "score_with_estimates": "ETF",
            "score_confirmed_only": "ETF",
            "score_possible_if_missing_data_positive": "ETF",
            "score_missing_data_count": 0,
            "score_estimate_gap": 0,
            "score_confidence_low": "ETF",
            "score_confidence_high": "ETF",
            "score_confidence_range": "ETF",
            "score_confidence_label": "ETF",
            "score_confidence_reason": "FNB/ETF: la plage de confiance d’entreprise ne s’applique pas.",
            "score_evidence_level": "ETF",
            "score_evidence_penalty": 0,
            "score_evidence_reason": f"{ticker} est un FNB/ETF ({focus}), donc il n’est pas scoré avec ROIC, moat, EPS et juste valeur comme une entreprise.",
            "criteria": {},
            "passed_criteria": [],
            "failed_criteria": [],
            "manual_required_criteria": [],
            "conviction_score": "ETF",
            "conviction_confidence_low": "ETF",
            "conviction_confidence_high": "ETF",
            "conviction_confidence_range": "ETF",
            "conviction_confidence_label": "ETF",
            "conviction_confidence_reason": "FNB/ETF: la plage de conviction d’entreprise ne s’applique pas.",
            "capital_allocation_score": "ETF",
            "capital_allocation_score_low": "ETF",
            "capital_allocation_score_high": "ETF",
            "capital_allocation_confidence_range": "ETF",
            "capital_allocation_confidence_label": "ETF",
            "capital_allocation_confidence_reason": "FNB/ETF: l’allocation est traitée par les règles ETF, pas par le score d’entreprise.",
            "double_counting_risk_level": "ETF",
            "double_counting_overlap_score": 0,
            "double_counting_adjustment": 0,
            "double_counting_clusters": "",
            "double_counting_reason": "Non applicable à un FNB/ETF analysé comme exposition indicielle.",
            "hidden_cluster_risk_level": "ETF",
            "hidden_cluster_exposure": 0,
            "hidden_cluster_clusters": "",
            "hidden_cluster_adjustment": 0,
            "hidden_cluster_reason": "Non applicable à un FNB/ETF analysé comme exposition indicielle.",
            "hidden_cluster_guardrail": "FNB/ETF traité selon son rôle de portefeuille, pas comme entreprise individuelle.",
            "hidden_cluster_exception_applied": False,
            "business_quality_score": "ETF",
            "high_cagr_potential_score": "ETF",
            "quality_cagr_intersection": "ETF",
            "cash_flow_quality_status": "ETF",
            "cash_flow_quality_score": "ETF",
            "cash_flow_quality_adjustment": "ETF",
            "cash_flow_quality_reason": "FNB/ETF: pas de free cash flow d’entreprise à scorer.",
            "shareholder_discipline_status": "ETF",
            "shareholder_discipline_score": "ETF",
            "shareholder_discipline_adjustment": "ETF",
            "shareholder_discipline_reason": "FNB/ETF: pas de dilution d’entreprise individuelle à scorer.",
            "expected_cagr_quality": "ETF_DIVERSIFIED",
            "opportunity_cost_status": "ETF_COMPARE_TO_VFV",
            "opportunity_cost_reason": f"{ticker} est comparé qualitativement à VFV.TO comme exposition indicielle, pas comme action individuelle.",
            "thesis_status": "ETF",
            "thesis_reasons": [f"FNB/ETF exposé à {focus}; pas de thèse d’entreprise individuelle à valider."],
            "fundamental_thesis_status": "ETF",
            "market_watch_status": "ETF",
            "valuation_watch_status": "ETF",
            "liquidation_status": "GREEN",
            "sell_status": "GREEN",
            "fundamental_sell_status": "GREEN",
            "monitoring_status": "NORMAL",
            "monitoring_decision": "NONE",
            "monitoring_reasons": [],
            "long_term_durability_score": "ETF",
            "long_term_durability_status": "ETF_DIVERSIFIED",
            "long_term_durability_reason": f"{ticker} dépend surtout de la qualité, diversification, concentration et frais de son indice sous-jacent.",
            "add_eligibility_status": "ETF_HOLD_ONLY",
            "add_eligibility_reason": f"{ticker} est un FNB/ETF détenu ou suivi; l’allocation automatique offensive reste réservée aux entreprises core et à VFV.TO comme filet.",
            "add_eligibility_size": "NONE",
            "data_quality": "ETF",
            "data_reliability_score": "ETF",
            "data_reliability_level": "ETF",
            "auto_estimate_dependency": "ETF",
            "automation_evidence_level": "ETF",
            "data_reliability_reasons": ["FNB/ETF: données fondamentales d’entreprise non requises."],
            "requires_manual_validation_for_large_allocation": False,
            "input_data_mode": "ETF_MARKET_DATA_ONLY",
            "auto_estimated_fields": [],
            "auto_source_notes": ["FNB/ETF: prix, rendement, SMA et drawdown seulement."],
            "winner_accelerated": False,
            "winner_accelerated_reason": "Non applicable à un FNB/ETF.",
            "quality_but_too_expensive": False,
            "mechanical_sell_signal": "NONE",
            "sell_review_required": False,
            "liquidation_decision": "HOLD",
            "recommended_action": "HOLD",
            "sell_decision": "HOLD",
            "liquidation_reasons": ["FNB/ETF: pas de signal mécanique de vente d’entreprise."],
            "signals_detected": [],
            "confirmed_fundamental_sell_signals": [],
            "technical_or_valuation_signals": [],
            "sell_discipline": "FNB/ETF traité comme exposition indicielle, pas comme entreprise individuelle.",
        }
    )


def apply_final_decisions(analyses: dict[str, dict[str, Any]], allocations: list[dict[str, Any]]) -> None:
    allocated = {}
    for row in allocations:
        ticker = normalize_ticker(row.get("destination"))
        allocated[ticker] = allocated.get(ticker, 0.0) + (safe_float(row.get("montant")) or 0.0)

    for ticker, analysis in analyses.items():
        amount = allocated.get(ticker, 0.0)
        if amount > 0 and ticker != "VFV.TO" and is_external_etf_allocation_candidate(analysis):
            allocation_decision = "BUY / ADD"
            allocation_reason = "ETF externe retenu par le mode utilisé; allocation limitée selon rôle de portefeuille, diversification, tendance et garde-fous ETF."
        elif amount > 0 and ticker != "VFV.TO":
            allocation_decision = "BUY / ADD"
            allocation_reason = "Reçoit du nouveau capital après score, thèse, admissibilité d’achat, drift et sizing."
        elif ticker == "VFV.TO" and amount > 0:
            allocation_decision = "BUY / ADD"
            allocation_reason = "Allocation obligatoire, redirection ou filet de sécurité; VFV.TO est traité comme benchmark, pas comme action individuelle."
        elif is_etf_asset_analysis(analysis):
            allocation_decision = "ETF_HOLD_ONLY"
            allocation_reason = "FNB/ETF conservé comme exposition indicielle; pas de nouvelle allocation automatique sauf VFV.TO comme filet de sécurité."
        elif analysis.get("deep_averaging_down_blocked") is True:
            allocation_decision = "DO_NOT_ADD"
            allocation_reason = str(analysis.get("deep_averaging_down_reason") or "Deep averaging-down safeguard active.")
        elif analysis.get("thesis_status") != "INTACT":
            allocation_decision = "DO_NOT_ADD"
            allocation_reason = "Thèse non intacte."
        elif analysis.get("quality_but_too_expensive"):
            allocation_decision = "DO_NOT_ADD"
            allocation_reason = "Qualité élevée possible, mais valorisation excessive."
        elif analysis.get("add_eligibility_status") == "ADD_ALLOWED_SMALL":
            allocation_decision = "ELIGIBLE_BUT_NOT_SELECTED"
            allocation_reason = "Petite allocation permise, mais non retenue par le sizing marginal de cette cotisation."
        elif analysis.get("add_eligibility_status") == "ADD_ALLOWED":
            allocation_decision = "ELIGIBLE_BUT_NOT_SELECTED"
            allocation_reason = "Achat permis, mais une autre destination a un meilleur score marginal pour cette cotisation."
        else:
            allocation_decision = "NO_NEW_ALLOCATION"
            allocation_reason = "Aucune allocation nouvelle après comparaison VFV, garde-fous et sizing."

        sell_decision = analysis.get("sell_decision") or analysis.get("recommended_action") or "HOLD"
        if ticker == "VFV.TO":
            sell_decision = analysis.get("sell_decision", "ETF_BENCHMARK_FALLBACK")
            sell_reason = "ETF benchmark: aucune règle de vente d’entreprise."
        elif is_etf_asset_analysis(analysis):
            sell_decision = analysis.get("sell_decision", "HOLD")
            sell_reason = "FNB/ETF: aucune règle de vente d’entreprise; surveiller plutôt l’indice, la concentration, la devise et les frais."
        elif analysis.get("liquidation_status") == "RED":
            sell_reason = "Signal mécanique de vente; validation manuelle requise avant transaction."
        elif analysis.get("liquidation_status") == "ORANGE":
            sell_reason = "Signal mécanique de réduction; validation manuelle requise avant transaction."
        elif analysis.get("liquidation_status") == "YELLOW":
            sell_reason = "Position à surveiller; aucun achat/vente automatique sans validation du contexte."
        else:
            sell_reason = "Aucun signal de vente mécanique."

        monitoring_status = analysis.get("monitoring_status", "NORMAL")
        monitoring_reason = "; ".join(str(item) for item in analysis.get("monitoring_reasons", []) if str(item).strip())
        final_action, final_reason = _combine_position_actions(
            allocation_decision,
            allocation_reason,
            sell_decision,
            sell_reason,
            ticker,
            monitoring_status,
            monitoring_reason,
        )
        analysis["allocation_decision"] = allocation_decision
        analysis["allocation_decision_reason"] = allocation_reason
        analysis["sell_decision"] = sell_decision
        analysis["sell_decision_reason"] = sell_reason
        analysis["final_position_action"] = final_action
        analysis["final_position_reason"] = final_reason
        analysis["decision"] = final_action
        analysis["decision_reason"] = final_reason


def _combine_position_actions(
    allocation_decision: str,
    allocation_reason: str,
    sell_decision: str,
    sell_reason: str,
    ticker: str,
    monitoring_status: str = "NORMAL",
    monitoring_reason: str = "",
) -> tuple[str, str]:
    if ticker == "VFV.TO":
        return allocation_decision, allocation_reason
    if sell_decision in {"REVIEW_TRIM_25", "REVIEW_TRIM_50", "REVIEW_LIQUIDATE_PROGRESSIVELY", "LIQUIDATE_URGENT_REVIEW"}:
        return sell_decision, sell_reason
    if allocation_decision == "BUY / ADD" and (sell_decision == "WATCH" or monitoring_status in {"WATCH", "MANUAL_REVIEW"}):
        detail = monitoring_reason or sell_reason
        return "ADD_WITH_MONITORING", f"{allocation_reason} Surveillance séparée: {detail}"
    if allocation_decision == "BUY / ADD":
        return "BUY / ADD", allocation_reason
    if sell_decision in {"WATCH", "DO_NOT_ADD"}:
        return sell_decision, sell_reason
    if allocation_decision in {"DO_NOT_ADD", "NO_NEW_ALLOCATION", "ELIGIBLE_BUT_NOT_SELECTED"}:
        return allocation_decision, allocation_reason
    return "HOLD", "Conserver; aucune action mécanique prioritaire."


def merge_data_gaps(market_gaps: list[dict[str, Any]], *analysis_groups: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    etf_tickers = {
        normalize_ticker(ticker or analysis.get("ticker"))
        for analyses in analysis_groups
        for ticker, analysis in analyses.items()
        if is_etf_asset_analysis(analysis)
    }
    rows: list[dict[str, Any]] = [row for row in market_gaps if normalize_ticker(row.get("ticker")) not in etf_tickers]
    for analyses in analysis_groups:
        for ticker, analysis in analyses.items():
            if is_etf_asset_analysis(analysis):
                continue
            for criterion in analysis.get("manual_required_criteria", []):
                rows.append(
                    {
                        "ticker": ticker,
                        "data_field": criterion,
                        "importance": "HIGH",
                        "impact": "Peut réduire score, conviction, thèse ou admissibilité à l’allocation.",
                    }
                )
            for field in analysis.get("auto_estimated_fields", []):
                rows.append(
                    {
                        "ticker": ticker,
                        "data_field": f"AUTO_ESTIMATE: {field}",
                        "importance": "MEDIUM",
                        "impact": "Donnée estimée automatiquement; à valider manuellement pour une décision importante.",
                        "forward_eps": analysis.get("forward_eps"),
                        "trailing_eps": analysis.get("trailing_eps"),
                        "number_of_analyst_opinions": analysis.get("number_of_analyst_opinions"),
                        "forward_eps_growth_direct": analysis.get("forward_eps_growth_direct"),
                        "forward_eps_growth_confidence": analysis.get("forward_eps_growth_confidence"),
                        "data_source_forward": analysis.get("data_source_forward"),
                        "eps_growth_5y_proxy_sanity": analysis.get("eps_growth_5y_proxy_sanity"),
                        "early_deterioration_signal": analysis.get("early_deterioration_signal"),
                    }
                )
    unique: dict[tuple[str, str], dict[str, Any]] = {}
    for row in rows:
        key = (str(row.get("ticker")), str(row.get("data_field")))
        unique[key] = row
    return list(unique.values())


def tax_penalty_map(tax_report: list[dict[str, Any]]) -> dict[str, float]:
    penalties: dict[str, float] = {}
    for row in tax_report:
        alert = str(row.get("alert") or "")
        soft_alert = "Dividendes américains potentiellement plus adaptés au REER" in alert
        if alert and "Aucune alerte" not in alert and "Compte non renseigné" not in alert and not soft_alert:
            ticker = row.get("ticker")
            penalties[ticker] = max(penalties.get(ticker, 0.0), 10.0)
    return penalties


def dividend_tax_flags(ticker: str, market: dict[str, Any], exposure: dict[str, Any]) -> dict[str, bool]:
    normalized = str(ticker or "").upper()
    currency = str(market.get("currency") or exposure.get("currency") or market.get("quote_currency") or "").upper()
    region = str(exposure.get("region") or market.get("country") or "").lower()
    is_canadian_ticker = normalized.endswith((".TO", ".V", ".CN", ".NE"))
    is_fund = is_etf_asset(normalized, market)
    is_canadian_eligible = bool((is_canadian_ticker or region == "canada") and currency == "CAD" and not is_fund)
    is_us = bool(currency == "USD" or region == "united states" or normalized == "VFV.TO")
    return {
        "is_canadian_eligible_dividend": is_canadian_eligible,
        "is_us_dividend": is_us,
    }


def refresh_add_and_opportunity_context(*analysis_groups: dict[str, dict[str, Any]]) -> None:
    for analyses in analysis_groups:
        for analysis in analyses.values():
            if analysis.get("benchmark_role") is True or analysis.get("ticker") == "VFV.TO":
                analysis.update(compute_add_eligibility_status(analysis))
                continue
            if is_etf_asset_analysis(analysis):
                apply_etf_asset_role(analysis)
                continue
            add_eligibility = compute_add_eligibility_status(analysis)
            analysis.update(add_eligibility)
            opportunity = apply_reliability_opportunity_cap(
                compute_opportunity_cost_status(
                    analysis,
                    analysis,
                    safe_float(analysis.get("conviction_score")) or 0.0,
                    str(analysis.get("expected_cagr_quality") or ""),
                    str(analysis.get("thesis_status") or ""),
                str(analysis.get("liquidation_status") or ""),
                analysis.get("quality_but_too_expensive") is True,
                add_eligibility["add_eligibility_status"],
                gross_yield=safe_float(analysis.get("dividend_yield")) or safe_float(analysis.get("gross_yield")) or 0.0,
                account_type=str(analysis.get("account_type") or ""),
                is_canadian_eligible_dividend=analysis.get("is_canadian_eligible_dividend") is True,
                is_us_dividend=analysis.get("is_us_dividend") is True,
                vfv_gross_yield=safe_float(analysis.get("vfv_gross_yield")) or 0.0,
                vfv_account_type=str(analysis.get("account_type") or ""),
            ),
            analysis,
            str(analysis.get("thesis_status") or ""),
            str(analysis.get("liquidation_status") or ""),
            add_eligibility["add_eligibility_status"],
            )
            analysis.update(opportunity)
            analysis.update(compute_winner_accelerated(analysis))
            analysis.update(compute_drift_status(analysis))


def load_positions() -> list[str]:
    loaded = load_yaml(CONFIG_DIR / "positions.yaml")
    positions = loaded.get("positions", [])
    return [normalize_ticker(ticker) for ticker in positions]


def load_default_manual_tickers() -> list[str]:
    tickers = []
    tickers.extend(load_positions())
    tickers.extend(normalize_ticker(ticker) for ticker in load_yaml(CONFIG_DIR / "watchlist.yaml").get("watchlist", []))
    tickers.extend(normalize_ticker(ticker) for ticker in load_yaml(CONFIG_DIR / "market_scanner.yaml").get("default_universe", []))
    tickers.extend(normalize_ticker(ticker) for ticker in load_yaml(CONFIG_DIR / "market_scanner.yaml").get("discovery_universe", []))
    seen: set[str] = set()
    ordered: list[str] = []
    for ticker in tickers:
        if ticker and ticker not in seen:
            ordered.append(ticker)
            seen.add(ticker)
    return ordered


def load_known_research_tickers() -> list[str]:
    ticker_aliases = load_ticker_aliases(CONFIG_DIR / "ticker_aliases.yaml")
    ticker_resolution_metadata: dict[str, dict[str, Any]] = {}
    tickers = set(load_default_manual_tickers())

    tickers.update(
        row["ticker"]
        for row in resolve_portfolio_rows(
            load_portfolio(DATA_DIR / "portfolio.csv"),
            ticker_aliases,
            ticker_resolution_metadata,
            "data/portfolio.csv",
        )
    )
    tickers.update(
        row["ticker"]
        for row in resolve_account_location_rows(
            load_account_locations(DATA_DIR / "account_locations.csv"),
            ticker_aliases,
            ticker_resolution_metadata,
            "data/account_locations.csv",
        )
    )
    tickers.update(
        load_and_resolve_universe(
            lambda: load_watchlist(CONFIG_DIR / "watchlist.yaml", DATA_DIR / "watchlist.csv"),
            ticker_aliases,
            ticker_resolution_metadata,
            "watchlist",
        ).keys()
    )
    tickers.update(
        load_and_resolve_universe(
            lambda: load_market_universe(CONFIG_DIR / "market_scanner.yaml", DATA_DIR / "market_universe.csv"),
            ticker_aliases,
            ticker_resolution_metadata,
            "market_universe",
        ).keys()
    )
    tickers.update(
        load_and_resolve_universe(
            lambda: load_discovery_universe(CONFIG_DIR / "market_scanner.yaml", set()),
            ticker_aliases,
            ticker_resolution_metadata,
            "discovery_universe",
        ).keys()
    )
    tickers.update(
        resolve_manual_inputs(
            load_friendly_manual_inputs(DATA_DIR / "manual_inputs_friendly.txt"),
            ticker_aliases,
            ticker_resolution_metadata,
            "data/manual_inputs_friendly.txt",
        ).keys()
    )
    return sorted(ticker for ticker in tickers if ticker)


def metadata_to_sector_exposure(universe: dict[str, dict[str, Any]]) -> tuple[dict[str, str], dict[str, dict[str, Any]]]:
    sectors: dict[str, str] = {}
    exposures: dict[str, dict[str, Any]] = {}
    for ticker, metadata in universe.items():
        if metadata.get("sector"):
            sectors[ticker] = metadata["sector"]
        exposures[ticker] = {
            "region": metadata.get("region") or "Unknown",
            "currency": metadata.get("currency") or "Unknown",
            "factor_exposure": [],
        }
    return sectors, exposures


def enrich_sector_map(
    configured_sectors: dict[str, str],
    market_data: dict[str, dict[str, Any]],
    tickers: list[str],
) -> dict[str, str]:
    enriched = dict(configured_sectors)
    for ticker in tickers:
        if enriched.get(ticker) and enriched[ticker] != "Unknown":
            continue
        market = market_data.get(ticker, {})
        sector = market.get("sector_name") or market.get("industry")
        if sector:
            enriched[ticker] = str(sector)
        elif is_etf_asset(ticker, market):
            enriched[ticker] = etf_risk_sector(ticker, market)
    return enriched


def enrich_exposure_map(
    configured_exposures: dict[str, dict[str, Any]],
    market_data: dict[str, dict[str, Any]],
    tickers: list[str],
) -> dict[str, dict[str, Any]]:
    enriched = {ticker: dict(value) for ticker, value in configured_exposures.items()}
    for ticker in tickers:
        market = market_data.get(ticker, {})
        current = dict(enriched.get(ticker, {}))
        if not current.get("region") or current.get("region") == "Unknown":
            current["region"] = market.get("country") or "Unknown"
        if not current.get("currency") or current.get("currency") == "Unknown":
            current["currency"] = market.get("currency") or "Unknown"
        if is_etf_asset(ticker, market) and (
            current.get("region") == "Unknown"
            or current.get("currency") == "Unknown"
            or not current.get("factor_exposure")
        ):
            etf_exposure = etf_risk_exposure(ticker, market)
            if current.get("region") == "Unknown":
                current["region"] = etf_exposure.get("region", "Diversified")
            if current.get("currency") == "Unknown":
                current["currency"] = etf_exposure.get("currency", "Unknown")
            if not current.get("factor_exposure"):
                current["factor_exposure"] = etf_exposure.get("factor_exposure", [])
        current.setdefault("factor_exposure", [])
        enriched[ticker] = current
    return enriched


def apply_external_superiority_gate(external_analysis: dict[str, Any], core_analyses: dict[str, dict[str, Any]]) -> None:
    profile_ok, profile_reason = promotion_profile_alignment_status(external_analysis)
    if not profile_ok:
        external_analysis["external_superiority"] = "NOT_FULLY_ALIGNED_WITH_HIGH_CAGR_CORE"
        external_analysis["external_superiority_reason"] = profile_reason
        if external_analysis.get("watchlist_status") == "HIGH_PRIORITY_WATCH":
            external_analysis["watchlist_status"] = "INTERESTING_BUT_WAIT"
            external_analysis["watchlist_reason"] = (
                str(external_analysis.get("watchlist_reason") or "")
                + f" {profile_reason}"
            ).strip()
        if external_analysis.get("candidate_status") == "MANUAL_REVIEW_TOP_CANDIDATE":
            external_analysis["candidate_status"] = "PROMISING_BUT_INCOMPLETE"
            external_analysis["candidate_reason"] = (
                str(external_analysis.get("candidate_reason") or "")
                + f" {profile_reason}"
            ).strip()
        return

    core_fit, core_fit_reason = external_core_fit_status(external_analysis, core_analyses)
    if core_fit:
        external_analysis["external_superiority"] = "COMPARABLE_TO_CORE_LEADERS"
        external_analysis["external_superiority_reason"] = core_fit_reason
        return

    external_analysis["external_superiority"] = "NOT_COMPARABLE_TO_CORE_LEADERS"
    external_analysis["external_superiority_reason"] = core_fit_reason
    if external_analysis.get("watchlist_status") == "HIGH_PRIORITY_WATCH":
        external_analysis["watchlist_status"] = "INTERESTING_BUT_WAIT"
        external_analysis["watchlist_reason"] = (
            str(external_analysis.get("watchlist_reason") or "")
            + f" {core_fit_reason}"
        ).strip()
    if external_analysis.get("candidate_status") == "MANUAL_REVIEW_TOP_CANDIDATE":
        external_analysis["candidate_status"] = "PROMISING_BUT_INCOMPLETE"
        external_analysis["candidate_reason"] = (
            str(external_analysis.get("candidate_reason") or "")
            + f" {core_fit_reason}"
        ).strip()


def weakest_core_position(core_analyses: dict[str, dict[str, Any]]) -> dict[str, Any] | None:
    candidates = [row for ticker, row in core_analyses.items() if ticker != "VFV.TO"]
    if not candidates:
        return None
    return sorted(
        candidates,
        key=lambda row: (
            safe_float(row.get("score_total")) or 0.0,
            safe_float(row.get("conviction_score")) or 0.0,
        ),
    )[0]


if __name__ == "__main__":
    sys.exit(main())
