from __future__ import annotations

from typing import Any, Callable

from .utils import safe_float


def compute_stress_tests(
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
                "description": description,
                "estimated_loss_dollars": total_loss,
                "estimated_loss_percent": total_loss / total if total > 0 else 0.0,
                "top_contributors": contributors,
                "primary_risk": _primary_risk(name),
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
