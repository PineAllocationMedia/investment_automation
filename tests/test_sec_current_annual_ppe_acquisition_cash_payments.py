"""Adversarial tests for CURRENT annual PP&E acquisition cash payments."""
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

from economic_facts import sec_current_annual_ppe_acquisition_cash_payments as qualifier
from economic_facts import sec_ppe_acquisition_cash_payments as extraction
from economic_facts import sec_ordinary_compounder_profile as profile_module
from economic_facts.sec_archive import ArchiveError, SecArchive
from tests import test_sec_current_eps_comparability_qualification as comparability_tests
from tests import test_sec_ordinary_compounder_profile as profile_tests
from tests.sec_current_security_eps_qualification_fixtures import (
    VALUES,
    companyfacts_rows,
)
from tests.sec_filing_fixtures import raw
from tests.sec_five_year_eps_presentation_fixtures import five_year_table
from tests.sec_ppe_acquisition_cash_payments_fixtures import (
    LATEST_ACCESSION,
    PPE_ACQUISITION_CASH_PAYMENTS_VALUE,
    SECOND_ACCESSION,
    capture_profile,
    coherent_payload,
    companyfacts_payload,
    conflicting_values_payload,
    duplicate_same_value_payload,
    financial_row,
    mismatched_period_payload,
    missing_payload,
    wrong_unit_payload,
)
from tests.sec_property4_temporal_boundary_fixtures import BOUNDARY_T1
from tests.sec_property4_temporal_fixtures import CIK


class SecCurrentAnnualPPEAcquisitionCashPaymentsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = comparability_tests.SecCurrentEPSComparabilityTests(
            methodName="runTest"
        )
        cls.fixture.setUp()
        cls.receipt, cls.available = capture_profile(cls.fixture)
        _, cls.unavailable = capture_profile(
            cls.fixture, sic=None, description=None
        )
        _, cls.unsupported = capture_profile(
            cls.fixture, sic=6021, description="National Commercial Banks"
        )
        _, cls.source_conflict = capture_profile(
            cls.fixture, expected_comparability_evidence_id="0" * 64
        )

    @classmethod
    def tearDownClass(cls):
        cls.fixture.doCleanups()

    def qualify(self, profile=None, archive=None):
        return (
            qualifier.
            qualify_sec_current_annual_ppe_acquisition_cash_payments(
                self.fixture.current_archive if archive is None else archive,
                self.available if profile is None else profile,
            )
        )

    def profile_for(self, payload, *, reverse=False, captured_at=BOUNDARY_T1):
        return capture_profile(
            self.fixture,
            payload,
            reverse=reverse,
            captured_at=captured_at,
        )[1]

    @staticmethod
    def replace_decision(profile, structure, **changes):
        return replace(
            profile,
            decisions=tuple(
                replace(item, **changes) if item.profile is structure else item
                for item in profile.decisions
            ),
        )

    def extract(self, payload, *, content=None):
        with tempfile.TemporaryDirectory() as temporary:
            archive = SecArchive(Path(temporary).resolve() / "archive")
            receipt = archive._capture_live(
                raw(payload) if content is None else content,
                cik=CIK,
                captured_at=BOUNDARY_T1,
            )
            return extraction.extract_ppe_acquisition_cash_payments(
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
                (
                    self.fixture.current_archive,
                    self.available.upstream_comparability,
                ),
            )
            for archive, profile in cases:
                with self.subTest(types=(type(archive), type(profile))),                         self.assertRaises(
                            qualifier.
                            CurrentAnnualPPEAcquisitionCashPaymentsError
                        ):
                    (
                        qualifier.
                        qualify_sec_current_annual_ppe_acquisition_cash_payments(
                            archive, profile
                        )
                    )

    def test_establishes_exact_reported_value_without_analysis(self):
        self.assertIs(
            self.available.status,
            profile_module.OrdinaryCompounderProfileStatus.
            ORDINARY_COMPOUNDER_PROFILE_ESTABLISHED,
        )
        result = self.qualify()
        self.assertIs(
            result.status,
            qualifier.CurrentAnnualPPEAcquisitionCashPaymentsStatus.
            PPE_ACQUISITION_CASH_PAYMENTS_ESTABLISHED,
        )
        self.assertEqual(result.period_start, "2024-01-01")
        self.assertEqual(result.period_end, "2024-12-31")
        self.assertEqual(
            result.ppe_acquisition_cash_payments,
            Decimal(PPE_ACQUISITION_CASH_PAYMENTS_VALUE),
        )
        self.assertIs(type(result.ppe_acquisition_cash_payments), Decimal)
        self.assertEqual(result.supporting_accessions, (LATEST_ACCESSION,))
        payload = result.to_dict()[
            "current_annual_ppe_acquisition_cash_payments"
        ]
        for forbidden in (
            "free_cash_flow", "owner_earnings", "ratio", "percentage",
            "maintenance_capex", "growth_capex", "quality_score",
            "grade", "recommendation", "allocation",
        ):
            self.assertNotIn(forbidden, payload)

    def test_native_upstream_states_project_exactly_without_partial_values(self):
        cases = (
            (
                self.unavailable,
                qualifier.CurrentAnnualPPEAcquisitionCashPaymentsStatus.
                EVIDENCE_UNAVAILABLE,
                qualifier.CurrentAnnualPPEAcquisitionCashPaymentsReason.
                UPSTREAM_PROFILE_UNAVAILABLE,
            ),
            (
                self.unsupported,
                qualifier.CurrentAnnualPPEAcquisitionCashPaymentsStatus.
                EVIDENCE_UNSUPPORTED,
                qualifier.CurrentAnnualPPEAcquisitionCashPaymentsReason.
                UPSTREAM_PROFILE_UNSUPPORTED,
            ),
            (
                self.source_conflict,
                qualifier.CurrentAnnualPPEAcquisitionCashPaymentsStatus.
                SOURCE_CONFLICT,
                qualifier.CurrentAnnualPPEAcquisitionCashPaymentsReason.
                UPSTREAM_SOURCE_CONFLICT,
            ),
        )
        for profile, status, reason in cases:
            result = self.qualify(profile)
            with self.subTest(status=status):
                self.assertIs(result.status, status)
                self.assertEqual(result.reasons, (reason,))
                self.assertIsNone(result.ppe_acquisition_cash_payments)
                self.assertEqual(result.selected_observation_ids, ())
                self.assertEqual(result.supporting_accessions, ())
                self.assertEqual(result.supporting_filings, ())

    def test_pr115_expected_versus_actual_replay_is_authenticated(self):
        self.assertIs(
            self.source_conflict.status,
            profile_module.OrdinaryCompounderProfileStatus.SOURCE_CONFLICT,
        )
        self.assertEqual(
            self.source_conflict.reasons,
            (profile_module.ProfileReason.REPLAY_IDENTITY_MISMATCH,),
        )
        fabricated = replace(
            self.available,
            status=profile_module.OrdinaryCompounderProfileStatus.
            SOURCE_CONFLICT,
            profile=None,
            reasons=(profile_module.ProfileReason.REPLAY_IDENTITY_MISMATCH,),
        )
        with self.assertRaises(
            qualifier.CurrentAnnualPPEAcquisitionCashPaymentsError
        ):
            self.qualify(fabricated)
        mutated = replace(
            self.available, expected_comparability_semantic_id="0" * 64
        )
        with self.assertRaises(
            qualifier.CurrentAnnualPPEAcquisitionCashPaymentsError
        ):
            self.qualify(mutated)

    def test_factory_impossible_upstream_states_are_contract_errors(self):
        impossible = (
            replace(
                self.available,
                status=profile_module.OrdinaryCompounderProfileStatus.
                PROFILE_UNAVAILABLE,
                profile=None,
                reasons=(),
            ),
            replace(
                self.available,
                status=profile_module.OrdinaryCompounderProfileStatus.
                PROFILE_UNSUPPORTED,
                profile=None,
                reasons=(profile_module.ProfileReason.SIC_MISSING_OR_INVALID,),
            ),
            replace(
                self.available,
                status=profile_module.OrdinaryCompounderProfileStatus.
                SOURCE_CONFLICT,
                profile=None,
                reasons=(profile_module.ProfileReason.UNSUPPORTED_SIC_PROFILE,),
            ),
            replace(self.available, status="FUTURE_STATE"),
            replace(self.available, source_cik="0000000001"),
            replace(
                self.available,
                contract_version=(
                    "2026-09-29-sec-ordinary-compounder-method-profile-v1"
                ),
            ),
        )
        for profile in impossible:
            with self.subTest(profile=profile), self.assertRaises(
                qualifier.CurrentAnnualPPEAcquisitionCashPaymentsError
            ):
                self.qualify(profile)

    def test_unsupported_bank_profile_cannot_be_forged_into_established(self):
        bank = next(
            item for item in self.unsupported.decisions
            if item.profile is profile_module.UnsupportedStructure.BANK
        )
        self.assertIs(
            self.unsupported.status,
            profile_module.OrdinaryCompounderProfileStatus.PROFILE_UNSUPPORTED,
        )
        self.assertIs(
            bank.decision,
            profile_module.ProfileDecisionValue.NOT_EXCLUDED,
        )
        forged = self.replace_decision(
            self.unsupported,
            profile_module.UnsupportedStructure.BANK,
            decision=profile_module.ProfileDecisionValue.EXCLUDED,
            reason="SEC_SIC_PROFILE_EXCLUDED:6021:National Commercial Banks",
        )
        forged = replace(
            forged,
            status=(
                profile_module.OrdinaryCompounderProfileStatus.
                ORDINARY_COMPOUNDER_PROFILE_ESTABLISHED
            ),
            profile=profile_module.PROFILE,
            reasons=(),
        )
        with self.assertRaises(
            qualifier.CurrentAnnualPPEAcquisitionCashPaymentsError
        ):
            self.qualify(forged)

    def test_profile_reasons_require_their_exact_factory_conditions(self):
        fabricated = (
            profile_module.ProfileReason.PR5C_NOT_ESTABLISHED,
            profile_module.ProfileReason.SIC_MISSING_OR_INVALID,
            profile_module.ProfileReason.SIC_DESCRIPTION_MISSING_OR_INVALID,
            profile_module.ProfileReason.
            REPORTING_SUBJECT_STABILITY_NOT_ESTABLISHED,
            profile_module.ProfileReason.MIXED_STRUCTURE_UNRESOLVED,
        )
        for reason in fabricated:
            forged = replace(
                self.available,
                status=(
                    profile_module.OrdinaryCompounderProfileStatus.
                    PROFILE_UNAVAILABLE
                ),
                profile=None,
                reasons=(reason,),
            )
            with self.subTest(reason=reason), self.assertRaises(
                qualifier.CurrentAnnualPPEAcquisitionCashPaymentsError
            ):
                self.qualify(forged)

    def test_unsupported_reason_requires_reachable_structural_decision(self):
        forged = replace(
            self.available,
            status=(
                profile_module.OrdinaryCompounderProfileStatus.
                PROFILE_UNSUPPORTED
            ),
            profile=None,
            reasons=(profile_module.ProfileReason.UNSUPPORTED_SIC_PROFILE,),
        )
        self.assertTrue(all(
            item.decision is profile_module.ProfileDecisionValue.EXCLUDED
            for item in forged.decisions
        ))
        with self.assertRaises(
            qualifier.CurrentAnnualPPEAcquisitionCashPaymentsError
        ):
            self.qualify(forged)

    def test_structural_decision_semantics_and_support_are_factory_exact(self):
        cases = (
            self.replace_decision(
                self.available,
                profile_module.UnsupportedStructure.BANK,
                decision=profile_module.ProfileDecisionValue.NOT_EXCLUDED,
            ),
            self.replace_decision(
                self.available,
                profile_module.UnsupportedStructure.REIT,
                reason="SEC_SIC_PROFILE_MATCH:3571:Electronic Computers",
            ),
            self.replace_decision(
                self.available,
                profile_module.UnsupportedStructure.TURNAROUND,
                supporting_semantic_ids=("0" * 64,),
            ),
            self.replace_decision(
                self.available,
                profile_module.UnsupportedStructure.LOSS_MAKING,
                supporting_evidence_ids=("0" * 64,),
            ),
        )
        for profile in cases:
            with self.subTest(profile=profile), self.assertRaises(
                qualifier.CurrentAnnualPPEAcquisitionCashPaymentsError
            ):
                self.qualify(profile)

    def test_genuine_turnaround_loss_and_mixed_states_are_preserved(self):
        factory = profile_tests.OrdinaryCompounderProfileTests(
            methodName="runTest"
        )
        factory.setUp()
        self.addCleanup(factory.doCleanups)
        transition = factory.qualify(
            filings=factory.bridge_fixture.comparability.filings(claims=(
                "Old Fiction was the predecessor, and New Fiction became the successor.",
            )),
        )
        mixed = factory.qualify(
            filings=factory.bridge_fixture.comparability.filings(claims=(
                "These are combined financial statements.",
            )),
        )
        rows = companyfacts_rows()
        for row in rows:
            if row["fy"] == 2024:
                row["val"] = -1
        values = dict(VALUES)
        values[2024] = Decimal("-1")
        loss_making = factory.qualify(
            current=factory.bridge_fixture.comparability.current(rows=rows),
            filings=factory.bridge_fixture.comparability.filings(
                table=five_year_table(values=values),
                value_overrides={2024: Decimal("-1")},
            ),
        )
        archive = factory.bridge_fixture.comparability.current_archive
        cases = (
            (
                transition,
                profile_module.OrdinaryCompounderProfileStatus.PROFILE_UNAVAILABLE,
                profile_module.ProfileReason.
                REPORTING_SUBJECT_STABILITY_NOT_ESTABLISHED,
                qualifier.CurrentAnnualPPEAcquisitionCashPaymentsStatus.
                EVIDENCE_UNAVAILABLE,
            ),
            (
                mixed,
                profile_module.OrdinaryCompounderProfileStatus.PROFILE_UNAVAILABLE,
                profile_module.ProfileReason.MIXED_STRUCTURE_UNRESOLVED,
                qualifier.CurrentAnnualPPEAcquisitionCashPaymentsStatus.
                EVIDENCE_UNAVAILABLE,
            ),
            (
                loss_making,
                profile_module.OrdinaryCompounderProfileStatus.PROFILE_UNSUPPORTED,
                profile_module.ProfileReason.
                POSITIVE_FIVE_PERIOD_ROUTE_NOT_ESTABLISHED,
                qualifier.CurrentAnnualPPEAcquisitionCashPaymentsStatus.
                EVIDENCE_UNSUPPORTED,
            ),
        )
        for profile, upstream_status, upstream_reason, local_status in cases:
            with self.subTest(upstream_status=upstream_status):
                self.assertIs(profile.status, upstream_status)
                self.assertIn(upstream_reason, profile.reasons)
                result = (
                    qualifier.
                    qualify_sec_current_annual_ppe_acquisition_cash_payments(
                        archive,
                        profile,
                    )
                )
                self.assertIs(result.status, local_status)
                self.assertIsNone(result.ppe_acquisition_cash_payments)

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
                qualifier.CurrentAnnualPPEAcquisitionCashPaymentsError
            ):
                self.qualify(profile)

    def test_extraction_preserves_exact_source_row_and_capture_semantics(self):
        observation = self.extract(coherent_payload()).observations[0]
        original = financial_row(PPE_ACQUISITION_CASH_PAYMENTS_VALUE)
        self.assertEqual(observation.source_cik, CIK)
        self.assertEqual(observation.namespace, "us-gaap")
        self.assertEqual(
            observation.concept,
            "PaymentsToAcquirePropertyPlantAndEquipment",
        )
        self.assertEqual(observation.unit, "USD")
        self.assertEqual(
            observation.value, Decimal(PPE_ACQUISITION_CASH_PAYMENTS_VALUE)
        )
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

    def test_only_exact_namespace_concept_and_usd_unit_are_admissible(self):
        for concept in (
            "PaymentsToAcquireProductiveAssets",
            "PropertyPlantAndEquipmentAdditions",
            "CapitalExpenditures",
        ):
            result = self.qualify(self.profile_for(
                companyfacts_payload(concept=concept)
            ))
            with self.subTest(concept=concept):
                self.assertEqual(
                    result.reasons,
                    (
                        qualifier.
                        CurrentAnnualPPEAcquisitionCashPaymentsReason.
                        PPE_ACQUISITION_CASH_PAYMENTS_UNAVAILABLE,
                    ),
                )
        extension = companyfacts_payload(
            namespace="fiction",
            concept="FictionPaymentsToAcquirePPE",
        )
        self.assertIs(
            self.qualify(self.profile_for(extension)).status,
            qualifier.CurrentAnnualPPEAcquisitionCashPaymentsStatus.
            EVIDENCE_UNAVAILABLE,
        )
        wrong_unit = self.qualify(self.profile_for(wrong_unit_payload()))
        self.assertEqual(
            wrong_unit.reasons,
            (
                qualifier.CurrentAnnualPPEAcquisitionCashPaymentsReason.
                EXACT_USD_UNIT_UNAVAILABLE,
            ),
        )
        missing_unit_payload = coherent_payload()
        missing_unit_payload["facts"]["us-gaap"][
            extraction.PPE_ACQUISITION_CASH_PAYMENTS_CONCEPT
        ]["units"] = {}
        missing_unit = self.qualify(self.profile_for(missing_unit_payload))
        self.assertEqual(
            missing_unit.reasons,
            (
                qualifier.CurrentAnnualPPEAcquisitionCashPaymentsReason.
                EXACT_USD_UNIT_UNAVAILABLE,
            ),
        )

    def test_missing_is_unavailable_while_zero_and_negative_are_preserved(self):
        missing = self.qualify(self.profile_for(missing_payload()))
        self.assertEqual(
            missing.reasons,
            (
                qualifier.CurrentAnnualPPEAcquisitionCashPaymentsReason.
                PPE_ACQUISITION_CASH_PAYMENTS_UNAVAILABLE,
            ),
        )
        self.assertIsNone(missing.ppe_acquisition_cash_payments)
        for value in (0, -1, -75_000_000):
            result = self.qualify(self.profile_for(
                companyfacts_payload(rows=[financial_row(value)])
            ))
            with self.subTest(value=value):
                self.assertIs(
                    result.status,
                    qualifier.CurrentAnnualPPEAcquisitionCashPaymentsStatus.
                    PPE_ACQUISITION_CASH_PAYMENTS_ESTABLISHED,
                )
                self.assertEqual(
                    result.ppe_acquisition_cash_payments, Decimal(value)
                )

    def test_invalid_float_malformed_and_nonfinite_facts_cannot_establish(self):
        for value in (None, "12.5", True):
            result = self.qualify(self.profile_for(
                companyfacts_payload(rows=[financial_row(value)])
            ))
            with self.subTest(value=value):
                self.assertEqual(
                    result.reasons,
                    (
                        qualifier.
                        CurrentAnnualPPEAcquisitionCashPaymentsReason.
                        FINITE_PPE_ACQUISITION_CASH_PAYMENTS_VALUE_UNAVAILABLE,
                    ),
                )
        observation = self.extract(coherent_payload()).observations[0]
        self.assertFalse(qualifier._eligible(
            replace(observation, value=1.5),
            cik=CIK,
            period_start="2024-01-01",
            period_end="2024-12-31",
        ))
        nonfinite = raw(coherent_payload()).replace(
            str(PPE_ACQUISITION_CASH_PAYMENTS_VALUE).encode(), b"NaN", 1
        )
        with self.assertRaises(ArchiveError):
            self.extract(coherent_payload(), content=nonfinite)
        with self.assertRaises(ArchiveError):
            self.extract(coherent_payload(), content=b'{"cik":0,"facts":')

    def test_exact_annual_duration_and_filing_presentation_are_required(self):
        payloads = (
            mismatched_period_payload(),
            companyfacts_payload(rows=[
                financial_row(
                    PPE_ACQUISITION_CASH_PAYMENTS_VALUE,
                    start="2024-10-01",
                    fp="Q4",
                    form="10-Q",
                )
            ]),
            companyfacts_payload(rows=[
                financial_row(
                    PPE_ACQUISITION_CASH_PAYMENTS_VALUE,
                    end="2024-09-30",
                    fp="Q3",
                    form="10-Q",
                )
            ]),
            companyfacts_payload(rows=[
                financial_row(
                    PPE_ACQUISITION_CASH_PAYMENTS_VALUE,
                    start="2024-04-01",
                )
            ]),
            companyfacts_payload(rows=[
                financial_row(
                    PPE_ACQUISITION_CASH_PAYMENTS_VALUE,
                    start=None,
                )
            ]),
        )
        for payload in payloads:
            result = self.qualify(self.profile_for(payload))
            with self.subTest(payload=payload):
                self.assertEqual(
                    result.reasons,
                    (
                        qualifier.
                        CurrentAnnualPPEAcquisitionCashPaymentsReason.
                        EXACT_ANNUAL_PERIOD_PRESENTATION_UNAVAILABLE,
                    ),
                )

    def test_duplicate_same_value_and_conflicting_values_are_closed(self):
        established = self.qualify(
            self.profile_for(duplicate_same_value_payload())
        )
        self.assertIs(
            established.status,
            qualifier.CurrentAnnualPPEAcquisitionCashPaymentsStatus.
            PPE_ACQUISITION_CASH_PAYMENTS_ESTABLISHED,
        )
        self.assertEqual(
            established.supporting_accessions,
            (LATEST_ACCESSION, SECOND_ACCESSION),
        )
        conflict = self.qualify(self.profile_for(conflicting_values_payload()))
        self.assertIs(
            conflict.status,
            qualifier.CurrentAnnualPPEAcquisitionCashPaymentsStatus.
            SOURCE_CONFLICT,
        )
        self.assertEqual(
            conflict.reasons,
            (
                qualifier.CurrentAnnualPPEAcquisitionCashPaymentsReason.
                COMPETING_PPE_ACQUISITION_CASH_PAYMENTS_VALUES,
            ),
        )
        self.assertIsNone(conflict.ppe_acquisition_cash_payments)
        self.assertEqual(conflict.selected_observation_ids, ())

    def test_annual_filing_metadata_must_be_coherent(self):
        for field, replacement_value in (
            ("form", "10-K/A"),
            ("filed", "2025-02-02"),
            ("fy", 2025),
        ):
            first = financial_row(PPE_ACQUISITION_CASH_PAYMENTS_VALUE)
            second = financial_row(
                PPE_ACQUISITION_CASH_PAYMENTS_VALUE,
                **{field: replacement_value},
            )
            result = self.qualify(self.profile_for(
                companyfacts_payload(rows=[first, second])
            ))
            with self.subTest(field=field):
                self.assertEqual(
                    result.reasons,
                    (
                        qualifier.
                        CurrentAnnualPPEAcquisitionCashPaymentsReason.
                        ANNUAL_FILING_METADATA_CONFLICT,
                    ),
                )
        frame_difference = self.qualify(self.profile_for(
            companyfacts_payload(rows=[
                financial_row(
                    PPE_ACQUISITION_CASH_PAYMENTS_VALUE,
                    frame="CY2024",
                ),
                financial_row(
                    PPE_ACQUISITION_CASH_PAYMENTS_VALUE,
                    frame="CY2024Q4",
                ),
            ])
        ))
        self.assertIs(
            frame_difference.status,
            qualifier.CurrentAnnualPPEAcquisitionCashPaymentsStatus.
            PPE_ACQUISITION_CASH_PAYMENTS_ESTABLISHED,
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
            qualifier.CurrentAnnualPPEAcquisitionCashPaymentsError
        ):
            self.qualify(route_mismatch)

        comparability = self.available.upstream_comparability
        security = comparability.upstream_security_eps
        bridge = security.upstream_registered_listing_bridge
        temporal = bridge.temporal_boundary
        current = temporal.current_evidence
        incoherent_current = replace(
            current,
            request=replace(current.request, cik="0000000001"),
        )
        incoherent_profile = replace(
            self.available,
            upstream_comparability=replace(
                comparability,
                upstream_security_eps=replace(
                    security,
                    upstream_registered_listing_bridge=replace(
                        bridge,
                        temporal_boundary=replace(
                            temporal, current_evidence=incoherent_current
                        ),
                    ),
                ),
            ),
        )
        route_conflict = self.qualify(incoherent_profile)
        self.assertEqual(
            route_conflict.reasons,
            (
                qualifier.CurrentAnnualPPEAcquisitionCashPaymentsReason.
                CANONICAL_ROUTE_IDENTITY_CONFLICT,
            ),
        )

        with tempfile.TemporaryDirectory() as temporary:
            foreign = SecArchive(Path(temporary).resolve() / "foreign")
            replay = self.qualify(archive=foreign)
        self.assertEqual(
            replay.reasons,
            (
                qualifier.CurrentAnnualPPEAcquisitionCashPaymentsReason.
                CAPTURE_REPLAY_CONFLICT,
            ),
        )
        with patch.object(
            self.fixture.current_archive,
            "read_object",
            side_effect=ArchiveError("corrupt object"),
        ):
            object_conflict = self.qualify()
        self.assertEqual(
            object_conflict.reasons,
            (
                qualifier.CurrentAnnualPPEAcquisitionCashPaymentsReason.
                CAPTURE_REPLAY_CONFLICT,
            ),
        )
        extracted = extraction.PPEAcquisitionCashPaymentsExtraction(
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
            "extract_ppe_acquisition_cash_payments",
            return_value=extracted,
        ):
            cik_conflict = self.qualify()
        self.assertEqual(
            cik_conflict.reasons,
            (
                qualifier.CurrentAnnualPPEAcquisitionCashPaymentsReason.
                SOURCE_CIK_CONFLICT,
            ),
        )

    def test_selected_observation_and_supporting_filing_partition_is_exact(self):
        result = self.qualify(
            self.profile_for(duplicate_same_value_payload())
        )
        ids = result.selected_observation_ids
        self.assertEqual(ids, tuple(sorted(set(ids))))
        flattened = tuple(sorted(
            observation_id
            for filing in result.supporting_filings
            for observation_id in filing.observation_ids
        ))
        self.assertEqual(flattened, ids)
        self.assertEqual(
            tuple(filing.accession for filing in result.supporting_filings),
            result.supporting_accessions,
        )
        for filing in result.supporting_filings:
            self.assertEqual(len(filing.forms), 1)
            self.assertEqual(len(filing.filed_dates), 1)
            self.assertEqual(len(filing.fiscal_years), 1)

    def test_source_order_decimal_lexical_forms_and_route_keys_are_semantic_neutral(self):
        payload = duplicate_same_value_payload()
        normal = self.qualify(self.profile_for(payload))
        reordered = duplicate_same_value_payload()
        reordered["facts"]["us-gaap"][
            extraction.PPE_ACQUISITION_CASH_PAYMENTS_CONCEPT
        ]["units"]["USD"].reverse()
        reordered_result = self.qualify(self.profile_for(reordered))
        self.assertEqual(normal.semantic_id, reordered_result.semantic_id)
        lexical = replace(
            normal,
            ppe_acquisition_cash_payments=Decimal("75000000.000"),
        )
        self.assertEqual(normal.semantic_id, lexical.semantic_id)
        route_changed = replace(
            normal,
            route_local_issuer_key="a" * 64,
            route_local_security_key="b" * 64,
        )
        self.assertEqual(normal.semantic_id, route_changed.semantic_id)
        self.assertNotEqual(normal.evidence_id, route_changed.evidence_id)

    def test_exact_base_ten_precision_is_never_binary_float(self):
        precise = "75000000.12345678901234567890123456789"
        content = raw(coherent_payload()).replace(
            str(PPE_ACQUISITION_CASH_PAYMENTS_VALUE).encode(),
            precise.encode(),
            1,
        )
        observation = self.extract(
            coherent_payload(), content=content
        ).observations[0]
        self.assertEqual(observation.value, Decimal(precise))
        self.assertIs(type(observation.value), Decimal)

    def test_legitimate_recapture_preserves_semantics_and_changes_evidence(self):
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
        recaptured = (
            qualifier.qualify_sec_current_annual_ppe_acquisition_cash_payments(
                recapture_fixture.current_archive,
                recaptured_profile,
            )
        )
        self.assertEqual(
            first.ppe_acquisition_cash_payments,
            recaptured.ppe_acquisition_cash_payments,
        )
        self.assertEqual(first.source_cik, recaptured.source_cik)
        self.assertEqual(first.period_start, recaptured.period_start)
        self.assertEqual(first.period_end, recaptured.period_end)
        self.assertEqual(first.semantic_id, recaptured.semantic_id)
        self.assertNotEqual(first.evidence_id, recaptured.evidence_id)
        self.assertNotEqual(
            first.capture_receipt_id,
            recaptured.capture_receipt_id,
        )
        self.assertNotEqual(
            first.source_object_hash,
            recaptured.source_object_hash,
        )
        changed_value = replace(
            first,
            ppe_acquisition_cash_payments=(
                first.ppe_acquisition_cash_payments + Decimal(1)
            ),
        )
        self.assertNotEqual(first.semantic_id, changed_value.semantic_id)

    def test_serialization_immutability_and_reason_order_are_deterministic(self):
        result = self.qualify()
        self.assertEqual(result.semantic_id, result.semantic_id)
        self.assertEqual(result.evidence_id, result.evidence_id)
        self.assertEqual(result.to_dict(), result.to_dict())
        json.dumps(result.to_dict(), sort_keys=True)
        self.assertEqual(
            result.reasons,
            tuple(sorted(set(result.reasons), key=lambda item: item.value)),
        )
        with self.assertRaises(FrozenInstanceError):
            result.ppe_acquisition_cash_payments = Decimal(1)
        with self.assertRaises(FrozenInstanceError):
            result.supporting_filings[0].accession = SECOND_ACCESSION

    def test_current_only_authority_and_closed_limitations_are_pinned(self):
        result = self.qualify()
        self.assertEqual(
            result.authority,
            "QUALITY_PPE_ACQUISITION_CASH_PAYMENTS_EVIDENCE_ONLY",
        )
        self.assertEqual(
            result.limitations,
            tuple(
                qualifier.
                CurrentAnnualPPEAcquisitionCashPaymentsLimitation
            ),
        )
        values = {item.value for item in result.limitations}
        for required in (
            "NO_UNIVERSAL_OR_TOTAL_CAPEX_CLAIM",
            "NO_FREE_CASH_FLOW_OR_OWNER_EARNINGS_CLAIM",
            "NO_REINVESTMENT_OR_CAPITAL_ALLOCATION_QUALITY_CONCLUSION",
            "NO_QUALITY_SCORE_GRADE_AGGREGATE_OR_RANKING",
            "NO_HISTORICAL_AS_OF_OR_PIT_AUTHORITY",
            "NO_PRODUCTION_DEPLOYMENT_OR_V2_PROMOTION_AUTHORITY",
        ):
            self.assertIn(required, values)

    def test_controlled_replay_has_no_network_clock_or_provider_acquisition(self):
        with patch.object(
            socket.socket, "connect", side_effect=AssertionError("network")
        ), patch.object(
            socket, "getaddrinfo", side_effect=AssertionError("network")
        ), patch(
            "time.time", side_effect=AssertionError("clock")
        ):
            self.assertIs(
                self.qualify().status,
                qualifier.CurrentAnnualPPEAcquisitionCashPaymentsStatus.
                PPE_ACQUISITION_CASH_PAYMENTS_ESTABLISHED,
            )

    def test_static_imports_and_dependency_boundaries_are_closed(self):
        allowed = {
            "dataclasses", "datetime", "decimal", "enum", "hashlib", "json",
            "re", "economic_facts", "economic_facts.sec_archive",
            "economic_facts.sec_current_eps_comparability_qualification",
            "economic_facts.sec_eps_series",
            "economic_facts.sec_ppe_acquisition_cash_payments",
            "economic_facts.sec_ordinary_compounder_profile",
        }
        for module in (extraction, qualifier):
            source = Path(module.__file__).read_text()
            tree = ast.parse(source)
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    self.assertTrue(
                        all(alias.name in allowed for alias in node.names)
                    )
                elif isinstance(node, ast.ImportFrom):
                    name = node.module
                    if node.level:
                        name = "economic_facts." + (name or "")
                    self.assertIn(name.rstrip("."), allowed)
                elif isinstance(node, ast.Call) and isinstance(
                    node.func, ast.Name
                ):
                    self.assertNotIn(
                        node.func.id,
                        {"eval", "exec", "__import__", "compile"},
                    )
            for token in (
                "requests", "urllib", "sec_acquisition",
                "expected_return_engine", "portfolio",
                "execution_instruction", "quality_score",
                "analysis_capabilities",
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
            (
                checkout / "tests" / "test_pit_adapter_equivalence.py"
            ).read_text(),
        )
        self.assertIn(
            "f8457910665391e39c234274cae4c029802c681211eebc7dba986a63000876f1",
            (checkout / "tests" / "test_pit_comparison.py").read_text(),
        )


if __name__ == "__main__":
    unittest.main()
