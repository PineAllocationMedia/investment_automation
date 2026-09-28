"""Fictional Companyfacts dividend evidence; no real issuer authority."""
import copy
import json

from economic_facts.sec_common_stock_dividends import (
    DECLARED_CONCEPT, PAID_CONCEPT,
)
from economic_facts.sec_verified_nonpayer import (
    NonpayerPeriodPolicy, VERIFIED_NONPAYER_CONTRACT_VERSION,
    VerifiedNonpayerRequest,
)
from tests.sec_filing_fixtures import CIK, T2


def dividend_row(value=0, *, year=2024, **changes):
    result = {
        "start": f"{year}-01-01",
        "end": f"{year}-12-31",
        "val": value,
        "fy": year,
        "fp": "FY",
        "form": "10-K",
        "filed": f"{year + 1}-02-01",
        "accn": f"0000000000-{(year + 1) % 100:02d}-000001",
        "frame": f"CY{year}",
    }
    result.update(changes)
    return result


def dividend_source(*, declared=None, paid=None, extra_facts=None, cik=0):
    facts = {
        DECLARED_CONCEPT: {
            "label": "Common stock dividends per share declared",
            "description": "Fictional fixture",
            "units": {"USD/shares": [dividend_row()] if declared is None else declared},
        },
        PAID_CONCEPT: {
            "label": "Common stock dividends per share cash paid",
            "description": "Fictional fixture",
            "units": {"USD/shares": [dividend_row()] if paid is None else paid},
        },
    }
    facts.update(extra_facts or {})
    return {"cik": cik, "entityName": "Fictional Dividend Fixture",
            "facts": {"us-gaap": facts}}


def dividend_raw(payload=None, *, reverse=False):
    def reorder(value):
        if type(value) is dict:
            return {key: reorder(child) for key, child in reversed(list(value.items()))}
        if type(value) is list:
            return [reorder(child) for child in value]
        return value
    payload = copy.deepcopy(dividend_source() if payload is None else payload)
    return json.dumps(reorder(payload) if reverse else payload,
                      separators=(",", ":")).encode()


def capture_dividends(archive, *, payload=None, raw=None, live=True, captured_at=T2):
    content = dividend_raw(payload) if raw is None else raw
    if live:
        return archive._capture_live(content, cik=CIK, captured_at=captured_at)
    return archive.capture(content, cik=CIK, captured_at=captured_at,
                           source_locator="fixture:dividends")


def nonpayer_request(receipt, **changes):
    fields = dict(
        contract_version=VERIFIED_NONPAYER_CONTRACT_VERSION,
        receipt_id=receipt.receipt_id,
        cik=CIK,
        latest_required_fiscal_end="2024-12-31",
        expected_unit="USD/shares",
        period_policy=NonpayerPeriodPolicy.FIXED_MONTH_END_365_366,
    )
    fields.update(changes)
    return VerifiedNonpayerRequest(**fields)
