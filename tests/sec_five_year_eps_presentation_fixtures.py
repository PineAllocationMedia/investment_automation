"""Fictional SEC-shaped five-year EPS presentations; never issuer authority."""
from decimal import Decimal

from tests.sec_current_security_eps_qualification_fixtures import VALUES


SUPPORTED_ROW = "Diluted earnings per share attributable to common stockholders"


def five_year_table(*, values=None, years=None, heading="Years Ended December 31",
                    row_label=SUPPORTED_ROW):
    if values is None:
        values = {year: Decimal(value) for year, value in VALUES.items()}
    if years is None:
        years = tuple(sorted(values, reverse=True))
    headers = "".join(f"<th>{year}</th>" for year in years)
    cells = "".join(f"<td>{values[year]}</td>" for year in years)
    return (
        "<table><thead><tr><th>" + heading + "</th>" + headers
        + "</tr></thead><tbody><tr><th>" + row_label + "</th>" + cells
        + "</tr></tbody></table>"
    )


def inject_before_body(raw, *html):
    marker = b"</body>"
    if raw.count(marker) < 1:
        raise AssertionError("Unexpected fictional primary-document shape")
    return raw.replace(marker, "".join(html).encode("utf-8") + marker, 1)
