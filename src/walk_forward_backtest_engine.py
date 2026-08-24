from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

import pandas as pd

from .backtest_engine import fetch_price_history_cad
from .benchmark_comparison_engine import (
    WALK_FORWARD_BENCHMARK_COLUMNS,
    benchmark_price_tickers,
    build_walk_forward_benchmark_comparisons,
    load_benchmark_definitions,
)
from .mode_artifacts import mode_artifact_path, write_csv_records_mode_pair, write_text_mode_pair
from .transaction_friction_engine import (
    BACKTEST_FRICTION_AUDIT_COLUMNS,
    add_friction_fields_to_walk_forward_periods,
    add_friction_fields_to_walk_forward_summary,
    build_walk_forward_friction_rows,
    merge_friction_audit_rows,
)
from .utils import DATA_DIR, DISCLAIMER, load_json, markdown_to_html, pct, read_csv_records, safe_float, write_csv_records, write_text
from .validation_evidence import (
    EvidenceClass,
    RunPurpose,
    combined_snapshot_purpose,
    evidence_maturity,
    purpose_is_walk_forward_decision,
    snapshot_run_purpose,
)


WALK_FORWARD_INVENTORY_COLUMNS = [
    "mode",
    "evidence_class",
    "analysis_date",
    "created_at",
    "model_rules_version",
    "run_purpose",
    "run_purpose_status",
    "primary_timeline_eligible",
    "eligibility_basis",
    "analysis_snapshot_path",
    "allocation_snapshot_path",
    "analysis_row_count",
    "core_position_count",
    "allocation_count",
    "allocated_tickers",
    "vfv_allocation_percent",
    "top_allocation_ticker",
    "top_allocation_percent",
    "next_analysis_date",
    "days_to_next",
    "usable_for_walk_forward",
    "exclusion_reason",
]

WALK_FORWARD_COVERAGE_COLUMNS = [
    "mode",
    "status",
    "evidence_class",
    "evidence_maturity",
    "distinct_analysis_dates",
    "paired_snapshot_dates",
    "decision_eligible_snapshots",
    "diagnostic_snapshots",
    "legacy_unknown_snapshots",
    "usable_walk_forward_periods",
    "first_analysis_date",
    "last_analysis_date",
    "min_days_between_points",
    "recommended_min_periods",
    "interpretation",
]

WALK_FORWARD_SUMMARY_COLUMNS = [
    "mode",
    "status",
    "evidence_class",
    "evidence_maturity",
    "strategy_validation_confidence",
    "simulated_periods",
    "usable_walk_forward_periods",
    "avg_period_days",
    "avg_strategy_period_return",
    "avg_vfv_period_return",
    "avg_excess_return_vs_vfv",
    "win_rate_vs_vfv",
    "compounded_strategy_return",
    "compounded_vfv_return",
    "compounded_excess_return_vs_vfv",
    "gross_return",
    "estimated_transaction_cost_cad",
    "net_return_after_friction",
    "friction_drag",
    "friction_assumption_status",
    "regime_coverage_status",
    "regime_count",
    "weak_regimes",
    "price_return_basis",
    "interpretation",
]

WALK_FORWARD_PERIOD_COLUMNS = [
    "mode",
    "evidence_class",
    "run_purpose",
    "model_rules_version",
    "analysis_date",
    "next_analysis_date",
    "days_held",
    "start_price_date",
    "end_price_date",
    "allocation_count",
    "allocated_tickers",
    "strategy_period_return",
    "vfv_period_return",
    "excess_return_vs_vfv",
    "strategy_annualized_return",
    "vfv_annualized_return",
    "estimated_transaction_cost_cad",
    "net_strategy_period_return_after_friction",
    "friction_drag",
    "friction_assumption_status",
    "market_regime",
    "regime_note",
    "missing_price_tickers",
    "missing_allocation_weight",
    "evaluation_status",
    "notes",
]

WALK_FORWARD_ALLOCATION_RETURN_COLUMNS = [
    "mode",
    "analysis_date",
    "next_analysis_date",
    "ticker",
    "allocation_weight",
    "start_price",
    "end_price",
    "period_return",
    "weighted_return_contribution",
    "trade_value_cad",
    "price_status",
]

WALK_FORWARD_REGIME_COLUMNS = [
    "mode",
    "market_regime",
    "period_count",
    "avg_strategy_period_return",
    "avg_vfv_period_return",
    "avg_excess_return_vs_vfv",
    "win_rate_vs_vfv",
    "compounded_excess_return_vs_vfv",
    "regime_status",
    "interpretation",
]


@dataclass(frozen=True)
class WalkForwardInventoryConfig:
    mode: str = "high-cagr"
    min_days_between_points: int = 14
    recommended_min_periods: int = 6
    max_missing_allocation_weight: float = 0.10


def run_walk_forward_inventory(
    reports_dir: str | Path,
    *,
    mode: str = "high-cagr",
    min_days_between_points: int = 14,
    recommended_min_periods: int = 6,
) -> dict[str, Any]:
    reports_dir = Path(reports_dir)
    config = WalkForwardInventoryConfig(
        mode=mode,
        min_days_between_points=max(1, int(min_days_between_points)),
        recommended_min_periods=max(2, int(recommended_min_periods)),
    )
    inventory_rows = build_walk_forward_inventory(reports_dir, config)
    coverage_row = build_walk_forward_coverage(inventory_rows, config)
    markdown = build_walk_forward_inventory_report(coverage_row, inventory_rows, config)

    write_csv_records_mode_pair(reports_dir, "latest_walk_forward_inventory.csv", mode, inventory_rows, WALK_FORWARD_INVENTORY_COLUMNS)
    write_csv_records_mode_pair(reports_dir, "latest_walk_forward_coverage.csv", mode, [coverage_row], WALK_FORWARD_COVERAGE_COLUMNS)
    write_text_mode_pair(reports_dir, "latest_walk_forward_inventory.md", mode, markdown)
    write_text_mode_pair(reports_dir, "latest_walk_forward_inventory.html", mode, markdown_to_html(markdown))
    return {"inventory_rows": inventory_rows, "coverage": coverage_row, "markdown": markdown}


def run_walk_forward_backtest(
    reports_dir: str | Path,
    data_dir: str | Path = DATA_DIR,
    *,
    mode: str = "high-cagr",
    min_days_between_points: int = 14,
    recommended_min_periods: int = 6,
    refresh_market_data: bool = False,
) -> dict[str, Any]:
    reports_dir = Path(reports_dir)
    config = WalkForwardInventoryConfig(
        mode=mode,
        min_days_between_points=max(1, int(min_days_between_points)),
        recommended_min_periods=max(2, int(recommended_min_periods)),
    )
    inventory_rows = build_walk_forward_inventory(reports_dir, config)
    coverage_row = build_walk_forward_coverage(inventory_rows, config)
    usable_rows = [row for row in inventory_rows if _truthy(row.get("usable_for_walk_forward"))]

    period_rows: list[dict[str, Any]] = []
    allocation_return_rows: list[dict[str, Any]] = []
    regime_rows: list[dict[str, Any]] = []
    benchmark_rows: list[dict[str, Any]] = []
    price_basis = "NOT_RUN_NO_USABLE_PERIODS"
    benchmark_definitions = load_benchmark_definitions()
    if usable_rows:
        tickers = sorted(set(_walk_forward_price_tickers(usable_rows)) | set(benchmark_price_tickers(benchmark_definitions)))
        years = _walk_forward_price_years(usable_rows)
        try:
            prices = fetch_price_history_cad(tickers, data_dir, years=years, refresh=refresh_market_data, mode=mode)
            price_basis = str(prices.attrs.get("price_return_basis") or "UNKNOWN_PRICE_BASIS")
            simulation = simulate_walk_forward_periods(usable_rows, prices, config)
            period_rows = simulation["period_rows"]
            allocation_return_rows = simulation["allocation_return_rows"]
            benchmark_rows = build_walk_forward_benchmark_comparisons(period_rows, prices, benchmark_definitions)
            regime_rows = build_walk_forward_regime_summary(period_rows, config)
        except Exception as exc:
            period_rows = [_simulation_error_row(config, str(exc))]
            price_basis = "PRICE_FETCH_FAILED"

    summary_row = build_walk_forward_simulation_summary(period_rows, coverage_row, config, price_basis, regime_rows)
    friction_rows = build_walk_forward_friction_rows(summary_row, period_rows, allocation_return_rows)
    period_rows = add_friction_fields_to_walk_forward_periods(period_rows, friction_rows)
    summary_row = add_friction_fields_to_walk_forward_summary(summary_row, friction_rows)
    report = build_walk_forward_backtest_report(coverage_row, inventory_rows, summary_row, period_rows, regime_rows, config, benchmark_rows)

    write_csv_records_mode_pair(reports_dir, "latest_walk_forward_inventory.csv", mode, inventory_rows, WALK_FORWARD_INVENTORY_COLUMNS)
    write_csv_records_mode_pair(reports_dir, "latest_walk_forward_coverage.csv", mode, [coverage_row], WALK_FORWARD_COVERAGE_COLUMNS)
    write_csv_records_mode_pair(reports_dir, "latest_walk_forward_summary.csv", mode, [summary_row], WALK_FORWARD_SUMMARY_COLUMNS)
    write_csv_records_mode_pair(reports_dir, "latest_walk_forward_periods.csv", mode, period_rows, WALK_FORWARD_PERIOD_COLUMNS)
    write_csv_records_mode_pair(
        reports_dir,
        "latest_walk_forward_period_allocations.csv",
        mode,
        allocation_return_rows,
        WALK_FORWARD_ALLOCATION_RETURN_COLUMNS,
    )
    write_csv_records_mode_pair(reports_dir, "latest_walk_forward_regime_summary.csv", mode, regime_rows, WALK_FORWARD_REGIME_COLUMNS)
    write_csv_records_mode_pair(
        reports_dir,
        "latest_walk_forward_benchmark_comparison.csv",
        mode,
        benchmark_rows,
        WALK_FORWARD_BENCHMARK_COLUMNS,
    )
    existing_friction_rows = read_csv_records(reports_dir / "latest_backtest_friction_audit.csv")
    existing_mode_friction_rows = read_csv_records(mode_artifact_path(reports_dir / "latest_backtest_friction_audit.csv", mode))
    write_csv_records(
        reports_dir / "latest_backtest_friction_audit.csv",
        merge_friction_audit_rows(existing_friction_rows, friction_rows, {"WALK_FORWARD_SUMMARY", "WALK_FORWARD_PERIOD"}),
        BACKTEST_FRICTION_AUDIT_COLUMNS,
    )
    write_csv_records(
        mode_artifact_path(reports_dir / "latest_backtest_friction_audit.csv", mode),
        merge_friction_audit_rows(existing_mode_friction_rows, friction_rows, {"WALK_FORWARD_SUMMARY", "WALK_FORWARD_PERIOD"}),
        BACKTEST_FRICTION_AUDIT_COLUMNS,
    )
    write_text_mode_pair(reports_dir, "latest_walk_forward_report.md", mode, report)
    write_text_mode_pair(reports_dir, "latest_walk_forward_report.html", mode, markdown_to_html(report))
    inventory_report = build_walk_forward_inventory_report(coverage_row, inventory_rows, config)
    write_text_mode_pair(reports_dir, "latest_walk_forward_inventory.md", mode, inventory_report)
    write_text_mode_pair(reports_dir, "latest_walk_forward_inventory.html", mode, markdown_to_html(inventory_report))
    return {
        "inventory_rows": inventory_rows,
        "coverage": coverage_row,
        "summary": summary_row,
        "period_rows": period_rows,
        "allocation_return_rows": allocation_return_rows,
        "regime_rows": regime_rows,
        "benchmark_rows": benchmark_rows,
        "friction_rows": friction_rows,
        "markdown": report,
    }


def build_walk_forward_inventory(
    reports_dir: str | Path,
    config: WalkForwardInventoryConfig | None = None,
) -> list[dict[str, Any]]:
    config = config or WalkForwardInventoryConfig()
    history_dir = Path(reports_dir) / "history"
    analysis_by_date = _latest_daily_payloads(history_dir, "analysis", config.mode)
    allocation_by_date = _latest_daily_payloads(history_dir, "allocation", config.mode)
    dates = sorted(set(analysis_by_date) | set(allocation_by_date))
    rows: list[dict[str, Any]] = []

    payloads_by_date: dict[str, tuple[dict[str, Any], dict[str, Any]]] = {}
    for analysis_date in dates:
        analysis = analysis_by_date.get(analysis_date, {})
        allocation = allocation_by_date.get(analysis_date, {})
        payloads_by_date[analysis_date] = (analysis, allocation)
        rows.append(_inventory_row(analysis_date, analysis, allocation, "", None, config))

    eligible_dates, eligibility_basis = _primary_timeline_dates(rows, config)
    eligible_index = {analysis_date: index for index, analysis_date in enumerate(eligible_dates)}
    for row in rows:
        analysis_date = str(row.get("analysis_date") or "")
        is_eligible = analysis_date in eligible_index
        row["primary_timeline_eligible"] = is_eligible
        row["eligibility_basis"] = eligibility_basis.get(analysis_date, "PURPOSE_EXCLUDED")
        if not is_eligible:
            row["next_analysis_date"] = ""
            row["days_to_next"] = ""
            row["usable_for_walk_forward"] = False
            row["exclusion_reason"] = f"RUN_PURPOSE_NOT_WALK_FORWARD_ELIGIBLE:{row.get('run_purpose')}"
            continue
        index = eligible_index[analysis_date]
        next_date = eligible_dates[index + 1] if index + 1 < len(eligible_dates) else ""
        days_to_next = _days_between(analysis_date, next_date) if next_date else None
        analysis, allocation = payloads_by_date[analysis_date]
        exclusion = _exclusion_reason(analysis, allocation, next_date, days_to_next, config)
        row["next_analysis_date"] = next_date
        row["days_to_next"] = days_to_next if days_to_next is not None else ""
        row["usable_for_walk_forward"] = not exclusion
        row["exclusion_reason"] = exclusion
    return rows


def build_walk_forward_coverage(
    inventory_rows: list[dict[str, Any]],
    config: WalkForwardInventoryConfig | None = None,
) -> dict[str, Any]:
    config = config or WalkForwardInventoryConfig()
    dated = [row for row in inventory_rows if row.get("analysis_date")]
    paired = [row for row in dated if row.get("analysis_snapshot_path") and row.get("allocation_snapshot_path")]
    usable = [row for row in dated if _truthy(row.get("usable_for_walk_forward"))]
    eligible = [row for row in dated if _truthy(row.get("primary_timeline_eligible"))]
    diagnostic = [
        row for row in dated
        if str(row.get("run_purpose") or "")
        in {RunPurpose.DIAGNOSTIC.value, RunPurpose.DEVELOPMENT_TEST.value, RunPurpose.ZERO_CAPITAL_ANALYSIS.value, RunPurpose.MAINTENANCE.value}
    ]
    legacy = [row for row in dated if str(row.get("run_purpose") or "") == RunPurpose.UNKNOWN_LEGACY.value]
    dates = [str(row.get("analysis_date")) for row in dated]
    status = _coverage_status(len(usable), config.recommended_min_periods)
    return {
        "mode": config.mode,
        "status": status,
        "evidence_class": EvidenceClass.POINT_IN_TIME_WALK_FORWARD.value,
        "evidence_maturity": evidence_maturity(len(usable)),
        "distinct_analysis_dates": len(dated),
        "paired_snapshot_dates": len(paired),
        "decision_eligible_snapshots": len(eligible),
        "diagnostic_snapshots": len(diagnostic),
        "legacy_unknown_snapshots": len(legacy),
        "usable_walk_forward_periods": len(usable),
        "first_analysis_date": min(dates) if dates else "",
        "last_analysis_date": max(dates) if dates else "",
        "min_days_between_points": config.min_days_between_points,
        "recommended_min_periods": config.recommended_min_periods,
        "interpretation": _coverage_interpretation(status, len(usable), config.recommended_min_periods),
    }


def build_walk_forward_inventory_report(
    coverage_row: dict[str, Any],
    inventory_rows: list[dict[str, Any]],
    config: WalkForwardInventoryConfig,
) -> str:
    lines = [
        "# Inventaire walk-forward",
        "",
        f"> {DISCLAIMER}",
        "",
        "## Lecture",
        "",
        "- Bloc 1 seulement: ce rapport ne simule pas encore la performance.",
        "- Il vérifie si l’historique local contient assez de snapshots analyse + allocation pour un futur backtest hors-échantillon.",
        "- Les analyses multiples d’une même journée sont dédupliquées sans laisser un diagnostic remplacer une décision explicitement identifiée.",
        "- La chronologie primaire utilise les décisions planifiées/manuelles; diagnostics, maintenance, tests et analyses à capital nul restent auditables mais ne la fragmentent pas.",
        "- Les anciens snapshots sans but explicite restent `UNKNOWN_LEGACY`; un repli causal et espacé peut les rendre `PARTIALLY_RECOVERABLE` sans prétendre connaître leur but réel.",
        "",
        "## Résumé",
        "",
        _markdown_table([coverage_row], WALK_FORWARD_COVERAGE_COLUMNS),
        "",
        "## Snapshots retenus",
        "",
        _markdown_table(_compact_inventory_rows(inventory_rows), [
            "analysis_date",
            "created_at",
            "run_purpose",
            "run_purpose_status",
            "primary_timeline_eligible",
            "eligibility_basis",
            "allocation_count",
            "allocated_tickers",
            "next_analysis_date",
            "days_to_next",
            "usable_for_walk_forward",
            "exclusion_reason",
        ]),
        "",
        "## Prochaine étape",
        "",
        "- Quand ce bloc indique assez de périodes utilisables, le bloc 2 pourra simuler une période suivante à partir de chaque recommandation réellement disponible à l’époque.",
        "- Tant que l’historique est court, le futur walk-forward devra rester informatif et ne pas déclencher d’auto-tuning agressif.",
        "",
    ]
    return "\n".join(lines)


def simulate_walk_forward_periods(
    usable_inventory_rows: list[dict[str, Any]],
    prices_cad: pd.DataFrame,
    config: WalkForwardInventoryConfig | None = None,
) -> dict[str, list[dict[str, Any]]]:
    config = config or WalkForwardInventoryConfig()
    prices = prices_cad.sort_index().ffill().dropna(how="all")
    period_rows: list[dict[str, Any]] = []
    allocation_return_rows: list[dict[str, Any]] = []
    if prices.empty:
        return {"period_rows": [_simulation_error_row(config, "Aucun prix historique disponible.")], "allocation_return_rows": []}

    for row in usable_inventory_rows:
        period = _simulate_single_walk_forward_period(row, prices, config)
        period_rows.append(period["period_row"])
        allocation_return_rows.extend(period["allocation_return_rows"])
    friction_rows = build_walk_forward_friction_rows({}, period_rows, allocation_return_rows)
    period_rows = add_friction_fields_to_walk_forward_periods(period_rows, friction_rows)
    return {"period_rows": period_rows, "allocation_return_rows": allocation_return_rows, "friction_rows": friction_rows}


def build_walk_forward_simulation_summary(
    period_rows: list[dict[str, Any]],
    coverage_row: dict[str, Any],
    config: WalkForwardInventoryConfig,
    price_basis: str,
    regime_rows: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    simulated = [
        row for row in period_rows
        if str(row.get("evaluation_status") or "") in {"SIMULATED", "SIMULATED_WITH_PARTIAL_PRICE_DATA"}
    ]
    usable_count = int(safe_float(coverage_row.get("usable_walk_forward_periods")) or 0)
    status = _simulation_status(len(simulated), usable_count, config.recommended_min_periods)
    strategy_returns = [safe_float(row.get("strategy_period_return")) or 0.0 for row in simulated]
    vfv_returns = [safe_float(row.get("vfv_period_return")) or 0.0 for row in simulated]
    excess_returns = [safe_float(row.get("excess_return_vs_vfv")) or 0.0 for row in simulated]
    days = [safe_float(row.get("days_held")) or 0.0 for row in simulated]
    compounded_strategy = _compound_returns(strategy_returns)
    compounded_vfv = _compound_returns(vfv_returns)
    compounded_excess = ""
    if isinstance(compounded_strategy, (int, float)) and isinstance(compounded_vfv, (int, float)) and (1.0 + compounded_vfv) > 0:
        compounded_excess = round((1.0 + compounded_strategy) / (1.0 + compounded_vfv) - 1.0, 4)
    regime_rows = regime_rows or []
    regime_status = _regime_coverage_status(regime_rows, len(simulated), config.recommended_min_periods)
    weak_regimes = [str(row.get("market_regime") or "") for row in regime_rows if str(row.get("regime_status") or "") == "WEAK"]
    return {
        "mode": config.mode,
        "status": status,
        "evidence_class": EvidenceClass.POINT_IN_TIME_WALK_FORWARD.value,
        "evidence_maturity": evidence_maturity(len(simulated)),
        "strategy_validation_confidence": evidence_maturity(len(simulated)),
        "simulated_periods": len(simulated),
        "usable_walk_forward_periods": usable_count,
        "avg_period_days": round(sum(days) / len(days), 1) if days else "",
        "avg_strategy_period_return": _average(strategy_returns),
        "avg_vfv_period_return": _average(vfv_returns),
        "avg_excess_return_vs_vfv": _average(excess_returns),
        "win_rate_vs_vfv": round(sum(1 for value in excess_returns if value > 0) / len(excess_returns), 4) if excess_returns else "",
        "compounded_strategy_return": compounded_strategy,
        "compounded_vfv_return": compounded_vfv,
        "compounded_excess_return_vs_vfv": compounded_excess,
        "regime_coverage_status": regime_status,
        "regime_count": len(regime_rows),
        "weak_regimes": ", ".join(regime for regime in weak_regimes if regime),
        "price_return_basis": price_basis,
        "interpretation": _simulation_interpretation(status, len(simulated), config.recommended_min_periods),
    }


def build_walk_forward_regime_summary(
    period_rows: list[dict[str, Any]],
    config: WalkForwardInventoryConfig | None = None,
) -> list[dict[str, Any]]:
    config = config or WalkForwardInventoryConfig()
    simulated = [
        row for row in period_rows
        if str(row.get("evaluation_status") or "") in {"SIMULATED", "SIMULATED_WITH_PARTIAL_PRICE_DATA"}
    ]
    by_regime: dict[str, list[dict[str, Any]]] = {}
    for row in simulated:
        regime = str(row.get("market_regime") or "UNKNOWN_REGIME")
        by_regime.setdefault(regime, []).append(row)

    rows: list[dict[str, Any]] = []
    for regime, regime_periods in sorted(by_regime.items()):
        strategy_returns = [safe_float(row.get("strategy_period_return")) or 0.0 for row in regime_periods]
        vfv_returns = [safe_float(row.get("vfv_period_return")) or 0.0 for row in regime_periods]
        excess_returns = [safe_float(row.get("excess_return_vs_vfv")) or 0.0 for row in regime_periods]
        compounded_strategy = _compound_returns(strategy_returns)
        compounded_vfv = _compound_returns(vfv_returns)
        compounded_excess = ""
        if isinstance(compounded_strategy, (int, float)) and isinstance(compounded_vfv, (int, float)) and (1.0 + compounded_vfv) > 0:
            compounded_excess = round((1.0 + compounded_strategy) / (1.0 + compounded_vfv) - 1.0, 4)
        win_rate = round(sum(1 for value in excess_returns if value > 0) / len(excess_returns), 4) if excess_returns else ""
        status = _regime_status(regime_periods, compounded_excess, win_rate)
        rows.append(
            {
                "mode": config.mode,
                "market_regime": regime,
                "period_count": len(regime_periods),
                "avg_strategy_period_return": _average(strategy_returns),
                "avg_vfv_period_return": _average(vfv_returns),
                "avg_excess_return_vs_vfv": _average(excess_returns),
                "win_rate_vs_vfv": win_rate,
                "compounded_excess_return_vs_vfv": compounded_excess,
                "regime_status": status,
                "interpretation": _regime_interpretation(status, regime, len(regime_periods)),
            }
        )
    return rows


def build_walk_forward_backtest_report(
    coverage_row: dict[str, Any],
    inventory_rows: list[dict[str, Any]],
    summary_row: dict[str, Any],
    period_rows: list[dict[str, Any]],
    regime_rows: list[dict[str, Any]],
    config: WalkForwardInventoryConfig,
    benchmark_rows: list[dict[str, Any]] | None = None,
) -> str:
    benchmark_rows = benchmark_rows or []
    display_summary = _display_simulation_summary(summary_row)
    display_periods = [_display_period_row(row) for row in period_rows]
    display_regimes = [_display_regime_row(row) for row in regime_rows]
    display_benchmarks = [_display_walk_forward_benchmark_row(row) for row in benchmark_rows]
    lines = [
        "# Backtest walk-forward",
        "",
        f"> {DISCLAIMER}",
        "",
        "## Lecture",
        "",
        f"- Classe canonique: `{EvidenceClass.POINT_IN_TIME_WALK_FORWARD.value}`.",
        "- Bloc 2: le rapport mesure les recommandations historiques admissibles jusqu’à la prochaine décision admissible, jamais jusqu’au prochain diagnostic.",
        "- Il utilise seulement les snapshots locaux déjà sauvegardés pour le mode choisi.",
        "- Il compare la recommandation complète de la cotisation à une allocation 100 % `VFV.TO` sur la même période.",
        "- Il ajoute aussi des comparaisons passives/mécaniques alternatives, uniquement comme audit.",
        "- Les frictions de transaction estimées sont affichées en audit-only: elles ne changent ni le scoring, ni les recommandations.",
        "- Si l’historique est trop court, trop rapproché ou si les prix manquent, le rapport reste un diagnostic préliminaire.",
        "- Si un benchmark alternatif manque parce que le cache local ne contient pas encore ses prix, relancer avec `--refresh-market-data` peut le rendre disponible.",
        "- Les rendements annualisés de périodes courtes peuvent être trompeurs; la ligne la plus utile est l’excès de rendement par période vs VFV.",
        "",
        "## Résumé de couverture",
        "",
        _markdown_table([coverage_row], WALK_FORWARD_COVERAGE_COLUMNS),
        "",
        "## Résumé de simulation",
        "",
        _markdown_table([display_summary], WALK_FORWARD_SUMMARY_COLUMNS),
        "",
        "## Périodes simulées",
        "",
        _markdown_table(display_periods, [
            "analysis_date",
            "run_purpose",
            "eligibility_basis",
            "next_analysis_date",
            "days_held",
            "market_regime",
            "allocated_tickers",
            "strategy_period_return",
            "vfv_period_return",
            "excess_return_vs_vfv",
            "net_strategy_period_return_after_friction",
            "friction_drag",
            "evaluation_status",
            "notes",
        ]),
        "",
        "## Résumé par régime de marché",
        "",
        "- Cette section évite de juger le modèle seulement sur un seul type de marché.",
        "- Si l’historique est trop court ou concentré dans un seul régime, elle reste informative et ne déclenche aucun tuning automatique agressif.",
        "",
        _markdown_table(display_regimes, WALK_FORWARD_REGIME_COLUMNS),
        "",
        "## Comparaisons benchmarks alternatifs",
        "",
        "- Cette section compare les mêmes périodes contre des benchmarks simples; elle n’influence aucune allocation.",
        "- `SIMPLE_MOMENTUM` sélectionne seulement avec l’historique disponible avant la date de décision.",
        "",
        _markdown_table(display_benchmarks, [
            "analysis_date",
            "next_analysis_date",
            "benchmark_id",
            "data_coverage_status",
            "strategy_period_return",
            "benchmark_period_return",
            "model_excess_return_vs_benchmark",
            "win_loss_vs_benchmark",
            "unavailable_reason",
        ]),
        "",
        "## Inventaire récent",
        "",
        _markdown_table(_compact_inventory_rows(inventory_rows), [
            "analysis_date",
            "allocation_count",
            "allocated_tickers",
            "next_analysis_date",
            "days_to_next",
            "usable_for_walk_forward",
            "exclusion_reason",
        ]),
        "",
        "## Garde-fous",
        "",
        f"- Période minimale: {config.min_days_between_points} jours.",
        f"- Périodes recommandées avant que l’évidence quitte son état le plus jeune: {config.recommended_min_periods}; ce seuil ne prouve ni alpha ni skill.",
        f"- Poids maximal avec prix manquant pour garder une simulation partielle: {pct(config.max_missing_allocation_weight, 0)}.",
        "- Aucune suggestion d’achat, de vente ou d’auto-tuning n’est déclenchée par ce bloc seul.",
        "",
    ]
    return "\n".join(lines)


def _latest_daily_payloads(history_dir: Path, kind: str, mode: str) -> dict[str, dict[str, Any]]:
    if kind not in {"analysis", "allocation"}:
        return {}
    selected: dict[str, dict[str, Any]] = {}
    if not history_dir.exists():
        return selected
    for path in history_dir.glob(f"{kind}_*.json"):
        payload = load_json(path)
        if not isinstance(payload, dict):
            continue
        if not _payload_mode_matches(payload, mode):
            continue
        rows_key = "analyses" if kind == "analysis" else "allocations"
        rows = payload.get(rows_key)
        if not isinstance(rows, list) or not rows:
            continue
        analysis_date = _payload_date(payload, path)
        if not analysis_date:
            continue
        created_at = str(payload.get("created_at") or path.stem)
        purpose = snapshot_run_purpose(payload)
        current = selected.get(analysis_date)
        candidate_rank = (_purpose_selection_rank(purpose), created_at)
        current_rank = (
            _purpose_selection_rank(current.get("run_purpose")) if current else -1,
            str(current.get("created_at") or "") if current else "",
        )
        if current and current_rank >= candidate_rank:
            continue
        selected[analysis_date] = {
            "path": str(path),
            "created_at": created_at,
            "analysis_date": analysis_date,
            "model_rules_version": str(payload.get("model_rules_version") or ""),
            "analysis_mode": _normalize_mode(payload.get("analysis_mode")),
            "run_purpose": purpose,
            "run_purpose_status": "EXPLICIT" if str(payload.get("run_purpose") or "").strip() else "LEGACY_UNCERTAINTY",
            "rows": rows,
        }
    return selected


def _inventory_row(
    analysis_date: str,
    analysis_payload: dict[str, Any],
    allocation_payload: dict[str, Any],
    next_date: str,
    days_to_next: int | None,
    config: WalkForwardInventoryConfig,
) -> dict[str, Any]:
    analysis_rows = analysis_payload.get("rows") if isinstance(analysis_payload.get("rows"), list) else []
    allocation_rows = allocation_payload.get("rows") if isinstance(allocation_payload.get("rows"), list) else []
    allocated = _allocated_tickers(allocation_rows)
    top_ticker, top_pct = _top_allocation(allocation_rows)
    vfv_pct = _allocation_pct(allocation_rows, "VFV.TO")
    run_purpose, purpose_status = combined_snapshot_purpose([analysis_payload, allocation_payload])
    exclusion = _exclusion_reason(analysis_payload, allocation_payload, next_date, days_to_next, config)
    return {
        "mode": config.mode,
        "evidence_class": EvidenceClass.POINT_IN_TIME_WALK_FORWARD.value,
        "analysis_date": analysis_date,
        "created_at": analysis_payload.get("created_at") or allocation_payload.get("created_at") or "",
        "model_rules_version": analysis_payload.get("model_rules_version") or allocation_payload.get("model_rules_version") or "",
        "run_purpose": run_purpose,
        "run_purpose_status": purpose_status,
        "primary_timeline_eligible": False,
        "eligibility_basis": "",
        "analysis_snapshot_path": analysis_payload.get("path", ""),
        "allocation_snapshot_path": allocation_payload.get("path", ""),
        "analysis_row_count": len(analysis_rows),
        "core_position_count": _core_position_count(analysis_rows),
        "allocation_count": len(allocation_rows),
        "allocated_tickers": ", ".join(allocated),
        "vfv_allocation_percent": round(vfv_pct, 4),
        "top_allocation_ticker": top_ticker,
        "top_allocation_percent": round(top_pct, 4),
        "next_analysis_date": next_date,
        "days_to_next": days_to_next if days_to_next is not None else "",
        "usable_for_walk_forward": not exclusion,
        "exclusion_reason": exclusion,
    }


def _primary_timeline_dates(
    rows: list[dict[str, Any]],
    config: WalkForwardInventoryConfig,
) -> tuple[list[str], dict[str, str]]:
    selected: list[str] = []
    basis: dict[str, str] = {}
    explicit_dates = [
        str(row.get("analysis_date") or "")
        for row in rows
        if purpose_is_walk_forward_decision(row.get("run_purpose"))
    ]
    for row in rows:
        analysis_date = str(row.get("analysis_date") or "")
        purpose = str(row.get("run_purpose") or "")
        if purpose_is_walk_forward_decision(purpose):
            selected.append(analysis_date)
            basis[analysis_date] = "EXPLICIT_DECISION_PURPOSE"
            continue
        if purpose != RunPurpose.UNKNOWN_LEGACY.value:
            continue
        previous_date = selected[-1] if selected else ""
        next_explicit = next((item for item in explicit_dates if item > analysis_date), "")
        far_enough_from_previous = not previous_date or (_days_between(previous_date, analysis_date) or 0) >= config.min_days_between_points
        far_enough_from_next_explicit = not next_explicit or (_days_between(analysis_date, next_explicit) or 0) >= config.min_days_between_points
        if far_enough_from_previous and far_enough_from_next_explicit:
            selected.append(analysis_date)
            basis[analysis_date] = "LEGACY_PARTIALLY_RECOVERABLE"
    return sorted(set(selected)), basis


def _purpose_selection_rank(value: Any) -> int:
    purpose = str(value or "")
    if purpose_is_walk_forward_decision(purpose):
        return 3
    if purpose == RunPurpose.UNKNOWN_LEGACY.value:
        return 2
    return 1


def _exclusion_reason(
    analysis_payload: dict[str, Any],
    allocation_payload: dict[str, Any],
    next_date: str,
    days_to_next: int | None,
    config: WalkForwardInventoryConfig,
) -> str:
    if not analysis_payload:
        return "MISSING_ANALYSIS_SNAPSHOT"
    if not allocation_payload:
        return "MISSING_ALLOCATION_SNAPSHOT"
    if not next_date:
        return "OPEN_PERIOD_NO_NEXT_ANALYSIS_YET"
    if days_to_next is None or days_to_next < config.min_days_between_points:
        return f"PERIOD_TOO_SHORT_UNDER_{config.min_days_between_points}_DAYS"
    return ""


def _payload_mode_matches(payload: dict[str, Any], mode: str) -> bool:
    return _normalize_mode(payload.get("analysis_mode")) == _normalize_mode(mode)


def _normalize_mode(value: Any) -> str:
    return str(value or "").strip().lower()


def _payload_date(payload: dict[str, Any], path: Path) -> str:
    analysis_date = str(payload.get("analysis_date") or "").strip()
    if analysis_date:
        return analysis_date[:10]
    created_at = str(payload.get("created_at") or "").strip()
    if created_at:
        return created_at[:10]
    return _date_from_path(path)


def _date_from_path(path: Path) -> str:
    for part in path.stem.split("_"):
        if len(part) == 8 and part.isdigit():
            return f"{part[:4]}-{part[4:6]}-{part[6:8]}"
    return ""


def _days_between(start: str, end: str) -> int | None:
    try:
        return (date.fromisoformat(end[:10]) - date.fromisoformat(start[:10])).days
    except ValueError:
        return None


def _allocated_tickers(rows: list[dict[str, Any]]) -> list[str]:
    tickers = []
    for row in rows:
        ticker = str(row.get("ticker") or row.get("destination") or "").strip().upper()
        amount = safe_float(row.get("amount", row.get("montant"))) or 0.0
        if ticker and amount > 0:
            tickers.append(ticker)
    return tickers


def _top_allocation(rows: list[dict[str, Any]]) -> tuple[str, float]:
    top_ticker = ""
    top_pct = 0.0
    for row in rows:
        ticker = str(row.get("ticker") or row.get("destination") or "").strip().upper()
        if ticker == "VFV.TO":
            continue
        pct = safe_float(row.get("percentage", row.get("pourcentage"))) or 0.0
        if pct > top_pct:
            top_ticker = ticker
            top_pct = pct
    return top_ticker, top_pct


def _allocation_pct(rows: list[dict[str, Any]], ticker: str) -> float:
    target = ticker.upper()
    for row in rows:
        row_ticker = str(row.get("ticker") or row.get("destination") or "").strip().upper()
        if row_ticker == target:
            return safe_float(row.get("percentage", row.get("pourcentage"))) or 0.0
    return 0.0


def _core_position_count(rows: list[dict[str, Any]]) -> int:
    return sum(1 for row in rows if str(row.get("universe") or "") == "CORE_PORTFOLIO")


def _coverage_status(usable_count: int, recommended_min_periods: int) -> str:
    if usable_count <= 0:
        return "INSUFFICIENT_HISTORY"
    if usable_count < max(2, recommended_min_periods // 2):
        return "EARLY_SIGNAL_ONLY"
    if usable_count < recommended_min_periods:
        return "BUILDING_HISTORY"
    return "READY_FOR_WALK_FORWARD_SIMULATION"


def _coverage_interpretation(status: str, usable_count: int, recommended_min_periods: int) -> str:
    if status == "READY_FOR_WALK_FORWARD_SIMULATION":
        return "Historique local suffisant pour démarrer une simulation walk-forward informative."
    if status == "BUILDING_HISTORY":
        return f"{usable_count} période(s) utilisable(s): utile pour observation, encore court pour tirer une conclusion forte."
    if status == "EARLY_SIGNAL_ONLY":
        return f"{usable_count} période(s) utilisable(s): signal très préliminaire seulement."
    return "Pas encore assez de snapshots analyse + allocation espacés pour tester les décisions hors-échantillon."


def _compact_inventory_rows(rows: list[dict[str, Any]], limit: int = 30) -> list[dict[str, Any]]:
    selected = sorted(rows, key=lambda row: str(row.get("analysis_date") or ""), reverse=True)
    return selected[:limit] or [
        {
            "analysis_date": "",
            "created_at": "",
            "allocation_count": "",
            "allocated_tickers": "",
            "next_analysis_date": "",
            "days_to_next": "",
            "usable_for_walk_forward": False,
            "exclusion_reason": "Aucun snapshot historique trouvé pour ce mode.",
        }
    ]


def _truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value or "").strip().lower() in {"true", "1", "yes", "oui"}


def _walk_forward_price_tickers(usable_rows: list[dict[str, Any]]) -> list[str]:
    tickers = {"VFV.TO"}
    for row in usable_rows:
        payload = load_json(row.get("allocation_snapshot_path") or "")
        allocations = payload.get("allocations") if isinstance(payload.get("allocations"), list) else []
        tickers.update(_allocation_weights(allocations))
    return sorted(ticker for ticker in tickers if ticker)


def _walk_forward_price_years(usable_rows: list[dict[str, Any]]) -> int:
    dates = []
    for row in usable_rows:
        for key in ("analysis_date", "next_analysis_date"):
            value = str(row.get(key) or "")[:10]
            try:
                dates.append(date.fromisoformat(value))
            except ValueError:
                continue
    if len(dates) < 2:
        return 1
    days = max(1, (max(dates) - min(dates)).days)
    return max(1, min(15, int(days / 365) + 2))


def _simulate_single_walk_forward_period(
    row: dict[str, Any],
    prices: pd.DataFrame,
    config: WalkForwardInventoryConfig,
) -> dict[str, list[dict[str, Any]] | dict[str, Any]]:
    analysis_date = str(row.get("analysis_date") or "")[:10]
    next_date = str(row.get("next_analysis_date") or "")[:10]
    allocation_payload = load_json(row.get("allocation_snapshot_path") or "")
    allocation_rows = allocation_payload.get("allocations") if isinstance(allocation_payload.get("allocations"), list) else []
    weights = _allocation_weights(allocation_rows)
    trade_values = _allocation_trade_values(allocation_rows, weights)
    allocation_return_rows: list[dict[str, Any]] = []

    if not weights:
        return {
            "period_row": _period_error_row(row, "NO_POSITIVE_ALLOCATION", "Aucune allocation positive à tester."),
            "allocation_return_rows": allocation_return_rows,
        }

    vfv_result = _ticker_period_return(prices, "VFV.TO", analysis_date, next_date)
    if vfv_result is None:
        return {
            "period_row": _period_error_row(row, "BENCHMARK_PRICE_MISSING", "Prix VFV.TO manquant pour cette période."),
            "allocation_return_rows": allocation_return_rows,
        }

    strategy_return = 0.0
    missing_tickers: list[str] = []
    missing_weight = 0.0
    start_dates: list[str] = [vfv_result["start_date"]]
    end_dates: list[str] = [vfv_result["end_date"]]

    for ticker, weight in weights.items():
        ticker_result = _ticker_period_return(prices, ticker, analysis_date, next_date)
        if ticker_result is None:
            missing_tickers.append(ticker)
            missing_weight += weight
            allocation_return_rows.append(
                _allocation_return_row(config, row, ticker, weight, "", "", "", 0.0, "MISSING_PRICE", trade_values.get(ticker))
            )
            continue
        contribution = weight * ticker_result["return"]
        strategy_return += contribution
        start_dates.append(ticker_result["start_date"])
        end_dates.append(ticker_result["end_date"])
        allocation_return_rows.append(
            _allocation_return_row(
                config,
                row,
                ticker,
                weight,
                ticker_result["start_price"],
                ticker_result["end_price"],
                ticker_result["return"],
                contribution,
                "OK",
                trade_values.get(ticker),
            )
        )

    days_held = _days_between(min(start_dates), max(end_dates)) or (safe_float(row.get("days_to_next")) or 0)
    evaluation_status = "SIMULATED"
    notes = "Simulation hors-échantillon basée sur l’allocation recommandée à cette date."
    if missing_weight > config.max_missing_allocation_weight:
        evaluation_status = "PRICE_DATA_TOO_INCOMPLETE"
        notes = "Poids trop élevé sans prix historique; période exclue du résumé."
    elif missing_weight > 0:
        evaluation_status = "SIMULATED_WITH_PARTIAL_PRICE_DATA"
        notes = "Petit poids sans prix traité prudemment comme rendement 0 %."

    vfv_return = vfv_result["return"]
    market_regime, regime_note = _classify_walk_forward_regime(vfv_return, days_held)
    return {
        "period_row": {
            "mode": config.mode,
            "evidence_class": EvidenceClass.POINT_IN_TIME_WALK_FORWARD.value,
            "run_purpose": row.get("run_purpose", RunPurpose.UNKNOWN_LEGACY.value),
            "model_rules_version": row.get("model_rules_version", ""),
            "analysis_date": analysis_date,
            "next_analysis_date": next_date,
            "days_held": int(days_held) if days_held else "",
            "start_price_date": min(start_dates),
            "end_price_date": max(end_dates),
            "allocation_count": len(weights),
            "allocated_tickers": ", ".join(weights),
            "strategy_period_return": round(strategy_return, 4),
            "vfv_period_return": round(vfv_return, 4),
            "excess_return_vs_vfv": round(strategy_return - vfv_return, 4),
            "strategy_annualized_return": _annualized_return(strategy_return, days_held),
            "vfv_annualized_return": _annualized_return(vfv_return, days_held),
            "market_regime": market_regime,
            "regime_note": regime_note,
            "missing_price_tickers": ", ".join(missing_tickers),
            "missing_allocation_weight": round(missing_weight, 4),
            "evaluation_status": evaluation_status,
            "notes": notes,
        },
        "allocation_return_rows": allocation_return_rows,
    }


def _allocation_weights(rows: list[dict[str, Any]]) -> dict[str, float]:
    amount_values: list[tuple[str, float]] = []
    percent_values: list[tuple[str, float]] = []
    for row in rows:
        ticker = str(row.get("ticker") or row.get("destination") or "").strip().upper()
        if not ticker:
            continue
        amount = safe_float(row.get("amount", row.get("montant")))
        percentage = safe_float(row.get("percentage", row.get("pourcentage")))
        if amount is not None and amount > 0:
            amount_values.append((ticker, amount))
        elif percentage is not None and percentage > 0:
            percent_values.append((ticker, percentage))

    source_values = amount_values if amount_values else percent_values
    totals: dict[str, float] = {}
    for ticker, value in source_values:
        totals[ticker] = totals.get(ticker, 0.0) + value
    total = sum(totals.values())
    if total <= 0:
        return {}
    return {ticker: value / total for ticker, value in totals.items() if value > 0}


def _allocation_trade_values(rows: list[dict[str, Any]], weights: dict[str, float]) -> dict[str, float]:
    values: dict[str, float] = {}
    for row in rows:
        ticker = str(row.get("ticker") or row.get("destination") or "").strip().upper()
        amount = safe_float(row.get("amount", row.get("montant")))
        if ticker and amount is not None and amount > 0:
            values[ticker] = values.get(ticker, 0.0) + amount
    return values


def _ticker_period_return(prices: pd.DataFrame, ticker: str, start_date: str, end_date: str) -> dict[str, Any] | None:
    if ticker not in prices.columns:
        return None
    start = _price_on_or_after(prices[ticker], start_date)
    end = _price_on_or_before(prices[ticker], end_date)
    if start is None or end is None:
        return None
    start_idx, start_price = start
    end_idx, end_price = end
    if end_idx <= start_idx or start_price <= 0 or end_price <= 0:
        return None
    return {
        "start_date": start_idx.date().isoformat(),
        "end_date": end_idx.date().isoformat(),
        "start_price": start_price,
        "end_price": end_price,
        "return": end_price / start_price - 1.0,
    }


def _price_on_or_after(series: pd.Series, target_date: str) -> tuple[pd.Timestamp, float] | None:
    try:
        target = pd.Timestamp(target_date)
    except Exception:
        return None
    clean = series.dropna()
    clean = clean[clean.index >= target]
    if clean.empty:
        return None
    value = safe_float(clean.iloc[0])
    if value is None:
        return None
    return clean.index[0], value


def _price_on_or_before(series: pd.Series, target_date: str) -> tuple[pd.Timestamp, float] | None:
    try:
        target = pd.Timestamp(target_date)
    except Exception:
        return None
    clean = series.dropna()
    clean = clean[clean.index <= target]
    if clean.empty:
        return None
    value = safe_float(clean.iloc[-1])
    if value is None:
        return None
    return clean.index[-1], value


def _allocation_return_row(
    config: WalkForwardInventoryConfig,
    period_row: dict[str, Any],
    ticker: str,
    weight: float,
    start_price: Any,
    end_price: Any,
    period_return: Any,
    contribution: float,
    price_status: str,
    trade_value_cad: Any = "",
) -> dict[str, Any]:
    return {
        "mode": config.mode,
        "analysis_date": period_row.get("analysis_date", ""),
        "next_analysis_date": period_row.get("next_analysis_date", ""),
        "ticker": ticker,
        "allocation_weight": round(weight, 4),
        "start_price": round(start_price, 4) if isinstance(start_price, (int, float)) else "",
        "end_price": round(end_price, 4) if isinstance(end_price, (int, float)) else "",
        "period_return": round(period_return, 4) if isinstance(period_return, (int, float)) else "",
        "weighted_return_contribution": round(contribution, 4),
        "trade_value_cad": round(trade_value_cad, 2) if isinstance(trade_value_cad, (int, float)) else "",
        "price_status": price_status,
    }


def _simulation_error_row(config: WalkForwardInventoryConfig, message: str) -> dict[str, Any]:
    return {
        "mode": config.mode,
        "evidence_class": EvidenceClass.POINT_IN_TIME_WALK_FORWARD.value,
        "run_purpose": "",
        "model_rules_version": "",
        "analysis_date": "",
        "next_analysis_date": "",
        "days_held": "",
        "start_price_date": "",
        "end_price_date": "",
        "allocation_count": "",
        "allocated_tickers": "",
        "strategy_period_return": "",
        "vfv_period_return": "",
        "excess_return_vs_vfv": "",
        "strategy_annualized_return": "",
        "vfv_annualized_return": "",
        "market_regime": "",
        "regime_note": "",
        "missing_price_tickers": "",
        "missing_allocation_weight": "",
        "evaluation_status": "SIMULATION_ERROR",
        "notes": message,
    }


def _period_error_row(row: dict[str, Any], status: str, message: str) -> dict[str, Any]:
    return {
        "mode": row.get("mode", ""),
        "evidence_class": EvidenceClass.POINT_IN_TIME_WALK_FORWARD.value,
        "run_purpose": row.get("run_purpose", RunPurpose.UNKNOWN_LEGACY.value),
        "model_rules_version": row.get("model_rules_version", ""),
        "analysis_date": row.get("analysis_date", ""),
        "next_analysis_date": row.get("next_analysis_date", ""),
        "days_held": row.get("days_to_next", ""),
        "start_price_date": "",
        "end_price_date": "",
        "allocation_count": row.get("allocation_count", ""),
        "allocated_tickers": row.get("allocated_tickers", ""),
        "strategy_period_return": "",
        "vfv_period_return": "",
        "excess_return_vs_vfv": "",
        "strategy_annualized_return": "",
        "vfv_annualized_return": "",
        "market_regime": "",
        "regime_note": "",
        "missing_price_tickers": "",
        "missing_allocation_weight": "",
        "evaluation_status": status,
        "notes": message,
    }


def _annualized_return(period_return: float, days_held: float | int | None) -> float | str:
    days = safe_float(days_held)
    if days is None or days <= 0 or 1.0 + period_return <= 0:
        return ""
    return round((1.0 + period_return) ** (365.0 / days) - 1.0, 4)


def _classify_walk_forward_regime(vfv_return: float, days_held: float | int | None) -> tuple[str, str]:
    days = safe_float(days_held) or 0.0
    if vfv_return <= -0.08:
        return "VFV_STRESS_DOWN", f"VFV a baissé de {pct(vfv_return, 1)} sur environ {int(days)} jours."
    if vfv_return <= -0.02:
        return "VFV_WEAK", f"VFV a reculé de {pct(vfv_return, 1)} sur environ {int(days)} jours."
    if vfv_return >= 0.08:
        return "VFV_STRONG_RALLY", f"VFV a fortement monté de {pct(vfv_return, 1)} sur environ {int(days)} jours."
    if vfv_return >= 0.02:
        return "VFV_POSITIVE", f"VFV a progressé de {pct(vfv_return, 1)} sur environ {int(days)} jours."
    return "VFV_FLAT", f"VFV est resté relativement stable ({pct(vfv_return, 1)}) sur environ {int(days)} jours."


def _average(values: list[float]) -> float | str:
    if not values:
        return ""
    return round(sum(values) / len(values), 4)


def _compound_returns(values: list[float]) -> float | str:
    if not values:
        return ""
    total = 1.0
    for value in values:
        total *= 1.0 + value
    return round(total - 1.0, 4)


def _regime_status(regime_periods: list[dict[str, Any]], compounded_excess: Any, win_rate: Any) -> str:
    period_count = len(regime_periods)
    if period_count <= 1:
        return "OBSERVE_ONLY"
    excess = safe_float(compounded_excess)
    win = safe_float(win_rate)
    if excess is not None and excess < -0.04 and win is not None and win <= 0.35:
        return "WEAK"
    if excess is not None and excess < -0.015:
        return "WATCH"
    if excess is not None and excess >= -0.01:
        return "OK"
    return "OBSERVE_ONLY"


def _regime_interpretation(status: str, regime: str, period_count: int) -> str:
    if status == "WEAK":
        return f"{period_count} période(s) dans {regime}; le modèle a nettement moins bien fait que VFV dans ce régime."
    if status == "WATCH":
        return f"{period_count} période(s) dans {regime}; résultat mitigé à surveiller avant tout auto-tuning."
    if status == "OK":
        return f"{period_count} période(s) dans {regime}; aucun signal de faiblesse net vs VFV."
    return f"{period_count} période(s) dans {regime}; historique trop mince pour conclure."


def _regime_coverage_status(regime_rows: list[dict[str, Any]], simulated_count: int, recommended_min_periods: int) -> str:
    if simulated_count <= 0:
        return "NO_REGIME_EVIDENCE"
    if simulated_count < max(2, recommended_min_periods // 2):
        return "EARLY_SINGLE_SIGNAL"
    regime_count = len(regime_rows)
    weak_count = sum(1 for row in regime_rows if str(row.get("regime_status") or "") == "WEAK")
    watch_count = sum(1 for row in regime_rows if str(row.get("regime_status") or "") == "WATCH")
    if simulated_count < recommended_min_periods:
        return "LIMITED_HISTORY"
    if regime_count <= 1:
        return "SINGLE_REGIME_ONLY"
    if weak_count:
        return "HAS_WEAK_REGIME"
    if watch_count:
        return "MIXED_REGIME_RESULTS"
    return "MULTI_REGIME_SUPPORTIVE"


def _simulation_status(simulated_count: int, usable_count: int, recommended_min_periods: int) -> str:
    if usable_count <= 0:
        return "NO_USABLE_PERIODS"
    if simulated_count <= 0:
        return "NO_SIMULATED_PERIODS"
    if simulated_count < max(2, recommended_min_periods // 2):
        return "EARLY_SIGNAL_ONLY"
    if simulated_count < recommended_min_periods:
        return "PRELIMINARY_WALK_FORWARD"
    return "READY_FOR_WALK_FORWARD_REVIEW"


def _simulation_interpretation(status: str, simulated_count: int, recommended_min_periods: int) -> str:
    if status == "READY_FOR_WALK_FORWARD_REVIEW":
        return "Assez de périodes simulées pour commencer une revue walk-forward informative, sans auto-tuning agressif."
    if status == "PRELIMINARY_WALK_FORWARD":
        return f"{simulated_count} période(s) simulée(s): utile pour observation, encore trop court pour conclure fortement."
    if status == "EARLY_SIGNAL_ONLY":
        return f"{simulated_count} période(s) simulée(s): signal très préliminaire seulement."
    if status == "NO_SIMULATED_PERIODS":
        return "Des périodes existent, mais les prix disponibles ne permettent pas encore de les simuler correctement."
    return "Aucune période walk-forward utilisable pour l’instant."


def _display_simulation_summary(row: dict[str, Any]) -> dict[str, Any]:
    percent_fields = {
        "avg_strategy_period_return",
        "avg_vfv_period_return",
        "avg_excess_return_vs_vfv",
        "win_rate_vs_vfv",
        "compounded_strategy_return",
        "compounded_vfv_return",
        "compounded_excess_return_vs_vfv",
        "gross_return",
        "net_return_after_friction",
        "friction_drag",
    }
    display = dict(row)
    for field in percent_fields:
        display[field] = pct(safe_float(row.get(field)), 2)
    if safe_float(row.get("estimated_transaction_cost_cad")) is not None:
        display["estimated_transaction_cost_cad"] = f"{safe_float(row.get('estimated_transaction_cost_cad')):.2f} $"
    return display


def _display_period_row(row: dict[str, Any]) -> dict[str, Any]:
    display = dict(row)
    for field in [
        "strategy_period_return",
        "vfv_period_return",
        "excess_return_vs_vfv",
        "net_strategy_period_return_after_friction",
        "friction_drag",
    ]:
        display[field] = pct(safe_float(row.get(field)), 2)
    if safe_float(row.get("estimated_transaction_cost_cad")) is not None:
        display["estimated_transaction_cost_cad"] = f"{safe_float(row.get('estimated_transaction_cost_cad')):.2f} $"
    return display


def _display_regime_row(row: dict[str, Any]) -> dict[str, Any]:
    display = dict(row)
    for field in [
        "avg_strategy_period_return",
        "avg_vfv_period_return",
        "avg_excess_return_vs_vfv",
        "win_rate_vs_vfv",
        "compounded_excess_return_vs_vfv",
    ]:
        display[field] = pct(safe_float(row.get(field)), 2)
    return display


def _display_walk_forward_benchmark_row(row: dict[str, Any]) -> dict[str, Any]:
    display = dict(row)
    for field in ["strategy_period_return", "benchmark_period_return", "model_excess_return_vs_benchmark"]:
        display[field] = pct(safe_float(row.get(field)), 2)
    return display


def _markdown_table(rows: list[dict[str, Any]], columns: list[str]) -> str:
    if not rows:
        rows = [{column: "" for column in columns}]
    header = "| " + " | ".join(columns) + " |"
    separator = "| " + " | ".join(["---"] * len(columns)) + " |"
    body = ["| " + " | ".join(_cell(row.get(column)) for column in columns) + " |" for row in rows]
    return "\n".join([header, separator, *body])


def _cell(value: Any) -> str:
    return str(value if value is not None else "").replace("\n", " ").replace("|", "/")
