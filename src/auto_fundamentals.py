from __future__ import annotations

from typing import Any

from .manual_inputs import CATASTROPHIC_COLUMNS, MANUAL_COLUMNS, empty_manual_row, parse_manual_row
from .proxy_correction_engine import apply_proxy_correction
from .utils import first_present, safe_float


FORWARD_EPS_HIGH_MEDIUM_WEIGHT = 0.60
FORWARD_EPS_HIGH_MEDIUM_PROXY_WEIGHT = 0.40
FORWARD_EPS_LOW_CONFIDENCE_WEIGHT = 0.30
FORWARD_EPS_LOW_CONFIDENCE_PROXY_WEIGHT = 0.70
FORWARD_EPS_HIGH_CONFIDENCE_ANALYSTS = 10
FORWARD_EPS_MEDIUM_CONFIDENCE_ANALYSTS = 5
FORWARD_EPS_MIN_ANALYSTS = 1
FORWARD_EPS_MIN_GROWTH = -0.50
FORWARD_EPS_MAX_GROWTH = 2.00
EPS_SANITY_REVIEW_DIVERGENCE = 0.40

CORE_AUTO_FIELDS = {
    "roic_5y_avg",
    "net_margin_stable_or_expanding",
    "eps_growth_5y",
    "moat_clear",
    "eps_growth_estimated_3_5y",
    "sector_cagr_estimated",
    "fair_value",
    "valuation_vs_5y_avg_ok",
    "forward_pe_growth_acceptable",
    "management_quality_good",
    "balance_sheet_strong",
}

OFFICIAL_MARKET_TO_MANUAL_FIELDS = {
    "return_on_equity": ["roic_5y_avg"],
    "return_on_assets": ["roic_5y_avg"],
    "profit_margins": ["net_margin_stable_or_expanding", "margin_or_profitability_under_pressure"],
    "gross_margins": ["net_margin_stable_or_expanding", "margin_or_profitability_under_pressure"],
    "operating_margins": ["net_margin_stable_or_expanding", "margin_or_profitability_under_pressure"],
    "free_cash_flow_margin": ["net_margin_stable_or_expanding", "margin_or_profitability_under_pressure"],
    "fcf_conversion": ["net_margin_stable_or_expanding", "margin_or_profitability_under_pressure"],
    "revenue_growth": ["eps_growth_5y", "eps_growth_estimated_3_5y"],
    "earnings_growth": ["eps_growth_5y", "eps_growth_estimated_3_5y"],
    "free_cash_flow_growth": ["eps_growth_5y", "eps_growth_estimated_3_5y"],
    "total_cash": ["balance_sheet_strong"],
    "total_debt": ["balance_sheet_strong"],
    "debt_to_equity": ["balance_sheet_strong"],
    "net_debt_to_fcf": ["balance_sheet_strong"],
    "peg": ["peg_manual"],
    "trailing_pe": ["peg_manual"],
}


def build_automated_manual_inputs(
    ticker: str,
    market: dict[str, Any],
    benchmark: dict[str, Any],
    proxy_corrections: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a conservative manual-input equivalent from free market data.

    These values are not meant to be perfect fundamental research. They let the
    agent run without a mandatory manual file while keeping source labels so the
    report can clearly say what was estimated automatically.
    """

    row = empty_manual_row(ticker)
    estimated_fields: list[str] = []
    source_notes: list[str] = []
    corrections_applied: list[dict[str, Any]] = []

    def set_auto(field: str, value: Any, source: str) -> None:
        if field not in MANUAL_COLUMNS:
            return
        if value is None or value == "":
            return
        adjusted_value, correction = apply_proxy_correction(field, value, proxy_corrections)
        if correction:
            corrections_applied.append(correction)
            value = adjusted_value
            source = (
                f"{source}; correction proxy active facteur {correction['factor']:.4f} "
                f"({correction.get('confidence') or 'N/D'}, n={correction.get('sample_count') or 'N/D'})"
            )
        row[field] = value
        estimated_fields.append(field)
        source_notes.append(f"{field}: {source}")

    profit_margin = safe_float(market.get("profit_margins"))
    operating_margin = safe_float(market.get("operating_margins"))
    roe = _percent_points(market.get("return_on_equity"))
    roa = _percent_points(market.get("return_on_assets"))
    roic_proxy = _estimate_roic_proxy(roe, roa, profit_margin, market)
    if roic_proxy is not None:
        source = "proxy ROA/ROE yfinance recalibre" if roa is not None else "proxy ROE yfinance recalibre"
        set_auto("roic_5y_avg", roic_proxy, source)

    revenue_growth = _percent_points(market.get("revenue_growth"))
    earnings_growth = _percent_points(market.get("earnings_growth"))
    earnings_quarterly_growth = _percent_points(market.get("earnings_quarterly_growth"))
    stock_cagr_5y = _percent_points(market.get("stock_cagr_5y"))
    stock_cagr_3y = _percent_points(market.get("stock_cagr_3y"))
    forward_eps_context = (
        _empty_forward_eps_growth_context(market)
        if _is_etf_or_fund_market(market)
        else compute_forward_eps_growth(
            market.get("forward_eps"),
            market.get("trailing_eps"),
            market.get("number_of_analyst_opinions"),
        )
    )

    if profit_margin is not None:
        if profit_margin < 0:
            set_auto("net_margin_stable_or_expanding", False, "marge nette negative")
        elif _is_low_margin_defensive_compounder(market, profit_margin, revenue_growth, earnings_growth, stock_cagr_5y):
            set_auto("net_margin_stable_or_expanding", True, "marge faible mais structurellement stable pour le modele d'affaires")
        elif profit_margin >= 0.05 and _any_positive([revenue_growth, earnings_growth, stock_cagr_5y]):
            set_auto("net_margin_stable_or_expanding", True, "marge positive + croissance/proxy positive")

    eps_hist_proxy = _estimate_historical_eps_growth_proxy(market, revenue_growth, earnings_growth, stock_cagr_5y)
    eps_growth_5y_proxy_sanity = _eps_growth_5y_proxy_sanity(market, eps_hist_proxy, market.get("trailing_eps"), profit_margin)
    if eps_hist_proxy is not None:
        set_auto("eps_growth_5y", eps_hist_proxy, "proxy croissance benefices 5 ans conservateur")

    eps_est_proxy = _estimate_future_eps_growth_proxy(market, revenue_growth, earnings_growth, stock_cagr_5y, stock_cagr_3y)
    eps_est_value, data_source_forward = _blend_forward_eps_growth_estimate(
        market,
        eps_est_proxy,
        forward_eps_context,
        revenue_growth,
        earnings_growth,
        stock_cagr_5y,
    )
    if eps_est_value is not None:
        source = "proxy croissance future recalibre: revenus comme ancre, EPS recent plafonne"
        if data_source_forward == "yfinance_forward_eps":
            source = "croissance future ancree par forward EPS yfinance, melangee au proxy long terme"
        elif data_source_forward == "yfinance_forward_eps_low_confidence":
            source = "forward EPS yfinance faible couverture, poids reduit et melange au proxy long terme"
        set_auto(
            "eps_growth_estimated_3_5y",
            eps_est_value,
            source,
        )

    benchmark_growth = _percent_points(
        first_present(
            benchmark.get("benchmark_usable_cagr"),
            benchmark.get("benchmark_10y_cagr"),
            benchmark.get("benchmark_5y_cagr"),
            benchmark.get("benchmark_3y_cagr"),
            benchmark.get("benchmark_1y_return"),
        )
    )
    if benchmark_growth is not None:
        relevance = str(benchmark.get("benchmark_relevance_level") or "HIGH").upper()
        if relevance == "LOW":
            set_auto(
                "sector_cagr_estimated",
                5.0,
                "proxy ETF faible pertinence; neutralisé pour éviter une fausse conclusion sectorielle",
            )
        elif relevance == "MEDIUM":
            set_auto("sector_cagr_estimated", benchmark_growth, "proxy ETF de comparaison partiellement pertinent")
        else:
            set_auto("sector_cagr_estimated", benchmark_growth, "proxy ETF de comparaison pertinent")

    market_cap = safe_float(market.get("market_cap"))
    moat_estimate = _estimate_moat(market_cap, profit_margin, operating_margin, stock_cagr_5y, revenue_growth, earnings_growth)
    if moat_estimate is not None:
        set_auto("moat_clear", moat_estimate, "estimation moat par taille, marges et croissance")

    forward_pe = safe_float(market.get("forward_pe"))
    trailing_pe = safe_float(market.get("trailing_pe"))
    peg = safe_float(market.get("peg"))
    eps_est = safe_float(row.get("eps_growth_estimated_3_5y"))
    calibrated_peg = _estimate_peg_proxy(market, forward_pe, eps_est, peg)
    if calibrated_peg is not None:
        source = "PEG yfinance" if peg == calibrated_peg else "PEG yfinance recalibre par croissance estimee"
        set_auto("peg_manual", calibrated_peg, source)
    current_price = safe_float(market.get("current_price"))
    acceptable_pe = _acceptable_forward_pe(eps_est)
    if forward_pe is not None and eps_est is not None:
        set_auto("forward_pe_growth_acceptable", forward_pe <= acceptable_pe, "forward PE compare a la croissance estimee")

    valuation_pe = first_present(forward_pe, trailing_pe)
    valuation_pe_source = "forward PE" if forward_pe is not None else "trailing PE gratuit"
    if current_price is not None and valuation_pe is not None and valuation_pe > 0:
        fair_value = _estimate_fair_value_proxy(current_price, valuation_pe, eps_est, calibrated_peg, market)
        set_auto("fair_value", round(fair_value, 2), f"juste valeur heuristique recalibree par {valuation_pe_source}")
        set_auto(
            "valuation_vs_5y_avg_ok",
            _valuation_ok(valuation_pe, calibrated_peg, current_price, fair_value, acceptable_pe),
            f"proxy valorisation par {valuation_pe_source}, PEG et juste valeur estimee",
        )

    margin_pressure = _estimate_margin_pressure(
        profit_margin,
        operating_margin,
        revenue_growth,
        earnings_growth,
        earnings_quarterly_growth,
    )
    if margin_pressure is not None:
        set_auto("margin_or_profitability_under_pressure", margin_pressure, "pression estimee par marges/croissance")
    early_deterioration_signal = bool(
        earnings_quarterly_growth is not None
        and earnings_quarterly_growth < 0
        and earnings_growth is not None
        and earnings_growth > 0
    )

    management_quality = _estimate_management_quality(market_cap, profit_margin, operating_margin, moat_estimate, stock_cagr_5y)
    if management_quality is not None:
        set_auto("management_quality_good", management_quality, "proxy qualite management par execution financiere")

    balance_sheet = _estimate_balance_sheet(market)
    if balance_sheet is not None:
        set_auto("balance_sheet_strong", balance_sheet, "proxy bilan par dette/cash")

    for field in CATASTROPHIC_COLUMNS:
        row[field] = False

    row["manual_confidence_level"] = _auto_confidence(estimated_fields, market)
    row["notes"] = "Donnees estimees automatiquement. A valider manuellement pour les decisions importantes."
    parsed = parse_manual_row(row)
    parsed["auto_estimated_fields"] = sorted(set(estimated_fields))
    parsed["auto_source_notes"] = source_notes
    parsed["proxy_corrections_applied"] = corrections_applied
    parsed["proxy_correction_fields"] = sorted({row["field"] for row in corrections_applied})
    parsed["proxy_correction_status"] = "ACTIVE" if corrections_applied else "NONE"
    parsed["forward_eps"] = safe_float(market.get("forward_eps"))
    parsed["trailing_eps"] = safe_float(market.get("trailing_eps"))
    parsed["number_of_analyst_opinions"] = int(safe_float(market.get("number_of_analyst_opinions")) or 0)
    parsed["forward_eps_growth_direct"] = forward_eps_context["forward_eps_growth_direct"]
    parsed["forward_eps_growth_confidence"] = forward_eps_context["forward_eps_growth_confidence"]
    parsed["analyst_opinion_count"] = forward_eps_context["analyst_opinion_count"]
    parsed["data_source_forward"] = data_source_forward
    parsed["eps_growth_5y_proxy_sanity"] = eps_growth_5y_proxy_sanity
    parsed["early_deterioration_signal"] = early_deterioration_signal
    parsed["auto_source_quality"] = _auto_source_quality(estimated_fields, market)
    parsed["input_data_mode"] = "AUTO_ESTIMATED"
    _attach_official_source_evidence(parsed, market)
    return parsed


def merge_automated_with_manual_overrides(
    automated: dict[str, Any],
    manual_override: dict[str, Any] | None,
) -> dict[str, Any]:
    if not manual_override:
        return dict(automated)

    merged = dict(automated)
    override_fields = []
    provided_fields = set(manual_override.get("manual_override_fields") or [])

    for field in MANUAL_COLUMNS:
        if field == "ticker":
            continue
        value = manual_override.get(field)
        should_override = field in provided_fields
        if value is not None and value != "" and should_override:
            merged[field] = value
            override_fields.append(field)

    merged["manual_override_fields"] = sorted(set(override_fields))
    merged["auto_estimated_fields"] = [
        field for field in merged.get("auto_estimated_fields", []) if field not in set(override_fields)
    ]
    _remove_proxy_corrections_for_fields(merged, override_fields)
    _remove_confirmed_fields_from_official_support(merged, override_fields)
    merged["input_data_mode"] = "AUTO_WITH_MANUAL_OVERRIDES" if override_fields else automated.get("input_data_mode", "AUTO_ESTIMATED")
    return merged


def _attach_official_source_evidence(parsed: dict[str, Any], market: dict[str, Any]) -> None:
    official_used_market_fields = _field_set(market.get("official_fundamental_fields"))
    official_confirmed_market_fields = _field_set(market.get("official_confirmed_fields"))
    official_conflicts = sorted(_field_set(market.get("official_data_conflicts")))
    official_supported_manual_fields = _manual_fields_from_official_market_fields(
        official_used_market_fields | official_confirmed_market_fields
    )
    official_confirmed_manual_fields = _manual_fields_from_official_market_fields(official_confirmed_market_fields)
    auto_fields = _field_set(parsed.get("auto_estimated_fields"))
    supported_auto_fields = sorted(official_supported_manual_fields & auto_fields)
    confirmed_auto_fields = sorted(official_confirmed_manual_fields & auto_fields)

    parsed["official_data_sources"] = _sorted_values(market.get("official_data_sources"))
    parsed["official_fundamental_fields"] = sorted(official_used_market_fields)
    parsed["official_confirmed_fields"] = sorted(official_confirmed_market_fields)
    parsed["official_data_conflicts"] = official_conflicts
    parsed["official_source_policy"] = _sorted_values(market.get("official_source_policy"))
    parsed["official_supported_manual_fields"] = supported_auto_fields
    parsed["official_confirmed_manual_fields"] = confirmed_auto_fields
    parsed["official_conflict_count"] = len(official_conflicts)

    notes = list(parsed.get("auto_source_notes") or [])
    if supported_auto_fields:
        notes.append("Sources complémentaires appuient des proxys fondamentaux: " + ", ".join(supported_auto_fields))
    if official_conflicts:
        notes.append(
            "Conflits entre sources traites comme avertissements non bloquants: "
            + "; ".join(official_conflicts[:4])
        )
    parsed["auto_source_notes"] = notes


def _manual_fields_from_official_market_fields(fields: set[str]) -> set[str]:
    manual_fields: set[str] = set()
    for field in fields:
        manual_fields.update(OFFICIAL_MARKET_TO_MANUAL_FIELDS.get(field, []))
    return manual_fields


def _remove_confirmed_fields_from_official_support(payload: dict[str, Any], confirmed_fields: list[str]) -> None:
    removed = set(confirmed_fields)
    if not removed:
        return
    for key in ("official_supported_manual_fields", "official_confirmed_manual_fields"):
        payload[key] = [field for field in payload.get(key, []) if field not in removed]


def _remove_proxy_corrections_for_fields(payload: dict[str, Any], confirmed_fields: list[str]) -> None:
    removed = set(confirmed_fields)
    if not removed:
        return
    corrections = [
        row for row in payload.get("proxy_corrections_applied", []) if str(row.get("field") or "") not in removed
    ]
    payload["proxy_corrections_applied"] = corrections
    payload["proxy_correction_fields"] = sorted({row.get("field") for row in corrections if row.get("field")})
    payload["proxy_correction_status"] = "ACTIVE" if corrections else "NONE"


def _field_set(value: Any) -> set[str]:
    if not value:
        return set()
    if isinstance(value, str):
        return {part.strip() for part in value.replace(";", ",").split(",") if part.strip()}
    return {str(part).strip() for part in value if str(part).strip()}


def _sorted_values(value: Any) -> list[str]:
    return sorted(_field_set(value))


def _percent_points(value: Any) -> float | None:
    number = safe_float(value)
    if number is None:
        return None
    if -5 <= number <= 5:
        return number * 100
    return number


def _bounded(value: float, lower: float, upper: float) -> float:
    return max(lower, min(upper, value))


def _any_positive(values: list[float | None]) -> bool:
    return any(value is not None and value > 0 for value in values)


def compute_forward_eps_growth(
    forward_eps: Any,
    trailing_eps: Any,
    number_of_analyst_opinions: Any,
) -> dict[str, Any]:
    """Compute direct next-year EPS growth from yfinance analyst EPS fields."""

    analyst_count = int(safe_float(number_of_analyst_opinions) or 0)
    forward = safe_float(forward_eps)
    trailing = safe_float(trailing_eps)
    direct = None
    if analyst_count >= FORWARD_EPS_MIN_ANALYSTS and forward is not None and trailing not in {None, 0}:
        direct = (forward - trailing) / abs(trailing)
        if direct < FORWARD_EPS_MIN_GROWTH or direct > FORWARD_EPS_MAX_GROWTH:
            direct = None

    if direct is None:
        confidence = "NONE"
    elif analyst_count >= FORWARD_EPS_HIGH_CONFIDENCE_ANALYSTS:
        confidence = "HIGH"
    elif analyst_count >= FORWARD_EPS_MEDIUM_CONFIDENCE_ANALYSTS:
        confidence = "MEDIUM"
    else:
        confidence = "LOW"
    return {
        "forward_eps_growth_direct": direct,
        "forward_eps_growth_confidence": confidence,
        "analyst_opinion_count": analyst_count,
    }


def _empty_forward_eps_growth_context(market: dict[str, Any]) -> dict[str, Any]:
    return {
        "forward_eps_growth_direct": None,
        "forward_eps_growth_confidence": "NONE",
        "analyst_opinion_count": int(safe_float(market.get("number_of_analyst_opinions")) or 0),
    }


def _blend_forward_eps_growth_estimate(
    market: dict[str, Any],
    existing_proxy_estimate: float | None,
    forward_eps_context: dict[str, Any],
    revenue_growth: float | None,
    earnings_growth: float | None,
    stock_cagr_5y: float | None,
) -> tuple[float | None, str]:
    confidence = str(forward_eps_context.get("forward_eps_growth_confidence") or "NONE").upper()
    direct_raw = safe_float(forward_eps_context.get("forward_eps_growth_direct"))
    direct_growth = direct_raw * 100 if direct_raw is not None else None
    if confidence == "NONE" or direct_growth is None:
        return existing_proxy_estimate, "proxy"

    if existing_proxy_estimate is None:
        blended = direct_growth
    elif confidence in {"HIGH", "MEDIUM"}:
        blended = (FORWARD_EPS_HIGH_MEDIUM_WEIGHT * direct_growth) + (
            FORWARD_EPS_HIGH_MEDIUM_PROXY_WEIGHT * existing_proxy_estimate
        )
    else:
        blended = (FORWARD_EPS_LOW_CONFIDENCE_WEIGHT * direct_growth) + (
            FORWARD_EPS_LOW_CONFIDENCE_PROXY_WEIGHT * existing_proxy_estimate
        )

    cap = _future_growth_cap(market, revenue_growth, earnings_growth, stock_cagr_5y)
    source = "yfinance_forward_eps" if confidence in {"HIGH", "MEDIUM"} else "yfinance_forward_eps_low_confidence"
    return round(_bounded(blended, -20.0, cap), 3), source


def _eps_growth_5y_proxy_sanity(
    market: dict[str, Any],
    eps_hist_proxy: float | None,
    trailing_eps: Any,
    profit_margin: float | None,
) -> str:
    if eps_hist_proxy is None:
        return "UNVERIFIED"
    trailing = safe_float(trailing_eps)
    if trailing is None or trailing == 0:
        return "UNVERIFIED"
    if trailing < 0 and profit_margin is not None and profit_margin > 0:
        return "UNVERIFIED"

    current_price = safe_float(market.get("current_price"))
    trailing_pe = safe_float(market.get("trailing_pe"))
    if current_price is None or trailing_pe is None or current_price <= 0 or trailing_pe <= 0:
        return "UNVERIFIED"

    implied_eps = current_price / trailing_pe
    divergence = abs(implied_eps - trailing) / max(abs(trailing), 1e-9)
    return "REVIEW" if divergence > EPS_SANITY_REVIEW_DIVERGENCE else "OK"


def _is_etf_or_fund_market(market: dict[str, Any]) -> bool:
    quote_type = str(market.get("quote_type") or "").upper()
    type_display = str(market.get("quote_type_display") or "").upper()
    return any(
        [
            quote_type in {"ETF", "FUND", "MUTUALFUND"},
            "ETF" in type_display,
            "FUND" in type_display,
            bool(market.get("fund_family")),
            bool(market.get("fund_category")),
        ]
    )


def _estimate_roic_proxy(
    roe_percent: float | None,
    roa_percent: float | None,
    profit_margin: float | None,
    market: dict[str, Any] | None = None,
) -> float | None:
    """Estimate ROIC conservatively from free ROA/ROE data.

    Calibration on user-provided examples showed raw ROE often overstated ROIC,
    especially when ROE is inflated by leverage or buybacks. ROA is used as the
    main anchor when available, with sector-neutral profitability adjustments.
    """

    if roa_percent is not None:
        sector = str((market or {}).get("sector_name") or "").lower()
        industry = str((market or {}).get("industry") or "").lower()
        if ("healthcare" in sector or "drug" in industry or "pharma" in industry) and roa_percent >= 15:
            multiplier = 1.50
        elif roa_percent >= 30:
            multiplier = 1.50
        elif profit_margin is not None and profit_margin < 0.05:
            multiplier = 2.20
        elif profit_margin is not None and profit_margin < 0.25:
            multiplier = 1.65
        else:
            multiplier = 2.00
        return round(_bounded(roa_percent * multiplier, -30, 80), 3)

    if roe_percent is None:
        return None
    if roe_percent <= 40:
        multiplier = 0.75
    elif roe_percent <= 80:
        multiplier = 0.60
    else:
        multiplier = 0.45
    return round(_bounded(roe_percent * multiplier, -30, 70), 3)


def _estimate_future_eps_growth_proxy(
    market: dict[str, Any],
    revenue_growth: float | None,
    earnings_growth: float | None,
    stock_cagr_5y: float | None,
    stock_cagr_3y: float | None,
) -> float | None:
    """Estimate future EPS growth qualitatively and conservatively.

    Recent EPS growth and share-price CAGR are noisy. User calibration showed
    they were too often treated as forward growth. Revenue growth is now the
    anchor, with recent EPS capped and sector-aware ceilings.
    """

    if revenue_growth is not None:
        if earnings_growth is not None and earnings_growth > 0:
            capped_earnings = min(earnings_growth, max(revenue_growth * 1.5, revenue_growth + 3.0))
            proxy = (0.85 * revenue_growth) + (0.15 * capped_earnings)
        else:
            proxy = revenue_growth * 0.75
    elif earnings_growth is not None:
        proxy = earnings_growth * 0.50
    else:
        cagr_proxy = first_present(stock_cagr_5y, stock_cagr_3y)
        if cagr_proxy is None:
            return None
        proxy = cagr_proxy * 0.50

    if _has_industrial_margin_expansion_signal(market, revenue_growth, earnings_growth, stock_cagr_5y):
        proxy = max(proxy, min((stock_cagr_5y or 0.0) * 0.85, 14.0))

    cap = _future_growth_cap(market, revenue_growth, earnings_growth, stock_cagr_5y)
    return round(_bounded(proxy, -20.0, cap), 3)


def _estimate_historical_eps_growth_proxy(
    market: dict[str, Any],
    revenue_growth: float | None,
    earnings_growth: float | None,
    stock_cagr_5y: float | None,
) -> float | None:
    """Estimate historical EPS growth without treating one-year EPS spikes as five-year EPS growth."""

    if stock_cagr_5y is not None:
        proxy = stock_cagr_5y * 0.75
        if earnings_growth is not None:
            if earnings_growth < 0:
                proxy = min(proxy, max(earnings_growth * 0.50, -20.0))
            else:
                capped_earnings = min(earnings_growth, max(proxy * 1.35, proxy + 5.0))
                proxy = (0.80 * proxy) + (0.20 * capped_earnings)
    elif revenue_growth is not None and earnings_growth is not None:
        if earnings_growth >= 0:
            capped_earnings = min(earnings_growth, max(revenue_growth * 1.5, revenue_growth + 5.0))
            proxy = (0.55 * revenue_growth) + (0.45 * capped_earnings)
        else:
            proxy = earnings_growth * 0.50
    elif earnings_growth is not None:
        proxy = earnings_growth * 0.35
    elif revenue_growth is not None:
        proxy = revenue_growth * 0.65
    else:
        return None

    cap = _historical_growth_cap(market, revenue_growth, earnings_growth, stock_cagr_5y)
    return round(_bounded(proxy, -30.0, cap), 3)


def _historical_growth_cap(
    market: dict[str, Any],
    revenue_growth: float | None,
    earnings_growth: float | None,
    stock_cagr_5y: float | None,
) -> float:
    sector = str(market.get("sector_name") or "").lower()
    industry = str(market.get("industry") or "").lower()

    if "semiconductor" in industry:
        return 65.0
    if "technology" in sector:
        return 55.0
    if "healthcare" in sector or "drug" in industry or "pharma" in industry:
        return 35.0
    if "financial" in sector or "asset management" in industry:
        return 30.0
    if "consumer defensive" in sector:
        return 35.0
    return 40.0


def _future_growth_cap(
    market: dict[str, Any],
    revenue_growth: float | None,
    earnings_growth: float | None,
    stock_cagr_5y: float | None,
) -> float:
    sector = str(market.get("sector_name") or "").lower()
    industry = str(market.get("industry") or "").lower()
    peg = safe_float(market.get("peg"))

    if "asset management" in industry and earnings_growth is not None and earnings_growth < 0:
        return 16.0
    if revenue_growth is not None and revenue_growth < 5:
        return 12.0
    if "consumer defensive" in sector or "utility" in sector or "utilities" in sector:
        return 14.0
    if "industrial" in sector:
        return 16.0
    if "financial" in sector:
        return 20.0
    if "communication" in sector:
        return 20.0
    if "semiconductor" in industry:
        if revenue_growth is not None and revenue_growth >= 25 and peg is not None and peg <= 1.2:
            return 42.0
        return 35.0
    if "technology" in sector:
        return 24.0
    return 22.0


def _estimate_moat(
    market_cap: float | None,
    profit_margin: float | None,
    operating_margin: float | None,
    stock_cagr_5y: float | None,
    revenue_growth: float | None,
    earnings_growth: float | None,
) -> bool | None:
    quality_signals = 0
    if market_cap is not None and market_cap >= 50_000_000_000:
        quality_signals += 1
    if profit_margin is not None and profit_margin >= 0.10:
        quality_signals += 1
    if operating_margin is not None and operating_margin >= 0.12:
        quality_signals += 1
    if _any_positive([stock_cagr_5y, revenue_growth, earnings_growth]):
        quality_signals += 1
    if quality_signals >= 3:
        return True
    if _is_low_margin_scale_moat(market_cap, profit_margin, operating_margin, stock_cagr_5y, revenue_growth):
        return True
    if profit_margin is not None and profit_margin < 0 and market_cap is not None and market_cap < 10_000_000_000:
        return False
    return None


def _estimate_peg_proxy(
    market: dict[str, Any],
    forward_pe: float | None,
    eps_est_percent: float | None,
    market_peg: float | None,
) -> float | None:
    """Use Yahoo PEG when plausible, but neutralize obvious PEG anomalies.

    User calibration showed Yahoo PEG is often useful, but can become absurd
    for some Canadian/industrial names. When the PEG conflicts strongly with a
    reasonable forward PE and growth estimate, derive a conservative PEG from
    forward PE / estimated EPS growth.
    """

    derived = None
    if forward_pe is not None and forward_pe > 0 and eps_est_percent is not None and eps_est_percent > 0:
        normalized_growth = eps_est_percent
        industry = str(market.get("industry") or "").lower()
        earnings_growth = _percent_points(market.get("earnings_growth"))
        if "asset management" in industry and earnings_growth is not None and earnings_growth < 0:
            normalized_growth *= 0.80
        derived = _bounded(forward_pe / normalized_growth, 0.2, 6.0)

    if market_peg is None or market_peg <= 0:
        return round(derived, 3) if derived is not None else None
    if derived is None:
        return round(_bounded(market_peg, 0.2, 8.0), 3)

    industry = str(market.get("industry") or "").lower()
    earnings_growth = _percent_points(market.get("earnings_growth"))
    if "asset management" in industry and earnings_growth is not None and earnings_growth < 0:
        return round(_bounded(max(market_peg, derived), 0.2, 8.0), 3)
    if market_peg > 8.0 and forward_pe is not None and forward_pe <= 35:
        return round(derived, 3)
    if market_peg < 0.50 and derived >= 0.80:
        return round(derived, 3)
    if market_peg > 4.0 and derived <= 3.0:
        return round(derived, 3)
    return round(_bounded(market_peg, 0.2, 8.0), 3)


def _acceptable_forward_pe(eps_est_percent: float | None) -> float:
    if eps_est_percent is None:
        return 35.0
    if eps_est_percent <= 0:
        return 18.0
    return _bounded(eps_est_percent * 2.2, 18.0, 45.0)


def _estimate_fair_value_proxy(
    current_price: float,
    valuation_pe: float,
    eps_est_percent: float | None,
    peg: float | None,
    market: dict[str, Any],
) -> float:
    target_pe = _fair_value_target_pe(eps_est_percent, peg, market)
    raw_fair_value = current_price * (target_pe / valuation_pe)
    upside_cap = current_price * 1.35
    downside_floor = current_price * 0.55
    return _bounded(raw_fair_value, downside_floor, upside_cap)


def _fair_value_target_pe(
    eps_est_percent: float | None,
    peg: float | None,
    market: dict[str, Any],
) -> float:
    sector = str(market.get("sector_name") or "").lower()
    industry = str(market.get("industry") or "").lower()
    market_cap = safe_float(market.get("market_cap"))
    profit_margin = safe_float(market.get("profit_margins"))

    if eps_est_percent is None:
        target = 22.0
    else:
        target = _bounded(eps_est_percent * 1.40, 14.0, 32.0)

    if market_cap is not None and market_cap >= 100_000_000_000 and profit_margin is not None and profit_margin >= 0.20:
        target = min(target + 4.0, 35.0)
    if _is_quality_industrial_compounder(market):
        target = max(target, 23.0)
    if "semiconductor" in industry:
        target = min(target, 28.0)
    if "healthcare" in sector or "drug" in industry or "pharma" in industry:
        target = min(target, 24.0)
    if "consumer defensive" in sector:
        target = max(target, 30.0)
    if peg is not None and peg > 3:
        target = min(target, 30.0)
    return target


def _valuation_ok(
    forward_pe: float | None,
    peg: float | None,
    current_price: float | None,
    fair_value: float | None,
    acceptable_pe: float,
) -> bool:
    if forward_pe is None:
        return False
    if peg is not None and peg > 3:
        return False
    ratio = current_price / fair_value if current_price and fair_value and fair_value > 0 else None
    if ratio is not None and ratio > 1.40:
        return False
    return forward_pe <= acceptable_pe * 1.30


def _estimate_margin_pressure(
    profit_margin: float | None,
    operating_margin: float | None,
    revenue_growth: float | None,
    earnings_growth: float | None,
    earnings_quarterly_growth: float | None = None,
) -> bool | None:
    if profit_margin is not None and profit_margin < 0:
        return True
    if (
        earnings_quarterly_growth is not None
        and earnings_quarterly_growth < 0
        and earnings_growth is not None
        and earnings_growth < 0
    ):
        return True
    if earnings_growth is not None and earnings_growth <= -20:
        if revenue_growth is not None and revenue_growth > 5 and profit_margin is not None and profit_margin >= 0.03:
            return False
        return True
    if revenue_growth is not None and revenue_growth <= -10:
        return True
    if (
        profit_margin is not None
        and profit_margin > 0
        and not _any_negative([revenue_growth, earnings_growth], threshold=-20)
        and (operating_margin is None or operating_margin > 0)
    ):
        return False
    return None


def _any_negative(values: list[float | None], threshold: float) -> bool:
    return any(value is not None and value <= threshold for value in values)


def _estimate_management_quality(
    market_cap: float | None,
    profit_margin: float | None,
    operating_margin: float | None,
    moat_estimate: bool | None,
    stock_cagr_5y: float | None,
) -> bool | None:
    if moat_estimate is True and profit_margin is not None and profit_margin > 0 and market_cap is not None and market_cap >= 25_000_000_000:
        return True
    if operating_margin is not None and operating_margin < 0 and stock_cagr_5y is not None and stock_cagr_5y < 0:
        return False
    return None


def _estimate_balance_sheet(market: dict[str, Any]) -> bool | None:
    debt_to_equity = safe_float(market.get("debt_to_equity"))
    total_debt = safe_float(market.get("total_debt"))
    total_cash = safe_float(market.get("total_cash"))
    market_cap = safe_float(market.get("market_cap"))
    profit_margin = safe_float(market.get("profit_margins"))
    operating_margin = safe_float(market.get("operating_margins"))
    if debt_to_equity is not None:
        if debt_to_equity <= 100:
            return True
        if debt_to_equity >= 250:
            if (
                market_cap is not None
                and market_cap > 0
                and total_debt is not None
                and total_debt / market_cap <= 0.08
                and profit_margin is not None
                and profit_margin >= 0.20
                and operating_margin is not None
                and operating_margin >= 0.30
            ):
                return True
            return False
    if (
        debt_to_equity is not None
        and debt_to_equity <= 160
        and market_cap is not None
        and market_cap > 0
        and total_debt is not None
        and total_debt / market_cap <= 0.10
        and profit_margin is not None
        and profit_margin >= 0.20
        and operating_margin is not None
        and operating_margin >= 0.25
    ):
        return True
    if total_cash is not None and total_debt is not None:
        return total_cash >= total_debt * 0.50
    return None


def _is_low_margin_defensive_compounder(
    market: dict[str, Any],
    profit_margin: float,
    revenue_growth: float | None,
    earnings_growth: float | None,
    stock_cagr_5y: float | None,
) -> bool:
    sector = str(market.get("sector_name") or "").lower()
    industry = str(market.get("industry") or "").lower()
    market_cap = safe_float(market.get("market_cap"))
    return (
        profit_margin >= 0.02
        and market_cap is not None
        and market_cap >= 50_000_000_000
        and ("consumer defensive" in sector or "discount" in industry or "retail" in industry)
        and _any_positive([revenue_growth, earnings_growth, stock_cagr_5y])
    )


def _is_low_margin_scale_moat(
    market_cap: float | None,
    profit_margin: float | None,
    operating_margin: float | None,
    stock_cagr_5y: float | None,
    revenue_growth: float | None,
) -> bool:
    if market_cap is None or profit_margin is None:
        return False
    if market_cap >= 100_000_000_000 and profit_margin >= 0.02 and _any_positive([stock_cagr_5y, revenue_growth]):
        return True
    if (
        market_cap >= 20_000_000_000
        and profit_margin >= 0.04
        and operating_margin is not None
        and operating_margin >= 0.08
        and (stock_cagr_5y is not None and stock_cagr_5y >= 8)
    ):
        return True
    return False


def _has_industrial_margin_expansion_signal(
    market: dict[str, Any],
    revenue_growth: float | None,
    earnings_growth: float | None,
    stock_cagr_5y: float | None,
) -> bool:
    sector = str(market.get("sector_name") or "").lower()
    industry = str(market.get("industry") or "").lower()
    profit_margin = safe_float(market.get("profit_margins"))
    return (
        ("industrial" in sector or "engineering" in industry or "construction" in industry)
        and revenue_growth is not None
        and revenue_growth > 0
        and earnings_growth is not None
        and earnings_growth >= 20
        and stock_cagr_5y is not None
        and stock_cagr_5y >= 8
        and profit_margin is not None
        and profit_margin > 0
    )


def _is_quality_industrial_compounder(market: dict[str, Any]) -> bool:
    sector = str(market.get("sector_name") or "").lower()
    industry = str(market.get("industry") or "").lower()
    market_cap = safe_float(market.get("market_cap"))
    operating_margin = safe_float(market.get("operating_margins"))
    debt_to_equity = safe_float(market.get("debt_to_equity"))
    stock_cagr_5y = safe_float(market.get("stock_cagr_5y"))
    return (
        ("industrial" in sector or "engineering" in industry or "construction" in industry)
        and market_cap is not None
        and market_cap >= 20_000_000_000
        and operating_margin is not None
        and operating_margin >= 0.08
        and (debt_to_equity is None or debt_to_equity <= 120)
        and stock_cagr_5y is not None
        and stock_cagr_5y >= 0.08
    )


def _auto_confidence(estimated_fields: list[str], market: dict[str, Any]) -> str:
    quality = _auto_source_quality(estimated_fields, market)
    if quality == "HIGH":
        return "HIGH"
    if quality == "MEDIUM":
        return "MEDIUM"
    return "LOW"


def _auto_source_quality(estimated_fields: list[str], market: dict[str, Any]) -> str:
    field_count = len(set(estimated_fields) & CORE_AUTO_FIELDS)
    market_confirmations = sum(
        1
        for field in [
            "current_price",
            "forward_pe",
            "forward_eps",
            "trailing_eps",
            "number_of_analyst_opinions",
            "peg",
            "profit_margins",
            "stock_cagr_5y",
            "sma_200",
        ]
        if market.get(field) is not None and (field != "number_of_analyst_opinions" or (safe_float(market.get(field)) or 0) > 0)
    )
    if field_count >= 8 and market_confirmations >= 5:
        return "HIGH"
    if field_count >= 5 and market_confirmations >= 3:
        return "MEDIUM"
    return "LOW"
