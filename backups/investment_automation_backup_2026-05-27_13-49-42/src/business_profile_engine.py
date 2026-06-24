from __future__ import annotations

import re
from typing import Any

from .utils import normalize_ticker


PROFILE_DEFAULT = "QUALITY_GROWTH_COMPOUNDER"

PROFILE_BY_TICKER = {
    "TD.TO": "BANK",
    "JPM": "BANK",
    "C": "BANK",
    "MFC.TO": "INSURANCE",
    "SLF.TO": "INSURANCE",
    "PGR": "INSURANCE",
    "FTS.TO": "UTILITY",
    "NEE": "UTILITY",
    "NPI.TO": "UTILITY",
    "BLX.TO": "UTILITY",
    "ENB.TO": "PIPELINE",
    "AEM.TO": "RESOURCES",
    "FNV.TO": "RESOURCES",
    "WPM.TO": "RESOURCES",
    "NTR.TO": "RESOURCES",
    "NEM": "RESOURCES",
    "CCO.TO": "RESOURCES",
    "COP": "ENERGY_CYCLICAL",
    "PLD": "REIT",
    "WELL": "REIT",
    "BAM": "ALT_ASSET_MANAGER",
    "BX": "ALT_ASSET_MANAGER",
    "KKR": "ALT_ASSET_MANAGER",
    "BLK": "ASSET_MANAGER",
}

PROFILE_SETTINGS = {
    PROFILE_DEFAULT: {
        "label": "Compounder croissance/qualité",
        "roic_threshold": 15.0,
        "eps_hist_threshold": 10.0,
        "eps_est_threshold": 12.0,
        "sector_cagr_threshold": 8.0,
        "forward_pe_limit": 35.0,
        "peg_limit": 2.0,
        "weak_growth_threshold": 10.0,
        "serious_growth_floor": 5.0,
        "roic_label": "ROIC 5 ans moyen > 15 %",
        "profile_reason": "Profil par défaut pour compounders de qualité et croissance.",
    },
    "BANK": {
        "label": "Banque",
        "roic_threshold": 10.0,
        "eps_hist_threshold": 6.0,
        "eps_est_threshold": 7.0,
        "sector_cagr_threshold": 4.0,
        "forward_pe_limit": 18.0,
        "peg_limit": 2.5,
        "weak_growth_threshold": 6.0,
        "serious_growth_floor": 3.0,
        "roic_label": "ROE / qualité du capital bancaire >= 10 %",
        "profile_reason": "Les banques se jugent mieux avec ROE, capital, crédit et cycle qu’avec un ROIC industriel strict.",
    },
    "INSURANCE": {
        "label": "Assurance",
        "roic_threshold": 9.0,
        "eps_hist_threshold": 5.0,
        "eps_est_threshold": 6.0,
        "sector_cagr_threshold": 4.0,
        "forward_pe_limit": 20.0,
        "peg_limit": 2.5,
        "weak_growth_threshold": 6.0,
        "serious_growth_floor": 3.0,
        "roic_label": "ROE / qualité du capital assurance >= 9 %",
        "profile_reason": "Les assureurs se jugent mieux avec ROE, discipline du capital et solidité du bilan qu’avec un ROIC industriel strict.",
    },
    "UTILITY": {
        "label": "Service public / énergie régulée",
        "roic_threshold": 6.0,
        "eps_hist_threshold": 4.0,
        "eps_est_threshold": 5.0,
        "sector_cagr_threshold": 3.0,
        "forward_pe_limit": 25.0,
        "peg_limit": 3.0,
        "weak_growth_threshold": 5.0,
        "serious_growth_floor": 2.0,
        "roic_label": "Rendement du capital adapté utility >= 6 %",
        "profile_reason": "Les utilities ont une croissance plus lente et régulée; le modèle réduit les seuils de croissance sans les transformer en titres haut CAGR.",
    },
    "PIPELINE": {
        "label": "Pipeline / infrastructure énergétique",
        "roic_threshold": 6.0,
        "eps_hist_threshold": 4.0,
        "eps_est_threshold": 5.0,
        "sector_cagr_threshold": 3.0,
        "forward_pe_limit": 22.0,
        "peg_limit": 3.0,
        "weak_growth_threshold": 5.0,
        "serious_growth_floor": 2.0,
        "roic_label": "Rendement du capital adapté pipeline >= 6 %",
        "profile_reason": "Les pipelines se jugent mieux avec flux de trésorerie, dette et régulation qu’avec les mêmes seuils qu’un compounder logiciel.",
    },
    "RESOURCES": {
        "label": "Ressources / matières premières",
        "roic_threshold": 8.0,
        "eps_hist_threshold": 5.0,
        "eps_est_threshold": 6.0,
        "sector_cagr_threshold": 3.0,
        "forward_pe_limit": 25.0,
        "peg_limit": 3.0,
        "weak_growth_threshold": 6.0,
        "serious_growth_floor": 2.0,
        "roic_label": "Rendement du capital adapté ressources >= 8 %",
        "profile_reason": "Les ressources sont cycliques; le score évite de les pénaliser comme des logiciels, mais le CAGR attendu reste contrôlé.",
    },
    "ENERGY_CYCLICAL": {
        "label": "Énergie cyclique",
        "roic_threshold": 8.0,
        "eps_hist_threshold": 5.0,
        "eps_est_threshold": 6.0,
        "sector_cagr_threshold": 3.0,
        "forward_pe_limit": 22.0,
        "peg_limit": 3.0,
        "weak_growth_threshold": 6.0,
        "serious_growth_floor": 2.0,
        "roic_label": "Rendement du capital adapté énergie >= 8 %",
        "profile_reason": "L’énergie est cyclique; le score utilise des seuils plus réalistes, mais exige une validation du cycle et du bilan.",
    },
    "REIT": {
        "label": "Immobilier / REIT",
        "roic_threshold": 5.0,
        "eps_hist_threshold": 4.0,
        "eps_est_threshold": 5.0,
        "sector_cagr_threshold": 3.0,
        "forward_pe_limit": 30.0,
        "peg_limit": 3.0,
        "weak_growth_threshold": 5.0,
        "serious_growth_floor": 2.0,
        "roic_label": "Rendement du capital adapté immobilier >= 5 %",
        "profile_reason": "Les REIT se jugent mieux avec FFO/AFFO, dette et qualité des actifs; les seuils EPS/ROIC sont assouplis.",
    },
    "ALT_ASSET_MANAGER": {
        "label": "Gestion alternative d’actifs",
        "roic_threshold": 8.0,
        "eps_hist_threshold": 7.0,
        "eps_est_threshold": 8.0,
        "sector_cagr_threshold": 5.0,
        "forward_pe_limit": 28.0,
        "peg_limit": 2.5,
        "weak_growth_threshold": 8.0,
        "serious_growth_floor": 4.0,
        "roic_label": "Rendement du capital adapté gestion d’actifs >= 8 %",
        "profile_reason": "Les gestionnaires d’actifs alternatifs dépendent des AUM, frais, carry, bilan et cycle des marchés privés.",
    },
    "ASSET_MANAGER": {
        "label": "Gestion d’actifs",
        "roic_threshold": 8.0,
        "eps_hist_threshold": 6.0,
        "eps_est_threshold": 7.0,
        "sector_cagr_threshold": 4.0,
        "forward_pe_limit": 24.0,
        "peg_limit": 2.5,
        "weak_growth_threshold": 7.0,
        "serious_growth_floor": 3.0,
        "roic_label": "Rendement du capital adapté gestion d’actifs >= 8 %",
        "profile_reason": "Les gestionnaires d’actifs se jugent avec AUM, marges, flux nets et cycle de marché en plus des métriques classiques.",
    },
}


def detect_business_profile(
    ticker: str,
    market: dict[str, Any] | None = None,
    sector: str | None = None,
) -> dict[str, Any]:
    ticker = normalize_ticker(ticker)
    profile = PROFILE_BY_TICKER.get(ticker)
    if not profile:
        profile = _profile_from_text(market or {}, sector or "")
    settings = dict(PROFILE_SETTINGS.get(profile, PROFILE_SETTINGS[PROFILE_DEFAULT]))
    settings["business_profile"] = profile
    settings["business_profile_label"] = settings["label"]
    return settings


def profile_setting(score_or_analysis: dict[str, Any], key: str, default: float) -> float:
    value = score_or_analysis.get(f"profile_{key}")
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _profile_from_text(market: dict[str, Any], sector: str) -> str:
    text = " ".join(
        str(part or "")
        for part in [
            sector,
            market.get("sector_name"),
            market.get("industry"),
            market.get("long_name"),
        ]
    ).lower()
    text = re.sub(r"[^a-z0-9 ]+", " ", text)
    if "reit" in text or "real estate investment" in text:
        return "REIT"
    if "bank" in text or "banks" in text:
        return "BANK"
    if "insurance" in text:
        return "INSURANCE"
    if "utility" in text or "utilities" in text:
        return "UTILITY"
    if "pipeline" in text or "midstream" in text:
        return "PIPELINE"
    if any(term in text for term in ["gold", "mining", "metals", "copper", "uranium", "fertilizer", "agricultural inputs"]):
        return "RESOURCES"
    if "oil" in text or "gas" in text or "energy" in text:
        return "ENERGY_CYCLICAL"
    if "asset management" in text or "capital markets" in text:
        return "ASSET_MANAGER"
    return PROFILE_DEFAULT
