"""Fictional Yahoo Chart-shaped bytes; never real market evidence."""
import json


CAPTURED_AT = "2026-02-25T12:00:00Z"
MARKET_EPOCH = 1772017200  # 2026-02-25T11:00:00Z


def chart_response(
    *,
    symbol="FICT",
    currency="USD",
    price_text="123.4500",
    market_time=MARKET_EPOCH,
    instrument_type="EQUITY",
    exchange_name="NMS",
    full_exchange_name="NasdaqGS",
    result_count=1,
    provider_error=None,
    omit=(),
    unknown_meta=None,
):
    meta = {
        "symbol": symbol,
        "currency": currency,
        "regularMarketPrice": "__PRICE__",
        "regularMarketTime": market_time,
        "instrumentType": instrument_type,
        "exchangeName": exchange_name,
        "fullExchangeName": full_exchange_name,
        "priceHint": 4,
    }
    for key in omit:
        meta.pop(key, None)
    if unknown_meta:
        meta.update(unknown_meta)
    result = [{"meta": dict(meta), "timestamp": [], "indicators": {}}
              for _ in range(result_count)]
    payload = {"chart": {"result": result, "error": provider_error}}
    raw = json.dumps(payload, separators=(",", ":"), sort_keys=True)
    if "regularMarketPrice" in meta:
        raw = raw.replace('"__PRICE__"', price_text)
    return raw.encode("utf-8")
