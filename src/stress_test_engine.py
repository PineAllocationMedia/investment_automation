from __future__ import annotations

from collections import defaultdict
from typing import Any, Callable

from .utils import safe_float


def compute_stress_tests(
    portfolio_rows: list[dict[str, Any]],
    exposures: dict[str, dict[str, Any]],
    sectors: dict[str, str],
) -> list[dict[str, Any]]:
    static_results = _compute_static_stress_tests(portfolio_rows, exposures, sectors)
    sequential_results = compute_sequential_crisis_scenarios(portfolio_rows, exposures, sectors)
    return static_results + sequential_results


def _compute_static_stress_tests(
    portfolio_rows: list[dict[str, Any]],
    exposures: dict[str, dict[str, Any]],
    sectors: dict[str, str],
) -> list[dict[str, Any]]:
    total = sum(safe_float(row.get("current_value")) or 0.0 for row in portfolio_rows)
    scenarios: list[tuple[str, str, Callable[[str], float]]] = [
        ("Bear market normal", "Actions individuelles -25 %, VFV -20 %.", lambda t: -0.20 if t == "VFV.TO" else -0.25),
        ("Crash sévère", "Actions individuelles -40 %, VFV -35 %.", lambda t: -0.35 if t == "VFV.TO" else -0.40),
        (
            "Tech/AI/Semiconductor unwind",
            "MSFT, AVGO, ASML, CSU.TO, TSLA, NVDA, GOOGL, AMZN -35 %, autres -15 %, VFV -20 %.",
            lambda t: -0.20 if t == "VFV.TO" else -0.35 if t in {"MSFT", "AVGO", "ASML", "CSU.TO", "TSLA", "NVDA", "GOOGL", "AMZN"} else -0.15,
        ),
        ("Taux élevés persistants", "Growth et actifs sensibles aux taux pénalisés.", lambda t: _rates_shock(t, exposures, sectors)),
        ("Récession", "Industrielles, consommation et paiements plus touchés.", lambda t: _recession_shock(t, exposures, sectors)),
        ("USD/CAD shock", "Impact simulé si USD baisse de 10 % face au CAD.", lambda t: -0.10 if exposures.get(t, {}).get("currency") == "USD" else 0.0),
    ]

    results: list[dict[str, Any]] = []
    for name, description, shock_fn in scenarios:
        losses: list[dict[str, Any]] = []
        for row in portfolio_rows:
            ticker = row["ticker"]
            value = safe_float(row.get("current_value")) or 0.0
            shock = shock_fn(ticker)
            estimated_loss = abs(value * shock)
            losses.append(
                {
                    "ticker": ticker,
                    "shock": shock,
                    "estimated_loss": estimated_loss,
                    "current_value": value,
                }
            )
        total_loss = sum(row["estimated_loss"] for row in losses)
        contributors = sorted(losses, key=lambda row: row["estimated_loss"], reverse=True)[:3]
        results.append(
            {
                "scenario": name,
                "scenario_type": "static_single_shock",
                "description": description,
                "estimated_loss_dollars": total_loss,
                "estimated_loss_percent": total_loss / total if total > 0 else 0.0,
                "scenario_quality": _scenario_quality(portfolio_rows, exposures, sectors),
                "top_contributors": contributors,
                "primary_risk": _primary_risk(name),
            }
        )
    return results


def compute_sequential_crisis_scenarios(
    portfolio_rows: list[dict[str, Any]],
    exposures: dict[str, dict[str, Any]],
    sectors: dict[str, str],
) -> list[dict[str, Any]]:
    """Return stylized multi-phase crisis diagnostics without affecting allocation decisions."""
    total = sum(safe_float(row.get("current_value")) or 0.0 for row in portfolio_rows)
    if total <= 0:
        return [_empty_sequential_scenario(definition, portfolio_rows, exposures, sectors) for definition in _sequential_definitions()]

    results: list[dict[str, Any]] = []
    for definition in _sequential_definitions():
        scenario_key = str(definition["key"])
        simulated_values = {
            str(row.get("ticker") or "").strip().upper(): safe_float(row.get("current_value")) or 0.0
            for row in portfolio_rows
            if str(row.get("ticker") or "").strip()
        }
        ticker_start_values = dict(simulated_values)
        portfolio_peak = total
        previous_portfolio_value = total
        phase_path: list[dict[str, Any]] = []

        for index, phase in enumerate(definition["phases"], start=1):
            phase_name = str(phase["phase"])
            base_return = safe_float(phase.get("base_return")) or 0.0
            for row in portfolio_rows:
                ticker = str(row.get("ticker") or "").strip().upper()
                if not ticker:
                    continue
                start_value = simulated_values.get(ticker, 0.0)
                ticker_return = _sequential_phase_return(ticker, row, exposures, sectors, scenario_key, base_return)
                simulated_values[ticker] = max(0.0, start_value * (1.0 + ticker_return))

            portfolio_value = sum(simulated_values.values())
            portfolio_peak = max(portfolio_peak, portfolio_value)
            phase_return = portfolio_value / previous_portfolio_value - 1.0 if previous_portfolio_value > 0 else 0.0
            drawdown = portfolio_value / portfolio_peak - 1.0 if portfolio_peak > 0 else 0.0
            phase_path.append(
                {
                    "month": index,
                    "phase": phase_name,
                    "base_return": base_return,
                    "portfolio_value": portfolio_value,
                    "phase_return": phase_return,
                    "drawdown": drawdown,
                }
            )
            previous_portfolio_value = portfolio_value

        final_value = sum(simulated_values.values())
        ticker_losses = _sequential_ticker_losses(portfolio_rows, exposures, sectors, ticker_start_values, simulated_values)
        sector_theme_losses = _sector_theme_losses(ticker_losses)
        max_drawdown_signed = min((safe_float(row.get("drawdown")) or 0.0 for row in phase_path), default=0.0)
        worst_phase = min(phase_path, key=lambda row: safe_float(row.get("phase_return")) or 0.0) if phase_path else {}
        estimated_loss = max(0.0, total - final_value)
        contributors = sorted(ticker_losses, key=lambda row: safe_float(row.get("estimated_loss")) or 0.0, reverse=True)[:3]
        amplifiers = sorted(ticker_losses, key=lambda row: safe_float(row.get("scenario_return")) or 0.0)[:3]
        resilient = sorted(ticker_losses, key=lambda row: safe_float(row.get("scenario_return")) or -1.0, reverse=True)[:3]

        results.append(
            {
                "scenario": definition["name"],
                "scenario_type": "sequential_stylized",
                "description": definition["description"],
                "estimated_loss_dollars": estimated_loss,
                "estimated_loss_percent": estimated_loss / total if total > 0 else 0.0,
                "estimated_final_portfolio_value": final_value,
                "max_drawdown_percent": abs(max_drawdown_signed),
                "max_drawdown_signed": max_drawdown_signed,
                "worst_phase": worst_phase,
                "worst_phase_name": worst_phase.get("phase", ""),
                "worst_phase_return": worst_phase.get("phase_return", 0.0),
                "phase_path": phase_path,
                "top_contributors": contributors,
                "contribution_by_ticker": ticker_losses,
                "contribution_by_sector_theme": sector_theme_losses,
                "amplifying_tickers": amplifiers,
                "resilient_tickers": resilient,
                "scenario_quality": _scenario_quality(portfolio_rows, exposures, sectors),
                "data_completeness": _scenario_data_completeness(portfolio_rows, exposures, sectors),
                "primary_risk": definition["primary_risk"],
                "interpretation": _sequential_interpretation(definition["name"], estimated_loss / total if total > 0 else 0.0, max_drawdown_signed),
                "diagnostic_only": True,
            }
        )
    return results


def _rates_shock(ticker: str, exposures: dict[str, dict[str, Any]], sectors: dict[str, str]) -> float:
    if ticker == "VFV.TO":
        return -0.15
    factors = set(exposures.get(ticker, {}).get("factor_exposure", []))
    sector = sectors.get(ticker, "")
    if ticker in {"TSLA", "BAM"} or "growth" in factors or "rates_sensitive" in factors:
        return -0.30
    if "healthcare" in factors or "Pharmaceutical" in sector:
        return -0.10
    return -0.15


def _recession_shock(ticker: str, exposures: dict[str, dict[str, Any]], sectors: dict[str, str]) -> float:
    if ticker == "VFV.TO":
        return -0.25
    factors = set(exposures.get(ticker, {}).get("factor_exposure", []))
    sector = sectors.get(ticker, "")
    cyclical = {"industrial", "consumer", "payments", "financials", "engineering", "infrastructure"}
    if factors & cyclical or any(word in sector.lower() for word in ["industrial", "consumer", "payment", "construction"]):
        return -0.30
    if "healthcare" in factors or "pharma" in factors:
        return -0.15
    return -0.20


def _primary_risk(name: str) -> str:
    mapping = {
        "Bear market normal": "Volatilité normale de marché.",
        "Crash sévère": "Compression généralisée des multiples et panique de liquidité.",
        "Tech/AI/Semiconductor unwind": "Corrélation cachée IA, cloud et semi-conducteurs.",
        "Taux élevés persistants": "Duration implicite des actions de croissance et actifs sensibles aux taux.",
        "Récession": "Baisse des revenus cycliques et compression des marges.",
        "USD/CAD shock": "Risque de devise pour un investisseur canadien.",
    }
    return mapping.get(name, "Risque global.")


def _sequential_definitions() -> list[dict[str, Any]]:
    return [
        {
            "key": "2008_credit_crisis_style",
            "name": "2008_credit_crisis_style",
            "description": "Diagnostic stylisé en plusieurs phases inspiré d'une crise de crédit; ce n'est pas une reconstruction historique exacte.",
            "primary_risk": "Assèchement du crédit, compression des multiples et pression sur les actifs cycliques ou sensibles au financement.",
            "phases": [
                {"phase": "credit_spread_widening", "base_return": -0.06},
                {"phase": "liquidity_and_deleveraging", "base_return": -0.12},
                {"phase": "earnings_recession", "base_return": -0.15},
                {"phase": "forced_selling", "base_return": -0.10},
                {"phase": "policy_stabilization", "base_return": 0.04},
                {"phase": "early_recovery", "base_return": 0.07},
            ],
        },
        {
            "key": "2020_liquidity_crash_style",
            "name": "2020_liquidity_crash_style",
            "description": "Diagnostic stylisé d'un choc de liquidité rapide suivi d'une normalisation partielle; ce n'est pas une reconstruction historique exacte.",
            "primary_risk": "Vente forcée rapide, liquidité fragile et dépendance au rebond des actifs de qualité.",
            "phases": [
                {"phase": "sudden_shutdown", "base_return": -0.12},
                {"phase": "liquidity_gap", "base_return": -0.16},
                {"phase": "policy_response", "base_return": 0.07},
                {"phase": "quality_rebound", "base_return": 0.10},
            ],
        },
        {
            "key": "2022_rate_shock_style",
            "name": "2022_rate_shock_style",
            "description": "Diagnostic stylisé d'une hausse rapide des taux qui pénalise les actifs de longue duration; ce n'est pas une reconstruction historique exacte.",
            "primary_risk": "Hausse des taux, compression des valorisations de croissance et pression sur les actifs sensibles au coût du capital.",
            "phases": [
                {"phase": "inflation_reset", "base_return": -0.05},
                {"phase": "multiple_compression", "base_return": -0.09},
                {"phase": "earnings_revision", "base_return": -0.06},
                {"phase": "rates_stay_high", "base_return": -0.04},
                {"phase": "selective_recovery", "base_return": 0.03},
            ],
        },
        {
            "key": "six_month_minus_40_crash",
            "name": "six_month_minus_40_crash",
            "description": "Diagnostic stylisé d'un krach étalé sur six mois visant environ -40 % pour une action individuelle moyenne.",
            "primary_risk": "Choc prolongé où la baisse se répète assez longtemps pour tester la patience, le sizing et la concentration.",
            "phases": [
                {"phase": "month_1_initial_break", "base_return": -0.08},
                {"phase": "month_2_acceleration", "base_return": -0.11},
                {"phase": "month_3_capitulation", "base_return": -0.10},
                {"phase": "month_4_aftershock", "base_return": -0.08},
                {"phase": "month_5_weak_bounce_failure", "base_return": -0.07},
                {"phase": "month_6_exhaustion", "base_return": -0.05},
            ],
        },
    ]


def _sequential_phase_return(
    ticker: str,
    row: dict[str, Any],
    exposures: dict[str, dict[str, Any]],
    sectors: dict[str, str],
    scenario_key: str,
    base_return: float,
) -> float:
    multiplier = _scenario_sensitivity_multiplier(ticker, row, exposures, sectors, scenario_key)
    if base_return >= 0:
        multiplier = _recovery_multiplier(multiplier, row, exposures.get(ticker, {}), sectors.get(ticker, ""))
    shock = base_return * multiplier
    return max(-0.70, min(0.35, shock))


def _scenario_sensitivity_multiplier(
    ticker: str,
    row: dict[str, Any],
    exposures: dict[str, dict[str, Any]],
    sectors: dict[str, str],
    scenario_key: str,
) -> float:
    exposure = exposures.get(ticker, {})
    factors = _factor_set(row, exposure)
    sector = str(sectors.get(ticker) or row.get("sector") or "").lower()
    asset_type = str(row.get("asset_type") or "").upper()
    multiplier = 1.0

    if ticker == "VFV.TO" or row.get("benchmark_role") is True:
        multiplier *= 0.88
    elif asset_type.startswith("ETF"):
        multiplier *= 0.92
    if any(word in asset_type for word in ["BOND", "FIXED_INCOME", "CASH"]):
        multiplier *= 0.35

    if _has_any(factors, {"healthcare", "pharma", "consumer_staples", "defensive"}) or any(
        word in sector for word in ["health", "pharma", "utility", "staple"]
    ):
        multiplier *= 0.78
    if _has_any(factors, {"growth", "technology", "cloud", "software", "AI", "semiconductors"}):
        multiplier *= 1.08
    if _has_any(factors, {"industrial", "consumer", "payments", "financials", "rates_sensitive", "capex_cycle"}):
        multiplier *= 1.10
    if str(row.get("cycle_bubble_risk_level") or "").upper() == "HIGH":
        multiplier *= 1.08
    elif str(row.get("cycle_bubble_risk_level") or "").upper() == "EXTREME":
        multiplier *= 1.18

    if scenario_key == "2008_credit_crisis_style":
        if _has_any(factors, {"financials", "alternative_assets", "rates_sensitive"}) or any(
            word in sector for word in ["financial", "bank", "asset management"]
        ):
            multiplier *= 1.25
        if _has_any(factors, {"industrial", "consumer", "engineering", "infrastructure"}):
            multiplier *= 1.10
    elif scenario_key == "2020_liquidity_crash_style":
        if _has_any(factors, {"consumer", "industrial", "travel", "cyclical"}):
            multiplier *= 1.18
        if _has_any(factors, {"cloud", "software", "payments", "healthcare"}):
            multiplier *= 0.92
    elif scenario_key == "2022_rate_shock_style":
        if _has_any(factors, {"growth", "AI", "cloud", "software", "semiconductors", "rates_sensitive"}):
            multiplier *= 1.30
        if _has_any(factors, {"financials", "healthcare", "pharma", "consumer_staples"}):
            multiplier *= 0.88
    elif scenario_key == "six_month_minus_40_crash":
        if _has_any(factors, {"speculative", "cyclical", "rates_sensitive"}) or str(row.get("long_term_durability_status") or "") == "SPECULATIVE_OR_UNPROVEN":
            multiplier *= 1.20

    durability = str(row.get("long_term_durability_status") or "")
    if durability == "VERY_DURABLE_COMPOUNDER":
        multiplier *= 0.92
    elif durability == "HIGH_GROWTH_BUT_FRAGILE":
        multiplier *= 1.10
    return max(0.20, min(multiplier, 1.80))


def _recovery_multiplier(multiplier: float, row: dict[str, Any], exposure: dict[str, Any], sector: str) -> float:
    factors = _factor_set(row, exposure)
    recovery = min(multiplier, 1.15)
    if _has_any(factors, {"cloud", "software", "technology", "AI", "semiconductors"}) and str(row.get("thesis_status") or "") == "INTACT":
        recovery *= 1.08
    if _has_any(factors, {"financials", "rates_sensitive"}) or "financial" in sector.lower():
        recovery *= 0.90
    return max(0.20, min(recovery, 1.25))


def _sequential_ticker_losses(
    portfolio_rows: list[dict[str, Any]],
    exposures: dict[str, dict[str, Any]],
    sectors: dict[str, str],
    start_values: dict[str, float],
    final_values: dict[str, float],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in portfolio_rows:
        ticker = str(row.get("ticker") or "").strip().upper()
        if not ticker:
            continue
        start = safe_float(start_values.get(ticker)) or 0.0
        final = safe_float(final_values.get(ticker)) or 0.0
        estimated_loss = max(0.0, start - final)
        scenario_return = final / start - 1.0 if start > 0 else 0.0
        sector = sectors.get(ticker) or row.get("sector") or "Unknown"
        theme = _theme_key(row, exposures.get(ticker, {}), str(sector))
        rows.append(
            {
                "ticker": ticker,
                "current_value": start,
                "final_value": final,
                "estimated_loss": estimated_loss,
                "estimated_loss_percent": estimated_loss / start if start > 0 else 0.0,
                "scenario_return": scenario_return,
                "sector": sector,
                "theme": theme,
                "sector_theme": theme if theme != "Unknown" else sector,
            }
        )
    return sorted(rows, key=lambda item: safe_float(item.get("estimated_loss")) or 0.0, reverse=True)


def _sector_theme_losses(ticker_losses: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: defaultdict[str, dict[str, Any]] = defaultdict(lambda: {"sector_theme": "", "estimated_loss": 0.0, "current_value": 0.0, "tickers": []})
    for row in ticker_losses:
        key = str(row.get("sector_theme") or "Unknown")
        grouped[key]["sector_theme"] = key
        grouped[key]["estimated_loss"] += safe_float(row.get("estimated_loss")) or 0.0
        grouped[key]["current_value"] += safe_float(row.get("current_value")) or 0.0
        grouped[key]["tickers"].append(row.get("ticker"))
    output = []
    for row in grouped.values():
        current = safe_float(row.get("current_value")) or 0.0
        loss = safe_float(row.get("estimated_loss")) or 0.0
        output.append(
            {
                "sector_theme": row["sector_theme"],
                "estimated_loss": loss,
                "estimated_loss_percent": loss / current if current > 0 else 0.0,
                "tickers": ", ".join(str(ticker) for ticker in row["tickers"] if ticker),
            }
        )
    return sorted(output, key=lambda item: safe_float(item.get("estimated_loss")) or 0.0, reverse=True)


def _theme_key(row: dict[str, Any], exposure: dict[str, Any], sector: str) -> str:
    factors = _factor_set(row, exposure)
    priorities = [
        ("AI/semiconductors/cloud", {"AI", "semiconductors", "cloud", "technology", "software"}),
        ("rates_sensitive", {"rates_sensitive", "alternative_assets", "financials"}),
        ("cyclical_growth", {"consumer", "industrial", "capex_cycle", "cyclical"}),
        ("healthcare_defensive", {"healthcare", "pharma", "defensive"}),
        ("broad_market", {"broad_market", "S&P500"}),
    ]
    for label, terms in priorities:
        if _has_any(factors, terms):
            return label
    return sector or "Unknown"


def _factor_set(row: dict[str, Any], exposure: dict[str, Any]) -> set[str]:
    raw = exposure.get("factor_exposure") or row.get("factor_exposure") or []
    if isinstance(raw, str):
        items = [item.strip() for item in raw.replace(";", ",").split(",")]
    else:
        items = [str(item).strip() for item in raw]
    return {item for item in items if item}


def _has_any(factors: set[str], terms: set[str]) -> bool:
    lowered = {factor.lower() for factor in factors}
    return any(term.lower() in lowered for term in terms)


def _scenario_data_completeness(
    portfolio_rows: list[dict[str, Any]],
    exposures: dict[str, dict[str, Any]],
    sectors: dict[str, str],
) -> float:
    usable_rows = [row for row in portfolio_rows if (safe_float(row.get("current_value")) or 0.0) > 0]
    if not usable_rows:
        return 0.0
    score = 0.0
    max_score = len(usable_rows) * 3.0
    for row in usable_rows:
        ticker = str(row.get("ticker") or "").strip().upper()
        if safe_float(row.get("current_value")) is not None:
            score += 1.0
        sector = sectors.get(ticker) or row.get("sector")
        if sector and str(sector).lower() not in {"unknown", "none"}:
            score += 1.0
        if _factor_set(row, exposures.get(ticker, {})):
            score += 1.0
    return round(score / max_score if max_score > 0 else 0.0, 4)


def _scenario_quality(
    portfolio_rows: list[dict[str, Any]],
    exposures: dict[str, dict[str, Any]],
    sectors: dict[str, str],
) -> str:
    completeness = _scenario_data_completeness(portfolio_rows, exposures, sectors)
    if completeness >= 0.75:
        return "HIGH"
    if completeness >= 0.45:
        return "MEDIUM"
    return "LOW"


def _empty_sequential_scenario(
    definition: dict[str, Any],
    portfolio_rows: list[dict[str, Any]],
    exposures: dict[str, dict[str, Any]],
    sectors: dict[str, str],
) -> dict[str, Any]:
    return {
        "scenario": definition["name"],
        "scenario_type": "sequential_stylized",
        "description": definition["description"],
        "estimated_loss_dollars": 0.0,
        "estimated_loss_percent": 0.0,
        "estimated_final_portfolio_value": 0.0,
        "max_drawdown_percent": 0.0,
        "max_drawdown_signed": 0.0,
        "worst_phase": {},
        "worst_phase_name": "",
        "worst_phase_return": 0.0,
        "phase_path": [],
        "top_contributors": [],
        "contribution_by_ticker": [],
        "contribution_by_sector_theme": [],
        "amplifying_tickers": [],
        "resilient_tickers": [],
        "scenario_quality": _scenario_quality(portfolio_rows, exposures, sectors),
        "data_completeness": _scenario_data_completeness(portfolio_rows, exposures, sectors),
        "primary_risk": definition["primary_risk"],
        "interpretation": "Diagnostic non calculable: aucune valeur de portefeuille utilisable.",
        "diagnostic_only": True,
    }


def _sequential_interpretation(scenario_name: str, final_loss_percent: float, max_drawdown_signed: float) -> str:
    drawdown = abs(max_drawdown_signed)
    if drawdown >= 0.40 or final_loss_percent >= 0.35:
        severity = "Le scénario montre une forte vulnérabilité de parcours: la concentration ou les thèmes dominants amplifieraient la baisse."
    elif drawdown >= 0.25 or final_loss_percent >= 0.20:
        severity = "Le scénario montre un stress sérieux mais tolérable pour un portefeuille long terme si les thèses restent intactes."
    else:
        severity = "Le scénario montre une perte contenue relativement au choc stylisé."
    return (
        f"{severity} {scenario_name} est un diagnostic déterministe: il informe le risque de trajectoire, "
        "mais ne déclenche aucune vente ni changement automatique d'allocation."
    )
