from __future__ import annotations

from pathlib import Path
from typing import Any

from .utils import CONFIG_DIR, load_yaml, safe_float
from .model_identity import IDENTITY_FIELDS, evidence_cohort, identity_fields


BACKTEST_FRICTION_AUDIT_COLUMNS = [
    *IDENTITY_FIELDS, "baseline_id", "run_id",
    "audit_scope",
    "mode",
    "period_years",
    "analysis_date",
    "next_analysis_date",
    "gross_return",
    "gross_value_cad",
    "total_notional_cad",
    "estimated_transaction_cost_cad",
    "net_value_after_friction_cad",
    "net_return_after_friction",
    "friction_drag",
    "friction_assumption_status",
    "trade_count",
    "fx_trade_count",
    "illiquid_trade_count",
    "small_trade_count",
    "interpretation",
]

DEFAULT_FRICTION_CONFIG = {
    "enabled": True,
    "commission_cad_per_trade": 0.0,
    "spread_bps_default": 8.0,
    "spread_bps_illiquid": 25.0,
    "fx_fee_bps": 150.0,
    "minimum_trade_value_cad": 25.0,
    "walk_forward_default_notional_cad": 1000.0,
    "illiquid_tickers": [],
}


def load_transaction_friction_config(path: str | Path | None = None) -> dict[str, Any]:
    config_path = Path(path) if path else CONFIG_DIR / "transaction_friction.yaml"
    loaded = load_yaml(config_path) if config_path.exists() else {}
    config = {**DEFAULT_FRICTION_CONFIG, **(loaded or {})}
    config["illiquid_tickers"] = [str(ticker).strip().upper() for ticker in config.get("illiquid_tickers") or []]
    return config


def estimate_trade_friction(
    ticker: str,
    trade_value_cad: float,
    ticker_context: dict[str, Any] | None = None,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    config = config or load_transaction_friction_config()
    ticker_context = ticker_context or {}
    ticker = str(ticker or "").strip().upper()
    trade_value = max(0.0, safe_float(trade_value_cad) or 0.0)
    if not config.get("enabled", True) or trade_value <= 0:
        return _empty_trade_result(ticker)

    commission = max(0.0, safe_float(config.get("commission_cad_per_trade")) or 0.0)
    minimum_trade = max(0.0, safe_float(config.get("minimum_trade_value_cad")) or 0.0)
    is_small = bool(minimum_trade and trade_value < minimum_trade)
    is_illiquid = _is_illiquid_trade(ticker, trade_value, ticker_context, config, is_small)
    spread_bps = safe_float(config.get("spread_bps_illiquid" if is_illiquid else "spread_bps_default")) or 0.0
    spread_cost = trade_value * max(0.0, spread_bps) / 10000.0

    currency = _ticker_currency(ticker, ticker_context)
    is_fx = currency not in {"", "CAD"}
    fx_bps = safe_float(config.get("fx_fee_bps")) or 0.0
    fx_cost = trade_value * max(0.0, fx_bps) / 10000.0 if is_fx else 0.0
    total = commission + spread_cost + fx_cost

    flags = []
    if is_fx:
        flags.append("FX_ESTIMATE")
    if is_illiquid:
        flags.append("ILLIQUID_OR_SMALL_SPREAD")
    if is_small:
        flags.append("SMALL_TRADE")
    status = "APPROXIMATE_" + "_".join(flags) if flags else "APPROXIMATE_STANDARD"
    return {
        "ticker": ticker,
        "trade_value_cad": round(trade_value, 2),
        "estimated_transaction_cost_cad": round(total, 4),
        "commission_cad": round(commission, 4),
        "spread_cost_cad": round(spread_cost, 4),
        "fx_cost_cad": round(fx_cost, 4),
        "is_fx_trade": is_fx,
        "is_illiquid_trade": is_illiquid,
        "is_small_trade": is_small,
        "friction_assumption_status": status,
    }


def build_theoretical_backtest_friction_rows(
    summaries: list[dict[str, Any]],
    allocation_rows: list[dict[str, Any]],
    analyses: dict[str, dict[str, Any]] | None = None,
    config: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    config = config or load_transaction_friction_config()
    analyses = analyses or {}
    allocations_by_period: dict[int, list[dict[str, Any]]] = {}
    for row in allocation_rows:
        period = int(safe_float(row.get("period_years")) or 0)
        allocations_by_period.setdefault(period, []).append(row)

    rows = []
    for summary in summaries:
        period = int(safe_float(summary.get("period_years")) or 0)
        allocations = allocations_by_period.get(period, [])
        friction = estimate_allocation_friction(
            allocations,
            analyses,
            config,
            amount_key="amount",
            fallback_notional=0.0,
        )
        total_contributed = safe_float(summary.get("total_contributed")) or 0.0
        gross_value = safe_float(summary.get("final_value")) or 0.0
        rows.append(
            _audit_row(
                audit_scope="THEORETICAL_BACKTEST",
                mode=str(summary.get("strategy") or ""),
                period_years=period,
                gross_value=gross_value,
                total_notional=total_contributed,
                transaction_cost=friction["estimated_transaction_cost_cad"],
                trade_count=friction["trade_count"],
                fx_trade_count=friction["fx_trade_count"],
                illiquid_trade_count=friction["illiquid_trade_count"],
                small_trade_count=friction["small_trade_count"],
                status=_aggregate_status(friction),
            )
        )
    return rows


def build_walk_forward_friction_rows(
    summary_row: dict[str, Any],
    period_rows: list[dict[str, Any]],
    allocation_return_rows: list[dict[str, Any]],
    config: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    config = config or load_transaction_friction_config()
    rows = []
    by_period: dict[tuple[str, ...], list[dict[str, Any]]] = {}
    for row in allocation_return_rows:
        key = _walk_forward_evidence_key(row)
        by_period.setdefault(key, []).append(row)

    for period in period_rows:
        if str(period.get("evaluation_status") or "") not in {"SIMULATED", "SIMULATED_WITH_PARTIAL_PRICE_DATA"}:
            continue
        key = _walk_forward_evidence_key(period)
        allocation_rows = by_period.get(key, [])
        total_notional = _walk_forward_notional(allocation_rows, config)
        friction = estimate_allocation_friction(
            allocation_rows,
            {},
            config,
            amount_key="trade_value_cad",
            weight_key="allocation_weight",
            fallback_notional=total_notional,
        )
        rows.append(
            _audit_row(
                audit_scope="WALK_FORWARD_PERIOD",
                mode=str(period.get("mode") or ""),
                period_years="",
                analysis_date=str(period.get("analysis_date") or ""),
                next_analysis_date=str(period.get("next_analysis_date") or ""),
                gross_return=safe_float(period.get("strategy_period_return")),
                gross_value=total_notional * (1.0 + (safe_float(period.get("strategy_period_return")) or 0.0)),
                total_notional=total_notional,
                transaction_cost=friction["estimated_transaction_cost_cad"],
                trade_count=friction["trade_count"],
                fx_trade_count=friction["fx_trade_count"],
                illiquid_trade_count=friction["illiquid_trade_count"],
                small_trade_count=friction["small_trade_count"],
                status=_aggregate_status(friction),
            )
        )

        rows[-1].update(identity_fields(period), baseline_id=period.get("baseline_id", ""), run_id=period.get("run_id", ""))

    simulated_count = int(safe_float(summary_row.get("simulated_periods")) or 0)
    if simulated_count:
        total_cost = sum(safe_float(row.get("estimated_transaction_cost_cad")) or 0.0 for row in rows)
        total_notional = sum(safe_float(row.get("total_notional_cad")) or 0.0 for row in rows)
        gross_return = safe_float(summary_row.get("compounded_strategy_return"))
        gross_value = total_notional * (1.0 + (gross_return or 0.0)) if total_notional > 0 else 0.0
        rows.insert(
            0,
            _audit_row(
                audit_scope="WALK_FORWARD_SUMMARY",
                mode=str(summary_row.get("mode") or ""),
                period_years="",
                gross_return=gross_return,
                gross_value=gross_value,
                total_notional=total_notional,
                transaction_cost=total_cost,
                trade_count=sum(int(safe_float(row.get("trade_count")) or 0) for row in rows),
                fx_trade_count=sum(int(safe_float(row.get("fx_trade_count")) or 0) for row in rows),
                illiquid_trade_count=sum(int(safe_float(row.get("illiquid_trade_count")) or 0) for row in rows),
                small_trade_count=sum(int(safe_float(row.get("small_trade_count")) or 0) for row in rows),
                status="APPROXIMATE_WALK_FORWARD_SUMMARY",
            ),
        )
    return rows


def estimate_allocation_friction(
    allocation_rows: list[dict[str, Any]],
    analyses: dict[str, dict[str, Any]],
    config: dict[str, Any],
    *,
    amount_key: str,
    weight_key: str = "percentage",
    fallback_notional: float = 0.0,
) -> dict[str, Any]:
    total_cost = 0.0
    trade_count = 0
    fx_count = 0
    illiquid_count = 0
    small_count = 0
    for row in allocation_rows:
        ticker = str(row.get("ticker") or row.get("destination") or "").strip().upper()
        if not ticker:
            continue
        amount = safe_float(row.get(amount_key))
        if amount is None and fallback_notional > 0:
            amount = fallback_notional * (safe_float(row.get(weight_key)) or 0.0)
        if amount is None or amount <= 0:
            continue
        context = analyses.get(ticker, row)
        trade = estimate_trade_friction(ticker, amount, context, config)
        total_cost += safe_float(trade.get("estimated_transaction_cost_cad")) or 0.0
        trade_count += 1
        fx_count += 1 if trade.get("is_fx_trade") else 0
        illiquid_count += 1 if trade.get("is_illiquid_trade") else 0
        small_count += 1 if trade.get("is_small_trade") else 0
    return {
        "estimated_transaction_cost_cad": round(total_cost, 2),
        "trade_count": trade_count,
        "fx_trade_count": fx_count,
        "illiquid_trade_count": illiquid_count,
        "small_trade_count": small_count,
    }


def add_friction_fields_to_backtest_summaries(
    summaries: list[dict[str, Any]],
    friction_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    by_period = {str(row.get("period_years")): row for row in friction_rows if row.get("audit_scope") == "THEORETICAL_BACKTEST"}
    output = []
    for summary in summaries:
        row = dict(summary)
        friction = by_period.get(str(summary.get("period_years"))) or {}
        row.update(_friction_summary_fields(friction))
        output.append(row)
    return output


def add_friction_fields_to_walk_forward_periods(
    period_rows: list[dict[str, Any]],
    friction_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    by_period = {
        _walk_forward_evidence_key(row): row
        for row in friction_rows
        if row.get("audit_scope") == "WALK_FORWARD_PERIOD"
    }
    output = []
    for period in period_rows:
        row = dict(period)
        friction = by_period.get(_walk_forward_evidence_key(row)) or {}
        row.update(_friction_period_fields(friction))
        output.append(row)
    return output


def add_friction_fields_to_walk_forward_summary(
    summary_row: dict[str, Any],
    friction_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    row = dict(summary_row)
    friction = next((item for item in friction_rows if item.get("audit_scope") == "WALK_FORWARD_SUMMARY"), {})
    row.update(_friction_summary_fields(friction))
    return row


def merge_friction_audit_rows(
    existing_rows: list[dict[str, Any]],
    new_rows: list[dict[str, Any]],
    scopes_to_replace: set[str],
) -> list[dict[str, Any]]:
    kept = [row for row in existing_rows if str(row.get("audit_scope") or "") not in scopes_to_replace]
    return kept + new_rows


def friction_compact_alert(rows: list[dict[str, Any]], *, drag_threshold: float = 0.01) -> str:
    if not rows:
        return ""
    high_drag = [row for row in rows if (safe_float(row.get("friction_drag")) or 0.0) >= drag_threshold]
    if not high_drag:
        return ""
    worst = max(high_drag, key=lambda row: safe_float(row.get("friction_drag")) or 0.0)
    return (
        "AUDIT-ONLY — aucune recommandation modifiée. "
        f"Les frictions estimées changent sensiblement l’interprétation du backtest "
        f"({worst.get('audit_scope')}: drag {round((safe_float(worst.get('friction_drag')) or 0.0) * 100, 2)}%)."
    )


def _friction_summary_fields(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "gross_return": row.get("gross_return", ""),
        "estimated_transaction_cost_cad": row.get("estimated_transaction_cost_cad", ""),
        "net_return_after_friction": row.get("net_return_after_friction", ""),
        "friction_drag": row.get("friction_drag", ""),
        "friction_assumption_status": row.get("friction_assumption_status", ""),
    }


def _friction_period_fields(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "estimated_transaction_cost_cad": row.get("estimated_transaction_cost_cad", ""),
        "net_strategy_period_return_after_friction": row.get("net_return_after_friction", ""),
        "friction_drag": row.get("friction_drag", ""),
        "friction_assumption_status": row.get("friction_assumption_status", ""),
    }


def _audit_row(
    *,
    audit_scope: str,
    mode: str,
    period_years: Any,
    gross_value: float,
    total_notional: float,
    transaction_cost: float,
    trade_count: int,
    fx_trade_count: int,
    illiquid_trade_count: int,
    small_trade_count: int,
    status: str,
    analysis_date: str = "",
    next_analysis_date: str = "",
    gross_return: float | None = None,
) -> dict[str, Any]:
    total_notional = max(0.0, safe_float(total_notional) or 0.0)
    gross_value = max(0.0, safe_float(gross_value) or 0.0)
    transaction_cost = max(0.0, safe_float(transaction_cost) or 0.0)
    if gross_return is None and total_notional > 0:
        gross_return = gross_value / total_notional - 1.0
    net_value = max(0.0, gross_value - transaction_cost)
    net_return = net_value / total_notional - 1.0 if total_notional > 0 else None
    drag = (gross_return - net_return) if gross_return is not None and net_return is not None else None
    return {
        "audit_scope": audit_scope,
        "mode": mode,
        "period_years": period_years,
        "analysis_date": analysis_date,
        "next_analysis_date": next_analysis_date,
        "gross_return": round(gross_return, 4) if gross_return is not None else "",
        "gross_value_cad": round(gross_value, 2),
        "total_notional_cad": round(total_notional, 2),
        "estimated_transaction_cost_cad": round(transaction_cost, 2),
        "net_value_after_friction_cad": round(net_value, 2),
        "net_return_after_friction": round(net_return, 4) if net_return is not None else "",
        "friction_drag": round(drag, 4) if drag is not None else "",
        "friction_assumption_status": status,
        "trade_count": trade_count,
        "fx_trade_count": fx_trade_count,
        "illiquid_trade_count": illiquid_trade_count,
        "small_trade_count": small_trade_count,
        "interpretation": _interpretation(audit_scope, drag, status),
    }


def _interpretation(audit_scope: str, drag: float | None, status: str) -> str:
    if drag is None:
        return "Données insuffisantes pour convertir les frictions en rendement net."
    if drag >= 0.02:
        level = "drag élevé"
    elif drag >= 0.01:
        level = "drag notable"
    elif drag >= 0.003:
        level = "drag modéré"
    else:
        level = "drag faible"
    return f"{level}; lecture audit-only pour {audit_scope}. Statut hypothèses: {status}. Aucune recommandation modifiée."


def _empty_trade_result(ticker: str) -> dict[str, Any]:
    return {
        "ticker": ticker,
        "trade_value_cad": 0.0,
        "estimated_transaction_cost_cad": 0.0,
        "commission_cad": 0.0,
        "spread_cost_cad": 0.0,
        "fx_cost_cad": 0.0,
        "is_fx_trade": False,
        "is_illiquid_trade": False,
        "is_small_trade": False,
        "friction_assumption_status": "DISABLED_OR_ZERO_TRADE",
    }


def _aggregate_status(friction: dict[str, Any]) -> str:
    if not friction.get("trade_count"):
        return "NO_TRADES_TO_ESTIMATE"
    flags = []
    if friction.get("fx_trade_count"):
        flags.append("FX")
    if friction.get("illiquid_trade_count"):
        flags.append("ILLIQUID")
    if friction.get("small_trade_count"):
        flags.append("SMALL_TRADES")
    return "APPROXIMATE_" + "_".join(flags) if flags else "APPROXIMATE_STANDARD"


def _is_illiquid_trade(
    ticker: str,
    trade_value: float,
    ticker_context: dict[str, Any],
    config: dict[str, Any],
    is_small: bool,
) -> bool:
    if ticker in set(config.get("illiquid_tickers") or []):
        return True
    if ticker.endswith(".V"):
        return True
    if is_small:
        return True
    market_cap = safe_float(ticker_context.get("market_cap") or ticker_context.get("marketCap"))
    if market_cap is not None and market_cap > 0 and market_cap < 500_000_000:
        return True
    return False


def _ticker_currency(ticker: str, ticker_context: dict[str, Any]) -> str:
    currency = str(ticker_context.get("quote_currency") or ticker_context.get("currency") or "").strip().upper()
    if currency:
        return currency
    if ticker.endswith(".TO") or ticker.endswith(".V"):
        return "CAD"
    return "USD"


def _walk_forward_notional(allocation_rows: list[dict[str, Any]], config: dict[str, Any]) -> float:
    amounts = [safe_float(row.get("trade_value_cad")) for row in allocation_rows]
    amount_total = sum(value for value in amounts if value is not None and value > 0)
    if amount_total > 0:
        return amount_total
    return max(1.0, safe_float(config.get("walk_forward_default_notional_cad")) or 1000.0)


def _walk_forward_evidence_key(row: dict[str, Any]) -> tuple[str, ...]:
    # This is evidence joining only; friction assumptions/calculations are unchanged.
    return (*evidence_cohort(row), str(row.get("run_id") or ""), str(row.get("mode") or ""),
            str(row.get("analysis_date") or ""), str(row.get("next_analysis_date") or ""))
