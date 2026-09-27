"""Fictional offline PR4D4C2 evidence; never real identity or admission."""
from tests.nasdaq_listed_fixtures import directory, row as nasdaq_row
from tests.sec_property4_temporal_fixtures import combined_submission
from tests.sec_ticker_exchange_fixtures import row as sec_row, snapshot


SEC_CAPTURE = "2026-02-03T12:00:00Z"
NASDAQ_CAPTURE = "2026-02-04T12:00:00Z"


def registered_submission(*, symbol="FICT", exchange="NASDAQ", title="Class A Common Stock",
                          **changes):
    raw = combined_submission(symbol=symbol, **changes)
    return raw.replace(b"Fictional Exchange", exchange.encode("utf-8")).replace(
        b"Class A Common Stock", title.encode("utf-8"))


def sec_snapshot(*, cik=123, symbol="FICT", exchange="Nasdaq", name="FICTIONAL D4C2 CORP",
                 rows=None):
    return snapshot([sec_row(cik, name, symbol, exchange)] if rows is None else rows)


def nasdaq_snapshot(*, symbol="FICT", test_issue="N", security_name="Unrelated Source Name",
                    rows=None):
    values = nasdaq_row(symbol, **{"Test Issue": test_issue,
                                  "Security Name": security_name})
    return directory([values] if rows is None else rows)
