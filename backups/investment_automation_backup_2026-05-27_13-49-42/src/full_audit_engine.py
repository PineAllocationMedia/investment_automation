from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime
from pathlib import Path
from typing import Any

from .backtest_engine import run_backtests_from_latest_reports
from .model_audit_engine import run_model_audit
from .underperformance_engine import UNDERPERFORMANCE_COLUMNS, build_underperformance_attribution
from .utils import DATA_DIR, DISCLAIMER, REPORTS_DIR, markdown_to_html, money, pct, read_csv_records, safe_float, write_csv_records, write_text


FULL_AUDIT_COLUMNS = [
    "section",
    "metric",
    "status",
    "value",
    "interpretation",
    "impact",
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

    metrics = build_full_audit_metrics(
        model_audit=model_audit,
        backtest_result=backtest_result,
        backtest_error=backtest_error,
        account_performance_rows=account_performance_rows,
        contribution_estimate=contribution,
        selected_monthly_capital=selected_monthly_capital,
        period=period,
        years=years,
        mode=mode,
    )
    rows = build_full_audit_rows(metrics)
    markdown = build_full_audit_markdown(metrics, rows, model_audit, backtest_result, account_performance_rows)
    audit = {
        "metrics": metrics,
        "rows": rows,
        "markdown": markdown,
        "model_audit": model_audit,
        "backtest_result": backtest_result,
        "account_performance_rows": account_performance_rows,
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
    account_performance_rows: list[dict[str, Any]],
    contribution_estimate: dict[str, Any],
    selected_monthly_capital: float,
    period: str,
    years: list[int],
    mode: str,
) -> dict[str, Any]:
    model_metrics = model_audit.get("metrics") or {}
    backtest_summaries = backtest_result.get("summaries") or []
    account_summary = _account_performance_summary(account_performance_rows)

    model_score = safe_float(model_metrics.get("health_score")) or 0.0
    backtest_score = _backtest_score(backtest_summaries, backtest_error)
    realized_score = _realized_performance_score(account_summary)
    evidence_score = _evidence_score(model_metrics, backtest_summaries, account_summary, contribution_estimate)
    underperformance = build_underperformance_attribution(
        model_metrics=model_metrics,
        account_performance_rows=account_performance_rows,
        backtest_summaries=backtest_summaries,
        mode=mode,
    )
    criterion7_score = round(
        0.30 * model_score + 0.30 * backtest_score + 0.20 * realized_score + 0.20 * evidence_score,
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
        "realized_performance_status": account_summary.get("status", "UNAVAILABLE"),
        "realized_performance_score": realized_score,
        "account_summary": account_summary,
        "underperformance_attribution": underperformance,
        "evidence_score": evidence_score,
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
    ]
    return rows


def build_full_audit_markdown(
    metrics: dict[str, Any],
    rows: list[dict[str, Any]],
    model_audit: dict[str, Any],
    backtest_result: dict[str, Any],
    account_performance_rows: list[dict[str, Any]],
) -> str:
    model_metrics = model_audit.get("metrics") or {}
    backtest_summaries = backtest_result.get("summaries") or []
    threshold = model_metrics.get("threshold_review") or {}
    underperformance = metrics.get("underperformance_attribution") or {}
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
        f"- Performance réelle suivie: **{metrics.get('realized_performance_status')}** ({metrics.get('realized_performance_score'):.1f}/100)",
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
    real_points = 70 if account_summary.get("status") not in {"UNAVAILABLE", ""} else 35
    return round(
        0.35 * confidence_points.get(model_conf, 45)
        + 0.20 * contribution_points
        + 0.25 * backtest_points
        + 0.20 * real_points,
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
