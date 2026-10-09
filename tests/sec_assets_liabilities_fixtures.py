"""Fictional bounded Companyfacts Assets and Liabilities evidence."""
from copy import deepcopy

from economic_facts import sec_ordinary_compounder_profile as profile_module
from economic_facts.sec_assets_liabilities import (
    LIABILITIES_CONCEPT,
    ASSETS_CONCEPT,
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


ASSETS_VALUE = 250_000_000
LIABILITIES_VALUE = 200_000_000
LATEST_END = "2024-12-31"
LATEST_ACCESSION = "0000000000-25-000001"
SECOND_ACCESSION = "0000000000-25-000099"


def financial_row(
    value,
    *,
    start=None,
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
        "end": end,
        "val": value,
        "fy": fy,
        "fp": fp,
        "form": form,
        "filed": filed,
        "accn": accession,
        "frame": frame,
    }
    if start is not None:
        result["start"] = start
    result.update(extra)
    return result


def companyfacts_payload(
    *,
    assets_rows=None,
    liabilities_rows=None,
    assets_unit="USD",
    liabilities_unit="USD",
    namespace="us-gaap",
    include_assets=True,
    include_liabilities=True,
    assets_concept=ASSETS_CONCEPT,
    liabilities_concept=LIABILITIES_CONCEPT,
):
    payload = source(companyfacts_rows())
    payload["cik"] = int(CIK)
    payload["entityName"] = "Fictional Paired Assets and Liabilities Issuer"
    facts = payload["facts"].setdefault(namespace, {})
    if include_assets:
        facts[assets_concept] = {
            "label": "Assets",
            "description": "Fictional fixture",
            "units": {
                assets_unit: deepcopy(
                    [financial_row(ASSETS_VALUE)]
                    if assets_rows is None
                    else assets_rows
                )
            },
        }
    if include_liabilities:
        facts[liabilities_concept] = {
            "label": "Liabilities",
            "description": "Fictional fixture",
            "units": {
                liabilities_unit: deepcopy(
                    [financial_row(LIABILITIES_VALUE)]
                    if liabilities_rows is None
                    else liabilities_rows
                )
            },
        }
    return payload


def coherent_pair_payload():
    return companyfacts_payload()


def missing_assets_payload():
    return companyfacts_payload(include_assets=False)


def missing_liabilities_payload():
    return companyfacts_payload(include_liabilities=False)


def wrong_unit_payload():
    return companyfacts_payload(
        assets_unit="shares",
        liabilities_unit="shares",
    )


def mismatched_period_payload():
    assets = financial_row(
        ASSETS_VALUE,
        end="2023-12-31",
    )
    liabilities = financial_row(
        LIABILITIES_VALUE,
        end="2023-12-31",
    )
    return companyfacts_payload(
        assets_rows=[assets],
        liabilities_rows=[liabilities],
    )


def no_common_accession_payload():
    return companyfacts_payload(
        assets_rows=[
            financial_row(ASSETS_VALUE, accession=LATEST_ACCESSION)
        ],
        liabilities_rows=[
            financial_row(LIABILITIES_VALUE, accession=SECOND_ACCESSION)
        ],
    )


def duplicate_same_value_payload():
    return companyfacts_payload(
        assets_rows=[
            financial_row(ASSETS_VALUE),
            financial_row(
                ASSETS_VALUE,
                accession=SECOND_ACCESSION,
                filed="2025-02-02",
            ),
        ],
        liabilities_rows=[
            financial_row(LIABILITIES_VALUE),
            financial_row(
                LIABILITIES_VALUE,
                accession=SECOND_ACCESSION,
                filed="2025-02-02",
            ),
        ],
    )


def conflicting_assets_payload():
    return companyfacts_payload(
        assets_rows=[
            financial_row(ASSETS_VALUE),
            financial_row(
                ASSETS_VALUE + 1,
                accession=SECOND_ACCESSION,
                filed="2025-02-02",
            ),
        ],
        liabilities_rows=[
            financial_row(LIABILITIES_VALUE),
            financial_row(
                LIABILITIES_VALUE,
                accession=SECOND_ACCESSION,
                filed="2025-02-02",
            ),
        ],
    )


def conflicting_liabilities_payload():
    return companyfacts_payload(
        assets_rows=[
            financial_row(ASSETS_VALUE),
            financial_row(
                ASSETS_VALUE,
                accession=SECOND_ACCESSION,
                filed="2025-02-02",
            ),
        ],
        liabilities_rows=[
            financial_row(LIABILITIES_VALUE),
            financial_row(
                LIABILITIES_VALUE + 1,
                accession=SECOND_ACCESSION,
                filed="2025-02-02",
            ),
        ],
    )


def orphan_assets_conflict_payload():
    return companyfacts_payload(
        assets_rows=[
            financial_row(ASSETS_VALUE),
            financial_row(
                ASSETS_VALUE + 1,
                accession=SECOND_ACCESSION,
            ),
        ],
        liabilities_rows=[financial_row(LIABILITIES_VALUE)],
    )


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
    payload = coherent_pair_payload() if payload is None else payload
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
