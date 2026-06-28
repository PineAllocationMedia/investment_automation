from __future__ import annotations

from typing import Any

from .portfolio_loader import account_tax_category
from .utils import CONFIG_DIR, clamp, load_yaml, safe_float


DEFAULT_TAX_PARAMETERS = {
    "canadian_dividend_tax_credit_gross_up": 1.38,
    "canadian_dividend_tax_credit_rate": 0.150198,
    "us_withholding_tax_tfsa": 0.15,
    "us_withholding_tax_rrsp": 0.0,
    "effective_marginal_rate_non_registered": 0.40,
    "us_dividend_non_registered_extra_drag": 0.08,
}


def compute_tax_location_report(
    account_locations: list[dict[str, Any]],
    portfolio_rows: list[dict[str, Any]],
    analyses: dict[str, dict[str, Any]],
    exposures: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    if not account_locations:
        account_locations = [
            {"ticker": row["ticker"], "account_type": "UNKNOWN", "current_value": row.get("current_value", 0.0)}
            for row in portfolio_rows
        ]

    rows: list[dict[str, Any]] = []
    for location in account_locations:
        ticker = location["ticker"]
        account_type = str(location.get("account_type") or "UNKNOWN").upper()
        tax_category = str(location.get("account_tax_category") or account_tax_category(account_type))
        analysis = analyses.get(ticker, {})
        expected = analysis.get("expected_cagr_quality", "UNCERTAIN")
        dividend_yield = safe_float(analysis.get("dividend_yield")) or 0.0
        currency = exposures.get(ticker, {}).get("currency", "Unknown")
        liquidation_status = analysis.get("liquidation_status", "UNKNOWN")
        ideal = suggested_account(ticker, expected, dividend_yield, currency)
        comment = account_comment(account_type)
        alerts: list[str] = []

        if expected in {"HIGH", "VERY_HIGH"} and tax_category not in {"TFSA", "FHSA", "UNKNOWN"}:
            alerts.append("Position haut CAGR potentiellement dans un compte moins optimal.")
        if tax_category == "NON_REGISTERED" and liquidation_status in {"ORANGE", "RED"}:
            alerts.append("Vente potentiellement taxable en non enregistré.")
        if ticker != "VFV.TO" and tax_category == "FHSA":
            alerts.append("Vérifier l’horizon de retrait avant de conserver une forte concentration en CELIAPP.")
        if currency == "USD" and dividend_yield > 0.01 and tax_category not in {"RRSP", "UNKNOWN"}:
            alerts.append("Dividendes américains potentiellement plus adaptés au REER selon situation.")

        rows.append(
            {
                "ticker": ticker,
                "account_type": account_type,
                "account_tax_category": tax_category,
                "shares": safe_float(location.get("shares")) or 0.0,
                "current_value": safe_float(location.get("current_value")) or 0.0,
                "tax_location_comment": comment,
                "suggested_account": ideal,
                "alert": " ".join(alerts) if alerts else "Aucune alerte fiscale mécanique.",
            }
        )
    return rows


def compute_after_tax_yield(
    ticker: str,
    gross_yield: float,
    account_type: str,
    is_canadian_eligible_dividend: bool,
    is_us_dividend: bool,
) -> dict[str, Any]:
    gross_yield = safe_float(gross_yield)
    if gross_yield is None:
        gross_yield = 0.0
    if gross_yield < 0:
        gross_yield = 0.0
    params = load_tax_parameters()
    category = account_tax_category(account_type)
    ticker = str(ticker or "").upper()

    if gross_yield == 0:
        return {
            "after_tax_yield": 0.0,
            "tax_adjustment_factor": 1.0,
            "tax_note": "after-tax est. (approx.): aucun dividende significatif.",
        }
    if category == "UNKNOWN":
        return {
            "after_tax_yield": gross_yield,
            "tax_adjustment_factor": 1.0,
            "tax_note": "after-tax est. (approx.): UNKNOWN_ACCOUNT, rendement brut conservé.",
        }

    factor = 1.0
    if category in {"TFSA", "FHSA"}:
        if is_us_dividend:
            factor = 1.0 - _param(params, "us_withholding_tax_tfsa")
            note = f"after-tax est. (approx.): dividende US/étranger en {category}, retenue non récupérable appliquée."
        else:
            note = f"after-tax est. (approx.): dividende canadien ou distribution non-US en {category}, rendement brut conservé."
    elif category == "RRSP":
        if is_us_dividend:
            factor = 1.0 - _param(params, "us_withholding_tax_rrsp")
            note = "after-tax est. (approx.): dividende US/étranger en RRSP, traité comme exempté de retenue."
        else:
            note = "after-tax est. (approx.): dividende en RRSP, traité brut pour comparaison relative."
    elif category == "NON_REGISTERED":
        marginal = _param(params, "effective_marginal_rate_non_registered")
        if is_canadian_eligible_dividend:
            gross_up = _param(params, "canadian_dividend_tax_credit_gross_up")
            credit_rate = _param(params, "canadian_dividend_tax_credit_rate")
            tax_drag = gross_up * marginal - gross_up * credit_rate
            factor = 1.0 - tax_drag
            note = "after-tax est. (approx.): dividende déterminé canadien en non enregistré avec effet DTC approximatif."
        elif is_us_dividend:
            factor = 1.0 - marginal - _param(params, "us_dividend_non_registered_extra_drag")
            note = "after-tax est. (approx.): dividende US/étranger en non enregistré avec traînée fiscale nette approximative."
        else:
            factor = 1.0 - marginal
            note = "after-tax est. (approx.): distribution non déterminée en non enregistré, taux marginal approximatif appliqué."
    else:
        return {
            "after_tax_yield": gross_yield,
            "tax_adjustment_factor": 1.0,
            "tax_note": f"after-tax est. (approx.): compte {category} non spécialisé, rendement brut conservé.",
        }

    factor = clamp(factor, 0.0, 1.25)
    return {
        "after_tax_yield": gross_yield * factor,
        "tax_adjustment_factor": factor,
        "tax_note": f"{note} Ticker={ticker}. À valider avec un fiscaliste ou comptable.",
    }


def load_tax_parameters() -> dict[str, float]:
    loaded = load_yaml(CONFIG_DIR / "tax_parameters.yaml")
    params: dict[str, float] = {}
    for key, default in DEFAULT_TAX_PARAMETERS.items():
        value = safe_float(loaded.get(key))
        params[key] = float(value if value is not None else default)
    return params


def _param(params: dict[str, float], key: str) -> float:
    return float(params.get(key, DEFAULT_TAX_PARAMETERS[key]))


def suggested_account(ticker: str, expected_cagr_quality: str, dividend_yield: float, currency: str) -> str:
    if expected_cagr_quality in {"HIGH", "VERY_HIGH"}:
        return "TFSA/CELI prioritaire; FHSA/CELIAPP possible si horizon long"
    if ticker == "VFV.TO":
        return "FHSA/CELIAPP, TFSA/CELI ou RRSP/REER selon horizon"
    if currency == "USD" and dividend_yield > 0.01:
        return "RRSP/REER à considérer pour dividendes américains"
    return "NON_REGISTERED possible si faible turnover; sinon TFSA/RRSP selon plan global"


def account_comment(account_type: str) -> str:
    label = str(account_type or "UNKNOWN").upper()
    category = account_tax_category(label)
    comments = {
        "TFSA": "Excellent pour actifs à haut CAGR; gains et retraits non imposables.",
        "FHSA": "Très utile pour objectif immobilier; adapter le risque à l’horizon de retrait.",
        "RRSP": "Utile pour report d’impôt et certains actifs américains à dividendes.",
        "NON_REGISTERED": "Limiter le turnover; attention aux gains imposables et dividendes étrangers.",
        "MIXED": "Même ticker réparti dans plusieurs types de comptes; l’analyse fiscale est agrégée.",
        "UNKNOWN": "Compte non renseigné; remplir account_type dans portfolio.csv pour améliorer l’analyse.",
    }
    comment = comments.get(category, comments["UNKNOWN"])
    if label and category in comments and label != category:
        return f"{comment} Libellé de compte: {label}."
    return comment
