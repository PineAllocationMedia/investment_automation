from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import math

import pandas as pd

from .utils import CONFIG_DIR, load_yaml, safe_float


DEFAULT_BENCHMARK_CONFIG = {
    "benchmarks": {
        "VFV_100": {
            "name": "100 % VFV.TO",
            "type": "STATIC_WEIGHTS",
            "components": {"VFV.TO": 1.0},
            "primary": True,
        },
        "XEQT_100": {
            "name": "100 % XEQT.TO",
            "type": "STATIC_WEIGHTS",
            "components": {"XEQT.TO": 1.0},
        },
        "CANADIAN_60_40": {
            "name": "Canadian 60/40",
            "type": "STATIC_WEIGHTS",
            "components": {"XEQT.TO": 0.60, "ZAG.TO": 0.40},
        },
        "SIMPLE_MOMENTUM": {
            "name": "Simple ETF momentum",
            "type": "SIMPLE_MOMENTUM",
            "universe": ["VFV.TO", "XEQT.TO", "XQQ.TO", "XIC.TO", "ZAG.TO"],
            "lookback_months": 6,
            "top_n": 1,
        },
    }
}


BACKTEST_BENCHMARK_COLUMNS = [
    "period_years",
    "benchmark_id",
    "benchmark_name",
    "benchmark_type",
    "components",
    "data_coverage_status",
    "unavailable_reason",
    "benchmark_final_value",
    "benchmark_return",
    "benchmark_max_drawdown",
    "model_final_value",
    "model_return",
    "excess_value_vs_benchmark",
    "model_return_minus_benchmark_return",
    "price_return_basis",
]

WALK_FORWARD_BENCHMARK_COLUMNS = [
    "mode",
    "analysis_date",
    "next_analysis_date",
    "days_held",
    "benchmark_id",
    "benchmark_name",
    "benchmark_type",
    "selected_components",
    "data_coverage_status",
    "unavailable_reason",
    "strategy_period_return",
    "benchmark_period_return",
    "model_excess_return_vs_benchmark",
    "win_loss_vs_benchmark",
]


@dataclass(frozen=True)
class BenchmarkDefinition:
    benchmark_id: str
    name: str
    benchmark_type: str
    components: dict[str, float]
    universe: list[str]
    lookback_months: int = 6
    top_n: int = 1
    primary: bool = False


def load_benchmark_definitions(path: str | Path | None = None) -> list[BenchmarkDefinition]:
    """Load audit benchmark definitions used by backtest and walk-forward comparisons."""
    config_path = Path(path) if path else CONFIG_DIR / "backtest_benchmarks.yaml"
    payload = load_yaml(config_path) if config_path.exists() else {}
    raw_benchmarks = payload.get("benchmarks") if isinstance(payload, dict) else None
    if not isinstance(raw_benchmarks, dict) or not raw_benchmarks:
        raw_benchmarks = DEFAULT_BENCHMARK_CONFIG["benchmarks"]

    definitions: list[BenchmarkDefinition] = []
    for benchmark_id, raw in raw_benchmarks.items():
        if not isinstance(raw, dict):
            continue
        benchmark_type = str(raw.get("type") or "STATIC_WEIGHTS").strip().upper()
        components = _normalized_weights(raw.get("components", {}))
        universe = _ticker_list(raw.get("universe", []))
        if benchmark_type == "STATIC_WEIGHTS" and not components:
            continue
        if benchmark_type == "SIMPLE_MOMENTUM" and not universe:
            continue
        definitions.append(
            BenchmarkDefinition(
                benchmark_id=str(benchmark_id).strip().upper(),
                name=str(raw.get("name") or benchmark_id),
                benchmark_type=benchmark_type,
                components=components,
                universe=universe,
                lookback_months=max(1, int(safe_float(raw.get("lookback_months")) or 6)),
                top_n=max(1, int(safe_float(raw.get("top_n")) or 1)),
                primary=bool(raw.get("primary", False)),
            )
        )
    return definitions


def benchmark_price_tickers(definitions: list[BenchmarkDefinition] | None = None) -> list[str]:
    definitions = definitions or load_benchmark_definitions()
    tickers: set[str] = set()
    for definition in definitions:
        tickers.update(definition.components)
        tickers.update(definition.universe)
    return sorted(ticker for ticker in tickers if ticker)


def build_backtest_benchmark_comparisons(
    summaries: list[dict[str, Any]],
    monthly_rows: list[dict[str, Any]],
    monthly_prices: pd.DataFrame,
    monthly_capital: float,
    definitions: list[BenchmarkDefinition] | None = None,
    price_return_basis: str = "",
) -> list[dict[str, Any]]:
    definitions = definitions or load_benchmark_definitions()
    rows: list[dict[str, Any]] = []
    for summary in summaries:
        period_years = int(safe_float(summary.get("period_years")) or 0)
        period_months = int(safe_float(summary.get("months")) or period_years * 12)
        period_dates = _period_dates(monthly_rows, period_years)
        if not period_dates and period_months > 0:
            period_dates = list(monthly_prices.index[-period_months:])
        for definition in definitions:
            benchmark = simulate_monthly_benchmark(
                monthly_prices,
                period_dates,
                monthly_capital,
                definition,
            )
            model_return = safe_float(summary.get("money_weighted_annual_return"))
            benchmark_return = safe_float(benchmark.get("benchmark_return"))
            model_final = safe_float(summary.get("final_value"))
            benchmark_final = safe_float(benchmark.get("benchmark_final_value"))
            rows.append(
                {
                    "period_years": period_years,
                    "benchmark_id": definition.benchmark_id,
                    "benchmark_name": definition.name,
                    "benchmark_type": definition.benchmark_type,
                    "components": benchmark.get("components", ""),
                    "data_coverage_status": benchmark.get("data_coverage_status"),
                    "unavailable_reason": benchmark.get("unavailable_reason", ""),
                    "benchmark_final_value": _round_or_blank(benchmark_final, 2),
                    "benchmark_return": _round_or_blank(benchmark_return, 4),
                    "benchmark_max_drawdown": _round_or_blank(benchmark.get("benchmark_max_drawdown"), 4),
                    "model_final_value": _round_or_blank(model_final, 2),
                    "model_return": _round_or_blank(model_return, 4),
                    "excess_value_vs_benchmark": _round_or_blank(model_final - benchmark_final if model_final is not None and benchmark_final is not None else None, 2),
                    "model_return_minus_benchmark_return": _round_or_blank(
                        model_return - benchmark_return if model_return is not None and benchmark_return is not None else None,
                        4,
                    ),
                    "price_return_basis": price_return_basis,
                }
            )
    return rows


def simulate_monthly_benchmark(
    monthly_prices: pd.DataFrame,
    period_dates: list[pd.Timestamp],
    monthly_capital: float,
    definition: BenchmarkDefinition,
) -> dict[str, Any]:
    if not period_dates:
        return _unavailable_benchmark(definition, "INSUFFICIENT_PRICE_HISTORY", "Aucune date mensuelle disponible.")
    prices = monthly_prices.sort_index().ffill()
    period_dates = [date for date in period_dates if date in prices.index]
    if not period_dates:
        return _unavailable_benchmark(definition, "INSUFFICIENT_PRICE_HISTORY", "Aucun prix disponible aux dates mensuelles.")

    if definition.benchmark_type == "SIMPLE_MOMENTUM":
        status, reason = _momentum_universe_coverage_status(prices, definition)
        if status != "AVAILABLE":
            return _unavailable_benchmark(definition, status, reason)
        allocations_by_date = _momentum_monthly_allocations(prices, period_dates, definition)
        if not allocations_by_date:
            return _unavailable_benchmark(definition, "INSUFFICIENT_PRICE_HISTORY", "Historique momentum insuffisant.")
        if len(allocations_by_date) < len(period_dates):
            return _unavailable_benchmark(
                definition,
                "PARTIAL_HISTORY",
                "Certaines dates n'avaient pas assez d'historique préalable pour le momentum.",
            )
        status = "AVAILABLE"
        reason = ""
    else:
        status, reason = _static_coverage_status(prices, period_dates, definition)
        if status != "AVAILABLE":
            return _unavailable_benchmark(definition, status, reason)
        allocations_by_date = {date: definition.components for date in period_dates}

    holdings: dict[str, float] = {}
    contributed = 0.0
    cashflows: list[float] = []
    multiples: list[float] = []
    peak_multiple = 0.0
    for date in period_dates:
        weights = allocations_by_date.get(date)
        if not weights:
            continue
        contributed += monthly_capital
        cashflows.append(-monthly_capital)
        for ticker, weight in weights.items():
            price = safe_float(prices.at[date, ticker]) if ticker in prices.columns else None
            if price is None or price <= 0:
                continue
            amount = monthly_capital * weight
            holdings[ticker] = holdings.get(ticker, 0.0) + amount / price
        value = _holdings_value(holdings, prices.loc[date])
        multiple = value / contributed if contributed > 0 else 1.0
        peak_multiple = max(peak_multiple, multiple)
        drawdown = multiple / peak_multiple - 1.0 if peak_multiple > 0 else 0.0
        multiples.append(drawdown)

    final_value = _holdings_value(holdings, prices.loc[period_dates[-1]]) if contributed > 0 else None
    if final_value is None or contributed <= 0:
        return _unavailable_benchmark(definition, "INSUFFICIENT_PRICE_HISTORY", "Aucune contribution benchmark simulable.")
    cashflows.append(final_value)
    return {
        "benchmark_final_value": final_value,
        "benchmark_return": _annualized_irr(cashflows),
        "benchmark_max_drawdown": min(multiples) if multiples else 0.0,
        "data_coverage_status": status,
        "unavailable_reason": reason,
        "components": _component_text(allocations_by_date.get(period_dates[-1], definition.components)),
    }


def build_walk_forward_benchmark_comparisons(
    period_rows: list[dict[str, Any]],
    prices: pd.DataFrame,
    definitions: list[BenchmarkDefinition] | None = None,
) -> list[dict[str, Any]]:
    definitions = definitions or load_benchmark_definitions()
    rows: list[dict[str, Any]] = []
    clean_prices = prices.sort_index().ffill().dropna(how="all")
    for period in period_rows:
        if str(period.get("evaluation_status") or "") not in {"SIMULATED", "SIMULATED_WITH_PARTIAL_PRICE_DATA"}:
            continue
        strategy_return = safe_float(period.get("strategy_period_return"))
        for definition in definitions:
            benchmark = benchmark_period_return(
                clean_prices,
                str(period.get("analysis_date") or ""),
                str(period.get("next_analysis_date") or ""),
                definition,
            )
            benchmark_return = safe_float(benchmark.get("benchmark_period_return"))
            excess = strategy_return - benchmark_return if strategy_return is not None and benchmark_return is not None else None
            rows.append(
                {
                    "mode": period.get("mode", ""),
                    "analysis_date": period.get("analysis_date", ""),
                    "next_analysis_date": period.get("next_analysis_date", ""),
                    "days_held": period.get("days_held", ""),
                    "benchmark_id": definition.benchmark_id,
                    "benchmark_name": definition.name,
                    "benchmark_type": definition.benchmark_type,
                    "selected_components": benchmark.get("selected_components", ""),
                    "data_coverage_status": benchmark.get("data_coverage_status"),
                    "unavailable_reason": benchmark.get("unavailable_reason", ""),
                    "strategy_period_return": _round_or_blank(strategy_return, 4),
                    "benchmark_period_return": _round_or_blank(benchmark_return, 4),
                    "model_excess_return_vs_benchmark": _round_or_blank(excess, 4),
                    "win_loss_vs_benchmark": _win_loss(excess),
                }
            )
    return rows


def benchmark_period_return(
    prices: pd.DataFrame,
    start_date: str,
    end_date: str,
    definition: BenchmarkDefinition,
) -> dict[str, Any]:
    if definition.benchmark_type == "SIMPLE_MOMENTUM":
        status, reason = _momentum_universe_coverage_status(prices, definition)
        if status != "AVAILABLE":
            return {
                "data_coverage_status": status,
                "unavailable_reason": reason,
                "selected_components": ", ".join(definition.universe),
            }
        weights = _momentum_weights_for_date(prices, pd.Timestamp(start_date), definition)
        if not weights:
            return {
                "data_coverage_status": "INSUFFICIENT_PRICE_HISTORY",
                "unavailable_reason": "Historique préalable insuffisant pour sélectionner le benchmark momentum.",
                "selected_components": "",
            }
        selected_components = _component_text(weights)
    else:
        status, reason = _static_period_coverage_status(prices, start_date, end_date, definition)
        if status != "AVAILABLE":
            return {"data_coverage_status": status, "unavailable_reason": reason, "selected_components": _component_text(definition.components)}
        weights = definition.components
        selected_components = _component_text(weights)

    weighted_return = 0.0
    for ticker, weight in weights.items():
        result = _ticker_period_return(prices, ticker, start_date, end_date)
        if result is None:
            return {
                "data_coverage_status": "INSUFFICIENT_PRICE_HISTORY",
                "unavailable_reason": f"Prix manquant pour {ticker}.",
                "selected_components": selected_components,
            }
        weighted_return += weight * result
    return {
        "benchmark_period_return": weighted_return,
        "data_coverage_status": "AVAILABLE",
        "unavailable_reason": "",
        "selected_components": selected_components,
    }


def _normalized_weights(raw: Any) -> dict[str, float]:
    if not isinstance(raw, dict):
        return {}
    weights = {str(ticker).strip().upper(): safe_float(weight) or 0.0 for ticker, weight in raw.items()}
    weights = {ticker: weight for ticker, weight in weights.items() if ticker and weight > 0}
    total = sum(weights.values())
    if total <= 0:
        return {}
    return {ticker: weight / total for ticker, weight in weights.items()}


def _ticker_list(raw: Any) -> list[str]:
    if not isinstance(raw, list):
        return []
    return [ticker for ticker in (str(item).strip().upper() for item in raw) if ticker]


def _period_dates(monthly_rows: list[dict[str, Any]], period_years: int) -> list[pd.Timestamp]:
    dates = [
        pd.Timestamp(str(row.get("date")))
        for row in monthly_rows
        if int(safe_float(row.get("period_years")) or 0) == period_years and row.get("date")
    ]
    return sorted(set(dates))


def _static_coverage_status(
    prices: pd.DataFrame,
    period_dates: list[pd.Timestamp],
    definition: BenchmarkDefinition,
) -> tuple[str, str]:
    for ticker in definition.components:
        if ticker not in prices.columns:
            return "INSUFFICIENT_PRICE_HISTORY", f"{ticker} absent des prix disponibles."
        available = prices[ticker].dropna()
        if available.empty:
            return "INSUFFICIENT_PRICE_HISTORY", f"{ticker} sans historique de prix."
        if available.index[0] > period_dates[0]:
            return "PARTIAL_HISTORY", f"{ticker} commence après le début de la période."
        if available.index[-1] < period_dates[-1]:
            return "PARTIAL_HISTORY", f"{ticker} se termine avant la fin de la période."
        missing_dates = [date for date in period_dates if safe_float(prices.at[date, ticker]) is None]
        if missing_dates:
            return "PARTIAL_HISTORY", f"{ticker} manque des prix mensuels dans la période."
    return "AVAILABLE", ""


def _static_period_coverage_status(
    prices: pd.DataFrame,
    start_date: str,
    end_date: str,
    definition: BenchmarkDefinition,
) -> tuple[str, str]:
    for ticker in definition.components:
        if _ticker_period_return(prices, ticker, start_date, end_date) is None:
            return "INSUFFICIENT_PRICE_HISTORY", f"Prix période indisponibles pour {ticker}."
    return "AVAILABLE", ""


def _momentum_monthly_allocations(
    prices: pd.DataFrame,
    period_dates: list[pd.Timestamp],
    definition: BenchmarkDefinition,
) -> dict[pd.Timestamp, dict[str, float]]:
    allocations: dict[pd.Timestamp, dict[str, float]] = {}
    for date in period_dates:
        weights = _momentum_weights_for_date(prices, date, definition)
        if weights:
            allocations[date] = weights
    return allocations


def _momentum_universe_coverage_status(prices: pd.DataFrame, definition: BenchmarkDefinition) -> tuple[str, str]:
    missing = [ticker for ticker in definition.universe if ticker not in prices.columns]
    if missing:
        return "PARTIAL_HISTORY", "Tickers momentum absents des prix disponibles: " + ", ".join(missing)
    for ticker in definition.universe:
        if prices[ticker].dropna().empty:
            return "INSUFFICIENT_PRICE_HISTORY", f"{ticker} sans historique de prix momentum."
    return "AVAILABLE", ""


def _momentum_weights_for_date(
    prices: pd.DataFrame,
    decision_date: pd.Timestamp,
    definition: BenchmarkDefinition,
) -> dict[str, float]:
    lookback_points = _momentum_lookback_points(prices, definition.lookback_months)
    scored: list[tuple[float, str]] = []
    for ticker in definition.universe:
        if ticker not in prices.columns:
            continue
        history = prices[ticker].dropna()
        history = history[history.index < decision_date]
        if len(history) <= lookback_points:
            continue
        current = safe_float(history.iloc[-1])
        past = safe_float(history.iloc[-lookback_points])
        if current is None or past is None or past <= 0:
            continue
        scored.append((current / past - 1.0, ticker))
    if not scored:
        return {}
    selected = [ticker for _, ticker in sorted(scored, reverse=True)[: definition.top_n]]
    weight = 1.0 / len(selected)
    return {ticker: weight for ticker in selected}


def _momentum_lookback_points(prices: pd.DataFrame, lookback_months: int) -> int:
    clean_index = prices.sort_index().dropna(how="all").index
    if len(clean_index) < 3:
        return max(1, int(lookback_months))
    gaps = pd.Series(clean_index).diff().dropna()
    median_gap_days = gaps.median().days if not gaps.empty else 1
    if median_gap_days >= 15:
        return max(1, int(lookback_months))
    return max(1, int(lookback_months * 21))


def _ticker_period_return(prices: pd.DataFrame, ticker: str, start_date: str, end_date: str) -> float | None:
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
    return end_price / start_price - 1.0


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


def _holdings_value(holdings: dict[str, float], prices_on_date: pd.Series) -> float:
    total = 0.0
    for ticker, shares in holdings.items():
        price = safe_float(prices_on_date.get(ticker))
        if price is not None:
            total += shares * price
    return total


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
            return (1 + mid) ** 12 - 1
        if low_value * mid_value <= 0:
            high = mid
            high_value = mid_value
        else:
            low = mid
            low_value = mid_value
    return (1 + ((low + high) / 2)) ** 12 - 1


def _component_text(weights: dict[str, float]) -> str:
    return ", ".join(f"{ticker}:{weight:.0%}" for ticker, weight in sorted(weights.items()))


def _unavailable_benchmark(definition: BenchmarkDefinition, status: str, reason: str) -> dict[str, Any]:
    return {
        "benchmark_final_value": None,
        "benchmark_return": None,
        "benchmark_max_drawdown": None,
        "data_coverage_status": status,
        "unavailable_reason": reason,
        "components": _component_text(definition.components) if definition.components else ", ".join(definition.universe),
    }


def _round_or_blank(value: Any, digits: int) -> Any:
    number = safe_float(value)
    if number is None:
        return ""
    return round(number, digits)


def _win_loss(excess: float | None) -> str:
    if excess is None:
        return "UNAVAILABLE"
    if excess > 0:
        return "WIN"
    if excess < 0:
        return "LOSS"
    return "TIE"
