"""Entirely fictional source JSON; never real issuer or LIVE qualification."""
import json

CIK = "0000000123"
T1 = "2026-09-20T12:00:00Z"
T2 = "2026-09-20T12:00:02Z"
NAME = "CIK" + CIK + "-submissions-001.json"
NAME2 = "CIK" + CIK + "-submissions-12345.json"


def row(number=1, **changes):
    return {**dict(accessionNumber=f"0000000001-26-{number:06d}", filingDate="2026-02-01",
                   reportDate="2025-12-31", acceptanceDateTime="2026-02-01T15:30:00.000Z",
                   form="10-K", primaryDocument="fictional.htm", fileNumber="001-00000",
                   filmNumber="26000000", items="", size=1200, isXBRL=1, isInlineXBRL=1,
                   primaryDocDescription="Fictional filing"), **changes}


def columns(rows=None):
    rows = [row()] if rows is None else rows
    keys = sorted(rows[0] if rows else row())
    return {key: [entry[key] for entry in rows] for key in keys}


def reference(name=NAME, **changes):
    return {**dict(name=name, filingCount=1, filingFrom="2020-01-01", filingTo="2026-12-31"), **changes}


def root_value(rows=None, refs=None, **changes):
    return {**dict(cik=123, name="Fictional Issuer", tickers=["FAKE"], exchanges=["Fictional Exchange"],
                   addresses={"business": {"street1": "Fictional", "city": "Nowhere"}},
                   formerNames=[{"name": "Former Fiction", "from": "2020-01-01", "to": "2021-01-01"}],
                   filings={"recent": columns(rows), "files": [] if refs is None else refs}), **changes}


def encode(value):
    return json.dumps(value, ensure_ascii=True, allow_nan=False).encode()


def root(rows=None, refs=None, **changes):
    return encode(root_value(rows, refs, **changes))


def history(rows=None):
    return encode(columns(rows))
