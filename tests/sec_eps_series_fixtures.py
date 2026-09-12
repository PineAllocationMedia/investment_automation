"""Fictional issuer evidence only; no real company or retained-archive dependency."""
from economic_facts.sec_eps_series import (PeriodPolicy, ResolutionMode, SERIES_CONTRACT_VERSION,
                                          SeriesResolutionRequest)
from tests.sec_filing_fixtures import CIK, T2, raw, row, source


def annual_rows():
    return [row(year, year - 2018) for year in range(2020, 2025)]


def request(receipt, **changes):
    fields = dict(contract_version=SERIES_CONTRACT_VERSION, mode=ResolutionMode.CURRENT_AS_REPORTED,
                  receipt_id=receipt.receipt_id, cik=CIK, latest_required_fiscal_end="2024-12-31",
                  expected_unit="USD/shares", period_policy=PeriodPolicy.FIXED_MONTH_END_365_366)
    fields.update(changes)
    return SeriesResolutionRequest(**fields)


def capture(archive, rows=None, *, payload=None, live=False, captured_at=T2):
    content = raw(source(annual_rows() if rows is None else rows) if payload is None else payload)
    if live:
        # Fixture publication only; does not invoke acquisition or assert real trust.
        return archive._capture_live(content, cik=CIK, captured_at=captured_at)
    return archive.capture(content, cik=CIK, captured_at=captured_at, source_locator="fixture:series")
