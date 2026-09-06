from __future__ import annotations

from .runtime_context import configure_provider_cache

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import math

import pandas as pd

from .benchmark_comparison_engine import (
    BACKTEST_BENCHMARK_COLUMNS,
    benchmark_price_tickers,
    build_backtest_benchmark_comparisons,
    load_benchmark_definitions,
)
from .mode_artifacts import (
    mode_artifact_path,
    read_mode_csv_if_exists,
    require_mode_artifact,
    write_csv_records_mode_pair,
    write_text_mode_pair,
)
from .transaction_friction_engine import (
    BACKTEST_FRICTION_AUDIT_COLUMNS,
    add_friction_fields_to_backtest_summaries,
    build_theoretical_backtest_friction_rows,
    merge_friction_audit_rows,
)
from .utils import DISCLAIMER, DATA_DIR, load_json, money, pct, read_csv_records, safe_float, save_json, write_csv_records, write_text
from .validation_evidence import EvidenceClass


BACKTEST_SUMMARY_COLUMNS = [
    "evidence_class",
    "evidence_role",
    "positive_validation_authority",
    "period_years",
    "strategy",
    "start_date",
    "end_date",
    "months",
    "monthly_capital",
    "total_contributed",
    "final_value",
    "total_gain",
    "money_weighted_annual_return",
    "vfv_final_value",
    "excess_value_vs_vfv",
    "price_return_basis",
    "max_drawdown_on_capital_multiple",
    "avg_vfv_allocation",
    "avg_top1_allocation",
    "gross_return",
    "estimated_transaction_cost_cad",
    "net_return_after_friction",
    "friction_drag",
    "friction_assumption_status",
    "notes",
]

BACKTEST_MONTHLY_COLUMNS = [
    "period_years",
    "date",
    "portfolio_value",
    "vfv_value",
    "contributed_to_date",
    "capital_multiple",
    "vfv_capital_multiple",
    "drawdown_on_capital_multiple",
    "selected_tickers",
    "vfv_allocation",
    "top_allocation",
]

BACKTEST_ALLOCATION_COLUMNS = [
    "period_years",
    "date",
    "ticker",
    "amount",
    "percentage",
    "price_cad",
    "shares_bought",
    "rule",
]


@dataclass(frozen=True)
class BacktestConfig:
    years: int
    monthly_capital: float
    mode: str
    min_vfv_percent: float


def run_backtests_from_latest_reports(
    reports_dir: str | Path,
    data_dir: str | Path = DATA_DIR,
    years: list[int] | None = None,
    monthly_capital: float = 500.0,
    mode: str = "high-cagr",
    refresh_market_data: bool = False,
) -> dict[str, Any]:
    reports_dir = Path(reports_dir)
    data_dir = Path(data_dir)
    years = sorted(set(years or [5, 10]))
    analyses = _load_latest_score_rows(reports_dir, mode=mode, strict_mode=True)
    if not analyses:
        raise RuntimeError(f"Missing mode-specific scores for {mode}. Run `python3 main.py analyze --mode {mode}` first.")

    min_vfv = _latest_mandatory_vfv_percent(reports_dir, mode)
    max_years = max(years)
    benchmark_definitions = load_benchmark_definitions()
    tickers = sorted(set(_backtest_tickers(analyses)) | set(benchmark_price_tickers(benchmark_definitions)))
    price_data = fetch_price_history_cad(tickers, data_dir, years=max_years, refresh=refresh_market_data, mode=mode)

    summaries: list[dict[str, Any]] = []
    monthly_rows: list[dict[str, Any]] = []
    allocation_rows: list[dict[str, Any]] = []
    friction_rows: list[dict[str, Any]] = []

    for period in years:
        config = BacktestConfig(
            years=period,
            monthly_capital=monthly_capital,
            mode=mode,
            min_vfv_percent=min_vfv,
        )
        result = simulate_monthly_model_backtest(analyses, price_data, config)
        summaries.append(result["summary"])
        monthly_rows.extend(result["monthly_rows"])
        allocation_rows.extend(result["allocation_rows"])
        friction_rows.extend(result.get("friction_rows") or [])

    write_csv_records_mode_pair(reports_dir, "latest_backtest_summary.csv", mode, summaries, BACKTEST_SUMMARY_COLUMNS)
    write_csv_records_mode_pair(reports_dir, "latest_backtest_monthly.csv", mode, monthly_rows, BACKTEST_MONTHLY_COLUMNS)
    write_csv_records_mode_pair(reports_dir, "latest_backtest_allocations.csv", mode, allocation_rows, BACKTEST_ALLOCATION_COLUMNS)
    existing_friction_rows = read_csv_records(reports_dir / "latest_backtest_friction_audit.csv")
    existing_mode_friction_rows = read_csv_records(mode_artifact_path(reports_dir / "latest_backtest_friction_audit.csv", mode))
    write_csv_records(
        reports_dir / "latest_backtest_friction_audit.csv",
        merge_friction_audit_rows(existing_friction_rows, friction_rows, {"THEORETICAL_BACKTEST"}),
        BACKTEST_FRICTION_AUDIT_COLUMNS,
    )
    write_csv_records(
        mode_artifact_path(reports_dir / "latest_backtest_friction_audit.csv", mode),
        merge_friction_audit_rows(existing_mode_friction_rows, friction_rows, {"THEORETICAL_BACKTEST"}),
        BACKTEST_FRICTION_AUDIT_COLUMNS,
    )
    benchmark_rows = build_backtest_benchmark_comparisons(
        summaries,
        monthly_rows,
        _actual_month_end_prices(price_data),
        monthly_capital,
        benchmark_definitions,
        price_return_basis=str(price_data.attrs.get("price_return_basis", "UNKNOWN_PRICE_BASIS")),
    )
    write_csv_records_mode_pair(reports_dir, "latest_benchmark_comparison.csv", mode, benchmark_rows, BACKTEST_BENCHMARK_COLUMNS)
    write_text_mode_pair(reports_dir, "latest_backtest_report.md", mode, build_backtest_report(summaries, benchmark_rows))
    return {
        "summaries": summaries,
        "monthly_rows": monthly_rows,
        "allocation_rows": allocation_rows,
        "benchmark_rows": benchmark_rows,
        "friction_rows": friction_rows,
    }


def fetch_price_history_cad(
    tickers: list[str],
    data_dir: str | Path,
    years: int,
    refresh: bool = False,
    mode: str | None = None,
) -> pd.DataFrame:
    cache_path = Path(data_dir) / "cached_market_data" / f"backtest_total_return_prices_cad_{years}y.csv"
    meta_path = cache_path.with_suffix(".meta.json")
    if cache_path.exists() and not refresh:
        cached = pd.read_csv(cache_path, index_col=0, parse_dates=True)
        if not cached.empty:
            meta = load_json(meta_path)
            cached.attrs["price_basis_by_ticker"] = meta.get("price_basis_by_ticker", {}) if isinstance(meta, dict) else {}
            cached.attrs["price_return_basis"] = meta.get("price_return_basis", "UNKNOWN_CACHE") if isinstance(meta, dict) else "UNKNOWN_CACHE"
            return cached

    try:
        import yfinance as yf  # type: ignore
        configure_provider_cache(yf)
    except Exception as exc:
        raise RuntimeError("yfinance n'est pas disponible pour télécharger l'historique.") from exc

    raw_tickers = sorted(set(tickers + ["USDCAD=X", "EURCAD=X"]))
    period = f"{years + 2}y"
    raw = yf.download(raw_tickers, period=period, auto_adjust=False, progress=False, group_by="ticker", threads=True)
    price_frame, price_basis_by_ticker = _total_return_price_frame(raw, raw_tickers)
    if price_frame.empty:
        raise RuntimeError("Aucun historique de prix reçu de yfinance.")

    scores = _load_latest_score_rows(Path(data_dir).parent / "reports", mode=mode, strict_mode=False)
    currencies = {ticker: str(row.get("quote_currency") or row.get("currency") or "CAD").upper() for ticker, row in scores.items()}
    prices = pd.DataFrame(index=price_frame.index)
    for ticker in tickers:
        if ticker not in price_frame:
            continue
        series = price_frame[ticker].dropna()
        if series.empty:
            continue
        currency = currencies.get(ticker, "CAD")
        if currency == "USD" and "USDCAD=X" in price_frame:
            prices[ticker] = price_frame[ticker] * price_frame["USDCAD=X"].ffill()
        elif currency == "EUR" and "EURCAD=X" in price_frame:
            prices[ticker] = price_frame[ticker] * price_frame["EURCAD=X"].ffill()
        else:
            prices[ticker] = price_frame[ticker]
    prices = prices.dropna(how="all")
    prices.attrs["price_basis_by_ticker"] = {ticker: price_basis_by_ticker.get(ticker, "PRICE_CLOSE") for ticker in tickers}
    prices.attrs["price_return_basis"] = _overall_price_return_basis(prices.attrs["price_basis_by_ticker"])
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    prices.to_csv(cache_path)
    save_json(
        meta_path,
        {
            "price_return_basis": prices.attrs["price_return_basis"],
            "price_basis_by_ticker": prices.attrs["price_basis_by_ticker"],
            "note": "Backtest uses Adj Close when available as a free total-return proxy; Close is the fallback.",
        },
    )
    return prices


def simulate_monthly_model_backtest(
    analyses: dict[str, dict[str, Any]],
    prices_cad: pd.DataFrame,
    config: BacktestConfig,
) -> dict[str, Any]:
    prices_cad = prices_cad.sort_index().ffill().dropna(how="all")
    if "VFV.TO" not in prices_cad.columns:
        raise RuntimeError("VFV.TO est requis pour comparer la stratégie au benchmark.")

    monthly_prices = _actual_month_end_prices(prices_cad)
    if len(monthly_prices) < config.years * 12:
        raise RuntimeError(f"Historique insuffisant pour {config.years} ans.")
    month_ends = list(monthly_prices.index[-config.years * 12 :])

    holdings = {ticker: 0.0 for ticker in prices_cad.columns}
    vfv_holdings = 0.0
    contributed = 0.0
    cashflows = []
    monthly_rows: list[dict[str, Any]] = []
    allocation_rows: list[dict[str, Any]] = []
    capital_multiple_peak = 0.0
    top_allocations: list[float] = []
    vfv_allocations: list[float] = []

    for date in month_ends:
        prices_on_date = monthly_prices.loc[date]
        allocations = _monthly_model_allocations(analyses, prices_cad.loc[:date], prices_on_date, config)
        contributed += config.monthly_capital
        cashflows.append(-config.monthly_capital)

        for ticker, amount in allocations.items():
            price = safe_float(prices_on_date.get(ticker))
            if price is None or price <= 0:
                ticker = "VFV.TO"
                price = safe_float(prices_on_date.get(ticker))
            if price is None or price <= 0:
                continue
            shares = amount / price
            holdings[ticker] = holdings.get(ticker, 0.0) + shares
            allocation_rows.append(
                {
                    "period_years": config.years,
                    "date": date.date().isoformat(),
                    "ticker": ticker,
                    "amount": round(amount, 2),
                    "percentage": round(amount / config.monthly_capital, 4) if config.monthly_capital > 0 else 0.0,
                    "price_cad": round(price, 4),
                    "shares_bought": shares,
                    "rule": "model-lite dynamic monthly allocation",
                }
            )

        vfv_price = safe_float(prices_on_date.get("VFV.TO"))
        if vfv_price and vfv_price > 0:
            vfv_holdings += config.monthly_capital / vfv_price

        portfolio_value = _portfolio_value(holdings, prices_on_date)
        vfv_value = vfv_holdings * (vfv_price or 0.0)
        capital_multiple = portfolio_value / contributed if contributed > 0 else 1.0
        vfv_multiple = vfv_value / contributed if contributed > 0 else 1.0
        capital_multiple_peak = max(capital_multiple_peak, capital_multiple)
        drawdown = capital_multiple / capital_multiple_peak - 1 if capital_multiple_peak > 0 else 0.0
        selected = [ticker for ticker, amount in allocations.items() if amount > 0]
        vfv_pct = allocations.get("VFV.TO", 0.0) / config.monthly_capital if config.monthly_capital > 0 else 0.0
        top_pct = max((amount / config.monthly_capital for ticker, amount in allocations.items() if ticker != "VFV.TO"), default=0.0)
        vfv_allocations.append(vfv_pct)
        top_allocations.append(top_pct)
        monthly_rows.append(
            {
                "period_years": config.years,
                "date": date.date().isoformat(),
                "portfolio_value": round(portfolio_value, 2),
                "vfv_value": round(vfv_value, 2),
                "contributed_to_date": round(contributed, 2),
                "capital_multiple": round(capital_multiple, 4),
                "vfv_capital_multiple": round(vfv_multiple, 4),
                "drawdown_on_capital_multiple": round(drawdown, 4),
                "selected_tickers": ", ".join(selected),
                "vfv_allocation": round(vfv_pct, 4),
                "top_allocation": round(top_pct, 4),
            }
        )

    final_value = monthly_rows[-1]["portfolio_value"]
    vfv_final = monthly_rows[-1]["vfv_value"]
    cashflows.append(final_value)
    irr = _annualized_irr(cashflows)
    summary = {
        "evidence_class": EvidenceClass.MECHANICAL_DIAGNOSTIC.value,
        "evidence_role": "NEGATIVE_WARNING_AND_NEUTRAL_DIAGNOSTIC_ONLY",
        "positive_validation_authority": False,
        "period_years": config.years,
        "strategy": f"model-lite {config.mode}",
        "start_date": month_ends[0].date().isoformat(),
        "end_date": month_ends[-1].date().isoformat(),
        "months": len(month_ends),
        "monthly_capital": round(config.monthly_capital, 2),
        "total_contributed": round(contributed, 2),
        "final_value": round(final_value, 2),
        "total_gain": round(final_value - contributed, 2),
        "money_weighted_annual_return": round(irr, 4) if irr is not None else "",
        "vfv_final_value": round(vfv_final, 2),
        "excess_value_vs_vfv": round(final_value - vfv_final, 2),
        "price_return_basis": prices_cad.attrs.get("price_return_basis", "UNKNOWN_PRICE_BASIS"),
        "max_drawdown_on_capital_multiple": min(row["drawdown_on_capital_multiple"] for row in monthly_rows),
        "avg_vfv_allocation": round(sum(vfv_allocations) / len(vfv_allocations), 4) if vfv_allocations else 0.0,
        "avg_top1_allocation": round(sum(top_allocations) / len(top_allocations), 4) if top_allocations else 0.0,
        "notes": (
            "MECHANICAL_DIAGNOSTIC: prix historiques avec scores/proxys actuels. "
            "Les résultats favorables n'ont aucune autorité positive de validation; "
            "les anomalies mécaniques défavorables restent des avertissements utiles."
        ),
    }
    friction_rows = build_theoretical_backtest_friction_rows([summary], allocation_rows, analyses)
    summary = add_friction_fields_to_backtest_summaries([summary], friction_rows)[0]
    return {"summary": summary, "monthly_rows": monthly_rows, "allocation_rows": allocation_rows, "friction_rows": friction_rows}


def build_backtest_report(summaries: list[dict[str, Any]], benchmark_rows: list[dict[str, Any]] | None = None) -> str:
    benchmark_rows = benchmark_rows or []
    lines = [
        "# Backtest théorique du modèle",
        "",
        f"> {DISCLAIMER}",
        "",
        "## Lecture importante",
        "",
        f"- Classe canonique: `{EvidenceClass.MECHANICAL_DIAGNOSTIC.value}`.",
        "- Ce backtest est théorique et sert à tester la mécanique, pas à valider historiquement la stratégie.",
        "- Un résultat défavorable peut signaler une mécanique pathologique; un résultat favorable ne prouve ni alpha, ni skill, ni robustesse multi-régime.",
        "- Les prix historiques viennent de yfinance quand disponibles.",
        "- Quand disponible, le backtest utilise `Adj Close`, un proxy gratuit de rendement total approximatif qui inclut les dividendes/distributions réinvestis; sinon il revient à `Close`.",
        "- Les fondamentaux historiques complets ne sont pas reconstruits gratuitement; les scores actuels du modèle servent d’ancrage.",
        "- Si un benchmark alternatif manque parce que le cache local ne contient pas encore ses prix, relancer avec `--refresh-market-data` peut le rendre disponible.",
        "- Le résultat peut surestimer ou sous-estimer la réalité à cause du biais de survie, des tickers récents, des taxes, des frais et du change.",
        "",
        "## Résumé",
        "",
        _markdown_table(
            [
                "evidence_class",
                "evidence_role",
                "positive_validation_authority",
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
                "gross_return",
                "estimated_transaction_cost_cad",
                "net_return_after_friction",
                "friction_drag",
                "friction_assumption_status",
            ],
            [_display_summary(row) for row in summaries],
        ),
        "",
        "## Comparaisons benchmarks alternatifs",
        "",
        "- Ces benchmarks sont des points de comparaison d’audit seulement; ils ne changent jamais la recommandation du modèle.",
        "- `SIMPLE_MOMENTUM` est mécanique et n’utilise que les prix disponibles avant chaque date simulée.",
        "",
        _markdown_table(
            [
                "period_years",
                "benchmark_id",
                "data_coverage_status",
                "benchmark_final_value",
                "benchmark_return",
                "excess_value_vs_benchmark",
                "model_return_minus_benchmark_return",
                "unavailable_reason",
            ],
            [_display_benchmark_row(row) for row in benchmark_rows],
        ),
        "",
        "## Interprétation",
        "",
    ]
    for row in summaries:
        excess = safe_float(row.get("excess_value_vs_vfv")) or 0.0
        if excess > 0:
            lines.append(
                f"- Sur {row.get('period_years')} ans, la simulation mécanique dépasse VFV.TO de {money(abs(excess))}; "
                "ce résultat contaminé ne possède aucune autorité positive de validation."
            )
        else:
            lines.append(
                f"- Sur {row.get('period_years')} ans, la simulation mécanique sous-performe VFV.TO de {money(abs(excess))}; "
                "ce signal défavorable reste un avertissement mécanique utile."
            )
    return "\n".join(lines) + "\n"


def _monthly_model_allocations(
    analyses: dict[str, dict[str, Any]],
    trailing_prices: pd.DataFrame,
    prices_on_date: pd.Series,
    config: BacktestConfig,
) -> dict[str, float]:
    candidates: list[tuple[str, float]] = []
    vfv_return = _one_year_return(trailing_prices.get("VFV.TO"))
    for ticker, row in analyses.items():
        if ticker == "VFV.TO" or ticker not in trailing_prices.columns:
            continue
        if not _currently_eligible_for_backtest(row):
            continue
        price = safe_float(prices_on_date.get(ticker))
        if price is None or price <= 0:
            continue
        dynamic_score = _dynamic_backtest_score(row, trailing_prices[ticker].dropna(), vfv_return)
        if dynamic_score >= 40:
            candidates.append((ticker, dynamic_score))

    vfv_floor = max(config.min_vfv_percent, 0.10 if config.mode == "high-cagr" else 0.15)
    allocations = {"VFV.TO": round(config.monthly_capital * vfv_floor, 2)}
    remaining = round(config.monthly_capital - allocations["VFV.TO"], 2)
    if not candidates or remaining <= 0:
        allocations["VFV.TO"] = config.monthly_capital
        return allocations

    candidates.sort(key=lambda item: item[1], reverse=True)
    top = candidates[:4]
    total_score = sum(max(score, 1.0) for _, score in top)
    watch_used = 0.0
    unallocated = 0.0
    for ticker, score in top:
        raw_amount = remaining * (max(score, 1.0) / total_score)
        row = analyses[ticker]
        cap_pct = 0.40
        if str(row.get("monitoring_status") or "NORMAL") in {"WATCH", "MANUAL_REVIEW"}:
            cap_pct = 0.35
        if str(row.get("score_evidence_level") or "") in {"ESTIMATE_HEAVY", "INSUFFICIENT_CONFIRMED"}:
            cap_pct = min(cap_pct, 0.25)
        amount = min(raw_amount, config.monthly_capital * cap_pct)
        if str(row.get("monitoring_status") or "NORMAL") in {"WATCH", "MANUAL_REVIEW"}:
            room = max(0.0, config.monthly_capital * 0.60 - watch_used)
            amount = min(amount, room)
            watch_used += amount
        allocations[ticker] = round(amount, 2)
        unallocated += raw_amount - amount

    if unallocated > 0.01:
        allocations["VFV.TO"] = round(allocations.get("VFV.TO", 0.0) + unallocated, 2)
    diff = round(config.monthly_capital - sum(allocations.values()), 2)
    if abs(diff) > 0.01:
        allocations["VFV.TO"] = round(allocations.get("VFV.TO", 0.0) + diff, 2)
    return {ticker: amount for ticker, amount in allocations.items() if amount > 0}


def _dynamic_backtest_score(row: dict[str, Any], prices: pd.Series, vfv_return: float | None) -> float:
    base = safe_float(row.get("capital_allocation_score")) or 0.0
    if len(prices) < 200:
        return base - 12
    price = safe_float(prices.iloc[-1]) or 0.0
    sma200 = prices.tail(200).mean()
    high_12m = prices.tail(252).max() if len(prices) >= 252 else prices.max()
    one_year = _one_year_return(prices)
    score = base
    if price >= sma200:
        score += 4
    else:
        score -= 8
    drawdown = price / high_12m - 1 if high_12m and high_12m > 0 else 0.0
    if -0.35 <= drawdown <= -0.10:
        score += 3
    elif drawdown < -0.45:
        score -= 10
    if one_year is not None and vfv_return is not None:
        relative = one_year - vfv_return
        if relative <= -0.15:
            score -= 5
        elif relative >= 0.15:
            score += 2
    return score


def _currently_eligible_for_backtest(row: dict[str, Any]) -> bool:
    if row.get("universe", "CORE_PORTFOLIO") != "CORE_PORTFOLIO":
        return False
    if str(row.get("ticker_validation_status") or "") in {"NO_MARKET_DATA", "POSSIBLE_WRONG_TICKER"}:
        return False
    if str(row.get("thesis_status") or "") != "INTACT":
        return False
    if str(row.get("liquidation_status") or "") not in {"GREEN", "YELLOW"}:
        return False
    if str(row.get("data_reliability_level") or "") == "LOW":
        return False
    if str(row.get("final_position_action") or "") in {"LIQUIDATE_PROGRESSIVELY", "LIQUIDATE_URGENT_REVIEW", "TRIM_50"}:
        return False
    return (safe_float(row.get("capital_allocation_score")) or 0.0) >= 35


def _load_latest_score_rows(
    reports_dir: str | Path,
    *,
    mode: str | None = None,
    strict_mode: bool = False,
) -> dict[str, dict[str, Any]]:
    rows = {}
    reports_dir = Path(reports_dir)
    if mode:
        if strict_mode:
            source_rows = read_csv_records(require_mode_artifact(reports_dir, "latest_scores.csv", mode, command_hint="analyze"))
        else:
            source_rows = read_mode_csv_if_exists(reports_dir, "latest_scores.csv", mode)
            if not source_rows:
                source_rows = read_csv_records(reports_dir / "latest_scores.csv")
    else:
        source_rows = read_csv_records(reports_dir / "latest_scores.csv")
    for row in source_rows:
        ticker = str(row.get("ticker") or "").strip().upper()
        if ticker:
            rows[ticker] = row
    return rows


def _latest_mandatory_vfv_percent(reports_dir: str | Path, mode: str | None = None) -> float:
    rows = read_mode_csv_if_exists(reports_dir, "latest_decision_quality.csv", mode) if mode else []
    if not rows and not mode:
        rows = read_csv_records(Path(reports_dir) / "latest_decision_quality.csv")
    if rows:
        value = safe_float(rows[0].get("vfv_mandatory_percent"))
        if value is not None:
            return value
    return 0.10


def _backtest_tickers(analyses: dict[str, dict[str, Any]]) -> list[str]:
    tickers = {"VFV.TO"}
    for ticker, row in analyses.items():
        if ticker and (_currently_eligible_for_backtest(row) or ticker == "VFV.TO"):
            tickers.add(ticker)
    return sorted(tickers)


def _total_return_price_frame(raw: pd.DataFrame, tickers: list[str]) -> tuple[pd.DataFrame, dict[str, str]]:
    if raw.empty:
        return pd.DataFrame(), {}
    frames = {}
    basis: dict[str, str] = {}
    if isinstance(raw.columns, pd.MultiIndex):
        for ticker in tickers:
            if (ticker, "Adj Close") in raw.columns and raw[(ticker, "Adj Close")].dropna().any():
                frames[ticker] = raw[(ticker, "Adj Close")]
                basis[ticker] = "ADJUSTED_CLOSE_TOTAL_RETURN_PROXY"
            elif (ticker, "Close") in raw.columns:
                frames[ticker] = raw[(ticker, "Close")]
                basis[ticker] = "PRICE_CLOSE"
        return pd.DataFrame(frames), basis
    if len(tickers) == 1:
        ticker = tickers[0]
        if "Adj Close" in raw.columns and raw["Adj Close"].dropna().any():
            return pd.DataFrame({ticker: raw["Adj Close"]}), {ticker: "ADJUSTED_CLOSE_TOTAL_RETURN_PROXY"}
        if "Close" in raw.columns:
            return pd.DataFrame({ticker: raw["Close"]}), {ticker: "PRICE_CLOSE"}
    return pd.DataFrame(), {}


def _overall_price_return_basis(price_basis_by_ticker: dict[str, str]) -> str:
    values = {basis for basis in price_basis_by_ticker.values() if basis}
    if not values:
        return "UNKNOWN_PRICE_BASIS"
    if values == {"ADJUSTED_CLOSE_TOTAL_RETURN_PROXY"}:
        return "ADJUSTED_CLOSE_TOTAL_RETURN_PROXY"
    if "ADJUSTED_CLOSE_TOTAL_RETURN_PROXY" in values:
        return "MIXED_ADJUSTED_CLOSE_AND_PRICE_CLOSE"
    return "PRICE_CLOSE"


def _actual_month_end_prices(prices: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, group in prices.groupby([prices.index.year, prices.index.month]):
        usable = group.dropna(how="all")
        if not usable.empty:
            rows.append(usable.iloc[[-1]])
    if not rows:
        return pd.DataFrame()
    return pd.concat(rows)


def _portfolio_value(holdings: dict[str, float], prices_on_date: pd.Series) -> float:
    total = 0.0
    for ticker, shares in holdings.items():
        price = safe_float(prices_on_date.get(ticker))
        if price is not None:
            total += shares * price
    return total


def _one_year_return(prices: pd.Series | None) -> float | None:
    if prices is None:
        return None
    clean = prices.dropna()
    if len(clean) < 252:
        return None
    current = safe_float(clean.iloc[-1])
    previous = safe_float(clean.iloc[-252])
    if current is None or previous is None or previous <= 0:
        return None
    return current / previous - 1


def _annualized_irr(cashflows: list[float]) -> float | None:
    if not cashflows or sum(1 for value in cashflows if value > 0) == 0 or sum(1 for value in cashflows if value < 0) == 0:
        return None
    low = -0.95
    high = 10.0

    def npv(rate: float) -> float:
        return sum(value / ((1 + rate) ** index) for index, value in enumerate(cashflows))

    low_value = npv(low)
    high_value = npv(high)
    if math.isnan(low_value) or math.isnan(high_value) or low_value * high_value > 0:
        return None
    for _ in range(100):
        mid = (low + high) / 2
        mid_value = npv(mid)
        if abs(mid_value) < 1e-6:
            monthly = mid
            return (1 + monthly) ** 12 - 1
        if low_value * mid_value <= 0:
            high = mid
            high_value = mid_value
        else:
            low = mid
            low_value = mid_value
    monthly = (low + high) / 2
    return (1 + monthly) ** 12 - 1


def _display_summary(row: dict[str, Any]) -> dict[str, Any]:
    return {
        **row,
        "total_contributed": money(safe_float(row.get("total_contributed"))),
        "final_value": money(safe_float(row.get("final_value"))),
        "vfv_final_value": money(safe_float(row.get("vfv_final_value"))),
        "excess_value_vs_vfv": money(safe_float(row.get("excess_value_vs_vfv"))),
        "price_return_basis": row.get("price_return_basis"),
        "money_weighted_annual_return": pct(safe_float(row.get("money_weighted_annual_return")), 2),
        "max_drawdown_on_capital_multiple": pct(safe_float(row.get("max_drawdown_on_capital_multiple")), 1),
        "avg_vfv_allocation": pct(safe_float(row.get("avg_vfv_allocation")), 1),
        "gross_return": pct(safe_float(row.get("gross_return")), 2),
        "estimated_transaction_cost_cad": money(safe_float(row.get("estimated_transaction_cost_cad"))),
        "net_return_after_friction": pct(safe_float(row.get("net_return_after_friction")), 2),
        "friction_drag": pct(safe_float(row.get("friction_drag")), 2),
        "friction_assumption_status": row.get("friction_assumption_status"),
    }


def _display_benchmark_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        **row,
        "benchmark_final_value": money(safe_float(row.get("benchmark_final_value"))),
        "benchmark_return": pct(safe_float(row.get("benchmark_return")), 2),
        "excess_value_vs_benchmark": money(safe_float(row.get("excess_value_vs_benchmark"))),
        "model_return_minus_benchmark_return": pct(safe_float(row.get("model_return_minus_benchmark_return")), 2),
    }


def _markdown_table(headers: list[str], rows: list[dict[str, Any]]) -> str:
    if not rows:
        rows = [{header: "" for header in headers}]
    header_line = "| " + " | ".join(headers) + " |"
    separator = "| " + " | ".join(["---"] * len(headers)) + " |"
    body = []
    for row in rows:
        body.append("| " + " | ".join(str(row.get(header, "")).replace("|", "/") for header in headers) + " |")
    return "\n".join([header_line, separator, *body])
