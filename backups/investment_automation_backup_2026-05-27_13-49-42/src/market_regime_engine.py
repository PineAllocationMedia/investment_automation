from __future__ import annotations

from pathlib import Path
from typing import Any

from .asset_type_engine import is_etf_asset_analysis
from .utils import load_yaml, pct, safe_float, write_csv_records


DEFAULT_MARKET_REGIME_CONFIG = {
    "enabled": True,
    "proxies": {
        "broad_market": "SPY",
        "canadian_sp500_proxy": "VFV.TO",
        "growth_tech": "QQQ",
        "technology": "XLK",
        "semiconductors": "SOXX",
        "small_caps": "IWM",
        "long_bonds": "TLT",
        "volatility": "^VIX",
        "ten_year_yield": "^TNX",
        "consumer_staples": "XLP",
        "utilities": "XLU",
        "healthcare": "XLV",
        "financials": "XLF",
        "industrials": "XLI",
        "usd_proxy": "UUP",
    },
    "mode_impact": {
        "high-cagr": {"max_penalty": 4.0, "max_bonus": 1.5, "multiplier": 0.55},
        "rational-aggressive": {"max_penalty": 5.0, "max_bonus": 2.0, "multiplier": 0.75},
        "family-office": {"max_penalty": 6.0, "max_bonus": 2.5, "multiplier": 1.0},
        "balanced": {"max_penalty": 8.0, "max_bonus": 3.5, "multiplier": 1.15},
    },
    "sector_euphoria": {
        "enabled": True,
        "activation_score": 55,
        "max_reported_sectors": 5,
        "sectors": {
            "technology": "XLK",
            "semiconductors": "SOXX",
            "communication": "XLC",
            "consumer_discretionary": "XLY",
            "financials": "XLF",
            "industrials": "XLI",
            "healthcare": "XLV",
            "energy": "XLE",
            "materials": "XLB",
            "utilities": "XLU",
            "consumer_staples": "XLP",
            "real_estate": "XLRE",
            "biotech": "XBI",
            "regional_banks": "KRE",
            "gold": "GLD",
            "uranium": "URA",
            "defense_aerospace": "ITA",
            "crypto": "FBTC",
        },
        "mode_impact": {
            "high-cagr": {"max_penalty": 2.5, "max_bonus": 0.5, "multiplier": 0.60},
            "rational-aggressive": {"max_penalty": 3.0, "max_bonus": 0.5, "multiplier": 0.75},
            "family-office": {"max_penalty": 4.0, "max_bonus": 0.7, "multiplier": 1.0},
            "balanced": {"max_penalty": 5.0, "max_bonus": 1.0, "multiplier": 1.15},
        },
    },
}

MARKET_REGIME_COLUMNS = [
    "metric",
    "status",
    "value",
    "interpretation",
    "impact",
]

MARKET_REGIME_ANALYSIS_COLUMNS = [
    "universe",
    "ticker",
    "market_regime_status",
    "market_regime_score",
    "market_regime_allocation_adjustment",
    "market_regime_exposure_intensity",
    "market_regime_exposure_level",
    "market_regime_exposure",
    "market_regime_reason",
    "market_regime_guardrail",
]

SECTOR_EUPHORIA_COLUMNS = [
    "sector",
    "ticker",
    "sector_euphoria_status",
    "sector_euphoria_score",
    "return_6m",
    "relative_6m_vs_market",
    "return_1y",
    "relative_1y_vs_market",
    "above_sma_200",
    "reason",
]

SECTOR_EUPHORIA_ANALYSIS_COLUMNS = [
    "universe",
    "ticker",
    "sector_euphoria_status",
    "sector_euphoria_score",
    "sector_euphoria_allocation_adjustment",
    "sector_euphoria_exposure_intensity",
    "sector_euphoria_exposure",
    "sector_euphoria_reason",
    "sector_euphoria_guardrail",
]

REGIME_TECH_AI_SEMI_FACTORS = {"technology", "cloud", "ai", "semiconductors", "software", "vertical_markets"}
REGIME_TECH_AI_SEMI_BENCHMARKS = {"SOXX", "SMH", "XLK", "IGV", "QQQ", "XLC"}
REGIME_TECH_AI_SEMI_TERMS = {
    "ai",
    "artificial intelligence",
    "cloud",
    "cyber",
    "cybersecurity",
    "data center",
    "digital",
    "e-commerce",
    "internet",
    "networking",
    "semiconductor",
    "software",
    "technology",
}

SECTOR_EUPHORIA_KEYWORDS = {
    "technology": {"tech", "technology", "software", "cloud", "cyber", "cybersecurity", "data center", "digital", "ai"},
    "semiconductors": {"semiconductor", "semiconductors", "chip", "chips", "lithography", "wafer", "foundry"},
    "communication": {"communication", "communications", "media", "advertising", "internet", "platform", "streaming"},
    "consumer_discretionary": {"consumer discretionary", "retail", "e-commerce", "auto", "automotive", "home improvement", "consumer"},
    "financials": {"financial", "financials", "bank", "banks", "insurance", "asset management", "payments"},
    "industrials": {"industrial", "industrials", "engineering", "construction", "machinery", "automation", "aerospace"},
    "healthcare": {"health", "healthcare", "pharma", "pharmaceutical", "medical", "drug", "drugs"},
    "energy": {"energy", "oil", "gas", "pipeline", "renewable", "power producer"},
    "materials": {"materials", "chemical", "chemicals", "mining", "metal", "metals", "lithium", "copper"},
    "utilities": {"utility", "utilities", "electric", "electricity", "water", "regulated utility"},
    "consumer_staples": {"consumer staples", "staples", "food", "beverage", "household", "grocery"},
    "real_estate": {"real estate", "reit", "property", "properties"},
    "biotech": {"biotech", "biotechnology", "clinical", "drug development"},
    "regional_banks": {"regional bank", "regional banks", "bank"},
    "gold": {"gold", "precious metals"},
    "uranium": {"uranium", "nuclear"},
    "defense_aerospace": {"defense", "aerospace", "military", "contractor"},
    "crypto": {"crypto", "bitcoin", "blockchain", "digital asset"},
}


def create_market_regime_config_template(path: str | Path, overwrite: bool = False) -> None:
    path = Path(path)
    if path.exists() and not overwrite:
        return
    lines = [
        "enabled: true",
        "proxies:",
        "  broad_market: SPY",
        "  canadian_sp500_proxy: VFV.TO",
        "  growth_tech: QQQ",
        "  technology: XLK",
        "  semiconductors: SOXX",
        "  small_caps: IWM",
        "  long_bonds: TLT",
        "  volatility: ^VIX",
        "  ten_year_yield: ^TNX",
        "  consumer_staples: XLP",
        "  utilities: XLU",
        "  healthcare: XLV",
        "  financials: XLF",
        "  industrials: XLI",
        "  usd_proxy: UUP",
        "mode_impact:",
        "  high-cagr:",
        "    max_penalty: 4.0",
        "    max_bonus: 1.5",
        "    multiplier: 0.55",
        "  rational-aggressive:",
        "    max_penalty: 5.0",
        "    max_bonus: 2.0",
        "    multiplier: 0.75",
        "  family-office:",
        "    max_penalty: 6.0",
        "    max_bonus: 2.5",
        "    multiplier: 1.0",
        "  balanced:",
        "    max_penalty: 8.0",
        "    max_bonus: 3.5",
        "    multiplier: 1.15",
        "sector_euphoria:",
        "  enabled: true",
        "  activation_score: 55",
        "  max_reported_sectors: 5",
        "  sectors:",
        "    technology: XLK",
        "    semiconductors: SOXX",
        "    communication: XLC",
        "    consumer_discretionary: XLY",
        "    financials: XLF",
        "    industrials: XLI",
        "    healthcare: XLV",
        "    energy: XLE",
        "    materials: XLB",
        "    utilities: XLU",
        "    consumer_staples: XLP",
        "    real_estate: XLRE",
        "    biotech: XBI",
        "    regional_banks: KRE",
        "    gold: GLD",
        "    uranium: URA",
        "    defense_aerospace: ITA",
        "    crypto: FBTC",
        "  mode_impact:",
        "    high-cagr:",
        "      max_penalty: 2.5",
        "      max_bonus: 0.5",
        "      multiplier: 0.60",
        "    rational-aggressive:",
        "      max_penalty: 3.0",
        "      max_bonus: 0.5",
        "      multiplier: 0.75",
        "    family-office:",
        "      max_penalty: 4.0",
        "      max_bonus: 0.7",
        "      multiplier: 1.0",
        "    balanced:",
        "      max_penalty: 5.0",
        "      max_bonus: 1.0",
        "      multiplier: 1.15",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def load_market_regime_config(path: str | Path) -> dict[str, Any]:
    config = load_yaml(path)
    if not config:
        return DEFAULT_MARKET_REGIME_CONFIG
    sector_euphoria = config.get("sector_euphoria") if isinstance(config.get("sector_euphoria"), dict) else {}
    default_sector_euphoria = DEFAULT_MARKET_REGIME_CONFIG["sector_euphoria"]
    merged = {
        "enabled": config.get("enabled", DEFAULT_MARKET_REGIME_CONFIG["enabled"]),
        "proxies": {**DEFAULT_MARKET_REGIME_CONFIG["proxies"], **(config.get("proxies") or {})},
        "mode_impact": {
            **DEFAULT_MARKET_REGIME_CONFIG["mode_impact"],
            **(config.get("mode_impact") or {}),
        },
        "sector_euphoria": {
            "enabled": sector_euphoria.get("enabled", default_sector_euphoria["enabled"]),
            "activation_score": sector_euphoria.get("activation_score", default_sector_euphoria["activation_score"]),
            "max_reported_sectors": sector_euphoria.get("max_reported_sectors", default_sector_euphoria["max_reported_sectors"]),
            "sectors": {
                **default_sector_euphoria["sectors"],
                **(sector_euphoria.get("sectors") or {}),
            },
            "mode_impact": {
                **default_sector_euphoria["mode_impact"],
                **(sector_euphoria.get("mode_impact") or {}),
            },
        },
    }
    return merged


def market_regime_tickers(config: dict[str, Any] | None = None) -> list[str]:
    config = config or DEFAULT_MARKET_REGIME_CONFIG
    if config.get("enabled") is False:
        return []
    tickers = {str(value).strip().upper() for value in (config.get("proxies") or {}).values() if str(value).strip()}
    sector_euphoria = config.get("sector_euphoria") if isinstance(config.get("sector_euphoria"), dict) else {}
    if sector_euphoria.get("enabled", True) is not False:
        tickers.update(
            str(value).strip().upper()
            for value in (sector_euphoria.get("sectors") or {}).values()
            if str(value).strip()
        )
    return sorted(tickers)


def fetch_market_regime_data(fetcher: Any, config: dict[str, Any], refresh: bool = False) -> dict[str, dict[str, Any]]:
    data: dict[str, dict[str, Any]] = {}
    for ticker in market_regime_tickers(config):
        try:
            data[ticker] = fetcher.fetch_ticker(ticker, refresh=refresh)
        except Exception as exc:
            data[ticker] = {"ticker": ticker, "source": "unavailable", "error": str(exc)}
    return data


def compute_market_regime(
    market_regime_data: dict[str, dict[str, Any]],
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    config = config or DEFAULT_MARKET_REGIME_CONFIG
    proxies = config.get("proxies") or {}
    if config.get("enabled") is False:
        return _regime_result("DISABLED", 50, {}, ["Moteur de régime désactivé dans la configuration."], config)

    payloads = {name: market_regime_data.get(str(ticker).upper(), {}) for name, ticker in proxies.items()}
    broad = payloads.get("broad_market") or payloads.get("canadian_sp500_proxy") or {}
    qqq = payloads.get("growth_tech") or {}
    tech = payloads.get("technology") or {}
    semi = payloads.get("semiconductors") or {}
    small = payloads.get("small_caps") or {}
    bonds = payloads.get("long_bonds") or {}
    vix = payloads.get("volatility") or {}
    tnx = payloads.get("ten_year_yield") or {}
    staples = payloads.get("consumer_staples") or {}
    utilities = payloads.get("utilities") or {}
    healthcare = payloads.get("healthcare") or {}
    financials = payloads.get("financials") or {}
    industrials = payloads.get("industrials") or {}

    metrics = {
        "broad_1y": _return_1y(broad),
        "broad_6m": _return_from_history(broad, 126),
        "broad_drawdown": safe_float(broad.get("drawdown_from_12m_high")),
        "broad_above_sma200": broad.get("price_above_sma_200"),
        "qqq_6m": _return_from_history(qqq, 126),
        "tech_6m": _return_from_history(tech, 126),
        "semi_6m": _return_from_history(semi, 126),
        "semi_1y": _return_1y(semi),
        "small_6m": _return_from_history(small, 126),
        "bonds_6m": _return_from_history(bonds, 126),
        "vix_level": safe_float(vix.get("current_price")),
        "tnx_3m": _return_from_history(tnx, 63),
        "tnx_1y": _return_1y(tnx),
        "defensive_6m": _average(
            [
                _return_from_history(staples, 126),
                _return_from_history(utilities, 126),
                _return_from_history(healthcare, 126),
            ]
        ),
        "financials_6m": _return_from_history(financials, 126),
        "industrials_6m": _return_from_history(industrials, 126),
    }
    broad_6m = metrics["broad_6m"]
    metrics["tech_relative_6m"] = _average([metrics["qqq_6m"], metrics["tech_6m"], metrics["semi_6m"]]) - broad_6m if broad_6m is not None else None
    metrics["small_relative_6m"] = metrics["small_6m"] - broad_6m if metrics["small_6m"] is not None and broad_6m is not None else None
    metrics["defensive_relative_6m"] = metrics["defensive_6m"] - broad_6m if metrics["defensive_6m"] is not None and broad_6m is not None else None
    sector_euphoria = compute_sector_euphoria(market_regime_data, metrics, config)

    bubble_points, bubble_reasons = _bubble_points(metrics)
    sector_points = safe_float(sector_euphoria.get("sector_euphoria_regime_points")) or 0.0
    if sector_points:
        bubble_points += sector_points
        bubble_reasons.extend(sector_euphoria.get("sector_euphoria_reasons") or [])
    risk_off_points, risk_off_reasons = _risk_off_points(metrics)
    rate_points, rate_reasons = _rate_stress_points(metrics)
    recession_points, recession_reasons = _recession_points(metrics)
    risk_on_points, risk_on_reasons = _risk_on_points(metrics)

    status = "NEUTRAL"
    score = 55
    reasons = ["Aucun régime extrême détecté avec les données gratuites disponibles."]
    if recession_points >= 45 and risk_off_points >= 30:
        status, score, reasons = "RECESSION_RISK", 100 - min(35, recession_points * 0.45), recession_reasons + risk_off_reasons
    elif risk_off_points >= 50:
        status, score, reasons = "RISK_OFF", 100 - min(40, risk_off_points * 0.50), risk_off_reasons
    elif bubble_points >= 45:
        status, score, reasons = "BUBBLE_RISK", 100 - min(30, bubble_points * 0.35), bubble_reasons
    elif rate_points >= 45:
        status, score, reasons = "RATE_STRESS", 100 - min(30, rate_points * 0.40), rate_reasons
    elif risk_on_points >= 45:
        status, score, reasons = "RISK_ON", min(85, 55 + risk_on_points * 0.35), risk_on_reasons

    return _regime_result(status, round(score, 1), metrics, reasons, config, sector_euphoria=sector_euphoria)


def apply_market_regime_context(
    analyses: dict[str, dict[str, Any]],
    regime: dict[str, Any],
    *,
    mode: str = "high-cagr",
    universe: str = "CORE_PORTFOLIO",
) -> None:
    for analysis in analyses.values():
        if analysis.get("ticker") == "VFV.TO" or analysis.get("benchmark_role") is True or is_etf_asset_analysis(analysis):
            continue
        analysis.update(compute_market_regime_adjustment(analysis, regime, mode=mode, universe=universe))


def apply_sector_euphoria_context(
    analyses: dict[str, dict[str, Any]],
    regime: dict[str, Any],
    *,
    mode: str = "high-cagr",
    universe: str = "CORE_PORTFOLIO",
) -> None:
    for analysis in analyses.values():
        if analysis.get("ticker") == "VFV.TO" or analysis.get("benchmark_role") is True or is_etf_asset_analysis(analysis):
            continue
        analysis.update(compute_sector_euphoria_adjustment(analysis, regime, mode=mode, universe=universe))


def compute_market_regime_adjustment(
    analysis: dict[str, Any],
    regime: dict[str, Any],
    *,
    mode: str = "high-cagr",
    universe: str = "CORE_PORTFOLIO",
) -> dict[str, Any]:
    status = str(regime.get("market_regime_status") or "NEUTRAL")
    impact = _mode_impact(regime, mode)
    exposure = _analysis_exposure(analysis)
    intensity = _regime_exposure_intensity(analysis, exposure, status)
    raw = 0.0
    reasons: list[str] = []

    if status == "BUBBLE_RISK":
        if intensity["score"] > 0:
            raw -= 0.08 * intensity["score"]
            reasons.append(
                "régime euphorique: exposition réelle "
                f"{intensity['level']} ({intensity['score']}/100)"
            )
        if exposure["hot_valuation"] and intensity["score"] >= 25:
            reasons.append("valorisation chaude: pénalité anti-bulle amplifiée")
        if exposure["tech_ai_semi"] and intensity["score"] >= 45:
            reasons.append("thème tech/IA/semi directement favorisé par le marché récent")
        if exposure["defensive_quality"] and intensity["score"] <= 35:
            raw += 0.8
            reasons.append("diversification de qualité dans un régime de bulle/tendance")
    elif status == "RATE_STRESS":
        if exposure["rate_sensitive"]:
            raw -= 4.0
            reasons.append("stress de taux: titre sensible aux taux ou à la durée de croissance")
        if exposure["strong_balance"]:
            raw += 0.7
            reasons.append("bilan solide: meilleure résistance au stress de taux")
    elif status == "RISK_OFF":
        if exposure["cyclical"] or exposure["high_beta"]:
            raw -= 4.0
            reasons.append("risk-off: exposition cyclique ou beta élevé")
        if exposure["quality_drawdown"]:
            raw += 1.2
            reasons.append("risk-off: baisse de qualité potentiellement exploitable avec thèse intacte")
        if exposure["defensive_quality"]:
            raw += 0.8
            reasons.append("profil plus défensif dans un régime risk-off")
    elif status == "RECESSION_RISK":
        if exposure["recession_sensitive"]:
            raw -= 4.5
            reasons.append("risque de récession: secteur plus sensible au cycle économique")
        if exposure["defensive_quality"]:
            raw += 1.0
            reasons.append("profil santé/consommation défensive dans un régime récession")
    elif status == "RISK_ON":
        if exposure["high_quality_growth"]:
            raw += 0.8
            reasons.append("risk-on: léger soutien aux compounders de croissance de qualité")

    if raw < 0 and exposure["exceptional_compounder"]:
        raw *= 0.60
        reasons.append("garde-fou: compounder exceptionnel, pénalité macro réduite")

    scaled = raw * impact["multiplier"]
    capped = _cap_adjustment(scaled, impact["max_penalty"], impact["max_bonus"])
    if not reasons:
        reasons.append("régime de marché sans impact matériel sur ce titre")

    return {
        "market_regime_status": status,
        "market_regime_score": regime.get("market_regime_score"),
        "market_regime_allocation_adjustment": round(capped, 2),
        "market_regime_exposure_intensity": intensity["score"],
        "market_regime_exposure_level": intensity["level"],
        "market_regime_exposure": ", ".join(key for key, value in exposure.items() if value) or "none",
        "market_regime_reason": "; ".join(reasons),
        "market_regime_guardrail": (
            "Impact plafonné: aucun achat/vente automatique, aucun market timing, aucun cash volontaire. "
            f"Mode {mode}: ajustement max -{impact['max_penalty']}/+{impact['max_bonus']} points."
        ),
        "market_regime_universe": universe,
    }


def compute_sector_euphoria_adjustment(
    analysis: dict[str, Any],
    regime: dict[str, Any],
    *,
    mode: str = "high-cagr",
    universe: str = "CORE_PORTFOLIO",
) -> dict[str, Any]:
    sector_euphoria = regime.get("sector_euphoria") if isinstance(regime.get("sector_euphoria"), dict) else {}
    active = sector_euphoria.get("sector_euphoria_status") == "ACTIVE"
    impact = _sector_euphoria_mode_impact(sector_euphoria, mode)
    exposure = _sector_euphoria_exposure(analysis, sector_euphoria)
    intensity = safe_float(exposure.get("sector_euphoria_exposure_intensity")) or 0.0
    raw = 0.0
    reasons: list[str] = []

    if active and intensity > 0:
        raw -= 0.045 * intensity
        reasons.append(
            "secteur euphorique: exposition "
            f"{exposure.get('sector_euphoria_exposure_level')} ({int(round(intensity))}/100)"
        )
        if analysis.get("quality_but_too_expensive") is True or (safe_float(analysis.get("peg")) or 0.0) > 3:
            raw -= 0.4
            reasons.append("valorisation chaude dans un secteur déjà favorisé")
        if str(analysis.get("cycle_bubble_risk_level") or "").upper() in {"HIGH", "EXTREME"}:
            raw -= 0.3
            reasons.append("risque cycle/bulle déjà élevé sur le titre")
        if analysis.get("thesis_status") == "INTACT" and analysis.get("expected_cagr_quality") in {"HIGH", "VERY_HIGH"}:
            raw += 0.25
            reasons.append("thèse intacte et qualité de CAGR élevée: pénalité sectorielle adoucie")
        if exposure.get("sector_euphoria_exposure_level") in {"LOW", "NONE"}:
            raw *= 0.5
            reasons.append("exposition sectorielle indirecte: effet réduit")
    else:
        reasons.append("aucune euphorie sectorielle matérielle ou aucune exposition directe détectée")

    if raw < 0 and _is_exceptional_compounder(analysis):
        raw *= 0.70
        reasons.append("garde-fou: compounder exceptionnel, pénalité sectorielle réduite")

    scaled = raw * impact["multiplier"]
    capped = _cap_adjustment(scaled, impact["max_penalty"], impact["max_bonus"])
    dominant = sector_euphoria.get("dominant_euphoric_sectors") or []
    return {
        "sector_euphoria_status": sector_euphoria.get("sector_euphoria_status", "INACTIVE"),
        "sector_euphoria_score": sector_euphoria.get("sector_euphoria_score", 0),
        "sector_euphoria_dominant_sectors": ", ".join(row.get("sector", "") for row in dominant[:3]) or "none",
        "sector_euphoria_allocation_adjustment": round(capped, 2),
        "sector_euphoria_exposure": exposure.get("sector_euphoria_exposure", "none"),
        "sector_euphoria_exposure_intensity": int(round(intensity)),
        "sector_euphoria_exposure_level": exposure.get("sector_euphoria_exposure_level", "NONE"),
        "sector_euphoria_reason": "; ".join(reasons),
        "sector_euphoria_guardrail": (
            "Impact plafonné et secondaire: aucune vente automatique, aucun cash volontaire, "
            f"mode {mode}: max -{impact['max_penalty']}/+{impact['max_bonus']} points."
        ),
        "sector_euphoria_universe": universe,
    }


def market_regime_rows(regime: dict[str, Any]) -> list[dict[str, Any]]:
    rows = list(regime.get("rows") or [])
    if not rows:
        rows = [
            {
                "metric": "Régime de marché",
                "status": regime.get("market_regime_status", "N/D"),
                "value": regime.get("market_regime_score", ""),
                "interpretation": regime.get("market_regime_interpretation", ""),
                "impact": regime.get("market_regime_guardrail", ""),
            }
        ]
    return rows


def market_regime_analysis_rows(*analysis_groups: tuple[str, dict[str, dict[str, Any]]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for universe, analyses in analysis_groups:
        for analysis in analyses.values():
            adjustment = safe_float(analysis.get("market_regime_allocation_adjustment")) or 0.0
            if adjustment == 0 and not analysis.get("market_regime_status"):
                continue
            rows.append(
                {
                    "universe": universe,
                    "ticker": analysis.get("ticker_display", analysis.get("ticker")),
                    "market_regime_status": analysis.get("market_regime_status"),
                    "market_regime_score": analysis.get("market_regime_score"),
                    "market_regime_allocation_adjustment": adjustment,
                    "market_regime_exposure_intensity": analysis.get("market_regime_exposure_intensity"),
                    "market_regime_exposure_level": analysis.get("market_regime_exposure_level"),
                    "market_regime_exposure": analysis.get("market_regime_exposure"),
                    "market_regime_reason": analysis.get("market_regime_reason"),
                    "market_regime_guardrail": analysis.get("market_regime_guardrail"),
                }
            )
    return sorted(rows, key=lambda row: abs(safe_float(row.get("market_regime_allocation_adjustment")) or 0.0), reverse=True)


def sector_euphoria_rows(regime: dict[str, Any]) -> list[dict[str, Any]]:
    sector_euphoria = regime.get("sector_euphoria") if isinstance(regime.get("sector_euphoria"), dict) else {}
    rows = sector_euphoria.get("sector_euphoria_rows") or []
    if rows:
        return rows
    return [
        {
            "sector": "Aucun",
            "ticker": "",
            "sector_euphoria_status": sector_euphoria.get("sector_euphoria_status", "INACTIVE"),
            "sector_euphoria_score": sector_euphoria.get("sector_euphoria_score", 0),
            "return_6m": "",
            "relative_6m_vs_market": "",
            "return_1y": "",
            "relative_1y_vs_market": "",
            "above_sma_200": "",
            "reason": sector_euphoria.get("sector_euphoria_reason", "Aucune euphorie sectorielle matérielle détectée."),
        }
    ]


def sector_euphoria_analysis_rows(*analysis_groups: tuple[str, dict[str, dict[str, Any]]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for universe, analyses in analysis_groups:
        for analysis in analyses.values():
            adjustment = safe_float(analysis.get("sector_euphoria_allocation_adjustment")) or 0.0
            if adjustment == 0 and not analysis.get("sector_euphoria_status"):
                continue
            rows.append(
                {
                    "universe": universe,
                    "ticker": analysis.get("ticker_display", analysis.get("ticker")),
                    "sector_euphoria_status": analysis.get("sector_euphoria_status"),
                    "sector_euphoria_score": analysis.get("sector_euphoria_score"),
                    "sector_euphoria_allocation_adjustment": adjustment,
                    "sector_euphoria_exposure_intensity": analysis.get("sector_euphoria_exposure_intensity"),
                    "sector_euphoria_exposure": analysis.get("sector_euphoria_exposure"),
                    "sector_euphoria_reason": analysis.get("sector_euphoria_reason"),
                    "sector_euphoria_guardrail": analysis.get("sector_euphoria_guardrail"),
                }
            )
    return sorted(rows, key=lambda row: abs(safe_float(row.get("sector_euphoria_allocation_adjustment")) or 0.0), reverse=True)


def write_market_regime_csvs(
    reports_dir: str | Path,
    regime: dict[str, Any],
    *analysis_groups: tuple[str, dict[str, dict[str, Any]]],
) -> None:
    reports_dir = Path(reports_dir)
    write_csv_records(reports_dir / "latest_market_regime_report.csv", market_regime_rows(regime), MARKET_REGIME_COLUMNS)
    write_csv_records(
        reports_dir / "latest_market_regime_allocations.csv",
        market_regime_analysis_rows(*analysis_groups),
        MARKET_REGIME_ANALYSIS_COLUMNS,
    )
    write_csv_records(reports_dir / "latest_sector_euphoria_report.csv", sector_euphoria_rows(regime), SECTOR_EUPHORIA_COLUMNS)
    write_csv_records(
        reports_dir / "latest_sector_euphoria_allocations.csv",
        sector_euphoria_analysis_rows(*analysis_groups),
        SECTOR_EUPHORIA_ANALYSIS_COLUMNS,
    )


def _regime_result(
    status: str,
    score: float,
    metrics: dict[str, Any],
    reasons: list[str],
    config: dict[str, Any],
    *,
    sector_euphoria: dict[str, Any] | None = None,
) -> dict[str, Any]:
    sector_euphoria = sector_euphoria or _empty_sector_euphoria()
    interpretation = _regime_interpretation(status)
    rows = [
        {
            "metric": "Régime de marché",
            "status": status,
            "value": score,
            "interpretation": interpretation,
            "impact": "Contexte de sizing seulement; ne déclenche jamais une vente ou du cash volontaire.",
        },
        {
            "metric": "Signaux principaux",
            "status": "INFO",
            "value": "; ".join(reasons[:4]),
            "interpretation": "Lecture basée sur ETF/indices gratuits et données yfinance.",
            "impact": "Aide à réduire les allocations trop concentrées dans un thème de marché extrême.",
        },
        {
            "metric": "Euphorie sectorielle",
            "status": sector_euphoria.get("sector_euphoria_status", "INACTIVE"),
            "value": sector_euphoria.get("sector_euphoria_score", 0),
            "interpretation": sector_euphoria.get("sector_euphoria_reason", "Aucune euphorie sectorielle matérielle détectée."),
            "impact": "Impact séparé, léger et plafonné sur les titres directement exposés seulement.",
        },
        {
            "metric": "Garde-fou anti-surcorrection",
            "status": "ACTIVE",
            "value": "impact plafonné",
            "interpretation": "Le régime ne remplace pas les fondamentaux, la thèse, la valorisation ou VFV.",
            "impact": "Protège le profil long terme contre le market timing macro.",
        },
        {
            "metric": "Sources gratuites suivies",
            "status": "YFINANCE_PROXY",
            "value": ", ".join(market_regime_tickers(config)),
            "interpretation": "ETF/indices utilisés comme proxys de climat de marché.",
            "impact": "Sources gratuites imparfaites, mais répétables et compatibles avec un agent local.",
        },
    ]
    return {
        "market_regime_status": status,
        "market_regime_score": score,
        "market_regime_metrics": metrics,
        "market_regime_reasons": reasons,
        "market_regime_interpretation": interpretation,
        "market_regime_guardrail": "Impact plafonné; aucun signal de vente automatique; aucun cash volontaire.",
        "market_regime_sources": ", ".join(market_regime_tickers(config)),
        "sector_euphoria": sector_euphoria,
        "config": config,
        "rows": rows,
    }


def _bubble_points(metrics: dict[str, Any]) -> tuple[float, list[str]]:
    points = 0.0
    reasons: list[str] = []
    tech_rel = metrics.get("tech_relative_6m")
    semi_6m = metrics.get("semi_6m")
    semi_1y = metrics.get("semi_1y")
    vix = metrics.get("vix_level")
    broad_above = metrics.get("broad_above_sma200")
    if tech_rel is not None and tech_rel > 0.12:
        points += 18
        reasons.append(f"tech/IA/semi surperforme le marché large sur 6 mois ({pct(tech_rel)})")
    if semi_6m is not None and semi_6m > 0.25:
        points += 16
        reasons.append(f"semi-conducteurs très forts sur 6 mois ({pct(semi_6m)})")
    if semi_1y is not None and semi_1y > 0.45:
        points += 14
        reasons.append(f"semi-conducteurs très forts sur 1 an ({pct(semi_1y)})")
    if broad_above is True:
        points += 5
    if vix is not None and vix < 18:
        points += 6
        reasons.append(f"VIX bas ({vix:.1f}) pendant leadership de croissance")
    return points, reasons


def _risk_off_points(metrics: dict[str, Any]) -> tuple[float, list[str]]:
    points = 0.0
    reasons: list[str] = []
    broad_above = metrics.get("broad_above_sma200")
    broad_drawdown = metrics.get("broad_drawdown")
    vix = metrics.get("vix_level")
    small_rel = metrics.get("small_relative_6m")
    if broad_above is False:
        points += 18
        reasons.append("marché large sous SMA 200")
    if broad_drawdown is not None and broad_drawdown <= -0.12:
        points += 14
        reasons.append(f"drawdown du marché large ({pct(broad_drawdown)})")
    if vix is not None and vix >= 25:
        points += 14
        reasons.append(f"VIX élevé ({vix:.1f})")
    if small_rel is not None and small_rel <= -0.10:
        points += 10
        reasons.append(f"petites capitalisations faibles vs marché large ({pct(small_rel)})")
    return points, reasons


def _rate_stress_points(metrics: dict[str, Any]) -> tuple[float, list[str]]:
    points = 0.0
    reasons: list[str] = []
    tnx_3m = metrics.get("tnx_3m")
    tnx_1y = metrics.get("tnx_1y")
    bonds_6m = metrics.get("bonds_6m")
    if tnx_3m is not None and tnx_3m > 0.10:
        points += 18
        reasons.append(f"taux 10 ans en hausse sur 3 mois ({pct(tnx_3m)})")
    if tnx_1y is not None and tnx_1y > 0.20:
        points += 14
        reasons.append(f"taux 10 ans en hausse sur 1 an ({pct(tnx_1y)})")
    if bonds_6m is not None and bonds_6m < -0.08:
        points += 16
        reasons.append(f"obligations longues faibles sur 6 mois ({pct(bonds_6m)})")
    return points, reasons


def _recession_points(metrics: dict[str, Any]) -> tuple[float, list[str]]:
    points = 0.0
    reasons: list[str] = []
    defensive_rel = metrics.get("defensive_relative_6m")
    small_rel = metrics.get("small_relative_6m")
    financials = metrics.get("financials_6m")
    industrials = metrics.get("industrials_6m")
    broad_above = metrics.get("broad_above_sma200")
    if broad_above is False:
        points += 12
    if defensive_rel is not None and defensive_rel > 0.06:
        points += 14
        reasons.append(f"secteurs défensifs surperforment ({pct(defensive_rel)})")
    if small_rel is not None and small_rel < -0.12:
        points += 12
        reasons.append(f"petites capitalisations sous-performent ({pct(small_rel)})")
    if financials is not None and financials < -0.08:
        points += 8
        reasons.append(f"financières faibles ({pct(financials)})")
    if industrials is not None and industrials < -0.08:
        points += 8
        reasons.append(f"industriels faibles ({pct(industrials)})")
    return points, reasons


def _risk_on_points(metrics: dict[str, Any]) -> tuple[float, list[str]]:
    points = 0.0
    reasons: list[str] = []
    broad = metrics.get("broad_6m")
    broad_above = metrics.get("broad_above_sma200")
    vix = metrics.get("vix_level")
    small_rel = metrics.get("small_relative_6m")
    if broad_above is True:
        points += 16
        reasons.append("marché large au-dessus SMA 200")
    if broad is not None and broad > 0.06:
        points += 12
        reasons.append(f"marché large positif sur 6 mois ({pct(broad)})")
    if small_rel is not None and small_rel > -0.03:
        points += 8
        reasons.append("petites capitalisations ne décrochent pas fortement")
    if vix is not None and vix < 22:
        points += 8
        reasons.append(f"volatilité contenue (VIX {vix:.1f})")
    return points, reasons


def compute_sector_euphoria(
    market_regime_data: dict[str, dict[str, Any]],
    market_metrics: dict[str, Any],
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    config = config or DEFAULT_MARKET_REGIME_CONFIG
    sector_config = config.get("sector_euphoria") if isinstance(config.get("sector_euphoria"), dict) else {}
    if sector_config.get("enabled", True) is False:
        return _empty_sector_euphoria(status="DISABLED", reason="Détecteur d’euphorie sectorielle désactivé.")

    sectors = sector_config.get("sectors") or {}
    broad_6m = safe_float(market_metrics.get("broad_6m"))
    broad_1y = safe_float(market_metrics.get("broad_1y"))
    activation_score = safe_float(sector_config.get("activation_score")) or 55.0
    rows: list[dict[str, Any]] = []
    dominant: list[dict[str, Any]] = []

    for sector, ticker in sectors.items():
        ticker_text = str(ticker).strip().upper()
        payload = market_regime_data.get(ticker_text) or {}
        ret_6m = _return_from_history(payload, 126)
        ret_1y = _return_1y(payload)
        rel_6m = ret_6m - broad_6m if ret_6m is not None and broad_6m is not None else None
        rel_1y = ret_1y - broad_1y if ret_1y is not None and broad_1y is not None else None
        above_sma = payload.get("price_above_sma_200")
        score, reason = _sector_euphoria_score(ret_6m, rel_6m, ret_1y, rel_1y, above_sma)
        row = {
            "sector": str(sector),
            "ticker": ticker_text,
            "sector_euphoria_status": "ACTIVE" if score >= activation_score else "INACTIVE",
            "sector_euphoria_score": round(score, 1),
            "return_6m": round(ret_6m, 4) if ret_6m is not None else "",
            "relative_6m_vs_market": round(rel_6m, 4) if rel_6m is not None else "",
            "return_1y": round(ret_1y, 4) if ret_1y is not None else "",
            "relative_1y_vs_market": round(rel_1y, 4) if rel_1y is not None else "",
            "above_sma_200": above_sma,
            "reason": reason,
        }
        rows.append(row)
        if score >= activation_score:
            dominant.append(row)

    max_reported = int(safe_float(sector_config.get("max_reported_sectors")) or 5)
    rows = sorted(rows, key=lambda row: safe_float(row.get("sector_euphoria_score")) or 0.0, reverse=True)
    dominant = sorted(dominant, key=lambda row: safe_float(row.get("sector_euphoria_score")) or 0.0, reverse=True)[:max_reported]
    if dominant:
        top = dominant[0]
        reason = "Secteurs dominants: " + ", ".join(
            f"{row.get('sector')} ({row.get('sector_euphoria_score')}/100)" for row in dominant[:3]
        )
        points = min(26.0, 10.0 + ((safe_float(top.get("sector_euphoria_score")) or 0.0) - activation_score) * 0.45)
        return {
            "sector_euphoria_status": "ACTIVE",
            "sector_euphoria_score": top.get("sector_euphoria_score"),
            "dominant_euphoric_sectors": dominant,
            "sector_euphoria_rows": rows,
            "sector_euphoria_reason": reason,
            "sector_euphoria_reasons": [reason],
            "sector_euphoria_regime_points": round(points, 1),
            "config": sector_config,
        }
    return {
        **_empty_sector_euphoria(reason="Aucun secteur ne dépasse le seuil d’euphorie matérielle."),
        "sector_euphoria_rows": rows,
        "config": sector_config,
    }


def _sector_euphoria_score(
    ret_6m: float | None,
    rel_6m: float | None,
    ret_1y: float | None,
    rel_1y: float | None,
    above_sma: Any,
) -> tuple[float, str]:
    score = 0.0
    reasons: list[str] = []
    if rel_6m is not None and rel_6m >= 0.15:
        score += min(30.0, 12.0 + rel_6m * 80.0)
        reasons.append(f"surperformance 6 mois vs marché {pct(rel_6m)}")
    if rel_1y is not None and rel_1y >= 0.25:
        score += min(25.0, 8.0 + rel_1y * 45.0)
        reasons.append(f"surperformance 1 an vs marché {pct(rel_1y)}")
    if ret_6m is not None and ret_6m >= 0.25:
        score += min(20.0, 8.0 + ret_6m * 35.0)
        reasons.append(f"hausse 6 mois forte {pct(ret_6m)}")
    if ret_1y is not None and ret_1y >= 0.45:
        score += min(15.0, 5.0 + ret_1y * 18.0)
        reasons.append(f"hausse 1 an forte {pct(ret_1y)}")
    if above_sma is True and score > 0:
        score += 6.0
        reasons.append("prix au-dessus SMA 200")
    if not reasons:
        reasons.append("pas d’euphorie sectorielle matérielle détectée")
    return min(100.0, score), "; ".join(reasons)


def _empty_sector_euphoria(status: str = "INACTIVE", reason: str = "Aucune euphorie sectorielle matérielle détectée.") -> dict[str, Any]:
    return {
        "sector_euphoria_status": status,
        "sector_euphoria_score": 0,
        "dominant_euphoric_sectors": [],
        "sector_euphoria_rows": [],
        "sector_euphoria_reason": reason,
        "sector_euphoria_reasons": [],
        "sector_euphoria_regime_points": 0.0,
    }


def _analysis_exposure(analysis: dict[str, Any]) -> dict[str, bool]:
    profile = str(analysis.get("cycle_risk_profile") or "").upper()
    sector = str(analysis.get("sector") or "").lower()
    benchmark = str(analysis.get("benchmark_ticker") or "").upper()
    factors = {str(item).lower() for item in (analysis.get("factor_exposure") or [])}
    theme_text = " ".join([sector, benchmark.lower(), " ".join(sorted(factors))]).lower()
    text = " ".join([profile.lower(), theme_text]).lower()
    direct_tech_theme = (
        benchmark in REGIME_TECH_AI_SEMI_BENCHMARKS
        or bool(factors & REGIME_TECH_AI_SEMI_FACTORS)
        or any(term in theme_text for term in REGIME_TECH_AI_SEMI_TERMS)
    )
    net_debt_to_fcf = safe_float(analysis.get("net_debt_to_fcf"))
    tech_ai_semi = (
        profile == "SEMI_CAPEX_CYCLE"
        or direct_tech_theme
        or (profile == "TECH_AI_GROWTH_THEME" and direct_tech_theme)
    )
    cyclical = profile in {"SEMI_CAPEX_CYCLE", "RESOURCE_CYCLE", "ENERGY_CYCLE", "INDUSTRIAL_CYCLE", "CONSUMER_CYCLE", "FINANCIAL_MARKET_CYCLE"}
    recession_sensitive = cyclical or any(term in text for term in ["consumer", "industrial", "financial", "bank", "machinery"])
    defensive_quality = any(term in text for term in ["health", "healthcare", "pharma", "consumer staples", "utility", "utilities"])
    return {
        "tech_ai_semi": tech_ai_semi,
        "cyclical": cyclical,
        "recession_sensitive": recession_sensitive,
        "rate_sensitive": "rates_sensitive" in factors or "growth" in factors or profile == "RATE_SENSITIVE_DEFENSIVE",
        "high_beta": (safe_float(analysis.get("beta")) or 0.0) >= 1.35,
        "hot_valuation": analysis.get("quality_but_too_expensive") is True or (safe_float(analysis.get("peg")) or 0.0) > 3,
        "strong_balance": analysis.get("balance_sheet_strong") is True or (net_debt_to_fcf is not None and net_debt_to_fcf < 2),
        "quality_drawdown": str(analysis.get("quality_drawdown_status") or "") in {"QUALITY_DRAWDOWN_OPPORTUNITY", "POSSIBLE_QUALITY_DRAWDOWN"},
        "high_quality_growth": analysis.get("thesis_status") == "INTACT" and analysis.get("expected_cagr_quality") in {"HIGH", "VERY_HIGH"},
        "exceptional_compounder": (
            analysis.get("thesis_status") == "INTACT"
            and analysis.get("opportunity_cost_status") == "CLEARLY_BETTER_THAN_VFV"
            and analysis.get("expected_cagr_quality") in {"HIGH", "VERY_HIGH"}
            and (safe_float(analysis.get("conviction_score")) or 0.0) >= 85
        ),
        "defensive_quality": defensive_quality,
    }


def _regime_exposure_intensity(analysis: dict[str, Any], exposure: dict[str, bool], status: str) -> dict[str, Any]:
    if status == "BUBBLE_RISK":
        score = _bubble_exposure_intensity(analysis, exposure)
    elif status == "RATE_STRESS":
        score = 35 if exposure["rate_sensitive"] else 0
        if exposure["hot_valuation"]:
            score += 15
        if exposure["strong_balance"]:
            score -= 8
    elif status == "RISK_OFF":
        score = 0
        if exposure["cyclical"]:
            score += 35
        if exposure["high_beta"]:
            score += 20
        if exposure["defensive_quality"]:
            score -= 20
        if exposure["quality_drawdown"]:
            score -= 8
    elif status == "RECESSION_RISK":
        score = 40 if exposure["recession_sensitive"] else 0
        if exposure["cyclical"]:
            score += 15
        if exposure["defensive_quality"]:
            score -= 25
    elif status == "RISK_ON":
        score = 25 if exposure["high_quality_growth"] else 0
    else:
        score = 0
    score = int(round(max(0, min(100, score))))
    return {"score": score, "level": _intensity_level(score)}


def _bubble_exposure_intensity(analysis: dict[str, Any], exposure: dict[str, bool]) -> float:
    score = 0.0
    score += _theme_exposure_score(analysis)
    if exposure["hot_valuation"]:
        score += 20
    if exposure["high_beta"]:
        score += 10
    if exposure["cyclical"]:
        score += 10

    bubble_level = str(analysis.get("cycle_bubble_risk_level") or "").upper()
    if bubble_level == "EXTREME":
        score += 15
    elif bubble_level == "HIGH":
        score += 10
    elif bubble_level == "MEDIUM":
        score += 5

    bubble_score = safe_float(analysis.get("cycle_bubble_score"))
    if bubble_score is not None:
        if bubble_score >= 85:
            score += 10
        elif bubble_score >= 70:
            score += 6

    if exposure["quality_drawdown"]:
        score -= 8
    if exposure["strong_balance"]:
        score -= 5
    if exposure["defensive_quality"]:
        score -= 25
    if exposure["exceptional_compounder"]:
        score -= 10
    return max(0.0, min(100.0, score))


def _theme_exposure_score(analysis: dict[str, Any]) -> float:
    profile = str(analysis.get("cycle_risk_profile") or "").upper()
    sector = str(analysis.get("sector") or "").lower()
    benchmark = str(analysis.get("benchmark_ticker") or "").upper()
    factors = {str(item).lower() for item in (analysis.get("factor_exposure") or [])}
    text = " ".join([sector, benchmark.lower(), " ".join(sorted(factors))]).lower()
    score = 0.0
    if profile == "SEMI_CAPEX_CYCLE" or benchmark in {"SOXX", "SMH"} or "semiconductors" in factors or "semiconductor" in text:
        score += 38
    elif benchmark in {"XLK", "IGV", "QQQ", "XLC"}:
        score += 28
    elif factors & REGIME_TECH_AI_SEMI_FACTORS or any(term in text for term in REGIME_TECH_AI_SEMI_TERMS):
        score += 24
    if profile == "TECH_AI_GROWTH_THEME" and score > 0:
        score += 8
    return min(45.0, score)


def _intensity_level(score: int) -> str:
    if score >= 75:
        return "VERY_HIGH"
    if score >= 55:
        return "HIGH"
    if score >= 35:
        return "MEDIUM"
    if score >= 15:
        return "LOW"
    return "NONE"


def _sector_euphoria_exposure(analysis: dict[str, Any], sector_euphoria: dict[str, Any]) -> dict[str, Any]:
    dominant = sector_euphoria.get("dominant_euphoric_sectors") or []
    if not dominant:
        return {
            "sector_euphoria_exposure": "none",
            "sector_euphoria_exposure_intensity": 0,
            "sector_euphoria_exposure_level": "NONE",
        }

    best_sector = ""
    best_intensity = 0.0
    for row in dominant:
        sector = str(row.get("sector") or "")
        sector_score = safe_float(row.get("sector_euphoria_score")) or 0.0
        exposure_score = _sector_match_score(analysis, sector, str(row.get("ticker") or ""))
        intensity = min(100.0, sector_score * exposure_score / 100.0)
        if intensity > best_intensity:
            best_sector = sector
            best_intensity = intensity

    intensity = int(round(max(0.0, min(100.0, best_intensity))))
    return {
        "sector_euphoria_exposure": best_sector or "none",
        "sector_euphoria_exposure_intensity": intensity,
        "sector_euphoria_exposure_level": _intensity_level(intensity),
    }


def _sector_match_score(analysis: dict[str, Any], sector: str, sector_ticker: str) -> float:
    sector_key = str(sector or "").lower()
    sector_text = str(analysis.get("sector") or "").lower()
    benchmark = str(analysis.get("benchmark_ticker") or "").upper()
    profile = str(analysis.get("cycle_risk_profile") or "").upper()
    factors = {str(item).lower() for item in (analysis.get("factor_exposure") or [])}
    text = " ".join([sector_text, benchmark.lower(), profile.lower(), " ".join(sorted(factors))])
    keywords = SECTOR_EUPHORIA_KEYWORDS.get(sector_key, {sector_key.replace("_", " ")})
    score = 0.0
    if benchmark and benchmark == str(sector_ticker or "").upper():
        score += 45.0
    if sector_key.replace("_", " ") in sector_text or sector_key in factors:
        score += 35.0
    if any(keyword in text for keyword in keywords):
        score += 30.0
    if _profile_matches_sector(profile, sector_key):
        score += 15.0
    if sector_key == "semiconductors" and (benchmark in {"SOXX", "SMH"} or "semiconductors" in factors):
        score += 20.0
    if sector_key == "technology" and benchmark in {"XLK", "IGV", "QQQ"}:
        score += 15.0
    if sector_key == "crypto" and is_etf_asset_analysis(analysis):
        score += 15.0
    return min(100.0, score)


def _profile_matches_sector(profile: str, sector_key: str) -> bool:
    return (
        (profile == "SEMI_CAPEX_CYCLE" and sector_key == "semiconductors")
        or (profile == "RESOURCE_CYCLE" and sector_key in {"materials", "gold", "uranium", "energy"})
        or (profile == "ENERGY_CYCLE" and sector_key == "energy")
        or (profile == "INDUSTRIAL_CYCLE" and sector_key in {"industrials", "defense_aerospace"})
        or (profile == "CONSUMER_CYCLE" and sector_key == "consumer_discretionary")
        or (profile == "FINANCIAL_MARKET_CYCLE" and sector_key in {"financials", "regional_banks"})
    )


def _is_exceptional_compounder(analysis: dict[str, Any]) -> bool:
    return (
        analysis.get("thesis_status") == "INTACT"
        and analysis.get("opportunity_cost_status") == "CLEARLY_BETTER_THAN_VFV"
        and analysis.get("expected_cagr_quality") in {"HIGH", "VERY_HIGH"}
        and (safe_float(analysis.get("conviction_score")) or 0.0) >= 85
    )


def _mode_impact(regime: dict[str, Any], mode: str) -> dict[str, float]:
    config = regime.get("config") if isinstance(regime.get("config"), dict) else None
    mode_impact = ((config or DEFAULT_MARKET_REGIME_CONFIG).get("mode_impact") or {}).get(mode)
    if not isinstance(mode_impact, dict):
        mode_impact = DEFAULT_MARKET_REGIME_CONFIG["mode_impact"].get(mode, DEFAULT_MARKET_REGIME_CONFIG["mode_impact"]["high-cagr"])
    return {
        "max_penalty": safe_float(mode_impact.get("max_penalty")) or 4.0,
        "max_bonus": safe_float(mode_impact.get("max_bonus")) or 1.5,
        "multiplier": safe_float(mode_impact.get("multiplier")) or 0.55,
    }


def _sector_euphoria_mode_impact(sector_euphoria: dict[str, Any], mode: str) -> dict[str, float]:
    config = sector_euphoria.get("config") if isinstance(sector_euphoria.get("config"), dict) else None
    mode_impact = ((config or DEFAULT_MARKET_REGIME_CONFIG["sector_euphoria"]).get("mode_impact") or {}).get(mode)
    if not isinstance(mode_impact, dict):
        mode_impact = DEFAULT_MARKET_REGIME_CONFIG["sector_euphoria"]["mode_impact"].get(
            mode,
            DEFAULT_MARKET_REGIME_CONFIG["sector_euphoria"]["mode_impact"]["high-cagr"],
        )
    return {
        "max_penalty": safe_float(mode_impact.get("max_penalty")) or 2.5,
        "max_bonus": safe_float(mode_impact.get("max_bonus")) or 0.5,
        "multiplier": safe_float(mode_impact.get("multiplier")) or 0.60,
    }


def _cap_adjustment(value: float, max_penalty: float, max_bonus: float) -> float:
    return max(-abs(max_penalty), min(abs(max_bonus), value))


def _return_1y(payload: dict[str, Any]) -> float | None:
    return safe_float(payload.get("adjusted_stock_return_1y")) if safe_float(payload.get("adjusted_stock_return_1y")) is not None else safe_float(payload.get("stock_return_1y"))


def _return_from_history(payload: dict[str, Any], trading_days: int) -> float | None:
    history = payload.get("total_return_price_history")
    if not isinstance(history, dict) or len(history) < max(5, trading_days // 3):
        return None
    values = [
        safe_float(value)
        for _, value in sorted((str(key), value) for key, value in history.items())
    ]
    values = [value for value in values if value is not None and value > 0]
    if len(values) < 2:
        return None
    current = values[-1]
    previous = values[-min(trading_days, len(values))]
    return current / previous - 1 if previous > 0 else None


def _average(values: list[float | None]) -> float | None:
    numbers = [value for value in values if value is not None]
    if not numbers:
        return None
    return sum(numbers) / len(numbers)


def _regime_interpretation(status: str) -> str:
    return {
        "DISABLED": "La couche de régime de marché est désactivée.",
        "RISK_ON": "Le marché large est constructif; l’appétit pour le risque semble raisonnable.",
        "NEUTRAL": "Aucun régime extrême clair; les fondamentaux des titres restent le moteur principal.",
        "RISK_OFF": "Le marché montre des signes de stress; le sizing des titres cycliques ou très volatils est légèrement surveillé.",
        "BUBBLE_RISK": "Un thème de croissance/tech/semi semble très dominant; le modèle limite modérément la surexposition au thème chaud.",
        "RATE_STRESS": "Les taux ou obligations signalent un stress; le modèle surveille les titres sensibles aux taux.",
        "RECESSION_RISK": "Les signaux de marché pointent vers un risque économique plus défensif; le sizing des cycliques est légèrement encadré.",
    }.get(status, "Régime non reconnu.")
