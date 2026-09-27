"""Invented PR5B source-shaped evidence; never real issuer authority."""
from tests.sec_current_common_stock_class_bridge_fixtures import class_bridge_submission
from tests.sec_filing_fixtures import row as companyfacts_row
from tests.sec_property4_temporal_fixtures import CIK
from tests.sec_submissions_fixtures import row as submissions_row


DISTRIBUTION_SENTENCE = (
    "Holders of our common stock are entitled to receive dividends when, as and if "
    "declared by our board of directors out of funds legally available therefor, "
    "subject to the prior rights of holders of any preferred stock."
)
LIQUIDATION_SENTENCE = (
    "Upon our liquidation, dissolution or winding up, after payment of our debts and "
    "other liabilities and any preferences of preferred stock, holders of our common "
    "stock are entitled to share ratably in the remaining assets."
)
VOTING_SENTENCE = (
    "Each holder of our common stock is entitled to one vote per share on each matter "
    "submitted to stockholders."
)
NO_PREFERENCE_SENTENCE = (
    "Our common stock is not redeemable or convertible and has no sinking fund."
)

VALUES = {2020: 2, 2021: 3, 2022: 4, 2023: 5, 2024: 6}


def accession(year, *, amendment=False):
    return f"0000000000-{(year + 1) % 100:02d}-{'000002' if amendment else '000001'}"


def companyfacts_rows(*, include_amendment=True):
    values = [companyfacts_row(year, value, accn=accession(year))
              for year, value in VALUES.items()]
    if include_amendment:
        values.append(companyfacts_row(
            2022,
            VALUES[2022],
            form="10-K/A",
            filed="2024-02-15",
            accn=accession(2022, amendment=True),
        ))
    return values


def source_row(year, *, amendment=False):
    filing_date = "2024-02-15" if amendment else f"{year + 1}-02-01"
    return submissions_row(
        year - 2019 + (10 if amendment else 0),
        accessionNumber=accession(year, amendment=amendment),
        filingDate=filing_date,
        reportDate=f"{year}-12-31",
        acceptanceDateTime=filing_date + "T15:30:00.000Z",
        form="10-K/A" if amendment else "10-K",
        primaryDocument="fictional.htm",
    )


def source_rows(*, include_amendment=True):
    rows = [source_row(year) for year in VALUES]
    if include_amendment:
        rows.append(source_row(2022, amendment=True))
    return rows


_SHARES_DIMENSION = (
    b'<xbrli:segment><xbrldi:explicitMember '
    b'dimension="us-gaap:StatementClassOfStockAxis">fiction:ClassAMember'
    b'</xbrldi:explicitMember></xbrli:segment>'
)
_EPS_ENTITY_CLOSE = (
    b'<xbrli:context id="eps"><xbrli:entity>'
    + f'<xbrli:identifier scheme="http://www.sec.gov/CIK">{CIK}</xbrli:identifier>'.encode()
    + b'</xbrli:entity>'
)
_EPS_DIMENSION = (
    b'<xbrli:segment><xbrldi:explicitMember '
    b'dimension="us-gaap:StatementClassOfStockAxis">fiction:ClassAMember'
    b'</xbrldi:explicitMember></xbrli:segment>'
)


def qualification_submission(
    year,
    *,
    amendment=False,
    value=None,
    rights_blocks=None,
    title="Class A Common Stock, $0.01 par value",
    dimensioned_eps=False,
    dimensioned_shares=False,
    include_eps=True,
    extra_registered=b"",
):
    if value is None:
        value = VALUES[year]
    if rights_blocks is None:
        rights_blocks = (
            ("h2", "CLASS A COMMON STOCK"),
            ("p", DISTRIBUTION_SENTENCE),
            ("p", LIQUIDATION_SENTENCE),
            ("p", VOTING_SENTENCE),
            ("p", NO_PREFERENCE_SENTENCE),
        )
    raw = class_bridge_submission(
        cik=CIK,
        accession=accession(year, amendment=amendment),
        form="10-K/A" if amendment else "10-K",
        title=title,
        rights_blocks=rights_blocks,
        include_eps=include_eps,
    )
    raw = raw.replace(b"2025-01-01", f"{year}-01-01".encode())
    raw = raw.replace(b"2025-12-31", f"{year}-12-31".encode())
    if include_eps:
        if raw.count(b">2.50</ix:nonFraction>") != 1:
            raise AssertionError("Unexpected fictional EPS fixture shape")
        raw = raw.replace(
            b">2.50</ix:nonFraction>",
            (">" + str(value) + "</ix:nonFraction>").encode(),
        )
    if not dimensioned_shares:
        if raw.count(_SHARES_DIMENSION) != 1:
            raise AssertionError("Unexpected fictional shares context shape")
        raw = raw.replace(_SHARES_DIMENSION, b"", 1)
    if dimensioned_eps and include_eps:
        if raw.count(_EPS_ENTITY_CLOSE) != 1:
            raise AssertionError("Unexpected fictional EPS context shape")
        raw = raw.replace(
            _EPS_ENTITY_CLOSE,
            _EPS_ENTITY_CLOSE[:-len(b"</xbrli:entity>")] + _EPS_DIMENSION
            + b"</xbrli:entity>",
            1,
        )
    if extra_registered:
        if raw.count(b"</ix:resources>") != 1:
            raise AssertionError("Unexpected fictional Inline XBRL resources shape")
        raw = raw.replace(b"</ix:resources>", extra_registered + b"</ix:resources>", 1)
    return raw


def with_competing_common_security(raw, year):
    context = (
        f'<xbrli:context id="registered-b"><xbrli:entity>'
        f'<xbrli:identifier scheme="http://www.sec.gov/CIK">{CIK}</xbrli:identifier>'
        '<xbrli:segment><xbrldi:explicitMember '
        'dimension="us-gaap:StatementClassOfStockAxis">fiction:ClassBMember'
        '</xbrldi:explicitMember><xbrldi:explicitMember '
        'dimension="dei:EntityListingsExchangeAxis">fiction:ExchangeMember'
        '</xbrldi:explicitMember></xbrli:segment></xbrli:entity><xbrli:period>'
        f'<xbrli:startDate>{year}-01-01</xbrli:startDate>'
        f'<xbrli:endDate>{year}-12-31</xbrli:endDate>'
        '</xbrli:period></xbrli:context>'
    ).encode()
    facts = (
        '<ix:nonNumeric name="dei:Security12bTitle" contextRef="registered-b">'
        'Class B Common Stock</ix:nonNumeric>'
        '<ix:nonNumeric name="dei:TradingSymbol" contextRef="registered-b">'
        'FICB</ix:nonNumeric>'
        '<ix:nonNumeric name="dei:SecurityExchangeName" contextRef="registered-b">'
        'NASDAQ</ix:nonNumeric>'
    ).encode()
    if raw.count(b"</ix:resources>") != 1 or raw.count(b"</body>") < 1:
        raise AssertionError("Unexpected fictional Inline XBRL shape")
    return raw.replace(b"</ix:resources>", context + b"</ix:resources>", 1).replace(
        b"</body>", facts + b"</body>", 1)


def with_mixed_dimensioned_eps(raw, year, value):
    context = (
        f'<xbrli:context id="eps-class"><xbrli:entity>'
        f'<xbrli:identifier scheme="http://www.sec.gov/CIK">{CIK}</xbrli:identifier>'
        '<xbrli:segment><xbrldi:explicitMember '
        'dimension="us-gaap:StatementClassOfStockAxis">fiction:ClassAMember'
        '</xbrldi:explicitMember></xbrli:segment></xbrli:entity><xbrli:period>'
        f'<xbrli:startDate>{year}-01-01</xbrli:startDate>'
        f'<xbrli:endDate>{year}-12-31</xbrli:endDate>'
        '</xbrli:period></xbrli:context>'
    ).encode()
    fact = (
        '<ix:nonFraction name="us-gaap:EarningsPerShareDiluted" '
        'contextRef="eps-class" unitRef="u-usd-per-share" decimals="2">'
        f'{value}</ix:nonFraction>'
    ).encode()
    if raw.count(b"</ix:resources>") != 1 or raw.count(b"</body>") < 1:
        raise AssertionError("Unexpected fictional Inline XBRL shape")
    return raw.replace(b"</ix:resources>", context + b"</ix:resources>", 1).replace(
        b"</body>", fact + b"</body>", 1)
