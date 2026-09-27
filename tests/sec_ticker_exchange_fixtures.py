"""Fictional SEC association bytes only; no real identity or listing authority."""
import json

T1 = "2026-09-26T12:00:00Z"
T2 = "2026-09-26T12:01:00Z"
FIELDS = ["cik", "name", "ticker", "exchange"]


def row(cik=1234567, name="FICTIONAL ALPHA CORP", ticker="FICT", exchange="Nasdaq"):
    return [cik, name, ticker, exchange]


def snapshot(rows=None, *, fields=None, extra=None):
    value = {"fields": FIELDS if fields is None else fields,
             "data": [row()] if rows is None else rows}
    if extra:
        value.update(extra)
    return json.dumps(value, ensure_ascii=True, separators=(",", ":")).encode("ascii")
