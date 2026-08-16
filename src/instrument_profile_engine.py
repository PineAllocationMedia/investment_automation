from __future__ import annotations

import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import requests

from .asset_type_engine import etf_asset_profile, is_etf_asset_analysis
from .utils import CACHE_DIR, load_json, normalize_ticker, safe_float, save_json, today_iso


INSTRUMENT_PROFILE_COLUMNS = [
    "ticker",
    "name",
    "instrument_type",
    "business_description",
    "sector_or_category",
    "industry",
    "revenue_model_or_activity",
    "portfolio_role",
    "key_watch_items",
    "top_holdings",
    "source",
    "source_confidence",
    "last_updated",
    "missing_fields",
    "profile_status",
]

PROFILE_CACHE_SUBDIR = "instrument_profiles"
PROFILE_CACHE_TTL_DAYS = 30
EXTERNAL_TIMEOUT_SECONDS = 10

SOURCE_CONFIDENCE_RANK = {"MISSING": 0, "LOW": 1, "MEDIUM": 2, "HIGH": 3}
REQUIRED_PROFILE_FIELDS = [
    "name",
    "instrument_type",
    "business_description",
    "sector_or_category",
    "revenue_model_or_activity",
    "portfolio_role",
    "key_watch_items",
]

FALLBACK_DESCRIPTION = (
    "Profil d’activité non confirmé avec les sources disponibles. Le titre est inclus dans la recommandation selon les "
    "critères financiers du modèle, mais sa description qualitative doit être validée manuellement."
)


def build_instrument_profiles(
    allocation_rows: list[dict[str, Any]],
    analyses: dict[str, dict[str, Any]],
    *,
    cache_dir: str | Path = CACHE_DIR / PROFILE_CACHE_SUBDIR,
    refresh_external: bool = False,
) -> list[dict[str, Any]]:
    """Build reporting-only business/ETF profiles for tickers receiving a positive allocation."""
    rows: list[dict[str, Any]] = []
    cache_path = Path(cache_dir)
    cache_path.mkdir(parents=True, exist_ok=True)
    for allocation in allocation_rows or []:
        amount = safe_float(allocation.get("amount") or allocation.get("monthly_contribution") or allocation.get("montant")) or 0.0
        if amount <= 0:
            continue
        ticker = normalize_ticker(allocation.get("ticker") or allocation.get("destination"))
        if not ticker:
            continue
        analysis = analyses.get(ticker) or analyses.get(str(allocation.get("ticker") or "")) or {"ticker": ticker}
        profile = build_instrument_profile(
            ticker,
            analysis,
            allocation,
            cache_dir=cache_path,
            refresh_external=refresh_external,
        )
        rows.append(profile)
    return rows


def build_instrument_profile(
    ticker: str,
    analysis: dict[str, Any],
    allocation: dict[str, Any] | None = None,
    *,
    cache_dir: str | Path = CACHE_DIR / PROFILE_CACHE_SUBDIR,
    refresh_external: bool = False,
) -> dict[str, Any]:
    """Build one reporting-only instrument profile without affecting allocation decisions."""
    ticker = normalize_ticker(ticker)
    analysis = analysis or {}
    allocation = allocation or {}
    cache_dir = Path(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)

    profile = _internal_profile(ticker, analysis, allocation)
    cached = _load_cached_profile(cache_dir, ticker)
    if cached:
        profile = _merge_missing_fields(profile, cached, "cache local")

    external = _optional_external_profile(ticker, profile, cache_dir, refresh_external=refresh_external)
    if external:
        profile = _merge_missing_fields(profile, external, str(external.get("source") or "source externe optionnelle"))
        _write_cached_profile(cache_dir, ticker, profile)
    elif _profile_has_usable_description(profile):
        _write_cached_profile(cache_dir, ticker, profile)

    profile = _finalize_profile(profile)
    return {column: profile.get(column, "") for column in INSTRUMENT_PROFILE_COLUMNS}


def _internal_profile(ticker: str, analysis: dict[str, Any], allocation: dict[str, Any]) -> dict[str, Any]:
    instrument_type = _instrument_type(analysis)
    name = _first_text(
        analysis.get("long_name"),
        analysis.get("company_name_found"),
        analysis.get("company_name"),
        analysis.get("asset_name"),
        ticker,
    )
    sector = _first_text(
        analysis.get("research_report_sector"),
        analysis.get("sector_or_category"),
        analysis.get("sector_name"),
        analysis.get("sector"),
        analysis.get("asset_focus"),
        analysis.get("fund_category"),
    )
    industry = _first_text(
        analysis.get("research_report_industry"),
        analysis.get("industry"),
        analysis.get("quote_type_display"),
        analysis.get("quote_type"),
    )

    if instrument_type == "etf":
        etf_profile = etf_asset_profile(ticker, analysis, analysis.get("sector"))
        name = _first_text(name, etf_profile.get("asset_name"), ticker)
        sector = _first_text(etf_profile.get("asset_focus"), sector, "ETF / FNB")
        business_description = _etf_description(name, etf_profile)
        revenue_model = _etf_activity_text(etf_profile)
        portfolio_role = _etf_portfolio_role(ticker, analysis, allocation, etf_profile)
        key_watch_items = _etf_watch_items(etf_profile)
        source = "données internes + classification ETF locale"
        confidence = "MEDIUM" if business_description else "LOW"
    elif instrument_type == "stock":
        research_description = _first_text(analysis.get("research_report_company_description"))
        business_description = _first_text(research_description, analysis.get("business_summary"))
        revenue_model = _stock_revenue_model_text(analysis)
        portfolio_role = _stock_portfolio_role(analysis, allocation)
        key_watch_items = _stock_watch_items(analysis)
        source_parts = []
        if research_description:
            source_parts.append(_research_report_profile_source_text(analysis))
        elif business_description:
            source_parts.append("résumé d’activité Yahoo/yfinance")
        if analysis.get("sec_edgar_company_name") or analysis.get("official_data_sources"):
            source_parts.append("SEC/official fundamentals")
        if analysis.get("research_report_sources") and not research_description:
            source_parts.append("rapports locaux BNCD/Morningstar")
        source = ", ".join(source_parts) or "données internes partielles"
        confidence = "HIGH" if business_description and len(source_parts) >= 2 else "MEDIUM" if business_description else "LOW"
    else:
        business_description = ""
        revenue_model = ""
        portfolio_role = _stock_portfolio_role(analysis, allocation)
        key_watch_items = _stock_watch_items(analysis)
        source = "données internes insuffisantes"
        confidence = "MISSING"

    return {
        "ticker": ticker,
        "name": name,
        "instrument_type": instrument_type,
        "business_description": business_description,
        "sector_or_category": sector,
        "industry": industry,
        "revenue_model_or_activity": revenue_model,
        "portfolio_role": portfolio_role,
        "key_watch_items": key_watch_items,
        "top_holdings": _top_holdings_text(analysis.get("top_holdings") or analysis.get("fund_top_holdings")),
        "source": source,
        "source_confidence": confidence,
        "last_updated": today_iso(),
        "missing_fields": "",
        "profile_status": "",
    }


def _optional_external_profile(
    ticker: str,
    base_profile: dict[str, Any],
    cache_dir: Path,
    *,
    refresh_external: bool,
) -> dict[str, Any]:
    if not _needs_external_profile(base_profile) and not refresh_external:
        return {}
    cached_external = _load_cached_profile(cache_dir / "external", ticker)
    if cached_external and not refresh_external:
        return cached_external
    external = {}
    alpha_key = os.environ.get("ALPHA_VANTAGE_API_KEY") or os.environ.get("ALPHAVANTAGE_API_KEY")
    if alpha_key:
        if base_profile.get("instrument_type") == "etf":
            external = _fetch_alpha_vantage_etf_profile(ticker, alpha_key)
        else:
            external = _fetch_alpha_vantage_overview(ticker, alpha_key)
    openfigi_key = os.environ.get("OPENFIGI_API_KEY")
    if openfigi_key and _needs_identity_mapping(base_profile):
        figi = _fetch_openfigi_profile(ticker, openfigi_key)
        external = _merge_missing_fields(external or {}, figi, "OpenFIGI") if figi else external
    if external:
        _write_cached_profile(cache_dir / "external", ticker, external)
    return external


def _fetch_alpha_vantage_overview(ticker: str, api_key: str) -> dict[str, Any]:
    url = "https://www.alphavantage.co/query"
    try:
        response = requests.get(
            url,
            params={"function": "OVERVIEW", "symbol": ticker, "apikey": api_key},
            timeout=EXTERNAL_TIMEOUT_SECONDS,
        )
        payload = response.json() if response.ok else {}
    except Exception:
        return {}
    description = _first_text(payload.get("Description"))
    if not description:
        return {}
    return {
        "ticker": ticker,
        "name": _first_text(payload.get("Name"), ticker),
        "instrument_type": "stock",
        "business_description": description,
        "sector_or_category": _first_text(payload.get("Sector")),
        "industry": _first_text(payload.get("Industry")),
        "revenue_model_or_activity": "Activité décrite par le profil Alpha Vantage OVERVIEW; valider manuellement les détails opérationnels.",
        "source": "Alpha Vantage OVERVIEW",
        "source_confidence": "MEDIUM",
        "last_updated": today_iso(),
    }


def _fetch_alpha_vantage_etf_profile(ticker: str, api_key: str) -> dict[str, Any]:
    url = "https://www.alphavantage.co/query"
    try:
        response = requests.get(
            url,
            params={"function": "ETF_PROFILE", "symbol": ticker, "apikey": api_key},
            timeout=EXTERNAL_TIMEOUT_SECONDS,
        )
        payload = response.json() if response.ok else {}
    except Exception:
        return {}
    holdings = payload.get("holdings") if isinstance(payload.get("holdings"), list) else []
    top_holdings = [str(row.get("description") or row.get("symbol") or "").strip() for row in holdings[:8] if isinstance(row, dict)]
    if not payload and not top_holdings:
        return {}
    return {
        "ticker": ticker,
        "name": _first_text(payload.get("name"), ticker),
        "instrument_type": "etf",
        "business_description": _first_text(payload.get("description")),
        "sector_or_category": _first_text(payload.get("net_assets"), payload.get("asset_class")),
        "top_holdings": ", ".join(item for item in top_holdings if item),
        "source": "Alpha Vantage ETF_PROFILE",
        "source_confidence": "MEDIUM" if top_holdings else "LOW",
        "last_updated": today_iso(),
    }


def _fetch_openfigi_profile(ticker: str, api_key: str) -> dict[str, Any]:
    try:
        response = requests.post(
            "https://api.openfigi.com/v3/mapping",
            headers={"Content-Type": "application/json", "X-OPENFIGI-APIKEY": api_key},
            json=[{"idType": "TICKER", "idValue": ticker}],
            timeout=EXTERNAL_TIMEOUT_SECONDS,
        )
        payload = response.json() if response.ok else []
    except Exception:
        return {}
    data = payload[0].get("data", []) if isinstance(payload, list) and payload else []
    if not data:
        return {}
    item = data[0]
    return {
        "ticker": ticker,
        "name": _first_text(item.get("name"), ticker),
        "sector_or_category": _first_text(item.get("marketSector")),
        "instrument_type": "etf" if "fund" in str(item.get("securityType") or "").lower() else "",
        "source": "OpenFIGI",
        "source_confidence": "LOW",
        "last_updated": today_iso(),
    }


def _instrument_type(analysis: dict[str, Any]) -> str:
    if is_etf_asset_analysis(analysis):
        return "etf"
    quote_type = str(analysis.get("quote_type") or analysis.get("quote_type_display") or "").strip().lower()
    if quote_type in {"equity", "stock"}:
        return "stock"
    if analysis.get("business_summary") or analysis.get("sector_name") or analysis.get("industry"):
        return "stock"
    return "unknown"


def _stock_revenue_model_text(analysis: dict[str, Any]) -> str:
    summary = _first_text(analysis.get("business_summary"))
    if summary:
        return "L’activité économique est décrite par le profil d’entreprise disponible; valider les segments exacts dans le rapport annuel si la position devient importante."
    sector = _first_text(analysis.get("sector_name"), analysis.get("sector"))
    industry = _first_text(analysis.get("industry"))
    if sector or industry:
        return f"Modèle d’affaires à confirmer; classification disponible: {sector or 'secteur inconnu'}{f' / {industry}' if industry else ''}."
    return ""


def _stock_portfolio_role(analysis: dict[str, Any], allocation: dict[str, Any]) -> str:
    reason = _first_text(allocation.get("reason"))
    cagr = _first_text(analysis.get("expected_cagr_quality"))
    opportunity = _first_text(analysis.get("opportunity_cost_status"))
    thesis = _first_text(analysis.get("thesis_status"))
    parts = []
    if cagr:
        parts.append(f"CAGR qualitatif {cagr}")
    if opportunity:
        parts.append(f"comparaison VFV: {opportunity}")
    if thesis:
        parts.append(f"thèse {thesis}")
    if reason:
        parts.append(reason)
    return "; ".join(parts) if parts else "Rôle exact à confirmer; profil inclus seulement parce que le titre reçoit une allocation positive."


def _stock_watch_items(analysis: dict[str, Any]) -> str:
    items = []
    for label, key in [
        ("croissance EPS", "eps_growth_estimated_3_5y"),
        ("marges", "profit_margins"),
        ("ROIC/qualité du capital", "roic_5y_avg"),
        ("thèse", "thesis_status"),
        ("risque cycle/bulle", "cycle_bubble_risk_level"),
    ]:
        value = analysis.get(key)
        if value not in {None, ""}:
            items.append(f"{label}: {_watch_item_value(key, value)}")
    return "; ".join(items[:5]) if items else "Surveiller croissance, marges, bilan, moat et thèse fondamentale."


def _watch_item_value(key: str, value: Any) -> str:
    number = safe_float(value)
    if key == "profit_margins" and number is not None:
        return f"{number * 100:.1f} %" if abs(number) <= 1 else f"{number:.1f} %"
    if key in {"eps_growth_estimated_3_5y", "roic_5y_avg"} and number is not None:
        return f"{number:.1f}"
    return str(value)


def _etf_description(name: str, profile: dict[str, str]) -> str:
    focus = _first_text(profile.get("asset_focus"))
    if not focus:
        return ""
    return f"{name} est traité comme un ETF/FNB dont l’exposition principale est: {focus}."


def _etf_activity_text(profile: dict[str, str]) -> str:
    asset_type = _first_text(profile.get("asset_type"))
    focus = _first_text(profile.get("asset_focus"))
    return f"Le fonds vise une exposition à {focus or 'un panier de titres'} via une structure {asset_type or 'ETF/FNB'}."


def _etf_portfolio_role(ticker: str, analysis: dict[str, Any], allocation: dict[str, Any], profile: dict[str, str]) -> str:
    reason = _first_text(allocation.get("reason"))
    role = _first_text(profile.get("asset_role"))
    if reason:
        return f"{reason} Rôle ETF: {role or 'diversification ou filet de sécurité'}."
    if ticker == "VFV.TO":
        return "Filet de sécurité et benchmark S&P 500 du modèle."
    return f"Rôle ETF: {role or 'diversification ou exposition de portefeuille'}."


def _etf_watch_items(profile: dict[str, str]) -> str:
    focus = _first_text(profile.get("asset_focus"))
    return f"Surveiller frais, indice suivi, concentration, devise, tracking error et évolution de l’exposition {focus or 'du fonds'}."


def _top_holdings_text(value: Any) -> str:
    if not value:
        return ""
    if isinstance(value, list):
        items = []
        for item in value[:8]:
            if isinstance(item, dict):
                items.append(str(item.get("ticker") or item.get("symbol") or item.get("name") or item.get("description") or "").strip())
            else:
                items.append(str(item).strip())
        return ", ".join(item for item in items if item)
    return str(value)


def _load_cached_profile(cache_dir: Path, ticker: str) -> dict[str, Any]:
    path = cache_dir / f"{_safe_cache_name(ticker)}.json"
    data = load_json(path)
    if not isinstance(data, dict):
        return {}
    updated = _parse_date(data.get("last_updated"))
    if updated and datetime.now() - updated > timedelta(days=PROFILE_CACHE_TTL_DAYS):
        data["source_confidence"] = _downgrade_confidence(data.get("source_confidence"))
        data["source"] = f"{data.get('source') or 'cache local'} (cache âgé)"
    return data


def _write_cached_profile(cache_dir: Path, ticker: str, profile: dict[str, Any]) -> None:
    try:
        cache_dir.mkdir(parents=True, exist_ok=True)
        save_json(cache_dir / f"{_safe_cache_name(ticker)}.json", {**profile, "last_updated": today_iso()})
    except Exception:
        return


def _merge_missing_fields(base: dict[str, Any], addition: dict[str, Any], source_label: str) -> dict[str, Any]:
    if not addition:
        return base
    merged = dict(base)
    source_conflict = False
    for key in INSTRUMENT_PROFILE_COLUMNS:
        value = addition.get(key)
        if _is_blank(value):
            continue
        if key in {"source", "source_confidence", "last_updated", "missing_fields", "profile_status"}:
            continue
        current = merged.get(key)
        if (
            _is_blank(current)
            or current == FALLBACK_DESCRIPTION
            or _is_placeholder_name(key, current, merged.get("ticker"))
            or _is_placeholder_instrument_type(key, current)
        ):
            merged[key] = value
        elif key in {"sector_or_category", "industry", "instrument_type"} and _material_text_conflict(current, value):
            source_conflict = True
    sources = [str(item).strip() for item in [merged.get("source"), source_label] if str(item or "").strip()]
    merged["source"] = " + ".join(dict.fromkeys(sources))
    merged["source_confidence"] = _best_confidence(merged.get("source_confidence"), addition.get("source_confidence"))
    if source_conflict:
        merged["source_confidence"] = _downgrade_confidence(merged.get("source_confidence"))
        merged["source"] = f"{merged.get('source')} (écart entre sources à valider)"
    merged["last_updated"] = _first_text(merged.get("last_updated"), addition.get("last_updated"), today_iso())
    return merged


def _finalize_profile(profile: dict[str, Any]) -> dict[str, Any]:
    output = dict(profile)
    if not _first_text(output.get("business_description")):
        output["business_description"] = FALLBACK_DESCRIPTION
    missing = [field for field in REQUIRED_PROFILE_FIELDS if not _first_text(output.get(field)) or output.get(field) == FALLBACK_DESCRIPTION]
    output["missing_fields"] = ", ".join(missing)
    confidence = str(output.get("source_confidence") or "MISSING").upper()
    if not missing and confidence in {"HIGH", "MEDIUM"}:
        status = "COMPLETE"
    elif len(missing) <= 3 and confidence in {"LOW", "MEDIUM", "HIGH"}:
        status = "PARTIAL"
    else:
        status = "UNCONFIRMED"
        output["source_confidence"] = "MISSING" if confidence == "MISSING" else "LOW"
    output["profile_status"] = status
    output["last_updated"] = _first_text(output.get("last_updated"), today_iso())
    return output


def _profile_has_usable_description(profile: dict[str, Any]) -> bool:
    return bool(_first_text(profile.get("business_description"))) and profile.get("business_description") != FALLBACK_DESCRIPTION


def _needs_external_profile(profile: dict[str, Any]) -> bool:
    return str(profile.get("source_confidence") or "").upper() in {"", "LOW", "MISSING"} or not _profile_has_usable_description(profile)


def _needs_identity_mapping(profile: dict[str, Any]) -> bool:
    return not _first_text(profile.get("name")) or str(profile.get("instrument_type") or "") == "unknown"


def _research_report_profile_source_text(analysis: dict[str, Any]) -> str:
    source = _first_text(analysis.get("research_report_company_description_source"))
    report_date = _first_text(analysis.get("research_report_company_description_date"))
    rank = _first_text(analysis.get("research_report_company_description_source_rank"))
    details = []
    if source:
        details.append(source)
    if report_date:
        details.append(report_date)
    if rank:
        details.append(f"rang source {rank}")
    suffix = f" ({', '.join(details)})" if details else ""
    return f"rapports locaux BNCD/Morningstar{suffix}"


def _first_text(*values: Any) -> str:
    for value in values:
        text = str(value or "").strip()
        if text:
            return " ".join(text.split())
    return ""


def _is_blank(value: Any) -> bool:
    return value is None or value == ""


def _is_placeholder_name(key: str, value: Any, ticker: Any) -> bool:
    return key == "name" and normalize_ticker(value) == normalize_ticker(ticker)


def _is_placeholder_instrument_type(key: str, value: Any) -> bool:
    return key == "instrument_type" and str(value or "").strip().lower() in {"", "unknown"}


def _safe_cache_name(ticker: str) -> str:
    return normalize_ticker(ticker).replace("/", "_").replace(".", "_").replace("-", "_")


def _parse_date(value: Any) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        try:
            return datetime.fromisoformat(text[:10])
        except ValueError:
            return None


def _best_confidence(left: Any, right: Any) -> str:
    left_text = str(left or "MISSING").upper()
    right_text = str(right or "MISSING").upper()
    return left_text if SOURCE_CONFIDENCE_RANK.get(left_text, 0) >= SOURCE_CONFIDENCE_RANK.get(right_text, 0) else right_text


def _downgrade_confidence(value: Any) -> str:
    text = str(value or "MISSING").upper()
    if text == "HIGH":
        return "MEDIUM"
    if text == "MEDIUM":
        return "LOW"
    return text if text in SOURCE_CONFIDENCE_RANK else "LOW"


def _material_text_conflict(left: Any, right: Any) -> bool:
    left_text = _first_text(left).lower()
    right_text = _first_text(right).lower()
    if not left_text or not right_text or left_text == right_text:
        return False
    return left_text not in right_text and right_text not in left_text
