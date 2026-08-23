from __future__ import annotations

from pathlib import Path
from typing import Any

from .account_charts import (
    ACCOUNT_CHART_COLUMNS,
    account_chart_rows_for_report,
    account_charts_markdown,
    build_account_allocation_chart_rows,
)
from .account_performance_engine import ACCOUNT_PERFORMANCE_COLUMNS
from .audit_snapshot_engine import save_audit_snapshot
from .allocation_change_engine import write_allocation_change_csv
from .allocation_sensitivity_engine import (
    sensitivity_rows_for_report,
    sensitivity_summary_rows_for_report,
    write_allocation_sensitivity_csv,
    write_allocation_sensitivity_summary_csv,
)
from .anomaly_detection_engine import ANOMALY_COLUMNS, anomaly_rows_for_report, anomaly_summary
from .asset_type_engine import is_etf_asset_analysis
from .cache_management_engine import CACHE_HEALTH_COLUMNS, cache_health_summary
from .cash_flow_quality_engine import CASH_FLOW_QUALITY_COLUMNS, cash_flow_rows_for_csv
from .company_dossier_engine import (
    COMPANY_DOSSIER_COLUMNS,
    build_company_dossier,
    build_company_dossier_rows,
)
from .shareholder_discipline_engine import SHAREHOLDER_DISCIPLINE_COLUMNS, shareholder_discipline_rows_for_csv
from .sell_validation_checklist_engine import (
    SELL_VALIDATION_CHECKLIST_COLUMNS,
    sell_validation_checklist_rows,
)
from .source_conflict_engine import (
    SOURCE_CONFLICT_COLUMNS,
    build_source_conflict_rows,
    compact_source_conflict_rows,
    source_conflict_summary,
)
from .source_health_engine import (
    SOURCE_HEALTH_COLUMNS,
    SOURCE_HEALTH_HISTORY_COLUMNS,
    build_source_health_rows,
    compact_source_health_rows,
    source_health_summary,
    update_source_health_history,
)
from .history_engine import TREND_COLUMNS, trend_rows_for_csv, write_trend_csv
from .hidden_cluster_engine import compact_hidden_cluster_rows
from .add_eligibility_engine import ADD_ALLOWED_STATUSES
from .cycle_bubble_risk_engine import cycle_risk_rows
from .decision_quality_engine import DECISION_QUALITY_COLUMNS, decision_quality_rows_for_csv
from .defensive_etf_engine import (
    DEFENSIVE_ETF_COLUMNS,
    defensive_etf_rows_for_csv,
    defensive_fallback_summary,
)
from .external_etf_engine import EXTERNAL_ETF_COLUMNS, external_etf_rows_for_csv
from .discovery_engine import (
    DISCOVERY_COLUMNS,
    DISCOVERY_MAINTENANCE_COLUMNS,
    DISCOVERY_SCOPE_NOTE,
    actionable_discovery_rows,
    build_discovery_idea_rows,
)
from .market_scanner import SCANNER_SCOPE_NOTE, build_market_candidate_rows
from .market_growth_thesis_engine import (
    MARKET_GROWTH_THESIS_COLUMNS,
    market_growth_thesis_rows_for_csv,
)
from .market_regime_engine import (
    MARKET_REGIME_ANALYSIS_COLUMNS,
    MARKET_REGIME_COLUMNS,
    SECTOR_EUPHORIA_ANALYSIS_COLUMNS,
    SECTOR_EUPHORIA_COLUMNS,
    market_regime_analysis_rows,
    market_regime_rows,
    sector_euphoria_analysis_rows,
    sector_euphoria_rows,
    write_market_regime_csvs,
)
from .model_version import MODEL_RULES_VERSION
from .portfolio_risk_engine import risk_rows_for_csv
from .portfolio_change_tracker import (
    PORTFOLIO_CHANGE_COLUMNS,
    PORTFOLIO_CHANGE_SUMMARY_COLUMNS,
)
from .portfolio_inferred_transactions import INFERRED_TRANSACTION_COLUMNS, reportable_inferred_transactions
from .portfolio_transactions import (
    PORTFOLIO_TRANSACTION_REPORT_COLUMNS,
    PORTFOLIO_TRANSACTION_SUMMARY_COLUMNS,
)
from .promotion_engine import (
    PROMOTION_COLUMNS,
    WEAKEST_CORE_AUDIT_COLUMNS,
    build_promotion_candidate_rows,
    build_weakest_core_audit_rows,
)
from .proxy_calibration import (
    PROXY_CALIBRATION_HISTORY_COLUMNS,
    PROXY_CALIBRATION_REPORT_COLUMNS,
    PROXY_CALIBRATION_SUMMARY_COLUMNS,
)
from .proxy_bias_engine import PROXY_BIAS_COLUMNS
from .proxy_correction_engine import (
    PROXY_CORRECTION_AUDIT_COLUMNS,
    proxy_correction_audit_summary,
)
from .report_formatters import (
    align_full_report_navigation,
    as_list as _as_list,
    build_compact_data_reliability_section,
    build_compact_decision_section,
    build_compact_external_monitoring_section,
    build_compact_model_health_section,
    build_compact_portfolio_section,
    build_decision_quality_compact_lines,
    build_instrument_profile_section,
    build_ranking_section,
    build_score_stability_signal_lines,
    build_triage_header,
    compact_list as _compact_list,
    compact_sentence as _compact_sentence,
    escape_markdown_cell as _escape,
    first_signal as _first_signal,
    list_text as _list_text,
    mapping_text as _mapping_text,
    proxy_corrections_text as _proxy_corrections_text,
    report_value as _report_value,
    truthy_report_value as _truthy_report_value,
    uses_yfinance_or_cache as _uses_yfinance_or_cache,
)
from .qualitative_moat_engine import (
    QUALITATIVE_MOAT_COLUMNS,
    build_qualitative_moat_rows,
    qualitative_moat_markdown,
)
from .quality_drawdown_engine import QUALITY_DRAWDOWN_COLUMNS, quality_drawdown_rows_for_csv
from .ticker_resolver import TICKER_ISSUE_COLUMNS, ticker_issue_rows_for_csv
from .ticker_memory_engine import TICKER_MEMORY_COLUMNS, compact_ticker_memory_rows, ticker_memory_summary
from .run_logging_engine import (
    RUN_LOG_COLUMNS,
    append_run_log_history,
    extend_report_run_log,
    run_log_rows_for_report,
    run_log_summary,
)
from .utils import (
    DATA_DIR,
    DISCLAIMER,
    markdown_to_html,
    money as _money,
    normalize_ticker,
    pct as _pct,
    read_csv_records,
    safe_float,
    today_iso,
    write_csv_records,
    write_text,
)
from .validation_priority_engine import (
    validation_priority_rows_for_report,
    write_validation_priority_csv,
)
from .watchlist_engine import build_watchlist_report_rows
from .winner_protection_engine import WINNER_PROTECTION_COLUMNS, winner_protection_rows


def money(value: Any) -> str:
    number = safe_float(value)
    if number is None:
        if isinstance(value, str) and value.strip():
            return value.strip()
        return _money(None)
    return _money(number)


def pct(value: Any, digits: int = 1) -> str:
    number = safe_float(value)
    if number is None:
        if isinstance(value, str) and value.strip():
            return value.strip()
        return _pct(None, digits)
    return _pct(number, digits)


THESIS_REVERSAL_COLUMNS = [
    "ticker",
    "ticker_display",
    "universe",
    "previous_thesis_status",
    "current_thesis_status",
    "thesis_reversal_status",
    "thesis_reversal_severity",
    "manual_review_priority",
    "conclusion_basis",
    "data_quality_driven",
    "score_contradiction_flag",
    "suggested_human_action",
    "allocation_impact",
    "reason_fr",
    "score_total_change",
    "conviction_score_change",
    "capital_allocation_score_change",
    "proof_score_status",
    "sell_validation_level",
    "data_reliability_level",
    "score_evidence_level",
    "source_conflict_profile",
    "history_reference_count",
    "history_reference_dates",
]


def _append_columns_once(columns: list[str], additions: list[str]) -> None:
    for column in additions:
        if column in columns:
            # WARNING: duplicate report column requested; keep first occurrence for CSV compatibility.
            continue
        columns.append(column)


SCORES_COLUMNS = [
    "ticker",
    "ticker_display",
    "input_tickers",
    "resolved_ticker",
    "company_name_found",
    "business_summary",
    "website",
    "company_city",
    "company_state",
    "full_time_employees",
    "ticker_validation_status",
    "ticker_coverage_status",
    "free_data_coverage_class",
    "free_data_coverage_score",
    "suggested_yahoo_tickers",
    "ticker_issues",
    "score_total",
    "score_with_estimates",
    "score_confirmed_only",
    "score_estimate_gap",
    "score_data_gap_haircut",
    "score_data_gap_flag",
    "score_data_gap_label",
    "score_confidence_range",
    "score_confidence_low",
    "score_confidence_high",
    "score_confidence_label",
    "score_confidence_reason",
    "score_estimated_points",
    "score_evidence_level",
    "score_evidence_penalty",
    "score_evidence_reason",
    "conviction_score",
    "conviction_score_raw",
    "conviction_confidence_range",
    "conviction_confidence_low",
    "conviction_confidence_high",
    "conviction_confidence_label",
    "conviction_confidence_reason",
    "business_quality_score",
    "high_cagr_potential_score",
    "shareholder_return_quality_score",
    "shareholder_return_profile",
    "shareholder_return_adjustment",
    "shareholder_return_reason",
    "cash_flow_quality_status",
    "cash_flow_quality_score",
    "cash_flow_quality_adjustment",
    "cash_flow_quality_reason",
    "operating_cash_flow",
    "capital_expenditures",
    "free_cash_flow",
    "free_cash_flow_margin",
    "free_cash_flow_growth",
    "fcf_conversion",
    "net_debt_to_fcf",
    "cash_flow_metrics_available_count",
    "shareholder_discipline_status",
    "shareholder_discipline_score",
    "shareholder_discipline_adjustment",
    "shareholder_discipline_reason",
    "shareholder_discipline_primary_dilution_rate",
    "shares_outstanding",
    "diluted_average_shares",
    "share_count_growth_1y",
    "share_count_cagr_3y",
    "share_count_cagr_5y",
    "share_repurchases",
    "buyback_yield",
    "stock_based_compensation",
    "sbc_to_revenue",
    "fcf_per_share",
    "fcf_per_share_growth",
    "dividend_yield",
    "after_tax_yield_adjusted",
    "tax_adjustment_factor",
    "tax_adjustment_note",
    "payout_ratio",
    "long_term_durability_score",
    "long_term_durability_status",
    "long_term_durability_reason",
    "market_growth_thesis_score",
    "market_growth_thesis_status",
    "market_growth_thesis_adjustment",
    "market_growth_thesis_confidence",
    "market_growth_thesis_themes",
    "market_growth_thesis_sources",
    "market_growth_thesis_reason",
    "capital_allocation_score",
    "capital_allocation_confidence_range",
    "capital_allocation_score_low",
    "capital_allocation_score_high",
    "capital_allocation_confidence_label",
    "capital_allocation_confidence_reason",
    "reliability_cap_status",
    "reliability_cap_applied",
    "reliability_allocation_cap_percent",
    "reliability_allocation_cap_amount",
    "reliability_cap_reason",
    "business_profile",
    "business_profile_label",
    "benchmark_ticker",
    "benchmark_source",
    "benchmark_relevance_level",
    "benchmark_relevance_score",
    "benchmark_relevance_reason",
    "expected_cagr_quality",
    "opportunity_cost_status",
    "thesis_status",
    "fundamental_thesis_status",
    "market_watch_status",
    "valuation_watch_status",
    "liquidation_status",
    "sell_status",
    "fundamental_sell_status",
    "monitoring_status",
    "monitoring_decision",
    "monitoring_reasons",
    "add_eligibility_status",
    "add_eligibility_size",
    "add_eligibility_reason",
    "winner_accelerated",
    "quality_but_too_expensive",
    "valuation_severity",
    "valuation_severity_reason",
    "quality_expensive_reasons",
    "quality_drawdown_status",
    "quality_drawdown_score",
    "quality_drawdown_allocation_adjustment",
    "quality_drawdown_reason",
    "news_context_triggered",
    "news_context_status",
    "news_context_reason",
    "news_context_sources",
    "news_context_headlines",
    "news_context_source_channels",
    "news_context_search_queries",
    "news_context_checked_at",
    "cycle_risk_profile",
    "cycle_bubble_risk_level",
    "cycle_bubble_score",
    "cycle_bubble_penalty",
    "cycle_bubble_allocation_multiplier",
    "cycle_normalized_status",
    "cycle_normalized_growth_cap",
    "cycle_adjusted_growth_estimate",
    "cycle_normalized_earnings_risk_score",
    "market_regime_status",
    "market_regime_score",
    "market_regime_allocation_adjustment",
    "market_regime_exposure_intensity",
    "market_regime_exposure_level",
    "market_regime_exposure",
    "market_regime_reason",
    "market_regime_guardrail",
    "sector_euphoria_status",
    "sector_euphoria_score",
    "sector_euphoria_dominant_sectors",
    "sector_euphoria_allocation_adjustment",
    "sector_euphoria_exposure_intensity",
    "sector_euphoria_exposure_level",
    "sector_euphoria_exposure",
    "sector_euphoria_reason",
    "sector_euphoria_guardrail",
    "double_counting_risk_level",
    "double_counting_overlap_score",
    "double_counting_adjustment",
    "double_counting_clusters",
    "double_counting_reason",
    "hidden_cluster_risk_level",
    "hidden_cluster_exposure",
    "hidden_cluster_clusters",
    "hidden_cluster_adjustment",
    "hidden_cluster_reason",
    "hidden_cluster_guardrail",
    "hidden_cluster_exception_applied",
    "allocation_stability_status",
    "allocation_stability_adjustment",
    "allocation_stability_reason",
    "previous_capital_allocation_score",
    "capital_allocation_score_change",
    "portfolio_valuation_source",
    "portfolio_valuation_warning",
    "current_price_cad",
    "current_value",
    "current_value_cad",
    "quote_currency",
    "quote_to_cad_rate",
    "average_cost_cad",
    "acquisition_value_cad",
    "average_cost_currency",
    "acquisition_value_currency",
    "current_value_currency",
    "shares",
    "average_cost",
    "average_cost_currency",
    "acquisition_value",
    "acquisition_value_currency",
    "unrealized_gain_amount",
    "unrealized_gain_percent",
    "personal_high_price",
    "drawdown_from_personal_high",
    "winner_protection_status",
    "winner_protection_action",
    "winner_protection_reason",
    "drawdown_12m",
    "position_weight",
    "data_quality",
    "data_reliability_score",
    "data_reliability_level",
    "auto_estimate_dependency",
    "automation_evidence_level",
    "data_fill_rate",
    "overall_data_freshness_level",
    "data_freshness_action",
    "market_data_freshness_level",
    "market_data_source",
    "market_data_fetched_at",
    "market_data_age_hours",
    "market_data_requires_refresh",
    "market_data_freshness_reason",
    "market_data_stale_cache_warning",
    "market_data_fetch_status",
    "market_data_fallback_level",
    "market_data_warning_flags",
    "market_data_fetch_attempts",
    "market_data_fetch_attempted_at",
    "market_data_circuit_breaker_open",
    "market_data_last_error",
    "last_known_good_at",
    "data_source_notes",
    "proxy_correction_status",
    "proxy_correction_fields",
    "proxy_corrections_applied",
    "manual_override_fields",
    "auto_estimated_fields",
    "field_provenance",
    "field_evidence_sources",
    "research_report_current_fields",
    "research_report_stale_fields",
    "research_report_unknown_date_fields",
    "research_report_field_freshness",
    "calibration_source",
    "calibration_source_date",
    "calibration_synced_fields",
    "calibration_current_fields",
    "calibration_stale_fields",
    "calibration_unknown_date_fields",
    "calibration_applied_fields",
    "calibration_ignored_fields",
    "calibration_field_freshness",
    "calibration_field_source_dates",
    "fundamental_evidence_conflict",
    "fundamental_evidence_conflict_fields",
    "fundamental_evidence_conflict_reason",
    "fundamental_fallback_fields",
    "official_data_sources",
    "official_fundamental_fields",
    "official_confirmed_fields",
    "official_supported_manual_fields",
    "official_confirmed_manual_fields",
    "official_evidence_level",
    "official_data_conflict_count",
    "official_technical_conflict_count",
    "official_material_conflict_count",
    "official_directional_conflict_count",
    "official_weighted_conflict_score",
    "official_conflict_profile",
    "official_data_conflicts",
    "official_source_policy",
    "canadian_data_sources",
    "canadian_fundamental_fields",
    "canadian_confirmed_fields",
    "canadian_data_conflicts",
    "canadian_source_policy",
    "canadian_coverage_status",
    "canadian_latest_period",
    "canadian_checked_at",
    "sec_edgar_cik",
    "sec_edgar_company_name",
    "sec_edgar_latest_filing_date",
    "sec_edgar_latest_fiscal_year",
    "research_report_sources",
    "research_report_fields",
    "research_report_field_confidence",
    "research_report_extraction_notes",
    "research_report_extraction_warnings",
    "research_report_text_quality_status",
    "research_report_text_quality_score",
    "research_report_extraction_method",
    "research_report_ocr_status",
    "research_report_freshness_level",
    "research_report_latest_date",
    "research_report_age_days",
    "research_report_requires_fresh_validation",
    "input_data_mode",
    "trend_status",
    "score_total_change",
    "conviction_score_change",
    "allocation_decision",
    "allocation_decision_reason",
    "sell_decision",
    "sell_decision_reason",
    "final_position_action",
    "final_position_reason",
    "decision",
    "forward_eps_growth_confidence",
    "data_source_forward",
    "eps_growth_5y_proxy_sanity",
]
_append_columns_once(SCORES_COLUMNS, ["data_confidence_badge", "canadian_tax_advantage_active"])
ALLOCATIONS_COLUMNS = [
    "ticker",
    "amount",
    "percentage",
    "reason",
    "confidence",
    "allocation_type",
    "reliability_cap_status",
    "reliability_cap_applied",
    "reliability_allocation_cap_percent",
    "reliability_allocation_cap_amount",
    "reliability_cap_reason",
    "capital_allocation_confidence_range",
    "capital_allocation_confidence_label",
    "single_name_concentration_status",
    "single_name_concentration_guardrail_applied",
    "single_name_concentration_current_weight",
    "single_name_concentration_monthly_cap",
    "single_name_concentration_target_cap",
    "single_name_concentration_reason",
    "decision_quality",
    "decision_quality_score",
    "decision_quality_reason",
]
_append_columns_once(ALLOCATIONS_COLUMNS, ["data_confidence_badge", "canadian_tax_advantage_active"])
SELL_SIGNALS_COLUMNS = [
    "ticker",
    "ticker_display",
    "resolved_ticker",
    "liquidation_status",
    "sell_status",
    "fundamental_sell_status",
    "monitoring_status",
    "monitoring_decision",
    "sell_decision",
    "allocation_decision",
    "final_position_action",
    "mechanical_sell_signal",
    "sell_review_required",
    "sell_signal_strength",
    "sell_signal_source_summary",
    "winner_protection_status",
    "winner_protection_action",
    "signals_detected",
    "confirmed_fundamental_sell_signals",
    "weak_or_unconfirmed_sell_signals",
    "technical_or_valuation_signals",
    "monitoring_reasons",
    "recommended_action",
]
WATCHLIST_COLUMNS = [
    "ticker",
    "ticker_display",
    "resolved_ticker",
    "score_total",
    "score_confidence_range",
    "score_confidence_label",
    "conviction_score",
    "conviction_confidence_range",
    "conviction_confidence_label",
    "expected_cagr_quality",
    "opportunity_cost_status",
    "benchmark_ticker",
    "benchmark_relevance_level",
    "ticker_validation_status",
    "ticker_coverage_status",
    "free_data_coverage_class",
    "suggested_yahoo_tickers",
    "cycle_bubble_risk_level",
    "cycle_bubble_score",
    "double_counting_risk_level",
    "double_counting_adjustment",
    "hidden_cluster_risk_level",
    "hidden_cluster_adjustment",
    "watchlist_status",
    "reason",
]
MARKET_CANDIDATE_COLUMNS = [
    "ticker",
    "ticker_display",
    "resolved_ticker",
    "company_name",
    "score_total",
    "score_confidence_range",
    "score_confidence_label",
    "conviction_score",
    "conviction_confidence_range",
    "conviction_confidence_label",
    "expected_cagr_quality",
    "opportunity_cost_status",
    "benchmark_ticker",
    "benchmark_relevance_level",
    "ticker_validation_status",
    "ticker_coverage_status",
    "free_data_coverage_class",
    "suggested_yahoo_tickers",
    "cycle_bubble_risk_level",
    "cycle_bubble_score",
    "double_counting_risk_level",
    "double_counting_adjustment",
    "hidden_cluster_risk_level",
    "hidden_cluster_adjustment",
    "candidate_status",
    "reason",
]
DATA_GAPS_BASE_COLUMNS = ["ticker", "data_field", "importance", "impact"]
DATA_GAPS_COLUMNS = [*DATA_GAPS_BASE_COLUMNS]
_append_columns_once(DATA_GAPS_COLUMNS, ["gap_resolvable_by"])
AUTO_ESTIMATES_COLUMNS = DATA_GAPS_BASE_COLUMNS + [
    "forward_eps",
    "trailing_eps",
    "number_of_analyst_opinions",
    "forward_eps_growth_direct",
    "forward_eps_growth_confidence",
    "data_source_forward",
    "eps_growth_5y_proxy_sanity",
    "early_deterioration_signal",
]
DATA_FRESHNESS_COLUMNS = [
    "ticker",
    "universe",
    "overall_data_freshness_level",
    "data_freshness_action",
    "market_data_freshness_level",
    "market_data_source",
    "market_data_fetched_at",
    "market_data_age_hours",
    "market_data_requires_refresh",
    "market_data_fetch_status",
    "market_data_fallback_level",
    "market_data_warning_flags",
    "market_data_circuit_breaker_open",
    "research_report_freshness_level",
    "research_report_latest_date",
    "research_report_age_days",
    "research_report_requires_fresh_validation",
    "reason",
]
RISK_COLUMNS = ["risk_type", "risk_level", "description", "impact"]
STRESS_TEST_COLUMNS = [
    "scenario",
    "scenario_type",
    "scenario_quality",
    "estimated_loss_dollars",
    "estimated_loss_percent",
    "max_drawdown_percent",
    "worst_phase_name",
    "worst_phase_return",
    "top_contributors",
    "amplifying_tickers",
    "resilient_tickers",
    "diagnostic_only",
    "primary_risk",
]
TAX_COLUMNS = ["ticker", "account_type", "account_tax_category", "shares", "current_value", "tax_comment", "warning"]
CYCLE_COLUMNS = [
    "universe",
    "ticker",
    "cycle_risk_profile",
    "cycle_bubble_risk_level",
    "cycle_bubble_score",
    "cycle_bubble_penalty",
    "allocation_multiplier",
    "cycle_normalized_status",
    "cycle_normalized_growth_cap",
    "cycle_adjusted_growth_estimate",
    "cycle_normalized_earnings_risk_score",
    "comment",
    "reasons",
]
DURABILITY_COLUMNS = [
    "universe",
    "ticker",
    "long_term_durability_score",
    "long_term_durability_status",
    "long_term_durability_reason",
    "expected_cagr_quality",
    "cycle_bubble_risk_level",
    "thesis_status",
    "data_reliability_level",
]

INSTRUMENT_PROFILE_REPORT_COLUMNS = [
    "ticker",
    "name",
    "instrument_type",
    "business_description",
    "sector_or_category",
    "industry",
    "revenue_model_or_activity",
    "portfolio_role",
    "key_watch_items",
    "top_holdings",
    "source",
    "source_confidence",
    "last_updated",
    "missing_fields",
    "profile_status",
]


def generate_reports(
    reports_dir: str | Path,
    mode: str,
    capital: float,
    analyses: dict[str, dict[str, Any]],
    allocation_result: dict[str, Any],
    portfolio_risk: dict[str, Any],
    stress_tests: list[dict[str, Any]],
    tax_report: list[dict[str, Any]],
    data_gaps: list[dict[str, Any]],
    validation_warnings: list[str],
    watchlist_analyses: dict[str, dict[str, Any]] | None = None,
    market_analyses: dict[str, dict[str, Any]] | None = None,
    market_universe: dict[str, dict[str, Any]] | None = None,
    discovery_analyses: dict[str, dict[str, Any]] | None = None,
    discovery_universe: dict[str, dict[str, Any]] | None = None,
    discovery_maintenance_rows: list[dict[str, Any]] | None = None,
    proxy_calibration_report: list[dict[str, Any]] | None = None,
    proxy_calibration_summary: list[dict[str, Any]] | None = None,
    proxy_calibration_history_rows: list[dict[str, Any]] | None = None,
    proxy_bias_rows: list[dict[str, Any]] | None = None,
    proxy_correction_audit_rows: list[dict[str, Any]] | None = None,
    allocation_change_rows: list[dict[str, Any]] | None = None,
    allocation_sensitivity: dict[str, Any] | None = None,
    validation_priority_rows: list[dict[str, Any]] | None = None,
    research_needed_rows: list[dict[str, Any]] | None = None,
    portfolio_change_rows: list[dict[str, Any]] | None = None,
    portfolio_change_history_rows: list[dict[str, Any]] | None = None,
    portfolio_change_summary_rows: list[dict[str, Any]] | None = None,
    portfolio_transaction_rows: list[dict[str, Any]] | None = None,
    portfolio_transaction_summary_rows: list[dict[str, Any]] | None = None,
    portfolio_inferred_transaction_rows: list[dict[str, Any]] | None = None,
    account_performance_rows: list[dict[str, Any]] | None = None,
    defensive_etf_candidates: list[dict[str, Any]] | None = None,
    market_regime: dict[str, Any] | None = None,
    thesis_reversal_rows: list[dict[str, Any]] | None = None,
    ticker_memory_rows: list[dict[str, Any]] | None = None,
    anomaly_rows: list[dict[str, Any]] | None = None,
    anomaly_history_rows: list[dict[str, Any]] | None = None,
    cache_health_rows: list[dict[str, Any]] | None = None,
    run_log_rows: list[dict[str, Any]] | None = None,
    walk_forward_signal: dict[str, str] | None = None,
    full_audit_signal: dict[str, str] | None = None,
    model_audit_signal: dict[str, str] | None = None,
    score_stability: dict[str, Any] | None = None,
    instrument_profile_rows: list[dict[str, Any]] | None = None,
) -> None:
    reports_dir = Path(reports_dir)
    reports_dir.mkdir(parents=True, exist_ok=True)
    watchlist_analyses = watchlist_analyses or {}
    market_analyses = market_analyses or {}
    market_universe = market_universe or {}
    discovery_analyses = discovery_analyses or {}
    discovery_universe = discovery_universe or {}
    discovery_maintenance_rows = discovery_maintenance_rows or []
    proxy_calibration_report = proxy_calibration_report or []
    proxy_calibration_summary = proxy_calibration_summary or []
    proxy_calibration_history_rows = proxy_calibration_history_rows or []
    proxy_bias_rows = proxy_bias_rows or []
    proxy_correction_audit_rows = proxy_correction_audit_rows or []
    allocation_change_rows = allocation_change_rows or []
    allocation_sensitivity = allocation_sensitivity or {}
    validation_priority_rows = validation_priority_rows or []
    research_needed_rows = research_needed_rows or []
    portfolio_change_rows = portfolio_change_rows or []
    portfolio_change_history_rows = portfolio_change_history_rows or []
    portfolio_change_summary_rows = portfolio_change_summary_rows or []
    portfolio_transaction_rows = portfolio_transaction_rows or []
    portfolio_transaction_summary_rows = portfolio_transaction_summary_rows or []
    portfolio_inferred_transaction_rows = portfolio_inferred_transaction_rows or []
    account_performance_rows = account_performance_rows or []
    defensive_etf_candidates = defensive_etf_candidates or []
    market_regime = market_regime or {}
    thesis_reversal_rows = thesis_reversal_rows or []
    ticker_memory_rows = ticker_memory_rows or []
    anomaly_rows = anomaly_rows or []
    anomaly_history_rows = anomaly_history_rows or []
    cache_health_rows = cache_health_rows or []
    run_log_rows = run_log_rows or []
    walk_forward_signal = walk_forward_signal or {}
    full_audit_signal = full_audit_signal or {}
    model_audit_signal = model_audit_signal or {}
    score_stability = score_stability or {}
    instrument_profile_rows = instrument_profile_rows or []
    allocation_lookup = {**analyses, **watchlist_analyses, **market_analyses, **discovery_analyses}
    source_conflict_rows = build_source_conflict_rows(
        {
            "CORE_PORTFOLIO": analyses,
            "WATCHLIST": watchlist_analyses,
            "MARKET_SCANNER": market_analyses,
            "DISCOVERY_IDEAS": discovery_analyses,
        }
    )
    source_health_history_path = DATA_DIR / "source_health_history.csv"
    source_health_rows = build_source_health_rows(
        {
            "CORE_PORTFOLIO": analyses,
            "WATCHLIST": watchlist_analyses,
            "MARKET_SCANNER": market_analyses,
            "DISCOVERY_IDEAS": discovery_analyses,
        },
        mode=mode,
        history_rows=read_csv_records(source_health_history_path),
    )
    source_health_history_rows = update_source_health_history(source_health_history_path, source_health_rows, mode=mode)
    run_log_rows = extend_report_run_log(
        run_log_rows,
        source_health_rows=source_health_rows,
        source_conflict_rows=source_conflict_rows,
        ticker_memory_rows=ticker_memory_rows,
    )
    account_chart_rows = build_account_allocation_chart_rows(tax_report, reports_dir / "charts")
    allocation_rows = allocation_rows_for_csv(allocation_result.get("allocations", []))
    qualitative_moat_rows = build_qualitative_moat_rows(
        allocation_lookup,
        allocation_rows,
    )
    company_dossier_rows = build_company_dossier_rows(allocation_lookup, allocation_rows, qualitative_moat_rows)
    weakest_core_audit_rows = build_weakest_core_audit_rows(analyses)

    markdown = build_markdown_report(
        mode,
        capital,
        analyses,
        allocation_result,
        portfolio_risk,
        stress_tests,
        tax_report,
        data_gaps,
        validation_warnings,
        watchlist_analyses,
        market_analyses,
        market_universe,
        discovery_analyses,
        discovery_universe,
        discovery_maintenance_rows,
        proxy_calibration_report,
        proxy_calibration_summary,
        proxy_correction_audit_rows,
        allocation_change_rows,
        allocation_sensitivity,
        validation_priority_rows,
        portfolio_change_rows,
        portfolio_change_history_rows,
        portfolio_change_summary_rows,
        portfolio_transaction_rows,
        portfolio_transaction_summary_rows,
        portfolio_inferred_transaction_rows,
        account_performance_rows,
        account_chart_rows,
        qualitative_moat_rows,
        company_dossier_rows,
        defensive_etf_candidates,
        market_regime,
        thesis_reversal_rows,
        source_health_rows,
        source_conflict_rows,
        ticker_memory_rows,
        anomaly_rows,
        cache_health_rows,
        run_log_rows,
        instrument_profile_rows,
    )
    write_text(reports_dir / "latest_report.md", markdown)
    write_text(reports_dir / "latest_report.html", markdown_to_html(markdown))
    compact_markdown = build_compact_markdown_report(
        mode=mode,
        capital=capital,
        analyses=analyses,
        allocation_result=allocation_result,
        portfolio_risk=portfolio_risk,
        tax_report=tax_report,
        validation_warnings=validation_warnings,
        watchlist_analyses=watchlist_analyses,
        market_analyses=market_analyses,
        market_universe=market_universe,
        discovery_analyses=discovery_analyses,
        discovery_universe=discovery_universe,
        proxy_calibration_summary=proxy_calibration_summary,
        proxy_correction_audit_rows=proxy_correction_audit_rows,
        allocation_change_rows=allocation_change_rows,
        allocation_sensitivity=allocation_sensitivity,
        validation_priority_rows=validation_priority_rows,
        research_needed_rows=research_needed_rows,
        portfolio_change_rows=portfolio_change_rows,
        portfolio_change_history_rows=portfolio_change_history_rows,
        portfolio_change_summary_rows=portfolio_change_summary_rows,
        account_performance_rows=account_performance_rows,
        account_chart_rows=account_chart_rows,
        qualitative_moat_rows=qualitative_moat_rows,
        company_dossier_rows=company_dossier_rows,
        defensive_etf_candidates=defensive_etf_candidates,
        market_regime=market_regime,
        thesis_reversal_rows=thesis_reversal_rows,
        source_health_rows=source_health_rows,
        source_conflict_rows=source_conflict_rows,
        ticker_memory_rows=ticker_memory_rows,
        anomaly_rows=anomaly_rows,
        cache_health_rows=cache_health_rows,
        run_log_rows=run_log_rows,
        weakest_core_audit_rows=weakest_core_audit_rows,
        walk_forward_signal=walk_forward_signal,
        full_audit_signal=full_audit_signal,
        model_audit_signal=model_audit_signal,
        score_stability=score_stability,
        instrument_profile_rows=instrument_profile_rows,
    )
    write_text(reports_dir / "latest_report_compact.md", compact_markdown)
    write_text(reports_dir / "latest_report_compact.html", markdown_to_html(compact_markdown))
    write_scores_csv(reports_dir / "latest_scores.csv", analyses)
    write_allocations_csv(reports_dir / "latest_allocations.csv", allocation_result.get("allocations", []))
    write_allocation_change_csv(reports_dir / "latest_allocation_changes.csv", allocation_change_rows)
    write_allocation_sensitivity_csv(reports_dir / "latest_allocation_sensitivity.csv", allocation_sensitivity.get("rows", []))
    write_allocation_sensitivity_summary_csv(
        reports_dir / "latest_allocation_sensitivity_summary.csv",
        allocation_sensitivity.get("summary", {}),
    )
    write_decision_quality_csv(reports_dir / "latest_decision_quality.csv", allocation_result.get("decision_quality", {}))
    write_sell_signals_csv(reports_dir / "latest_sell_signals.csv", analyses)
    write_csv_records(
        reports_dir / "latest_sell_validation_checklist.csv",
        sell_validation_checklist_rows(analyses, tax_report, active_only=False),
        SELL_VALIDATION_CHECKLIST_COLUMNS,
    )
    write_csv_records(
        reports_dir / "latest_quality_drawdown_report.csv",
        quality_drawdown_rows_for_csv(analyses, watchlist_analyses, market_analyses, discovery_analyses),
        QUALITY_DRAWDOWN_COLUMNS,
    )
    write_watchlist_csv(reports_dir / "latest_watchlist_report.csv", watchlist_analyses)
    write_market_candidates_csv(reports_dir / "latest_market_candidates.csv", market_analyses, market_universe)
    write_discovery_ideas_csv(reports_dir / "latest_discovery_ideas.csv", discovery_analyses, discovery_universe)
    write_csv_records(reports_dir / "latest_discovery_maintenance.csv", discovery_maintenance_rows, DISCOVERY_MAINTENANCE_COLUMNS)
    write_auto_estimates_csv(reports_dir / "latest_auto_estimates.csv", data_gaps)
    write_promotion_candidates_csv(
        reports_dir / "latest_promotion_candidates.csv",
        watchlist_analyses,
        market_analyses,
        analyses,
        portfolio_risk,
        market_universe,
    )
    write_csv_records(
        reports_dir / "latest_weakest_core_audit.csv",
        weakest_core_audit_rows,
        WEAKEST_CORE_AUDIT_COLUMNS,
    )
    write_trend_csv(reports_dir / "latest_trend_report.csv", analyses, watchlist_analyses, market_analyses)
    write_csv_records(
        reports_dir / "latest_winner_protection_report.csv",
        winner_protection_rows(analyses),
        WINNER_PROTECTION_COLUMNS,
    )
    write_csv_records(
        reports_dir / "latest_cycle_bubble_report.csv",
        cycle_risk_rows(analyses, watchlist_analyses, market_analyses),
        CYCLE_COLUMNS,
    )
    write_market_regime_csvs(
        reports_dir,
        market_regime,
        ("CORE_PORTFOLIO", analyses),
        ("WATCHLIST", watchlist_analyses),
        ("MARKET_SCANNER", market_analyses),
        ("DISCOVERY_IDEAS", discovery_analyses),
    )
    write_csv_records(reports_dir / "latest_thesis_reversal_audit.csv", thesis_reversal_rows, THESIS_REVERSAL_COLUMNS)
    write_csv_records(
        reports_dir / "latest_long_term_durability_report.csv",
        durability_rows_for_csv(analyses, watchlist_analyses, market_analyses, discovery_analyses),
        DURABILITY_COLUMNS,
    )
    write_csv_records(
        reports_dir / "latest_market_growth_thesis_report.csv",
        market_growth_thesis_rows_for_csv(analyses, watchlist_analyses, market_analyses, discovery_analyses),
        MARKET_GROWTH_THESIS_COLUMNS,
    )
    write_csv_records(
        reports_dir / "latest_cash_flow_quality_report.csv",
        cash_flow_rows_for_csv(analyses, watchlist_analyses, market_analyses, discovery_analyses),
        CASH_FLOW_QUALITY_COLUMNS,
    )
    write_csv_records(
        reports_dir / "latest_shareholder_discipline_report.csv",
        shareholder_discipline_rows_for_csv(analyses, watchlist_analyses, market_analyses, discovery_analyses),
        SHAREHOLDER_DISCIPLINE_COLUMNS,
    )
    write_data_freshness_csv(reports_dir / "latest_data_freshness.csv", analyses, watchlist_analyses, market_analyses, discovery_analyses)
    write_proxy_calibration_csv(reports_dir / "latest_proxy_calibration.csv", proxy_calibration_report)
    write_proxy_calibration_summary_csv(reports_dir / "latest_proxy_calibration_summary.csv", proxy_calibration_summary)
    write_csv_records(
        reports_dir / "latest_proxy_calibration_history.csv",
        proxy_calibration_history_rows,
        PROXY_CALIBRATION_HISTORY_COLUMNS,
    )
    write_csv_records(reports_dir / "latest_proxy_bias_report.csv", proxy_bias_rows, PROXY_BIAS_COLUMNS)
    write_csv_records(
        reports_dir / "latest_proxy_correction_audit.csv",
        proxy_correction_audit_rows,
        PROXY_CORRECTION_AUDIT_COLUMNS,
    )
    write_ticker_issues_csv(reports_dir / "latest_ticker_issues.csv", analyses, watchlist_analyses, market_analyses)
    write_validation_priority_csv(reports_dir / "latest_validation_priority.csv", validation_priority_rows)
    write_data_gaps_csv(reports_dir / "latest_data_gaps.csv", data_gaps)
    write_risk_csv(reports_dir / "latest_risk_report.csv", portfolio_risk)
    write_csv_records(reports_dir / "latest_stress_tests.csv", stress_rows_for_csv(stress_tests), STRESS_TEST_COLUMNS)
    write_tax_csv(reports_dir / "latest_tax_location_report.csv", tax_report)
    write_csv_records(reports_dir / "latest_portfolio_changes.csv", portfolio_change_rows, PORTFOLIO_CHANGE_COLUMNS)
    write_csv_records(
        reports_dir / "latest_portfolio_change_history.csv",
        portfolio_change_history_rows,
        PORTFOLIO_CHANGE_COLUMNS,
    )
    write_csv_records(
        reports_dir / "latest_portfolio_change_summary.csv",
        portfolio_change_summary_rows,
        PORTFOLIO_CHANGE_SUMMARY_COLUMNS,
    )
    write_csv_records(
        reports_dir / "latest_portfolio_transactions.csv",
        portfolio_transaction_rows,
        PORTFOLIO_TRANSACTION_REPORT_COLUMNS,
    )
    write_csv_records(
        reports_dir / "latest_portfolio_transaction_summary.csv",
        portfolio_transaction_summary_rows,
        PORTFOLIO_TRANSACTION_SUMMARY_COLUMNS,
    )
    write_csv_records(
        reports_dir / "latest_portfolio_inferred_transactions.csv",
        portfolio_inferred_transaction_rows,
        INFERRED_TRANSACTION_COLUMNS,
    )
    write_csv_records(
        reports_dir / "latest_account_allocation_charts.csv",
        account_chart_rows,
        ACCOUNT_CHART_COLUMNS,
    )
    write_csv_records(
        reports_dir / "latest_account_performance_vs_sp500.csv",
        account_performance_rows,
        ACCOUNT_PERFORMANCE_COLUMNS,
    )
    write_csv_records(
        reports_dir / "latest_qualitative_moat_report.csv",
        qualitative_moat_rows,
        QUALITATIVE_MOAT_COLUMNS,
    )
    write_csv_records(
        reports_dir / "latest_company_dossiers.csv",
        company_dossier_rows,
        COMPANY_DOSSIER_COLUMNS,
    )
    write_csv_records(
        reports_dir / "latest_instrument_profiles.csv",
        instrument_profile_rows,
        INSTRUMENT_PROFILE_REPORT_COLUMNS,
    )
    write_csv_records(
        reports_dir / "latest_defensive_etf_fallback.csv",
        defensive_etf_rows_for_csv(defensive_etf_candidates),
        DEFENSIVE_ETF_COLUMNS,
    )
    write_csv_records(
        reports_dir / "latest_external_etf_candidates.csv",
        external_etf_rows_for_csv(watchlist_analyses, market_analyses, discovery_analyses),
        EXTERNAL_ETF_COLUMNS,
    )
    write_csv_records(reports_dir / "latest_source_health.csv", source_health_rows, SOURCE_HEALTH_COLUMNS)
    write_csv_records(
        reports_dir / "latest_source_health_history.csv",
        source_health_history_rows,
        SOURCE_HEALTH_HISTORY_COLUMNS,
    )
    write_csv_records(reports_dir / "latest_source_conflicts.csv", source_conflict_rows, SOURCE_CONFLICT_COLUMNS)
    write_csv_records(reports_dir / "latest_ticker_memory.csv", ticker_memory_rows, TICKER_MEMORY_COLUMNS)
    write_csv_records(reports_dir / "latest_anomaly_report.csv", anomaly_rows, ANOMALY_COLUMNS)
    write_csv_records(reports_dir / "latest_anomaly_history.csv", anomaly_history_rows, ANOMALY_COLUMNS)
    write_csv_records(reports_dir / "latest_cache_health.csv", cache_health_rows, CACHE_HEALTH_COLUMNS)
    write_csv_records(reports_dir / "latest_run_log.csv", run_log_rows, RUN_LOG_COLUMNS)
    append_run_log_history(DATA_DIR / "run_log_history.csv", run_log_rows)
    snapshot_allocation_result = {
        **allocation_result,
        "monthly_contribution": capital,
        "portfolio_total_value_cad": portfolio_risk.get("total_portfolio_value"),
        "decision_quality_score": (allocation_result.get("decision_quality") or {}).get("decision_quality_score"),
        "decision_quality_label": (allocation_result.get("decision_quality") or {}).get("decision_quality_level"),
        "robustness_score": (allocation_sensitivity.get("summary") or {}).get("robustness_score"),
        "robustness_label": (allocation_sensitivity.get("summary") or {}).get("robustness_status"),
    }
    save_audit_snapshot(
        reports_dir=reports_dir,
        analysis_mode=mode,
        allocation_result=snapshot_allocation_result,
        anomaly_rows=anomaly_rows,
        validation_priority_rows=validation_priority_rows,
        run_log_rows=run_log_rows,
    )
    _mirror_mode_specific_report_outputs(reports_dir, mode)


def _report_mode_slug(mode: str | None) -> str:
    return {
        "balanced": "balanced",
        "family-office": "family_office",
        "rational-aggressive": "rational_aggressive",
        "high-cagr": "high_cagr",
    }.get(str(mode or "").strip(), str(mode or "").strip().replace("-", "_"))


def _mode_report_path(path: Path, mode: str | None) -> Path:
    slug = _report_mode_slug(mode)
    if not slug:
        return path
    return path.with_name(f"{path.stem}_{slug}{path.suffix}")


def _mirror_mode_specific_report_outputs(reports_dir: Path, mode: str | None) -> None:
    for filename in _MODE_SCOPED_REPORT_OUTPUTS:
        source = reports_dir / filename
        if not source.exists():
            continue
        target = _mode_report_path(source, mode)
        target.write_bytes(source.read_bytes())


_MODE_SCOPED_REPORT_OUTPUTS = [
    "latest_report.md",
    "latest_report.html",
    "latest_report_compact.md",
    "latest_report_compact.html",
    "latest_scores.csv",
    "latest_allocations.csv",
    "latest_allocation_changes.csv",
    "latest_allocation_sensitivity.csv",
    "latest_allocation_sensitivity_summary.csv",
    "latest_decision_quality.csv",
    "latest_sell_signals.csv",
    "latest_sell_validation_checklist.csv",
    "latest_quality_drawdown_report.csv",
    "latest_watchlist_report.csv",
    "latest_market_candidates.csv",
    "latest_discovery_ideas.csv",
    "latest_promotion_candidates.csv",
    "latest_weakest_core_audit.csv",
    "latest_trend_report.csv",
    "latest_winner_protection_report.csv",
    "latest_cycle_bubble_report.csv",
    "latest_thesis_reversal_audit.csv",
    "latest_long_term_durability_report.csv",
    "latest_market_growth_thesis_report.csv",
    "latest_cash_flow_quality_report.csv",
    "latest_shareholder_discipline_report.csv",
    "latest_data_freshness.csv",
    "latest_data_gaps.csv",
    "latest_risk_report.csv",
    "latest_stress_tests.csv",
    "latest_tax_location_report.csv",
    "latest_account_performance_vs_sp500.csv",
    "latest_qualitative_moat_report.csv",
    "latest_company_dossiers.csv",
    "latest_instrument_profiles.csv",
    "latest_defensive_etf_fallback.csv",
    "latest_external_etf_candidates.csv",
    "latest_anomaly_report.csv",
    "latest_validation_priority.csv",
]


def data_coverage_summary_rows(analyses: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    if not analyses:
        return []
    badges = [str(row.get("data_confidence_badge") or "").strip().upper() for row in analyses.values()]
    badges = [badge for badge in badges if badge]
    if not badges:
        return []

    non_etf_badges = [badge for badge in badges if badge != "ETF_N/A"]
    non_etf_total = len(non_etf_badges)
    labels = {
        "STRONG": "Données solides: sources directes ou très bonne fiabilité.",
        "MODERATE": "Données utilisables, mais avec quelques limites ou estimations.",
        "WEAK": "Données faibles: prudence avant grosse décision.",
        "PROXY_ONLY": "Principalement estimé: à confirmer manuellement si le titre devient important.",
        "ETF_N/A": "ETF/FNB: exclu du score de couverture d'entreprise.",
    }
    rows = []
    for badge in ["STRONG", "MODERATE", "WEAK", "PROXY_ONLY"]:
        count = non_etf_badges.count(badge)
        if count == 0 and badge not in set(non_etf_badges):
            continue
        rows.append(
            {
                "niveau": badge,
                "titres": count,
                "% hors ETF": pct(count / non_etf_total, 0) if non_etf_total else "N/D",
                "lecture": labels[badge],
            }
        )
    etf_count = badges.count("ETF_N/A")
    if etf_count:
        rows.append(
            {
                "niveau": "ETF_N/A",
                "titres": etf_count,
                "% hors ETF": "exclu",
                "lecture": labels["ETF_N/A"],
            }
        )
    return rows


def data_coverage_summary_block(analyses: dict[str, dict[str, Any]]) -> list[str]:
    rows = data_coverage_summary_rows(analyses)
    if not rows:
        return []
    return [
        "## Couverture des données",
        "",
        "Lecture rapide de la qualité des données utilisées pour les positions du portefeuille. Les ETF/FNB sont exclus des pourcentages parce qu’ils ne se scorent pas comme des entreprises.",
        "",
        _markdown_table(["niveau", "titres", "% hors ETF", "lecture"], rows),
        "",
    ]


def build_compact_markdown_report(
    *,
    mode: str,
    capital: float,
    analyses: dict[str, dict[str, Any]],
    allocation_result: dict[str, Any],
    portfolio_risk: dict[str, Any],
    tax_report: list[dict[str, Any]],
    validation_warnings: list[str],
    watchlist_analyses: dict[str, dict[str, Any]],
    market_analyses: dict[str, dict[str, Any]],
    market_universe: dict[str, dict[str, Any]],
    discovery_analyses: dict[str, dict[str, Any]],
    discovery_universe: dict[str, dict[str, Any]],
    proxy_calibration_summary: list[dict[str, Any]],
    proxy_correction_audit_rows: list[dict[str, Any]],
    allocation_change_rows: list[dict[str, Any]],
    allocation_sensitivity: dict[str, Any],
    validation_priority_rows: list[dict[str, Any]],
    research_needed_rows: list[dict[str, Any]],
    portfolio_change_rows: list[dict[str, Any]],
    portfolio_change_history_rows: list[dict[str, Any]],
    portfolio_change_summary_rows: list[dict[str, Any]],
    account_performance_rows: list[dict[str, Any]],
    account_chart_rows: list[dict[str, Any]],
    qualitative_moat_rows: list[dict[str, Any]] | None = None,
    company_dossier_rows: list[dict[str, Any]] | None = None,
    defensive_etf_candidates: list[dict[str, Any]] | None = None,
    market_regime: dict[str, Any] | None = None,
    thesis_reversal_rows: list[dict[str, Any]] | None = None,
    source_health_rows: list[dict[str, Any]] | None = None,
    source_conflict_rows: list[dict[str, Any]] | None = None,
    ticker_memory_rows: list[dict[str, Any]] | None = None,
    anomaly_rows: list[dict[str, Any]] | None = None,
    cache_health_rows: list[dict[str, Any]] | None = None,
    run_log_rows: list[dict[str, Any]] | None = None,
    weakest_core_audit_rows: list[dict[str, Any]] | None = None,
    walk_forward_signal: dict[str, str] | None = None,
    full_audit_signal: dict[str, str] | None = None,
    model_audit_signal: dict[str, str] | None = None,
    score_stability: dict[str, Any] | None = None,
    instrument_profile_rows: list[dict[str, Any]] | None = None,
) -> str:
    allocation_rows = allocation_rows_for_csv(allocation_result.get("allocations", []))
    allocation_lookup = {**analyses, **watchlist_analyses, **market_analyses, **discovery_analyses}
    external_policy_note = _external_allocation_policy_note(mode)
    qualitative_moat_rows = qualitative_moat_rows or []
    company_dossier_rows = company_dossier_rows or build_company_dossier_rows(allocation_lookup, allocation_rows, qualitative_moat_rows)
    market_regime = market_regime or {}
    thesis_reversal_rows = thesis_reversal_rows or []
    source_health_rows = source_health_rows or []
    source_conflict_rows = source_conflict_rows or []
    ticker_memory_rows = ticker_memory_rows or []
    anomaly_rows = anomaly_rows or []
    cache_health_rows = cache_health_rows or []
    run_log_rows = run_log_rows or []
    weakest_core_audit_rows = weakest_core_audit_rows or []
    walk_forward_signal = walk_forward_signal or {}
    full_audit_signal = full_audit_signal or {}
    model_audit_signal = model_audit_signal or {}
    score_stability = score_stability or {}
    instrument_profile_rows = instrument_profile_rows or []
    allocated_tickers = {row.get("ticker") for row in allocation_rows if row.get("ticker")}
    sorted_core = sorted(analyses.values(), key=lambda row: safe_float(row.get("capital_allocation_score")) or 0.0, reverse=True)
    sell_rows = sell_signal_rows_for_csv(analyses)
    triage_block = build_triage_header(
        mode=mode,
        allocation_result=allocation_result,
        sell_rows=sell_rows,
        validation_priority_rows=validation_priority_rows,
        anomaly_rows=anomaly_rows,
        analyses=analyses,
        watchlist_analyses=watchlist_analyses,
        market_analyses=market_analyses,
        discovery_analyses=discovery_analyses,
        score_stability=score_stability,
        walk_forward_status=walk_forward_signal,
        research_needed_rows=research_needed_rows,
    )
    sell_report_rows = compact_sell_rows(sell_rows_for_report(_display_rows(sell_rows)), limit=8)
    sell_validation_rows = compact_sell_validation_rows_for_compact_report(
        sell_validation_checklist_rows(analyses, tax_report),
        limit=8,
    )
    score_evidence_display_rows = compact_score_evidence_rows(sorted_core, allocated_tickers, limit=8)
    double_counting_display_rows = compact_double_counting_rows(sorted_core, allocated_tickers, limit=8)
    hidden_cluster_display_rows = compact_hidden_cluster_rows(sorted_core, allocated_tickers, limit=8)
    sell_recommendation_text_lines = sell_recommendation_narrative_lines(analyses, company_dossier_rows)
    monitoring_rows = compact_monitoring_rows(monitoring_rows_for_report(_display_rows(sell_rows)), allocated_tickers, limit=8)
    quality_drawdown_rows = compact_quality_drawdown_rows(
        quality_drawdown_rows_for_csv(analyses, watchlist_analyses, market_analyses, discovery_analyses),
        allocated_tickers,
        limit=8,
    )
    market_growth_rows = compact_market_growth_rows_for_compact_report(
        market_growth_thesis_rows_for_csv(analyses, watchlist_analyses, market_analyses, discovery_analyses),
        allocated_tickers,
        limit=8,
    )
    core_rows = compact_core_for_compact_report(sorted_core, allocated_tickers)
    allocation_change_display_rows = _display_rows(allocation_change_rows_for_report(allocation_change_rows))[:8]
    allocation_justification_rows = _display_rows(
        allocation_justification_rows_for_report(
            allocation_rows,
            allocation_lookup,
            allocation_change_rows,
            portfolio_change_rows,
            portfolio_change_history_rows,
        )
    )
    allocation_recommendation_text = allocation_recommendation_narrative(
        allocation_rows,
        allocation_lookup,
        allocation_change_rows,
        qualitative_moat_rows,
        company_dossier_rows,
    )
    company_dossier_display_rows = compact_company_dossier_rows_for_report(company_dossier_rows or [], limit=8)
    sensitivity_summary_rows = _sensitivity_summary_rows_for_display(
        sensitivity_summary_rows_for_report(allocation_sensitivity or {})
    )
    decision_quality = allocation_result.get("decision_quality", {}) or {}
    raw_data_freshness_rows = data_freshness_rows_for_report(
        data_freshness_rows_for_csv(analyses, watchlist_analyses, market_analyses, discovery_analyses)
    )
    compact_decision_section = build_compact_decision_section(
        allocation_result=allocation_result,
        allocation_change_rows=allocation_change_rows,
        analyses=analyses,
        watchlist_analyses=watchlist_analyses,
        market_analyses=market_analyses,
        discovery_analyses=discovery_analyses,
        instrument_profiles=instrument_profile_rows,
        decision_quality=decision_quality,
    )
    compact_model_health_section = build_compact_model_health_section(
        score_stability=score_stability,
        walk_forward_status=walk_forward_signal,
        full_audit_status=full_audit_signal,
        model_audit_status=model_audit_signal,
        decision_quality=decision_quality,
        allocation_result=allocation_result,
        data_freshness_rows=raw_data_freshness_rows,
    )
    compact_data_reliability_section = build_compact_data_reliability_section(
        analyses=analyses,
        watchlist_analyses=watchlist_analyses,
        source_health_rows=source_health_rows,
        source_conflict_rows=source_conflict_rows,
        data_freshness_rows=raw_data_freshness_rows,
        validation_priority_rows=validation_priority_rows,
    )
    raw_validation_priority_rows = validation_priority_rows_for_report(validation_priority_rows)
    validation_priority_display_rows = compact_validation_priority_for_compact_report(raw_validation_priority_rows)
    risk_display_rows = compact_risk_for_compact_report(portfolio_risk)
    sector_concentration_rows = compact_portfolio_risk_weight_rows(
        portfolio_risk.get("concentration_by_sector", {}),
        label_key="secteur",
        category="sector",
        limit=10,
    )
    region_concentration_rows = compact_portfolio_risk_weight_rows(
        portfolio_risk.get("concentration_by_region", {}),
        label_key="région",
        category="region",
        limit=8,
    )
    factor_exposure_rows = compact_portfolio_risk_weight_rows(
        portfolio_risk.get("factor_exposure", {}),
        label_key="facteur",
        category="factor",
        limit=12,
    )
    tax_alert_rows = compact_tax_for_compact_report(tax_report)
    account_performance_display_rows = compact_account_performance_for_compact_report(account_performance_rows)
    portfolio_change_display_rows = compact_portfolio_changes_for_compact_report(
        portfolio_change_rows,
        portfolio_change_history_rows,
    )
    portfolio_change_summary_display_rows = compact_portfolio_change_summary_for_compact_report(portfolio_change_summary_rows)
    account_allocation_display_rows = compact_account_allocation_for_compact_report(account_chart_rows)
    proxy_summary_rows = compact_proxy_summary_for_compact_report(proxy_calibration_summary_rows_for_report(proxy_calibration_summary))
    proxy_correction_display_rows = compact_proxy_correction_audit_rows(proxy_correction_audit_rows)
    promotion_rows = build_promotion_candidate_rows(watchlist_analyses, market_analyses, analyses, portfolio_risk, market_universe)
    promotion_display_rows = compact_promotion_rows_for_compact_report(promotion_recommendation_rows(promotion_rows))
    external_rows = compact_external_candidates_for_compact_report(
        watchlist_analyses,
        market_analyses,
        market_universe,
        discovery_analyses,
        discovery_universe,
        analyses,
        portfolio_risk,
    )
    blocked_external_validation_rows, _ = (
        _blocked_external_validation_rows_for_compact_report(
            watchlist_analyses,
            market_analyses,
            discovery_analyses,
        )
    )
    source_display_rows = compact_source_rows_for_compact_report(
        source_rows_for_report(analyses, watchlist_analyses, market_analyses, discovery_analyses)
    )
    source_health_display_rows = compact_source_health_rows(source_health_rows)
    source_conflict_display_rows = compact_source_conflict_rows(source_conflict_rows)
    ticker_memory_display_rows = compact_ticker_memory_rows(ticker_memory_rows, limit=8)
    anomaly_display_rows = anomaly_rows_for_report(anomaly_rows, limit=8)
    cache_health_display_rows = compact_cache_health_rows(cache_health_rows, limit=8)
    run_log_display_rows = [
        row
        for row in run_log_rows_for_report(run_log_rows, limit=8)
        if str(row.get("événement") or row.get("event") or "").strip().upper()
        != "HIGH_PRIORITY_VALIDATION"
    ]
    data_freshness_display_rows = compact_data_freshness_rows(
        _display_rows(raw_data_freshness_rows),
        allocated_tickers,
        limit=8,
    )
    defensive_summary = defensive_fallback_summary(defensive_etf_candidates or [], mode)
    external_etf_display_rows = compact_external_etf_rows_for_report(
        external_etf_rows_for_csv(watchlist_analyses, market_analyses, discovery_analyses)
    )
    market_regime_display_rows = market_regime_rows(market_regime)
    market_regime_analysis_display_rows = compact_market_regime_analysis_rows(
        market_regime_analysis_rows(
            ("CORE_PORTFOLIO", analyses),
            ("WATCHLIST", watchlist_analyses),
            ("MARKET_SCANNER", market_analyses),
            ("DISCOVERY_IDEAS", discovery_analyses),
        )
    )
    sector_euphoria = market_regime.get("sector_euphoria", {}) if isinstance(market_regime.get("sector_euphoria"), dict) else {}
    sector_euphoria_display_rows = sector_euphoria_rows(market_regime)
    sector_euphoria_analysis_display_rows = compact_sector_euphoria_analysis_rows(
        sector_euphoria_analysis_rows(
            ("CORE_PORTFOLIO", analyses),
            ("WATCHLIST", watchlist_analyses),
            ("MARKET_SCANNER", market_analyses),
            ("DISCOVERY_IDEAS", discovery_analyses),
        )
    )
    recent_guardrail_rows = compact_recent_guardrail_rows(
        allocation_rows,
        score_evidence_display_rows,
        double_counting_display_rows,
        hidden_cluster_display_rows,
    )

    short_justification_rows = [
        {
            "ticker": row.get("ticker"),
            "montant": row.get("montant"),
            "pourquoi_ce_titre": _compact_sentence(row.get("pourquoi_ce_titre"), 180),
            "pourquoi_ce_montant": _compact_sentence(row.get("pourquoi_ce_montant"), 180),
            "vs_dernière_recommandation": _compact_sentence(row.get("vs_dernière_recommandation"), 150),
        }
        for row in allocation_justification_rows
    ]
    allocation_summary_paragraph = allocation_recommendation_text.split("\n\n", 1)[0]
    ranking_section = build_ranking_section(
        analyses,
        watchlist_analyses,
        market_analyses,
        discovery_analyses,
        top_n=15,
    )
    action_required_rows = []
    for row in sell_report_rows:
        status = str(row.get("statut_vente") or "").upper()
        action = str(row.get("action_recommandée") or "").upper()
        manual_review = str(row.get("validation_manuelle_requise") or "").strip().lower() == "oui"
        if (
            status in {"SELL", "ORANGE", "RED", "MANUAL_REVIEW"}
            or action in {"SELL", "TRIM_25", "TRIM_50", "REVIEW_TRIM_25", "REVIEW_TRIM_50", "LIQUIDATE_PROGRESSIVELY", "LIQUIDATE_URGENT_REVIEW"}
            or "LIQUIDATE" in action
            or "TRIM" in action
            or manual_review
        ):
            action_required_rows.append(
                {
                    "ticker": row.get("ticker"),
                    "statut": row.get("statut_vente"),
                    "raison_principale": row.get("raison_principale"),
                    "validation_manuelle_requise": row.get("validation_manuelle_requise"),
                }
            )
    for row in thesis_reversal_rows:
        if str(row.get("thesis_reversal_status") or "").upper() == "REVIEW":
            action_required_rows.append(
                {
                    "ticker": row.get("ticker_display") or row.get("ticker"),
                    "statut": "THESIS_REVERSAL_REVIEW",
                    "raison_principale": _compact_sentence(row.get("reason_fr"), 180),
                    "validation_manuelle_requise": "Oui",
                }
            )
    action_required_tickers = {str(row.get("ticker") or "") for row in action_required_rows if row.get("ticker")}
    sell_validation_action_rows = [
        row
        for row in sell_validation_rows
        if str(row.get("niveau") or "").upper() != "NO_SELL_SIGNAL"
        and str(row.get("ticker") or "") in action_required_tickers
    ]
    monitoring_active_rows = [
        row for row in monitoring_rows if str(row.get("statut_surveillance") or "").upper() not in {"", "NORMAL"}
    ]
    monitoring_summary_rows = compact_monitoring_summary_rows(monitoring_active_rows, limit=3)
    monitoring_extra_count = max(0, len(monitoring_active_rows) - len(monitoring_summary_rows))
    quality_drawdown_opportunity_rows = [
        row for row in quality_drawdown_rows if str(row.get("statut") or "").upper() == "QUALITY_DRAWDOWN_OPPORTUNITY"
    ]
    factor_exposure_over_20_rows = []
    for row in factor_exposure_rows:
        weight = safe_float(str(row.get("poids") or "").replace("%", "").replace(" ", "").replace(",", ".")) or 0.0
        if weight > 20.0:
            factor_exposure_over_20_rows.append(row)
    portfolio_change_action_rows = [
        row
        for row in portfolio_change_display_rows
        if str(row.get("changement") or "").upper() not in {"", "AUCUN_CHANGEMENT_DETECTE", "COST_BASIS_UPDATED"}
    ]
    portfolio_change_summary_active_rows = [
        row for row in portfolio_change_summary_display_rows if abs(safe_float(row.get("variation_nette")) or 0.0) > 0
    ]
    account_performance_sorted_rows = sorted(
        account_performance_display_rows,
        key=lambda row: (0 if str(row.get("account_type") or "").upper() == "ALL_ACCOUNTS" else 1, str(row.get("account_type") or "")),
    )
    account_performance_raw_sorted_rows = sorted(
        account_performance_rows or [],
        key=lambda row: (0 if str(row.get("account_type") or "").upper() == "ALL_ACCOUNTS" else 1, str(row.get("account_type") or "")),
    )
    compact_account_chart_lines = [
        line for line in compact_account_charts_markdown(account_chart_rows) if str(line).strip().startswith("![")
    ]
    compact_portfolio_section = build_compact_portfolio_section(
        account_performance_rows=account_performance_raw_sorted_rows,
        portfolio_change_rows=portfolio_change_action_rows or portfolio_change_display_rows,
        risk_rows=risk_display_rows,
        hidden_cluster_rows=hidden_cluster_display_rows,
        market_regime=market_regime,
        account_charts=compact_account_chart_lines,
        account_summary_rows=account_allocation_display_rows,
    )
    data_coverage_display_rows = data_coverage_summary_rows(analyses)
    priority_validation_rows = [
        row
        for row in validation_priority_display_rows
        if str(row.get("importance") or "").upper() in {"TRES_HAUTE", "TRÈS_HAUTE", "HAUTE", "HIGH", "CRITICAL"}
    ]
    critical_source_conflict_rows = [
        row for row in source_conflict_display_rows if str(row.get("severity") or "").upper() == "HIGH_REVIEW"
    ]
    run_log_warn_rows = [
        row for row in run_log_display_rows if str(row.get("niveau") or "").upper() in {"WARN", "ERROR"}
    ]
    ticker_memory_review_rows = [
        row for row in ticker_memory_display_rows if str(row.get("ticker_memory_status") or "").upper() == "NEEDS_TICKER_REVIEW"
    ]
    cache_problem_rows = [
        row for row in cache_health_display_rows if str(row.get("status") or "").upper() in {"WARN", "FAIL"}
    ]
    freshness_problem_rows = [
        row
        for row in data_freshness_display_rows
        if str(row.get("overall_data_freshness_level") or "").upper() not in {"", "OK", "LIVE_SUCCESS", "FRESH"}
        or "FALLBACK" in str(row.get("market_data_fetch_status") or "").upper()
    ]
    validation_warning_rows = [{"warning": item} for item in validation_warnings[:8]]

    def _compact_details_block(summary: str, content: list[str]) -> list[str]:
        return ["<details>", f"<summary>{summary}</summary>", "", *content, "", "</details>", ""]

    sell_section_lines = [
        "## Vente & surveillance",
        "",
        *(["🟢 Rien à vendre ou réduire maintenant.", ""] if not action_required_rows else []),
        *(
            [
                "### À faire maintenant",
                "",
                _markdown_table(
                    ["ticker", "statut", "raison_principale", "validation_manuelle_requise"],
                    action_required_rows,
                ),
                "",
            ]
            if action_required_rows
            else []
        ),
        *(
            [
                "#### Check-list avant vente",
                "",
                _markdown_table(["ticker", "niveau", "preuve_clé", "point_à_valider", "conclusion"], sell_validation_action_rows),
                "",
                *sell_recommendation_text_lines,
            ]
            if sell_validation_action_rows
            else []
        ),
        "### Surveillance",
        "",
        *(["🟢 Aucune surveillance active.", ""] if not monitoring_active_rows else []),
        *(
            [
                f"🟡 {len(monitoring_active_rows)} position(s) suivie(s), sans action de vente immédiate.",
                "",
                _markdown_table(["ticker", "consigne_simple", "raison_principale"], monitoring_summary_rows),
                "",
                *(
                    [f"+ {monitoring_extra_count} autre(s) position(s) suivie(s) dans le détail repliable.", ""]
                    if monitoring_extra_count
                    else []
                ),
                *_compact_details_block(
                    "Voir les signaux techniques détaillés",
                    [
                        _markdown_table(
                            ["ticker", "statut_surveillance", "raison_principale", "impact_sur_achat"],
                            monitoring_active_rows,
                        )
                    ],
                ),
                "",
            ]
            if monitoring_active_rows
            else []
        ),
    ]

    compact_external_section = build_compact_external_monitoring_section(
        mode=mode,
        allocation_result=allocation_result,
        core_analyses=analyses,
        watchlist_analyses=watchlist_analyses,
        market_analyses=market_analyses,
        discovery_analyses=discovery_analyses,
        external_candidate_rows=external_rows,
        blocked_validation_rows=blocked_external_validation_rows,
        promotion_rows=promotion_display_rows,
        external_etf_rows=external_etf_display_rows,
        policy_note=external_policy_note,
    )

    annex_a_lines = [
        "Lecture rapide de la qualité des données utilisées pour les positions du portefeuille. Les ETF/FNB sont exclus des pourcentages parce qu’ils ne se scorent pas comme des entreprises.",
        "",
        _markdown_table(["niveau", "titres", "% hors ETF", "lecture"], data_coverage_display_rows),
    ]
    annex_b_lines = [
        *(["🟢 Aucune donnée prioritaire ni conflit critique.", ""] if not priority_validation_rows and not critical_source_conflict_rows else []),
        *(
            [
                "#### Données à vérifier",
                "",
                _markdown_table(["ticker", "donnée", "importance", "pourquoi"], priority_validation_rows),
                "",
            ]
            if priority_validation_rows
            else []
        ),
        *(
            [
                "#### Conflits de sources",
                "",
                _markdown_table(
                    ["ticker", "universe", "severity", "conflict_count", "conflict_profile", "recommended_action"],
                    critical_source_conflict_rows,
                ),
            ]
            if critical_source_conflict_rows
            else []
        ),
    ]
    annex_c_lines = [
        *(["🟢 Aucune anomalie détectée.", ""] if not anomaly_display_rows else []),
        *(
            [
                _markdown_table(["scope", "ticker", "niveau", "signal", "metrique", "variation", "lecture", "action"], anomaly_display_rows),
            ]
            if anomaly_display_rows
            else []
        ),
    ]
    annex_d_lines = [
        *(["🟢 Journal propre — aucun avertissement.", ""] if not run_log_warn_rows else []),
        *(
            [
                _markdown_table(["niveau", "composant", "événement", "message", "action"], run_log_warn_rows),
                "",
            ]
            if run_log_warn_rows
            else []
        ),
        *(
            [
                "#### Mémoire ticker à revoir",
                "",
                _markdown_table(["ticker", "ticker_memory_status", "sector", "region", "currency", "ticker_memory_action"], ticker_memory_review_rows),
            ]
            if ticker_memory_review_rows
            else []
        ),
    ]
    annex_e_lines = [
        *(["🟢 Cache: OK — Fraîcheur: OK.", ""] if not cache_problem_rows and not freshness_problem_rows else []),
        *(
            [
                "#### Cache local de marché",
                "",
                _markdown_table(["category", "status", "count", "cleaned_count", "details", "suggested_action"], cache_problem_rows),
                "",
            ]
            if cache_problem_rows
            else []
        ),
        *(
            [
                "#### Fraîcheur et fallback des données de marché",
                "",
                _markdown_table(
                    [
                        "ticker",
                        "overall_data_freshness_level",
                        "market_data_freshness_level",
                        "market_data_fetch_status",
                        "market_data_fallback_level",
                        "market_data_warning_flags",
                        "data_freshness_action",
                    ],
                    freshness_problem_rows,
                ),
            ]
            if freshness_problem_rows
            else []
        ),
    ]
    annex_f_lines = [
        *_details_block(
            "Garde-fous récents",
            [
                _markdown_table(["garde_fou", "à_quoi_ça_sert", "comment_lire", "impact_ici"], recent_guardrail_rows),
            ],
        ),
        *_details_block(
            "Preuves, fourchettes et risques de surconfiance",
            [
                "### Plage de confiance des scores",
                "",
                "Lecture: `TIGHT`/`NORMAL` veut dire que le score est assez stable; `WIDE`/`VERY_WIDE` veut dire qu’il faut le lire comme une zone, surtout si la recommandation dépend de données estimées. Ce n’est pas une prévision de rendement.",
                "",
                _markdown_table(
                    [
                        "ticker",
                        "score_with_estimates",
                        "score_confirmed_only",
                        "score_confidence_range",
                        "score_confidence_label",
                        "score_evidence_level",
                    ],
                    score_evidence_display_rows,
                ),
                "",
                "### Double-counting des signaux",
                "",
                "Lecture: cette couche ne rend pas le modèle défensif; elle réduit légèrement le sizing quand plusieurs points récompensent le même thème, la même croissance ou le même momentum.",
                "",
                _markdown_table(["ticker", "niveau", "score_chevauchement", "ajustement_sizing", "clusters", "lecture"], double_counting_display_rows),
                "",
                "### Clusters cachés",
                "",
                "Lecture: cette couche ne force pas la diversification et ne vend rien. Elle amortit seulement le sizing quand plusieurs titres différents ajoutent au même pari caché: thème, facteur, devise, région ou méga-tendance.",
                "",
                _markdown_table(["ticker", "niveau", "exposition_cluster", "ajustement_sizing", "clusters", "lecture"], hidden_cluster_display_rows),
                "",
                "### Thèse de marché long terme",
                "",
                "Cette couche regarde si le marché adressable possède un vent structurel durable. Son impact sur le sizing est volontairement limité pour éviter de transformer une mode de marché en recommandation automatique.",
                "",
                _markdown_table(["ticker", "statut", "score", "impact", "confiance", "raison"], market_growth_rows),
            ],
        ),
    ]
    annex_g_lines = [
        *_details_block(
            "Santé des sources et calibration",
            [
                "### Santé des sources",
                "",
                "Cette table surveille si les sources gratuites ou locales deviennent moins fiables. Elle n’achète ni ne vend rien: elle indique surtout quand il faut rafraîchir, valider ou ajouter un rapport.",
                "",
                _markdown_table(["source", "statut", "score", "tendance", "action"], source_health_display_rows),
                "",
                "### Calibration des proxies",
                "",
                _markdown_table(["field", "reliability_status", "recommended_action"], proxy_summary_rows),
                "",
                "### Corrections de proxy actives",
                "",
                "Lecture: cette table vérifie que les corrections validées ne deviennent pas une source de surcorrection. Elle n’ajuste rien toute seule; elle signale seulement quand une correction doit être revue.",
                "",
                _markdown_table(["field", "status", "risk_level", "factor", "recommended_action", "reason"], proxy_correction_display_rows),
            ],
        ),
        *(
            [
                "### Avertissements de validation",
                "",
                _markdown_table(["warning"], validation_warning_rows),
            ]
            if validation_warning_rows
            else []
        ),
    ]
    annex_h_lines = [
        "Cette section résume les sources consultées pendant cette analyse. Le rapport complet garde la version plus détaillée.",
        "",
        _markdown_table(["source", "utilisation", "éléments_consultés", "limite"], source_display_rows),
    ]

    lines = [
        "# Rapport compact d'investissement",
        "",
        triage_block,
        "",
        "## 1. Décision & positions",
        "",
        compact_decision_section,
        "",
        *sell_section_lines,
        "",
        "## 2. Santé du modèle",
        "",
        compact_model_health_section,
        "",
        "## 3. Titres qui se démarquent",
        "",
        ranking_section,
        "",
        "## 4. Portefeuille & risques",
        "",
        compact_portfolio_section,
        "",
        "## 5. Fiabilité des données",
        "",
        compact_data_reliability_section,
        "",
        compact_external_section,
        "",
        "## 7. Annexes techniques",
        "",
        "Ces annexes gardent les preuves et contrôles sans encombrer la décision principale. Quand tout est propre, elles se condensent automatiquement.",
        "",
        *_compact_details_block("A — Couverture des données", annex_a_lines),
        *_compact_details_block("B — Données prioritaires & conflits", annex_b_lines),
        *_compact_details_block("C — Anomalies post-analyse", annex_c_lines),
        *_compact_details_block("D — Journal d'exécution", annex_d_lines),
        *_compact_details_block("E — Cache & fraîcheur", annex_e_lines),
        *_compact_details_block("F — Garde-fous & preuves", annex_f_lines),
        *_compact_details_block("G — Santé des sources & calibration", annex_g_lines),
        *_compact_details_block("H — Bibliographie complète", annex_h_lines),
    ]
    return "\n".join(lines)


def build_markdown_report(
    mode: str,
    capital: float,
    analyses: dict[str, dict[str, Any]],
    allocation_result: dict[str, Any],
    portfolio_risk: dict[str, Any],
    stress_tests: list[dict[str, Any]],
    tax_report: list[dict[str, Any]],
    data_gaps: list[dict[str, Any]],
    validation_warnings: list[str],
    watchlist_analyses: dict[str, dict[str, Any]],
    market_analyses: dict[str, dict[str, Any]],
    market_universe: dict[str, dict[str, Any]],
    discovery_analyses: dict[str, dict[str, Any]],
    discovery_universe: dict[str, dict[str, Any]],
    discovery_maintenance_rows: list[dict[str, Any]],
    proxy_calibration_report: list[dict[str, Any]],
    proxy_calibration_summary: list[dict[str, Any]],
    proxy_correction_audit_rows: list[dict[str, Any]],
    allocation_change_rows: list[dict[str, Any]] | None = None,
    allocation_sensitivity: dict[str, Any] | None = None,
    validation_priority_rows: list[dict[str, Any]] | None = None,
    portfolio_change_rows: list[dict[str, Any]] | None = None,
    portfolio_change_history_rows: list[dict[str, Any]] | None = None,
    portfolio_change_summary_rows: list[dict[str, Any]] | None = None,
    portfolio_transaction_rows: list[dict[str, Any]] | None = None,
    portfolio_transaction_summary_rows: list[dict[str, Any]] | None = None,
    portfolio_inferred_transaction_rows: list[dict[str, Any]] | None = None,
    account_performance_rows: list[dict[str, Any]] | None = None,
    account_chart_rows: list[dict[str, Any]] | None = None,
    qualitative_moat_rows: list[dict[str, Any]] | None = None,
    company_dossier_rows: list[dict[str, Any]] | None = None,
    defensive_etf_candidates: list[dict[str, Any]] | None = None,
    market_regime: dict[str, Any] | None = None,
    thesis_reversal_rows: list[dict[str, Any]] | None = None,
    source_health_rows: list[dict[str, Any]] | None = None,
    source_conflict_rows: list[dict[str, Any]] | None = None,
    ticker_memory_rows: list[dict[str, Any]] | None = None,
    anomaly_rows: list[dict[str, Any]] | None = None,
    cache_health_rows: list[dict[str, Any]] | None = None,
    run_log_rows: list[dict[str, Any]] | None = None,
    instrument_profile_rows: list[dict[str, Any]] | None = None,
) -> str:
    allocations = allocation_result.get("allocations", [])
    allocation_rows = allocation_rows_for_csv(allocations)
    allocation_lookup = {**analyses, **watchlist_analyses, **market_analyses, **discovery_analyses}
    external_policy_note = _external_allocation_policy_note(mode)
    sorted_core = sorted(analyses.values(), key=lambda row: safe_float(row.get("capital_allocation_score")) or 0.0, reverse=True)
    watchlist_rows = build_watchlist_report_rows(watchlist_analyses)
    market_rows = build_market_candidate_rows(market_analyses, market_universe)
    discovery_rows = build_discovery_idea_rows(discovery_analyses, discovery_universe)
    discovery_report_rows = build_discovery_idea_rows(discovery_analyses, discovery_universe, report_only=True)
    promotion_rows = build_promotion_candidate_rows(watchlist_analyses, market_analyses, analyses, portfolio_risk, market_universe)
    sell_rows = sell_signal_rows_for_csv(analyses)
    winner_rows = winner_protection_rows(analyses)
    ticker_issue_rows = ticker_issue_rows_for_csv(analyses, watchlist_analyses, market_analyses)
    sell_display_rows = _display_rows(sell_rows)
    sell_validation_rows = sell_validation_checklist_rows(analyses, tax_report)
    monitoring_display_rows = monitoring_rows_for_report(sell_display_rows)
    winner_display_rows = _display_rows(winner_rows_for_output(winner_rows))
    watchlist_display_rows = _display_rows(watchlist_rows)
    market_display_rows = _display_rows(market_rows)
    discovery_display_rows = _display_rows(discovery_report_rows)
    discovery_maintenance_display_rows = _display_rows(_discovery_maintenance_rows_for_report(discovery_maintenance_rows))
    promotion_display_rows = _display_rows(promotion_recommendation_rows(promotion_rows))
    allocation_change_rows = allocation_change_rows or []
    allocation_sensitivity = allocation_sensitivity or {}
    validation_priority_rows = validation_priority_rows or []
    portfolio_change_rows = portfolio_change_rows or []
    portfolio_change_history_rows = portfolio_change_history_rows or []
    portfolio_change_summary_rows = portfolio_change_summary_rows or []
    portfolio_transaction_rows = portfolio_transaction_rows or []
    portfolio_transaction_summary_rows = portfolio_transaction_summary_rows or []
    portfolio_inferred_transaction_rows = portfolio_inferred_transaction_rows or []
    account_performance_rows = account_performance_rows or []
    account_chart_rows = account_chart_rows or []
    qualitative_moat_rows = qualitative_moat_rows or []
    company_dossier_rows = company_dossier_rows or build_company_dossier_rows(allocation_lookup, allocation_rows, qualitative_moat_rows)
    defensive_etf_candidates = defensive_etf_candidates or []
    market_regime = market_regime or {}
    thesis_reversal_rows = thesis_reversal_rows or []
    source_health_rows = source_health_rows or []
    source_conflict_rows = source_conflict_rows or []
    ticker_memory_rows = ticker_memory_rows or []
    anomaly_rows = anomaly_rows or []
    cache_health_rows = cache_health_rows or []
    run_log_rows = run_log_rows or []
    instrument_profile_rows = instrument_profile_rows or []
    top_watch = [row for row in watchlist_rows if row.get("watchlist_status") == "HIGH_PRIORITY_WATCH"]
    top_market = [row for row in market_rows if row.get("candidate_status") == "MANUAL_REVIEW_TOP_CANDIDATE"]
    top_discovery = actionable_discovery_rows(discovery_rows)
    top_promotions = [row for row in promotion_rows if row.get("promotion_status") == "PROMOTE_TO_CORE_REVIEW"]
    allocated_core = [row for row in allocation_rows if row["ticker"] != "VFV.TO"]
    opportunity_rows = opportunity_cost_rows(analyses, watchlist_analyses, market_analyses, discovery_analyses)
    trend_rows = trend_rows_for_csv(analyses, watchlist_analyses, market_analyses)
    quality_drawdown_rows = quality_drawdown_rows_for_csv(analyses, watchlist_analyses, market_analyses, discovery_analyses)
    cycle_rows = cycle_risk_rows(analyses, watchlist_analyses, market_analyses)
    durability_rows = durability_rows_for_csv(analyses, watchlist_analyses, market_analyses, discovery_analyses)
    market_growth_rows = market_growth_thesis_rows_for_csv(analyses, watchlist_analyses, market_analyses, discovery_analyses)
    cash_flow_rows = cash_flow_rows_for_csv(analyses, watchlist_analyses, market_analyses, discovery_analyses)
    shareholder_discipline_rows = shareholder_discipline_rows_for_csv(analyses, watchlist_analyses, market_analyses, discovery_analyses)
    defensive_etf_display_rows = compact_defensive_etf_rows_for_report(defensive_etf_candidates)
    external_etf_display_rows = compact_external_etf_rows_for_report(
        external_etf_rows_for_csv(watchlist_analyses, market_analyses, discovery_analyses),
        limit=12,
    )
    market_regime_display_rows = _display_rows(market_regime_rows(market_regime))
    market_regime_analysis_display_rows = _display_rows(
        compact_market_regime_analysis_rows(
            market_regime_analysis_rows(
                ("CORE_PORTFOLIO", analyses),
                ("WATCHLIST", watchlist_analyses),
                ("MARKET_SCANNER", market_analyses),
                ("DISCOVERY_IDEAS", discovery_analyses),
            ),
            limit=20,
        )
    )
    sector_euphoria = market_regime.get("sector_euphoria", {}) if isinstance(market_regime.get("sector_euphoria"), dict) else {}
    sector_euphoria_display_rows = _display_rows(sector_euphoria_rows(market_regime))
    sector_euphoria_analysis_display_rows = _display_rows(
        compact_sector_euphoria_analysis_rows(
            sector_euphoria_analysis_rows(
                ("CORE_PORTFOLIO", analyses),
                ("WATCHLIST", watchlist_analyses),
                ("MARKET_SCANNER", market_analyses),
                ("DISCOVERY_IDEAS", discovery_analyses),
            ),
            limit=20,
        )
    )
    data_freshness_rows = data_freshness_rows_for_csv(analyses, watchlist_analyses, market_analyses, discovery_analyses)
    data_freshness_display_rows = _display_rows(data_freshness_rows_for_report(data_freshness_rows))
    proxy_calibration_display_rows = _display_rows(proxy_calibration_rows_for_report(proxy_calibration_report))
    proxy_calibration_summary_display_rows = _display_rows(proxy_calibration_summary_rows_for_report(proxy_calibration_summary))
    proxy_correction_display_rows = _display_rows(proxy_correction_audit_rows_for_report(proxy_correction_audit_rows))
    allocation_change_display_rows = _display_rows(allocation_change_rows_for_report(allocation_change_rows))
    allocation_justification_display_rows = _display_rows(
        allocation_justification_rows_for_report(
            allocation_rows,
            allocation_lookup,
            allocation_change_rows,
            portfolio_change_rows,
            portfolio_change_history_rows,
        )
    )
    allocation_recommendation_text = allocation_recommendation_narrative(
        allocation_rows,
        allocation_lookup,
        allocation_change_rows,
        qualitative_moat_rows,
        company_dossier_rows,
    )
    company_dossier_display_rows = compact_company_dossier_rows_for_report(company_dossier_rows, limit=12)
    sensitivity_summary_display_rows = _sensitivity_summary_rows_for_display(sensitivity_summary_rows_for_report(allocation_sensitivity))
    sensitivity_display_rows = _display_rows(_sensitivity_rows_for_display(sensitivity_rows_for_report(allocation_sensitivity)))
    validation_priority_display_rows = _display_rows(validation_priority_rows_for_report(validation_priority_rows))
    portfolio_change_display_rows = _display_rows(portfolio_change_rows_for_report(portfolio_change_rows))
    portfolio_change_history_display_rows = _display_rows(portfolio_change_rows_for_report(portfolio_change_history_rows, limit=12))
    portfolio_change_summary_display_rows = _display_rows(portfolio_change_summary_rows_for_report(portfolio_change_summary_rows))
    portfolio_transaction_display_rows = _display_rows(transaction_rows_for_report(portfolio_transaction_rows))
    portfolio_transaction_summary_display_rows = _display_rows(
        transaction_summary_rows_for_report(portfolio_transaction_summary_rows)
    )
    portfolio_inferred_transaction_display_rows = _display_rows(
        inferred_transaction_rows_for_report(portfolio_inferred_transaction_rows)
    )
    account_chart_display_rows = _display_rows(account_chart_rows_for_report(account_chart_rows))
    account_performance_display_rows = _display_rows(account_performance_rows_for_report(account_performance_rows))
    true_data_gaps = true_missing_data_rows(data_gaps)
    auto_estimate_rows = auto_estimate_rows_for_output(data_gaps)
    decision_quality = allocation_result.get("decision_quality", {}) or {}
    allocated_tickers = {row.get("ticker") for row in allocation_rows if row.get("ticker")}
    sell_report_rows = compact_sell_rows(sell_rows_for_report(sell_display_rows))
    sell_validation_display_rows = compact_sell_validation_rows_for_full_report(sell_validation_rows)
    thesis_reversal_display_rows = compact_thesis_reversal_rows_for_full_report(thesis_reversal_rows)
    sell_recommendation_text_lines = sell_recommendation_narrative_lines(analyses, company_dossier_rows)
    monitoring_display_rows = compact_monitoring_rows(monitoring_display_rows, allocated_tickers)
    winner_display_rows = compact_winner_rows(winner_display_rows, allocated_tickers)
    core_focus_rows = compact_core_focus_rows(sorted_core, allocated_tickers)
    score_evidence_display_rows = compact_score_evidence_rows(sorted_core, allocated_tickers)
    double_counting_display_rows = compact_double_counting_rows(sorted_core, allocated_tickers)
    hidden_cluster_display_rows = compact_hidden_cluster_rows(sorted_core, allocated_tickers)
    durability_display_rows = _display_rows(compact_durability_rows(durability_rows, allocated_tickers))
    market_growth_display_rows = _display_rows(compact_market_growth_rows(market_growth_rows, allocated_tickers))
    cash_flow_display_rows = _display_rows(compact_cash_flow_rows(cash_flow_rows, allocated_tickers))
    shareholder_discipline_display_rows = _display_rows(compact_shareholder_discipline_rows(shareholder_discipline_rows, allocated_tickers))
    market_display_rows = _display_rows(compact_market_rows(market_rows))
    discovery_display_rows = _display_rows(compact_discovery_rows(discovery_report_rows))
    discovery_maintenance_display_rows = _display_rows(compact_discovery_maintenance_rows(discovery_maintenance_rows))
    opportunity_display_rows = compact_opportunity_rows(opportunity_rows, allocated_tickers)
    trend_display_rows = compact_trend_rows(trend_rows)
    quality_drawdown_display_rows = compact_quality_drawdown_rows(quality_drawdown_rows, allocated_tickers)
    stability_display_rows = compact_stability_rows(stability_rows_for_report(analyses))
    cycle_display_rows = compact_cycle_rows(cycle_rows, allocated_tickers)
    ticker_issue_display_rows = compact_ticker_issue_rows(ticker_issue_rows)
    true_data_gap_display_rows = compact_data_gap_rows(true_data_gaps, validation_priority_display_rows)
    auto_estimate_display_rows = compact_auto_estimate_rows(auto_estimate_rows, allocated_tickers, validation_priority_display_rows)
    data_freshness_display_rows = compact_data_freshness_rows(data_freshness_display_rows, allocated_tickers)
    proxy_calibration_display_rows = compact_proxy_calibration_rows(proxy_calibration_display_rows)
    source_health_display_rows = compact_source_health_rows(source_health_rows, limit=10)
    source_conflict_display_rows = compact_source_conflict_rows(source_conflict_rows, limit=12)
    ticker_memory_display_rows = compact_ticker_memory_rows(ticker_memory_rows, limit=12)
    anomaly_display_rows = anomaly_rows_for_report(anomaly_rows, limit=12)
    cache_health_display_rows = compact_cache_health_rows(cache_health_rows, limit=10)
    cache_all_pass = bool(cache_health_rows) and not [
        row for row in cache_health_rows if str(row.get("status") or "").upper() in {"WARN", "FAIL"}
    ]
    cache_summary_row = next((row for row in cache_health_rows if str(row.get("category") or "") == "summary"), {})
    cache_total_count = int(safe_float(cache_summary_row.get("count")) or 0)
    if cache_total_count <= 0:
        cache_total_count = int(
            sum(
                safe_float(row.get("count")) or 0.0
                for row in cache_health_rows
                if str(row.get("category") or "") != "summary"
            )
        )
    cache_lkg_count = int(
        sum(
            safe_float(row.get("count")) or 0.0
            for row in cache_health_rows
            if str(row.get("category") or "") == "last_known_good"
        )
    )
    run_log_display_rows = run_log_rows_for_report(run_log_rows, limit=12)
    instrument_profile_section = build_instrument_profile_section(instrument_profile_rows, compact=False)

    lines = [
        "# Rapport trimestriel d’investissement",
        "",
        f"- Date: {today_iso()}",
        f"- Mode utilisé: {mode}",
        f"- Version des règles: {MODEL_RULES_VERSION}",
        f"- Capital analysé: {money(capital)}",
        f"- Valeur totale du portefeuille: {money(portfolio_risk.get('total_portfolio_value'))}",
        f"- Moyenne pondérée des scores hors VFV: {_average_score_text(allocation_result.get('average_score_ex_vfv'))}",
        f"- Légende ticker: `*` = données très insuffisantes, absence de prix, ou compagnie à vérifier. Un alias simple est affiché entre parenthèses.",
        "",
        f"> {DISCLAIMER}",
        "",
        "## 1. Résumé exécutif",
        "",
        f"- Allocation recommandée de la cotisation: {_allocation_summary(allocation_rows)}",
        f"- Changement principal d’allocation: {_allocation_change_summary(allocation_change_display_rows)}",
        f"- Robustesse de l’allocation: {_sensitivity_summary_text(sensitivity_summary_display_rows)}",
        f"- Qualité de décision: {decision_quality.get('decision_quality_level', 'N/D')} "
        f"({decision_quality.get('decision_quality_score', 'N/D')}/100) - {decision_quality.get('summary', 'N/D')}",
        f"- Meilleur achat actuel: {_row_or_none(allocated_core, 'ticker')}",
        f"- Meilleure opportunité actuelle: {_best_opportunity(sorted_core)}",
        f"- Allocation VFV: {pct(allocation_result.get('mandatory_vfv_percent'), 0)} obligatoire avant redirections.",
        f"- ETF défensifs: {defensive_fallback_summary(defensive_etf_candidates, mode)}",
        f"- Régime de marché: {market_regime.get('market_regime_status', 'N/D')} "
        f"({market_regime.get('market_regime_score', 'N/D')}/100) - {market_regime.get('market_regime_interpretation', 'N/D')}",
        f"- Euphorie sectorielle: {sector_euphoria.get('sector_euphoria_status', 'INACTIVE')} "
        f"({sector_euphoria.get('sector_euphoria_score', 0)}/100) - {sector_euphoria.get('sector_euphoria_reason', 'N/D')}",
        f"- Positions exclues de cette moyenne, mais toujours considérées pour les cotisations: {_satellite_exclusion_summary(sorted_core)}",
        f"- Signaux de vente: {_sell_signal_summary(sell_display_rows)}",
        f"- Alertes de surveillance non liées à une vente: {_monitoring_summary(monitoring_display_rows)}",
        f"- {_thesis_reversal_compact_summary(thesis_reversal_rows)}",
        f"- Opportunités quality drawdown: {_quality_drawdown_summary(quality_drawdown_display_rows)}",
        f"- Protection des winners: {_winner_protection_summary(winner_display_rows)}",
        *(
            [f"- Meilleures candidates watchlist: {_status_summary(watchlist_display_rows, 'watchlist_status', 'HIGH_PRIORITY_WATCH')}"]
            if watchlist_display_rows
            else []
        ),
        f"- Meilleures candidates surveillance externe: {_status_summary(market_display_rows, 'candidate_status', 'MANUAL_REVIEW_TOP_CANDIDATE')}",
        f"- Nouvelles idées à ajouter au market_universe: {_row_list_or_none(_display_rows(top_discovery), 'ticker')}",
        f"- Candidates à promouvoir manuellement: {_row_list_or_none(_display_rows(top_promotions), 'ticker')}",
        f"- Tendances historiques à surveiller: {_trend_summary(trend_rows)}",
        f"- Risque cycle/bulle/tendance dominant: {_cycle_summary(cycle_rows)}",
        f"- Durabilité 15-30 ans: {_durability_summary(durability_rows)}",
        f"- Thèse de croissance de marché: {_market_growth_summary(market_growth_rows)}",
        f"- Fraîcheur des données: {_data_freshness_summary(data_freshness_rows)}",
        f"- Santé des sources: {source_health_summary(source_health_rows)}",
        f"- Contradictions entre sources: {source_conflict_summary(source_conflict_rows)}",
        f"- Mémoire ticker: {ticker_memory_summary(ticker_memory_rows)}",
        f"- Anomalies post-analyse: {anomaly_summary(anomaly_rows)}",
        f"- Cache de marché: {cache_health_summary(cache_health_rows)}",
        f"- Journal d'exécution: {run_log_summary(run_log_rows)}",
        f"- Donnée à valider en priorité: {_top_validation_priority_text(validation_priority_display_rows)}",
        f"- Risque principal du portefeuille: {portfolio_risk.get('primary_risk')}",
        "",
        *portfolio_history_section(
            2,
            portfolio_change_display_rows,
            portfolio_change_summary_display_rows,
            portfolio_change_history_display_rows,
            portfolio_transaction_display_rows,
            portfolio_inferred_transaction_display_rows,
        ),
        *account_charts_markdown(account_chart_rows),
        _markdown_table(
            ["account_type", "total_value_cad", "positions_count", "top_positions", "note"],
            account_chart_display_rows,
        ),
        "",
        "### Performance par compte vs S&P 500",
        "",
        "Cette section compare la performance estimée des comptes à VFV.TO, utilisé comme proxy S&P 500 en CAD. La colonne `valeur ajoutée vs S&P 500` tient maintenant compte des transactions déduites automatiquement quand le prix VFV du jour est disponible; elle reste approximative parce que les vrais frais et prix de transaction ne sont pas connus.",
        "",
        _account_performance_method_text(),
        "",
        _markdown_table(
            ["indicateur", "à quoi ça sert", "comment l’interpréter"],
            account_performance_indicator_legend_rows(),
        ),
        "",
        _markdown_table(
            [
                "account_type",
                "current_value_cad",
                "unrealized_gain_percent",
                "tracking_start_date",
                "benchmark_return_basis",
                "portfolio_return_since_tracking",
                "sp500_return_since_tracking",
                "excess_return_vs_sp500",
                "portfolio_twr",
                "sp500_twr",
                "twr_excess_vs_sp500",
                "twr_status",
                "twr_period_count",
                "twr_method",
                "portfolio_xirr",
                "sp500_xirr",
                "xirr_excess_vs_sp500",
                "xirr_status",
                "xirr_flow_count",
                "xirr_method",
                "external_flows_cad",
                "sp500_equivalent_value_cad",
                "value_added_vs_sp500_cad",
                "value_added_vs_sp500_percent",
                "flow_adjusted_status",
                "comparison_status",
                "simple_return_status",
                "preferred_performance_read",
                "preferred_performance_summary",
                "interpretation",
            ],
            account_performance_display_rows,
        ),
        "",
        "## 3. Allocation de la cotisation",
        "",
        "Le cap fiabilité ne change pas le score d’une entreprise: il limite seulement la taille d’un gros bloc quand les preuves ne sont pas encore assez solides.",
        "",
        _markdown_table(
            [
                "ticker",
                "amount",
                "percentage",
                "reason",
                "confidence",
                "allocation_type",
                "cap_fiabilité",
                "decision_quality",
            ],
            [
                {
                    **row,
                    "amount": money(row["amount"]),
                    "percentage": pct(row["percentage"], 1),
                    "cap_fiabilité": _allocation_reliability_cap_text(row),
                }
                for row in allocation_rows
            ],
        ),
        "",
        *([instrument_profile_section, ""] if instrument_profile_section else []),
        "### Defensive ETF Fallback",
        "",
        "Cette couche sert seulement de stabilisateur dans les modes plus prudents. Elle est désactivée en `high-cagr`; en `rational-aggressive`, elle reste volontairement très plafonnée.",
        "",
        _markdown_table(["ticker", "statut", "score", "rôle", "raison"], defensive_etf_display_rows),
        "",
        "### ETF externes possibles",
        "",
        "Cette couche analyse les ETF présents dans les listes externes avec une logique ETF: rôle de portefeuille, volatilité, drawdown, tendance, risque de concentration et adéquation au mode. Elle ne s’active pas en `high-cagr`.",
        "",
        _markdown_table(["ticker", "statut", "score", "fit_mode", "raison"], external_etf_display_rows),
        "",
        "### Régime de marché et contexte institutionnel léger",
        "",
        "Cette couche lit des ETF/indices gratuits pour détecter le climat général: risk-on, risk-off, stress de taux, risque de bulle/tendance ou risque de récession. Elle influence seulement le sizing avec un impact plafonné; elle ne vend rien, ne garde pas de cash volontairement et ne remplace jamais les fondamentaux.",
        "",
        _markdown_table(MARKET_REGIME_COLUMNS, market_regime_display_rows),
        "",
        _markdown_table(MARKET_REGIME_ANALYSIS_COLUMNS, market_regime_analysis_display_rows),
        "",
        "### Euphorie sectorielle universelle",
        "",
        "Cette sous-couche surveille plusieurs ETF sectoriels gratuits pour détecter si un secteur précis devient très dominant. L’impact reste léger, plafonné et limité aux titres directement exposés; il ne déclenche jamais une vente et ne remplace jamais les fondamentaux.",
        "",
        _markdown_table(SECTOR_EUPHORIA_COLUMNS, sector_euphoria_display_rows),
        "",
        _markdown_table(SECTOR_EUPHORIA_ANALYSIS_COLUMNS, sector_euphoria_analysis_display_rows),
        "",
        "### Justification de chaque montant recommandé",
        "",
        "Cette section explique seulement les titres qui reçoivent une partie de la cotisation. Elle relie le choix actuel aux scores, au sizing, à la dernière recommandation et aux derniers changements détectés dans `portfolio.csv`.",
        "",
        "#### Synthèse longue de la recommandation",
        "",
        allocation_recommendation_text,
        "",
        _markdown_table(
            [
                "ticker",
                "montant",
                "pourquoi_ce_titre",
                "pourquoi_ce_montant",
                "vs_dernière_recommandation",
                "lien_avec_portefeuille",
            ],
            allocation_justification_display_rows,
        ),
        "",
        *qualitative_moat_markdown(qualitative_moat_rows),
        "### Fiches qualitatives automatiques multi-sources",
        "",
        "Ces fiches combinent les rapports locaux disponibles, yfinance/Yahoo Finance, SEC EDGAR ou sources canadiennes gratuites quand disponibles, nouvelles gratuites, thèse de marché, métriques de cash-flow et historique local. Elles ne remplacent pas une analyse professionnelle, mais elles rendent la justification moins générique.",
        "",
        _markdown_table(["ticker", "statut", "niveau_sources", "lecture", "sources_manquantes"], company_dossier_display_rows),
        "",
        "### Qualité de décision",
        "",
        "Cette section indique à quel point la recommandation est robuste avec les preuves disponibles aujourd’hui. Elle n’ajoute pas une nouvelle allocation: elle qualifie la décision finale.",
        "",
        _markdown_table(
            [
                "decision_quality_level",
                "decision_quality_score",
                "summary",
                "profile_calibration",
                "vfv_total_percent",
                "vfv_redirection_percent",
                "core_allocation_percent",
                "data_quality_status",
                "risk_status",
                "stability_status",
                "sensitivity_status",
            ],
            _decision_quality_display_rows(decision_quality),
        ),
        "",
        f"- Interprétation du score: {_decision_quality_score_interpretation(decision_quality)}",
        f"- Raisons principales: {_list_text(decision_quality.get('main_reasons'))}",
        f"- Points à surveiller: {_list_text(decision_quality.get('watchpoints'))}",
        f"- Ce qui empêche HIGH: {_list_text(decision_quality.get('why_not_high'))}",
        "",
        "### Pourquoi l’allocation a changé",
        "",
        "Cette section explique les variations par rapport aux analyses précédentes. Elle n’ancre pas la décision: elle décrit seulement pourquoi le moteur a choisi différemment ou non.",
        "",
        _markdown_table(
            [
                "ticker",
                "previous_amount",
                "current_amount",
                "change_amount",
                "change_status",
                "main_explanation",
                "decision_impact",
            ],
            allocation_change_display_rows,
        ),
        "",
        "### Robustesse de l’allocation",
        "",
        "Cette section teste la recommandation avec deux hypothèses plus prudentes. Elle ne propose pas une deuxième allocation: elle indique seulement si la décision actuelle dépend trop d’optimisme dans les données.",
        "",
        _markdown_table(
            [
                "robustness_status",
                "robustness_score",
                "top_pick_status",
                "base_top_pick",
                "prudent_top_pick",
                "strict_data_top_pick",
                "vfv_base_percent",
                "vfv_prudent_percent",
                "vfv_strict_data_percent",
                "summary",
            ],
            sensitivity_summary_display_rows,
        ),
        "",
        f"- Interprétation du score: {_sensitivity_score_interpretation(sensitivity_summary_display_rows)}",
        _markdown_table(
            [
                "ticker",
                "base_amount",
                "prudent_amount",
                "strict_data_amount",
                "max_change_amount",
                "max_change_percent",
                "robustness_note",
            ],
            sensitivity_display_rows,
        ),
        "",
            "## 4. Signaux de vente et surveillance",
            "",
            "Les signaux de vente fondamentaux sont séparés des alertes de surveillance. Une alerte technique ou de valorisation peut limiter une cotisation sans devenir une recommandation de vente.",
            "",
            "Lecture simple: le premier tableau répond à “faut-il vendre, réduire ou liquider?”. Le second répond à “faut-il surveiller avant d’ajouter?”. Les détails complets restent dans `latest_sell_signals.csv`.",
            "",
            _markdown_table(
                [
                    "ticker",
                    "statut_vente",
                    "action_recommandée",
                    "raison_principale",
                    "preuve_fondamentale_confirmée",
                    "validation_manuelle_requise",
                    "protection_winner",
                ],
                sell_report_rows,
            ),
            "",
            "### Check-list avant vente",
            "",
            "Cette bonification regroupe les preuves déjà calculées par le modèle. Elle aide à éviter deux erreurs: vendre un winner sur du bruit de marché, ou garder un loser quand la thèse fondamentale est réellement cassée. Une réduction ou liquidation importante doit rester validée manuellement.",
            "",
            _markdown_table(
                [
                    "ticker",
                    "validation_level",
                    "fundamental_evidence",
                    "technical_or_valuation_context",
                    "winner_protection_check",
                    "historical_trend_check",
                    "news_or_research_check",
                    "tax_check",
                    "checklist_summary",
                ],
                sell_validation_display_rows,
            ),
            "",
            "### Renversement de thèse (audit-only)",
            "",
            "Cette couche compare la thèse actuelle à l’historique local et indique si la détérioration semble fondamentale ou surtout liée à la qualité des données. Elle ne modifie jamais l’allocation, le sizing ou une recommandation de vente.",
            "",
            _markdown_table(
                [
                    "ticker",
                    "previous_thesis_status",
                    "current_thesis_status",
                    "thesis_reversal_status",
                    "thesis_reversal_severity",
                    "manual_review_priority",
                    "conclusion_basis",
                    "data_quality_driven",
                    "score_contradiction_flag",
                    "reason_fr",
                ],
                thesis_reversal_display_rows,
            ),
            "",
            *sell_recommendation_text_lines,
            "### Alertes de surveillance",
            "",
            _markdown_table(
                [
                    "ticker",
                    "statut_surveillance",
                    "action",
                    "raison_principale",
                    "impact_sur_achat",
                ],
                monitoring_display_rows,
            ),
            "",
            "### Quality Drawdown Opportunity",
            "",
            "Cette couche sépare une baisse dangereuse d'une baisse potentiellement intéressante: elle ne bonifie un titre que si la thèse, la vente GREEN, la qualité, le cash-flow et les nouvelles disponibles ne montrent pas de détérioration fondamentale.",
            "",
            _markdown_table(
                [
                    "ticker",
                    "statut",
                    "score",
                    "impact_allocation",
                    "contexte_nouvelles",
                    "lecture",
                    "titres_récents",
                ],
                quality_drawdown_display_rows,
            ),
            "",
            "## 5. Protection des winners",
            "",
            "Cette couche ne vend pas une baisse normale. Elle surveille surtout les winners qui reculent fortement depuis leur sommet personnel en même temps que la thèse ou les fondamentaux se détériorent.",
            "",
            "Les valeurs de portefeuille sont exprimées en CAD quand le prix gratuit et le taux de change sont disponibles. Si une donnée manque, la colonne `portfolio_valuation_source` dans `latest_scores.csv` indique la méthode de secours utilisée.",
            "",
            _markdown_table(
                [
                    "ticker",
                    "shares",
                    "average_cost",
                    "average_cost_currency",
                    "average_cost_cad",
                    "acquisition_value",
                    "acquisition_value_currency",
                    "acquisition_value_cad",
                    "current_value",
                    "current_value_currency",
                    "quote_currency",
                    "current_price_cad",
                    "unrealized_gain_percent",
                    "drawdown_from_personal_high",
                    "winner_protection_status",
                    "winner_protection_action",
                    "winner_protection_reason",
                ],
                winner_display_rows,
            ),
            "",
            "## 6. Core Portfolio Analysis",
            "",
            "Lecture simple: ce tableau répond à “est-ce que ce titre mérite une cotisation, une surveillance ou une exclusion?”. Les scores complets restent dans `latest_scores.csv`.",
        "",
        _markdown_table(
            [
                "ticker",
                "score_total",
                "conviction_score",
                "capital_allocation_score",
                "expected_cagr_quality",
                "long_term_durability_status",
                "cash_flow_quality_status",
                "shareholder_discipline_status",
                "shareholder_return_profile",
                "opportunity_cost_status",
                "thesis_status",
                "liquidation_status",
                "monitoring_status",
                "winner_protection_status",
                "cycle_bubble_risk_level",
                "double_counting_risk_level",
                "hidden_cluster_risk_level",
                "data_reliability_level",
                "allocation_decision",
                "final_position_action",
            ],
            [_core_summary_row(row) for row in sorted_core],
        ),
        "",
        "### Preuve du score",
        "",
        "Cette section sépare le score complet avec estimations du score confirmé par preuves directes. La fourchette de confiance ne change pas l’allocation à elle seule: elle indique seulement si le score doit être lu comme précis (`TIGHT`/`NORMAL`) ou comme une zone plus approximative (`WIDE`/`VERY_WIDE`). Ce n’est pas une prévision de rendement.",
        "",
        _markdown_table(
            [
                "ticker",
                "score_with_estimates",
                "score_confirmed_only",
                "score_estimate_gap",
                "score_confidence_range",
                "score_confidence_label",
                "score_evidence_level",
                "score_evidence_penalty",
                "score_evidence_reason",
            ],
            score_evidence_display_rows,
        ),
        "",
        "### Double-counting des signaux",
        "",
        "Cette couche identifie les cas où plusieurs signaux récompensent possiblement le même narratif: croissance, thème, momentum ou marché adressable. Elle agit seulement sur le sizing, avec un ajustement léger et plafonné.",
        "",
        _markdown_table(["ticker", "niveau", "score_chevauchement", "ajustement_sizing", "clusters", "lecture"], double_counting_display_rows),
        "",
        "### Clusters cachés",
        "",
        "Cette couche repère les cas où plusieurs titres apparemment différents dépendent du même pari sous-jacent: IA/semi/cloud, méga-cap tech, taux, devise, géographie ou thème industriel. Elle ne vend rien et ne bloque pas les compounders exceptionnels; elle agit seulement sur le sizing avec un impact léger et plafonné.",
        "",
        _markdown_table(["ticker", "niveau", "exposition_cluster", "ajustement_sizing", "clusters", "lecture"], hidden_cluster_display_rows),
        "",
    ]

    lines.extend(
        [
            "### Positions à lire en priorité",
            "",
            "Le détail complet par critère a été retiré du rapport principal pour garder le document utilisable. Les positions ci-dessous sont celles qui reçoivent du capital, déclenchent une surveillance, ont un signal de vente, ou ont une donnée/risque qui peut changer la décision. Le détail complet reste dans `latest_scores.csv`.",
            "",
            _markdown_table(
                [
                    "ticker",
                    "allocation_decision",
                    "final_position_action",
                    "capital_allocation_score",
                    "score_total",
                    "opportunity_cost_status",
                    "monitoring_status",
                    "sell_status",
                    "cycle_bubble_risk_level",
                    "data_reliability_level",
                    "raison",
                ],
                core_focus_rows,
            ),
            "",
        ]
    )

    section_number = 7
    lines.extend(
        [
            f"## {section_number}. Durabilité 15-30 ans",
            "",
            "Cette section ne prédit pas un rendement exact. Elle classe la solidité probable du modèle d’affaires sur un horizon très long et aide à éviter de confondre une tendance chaude avec un compounder durable.",
            "",
            _markdown_table(
                [
                    "universe",
                    "ticker",
                    "long_term_durability_score",
                    "long_term_durability_status",
                    "expected_cagr_quality",
                    "cycle_bubble_risk_level",
                    "thesis_status",
                    "data_reliability_level",
                ],
                durability_display_rows,
            ),
            "",
        ]
    )
    section_number += 1
    lines.extend(
        [
            f"## {section_number}. Thèse de croissance de marché long terme",
            "",
            "Cette couche regarde si le marché adressable a un vent structurel durable. Elle s'appuie sur les données gratuites déjà disponibles, les benchmarks sectoriels, les sources officielles/rapports locaux quand présents et un catalogue prudent de sources publiques. Son impact sur le score d'allocation est volontairement faible pour ne pas acheter une mode.",
            "",
            _markdown_table(
                [
                    "universe",
                    "ticker",
                    "market_growth_thesis_score",
                    "market_growth_thesis_status",
                    "market_growth_thesis_adjustment",
                    "market_growth_thesis_confidence",
                    "market_growth_thesis_themes",
                    "market_growth_thesis_sources",
                    "market_growth_thesis_reason",
                ],
                market_growth_display_rows,
            ),
            "",
        ]
    )
    section_number += 1
    lines.extend(
        [
            f"## {section_number}. Qualité du cash-flow",
            "",
            "Cette couche vérifie si les profits semblent appuyés par du free cash flow durable. Elle influence légèrement le sizing: bon cash-flow = petit bonus, cash-flow faible = prudence, secteurs non comparables = pas de pénalité mécanique.",
            "",
            _markdown_table(
                [
                    "universe",
                    "ticker",
                    "cash_flow_quality_status",
                    "cash_flow_quality_score",
                    "cash_flow_quality_adjustment",
                    "free_cash_flow_margin",
                    "fcf_conversion",
                    "net_debt_to_fcf",
                    "free_cash_flow_growth",
                    "cash_flow_quality_reason",
                ],
                cash_flow_display_rows,
            ),
            "",
        ]
    )
    section_number += 1
    lines.extend(
        [
            f"## {section_number}. Discipline envers les actionnaires",
            "",
            "Cette couche vérifie si la croissance se transforme en valeur par action. Une dilution normale ou compensée ne déclenche pas de vente; une dilution élevée limite surtout le sizing et demande une surveillance.",
            "",
            _markdown_table(
                [
                    "universe",
                    "ticker",
                    "shareholder_discipline_status",
                    "shareholder_discipline_score",
                    "shareholder_discipline_adjustment",
                    "share_count_growth_1y",
                    "share_count_cagr_3y",
                    "share_count_cagr_5y",
                    "buyback_yield",
                    "sbc_to_revenue",
                    "fcf_per_share_growth",
                    "shareholder_discipline_reason",
                ],
                shareholder_discipline_display_rows,
            ),
            "",
        ]
    )
    section_number += 1
    if watchlist_display_rows:
        lines.extend(
            [
                f"## {section_number}. Watchlist Analysis",
                "",
                external_policy_note,
                "",
                _markdown_table(
                    [
                        "ticker",
                        "score_total",
                        "score_confidence_range",
                        "score_confidence_label",
                        "conviction_score",
                        "conviction_confidence_range",
                        "conviction_confidence_label",
                        "expected_cagr_quality",
                        "opportunity_cost_status",
                        "benchmark_ticker",
                        "benchmark_relevance_level",
                        "cycle_bubble_risk_level",
                        "cycle_bubble_score",
                        "watchlist_status",
                        "reason",
                    ],
                    watchlist_display_rows,
                ),
                "",
            ]
        )
        section_number += 1

    lines.extend(
        [
            f"## {section_number}. Surveillance externe / Market Universe",
            "",
            SCANNER_SCOPE_NOTE,
            "",
            external_policy_note,
            "",
            _markdown_table(
                [
                    "ticker",
                    "company_name",
                    "score_total",
                    "score_confidence_range",
                    "score_confidence_label",
                    "conviction_score",
                    "conviction_confidence_range",
                    "conviction_confidence_label",
                    "expected_cagr_quality",
                    "opportunity_cost_status",
                    "benchmark_ticker",
                    "benchmark_relevance_level",
                    "cycle_bubble_risk_level",
                    "cycle_bubble_score",
                    "candidate_status",
                    "reason",
                ],
                market_display_rows,
            ),
            "",
        ]
    )
    section_number += 1

    lines.extend(
        [
            f"## {section_number}. Découverte externe à ajouter au Market Universe",
            "",
            DISCOVERY_SCOPE_NOTE,
            "",
            external_policy_note,
            "",
            "Le nettoyage automatique met en quarantaine ou écarte les titres avec données indisponibles, signaux de faillite/delisting dans les nouvelles gratuites, prix très faible, taille trop petite ou détérioration mécanique majeure.",
            "",
            "Si rien n’apparaît ici, cela veut dire qu’aucune idée externe n’a passé les filtres assez stricts pour mériter une attention prioritaire.",
            "",
            _markdown_table(
                [
                    "ticker",
                    "company_name",
                    "score_total",
                    "score_confidence_range",
                    "score_confidence_label",
                    "conviction_score",
                    "conviction_confidence_range",
                    "conviction_confidence_label",
                    "expected_cagr_quality",
                    "opportunity_cost_status",
                    "data_quality",
                    "valuation_status",
                    "cycle_bubble_risk_level",
                    "discovery_status",
                    "reason",
                    "suggested_action",
                ],
                discovery_display_rows
                or [
                    {
                        "ticker": "",
                        "company_name": "",
                        "score_total": "",
                        "conviction_score": "",
                        "expected_cagr_quality": "",
                        "opportunity_cost_status": "",
                        "data_quality": "",
                        "valuation_status": "",
                        "cycle_bubble_risk_level": "",
                        "discovery_status": "AUCUNE_IDEE_PRIORITAIRE",
                        "reason": "Aucun titre externe n’a passé les filtres stricts de découverte.",
                        "suggested_action": "Ne rien ajouter au market_universe pour l’instant.",
                    }
                ],
            ),
            "",
            "### Nettoyage automatique du radar",
            "",
            _markdown_table(
                DISCOVERY_MAINTENANCE_COLUMNS,
                discovery_maintenance_display_rows
                or [
                    {
                        "ticker": "",
                        "ticker_display": "",
                        "company_name": "",
                        "source": "",
                        "maintenance_status": "AUCUN_SIGNAL_PRIORITAIRE",
                        "reason": "Aucun titre à mettre en avant, en quarantaine ou à retirer.",
                        "suggested_action": "Ne rien faire.",
                    }
                ],
            ),
            "",
        ]
    )
    section_number += 1

    lines.extend(
        [
            f"## {section_number}. Promotion manuelle vers le Core Portfolio",
            "",
            "Cette section affiche seulement les actions externes qui méritent vraiment une revue de promotion vers `portfolio.csv` avec `shares=0`.",
            "",
            "Le filtre compare maintenant la candidate aux meilleurs titres du Core Portfolio, pas seulement à la position la plus faible. Si aucune entreprise ne passe ces filtres stricts, l’agent ne recommande aucune promotion. En `high-cagr`, une candidate externe ne reçoit toujours aucune allocation automatique; dans les modes plus prudents, elle peut être utilisée seulement si les filtres stricts du mode la rendent admissible.",
            "",
            _markdown_table(PROMOTION_COLUMNS, promotion_display_rows),
            "",
        ]
    )
    section_number += 1

    lines.extend(
        [
            f"## {section_number}. Opportunity Cost vs VFV",
            "",
            "Les colonnes `after_tax_yield_adjusted` sont des estimations fiscales approximatives pour comparaison relative seulement (`after-tax est. (approx.)`). Elles ne remplacent pas une validation avec un fiscaliste ou comptable.",
            "",
            _markdown_table(
                [
                    "universe",
                    "ticker",
                    "opportunity_cost_status",
                    "gross_yield",
                    "after_tax_yield_adjusted",
                    "vfv_after_tax_yield_adjusted",
                    "after_tax_yield_spread_vs_vfv",
                    "score_total",
                    "conviction_score",
                    "allocation_decision",
                    "sell_decision",
                    "final_position_action",
                ],
                opportunity_display_rows,
            ),
            "",
        ]
    )
    section_number += 1

    lines.extend(
        [
            f"## {section_number}. Historique et tendances",
            "",
            "Cette section compare l’analyse actuelle avec les analyses précédentes quand elles existent.",
            "",
            _markdown_table(TREND_COLUMNS, trend_display_rows),
            "",
        ]
    )
    section_number += 1

    lines.extend(
        [
            f"## {section_number}. Stabilité mensuelle modérée",
            "",
            "Cette section amortit les petits changements d’un mois à l’autre sans bloquer une vraie amélioration ni cacher une détérioration. Un nouveau titre peut remplacer l’ancien choix seulement s’il est nettement meilleur, ou si l’ancien choix se détériore.",
            "",
            _markdown_table(
                [
                    "ticker",
                    "allocation_stability_status",
                    "allocation_stability_adjustment",
                    "previous_capital_allocation_score",
                    "capital_allocation_score_change",
                    "allocation_decision",
                    "final_position_action",
                    "reason",
                ],
                stability_display_rows,
            ),
            "",
        ]
    )
    section_number += 1

    lines.extend(
        [
            f"## {section_number}. Risque cycle / bulle / tendance",
            "",
            "Cette section ne sert pas à vendre automatiquement. Elle sert à éviter qu’une cotisation long terme soit trop influencée par un thème déjà très populaire ou par le haut d’un cycle.",
            "",
            _markdown_table(
                [
                    "universe",
                    "ticker",
                    "cycle_risk_profile",
                    "cycle_bubble_risk_level",
                "cycle_bubble_score",
                "cycle_bubble_penalty",
                "allocation_multiplier",
                "cycle_normalized_status",
                "cycle_normalized_growth_cap",
                "cycle_adjusted_growth_estimate",
                "cycle_normalized_earnings_risk_score",
                "comment",
                "reasons",
            ],
                cycle_display_rows,
            ),
            "",
        ]
    )
    section_number += 1

    lines.extend(
        [
            f"## {section_number}. Portfolio Risk",
            "",
            f"- Nombre de positions effectives: {portfolio_risk.get('effective_positions', 0):.2f}",
            f"- Poids des 3 plus grosses positions: {pct(portfolio_risk.get('top3_weight'), 1)}",
            f"- Poids des 5 plus grosses positions: {pct(portfolio_risk.get('top5_weight'), 1)}",
            f"- Poids total tech/IA/semi-conducteurs: {pct(portfolio_risk.get('tech_ai_semi_weight'), 1)}",
            f"- Poids total USD: {pct(portfolio_risk.get('usd_weight'), 1)}",
            f"- Poids total CAD: {pct(portfolio_risk.get('cad_weight'), 1)}",
            f"- Poids total EUR: {pct(portfolio_risk.get('eur_weight'), 1)}",
            "",
            "### Concentration par action",
            "",
            _dict_table("Nom", "Poids", portfolio_risk.get("concentration_by_action", {})),
            "",
            "### Concentration par secteur",
            "",
            "Le secteur indique dans quel type d’industrie chaque position est classée: logiciel, semi-conducteurs, santé, paiements, industrielles, etc.",
            "",
            _dict_table("Secteur", "Poids", portfolio_risk.get("concentration_by_sector", {})),
            "",
            "### Concentration par devise",
            "",
            _dict_table("Devise", "Poids", portfolio_risk.get("concentration_by_currency", {})),
            "",
            "### Concentration par région",
            "",
            _dict_table("Région", "Poids", portfolio_risk.get("concentration_by_region", {})),
            "",
            "### Facteurs communs",
            "",
            "Les facteurs communs indiquent les moteurs ou risques qui peuvent relier plusieurs positions même si elles sont dans des secteurs différents: IA, croissance, taux d’intérêt, cloud, semi-conducteurs, consommation, etc.",
            "",
            _dict_table("Facteur", "Poids", portfolio_risk.get("factor_exposure", {})),
            "",
            "### Alertes",
            "",
            _markdown_table(["risk_type", "risk_level", "description", "impact"], risk_rows_for_output(portfolio_risk)),
            "",
        ]
    )
    section_number += 1

    lines.extend([f"## {section_number}. Stress Tests", ""])
    section_number += 1

    for scenario in stress_tests:
        contributors = ", ".join(
            f"{item['ticker']} ({money(item['estimated_loss'])})"
            for item in scenario.get("top_contributors", [])
        )
        if scenario.get("scenario_type") == "sequential_stylized":
            amplifiers = _stress_ticker_summary(scenario.get("amplifying_tickers", []), "scenario_return")
            resilient = _stress_ticker_summary(scenario.get("resilient_tickers", []), "scenario_return")
            sector_theme = _stress_sector_theme_summary(scenario.get("contribution_by_sector_theme", []))
            lines.extend(
                [
                    f"### {scenario.get('scenario')}",
                    "",
                    "- Type: scénario séquentiel stylisé déterministe, diagnostic seulement.",
                    f"- Qualité du diagnostic: {scenario.get('scenario_quality', 'LOW')} ({pct(safe_float(scenario.get('data_completeness')), 0)} des métadonnées clés disponibles).",
                    f"- Perte finale estimée: {money(scenario.get('estimated_loss_dollars'))} ({pct(scenario.get('estimated_loss_percent'), 1)})",
                    f"- Drawdown maximal simulé: {pct(scenario.get('max_drawdown_percent'), 1)}",
                    f"- Pire phase simulée: {scenario.get('worst_phase_name') or 'Donnée pas dispo'} ({pct(scenario.get('worst_phase_return'), 1)})",
                    f"- Positions qui contribuent le plus: {contributors or 'Aucune'}",
                    f"- Titres qui amplifient le plus le scénario: {amplifiers or 'Donnée pas dispo'}",
                    f"- Titres les plus résilients dans ce scénario: {resilient or 'Donnée pas dispo'}",
                    f"- Contribution par secteur/thème: {sector_theme or 'Donnée pas dispo'}",
                    f"- Interprétation: {scenario.get('interpretation') or scenario.get('primary_risk')}",
                    "",
                ]
            )
            continue
        lines.extend(
            [
                f"### {scenario.get('scenario')}",
                "",
                f"- Perte estimée en dollars: {money(scenario.get('estimated_loss_dollars'))}",
                f"- Perte estimée en %: {pct(scenario.get('estimated_loss_percent'), 1)}",
                f"- Positions qui contribuent le plus: {contributors or 'Aucune'}",
                f"- Interprétation: {scenario.get('primary_risk')}",
                "",
            ]
        )

    lines.extend(
        [
            f"## {section_number}. Fiscalité approximative",
            "",
            "Analyse fiscale approximative à valider avec un comptable ou fiscaliste.",
            "",
            _markdown_table(
                ["ticker", "account_type", "account_tax_category", "shares", "current_value", "tax_comment", "warning"],
                tax_rows_for_output(tax_report),
            ),
            "",
        ]
    )
    section_number += 1

    lines.extend(
        [
            f"## {section_number}. Données manquantes et estimations automatiques",
            "",
            "### Tickers à vérifier",
            "",
            "`*` signifie que les données sont très insuffisantes, que le prix manque, ou que la compagnie trouvée doit être validée. Un alias simple est affiché entre parenthèses, par exemple `SBGSY (SCHN)`. Le statut de couverture distingue un vrai doute sur le ticker d’un simple manque de données gratuites.",
            "",
            _markdown_table(TICKER_ISSUE_COLUMNS, ticker_issue_display_rows),
            "",
            "### Données à valider en priorité",
            "",
            "Cette section classe seulement les données qui peuvent vraiment changer une allocation, un signal de vente ou la confiance. Elle sert à éviter de chercher des rapports pour des champs qui ne changeraient probablement rien.",
            "",
            _markdown_table(
                [
                    "priority_rank",
                    "priority",
                    "ticker",
                    "universe",
                    "field_label",
                    "priority_score",
                    "decision_impact",
                    "suggested_action",
                    "bncd_report_needed",
                ],
                validation_priority_display_rows,
            ),
            "",
            "### Données vraiment manquantes",
            "",
            "Ces lignes indiquent les champs que l’agent n’a pas pu obtenir ou estimer correctement avec les données gratuites.",
            "",
            _markdown_table(["ticker", "data_field", "importance", "impact"], true_data_gap_display_rows),
            "",
            "### Fraîcheur des données",
            "",
            "Cette table indique si les prix, le cache local ou les rapports BNCD/Morningstar sont assez récents. Une donnée périmée ne bloque pas l’analyse, mais elle réduit la confiance et demande une validation avant une grosse décision.",
            "",
            _markdown_table(
                [
                    "ticker",
                    "overall_data_freshness_level",
                    "market_data_freshness_level",
                    "market_data_fetch_status",
                    "market_data_fallback_level",
                    "market_data_warning_flags",
                    "market_data_age_hours",
                    "research_report_freshness_level",
                    "data_freshness_action",
                ],
                data_freshness_display_rows,
            ),
            "",
            "### Santé des sources",
            "",
            "Cette table regarde la santé globale des sources utilisées par l’agent: disponibilité, fraîcheur, conflits et dépendance aux estimations. Elle sert à détecter une source qui se dégrade avant que cela influence trop les recommandations.",
            "",
            _markdown_table(["source", "statut", "score", "tendance", "action"], source_health_display_rows),
            "",
            "### Cache local de marché",
            "",
            "Cette table résume le nettoyage prudent du cache: fichiers temporaires, caches illisibles, caches indisponibles, anciens fallbacks et copies last-known-good. Le cache utile est conservé; l’agent ne supprime pas agressivement les données pouvant encore servir de filet de secours.",
            "",
            *(
                [f"✅ Cache: OK ({cache_total_count} entrées — {cache_lkg_count} last-known-good)", ""]
                if cache_all_pass
                else [
                    _markdown_table(
                        ["category", "status", "count", "cleaned_count", "details", "suggested_action"],
                        cache_health_rows or cache_health_display_rows,
                    ),
                    "",
                ]
            ),
            "### Journal d'exécution",
            "",
            "Cette table résume les événements techniques utiles de l'analyse: cache, sources, données fragiles, anomalies et règles d'allocation. Elle sert à expliquer une recommandation surprenante sans rendre le modèle plus conservateur.",
            "",
            _markdown_table(["niveau", "composant", "événement", "message", "action"], run_log_display_rows),
            "",
            "### Contradictions entre sources",
            "",
            "Cette section rend visibles les écarts entre yfinance et les données officielles disponibles. Elle ne change pas automatiquement une allocation, parce que les données officielles peuvent être plus anciennes ou calculées différemment.",
            "",
            _markdown_table(
                ["ticker", "universe", "severity", "conflict_count", "conflict_profile", "recommended_action"],
                source_conflict_display_rows,
            ),
            "",
            "### Anomalies post-analyse",
            "",
            "Cette couche compare les résultats du rapport avec l'historique local du même mode. Elle ne modifie pas l'allocation: elle sert à détecter une chute inhabituelle de score, une bascule de statut, une surcharge de validations ou une source de données fragile.",
            "",
            _markdown_table(["scope", "ticker", "niveau", "signal", "metrique", "variation", "lecture", "action"], anomaly_display_rows),
            "",
            "### Mémoire ticker",
            "",
            "Cette mémoire garde les classifications observées des tickers nouveaux, canadiens, internationaux ou mal couverts. Elle sert de filet de secours pour secteur, région et devise si une future source gratuite devient incomplète; elle ne remplace pas les données fraîches.",
            "",
            _markdown_table(["ticker", "ticker_memory_status", "sector", "region", "currency", "ticker_memory_action"], ticker_memory_display_rows),
            "",
            "### Estimations automatiques à valider",
            "",
            "Ces lignes ne veulent pas dire que la donnée est absente: elles indiquent que l’agent a utilisé un proxy gratuit qui mérite validation avant une décision importante.",
            "",
            _markdown_table(["ticker", "data_field", "importance", "impact"], auto_estimate_display_rows),
            "",
        ]
    )
    section_number += 1

    lines.extend(
        [
            f"## {section_number}. Calibration des proxies automatiques",
            "",
            "Cette section compare les vraies données que vous fournissez dans `data/proxy_calibration.csv` avec les estimations automatiques de l’agent.",
            "",
            "Elle ne change pas automatiquement les règles. Elle sert à voir quels proxies sont fiables et lesquels méritent une amélioration manuelle ou une future recalibration.",
            "",
            "Résumé par donnée:",
            "",
            _markdown_table(
                [
                    "field",
                    "filled_examples",
                    "usable_examples",
                    "match_count",
                    "close_count",
                    "review_count",
                    "bias_direction",
                    "reliability_status",
                    "recommended_action",
                ],
                proxy_calibration_summary_display_rows,
            ),
            "",
            "Détail par entreprise:",
            "",
            _markdown_table(
                [
                    "ticker",
                    "field",
                    "true_value",
                    "proxy_value",
                    "difference",
                    "relative_difference",
                    "comparison_status",
                    "recalibration_hint",
                ],
                proxy_calibration_display_rows,
            ),
            "",
            "Audit des corrections actives:",
            "",
            "Cette sous-section surveille les corrections de proxy déjà activées afin d’éviter une surcorrection. Elle ne désactive rien automatiquement pendant l’analyse normale: elle rend seulement visible une correction trop ancienne, trop proche de la limite ou contredite par de nouvelles vraies données.",
            "",
            f"- Résumé: {proxy_correction_audit_summary(proxy_correction_audit_rows)}",
            "",
            _markdown_table(
                [
                    "field",
                    "status",
                    "risk_level",
                    "factor",
                    "confidence",
                    "sample_count",
                    "last_updated",
                    "bias_status",
                    "current_suggested_factor",
                    "recommended_action",
                    "reason",
                ],
                proxy_correction_display_rows,
            ),
            "",
        ]
    )
    section_number += 1

    lines.extend(
        [
            f"## {section_number}. Limites",
            "",
            "- Données gratuites incomplètes.",
            "- yfinance peut être incomplet, retardé ou temporairement indisponible.",
            "- Le fichier manuel est optionnel: les champs vides sont remplacés par des estimations automatiques prudentes quand c’est possible.",
            "- Les estimations automatiques ne remplacent pas une vraie lecture des rapports annuels.",
            "- Le scanner et la découverte externe ne sont pas exhaustifs: ils analysent seulement les univers fournis ou configurés.",
            "- Le système applique des règles; il ne prédit pas l’avenir.",
            "- Ceci n’est pas un conseil financier.",
            "- Les décisions finales doivent être validées manuellement.",
            "- Les règles fiscales sont approximatives.",
            "",
        ]
    )
    section_number += 1

    lines.extend(
        [
            f"## {section_number}. Sources / médiagraphie",
            "",
            "Cette section liste les sources consultées par l’agent pour produire cette analyse locale.",
            "",
            _markdown_table(
                ["source", "utilisation", "éléments consultés", "limite"],
                source_rows_for_report(analyses, watchlist_analyses, market_analyses, discovery_analyses),
            ),
        ]
    )
    if validation_warnings:
        lines.extend(["", "### Avertissements de validation", ""])
        lines.extend([f"- {warning}" for warning in validation_warnings])
    lines = align_full_report_navigation(lines)
    return "\n".join(lines) + "\n"


def write_scores_csv(path: str | Path, analyses: dict[str, dict[str, Any]]) -> None:
    write_csv_records(path, [_score_row_for_csv(row) for row in sorted(analyses.values(), key=lambda item: item.get("ticker", ""))], SCORES_COLUMNS)


def write_allocations_csv(path: str | Path, allocations: list[dict[str, Any]]) -> None:
    write_csv_records(path, allocation_rows_for_csv(allocations), ALLOCATIONS_COLUMNS)


def write_decision_quality_csv(path: str | Path, decision_quality: dict[str, Any]) -> None:
    write_csv_records(path, decision_quality_rows_for_csv(decision_quality), DECISION_QUALITY_COLUMNS)


def write_sell_signals_csv(path: str | Path, analyses: dict[str, dict[str, Any]]) -> None:
    write_csv_records(path, sell_signal_rows_for_csv(analyses), SELL_SIGNALS_COLUMNS)


def write_watchlist_csv(path: str | Path, analyses: dict[str, dict[str, Any]]) -> None:
    write_csv_records(path, build_watchlist_report_rows(analyses), WATCHLIST_COLUMNS)


def write_market_candidates_csv(
    path: str | Path, analyses: dict[str, dict[str, Any]], universe: dict[str, dict[str, Any]]
) -> None:
    write_csv_records(path, build_market_candidate_rows(analyses, universe), MARKET_CANDIDATE_COLUMNS)


def write_discovery_ideas_csv(
    path: str | Path, analyses: dict[str, dict[str, Any]], universe: dict[str, dict[str, Any]]
) -> None:
    rows = build_discovery_idea_rows(analyses, universe, report_only=True)
    if not rows:
        rows = [
            {
                "ticker": "",
                "ticker_display": "",
                "resolved_ticker": "",
                "company_name": "",
                "score_total": "",
                "conviction_score": "",
                "expected_cagr_quality": "",
                "opportunity_cost_status": "",
                "data_quality": "",
                "valuation_status": "",
                "cycle_bubble_risk_level": "",
                "discovery_status": "AUCUNE_IDEE_PRIORITAIRE",
                "reason": "Aucune nouvelle idée externe n’a passé les filtres stricts.",
                "suggested_action": "Ne rien ajouter au market_universe pour l’instant.",
            }
        ]
    write_csv_records(path, rows, DISCOVERY_COLUMNS)


def _discovery_maintenance_rows_for_report(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    priority_statuses = {"ACTIVE_TOP_IDEA", "QUARANTINE", "REMOVE_CANDIDATE"}
    return [row for row in rows if row.get("maintenance_status") in priority_statuses]


def write_ticker_issues_csv(
    path: str | Path,
    *analysis_groups: dict[str, dict[str, Any]],
) -> None:
    rows = ticker_issue_rows_for_csv(*analysis_groups)
    if not rows:
        rows = [
            {
                "ticker_display": "",
                "input_tickers": "",
                "resolved_ticker": "",
                "intended_company_name": "",
                "company_name_found": "",
                "ticker_validation_status": "",
                "ticker_coverage_status": "",
                "free_data_coverage_class": "",
                "free_data_coverage_score": "",
                "suggested_yahoo_tickers": "",
                "issues": "",
                "suggested_action": "Aucun ticker problématique détecté.",
            }
        ]
    write_csv_records(path, rows, TICKER_ISSUE_COLUMNS)


def write_promotion_candidates_csv(
    path: str | Path,
    watchlist_analyses: dict[str, dict[str, Any]],
    market_analyses: dict[str, dict[str, Any]],
    core_analyses: dict[str, dict[str, Any]],
    portfolio_risk: dict[str, Any],
    market_universe: dict[str, dict[str, Any]],
) -> None:
    rows = build_promotion_candidate_rows(watchlist_analyses, market_analyses, core_analyses, portfolio_risk, market_universe)
    write_csv_records(path, promotion_recommendation_rows(rows), PROMOTION_COLUMNS)


def promotion_recommendation_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    promoted = [row for row in rows if row.get("promotion_status") == "PROMOTE_TO_CORE_REVIEW"]
    if promoted:
        return promoted
    return [
        {
            "universe": "",
            "ticker": "",
            "ticker_display": "",
            "resolved_ticker": "",
            "company_name": "",
            "score_total": "",
            "conviction_score": "",
            "expected_cagr_quality": "",
            "opportunity_cost_status": "",
            "data_quality": "",
            "cycle_bubble_risk_level": "",
            "cycle_bubble_score": "",
            "promotion_status": "AUCUNE_PROMOTION_FONDEE",
            "reason": "Aucun titre externe ne mérite vraiment une promotion vers le Core Portfolio selon les filtres stricts.",
            "next_step": "Ne rien ajouter au portfolio pour l’instant; continuer la surveillance dans le market_universe.",
        }
    ]


def _gap_field_key(data_field: Any) -> str:
    text = str(data_field or "").replace("AUTO_ESTIMATE:", "", 1).strip().lower()
    if ":" in text:
        text = text.split(":", 1)[1].strip()
    return text.replace(" ", "_").replace("-", "_")


def _gap_resolvable_by(row: dict[str, Any]) -> str:
    ticker = normalize_ticker(row.get("ticker"))
    field = _gap_field_key(row.get("data_field"))
    is_canadian = ticker.endswith((".TO", ".V"))
    sedarplus_fields = {
        "profit_margins",
        "operating_margins",
        "revenue_growth",
        "earnings_growth",
        "return_on_equity",
        "return_on_assets",
        "free_cash_flow",
        "free_cash_flow_margin",
        "total_debt",
        "total_cash",
        "net_debt_to_fcf",
        "total_assets",
        "total_liabilities",
    }
    yf_us_forward_fields = {
        "forward_eps",
        "trailing_eps",
        "number_of_analyst_opinions",
        "forward_pe",
        "peg",
        "earnings_growth",
        "revenue_growth",
    }
    yf_profile_fields = {"sector_name", "industry", "market_cap", "dividend_yield"}
    yf_market_fields = {"current_price", "sma_200", "stock_return_1y", "cagr_5y"}
    if is_canadian and field in sedarplus_fields:
        return "sedarplus"
    if not is_canadian and field in yf_us_forward_fields:
        return "yfinance_live"
    if field in yf_profile_fields or field in yf_market_fields:
        return "yfinance_live"
    return "manual"


def data_gap_rows_for_output(data_gaps: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for row in true_missing_data_rows(data_gaps):
        output = dict(row)
        output["gap_resolvable_by"] = _gap_resolvable_by(row)
        rows.append(output)
    return rows


def write_data_gaps_csv(path: str | Path, data_gaps: list[dict[str, Any]]) -> None:
    rows = data_gap_rows_for_output(data_gaps)
    if not rows:
        rows = [
            {
                "ticker": "",
                "data_field": "",
                "importance": "",
                "impact": "Aucune donnée vraiment manquante majeure.",
                "gap_resolvable_by": "",
            }
        ]
    write_csv_records(path, rows, DATA_GAPS_COLUMNS)


def write_auto_estimates_csv(path: str | Path, data_gaps: list[dict[str, Any]]) -> None:
    rows = auto_estimate_rows_for_output(data_gaps)
    if not rows:
        rows = [{"ticker": "", "data_field": "", "importance": "", "impact": "Aucune estimation automatique majeure à valider."}]
    write_csv_records(path, rows, AUTO_ESTIMATES_COLUMNS)


def write_data_freshness_csv(path: str | Path, *analysis_groups: dict[str, dict[str, Any]]) -> None:
    rows = data_freshness_rows_for_csv(*analysis_groups)
    if not rows:
        rows = [
            {
                "ticker": "",
                "universe": "",
                "overall_data_freshness_level": "AUCUNE_DONNEE",
                "data_freshness_action": "",
                "market_data_freshness_level": "",
                "market_data_source": "",
                "market_data_fetched_at": "",
                "market_data_age_hours": "",
                "market_data_requires_refresh": "",
                "market_data_fetch_status": "",
                "market_data_fallback_level": "",
                "market_data_warning_flags": "",
                "market_data_circuit_breaker_open": "",
                "research_report_freshness_level": "",
                "research_report_latest_date": "",
                "research_report_age_days": "",
                "research_report_requires_fresh_validation": "",
                "reason": "",
            }
        ]
    write_csv_records(path, rows, DATA_FRESHNESS_COLUMNS)


def data_freshness_rows_for_csv(*analysis_groups: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for group in analysis_groups:
        for row in sorted(group.values(), key=lambda item: (str(item.get("universe")), str(item.get("ticker")))):
            if row.get("benchmark_role") is True:
                continue
            rows.append(
                {
                    "ticker": row.get("ticker_display", row.get("ticker")),
                    "universe": row.get("universe"),
                    "overall_data_freshness_level": row.get("overall_data_freshness_level"),
                    "data_freshness_action": row.get("data_freshness_action"),
                    "market_data_freshness_level": row.get("market_data_freshness_level"),
                    "market_data_source": row.get("market_data_source", row.get("source")),
                    "market_data_fetched_at": row.get("market_data_fetched_at", row.get("fetched_at")),
                    "market_data_age_hours": row.get("market_data_age_hours"),
                    "market_data_requires_refresh": row.get("market_data_requires_refresh"),
                    "market_data_fetch_status": row.get("market_data_fetch_status"),
                    "market_data_fallback_level": row.get("market_data_fallback_level"),
                    "market_data_warning_flags": _list_text(row.get("market_data_warning_flags") or []),
                    "market_data_circuit_breaker_open": row.get("market_data_circuit_breaker_open"),
                    "research_report_freshness_level": row.get("research_report_freshness_level"),
                    "research_report_latest_date": row.get("research_report_latest_date"),
                    "research_report_age_days": row.get("research_report_age_days"),
                    "research_report_requires_fresh_validation": row.get("research_report_requires_fresh_validation"),
                    "reason": _freshness_reason(row),
                }
            )
    return sorted(rows, key=_data_freshness_sort_key, reverse=True)


def data_freshness_rows_for_report(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    important = [
        row
        for row in rows
        if row.get("universe") != "DISCOVERY_IDEAS"
        and (
            row.get("overall_data_freshness_level") not in {"FRESH_ENOUGH", "OK_BUT_AGING"}
            or row.get("market_data_requires_refresh") is True
            or row.get("research_report_requires_fresh_validation") is True
        )
    ]
    if important:
        return important[:20]
    discovery_critical = [
        row
        for row in rows
        if row.get("overall_data_freshness_level") not in {"FRESH_ENOUGH", "OK_BUT_AGING"}
        or row.get("market_data_requires_refresh") is True
        or row.get("research_report_requires_fresh_validation") is True
        if row.get("universe") == "DISCOVERY_IDEAS"
    ]
    if discovery_critical:
        return discovery_critical[:10]
    return [
        {
            "ticker": "",
            "overall_data_freshness_level": "FRESH_ENOUGH",
            "market_data_freshness_level": "FRESH",
            "market_data_fetch_status": "OK",
            "market_data_fallback_level": "NONE",
            "market_data_warning_flags": "",
            "market_data_age_hours": "",
            "research_report_freshness_level": "Aucune alerte majeure",
            "data_freshness_action": "Aucune donnée périmée majeure détectée.",
        }
    ]


def compact_core_focus_rows(
    rows: list[dict[str, Any]],
    allocated_tickers: set[str],
    limit: int = 16,
) -> list[dict[str, Any]]:
    focused = []
    for row in rows:
        if row.get("benchmark_role") is True:
            continue
        ticker = str(row.get("ticker") or "")
        display = row.get("ticker_display", ticker)
        allocation = str(row.get("allocation_decision") or "")
        final_action = str(row.get("final_position_action") or "")
        monitoring = str(row.get("monitoring_status") or "NORMAL")
        sell_status = str(row.get("sell_status") or row.get("liquidation_status") or "")
        cycle = str(row.get("cycle_bubble_risk_level") or "")
        data_reliability = str(row.get("data_reliability_level") or "")
        should_show = (
            ticker in allocated_tickers
            or allocation in {"BUY / ADD", "DO_NOT_ADD"}
            or final_action in {"ADD_WITH_MONITORING", "WATCH", "REVIEW_TRIM_25", "REVIEW_TRIM_50", "LIQUIDATE_URGENT_REVIEW"}
            or monitoring not in {"", "NORMAL", "BENCHMARK"}
            or sell_status in {"YELLOW", "ORANGE", "RED"}
            or cycle in {"HIGH", "EXTREME"} and ticker in allocated_tickers
            or data_reliability == "LOW"
        )
        if not should_show:
            continue
        focused.append(
            {
                "ticker": display,
                "allocation_decision": allocation,
                "final_position_action": final_action,
                "capital_allocation_score": row.get("capital_allocation_score"),
                "score_total": row.get("score_total"),
                "opportunity_cost_status": row.get("opportunity_cost_status"),
                "monitoring_status": monitoring,
                "sell_status": sell_status,
                "cycle_bubble_risk_level": cycle,
                "data_reliability_level": data_reliability,
                "raison": _compact_position_reason(row),
                "_sort": _core_focus_sort_key(row, ticker in allocated_tickers),
            }
        )
    if not focused:
        return [
            {
                "ticker": "",
                "allocation_decision": "",
                "final_position_action": "",
                "capital_allocation_score": "",
                "score_total": "",
                "opportunity_cost_status": "",
                "monitoring_status": "",
                "sell_status": "",
                "cycle_bubble_risk_level": "",
                "data_reliability_level": "",
                "raison": "Aucune position prioritaire à détailler.",
            }
        ]
    return [{key: value for key, value in row.items() if key != "_sort"} for row in sorted(focused, key=lambda item: item["_sort"], reverse=True)[:limit]]


def compact_sell_rows(rows: list[dict[str, Any]], limit: int = 12) -> list[dict[str, Any]]:
    selected = [
        row
        for row in rows
        if row.get("statut_vente") not in {"GREEN", "BENCHMARK", ""}
        or row.get("action_recommandée") not in {"HOLD", "ETF_BENCHMARK_FALLBACK", ""}
        or row.get("validation_manuelle_requise") == "Oui"
    ]
    if selected:
        return selected[:limit]
    return [
        {
            "ticker": "",
            "statut_vente": "AUCUN_SIGNAL_DE_VENTE_MAJEUR",
            "action_recommandée": "HOLD",
            "raison_principale": "Aucune position ne déclenche de vente mécanique dans le rapport court.",
            "preuve_fondamentale_confirmée": "Non",
            "validation_manuelle_requise": "Non",
            "protection_winner": "",
        }
    ]


def compact_sell_validation_rows_for_compact_report(
    rows: list[dict[str, Any]],
    limit: int = 8,
) -> list[dict[str, Any]]:
    if not rows:
        return [
            {
                "ticker": "",
                "niveau": "NO_SELL_SIGNAL",
                "preuve_clé": "Aucun signal de vente actif.",
                "point_à_valider": "Aucune validation urgente.",
                "conclusion": "Conserver selon les autres règles du modèle.",
            }
        ]
    output = []
    for row in rows[:limit]:
        output.append(
            {
                "ticker": row.get("ticker_display", row.get("ticker")),
                "niveau": row.get("validation_level"),
                "preuve_clé": _compact_sentence(row.get("fundamental_evidence"), 150),
                "point_à_valider": _compact_sentence(_validation_point_text(row), 150),
                "conclusion": _compact_sentence(row.get("checklist_summary"), 150),
            }
        )
    return output


def compact_sell_validation_rows_for_full_report(rows: list[dict[str, Any]], limit: int = 18) -> list[dict[str, Any]]:
    if not rows:
        return [
            {
                "ticker": "",
                "validation_level": "NO_SELL_SIGNAL",
                "fundamental_evidence": "Aucun signal de vente actif.",
                "technical_or_valuation_context": "",
                "winner_protection_check": "",
                "historical_trend_check": "",
                "news_or_research_check": "",
                "tax_check": "",
                "checklist_summary": "Aucune vente ou réduction à valider dans cette analyse.",
            }
        ]
    output = []
    for row in rows[:limit]:
        output.append({**row, "ticker": row.get("ticker_display", row.get("ticker"))})
    return output


def compact_monitoring_rows(
    rows: list[dict[str, Any]],
    allocated_tickers: set[str],
    limit: int = 12,
) -> list[dict[str, Any]]:
    def sort_key(row: dict[str, Any]) -> tuple[float, float, str]:
        ticker = str(row.get("ticker") or "")
        manual = 1.0 if row.get("statut_surveillance") == "MANUAL_REVIEW" else 0.0
        return (1.0 if ticker in allocated_tickers else 0.0, manual, ticker)

    return [
        {
            "ticker": row.get("ticker"),
            "statut_surveillance": row.get("statut_surveillance"),
            "raison_principale": _compact_sentence(row.get("raison_principale"), 160),
            "impact_sur_achat": _compact_sentence(row.get("impact_sur_achat"), 160),
        }
        for row in sorted(rows, key=sort_key, reverse=True)[:limit]
    ]


def compact_monitoring_summary_rows(
    rows: list[dict[str, Any]],
    limit: int = 3,
) -> list[dict[str, Any]]:
    output = []
    for row in rows[:limit]:
        status = str(row.get("statut_surveillance") or "").upper()
        reason = _compact_sentence(row.get("raison_principale"), 120)
        for separator in (".,", " | ", "\n"):
            reason = reason.split(separator, 1)[0].strip()
        for prefix, replacement in (
            ("Alerte technique:", "Signal technique:"),
            ("Alerte valorisation:", "Valorisation:"),
            ("Alerte marché:", "Performance de marché:"),
            ("Alerte surveillance:", "Surveillance:"),
            ("Alerte:", ""),
            ("Validation manuelle requise:", "À valider:"),
        ):
            if reason.startswith(prefix):
                reason = f"{replacement}{reason[len(prefix):]}".strip()
                break
        reason = reason.replace(" (pertinence HIGH)", "")
        reason = f"{reason[:1].upper()}{reason[1:]}" if reason else reason
        if reason and reason[-1] not in ".!?":
            reason += "."
        if status == "MANUAL_REVIEW":
            instruction = "Ne pas renforcer avant validation."
        elif status == "WATCH":
            instruction = "Conserver et surveiller."
        else:
            instruction = "Surveiller; aucune action immédiate."
        output.append(
            {
                "ticker": row.get("ticker"),
                "consigne_simple": instruction,
                "raison_principale": reason or "Signal à surveiller; voir le détail.",
            }
        )
    return output


def compact_winner_rows(
    rows: list[dict[str, Any]],
    allocated_tickers: set[str],
    limit: int = 10,
) -> list[dict[str, Any]]:
    active_statuses = {
        "WATCH_WINNER_PULLBACK",
        "PROTECT_WINNER_REVIEW",
        "TRIM_25_REVIEW",
        "TRIM_50_REVIEW",
        "LIQUIDATE_WINNER_REVIEW",
    }
    selected = []
    for row in rows:
        ticker = str(row.get("ticker") or "")
        status = str(row.get("winner_protection_status") or "")
        action = str(row.get("winner_protection_action") or "")
        if status in active_statuses or action not in {"", "NONE", "HOLD"} or ticker in allocated_tickers and status == "NO_COST_DATA":
            selected.append(row)
    if selected:
        return selected[:limit]
    return [
        {
            "ticker": "",
            "shares": "",
            "average_cost": "",
            "average_cost_currency": "",
            "average_cost_cad": "",
            "acquisition_value": "",
            "acquisition_value_currency": "",
            "acquisition_value_cad": "",
            "current_value": "",
            "current_value_currency": "",
            "quote_currency": "",
            "current_price_cad": "",
            "unrealized_gain_percent": "",
            "drawdown_from_personal_high": "",
            "winner_protection_status": "AUCUNE_PROTECTION_ACTIVE",
            "winner_protection_action": "HOLD",
            "winner_protection_reason": "Aucun winner ne demande une protection spéciale dans le rapport court.",
        }
    ]


def compact_score_evidence_rows(
    rows: list[dict[str, Any]],
    allocated_tickers: set[str],
    limit: int = 14,
) -> list[dict[str, Any]]:
    all_rows = score_evidence_rows_for_report(rows)
    selected = []
    for row in all_rows:
        gap = abs(safe_float(row.get("score_estimate_gap")) or 0.0)
        ticker = str(row.get("ticker") or "")
        if ticker in allocated_tickers or gap >= 3 or row.get("score_evidence_level") in {"ESTIMATE_HEAVY", "INSUFFICIENT_CONFIRMED"}:
            selected.append(row)
    return selected[:limit] or all_rows[: min(limit, len(all_rows))]


def double_counting_rows_for_report(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    output = []
    for row in rows:
        if is_etf_asset_analysis(row):
            continue
        output.append(
            {
                "ticker": row.get("ticker_display", row.get("ticker")),
                "niveau": row.get("double_counting_risk_level", "LOW"),
                "score_chevauchement": row.get("double_counting_overlap_score", 0),
                "ajustement_sizing": row.get("double_counting_adjustment", 0),
                "clusters": row.get("double_counting_clusters", ""),
                "lecture": row.get("double_counting_reason", ""),
            }
        )
    return output


def compact_double_counting_rows(
    rows: list[dict[str, Any]],
    allocated_tickers: set[str],
    limit: int = 12,
) -> list[dict[str, Any]]:
    all_rows = double_counting_rows_for_report(rows)
    selected = []
    for row in all_rows:
        ticker = str(row.get("ticker") or "")
        level = str(row.get("niveau") or "")
        adjustment = abs(safe_float(row.get("ajustement_sizing")) or 0.0)
        if ticker in allocated_tickers or level in {"HIGH", "EXTREME"} or adjustment >= 2:
            selected.append(row)
    if selected:
        return selected[:limit]
    return all_rows[: min(limit, len(all_rows))]


def compact_recent_guardrail_rows(
    allocation_rows: list[dict[str, Any]],
    score_rows: list[dict[str, Any]],
    double_counting_rows: list[dict[str, Any]],
    hidden_cluster_rows: list[dict[str, Any]],
) -> list[dict[str, str]]:
    cap_tickers = [
        str(row.get("ticker") or "")
        for row in allocation_rows
        if _truthy_report_value(row.get("reliability_cap_applied"))
    ]
    wide_score_tickers = [
        str(row.get("ticker") or "")
        for row in score_rows
        if str(row.get("score_confidence_label") or "").upper() in {"WIDE", "VERY_WIDE"}
    ]
    double_counting_tickers = [
        str(row.get("ticker") or "")
        for row in double_counting_rows
        if (safe_float(row.get("ajustement_sizing")) or 0.0) < 0
    ]
    hidden_cluster_tickers = [
        str(row.get("ticker") or "")
        for row in hidden_cluster_rows
        if (safe_float(row.get("ajustement_sizing")) or 0.0) < 0
    ]
    return [
        {
            "garde_fou": "Plage de confiance",
            "à_quoi_ça_sert": "Montre si un score doit être lu comme un chiffre solide ou comme une zone.",
            "comment_lire": "`WIDE`/`VERY_WIDE` = valider davantage avant une grosse décision; `NORMAL`/`TIGHT` = lecture plus stable.",
            "impact_ici": _guardrail_ticker_text(wide_score_tickers, "score large"),
        },
        {
            "garde_fou": "Cap fiabilité",
            "à_quoi_ça_sert": "Empêche un gros bloc quand les preuves sont bonnes mais encore incomplètes.",
            "comment_lire": "Le titre peut rester acheté; le modèle limite seulement le montant.",
            "impact_ici": _guardrail_ticker_text(cap_tickers, "cap appliqué"),
        },
        {
            "garde_fou": "Double-counting",
            "à_quoi_ça_sert": "Repère quand croissance, momentum, thème et marché adressable racontent la même histoire.",
            "comment_lire": "Ajustement léger du sizing; ne change pas la thèse et ne déclenche pas de vente.",
            "impact_ici": _guardrail_ticker_text(double_counting_tickers, "sizing amorti"),
        },
        {
            "garde_fou": "Clusters cachés",
            "à_quoi_ça_sert": "Repère plusieurs titres exposés au même pari: IA, semi, mega-cap tech, taux, devise ou région.",
            "comment_lire": "Les winners peuvent rester gros; le modèle évite seulement d’ajouter trop au même risque.",
            "impact_ici": _guardrail_ticker_text(hidden_cluster_tickers, "sizing amorti"),
        },
        {
            "garde_fou": "Anti-overfitting",
            "à_quoi_ça_sert": "Protège les commandes d’audit/tuning contre des ajustements basés seulement sur une période récente.",
            "comment_lire": "Affecte surtout `improvement-audit` et `apply-safe-tuning`, pas la cotisation mensuelle directe.",
            "impact_ici": "Vérifié dans l’audit; aucune action à prendre dans ce rapport compact.",
        },
    ]


def compact_durability_rows(
    rows: list[dict[str, Any]],
    allocated_tickers: set[str],
    limit: int = 28,
) -> list[dict[str, Any]]:
    selected = []
    for row in rows:
        ticker = str(row.get("ticker") or "")
        universe = str(row.get("universe") or "")
        status = str(row.get("long_term_durability_status") or "")
        if (
            universe == "CORE_PORTFOLIO"
            or ticker in allocated_tickers
            or status in {"VERY_DURABLE_COMPOUNDER", "SPECULATIVE_OR_UNPROVEN"}
        ):
            selected.append(row)
    return selected[:limit]


def compact_market_growth_rows_for_compact_report(
    rows: list[dict[str, Any]],
    allocated_tickers: set[str],
    limit: int = 8,
) -> list[dict[str, Any]]:
    selected = []
    priority_statuses = {"STRUCTURAL_TAILWIND", "HYPE_RISK", "MATURE_OR_LOW_GROWTH"}
    for row in rows:
        ticker = str(row.get("ticker") or "")
        universe = str(row.get("universe") or "")
        status = str(row.get("market_growth_thesis_status") or "")
        if universe == "CORE_PORTFOLIO" and (ticker in allocated_tickers or status in priority_statuses):
            selected.append(
                {
                    "ticker": ticker,
                    "statut": status,
                    "score": row.get("market_growth_thesis_score"),
                    "impact": row.get("market_growth_thesis_adjustment"),
                    "confiance": row.get("market_growth_thesis_confidence"),
                    "raison": _compact_sentence(row.get("market_growth_thesis_reason"), 180),
                }
            )
    if selected:
        return selected[:limit]
    return [
        {
            "ticker": "",
            "statut": "AUCUN_SIGNAL_MAJEUR",
            "score": "",
            "impact": "0",
            "confiance": "",
            "raison": "Aucune thèse de marché long terme assez importante pour être affichée dans le rapport compact.",
        }
    ]


def compact_market_growth_rows(
    rows: list[dict[str, Any]],
    allocated_tickers: set[str],
    limit: int = 28,
) -> list[dict[str, Any]]:
    selected = []
    priority_statuses = {"STRUCTURAL_TAILWIND", "ATTRACTIVE_BUT_CYCLICAL", "HYPE_RISK", "MATURE_OR_LOW_GROWTH"}
    for row in rows:
        ticker = str(row.get("ticker") or "")
        universe = str(row.get("universe") or "")
        status = str(row.get("market_growth_thesis_status") or "")
        if universe == "CORE_PORTFOLIO" or ticker in allocated_tickers or status in priority_statuses:
            selected.append(row)
    return selected[:limit]


def compact_cash_flow_rows(
    rows: list[dict[str, Any]],
    allocated_tickers: set[str],
    limit: int = 28,
) -> list[dict[str, Any]]:
    selected = []
    priority_statuses = {
        "EXCELLENT_CASH_COMPOUNDER",
        "GOOD_CASH_GENERATOR",
        "WEAK_CASH_CONVERSION",
        "CASH_FLOW_STRESS",
        "CASH_FLOW_UNCERTAIN",
    }
    for row in rows:
        ticker = str(row.get("ticker") or "")
        universe = str(row.get("universe") or "")
        status = str(row.get("cash_flow_quality_status") or "")
        if universe == "CORE_PORTFOLIO" or ticker in allocated_tickers or status in priority_statuses:
            selected.append(row)
    return selected[:limit]


def compact_shareholder_discipline_rows(
    rows: list[dict[str, Any]],
    allocated_tickers: set[str],
    limit: int = 24,
) -> list[dict[str, Any]]:
    selected = []
    priority_statuses = {"SHAREHOLDER_FRIENDLY", "ACCEPTABLE_DILUTION", "DILUTION_WATCH", "HIGH_DILUTION_RISK"}
    for row in rows:
        ticker = str(row.get("ticker") or "")
        universe = str(row.get("universe") or "")
        status = str(row.get("shareholder_discipline_status") or "")
        if universe == "CORE_PORTFOLIO" or ticker in allocated_tickers or status in priority_statuses:
            selected.append(row)
    return selected[:limit]


def compact_market_rows(rows: list[dict[str, Any]], limit: int = 18) -> list[dict[str, Any]]:
    priority_statuses = {"MANUAL_REVIEW_TOP_CANDIDATE", "PROMISING_BUT_INCOMPLETE", "TOO_EXPENSIVE"}
    selected = [row for row in rows if row.get("candidate_status") in priority_statuses]
    return selected[:limit] or rows[: min(limit, len(rows))]


def compact_discovery_rows(rows: list[dict[str, Any]], limit: int = 12) -> list[dict[str, Any]]:
    return rows[:limit]


def compact_discovery_maintenance_rows(rows: list[dict[str, Any]], limit: int = 12) -> list[dict[str, Any]]:
    return _discovery_maintenance_rows_for_report(rows)[:limit]


def compact_opportunity_rows(
    rows: list[dict[str, Any]],
    allocated_tickers: set[str],
    limit: int = 34,
) -> list[dict[str, Any]]:
    selected = []
    for row in rows:
        ticker = str(row.get("ticker") or "")
        universe = str(row.get("universe") or "")
        status = str(row.get("opportunity_cost_status") or "")
        action = str(row.get("allocation_decision") or "")
        if (
            universe == "CORE_PORTFOLIO"
            or ticker in allocated_tickers
            or status == "CLEARLY_BETTER_THAN_VFV"
            or action in {"MANUAL_REVIEW_TOP_CANDIDATE", "HIGH_PRIORITY_WATCH"}
        ):
            selected.append(row)
    return selected[:limit]


def compact_trend_rows(rows: list[dict[str, Any]], limit: int = 18) -> list[dict[str, Any]]:
    selected = [
        row
        for row in rows
        if row.get("trend_status") not in {"NEW", "STABLE", ""}
        or safe_float(row.get("score_total_change")) not in {None, 0.0}
        or safe_float(row.get("conviction_score_change")) not in {None, 0.0}
        or safe_float(row.get("capital_allocation_score_change")) not in {None, 0.0}
    ]
    if selected:
        return selected[:limit]
    return [
        {
            "ticker": "",
            "universe": "",
            "trend_status": "AUCUNE_TENDANCE_MAJEURE",
            "trend_severity": "",
            "history_reference_count": "",
            "history_reference_dates": "",
            "score_total_change": "",
            "conviction_score_change": "",
            "capital_allocation_score_change": "",
            "previous_thesis_status": "",
            "current_thesis_status": "",
            "previous_liquidation_status": "",
            "current_liquidation_status": "",
            "previous_allocation_decision": "",
            "previous_final_position_action": "",
            "trend_reasons": "Aucun changement historique significatif à afficher dans le rapport court.",
        }
    ]


def compact_quality_drawdown_rows(
    rows: list[dict[str, Any]],
    allocated_tickers: set[str],
    limit: int = 14,
) -> list[dict[str, Any]]:
    selected = []
    for row in rows:
        status = str(row.get("quality_drawdown_status") or "")
        ticker = str(row.get("ticker") or "")
        if status in {"", "NO_DRAWDOWN_SIGNAL"}:
            continue
        if (
            ticker in allocated_tickers
            or status in {"QUALITY_DRAWDOWN_OPPORTUNITY", "PRICE_WEAKNESS_WITH_FUNDAMENTAL_RISK", "AVOID_FALLING_KNIFE"}
            or row.get("universe") == "CORE_PORTFOLIO"
        ):
            selected.append(
                {
                    "ticker": row.get("ticker"),
                    "statut": status,
                    "score": row.get("quality_drawdown_score"),
                    "impact_allocation": row.get("quality_drawdown_allocation_adjustment"),
                    "contexte_nouvelles": row.get("news_context_status"),
                    "lecture": _compact_sentence(row.get("quality_drawdown_reason"), 170),
                    "titres_récents": _compact_list(_as_list(row.get("news_context_headlines")), limit=3),
                }
            )
    if selected:
        return selected[:limit]
    return [
        {
            "ticker": "",
            "statut": "AUCUNE_OPPORTUNITE_DRAWDOWN",
            "score": "",
            "impact_allocation": "",
            "contexte_nouvelles": "",
            "lecture": "Aucune baisse de qualité assez claire pour bonifier une allocation.",
            "titres_récents": "",
        }
    ]


def compact_core_for_compact_report(
    rows: list[dict[str, Any]],
    allocated_tickers: set[str],
    limit: int = 16,
) -> list[dict[str, Any]]:
    selected = []
    for row in rows:
        ticker = str(row.get("ticker_display") or row.get("ticker") or "")
        if row.get("ticker") == "VFV.TO" or row.get("benchmark_role") is True:
            continue
        allocation = str(row.get("allocation_decision") or "")
        final_action = str(row.get("final_position_action") or row.get("decision") or "")
        monitoring = str(row.get("monitoring_status") or "NORMAL")
        sell = str(row.get("sell_status") or row.get("liquidation_status") or "")
        drawdown_status = str(row.get("quality_drawdown_status") or "")
        include = (
            ticker in allocated_tickers
            or allocation in {"BUY / ADD", "ADD_WITH_MONITORING", "ELIGIBLE_BUT_NOT_SELECTED"}
            or sell in {"YELLOW", "ORANGE", "RED"}
            or monitoring != "NORMAL"
            or drawdown_status in {"QUALITY_DRAWDOWN_OPPORTUNITY", "PRICE_WEAKNESS_WITH_FUNDAMENTAL_RISK", "AVOID_FALLING_KNIFE"}
        )
        if not include and len(selected) >= 8:
            continue
        selected.append(
            {
                "ticker": ticker,
                "allocation": allocation or final_action,
                "score": row.get("capital_allocation_score"),
                "cagr": row.get("expected_cagr_quality"),
                "vs_vfv": row.get("opportunity_cost_status"),
                "thèse": row.get("thesis_status"),
                "vente": sell,
                "surveillance": monitoring,
                "drawdown": drawdown_status,
                "raison": _compact_sentence(row.get("allocation_decision_reason") or row.get("final_position_reason"), 150),
            }
        )
    return selected[:limit]


def compact_validation_priority_for_compact_report(rows: list[dict[str, Any]], limit: int = 8) -> list[dict[str, Any]]:
    output = []
    for row in rows[:limit]:
        output.append(
            {
                "ticker": row.get("ticker"),
                "donnée": row.get("field_label") or row.get("field"),
                "importance": row.get("priority"),
                "pourquoi": _compact_sentence(row.get("decision_impact") or row.get("suggested_action"), 160),
            }
        )
    return output or [{"ticker": "", "donnée": "", "importance": "AUCUNE_PRIORITE", "pourquoi": "Aucune donnée prioritaire."}]


def compact_risk_for_compact_report(portfolio_risk: dict[str, Any], limit: int = 20) -> list[dict[str, Any]]:
    rows = [row for row in risk_rows_for_output(portfolio_risk) if str(row.get("risk_level") or "") != "INFO"]
    if not rows:
        rows = risk_rows_for_output(portfolio_risk)
    output = [
        {
            "risk_type": row.get("risk_type"),
            "risk_level": row.get("risk_level"),
            "description": _compact_sentence(row.get("description"), 150),
            "impact": row.get("impact"),
        }
        for row in rows
    ]
    displayed_clusters = {
        str(row.get("description") or "").split(":", 1)[0].strip()
        for row in output
        if "cluster" in str(row.get("risk_type") or "").lower()
    }
    for cluster, exposure in sorted(
        (portfolio_risk.get("hidden_cluster_exposure") or {}).items(),
        key=lambda item: safe_float(item[1]) or 0.0,
        reverse=True,
    ):
        weight = safe_float(exposure) or 0.0
        if not cluster or cluster in displayed_clusters or weight <= 0:
            continue
        output.append(
            {
                "risk_type": "cluster_caché",
                "risk_level": "SECONDARY",
                "description": f"{cluster}: exposition agrégée",
                "impact": f"Poids concerné: {pct(weight, 1)}",
            }
        )
    return output[:limit]


def compact_portfolio_risk_weight_rows(
    values: dict[str, Any],
    *,
    label_key: str,
    category: str,
    limit: int = 10,
) -> list[dict[str, str]]:
    sorted_items = sorted(
        values.items(),
        key=lambda item: safe_float(item[1]) or 0.0,
        reverse=True,
    )
    rows = []
    for name, raw_weight in sorted_items[:limit]:
        weight = safe_float(raw_weight) or 0.0
        rows.append(
            {
                label_key: str(name),
                "poids": pct(weight, 1),
                "lecture": _portfolio_risk_weight_note(category, str(name), weight),
            }
        )
    if rows:
        return rows
    return [{label_key: "Donnée pas dispo", "poids": "Donnée pas dispo", "lecture": "Aucune donnée de concentration disponible."}]


def _portfolio_risk_weight_note(category: str, name: str, weight: float) -> str:
    clean_name = str(name or "").strip().lower()
    if clean_name in {"unknown", "donnée pas dispo", "donnee pas dispo", ""}:
        return "Classification incomplète: à corriger si cette ligne devient importante."
    if category == "sector":
        if weight > 0.55:
            return "Risque sectoriel extrême: le portefeuille dépend beaucoup de ce secteur."
        if weight > 0.40:
            return "Risque sectoriel élevé: ajout dans ce secteur à faire avec forte conviction."
        if weight > 0.25:
            return "Exposition importante mais acceptable si les titres restent de haute qualité."
        return "Exposition modérée."
    if category == "region":
        if weight > 0.75:
            return "Région dominante: risque pays/devise à surveiller."
        if weight > 0.50:
            return "Forte exposition régionale, normale si assumée par la stratégie."
        return "Exposition régionale secondaire ou diversifiante."
    if category == "factor":
        if weight > 0.40:
            return "Corrélation cachée possible: plusieurs titres peuvent réagir au même moteur."
        if weight > 0.25:
            return "Facteur important à surveiller, sans bloquer les meilleurs compounders."
        return "Facteur secondaire."
    return "À surveiller selon le contexte."


def compact_tax_for_compact_report(tax_report: list[dict[str, Any]], limit: int = 8) -> list[dict[str, Any]]:
    rows = [
        row
        for row in tax_rows_for_output(tax_report)
        if row.get("warning") and "Aucune alerte" not in str(row.get("warning"))
    ]
    if not rows:
        rows = tax_rows_for_output(tax_report)[:3]
    return [
        {
            "ticker": row.get("ticker"),
            "account_type": row.get("account_type"),
            "tax_comment": _compact_sentence(row.get("tax_comment"), 130),
            "warning": _compact_sentence(row.get("warning"), 130),
        }
        for row in rows[:limit]
    ]


def compact_account_performance_for_compact_report(rows: list[dict[str, Any]], limit: int = 6) -> list[dict[str, Any]]:
    display_rows = account_performance_rows_for_report(rows)
    return [
        {
            "account_type": row.get("account_type"),
            "preferred_performance_summary": _compact_sentence(row.get("preferred_performance_summary"), 180),
            "portfolio_return_since_tracking": row.get("portfolio_return_since_tracking"),
            "sp500_return_since_tracking": row.get("sp500_return_since_tracking"),
            "excess_return_vs_sp500": row.get("excess_return_vs_sp500"),
            "twr_excess_vs_sp500": row.get("twr_excess_vs_sp500"),
            "twr_status": row.get("twr_status"),
            "value_added_vs_sp500_cad": row.get("value_added_vs_sp500_cad"),
            "value_added_vs_sp500_percent": row.get("value_added_vs_sp500_percent"),
            "xirr_excess_vs_sp500": row.get("xirr_excess_vs_sp500"),
            "xirr_status": row.get("xirr_status"),
            "interpretation": _compact_sentence(row.get("interpretation"), 150),
        }
        for row in display_rows[:limit]
    ]


def compact_portfolio_changes_for_compact_report(
    current_rows: list[dict[str, Any]],
    history_rows: list[dict[str, Any]],
    limit: int = 6,
) -> list[dict[str, Any]]:
    real_current = [row for row in current_rows if str(row.get("change_type") or "") != "BASELINE"]
    substantive_current = _substantive_portfolio_change_rows(real_current)
    substantive_history = _substantive_portfolio_change_rows(history_rows)
    source_rows = substantive_current or real_current
    source_label = "Depuis la dernière analyse"
    if not source_rows:
        source_rows = substantive_history or [row for row in history_rows if str(row.get("change_type") or "") != "BASELINE"]
        source_label = "Dernier historique connu"
    display_rows = portfolio_change_rows_for_report(_sort_portfolio_changes_for_compact(source_rows), limit=limit)
    output = []
    for row in display_rows:
        output.append(
            {
                "date": row.get("date"),
                "ticker": row.get("ticker"),
                "compte": row.get("account_type"),
                "changement": row.get("change_type"),
                "variation": row.get("shares_change"),
                "valeur_estimée": row.get("estimated_change_value_cad"),
                "lecture": _compact_sentence(f"{source_label}. {row.get('reason') or ''}", 150),
            }
        )
    if output:
        return output
    return [
        {
            "date": "",
            "ticker": "",
            "compte": "",
            "changement": "AUCUN_CHANGEMENT_DETECTE",
            "variation": "",
            "valeur_estimée": "",
            "lecture": "Aucune modification récente détectée dans portfolio.csv depuis le début du suivi.",
        }
    ]


def compact_portfolio_change_summary_for_compact_report(
    rows: list[dict[str, Any]],
    limit: int = 6,
) -> list[dict[str, Any]]:
    sorted_rows = sorted(rows, key=lambda row: str(row.get("last_change_date") or row.get("first_change_date") or ""), reverse=True)
    output = []
    for row in sorted_rows[:limit]:
        output.append(
            {
                "compte": row.get("account_type"),
                "ticker": row.get("ticker"),
                "achats/ajouts": row.get("buy_or_add_count"),
                "ventes/réductions": row.get("sell_or_reduce_count"),
                "variation_nette": row.get("net_shares_change"),
                "valeur_nette_estimée": money(safe_float(row.get("estimated_net_add_value_cad"))),
                "dernière_date": row.get("last_change_date"),
            }
        )
    if output:
        return output
    return [
        {
            "compte": "",
            "ticker": "",
            "achats/ajouts": "",
            "ventes/réductions": "",
            "variation_nette": "",
            "valeur_nette_estimée": "",
            "dernière_date": "Aucun résumé cumulatif encore disponible.",
        }
    ]


def compact_account_allocation_for_compact_report(rows: list[dict[str, Any]], limit: int = 8) -> list[dict[str, Any]]:
    display_rows = account_chart_rows_for_report(rows)
    output = []
    for row in display_rows[:limit]:
        output.append(
            {
                "compte": row.get("account_type"),
                "valeur_totale": row.get("total_value_cad"),
                "positions": row.get("positions_count"),
                "principales_positions": row.get("top_positions"),
                "note": _compact_sentence(row.get("note"), 120),
            }
        )
    if output:
        return output
    return [
        {
            "compte": "",
            "valeur_totale": "",
            "positions": "",
            "principales_positions": "",
            "note": "Aucune répartition par compte disponible.",
        }
    ]


def compact_account_charts_markdown(rows: list[dict[str, Any]]) -> list[str]:
    if not rows:
        return [
            "Aucun diagramme généré: aucune position avec une valeur positive n’a été trouvée par compte.",
            "",
        ]

    lines = [
        "Diagrammes circulaires par compte, basés sur la valeur actuelle estimée en CAD.",
        "",
    ]
    for row in rows:
        account_type = row.get("account_type") or "UNKNOWN"
        chart_path = row.get("chart_path")
        if not chart_path:
            continue
        lines.extend(
            [
                f"#### {account_type}",
                "",
                f"![Répartition du compte {account_type}]({chart_path})",
                "",
            ]
        )
    return lines


def compact_defensive_etf_rows_for_report(rows: list[dict[str, Any]], limit: int = 8) -> list[dict[str, Any]]:
    selected = [
        row
        for row in rows
        if row.get("selected_for_allocation") is True
        or row.get("selector_status") in {"SELECTED_AUTO_FALLBACK", "RESERVE_SAME_CATEGORY", "RESERVE_MODE_LIMIT"}
        or row.get("status") in {"WATCH_ONLY"}
    ]
    if not selected:
        return [
            {
                "ticker": "",
                "statut": "DESACTIVE",
                "score": "",
                "rôle": "",
                "raison": "Couche ETF défensive inactive pour ce mode.",
            }
        ]
    return [
        {
            "ticker": row.get("ticker"),
            "statut": row.get("selector_status") or row.get("status"),
            "score": row.get("defensive_score"),
            "rôle": row.get("role"),
            "raison": _compact_sentence(row.get("selector_reason") or row.get("reason"), 170),
        }
        for row in selected[:limit]
    ]


def compact_external_etf_rows_for_report(rows: list[dict[str, Any]], limit: int = 8) -> list[dict[str, Any]]:
    selected = [
        row
        for row in rows
        if row.get("external_etf_allocation_status")
        in {"ELIGIBLE_EXTERNAL_ETF_ALLOCATION", "WATCH_ONLY_EXTERNAL_ETF", "INSUFFICIENT_ETF_DATA"}
    ]
    if not selected:
        return [
            {
                "ticker": "",
                "statut": "AUCUN_ETF_EXTERNE",
                "score": "",
                "fit_mode": "",
                "raison": "Aucun ETF externe admissible ou à surveiller dans les listes externes.",
            }
        ]
    return [
        {
            "ticker": row.get("ticker"),
            "statut": row.get("external_etf_allocation_status"),
            "score": row.get("external_etf_score"),
            "fit_mode": row.get("mode_fit"),
            "raison": _compact_sentence(row.get("reason"), 170),
        }
        for row in selected[:limit]
    ]


def compact_proxy_summary_for_compact_report(rows: list[dict[str, Any]], limit: int = 8) -> list[dict[str, Any]]:
    selected = [
        row
        for row in rows
        if row.get("reliability_status") in {"RECALIBRATION_CANDIDATE", "MONITOR_MORE_EXAMPLES", "NEED_MORE_EXAMPLES"}
    ]
    if not selected:
        selected = rows[:3]
    return [
        {
            "field": row.get("field"),
            "reliability_status": row.get("reliability_status"),
            "recommended_action": _compact_sentence(row.get("recommended_action"), 170),
        }
        for row in selected[:limit]
    ]


def compact_proxy_correction_audit_rows(rows: list[dict[str, Any]], limit: int = 8) -> list[dict[str, Any]]:
    display_rows = proxy_correction_audit_rows_for_report(rows)
    selected = [
        row
        for row in display_rows
        if str(row.get("status") or "") not in {"ACTIVE_OK", "DISABLED", "NO_ACTIVE_CORRECTIONS"}
    ]
    if not selected:
        selected = display_rows[:3]
    return [
        {
            "field": row.get("field"),
            "status": row.get("status"),
            "risk_level": row.get("risk_level"),
            "factor": row.get("factor"),
            "recommended_action": _compact_sentence(row.get("recommended_action"), 170),
            "reason": _compact_sentence(row.get("reason"), 190),
        }
        for row in selected[:limit]
    ]


def compact_external_candidates_for_compact_report(
    watchlist_analyses: dict[str, dict[str, Any]],
    market_analyses: dict[str, dict[str, Any]],
    market_universe: dict[str, dict[str, Any]],
    discovery_analyses: dict[str, dict[str, Any]],
    discovery_universe: dict[str, dict[str, Any]],
    core_analyses: dict[str, dict[str, Any]],
    portfolio_risk: dict[str, Any],
    limit: int = 8,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if len(rows) < limit:
        for row in build_market_candidate_rows(market_analyses, market_universe):
            if row.get("candidate_status") in {"MANUAL_REVIEW_TOP_CANDIDATE", "PROMISING_BUT_INCOMPLETE"}:
                rows.append(
                    {
                        "source": "MARKET_UNIVERSE",
                        "ticker": row.get("ticker_display") or row.get("ticker"),
                        "status": row.get("candidate_status"),
                        "score": row.get("score_total"),
                        "raison": _compact_sentence(row.get("reason"), 160),
                    }
                )
    if len(rows) < limit:
        for row in build_discovery_idea_rows(discovery_analyses, discovery_universe, report_only=True):
            if row.get("discovery_status") == "ADD_TO_MARKET_UNIVERSE_REVIEW":
                rows.append(
                    {
                        "source": "DISCOVERY",
                        "ticker": row.get("ticker_display") or row.get("ticker"),
                        "status": row.get("discovery_status"),
                        "score": row.get("score_total"),
                        "raison": _compact_sentence(row.get("reason"), 160),
                    }
                )
    if not rows:
        return [
            {
                "source": "",
                "ticker": "",
                "status": "AUCUNE_CANDIDATE_EXTERNE_PRIORITAIRE",
                "score": "",
                "raison": "Aucun titre externe ne mérite une action prioritaire.",
            }
        ]
    return rows[:limit]


def _blocked_external_validation_rows_for_compact_report(
    watchlist_analyses: dict[str, dict[str, Any]],
    market_analyses: dict[str, dict[str, Any]],
    discovery_analyses: dict[str, dict[str, Any]],
    limit: int = 5,
) -> tuple[list[dict[str, Any]], int]:
    rows: list[dict[str, Any]] = []
    for provenance, universe in [
        ("Watchlist", watchlist_analyses or {}),
        ("Market", market_analyses or {}),
        ("Discovery", discovery_analyses or {}),
    ]:
        for ticker, analysis in universe.items():
            if str(analysis.get("external_validation_status") or "") != "BLOCKED_PENDING_PERSONAL_VALIDATION":
                continue
            display_ticker = analysis.get("ticker_display") or analysis.get("ticker") or ticker
            score = safe_float(analysis.get("capital_allocation_score"))
            rows.append(
                {
                    "ticker": display_ticker,
                    "provenance": provenance,
                    "score": round(score, 2) if score is not None else "N/D",
                    "fourchette_confiance": analysis.get("score_confidence_label") or "N/D",
                    "pdf_suggéré": f"{display_ticker}_{today_iso()}_BNCD_Morningstar.pdf",
                    "action": "Déposer le PDF dans le dossier BNCD/Morningstar puis relancer l'analyse.",
                }
            )
    if not rows:
        return (
            [
                {
                    "ticker": "AUCUN_CANDIDAT_BLOQUE",
                    "provenance": "",
                    "score": "",
                    "fourchette_confiance": "",
                    "pdf_suggéré": "",
                    "action": "Tous les candidats externes évalués disposent d'au moins une donnée validée personnellement.",
                }
            ],
            0,
        )
    rows = sorted(rows, key=lambda row: safe_float(row.get("score")) or 0.0, reverse=True)
    return rows[:limit], max(0, len(rows) - limit)


def compact_promotion_rows_for_compact_report(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    output = []
    for row in rows:
        output.append(
            {
                "source": row.get("universe"),
                "ticker": row.get("ticker_display") or row.get("ticker"),
                "statut": row.get("promotion_status"),
                "raison": _compact_sentence(row.get("reason"), 180),
                "prochaine_étape": _compact_sentence(row.get("next_step"), 180),
            }
        )
    return output


def _weakest_core_compact_alert_lines(rows: list[dict[str, Any]]) -> list[str]:
    if not rows:
        return []
    row = rows[0]
    if _csv_bool(row.get("same_result")):
        return []
    active = row.get("current_weakest_ticker") or "N/D"
    candidate = row.get("candidate_weakest_ticker") or "N/D"
    status = row.get("audit_status") or "OBSERVE_ONLY"
    interpretation = _compact_sentence(row.get("interpretation"), 220)
    suffix = f" {interpretation}" if interpretation else ""
    return [
        "- Audit weakest core: **AUDIT-ONLY — aucune recommandation modifiée.** "
        f"Logique active: {active}; logique candidate: {candidate}; statut: {status}.{suffix}"
    ]


def _csv_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value or "").strip().lower() in {"1", "true", "yes", "oui"}


def _thesis_reversal_compact_summary(rows: list[dict[str, Any]], limit: int = 5) -> str:
    alerts = [
        row
        for row in rows
        if str(row.get("thesis_reversal_status") or "") in {"WATCH", "REVIEW", "BROKEN"}
    ]
    if not alerts:
        return "Thesis reversal: aucun renversement majeur détecté."
    shown = alerts[:limit]
    summary = ", ".join(f"{row.get('ticker')}={row.get('thesis_reversal_status')}" for row in shown)
    suffix = f" (+{len(alerts) - limit})" if len(alerts) > limit else ""
    return (
        f"Thesis reversal: {summary}{suffix}. Audit-only: aucune vente automatique; "
        "revue manuelle avant nouvel ajout si REVIEW/HIGH."
    )


def compact_thesis_reversal_rows_for_full_report(rows: list[dict[str, Any]], limit: int = 24) -> list[dict[str, Any]]:
    alerts = [
        row
        for row in rows
        if str(row.get("thesis_reversal_status") or "") in {"WATCH", "REVIEW", "BROKEN"}
    ]
    selected = alerts or rows[:1]
    if not selected:
        selected = [
            {
                "ticker": "",
                "previous_thesis_status": "",
                "current_thesis_status": "",
                "thesis_reversal_status": "NONE",
                "thesis_reversal_severity": 0,
                "manual_review_priority": "LOW",
                "conclusion_basis": "NO_ALERT",
                "data_quality_driven": False,
                "score_contradiction_flag": False,
                "reason_fr": "Aucun renversement de thèse disponible dans cette analyse.",
            }
        ]
    output = []
    for row in selected[:limit]:
        output.append(
            {
                "ticker": row.get("ticker_display") or row.get("ticker"),
                "previous_thesis_status": row.get("previous_thesis_status"),
                "current_thesis_status": row.get("current_thesis_status"),
                "thesis_reversal_status": row.get("thesis_reversal_status"),
                "thesis_reversal_severity": row.get("thesis_reversal_severity"),
                "manual_review_priority": row.get("manual_review_priority"),
                "conclusion_basis": row.get("conclusion_basis"),
                "data_quality_driven": row.get("data_quality_driven"),
                "score_contradiction_flag": row.get("score_contradiction_flag"),
                "reason_fr": _compact_sentence(row.get("reason_fr"), 260),
            }
        )
    return output


def compact_source_rows_for_compact_report(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "source": row.get("source"),
            "utilisation": _compact_sentence(row.get("utilisation"), 170),
            "éléments_consultés": _compact_sentence(row.get("éléments consultés") or row.get("éléments_consultés"), 260),
            "limite": _compact_sentence(row.get("limite"), 170),
        }
        for row in rows
    ]


def compact_cache_health_rows(rows: list[dict[str, Any]], limit: int = 8) -> list[dict[str, Any]]:
    if not rows:
        return [
            {
                "category": "cache",
                "status": "NON_VERIFIE",
                "count": "",
                "cleaned_count": "",
                "details": "Cache non vérifié pendant cette analyse.",
                "suggested_action": "Relancer health-check si nécessaire.",
            }
        ]
    priority = {"WARN": 0, "FAIL": 0, "INFO": 1, "PASS": 2}
    selected = sorted(rows, key=lambda row: (priority.get(str(row.get("status") or ""), 3), str(row.get("category") or "")))
    return [
        {
            "category": row.get("category"),
            "status": row.get("status"),
            "count": row.get("count"),
            "cleaned_count": row.get("cleaned_count"),
            "details": _compact_sentence(row.get("details"), 180),
            "suggested_action": _compact_sentence(row.get("suggested_action"), 180),
        }
        for row in selected[:limit]
    ]


def compact_stability_rows(rows: list[dict[str, Any]], limit: int = 16) -> list[dict[str, Any]]:
    selected = [
        row
        for row in rows
        if abs(safe_float(row.get("allocation_stability_adjustment")) or 0.0) > 0
        or row.get("allocation_decision") == "BUY / ADD"
        or row.get("final_position_action") == "ADD_WITH_MONITORING"
    ]
    return selected[:limit] or rows[: min(limit, len(rows))]


def compact_cycle_rows(
    rows: list[dict[str, Any]],
    allocated_tickers: set[str],
    limit: int = 24,
) -> list[dict[str, Any]]:
    selected = []
    for row in rows:
        ticker = str(row.get("ticker") or "")
        level = str(row.get("cycle_bubble_risk_level") or "")
        universe = str(row.get("universe") or "")
        if ticker in allocated_tickers or universe == "CORE_PORTFOLIO" and level in {"HIGH", "EXTREME"} or level == "EXTREME":
            selected.append(row)
    return selected[:limit]


def compact_market_regime_analysis_rows(rows: list[dict[str, Any]], limit: int = 12) -> list[dict[str, Any]]:
    selected = [row for row in rows if abs(safe_float(row.get("market_regime_allocation_adjustment")) or 0.0) > 0]
    return selected[:limit] or rows[: min(limit, len(rows))]


def compact_sector_euphoria_analysis_rows(rows: list[dict[str, Any]], limit: int = 12) -> list[dict[str, Any]]:
    selected = [row for row in rows if abs(safe_float(row.get("sector_euphoria_allocation_adjustment")) or 0.0) > 0]
    return selected[:limit] or rows[: min(limit, len(rows))]


def compact_ticker_issue_rows(rows: list[dict[str, Any]], limit: int = 18) -> list[dict[str, Any]]:
    selected = [
        row
        for row in rows
        if row.get("ticker_validation_status") not in {"OK", "ETF_OR_BENCHMARK", "ETF_OR_FUND", ""}
        or row.get("ticker_coverage_status") not in {"OK", "ETF_OR_BENCHMARK", "ETF_OR_FUND", "GOOD_COVERAGE", ""}
        or row.get("free_data_coverage_class") not in {"GOOD_COVERAGE", "ETF_OR_BENCHMARK", "ETF_OR_FUND", ""}
        or row.get("issues")
    ]
    return selected[:limit] or [
        {
            "ticker_display": "",
            "input_tickers": "",
            "resolved_ticker": "",
            "intended_company_name": "",
            "company_name_found": "",
            "ticker_validation_status": "AUCUN_TICKER_PROBLEMATIQUE",
            "ticker_coverage_status": "",
            "free_data_coverage_class": "",
            "free_data_coverage_score": "",
            "suggested_yahoo_tickers": "",
            "issues": "",
            "suggested_action": "Aucun ticker problématique majeur à afficher dans le rapport court.",
        }
    ]


def compact_data_gap_rows(
    rows: list[dict[str, Any]],
    validation_priority_rows: list[dict[str, Any]],
    limit: int = 20,
) -> list[dict[str, Any]]:
    priority_tickers = [str(row.get("ticker") or "") for row in validation_priority_rows if row.get("ticker")]
    selected = [row for row in rows if str(row.get("ticker") or "") in priority_tickers]
    selected.extend(row for row in rows if row not in selected)
    return selected[:limit]


def compact_auto_estimate_rows(
    rows: list[dict[str, Any]],
    allocated_tickers: set[str],
    validation_priority_rows: list[dict[str, Any]],
    limit: int = 24,
) -> list[dict[str, Any]]:
    priority_tickers = {str(row.get("ticker") or "") for row in validation_priority_rows if row.get("ticker")}
    selected = [
        row
        for row in rows
        if str(row.get("ticker") or "") in allocated_tickers or str(row.get("ticker") or "") in priority_tickers
    ]
    selected.extend(row for row in rows if row not in selected and str(row.get("importance") or "") in {"HIGH", "TRES_HAUTE"})
    return selected[:limit]


def compact_data_freshness_rows(
    rows: list[dict[str, Any]],
    allocated_tickers: set[str],
    limit: int = 12,
) -> list[dict[str, Any]]:
    selected = [
        row
        for row in rows
        if str(row.get("ticker") or "") in allocated_tickers
        or str(row.get("universe") or "") == "CORE_PORTFOLIO"
    ]
    selected.extend(row for row in rows if row not in selected)
    return selected[:limit]


def compact_proxy_calibration_rows(rows: list[dict[str, Any]], limit: int = 24) -> list[dict[str, Any]]:
    usable = [row for row in rows if str(row.get("true_value") or "").strip()]
    if not usable:
        return [
            {
                "ticker": "",
                "field": "",
                "true_value": "",
                "proxy_value": "",
                "difference": "",
                "relative_difference": "",
                "comparison_status": "AUCUNE_VRAIE_DONNEE_AFFICHER",
                "recalibration_hint": "Aucune vraie donnée utilisable n’est affichée dans le rapport court. Le détail complet reste dans latest_proxy_calibration.csv.",
            }
        ]
    selected = [
        row
        for row in usable
        if str(row.get("comparison_status") or "") not in {"MATCH", "CLOSE", "OK"}
        or str(row.get("recalibration_hint") or "").strip()
    ]
    return selected[:limit] or usable[: min(limit, len(usable))]


def _compact_position_reason(row: dict[str, Any]) -> str:
    reasons = [
        row.get("final_position_reason"),
        row.get("allocation_decision_reason"),
        row.get("add_eligibility_reason"),
        _first_signal(row.get("monitoring_reasons")),
        _first_signal(row.get("technical_or_valuation_signals")),
        row.get("score_evidence_reason"),
    ]
    for reason in reasons:
        text = str(reason or "").strip()
        if text and text != "Aucun":
            return text
    return "Aucune raison prioritaire."


def _core_focus_sort_key(row: dict[str, Any], is_allocated: bool) -> tuple[float, float, float, float, float]:
    sell_rank = {"RED": 4.0, "ORANGE": 3.0, "YELLOW": 2.0, "GREEN": 0.0}.get(
        str(row.get("sell_status") or row.get("liquidation_status") or ""),
        0.0,
    )
    monitoring_rank = 1.0 if str(row.get("monitoring_status") or "NORMAL") not in {"NORMAL", "", "BENCHMARK"} else 0.0
    cycle_rank = {"EXTREME": 2.0, "HIGH": 1.0}.get(str(row.get("cycle_bubble_risk_level") or ""), 0.0)
    score = safe_float(row.get("capital_allocation_score")) or 0.0
    return (1.0 if is_allocated else 0.0, sell_rank, monitoring_rank, cycle_rank, score)


def true_missing_data_rows(data_gaps: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [row for row in data_gaps if not str(row.get("data_field") or "").startswith("AUTO_ESTIMATE:")]


def auto_estimate_rows_for_output(data_gaps: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for row in data_gaps:
        field = str(row.get("data_field") or "")
        if not field.startswith("AUTO_ESTIMATE:"):
            continue
        display = field.replace("AUTO_ESTIMATE:", "", 1).strip()
        rows.append(
            {
                "ticker": row.get("ticker"),
                "data_field": display,
                "importance": row.get("importance"),
                "impact": row.get("impact"),
                "forward_eps": row.get("forward_eps"),
                "trailing_eps": row.get("trailing_eps"),
                "number_of_analyst_opinions": row.get("number_of_analyst_opinions"),
                "forward_eps_growth_direct": row.get("forward_eps_growth_direct"),
                "forward_eps_growth_confidence": row.get("forward_eps_growth_confidence"),
                "data_source_forward": row.get("data_source_forward"),
                "eps_growth_5y_proxy_sanity": row.get("eps_growth_5y_proxy_sanity"),
                "early_deterioration_signal": row.get("early_deterioration_signal"),
            }
        )
    return rows


def stress_rows_for_csv(stress_tests: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for scenario in stress_tests:
        rows.append(
            {
                "scenario": scenario.get("scenario"),
                "scenario_type": scenario.get("scenario_type", "static_single_shock"),
                "scenario_quality": scenario.get("scenario_quality", ""),
                "estimated_loss_dollars": scenario.get("estimated_loss_dollars"),
                "estimated_loss_percent": scenario.get("estimated_loss_percent"),
                "max_drawdown_percent": scenario.get("max_drawdown_percent", ""),
                "worst_phase_name": scenario.get("worst_phase_name", ""),
                "worst_phase_return": scenario.get("worst_phase_return", ""),
                "top_contributors": _stress_ticker_summary(scenario.get("top_contributors", []), "estimated_loss"),
                "amplifying_tickers": _stress_ticker_summary(scenario.get("amplifying_tickers", []), "scenario_return"),
                "resilient_tickers": _stress_ticker_summary(scenario.get("resilient_tickers", []), "scenario_return"),
                "diagnostic_only": scenario.get("diagnostic_only", False),
                "primary_risk": scenario.get("primary_risk"),
            }
        )
    return rows


def _stress_ticker_summary(rows: list[dict[str, Any]], metric: str) -> str:
    rows = rows or []
    parts = []
    for row in rows[:3]:
        ticker = row.get("ticker")
        if not ticker:
            continue
        value = safe_float(row.get(metric))
        if metric == "estimated_loss":
            display = money(value)
        elif value is None:
            display = "Donnée pas dispo"
        else:
            display = pct(value, 1)
        parts.append(f"{ticker} ({display})")
    return ", ".join(parts)


def _stress_sector_theme_summary(rows: list[dict[str, Any]]) -> str:
    rows = rows or []
    parts = []
    for row in rows[:3]:
        label = row.get("sector_theme")
        if not label:
            continue
        parts.append(f"{label} ({money(row.get('estimated_loss'))})")
    return ", ".join(parts)


def write_risk_csv(path: str | Path, portfolio_risk: dict[str, Any]) -> None:
    write_csv_records(path, risk_rows_for_output(portfolio_risk), RISK_COLUMNS)


def write_tax_csv(path: str | Path, tax_report: list[dict[str, Any]]) -> None:
    write_csv_records(path, tax_rows_for_output(tax_report), TAX_COLUMNS)


def durability_rows_for_csv(*analysis_groups: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for group in analysis_groups:
        for row in sorted(group.values(), key=lambda item: (str(item.get("universe")), str(item.get("ticker")))):
            if row.get("ticker") == "VFV.TO" or row.get("benchmark_role") is True:
                continue
            rows.append(
                {
                    "universe": row.get("universe"),
                    "ticker": row.get("ticker_display", row.get("ticker")),
                    "long_term_durability_score": row.get("long_term_durability_score"),
                    "long_term_durability_status": row.get("long_term_durability_status"),
                    "long_term_durability_reason": row.get("long_term_durability_reason"),
                    "expected_cagr_quality": row.get("expected_cagr_quality"),
                    "cycle_bubble_risk_level": row.get("cycle_bubble_risk_level"),
                    "thesis_status": row.get("thesis_status"),
                    "data_reliability_level": row.get("data_reliability_level"),
                }
            )
    return sorted(rows, key=_durability_sort_key, reverse=True)


def write_proxy_calibration_csv(path: str | Path, rows: list[dict[str, Any]]) -> None:
    write_csv_records(path, proxy_calibration_rows_for_report(rows), PROXY_CALIBRATION_REPORT_COLUMNS)


def write_proxy_calibration_summary_csv(path: str | Path, rows: list[dict[str, Any]]) -> None:
    write_csv_records(path, proxy_calibration_summary_rows_for_report(rows), PROXY_CALIBRATION_SUMMARY_COLUMNS)


def proxy_correction_audit_rows_for_report(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if rows:
        return rows
    return [
        {
            "field": "",
            "status": "NO_AUDIT_AVAILABLE",
            "risk_level": "LOW",
            "factor": "",
            "confidence": "",
            "sample_count": "",
            "last_updated": "",
            "days_since_update": "",
            "bias_status": "",
            "bias_confidence": "",
            "bias_sample_count": "",
            "current_suggested_factor": "",
            "factor_gap": "",
            "max_safe_factor_change": "",
            "recommended_action": "Relancer une analyse complète pour générer l’audit.",
            "reason": "Aucune ligne d’audit des corrections proxy n’a été fournie.",
        }
    ]


def proxy_calibration_rows_for_report(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if rows:
        return rows
    return [
        {
            "ticker": "",
            "company_name": "",
            "field": "",
            "true_value": "",
            "proxy_value": "",
            "difference": "",
            "relative_difference": "",
            "comparison_status": "AUCUNE_DONNEE_FOURNIE",
            "recalibration_hint": "Remplir data/proxy_calibration.csv pour comparer les proxies aux vraies données.",
            "proxy_source": "",
            "source": "",
            "source_date": "",
            "confidence": "",
            "notes": "",
        }
    ]


def proxy_calibration_summary_rows_for_report(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if rows:
        return rows
    return [
        {
            "field": "",
            "filled_examples": 0,
            "usable_examples": 0,
            "match_count": 0,
            "close_count": 0,
            "review_count": 0,
            "missing_proxy_count": 0,
            "invalid_count": 0,
            "average_difference": "",
            "average_relative_difference": "",
            "bias_direction": "WAITING_FOR_EXAMPLES",
            "reliability_status": "AUCUNE_DONNEE_FOURNIE",
            "recommended_action": "Remplir data/proxy_calibration.csv avec plusieurs exemples avant de recalibrer une formule.",
        }
    ]


def allocation_rows_for_csv(allocations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for row in allocations:
        ticker = row.get("destination", row.get("ticker", ""))
        data_confidence_badge = row.get("data_confidence_badge", "")
        if not data_confidence_badge and normalize_ticker(ticker) == "VFV.TO":
            data_confidence_badge = "ETF_N/A"
        rows.append(
            {
                "ticker": ticker,
                "amount": safe_float(row.get("montant", row.get("amount"))) or 0.0,
                "percentage": safe_float(row.get("pourcentage", row.get("percentage"))) or 0.0,
                "reason": row.get("raison", row.get("reason", "")),
                "confidence": row.get("niveau de confiance", row.get("confidence", "MEDIUM")),
                "allocation_type": row.get("bloc", row.get("allocation_type", "")),
                "reliability_cap_status": row.get("reliability_cap_status", ""),
                "reliability_cap_applied": row.get("reliability_cap_applied", ""),
                "reliability_allocation_cap_percent": row.get("reliability_allocation_cap_percent", ""),
                "reliability_allocation_cap_amount": row.get("reliability_allocation_cap_amount", ""),
                "reliability_cap_reason": row.get("reliability_cap_reason", ""),
                "capital_allocation_confidence_range": row.get("capital_allocation_confidence_range", ""),
                "capital_allocation_confidence_label": row.get("capital_allocation_confidence_label", ""),
                "single_name_concentration_status": row.get("single_name_concentration_status", ""),
                "single_name_concentration_guardrail_applied": row.get("single_name_concentration_guardrail_applied", ""),
                "single_name_concentration_current_weight": row.get("single_name_concentration_current_weight", ""),
                "single_name_concentration_monthly_cap": row.get("single_name_concentration_monthly_cap", ""),
                "single_name_concentration_target_cap": row.get("single_name_concentration_target_cap", ""),
                "single_name_concentration_reason": row.get("single_name_concentration_reason", ""),
                "decision_quality": row.get("decision_quality", ""),
                "decision_quality_score": row.get("decision_quality_score", ""),
                "decision_quality_reason": row.get("decision_quality_reason", ""),
                "data_confidence_badge": data_confidence_badge,
                "canadian_tax_advantage_active": row.get("canadian_tax_advantage_active", False),
            }
        )
    return rows


def _allocation_reliability_cap_text(row: dict[str, Any]) -> str:
    status = str(row.get("reliability_cap_status") or "")
    if not status or status == "NONE":
        return "aucun"
    cap = safe_float(row.get("reliability_allocation_cap_percent"))
    applied = row.get("reliability_cap_applied")
    prefix = "appliqué" if str(applied).lower() in {"true", "1", "yes"} or applied is True else "non appliqué"
    cap_text = pct(cap, 0) if cap is not None else "N/D"
    return f"{status} {prefix} max {cap_text}"


def _allocation_single_name_concentration_text(row: dict[str, Any]) -> str:
    status = str(row.get("single_name_concentration_status") or "")
    if not status or status == "NONE":
        return "aucun"
    cap = safe_float(row.get("single_name_concentration_monthly_cap"))
    weight = safe_float(row.get("single_name_concentration_current_weight"))
    applied = row.get("single_name_concentration_guardrail_applied")
    prefix = "appliqué" if str(applied).lower() in {"true", "1", "yes"} or applied is True else "observé"
    cap_text = pct(cap, 0) if cap is not None else "N/D"
    weight_text = pct(weight, 1) if weight is not None else "N/D"
    return f"{status} {prefix}, poids {weight_text}, max mensuel {cap_text}"


def allocation_change_rows_for_report(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not rows:
        return [
            {
                "ticker": "",
                "previous_amount": "",
                "current_amount": "",
                "change_amount": "",
                "previous_percentage": "",
                "current_percentage": "",
                "change_status": "NO_HISTORY",
                "main_explanation": "Aucune référence d’allocation précédente disponible.",
                "decision_impact": "Explication seulement; ne modifie pas l’allocation.",
                "reference_dates": "",
            }
        ]
    display_rows = []
    for row in rows:
        display_rows.append(
            {
                **row,
                "previous_amount": money(row.get("previous_amount")),
                "current_amount": money(row.get("current_amount")),
                "change_amount": money(row.get("change_amount")),
                "previous_percentage": pct(row.get("previous_percentage"), 1),
                "current_percentage": pct(row.get("current_percentage"), 1),
            }
        )
    return display_rows


def allocation_justification_rows_for_report(
    allocation_rows: list[dict[str, Any]],
    analyses: dict[str, dict[str, Any]],
    allocation_change_rows: list[dict[str, Any]],
    portfolio_change_rows: list[dict[str, Any]],
    portfolio_change_history_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    rows = [row for row in allocation_rows if (safe_float(row.get("amount")) or 0.0) > 0]
    if not rows:
        return [
            {
                "ticker": "",
                "montant": "",
                "pourquoi_ce_titre": "Aucune allocation positive dans cette analyse.",
                "pourquoi_ce_montant": "",
                "vs_dernière_recommandation": "",
                "lien_avec_portefeuille": "",
            }
        ]

    change_by_ticker = {str(row.get("ticker") or ""): row for row in allocation_change_rows}
    output = []
    for row in rows:
        ticker = str(row.get("ticker") or "")
        analysis = analyses.get(ticker, {})
        output.append(
            {
                "ticker": ticker,
                "montant": f"{money(safe_float(row.get('amount')))} ({pct(safe_float(row.get('percentage')), 1)})",
                "pourquoi_ce_titre": _allocation_choice_reason(ticker, analysis, row),
                "pourquoi_ce_montant": _allocation_amount_reason(row, analysis),
                "vs_dernière_recommandation": _allocation_previous_recommendation_text(
                    change_by_ticker.get(ticker),
                ),
                "lien_avec_portefeuille": _allocation_portfolio_change_text(
                    ticker,
                    portfolio_change_rows,
                    portfolio_change_history_rows,
                ),
            }
        )
    return output


def allocation_recommendation_narrative(
    allocation_rows: list[dict[str, Any]],
    analyses: dict[str, dict[str, Any]],
    allocation_change_rows: list[dict[str, Any]] | None = None,
    qualitative_moat_rows: list[dict[str, Any]] | None = None,
    company_dossier_rows: list[dict[str, Any]] | None = None,
) -> str:
    selected = [
        row
        for row in allocation_rows
        if (safe_float(row.get("amount")) or 0.0) > 0 and str(row.get("ticker") or "") != "VFV.TO"
    ]
    if not selected:
        return (
            "Aucune position individuelle autre que VFV.TO ne reçoit de capital dans cette recommandation. "
            "Cela signifie que, selon les règles actuelles, les preuves disponibles ne justifient pas de forcer une "
            "cotisation vers une entreprise précise; le filet indiciel est donc préféré jusqu’à ce qu’un titre offre "
            "un meilleur équilibre entre qualité, thèse intacte, valorisation, risque et avantage clair face à VFV.TO."
        )

    selected = sorted(selected, key=lambda row: safe_float(row.get("amount")) or 0.0, reverse=True)
    change_by_ticker = {str(row.get("ticker") or ""): row for row in allocation_change_rows or []}
    qualitative_by_ticker = {
        str(row.get("ticker") or ""): row
        for row in qualitative_moat_rows or []
        if row.get("ticker")
    }
    dossier_by_ticker = {
        str(row.get("ticker") or ""): row
        for row in company_dossier_rows or []
        if row.get("ticker")
    }
    tickers = ", ".join(str(row.get("ticker") or "") for row in selected)
    sections = [
        f"En excluant VFV.TO, la cotisation va vers {tickers} parce que ces positions ressortent comme les meilleurs "
        "compromis actuels entre qualité d’entreprise, potentiel de composition long terme, thèse intacte, valorisation "
        "acceptable et risque de portefeuille. L’agent ne récompense pas seulement une hausse ou une baisse de prix: "
        "il exige que l’avantage attendu reste supérieur au coût d’opportunité de VFV.TO. Les textes ci-dessous détaillent "
        "chaque titre recommandé séparément.",
        "",
    ]
    for index, row in enumerate(selected, start=1):
        ticker = str(row.get("ticker") or "")
        sections.extend(
            [
            _allocation_position_narrative(
                ticker,
                row,
                analyses.get(ticker, {}),
                change_by_ticker.get(ticker),
                qualitative_by_ticker.get(ticker),
                dossier_by_ticker.get(ticker),
                rank=index,
                selected_count=len(selected),
                ),
                "",
            ]
        )
    sections.append(
        "Cette lecture reste une recommandation mécanique et probabiliste: elle indique où le prochain dollar semble "
        "le mieux aligné avec ton profil haut CAGR 15-30 ans, avec garde-fous contre concentration, mode de marché, "
        "valorisation extrême et thèse qui se détériore."
    )
    return "\n\n".join(section for section in sections if section != "")


def _allocation_position_narrative(
    ticker: str,
    allocation_row: dict[str, Any],
    analysis: dict[str, Any],
    change_row: dict[str, Any] | None,
    qualitative_row: dict[str, Any] | None,
    dossier_row: dict[str, Any] | None,
    *,
    rank: int,
    selected_count: int,
) -> str:
    amount = money(safe_float(allocation_row.get("amount")) or 0.0)
    percentage = pct(safe_float(allocation_row.get("percentage")), 1)
    company = _company_label(ticker, analysis)
    score = safe_float(analysis.get("capital_allocation_score"))
    conviction = safe_float(analysis.get("conviction_score"))
    score_text = []
    if score is not None:
        score_text.append(f"score d’allocation {score:.1f}/100")
    if conviction is not None:
        score_text.append(f"conviction {conviction:.0f}/100")
    if not score_text:
        score_text.append("score d’allocation non disponible")

    expected = _human_status(analysis.get("expected_cagr_quality"))
    opportunity = _human_status(analysis.get("opportunity_cost_status"))
    thesis = _human_status(analysis.get("thesis_status"))
    liquidation = _human_status(analysis.get("liquidation_status"))
    durability = _human_status(analysis.get("long_term_durability_status"))
    market_growth = _human_status(analysis.get("market_growth_thesis_status"))
    cash_flow = _human_status(analysis.get("cash_flow_quality_status"))
    shareholder = _human_status(analysis.get("shareholder_discipline_status"))
    cycle = _human_status(analysis.get("cycle_bubble_risk_level"))
    data_quality = _human_status(analysis.get("data_reliability_level") or analysis.get("data_quality"))
    moat_text = _moat_text(analysis)
    valuation_text = _valuation_text(analysis)
    amount_context = _allocation_amount_driver_text(allocation_row, analysis)
    previous_context = _allocation_change_short_text(change_row)

    rank_text = "première destination hors VFV" if rank == 1 else f"destination #{rank} hors VFV"
    if selected_count == 1:
        rank_text = "seule destination hors VFV"

    profile_text = _business_profile_text(analysis)
    management_text = _management_quality_text(analysis)
    sector_text = _sector_health_text(analysis)
    moat_detail = _moat_detail_text(analysis)
    company_context = _company_specific_context(ticker, analysis, qualitative_row, dossier_row)
    evidence_text = _evidence_source_text(analysis)

    text = (
        f"**{company} — justification détaillée.** {company} reçoit {amount} ({percentage}) comme {rank_text}. "
        f"Son profil est le suivant: {profile_text} Le titre est retenu parce qu’il combine {', '.join(score_text)}, "
        f"un potentiel qualitatif {expected}, une thèse {thesis}, un statut de vente {liquidation} et un avantage vs VFV "
        f"jugé {opportunity}. Le modèle ne le choisit donc pas pour une simple tendance de prix: il estime que le compromis "
        f"qualité, croissance, valorisation et risque marginal est actuellement meilleur que VFV.TO. Le montant reflète "
        f"{amount_context}, {valuation_text}, un risque cycle/bulle {cycle}, un niveau de fiabilité des données {data_quality} "
        f"et l’effet de concentration après achat. {previous_context} "
        f"{company_context} "
        f"Sur l’équipe de gestion, {management_text} L’agent ne rencontre évidemment pas les dirigeants; il évalue plutôt "
        f"les traces mesurables: rentabilité, free cash flow, bilan, dilution, rachats ou émission d’actions. Ici, le "
        f"cash-flow est {cash_flow} et la discipline actionnariale {shareholder}; cela indique si la croissance peut "
        f"devenir de la valeur par action plutôt qu’une simple expansion du chiffre d’affaires. "
        f"Côté secteur, {sector_text} La thèse de marché est {market_growth} et la durabilité 15-30 ans {durability}. "
        f"Pour ton profil, le secteur doit être assez grand et assez sain pour laisser l’entreprise réinvestir longtemps; "
        f"s’il est cyclique ou sensible à une mode, le modèle limite le sizing au lieu de rejeter automatiquement. "
        f"Le moat reste le point central. {moat_detail} {moat_text.capitalize()}. L’avantage recherché est la capacité à "
        f"protéger les marges, conserver les clients, monétiser mieux sans détruire la demande et réinvestir à rendement élevé. "
        f"Le titre est donc choisi parce qu’il combine qualité d’entreprise, santé sectorielle, discipline de gestion, moat, "
        f"valorisation non excessive et compatibilité avec ton horizon 15-30 ans. {evidence_text}"
    )
    return " ".join(text.split())


def _company_label(ticker: str, analysis: dict[str, Any]) -> str:
    name = str(
        analysis.get("company_name")
        or analysis.get("company_name_found")
        or analysis.get("long_name")
        or analysis.get("short_name")
        or ""
    ).strip()
    if name and name.upper() != ticker.upper():
        return f"{ticker} ({name})"
    return ticker


COMPANY_CONTEXTS = {
    "GOOGL": {
        "business": "Alphabet est d’abord une plateforme de recherche, publicité numérique, YouTube, Android et Google Cloud.",
        "moat": "Son rempart spécifique vient surtout de l’échelle des données, de la distribution mondiale de ses produits, de l’intégration de son écosystème et des effets d’habitude autour de Search, YouTube et Android.",
        "pricing": "Sa capacité de monétisation ne dépend pas seulement d’une hausse de prix directe: elle vient aussi de la qualité du ciblage publicitaire, de l’inventaire vidéo, du cloud et de l’intégration de l’IA dans ses produits.",
        "risk": "Le principal contrepoids est le risque réglementaire, la pression concurrentielle en IA/recherche et le caractère cyclique des budgets publicitaires.",
    },
    "META": {
        "business": "Meta est une plateforme sociale et publicitaire centrée sur Facebook, Instagram, WhatsApp, Messenger et ses outils publicitaires.",
        "moat": "Son avantage concurrentiel vient surtout des effets de réseau, de la taille de l’audience, des données d’engagement, des outils annonceurs et de la capacité à diffuser de nouveaux formats à très grande échelle.",
        "pricing": "Sa force de monétisation dépend de la valeur mesurable offerte aux annonceurs et de la capacité à augmenter les impressions, les formats et l’efficacité publicitaire sans faire fuir les utilisateurs.",
        "risk": "Les risques à surveiller sont la réglementation, la dépendance à la publicité, les cycles de budgets marketing et les dépenses lourdes en IA ou Reality Labs.",
    },
    "APP": {
        "business": "AppLovin est une entreprise de logiciel publicitaire et de monétisation d’applications, avec une forte exposition au marché des applications mobiles et de la publicité axée performance.",
        "moat": "Son rempart repose sur ses modèles de ciblage, sa plateforme publicitaire, les données de performance et l’intégration entre acquisition d’utilisateurs, enchères et monétisation.",
        "pricing": "Sa capacité à capter de la valeur dépend moins d’un prix affiché que de la performance livrée aux annonceurs: si la plateforme améliore le retour sur dépenses publicitaires, elle peut capter une part plus élevée du budget client.",
        "risk": "Le risque principal est que le secteur publicitaire mobile reste compétitif et sensible aux changements de plateformes, de confidentialité, de cycles marketing et de concentration client.",
    },
    "MSFT": {
        "business": "Microsoft combine logiciel d’entreprise, cloud Azure, Windows, Office, LinkedIn, sécurité, développeurs et IA.",
        "moat": "Son rempart vient des coûts de changement, de la distribution enterprise, de l’écosystème Office/Azure/Windows, des relations clients et de l’intégration de l’IA dans des produits déjà critiques.",
        "pricing": "Son pouvoir de prix vient des abonnements, de la criticité des outils et de la capacité à ajouter des modules cloud, sécurité et IA dans une base installée massive.",
        "risk": "Les risques principaux sont la concurrence cloud, les dépenses d’infrastructure IA, la réglementation et la pression sur les multiples si la croissance ralentit.",
    },
    "AAPL": {
        "business": "Apple combine matériel premium, services, logiciel, semi-conducteurs internes et écosystème iPhone.",
        "moat": "Son avantage vient de la marque, de l’écosystème, de la fidélité client, de l’intégration matériel/logiciel/services et de coûts de changement élevés.",
        "pricing": "Son pouvoir de prix repose sur la valeur perçue des appareils, l’écosystème et les services récurrents, même si le cycle matériel peut limiter la croissance.",
        "risk": "Les risques sont la maturité du smartphone, la dépendance à l’iPhone, la Chine, la réglementation de l’App Store et une valorisation parfois exigeante.",
    },
    "AVGO": {
        "business": "Broadcom combine semi-conducteurs spécialisés, connectivité, infrastructure réseau et logiciels d’infrastructure.",
        "moat": "Son rempart vient de produits critiques, de positions fortes dans certaines niches, de relations clients profondes et d’une discipline d’acquisition/intégration.",
        "pricing": "Le pouvoir de prix dépend de la criticité des composants et logiciels, mais reste lié aux cycles d’investissement en semi-conducteurs et infrastructure.",
        "risk": "Les risques sont la cyclicité des semi-conducteurs, la concentration client, l’intégration d’acquisitions et les attentes élevées liées à l’IA.",
    },
    "LLY": {
        "business": "Eli Lilly est une pharmaceutique centrée sur médicaments brevetés, innovation clinique et franchises thérapeutiques à forte croissance.",
        "moat": "Son avantage repose sur la propriété intellectuelle, les essais cliniques, les capacités réglementaires, l’échelle commerciale et les barrières scientifiques.",
        "pricing": "Le pouvoir de prix dépend des brevets, de la valeur clinique et du remboursement, mais il est encadré par assureurs, gouvernements et concurrence.",
        "risk": "Les risques principaux sont la concentration de produits, les résultats cliniques, les pressions réglementaires sur les prix et la capacité manufacturière.",
    },
    "MA": {
        "business": "Mastercard exploite un réseau mondial de paiements et de services liés aux transactions numériques.",
        "moat": "Son rempart vient des effets de réseau entre consommateurs, marchands, banques et processeurs, de la marque, de l’acceptation mondiale et de la fiabilité de l’infrastructure.",
        "pricing": "Son pouvoir économique vient du volume de transactions, de la migration du cash vers le numérique et des services à valeur ajoutée, plus que d’une simple hausse de frais.",
        "risk": "Les risques sont la réglementation des frais, la concurrence fintech, les réseaux alternatifs et la sensibilité aux volumes de consommation.",
    },
}


def _company_specific_context(
    ticker: str,
    analysis: dict[str, Any],
    qualitative_row: dict[str, Any] | None = None,
    dossier_row: dict[str, Any] | None = None,
) -> str:
    normalized = str(ticker or analysis.get("ticker") or "").upper()
    normalized = normalized.replace(".TO", "").replace(".V", "")
    context = COMPANY_CONTEXTS.get(normalized)
    if dossier_row and dossier_row.get("dossier_text"):
        source_quality = str(dossier_row.get("source_quality") or "")
        if context and _dossier_needs_curated_context(dossier_row):
            return f"{dossier_row.get('dossier_text')} Fiche interne prudente du modèle: {_curated_company_context_text(context)}"
        if source_quality != "LIMITED_SOURCE" or normalized not in COMPANY_CONTEXTS:
            return str(dossier_row.get("dossier_text"))
    auto_dossier = build_company_dossier(analysis, qualitative_row, target_status="RECOMMANDÉ")
    if auto_dossier.get("dossier_text") and str(auto_dossier.get("source_quality") or "") != "LIMITED_SOURCE":
        if context and _dossier_needs_curated_context(auto_dossier):
            return f"{auto_dossier.get('dossier_text')} Fiche interne prudente du modèle: {_curated_company_context_text(context)}"
        return str(auto_dossier.get("dossier_text"))
    if not context:
        return str(auto_dossier.get("dossier_text") or _industry_specific_context(analysis))
    return f"Spécifiquement, {_curated_company_context_text(context)}"


def _curated_company_context_text(context: dict[str, str]) -> str:
    return (
        f"{context['business']} {context['moat']} {context['pricing']} "
        f"Ce qui peut invalider ou limiter la thèse: {context['risk']}"
    )


def _dossier_needs_curated_context(dossier_row: dict[str, Any]) -> bool:
    if "fiche interne prudente" in str(dossier_row.get("sources_used") or "").lower():
        return False
    missing = str(dossier_row.get("missing_sources") or "").lower()
    text = str(dossier_row.get("business_model") or dossier_row.get("dossier_text") or "").lower()
    lacks_profile_source = "résumé d'activité gratuit yahoo finance" in missing
    generic_business_model = "utilise cette classification" in text or "profil d'activité gratuit assez complet" in text
    return lacks_profile_source or generic_business_model


def _industry_specific_context(analysis: dict[str, Any]) -> str:
    industry = str(analysis.get("industry") or analysis.get("sector") or analysis.get("sector_name") or "").lower()
    if "semiconductor" in industry:
        return (
            "Spécifiquement, le titre est lu comme une entreprise liée aux semi-conducteurs: le moat vient souvent de la propriété intellectuelle, "
            "de la complexité technique, de la relation client et de l’échelle, mais le secteur reste cyclique et sensible aux cycles de capex."
        )
    if "software" in industry or "cloud" in industry or "internet" in industry:
        return (
            "Spécifiquement, le titre est lu comme une entreprise numérique ou logicielle: le moat vient souvent des coûts de changement, "
            "de l’échelle, des données, de la distribution et de la récurrence, mais il faut surveiller la concurrence et la saturation."
        )
    if "pharma" in industry or "health" in industry or "biotech" in industry:
        return (
            "Spécifiquement, le titre est lu comme une entreprise de santé: le moat vient souvent des brevets, données cliniques, capacités réglementaires "
            "et réseaux commerciaux, mais les risques de pipeline, remboursement et réglementation restent importants."
        )
    if "bank" in industry or "financial" in industry or "asset" in industry:
        return (
            "Spécifiquement, le titre est lu comme une entreprise financière: le moat dépend de la marque, de l’échelle, des relations clients, "
            "de la discipline du capital et du cycle de crédit ou de marché."
        )
    return (
        "Spécifiquement, l’agent ne dispose pas encore d’une fiche qualitative détaillée pour cette entreprise. "
        "La personnalisation repose donc surtout sur son secteur, son industrie, ses métriques financières et les rapports locaux disponibles."
    )


def _human_status(value: Any) -> str:
    text = str(value or "N/D").strip()
    if not text:
        return "N/D"
    labels = {
        "VERY_HIGH": "très élevé",
        "HIGH": "élevé",
        "MEDIUM": "moyen",
        "LOW": "faible",
        "VERY_LOW": "très faible",
        "INTACT": "intacte",
        "GREEN": "vert",
        "YELLOW": "jaune",
        "ORANGE": "orange",
        "RED": "rouge",
        "CLEARLY_BETTER_THAN_VFV": "clairement meilleur que VFV",
        "SIMILAR_TO_VFV": "similaire à VFV",
        "WORSE_THAN_VFV": "moins intéressant que VFV",
        "VERY_DURABLE_COMPOUNDER": "très durable",
        "HIGH_GROWTH_BUT_FRAGILE": "croissante mais plus fragile",
        "SPECULATIVE_OR_UNPROVEN": "spéculative ou non prouvée",
        "STRUCTURAL_TAILWIND": "portée par un vent structurel",
        "ATTRACTIVE_BUT_CYCLICAL": "attrayante mais cyclique",
        "HYPE_RISK": "exposée au risque de mode",
        "EXCELLENT_CASH_COMPOUNDER": "excellent",
        "GOOD_CASH_GENERATOR": "solide",
        "WEAK_CASH_CONVERSION": "faible",
        "SHAREHOLDER_FRIENDLY": "favorable",
        "ACCEPTABLE_DILUTION": "acceptable",
        "DILUTION_WATCH": "à surveiller",
        "DISCIPLINED": "disciplinée",
        "MODERATE": "modéré",
        "NORMAL": "normal",
        "LIMITED": "limité",
        "REDUCED": "réduit",
        "STRONG": "fort",
        "VERY_STRONG": "très fort",
    }
    upper = text.upper()
    if upper in labels:
        return labels[upper]
    return text.replace("_", " ").lower()


def _business_profile_text(analysis: dict[str, Any]) -> str:
    label = str(analysis.get("business_profile_label") or analysis.get("business_profile") or "").strip()
    reason = str(analysis.get("business_profile_reason") or "").strip()
    sector = str(analysis.get("sector") or analysis.get("sector_name") or "").strip()
    industry = str(analysis.get("industry") or "").strip()
    parts = []
    if label:
        parts.append(f"profil {label}")
    if sector:
        parts.append(f"secteur {sector}")
    if industry and industry.lower() not in sector.lower():
        parts.append(f"industrie {industry}")
    if reason:
        return f"{', '.join(parts) if parts else 'profil à confirmer'}. {reason}"
    return f"{', '.join(parts) if parts else 'profil d’entreprise à confirmer avec les sources disponibles'}."


def _management_quality_text(analysis: dict[str, Any]) -> str:
    management = analysis.get("management_quality_good")
    balance = analysis.get("balance_sheet_strong")
    fcf_margin = safe_float(analysis.get("free_cash_flow_margin"))
    fcf_conversion = safe_float(analysis.get("fcf_conversion"))
    net_debt_to_fcf = safe_float(analysis.get("net_debt_to_fcf"))
    sbc_to_revenue = safe_float(analysis.get("sbc_to_revenue"))
    share_count_growth = safe_float(analysis.get("share_count_growth_1y"))
    parts = []
    if management is True:
        parts.append("la qualité de gestion est traitée comme favorable")
    elif management is False:
        parts.append("la qualité de gestion demande une validation supplémentaire")
    else:
        parts.append("la qualité de gestion directe n’est pas pleinement observable automatiquement")
    if balance is True:
        parts.append("le bilan est jugé solide")
    elif balance is False:
        parts.append("le bilan est un point de prudence")
    cash_parts = []
    if fcf_margin is not None:
        cash_parts.append(f"marge de free cash flow autour de {fcf_margin:.1%}")
    if fcf_conversion is not None:
        cash_parts.append(f"conversion FCF/bénéfice {fcf_conversion:.2f}x")
    if net_debt_to_fcf is not None:
        cash_parts.append(f"dette nette/FCF {net_debt_to_fcf:.2f}x")
    if cash_parts:
        parts.append("cash-flow: " + ", ".join(cash_parts))
    shareholder_parts = []
    if share_count_growth is not None:
        shareholder_parts.append(f"variation du nombre d’actions {share_count_growth:.1%}")
    if sbc_to_revenue is not None:
        shareholder_parts.append(f"SBC/revenus {sbc_to_revenue:.1%}")
    if shareholder_parts:
        parts.append("discipline actionnariale: " + ", ".join(shareholder_parts))
    return "; ".join(parts) + "."


def _sector_health_text(analysis: dict[str, Any]) -> str:
    sector_cagr = safe_float(analysis.get("sector_cagr_estimated"))
    benchmark_5y = safe_float(analysis.get("benchmark_5y_cagr"))
    benchmark_10y = safe_float(analysis.get("benchmark_10y_cagr"))
    benchmark_above = analysis.get("benchmark_above_sma_200")
    market_status = _human_status(analysis.get("market_growth_thesis_status"))
    confidence = _human_status(analysis.get("market_growth_thesis_confidence"))
    themes = [str(theme) for theme in _as_list(analysis.get("market_growth_thesis_themes")) if theme]
    parts = []
    if sector_cagr is not None:
        parts.append(f"croissance sectorielle estimée autour de {sector_cagr:.1f} %")
    if benchmark_10y is not None:
        parts.append(f"benchmark sectoriel 10 ans à {benchmark_10y:.1%}")
    elif benchmark_5y is not None:
        parts.append(f"benchmark sectoriel 5 ans à {benchmark_5y:.1%}")
    if benchmark_above is True:
        parts.append("benchmark au-dessus de sa moyenne 200 jours")
    elif benchmark_above is False:
        parts.append("benchmark sous sa moyenne 200 jours")
    if market_status != "N/D":
        parts.append(f"thèse de marché {market_status}")
    if confidence != "N/D":
        parts.append(f"confiance {confidence}")
    if themes:
        parts.append(f"thèmes: {_compact_list(themes, limit=4)}")
    if not parts:
        return "La santé du secteur est évaluée avec les proxys gratuits disponibles, mais elle doit encore être validée si la position grossit."
    return "; ".join(parts) + "."


def _moat_detail_text(analysis: dict[str, Any]) -> str:
    durability_status = _human_status(analysis.get("long_term_durability_status"))
    durability_score = safe_float(analysis.get("long_term_durability_score"))
    profile = str(analysis.get("business_profile_label") or analysis.get("business_profile") or "son profil").strip()
    if analysis.get("moat_clear") is True:
        base = (
            f"Le modèle voit un avantage concurrentiel cohérent avec {profile}: capacité à maintenir des marges, "
            "à défendre la relation client et à réinvestir sans dépendre seulement d’un cycle favorable."
        )
    elif analysis.get("moat_clear") is False:
        base = (
            f"Le moat n’est pas considéré assez fort pour être tenu pour acquis; le titre ne devrait donc recevoir du capital "
            "que si les autres preuves compensent clairement ce risque."
        )
    else:
        base = "Le moat reste une donnée à valider, surtout si le titre devient une position plus importante."
    if durability_score is not None:
        base += f" La durabilité long terme est classée {durability_status} avec un score de {durability_score:.1f}/100."
    elif durability_status != "N/D":
        base += f" La durabilité long terme est classée {durability_status}."
    return base


def _evidence_source_text(analysis: dict[str, Any]) -> str:
    sources = []
    sources.extend(str(source) for source in _as_list(analysis.get("official_data_sources")) if source)
    sources.extend(str(source) for source in _as_list(analysis.get("research_report_sources")) if source)
    if analysis.get("source"):
        sources.append(str(analysis.get("source")))
    if analysis.get("market_growth_thesis_sources"):
        sources.extend(str(source) for source in _as_list(analysis.get("market_growth_thesis_sources")) if source)
    ignored = {"stale_cache", "cache", "none", "null", "n/d"}
    unique = []
    for source in sources:
        clean = str(source).strip()
        if clean.lower() in ignored:
            continue
        if clean not in unique:
            unique.append(clean)
    if not unique:
        return "Sources utilisées: données gratuites de marché, historique local, règles du modèle et champs manuels/proxys disponibles."
    return f"Sources utilisées: {_compact_list(unique, limit=6)}."


def _moat_text(analysis: dict[str, Any]) -> str:
    if analysis.get("moat_clear") is True:
        return "le moat est considéré clair par les données disponibles"
    if analysis.get("moat_clear") is False:
        return "le moat n’est pas encore assez confirmé, ce qui limite la lecture"
    return "le moat doit encore être validé si la position devient plus importante"


def _valuation_text(analysis: dict[str, Any]) -> str:
    if analysis.get("quality_but_too_expensive") is True:
        if str(analysis.get("valuation_severity") or "") == "EXPENSIVE_BUT_EXCEPTIONAL":
            return "une valorisation exigeante mais tolérable seulement en petit bloc vu la qualité exceptionnelle"
        if str(analysis.get("valuation_severity") or "") == "EXTREMELY_EXPENSIVE":
            return "une valorisation extrême qui bloque normalement tout nouvel achat"
        return "une qualité reconnue mais une valorisation jugée exigeante"
    ratio = safe_float(analysis.get("price_to_fair_value"))
    if ratio is None:
        price = safe_float(analysis.get("current_price"))
        fair_value = safe_float(analysis.get("fair_value"))
        if price is not None and fair_value not in {None, 0}:
            ratio = price / fair_value
    if ratio is not None:
        if ratio <= 1.2:
            return "une valorisation non extrême face à la juste valeur disponible"
        if ratio <= 1.4:
            return "une valorisation acceptable mais déjà plus exigeante"
        return "une valorisation élevée qui limite le sizing"
    valuation_ok = analysis.get("valuation_vs_5y_avg_ok")
    if valuation_ok is True:
        return "une valorisation jugée raisonnable par rapport à l’historique disponible"
    if valuation_ok is False:
        return "une valorisation jugée exigeante par rapport à l’historique disponible"
    return "les données de valorisation disponibles"


def _allocation_amount_driver_text(allocation_row: dict[str, Any], analysis: dict[str, Any]) -> str:
    add_size = str(analysis.get("add_eligibility_size") or "").strip()
    reason = str(allocation_row.get("reason") or "").strip()
    lower_reason = reason.lower()
    if "quality drawdown" in lower_reason:
        driver = "une opportunité de baisse de qualité encadrée"
    elif "meilleur gain marginal" in lower_reason:
        driver = "le meilleur gain marginal simulé après comparaison avec les autres titres"
    elif "allocation vfv" in lower_reason:
        driver = "le filet indiciel obligatoire"
    elif reason:
        driver = reason.split(".")[0].strip().lower()
    else:
        driver = ""
    if add_size and add_size not in {"BENCHMARK", "FALLBACK", "UNKNOWN"}:
        size_text = _human_status(add_size)
        if driver:
            link = f"au {driver[3:]}" if driver.startswith("le ") else f"à {driver}"
            return f"un sizing {size_text} lié {link}"
        return f"un sizing {size_text}."
    if driver:
        return driver
    return "le score marginal, la concentration, le risque et la comparaison à VFV."


def _allocation_change_short_text(change_row: dict[str, Any] | None) -> str:
    if not change_row:
        return ""
    status = str(change_row.get("change_status") or "N/D")
    previous_amount = safe_float(change_row.get("previous_amount"))
    current_amount = safe_float(change_row.get("current_amount"))
    explanation = str(change_row.get("main_explanation") or "").strip()
    if status in {"NEW_OR_RETURNED", "NO_HISTORY", "NO_ALLOCATION_TO_COMPARE"}:
        return ""
    base = f"Par rapport à la dernière recommandation comparable: {status}, de {money(previous_amount)} à {money(current_amount)}."
    if explanation:
        base += f" {explanation}"
    return base


SELL_RECOMMENDATION_ACTIONS = {
    "REVIEW_TRIM_25",
    "REVIEW_TRIM_50",
    "REVIEW_LIQUIDATE_PROGRESSIVELY",
    "LIQUIDATE_URGENT_REVIEW",
    "TRIM_25_REVIEW",
    "TRIM_50_REVIEW",
    "LIQUIDATE_WINNER_REVIEW",
}


def sell_recommendation_narrative_lines(
    analyses: dict[str, dict[str, Any]],
    company_dossier_rows: list[dict[str, Any]] | None = None,
) -> list[str]:
    rows = [row for row in analyses.values() if _has_real_sell_recommendation(row)]
    rows = sorted(rows, key=_sell_narrative_sort_key, reverse=True)
    if not rows:
        return []
    dossier_by_ticker = {
        str(row.get("ticker") or ""): row
        for row in company_dossier_rows or []
        if row.get("ticker")
    }
    lines = [
        "### Justification détaillée des ventes recommandées",
        "",
        "Cette section apparaît seulement quand l’agent recommande une vraie réduction ou liquidation. Elle ne transforme pas le signal en ordre de vente automatique: elle explique pourquoi une validation manuelle sérieuse est nécessaire avant d’exécuter.",
        "",
    ]
    for row in rows:
        ticker = str(row.get("ticker") or "")
        lines.extend([_sell_position_narrative(row, dossier_by_ticker.get(ticker)), ""])
    return lines


def _has_real_sell_recommendation(row: dict[str, Any]) -> bool:
    action = str(row.get("sell_decision") or row.get("recommended_action") or row.get("winner_protection_action") or "")
    mechanical = str(row.get("mechanical_sell_signal") or "")
    status = str(row.get("sell_status") or row.get("liquidation_status") or "")
    return action in SELL_RECOMMENDATION_ACTIONS or mechanical in {"TRIM_25", "TRIM_50", "LIQUIDATE_PROGRESSIVELY"} or status == "RED"


def _sell_narrative_sort_key(row: dict[str, Any]) -> tuple[float, float, str]:
    status_rank = {"RED": 3.0, "ORANGE": 2.0, "YELLOW": 1.0}.get(str(row.get("sell_status") or row.get("liquidation_status") or ""), 0.0)
    value = safe_float(row.get("current_value_cad") or row.get("current_value")) or 0.0
    return status_rank, value, str(row.get("ticker") or "")


def _sell_position_narrative(row: dict[str, Any], dossier_row: dict[str, Any] | None = None) -> str:
    ticker = str(row.get("ticker_display") or row.get("ticker") or "")
    company = _company_label(str(row.get("ticker") or ticker), row)
    action = str(row.get("sell_decision") or row.get("recommended_action") or row.get("winner_protection_action") or "REVIEW")
    status = _human_status(row.get("sell_status") or row.get("liquidation_status"))
    thesis = _human_status(row.get("thesis_status"))
    mechanical = str(row.get("mechanical_sell_signal") or "NONE")
    confirmed = _as_text_list(row.get("confirmed_fundamental_sell_signals"))
    technical = _as_text_list(row.get("technical_or_valuation_signals"))
    liquidation_reasons = _as_text_list(row.get("liquidation_reasons") or row.get("signals_detected"))
    winner_reason = str(row.get("winner_protection_reason") or "").strip()
    trend_status = _human_status(row.get("trend_status"))
    score_change = safe_float(row.get("score_total_change"))
    conviction_change = safe_float(row.get("conviction_score_change"))
    management_text = _management_quality_text(row)
    sector_text = _sector_health_text(row)
    moat_detail = _moat_detail_text(row)
    company_context = _company_specific_context(str(row.get("ticker") or ticker), row, dossier_row=dossier_row)
    valuation_text = _valuation_text(row)
    data_quality = _human_status(row.get("data_reliability_level") or row.get("data_quality"))
    tax_warning = str(row.get("tax_warning") or "").strip()
    evidence_text = _evidence_source_text(row)
    confirmed_text = _compact_list(confirmed, limit=4) if confirmed else "aucun signal fondamental confirmé listé"
    technical_text = _compact_list(technical, limit=4) if technical else "aucun signal technique/valorisation déterminant"
    reason_text = _compact_list(liquidation_reasons, limit=5) if liquidation_reasons else "raison principale non détaillée"
    change_bits = []
    if score_change is not None:
        change_bits.append(f"score total: {score_change:+.2f}")
    if conviction_change is not None:
        change_bits.append(f"conviction: {conviction_change:+.1f}")
    change_text = ", ".join(change_bits) if change_bits else "historique quantitatif encore limité"
    if not tax_warning:
        tax_warning = "impact fiscal non définitif; à valider si la position est en compte non enregistré."
    if winner_reason:
        winner_sentence = f"La couche de protection des winners ajoute ceci: {winner_reason}"
    else:
        winner_sentence = "La couche de protection des winners ne suffit pas seule: elle sert surtout à éviter de vendre un gagnant sur une volatilité normale."

    text = (
        f"**{company} — justification de vente/réduction.** Le signal actif est `{action}` avec statut de vente {status} "
        f"et signal mécanique `{mechanical}`. L’agent ne recommande pas cette réduction parce que le prix a simplement baissé; "
        f"il le fait seulement quand la combinaison thèse, fondamentaux, historique et risque rend le rendement futur attendu "
        f"moins attrayant que la conservation complète. La thèse est actuellement {thesis}; les signaux fondamentaux confirmés "
        f"sont: {confirmed_text}. Les autres signaux à considérer sont: {technical_text}. La lecture consolidée du moteur est: "
        f"{reason_text}. Cette distinction est importante pour ton profil: une baisse normale d’un winner ne doit pas être vendue, "
        f"mais une baisse accompagnée d’un moat affaibli, d’une marge sous pression, d’une croissance cassée, d’un bilan fragile "
        f"ou d’une tendance historique négative mérite une revue sérieuse. "
        f"Le profil d’entreprise reste analysé avec les mêmes critères que pour un achat: {_business_profile_text(row)} "
        f"{company_context} "
        f"Sur la gestion, {management_text} Si ces signaux deviennent négatifs, le modèle préfère réduire progressivement plutôt "
        f"que rester accroché à l’idée de revenir au prix d’achat. Côté secteur, {sector_text} Une industrie moins saine ou plus "
        f"cyclique ne force pas une vente automatiquement, mais elle diminue la marge d’erreur quand la position montre déjà des "
        f"preuves de détérioration. "
        f"Le moat et l’avantage concurrentiel sont le coeur du diagnostic: {moat_detail} Si ce rempart se détériore, la position "
        f"peut cesser d’être un compounder long terme et devenir un piège de valorisation ou de cycle. La valorisation est lue comme "
        f"{valuation_text}; une valorisation chère n’est pas une raison suffisante pour vendre seule, mais elle devient plus grave "
        f"si la croissance, la rentabilité ou la qualité du secteur diminuent. L’historique récent indique {trend_status}; variation "
        f"des scores: {change_text}. {winner_sentence} Avant exécution, le modèle exige une validation manuelle, surtout si les données "
        f"sont de qualité {data_quality} ou si l’impact fiscal est important. Fiscalité: {tax_warning} {evidence_text}"
    )
    return " ".join(text.split())


def _as_text_list(values: Any) -> list[str]:
    output = []
    for value in _as_list(values):
        text = str(value or "").strip()
        if not text or text == "Aucun":
            continue
        if ";" in text and not text.startswith("http"):
            output.extend(part.strip() for part in text.split(";") if part.strip())
        else:
            output.append(text)
    return output


def _allocation_choice_reason(ticker: str, analysis: dict[str, Any], allocation_row: dict[str, Any]) -> str:
    if ticker == "VFV.TO":
        return "VFV sert de filet de sécurité mécanique quand une partie du capital doit rester exposée au marché large au lieu d’être forcée vers un titre individuel."

    parts = []
    score = safe_float(analysis.get("capital_allocation_score"))
    if score is not None:
        parts.append(f"score d’allocation {score:.1f}/100")
    expected = analysis.get("expected_cagr_quality")
    if expected:
        parts.append(f"CAGR qualitatif {expected}")
    opportunity = analysis.get("opportunity_cost_status")
    if opportunity:
        parts.append(f"vs VFV: {opportunity}")
    thesis = analysis.get("thesis_status")
    liquidation = analysis.get("liquidation_status")
    if thesis or liquidation:
        parts.append(f"thèse {thesis or 'N/D'}, liquidation {liquidation or 'N/D'}")
    decision = analysis.get("allocation_decision")
    if decision:
        parts.append(str(decision))
    if parts:
        return "; ".join(parts) + "."
    reason = str(allocation_row.get("reason") or "").strip()
    return reason or "Titre retenu par le moteur d’allocation parmi les positions admissibles du mode utilisé."


def _allocation_amount_reason(allocation_row: dict[str, Any], analysis: dict[str, Any]) -> str:
    allocation_type = str(allocation_row.get("allocation_type") or "")
    row_reason = str(allocation_row.get("reason") or "").strip()
    if str(allocation_row.get("ticker") or "") == "VFV.TO":
        return f"{allocation_type}. {row_reason}".strip(". ")

    add_size = str(analysis.get("add_eligibility_size") or "").strip()
    stability = str(analysis.get("allocation_stability_status") or "").strip()
    cycle = str(analysis.get("cycle_bubble_risk_level") or "").strip()
    monitoring = str(analysis.get("monitoring_status") or "").strip()

    context = []
    if allocation_type:
        context.append(allocation_type)
    if add_size and add_size not in {"BENCHMARK", "FALLBACK", "UNKNOWN"}:
        context.append(f"sizing permis: {add_size}")
    if monitoring and monitoring not in {"NORMAL", "BENCHMARK"}:
        context.append(f"surveillance: {monitoring}")
    if cycle and cycle not in {"LOW", "NORMAL", "BENCHMARK"}:
        context.append(f"risque cycle/bulle: {cycle}")
    if stability and stability not in {"NEUTRAL_NO_HISTORY", "BENCHMARK"}:
        context.append(f"stabilité: {stability}")
    cap_text = _allocation_reliability_cap_text(allocation_row)
    if cap_text != "aucun":
        context.append(f"cap fiabilité: {cap_text}")
    single_name_text = _allocation_single_name_concentration_text(allocation_row)
    if single_name_text != "aucun":
        context.append(f"concentration individuelle: {single_name_text}")

    prefix = "; ".join(context)
    if row_reason and prefix:
        return f"{prefix}. {row_reason}"
    if row_reason:
        return row_reason
    if prefix:
        return prefix + "."
    return "Montant choisi par le moteur de sizing selon score, conviction, concentration, risque et filet VFV."


def _allocation_previous_recommendation_text(change_row: dict[str, Any] | None) -> str:
    if not change_row:
        return "Aucune recommandation précédente comparable pour ce titre."

    status = str(change_row.get("change_status") or "N/D")
    previous_amount = safe_float(change_row.get("previous_amount"))
    current_amount = safe_float(change_row.get("current_amount"))
    change_amount = safe_float(change_row.get("change_amount"))
    explanation = str(change_row.get("main_explanation") or "").strip()
    reference_dates = str(change_row.get("reference_dates") or "").strip()

    text = (
        f"Avant: {money(previous_amount)}; maintenant: {money(current_amount)}; "
        f"variation: {money(change_amount)}; statut: {status}."
    )
    if explanation:
        text += f" {explanation}"
    if reference_dates:
        text += f" Référence: {reference_dates}."
    return text


def _allocation_portfolio_change_text(
    ticker: str,
    portfolio_change_rows: list[dict[str, Any]],
    portfolio_change_history_rows: list[dict[str, Any]],
) -> str:
    latest_real_changes = _latest_portfolio_changes([*portfolio_change_rows, *portfolio_change_history_rows], include_baseline=False)
    ticker_change = _find_latest_change_for_ticker(ticker, latest_real_changes)
    if ticker_change:
        return "Dernier changement du titre: " + _portfolio_change_sentence(ticker_change)

    latest_any_real = latest_real_changes[0] if latest_real_changes else None
    if latest_any_real:
        return (
            "Aucun changement récent détecté sur ce titre; dernier changement réel du portefeuille: "
            + _portfolio_change_sentence(latest_any_real)
        )

    baseline_changes = _latest_portfolio_changes(portfolio_change_history_rows, include_baseline=True)
    ticker_baseline = _find_latest_change_for_ticker(ticker, baseline_changes)
    if ticker_baseline:
        return "Historique initial seulement pour ce titre; le modèle part de la composition actuelle du portefeuille."
    if baseline_changes:
        return "Aucun changement réel encore détecté; l’historique actuel sert surtout de point de départ."
    return "Aucun historique de changement de portefeuille encore disponible."


def _latest_portfolio_changes(rows: list[dict[str, Any]], *, include_baseline: bool) -> list[dict[str, Any]]:
    filtered = []
    for row in rows:
        change_type = str(row.get("change_type") or "")
        if not include_baseline and change_type in {"BASELINE", "COST_BASIS_UPDATED"}:
            continue
        if not str(row.get("ticker") or "").strip():
            continue
        filtered.append(row)
    return sorted(filtered, key=lambda item: str(item.get("date") or ""), reverse=True)


def _find_latest_change_for_ticker(ticker: str, rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    normalized = str(ticker or "").upper()
    for row in rows:
        if str(row.get("ticker") or "").upper() == normalized:
            return row
    return None


def _portfolio_change_sentence(row: dict[str, Any]) -> str:
    date = row.get("date") or "date inconnue"
    ticker = row.get("ticker") or "titre inconnu"
    account = row.get("account_type") or "compte inconnu"
    change_type = row.get("change_type") or "changement"
    shares_change = safe_float(row.get("shares_change"))
    value = safe_float(row.get("estimated_change_value_cad"))
    details = []
    if shares_change is not None:
        details.append(f"variation {shares_change:g} action(s)")
    if value is not None:
        details.append(f"valeur estimée {money(value)}")
    detail_text = f" ({', '.join(details)})" if details else ""
    return f"{date}: {change_type} sur {ticker} dans {account}{detail_text}."


def _sensitivity_rows_for_display(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    display_rows = []
    for row in rows:
        display_rows.append(
            {
                **row,
                "base_amount": money(safe_float(row.get("base_amount"))),
                "prudent_amount": money(safe_float(row.get("prudent_amount"))),
                "strict_data_amount": money(safe_float(row.get("strict_data_amount"))),
                "min_amount": money(safe_float(row.get("min_amount"))),
                "max_amount": money(safe_float(row.get("max_amount"))),
                "max_change_amount": money(safe_float(row.get("max_change_amount"))),
                "max_change_percent": pct(safe_float(row.get("max_change_percent")), 1),
            }
        )
    return display_rows


def _sensitivity_summary_rows_for_display(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    display_rows = []
    for row in rows:
        display = dict(row)
        for field in ["vfv_base_percent", "vfv_prudent_percent", "vfv_strict_data_percent", "largest_change_percent"]:
            value = safe_float(display.get(field))
            display[field] = pct(value, 1) if value is not None else display.get(field, "")
        if safe_float(display.get("largest_change_amount")) is not None:
            display["largest_change_amount"] = money(safe_float(display.get("largest_change_amount")))
        display_rows.append(display)
    return display_rows


def score_evidence_rows_for_report(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    output = []
    for row in rows:
        if is_etf_asset_analysis(row):
            continue
        output.append(
            {
                "ticker": row.get("ticker_display", row.get("ticker")),
                "score_with_estimates": row.get("score_with_estimates", row.get("score_total")),
                "score_confirmed_only": row.get("score_confirmed_only"),
                "score_estimate_gap": row.get("score_estimate_gap"),
                "score_confidence_range": row.get("score_confidence_range"),
                "score_confidence_label": row.get("score_confidence_label"),
                "score_evidence_level": row.get("score_evidence_level"),
                "score_evidence_penalty": row.get("score_evidence_penalty"),
                "score_evidence_reason": row.get("score_evidence_reason"),
            }
        )
    return output


def sell_signal_rows_for_csv(analyses: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for row in sorted(analyses.values(), key=lambda item: item.get("ticker", "")):
        signals = row["signals_detected"] if "signals_detected" in row else row.get("liquidation_reasons", [])
        if isinstance(signals, list):
            signals = "; ".join(str(item) for item in signals)
        confirmed = row.get("confirmed_fundamental_sell_signals") or []
        weak = row.get("weak_or_unconfirmed_sell_signals") or []
        technical = row.get("technical_or_valuation_signals") or []
        monitoring = row.get("monitoring_reasons") or []
        rows.append(
            {
                "ticker": row.get("ticker"),
                "ticker_display": row.get("ticker_display", row.get("ticker")),
                "resolved_ticker": row.get("resolved_ticker", row.get("ticker")),
                "liquidation_status": row.get("liquidation_status"),
                "sell_status": row.get("sell_status", row.get("liquidation_status")),
                "fundamental_sell_status": row.get("fundamental_sell_status", row.get("liquidation_status")),
                "monitoring_status": row.get("monitoring_status", "NORMAL"),
                "monitoring_decision": row.get("monitoring_decision", "NONE"),
                "sell_decision": row.get("sell_decision", row.get("recommended_action")),
                "allocation_decision": row.get("allocation_decision"),
                "final_position_action": row.get("final_position_action", row.get("decision")),
                "mechanical_sell_signal": row.get("mechanical_sell_signal", "NONE"),
                "sell_review_required": row.get("sell_review_required", False),
                "sell_signal_strength": row.get("sell_signal_strength", "NO_SELL_SIGNAL"),
                "sell_signal_source_summary": row.get("sell_signal_source_summary"),
                "winner_protection_status": row.get("winner_protection_status"),
                "winner_protection_action": row.get("winner_protection_action"),
                "signals_detected": signals,
                "confirmed_fundamental_sell_signals": _list_text(confirmed),
                "weak_or_unconfirmed_sell_signals": _list_text(weak),
                "technical_or_valuation_signals": _list_text(technical),
                "monitoring_reasons": _list_text(monitoring),
                "recommended_action": row.get("recommended_action", row.get("decision")),
            }
        )
    return rows


def sell_rows_for_report(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    output = []
    for row in rows:
        if row.get("ticker") == "VFV.TO" or row.get("liquidation_status") == "BENCHMARK":
            continue
        confirmed = str(row.get("confirmed_fundamental_sell_signals") or "")
        sell_review_required = str(row.get("sell_review_required") or "").lower() == "true" or row.get("sell_review_required") is True
        sell_status = row.get("sell_status", row.get("liquidation_status"))
        output.append(
            {
                "ticker": row.get("ticker"),
                "statut_vente": sell_status,
                "action_recommandée": row.get("sell_decision") or row.get("recommended_action"),
                "raison_principale": (_first_signal(row.get("signals_detected")) or "Aucun signal majeur.")
                if sell_status != "GREEN"
                else "Aucun signal de vente fondamental.",
                "preuve_fondamentale_confirmée": "Oui" if confirmed and confirmed != "Aucun" else "Non",
                "validation_manuelle_requise": "Oui" if sell_review_required else "Non",
                "protection_winner": _winner_protection_label(row),
            }
        )
    return output


def monitoring_rows_for_report(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    output = []
    for row in rows:
        if row.get("ticker") == "VFV.TO" or row.get("liquidation_status") == "BENCHMARK":
            continue
        monitoring_status = str(row.get("monitoring_status") or "NORMAL")
        if monitoring_status == "NORMAL":
            continue
        output.append(
            {
                "ticker": row.get("ticker"),
                "statut_surveillance": monitoring_status,
                "action": row.get("monitoring_decision") or "WATCH_POSITION",
                "raison_principale": _first_signal(row.get("monitoring_reasons")) or _first_signal(row.get("technical_or_valuation_signals")),
                "impact_sur_achat": row.get("add_eligibility_reason") or "Peut limiter le sizing sans déclencher une vente.",
            }
        )
    return output


def risk_rows_for_output(portfolio_risk: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for row in risk_rows_for_csv(portfolio_risk):
        alert = row.get("alert", "")
        weight = safe_float(row.get("weight"))
        rows.append(
            {
                "risk_type": row.get("risk_type"),
                "risk_level": _risk_level(alert),
                "description": f"{row.get('name')}: {alert}",
                "impact": f"Poids concerné: {pct(weight, 1)}" if weight is not None else "Aucune alerte majeure.",
            }
        )
    return rows


def portfolio_history_section(
    section_number: int,
    portfolio_change_display_rows: list[dict[str, Any]],
    portfolio_change_summary_display_rows: list[dict[str, Any]],
    portfolio_change_history_display_rows: list[dict[str, Any]],
    portfolio_transaction_display_rows: list[dict[str, Any]],
    portfolio_inferred_transaction_display_rows: list[dict[str, Any]],
) -> list[str]:
    return [
        f"## {section_number}. Historique automatique des changements du portefeuille",
        "",
        "Cette section se met à jour automatiquement quand `portfolio.csv` change. L’agent compare les actions et les comptes de cette analyse avec l’état précédent, puis inscrit les ajouts, réductions, ventes, transferts possibles et changements de coût moyen.",
        "",
        "`portfolio.csv` reste l’état actuel du portefeuille. L’historique automatique est conservé dans `data/portfolio_change_history.csv` et recopié dans les rapports.",
        "",
        "### Changements détectés depuis la dernière analyse",
        "",
        _markdown_table(
            [
                "date",
                "ticker",
                "account_type",
                "change_type",
                "shares_before",
                "shares_after",
                "shares_change",
                "estimated_change_value_cad",
                "current_value_cad_after",
                "reason",
            ],
            portfolio_change_display_rows
            or [
                {
                    "date": "",
                    "ticker": "",
                    "account_type": "",
                    "change_type": "AUCUN_CHANGEMENT_DETECTE",
                    "shares_before": "",
                    "shares_after": "",
                    "shares_change": "",
                    "estimated_change_value_cad": "",
                    "current_value_cad_after": "",
                    "reason": "Aucune différence de position détectée depuis la dernière analyse.",
                }
            ],
        ),
        "",
        "### Résumé par compte et titre",
        "",
        _markdown_table(
            [
                "account_type",
                "account_tax_category",
                "ticker",
                "buy_or_add_count",
                "sell_or_reduce_count",
                "transfer_count",
                "cost_update_count",
                "net_shares_change",
                "estimated_net_add_value_cad",
                "first_change_date",
                "last_change_date",
            ],
            portfolio_change_summary_display_rows
            or [
                {
                    "account_type": "",
                    "account_tax_category": "",
                    "ticker": "",
                    "buy_or_add_count": "",
                    "sell_or_reduce_count": "",
                    "transfer_count": "",
                    "cost_update_count": "",
                    "net_shares_change": "",
                    "estimated_net_add_value_cad": "",
                    "first_change_date": "",
                    "last_change_date": "",
                }
            ],
        ),
        "",
        "### Derniers changements historiques",
        "",
        _markdown_table(
            [
                "date",
                "ticker",
                "account_type",
                "change_type",
                "shares_before",
                "shares_after",
                "shares_change",
                "estimated_change_value_cad",
                "reason",
            ],
            portfolio_change_history_display_rows
            or [
                {
                    "date": "",
                    "ticker": "",
                    "account_type": "",
                    "change_type": "",
                    "shares_before": "",
                    "shares_after": "",
                    "shares_change": "",
                    "estimated_change_value_cad": "",
                    "reason": "Aucun historique automatique encore disponible.",
                }
            ],
        ),
        "",
        "### Transactions déduites automatiquement",
        "",
        "Ce registre est généré automatiquement à partir des changements détectés dans `portfolio.csv`. Il sert à améliorer la comparaison avec VFV.TO, mais il reste approximatif: le vrai prix de transaction, les frais et l’heure exacte ne sont pas connus.",
        "",
        _markdown_table(
            [
                "date",
                "ticker",
                "account_type",
                "inferred_transaction_type",
                "shares_change",
                "estimated_value_cad",
                "external_flow_cad",
                "sp500_proxy_price_at_flow",
                "confidence",
                "notes",
            ],
            portfolio_inferred_transaction_display_rows
            or [
                {
                    "date": "",
                    "ticker": "",
                    "account_type": "",
                    "inferred_transaction_type": "AUCUNE_TRANSACTION_DEDUITE",
                    "shares_change": "",
                    "estimated_value_cad": "",
                    "external_flow_cad": "",
                    "sp500_proxy_price_at_flow": "",
                    "confidence": "",
                    "notes": "Aucun changement exploitable pour déduire une transaction.",
                }
            ],
        ),
        "",
        "### Registre manuel optionnel",
        "",
        "Ce tableau est seulement utile si vous voulez inscrire manuellement une cotisation en espèces, un dividende ou une note de transaction. Il n’est pas nécessaire pour détecter les changements de positions.",
        "",
        _markdown_table(
            [
                "date",
                "ticker",
                "account_type",
                "transaction_type",
                "shares",
                "trade_value_cad",
                "net_contribution_cad",
                "income_cad",
                "notes",
            ],
            portfolio_transaction_display_rows
            or [
                {
                    "date": "",
                    "ticker": "",
                    "account_type": "",
                    "transaction_type": "",
                    "shares": "",
                    "trade_value_cad": "",
                    "net_contribution_cad": "",
                    "income_cad": "",
                    "notes": "Aucune transaction manuelle inscrite.",
                }
            ],
        ),
        "",
    ]


def portfolio_change_rows_for_report(rows: list[dict[str, Any]], limit: int | None = None) -> list[dict[str, Any]]:
    sorted_rows = sorted(rows, key=lambda row: str(row.get("date") or ""), reverse=True)
    if limit is not None:
        sorted_rows = sorted_rows[:limit]
    output = []
    for row in sorted_rows:
        output.append(
            {
                **row,
                "estimated_change_value_cad": money(safe_float(row.get("estimated_change_value_cad")))
                if safe_float(row.get("estimated_change_value_cad")) is not None
                else "",
                "current_value_cad_after": money(safe_float(row.get("current_value_cad_after")))
                if safe_float(row.get("current_value_cad_after")) is not None
                else "",
            }
        )
    return output


def portfolio_change_summary_rows_for_report(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    output = []
    for row in rows:
        output.append(
            {
                **row,
                "estimated_net_add_value_cad": money(safe_float(row.get("estimated_net_add_value_cad"))),
            }
        )
    return output


def transaction_rows_for_report(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    latest_rows = sorted(rows, key=lambda row: str(row.get("date") or ""), reverse=True)[:12]
    output = []
    for row in latest_rows:
        output.append(
            {
                **row,
                "trade_value_cad": money(safe_float(row.get("trade_value_cad")))
                if safe_float(row.get("trade_value_cad")) is not None
                else "",
                "net_contribution_cad": money(safe_float(row.get("net_contribution_cad")))
                if safe_float(row.get("net_contribution_cad")) not in {None, 0.0}
                else "",
                "income_cad": money(safe_float(row.get("income_cad")))
                if safe_float(row.get("income_cad")) not in {None, 0.0}
                else "",
            }
        )
    return output


def inferred_transaction_rows_for_report(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    output = []
    for row in reportable_inferred_transactions(rows):
        output.append(
            {
                **row,
                "estimated_value_cad": money(safe_float(row.get("estimated_value_cad")))
                if safe_float(row.get("estimated_value_cad")) is not None
                else "",
                "external_flow_cad": money(safe_float(row.get("external_flow_cad")))
                if safe_float(row.get("external_flow_cad")) not in {None, 0.0}
                else "",
                "sp500_proxy_price_at_flow": money(safe_float(row.get("sp500_proxy_price_at_flow")))
                if safe_float(row.get("sp500_proxy_price_at_flow")) is not None
                else "",
            }
        )
    return output


def transaction_summary_rows_for_report(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    output = []
    for row in rows:
        output.append(
            {
                **row,
                "buy_value_cad": money(safe_float(row.get("buy_value_cad"))),
                "sell_value_cad": money(safe_float(row.get("sell_value_cad"))),
                "net_buy_sell_cad": money(safe_float(row.get("net_buy_sell_cad"))),
                "net_contributions_cad": money(safe_float(row.get("net_contributions_cad"))),
                "income_cad": money(safe_float(row.get("income_cad"))),
            }
        )
    return output


def account_performance_rows_for_report(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not rows:
        return [
            {
                "account_type": "",
                "current_value_cad": "",
                "unrealized_gain_percent": "",
                "tracking_start_date": "",
                "benchmark_return_basis": "",
                "portfolio_return_since_tracking": "",
                "sp500_return_since_tracking": "",
                "excess_return_vs_sp500": "",
                "portfolio_twr": "",
                "sp500_twr": "",
                "twr_excess_vs_sp500": "",
                "twr_status": "",
                "twr_period_count": "",
                "twr_method": "",
                "portfolio_xirr": "",
                "sp500_xirr": "",
                "xirr_excess_vs_sp500": "",
                "xirr_status": "",
                "xirr_flow_count": "",
                "xirr_method": "",
                "flow_adjusted_start_date": "",
                "external_flows_cad": "",
                "sp500_equivalent_value_cad": "",
                "value_added_vs_sp500_cad": "",
                "value_added_vs_sp500_percent": "",
                "flow_adjusted_status": "",
                "comparison_status": "AUCUNE_DONNEE",
                "simple_return_status": "",
                "preferred_performance_read": "",
                "preferred_performance_summary": "",
                "interpretation": "Aucune donnée de compte disponible.",
            }
        ]
    output = []
    for row in rows:
        output.append(
            {
                **row,
                "current_value_cad": money(safe_float(row.get("current_value_cad"))),
                "acquisition_value_cad": money(safe_float(row.get("acquisition_value_cad")))
                if safe_float(row.get("acquisition_value_cad")) is not None
                else "",
                "unrealized_gain_cad": money(safe_float(row.get("unrealized_gain_cad")))
                if safe_float(row.get("unrealized_gain_cad")) is not None
                else "",
                "unrealized_gain_percent": pct(safe_float(row.get("unrealized_gain_percent")), 1)
                if safe_float(row.get("unrealized_gain_percent")) is not None
                else "N/D",
                "portfolio_return_since_tracking": _simple_performance_display_value(
                    row, "portfolio_return_since_tracking"
                ),
                "sp500_return_since_tracking": pct(safe_float(row.get("sp500_return_since_tracking")), 1)
                if safe_float(row.get("sp500_return_since_tracking")) is not None
                else "N/D",
                "excess_return_vs_sp500": _simple_performance_display_value(row, "excess_return_vs_sp500"),
                "portfolio_twr": pct(safe_float(row.get("portfolio_twr")), 1)
                if safe_float(row.get("portfolio_twr")) is not None
                else "N/D",
                "sp500_twr": pct(safe_float(row.get("sp500_twr")), 1)
                if safe_float(row.get("sp500_twr")) is not None
                else "N/D",
                "twr_excess_vs_sp500": pct(safe_float(row.get("twr_excess_vs_sp500")), 1)
                if safe_float(row.get("twr_excess_vs_sp500")) is not None
                else "N/D",
                "portfolio_xirr": _xirr_display_value(row, "portfolio_xirr"),
                "sp500_xirr": _xirr_display_value(row, "sp500_xirr"),
                "xirr_excess_vs_sp500": _xirr_display_value(row, "xirr_excess_vs_sp500"),
                "external_flows_cad": money(safe_float(row.get("external_flows_cad")))
                if safe_float(row.get("external_flows_cad")) is not None
                else "",
                "sp500_equivalent_value_cad": money(safe_float(row.get("sp500_equivalent_value_cad")))
                if safe_float(row.get("sp500_equivalent_value_cad")) is not None
                else "N/D",
                "value_added_vs_sp500_cad": money(safe_float(row.get("value_added_vs_sp500_cad")))
                if safe_float(row.get("value_added_vs_sp500_cad")) is not None
                else "N/D",
                "value_added_vs_sp500_percent": pct(safe_float(row.get("value_added_vs_sp500_percent")), 1)
                if safe_float(row.get("value_added_vs_sp500_percent")) is not None
                else "N/D",
            }
        )
    return output


def _account_performance_method_text(*, compact: bool = False) -> str:
    if compact:
        return (
            "Méthode: l’agent compare chaque compte à VFV.TO, utilisé comme proxy S&P 500 en CAD, depuis la première analyse locale disponible. "
            "Quand disponible, VFV est mesuré avec `Adj Close`, un proxy gratuit de rendement total approximatif qui inclut les distributions réinvesties. "
            "`portfolio_return_since_tracking` = valeur actuelle du compte / valeur du compte au début du suivi - 1. "
            "`sp500_return_since_tracking` = prix VFV actuel / prix VFV au début du suivi - 1. "
            "`excess_return_vs_sp500` est l’écart entre les deux, mais il est masqué si des flux rendent le rendement simple trompeur. Si des cotisations ou retraits sont détectés, `value_added_vs_sp500_cad` estime ce que le compte vaudrait si les mêmes flux avaient été investis dans VFV.TO, puis compare cette valeur théorique à la valeur actuelle."
            " La mesure `TWR` neutralise les flux entre snapshots locaux et devient la lecture principale pour juger la stratégie. La mesure `XIRR` ajoute une lecture annualisée plus personnelle; si l’historique local est trop court, le rapport évite d’en tirer une conclusion."
        )
    return "\n".join(
        [
            "Lecture du calcul:",
            "",
            "- Proxy utilisé: `VFV.TO`, car il représente le S&P 500 en dollars canadiens dans le modèle.",
            "- Base de rendement du benchmark: si disponible, l’agent utilise `Adj Close` de yfinance comme proxy gratuit de rendement total approximatif, donc les distributions de VFV sont intégrées dans la comparaison. Si `Adj Close` est indisponible, il revient au prix `Close`.",
            "- Date de départ: la première analyse locale exploitable conservée dans `data/account_performance_history.csv` pour chaque compte.",
            "- Rendement du compte: `valeur actuelle du compte / valeur du compte à la date de départ - 1`.",
            "- Rendement S&P 500: `prix VFV.TO actuel / prix VFV.TO à la date de départ - 1`.",
            "- Écart vs S&P 500: `rendement du compte - rendement VFV.TO`.",
            "- Protection anti-erreur: si des cotisations, retraits, achats ou ventes sont détectés depuis la date de départ, le rapport masque le rendement simple du compte et l’écart simple vs S&P 500, car ces chiffres peuvent confondre argent ajouté et vraie performance.",
            "- TWR du portefeuille: rendement chaîné approximatif entre snapshots locaux; à chaque période, les cotisations/retraits détectés sont retirés du calcul afin de mieux mesurer le mouvement des titres et la qualité de la stratégie.",
            "- TWR du S&P 500: rendement VFV.TO chaîné sur les mêmes dates de snapshots.",
            "- Écart TWR vs S&P 500: `TWR du portefeuille - TWR VFV.TO`. C’est la lecture principale pour juger la stratégie indépendamment du timing des cotisations.",
            "- Valeur équivalente S&P 500: l’agent simule la valeur qu’aurait eue le compte si la valeur de départ, puis les cotisations/retraits détectés, avaient suivi VFV.TO.",
            "- Valeur ajoutée vs S&P 500: `valeur actuelle du compte - valeur équivalente S&P 500`.",
            "- XIRR du portefeuille: rendement annualisé pondéré par l’argent, calculé avec la valeur de départ comme investissement initial, les cotisations/retraits datés, puis la valeur actuelle comme valeur finale.",
            "- XIRR du S&P 500: même logique, mais en simulant que les mêmes flux datés auraient été investis dans VFV.TO.",
            "- Écart XIRR vs S&P 500: `XIRR du portefeuille - XIRR VFV.TO`. C’est la lecture la plus fidèle lorsque les flux et les prix VFV aux dates utiles sont disponibles.",
            "- Prudence: si l’historique local est inférieur à environ 90 jours, le XIRR annualisé peut devenir très extrême; le rapport l’indique alors comme historique trop court au lieu d’en faire une conclusion.",
            "",
            "Limite importante: ce calcul est approximatif. Il dépend de l’historique local conservé, des changements détectés automatiquement dans `portfolio.csv`, des transactions réelles si tu les inscris dans `portfolio_transactions.csv`, du prix VFV disponible aux dates utiles, et ne connaît pas parfaitement les frais, impôts, écarts de prix exacts ou transactions intrajournalières.",
        ]
    )


def account_performance_indicator_legend_rows(*, compact: bool = False) -> list[dict[str, str]]:
    rows = [
        {
            "indicateur": "preferred_performance_summary",
            "à quoi ça sert": "Résumé choisi par le modèle.",
            "comment l’interpréter": "Lis cette phrase en premier: elle privilégie l’indicateur le plus fiable selon les flux détectés.",
        },
        {
            "indicateur": "portfolio_twr",
            "à quoi ça sert": "Mesure la performance de la stratégie du compte.",
            "comment l’interpréter": "Neutralise les cotisations/retraits détectés; c’est la meilleure lecture pour juger le mouvement réel des titres.",
        },
        {
            "indicateur": "twr_excess_vs_sp500",
            "à quoi ça sert": "Compare la stratégie à VFV.TO.",
            "comment l’interpréter": "Positif = la stratégie bat VFV sur l’historique local; négatif = elle est derrière VFV.",
        },
        {
            "indicateur": "value_added_vs_sp500_cad",
            "à quoi ça sert": "Montant gagné ou perdu vs un scénario VFV.",
            "comment l’interpréter": "Estime la différence en dollars si les mêmes flux avaient été investis dans VFV.TO.",
        },
        {
            "indicateur": "portfolio_return_since_tracking",
            "à quoi ça sert": "Rendement simple depuis le début du suivi.",
            "comment l’interpréter": "Utile seulement sans flux importants; sinon le rapport affiche N/D pour éviter de confondre cotisation et rendement.",
        },
        {
            "indicateur": "xirr_excess_vs_sp500",
            "à quoi ça sert": "Compare le rendement annualisé personnel à VFV.",
            "comment l’interpréter": "Très utile après plusieurs mois/années; si l’historique est court, le rapport évite d’en tirer une conclusion.",
        },
    ]
    if compact:
        return rows
    rows.extend(
        [
            {
                "indicateur": "benchmark_return_basis",
                "à quoi ça sert": "Indique la base utilisée pour VFV.",
                "comment l’interpréter": "`ADJUSTED_CLOSE_TOTAL_RETURN_PROXY` est préférable: la comparaison inclut approximativement les distributions réinvesties.",
            },
            {
                "indicateur": "sp500_twr",
                "à quoi ça sert": "TWR de VFV.TO sur les mêmes dates.",
                "comment l’interpréter": "C’est le point de comparaison principal pour savoir si la stratégie fait mieux que le S&P 500 en CAD.",
            },
            {
                "indicateur": "sp500_equivalent_value_cad",
                "à quoi ça sert": "Valeur théorique du compte en version VFV.",
                "comment l’interpréter": "Montre combien le compte vaudrait environ si la valeur initiale et les flux avaient suivi VFV.TO.",
            },
            {
                "indicateur": "external_flows_cad",
                "à quoi ça sert": "Flux détectés depuis le début du suivi.",
                "comment l’interpréter": "Montant de cotisations/retraits/achats déduits qui sont neutralisés dans les lectures ajustées.",
            },
            {
                "indicateur": "twr_status / xirr_status",
                "à quoi ça sert": "Qualité ou état du calcul.",
                "comment l’interpréter": "Indique si le calcul est ajusté des flux, si l’historique est court ou si des données manquent.",
            },
        ]
    )
    return rows


def _simple_performance_display_value(row: dict[str, Any], field: str) -> str:
    status = str(row.get("simple_return_status") or "")
    value = safe_float(row.get(field))
    if value is None:
        return "N/D"
    if status == "FLOW_DISTORTED_BY_CONTRIBUTIONS":
        return "N/D (flux détectés)"
    return pct(value, 1)


def _xirr_display_value(row: dict[str, Any], field: str) -> str:
    status = str(row.get("xirr_status") or "")
    value = safe_float(row.get(field))
    if value is None:
        return "N/D"
    if status == "XIRR_AVAILABLE_SHORT_HISTORY":
        return "N/D (historique < 90 jours)"
    return pct(value, 1)


def tax_rows_for_output(tax_report: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not tax_report:
        return [{"ticker": "", "account_type": "", "tax_comment": "", "warning": "Aucune donnée de compte."}]
    return [
        {
            "ticker": row.get("ticker"),
            "account_type": row.get("account_type"),
            "account_tax_category": row.get("account_tax_category"),
            "shares": row.get("shares"),
            "current_value": money(row.get("current_value")) if safe_float(row.get("current_value")) is not None else None,
            "tax_comment": row.get("tax_location_comment"),
            "warning": row.get("alert"),
        }
        for row in tax_report
    ]


def winner_rows_for_output(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    output = []
    for row in rows:
        output.append(
            {
                **row,
                "average_cost": money(row.get("average_cost")) if safe_float(row.get("average_cost")) is not None else None,
                "average_cost_currency": row.get("average_cost_currency"),
                "average_cost_cad": money(row.get("average_cost_cad")) if safe_float(row.get("average_cost_cad")) is not None else None,
                "acquisition_value": money(row.get("acquisition_value")) if safe_float(row.get("acquisition_value")) is not None else None,
                "acquisition_value_currency": row.get("acquisition_value_currency"),
                "acquisition_value_cad": money(row.get("acquisition_value_cad")) if safe_float(row.get("acquisition_value_cad")) is not None else None,
                "current_value": money(row.get("current_value")) if safe_float(row.get("current_value")) is not None else None,
                "current_value_currency": row.get("current_value_currency"),
                "current_price_cad": money(row.get("current_price_cad")) if safe_float(row.get("current_price_cad")) is not None else None,
                "unrealized_gain_amount": money(row.get("unrealized_gain_amount")) if safe_float(row.get("unrealized_gain_amount")) is not None else None,
                "unrealized_gain_percent": pct(row.get("unrealized_gain_percent"), 1),
                "drawdown_from_personal_high": pct(row.get("drawdown_from_personal_high"), 1),
            }
        )
    return output


def stability_rows_for_report(analyses: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for row in sorted(
        analyses.values(),
        key=lambda item: abs(safe_float(item.get("allocation_stability_adjustment")) or 0.0),
        reverse=True,
    ):
        if row.get("benchmark_role") is True:
            continue
        rows.append(
            {
                "ticker": row.get("ticker_display", row.get("ticker")),
                "allocation_stability_status": row.get("allocation_stability_status", "NEUTRAL_NO_HISTORY"),
                "allocation_stability_adjustment": row.get("allocation_stability_adjustment", 0.0),
                "previous_capital_allocation_score": row.get("previous_capital_allocation_score"),
                "capital_allocation_score_change": row.get("capital_allocation_score_change"),
                "allocation_decision": row.get("allocation_decision"),
                "final_position_action": row.get("final_position_action"),
                "reason": row.get("allocation_stability_reason", "Aucun historique exploitable."),
            }
        )
    return rows


def source_rows_for_report(
    analyses: dict[str, dict[str, Any]],
    watchlist_analyses: dict[str, dict[str, Any]],
    market_analyses: dict[str, dict[str, Any]],
    discovery_analyses: dict[str, dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    discovery_analyses = discovery_analyses or {}
    all_rows = (
        list(analyses.values())
        + list(watchlist_analyses.values())
        + list(market_analyses.values())
        + list(discovery_analyses.values())
    )
    yfinance_tickers = sorted(
        {
            str(row.get("ticker_display") or row.get("ticker"))
            for row in all_rows
            if _uses_yfinance_or_cache(row)
        }
    )
    yfinance_notes = sorted(
        {
            str(note)
            for row in all_rows
            for note in _as_list(row.get("data_source_notes"))
            if note
        }
    )
    rows = [
        {
            "source": "Yahoo Finance via yfinance",
            "utilisation": "Prix, historique, SMA 200, drawdown, rendement, PE/PEG, marges, profil d'activité, secteur/industrie et données financières disponibles gratuitement.",
            "éléments consultés": (
                _compact_list(yfinance_tickers)
                + (
                    " / familles de champs: prix, historique, valorisation, marges, cash-flow, profil d'activité, secteur, industrie, nouvelles yfinance."
                    if yfinance_notes
                    else ""
                )
            ),
            "limite": "Données gratuites parfois incomplètes, retardées, manquantes ou différentes selon la cotation.",
        },
        {
            "source": "Fichiers locaux utilisateur",
            "utilisation": "Portefeuille, comptes, historique automatique des changements, corrections manuelles optionnelles, univers scanner et liste de découverte configurée.",
            "éléments consultés": "data/portfolio.csv, data/portfolio_change_history.csv, data/portfolio_inferred_transactions.csv, data/account_performance_history.csv, data/portfolio_state_snapshot.csv, data/portfolio_transactions.csv, data/manual_inputs_friendly.txt, data/proxy_calibration.csv, config/proxy_corrections.yaml, data/market_universe.csv, config/market_scanner.yaml",
            "limite": "La qualité dépend de ce qui est rempli et de l’exactitude des tickers.",
        },
    ]
    canadian_tickers = sorted(
        {
            str(row.get("ticker_display") or row.get("ticker"))
            for row in all_rows
            if row.get("canadian_data_sources")
            or row.get("canadian_fundamental_fields")
            or row.get("canadian_confirmed_fields")
            or row.get("canadian_data_conflicts")
        }
    )
    canadian_fields = sorted(
        {
            str(field)
            for row in all_rows
            for field in _as_list(row.get("canadian_fundamental_fields")) + _as_list(row.get("canadian_confirmed_fields"))
            if field
        }
    )
    if canadian_tickers:
        rows.append(
            {
                "source": "StockAnalysis Canadian financial pages",
                "utilisation": "Secours gratuit pour certains fondamentaux des titres canadiens: marges, croissance, dette, cash-flow, ROE/ROA et discipline actionnariale quand yfinance couvre mal le titre.",
                "éléments consultés": f"{_compact_list(canadian_tickers)} / champs: {_compact_list(canadian_fields)}",
                "limite": "Source web gratuite non officielle et parfois publiée en millions; l’agent l’utilise surtout pour remplir les champs manquants ou confirmer les ratios comparables, pas pour écraser une bonne donnée yfinance.",
            }
        )

    official_tickers = sorted(
        {
            str(row.get("ticker_display") or row.get("ticker"))
            for row in all_rows
            if row.get("sec_edgar_cik")
        }
    )
    official_fields = sorted(
        {
            str(field)
            for row in all_rows
            for field in _as_list(row.get("official_fundamental_fields")) + _as_list(row.get("official_confirmed_fields"))
            if field and row.get("sec_edgar_cik")
        }
    )
    if official_tickers:
        rows.append(
            {
                "source": "SEC EDGAR companyfacts",
                "utilisation": "Valider ou compléter automatiquement certains fondamentaux officiels des sociétés américaines: marges, croissance annuelle, dette, cash, ROE/ROA. En cas de conflit ambigu, l’agent conserve la donnée de marché gratuite et signale le conflit.",
                "éléments consultés": f"{_compact_list(official_tickers)} / champs: {_compact_list(official_fields)}",
                "limite": "Couvre surtout les sociétés américaines déposant à la SEC; ne remplace pas une lecture complète du 10-K ou des rapports annuels.",
            }
        )
    if any(str(row.get("quote_currency") or row.get("currency") or "").upper() not in {"", "CAD"} for row in all_rows):
        rows.append(
            {
                "source": "Banque du Canada Valet API",
                "utilisation": "Taux de change officiels vers le CAD quand le portefeuille doit convertir des positions étrangères.",
                "éléments consultés": "Séries FXUSDCAD, FXEURCAD, FXGBPCAD, FXCHFCAD ou FXJPYCAD selon les devises présentes.",
                "limite": "Le taux officiel peut être publié avec un délai; si indisponible, l’agent revient aux sources gratuites de marché puis au taux de secours.",
            }
        )
    news_tickers = sorted(
        {
            str(row.get("ticker_display") or row.get("ticker"))
            for row in all_rows
            if row.get("news_context_headlines") or row.get("news_red_flags")
        }
    )
    news_sources = sorted(
        {
            str(source)
            for row in all_rows
            for source in _as_list(row.get("news_context_sources"))
            if source
        }
    )
    news_channels = sorted(
        {
            str(channel)
            for row in all_rows
            for channel in _as_list(row.get("news_context_source_channels"))
            if channel
        }
    )
    if news_tickers:
        rows.append(
            {
                "source": "Flux gratuits de nouvelles: yfinance/Yahoo Finance + Google News RSS",
                "utilisation": "Titres d’articles récents utilisés seulement comme contexte pour distinguer baisse temporaire, pression sectorielle et risque fondamental possible.",
                "éléments consultés": (
                    f"{_compact_list(news_tickers)} / canaux: {_compact_list(news_channels)} "
                    f"/ médias affichés: {_compact_list(news_sources)}"
                ),
                "limite": "Ces flux gratuits sont incomplets, parfois bruyants et ne remplacent pas les communiqués officiels, rapports trimestriels ou analyses BNCD/Morningstar.",
            }
        )
    market_growth_tickers = sorted(
        {
            str(row.get("ticker_display") or row.get("ticker"))
            for row in all_rows
            if row.get("market_growth_thesis_score") not in {None, ""}
        }
    )
    market_growth_sources = sorted(
        {
            str(source)
            for row in all_rows
            for source in _as_list(row.get("market_growth_thesis_sources"))
            if source
        }
    )
    if market_growth_tickers:
        rows.append(
            {
                "source": "Thèse de marché long terme: sources publiques gratuites",
                "utilisation": "Identifier si le marché adressable bénéficie d’un vent structurel durable avant d’ajuster légèrement le sizing.",
                "éléments consultés": f"{_compact_list(market_growth_tickers)} / références: {_compact_list(market_growth_sources)}",
                "limite": "Cette couche reste modérée: elle ne prédit pas la taille exacte du marché et ne remplace pas les fondamentaux de l’entreprise.",
            }
        )
    research_sources = sorted(
        {
            str(source)
            for row in all_rows
            for source in _as_list(row.get("research_report_sources"))
            if source
        }
    )
    research_tickers = sorted(
        {
            str(row.get("ticker_display") or row.get("ticker"))
            for row in all_rows
            if row.get("research_report_sources")
        }
    )
    if research_sources:
        rows.append(
            {
                "source": "Rapports locaux BNCD/Morningstar",
                "utilisation": "Compléter certaines données fondamentales manquantes: juste valeur, moat, risques, bilan, marges ou valorisation quand détectable.",
                "éléments consultés": f"{_compact_list(research_tickers)} / fichiers: {_compact_list(research_sources)}",
                "limite": "Extraction automatique imparfaite; les PDF doivent être validés manuellement et ne doivent pas être recopiés longuement.",
            }
        )
    dossier_tickers = sorted(
        {
            str(row.get("ticker_display") or row.get("ticker"))
            for row in all_rows
            if row.get("business_summary")
            or row.get("research_report_sources")
            or row.get("market_growth_thesis_sources")
            or row.get("official_data_sources")
        }
    )
    if dossier_tickers:
        rows.append(
            {
                "source": "Fiches qualitatives automatiques multi-sources",
                "utilisation": "Assembler une justification spécifique par entreprise: modèle d'affaires, moat, protections en crise, pouvoir de prix, gestion, secteur, risques et fit portefeuille.",
                "éléments consultés": f"Titres avec sources qualitatives ou fondamentales exploitables: {_compact_list(dossier_tickers)} / fiches retenues: reports/latest_company_dossiers.csv",
                "limite": "La fiche synthétise des indices gratuits et locaux; si une source manque, elle signale la limite plutôt que de conclure avec certitude.",
            }
        )
    rows.extend(
        [
            {
                "source": "Configuration locale de l’agent",
                "utilisation": "Règles de scoring, benchmarks, secteurs, expositions, alias de tickers et paramètres du scanner.",
                "éléments consultés": "config/positions.yaml, benchmarks.yaml, sectors.yaml, exposures.yaml, rules.yaml, ticker_aliases.yaml, market_scanner.yaml",
                "limite": "Ces règles sont mécaniques et ne remplacent pas une analyse professionnelle.",
            },
            {
                "source": "Historique local",
                "utilisation": "Comparaison avec les analyses précédentes pour détecter détérioration, solidification ou développement.",
                "éléments consultés": "reports/history/*.json et reports/latest_analysis_snapshot.json",
                "limite": "La tendance dépend des analyses conservées localement; supprimer l’historique efface cette mémoire.",
            },
            {
                "source": "Calculs internes Python",
                "utilisation": "Scores, conviction, thèse, liquidation, risque portefeuille, stress tests, fiscalité approximative et allocation.",
                "éléments consultés": "Modules src/*.py du projet local.",
                "limite": "Le système applique des règles; il ne prédit pas l’avenir.",
            },
        ]
    )
    return rows


def compact_company_dossier_rows_for_report(rows: list[dict[str, Any]], limit: int = 12) -> list[dict[str, Any]]:
    output = []
    status_order = {"RECOMMANDÉ": 0, "VENTE_A_VALIDER": 1, "ÉLIGIBLE_NON_RETENU": 2}
    quality_order = {
        "FULL_SOURCE_BACKED": 0,
        "PARTIAL_SOURCE_BACKED": 1,
        "BASIC_AUTOMATED": 2,
        "LIMITED_SOURCE": 3,
        "ETF_CLASSIFICATION": 4,
    }
    for row in sorted(
        rows,
        key=lambda item: (
            status_order.get(str(item.get("target_status") or ""), 9),
            quality_order.get(str(item.get("source_quality") or ""), 9),
            -(safe_float(item.get("allocation_amount")) or 0.0),
            str(item.get("ticker") or ""),
        ),
    )[:limit]:
        output.append(
            {
                "ticker": row.get("ticker_display") or row.get("ticker"),
                "statut": row.get("target_status"),
                "niveau_sources": row.get("source_quality"),
                "lecture": _compact_sentence(row.get("dossier_text"), 360),
                "sources_manquantes": _compact_sentence(row.get("missing_sources"), 180),
            }
        )
    return output


def opportunity_cost_rows(
    analyses: dict[str, dict[str, Any]],
    watchlist_analyses: dict[str, dict[str, Any]],
    market_analyses: dict[str, dict[str, Any]],
    discovery_analyses: dict[str, dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    discovery_analyses = discovery_analyses or {}
    rows = []
    for universe, group in [
        ("CORE_PORTFOLIO", analyses),
        ("WATCHLIST", watchlist_analyses),
        ("MARKET_UNIVERSE", market_analyses),
        ("DISCOVERY_IDEAS", discovery_analyses),
    ]:
        for row in sorted(group.values(), key=lambda item: item.get("ticker", "")):
            rows.append(
                {
                    "universe": universe,
                    "ticker": row.get("ticker_display", row.get("ticker")),
                    "opportunity_cost_status": row.get("opportunity_cost_status"),
                    "gross_yield": row.get("gross_yield"),
                    "after_tax_yield_adjusted": row.get("after_tax_yield_adjusted"),
                    "vfv_after_tax_yield_adjusted": row.get("vfv_after_tax_yield_adjusted"),
                    "after_tax_yield_spread_vs_vfv": row.get("after_tax_yield_spread_vs_vfv"),
                    "score_total": row.get("score_total"),
                    "conviction_score": row.get("conviction_score"),
                    "allocation_decision": row.get(
                        "allocation_decision",
                        row.get("watchlist_status", row.get("candidate_status", row.get("discovery_status", ""))),
                    ),
                    "sell_decision": row.get("sell_decision", ""),
                    "final_position_action": row.get("final_position_action", row.get("decision", "")),
                }
            )
    return rows


def _score_row_for_csv(row: dict[str, Any]) -> dict[str, Any]:
    issues = row.get("ticker_issue_reasons") or []
    if isinstance(issues, list):
        issues = "; ".join(str(issue) for issue in issues)
    return {
        "ticker": row.get("ticker"),
        "ticker_display": row.get("ticker_display", row.get("ticker")),
        "input_tickers": row.get("input_tickers"),
        "resolved_ticker": row.get("resolved_ticker", row.get("ticker")),
        "company_name_found": row.get("company_name_found"),
        "business_summary": row.get("business_summary"),
        "website": row.get("website"),
        "company_city": row.get("company_city"),
        "company_state": row.get("company_state"),
        "full_time_employees": row.get("full_time_employees"),
        "ticker_validation_status": row.get("ticker_validation_status"),
        "ticker_coverage_status": row.get("ticker_coverage_status"),
        "free_data_coverage_class": row.get("free_data_coverage_class"),
        "free_data_coverage_score": row.get("free_data_coverage_score"),
        "suggested_yahoo_tickers": row.get("suggested_yahoo_tickers"),
        "ticker_issues": issues,
        "score_total": row.get("score_total"),
        "score_with_estimates": row.get("score_with_estimates"),
        "score_confirmed_only": row.get("score_confirmed_only"),
        "score_estimate_gap": row.get("score_estimate_gap"),
        "score_data_gap_haircut": row.get("score_data_gap_haircut", 0.0),
        "score_data_gap_flag": row.get("score_data_gap_flag", False),
        "score_data_gap_label": row.get("score_data_gap_label", "COMPLET"),
        "score_confidence_range": row.get("score_confidence_range"),
        "score_confidence_low": row.get("score_confidence_low"),
        "score_confidence_high": row.get("score_confidence_high"),
        "score_confidence_label": row.get("score_confidence_label"),
        "score_confidence_reason": row.get("score_confidence_reason"),
        "score_estimated_points": row.get("score_estimated_points"),
        "score_evidence_level": row.get("score_evidence_level"),
        "score_evidence_penalty": row.get("score_evidence_penalty"),
        "score_evidence_reason": row.get("score_evidence_reason"),
        "conviction_score": row.get("conviction_score"),
        "conviction_score_raw": row.get("conviction_score_raw"),
        "conviction_confidence_range": row.get("conviction_confidence_range"),
        "conviction_confidence_low": row.get("conviction_confidence_low"),
        "conviction_confidence_high": row.get("conviction_confidence_high"),
        "conviction_confidence_label": row.get("conviction_confidence_label"),
        "conviction_confidence_reason": row.get("conviction_confidence_reason"),
        "business_quality_score": row.get("business_quality_score"),
        "high_cagr_potential_score": row.get("high_cagr_potential_score"),
        "shareholder_return_quality_score": row.get("shareholder_return_quality_score"),
        "shareholder_return_profile": row.get("shareholder_return_profile"),
        "shareholder_return_adjustment": row.get("shareholder_return_adjustment"),
        "shareholder_return_reason": row.get("shareholder_return_reason"),
        "cash_flow_quality_status": row.get("cash_flow_quality_status"),
        "cash_flow_quality_score": row.get("cash_flow_quality_score"),
        "cash_flow_quality_adjustment": row.get("cash_flow_quality_adjustment"),
        "cash_flow_quality_reason": row.get("cash_flow_quality_reason"),
        "operating_cash_flow": row.get("operating_cash_flow"),
        "capital_expenditures": row.get("capital_expenditures"),
        "free_cash_flow": row.get("free_cash_flow"),
        "free_cash_flow_margin": row.get("free_cash_flow_margin"),
        "free_cash_flow_growth": row.get("free_cash_flow_growth"),
        "fcf_conversion": row.get("fcf_conversion"),
        "net_debt_to_fcf": row.get("net_debt_to_fcf"),
        "cash_flow_metrics_available_count": row.get("cash_flow_metrics_available_count"),
        "shareholder_discipline_status": row.get("shareholder_discipline_status"),
        "shareholder_discipline_score": row.get("shareholder_discipline_score"),
        "shareholder_discipline_adjustment": row.get("shareholder_discipline_adjustment"),
        "shareholder_discipline_reason": row.get("shareholder_discipline_reason"),
        "shareholder_discipline_primary_dilution_rate": row.get("shareholder_discipline_primary_dilution_rate"),
        "shares_outstanding": row.get("shares_outstanding"),
        "diluted_average_shares": row.get("diluted_average_shares"),
        "share_count_growth_1y": row.get("share_count_growth_1y"),
        "share_count_cagr_3y": row.get("share_count_cagr_3y"),
        "share_count_cagr_5y": row.get("share_count_cagr_5y"),
        "share_repurchases": row.get("share_repurchases"),
        "buyback_yield": row.get("buyback_yield"),
        "stock_based_compensation": row.get("stock_based_compensation"),
        "sbc_to_revenue": row.get("sbc_to_revenue"),
        "fcf_per_share": row.get("fcf_per_share"),
        "fcf_per_share_growth": row.get("fcf_per_share_growth"),
        "dividend_yield": row.get("dividend_yield"),
        "after_tax_yield_adjusted": row.get("after_tax_yield_adjusted"),
        "tax_adjustment_factor": row.get("tax_adjustment_factor"),
        "tax_adjustment_note": row.get("tax_adjustment_note"),
        "payout_ratio": row.get("payout_ratio"),
        "long_term_durability_score": row.get("long_term_durability_score"),
        "long_term_durability_status": row.get("long_term_durability_status"),
        "long_term_durability_reason": row.get("long_term_durability_reason"),
        "market_growth_thesis_score": row.get("market_growth_thesis_score"),
        "market_growth_thesis_status": row.get("market_growth_thesis_status"),
        "market_growth_thesis_adjustment": row.get("market_growth_thesis_adjustment"),
        "market_growth_thesis_confidence": row.get("market_growth_thesis_confidence"),
        "market_growth_thesis_themes": _list_text(row.get("market_growth_thesis_themes") or []),
        "market_growth_thesis_sources": _list_text(row.get("market_growth_thesis_sources") or []),
        "market_growth_thesis_reason": row.get("market_growth_thesis_reason"),
        "capital_allocation_score": row.get("capital_allocation_score"),
        "capital_allocation_confidence_range": row.get("capital_allocation_confidence_range"),
        "capital_allocation_score_low": row.get("capital_allocation_score_low"),
        "capital_allocation_score_high": row.get("capital_allocation_score_high"),
        "capital_allocation_confidence_label": row.get("capital_allocation_confidence_label"),
        "capital_allocation_confidence_reason": row.get("capital_allocation_confidence_reason"),
        "reliability_cap_status": row.get("reliability_cap_status"),
        "reliability_cap_applied": row.get("reliability_cap_applied"),
        "reliability_allocation_cap_percent": row.get("reliability_allocation_cap_percent"),
        "reliability_allocation_cap_amount": row.get("reliability_allocation_cap_amount"),
        "reliability_cap_reason": row.get("reliability_cap_reason"),
        "double_counting_risk_level": row.get("double_counting_risk_level"),
        "double_counting_overlap_score": row.get("double_counting_overlap_score"),
        "double_counting_adjustment": row.get("double_counting_adjustment"),
        "double_counting_clusters": row.get("double_counting_clusters"),
        "double_counting_reason": row.get("double_counting_reason"),
        "hidden_cluster_risk_level": row.get("hidden_cluster_risk_level"),
        "hidden_cluster_exposure": row.get("hidden_cluster_exposure"),
        "hidden_cluster_clusters": row.get("hidden_cluster_clusters"),
        "hidden_cluster_adjustment": row.get("hidden_cluster_adjustment"),
        "hidden_cluster_reason": row.get("hidden_cluster_reason"),
        "hidden_cluster_guardrail": row.get("hidden_cluster_guardrail"),
        "hidden_cluster_exception_applied": row.get("hidden_cluster_exception_applied"),
        "business_profile": row.get("business_profile"),
        "business_profile_label": row.get("business_profile_label"),
        "benchmark_ticker": row.get("benchmark_ticker"),
        "benchmark_source": row.get("benchmark_source"),
        "benchmark_relevance_level": row.get("benchmark_relevance_level"),
        "benchmark_relevance_score": row.get("benchmark_relevance_score"),
        "benchmark_relevance_reason": row.get("benchmark_relevance_reason"),
        "expected_cagr_quality": row.get("expected_cagr_quality"),
        "opportunity_cost_status": row.get("opportunity_cost_status"),
        "thesis_status": row.get("thesis_status"),
        "fundamental_thesis_status": row.get("fundamental_thesis_status"),
        "market_watch_status": row.get("market_watch_status"),
        "valuation_watch_status": row.get("valuation_watch_status"),
        "liquidation_status": row.get("liquidation_status"),
        "sell_status": row.get("sell_status", row.get("liquidation_status")),
        "fundamental_sell_status": row.get("fundamental_sell_status", row.get("liquidation_status")),
        "monitoring_status": row.get("monitoring_status", "NORMAL"),
        "monitoring_decision": row.get("monitoring_decision", "NONE"),
        "monitoring_reasons": _list_text(row.get("monitoring_reasons") or []),
        "add_eligibility_status": row.get("add_eligibility_status"),
        "add_eligibility_size": row.get("add_eligibility_size"),
        "add_eligibility_reason": row.get("add_eligibility_reason"),
        "winner_accelerated": row.get("winner_accelerated"),
        "quality_but_too_expensive": row.get("quality_but_too_expensive"),
        "valuation_severity": row.get("valuation_severity"),
        "valuation_severity_reason": row.get("valuation_severity_reason"),
        "quality_expensive_reasons": _list_text(row.get("quality_expensive_reasons") or []),
        "quality_drawdown_status": row.get("quality_drawdown_status"),
        "quality_drawdown_score": row.get("quality_drawdown_score"),
        "quality_drawdown_allocation_adjustment": row.get("quality_drawdown_allocation_adjustment"),
        "quality_drawdown_reason": row.get("quality_drawdown_reason"),
        "news_context_triggered": row.get("news_context_triggered"),
        "news_context_status": row.get("news_context_status"),
        "news_context_reason": row.get("news_context_reason"),
        "news_context_sources": _list_text(row.get("news_context_sources") or []),
        "news_context_headlines": _list_text(row.get("news_context_headlines") or []),
        "news_context_source_channels": _list_text(row.get("news_context_source_channels") or []),
        "news_context_search_queries": _list_text(row.get("news_context_search_queries") or []),
        "news_context_checked_at": row.get("news_context_checked_at"),
        "cycle_risk_profile": row.get("cycle_risk_profile"),
        "cycle_bubble_risk_level": row.get("cycle_bubble_risk_level"),
        "cycle_bubble_score": row.get("cycle_bubble_score"),
        "cycle_bubble_penalty": row.get("cycle_bubble_penalty"),
        "cycle_bubble_allocation_multiplier": row.get("cycle_bubble_allocation_multiplier"),
        "cycle_normalized_status": row.get("cycle_normalized_status"),
        "cycle_normalized_growth_cap": row.get("cycle_normalized_growth_cap"),
        "cycle_adjusted_growth_estimate": row.get("cycle_adjusted_growth_estimate"),
        "cycle_normalized_earnings_risk_score": row.get("cycle_normalized_earnings_risk_score"),
        "allocation_stability_status": row.get("allocation_stability_status"),
        "allocation_stability_adjustment": row.get("allocation_stability_adjustment"),
        "allocation_stability_reason": row.get("allocation_stability_reason"),
        "previous_capital_allocation_score": row.get("previous_capital_allocation_score"),
        "capital_allocation_score_change": row.get("capital_allocation_score_change"),
        "portfolio_valuation_source": row.get("portfolio_valuation_source"),
        "portfolio_valuation_warning": row.get("portfolio_valuation_warning"),
        "current_price_cad": row.get("current_price_cad"),
        "current_value": row.get("current_value"),
        "current_value_cad": row.get("current_value_cad"),
        "quote_currency": row.get("quote_currency"),
        "quote_to_cad_rate": row.get("quote_to_cad_rate"),
        "average_cost_cad": row.get("average_cost_cad"),
        "acquisition_value_cad": row.get("acquisition_value_cad"),
        "average_cost_currency": row.get("average_cost_currency"),
        "acquisition_value_currency": row.get("acquisition_value_currency"),
        "current_value_currency": row.get("current_value_currency"),
        "shares": row.get("shares"),
        "average_cost": row.get("average_cost"),
        "average_cost_currency": row.get("average_cost_currency"),
        "acquisition_value": row.get("acquisition_value"),
        "acquisition_value_currency": row.get("acquisition_value_currency"),
        "unrealized_gain_amount": row.get("unrealized_gain_amount"),
        "unrealized_gain_percent": row.get("unrealized_gain_percent"),
        "personal_high_price": row.get("personal_high_price"),
        "drawdown_from_personal_high": row.get("drawdown_from_personal_high"),
        "winner_protection_status": row.get("winner_protection_status"),
        "winner_protection_action": row.get("winner_protection_action"),
        "winner_protection_reason": row.get("winner_protection_reason"),
        "drawdown_12m": row.get("drawdown_from_12m_high"),
        "position_weight": row.get("position_weight"),
        "data_quality": row.get("data_quality"),
        "data_reliability_score": row.get("data_reliability_score"),
        "data_reliability_level": row.get("data_reliability_level"),
        "auto_estimate_dependency": row.get("auto_estimate_dependency"),
        "automation_evidence_level": row.get("automation_evidence_level"),
        "data_fill_rate": row.get("data_fill_rate"),
        "overall_data_freshness_level": row.get("overall_data_freshness_level"),
        "data_freshness_action": row.get("data_freshness_action"),
        "market_data_freshness_level": row.get("market_data_freshness_level"),
        "market_data_source": row.get("market_data_source", row.get("source")),
        "market_data_fetched_at": row.get("market_data_fetched_at", row.get("fetched_at")),
        "market_data_age_hours": row.get("market_data_age_hours"),
        "market_data_requires_refresh": row.get("market_data_requires_refresh"),
        "market_data_freshness_reason": row.get("market_data_freshness_reason"),
        "market_data_stale_cache_warning": row.get("market_data_stale_cache_warning"),
        "market_data_fetch_status": row.get("market_data_fetch_status"),
        "market_data_fallback_level": row.get("market_data_fallback_level"),
        "market_data_warning_flags": _list_text(row.get("market_data_warning_flags") or []),
        "market_data_fetch_attempts": row.get("market_data_fetch_attempts"),
        "market_data_fetch_attempted_at": row.get("market_data_fetch_attempted_at"),
        "market_data_circuit_breaker_open": row.get("market_data_circuit_breaker_open"),
        "market_data_last_error": row.get("market_data_last_error"),
        "last_known_good_at": row.get("last_known_good_at"),
        "data_source_notes": _list_text(row.get("data_source_notes") or []),
        "proxy_correction_status": row.get("proxy_correction_status"),
        "proxy_correction_fields": _list_text(row.get("proxy_correction_fields") or []),
        "proxy_corrections_applied": _proxy_corrections_text(row.get("proxy_corrections_applied") or []),
        "manual_override_fields": _list_text(row.get("manual_override_fields") or []),
        "auto_estimated_fields": _list_text(row.get("auto_estimated_fields") or []),
        "field_provenance": _mapping_text(row.get("field_provenance") or {}),
        "field_evidence_sources": _mapping_text(row.get("field_evidence_sources") or {}),
        "research_report_current_fields": _list_text(row.get("research_report_current_fields") or []),
        "research_report_stale_fields": _list_text(row.get("research_report_stale_fields") or []),
        "research_report_unknown_date_fields": _list_text(row.get("research_report_unknown_date_fields") or []),
        "research_report_field_freshness": _mapping_text(row.get("research_report_field_freshness") or {}),
        "calibration_source": row.get("calibration_source"),
        "calibration_source_date": row.get("calibration_source_date"),
        "calibration_synced_fields": _list_text(row.get("calibration_synced_fields") or []),
        "calibration_current_fields": _list_text(row.get("calibration_current_fields") or []),
        "calibration_stale_fields": _list_text(row.get("calibration_stale_fields") or []),
        "calibration_unknown_date_fields": _list_text(row.get("calibration_unknown_date_fields") or []),
        "calibration_applied_fields": _list_text(row.get("calibration_applied_fields") or []),
        "calibration_ignored_fields": _list_text(row.get("calibration_ignored_fields") or []),
        "calibration_field_freshness": _mapping_text(row.get("calibration_field_freshness") or {}),
        "calibration_field_source_dates": _mapping_text(row.get("calibration_field_source_dates") or {}),
        "fundamental_evidence_conflict": row.get("fundamental_evidence_conflict"),
        "fundamental_evidence_conflict_fields": _list_text(row.get("fundamental_evidence_conflict_fields") or []),
        "fundamental_evidence_conflict_reason": row.get("fundamental_evidence_conflict_reason"),
        "fundamental_fallback_fields": _list_text(row.get("fundamental_fallback_fields") or []),
        "official_data_sources": _list_text(row.get("official_data_sources") or []),
        "official_fundamental_fields": _list_text(row.get("official_fundamental_fields") or []),
        "official_confirmed_fields": _list_text(row.get("official_confirmed_fields") or []),
        "official_supported_manual_fields": _list_text(row.get("official_supported_manual_fields") or []),
        "official_confirmed_manual_fields": _list_text(row.get("official_confirmed_manual_fields") or []),
        "official_evidence_level": row.get("official_evidence_level"),
        "official_data_conflict_count": row.get("official_data_conflict_count"),
        "official_technical_conflict_count": row.get("official_technical_conflict_count"),
        "official_material_conflict_count": row.get("official_material_conflict_count"),
        "official_directional_conflict_count": row.get("official_directional_conflict_count"),
        "official_weighted_conflict_score": row.get("official_weighted_conflict_score"),
        "official_conflict_profile": row.get("official_conflict_profile"),
        "official_data_conflicts": _list_text(row.get("official_data_conflicts") or []),
        "official_source_policy": _list_text(row.get("official_source_policy") or []),
        "canadian_data_sources": _list_text(row.get("canadian_data_sources") or []),
        "canadian_fundamental_fields": _list_text(row.get("canadian_fundamental_fields") or []),
        "canadian_confirmed_fields": _list_text(row.get("canadian_confirmed_fields") or []),
        "canadian_data_conflicts": _list_text(row.get("canadian_data_conflicts") or []),
        "canadian_source_policy": _list_text(row.get("canadian_source_policy") or []),
        "canadian_coverage_status": row.get("canadian_coverage_status"),
        "canadian_latest_period": row.get("canadian_latest_period"),
        "canadian_checked_at": row.get("canadian_checked_at"),
        "sec_edgar_cik": row.get("sec_edgar_cik"),
        "sec_edgar_company_name": row.get("sec_edgar_company_name"),
        "sec_edgar_latest_filing_date": row.get("sec_edgar_latest_filing_date"),
        "sec_edgar_latest_fiscal_year": row.get("sec_edgar_latest_fiscal_year"),
        "research_report_sources": _list_text(row.get("research_report_sources") or []),
        "research_report_fields": _list_text(row.get("research_report_fields") or []),
        "research_report_field_confidence": _mapping_text(row.get("research_report_field_confidence") or {}),
        "research_report_extraction_notes": _list_text(row.get("research_report_extraction_notes") or []),
        "research_report_extraction_warnings": _list_text(row.get("research_report_extraction_warnings") or []),
        "research_report_text_quality_status": row.get("research_report_text_quality_status"),
        "research_report_text_quality_score": row.get("research_report_text_quality_score"),
        "research_report_extraction_method": row.get("research_report_extraction_method"),
        "research_report_ocr_status": row.get("research_report_ocr_status"),
        "research_report_freshness_level": row.get("research_report_freshness_level"),
        "research_report_latest_date": row.get("research_report_latest_date"),
        "research_report_age_days": row.get("research_report_age_days"),
        "research_report_requires_fresh_validation": row.get("research_report_requires_fresh_validation"),
        "input_data_mode": row.get("input_data_mode"),
        "trend_status": row.get("trend_status"),
        "score_total_change": row.get("score_total_change"),
        "conviction_score_change": row.get("conviction_score_change"),
        "allocation_decision": row.get("allocation_decision"),
        "allocation_decision_reason": row.get("allocation_decision_reason"),
        "sell_decision": row.get("sell_decision"),
        "sell_decision_reason": row.get("sell_decision_reason"),
        "final_position_action": row.get("final_position_action"),
        "final_position_reason": row.get("final_position_reason"),
        "decision": row.get("decision"),
        "forward_eps_growth_confidence": row.get("forward_eps_growth_confidence"),
        "data_source_forward": row.get("data_source_forward"),
        "eps_growth_5y_proxy_sanity": row.get("eps_growth_5y_proxy_sanity"),
        "data_confidence_badge": row.get("data_confidence_badge"),
        "canadian_tax_advantage_active": row.get("canadian_tax_advantage_active"),
    }


def _core_summary_row(row: dict[str, Any]) -> dict[str, Any]:
    if row.get("benchmark_role") is True:
        return {
            "ticker": row.get("ticker_display", row.get("ticker")),
            "score_total": "BENCHMARK",
            "score_with_estimates": "BENCHMARK",
            "score_confirmed_only": "BENCHMARK",
            "score_estimate_gap": "BENCHMARK",
            "score_confidence_range": "BENCHMARK",
            "score_confidence_label": "BENCHMARK",
            "score_evidence_level": "BENCHMARK",
            "conviction_score": "BENCHMARK",
            "conviction_confidence_range": "BENCHMARK",
            "conviction_confidence_label": "BENCHMARK",
            "business_quality_score": "BENCHMARK",
            "high_cagr_potential_score": "BENCHMARK",
            "shareholder_return_quality_score": "BENCHMARK",
            "shareholder_return_profile": "BENCHMARK",
            "shareholder_return_adjustment": "BENCHMARK",
            "shareholder_return_reason": "VFV.TO est un benchmark, pas une entreprise à dividende à scorer.",
            "cash_flow_quality_status": "BENCHMARK",
            "cash_flow_quality_score": "BENCHMARK",
            "cash_flow_quality_adjustment": "BENCHMARK",
            "cash_flow_quality_reason": "VFV.TO est un benchmark, pas une entreprise à analyser par free cash flow.",
            "shareholder_discipline_status": "BENCHMARK",
            "shareholder_discipline_score": "BENCHMARK",
            "shareholder_discipline_adjustment": "BENCHMARK",
            "shareholder_discipline_reason": "VFV.TO est un benchmark, pas une entreprise à analyser par dilution.",
            "long_term_durability_score": "BENCHMARK",
            "long_term_durability_status": "BENCHMARK",
            "capital_allocation_score": "BENCHMARK",
            "capital_allocation_confidence_range": "BENCHMARK",
            "capital_allocation_confidence_label": "BENCHMARK",
            "business_profile": "BENCHMARK",
            "cycle_bubble_risk_level": "BENCHMARK",
            "cycle_bubble_score": "BENCHMARK",
            "cycle_bubble_penalty": "BENCHMARK",
            "double_counting_risk_level": "BENCHMARK",
            "double_counting_adjustment": "BENCHMARK",
            "hidden_cluster_risk_level": "BENCHMARK",
            "hidden_cluster_adjustment": "BENCHMARK",
            "allocation_stability_status": "BENCHMARK",
            "allocation_stability_adjustment": "BENCHMARK",
            "winner_protection_status": "BENCHMARK",
            "winner_protection_action": "BENCHMARK",
            "benchmark_ticker": row.get("benchmark_ticker"),
            "benchmark_source": "BENCHMARK",
            "benchmark_relevance_level": "BENCHMARK",
            "benchmark_relevance_score": "BENCHMARK",
            "benchmark_relevance_reason": "VFV.TO est lui-même le benchmark.",
            "expected_cagr_quality": "BENCHMARK",
            "opportunity_cost_status": "BENCHMARK_FALLBACK",
            "thesis_status": "BENCHMARK",
            "fundamental_thesis_status": "BENCHMARK",
            "market_watch_status": "BENCHMARK",
            "valuation_watch_status": "BENCHMARK",
            "liquidation_status": "BENCHMARK",
            "monitoring_status": "BENCHMARK",
            "add_eligibility_status": "BENCHMARK_FALLBACK",
            "add_eligibility_size": "FALLBACK",
            "data_quality": "BENCHMARK",
            "data_reliability_level": "BENCHMARK",
            "auto_estimate_dependency": "BENCHMARK",
            "automation_evidence_level": "BENCHMARK",
            "trend_status": row.get("trend_status"),
            "allocation_decision": row.get("allocation_decision"),
            "sell_decision": row.get("sell_decision"),
            "final_position_action": row.get("final_position_action"),
            "decision": row.get("decision"),
        }
    if is_etf_asset_analysis(row):
        return {
            "ticker": row.get("ticker_display", row.get("ticker")),
            "score_total": "ETF",
            "score_with_estimates": "ETF",
            "score_confirmed_only": "ETF",
            "score_estimate_gap": "ETF",
            "score_confidence_range": "ETF",
            "score_confidence_label": "ETF",
            "score_evidence_level": "ETF",
            "conviction_score": "ETF",
            "conviction_confidence_range": "ETF",
            "conviction_confidence_label": "ETF",
            "business_quality_score": "ETF",
            "high_cagr_potential_score": "ETF",
            "shareholder_return_quality_score": "ETF",
            "shareholder_return_profile": "ETF",
            "shareholder_return_adjustment": "ETF",
            "shareholder_return_reason": "ETF: rendement total traité par l’indice/fonds, pas par une politique de dividende d’entreprise.",
            "cash_flow_quality_status": "ETF",
            "cash_flow_quality_score": "ETF",
            "cash_flow_quality_adjustment": "ETF",
            "cash_flow_quality_reason": "FNB/ETF: pas de free cash flow d’entreprise à scorer.",
            "shareholder_discipline_status": "ETF",
            "shareholder_discipline_score": "ETF",
            "shareholder_discipline_adjustment": "ETF",
            "shareholder_discipline_reason": "FNB/ETF: pas de dilution d’entreprise individuelle à scorer.",
            "long_term_durability_score": "ETF",
            "long_term_durability_status": row.get("long_term_durability_status", "ETF_DIVERSIFIED"),
            "capital_allocation_score": "ETF",
            "capital_allocation_confidence_range": "ETF",
            "capital_allocation_confidence_label": "ETF",
            "business_profile": "ETF",
            "cycle_bubble_risk_level": "ETF",
            "cycle_bubble_score": "ETF",
            "cycle_bubble_penalty": "ETF",
            "double_counting_risk_level": "ETF",
            "double_counting_adjustment": "ETF",
            "hidden_cluster_risk_level": "ETF",
            "hidden_cluster_adjustment": "ETF",
            "allocation_stability_status": "ETF",
            "allocation_stability_adjustment": "ETF",
            "winner_protection_status": "ETF",
            "winner_protection_action": "ETF",
            "benchmark_ticker": row.get("benchmark_ticker"),
            "benchmark_source": row.get("benchmark_source"),
            "benchmark_relevance_level": row.get("benchmark_relevance_level"),
            "benchmark_relevance_score": row.get("benchmark_relevance_score"),
            "benchmark_relevance_reason": row.get("benchmark_relevance_reason"),
            "expected_cagr_quality": row.get("expected_cagr_quality", "ETF_DIVERSIFIED"),
            "opportunity_cost_status": row.get("opportunity_cost_status", "ETF_COMPARE_TO_VFV"),
            "thesis_status": "ETF",
            "fundamental_thesis_status": "ETF",
            "market_watch_status": "ETF",
            "valuation_watch_status": "ETF",
            "liquidation_status": row.get("liquidation_status", "GREEN"),
            "monitoring_status": row.get("monitoring_status", "NORMAL"),
            "add_eligibility_status": row.get("add_eligibility_status", "ETF_HOLD_ONLY"),
            "add_eligibility_size": row.get("add_eligibility_size", "NONE"),
            "data_quality": "ETF",
            "data_reliability_level": "ETF",
            "auto_estimate_dependency": "ETF",
            "automation_evidence_level": "ETF",
            "trend_status": row.get("trend_status"),
            "allocation_decision": row.get("allocation_decision"),
            "sell_decision": row.get("sell_decision"),
            "final_position_action": row.get("final_position_action"),
            "decision": row.get("decision"),
        }
    return {
        "ticker": row.get("ticker_display", row.get("ticker")),
        "score_total": row.get("score_total"),
        "score_with_estimates": row.get("score_with_estimates"),
        "score_confirmed_only": row.get("score_confirmed_only"),
        "score_estimate_gap": row.get("score_estimate_gap"),
        "score_confidence_range": row.get("score_confidence_range"),
        "score_confidence_label": row.get("score_confidence_label"),
        "score_evidence_level": row.get("score_evidence_level"),
        "conviction_score": row.get("conviction_score"),
        "conviction_confidence_range": row.get("conviction_confidence_range"),
        "conviction_confidence_label": row.get("conviction_confidence_label"),
        "business_quality_score": row.get("business_quality_score"),
        "high_cagr_potential_score": row.get("high_cagr_potential_score"),
        "shareholder_return_quality_score": row.get("shareholder_return_quality_score"),
        "shareholder_return_profile": row.get("shareholder_return_profile"),
        "shareholder_return_adjustment": row.get("shareholder_return_adjustment"),
        "shareholder_return_reason": row.get("shareholder_return_reason"),
        "cash_flow_quality_status": row.get("cash_flow_quality_status"),
        "cash_flow_quality_score": row.get("cash_flow_quality_score"),
        "cash_flow_quality_adjustment": row.get("cash_flow_quality_adjustment"),
        "cash_flow_quality_reason": row.get("cash_flow_quality_reason"),
        "shareholder_discipline_status": row.get("shareholder_discipline_status"),
        "shareholder_discipline_score": row.get("shareholder_discipline_score"),
        "shareholder_discipline_adjustment": row.get("shareholder_discipline_adjustment"),
        "shareholder_discipline_reason": row.get("shareholder_discipline_reason"),
        "long_term_durability_score": row.get("long_term_durability_score"),
        "long_term_durability_status": row.get("long_term_durability_status"),
        "capital_allocation_score": row.get("capital_allocation_score"),
        "capital_allocation_confidence_range": row.get("capital_allocation_confidence_range"),
        "capital_allocation_confidence_label": row.get("capital_allocation_confidence_label"),
        "business_profile": row.get("business_profile"),
        "cycle_bubble_risk_level": row.get("cycle_bubble_risk_level"),
        "cycle_bubble_score": row.get("cycle_bubble_score"),
        "cycle_bubble_penalty": row.get("cycle_bubble_penalty"),
        "double_counting_risk_level": row.get("double_counting_risk_level"),
        "double_counting_adjustment": row.get("double_counting_adjustment"),
        "hidden_cluster_risk_level": row.get("hidden_cluster_risk_level"),
        "hidden_cluster_adjustment": row.get("hidden_cluster_adjustment"),
        "allocation_stability_status": row.get("allocation_stability_status"),
        "allocation_stability_adjustment": row.get("allocation_stability_adjustment"),
        "winner_protection_status": row.get("winner_protection_status"),
        "winner_protection_action": row.get("winner_protection_action"),
        "benchmark_ticker": row.get("benchmark_ticker"),
        "benchmark_source": row.get("benchmark_source"),
        "benchmark_relevance_level": row.get("benchmark_relevance_level"),
        "benchmark_relevance_score": row.get("benchmark_relevance_score"),
        "benchmark_relevance_reason": row.get("benchmark_relevance_reason"),
        "expected_cagr_quality": row.get("expected_cagr_quality"),
        "opportunity_cost_status": row.get("opportunity_cost_status"),
        "thesis_status": row.get("thesis_status"),
        "fundamental_thesis_status": row.get("fundamental_thesis_status"),
        "market_watch_status": row.get("market_watch_status"),
        "valuation_watch_status": row.get("valuation_watch_status"),
        "liquidation_status": row.get("liquidation_status"),
        "monitoring_status": row.get("monitoring_status", "NORMAL"),
        "add_eligibility_status": row.get("add_eligibility_status"),
        "add_eligibility_size": row.get("add_eligibility_size"),
        "data_quality": row.get("data_quality"),
        "data_reliability_level": row.get("data_reliability_level"),
        "auto_estimate_dependency": row.get("auto_estimate_dependency"),
        "automation_evidence_level": row.get("automation_evidence_level"),
        "trend_status": row.get("trend_status"),
        "allocation_decision": row.get("allocation_decision"),
        "sell_decision": row.get("sell_decision"),
        "final_position_action": row.get("final_position_action"),
        "decision": row.get("decision"),
    }


def _position_section(row: dict[str, Any]) -> list[str]:
    if row.get("benchmark_role") is True:
        return [
            f"### {row.get('ticker_display', row.get('ticker'))}",
            "",
            "- Type d’actif: ETF S&P 500 coté au Canada, pas une compagnie.",
            "- Rôle: benchmark, coût d’opportunité et destination de secours.",
            "- VFV.TO n’est pas scoré comme une action individuelle: pas de ROIC, moat, EPS, conviction d’entreprise ou liquidation automatique.",
            f"- Décision allocation: {row.get('allocation_decision')}",
            f"- Décision vente/surveillance: {row.get('sell_decision')}",
            f"- Action finale: {row.get('final_position_action')}",
            f"- Justification finale: {row.get('final_position_reason')}",
            "",
        ]
    if is_etf_asset_analysis(row):
        return [
            f"### {row.get('ticker_display', row.get('ticker'))}",
            "",
            f"- Type d’actif: FNB/ETF ({row.get('asset_focus') or 'indice ou panier diversifié'}), pas une compagnie.",
            "- Rôle: exposition indicielle à surveiller par diversification, concentration, devise, frais et rendement de l’indice.",
            "- Le titre n’est pas scoré avec ROIC, moat, EPS ou juste valeur comme une entreprise individuelle.",
            f"- Décision allocation: {row.get('allocation_decision')}",
            f"- Décision vente/surveillance: {row.get('sell_decision')}",
            f"- Action finale: {row.get('final_position_action')}",
            f"- Justification finale: {row.get('final_position_reason')}",
            "",
        ]
    criteria_rows = []
    for code, criterion in row.get("criteria", {}).items():
        criteria_rows.append(
            {
                "critère": code,
                "description": criterion.get("label"),
                "points": criterion.get("points") if criterion.get("points") is not None else "MANUAL_REQUIRED",
                "détail": criterion.get("detail"),
            }
        )
    missing = row.get("manual_required_criteria") or []
    auto_fields = row.get("auto_estimated_fields") or []
    manual_fields = row.get("manual_override_fields") or []
    source_notes = row.get("data_source_notes") or []
    fallback_fields = row.get("fundamental_fallback_fields") or []
    research_sources = row.get("research_report_sources") or []
    research_fields = row.get("research_report_fields") or []
    reliability_reasons = row.get("data_reliability_reasons") or []
    if isinstance(reliability_reasons, list):
        reliability_text = ", ".join(str(item) for item in reliability_reasons) if reliability_reasons else "Aucune"
    else:
        reliability_text = str(reliability_reasons)
    trend_reasons = row.get("trend_reasons") or []
    if isinstance(trend_reasons, list):
        trend_reasons_text = ", ".join(str(item) for item in trend_reasons) if trend_reasons else "Aucune"
    else:
        trend_reasons_text = str(trend_reasons)
    market_watch_reasons = row.get("market_watch_reasons") or []
    valuation_watch_reasons = row.get("valuation_watch_reasons") or []
    return [
        f"### {row.get('ticker_display', row.get('ticker'))}",
        "",
        _markdown_table(["critère", "description", "points", "détail"], criteria_rows),
        "",
        (
            f"- Données utilisées: prix={_report_value(row.get('current_price'))}, "
            f"forward PE={_report_value(row.get('forward_pe'))}, "
            f"PEG={_report_value(row.get('peg'))}, "
            f"juste valeur={_report_value(row.get('fair_value'))}"
        ),
        f"- Sources gratuites utilisées: {_list_text(source_notes)}",
        f"- Champs complétés par fallback gratuit: {_list_text(fallback_fields)}",
        f"- Rapports BNCD/Morningstar utilisés: {_list_text(research_sources)}",
        f"- Champs complétés depuis rapports BNCD/Morningstar: {_list_text(research_fields)}",
        (
            f"- Fraîcheur rapports BNCD/Morningstar: {row.get('research_report_freshness_level') or 'NO_REPORT'} "
            f"/ date={row.get('research_report_latest_date') or 'N/D'} "
            f"/ âge={_report_value(row.get('research_report_age_days'))} jours "
            f"({row.get('research_report_freshness_reason') or 'Aucun rapport local utilisé.'})"
        ),
        (
            f"- Fraîcheur données de marché: {row.get('overall_data_freshness_level') or 'N/D'} "
            f"/ prix={row.get('market_data_freshness_level') or 'N/D'} "
            f"/ source={row.get('market_data_source') or row.get('source') or 'N/D'} "
            f"/ âge={_report_value(row.get('market_data_age_hours'))} heures "
            f"({row.get('data_freshness_action') or 'N/D'})"
        ),
        f"- Mode de données: {row.get('input_data_mode')} / qualité={row.get('data_quality')} / taux de données={_report_value(row.get('data_fill_rate'))}",
        (
            f"- Couverture ticker/données gratuites: {row.get('ticker_coverage_status') or 'N/D'} "
            f"/ classe={row.get('free_data_coverage_class') or 'N/D'} "
            f"/ validation={row.get('ticker_validation_status') or 'N/D'} "
            f"/ score couverture={_report_value(row.get('free_data_coverage_score'))}"
        ),
        (
            f"- Fiabilité des données: {row.get('data_reliability_level')} "
            f"({row.get('data_reliability_score')}) / dépendance aux estimations={row.get('auto_estimate_dependency')} "
            f"/ preuve automatique={row.get('automation_evidence_level')}"
        ),
        f"- Raison fiabilité: {reliability_text}",
        (
            f"- Preuve du score: complet={row.get('score_with_estimates') or row.get('score_total')} "
            f"/ confirmé seulement={row.get('score_confirmed_only') or 'N/D'} "
            f"/ écart estimé={row.get('score_estimate_gap') or 0} "
            f"/ fourchette={row.get('score_confidence_range') or 'N/D'} "
            f"({row.get('score_confidence_label') or 'N/D'}) "
            f"/ niveau={row.get('score_evidence_level') or 'N/D'} "
            f"({row.get('score_evidence_reason') or 'N/D'})"
        ),
        f"- Ticker demandé/résolu: {row.get('input_tickers') or row.get('ticker')} -> {row.get('resolved_ticker', row.get('ticker'))}",
        f"- Nom trouvé: {row.get('company_name_found') or 'N/D'}",
        f"- Vérification ticker: {_ticker_issue_text(row)}",
        f"- Champs estimés automatiquement: {', '.join(auto_fields) if auto_fields else 'Aucun'}",
        f"- Corrections manuelles utilisées: {', '.join(manual_fields) if manual_fields else 'Aucune'}",
        (
            f"- Calibration proxy: appliquée={_list_text(row.get('calibration_applied_fields') or [])}; "
            f"périmée={_list_text(row.get('calibration_stale_fields') or [])}; "
            f"date inconnue={_list_text(row.get('calibration_unknown_date_fields') or [])}; "
            f"source_date={row.get('calibration_source_date') or 'N/D'}"
        ),
        (
            f"- Conflit de preuves fondamentales: "
            f"{'OUI' if row.get('fundamental_evidence_conflict') else 'NON'} "
            f"({row.get('fundamental_evidence_conflict_reason') or 'Aucun conflit calibration/preuve actuelle.'})"
        ),
        f"- Données manquantes: {', '.join(missing) if missing else 'Aucune donnée critique majeure.'}",
        f"- Tendance historique: {row.get('trend_status')} ({trend_reasons_text})",
        (
            f"- Conviction_score: {row.get('conviction_score')} ({row.get('conviction_category')})"
            + (f" / fourchette={row.get('conviction_confidence_range')} ({row.get('conviction_confidence_label')})" if row.get("conviction_confidence_range") else "")
            + (f" / brut avant fiabilité={row.get('conviction_score_raw')}" if row.get("conviction_score_raw") else "")
        ),
        f"- Business_quality_score: {row.get('business_quality_score')}",
        f"- High_cagr_potential_score: {row.get('high_cagr_potential_score')}",
        (
            f"- Durabilité 15-30 ans: {row.get('long_term_durability_status') or 'N/D'} "
            f"({row.get('long_term_durability_score') or 'N/D'}) - "
            f"{row.get('long_term_durability_reason') or 'N/D'}"
        ),
        (
            f"- Thèse de croissance de marché: {row.get('market_growth_thesis_status') or 'N/D'} "
            f"({row.get('market_growth_thesis_score') or 'N/D'}) / ajustement sizing="
            f"{row.get('market_growth_thesis_adjustment') or 0} "
            f"({row.get('market_growth_thesis_reason') or 'N/D'})"
        ),
        (
            f"- Qualité du cash-flow: {row.get('cash_flow_quality_status') or 'N/D'} "
            f"({row.get('cash_flow_quality_score') or 'N/D'}) / ajustement sizing="
            f"{row.get('cash_flow_quality_adjustment') or 0} "
            f"({row.get('cash_flow_quality_reason') or 'N/D'})"
        ),
        (
            f"- Discipline actionnariale/dilution: {row.get('shareholder_discipline_status') or 'N/D'} "
            f"({row.get('shareholder_discipline_score') or 'N/D'}) / ajustement sizing="
            f"{row.get('shareholder_discipline_adjustment') or 0} "
            f"({row.get('shareholder_discipline_reason') or 'N/D'})"
        ),
        (
            f"- Capital_allocation_score: {row.get('capital_allocation_score')}"
            + (
                f" / fourchette={row.get('capital_allocation_confidence_range')} "
                f"({row.get('capital_allocation_confidence_label')})"
                if row.get("capital_allocation_confidence_range")
                else ""
            )
            + (
                f" / cap fiabilité={row.get('reliability_cap_status')} "
                f"({pct(row.get('reliability_allocation_cap_percent'), 0)})"
                if row.get("reliability_cap_status") not in {None, "", "NONE", "BENCHMARK", "ETF"}
                else ""
            )
        ),
        (
            f"- Double-counting des signaux: {row.get('double_counting_risk_level') or 'LOW'} "
            f"score={row.get('double_counting_overlap_score') or 0} "
            f"ajustement={row.get('double_counting_adjustment') or 0} "
            f"clusters={row.get('double_counting_clusters') or 'aucun'} "
            f"({row.get('double_counting_reason') or 'N/D'})"
        ),
        (
            f"- Cluster caché: {row.get('hidden_cluster_risk_level') or 'LOW'} "
            f"exposition={pct(row.get('hidden_cluster_exposure'), 1)} "
            f"ajustement={row.get('hidden_cluster_adjustment') or 0} "
            f"clusters={row.get('hidden_cluster_clusters') or 'aucun'} "
            f"({row.get('hidden_cluster_reason') or 'N/D'})"
        ),
        (
            f"- Stabilité mensuelle: {row.get('allocation_stability_status') or 'N/D'} "
            f"ajustement={row.get('allocation_stability_adjustment') or 0} "
            f"({row.get('allocation_stability_reason') or 'N/D'})"
        ),
        (
            f"- Protection des winners: {row.get('winner_protection_status') or 'N/D'} "
            f"/ action={row.get('winner_protection_action') or 'N/D'} "
            f"/ gain latent={pct(row.get('unrealized_gain_percent'), 1)} "
            f"/ drawdown sommet personnel={pct(row.get('drawdown_from_personal_high'), 1)} "
            f"({row.get('winner_protection_reason') or 'N/D'})"
        ),
        f"- Profil d’entreprise: {row.get('business_profile_label') or row.get('business_profile') or 'N/D'} ({row.get('business_profile_reason') or 'N/D'})",
        (
            f"- Risque cycle/bulle/tendance: {row.get('cycle_bubble_risk_level') or 'N/D'} "
            f"score={row.get('cycle_bubble_score') or 'N/D'} "
            f"pénalité={row.get('cycle_bubble_penalty') or 0} "
            f"multiplicateur allocation={row.get('cycle_bubble_allocation_multiplier') or 'N/D'} "
            f"({row.get('cycle_bubble_comment') or 'N/D'})"
        ),
        (
            f"- Normalisation cycle complet: {row.get('cycle_normalized_status') or 'N/D'} "
            f"cap croissance={row.get('cycle_normalized_growth_cap') or 'N/D'} "
            f"croissance ajustée={row.get('cycle_adjusted_growth_estimate') or 'N/D'} "
            f"risque profits normalisés={row.get('cycle_normalized_earnings_risk_score') or 0}"
        ),
        f"- Raisons cycle/bulle/tendance: {_list_text(row.get('cycle_bubble_reasons') or [])}",
        (
            f"- Benchmark utilisé: {row.get('benchmark_ticker') or 'N/D'} / source={row.get('benchmark_source') or 'N/D'} "
            f"/ pertinence={row.get('benchmark_relevance_level') or 'N/D'} "
            f"({row.get('benchmark_relevance_reason') or 'N/D'})"
        ),
        f"- Expected_cagr_quality: {row.get('expected_cagr_quality')}",
        f"- Opportunity_cost_status vs VFV: {row.get('opportunity_cost_status')}",
        f"- Thesis_status: {row.get('thesis_status')}",
        f"- Fundamental_thesis_status: {row.get('fundamental_thesis_status')}",
        f"- Market_watch_status: {row.get('market_watch_status')} ({_list_text(market_watch_reasons)})",
        f"- Valuation_watch_status: {row.get('valuation_watch_status')} ({_list_text(valuation_watch_reasons)})",
        f"- Statut de vente fondamentale: {row.get('sell_status', row.get('liquidation_status'))}",
        (
            f"- Statut de surveillance: {row.get('monitoring_status') or 'NORMAL'} "
            f"({row.get('monitoring_decision') or 'NONE'}; {_list_text(row.get('monitoring_reasons') or [])})"
        ),
        f"- Add_eligibility_status: {row.get('add_eligibility_status')} ({row.get('add_eligibility_size')})",
        f"- Add_eligibility_reason: {row.get('add_eligibility_reason')}",
        f"- Signaux de vente détectés: {_signals(row)}",
        f"- Décision allocation: {row.get('allocation_decision')} ({row.get('allocation_decision_reason')})",
        f"- Décision vente: {row.get('sell_decision')} ({row.get('sell_decision_reason')})",
        f"- Action finale: {row.get('final_position_action')}",
        f"- Justification finale: {row.get('final_position_reason')}",
        "",
    ]


def _markdown_table(headers: list[str], rows: list[dict[str, Any]]) -> str:
    if not rows:
        rows = [{header: "" for header in headers}]
    header_line = "| " + " | ".join(headers) + " |"
    separator = "| " + " | ".join(["---"] * len(headers)) + " |"
    body = []
    for row in rows:
        body.append("| " + " | ".join(_escape(row.get(header, "")) for header in headers) + " |")
    return "\n".join([header_line, separator, *body])


def _details_block(summary: str, lines: list[str], *, open_by_default: bool = False) -> list[str]:
    open_attr = " open" if open_by_default else ""
    return [
        f"<details markdown=\"1\"{open_attr}>",
        f"<summary>{summary}</summary>",
        "",
        *lines,
        "",
        "</details>",
        "",
    ]


def _dict_table(key_header: str, value_header: str, values: dict[str, float]) -> str:
    rows = [{key_header: key, value_header: pct(value, 1)} for key, value in values.items()]
    return _markdown_table([key_header, value_header], rows)


def _winner_protection_label(row: dict[str, Any]) -> str:
    status = str(row.get("winner_protection_status") or "").strip()
    action = str(row.get("winner_protection_action") or "").strip()
    if not status or status == "Donnée pas dispo":
        return "N/D"
    if action and action not in {"NONE", "HOLD"}:
        return f"{status} / {action}"
    return status


def _guardrail_ticker_text(tickers: list[str], label: str) -> str:
    clean = [ticker for ticker in tickers if ticker]
    if not clean:
        return "Aucun signal important affiché."
    return f"{label}: {_compact_list(clean, limit=6)}"


def _validation_point_text(row: dict[str, Any]) -> str:
    for field in [
        "news_or_research_check",
        "data_quality_check",
        "tax_check",
        "technical_or_valuation_context",
        "winner_protection_check",
    ]:
        text = str(row.get(field) or "").strip()
        if text and text not in {
            "Aucune alerte fiscale majeure détectée.",
            "Aucun signal technique/valorisation majeur.",
            "Aucune vente winner active.",
        }:
            return text
    return "Aucune preuve additionnelle urgente."


def _allocation_summary(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "Aucune cotisation à allouer."
    return ", ".join(f"{row['ticker']} {money(row['amount'])}" for row in rows)


def _allocation_change_summary(rows: list[dict[str, Any]]) -> str:
    active = [row for row in rows if row.get("change_status") not in {"STABLE", "NO_HISTORY", "NO_ALLOCATION_TO_COMPARE"}]
    if not active:
        return "Aucun changement majeur ou pas encore assez d’historique distinct."

    def magnitude(row: dict[str, Any]) -> float:
        raw = str(row.get("change_amount") or "0").replace("$", "").replace(" ", "").replace(",", ".")
        return abs(safe_float(raw) or 0.0)

    row = max(active, key=magnitude)
    return f"{row.get('ticker')}: {row.get('change_status')} ({row.get('main_explanation')})"


def _sensitivity_summary_text(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "Non disponible."
    row = rows[0]
    status = row.get("robustness_status") or "N/D"
    score = row.get("robustness_score") or "N/D"
    summary = row.get("summary") or ""
    return f"{status} ({score}/100) - {summary}"


def _sensitivity_score_interpretation(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "Score non disponible: l’agent ne peut pas juger si l’allocation est stable sous hypothèses prudentes."
    row = rows[0]
    score = safe_float(row.get("robustness_score"))
    status = str(row.get("robustness_status") or "")
    if score is None:
        return "Score non disponible: l’allocation doit être lue avec prudence."
    if status == "ROBUST" or score >= 80:
        return (
            "80-100 indique que l’allocation reste assez stable même si les hypothèses deviennent un peu plus prudentes. "
            "La recommandation peut être lue comme robuste, tout en validant les données normales."
        )
    if status == "MODERATELY_SENSITIVE" or score >= 65:
        return (
            "65-79 indique une sensibilité modérée: la recommandation reste utilisable, mais certains montants peuvent bouger "
            "si les estimations de croissance, valorisation ou qualité des données sont moins favorables."
        )
    return (
        "Sous 65 indique une allocation très sensible: avant une grosse cotisation, il faut valider les données prioritaires "
        "et éviter de traiter la répartition comme très solide."
    )


def _decision_quality_score_interpretation(decision_quality: dict[str, Any]) -> str:
    score = safe_float((decision_quality or {}).get("decision_quality_score"))
    if score is None:
        return "Score non disponible: la qualité de la recommandation ne peut pas être évaluée."
    if score >= 85:
        return (
            "85-100 indique une recommandation très solide: les données, les risques, la concentration, VFV et la logique "
            "high-CAGR sont bien alignés."
        )
    if score >= 70:
        return (
            "70-84 indique une recommandation crédible et utilisable: elle est alignée avec le profil high-CAGR, "
            "mais quelques données, risques ou sensibilités empêchent de la considérer parfaite."
        )
    if score >= 55:
        return (
            "55-69 indique une recommandation prudente ou fragile: elle peut rester utile, mais il faut accorder plus de poids "
            "aux validations manuelles et aux garde-fous."
        )
    return (
        "Sous 55 indique une recommandation faible: l’agent préfère probablement VFV ou manque de preuves suffisantes; "
        "une validation manuelle est nécessaire avant d’agir."
    )


def _top_validation_priority_text(rows: list[dict[str, Any]]) -> str:
    real_rows = [row for row in rows if row.get("ticker")]
    if not real_rows:
        return "Aucune priorité majeure."
    row = real_rows[0]
    field = row.get("field_label") or row.get("field") or row.get("donnée") or "donnée à valider"
    priority = row.get("priority") or row.get("importance") or "priorité non classée"
    return f"{row.get('ticker')} - {field} ({priority})"


def _portfolio_change_summary_text(
    current_rows: list[dict[str, Any]],
    history_rows: list[dict[str, Any]],
) -> str:
    real_current = [row for row in current_rows if str(row.get("change_type") or "") != "BASELINE"]
    substantive_current = _substantive_portfolio_change_rows(real_current)
    substantive_history = _substantive_portfolio_change_rows(history_rows)
    rows = substantive_current or real_current or substantive_history or [
        row for row in history_rows if str(row.get("change_type") or "") != "BASELINE"
    ]
    if not rows:
        return "Aucun changement réel encore détecté."
    row = _sort_portfolio_changes_for_compact(rows)[0]
    value = safe_float(row.get("estimated_change_value_cad"))
    value_text = f", valeur estimée {money(value)}" if value is not None else ""
    scope = "depuis la dernière analyse" if real_current else "dernier historique connu"
    return (
        f"{scope}: {row.get('date') or 'date inconnue'} - {row.get('ticker')} "
        f"({row.get('account_type')}), {row.get('change_type')} "
        f"variation {row.get('shares_change')}{value_text}."
    )


def _substantive_portfolio_change_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    output = []
    for row in rows:
        change_type = str(row.get("change_type") or "")
        shares_change = safe_float(row.get("shares_change"))
        if change_type in {"BASELINE", "COST_BASIS_UPDATED"}:
            continue
        if shares_change in {None, 0.0}:
            continue
        output.append(row)
    return output


def _sort_portfolio_changes_for_compact(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    priority = {
        "POSITION_ADDED": 5,
        "POSITION_INCREASED": 5,
        "POSITION_REDUCED": 5,
        "POSITION_REMOVED": 5,
        "TRANSFER_IN": 4,
        "TRANSFER_OUT": 4,
        "COST_BASIS_UPDATED": 1,
        "BASELINE": 0,
    }
    return sorted(
        rows,
        key=lambda row: (
            str(row.get("date") or ""),
            priority.get(str(row.get("change_type") or ""), 2),
            abs(safe_float(row.get("estimated_change_value_cad")) or 0.0),
        ),
        reverse=True,
    )


def _account_allocation_summary_text(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "Aucune répartition par compte disponible."
    sorted_rows = sorted(rows, key=lambda row: safe_float(row.get("total_value_cad")) or 0.0, reverse=True)
    summaries = []
    for row in sorted_rows[:3]:
        account = row.get("account_type") or "UNKNOWN"
        value = money(safe_float(row.get("total_value_cad")))
        top_positions = _compact_sentence(row.get("top_positions"), 90)
        summaries.append(f"{account}: {value} ({top_positions})")
    suffix = "" if len(sorted_rows) <= 3 else f"; +{len(sorted_rows) - 3} autre(s) compte(s)"
    return "; ".join(summaries) + suffix


def _decision_quality_display_rows(decision_quality: dict[str, Any]) -> list[dict[str, Any]]:
    if not decision_quality:
        return [
            {
                "decision_quality_level": "N/D",
                "decision_quality_score": "N/D",
                "summary": "Aucune évaluation disponible.",
                "profile_calibration": "N/D",
                "vfv_total_percent": "N/D",
                "vfv_redirection_percent": "N/D",
                "core_allocation_percent": "N/D",
                "data_quality_status": "N/D",
                "risk_status": "N/D",
                "stability_status": "N/D",
                "sensitivity_status": "N/D",
            }
        ]
    row = dict(decision_quality)
    for field in ["vfv_total_percent", "vfv_redirection_percent", "core_allocation_percent"]:
        row[field] = pct(safe_float(row.get(field)), 1)
    return [row]


def _row_or_none(rows: list[dict[str, Any]], key: str) -> str:
    return str(rows[0].get(key)) if rows else "Aucune"


def _row_list_or_none(rows: list[dict[str, Any]], key: str) -> str:
    values = [str(row.get(key)) for row in rows if row.get(key)]
    return ", ".join(values) if values else "Aucune"


def _display_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    display_rows = []
    for row in rows:
        display = row.get("ticker_display") or row.get("ticker")
        display_rows.append({**row, "ticker": display})
    return display_rows


def _best_opportunity(rows: list[dict[str, Any]]) -> str:
    eligible = [
        row
        for row in rows
        if row.get("ticker") != "VFV.TO"
        and row.get("thesis_status") == "INTACT"
        and (
            row.get("add_eligibility_status") in ADD_ALLOWED_STATUSES
            or (not row.get("add_eligibility_status") and row.get("liquidation_status") == "GREEN")
        )
    ]
    return str(eligible[0].get("ticker")) if eligible else "Aucune"


def _sell_signal_summary(rows: list[dict[str, Any]]) -> str:
    active = [row for row in rows if row.get("sell_status", row.get("liquidation_status")) in {"YELLOW", "ORANGE", "RED"}]
    if not active:
        return "Aucun signal de vente majeur."
    return ", ".join(f"{row['ticker']}={row.get('sell_decision', row.get('recommended_action'))}" for row in active)


def _monitoring_summary(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "Aucune alerte de surveillance majeure."
    return ", ".join(f"{row.get('ticker')}={row.get('statut_surveillance')}" for row in rows[:8])


def _quality_drawdown_summary(rows: list[dict[str, Any]]) -> str:
    active = [row for row in rows if row.get("statut") == "QUALITY_DRAWDOWN_OPPORTUNITY"]
    if active:
        return ", ".join(f"{row.get('ticker')}=opportunité potentielle" for row in active[:6])
    risk = [row for row in rows if row.get("statut") in {"PRICE_WEAKNESS_WITH_FUNDAMENTAL_RISK", "AVOID_FALLING_KNIFE"}]
    if risk:
        return ", ".join(f"{row.get('ticker')}=baisse à risque" for row in risk[:6])
    return "Aucune opportunité de baisse de qualité détectée."


def _external_allocation_policy_note(mode: str) -> str:
    if mode == "high-cagr":
        return (
            "En mode `high-cagr`, les titres externes (WATCHLIST, MARKET_SCANNER, DISCOVERY_IDEAS) "
            "peuvent recevoir une allocation directe sans promotion manuelle vers le Core Portfolio, "
            "si et seulement s'ils franchissent les filtres stricts de qualité, thèse, données et "
            "avantage face à VFV définis dans l'allocation engine. "
            "Les candidats Discovery scorés uniquement sur données gratuites sans rapport BNCD/Morningstar "
            # Garder 70 synchronisé avec DISCOVERY_VALIDATION_PRIORITY_MIN_SCORE dans main.py.
            "apparaissent dans latest_validation_priority.csv si leur score dépasse 70 et leur statut "
            "d'allocation est éligible. "
            "[DECISION 2026-06-30 Proposition 8 — DECISION 2026-07-04]"
        )
    return (
        f"En mode `{mode}`, les titres externes peuvent entrer directement dans l'allocation seulement s'ils "
        "passent les filtres stricts du mode: thèse intacte, vente GREEN, données suffisantes, valorisation non "
        "extrême, avantage clair vs VFV et plafond de nouvelle position externe."
    )


def _winner_protection_summary(rows: list[dict[str, Any]]) -> str:
    active_statuses = {"WATCH_WINNER_PULLBACK", "PROTECT_WINNER_REVIEW", "TRIM_25_REVIEW", "TRIM_50_REVIEW", "LIQUIDATE_WINNER_REVIEW"}
    active = [row for row in rows if row.get("winner_protection_status") in active_statuses]
    if not active:
        return "Aucun winner ne demande une protection spéciale."
    return ", ".join(f"{row['ticker']}={row.get('winner_protection_action')}" for row in active)


def _status_summary(rows: list[dict[str, Any]], field: str, wanted: str) -> str:
    tickers = [str(row.get("ticker")) for row in rows if row.get(field) == wanted]
    return ", ".join(tickers) if tickers else "Aucune"


def _trend_summary(rows: list[dict[str, Any]]) -> str:
    active = [
        row
        for row in rows
        if row.get("universe") == "CORE_PORTFOLIO" and row.get("trend_status") in {"DETERIORATING", "SOLIDIFYING", "DEVELOPING"}
    ]
    if not active:
        return "Aucune tendance historique majeure."
    return ", ".join(f"{row.get('ticker')}={row.get('trend_status')}" for row in active)


def _cycle_summary(rows: list[dict[str, Any]]) -> str:
    active = [row for row in rows if row.get("universe") == "CORE_PORTFOLIO" and row.get("cycle_bubble_risk_level") in {"HIGH", "EXTREME"}]
    if not active:
        return "Aucun risque dominant élevé dans le core."
    return ", ".join(f"{row.get('ticker')}={row.get('cycle_bubble_risk_level')}" for row in active[:6])


def _durability_summary(rows: list[dict[str, Any]]) -> str:
    core_rows = [row for row in rows if row.get("universe") == "CORE_PORTFOLIO"]
    durable = [row for row in core_rows if row.get("long_term_durability_status") == "VERY_DURABLE_COMPOUNDER"]
    fragile = [row for row in core_rows if row.get("long_term_durability_status") in {"HIGH_GROWTH_BUT_FRAGILE", "SPECULATIVE_OR_UNPROVEN"}]
    durable_text = ", ".join(str(row.get("ticker")) for row in durable[:5]) if durable else "aucun"
    fragile_text = ", ".join(str(row.get("ticker")) for row in fragile[:5]) if fragile else "aucun"
    return f"compounders très durables={durable_text}; fragiles/non prouvés={fragile_text}"


def _market_growth_summary(rows: list[dict[str, Any]]) -> str:
    core_rows = [row for row in rows if row.get("universe") == "CORE_PORTFOLIO"]
    tailwinds = [row for row in core_rows if row.get("market_growth_thesis_status") == "STRUCTURAL_TAILWIND"]
    hype = [row for row in core_rows if row.get("market_growth_thesis_status") == "HYPE_RISK"]
    tailwind_text = ", ".join(str(row.get("ticker")) for row in tailwinds[:5]) if tailwinds else "aucun"
    hype_text = ", ".join(str(row.get("ticker")) for row in hype[:5]) if hype else "aucun"
    return f"vents structurels={tailwind_text}; risque hype={hype_text}"


def _data_freshness_summary(rows: list[dict[str, Any]]) -> str:
    primary_rows = [row for row in rows if row.get("universe") != "DISCOVERY_IDEAS"]
    critical = [
        row
        for row in primary_rows
        if row.get("overall_data_freshness_level") in {"CRITICAL_REFRESH_NEEDED", "STALE_REFRESH_RECOMMENDED"}
    ]
    watch = [row for row in primary_rows if row.get("overall_data_freshness_level") == "WATCH_FRESHNESS"]
    if critical:
        return "à rafraîchir=" + ", ".join(str(row.get("ticker")) for row in critical[:6])
    if watch:
        return "à surveiller=" + ", ".join(str(row.get("ticker")) for row in watch[:6])
    discovery_issues = [
        row
        for row in rows
        if row.get("universe") == "DISCOVERY_IDEAS"
        and row.get("overall_data_freshness_level") in {"CRITICAL_REFRESH_NEEDED", "STALE_REFRESH_RECOMMENDED"}
    ]
    if discovery_issues:
        return f"aucune alerte majeure dans le core/scanner; {len(discovery_issues)} idées discovery à vérifier"
    return "aucune donnée périmée majeure détectée"


def _freshness_reason(row: dict[str, Any]) -> str:
    reasons = []
    market_reason = str(row.get("market_data_freshness_reason") or "").strip()
    research_reason = str(row.get("research_report_freshness_reason") or "").strip()
    stale_warning = str(row.get("market_data_stale_cache_warning") or "").strip()
    if market_reason:
        reasons.append(market_reason)
    if stale_warning:
        reasons.append(stale_warning)
    if research_reason and row.get("research_report_freshness_level") not in {"NO_REPORT", "RECENT"}:
        reasons.append(research_reason)
    return " ".join(reasons) or "Aucune alerte de fraîcheur majeure."


def _data_freshness_sort_key(row: dict[str, Any]) -> tuple[int, float, str]:
    rank = {
        "CRITICAL_REFRESH_NEEDED": 4,
        "STALE_REFRESH_RECOMMENDED": 3,
        "WATCH_FRESHNESS": 2,
        "OK_BUT_AGING": 1,
        "FRESH_ENOUGH": 0,
    }.get(str(row.get("overall_data_freshness_level")), 0)
    age = safe_float(row.get("market_data_age_hours")) or 0.0
    return rank, age, str(row.get("ticker"))


def _durability_sort_key(row: dict[str, Any]) -> tuple[int, float, str]:
    status_rank = {
        "VERY_DURABLE_COMPOUNDER": 4,
        "DURABLE_BUT_CYCLICAL": 3,
        "HIGH_GROWTH_BUT_FRAGILE": 2,
        "SPECULATIVE_OR_UNPROVEN": 1,
    }.get(str(row.get("long_term_durability_status")), 0)
    return status_rank, safe_float(row.get("long_term_durability_score")) or 0.0, str(row.get("ticker"))


def _average_score_text(value: Any) -> str:
    number = safe_float(value)
    return f"{number:.2f}" if number is not None else "N/D"


def _satellite_exclusion_summary(rows: list[dict[str, Any]]) -> str:
    tickers = [
        str(row.get("ticker"))
        for row in rows
        if row.get("average_score_excluded_reason")
    ]
    return ", ".join(tickers) if tickers else "Aucune"


def _signals(row: dict[str, Any]) -> str:
    signals = row["signals_detected"] if "signals_detected" in row else row.get("liquidation_reasons", [])
    if isinstance(signals, list):
        return ", ".join(str(item) for item in signals) if signals else "Aucun"
    return str(signals)


def _ticker_issue_text(row: dict[str, Any]) -> str:
    issues = row.get("ticker_issue_reasons") or []
    if isinstance(issues, list):
        if not issues:
            return "Aucune"
        return ", ".join(str(issue) for issue in issues) + f". {row.get('ticker_suggested_action')}"
    return str(issues) if issues else "Aucune"


def _risk_level(alert: str) -> str:
    text = str(alert).lower()
    if "extrême" in text or "extreme" in text:
        return "HIGH"
    if "élev" in text or "forte" in text or "très concentré" in text:
        return "MEDIUM"
    return "LOW"
