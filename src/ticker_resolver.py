from __future__ import annotations

import re
import unicodedata
from pathlib import Path
from typing import Any

from .asset_type_engine import is_etf_asset_analysis
from .utils import load_yaml, normalize_ticker, safe_float


TICKER_ISSUE_COLUMNS = [
    "ticker_display",
    "input_tickers",
    "resolved_ticker",
    "intended_company_name",
    "company_name_found",
    "ticker_validation_status",
    "ticker_coverage_status",
    "free_data_coverage_class",
    "free_data_coverage_score",
    "suggested_yahoo_tickers",
    "issues",
    "suggested_action",
]

MARKET_COVERAGE_FIELDS = [
    "current_price",
    "sma_200",
    "stock_return_1y",
    "market_cap",
    "profit_margins",
    "operating_margins",
    "return_on_equity",
    "return_on_assets",
    "revenue_growth",
    "earnings_growth",
    "total_debt",
    "total_cash",
    "trailing_pe",
    "forward_pe",
    "peg",
]


def load_ticker_aliases(path: str | Path) -> dict[str, dict[str, str]]:
    raw_aliases = load_yaml(path).get("aliases", {})
    aliases: dict[str, dict[str, str]] = {}
    if not isinstance(raw_aliases, dict):
        return aliases

    for raw_input, raw_value in raw_aliases.items():
        input_ticker = normalize_ticker(raw_input)
        if not input_ticker:
            continue
        if isinstance(raw_value, str):
            resolved = normalize_ticker(raw_value)
            company_name = ""
            reason = "Alias de ticker configurable."
        elif isinstance(raw_value, dict):
            resolved = normalize_ticker(raw_value.get("ticker"))
            company_name = str(raw_value.get("company_name") or "").strip()
            reason = str(raw_value.get("reason") or "Alias de ticker configurable.").strip()
        else:
            continue
        if not resolved:
            continue
        aliases[input_ticker] = {
            "input_ticker": input_ticker,
            "resolved_ticker": resolved,
            "intended_company_name": company_name,
            "alias_reason": reason,
        }
    return aliases


def resolve_ticker(ticker: Any, aliases: dict[str, dict[str, str]]) -> str:
    input_ticker = normalize_ticker(ticker)
    return aliases.get(input_ticker, {}).get("resolved_ticker", input_ticker)


def resolve_ticker_list(
    tickers: list[str],
    aliases: dict[str, dict[str, str]],
    metadata: dict[str, dict[str, Any]] | None = None,
    source: str = "",
) -> list[str]:
    resolved: list[str] = []
    seen: set[str] = set()
    for ticker in tickers:
        input_ticker = normalize_ticker(ticker)
        if not input_ticker:
            continue
        canonical = resolve_ticker(input_ticker, aliases)
        if metadata is not None:
            register_ticker_resolution(metadata, input_ticker, canonical, aliases, source=source)
        if canonical not in seen:
            resolved.append(canonical)
            seen.add(canonical)
    return resolved


def resolve_portfolio_rows(
    rows: list[dict[str, Any]],
    aliases: dict[str, dict[str, str]],
    metadata: dict[str, dict[str, Any]],
    source: str,
) -> list[dict[str, Any]]:
    totals: dict[str, dict[str, Any]] = {}
    for row in rows:
        input_ticker = normalize_ticker(row.get("ticker"))
        if not input_ticker:
            continue
        canonical = resolve_ticker(input_ticker, aliases)
        register_ticker_resolution(metadata, input_ticker, canonical, aliases, source=source)
        row_currency = str(row.get("average_cost_currency") or row.get("acquisition_value_currency") or "CAD").upper()
        row_account_type = str(row.get("account_type") or "").strip().upper()
        bucket = totals.setdefault(
            canonical,
            {
                "current_value": 0.0,
                "shares": 0.0,
                "acquisition_value": 0.0,
                "average_cost_currency": row_currency,
                "account_type": row_account_type,
            },
        )
        if bucket.get("average_cost_currency") != row_currency:
            bucket["average_cost_currency"] = "MIXED"
        if row_account_type:
            if bucket.get("account_type") in {None, ""}:
                bucket["account_type"] = row_account_type
            elif bucket.get("account_type") != row_account_type:
                bucket["account_type"] = "MIXED"
        shares = safe_float(row.get("shares")) or 0.0
        acquisition_value = safe_float(row.get("acquisition_value")) or 0.0
        average_cost = safe_float(row.get("average_cost"))
        if acquisition_value <= 0 and shares > 0 and average_cost is not None:
            acquisition_value = shares * average_cost
        bucket["current_value"] += safe_float(row.get("current_value_cad") or row.get("current_value")) or 0.0
        bucket["shares"] += shares
        if bucket.get("average_cost_currency") != "MIXED":
            bucket["acquisition_value"] += acquisition_value
    resolved = []
    for ticker, values in sorted(totals.items()):
        shares = values["shares"]
        acquisition_value = values["acquisition_value"] if values["acquisition_value"] > 0 else None
        average_cost = acquisition_value / shares if shares > 0 and acquisition_value is not None else None
        average_cost_currency = values.get("average_cost_currency")
        if average_cost_currency == "MIXED":
            acquisition_value = None
            average_cost = None
        resolved.append(
            {
                "ticker": ticker,
                "current_value": round(values["current_value"], 2),
                "current_value_cad": round(values["current_value"], 2),
                "shares": shares,
                "average_cost": average_cost,
                "average_cost_cad": average_cost if average_cost_currency == "CAD" else None,
                "average_cost_currency": average_cost_currency if average_cost is not None else None,
                "acquisition_value": acquisition_value,
                "acquisition_value_cad": acquisition_value if average_cost_currency == "CAD" else None,
                "acquisition_value_currency": average_cost_currency if acquisition_value is not None else None,
                "account_type": values.get("account_type") or "",
            }
        )
    return resolved


def resolve_portfolio_lot_rows(
    rows: list[dict[str, Any]],
    aliases: dict[str, dict[str, str]],
    metadata: dict[str, dict[str, Any]],
    source: str,
) -> list[dict[str, Any]]:
    resolved: list[dict[str, Any]] = []
    for row in rows:
        input_ticker = normalize_ticker(row.get("ticker"))
        if not input_ticker:
            continue
        canonical = resolve_ticker(input_ticker, aliases)
        register_ticker_resolution(metadata, input_ticker, canonical, aliases, source=source)
        resolved.append({**row, "ticker": canonical})
    return resolved


def resolve_portfolio_transaction_rows(
    rows: list[dict[str, Any]],
    aliases: dict[str, dict[str, str]],
    metadata: dict[str, dict[str, Any]],
    source: str,
) -> list[dict[str, Any]]:
    resolved: list[dict[str, Any]] = []
    for row in rows:
        input_ticker = normalize_ticker(row.get("ticker"))
        if not input_ticker:
            resolved.append(dict(row))
            continue
        canonical = resolve_ticker(input_ticker, aliases)
        register_ticker_resolution(metadata, input_ticker, canonical, aliases, source=source)
        resolved.append({**row, "ticker": canonical})
    return resolved


def resolve_account_location_rows(
    rows: list[dict[str, Any]],
    aliases: dict[str, dict[str, str]],
    metadata: dict[str, dict[str, Any]],
    source: str,
) -> list[dict[str, Any]]:
    totals: dict[tuple[str, str], float] = {}
    for row in rows:
        input_ticker = normalize_ticker(row.get("ticker"))
        if not input_ticker:
            continue
        canonical = resolve_ticker(input_ticker, aliases)
        account_type = str(row.get("account_type") or "").strip().upper()
        register_ticker_resolution(metadata, input_ticker, canonical, aliases, source=source)
        key = (canonical, account_type)
        totals[key] = totals.get(key, 0.0) + (safe_float(row.get("current_value")) or 0.0)
    return [
        {"ticker": ticker, "account_type": account_type, "current_value": value}
        for (ticker, account_type), value in sorted(totals.items())
    ]


def resolve_manual_inputs(
    rows_by_ticker: dict[str, dict[str, Any]],
    aliases: dict[str, dict[str, str]],
    metadata: dict[str, dict[str, Any]],
    source: str,
) -> dict[str, dict[str, Any]]:
    resolved: dict[str, dict[str, Any]] = {}
    for ticker, row in rows_by_ticker.items():
        input_ticker = normalize_ticker(ticker)
        canonical = resolve_ticker(input_ticker, aliases)
        register_ticker_resolution(metadata, input_ticker, canonical, aliases, source=source)
        current = dict(resolved.get(canonical, {}))
        incoming = dict(row)
        incoming["ticker"] = canonical
        current.update({key: value for key, value in incoming.items() if value is not None and value != ""})
        current.setdefault("ticker", canonical)
        resolved[canonical] = current
    return resolved


def resolve_universe_mapping(
    rows_by_ticker: dict[str, dict[str, Any]],
    aliases: dict[str, dict[str, str]],
    metadata: dict[str, dict[str, Any]],
    source: str,
) -> dict[str, dict[str, Any]]:
    resolved: dict[str, dict[str, Any]] = {}
    for ticker, row in rows_by_ticker.items():
        input_ticker = normalize_ticker(ticker)
        canonical = resolve_ticker(input_ticker, aliases)
        company_name = str(row.get("company_name") or "").strip()
        register_ticker_resolution(
            metadata,
            input_ticker,
            canonical,
            aliases,
            source=source,
            intended_company_name=company_name,
        )
        current = dict(resolved.get(canonical, {}))
        incoming = dict(row)
        incoming["ticker"] = canonical
        if not incoming.get("company_name"):
            incoming["company_name"] = aliases.get(input_ticker, {}).get("intended_company_name", "")
        resolved[canonical] = _merge_metadata_row(current, incoming)
    return resolved


def load_and_resolve_universe(
    loader_fn: Any,
    aliases: dict[str, dict[str, str]],
    metadata: dict[str, dict[str, Any]],
    source: str,
) -> dict[str, dict[str, Any]]:
    """Load a ticker universe and resolve aliases in one reusable step."""
    return resolve_universe_mapping(loader_fn(), aliases, metadata, source)


def resolve_keyed_config(
    mapping: dict[str, Any],
    aliases: dict[str, dict[str, str]],
    metadata: dict[str, dict[str, Any]] | None = None,
    source: str = "",
) -> dict[str, Any]:
    resolved: dict[str, Any] = {}
    for key, value in mapping.items():
        input_ticker = normalize_ticker(key)
        if not input_ticker:
            continue
        canonical = resolve_ticker(input_ticker, aliases)
        if metadata is not None:
            register_ticker_resolution(metadata, input_ticker, canonical, aliases, source=source)
        if isinstance(value, dict) and isinstance(resolved.get(canonical), dict):
            merged = dict(resolved[canonical])
            merged.update(value)
            resolved[canonical] = merged
        else:
            resolved[canonical] = value
    return resolved


def register_ticker_resolution(
    metadata: dict[str, dict[str, Any]],
    input_ticker: str,
    resolved_ticker: str,
    aliases: dict[str, dict[str, str]],
    source: str = "",
    intended_company_name: str = "",
) -> None:
    if not resolved_ticker:
        return
    entry = metadata.setdefault(
        resolved_ticker,
        {
            "resolved_ticker": resolved_ticker,
            "input_tickers": [],
            "source_files": [],
            "alias_reasons": [],
            "intended_company_name": "",
            "ticker_alias_used": False,
        },
    )
    if input_ticker and input_ticker not in entry["input_tickers"]:
        entry["input_tickers"].append(input_ticker)
    if source and source not in entry["source_files"]:
        entry["source_files"].append(source)
    alias = aliases.get(input_ticker, {})
    if input_ticker and input_ticker != resolved_ticker:
        entry["ticker_alias_used"] = True
    if alias.get("alias_reason") and alias["alias_reason"] not in entry["alias_reasons"]:
        entry["alias_reasons"].append(alias["alias_reason"])
    intended = intended_company_name or alias.get("intended_company_name", "")
    if intended and not entry.get("intended_company_name"):
        entry["intended_company_name"] = intended


def apply_ticker_attention_flags(analysis: dict[str, Any], metadata: dict[str, Any] | None = None) -> None:
    ticker = normalize_ticker(analysis.get("ticker"))
    if analysis.get("benchmark_role") is True:
        analysis["ticker_display"] = ticker
        analysis["resolved_ticker"] = ticker
        analysis["input_tickers"] = ticker
        analysis["company_name_found"] = analysis.get("company_name_found") or analysis.get("asset_name") or "ETF S&P 500"
        analysis["ticker_needs_attention"] = False
        analysis["ticker_issue_reasons"] = []
        analysis["ticker_validation_status"] = "ETF_OR_BENCHMARK"
        analysis["ticker_coverage_status"] = "ETF_OR_BENCHMARK"
        analysis["free_data_coverage_class"] = "ETF_OR_BENCHMARK"
        analysis["free_data_coverage_score"] = 1.0
        analysis["suggested_yahoo_tickers"] = ""
        return

    if is_etf_asset_analysis(analysis):
        analysis["ticker_display"] = ticker
        analysis["resolved_ticker"] = ticker
        analysis["input_tickers"] = ticker
        analysis["company_name_found"] = analysis.get("company_name_found") or analysis.get("asset_name") or analysis.get("long_name") or f"FNB/ETF {ticker}"
        analysis["ticker_needs_attention"] = False
        analysis["ticker_issue_reasons"] = []
        analysis["ticker_validation_status"] = "ETF_OR_FUND"
        analysis["ticker_coverage_status"] = "ETF_OR_FUND"
        analysis["free_data_coverage_class"] = "ETF_OR_FUND"
        analysis["free_data_coverage_score"] = 1.0
        analysis["suggested_yahoo_tickers"] = ""
        return

    metadata = metadata or {}
    input_tickers = list(metadata.get("input_tickers") or [ticker])
    alias_reasons = list(metadata.get("alias_reasons") or [])
    intended_company = str(metadata.get("intended_company_name") or analysis.get("company_name") or "").strip()
    company_found = str(analysis.get("long_name") or "").strip()
    missing_count = int(analysis.get("score_missing_data_count") or 0)
    data_quality = str(analysis.get("data_quality") or "").upper()
    alias_used = bool(metadata.get("ticker_alias_used"))
    alias_inputs = [input_ticker for input_ticker in input_tickers if normalize_ticker(input_ticker) != ticker]
    issues: list[str] = []

    price_missing = not safe_float(analysis.get("current_price"))
    company_mismatch = bool(intended_company and company_found and not company_names_match(intended_company, company_found))
    coverage = ticker_coverage_assessment(analysis, metadata)
    validation_status = str(coverage.get("ticker_validation_status"))
    coverage_status = str(coverage.get("ticker_coverage_status"))
    coverage_class = str(coverage.get("free_data_coverage_class") or "")

    if price_missing:
        issues.append("NO_MARKET_DATA")
    if validation_status == "POSSIBLE_WRONG_TICKER":
        issues.append("POSSIBLE_WRONG_TICKER")
    if missing_count >= 4:
        issues.append("MANUAL_REQUIRED")
    if data_quality == "LOW":
        issues.append("LOW_DATA_QUALITY")
    if company_mismatch:
        issues.append("COMPANY_NAME_TO_VERIFY")
    if coverage_status == "NEEDS_BNCD_OR_MANUAL_CONFIRMATION":
        issues.append(coverage_class)
        issues.append(coverage_status)
    elif coverage_status == "LOW_FREE_DATA_COVERAGE" and (data_quality == "LOW" or missing_count >= 4):
        issues.append(coverage_class)
        issues.append(coverage_status)

    unique_issues = _unique(issues)
    analysis["input_tickers"] = ", ".join(input_tickers)
    analysis["resolved_ticker"] = ticker
    analysis["intended_company_name"] = intended_company
    analysis["company_name_found"] = company_found
    analysis["ticker_alias_used"] = alias_used
    analysis["ticker_alias_reasons"] = alias_reasons
    analysis["ticker_issue_reasons"] = unique_issues
    analysis["ticker_needs_attention"] = bool(unique_issues)
    analysis.update(coverage)
    alias_text = f" ({', '.join(alias_inputs)})" if alias_inputs else ""
    attention_text = "*" if unique_issues else ""
    analysis["ticker_display"] = f"{ticker}{alias_text}{attention_text}"
    analysis["ticker_suggested_action"] = ticker_suggested_action(analysis)


def ticker_coverage_assessment(analysis: dict[str, Any], metadata: dict[str, Any] | None = None) -> dict[str, Any]:
    metadata = metadata or {}
    ticker = normalize_ticker(analysis.get("ticker"))
    input_tickers = list(metadata.get("input_tickers") or [ticker])
    intended_company = str(metadata.get("intended_company_name") or analysis.get("company_name") or "").strip()
    company_found = str(analysis.get("long_name") or analysis.get("company_name_found") or "").strip()
    alias_used = bool(metadata.get("ticker_alias_used"))
    missing_count = int(analysis.get("score_missing_data_count") or 0)
    data_quality = str(analysis.get("data_quality") or "").upper()
    source = str(analysis.get("source") or analysis.get("market_data_source") or "").lower()
    price = safe_float(analysis.get("current_price"))
    data_fill = safe_float(analysis.get("data_fill_rate"))
    if data_fill is None:
        data_fill = _market_field_fill_rate(analysis)

    confirmed_fields = len(analysis.get("manual_override_fields") or []) + len(analysis.get("research_report_fields") or [])
    confirmation_bonus = min(0.18, confirmed_fields * 0.025)
    missing_penalty = min(0.25, missing_count * 0.04)
    coverage_score = _clamp((data_fill or 0.0) + confirmation_bonus - missing_penalty, 0.0, 1.0)
    suggested = suggested_yahoo_tickers(input_tickers, analysis, intended_company)

    if price is None or source in {"unavailable", "empty"}:
        validation_status = "NO_MARKET_DATA"
        coverage_status = "NO_MARKET_DATA"
    elif intended_company and company_found and not company_names_match(intended_company, company_found):
        validation_status = "POSSIBLE_WRONG_TICKER"
        coverage_status = "POSSIBLE_WRONG_TICKER"
    else:
        validation_status = "ALIAS_USED" if alias_used else "OK"
        if missing_count >= 4 or data_quality == "LOW":
            coverage_status = "NEEDS_BNCD_OR_MANUAL_CONFIRMATION"
        elif coverage_score < 0.55:
            coverage_status = "LOW_FREE_DATA_COVERAGE"
        elif coverage_score < 0.75 or missing_count > 0:
            coverage_status = "PARTIAL_FREE_DATA_COVERAGE"
        elif alias_used:
            coverage_status = "ALIAS_USED"
        else:
            coverage_status = "OK"

    if validation_status not in {"NO_MARKET_DATA", "POSSIBLE_WRONG_TICKER"}:
        suggested = []

    coverage_class = _free_data_coverage_class(validation_status, coverage_status)

    return {
        "ticker_validation_status": validation_status,
        "ticker_coverage_status": coverage_status,
        "free_data_coverage_class": coverage_class,
        "free_data_coverage_score": round(coverage_score, 4),
        "suggested_yahoo_tickers": ", ".join(suggested),
    }


def ticker_issue_rows_for_csv(*analysis_groups: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for group in analysis_groups:
        for analysis in sorted(group.values(), key=lambda row: (str(row.get("universe")), str(row.get("ticker")))):
            if not analysis.get("ticker_needs_attention"):
                continue
            issues = analysis.get("ticker_issue_reasons") or []
            if isinstance(issues, list):
                issues_text = "; ".join(str(issue) for issue in issues)
            else:
                issues_text = str(issues)
            rows.append(
                {
                    "ticker_display": analysis.get("ticker_display"),
                    "input_tickers": analysis.get("input_tickers"),
                    "resolved_ticker": analysis.get("resolved_ticker", analysis.get("ticker")),
                    "intended_company_name": analysis.get("intended_company_name"),
                    "company_name_found": analysis.get("company_name_found"),
                    "ticker_validation_status": analysis.get("ticker_validation_status"),
                    "ticker_coverage_status": analysis.get("ticker_coverage_status"),
                    "free_data_coverage_class": analysis.get("free_data_coverage_class"),
                    "free_data_coverage_score": analysis.get("free_data_coverage_score"),
                    "suggested_yahoo_tickers": analysis.get("suggested_yahoo_tickers"),
                    "issues": issues_text,
                    "suggested_action": analysis.get("ticker_suggested_action"),
                }
            )
    return rows


def ticker_suggested_action(analysis: dict[str, Any]) -> str:
    issues = set(analysis.get("ticker_issue_reasons") or [])
    alias_reasons = analysis.get("ticker_alias_reasons") or []
    alias_used = bool(analysis.get("ticker_alias_used"))
    suggestions = str(analysis.get("suggested_yahoo_tickers") or "").strip()
    if "NO_MARKET_DATA" in issues:
        if alias_used:
            return (
                "Alias applique, mais yfinance n'a pas donne les donnees de marche. "
                "Relancer avec --refresh-market-data; si le probleme reste, verifier le ticker Yahoo Finance exact."
            )
        extra = f" Suggestions a essayer: {suggestions}." if suggestions else ""
        return "Verifier le ticker Yahoo Finance exact, puis ajouter un alias dans config/ticker_aliases.yaml si necessaire." + extra
    if "POSSIBLE_WRONG_TICKER" in issues:
        extra = f" Suggestions a essayer: {suggestions}." if suggestions else ""
        return "Ne pas utiliser ce titre pour l'allocation avant validation: le nom trouve ne correspond peut-etre pas a la compagnie voulue." + extra
    if "COMPANY_NAME_TO_VERIFY" in issues:
        return "Verifier que le ticker trouve correspond bien a la compagnie voulue."
    if alias_used and not issues:
        return "Alias applique automatiquement: " + " ".join(str(reason) for reason in alias_reasons)
    if "VALID_TICKER_POOR_FREE_COVERAGE" in issues:
        return (
            "Le ticker semble valide, mais les donnees gratuites couvrent mal les fondamentaux. "
            "Ce n'est pas un signal negatif sur la compagnie; limiter les grosses allocations jusqu'a validation BNCD/Morningstar ou manuelle."
        )
    if "NEEDS_BNCD_OR_MANUAL_CONFIRMATION" in issues:
        return (
            "Le ticker semble valide, mais les donnees gratuites sont incomplètes. "
            "Chercher un rapport BNCD/Morningstar ou confirmer les champs clés manuellement."
        )
    if "LOW_FREE_DATA_COVERAGE" in issues:
        return "Le ticker semble valide, mais yfinance couvre mal certains fondamentaux; limiter la conclusion avant validation."
    if "MANUAL_REQUIRED" in issues or "LOW_DATA_QUALITY" in issues:
        return "Completer ou verifier les donnees dans manual_inputs_friendly.txt pour reduire l'incertitude."
    return "Aucune action requise."


def suggested_yahoo_tickers(input_tickers: list[str], analysis: dict[str, Any], intended_company: str = "") -> list[str]:
    suggestions: list[str] = []
    raw_inputs = [normalize_ticker(ticker) for ticker in input_tickers if normalize_ticker(ticker)]
    base = next((ticker for ticker in raw_inputs if "." not in ticker and "-" not in ticker), raw_inputs[0] if raw_inputs else "")
    if not base or "." in base:
        return suggestions

    text = " ".join(
        [
            intended_company,
            str(analysis.get("company_name") or ""),
            str(analysis.get("country") or ""),
            str(analysis.get("region") or ""),
            str(analysis.get("currency") or ""),
            str(analysis.get("quote_currency") or ""),
        ]
    ).lower()

    if any(token in text for token in ["canada", "canadian", "cad", "toronto", "tsx"]):
        suggestions.extend([f"{base}.TO", f"{base}.V"])
    elif any(token in text for token in ["france", "paris", "eur", "europe"]):
        suggestions.extend([f"{base}.PA", f"{base}.AS", f"{base}.DE"])
    elif any(token in text for token in ["united kingdom", "london", "gbp"]):
        suggestions.append(f"{base}.L")
    else:
        suggestions.extend([f"{base}.TO", f"{base}.V", f"{base}.PA"])

    resolved = normalize_ticker(analysis.get("ticker"))
    return _unique([suggestion for suggestion in suggestions if suggestion not in raw_inputs and suggestion != resolved])


def company_names_match(intended: str, found: str) -> bool:
    intended_tokens = _company_tokens(intended)
    found_tokens = _company_tokens(found)
    if not intended_tokens or not found_tokens:
        return True
    overlap = intended_tokens & found_tokens
    if overlap:
        return True
    compact_intended = "".join(sorted(intended_tokens))
    compact_found = "".join(sorted(found_tokens))
    return compact_intended in compact_found or compact_found in compact_intended


def _company_tokens(name: str) -> set[str]:
    stopwords = {
        "a",
        "and",
        "co",
        "com",
        "corp",
        "corporation",
        "inc",
        "incorporated",
        "ltd",
        "limited",
        "plc",
        "sa",
        "se",
        "the",
    }
    normalized_name = unicodedata.normalize("NFKD", name.lower()).encode("ascii", "ignore").decode("ascii")
    tokens = re.findall(r"[a-z0-9]+", normalized_name)
    useful_tokens = {token for token in tokens if token not in stopwords and len(token) > 1}
    return _expand_known_company_equivalents(useful_tokens)


def _expand_known_company_equivalents(tokens: set[str]) -> set[str]:
    expanded = set(tokens)
    if "tsmc" in expanded or {"taiwan", "semiconductor", "manufacturing"} <= expanded:
        expanded.update({"tsmc", "taiwan", "semiconductor", "manufacturing"})
    if {"ritchie", "bros"} <= expanded or {"rb", "global"} <= expanded:
        expanded.update({"ritchie", "bros", "rb", "global"})
    return expanded


def _merge_metadata_row(current: dict[str, Any], incoming: dict[str, Any]) -> dict[str, Any]:
    merged = dict(current)
    for key, value in incoming.items():
        if (value is not None and value != "") or key not in merged:
            merged[key] = value
    return merged


def _market_field_fill_rate(analysis: dict[str, Any]) -> float:
    filled = sum(1 for field in MARKET_COVERAGE_FIELDS if analysis.get(field) is not None)
    return filled / len(MARKET_COVERAGE_FIELDS)


def _free_data_coverage_class(validation_status: str, coverage_status: str) -> str:
    if validation_status in {"NO_MARKET_DATA", "POSSIBLE_WRONG_TICKER"}:
        return "WRONG_OR_NO_MARKET_DATA"
    if validation_status in {"ETF_OR_BENCHMARK", "ETF_OR_FUND"} or coverage_status in {"ETF_OR_BENCHMARK", "ETF_OR_FUND"}:
        return validation_status if validation_status in {"ETF_OR_BENCHMARK", "ETF_OR_FUND"} else coverage_status
    if coverage_status in {"NEEDS_BNCD_OR_MANUAL_CONFIRMATION", "LOW_FREE_DATA_COVERAGE"}:
        return "VALID_TICKER_POOR_FREE_COVERAGE"
    if coverage_status in {"PARTIAL_FREE_DATA_COVERAGE", "ALIAS_USED"}:
        return "PARTIAL_BUT_USABLE"
    return "GOOD_COVERAGE"


def _clamp(value: float, lower: float, upper: float) -> float:
    return max(lower, min(upper, value))


def _unique(values: list[str]) -> list[str]:
    result: list[str] = []
    for value in values:
        if value and value not in result:
            result.append(value)
    return result
