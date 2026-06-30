from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime
from pathlib import Path
from typing import Any

from .backtest_engine import run_backtests_from_latest_reports
from .model_audit_engine import run_model_audit
from .source_health_engine import SOURCE_HEALTH_COLUMNS, source_health_audit_context
from .ticker_source_audit_engine import (
    TICKER_SOURCE_AUDIT_COLUMNS,
    build_ticker_source_audit_context,
    ticker_source_audit_rows,
)
from .transaction_friction_engine import BACKTEST_FRICTION_AUDIT_COLUMNS
from .underperformance_engine import UNDERPERFORMANCE_COLUMNS, build_underperformance_attribution
from .utils import DATA_DIR, DISCLAIMER, REPORTS_DIR, markdown_to_html, money, pct, read_csv_records, safe_float, write_csv_records, write_text
from .walk_forward_backtest_engine import run_walk_forward_backtest


FULL_AUDIT_COLUMNS = [
    "section",
    "metric",
    "status",
    "value",
    "interpretation",
    "impact",
]

WEAKEST_CORE_AUDIT_FULL_COLUMNS = [
    "audit_status",
    "current_weakest_ticker",
    "candidate_weakest_ticker",
    "same_result",
    "current_reason",
    "candidate_reason",
    "interpretation",
]

BACKTEST_FRICTION_FULL_COLUMNS = [
    "audit_scope",
    "mode",
    "period_years",
    "analysis_date",
    "next_analysis_date",
    "gross_return",
    "estimated_transaction_cost_cad",
    "net_return_after_friction",
    "friction_drag",
    "friction_assumption_status",
    "interpretation",
]

DEFAULT_AUDIT_MONTHLY_CAPITAL = 500.0


def run_full_audit(
    reports_dir: str | Path = REPORTS_DIR,
    data_dir: str | Path = DATA_DIR,
    *,
    period: str = "all",
    years: list[int] | None = None,
    mode: str = "high-cagr",
    monthly_capital: float | None = None,
    refresh_market_data: bool = False,
) -> dict[str, Any]:
    reports_dir = Path(reports_dir)
    data_dir = Path(data_dir)
    years = sorted(set(years or [5, 10]))

    contribution = estimate_monthly_contribution(data_dir)
    selected_monthly_capital = (
        float(monthly_capital)
        if monthly_capital is not None and monthly_capital > 0
        else float(contribution["monthly_capital"])
    )

    model_audit = run_model_audit(reports_dir, period=period, mode=mode)
    account_performance_rows = read_csv_records(reports_dir / "latest_account_performance_vs_sp500.csv")
    source_health_rows = read_csv_records(reports_dir / "latest_source_health.csv")
    weakest_core_audit_rows = read_csv_records(reports_dir / "latest_weakest_core_audit.csv")
    ticker_source_context = build_ticker_source_audit_context(
        ticker_memory_rows=read_csv_records(reports_dir / "latest_ticker_memory.csv"),
        source_conflict_rows=read_csv_records(reports_dir / "latest_source_conflicts.csv"),
        ticker_issue_rows=read_csv_records(reports_dir / "latest_ticker_issues.csv"),
    )

    backtest_result: dict[str, Any] = {}
    backtest_error = ""
    try:
        backtest_result = run_backtests_from_latest_reports(
            reports_dir=reports_dir,
            data_dir=data_dir,
            years=years,
            monthly_capital=selected_monthly_capital,
            mode=mode,
            refresh_market_data=refresh_market_data,
        )
    except Exception as exc:  # pragma: no cover - exercised through CLI in real use
        backtest_error = str(exc)

    walk_forward_result: dict[str, Any] = {}
    walk_forward_error = ""
    try:
        walk_forward_result = run_walk_forward_backtest(
            reports_dir=reports_dir,
            data_dir=data_dir,
            mode=mode,
            refresh_market_data=refresh_market_data,
        )
    except Exception as exc:  # pragma: no cover - exercised through CLI in real use
        walk_forward_error = str(exc)

    backtest_friction_rows = [
        *(backtest_result.get("friction_rows") or []),
        *(walk_forward_result.get("friction_rows") or []),
    ]
    write_csv_records(reports_dir / "latest_backtest_friction_audit.csv", backtest_friction_rows, BACKTEST_FRICTION_AUDIT_COLUMNS)

    metrics = build_full_audit_metrics(
        model_audit=model_audit,
        backtest_result=backtest_result,
        backtest_error=backtest_error,
        walk_forward_result=walk_forward_result,
        walk_forward_error=walk_forward_error,
        account_performance_rows=account_performance_rows,
        contribution_estimate=contribution,
        selected_monthly_capital=selected_monthly_capital,
        period=period,
        years=years,
        mode=mode,
        source_health_rows=source_health_rows,
        ticker_source_context=ticker_source_context,
    )
    rows = build_full_audit_rows(metrics)
    markdown = build_full_audit_markdown(
        metrics,
        rows,
        model_audit,
        backtest_result,
        walk_forward_result,
        account_performance_rows,
        source_health_rows,
        ticker_source_context,
        weakest_core_audit_rows,
        backtest_friction_rows,
    )
    audit = {
        "metrics": metrics,
        "rows": rows,
        "markdown": markdown,
        "model_audit": model_audit,
        "backtest_result": backtest_result,
        "walk_forward_result": walk_forward_result,
        "account_performance_rows": account_performance_rows,
        "source_health_rows": source_health_rows,
        "ticker_source_context": ticker_source_context,
        "weakest_core_audit_rows": weakest_core_audit_rows,
        "backtest_friction_rows": backtest_friction_rows,
    }
    write_full_audit_outputs(reports_dir, audit)
    return audit


def estimate_monthly_contribution(
    data_dir: str | Path = DATA_DIR,
    *,
    fallback_monthly_capital: float = DEFAULT_AUDIT_MONTHLY_CAPITAL,
) -> dict[str, Any]:
    data_dir = Path(data_dir)
    flows = _detected_external_flows(data_dir)
    if not flows:
        return {
            "monthly_capital": fallback_monthly_capital,
            "detected_monthly_capital": "",
            "total_detected_contributions": 0.0,
            "positive_flow_count": 0,
            "positive_flow_month_count": 0,
            "first_flow_date": "",
            "last_flow_date": "",
            "source": "DEFAULT_INSUFFICIENT_HISTORY",
            "confidence": "LOW",
            "interpretation": "Aucune cotisation externe exploitable détectée; l’audit utilise 500 $/mois par défaut.",
        }

    monthly_totals: dict[str, float] = defaultdict(float)
    dates: list[date] = []
    for flow_date, amount in flows:
        month_key = flow_date.strftime("%Y-%m")
        monthly_totals[month_key] += amount
        dates.append(flow_date)

    first = min(dates)
    last = max(dates)
    elapsed_months = max(1, _month_span(first, last))
    total = sum(amount for _, amount in flows)
    monthly_average = total / elapsed_months
    positive_months = sum(1 for amount in monthly_totals.values() if amount > 0)
    confidence = _contribution_confidence(positive_months, (last - first).days)
    return {
        "monthly_capital": round(monthly_average, 2),
        "detected_monthly_capital": round(monthly_average, 2),
        "total_detected_contributions": round(total, 2),
        "positive_flow_count": len(flows),
        "positive_flow_month_count": positive_months,
        "first_flow_date": first.isoformat(),
        "last_flow_date": last.isoformat(),
        "source": "DETECTED_EXTERNAL_FLOWS",
        "confidence": confidence,
        "interpretation": (
            f"Cotisation mensuelle moyenne estimée à partir de {positive_months} mois avec flux positif "
            f"sur {elapsed_months} mois civils observés."
        ),
    }


def build_full_audit_metrics(
    *,
    model_audit: dict[str, Any],
    backtest_result: dict[str, Any],
    backtest_error: str,
    walk_forward_result: dict[str, Any] | None = None,
    walk_forward_error: str = "",
    account_performance_rows: list[dict[str, Any]],
    contribution_estimate: dict[str, Any],
    selected_monthly_capital: float,
    period: str,
    years: list[int],
    mode: str,
    source_health_rows: list[dict[str, Any]] | None = None,
    ticker_source_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    model_metrics = model_audit.get("metrics") or {}
    backtest_summaries = backtest_result.get("summaries") or []
    walk_forward_result = walk_forward_result or {}
    walk_forward_summary = walk_forward_result.get("summary") or {}
    walk_forward_periods = walk_forward_result.get("period_rows") or []
    account_summary = _account_performance_summary(account_performance_rows)

    model_score = safe_float(model_metrics.get("health_score")) or 0.0
    backtest_score = _backtest_score(backtest_summaries, backtest_error)
    walk_forward_score = _walk_forward_score(walk_forward_summary, walk_forward_error)
    realized_score = _realized_performance_score(account_summary)
    source_health = source_health_audit_context(source_health_rows or [])
    ticker_source_context = ticker_source_context or build_ticker_source_audit_context()
    evidence_score = _evidence_score(
        model_metrics,
        backtest_summaries,
        account_summary,
        contribution_estimate,
        source_health,
        ticker_source_context,
        walk_forward_summary,
    )
    underperformance = build_underperformance_attribution(
        model_metrics=model_metrics,
        account_performance_rows=account_performance_rows,
        backtest_summaries=backtest_summaries,
        mode=mode,
    )
    criterion7_score = round(
        0.28 * model_score + 0.25 * backtest_score + 0.12 * walk_forward_score + 0.20 * realized_score + 0.15 * evidence_score,
        1,
    )
    criterion7_status = _criterion7_status(criterion7_score, model_metrics, backtest_error)

    return {
        "date": date.today().isoformat(),
        "period": period,
        "years": years,
        "mode": mode,
        "selected_monthly_capital": round(selected_monthly_capital, 2),
        "contribution_estimate": contribution_estimate,
        "model_health_status": model_metrics.get("health_status", "N/D"),
        "model_health_score": round(model_score, 1),
        "model_confidence": model_metrics.get("confidence", "N/D"),
        "model_sample_count": model_metrics.get("sample_count", 0),
        "model_allocation_sample_count": model_metrics.get("allocation_sample_count", 0),
        "model_span_days": model_metrics.get("span_days", 0),
        "avg_allocation_turnover": model_metrics.get("avg_allocation_turnover", 0.0),
        "avg_vfv": model_metrics.get("avg_vfv", 0.0),
        "avg_core": model_metrics.get("avg_core", 0.0),
        "avg_max_single": model_metrics.get("avg_max_single", 0.0),
        "high_cycle_day_rate": model_metrics.get("high_cycle_day_rate", 0.0),
        "low_data_day_rate": model_metrics.get("low_data_day_rate", 0.0),
        "backtest_status": "UNAVAILABLE" if backtest_error else _backtest_status(backtest_summaries),
        "backtest_score": backtest_score,
        "backtest_error": backtest_error,
        "backtest_summaries": backtest_summaries,
        "walk_forward_status": "UNAVAILABLE" if walk_forward_error else _walk_forward_audit_status(walk_forward_summary),
        "walk_forward_score": walk_forward_score,
        "walk_forward_error": walk_forward_error,
        "walk_forward_summary": walk_forward_summary,
        "walk_forward_periods": walk_forward_periods,
        "realized_performance_status": account_summary.get("status", "UNAVAILABLE"),
        "realized_performance_score": realized_score,
        "account_summary": account_summary,
        "underperformance_attribution": underperformance,
        "evidence_score": evidence_score,
        "source_health": source_health,
        "source_health_status": source_health.get("source_health_status"),
        "source_health_score": source_health.get("source_health_score"),
        "source_health_weakest_source": source_health.get("source_health_weakest_source"),
        "source_health_auto_tuning_gate": source_health.get("source_health_auto_tuning_gate"),
        "ticker_source_quality": ticker_source_context,
        "ticker_source_quality_status": ticker_source_context.get("ticker_source_quality_status"),
        "ticker_source_quality_score": ticker_source_context.get("ticker_source_quality_score"),
        "ticker_source_interpretation": ticker_source_context.get("ticker_source_interpretation"),
        "criterion7_score": criterion7_score,
        "criterion7_status": criterion7_status,
        "criterion7_interpretation": _criterion7_interpretation(criterion7_status),
    }


def build_full_audit_rows(metrics: dict[str, Any]) -> list[dict[str, Any]]:
    contribution = metrics.get("contribution_estimate") or {}
    account = metrics.get("account_summary") or {}
    underperformance = metrics.get("underperformance_attribution") or {}
    rows = [
        _row(
            "Résumé",
            "Intégration du critère 7",
            metrics["criterion7_status"],
            f"{metrics['criterion7_score']:.1f}/100",
            metrics["criterion7_interpretation"],
            "Synthèse de la stabilité, du backtest, de la performance réelle suivie et de la qualité de l’historique.",
        ),
        _row(
            "Cotisation",
            "Capital mensuel utilisé",
            contribution.get("confidence", "LOW"),
            money(safe_float(metrics.get("selected_monthly_capital"))),
            contribution.get("interpretation", ""),
            "Sert seulement au backtest théorique; l’analyse mensuelle normale garde son --capital réel.",
        ),
        _row(
            "Cohérence",
            "Santé du modèle",
            metrics.get("model_health_status", "N/D"),
            f"{safe_float(metrics.get('model_health_score')) or 0:.1f}/100",
            f"{metrics.get('model_allocation_sample_count', 0)} date(s) avec allocation sur {metrics.get('model_span_days', 0)} jour(s).",
            "Vérifie que le modèle ne devient pas trop instable, trop défensif ou trop concentré.",
        ),
        _row(
            "Cohérence",
            "Rotation moyenne des recommandations",
            _rate_status(safe_float(metrics.get("avg_allocation_turnover")) or 0.0, 0.20, 0.45, inverse=True),
            pct(safe_float(metrics.get("avg_allocation_turnover"))),
            "Part moyenne de cotisation qui change de destination entre deux dates d’analyse.",
            "Protège contre les changements causés seulement par du bruit de marché.",
        ),
        _row(
            "Risque",
            "Noyau VFV moyen",
            _vfv_status(safe_float(metrics.get("avg_vfv")) or 0.0),
            pct(safe_float(metrics.get("avg_vfv"))),
            f"Exposition core moyenne: {pct(safe_float(metrics.get('avg_core')))}.",
            "Confirme que VFV sert de noyau/pare-chocs sans tuer le rendement recherché.",
        ),
        _row(
            "Risque",
            "Plus gros bloc moyen",
            _rate_status(safe_float(metrics.get("avg_max_single")) or 0.0, 0.35, 0.55, inverse=True),
            pct(safe_float(metrics.get("avg_max_single"))),
            "Moyenne de la plus grosse allocation individuelle.",
            "Évite de transformer une stratégie high CAGR en pari trop concentré.",
        ),
        _row(
            "Risque",
            "Exposition cycles/bulles",
            _rate_status(safe_float(metrics.get("high_cycle_day_rate")) or 0.0, 0.25, 0.50, inverse=True),
            pct(safe_float(metrics.get("high_cycle_day_rate"))),
            "Fréquence où une recommandation financée portait un risque cycle/bulle élevé.",
            "Vérifie que le modèle ne court pas seulement après le thème chaud du moment.",
        ),
        _row(
            "Backtest",
            "Résultat théorique 5-10 ans",
            metrics.get("backtest_status", "N/D"),
            f"{safe_float(metrics.get('backtest_score')) or 0:.1f}/100",
            _backtest_interpretation(metrics),
            "Teste la mécanique avec des prix historiques gratuits, sans prétendre prédire l’avenir.",
        ),
        _row(
            "Backtest",
            "Walk-forward hors-échantillon",
            metrics.get("walk_forward_status", "N/D"),
            f"{safe_float(metrics.get('walk_forward_score')) or 0:.1f}/100",
            _walk_forward_interpretation(metrics),
            "Teste les recommandations réellement produites dans le passé jusqu’à l’analyse suivante disponible.",
        ),
        _row(
            "Performance réelle",
            "Portefeuille vs S&P 500 local",
            metrics.get("realized_performance_status", "UNAVAILABLE"),
            f"{safe_float(metrics.get('realized_performance_score')) or 0:.1f}/100",
            account.get("interpretation", "Historique réel encore insuffisant ou indisponible."),
            "Construit progressivement une preuve réelle de ta stratégie à chaque analyse.",
        ),
        _row(
            "Attribution",
            "Sous-performance et gouverneur",
            underperformance.get("status", "N/D"),
            underperformance.get("correction_governor", "N/D"),
            underperformance.get("interpretation", ""),
            underperformance.get("guardrail", "Décide si une correction automatique serait prudente ou non."),
        ),
        _row(
            "Données",
            "Qualité de preuve",
            _score_status(safe_float(metrics.get("evidence_score"))),
            f"{safe_float(metrics.get('evidence_score')) or 0:.1f}/100",
            f"Confiance modèle: {metrics.get('model_confidence')}; confiance cotisation: {contribution.get('confidence')}.",
            "Plus l’historique local s’allonge, plus l’audit devient représentatif.",
        ),
        _row(
            "Données",
            "Santé des sources",
            metrics.get("source_health_status", "UNKNOWN"),
            f"{safe_float(metrics.get('source_health_score')) or 0:.1f}/100",
            f"Source la plus faible: {metrics.get('source_health_weakest_source', 'N/D')}; gate tuning: {metrics.get('source_health_auto_tuning_gate', 'N/D')}.",
            "Sert de garde-fou d’audit: n’affecte pas l’allocation mensuelle, mais peut bloquer un auto-tuning si une source centrale est critique.",
        ),
        _row(
            "Données",
            "Qualité tickers et contradictions",
            metrics.get("ticker_source_quality_status", "UNKNOWN"),
            f"{safe_float(metrics.get('ticker_source_quality_score')) or 0:.1f}/100",
            metrics.get("ticker_source_interpretation", "N/D"),
            "Garde-fou informatif: réduit très légèrement la qualité de preuve si un ticker/source prioritaire doit être validé.",
        ),
    ]
    return rows


def build_full_audit_markdown(
    metrics: dict[str, Any],
    rows: list[dict[str, Any]],
    model_audit: dict[str, Any],
    backtest_result: dict[str, Any],
    walk_forward_result: dict[str, Any],
    account_performance_rows: list[dict[str, Any]],
    source_health_rows: list[dict[str, Any]] | None = None,
    ticker_source_context: dict[str, Any] | None = None,
    weakest_core_audit_rows: list[dict[str, Any]] | None = None,
    backtest_friction_rows: list[dict[str, Any]] | None = None,
) -> str:
    model_metrics = model_audit.get("metrics") or {}
    backtest_summaries = backtest_result.get("summaries") or []
    backtest_benchmark_rows = backtest_result.get("benchmark_rows") or []
    walk_forward_summary = (walk_forward_result or {}).get("summary") or metrics.get("walk_forward_summary") or {}
    walk_forward_periods = (walk_forward_result or {}).get("period_rows") or metrics.get("walk_forward_periods") or []
    walk_forward_benchmark_rows = (walk_forward_result or {}).get("benchmark_rows") or []
    threshold = model_metrics.get("threshold_review") or {}
    underperformance = metrics.get("underperformance_attribution") or {}
    ticker_source_context = ticker_source_context or metrics.get("ticker_source_quality") or {}
    weakest_core_audit_rows = _display_weakest_core_audit_rows(weakest_core_audit_rows or [])
    backtest_friction_rows = _display_backtest_friction_rows(backtest_friction_rows or [])
    lines = [
        "# Audit maître du modèle",
        "",
        f"- Date: {metrics.get('date')}",
        f"- Mode audité: {metrics.get('mode')}",
        f"- Période d’audit: {metrics.get('period')}",
        f"- Backtest demandé: {', '.join(str(year) + ' ans' for year in metrics.get('years', []))}",
        f"- Cotisation mensuelle utilisée pour le backtest: {money(safe_float(metrics.get('selected_monthly_capital')))}",
        "",
        f"> {DISCLAIMER}",
        "",
        "## Résumé exécutif",
        "",
        f"- Statut critère 7: **{metrics.get('criterion7_status')}** ({metrics.get('criterion7_score'):.1f}/100)",
        f"- Santé du modèle: **{metrics.get('model_health_status')}** ({metrics.get('model_health_score'):.1f}/100)",
        f"- Backtest: **{metrics.get('backtest_status')}** ({metrics.get('backtest_score'):.1f}/100)",
        f"- Walk-forward: **{metrics.get('walk_forward_status')}** ({metrics.get('walk_forward_score'):.1f}/100)",
        f"- Performance réelle suivie: **{metrics.get('realized_performance_status')}** ({metrics.get('realized_performance_score'):.1f}/100)",
        f"- Santé des sources: **{metrics.get('source_health_status', 'UNKNOWN')}** ({safe_float(metrics.get('source_health_score')) or 0:.1f}/100)",
        f"- Qualité tickers/sources: **{metrics.get('ticker_source_quality_status', 'UNKNOWN')}** ({safe_float(metrics.get('ticker_source_quality_score')) or 0:.1f}/100)",
        f"- Attribution de sous-performance: **{underperformance.get('status', 'N/D')}** / gouverneur **{underperformance.get('correction_governor', 'N/D')}**",
        f"- Conclusion: {metrics.get('criterion7_interpretation')}",
        "",
        "## Tableau maître",
        "",
        _markdown_table(rows, FULL_AUDIT_COLUMNS),
        "",
        "## Cotisation détectée",
        "",
        _markdown_table([metrics.get("contribution_estimate") or {}], [
            "monthly_capital",
            "source",
            "confidence",
            "positive_flow_month_count",
            "total_detected_contributions",
            "first_flow_date",
            "last_flow_date",
            "interpretation",
        ]),
        "",
        "## Backtest théorique",
        "",
        "- Cette partie teste la mécanique actuelle avec prix historiques gratuits. Elle ne reconstruit pas parfaitement les fondamentaux historiques.",
        "",
        _markdown_table(_display_backtest_summaries(backtest_summaries), [
            "period_years",
            "start_date",
            "end_date",
            "total_contributed",
            "final_value",
            "vfv_final_value",
            "excess_value_vs_vfv",
            "price_return_basis",
            "money_weighted_annual_return",
            "max_drawdown_on_capital_multiple",
            "avg_vfv_allocation",
        ]),
        "",
        "### Benchmarks alternatifs du backtest",
        "",
        "- Comparaisons d’audit seulement: elles ne changent pas le score, le sizing ou les recommandations.",
        "",
        _markdown_table(_display_backtest_benchmark_rows(backtest_benchmark_rows), [
            "period_years",
            "benchmark_id",
            "data_coverage_status",
            "benchmark_final_value",
            "benchmark_return",
            "excess_value_vs_benchmark",
            "model_return_minus_benchmark_return",
            "unavailable_reason",
        ]),
        "",
        "## Backtest walk-forward",
        "",
        "- Cette partie utilise les anciennes recommandations réellement produites et mesure ce qui s’est passé jusqu’à l’analyse suivante disponible.",
        "- Si l’historique est trop rapproché, elle reste neutre et ne pénalise pas le modèle.",
        "",
        _markdown_table(_display_walk_forward_summary(walk_forward_summary), [
            "status",
            "simulated_periods",
            "usable_walk_forward_periods",
            "regime_coverage_status",
            "regime_count",
            "weak_regimes",
            "avg_excess_return_vs_vfv",
            "win_rate_vs_vfv",
            "compounded_excess_return_vs_vfv",
            "price_return_basis",
            "interpretation",
        ]),
        "",
        _markdown_table(_display_walk_forward_periods(walk_forward_periods), [
            "analysis_date",
            "next_analysis_date",
            "days_held",
            "allocated_tickers",
            "strategy_period_return",
            "vfv_period_return",
            "excess_return_vs_vfv",
            "evaluation_status",
        ]),
        "",
        "### Benchmarks alternatifs walk-forward",
        "",
        "- Chaque période utilisable est comparée aux mêmes alternatives passives/mécaniques.",
        "",
        _markdown_table(_display_walk_forward_benchmark_rows(walk_forward_benchmark_rows), [
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
        "## Frictions de transaction des backtests",
        "",
        "- **AUDIT-ONLY — aucune recommandation modifiée.** Cette section estime l’effet des commissions, spreads et frais FX sur les backtests.",
        "- Les rendements bruts restent conservés; la version nette sert seulement à voir si le backtest surestime la réalité d’exécution.",
        "",
        _markdown_table(backtest_friction_rows, BACKTEST_FRICTION_FULL_COLUMNS),
        "",
        "## Performance réelle du portefeuille",
        "",
        "- Cette section s’améliore avec le temps. Au début, elle sert surtout à créer une base de suivi.",
        "",
        _markdown_table(account_performance_rows, [
            "account_type",
            "current_value_cad",
            "tracking_start_date",
            "benchmark_return_basis",
            "preferred_performance_summary",
            "portfolio_twr",
            "sp500_twr",
            "twr_excess_vs_sp500",
            "twr_status",
            "portfolio_return_since_tracking",
            "sp500_return_since_tracking",
            "excess_return_vs_sp500",
            "portfolio_xirr",
            "sp500_xirr",
            "xirr_excess_vs_sp500",
            "xirr_status",
            "value_added_vs_sp500_cad",
            "comparison_status",
            "interpretation",
        ]),
        "",
        "## Attribution de sous-performance",
        "",
        "- Cette section évite de corriger le modèle simplement parce que le S&P 500 a gagné une période donnée.",
        "- Elle sépare une sous-performance potentiellement normale d’un vrai problème de processus.",
        "",
        _markdown_table(underperformance.get("rows") or [], UNDERPERFORMANCE_COLUMNS),
        "",
        "## Santé des sources",
        "",
        "- Cette section évite qu’un audit ou un tuning automatique tire une conclusion trop forte si les sources sont fragiles.",
        "- Elle ne change pas l’allocation mensuelle. Elle limite seulement l’auto-correction du modèle en cas de source centrale critique.",
        "",
        _markdown_table(source_health_rows or [], SOURCE_HEALTH_COLUMNS),
        "",
        "## Qualité tickers et contradictions de sources",
        "",
        "- Cette section vérifie si un ticker important semble mal classé, peu couvert ou contradictoire entre sources.",
        "- Elle ne change pas l’allocation mensuelle et ne bloque pas `apply-safe-tuning` à elle seule.",
        "- Elle sert à éviter une mauvaise exécution avant une grosse décision.",
        "",
        _markdown_table(ticker_source_audit_rows(ticker_source_context), TICKER_SOURCE_AUDIT_COLUMNS),
        "",
        "## Audit weakest core",
        "",
        "- **AUDIT-ONLY — aucune recommandation modifiée.** Cette section compare la logique active qui identifie le maillon faible du core avec une logique candidate composite.",
        "- Objectif: observer les divergences avant toute activation éventuelle, surtout pour les promotions externes et les audits.",
        "",
        _markdown_table(weakest_core_audit_rows, WEAKEST_CORE_AUDIT_FULL_COLUMNS),
        "",
        "## Revue des seuils",
        "",
        f"- Diagnostic: **{threshold.get('status', 'N/D')}**",
        f"- Interprétation: {threshold.get('interpretation', 'N/D')}",
        "",
        "## Ce que cet audit améliore",
        "",
        "- Il regroupe la stabilité du modèle, le risque, la comparaison à VFV, la performance réelle suivie et le backtest en un seul diagnostic.",
        "- Il évite de juger le modèle sur une seule recommandation ponctuelle.",
        "- Il utilise la cotisation moyenne détectée quand l’historique est exploitable, ce qui rend le backtest plus proche de ta vraie méthode.",
        "- Il ne modifie pas automatiquement les règles: il signale les seuils à surveiller pour éviter de recalibrer le modèle sur trop peu de données.",
        "",
        "## Limites",
        "",
        "- Le backtest reste théorique: il utilise des scores/proxys actuels et des prix historiques gratuits.",
        "- La performance réelle devient vraiment informative seulement après plusieurs mois, puis plusieurs années de suivi.",
        "- Les taxes, frais exacts, prix exacts de transaction et données manquantes peuvent créer un écart avec la réalité.",
        "- Une bonne note d’audit ne garantit pas une surperformance future.",
        "",
    ]
    if metrics.get("backtest_error"):
        lines.extend(
            [
                "## Backtest non disponible",
                "",
                f"- Raison: {metrics.get('backtest_error')}",
                "",
            ]
        )
    return "\n".join(lines)


def write_full_audit_outputs(reports_dir: str | Path, audit: dict[str, Any]) -> None:
    reports_dir = Path(reports_dir)
    markdown = str(audit.get("markdown") or "")
    rows = audit.get("rows") or []
    underperformance_rows = ((audit.get("metrics") or {}).get("underperformance_attribution") or {}).get("rows") or []
    write_text(reports_dir / "latest_full_audit.md", markdown)
    write_text(reports_dir / "latest_full_audit.html", markdown_to_html(markdown))
    write_csv_records(reports_dir / "latest_full_audit_summary.csv", rows, FULL_AUDIT_COLUMNS)
    write_csv_records(reports_dir / "latest_underperformance_attribution.csv", underperformance_rows, UNDERPERFORMANCE_COLUMNS)


def _detected_external_flows(data_dir: Path) -> list[tuple[date, float]]:
    flows: list[tuple[date, float]] = []
    for row in read_csv_records(data_dir / "portfolio_inferred_transactions.csv"):
        tx_type = str(row.get("inferred_transaction_type") or "").upper()
        confidence = str(row.get("confidence") or "").upper()
        if tx_type in {"BASELINE", "INFERRED_COST_UPDATE"} or confidence == "INFO_ONLY":
            continue
        amount = safe_float(row.get("external_flow_cad"))
        parsed = _parse_date(row.get("date"))
        if parsed and amount and amount > 0:
            flows.append((parsed, amount))

    for row in read_csv_records(data_dir / "portfolio_transactions.csv"):
        tx_type = str(row.get("transaction_type") or "").upper()
        if tx_type not in {"CONTRIBUTION", "DEPOSIT", "CASH_IN", "TRANSFER_IN"}:
            continue
        amount = safe_float(row.get("cash_amount"))
        parsed = _parse_date(row.get("date"))
        if parsed and amount and amount > 0:
            flows.append((parsed, amount))
    return sorted(flows, key=lambda item: item[0])


def _parse_date(value: Any) -> date | None:
    try:
        return datetime.fromisoformat(str(value or "")[:10]).date()
    except ValueError:
        return None


def _month_span(first: date, last: date) -> int:
    return (last.year - first.year) * 12 + (last.month - first.month) + 1


def _contribution_confidence(positive_months: int, span_days: int) -> str:
    if positive_months <= 1:
        return "PRELIMINARY"
    if positive_months <= 3 or span_days < 90:
        return "USEFUL_EARLY"
    if positive_months <= 6 or span_days < 180:
        return "SOLID"
    return "REPRESENTATIVE"


def _account_performance_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        return {
            "status": "UNAVAILABLE",
            "interpretation": "Aucun rapport de performance réelle vs S&P 500 disponible. Lance une analyse normale avant l’audit.",
        }
    all_accounts = next((row for row in rows if str(row.get("account_type") or "") == "ALL_ACCOUNTS"), rows[0])
    status = str(
        all_accounts.get("twr_status")
        or all_accounts.get("comparison_status")
        or all_accounts.get("flow_adjusted_status")
        or "UNAVAILABLE"
    )
    value_added = safe_float(all_accounts.get("value_added_vs_sp500_cad"))
    twr_excess = safe_float(all_accounts.get("twr_excess_vs_sp500"))
    xirr_excess = safe_float(all_accounts.get("xirr_excess_vs_sp500"))
    excess = safe_float(all_accounts.get("excess_return_vs_sp500"))
    preferred_summary = str(all_accounts.get("preferred_performance_summary") or "")
    benchmark_basis = str(all_accounts.get("benchmark_return_basis") or "")
    interpretation = preferred_summary or str(all_accounts.get("interpretation") or "")
    if twr_excess is not None:
        interpretation = f"{interpretation} Écart TWR vs S&P 500: {pct(twr_excess)}."
    elif xirr_excess is not None:
        interpretation = f"{interpretation} Écart XIRR annualisé vs S&P 500: {pct(xirr_excess)}."
    elif value_added is not None:
        interpretation = f"{interpretation} Valeur ajoutée estimée vs S&P 500: {money(value_added)}."
    elif excess is not None:
        interpretation = f"{interpretation} Écart de rendement vs S&P 500: {pct(excess)}."
    if benchmark_basis:
        interpretation = f"{interpretation} Base VFV: {benchmark_basis}."
    return {
        "status": status,
        "benchmark_return_basis": benchmark_basis,
        "value_added_vs_sp500_cad": value_added,
        "twr_excess_vs_sp500": twr_excess,
        "xirr_excess_vs_sp500": xirr_excess,
        "excess_return_vs_sp500": excess,
        "interpretation": interpretation,
    }


def _backtest_score(summaries: list[dict[str, Any]], error: str) -> float:
    if error:
        return 45.0
    if not summaries:
        return 50.0
    scores = []
    for row in summaries:
        score = 65.0
        excess = safe_float(row.get("excess_value_vs_vfv"))
        drawdown = safe_float(row.get("max_drawdown_on_capital_multiple"))
        avg_vfv = safe_float(row.get("avg_vfv_allocation")) or 0.0
        if excess is not None:
            score += 12 if excess > 0 else -10
        if drawdown is not None:
            if drawdown <= -0.45:
                score -= 14
            elif drawdown <= -0.30:
                score -= 7
            elif drawdown >= -0.15:
                score += 4
        if avg_vfv > 0.35:
            score -= 8
        elif 0.08 <= avg_vfv <= 0.25:
            score += 4
        scores.append(max(0.0, min(100.0, score)))
    return round(sum(scores) / len(scores), 1)


def _backtest_status(summaries: list[dict[str, Any]]) -> str:
    if not summaries:
        return "NO_BACKTEST"
    score = _backtest_score(summaries, "")
    if score >= 78:
        return "THEORETICAL_STRONG"
    if score >= 65:
        return "THEORETICAL_ACCEPTABLE"
    if score >= 52:
        return "THEORETICAL_MIXED"
    return "THEORETICAL_WEAK"


def _walk_forward_score(summary: dict[str, Any], error: str) -> float:
    if error:
        return 45.0
    status = str(summary.get("status") or "")
    simulated = int(safe_float(summary.get("simulated_periods")) or 0)
    if status in {"", "NO_USABLE_PERIODS", "NO_SIMULATED_PERIODS"} or simulated <= 0:
        return 60.0
    score = 62.0
    excess = safe_float(summary.get("compounded_excess_return_vs_vfv"))
    avg_excess = safe_float(summary.get("avg_excess_return_vs_vfv"))
    win_rate = safe_float(summary.get("win_rate_vs_vfv"))
    if excess is not None:
        if excess >= 0.05:
            score += 12
        elif excess >= 0:
            score += 6
        elif excess <= -0.08:
            score -= 12
        elif excess < -0.02:
            score -= 6
    if avg_excess is not None:
        score += 4 if avg_excess > 0 else -4 if avg_excess < -0.02 else 0
    if win_rate is not None:
        if win_rate >= 0.60:
            score += 5
        elif win_rate <= 0.35:
            score -= 5
    if status in {"EARLY_SIGNAL_ONLY", "PRELIMINARY_WALK_FORWARD"}:
        score = 60.0 + (score - 60.0) * 0.50
    return round(max(0.0, min(100.0, score)), 1)


def _walk_forward_audit_status(summary: dict[str, Any]) -> str:
    status = str(summary.get("status") or "")
    if status in {"", "NO_USABLE_PERIODS"}:
        return "WALK_FORWARD_NOT_READY"
    if status == "NO_SIMULATED_PERIODS":
        return "WALK_FORWARD_DATA_GAP"
    if status == "EARLY_SIGNAL_ONLY":
        return "WALK_FORWARD_EARLY"
    if status == "PRELIMINARY_WALK_FORWARD":
        return "WALK_FORWARD_PRELIMINARY"
    if status == "READY_FOR_WALK_FORWARD_REVIEW":
        score = _walk_forward_score(summary, "")
        if score >= 72:
            return "WALK_FORWARD_SUPPORTIVE"
        if score >= 55:
            return "WALK_FORWARD_MIXED"
        return "WALK_FORWARD_WEAK"
    return status or "WALK_FORWARD_UNKNOWN"


def _walk_forward_interpretation(metrics: dict[str, Any]) -> str:
    if metrics.get("walk_forward_error"):
        return f"Walk-forward non disponible: {metrics.get('walk_forward_error')}"
    summary = metrics.get("walk_forward_summary") or {}
    status = str(summary.get("status") or "")
    if status in {"", "NO_USABLE_PERIODS"}:
        return "Pas encore assez d’analyses espacées pour tester les recommandations hors-échantillon."
    if status == "NO_SIMULATED_PERIODS":
        return "Des périodes existent, mais les prix historiques ne permettent pas encore un calcul propre."
    simulated = int(safe_float(summary.get("simulated_periods")) or 0)
    excess = safe_float(summary.get("compounded_excess_return_vs_vfv"))
    return (
        f"{simulated} période(s) simulée(s); excès composé vs VFV: {pct(excess, 2)}. "
        "À lire comme preuve complémentaire, surtout si l’historique devient long."
    )


def _realized_performance_score(summary: dict[str, Any]) -> float:
    status = str(summary.get("status") or "")
    excess = (
        safe_float(summary.get("twr_excess_vs_sp500"))
        if safe_float(summary.get("twr_excess_vs_sp500")) is not None
        else safe_float(summary.get("excess_return_vs_sp500"))
    )
    if status == "UNAVAILABLE":
        return 45.0
    if "BASELINE" in status or "NO_EXTERNAL_FLOWS" in status or status == "SIMILAR_TO_SP500":
        base = 62.0
    elif "OUTPERFORM" in status or "AHEAD" in status:
        base = 78.0
    elif "UNDERPERFORM" in status or "BEHIND" in status:
        base = 50.0
    else:
        base = 60.0
    if excess is not None:
        if excess > 0.05:
            base += 8
        elif excess < -0.05:
            base -= 8
    return round(max(0.0, min(100.0, base)), 1)


def _evidence_score(
    model_metrics: dict[str, Any],
    backtest_summaries: list[dict[str, Any]],
    account_summary: dict[str, Any],
    contribution: dict[str, Any],
    source_health: dict[str, Any] | None = None,
    ticker_source_context: dict[str, Any] | None = None,
    walk_forward_summary: dict[str, Any] | None = None,
) -> float:
    confidence_points = {
        "VERY_LIMITED": 30,
        "PRELIMINARY": 45,
        "USEFUL_EARLY": 58,
        "USEFUL_BUT_SHORT_SPAN": 68,
        "SOLID": 80,
        "REPRESENTATIVE": 90,
    }
    model_conf = str(model_metrics.get("confidence") or "VERY_LIMITED")
    contribution_conf = str(contribution.get("confidence") or "LOW")
    contribution_points = {
        "LOW": 35,
        "PRELIMINARY": 45,
        "USEFUL_EARLY": 58,
        "SOLID": 75,
        "REPRESENTATIVE": 85,
    }.get(contribution_conf, 45)
    backtest_points = 75 if backtest_summaries else 35
    walk_forward_summary = walk_forward_summary or {}
    walk_forward_status = str(walk_forward_summary.get("status") or "")
    walk_forward_points = 60 if walk_forward_status in {"", "NO_USABLE_PERIODS", "NO_SIMULATED_PERIODS"} else _walk_forward_score(walk_forward_summary, "")
    real_points = 70 if account_summary.get("status") not in {"UNAVAILABLE", ""} else 35
    source_health = source_health or {}
    source_points = safe_float(source_health.get("source_health_score"))
    if source_points is None:
        source_points = 60.0
    base = (
        0.32 * confidence_points.get(model_conf, 45)
        + 0.20 * contribution_points
        + 0.20 * backtest_points
        + 0.08 * walk_forward_points
        + 0.20 * real_points
    )
    # Source health is deliberately capped to a small adjustment so a temporary
    # data-source issue does not dominate the long-term audit.
    source_adjustment = max(-6.0, min(3.0, (source_points - 75.0) * 0.12))
    ticker_source_context = ticker_source_context or {}
    ticker_source_points = safe_float(ticker_source_context.get("ticker_source_quality_score"))
    if ticker_source_points is None:
        ticker_source_points = 80.0
    # Ticker/source conflict quality is a narrow execution-risk adjustment only.
    # It must not turn a high-CAGR model into a conservative model.
    ticker_source_adjustment = max(-3.0, min(1.0, (ticker_source_points - 80.0) * 0.06))
    return round(
        max(0.0, min(100.0, base + source_adjustment + ticker_source_adjustment)),
        1,
    )


def _criterion7_status(score: float, model_metrics: dict[str, Any], backtest_error: str) -> str:
    sample_count = int(model_metrics.get("allocation_sample_count") or 0)
    if sample_count <= 1 and backtest_error:
        return "AUDIT_TOO_YOUNG"
    if score >= 82:
        return "AUDIT_STRONG"
    if score >= 70:
        return "AUDIT_ACCEPTABLE"
    if score >= 58:
        return "AUDIT_USEFUL_BUT_YOUNG"
    if score >= 45:
        return "AUDIT_NEEDS_MORE_HISTORY"
    return "AUDIT_NEEDS_REVIEW"


def _criterion7_interpretation(status: str) -> str:
    messages = {
        "AUDIT_STRONG": "Le modèle possède une preuve de méthode solide selon les données disponibles, sans garantir l’avenir.",
        "AUDIT_ACCEPTABLE": "Le modèle est utilisable sur le long terme, avec une surveillance périodique des seuils, du risque et de VFV.",
        "AUDIT_USEFUL_BUT_YOUNG": "L’audit est utile, mais l’historique réel reste encore jeune pour conclure sur plusieurs cycles.",
        "AUDIT_NEEDS_MORE_HISTORY": "La mécanique est auditée, mais il faut plus de mois réels pour juger la constance et la performance.",
        "AUDIT_TOO_YOUNG": "Il n’y a pas encore assez d’historique exploitable; l’audit sert surtout de point de départ.",
        "AUDIT_NEEDS_REVIEW": "Certains signaux suggèrent une revue manuelle de la mécanique avant de trop s’y fier.",
    }
    return messages.get(status, "Audit disponible, mais interprétation à valider manuellement.")


def _backtest_interpretation(metrics: dict[str, Any]) -> str:
    if metrics.get("backtest_error"):
        return f"Backtest non disponible: {metrics.get('backtest_error')}"
    summaries = metrics.get("backtest_summaries") or []
    if not summaries:
        return "Aucun résumé de backtest disponible."
    parts = []
    for row in summaries:
        excess = safe_float(row.get("excess_value_vs_vfv"))
        verdict = "au-dessus de VFV" if excess is not None and excess > 0 else "sous VFV"
        parts.append(f"{row.get('period_years')} ans {verdict} ({money(excess)})")
    return "; ".join(parts)


def _display_backtest_summaries(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    output = []
    for row in rows:
        output.append(
            {
                **row,
                "total_contributed": money(safe_float(row.get("total_contributed"))),
                "final_value": money(safe_float(row.get("final_value"))),
                "vfv_final_value": money(safe_float(row.get("vfv_final_value"))),
                "excess_value_vs_vfv": money(safe_float(row.get("excess_value_vs_vfv"))),
                "money_weighted_annual_return": pct(safe_float(row.get("money_weighted_annual_return")), 2),
                "max_drawdown_on_capital_multiple": pct(safe_float(row.get("max_drawdown_on_capital_multiple")), 1),
                "avg_vfv_allocation": pct(safe_float(row.get("avg_vfv_allocation")), 1),
            }
        )
    return output


def _display_backtest_benchmark_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    output = []
    for row in rows:
        output.append(
            {
                **row,
                "benchmark_final_value": money(safe_float(row.get("benchmark_final_value"))),
                "benchmark_return": pct(safe_float(row.get("benchmark_return")), 2),
                "excess_value_vs_benchmark": money(safe_float(row.get("excess_value_vs_benchmark"))),
                "model_return_minus_benchmark_return": pct(safe_float(row.get("model_return_minus_benchmark_return")), 2),
            }
        )
    return output


def _display_walk_forward_summary(row: dict[str, Any]) -> list[dict[str, Any]]:
    if not row:
        return [
            {
                "status": "NO_DATA",
                "simulated_periods": 0,
                "usable_walk_forward_periods": 0,
                "avg_excess_return_vs_vfv": "N/D",
                "win_rate_vs_vfv": "N/D",
                "compounded_excess_return_vs_vfv": "N/D",
                "price_return_basis": "",
                "interpretation": "Aucun résumé walk-forward disponible.",
            }
        ]
    return [
        {
            **row,
            "avg_excess_return_vs_vfv": pct(safe_float(row.get("avg_excess_return_vs_vfv")), 2),
            "win_rate_vs_vfv": pct(safe_float(row.get("win_rate_vs_vfv")), 1),
            "compounded_excess_return_vs_vfv": pct(safe_float(row.get("compounded_excess_return_vs_vfv")), 2),
        }
    ]


def _display_walk_forward_periods(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    output = []
    for row in rows:
        output.append(
            {
                **row,
                "strategy_period_return": pct(safe_float(row.get("strategy_period_return")), 2),
                "vfv_period_return": pct(safe_float(row.get("vfv_period_return")), 2),
                "excess_return_vs_vfv": pct(safe_float(row.get("excess_return_vs_vfv")), 2),
            }
        )
    return output


def _display_walk_forward_benchmark_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    output = []
    for row in rows:
        output.append(
            {
                **row,
                "strategy_period_return": pct(safe_float(row.get("strategy_period_return")), 2),
                "benchmark_period_return": pct(safe_float(row.get("benchmark_period_return")), 2),
                "model_excess_return_vs_benchmark": pct(safe_float(row.get("model_excess_return_vs_benchmark")), 2),
            }
        )
    return output


def _display_weakest_core_audit_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if rows:
        return rows[:5]
    return [
        {
            "audit_status": "NOT_AVAILABLE",
            "current_weakest_ticker": "",
            "candidate_weakest_ticker": "",
            "same_result": "",
            "current_reason": "",
            "candidate_reason": "",
            "interpretation": "Lancer une analyse complète pour générer reports/latest_weakest_core_audit.csv avant cet audit.",
        }
    ]


def _display_backtest_friction_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not rows:
        return [
            {
                "audit_scope": "NOT_AVAILABLE",
                "mode": "",
                "period_years": "",
                "analysis_date": "",
                "next_analysis_date": "",
                "gross_return": "",
                "estimated_transaction_cost_cad": "",
                "net_return_after_friction": "",
                "friction_drag": "",
                "friction_assumption_status": "",
                "interpretation": "Aucun audit de friction disponible. Lancer backtest ou full-audit pour le générer.",
            }
        ]
    display = []
    for row in rows[:40]:
        item = dict(row)
        item["gross_return"] = pct(safe_float(item.get("gross_return")), 2)
        item["estimated_transaction_cost_cad"] = money(safe_float(item.get("estimated_transaction_cost_cad")))
        item["net_return_after_friction"] = pct(safe_float(item.get("net_return_after_friction")), 2)
        item["friction_drag"] = pct(safe_float(item.get("friction_drag")), 2)
        display.append(item)
    return display


def _vfv_status(value: float) -> str:
    if value > 0.35:
        return "TOO_DEFENSIVE"
    if value > 0.25:
        return "WATCH"
    if value < 0.05:
        return "VERY_AGGRESSIVE"
    return "BALANCED_FOR_HIGH_CAGR"


def _rate_status(value: float, caution: float, danger: float, *, inverse: bool = False) -> str:
    if inverse:
        if value >= danger:
            return "HIGH_RISK"
        if value >= caution:
            return "WATCH"
        return "OK"
    if value < caution:
        return "LOW"
    if value < danger:
        return "OK"
    return "HIGH"


def _score_status(value: float | None) -> str:
    if value is None:
        return "N/D"
    if value >= 80:
        return "HIGH"
    if value >= 65:
        return "MEDIUM"
    if value >= 50:
        return "LOW"
    return "VERY_LOW"


def _row(section: str, metric: str, status: str, value: str, interpretation: str, impact: str) -> dict[str, Any]:
    return {
        "section": section,
        "metric": metric,
        "status": status,
        "value": value,
        "interpretation": interpretation,
        "impact": impact,
    }


def _markdown_table(rows: list[dict[str, Any]], columns: list[str] = FULL_AUDIT_COLUMNS) -> str:
    if not rows:
        return "_Aucune donnée disponible._"
    lines = [
        "| " + " | ".join(columns) + " |",
        "| " + " | ".join(["---"] * len(columns)) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(_cell(row.get(column, "")) for column in columns) + " |")
    return "\n".join(lines)


def _cell(value: Any) -> str:
    text = str(value if value is not None else "")
    return text.replace("\n", " ").replace("|", "/")
