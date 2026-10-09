"""Fictional bounded Companyfacts PP&E acquisition cash-payment evidence."""
from copy import deepcopy

from economic_facts import sec_ordinary_compounder_profile as profile_module
from economic_facts.sec_ppe_acquisition_cash_payments import (
    PPE_ACQUISITION_CASH_PAYMENTS_CONCEPT,
)
from tests.sec_current_security_eps_qualification_fixtures import (
    companyfacts_rows,
    source_rows,
)
from tests.sec_filing_fixtures import raw, source
from tests.sec_property4_temporal_boundary_fixtures import (
    BOUNDARY_T1,
    current_request,
)
from tests.sec_property4_temporal_fixtures import CIK
from tests.sec_submissions_fixtures import root as submissions_root


PPE_ACQUISITION_CASH_PAYMENTS_VALUE = 75_000_000
LATEST_START = "2024-01-01"
LATEST_END = "2024-12-31"
LATEST_ACCESSION = "0000000000-25-000001"
SECOND_ACCESSION = "0000000000-25-000099"


def financial_row(
    value,
    *,
    start=LATEST_START,
    end=LATEST_END,
    fy=2024,
    fp="FY",
    form="10-K",
    filed="2025-02-01",
    accession=LATEST_ACCESSION,
    frame="CY2024",
    **extra,
):
    result = {
        "start": start,
        "end": end,
        "val": value,
        "fy": fy,
        "fp": fp,
        "form": form,
        "filed": filed,
        "accn": accession,
        "frame": frame,
    }
    result.update(extra)
    return result


def companyfacts_payload(
    *,
    rows=None,
    unit="USD",
    namespace="us-gaap",
    include_concept=True,
    concept=PPE_ACQUISITION_CASH_PAYMENTS_CONCEPT,
):
    payload = source(companyfacts_rows())
    payload["cik"] = int(CIK)
    payload["entityName"] = "Fictional PP&E Cash Payments Issuer"
    facts = payload["facts"].setdefault(namespace, {})
    if include_concept:
        facts[concept] = {
            "label": "Payments to acquire property, plant and equipment",
            "description": "Fictional fixture",
            "units": {
                unit: deepcopy(
                    [financial_row(PPE_ACQUISITION_CASH_PAYMENTS_VALUE)]
                    if rows is None
                    else rows
                )
            },
        }
    return payload


def coherent_payload():
    return companyfacts_payload()


def missing_payload():
    return companyfacts_payload(include_concept=False)


def wrong_unit_payload():
    return companyfacts_payload(unit="shares")


def mismatched_period_payload():
    return companyfacts_payload(rows=[
        financial_row(
            PPE_ACQUISITION_CASH_PAYMENTS_VALUE,
            start="2023-01-01",
            end="2023-12-31",
        )
    ])


def duplicate_same_value_payload():
    return companyfacts_payload(rows=[
        financial_row(PPE_ACQUISITION_CASH_PAYMENTS_VALUE),
        financial_row(
            PPE_ACQUISITION_CASH_PAYMENTS_VALUE,
            accession=SECOND_ACCESSION,
            filed="2025-02-02",
        ),
    ])


def conflicting_values_payload():
    return companyfacts_payload(rows=[
        financial_row(PPE_ACQUISITION_CASH_PAYMENTS_VALUE),
        financial_row(
            PPE_ACQUISITION_CASH_PAYMENTS_VALUE + 1,
            accession=SECOND_ACCESSION,
            filed="2025-02-02",
        ),
    ])


def capture_profile(
    comparability_fixture,
    payload=None,
    *,
    reverse=False,
    captured_at=BOUNDARY_T1,
    sic=3571,
    description="Electronic Computers",
    expected_comparability_semantic_id=None,
    expected_comparability_evidence_id=None,
):
    """Build the canonical synthetic route around one Companyfacts object."""
    payload = coherent_payload() if payload is None else payload
    receipt = comparability_fixture.current_archive._capture_live(
        raw(payload, reverse=reverse),
        cik=CIK,
        captured_at=captured_at,
    )
    current = current_request(receipt)
    parent = comparability_fixture.submissions_archive._capture_live(
        submissions_root(
            source_rows(),
            cik=CIK,
            sic=sic,
            sicDescription=description,
        ),
        cik=CIK,
        captured_at="2026-02-25T12:00:00Z",
    )
    request = comparability_fixture.build_request(parent=parent, current=current)
    comparability = comparability_fixture.qualify_request(request)
    profile_request = profile_module.SecOrdinaryCompounderProfileRequest(
        request,
        (
            comparability.semantic_id
            if expected_comparability_semantic_id is None
            else expected_comparability_semantic_id
        ),
        (
            comparability.evidence_id
            if expected_comparability_evidence_id is None
            else expected_comparability_evidence_id
        ),
    )
    profile = profile_module.qualify_sec_ordinary_compounder_profile(
        comparability_fixture.current_archive,
        comparability_fixture.submissions_archive,
        comparability_fixture.filing_archive,
        comparability_fixture.sec_archive,
        comparability_fixture.nasdaq_archive,
        profile_request,
    )
    return receipt, profile
