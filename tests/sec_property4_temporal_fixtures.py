"""Fictional D2B/D2A/D3A/D3B temporal evidence; never real authority."""
from xml.sax.saxutils import escape

from tests.sec_original_filing_fixtures import filing

CIK = "0000000123"
ACCESSION = "0000000001-26-000001"
FORM = "10-K"
FILENAME = "fictional.htm"
CAPTURE_1 = "2026-09-20T12:00:00Z"
CAPTURE_2 = "2026-09-20T12:00:02Z"

PROFILES = {
    2019: ("http://xbrl.sec.gov/dei/2019-01-31", "http://fasb.org/us-gaap/2019-01-31"),
    2025: ("http://xbrl.sec.gov/dei/2025", "http://fasb.org/us-gaap/2025"),
    2026: ("http://xbrl.sec.gov/dei/2026", "http://fasb.org/us-gaap/2026"),
}


def combined_inline(*, cik=CIK, profile=PROFILES[2025], symbol="FICT", member="fiction:ClassAMember",
                    include_registered=True, include_shares=True, include_eps=True,
                    extra_registered="", extra_class_eps=""):
    dei, gaap = profile
    registered_context = (
        '<xbrli:context id="registered"><xbrli:entity>'
        f'<xbrli:identifier scheme="http://www.sec.gov/CIK">{cik}</xbrli:identifier>'
        '<xbrli:segment>'
        '<xbrldi:explicitMember dimension="us-gaap:StatementClassOfStockAxis">'
        f'{escape(member)}</xbrldi:explicitMember>'
        '<xbrldi:explicitMember dimension="dei:EntityListingsExchangeAxis">'
        'fiction:ExchangeMember</xbrldi:explicitMember>'
        '</xbrli:segment></xbrli:entity><xbrli:period>'
        '<xbrli:startDate>2025-01-01</xbrli:startDate>'
        '<xbrli:endDate>2025-12-31</xbrli:endDate>'
        '</xbrli:period></xbrli:context>')
    shares_context = (
        '<xbrli:context id="shares"><xbrli:entity>'
        f'<xbrli:identifier scheme="http://www.sec.gov/CIK">{cik}</xbrli:identifier>'
        '<xbrli:segment>'
        '<xbrldi:explicitMember dimension="us-gaap:StatementClassOfStockAxis">'
        f'{escape(member)}</xbrldi:explicitMember>'
        '</xbrli:segment></xbrli:entity><xbrli:period>'
        '<xbrli:instant>2025-12-31</xbrli:instant>'
        '</xbrli:period></xbrli:context>')
    eps_context = (
        '<xbrli:context id="eps"><xbrli:entity>'
        f'<xbrli:identifier scheme="http://www.sec.gov/CIK">{cik}</xbrli:identifier>'
        '</xbrli:entity><xbrli:period><xbrli:startDate>2025-01-01</xbrli:startDate>'
        '<xbrli:endDate>2025-12-31</xbrli:endDate>'
        '</xbrli:period></xbrli:context>')
    units = (
        '<xbrli:unit id="u-shares"><xbrli:measure>xbrli:shares</xbrli:measure></xbrli:unit>'
        '<xbrli:unit id="u-usd-per-share"><xbrli:divide><xbrli:unitNumerator>'
        '<xbrli:measure>iso4217:USD</xbrli:measure></xbrli:unitNumerator>'
        '<xbrli:unitDenominator><xbrli:measure>xbrli:shares</xbrli:measure>'
        '</xbrli:unitDenominator></xbrli:divide></xbrli:unit>')
    registered = ""
    if include_registered:
        registered = (
            '<ix:nonNumeric name="dei:Security12bTitle" contextRef="registered">'
            'Class A Common Stock</ix:nonNumeric>'
            '<ix:nonNumeric name="dei:TradingSymbol" contextRef="registered">'
            f'{escape(symbol)}</ix:nonNumeric>'
            '<ix:nonNumeric name="dei:SecurityExchangeName" contextRef="registered">'
            'Fictional Exchange</ix:nonNumeric>')
    shares = ('' if not include_shares else
              '<ix:nonFraction name="dei:EntityCommonStockSharesOutstanding" '
              'contextRef="shares" unitRef="u-shares" decimals="0">1000000</ix:nonFraction>')
    eps = ('' if not include_eps else
           '<ix:nonFraction name="us-gaap:EarningsPerShareDiluted" '
           'contextRef="eps" unitRef="u-usd-per-share" decimals="2">2.50</ix:nonFraction>')
    return (f'<html xmlns="http://www.w3.org/1999/xhtml" '
            f'xmlns:ix="http://www.xbrl.org/2013/inlineXBRL" xmlns:dei="{dei}" '
            f'xmlns:us-gaap="{gaap}" xmlns:fiction="https://fiction.invalid/profile" '
            'xmlns:xbrli="http://www.xbrl.org/2003/instance" '
            'xmlns:xbrldi="http://xbrl.org/2006/xbrldi" '
            'xmlns:iso4217="http://www.xbrl.org/2003/iso4217">'
            '<head><title>Fictional only</title></head><body><ix:header><ix:resources>'
            + registered_context + shares_context + eps_context + units
            + '</ix:resources></ix:header>' + registered + shares + eps
            + extra_registered + extra_class_eps + '</body></html>').encode("utf-8")


def combined_submission(*, cik=CIK, accession=ACCESSION, form=FORM,
                        filename=FILENAME, **inline_changes):
    raw = filing(cik=cik, accession=accession, form=form,
                 payload=combined_inline(cik=cik, **inline_changes))
    if filename != FILENAME:
        raw = raw.replace(b"<FILENAME>fictional.htm", b"<FILENAME>" + filename.encode("ascii"))
    return raw
