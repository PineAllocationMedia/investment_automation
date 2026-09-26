"""Fictional offline Inline XBRL class/EPS claims; never real issuer evidence."""
from xml.sax.saxutils import escape, quoteattr

from tests.sec_original_filing_fixtures import CIK, filing

PROFILES = {
    2025: ("http://xbrl.sec.gov/dei/2025", "http://fasb.org/us-gaap/2025"),
    2026: ("http://xbrl.sec.gov/dei/2026", "http://fasb.org/us-gaap/2026"),
}


def context(ref, *, kind="duration", member=None, cik=CIK,
            start="2025-01-01", end="2025-12-31"):
    dimension = ""
    if member is not None:
        dimension = (f'<xbrli:segment><xbrldi:explicitMember '
                     f'dimension="us-gaap:StatementClassOfStockAxis">'
                     f'{escape(member)}</xbrldi:explicitMember></xbrli:segment>')
    if kind == "instant":
        period = f"<xbrli:instant>{end}</xbrli:instant>"
    else:
        period = (f"<xbrli:startDate>{start}</xbrli:startDate>"
                  f"<xbrli:endDate>{end}</xbrli:endDate>")
    return (f'<xbrli:context id={quoteattr(ref)}><xbrli:entity>'
            f'<xbrli:identifier scheme="http://www.sec.gov/CIK">{cik}</xbrli:identifier>'
            f'{dimension}</xbrli:entity><xbrli:period>{period}</xbrli:period>'
            f'</xbrli:context>')


def numeric_fact(name, value, ref, *, prefix, unit="shares", fact_id=None,
                 decimals="0", precision=None, attrs=""):
    accuracy = (f' precision={quoteattr(precision)}' if precision is not None
                else f' decimals={quoteattr(decimals)}')
    identity = "" if fact_id is None else f' id={quoteattr(fact_id)}'
    return (f'<ix:nonFraction name={quoteattr(prefix + ":" + name)} '
            f'contextRef={quoteattr(ref)} unitRef={quoteattr(unit)}'
            f'{accuracy}{identity}{attrs}>{escape(value)}</ix:nonFraction>')


def common_shares(value="1000000", ref="shares", **kwargs):
    return numeric_fact("EntityCommonStockSharesOutstanding", value, ref,
                        prefix="dei", unit="u-shares", **kwargs)


def diluted_eps(value="2.50", ref="eps", **kwargs):
    return numeric_fact("EarningsPerShareDiluted", value, ref,
                        prefix="us-gaap", unit="u-usd-per-share", decimals="2", **kwargs)


def inline(*, year=2025, contexts=None, facts=None, extra="", namespaces=""):
    dei, gaap = PROFILES[year]
    default_contexts = (context("shares", kind="instant", member="fiction:ClassAMember")
                        + context("eps"))
    default_facts = common_shares(fact_id="shares-fact") + diluted_eps(fact_id="eps-fact")
    return (f'<html xmlns="http://www.w3.org/1999/xhtml" '
            f'xmlns:ix="http://www.xbrl.org/2013/inlineXBRL" xmlns:dei="{dei}" '
            f'xmlns:us-gaap="{gaap}" xmlns:fiction="https://fiction.invalid/{year}" '
            'xmlns:xbrli="http://www.xbrl.org/2003/instance" '
            'xmlns:xbrldi="http://xbrl.org/2006/xbrldi" '
            'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
            f'{namespaces}><head><title>Fictional only</title></head><body>'
            '<ix:header><ix:resources>'
            + (default_contexts if contexts is None else contexts)
            + '<xbrli:unit id="u-shares"><xbrli:measure>xbrli:shares</xbrli:measure></xbrli:unit>'
            + '<xbrli:unit id="u-usd-per-share"><xbrli:divide><xbrli:unitNumerator>'
              '<xbrli:measure>iso4217:USD</xbrli:measure></xbrli:unitNumerator>'
              '<xbrli:unitDenominator><xbrli:measure>xbrli:shares</xbrli:measure>'
              '</xbrli:unitDenominator></xbrli:divide></xbrli:unit>'
            + '</ix:resources></ix:header>'
            + (default_facts if facts is None else facts) + extra
            + '</body></html>').encode("utf-8")


def submission(**kwargs):
    return filing(payload=inline(**kwargs))
