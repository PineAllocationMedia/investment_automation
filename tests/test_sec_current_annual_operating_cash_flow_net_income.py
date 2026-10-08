"""Adversarial tests for paired CURRENT annual OCF and net income."""
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

from economic_facts import sec_current_annual_operating_cash_flow_net_income as qualifier
from economic_facts import sec_operating_cash_flow_net_income as extraction
from economic_facts import sec_ordinary_compounder_profile as profile_module
from economic_facts.sec_archive import ArchiveError, SecArchive
from tests import test_sec_current_eps_comparability_qualification as comparability_tests
from tests.sec_filing_fixtures import raw
from tests.sec_operating_cash_flow_net_income_fixtures import (
    LATEST_ACCESSION,
    NET_INCOME_VALUE,
    OPERATING_CASH_FLOW_VALUE,
    SECOND_ACCESSION,
    capture_profile,
    coherent_pair_payload,
    companyfacts_payload,
    conflicting_net_income_payload,
    conflicting_operating_cash_flow_payload,
    duplicate_same_value_payload,
    financial_row,
    mismatched_period_payload,
    missing_net_income_payload,
    missing_operating_cash_flow_payload,
    no_common_accession_payload,
    orphan_operating_cash_flow_conflict_payload,
    wrong_unit_payload,
)
from tests.sec_property4_temporal_boundary_fixtures import BOUNDARY_T1
from tests.sec_property4_temporal_fixtures import CIK


class SecCurrentAnnualOperatingCashFlowNetIncomeTests(unittest.TestCase):
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
            expected_comparability_evidence_id="0" * 64,
        )

    @classmethod
    def tearDownClass(cls):
        cls.fixture.doCleanups()

    def qualify(self, profile=None, archive=None):
        return qualifier.qualify_sec_current_annual_operating_cash_flow_net_income(
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
            return extraction.extract_operating_cash_flow_net_income(
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
                            qualifier.CurrentAnnualOperatingCashFlowNetIncomeError
                        ):
                    qualifier.qualify_sec_current_annual_operating_cash_flow_net_income(
                        archive, profile
                    )

    def test_coherent_pair_establishes_exact_decimal_facts_only(self):
        result = self.qualify()
        self.assertIs(
            result.status,
            qualifier.CurrentAnnualOperatingCashFlowNetIncomeStatus.
            PAIRED_OPERATING_CASH_FLOW_NET_INCOME_ESTABLISHED,
        )
        self.assertEqual(result.period_start, "2024-01-01")
        self.assertEqual(result.period_end, "2024-12-31")
        self.assertEqual(result.operating_cash_flow, Decimal(OPERATING_CASH_FLOW_VALUE))
        self.assertEqual(result.net_income, Decimal(NET_INCOME_VALUE))
        self.assertIs(type(result.operating_cash_flow), Decimal)
        self.assertIs(type(result.net_income), Decimal)
        self.assertEqual(result.supporting_accessions, (LATEST_ACCESSION,))
        for forbidden in (
            "ratio", "percentage", "cash_conversion", "quality_score",
            "grade", "threshold", "recommendation", "allocation",
        ):
            self.assertNotIn(forbidden, result.to_dict()[
                "current_annual_operating_cash_flow_net_income"
            ])

    def test_profile_capability_states_project_exactly_without_partial_values(self):
        cases = (
            (
                self.unavailable,
                qualifier.CurrentAnnualOperatingCashFlowNetIncomeStatus.
                EVIDENCE_UNAVAILABLE,
                qualifier.CurrentAnnualOperatingCashFlowNetIncomeReason.
                UPSTREAM_PROFILE_UNAVAILABLE,
            ),
            (
                self.unsupported,
                qualifier.CurrentAnnualOperatingCashFlowNetIncomeStatus.
                EVIDENCE_UNSUPPORTED,
                qualifier.CurrentAnnualOperatingCashFlowNetIncomeReason.
                UPSTREAM_PROFILE_UNSUPPORTED,
            ),
            (
                self.source_conflict,
                qualifier.CurrentAnnualOperatingCashFlowNetIncomeStatus.SOURCE_CONFLICT,
                qualifier.CurrentAnnualOperatingCashFlowNetIncomeReason.
                UPSTREAM_SOURCE_CONFLICT,
            ),
        )
        for profile, status, reason in cases:
            with self.subTest(status=status):
                result = self.qualify(profile)
                self.assertIs(result.status, status)
                self.assertEqual(result.reasons, (reason,))
                self.assertIsNone(result.operating_cash_flow)
                self.assertIsNone(result.net_income)
                self.assertEqual(result.selected_operating_cash_flow_observation_ids, ())
                self.assertEqual(result.selected_net_income_observation_ids, ())
                self.assertEqual(result.supporting_accessions, ())
                self.assertEqual(result.supporting_filings, ())

    def test_genuine_replay_conflict_is_authenticated_and_projected(self):
        self.assertIs(
            self.source_conflict.status,
            profile_module.OrdinaryCompounderProfileStatus.SOURCE_CONFLICT,
        )
        self.assertEqual(
            self.source_conflict.reasons,
            (profile_module.ProfileReason.REPLAY_IDENTITY_MISMATCH,),
        )
        self.assertEqual(
            self.source_conflict.expected_comparability_semantic_id,
            self.source_conflict.upstream_comparability.semantic_id,
        )
        self.assertNotEqual(
            self.source_conflict.expected_comparability_evidence_id,
            self.source_conflict.upstream_comparability.evidence_id,
        )
        result = self.qualify(self.source_conflict)
        self.assertIs(
            result.status,
            qualifier.CurrentAnnualOperatingCashFlowNetIncomeStatus.SOURCE_CONFLICT,
        )

    def test_fabricated_replay_conflict_is_rejected(self):
        fabricated = replace(
            self.available,
            status=profile_module.OrdinaryCompounderProfileStatus.SOURCE_CONFLICT,
            profile=None,
            reasons=(profile_module.ProfileReason.REPLAY_IDENTITY_MISMATCH,),
        )
        self.assertEqual(
            fabricated.expected_comparability_semantic_id,
            fabricated.upstream_comparability.semantic_id,
        )
        self.assertEqual(
            fabricated.expected_comparability_evidence_id,
            fabricated.upstream_comparability.evidence_id,
        )
        with self.assertRaises(
            qualifier.CurrentAnnualOperatingCashFlowNetIncomeError
        ):
            self.qualify(fabricated)

    def test_expected_replay_mutation_without_state_update_is_rejected(self):
        mutated = replace(
            self.available,
            expected_comparability_semantic_id="0" * 64,
        )
        with self.assertRaises(
            qualifier.CurrentAnnualOperatingCashFlowNetIncomeError
        ):
            self.qualify(mutated)

    def test_v1_profile_contract_is_rejected(self):
        old = replace(
            self.available,
            contract_version=(
                "2026-09-29-sec-ordinary-compounder-method-profile-v1"
            ),
        )
        with self.assertRaises(
            qualifier.CurrentAnnualOperatingCashFlowNetIncomeError
        ):
            self.qualify(old)

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
                qualifier.CurrentAnnualOperatingCashFlowNetIncomeError
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
                qualifier.CurrentAnnualOperatingCashFlowNetIncomeStatus.
                EVIDENCE_UNAVAILABLE,
                qualifier.CurrentAnnualOperatingCashFlowNetIncomeReason.
                UPSTREAM_PROFILE_UNAVAILABLE,
            ),
            profile_module.OrdinaryCompounderProfileStatus.PROFILE_UNSUPPORTED: (
                qualifier.CurrentAnnualOperatingCashFlowNetIncomeStatus.
                EVIDENCE_UNSUPPORTED,
                qualifier.CurrentAnnualOperatingCashFlowNetIncomeReason.
                UPSTREAM_PROFILE_UNSUPPORTED,
            ),
            profile_module.OrdinaryCompounderProfileStatus.SOURCE_CONFLICT: (
                qualifier.CurrentAnnualOperatingCashFlowNetIncomeStatus.SOURCE_CONFLICT,
                qualifier.CurrentAnnualOperatingCashFlowNetIncomeReason.
                UPSTREAM_SOURCE_CONFLICT,
            ),
        }
        expected_status, expected_reason = projected[profile.status]
        self.assertIs(result.status, expected_status)
        self.assertEqual(result.reasons, (expected_reason,))
        self.assertIsNone(result.operating_cash_flow)
        self.assertIsNone(result.net_income)
        self.assertEqual(result.selected_operating_cash_flow_observation_ids, ())
        self.assertEqual(result.selected_net_income_observation_ids, ())
        self.assertEqual(result.supporting_accessions, ())
        self.assertEqual(result.supporting_filings, ())

        for invalid_sic in ("10000", 10000.0, True):
            with self.subTest(invalid_sic=invalid_sic), self.assertRaises(
                qualifier.CurrentAnnualOperatingCashFlowNetIncomeError
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
                qualifier.CurrentAnnualOperatingCashFlowNetIncomeError
            ):
                self.qualify(profile)

    def test_extraction_preserves_exact_source_row_and_capture_semantics(self):
        observation = next(
            item for item in self.extract(coherent_pair_payload()).observations
            if item.concept == extraction.OPERATING_CASH_FLOW_CONCEPT
        )
        original = financial_row(OPERATING_CASH_FLOW_VALUE)
        self.assertEqual(observation.source_cik, CIK)
        self.assertEqual(observation.namespace, "us-gaap")
        self.assertEqual(observation.unit, "USD")
        self.assertEqual(observation.value, Decimal(OPERATING_CASH_FLOW_VALUE))
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

    def test_only_exact_concepts_namespace_and_usd_unit_are_admissible(self):
        substitutes = (
            ("operating_cash_flow_concept", "FreeCashFlow"),
            ("operating_cash_flow_concept", "NetCashProvidedByOperatingActivities"),
            ("net_income_concept", "ProfitLoss"),
            ("net_income_concept", "AdjustedNetIncome"),
            ("net_income_concept", "EBITDA"),
        )
        for key, concept in substitutes:
            result = self.qualify(self.profile_for(companyfacts_payload(**{key: concept})))
            with self.subTest(concept=concept):
                self.assertIs(
                    result.status,
                    qualifier.CurrentAnnualOperatingCashFlowNetIncomeStatus.
                    EVIDENCE_UNAVAILABLE,
                )
                self.assertIsNone(result.operating_cash_flow)
                self.assertIsNone(result.net_income)
        issuer_extension = companyfacts_payload(
            namespace="fiction",
            operating_cash_flow_concept="FictionOperatingCashFlow",
            net_income_concept="FictionNetIncome",
        )
        result = self.qualify(self.profile_for(issuer_extension))
        self.assertIs(
            result.status,
            qualifier.CurrentAnnualOperatingCashFlowNetIncomeStatus.EVIDENCE_UNAVAILABLE,
        )
        wrong_unit = self.qualify(self.profile_for(wrong_unit_payload()))
        self.assertEqual(
            wrong_unit.reasons,
            (qualifier.CurrentAnnualOperatingCashFlowNetIncomeReason.
             EXACT_USD_UNIT_UNAVAILABLE,),
        )
        missing_unit_payload = coherent_pair_payload()
        missing_unit_payload["facts"]["us-gaap"][
            extraction.OPERATING_CASH_FLOW_CONCEPT
        ]["units"] = {}
        missing_unit = self.qualify(self.profile_for(missing_unit_payload))
        self.assertEqual(
            missing_unit.reasons,
            (qualifier.CurrentAnnualOperatingCashFlowNetIncomeReason.
             EXACT_USD_UNIT_UNAVAILABLE,),
        )

    def test_missing_concepts_are_unavailable_and_never_zero(self):
        cases = (
            (
                missing_operating_cash_flow_payload(),
                qualifier.CurrentAnnualOperatingCashFlowNetIncomeReason.
                OPERATING_CASH_FLOW_UNAVAILABLE,
            ),
            (
                missing_net_income_payload(),
                qualifier.CurrentAnnualOperatingCashFlowNetIncomeReason.
                NET_INCOME_UNAVAILABLE,
            ),
        )
        for payload, reason in cases:
            result = self.qualify(self.profile_for(payload))
            with self.subTest(reason=reason):
                self.assertIs(
                    result.status,
                    qualifier.CurrentAnnualOperatingCashFlowNetIncomeStatus.
                    EVIDENCE_UNAVAILABLE,
                )
                self.assertIn(reason, result.reasons)
                self.assertIsNone(result.operating_cash_flow)
                self.assertIsNone(result.net_income)

    def test_zero_and_negative_values_are_legitimate_exact_facts(self):
        cases = ((0, 0), (-1, 2), (3, -4), (-5, -6))
        for operating_value, income_value in cases:
            payload = companyfacts_payload(
                operating_cash_flow_rows=[financial_row(operating_value)],
                net_income_rows=[financial_row(income_value)],
            )
            result = self.qualify(self.profile_for(payload))
            with self.subTest(values=(operating_value, income_value)):
                self.assertIs(
                    result.status,
                    qualifier.CurrentAnnualOperatingCashFlowNetIncomeStatus.
                    PAIRED_OPERATING_CASH_FLOW_NET_INCOME_ESTABLISHED,
                )
                self.assertEqual(result.operating_cash_flow, Decimal(operating_value))
                self.assertEqual(result.net_income, Decimal(income_value))

    def test_nonfinite_and_invalid_values_cannot_establish(self):
        payload = companyfacts_payload(
            operating_cash_flow_rows=[financial_row("NaN")],
            net_income_rows=[financial_row(NET_INCOME_VALUE)],
        )
        result = self.qualify(self.profile_for(payload))
        self.assertEqual(
            result.reasons,
            (qualifier.CurrentAnnualOperatingCashFlowNetIncomeReason.
             FINITE_OPERATING_CASH_FLOW_VALUE_UNAVAILABLE,),
        )
        nonfinite = raw(coherent_pair_payload()).replace(
            str(OPERATING_CASH_FLOW_VALUE).encode(), b"NaN", 1
        )
        with self.assertRaises(ArchiveError):
            self.extract(coherent_pair_payload(), content=nonfinite)

    def test_exact_annual_period_and_presentation_are_required(self):
        payloads = (
            mismatched_period_payload(),
            companyfacts_payload(
                operating_cash_flow_rows=[financial_row(
                    OPERATING_CASH_FLOW_VALUE, fp="Q4", form="10-Q"
                )],
                net_income_rows=[financial_row(
                    NET_INCOME_VALUE, fp="Q4", form="10-Q"
                )],
            ),
            companyfacts_payload(
                operating_cash_flow_rows=[financial_row(
                    OPERATING_CASH_FLOW_VALUE, start=None
                )],
                net_income_rows=[financial_row(NET_INCOME_VALUE, start=None)],
            ),
        )
        for payload in payloads:
            result = self.qualify(self.profile_for(payload))
            with self.subTest(payload=payload):
                self.assertIs(
                    result.status,
                    qualifier.CurrentAnnualOperatingCashFlowNetIncomeStatus.
                    EVIDENCE_UNAVAILABLE,
                )
                self.assertIn(
                    qualifier.CurrentAnnualOperatingCashFlowNetIncomeReason.
                    EXACT_ANNUAL_PERIOD_PRESENTATION_UNAVAILABLE,
                    result.reasons,
                )

    def test_common_accession_required_and_orphan_does_not_poison_pair(self):
        unavailable = self.qualify(self.profile_for(no_common_accession_payload()))
        self.assertEqual(
            unavailable.reasons,
            (qualifier.CurrentAnnualOperatingCashFlowNetIncomeReason.
             NO_COMMON_ANNUAL_FILING_ACCESSION,),
        )
        established = self.qualify(
            self.profile_for(orphan_operating_cash_flow_conflict_payload())
        )
        self.assertIs(
            established.status,
            qualifier.CurrentAnnualOperatingCashFlowNetIncomeStatus.
            PAIRED_OPERATING_CASH_FLOW_NET_INCOME_ESTABLISHED,
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
                conflicting_operating_cash_flow_payload(),
                qualifier.CurrentAnnualOperatingCashFlowNetIncomeReason.
                COMPETING_OPERATING_CASH_FLOW_VALUES,
            ),
            (
                conflicting_net_income_payload(),
                qualifier.CurrentAnnualOperatingCashFlowNetIncomeReason.
                COMPETING_NET_INCOME_VALUES,
            ),
        )
        for payload, reason in cases:
            result = self.qualify(self.profile_for(payload))
            with self.subTest(reason=reason):
                self.assertIs(
                    result.status,
                    qualifier.CurrentAnnualOperatingCashFlowNetIncomeStatus.
                    SOURCE_CONFLICT,
                )
                self.assertIn(reason, result.reasons)
                self.assertIsNone(result.operating_cash_flow)
                self.assertIsNone(result.net_income)

    def test_common_accession_metadata_must_be_coherent_but_frame_may_differ(self):
        for field, replacement in (
            ("form", "10-K/A"),
            ("filed", "2025-02-02"),
            ("fy", 2025),
        ):
            operating = financial_row(OPERATING_CASH_FLOW_VALUE)
            income = financial_row(NET_INCOME_VALUE, **{field: replacement})
            result = self.qualify(self.profile_for(companyfacts_payload(
                operating_cash_flow_rows=[operating],
                net_income_rows=[income],
            )))
            with self.subTest(field=field):
                self.assertEqual(
                    result.reasons,
                    (qualifier.CurrentAnnualOperatingCashFlowNetIncomeReason.
                     COMMON_FILING_METADATA_CONFLICT,),
                )
        frame_difference = self.qualify(self.profile_for(companyfacts_payload(
            operating_cash_flow_rows=[financial_row(
                OPERATING_CASH_FLOW_VALUE, frame="CY2024"
            )],
            net_income_rows=[financial_row(
                NET_INCOME_VALUE, frame="CY2024Q4"
            )],
        )))
        self.assertIs(
            frame_difference.status,
            qualifier.CurrentAnnualOperatingCashFlowNetIncomeStatus.
            PAIRED_OPERATING_CASH_FLOW_NET_INCOME_ESTABLISHED,
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
            qualifier.CurrentAnnualOperatingCashFlowNetIncomeError
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
            (qualifier.CurrentAnnualOperatingCashFlowNetIncomeReason.
             CANONICAL_ROUTE_IDENTITY_CONFLICT,),
        )

        with tempfile.TemporaryDirectory() as temporary:
            foreign = SecArchive(Path(temporary).resolve() / "foreign")
            replay = self.qualify(archive=foreign)
        self.assertEqual(
            replay.reasons,
            (qualifier.CurrentAnnualOperatingCashFlowNetIncomeReason.
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
            (qualifier.CurrentAnnualOperatingCashFlowNetIncomeReason.
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
            (qualifier.CurrentAnnualOperatingCashFlowNetIncomeReason.
             CAPTURE_REPLAY_CONFLICT,),
        )
        extracted = extraction.OperatingCashFlowNetIncomeExtraction(
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
            "extract_operating_cash_flow_net_income",
            return_value=extracted,
        ):
            cik_conflict = self.qualify()
        self.assertEqual(
            cik_conflict.reasons,
            (qualifier.CurrentAnnualOperatingCashFlowNetIncomeReason.
             SOURCE_CIK_CONFLICT,),
        )

    def test_selected_observation_partition_and_supporting_metadata_are_exact(self):
        result = self.qualify(self.profile_for(duplicate_same_value_payload()))
        operating_ids = result.selected_operating_cash_flow_observation_ids
        income_ids = result.selected_net_income_observation_ids
        self.assertEqual(operating_ids, tuple(sorted(set(operating_ids))))
        self.assertEqual(income_ids, tuple(sorted(set(income_ids))))
        self.assertFalse(set(operating_ids) & set(income_ids))
        flattened_operating = tuple(sorted(
            item for filing in result.supporting_filings
            for item in filing.operating_cash_flow_observation_ids
        ))
        flattened_income = tuple(sorted(
            item for filing in result.supporting_filings
            for item in filing.net_income_observation_ids
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
            extraction.OPERATING_CASH_FLOW_CONCEPT,
            extraction.NET_INCOME_CONCEPT,
        ):
            facts[concept]["units"]["USD"].reverse()
        reordered_result = self.qualify(self.profile_for(reordered))
        self.assertIs(normal.status, reordered_result.status)
        self.assertEqual(normal.reasons, reordered_result.reasons)
        self.assertEqual(
            normal.operating_cash_flow,
            reordered_result.operating_cash_flow,
        )
        self.assertEqual(normal.net_income, reordered_result.net_income)
        self.assertEqual(
            normal.supporting_accessions,
            reordered_result.supporting_accessions,
        )
        reversed_evidence = replace(
            normal,
            selected_operating_cash_flow_observation_ids=tuple(
                reversed(normal.selected_operating_cash_flow_observation_ids)
            ),
            selected_net_income_observation_ids=tuple(
                reversed(normal.selected_net_income_observation_ids)
            ),
        )
        self.assertEqual(normal.semantic_id, reversed_evidence.semantic_id)
        lexical = replace(
            normal,
            operating_cash_flow=Decimal("250000000.000"),
            net_income=Decimal("2.00000000E+8"),
        )
        self.assertEqual(normal.semantic_id, lexical.semantic_id)

    def test_exact_base_ten_precision_is_never_binary_float(self):
        precise = "250000000.12345678901234567890123456789"
        content = raw(coherent_pair_payload()).replace(
            str(OPERATING_CASH_FLOW_VALUE).encode(), precise.encode(), 1
        )
        extracted = self.extract(coherent_pair_payload(), content=content)
        observation = next(
            item for item in extracted.observations
            if item.concept == extraction.OPERATING_CASH_FLOW_CONCEPT
        )
        self.assertEqual(observation.value, Decimal(precise))
        self.assertIs(type(observation.value), Decimal)

    def test_legitimate_recapture_preserves_semantics_and_changes_evidence(self):
        first = self.qualify()
        second = replace(
            first,
            upstream_profile_evidence_id="f" * 64,
            upstream_comparability_evidence_id="e" * 64,
            capture_receipt_id="d" * 64,
            source_object_hash="c" * 64,
            captured_at="2025-03-02T12:00:00Z",
            selected_operating_cash_flow_observation_ids=("b" * 64,),
            selected_net_income_observation_ids=("a" * 64,),
        )
        self.assertEqual(first.semantic_id, second.semantic_id)
        self.assertNotEqual(first.evidence_id, second.evidence_id)

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
            result.operating_cash_flow = Decimal(1)
        with self.assertRaises(FrozenInstanceError):
            result.supporting_filings[0].accession = SECOND_ACCESSION

    def test_current_only_authority_and_closed_limitations_are_pinned(self):
        result = self.qualify()
        self.assertEqual(result.authority, "QUALITY_CASH_CONVERSION_EVIDENCE_ONLY")
        self.assertEqual(
            result.limitations,
            tuple(qualifier.CurrentAnnualOperatingCashFlowNetIncomeLimitation),
        )
        values = {item.value for item in result.limitations}
        for required in (
            "NO_CASH_CONVERSION_RATIO_OR_DIAGNOSTIC",
            "NO_FREE_CASH_FLOW_CLAIM",
            "NO_ACCRUALS_QUALITY_CONCLUSION",
            "NO_PROFITABILITY_QUALITY_CONCLUSION",
            "NO_HISTORICAL_AS_OF_OR_PIT_AUTHORITY",
            "NO_EXECUTION_PRODUCTION_OR_V2_PROMOTION_AUTHORITY",
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
                qualifier.CurrentAnnualOperatingCashFlowNetIncomeStatus.
                PAIRED_OPERATING_CASH_FLOW_NET_INCOME_ESTABLISHED,
            )

    def test_static_imports_and_dependency_boundaries_are_closed(self):
        allowed = {
            "dataclasses", "datetime", "decimal", "enum", "hashlib", "json", "re",
            "economic_facts",
            "economic_facts.sec_archive",
            "economic_facts.sec_current_eps_comparability_qualification",
            "economic_facts.sec_eps_series",
            "economic_facts.sec_operating_cash_flow_net_income",
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
