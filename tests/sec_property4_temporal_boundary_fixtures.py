"""Fictional offline PR4D4B evidence; never a real observation."""
from economic_facts.sec_eps_series import (
    PeriodPolicy,
    ResolutionMode,
    SERIES_CONTRACT_VERSION,
    SeriesResolutionRequest,
)
from tests.sec_eps_series_fixtures import annual_rows
from tests.sec_filing_fixtures import raw, source
from tests.sec_property4_temporal_fixtures import CIK


BOUNDARY_T1 = "2026-03-01T12:00:00Z"
BOUNDARY_T2 = "2026-06-01T12:00:00Z"
PRE_BOUNDARY_CAPTURE = "2026-02-02T12:00:00Z"
POST_BOUNDARY_CAPTURE = "2026-05-01T12:00:00Z"


def current_payload(*, cik=CIK, rows=None):
    value = source(annual_rows() if rows is None else rows)
    value["cik"] = int(cik)
    value["entityName"] = "Fictional D4B Issuer"
    return raw(value)


def capture_current(archive, *, cik=CIK, boundary=BOUNDARY_T1, live=True, rows=None):
    payload = current_payload(cik=cik, rows=rows)
    if live:
        return archive._capture_live(payload, cik=cik, captured_at=boundary)
    return archive.capture(payload, cik=cik, captured_at=boundary,
                           source_locator="fixture:property4-boundary")


def current_request(receipt, *, cik=CIK, mode=ResolutionMode.CURRENT_AS_REPORTED):
    return SeriesResolutionRequest(
        SERIES_CONTRACT_VERSION,
        mode,
        receipt.receipt_id,
        cik,
        "2024-12-31",
        "USD/shares",
        PeriodPolicy.FIXED_MONTH_END_365_366,
    )
