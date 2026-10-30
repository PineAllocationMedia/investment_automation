"""Primary-source macro-regime references, NOT calibrated asset returns.

Static official references inspected 2026-10-30. No runtime source access,
claim of a certified PIT dataset, instrument shocks, trades or policy authority.
"""
from copy import deepcopy
from datetime import date

_REGIMES = {
    "US_2008_CREDIT_LIQUIDITY": {
        "label_fr": "Credit et liquidite (Etats-Unis, septembre 2008)",
        "event_period": "2008-09", "available_after": "2008-09-23",
        "observed_fr": "La Fed decrit une baisse des actions, de fortes tensions de credit et une fuite vers les bons du Tresor.",
        "source_name": "Federal Reserve Board, testimony, 2008-09-23",
        "source_url": "https://www.federalreserve.gov/newsevents/testimony/bernanke20080923a1.htm",
        "source_date": "2008-09-23",
    },
    "CA_2020_PANDEMIC_LIQUIDITY": {
        "label_fr": "Liquidite et choc pandemique (Canada, mars 2020)",
        "event_period": "2020-03", "available_after": "2020-05-31",
        "observed_fr": "La Banque du Canada decrit la chute des actions, les spreads de credit et la perturbation de la liquidite.",
        "source_name": "Bank of Canada, Financial System Review 2020",
        "source_url": "https://www.bankofcanada.ca/2020/05/financial-system-review-2020/",
        "source_date": "2020-05 (jour exact non atteste; borne conservatrice au 31 mai)",
    },
    "CA_2022_INFLATION": {
        "label_fr": "Inflation elevee (Canada, juin 2022)",
        "event_period": "2022-06", "available_after": "2022-07-20",
        "observed_fr": "Statistique Canada rapporte 8,1 % d'inflation IPC annuelle en juin 2022; ce n'est pas un rendement d'actif.",
        "source_name": "Statistics Canada, CPI June 2022",
        "source_url": "https://www150.statcan.gc.ca/n1/daily-quotidien/220720/dq220720a-eng.htm",
        "source_date": "2022-07-20",
    },
}


def prepare_historical_regime_context(*, regime_id, analysis_as_of):
    if not isinstance(regime_id, str) or regime_id not in _REGIMES:
        raise ValueError("REGIME_CONTEXT_UNKNOWN")
    if not isinstance(analysis_as_of, str):
        raise ValueError("REGIME_CONTEXT_AS_OF_INVALID")
    try:
        cutoff = date.fromisoformat(analysis_as_of)
    except ValueError as exc:
        raise ValueError("REGIME_CONTEXT_AS_OF_INVALID") from exc
    if cutoff.isoformat() != analysis_as_of:
        raise ValueError("REGIME_CONTEXT_AS_OF_INVALID")
    row = deepcopy(_REGIMES[regime_id])
    if cutoff < date.fromisoformat(row["available_after"]):
        raise ValueError("REGIME_CONTEXT_SOURCE_POSTDATES_CUTOFF")
    return {
        **row, "regime_id": regime_id, "analysis_as_of": analysis_as_of,
        "links_reviewed_on": "2026-10-30",
        "source_status": "FIXED_OFFICIAL_LINKS_NO_RUNTIME_AUTHENTICATION",
        "rights_status": "LINKS_ONLY_NO_DATASET_COPIED",
        "asset_returns": "NOT_SUPPLIED",
        "shocks_derived": "NO",
        "historical_calibration": "NOT_PERFORMED",
        "policy_authority": "NONE",
    }
