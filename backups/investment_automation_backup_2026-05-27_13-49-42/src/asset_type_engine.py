from __future__ import annotations

from typing import Any

from .utils import normalize_ticker


FALLBACK_BENCHMARK_TICKER = "VFV.TO"

KNOWN_ETF_TICKERS = {
    FALLBACK_BENCHMARK_TICKER,
    "FBTC",
    "FBTC.TO",
    "FBTC-U.TO",
    "FBTC-U",
    "XUS.TO",
    "QQC.TO",
    "QQQ",
    "SPY",
    "VOO",
    "IVV",
    "VTI",
    "XIC.TO",
    "VCN.TO",
    "XEQT.TO",
    "VEQT.TO",
    "VCNS.TO",
    "VBAL.TO",
    "XCNS.TO",
    "XBAL.TO",
    "XQQ.TO",
    "ZSP.TO",
    "ZQQ.TO",
    "VAB.TO",
    "XBB.TO",
    "ZAG.TO",
    "XSB.TO",
    "VSB.TO",
    "ZFS.TO",
    "CASH.TO",
    "PSA.TO",
    "CBIL.TO",
    "ZLB.TO",
    "ZLU.TO",
    "XST.TO",
    "XMV.TO",
}

ETF_NAME_MARKERS = {
    " ETF",
    "ETF ",
    "INDEX ETF",
    "INDEX FUND",
    "EXCHANGE TRADED FUND",
    "ETF SHARES",
    "ISHARES",
    "VANGUARD",
    "SPDR",
    "INVESCO NASDAQ 100",
    "BITCOIN ETF",
    "BITCOIN FUND",
    "FIDELITY ADVANTAGE BITCOIN",
    "FIDELITY WISE ORIGIN BITCOIN",
}

ETF_QUOTE_TYPES = {"ETF", "MUTUALFUND", "FUND"}


def is_fallback_benchmark(ticker: Any) -> bool:
    return normalize_ticker(ticker) == FALLBACK_BENCHMARK_TICKER


def is_etf_asset(ticker: Any, market: dict[str, Any] | None = None, sector: Any = None) -> bool:
    ticker = normalize_ticker(ticker)
    market = market or {}
    if ticker in KNOWN_ETF_TICKERS:
        return True

    quote_type = _upper(market.get("quote_type") or market.get("quoteType"))
    quote_display = _upper(market.get("quote_type_display") or market.get("typeDisp") or market.get("quoteType"))
    if quote_type in ETF_QUOTE_TYPES or quote_display in ETF_QUOTE_TYPES:
        return True
    if "ETF" in quote_display or "FUND" in quote_display:
        return True

    name = _upper(market.get("long_name") or market.get("short_name") or market.get("company_name_found"))
    if any(marker in f" {name} " for marker in ETF_NAME_MARKERS):
        return True

    sector_text = _upper(sector or market.get("sector") or market.get("sector_name"))
    return " ETF" in f" {sector_text} " or sector_text in {"ETF", "FNB", "S&P 500 ETF"}


def is_etf_asset_analysis(analysis: dict[str, Any]) -> bool:
    if analysis.get("benchmark_role") is True:
        return True
    asset_type = _upper(analysis.get("asset_type"))
    if asset_type.startswith("ETF") or asset_type.startswith("FNB"):
        return True
    return is_etf_asset(analysis.get("ticker"), analysis, analysis.get("sector"))


def etf_asset_profile(ticker: Any, market: dict[str, Any] | None = None, sector: Any = None) -> dict[str, str]:
    ticker = normalize_ticker(ticker)
    market = market or {}
    name = str(market.get("long_name") or market.get("asset_name") or market.get("company_name_found") or "").strip()
    upper_name = _upper(name)

    if ticker == FALLBACK_BENCHMARK_TICKER:
        return {
            "asset_type": "ETF_S_AND_P_500",
            "asset_role": "BENCHMARK_FALLBACK",
            "asset_name": name or "Vanguard S&P 500 Index ETF",
            "asset_focus": "S&P 500",
            "company_name_found": "ETF S&P 500 coté au Canada",
        }
    if _is_bitcoin_etf(ticker, upper_name):
        focus = "Bitcoin"
        asset_type = "ETF_BITCOIN"
    elif ticker in {"XUS.TO", "SPY", "VOO", "IVV", "ZSP.TO"} or "S&P 500" in upper_name or "S AND P 500" in upper_name:
        focus = "S&P 500"
        asset_type = "ETF_S_AND_P_500"
    elif ticker in {"VCN.TO", "XIC.TO"} or "CANADA ALL CAP" in upper_name or "CANADIAN EQUITY" in upper_name:
        focus = "marché canadien large"
        asset_type = "ETF_CANADA_EQUITY"
    elif ticker in {"QQC.TO", "QQQ", "XQQ.TO", "ZQQ.TO"} or "NASDAQ 100" in upper_name:
        focus = "Nasdaq 100"
        asset_type = "ETF_NASDAQ_100"
    elif ticker in {"VCNS.TO", "XCNS.TO"} or "CONSERVATIVE ETF PORTFOLIO" in upper_name or "CONSERVATIVE BALANCED" in upper_name:
        focus = "portefeuille conservateur diversifié"
        asset_type = "ETF_CONSERVATIVE_ALLOCATION"
    elif ticker in {"VBAL.TO", "XBAL.TO"} or "BALANCED ETF PORTFOLIO" in upper_name:
        focus = "portefeuille équilibré diversifié"
        asset_type = "ETF_BALANCED_ALLOCATION"
    elif "TOTAL MARKET" in upper_name or ticker == "VTI":
        focus = "marché large"
        asset_type = "ETF_BROAD_MARKET"
    elif ticker in {"CASH.TO", "PSA.TO", "CBIL.TO"} or "HIGH INTEREST SAVINGS" in upper_name or "T-BILL" in upper_name:
        focus = "liquidités / bons du Trésor court terme"
        asset_type = "ETF_CASH_LIKE"
    elif ticker in {"VAB.TO", "XSB.TO", "XBB.TO", "ZAG.TO", "VSB.TO", "ZFS.TO"} or "BOND" in upper_name or "FIXED INCOME" in upper_name:
        focus = "obligations"
        asset_type = "ETF_BOND"
    elif ticker in {"ZLB.TO", "ZLU.TO", "XMV.TO"} or "LOW VOLATILITY" in upper_name or "MIN VOL" in upper_name:
        focus = "actions faible volatilité"
        asset_type = "ETF_LOW_VOLATILITY_EQUITY"
    elif ticker == "XST.TO" or "CONSUMER STAPLES" in upper_name:
        focus = "consommation de base"
        asset_type = "ETF_DEFENSIVE_SECTOR"
    elif "DIVIDEND" in upper_name:
        focus = "dividendes"
        asset_type = "ETF_DIVIDEND"
    elif "REAL ESTATE" in upper_name or "REIT" in upper_name:
        focus = "immobilier coté"
        asset_type = "ETF_REAL_ESTATE"
    elif "TECHNOLOGY" in upper_name or "TECH" in upper_name:
        focus = "technologie"
        asset_type = "ETF_TECHNOLOGY"
    else:
        focus = str(sector or market.get("sector_name") or "indice ou panier diversifié").strip() or "indice ou panier diversifié"
        asset_type = "ETF_OR_FUND"

    return {
        "asset_type": asset_type,
        "asset_role": "ETF_HOLDING_INFORMATIONAL",
        "asset_name": name or ticker,
        "asset_focus": focus,
        "company_name_found": name or f"FNB/ETF {ticker}",
    }


def etf_risk_sector(ticker: Any, market: dict[str, Any] | None = None, sector: Any = None) -> str:
    profile = etf_asset_profile(ticker, market, sector)
    asset_type = profile.get("asset_type")
    if asset_type == "ETF_S_AND_P_500":
        return "S&P 500 ETF"
    if asset_type == "ETF_NASDAQ_100":
        return "Nasdaq 100 ETF"
    if asset_type == "ETF_BROAD_MARKET":
        return "Broad Market ETF"
    if asset_type == "ETF_CANADA_EQUITY":
        return "Canadian Equity ETF"
    if asset_type == "ETF_BOND":
        return "Bond ETF"
    if asset_type == "ETF_CASH_LIKE":
        return "Cash / T-Bill ETF"
    if asset_type == "ETF_LOW_VOLATILITY_EQUITY":
        return "Low Volatility Equity ETF"
    if asset_type == "ETF_DEFENSIVE_SECTOR":
        return "Defensive Sector ETF"
    if asset_type == "ETF_CONSERVATIVE_ALLOCATION":
        return "Conservative Allocation ETF"
    if asset_type == "ETF_BALANCED_ALLOCATION":
        return "Balanced Allocation ETF"
    if asset_type == "ETF_DIVIDEND":
        return "Dividend ETF"
    if asset_type == "ETF_REAL_ESTATE":
        return "Real Estate ETF"
    if asset_type == "ETF_TECHNOLOGY":
        return "Technology ETF"
    if asset_type == "ETF_BITCOIN":
        return "Bitcoin / Crypto ETF"
    return "ETF / Fund"


def etf_risk_exposure(ticker: Any, market: dict[str, Any] | None = None, sector: Any = None) -> dict[str, Any]:
    ticker = normalize_ticker(ticker)
    market = market or {}
    profile = etf_asset_profile(ticker, market, sector)
    asset_type = profile.get("asset_type")
    currency = str(market.get("currency") or _default_etf_currency(ticker)).upper()

    if asset_type == "ETF_S_AND_P_500":
        return {"region": "United States", "currency": currency, "factor_exposure": ["broad_market", "S&P500", "large_cap"]}
    if asset_type == "ETF_NASDAQ_100":
        return {"region": "United States", "currency": currency, "factor_exposure": ["Nasdaq100", "technology", "growth", "mega_cap"]}
    if asset_type == "ETF_BROAD_MARKET":
        return {"region": "United States", "currency": currency, "factor_exposure": ["broad_market", "large_cap"]}
    if asset_type == "ETF_CANADA_EQUITY":
        return {"region": "Canada", "currency": currency, "factor_exposure": ["broad_market", "Canada", "equity"]}
    if asset_type == "ETF_BOND":
        return {"region": "Diversified", "currency": currency, "factor_exposure": ["fixed_income", "rates_sensitive"]}
    if asset_type == "ETF_CASH_LIKE":
        return {"region": "Canada", "currency": currency, "factor_exposure": ["cash_like", "short_duration", "low_volatility"]}
    if asset_type == "ETF_LOW_VOLATILITY_EQUITY":
        return {"region": "Diversified", "currency": currency, "factor_exposure": ["low_volatility", "defensive_equity"]}
    if asset_type == "ETF_DEFENSIVE_SECTOR":
        return {"region": "Canada", "currency": currency, "factor_exposure": ["consumer_staples", "defensive_equity", "sector_etf"]}
    if asset_type == "ETF_CONSERVATIVE_ALLOCATION":
        return {"region": "Diversified", "currency": currency, "factor_exposure": ["asset_allocation", "fixed_income", "defensive"]}
    if asset_type == "ETF_BALANCED_ALLOCATION":
        return {"region": "Diversified", "currency": currency, "factor_exposure": ["asset_allocation", "balanced", "broad_market"]}
    if asset_type == "ETF_DIVIDEND":
        return {"region": "Diversified", "currency": currency, "factor_exposure": ["dividend", "value", "broad_market"]}
    if asset_type == "ETF_REAL_ESTATE":
        return {"region": "Diversified", "currency": currency, "factor_exposure": ["real_estate", "rates_sensitive"]}
    if asset_type == "ETF_TECHNOLOGY":
        return {"region": "Diversified", "currency": currency, "factor_exposure": ["technology", "growth"]}
    if asset_type == "ETF_BITCOIN":
        return {
            "region": "Global",
            "currency": currency,
            "factor_exposure": ["bitcoin", "crypto", "high_volatility", "speculative_asset", "alternative_asset"],
        }
    return {
        "region": str(market.get("country") or "Diversified"),
        "currency": currency,
        "factor_exposure": ["ETF", "diversified"],
    }


def _is_bitcoin_etf(ticker: str, upper_name: str) -> bool:
    return ticker in {"FBTC", "FBTC.TO", "FBTC-U", "FBTC-U.TO"} or "BITCOIN" in upper_name


def _default_etf_currency(ticker: str) -> str:
    if ticker in {"FBTC-U", "FBTC-U.TO"}:
        return "USD"
    if ticker.endswith(".TO"):
        return "CAD"
    return "USD"


def _upper(value: Any) -> str:
    return str(value or "").strip().upper()
