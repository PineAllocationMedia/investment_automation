"""Fictional bounded Companyfacts denominator-share evidence."""
from copy import deepcopy

from economic_facts import sec_ordinary_compounder_profile as profile_module
from economic_facts.sec_eps_denominator_shares import (
    BASIC_CONCEPT,
    DILUTED_CONCEPT,
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


BASIC_VALUE = 100_000_000
DILUTED_VALUE = 105_000_000
LATEST_START = "2024-01-01"
LATEST_END = "2024-12-31"
LATEST_ACCESSION = "0000000000-25-000001"
SECOND_ACCESSION = "0000000000-25-000099"


def denominator_row(
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
    basic_rows=None,
    diluted_rows=None,
    basic_unit="shares",
    diluted_unit="shares",
    namespace="us-gaap",
    include_basic=True,
    include_diluted=True,
    issuer_extension_basic=False,
):
    payload = source(companyfacts_rows())
    payload["cik"] = int(CIK)
    payload["entityName"] = "Fictional Denominator Shares Issuer"
    facts = payload["facts"].setdefault(namespace, {})
    if include_basic:
        concept = "fiction:WeightedAverageBasicShares" if issuer_extension_basic else BASIC_CONCEPT
        facts[concept] = {
            "label": "Weighted average basic shares",
            "description": "Fictional fixture",
            "units": {
                basic_unit: deepcopy(
                    [denominator_row(BASIC_VALUE)]
                    if basic_rows is None else basic_rows
                )
            },
        }
    if include_diluted:
        facts[DILUTED_CONCEPT] = {
            "label": "Weighted average diluted shares",
            "description": "Fictional fixture",
            "units": {
                diluted_unit: deepcopy(
                    [denominator_row(DILUTED_VALUE)]
                    if diluted_rows is None else diluted_rows
                )
            },
        }
    return payload


def coherent_pair_payload():
    return companyfacts_payload()


def basic_missing_payload():
    return companyfacts_payload(include_basic=False)


def diluted_missing_payload():
    return companyfacts_payload(include_diluted=False)


def wrong_unit_payload():
    return companyfacts_payload(basic_unit="USD", diluted_unit="USD")


def quarterly_payload():
    quarterly = denominator_row(
        BASIC_VALUE,
        start="2024-10-01",
        fp="Q4",
        form="10-Q",
    )
    quarterly_diluted = dict(quarterly, val=DILUTED_VALUE)
    return companyfacts_payload(
        basic_rows=[quarterly], diluted_rows=[quarterly_diluted]
    )


def mismatched_period_payload():
    return companyfacts_payload(
        basic_rows=[denominator_row(BASIC_VALUE, start="2023-01-01", end="2023-12-31")],
        diluted_rows=[denominator_row(DILUTED_VALUE, start="2023-01-01", end="2023-12-31")],
    )


def no_common_accession_payload():
    return companyfacts_payload(
        basic_rows=[denominator_row(BASIC_VALUE, accession=LATEST_ACCESSION)],
        diluted_rows=[denominator_row(DILUTED_VALUE, accession=SECOND_ACCESSION)],
    )


def duplicate_same_value_payload():
    return companyfacts_payload(
        basic_rows=[
            denominator_row(BASIC_VALUE, accession=LATEST_ACCESSION),
            denominator_row(BASIC_VALUE, accession=SECOND_ACCESSION, filed="2025-02-02"),
        ],
        diluted_rows=[
            denominator_row(DILUTED_VALUE, accession=LATEST_ACCESSION),
            denominator_row(DILUTED_VALUE, accession=SECOND_ACCESSION, filed="2025-02-02"),
        ],
    )


def conflicting_values_payload():
    return companyfacts_payload(
        basic_rows=[
            denominator_row(BASIC_VALUE),
            denominator_row(BASIC_VALUE + 1, accession=SECOND_ACCESSION),
        ],
        diluted_rows=[
            denominator_row(DILUTED_VALUE),
            denominator_row(DILUTED_VALUE, accession=SECOND_ACCESSION),
        ],
    )


def diluted_below_basic_payload():
    return companyfacts_payload(
        basic_rows=[denominator_row(BASIC_VALUE)],
        diluted_rows=[denominator_row(BASIC_VALUE - 1)],
    )


def capture_profile(comparability_fixture, payload=None, *, reverse=False,
                    sic=3571, description="Electronic Computers"):
    """Build the real synthetic canonical route around one Companyfacts object."""
    payload = coherent_pair_payload() if payload is None else payload
    receipt = comparability_fixture.current_archive._capture_live(
        raw(payload, reverse=reverse), cik=CIK, captured_at=BOUNDARY_T1
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
        request, comparability.semantic_id, comparability.evidence_id
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
