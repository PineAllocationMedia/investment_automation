"""Invented Inline XBRL complete submissions only; never live issuer evidence."""
from xml.sax.saxutils import escape, quoteattr

from tests.sec_original_filing_fixtures import CIK, filing

PROFILES = {
    "2019/2019": ("http://xbrl.sec.gov/dei/2019-01-31",
                  "http://fasb.org/us-gaap/2019-01-31"),
    "2019/2020": ("http://xbrl.sec.gov/dei/2019-01-31",
                  "http://fasb.org/us-gaap/2020-01-31"),
    "2020/2019": ("http://xbrl.sec.gov/dei/2020-01-31",
                  "http://fasb.org/us-gaap/2019-01-31"),
    "2020/2020": ("http://xbrl.sec.gov/dei/2020-01-31",
                  "http://fasb.org/us-gaap/2020-01-31"),
    "2021": ("http://xbrl.sec.gov/dei/2021", "http://fasb.org/us-gaap/2021-01-31"),
    "2021q4": ("http://xbrl.sec.gov/dei/2021q4", "http://fasb.org/us-gaap/2021-01-31"),
    "2022": ("http://xbrl.sec.gov/dei/2022", "http://fasb.org/us-gaap/2022"),
    "2022q4": ("http://xbrl.sec.gov/dei/2022q4", "http://fasb.org/us-gaap/2022"),
    "2023": ("http://xbrl.sec.gov/dei/2023", "http://fasb.org/us-gaap/2023"),
    "2024": ("http://xbrl.sec.gov/dei/2024", "http://fasb.org/us-gaap/2024"),
    "2025": ("http://xbrl.sec.gov/dei/2025", "http://fasb.org/us-gaap/2025"),
    "2026": ("http://xbrl.sec.gov/dei/2026", "http://fasb.org/us-gaap/2026"),
}
DEI, GAAP = PROFILES["2025"]


def context(ref="c1", *, member=None, exchange=None, cik=CIK, start="2025-01-01", end="2025-12-31"):
    dimensions = ""
    for axis, value in (("us-gaap:StatementClassOfStockAxis", member),
                        ("dei:EntityListingsExchangeAxis", exchange)):
        if value is not None:
            dimensions += f'<xbrldi:explicitMember dimension="{axis}">{escape(value)}</xbrldi:explicitMember>'
    segment = f"<xbrli:segment>{dimensions}</xbrli:segment>" if dimensions else ""
    return (f'<xbrli:context id={quoteattr(ref)}><xbrli:entity>'
            f'<xbrli:identifier scheme="http://www.sec.gov/CIK">{cik}</xbrli:identifier>{segment}'
            f'</xbrli:entity><xbrli:period><xbrli:startDate>{start}</xbrli:startDate>'
            f'<xbrli:endDate>{end}</xbrli:endDate></xbrli:period></xbrli:context>')


def fact(name, value, ref="c1", *, attrs="", markup=False):
    return (f'<ix:nonNumeric name="dei:{name}" contextRef={quoteattr(ref)}{attrs}>'
            + (value if markup else escape(value)) + '</ix:nonNumeric>')


def security(ref="c1", *, title="Class A Common Stock, $0.01 par value", symbol="FICT",
             exchange="NASDAQ", no_symbol=False):
    return (fact("Security12bTitle", title, ref)
            + (fact("NoTradingSymbolFlag", "true", ref) if no_symbol else fact("TradingSymbol", symbol, ref))
            + fact("SecurityExchangeName", exchange, ref))


def inline(*, contexts=None, facts=None, extra="", namespaces="", profile=None):
    dei, gaap = (DEI, GAAP) if profile is None else profile
    return (f'<html xmlns="http://www.w3.org/1999/xhtml" '
            f'xmlns:ix="http://www.xbrl.org/2013/inlineXBRL" xmlns:dei="{dei}" '
            f'xmlns:us-gaap="{gaap}" xmlns:fiction="https://fiction.invalid/2025" '
            'xmlns:xbrli="http://www.xbrl.org/2003/instance" '
            'xmlns:xbrldi="http://xbrl.org/2006/xbrldi" '
            'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
            f'{namespaces}><head><title>Fictional only</title></head><body>'
            '<ix:header><ix:resources>' + (context() if contexts is None else contexts)
            + '</ix:resources></ix:header>' + (security() if facts is None else facts)
            + extra + '</body></html>').encode('utf-8')


def submission(**kwargs):
    return filing(payload=inline(**kwargs))
