"""Invented D4D3B temporal source evidence; never continuity or identity."""
from tests.sec_current_common_stock_class_bridge_fixtures import (
    class_bridge_submission,
)


ACCESSION_1 = "0000000001-26-000001"
ACCESSION_2 = "0000000001-26-000002"
ACCEPTANCE_1 = "2026-01-10T15:30:00.000Z"
ACCEPTANCE_2 = "2026-02-10T15:30:00.000Z"
CAPTURE_1 = "2026-01-11T12:00:00Z"
CAPTURE_2 = "2026-02-11T12:00:00Z"


def temporal_class_submission(*, accession=ACCESSION_1, **changes):
    return class_bridge_submission(accession=accession, **changes)
