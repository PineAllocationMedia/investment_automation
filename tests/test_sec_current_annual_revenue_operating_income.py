"""Adversarial tests for paired CURRENT annual revenue and operating income."""
import ast
from collections import UserDict
from dataclasses import FrozenInstanceError, fields, replace
from decimal import Decimal
import json
from pathlib import Path
import socket
import tempfile
import unittest
from unittest.mock import patch

from economic_facts import sec_current_annual_revenue_operating_income as qualifier
from economic_facts import sec_revenue_operating_income as extraction
from economic_facts import sec_ordinary_compounder_profile as profile_module
from economic_facts.sec_archive import ArchiveError, SecArchive
from tests import test_sec_current_eps_comparability_qualification as comparability_tests
from tests.sec_filing_fixtures import raw
from tests.sec_revenue_operating_income_fixtures import (
    LATEST_ACCESSION,
    OPERATING_INCOME_VALUE,
    REVENUE_VALUE,
    SECOND_ACCESSION,
    capture_profile,
    coherent_pair_payload,
    companyfacts_payload,
    conflicting_operating_income_payload,
    conflicting_revenue_payload,
    duplicate_same_value_payload,
    financial_row,
    mismatched_period_payload,
    missing_operating_income_payload,
    missing_revenue_payload,
    no_common_accession_payload,
    orphan_revenue_conflict_payload,
    wrong_unit_payload,
)
from tests.sec_property4_temporal_boundary_fixtures import BOUNDARY_T1, BOUNDARY_T2
from tests.sec_property4_temporal_fixtures import CIK


class SecCurrentAnnualRevenueOperatingIncomeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = comparability_tests.SecCurrentEPSComparabilityTests(
            methodName="runTest"
        )
        cls.fixture.setUp()
        cls.receipt, cls.available = capture_profile(cls.fixture)
        _, cls.unavailable = capture_profile(
            cls.fixture,
            sic=None,
            description=None,
        )
        _, cls.unsupported = capture_profile(
            cls.fixture,
            sic=6021,
            description="National Commercial Banks",
        )
        _, cls.source_conflict = capture_profile(
            cls.fixture,
            expected_comparability_semantic_id="0" * 64,
        )

    @classmethod
    def tearDownClass(cls):
        cls.fixture.doCleanups()

    def qualify(self, profile=None, archive=None):
        return qualifier.qualify_sec_current_annual_revenue_operating_income(
            self.fixture.current_archive if archive is None else archive,
            self.available if profile is None else profile,
        )

    def profile_for(self, payload, *, reverse=False, captured_at=BOUNDARY_T1):
        return capture_profile(
            self.fixture,
            payload,
            reverse=reverse,
            captured_at=captured_at,
        )[1]

    def extract(self, payload, *, content=None):
        with tempfile.TemporaryDirectory() as temporary:
            archive = SecArchive(Path(temporary).resolve() / "archive")
            receipt = archive._capture_live(
                raw(payload) if content is None else content,
                cik=CIK,
                captured_at=BOUNDARY_T1,
            )
            return extraction.extract_revenue_operating_income(
                archive.read_object(receipt), receipt
            )

    def test_exact_public_input_types_only(self):
        class ArchiveSubclass(SecArchive):
            pass

        class ProfileSubclass(
            profile_module.OrdinaryCompounderMethodProfileQualification
        ):
            pass

        subclass = ProfileSubclass(*(
            getattr(self.available, field.name)
            for field in fields(self.available)
        ))
        with tempfile.TemporaryDirectory() as temporary:
            foreign_archive = ArchiveSubclass(Path(temporary) / "archive")
            cases = (
                ({}, self.available),
                (UserDict(), self.available),
                (foreign_archive, self.available),
                (self.fixture.current_archive, {}),
                (self.fixture.current_archive, UserDict()),
                (self.fixture.current_archive, subclass),
                (self.fixture.current_archive, self.available.upstream_comparability),
            )
            for archive, profile in cases:
                with self.subTest(types=(type(archive), type(profile))), \
                        self.assertRaises(
                            qualifier.CurrentAnnualRevenueOperatingIncomeError
                        ):
                    qualifier.qualify_sec_current_annual_revenue_operating_income(
                        archive, profile
                    )

    def test_coherent_pair_establishes_exact_decimal_facts_only(self):
        result = self.qualify()
        self.assertEqual(
            result.contract_version,
            "2026-10-07-current-annual-revenue-operating-income-qualification-v1",
        )
        self.assertEqual(
            result.qualifier_version,
            "2026-10-07-paired-common-filing-exact-decimal-usd-qualification-v1",
        )
        self.assertEqual(
            result.evidence_kind,
            "CURRENT_ANNUAL_REVENUE_OPERATING_INCOME_QUALIFICATION",
        )
        self.assertIs(
            result.status,
            qualifier.CurrentAnnualRevenueOperatingIncomeStatus.
            PAIRED_REVENUE_OPERATING_INCOME_ESTABLISHED,
        )
        self.assertEqual(result.period_start, "2024-01-01")
        self.assertEqual(result.period_end, "2024-12-31")
        self.assertEqual(result.revenue, Decimal(REVENUE_VALUE))
        self.assertEqual(result.operating_income, Decimal(OPERATING_INCOME_VALUE))
        self.assertIs(type(result.revenue), Decimal)
        self.assertIs(type(result.operating_income), Decimal)
        self.assertEqual(result.supporting_accessions, (LATEST_ACCESSION,))
        for forbidden in (
            "ratio", "percentage", "margin", "quality_score",
            "grade", "threshold", "recommendation", "allocation",
        ):
            self.assertNotIn(forbidden, result.to_dict()[
                "current_annual_revenue_operating_income"
            ])

    def test_profile_capability_states_project_exactly_without_partial_values(self):
        cases = (
            (
                self.unavailable,
                qualifier.CurrentAnnualRevenueOperatingIncomeStatus.
                EVIDENCE_UNAVAILABLE,
                qualifier.CurrentAnnualRevenueOperatingIncomeReason.
                UPSTREAM_PROFILE_UNAVAILABLE,
            ),
            (
                self.unsupported,
                qualifier.CurrentAnnualRevenueOperatingIncomeStatus.
                EVIDENCE_UNSUPPORTED,
                qualifier.CurrentAnnualRevenueOperatingIncomeReason.
                UPSTREAM_PROFILE_UNSUPPORTED,
            ),
            (
                self.source_conflict,
                qualifier.CurrentAnnualRevenueOperatingIncomeStatus.SOURCE_CONFLICT,
                qualifier.CurrentAnnualRevenueOperatingIncomeReason.
                UPSTREAM_SOURCE_CONFLICT,
            ),
        )
        for profile, status, reason in cases:
            with self.subTest(status=status):
                result = self.qualify(profile)
                self.assertIs(result.status, status)
                self.assertEqual(result.reasons, (reason,))
                self.assertIsNone(result.revenue)
                self.assertIsNone(result.operating_income)
                self.assertEqual(result.selected_revenue_observation_ids, ())
                self.assertEqual(result.selected_operating_income_observation_ids, ())
                self.assertEqual(result.supporting_accessions, ())
                self.assertEqual(result.supporting_filings, ())

    def test_factory_impossible_reconstructed_profile_states_are_rejected(self):
        impossible = (
            replace(
                self.available,
                status=profile_module.OrdinaryCompounderProfileStatus.PROFILE_UNAVAILABLE,
                profile=None,
                reasons=(),
            ),
            replace(
                self.available,
                status=profile_module.OrdinaryCompounderProfileStatus.PROFILE_UNSUPPORTED,
                profile=None,
                reasons=(profile_module.ProfileReason.SIC_MISSING_OR_INVALID,),
            ),
            replace(
                self.available,
                status=profile_module.OrdinaryCompounderProfileStatus.SOURCE_CONFLICT,
                profile=None,
                reasons=(profile_module.ProfileReason.UNSUPPORTED_SIC_PROFILE,),
            ),
            replace(
                self.available,
                status=profile_module.OrdinaryCompounderProfileStatus.PROFILE_UNAVAILABLE,
                profile=None,
                reasons=(
                    profile_module.ProfileReason.
                    POSITIVE_FIVE_PERIOD_ROUTE_NOT_ESTABLISHED,
                ),
            ),
            replace(self.available, status="FUTURE_STATE"),
            replace(self.available, source_cik="0000000001"),
        )
        for profile in impossible:
            with self.subTest(profile=profile), self.assertRaises(
                qualifier.CurrentAnnualRevenueOperatingIncomeError
            ):
                self.qualify(profile)

    def test_factory_out_of_range_integer_sic_projects_capability_state(self):
        _, profile = capture_profile(
            self.fixture,
            sic=10000,
            description="Out of Range Industry",
        )
        self.assertIs(
            profile.status,
            profile_module.OrdinaryCompounderProfileStatus.PROFILE_UNAVAILABLE,
        )
        self.assertIn(
            profile_module.ProfileReason.SIC_MISSING_OR_INVALID,
            profile.reasons,
        )
        self.assertEqual(profile.sic, 10000)
        self.assertEqual(len(profile.decisions), len(profile_module.UnsupportedStructure))

        result = self.qualify(profile)
        projected = {
            profile_module.OrdinaryCompounderProfileStatus.PROFILE_UNAVAILABLE: (
                qualifier.CurrentAnnualRevenueOperatingIncomeStatus.
                EVIDENCE_UNAVAILABLE,
                qualifier.CurrentAnnualRevenueOperatingIncomeReason.
                UPSTREAM_PROFILE_UNAVAILABLE,
            ),
            profile_module.OrdinaryCompounderProfileStatus.PROFILE_UNSUPPORTED: (
                qualifier.CurrentAnnualRevenueOperatingIncomeStatus.
                EVIDENCE_UNSUPPORTED,
                qualifier.CurrentAnnualRevenueOperatingIncomeReason.
                UPSTREAM_PROFILE_UNSUPPORTED,
            ),
            profile_module.OrdinaryCompounderProfileStatus.SOURCE_CONFLICT: (
                qualifier.CurrentAnnualRevenueOperatingIncomeStatus.SOURCE_CONFLICT,
                qualifier.CurrentAnnualRevenueOperatingIncomeReason.
                UPSTREAM_SOURCE_CONFLICT,
            ),
        }
        expected_status, expected_reason = projected[profile.status]
        self.assertIs(result.status, expected_status)
        self.assertEqual(result.reasons, (expected_reason,))
        self.assertIsNone(result.revenue)
        self.assertIsNone(result.operating_income)
        self.assertEqual(result.selected_revenue_observation_ids, ())
        self.assertEqual(result.selected_operating_income_observation_ids, ())
        self.assertEqual(result.supporting_accessions, ())
        self.assertEqual(result.supporting_filings, ())

        for invalid_sic in ("10000", 10000.0, True):
            with self.subTest(invalid_sic=invalid_sic), self.assertRaises(
                qualifier.CurrentAnnualRevenueOperatingIncomeError
            ):
                self.qualify(replace(profile, sic=invalid_sic))

    def test_established_profile_and_period_chain_must_remain_canonical(self):
        periods = list(self.available.upstream_comparability.period_decisions)
        periods[2] = replace(
            periods[2],
            period_start=periods[1].period_start,
            period_end=periods[1].period_end,
        )
        cases = (
            replace(self.available, metadata_semantic_id=None),
            replace(self.available, sic_description=" Electronic Computers "),
            replace(self.available, sic=10000),
            replace(
                self.available,
                upstream_comparability=replace(
                    self.available.upstream_comparability,
                    period_decisions=tuple(periods),
                ),
            ),
        )
        for profile in cases:
            with self.subTest(profile=profile), self.assertRaises(
                qualifier.CurrentAnnualRevenueOperatingIncomeError
            ):
                self.qualify(profile)

    def test_extraction_preserves_exact_source_row_and_capture_semantics(self):
        observation = next(
            item for item in self.extract(coherent_pair_payload()).observations
            if item.concept == extraction.REVENUE_CONCEPT
        )
        original = financial_row(REVENUE_VALUE)
        self.assertEqual(observation.source_cik, CIK)
        self.assertEqual(observation.namespace, "us-gaap")
        self.assertEqual(observation.unit, "USD")
        self.assertEqual(observation.value, Decimal(REVENUE_VALUE))
        for field, source_key in (
            ("start", "start"), ("end", "end"), ("fy", "fy"),
            ("fp", "fp"), ("form", "form"), ("filed", "filed"),
            ("accession", "accn"), ("frame", "frame"),
        ):
            self.assertEqual(getattr(observation, field), original[source_key])
        self.assertTrue(observation.source_object_hash)
        self.assertTrue(observation.capture_receipt_id)
        self.assertTrue(observation.source_locator)
        self.assertTrue(observation.semantic_locator)
        self.assertTrue(observation.row_json)
        self.assertIn("CURRENT_CAPTURE_REPLAY", observation.source_semantics)

    def test_malformed_companyfacts_structures_fail_closed(self):
        malformed = []
        facts_array = coherent_pair_payload()
        facts_array["facts"] = []
        malformed.append(facts_array)
        units_array = coherent_pair_payload()
        units_array["facts"]["us-gaap"][extraction.REVENUE_CONCEPT]["units"] = []
        malformed.append(units_array)
        rows_object = coherent_pair_payload()
        rows_object["facts"]["us-gaap"][extraction.REVENUE_CONCEPT]["units"][
            "USD"
        ] = {}
        malformed.append(rows_object)
        row_array = coherent_pair_payload()
        row_array["facts"]["us-gaap"][extraction.REVENUE_CONCEPT]["units"][
            "USD"
        ] = [[]]
        malformed.append(row_array)
        for payload in malformed:
            with self.subTest(payload=payload), self.assertRaises(ArchiveError):
                self.extract(payload)

    def test_state_and_reason_surfaces_are_closed(self):
        self.assertEqual(
            {item.value for item in qualifier.CurrentAnnualRevenueOperatingIncomeStatus},
            {
                "PAIRED_REVENUE_OPERATING_INCOME_ESTABLISHED",
                "EVIDENCE_UNAVAILABLE",
                "EVIDENCE_UNSUPPORTED",
                "SOURCE_CONFLICT",
            },
        )
        self.assertEqual(
            {item.value for item in qualifier.CurrentAnnualRevenueOperatingIncomeReason},
            {
                "UPSTREAM_PROFILE_UNAVAILABLE",
                "UPSTREAM_PROFILE_UNSUPPORTED",
                "UPSTREAM_SOURCE_CONFLICT",
                "CANONICAL_ROUTE_IDENTITY_CONFLICT",
                "CAPTURE_REPLAY_CONFLICT",
                "SOURCE_CIK_CONFLICT",
                "REVENUE_UNAVAILABLE",
                "OPERATING_INCOME_UNAVAILABLE",
                "EXACT_USD_UNIT_UNAVAILABLE",
                "FINITE_REVENUE_VALUE_UNAVAILABLE",
                "FINITE_OPERATING_INCOME_VALUE_UNAVAILABLE",
                "EXACT_ANNUAL_PERIOD_PRESENTATION_UNAVAILABLE",
                "NO_COMMON_ANNUAL_FILING_ACCESSION",
                "COMPETING_REVENUE_VALUES",
                "COMPETING_OPERATING_INCOME_VALUES",
                "COMMON_FILING_METADATA_CONFLICT",
            },
        )

    def test_only_exact_concepts_namespace_and_usd_unit_are_admissible(self):
        substitutes = (
            ("revenue_concept", "SalesRevenueNet"),
            ("revenue_concept", "Revenues"),
            ("operating_income_concept", "ProfitLoss"),
            ("operating_income_concept", "GrossProfit"),
            ("operating_income_concept", "AdjustedOperatingIncome"),
            ("operating_income_concept", "EBITDA"),
        )
        for key, concept in substitutes:
            result = self.qualify(self.profile_for(companyfacts_payload(**{key: concept})))
            with self.subTest(concept=concept):
                self.assertIs(
                    result.status,
                    qualifier.CurrentAnnualRevenueOperatingIncomeStatus.
                    EVIDENCE_UNAVAILABLE,
                )
                self.assertIsNone(result.revenue)
                self.assertIsNone(result.operating_income)
        issuer_extension = companyfacts_payload(
            namespace="fiction",
            revenue_concept="FictionRevenue",
            operating_income_concept="FictionOperatingIncome",
        )
        result = self.qualify(self.profile_for(issuer_extension))
        self.assertIs(
            result.status,
            qualifier.CurrentAnnualRevenueOperatingIncomeStatus.EVIDENCE_UNAVAILABLE,
        )
        wrong_unit = self.qualify(self.profile_for(wrong_unit_payload()))
        self.assertEqual(
            wrong_unit.reasons,
            (qualifier.CurrentAnnualRevenueOperatingIncomeReason.
             EXACT_USD_UNIT_UNAVAILABLE,),
        )
        missing_unit_payload = coherent_pair_payload()
        missing_unit_payload["facts"]["us-gaap"][
            extraction.REVENUE_CONCEPT
        ]["units"] = {}
        missing_unit = self.qualify(self.profile_for(missing_unit_payload))
        self.assertEqual(
            missing_unit.reasons,
            (qualifier.CurrentAnnualRevenueOperatingIncomeReason.
             EXACT_USD_UNIT_UNAVAILABLE,),
        )

    def test_missing_concepts_are_unavailable_and_never_zero(self):
        cases = (
            (
                missing_revenue_payload(),
                qualifier.CurrentAnnualRevenueOperatingIncomeReason.
                REVENUE_UNAVAILABLE,
            ),
            (
                missing_operating_income_payload(),
                qualifier.CurrentAnnualRevenueOperatingIncomeReason.
                OPERATING_INCOME_UNAVAILABLE,
            ),
        )
        for payload, reason in cases:
            result = self.qualify(self.profile_for(payload))
            with self.subTest(reason=reason):
                self.assertIs(
                    result.status,
                    qualifier.CurrentAnnualRevenueOperatingIncomeStatus.
                    EVIDENCE_UNAVAILABLE,
                )
                self.assertIn(reason, result.reasons)
                self.assertIsNone(result.revenue)
                self.assertIsNone(result.operating_income)

        both = self.qualify(self.profile_for(companyfacts_payload(
            include_revenue=False,
            include_operating_income=False,
        )))
        self.assertEqual(
            both.reasons,
            tuple(sorted(
                (
                    qualifier.CurrentAnnualRevenueOperatingIncomeReason.
                    REVENUE_UNAVAILABLE,
                    qualifier.CurrentAnnualRevenueOperatingIncomeReason.
                    OPERATING_INCOME_UNAVAILABLE,
                ),
                key=lambda item: item.value,
            )),
        )

    def test_zero_and_negative_values_are_legitimate_exact_facts(self):
        cases = ((9, 5), (9, 0), (9, -4), (0, 2), (-5, 2), (-5, -6))
        for revenue_value, operating_income_value in cases:
            payload = companyfacts_payload(
                revenue_rows=[financial_row(revenue_value)],
                operating_income_rows=[financial_row(operating_income_value)],
            )
            result = self.qualify(self.profile_for(payload))
            with self.subTest(values=(revenue_value, operating_income_value)):
                self.assertIs(
                    result.status,
                    qualifier.CurrentAnnualRevenueOperatingIncomeStatus.
                    PAIRED_REVENUE_OPERATING_INCOME_ESTABLISHED,
                )
                self.assertEqual(result.revenue, Decimal(revenue_value))
                self.assertEqual(
                    result.operating_income, Decimal(operating_income_value)
                )

    def test_nonfinite_and_invalid_values_cannot_establish(self):
        cases = (
            (
                companyfacts_payload(
                    revenue_rows=[financial_row("NaN")],
                    operating_income_rows=[financial_row(OPERATING_INCOME_VALUE)],
                ),
                qualifier.CurrentAnnualRevenueOperatingIncomeReason.
                FINITE_REVENUE_VALUE_UNAVAILABLE,
            ),
            (
                companyfacts_payload(
                    revenue_rows=[financial_row(REVENUE_VALUE)],
                    operating_income_rows=[financial_row("Infinity")],
                ),
                qualifier.CurrentAnnualRevenueOperatingIncomeReason.
                FINITE_OPERATING_INCOME_VALUE_UNAVAILABLE,
            ),
        )
        for payload, reason in cases:
            with self.subTest(reason=reason):
                self.assertEqual(
                    self.qualify(self.profile_for(payload)).reasons,
                    (reason,),
                )
        nonfinite = raw(coherent_pair_payload()).replace(
            str(REVENUE_VALUE).encode(), b"NaN", 1
        )
        with self.assertRaises(ArchiveError):
            self.extract(coherent_pair_payload(), content=nonfinite)

    def test_exact_annual_period_and_presentation_are_required(self):
        payloads = (
            mismatched_period_payload(),
            companyfacts_payload(
                revenue_rows=[financial_row(
                    REVENUE_VALUE, fp="Q4", form="10-Q"
                )],
                operating_income_rows=[financial_row(
                    OPERATING_INCOME_VALUE, fp="Q4", form="10-Q"
                )],
            ),
            companyfacts_payload(
                revenue_rows=[financial_row(
                    REVENUE_VALUE, start=None
                )],
                operating_income_rows=[financial_row(OPERATING_INCOME_VALUE, start=None)],
            ),
        )
        for payload in payloads:
            result = self.qualify(self.profile_for(payload))
            with self.subTest(payload=payload):
                self.assertIs(
                    result.status,
                    qualifier.CurrentAnnualRevenueOperatingIncomeStatus.
                    EVIDENCE_UNAVAILABLE,
                )
                self.assertIn(
                    qualifier.CurrentAnnualRevenueOperatingIncomeReason.
                    EXACT_ANNUAL_PERIOD_PRESENTATION_UNAVAILABLE,
                    result.reasons,
                )

    def test_common_accession_required_and_orphan_does_not_poison_pair(self):
        unavailable = self.qualify(self.profile_for(no_common_accession_payload()))
        self.assertEqual(
            unavailable.reasons,
            (qualifier.CurrentAnnualRevenueOperatingIncomeReason.
             NO_COMMON_ANNUAL_FILING_ACCESSION,),
        )
        established = self.qualify(
            self.profile_for(orphan_revenue_conflict_payload())
        )
        self.assertIs(
            established.status,
            qualifier.CurrentAnnualRevenueOperatingIncomeStatus.
            PAIRED_REVENUE_OPERATING_INCOME_ESTABLISHED,
        )
        self.assertEqual(established.supporting_accessions, (LATEST_ACCESSION,))

    def test_multiple_coherent_common_accessions_are_deterministic(self):
        profile = self.profile_for(duplicate_same_value_payload())
        first = self.qualify(profile)
        second = self.qualify(profile)
        self.assertEqual(first, second)
        self.assertEqual(first.supporting_accessions,
                         (LATEST_ACCESSION, SECOND_ACCESSION))
        self.assertEqual(first.semantic_id, second.semantic_id)
        self.assertEqual(first.evidence_id, second.evidence_id)

    def test_competing_common_pair_values_are_source_conflicts(self):
        cases = (
            (
                conflicting_revenue_payload(),
                qualifier.CurrentAnnualRevenueOperatingIncomeReason.
                COMPETING_REVENUE_VALUES,
            ),
            (
                conflicting_operating_income_payload(),
                qualifier.CurrentAnnualRevenueOperatingIncomeReason.
                COMPETING_OPERATING_INCOME_VALUES,
            ),
        )
        for payload, reason in cases:
            result = self.qualify(self.profile_for(payload))
            with self.subTest(reason=reason):
                self.assertIs(
                    result.status,
                    qualifier.CurrentAnnualRevenueOperatingIncomeStatus.
                    SOURCE_CONFLICT,
                )
                self.assertIn(reason, result.reasons)
                self.assertIsNone(result.revenue)
                self.assertIsNone(result.operating_income)

        both = companyfacts_payload(
            revenue_rows=[
                financial_row(100),
                financial_row(101, accession=SECOND_ACCESSION, filed="2025-02-02"),
            ],
            operating_income_rows=[
                financial_row(20),
                financial_row(21, accession=SECOND_ACCESSION, filed="2025-02-02"),
            ],
        )
        result = self.qualify(self.profile_for(both))
        self.assertEqual(
            set(result.reasons),
            {
                qualifier.CurrentAnnualRevenueOperatingIncomeReason.
                COMPETING_REVENUE_VALUES,
                qualifier.CurrentAnnualRevenueOperatingIncomeReason.
                COMPETING_OPERATING_INCOME_VALUES,
            },
        )

    def test_common_accession_metadata_must_be_coherent_but_frame_may_differ(self):
        for field, replacement in (
            ("form", "10-K/A"),
            ("filed", "2025-02-02"),
            ("fy", 2025),
        ):
            operating = financial_row(REVENUE_VALUE)
            income = financial_row(OPERATING_INCOME_VALUE, **{field: replacement})
            result = self.qualify(self.profile_for(companyfacts_payload(
                revenue_rows=[operating],
                operating_income_rows=[income],
            )))
            with self.subTest(field=field):
                self.assertEqual(
                    result.reasons,
                    (qualifier.CurrentAnnualRevenueOperatingIncomeReason.
                     COMMON_FILING_METADATA_CONFLICT,),
                )
        frame_difference = self.qualify(self.profile_for(companyfacts_payload(
            revenue_rows=[financial_row(
                REVENUE_VALUE, frame="CY2024"
            )],
            operating_income_rows=[financial_row(
                OPERATING_INCOME_VALUE, frame="CY2024Q4"
            )],
        )))
        self.assertIs(
            frame_difference.status,
            qualifier.CurrentAnnualRevenueOperatingIncomeStatus.
            PAIRED_REVENUE_OPERATING_INCOME_ESTABLISHED,
        )

    def test_route_receipt_object_and_source_cik_conflicts_fail_closed(self):
        route_mismatch = replace(
            self.available,
            upstream_comparability=replace(
                self.available.upstream_comparability,
                route_local_issuer_key="0" * 64,
            ),
        )
        with self.assertRaises(
            qualifier.CurrentAnnualRevenueOperatingIncomeError
        ):
            self.qualify(route_mismatch)

        comparability = self.available.upstream_comparability
        security = comparability.upstream_security_eps
        bridge = security.upstream_registered_listing_bridge
        temporal = bridge.temporal_boundary
        current = temporal.current_evidence
        incoherent_request = replace(current.request, cik="0000000001")
        incoherent_current = replace(current, request=incoherent_request)
        incoherent_temporal = replace(temporal, current_evidence=incoherent_current)
        incoherent_bridge = replace(bridge, temporal_boundary=incoherent_temporal)
        incoherent_security = replace(
            security,
            upstream_registered_listing_bridge=incoherent_bridge,
        )
        incoherent_comparability = replace(
            comparability,
            upstream_security_eps=incoherent_security,
        )
        incoherent_profile = replace(
            self.available,
            upstream_comparability=incoherent_comparability,
        )
        route_conflict = self.qualify(incoherent_profile)
        self.assertEqual(
            route_conflict.reasons,
            (qualifier.CurrentAnnualRevenueOperatingIncomeReason.
             CANONICAL_ROUTE_IDENTITY_CONFLICT,),
        )

        with tempfile.TemporaryDirectory() as temporary:
            foreign = SecArchive(Path(temporary).resolve() / "foreign")
            replay = self.qualify(archive=foreign)
        self.assertEqual(
            replay.reasons,
            (qualifier.CurrentAnnualRevenueOperatingIncomeReason.
             CAPTURE_REPLAY_CONFLICT,),
        )
        mismatched_receipt = replace(
            self.receipt,
            captured_at="2025-03-02T12:00:00Z",
        )
        with patch.object(
            self.fixture.current_archive,
            "read_receipt",
            return_value=mismatched_receipt,
        ):
            receipt_conflict = self.qualify()
        self.assertEqual(
            receipt_conflict.reasons,
            (qualifier.CurrentAnnualRevenueOperatingIncomeReason.
             CAPTURE_REPLAY_CONFLICT,),
        )
        with patch.object(
            self.fixture.current_archive,
            "read_object",
            side_effect=ArchiveError("corrupt object"),
        ):
            object_conflict = self.qualify()
        self.assertEqual(
            object_conflict.reasons,
            (qualifier.CurrentAnnualRevenueOperatingIncomeReason.
             CAPTURE_REPLAY_CONFLICT,),
        )
        extracted = extraction.RevenueOperatingIncomeExtraction(
            extraction.EXTRACTION_VERSION,
            "0000000001",
            self.receipt.receipt_id,
            self.receipt.content_sha256,
            self.receipt.captured_at,
            self.receipt.source_locator,
            (),
            (),
        )
        with patch.object(
            qualifier,
            "extract_revenue_operating_income",
            return_value=extracted,
        ):
            cik_conflict = self.qualify()
        self.assertEqual(
            cik_conflict.reasons,
            (qualifier.CurrentAnnualRevenueOperatingIncomeReason.
             SOURCE_CIK_CONFLICT,),
        )

    def test_selected_observation_partition_and_supporting_metadata_are_exact(self):
        result = self.qualify(self.profile_for(duplicate_same_value_payload()))
        operating_ids = result.selected_revenue_observation_ids
        income_ids = result.selected_operating_income_observation_ids
        self.assertEqual(operating_ids, tuple(sorted(set(operating_ids))))
        self.assertEqual(income_ids, tuple(sorted(set(income_ids))))
        self.assertFalse(set(operating_ids) & set(income_ids))
        flattened_operating = tuple(sorted(
            item for filing in result.supporting_filings
            for item in filing.revenue_observation_ids
        ))
        flattened_income = tuple(sorted(
            item for filing in result.supporting_filings
            for item in filing.operating_income_observation_ids
        ))
        self.assertEqual(flattened_operating, operating_ids)
        self.assertEqual(flattened_income, income_ids)
        self.assertEqual(
            tuple(filing.accession for filing in result.supporting_filings),
            result.supporting_accessions,
        )
        for filing in result.supporting_filings:
            self.assertEqual(len(filing.forms), 1)
            self.assertEqual(len(filing.filed_dates), 1)
            self.assertEqual(len(filing.fiscal_years), 1)

    def test_source_evidence_order_and_decimal_lexical_forms_do_not_change_semantics(self):
        payload = duplicate_same_value_payload()
        normal = self.qualify(self.profile_for(payload))
        reordered = duplicate_same_value_payload()
        facts = reordered["facts"]["us-gaap"]
        for concept in (
            extraction.REVENUE_CONCEPT,
            extraction.OPERATING_INCOME_CONCEPT,
        ):
            facts[concept]["units"]["USD"].reverse()
        reordered_result = self.qualify(self.profile_for(reordered))
        self.assertIs(normal.status, reordered_result.status)
        self.assertEqual(normal.reasons, reordered_result.reasons)
        self.assertEqual(
            normal.revenue,
            reordered_result.revenue,
        )
        self.assertEqual(normal.operating_income, reordered_result.operating_income)
        self.assertEqual(
            normal.supporting_accessions,
            reordered_result.supporting_accessions,
        )
        reversed_evidence = replace(
            normal,
            selected_revenue_observation_ids=tuple(
                reversed(normal.selected_revenue_observation_ids)
            ),
            selected_operating_income_observation_ids=tuple(
                reversed(normal.selected_operating_income_observation_ids)
            ),
        )
        self.assertEqual(normal.semantic_id, reversed_evidence.semantic_id)
        lexical = replace(
            normal,
            revenue=Decimal("250000000.000"),
            operating_income=Decimal("2.00000000E+8"),
        )
        self.assertEqual(normal.semantic_id, lexical.semantic_id)

    def test_exact_base_ten_precision_is_never_binary_float(self):
        precise = "250000000.12345678901234567890123456789"
        content = raw(coherent_pair_payload()).replace(
            str(REVENUE_VALUE).encode(), precise.encode(), 1
        )
        extracted = self.extract(coherent_pair_payload(), content=content)
        observation = next(
            item for item in extracted.observations
            if item.concept == extraction.REVENUE_CONCEPT
        )
        self.assertEqual(observation.value, Decimal(precise))
        self.assertIs(type(observation.value), Decimal)

    def test_genuine_factory_recapture_preserves_semantics_and_changes_evidence(self):
        first = self.qualify()
        recapture_fixture = comparability_tests.SecCurrentEPSComparabilityTests(
            methodName="runTest"
        )
        recapture_fixture.setUp()
        self.addCleanup(recapture_fixture.doCleanups)
        _, recaptured_profile = capture_profile(
            recapture_fixture,
            reverse=True,
            captured_at=BOUNDARY_T1,
        )
        recaptured = qualifier.qualify_sec_current_annual_revenue_operating_income(
            recapture_fixture.current_archive,
            recaptured_profile,
        )
        self.assertEqual(first.revenue, recaptured.revenue)
        self.assertEqual(first.operating_income, recaptured.operating_income)
        self.assertEqual(first.source_cik, recaptured.source_cik)
        self.assertEqual(first.period_start, recaptured.period_start)
        self.assertEqual(first.period_end, recaptured.period_end)
        self.assertEqual(first.semantic_id, recaptured.semantic_id)
        self.assertNotEqual(first.evidence_id, recaptured.evidence_id)
        self.assertNotEqual(first.capture_receipt_id, recaptured.capture_receipt_id)
        self.assertNotEqual(first.source_object_hash, recaptured.source_object_hash)

    def test_later_current_capture_changes_route_evidence_not_semantics(self):
        first = self.qualify()
        later_fixture = comparability_tests.SecCurrentEPSComparabilityTests(
            methodName="runTest"
        )
        later_fixture.setUp()
        self.addCleanup(later_fixture.doCleanups)
        _, later_profile = capture_profile(
            later_fixture,
            captured_at=BOUNDARY_T2,
        )
        later = qualifier.qualify_sec_current_annual_revenue_operating_income(
            later_fixture.current_archive,
            later_profile,
        )
        self.assertNotEqual(first.route_local_issuer_key, later.route_local_issuer_key)
        self.assertNotEqual(first.route_local_security_key, later.route_local_security_key)
        self.assertEqual(first.semantic_id, later.semantic_id)
        self.assertNotEqual(first.evidence_id, later.evidence_id)
        self.assertEqual(later.route_local_issuer_key,
                         later_profile.upstream_comparability.route_local_issuer_key)
        self.assertEqual(later.route_local_security_key,
                         later_profile.upstream_comparability.route_local_security_key)

    def test_semantic_identity_binds_economics_not_margin_only(self):
        first = self.qualify(self.profile_for(companyfacts_payload(
            revenue_rows=[financial_row(100)],
            operating_income_rows=[financial_row(20)],
        )))
        same_margin = self.qualify(self.profile_for(companyfacts_payload(
            revenue_rows=[financial_row(200)],
            operating_income_rows=[financial_row(40)],
        )))
        self.assertNotEqual(first.semantic_id, same_margin.semantic_id)
        changed = (
            replace(first, source_cik="0000000001"),
            replace(first, period_start="2023-01-01", period_end="2023-12-31"),
            replace(first, revenue=Decimal("101")),
            replace(first, operating_income=Decimal("21")),
        )
        for result in changed:
            with self.subTest(result=result):
                self.assertNotEqual(first.semantic_id, result.semantic_id)

    def test_route_context_state_is_stable_but_mixed_state_is_rejected(self):
        present = self.qualify()
        changed_keys = replace(
            present,
            route_local_issuer_key="0" * 64,
            route_local_security_key="1" * 64,
        )
        absent = replace(
            present,
            route_local_issuer_key=None,
            route_local_security_key=None,
        )
        mixed = replace(present, route_local_issuer_key=None)
        self.assertEqual(present.semantic_id, changed_keys.semantic_id)
        self.assertNotEqual(present.evidence_id, changed_keys.evidence_id)
        self.assertNotEqual(present.semantic_id, absent.semantic_id)
        with self.assertRaises(qualifier.CurrentAnnualRevenueOperatingIncomeError):
            _ = mixed.semantic_id

    def test_result_serialization_identity_and_reasons_are_deterministic(self):
        result = self.qualify()
        self.assertEqual(result.semantic_id, result.semantic_id)
        self.assertEqual(result.evidence_id, result.evidence_id)
        self.assertEqual(result.to_dict(), result.to_dict())
        json.dumps(result.to_dict(), sort_keys=True)
        self.assertEqual(result.reasons, tuple(sorted(
            set(result.reasons), key=lambda item: item.value
        )))
        with self.assertRaises(FrozenInstanceError):
            result.revenue = Decimal(1)
        with self.assertRaises(FrozenInstanceError):
            result.supporting_filings[0].accession = SECOND_ACCESSION

    def test_current_only_authority_and_closed_limitations_are_pinned(self):
        result = self.qualify()
        self.assertEqual(result.authority, "QUALITY_PROFITABILITY_EVIDENCE_ONLY")
        self.assertEqual(
            result.limitations,
            tuple(qualifier.CurrentAnnualRevenueOperatingIncomeLimitation),
        )
        values = {item.value for item in result.limitations}
        for required in (
            "NO_OPERATING_MARGIN",
            "NO_GOOD_OR_BAD_PROFITABILITY",
            "NO_AGGREGATE_QUALITY_SCORE_GRADE_OR_WEIGHT",
            "NO_PROFITABILITY_QUALITY_CONCLUSION",
            "NO_HISTORICAL_AS_OF_OR_PIT_AUTHORITY",
            "NO_EXECUTION_PRODUCTION_DEPLOYMENT_OR_V2_PROMOTION_AUTHORITY",
        ):
            self.assertIn(required, values)

    def test_controlled_replay_has_no_network_or_provider_acquisition(self):
        with patch.object(
            socket.socket, "connect", side_effect=AssertionError("network")
        ), patch.object(
            socket, "getaddrinfo", side_effect=AssertionError("network")
        ):
            self.assertIs(
                self.qualify().status,
                qualifier.CurrentAnnualRevenueOperatingIncomeStatus.
                PAIRED_REVENUE_OPERATING_INCOME_ESTABLISHED,
            )

    def test_static_imports_and_dependency_boundaries_are_closed(self):
        allowed = {
            "dataclasses", "datetime", "decimal", "enum", "hashlib", "json", "re",
            "economic_facts",
            "economic_facts.sec_archive",
            "economic_facts.sec_current_eps_comparability_qualification",
            "economic_facts.sec_eps_series",
            "economic_facts.sec_revenue_operating_income",
            "economic_facts.sec_ordinary_compounder_profile",
        }
        for module in (extraction, qualifier):
            source = Path(module.__file__).read_text()
            tree = ast.parse(source)
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    self.assertTrue(all(alias.name in allowed for alias in node.names))
                elif isinstance(node, ast.ImportFrom):
                    name = node.module
                    if node.level:
                        name = "economic_facts." + (name or "")
                    self.assertIn(name.rstrip("."), allowed)
                elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                    self.assertNotIn(node.func.id, {"eval", "exec", "__import__", "compile"})
            for token in (
                "requests", "urllib", "sec_acquisition", "expected_return_engine",
                "portfolio", "execution_instruction", "cash_conversion_ratio",
                "quality_score", "analysis_capabilities",
            ):
                self.assertNotIn(token, source)

    def test_model_rules_and_protected_fingerprints_remain_pinned(self):
        checkout = Path(__file__).resolve().parents[1]
        self.assertIn(
            'MODEL_RULES_VERSION = "2026-08-23-allocation-room-integrity-v7"',
            (checkout / "src" / "model_version.py").read_text(),
        )
        self.assertIn(
            "f1e73b27b80e41d96ff5e0fe990b482bad71b7220db0b5bd6a2f470d72786166",
            (checkout / "tests" / "test_pit_adapter_equivalence.py").read_text(),
        )
        self.assertIn(
            "f8457910665391e39c234274cae4c029802c681211eebc7dba986a63000876f1",
            (checkout / "tests" / "test_pit_comparison.py").read_text(),
        )


if __name__ == "__main__":
    unittest.main()
