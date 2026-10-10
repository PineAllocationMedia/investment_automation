"""Adversarial tests for exact CURRENT annual opening/closing Assets evidence."""
import ast
from collections import UserDict
from copy import deepcopy
from dataclasses import FrozenInstanceError, fields, replace
from datetime import date
from decimal import Decimal, localcontext
import json
from pathlib import Path
import socket
import tempfile
import unittest
from unittest.mock import patch

from economic_facts import sec_current_annual_opening_closing_assets as qualifier
from economic_facts import sec_assets_liabilities as extraction
from economic_facts import sec_ordinary_compounder_profile as profile_module
from economic_facts.sec_archive import ArchiveError, SecArchive
from tests import test_sec_current_eps_comparability_qualification as comparability_tests
from tests import test_sec_ordinary_compounder_profile as profile_tests
from tests.sec_current_security_eps_qualification_fixtures import VALUES, companyfacts_rows
from tests.sec_five_year_eps_presentation_fixtures import five_year_table
from tests.sec_assets_liabilities_fixtures import (
    LATEST_ACCESSION, SECOND_ACCESSION, capture_profile, companyfacts_payload,
    financial_row,
)
from tests.sec_property4_temporal_boundary_fixtures import BOUNDARY_T1, BOUNDARY_T2

Status = qualifier.CurrentAnnualOpeningClosingAssetsStatus
Reason = qualifier.CurrentAnnualOpeningClosingAssetsReason
Error = qualifier.CurrentAnnualOpeningClosingAssetsError
OPENING = "2023-12-31"
CLOSING = "2024-12-31"
OPENING_VALUE = 200_000_000
CLOSING_VALUE = 250_000_000


def payload_for(*, opening=OPENING_VALUE, closing=CLOSING_VALUE, rows=None, **kwargs):
    return companyfacts_payload(
        assets_rows=(
            [financial_row(opening, end=OPENING), financial_row(closing)]
            if rows is None else rows
        ), include_liabilities=False, **kwargs,
    )


class SecCurrentAnnualOpeningClosingAssetsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = comparability_tests.SecCurrentEPSComparabilityTests(methodName="runTest")
        cls.fixture.setUp()
        cls.receipt, cls.available = capture_profile(cls.fixture, payload_for())
        _, cls.unavailable = capture_profile(cls.fixture, payload_for(), sic=None, description=None)
        _, cls.unsupported = capture_profile(cls.fixture, payload_for(), sic=6021,
                                            description="National Commercial Banks")
        _, cls.semantic_replay_conflict = capture_profile(
            cls.fixture, payload_for(), expected_comparability_semantic_id="0" * 64)
        _, cls.evidence_replay_conflict = capture_profile(
            cls.fixture, payload_for(), expected_comparability_evidence_id="0" * 64)

    @classmethod
    def tearDownClass(cls):
        cls.fixture.doCleanups()

    def qualify(self, profile=None, archive=None):
        return qualifier.qualify_sec_current_annual_opening_closing_assets(
            self.fixture.current_archive if archive is None else archive,
            self.available if profile is None else profile,
        )

    def profile_for(self, payload, **kwargs):
        return capture_profile(self.fixture, payload, **kwargs)[1]

    @staticmethod
    def replace_decision(profile, structure, **changes):
        return replace(profile, decisions=tuple(
            replace(item, **changes) if item.profile is structure else item
            for item in profile.decisions))

    def assert_empty(self, result):
        self.assertIsNone(result.opening_assets)
        self.assertIsNone(result.closing_assets)
        self.assertEqual(result.selected_opening_assets_observation_ids, ())
        self.assertEqual(result.selected_closing_assets_observation_ids, ())
        self.assertEqual(result.selected_opening_observations, ())
        self.assertEqual(result.selected_closing_observations, ())
        self.assertEqual(result.supporting_accessions, ())
        self.assertEqual(result.supporting_filings, ())


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
                                qualifier.CurrentAnnualOpeningClosingAssetsError
                            ):
                        qualifier.qualify_sec_current_annual_opening_closing_assets(
                            archive, profile
                        )

    def test_replay_provenance_is_authenticated_expected_vs_actual(self):
            comparability = self.available.upstream_comparability
            self.assertEqual(
                self.available.expected_comparability_semantic_id,
                comparability.semantic_id,
            )
            self.assertEqual(
                self.available.expected_comparability_evidence_id,
                comparability.evidence_id,
            )
            self.assertNotIn(
                profile_module.ProfileReason.REPLAY_IDENTITY_MISMATCH,
                self.available.reasons,
            )
            for profile in (
                self.semantic_replay_conflict,
                self.evidence_replay_conflict,
            ):
                with self.subTest(profile=profile):
                    actual = profile.upstream_comparability
                    self.assertTrue(
                        profile.expected_comparability_semantic_id
                        != actual.semantic_id
                        or profile.expected_comparability_evidence_id
                        != actual.evidence_id
                    )
                    self.assertIs(
                        profile.status,
                        profile_module.OrdinaryCompounderProfileStatus.SOURCE_CONFLICT,
                    )
                    self.assertIn(
                        profile_module.ProfileReason.REPLAY_IDENTITY_MISMATCH,
                        profile.reasons,
                    )
                    result = self.qualify(profile)
                    self.assertIs(
                        result.status,
                        qualifier.CurrentAnnualOpeningClosingAssetsStatus.
                        SOURCE_CONFLICT,
                    )
                    self.assertEqual(
                        result.reasons,
                        (
                            qualifier.CurrentAnnualOpeningClosingAssetsReason.
                            UPSTREAM_SOURCE_CONFLICT,
                        ),
                    )

    def test_fabricated_replay_conflict_and_expected_id_mutation_are_rejected(self):
            fabricated = replace(
                self.available,
                status=profile_module.OrdinaryCompounderProfileStatus.SOURCE_CONFLICT,
                profile=None,
                reasons=(profile_module.ProfileReason.REPLAY_IDENTITY_MISMATCH,),
            )
            mutations = (
                fabricated,
                replace(
                    self.available,
                    expected_comparability_semantic_id="0" * 64,
                ),
                replace(
                    self.available,
                    expected_comparability_evidence_id="0" * 64,
                ),
            )
            for profile in mutations:
                with self.subTest(profile=profile), self.assertRaises(
                    qualifier.CurrentAnnualOpeningClosingAssetsError
                ):
                    self.qualify(profile)

    def test_v1_profile_contract_is_rejected_without_migration(self):
            legacy = replace(
                self.available,
                contract_version=(
                    "2026-09-29-sec-ordinary-compounder-method-profile-v1"
                ),
            )
            with self.assertRaises(
                qualifier.CurrentAnnualOpeningClosingAssetsError
            ):
                self.qualify(legacy)

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
                    qualifier.CurrentAnnualOpeningClosingAssetsError
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
            self.assertIs(bank.decision, profile_module.ProfileDecisionValue.NOT_EXCLUDED)
            self.assertIn(
                profile_module.ProfileReason.UNSUPPORTED_SIC_PROFILE,
                self.unsupported.reasons,
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
                qualifier.CurrentAnnualOpeningClosingAssetsError
            ):
                self.qualify(forged)

    def test_profile_reasons_require_their_exact_factory_conditions(self):
            unavailable = profile_module.OrdinaryCompounderProfileStatus.PROFILE_UNAVAILABLE
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
                    status=unavailable,
                    profile=None,
                    reasons=(reason,),
                )
                with self.subTest(reason=reason), self.assertRaises(
                    qualifier.CurrentAnnualOpeningClosingAssetsError
                ):
                    self.qualify(forged)

    def test_unsupported_reason_requires_reachable_structural_decision(self):
            forged = replace(
                self.available,
                status=profile_module.OrdinaryCompounderProfileStatus.PROFILE_UNSUPPORTED,
                profile=None,
                reasons=(profile_module.ProfileReason.UNSUPPORTED_SIC_PROFILE,),
            )
            self.assertTrue(all(
                item.decision is profile_module.ProfileDecisionValue.EXCLUDED
                for item in forged.decisions
            ))
            with self.assertRaises(
                qualifier.CurrentAnnualOpeningClosingAssetsError
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
                    qualifier.CurrentAnnualOpeningClosingAssetsError
                ):
                    self.qualify(profile)

    def test_genuine_turnaround_loss_reporting_and_mixed_states_are_preserved(self):
            factory = profile_tests.OrdinaryCompounderProfileTests(methodName="runTest")
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
                    qualifier.CurrentAnnualOpeningClosingAssetsStatus.
                    EVIDENCE_UNAVAILABLE,
                ),
                (
                    mixed,
                    profile_module.OrdinaryCompounderProfileStatus.PROFILE_UNAVAILABLE,
                    profile_module.ProfileReason.MIXED_STRUCTURE_UNRESOLVED,
                    qualifier.CurrentAnnualOpeningClosingAssetsStatus.
                    EVIDENCE_UNAVAILABLE,
                ),
                (
                    loss_making,
                    profile_module.OrdinaryCompounderProfileStatus.PROFILE_UNSUPPORTED,
                    profile_module.ProfileReason.
                    POSITIVE_FIVE_PERIOD_ROUTE_NOT_ESTABLISHED,
                    qualifier.CurrentAnnualOpeningClosingAssetsStatus.
                    EVIDENCE_UNSUPPORTED,
                ),
            )
            for profile, upstream_status, upstream_reason, local_status in cases:
                with self.subTest(upstream_status=upstream_status):
                    self.assertIs(profile.status, upstream_status)
                    self.assertIn(upstream_reason, profile.reasons)
                    result = qualifier.qualify_sec_current_annual_opening_closing_assets(
                        archive,
                        profile,
                    )
                    self.assertIs(result.status, local_status)
                    self.assertIsNone(result.closing_assets)
                    self.assertIsNone(result.opening_assets)

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
                    qualifier.CurrentAnnualOpeningClosingAssetsStatus.
                    EVIDENCE_UNAVAILABLE,
                    qualifier.CurrentAnnualOpeningClosingAssetsReason.
                    UPSTREAM_PROFILE_UNAVAILABLE,
                ),
                profile_module.OrdinaryCompounderProfileStatus.PROFILE_UNSUPPORTED: (
                    qualifier.CurrentAnnualOpeningClosingAssetsStatus.
                    EVIDENCE_UNSUPPORTED,
                    qualifier.CurrentAnnualOpeningClosingAssetsReason.
                    UPSTREAM_PROFILE_UNSUPPORTED,
                ),
                profile_module.OrdinaryCompounderProfileStatus.SOURCE_CONFLICT: (
                    qualifier.CurrentAnnualOpeningClosingAssetsStatus.SOURCE_CONFLICT,
                    qualifier.CurrentAnnualOpeningClosingAssetsReason.
                    UPSTREAM_SOURCE_CONFLICT,
                ),
            }
            expected_status, expected_reason = projected[profile.status]
            self.assertIs(result.status, expected_status)
            self.assertEqual(result.reasons, (expected_reason,))
            self.assertIsNone(result.closing_assets)
            self.assertIsNone(result.opening_assets)
            self.assertEqual(result.selected_closing_assets_observation_ids, ())
            self.assertEqual(result.selected_opening_assets_observation_ids, ())
            self.assertEqual(result.supporting_accessions, ())
            self.assertEqual(result.supporting_filings, ())

            for invalid_sic in ("10000", 10000.0, True):
                with self.subTest(invalid_sic=invalid_sic), self.assertRaises(
                    qualifier.CurrentAnnualOpeningClosingAssetsError
                ):
                    self.qualify(replace(profile, sic=invalid_sic))

    def test_route_receipt_object_and_source_cik_conflicts_fail_closed(self):
            route_mismatch = replace(
                self.available,
                upstream_comparability=replace(
                    self.available.upstream_comparability,
                    route_local_issuer_key="0" * 64,
                ),
            )
            with self.assertRaises(
                qualifier.CurrentAnnualOpeningClosingAssetsError
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
                (qualifier.CurrentAnnualOpeningClosingAssetsReason.
                 CANONICAL_ROUTE_IDENTITY_CONFLICT,),
            )

            with tempfile.TemporaryDirectory() as temporary:
                foreign = SecArchive(Path(temporary).resolve() / "foreign")
                replay = self.qualify(archive=foreign)
            self.assertEqual(
                replay.reasons,
                (qualifier.CurrentAnnualOpeningClosingAssetsReason.
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
                (qualifier.CurrentAnnualOpeningClosingAssetsReason.
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
                (qualifier.CurrentAnnualOpeningClosingAssetsReason.
                 CAPTURE_REPLAY_CONFLICT,),
            )
            extracted = extraction.AssetsLiabilitiesExtraction(
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
                "extract_assets_liabilities",
                return_value=extracted,
            ):
                cik_conflict = self.qualify()
            self.assertEqual(
                cik_conflict.reasons,
                (qualifier.CurrentAnnualOpeningClosingAssetsReason.
                 SOURCE_CIK_CONFLICT,),
            )

    def test_exact_versioned_immutable_evidence_and_dates(self):
        result = self.qualify()
        self.assertIs(result.status, Status.OPENING_CLOSING_ASSETS_ESTABLISHED)
        self.assertEqual(result.reasons, ())
        self.assertEqual(result.contract_version,
                         '2026-10-10-current-annual-opening-closing-assets-qualification-v1')
        self.assertEqual(result.qualifier_version,
                         '2026-10-10-adjacent-common-filing-exact-decimal-usd-assets-instants-qualification-v1')
        self.assertEqual(result.evidence_kind, 'CURRENT_ANNUAL_OPENING_CLOSING_ASSETS_QUALIFICATION')
        self.assertEqual((result.period_start, result.period_end), ('2024-01-01', CLOSING))
        self.assertEqual((result.opening_balance_date, result.closing_balance_date), (OPENING, CLOSING))
        self.assertEqual((date.fromisoformat(result.period_start) -
                          date.fromisoformat(result.opening_balance_date)).days, 1)
        self.assertEqual((result.opening_assets, result.closing_assets),
                         (Decimal(OPENING_VALUE), Decimal(CLOSING_VALUE)))
        self.assertEqual((result.accounting_namespace, result.concept,
                          result.accounting_basis, result.unit), ('us-gaap', 'Assets', 'US_GAAP', 'USD'))
        self.assertEqual(result.authority, 'QUALITY_OPENING_CLOSING_ASSETS_EVIDENCE_ONLY')
        self.assertEqual(result.limitations, tuple(qualifier.CurrentAnnualOpeningClosingAssetsLimitation))
        with self.assertRaises(FrozenInstanceError):
            result.opening_assets = Decimal(1)
        self.assertEqual(self.qualify(), result)
        encoded = json.dumps(result.to_dict(), sort_keys=True)
        self.assertEqual(encoded, json.dumps(self.qualify().to_dict(), sort_keys=True))
        keys = set(result.to_dict()['current_annual_opening_closing_assets'])
        for prohibited in ('average_assets', 'roa', 'roe', 'roic', 'score', 'grade',
                           'ratio', 'capital_efficiency', 'recommendation', 'allocation'):
            self.assertNotIn(prohibited, keys)

    def test_native_upstream_capability_states_are_truthful_and_empty(self):
        for profile, status, reason in (
            (self.unavailable, Status.EVIDENCE_UNAVAILABLE, Reason.UPSTREAM_PROFILE_UNAVAILABLE),
            (self.unsupported, Status.EVIDENCE_UNSUPPORTED, Reason.UPSTREAM_PROFILE_UNSUPPORTED),
            (self.semantic_replay_conflict, Status.SOURCE_CONFLICT, Reason.UPSTREAM_SOURCE_CONFLICT),
            (self.evidence_replay_conflict, Status.SOURCE_CONFLICT, Reason.UPSTREAM_SOURCE_CONFLICT),
        ):
            with self.subTest(status=status):
                result = self.qualify(profile)
                self.assertIs(result.status, status)
                self.assertEqual(result.reasons, (reason,))
                self.assertEqual(result.upstream_profile_status, profile.status)
                self.assertEqual(result.upstream_profile_reasons, profile.reasons)
                self.assert_empty(result)

    def test_exact_missing_concept_unit_and_boundary_states(self):
        for payload, reasons in (
            (payload_for(include_assets=False), {Reason.OPENING_ASSETS_UNAVAILABLE,
                                                 Reason.CLOSING_ASSETS_UNAVAILABLE}),
            (payload_for(namespace='fictional'), {Reason.OPENING_ASSETS_UNAVAILABLE,
                                                  Reason.CLOSING_ASSETS_UNAVAILABLE}),
            (payload_for(assets_concept='AssetsCurrent'), {Reason.OPENING_ASSETS_UNAVAILABLE,
                                                          Reason.CLOSING_ASSETS_UNAVAILABLE}),
            (payload_for(assets_unit='shares'), {Reason.EXACT_USD_UNIT_UNAVAILABLE}),
            (payload_for(assets_unit='usd'), {Reason.EXACT_USD_UNIT_UNAVAILABLE}),
            (payload_for(rows=[financial_row(CLOSING_VALUE)]), {Reason.OPENING_ASSETS_UNAVAILABLE}),
            (payload_for(rows=[financial_row(OPENING_VALUE, end=OPENING)]), {Reason.CLOSING_ASSETS_UNAVAILABLE}),
        ):
            with self.subTest(reasons=reasons):
                result = self.qualify(self.profile_for(payload))
                self.assertIs(result.status, Status.EVIDENCE_UNAVAILABLE)
                self.assertEqual(set(result.reasons), reasons)
                self.assertEqual(result.reasons, tuple(sorted(reasons, key=lambda r: r.value)))
                self.assert_empty(result)

    def test_instant_and_annual_metadata_are_exact(self):
        for boundary in (OPENING, CLOSING):
            for changes in ({'start': '2024-01-01'}, {'fp': 'Q4'}, {'form': '10-Q'},
                            {'filed': '2025-02-30'}, {'accn': 'invalid'}, {'fy': '2024'},
                            {'end': '2024-12-30'}, {'start': 1}, {'frame': ''}):
                rows = [financial_row(OPENING_VALUE, end=OPENING), financial_row(CLOSING_VALUE)]
                target = next(row for row in rows if row['end'] == boundary)
                target.update(changes)
                with self.subTest(boundary=boundary, changes=changes):
                    result = self.qualify(self.profile_for(payload_for(rows=rows)))
                    self.assertIs(result.status, Status.EVIDENCE_UNAVAILABLE)
                    self.assert_empty(result)
                    if 'end' not in changes:
                        self.assertIn(Reason.EXACT_OPENING_CLOSING_INSTANT_PRESENTATION_UNAVAILABLE,
                                      result.reasons)
        payload = payload_for()
        rows = payload['facts']['us-gaap']['Assets']['units']['USD']
        rows[0]['frame'] = 'CY2023Q4I'
        rows[1]['frame'] = 'CY2024Q4I'
        self.assertIs(self.qualify(self.profile_for(payload)).status, Status.OPENING_CLOSING_ASSETS_ESTABLISHED)

    def test_nonfinite_or_malformed_values_cannot_hide_behind_other_instant(self):
        for boundary, reason in ((OPENING, Reason.FINITE_OPENING_ASSETS_VALUE_UNAVAILABLE),
                                 (CLOSING, Reason.FINITE_CLOSING_ASSETS_VALUE_UNAVAILABLE)):
            for value in (None, 'NaN', 'Infinity', '250000000', True, []):
                payload = payload_for()
                for row in payload['facts']['us-gaap']['Assets']['units']['USD']:
                    if row['end'] == boundary:
                        row['val'] = value
                with self.subTest(boundary=boundary, value=value):
                    result = self.qualify(self.profile_for(payload))
                    self.assertEqual(result.reasons, (reason,))
                    self.assert_empty(result)
        # Nonfinite JSON constants and structural corruption are rejected during replay.
        with patch.object(self.fixture.current_archive, 'read_object', return_value=b'{"val":NaN}'):
            self.assertEqual(self.qualify().reasons, (Reason.CAPTURE_REPLAY_CONFLICT,))

    def test_structurally_malformed_assets_fail_closed(self):
        for node in ([], {'units': []}, {'units': {'USD': {}}}, {'units': {'USD': [[]]}}):
            payload = payload_for()
            payload['facts']['us-gaap']['Assets'] = node
            result = self.qualify(self.profile_for(payload))
            self.assertEqual(result.reasons, (Reason.CAPTURE_REPLAY_CONFLICT,))
            self.assert_empty(result)

    def test_signed_and_zero_source_facts_are_preserved_exactly(self):
        for opening, closing in ((0, 0), (-4, 0), (0, -8), (-3, -7)):
            with self.subTest(opening=opening, closing=closing):
                result = self.qualify(self.profile_for(payload_for(opening=opening, closing=closing)))
                self.assertIs(result.status, Status.OPENING_CLOSING_ASSETS_ESTABLISHED)
                self.assertEqual((result.opening_assets, result.closing_assets),
                                 (Decimal(opening), Decimal(closing)))
                self.assertIs(type(result.opening_assets), Decimal)
                self.assertIs(type(result.closing_assets), Decimal)

    def test_no_standalone_prior_filing_can_supply_opening(self):
        payload = payload_for(rows=[financial_row(OPENING_VALUE, end=OPENING, accession=SECOND_ACCESSION),
                                    financial_row(CLOSING_VALUE)])
        result = self.qualify(self.profile_for(payload))
        self.assertEqual(result.reasons, (Reason.NO_COMMON_ANNUAL_FILING_ACCESSION,))
        self.assert_empty(result)

    def test_orphan_values_and_metadata_do_not_poison_common_pair(self):
        payload = payload_for()
        payload['facts']['us-gaap']['Assets']['units']['USD'].extend([
            financial_row(123, end=OPENING, accession=SECOND_ACCESSION, fy=2023),
            financial_row(999, end='2022-12-31', accession=SECOND_ACCESSION),
        ])
        result = self.qualify(self.profile_for(payload))
        self.assertIs(result.status, Status.OPENING_CLOSING_ASSETS_ESTABLISHED)
        self.assertEqual(result.supporting_accessions, (LATEST_ACCESSION,))
        self.assertEqual(result.opening_assets, Decimal(OPENING_VALUE))
        self.assertEqual(len(result.selected_opening_observations), 1)

    @staticmethod
    def multiple_common_rows():
        return [financial_row(OPENING_VALUE, end=OPENING), financial_row(CLOSING_VALUE),
                financial_row(OPENING_VALUE, end=OPENING, accession=SECOND_ACCESSION, filed='2025-02-02'),
                financial_row(CLOSING_VALUE, accession=SECOND_ACCESSION, filed='2025-02-02')]

    def test_multiple_common_filings_and_exact_observation_partition(self):
        result = self.qualify(self.profile_for(payload_for(rows=self.multiple_common_rows())))
        self.assertIs(result.status, Status.OPENING_CLOSING_ASSETS_ESTABLISHED)
        self.assertEqual(result.supporting_accessions, (LATEST_ACCESSION, SECOND_ACCESSION))
        for name in ('opening', 'closing'):
            ids = getattr(result, f'selected_{name}_assets_observation_ids')
            observations = getattr(result, f'selected_{name}_observations')
            self.assertEqual(ids, tuple(sorted(set(ids))))
            self.assertEqual(ids, tuple(row.observation_id for row in observations))
            self.assertEqual(ids, tuple(sorted(
                oid for filing in result.supporting_filings
                for oid in getattr(filing, f'{name}_assets_observation_ids'))))
            for row in observations:
                self.assertEqual(row.capture_receipt_id, result.capture_receipt_id)
                self.assertEqual(row.source_object_hash, result.source_object_hash)
                self.assertEqual(row.captured_at, result.captured_at)
                self.assertEqual(row.end, getattr(result, f'{name}_balance_date'))
                self.assertEqual(row.accounting_basis, result.accounting_basis)
                self.assertTrue(row.source_locator.startswith('/facts/us-gaap/Assets/units/USD/'))
        self.assertFalse(set(result.selected_opening_assets_observation_ids) &
                         set(result.selected_closing_assets_observation_ids))

    def test_competing_values_are_independent_closed_conflicts(self):
        for boundaries, reasons in (
            ((OPENING,), {Reason.COMPETING_OPENING_ASSETS_VALUES}),
            ((CLOSING,), {Reason.COMPETING_CLOSING_ASSETS_VALUES}),
            ((OPENING, CLOSING), {Reason.COMPETING_OPENING_ASSETS_VALUES, Reason.COMPETING_CLOSING_ASSETS_VALUES}),
        ):
            rows = self.multiple_common_rows()
            for row in rows:
                if row['end'] in boundaries and row['accn'] == SECOND_ACCESSION:
                    row['val'] += 1
            result = self.qualify(self.profile_for(payload_for(rows=rows)))
            self.assertIs(result.status, Status.SOURCE_CONFLICT)
            self.assertEqual(set(result.reasons), reasons)
            self.assert_empty(result)
        rows = self.multiple_common_rows()[:2] + [financial_row(OPENING_VALUE + 1, end=OPENING)]
        self.assertEqual(self.qualify(self.profile_for(payload_for(rows=rows))).reasons,
                         (Reason.COMPETING_OPENING_ASSETS_VALUES,))

    def test_common_filing_metadata_conflicts_fail_closed(self):
        for field, value in (('form', '10-K/A'), ('filed', '2025-02-02'), ('fy', 2023)):
            rows = self.multiple_common_rows()
            rows[0][field] = value
            result = self.qualify(self.profile_for(payload_for(rows=rows)))
            self.assertEqual(result.reasons, (Reason.COMMON_FILING_METADATA_CONFLICT,))
            self.assert_empty(result)

    def test_authentic_independent_recapture_has_stable_economics(self):
        # Each invocation captures source bytes and rebuilds the entire native profile graph.
        first_profile = self.profile_for(payload_for(), captured_at=BOUNDARY_T1)
        second_profile = self.profile_for(payload_for(), captured_at=BOUNDARY_T2)
        first, second = self.qualify(first_profile), self.qualify(second_profile)
        self.assertIs(first.status, Status.OPENING_CLOSING_ASSETS_ESTABLISHED)
        self.assertIs(second.status, Status.OPENING_CLOSING_ASSETS_ESTABLISHED)
        self.assertNotEqual(first.capture_receipt_id, second.capture_receipt_id)
        self.assertNotEqual(first.route_local_issuer_key, second.route_local_issuer_key)
        self.assertNotEqual(first.upstream_profile_semantic_id, second.upstream_profile_semantic_id)
        self.assertNotEqual(first.upstream_comparability_semantic_id, second.upstream_comparability_semantic_id)
        self.assertEqual(first.source_object_hash, second.source_object_hash)
        self.assertEqual(first.semantic_id, second.semantic_id)
        self.assertNotEqual(first.evidence_id, second.evidence_id)
        self.assertNotEqual(first.selected_opening_assets_observation_ids,
                            second.selected_opening_assets_observation_ids)

    def test_either_genuine_amount_changes_semantic_identity(self):
        original = self.qualify()
        for payload in (payload_for(opening=OPENING_VALUE + 1), payload_for(closing=CLOSING_VALUE + 1)):
            changed = self.qualify(self.profile_for(payload))
            self.assertNotEqual(original.semantic_id, changed.semantic_id)

    def test_row_reordering_and_decimal_forms_preserve_semantics(self):
        payload = payload_for(rows=self.multiple_common_rows())
        normal = self.qualify(self.profile_for(payload))
        payload['facts']['us-gaap']['Assets']['units']['USD'].reverse()
        reordered = self.qualify(self.profile_for(payload, reverse=True))
        self.assertEqual(normal.semantic_id, reordered.semantic_id)
        self.assertEqual(normal.supporting_accessions, reordered.supporting_accessions)
        self.assertNotEqual(normal.source_object_hash, reordered.source_object_hash)
        self.assertNotEqual(normal.evidence_id, reordered.evidence_id)
        integers = self.qualify(self.profile_for(payload_for(opening=1000, closing=2500)))
        floats = self.qualify(self.profile_for(payload_for(opening=1000.0, closing=2500.0)))
        self.assertEqual(integers.semantic_id, floats.semantic_id)
        self.assertIs(type(floats.opening_assets), Decimal)
        with localcontext() as context:
            context.prec = 2
            for text in ('1000.000', '1E+3', '1000'):
                self.assertEqual(qualifier._canonical_decimal(Decimal(text)),
                                 qualifier._canonical_decimal(Decimal(1000)))

    def test_fabricated_or_malformed_canonical_chain_is_rejected(self):
        comp = self.available.upstream_comparability
        mutations = (
            (), comp.period_decisions[:-1], tuple(reversed(comp.period_decisions)),
            comp.period_decisions[:-1] + (replace(comp.period_decisions[-1], period_start='2024-01-02'),),
            comp.period_decisions[:-1] + (replace(comp.period_decisions[-1], period_end='2024-02-30'),),
            comp.period_decisions[:-1] + (replace(comp.period_decisions[-1], period_start='20240101'),),
            comp.period_decisions[:-1] + (replace(comp.period_decisions[-1], c3_value=Decimal(8)),),
        )
        for periods in mutations:
            forged_comp = replace(comp, period_decisions=periods)
            forged_profile = qualifier._factory_reachable_profile(self.available, forged_comp)
            forged_profile = replace(forged_profile,
                expected_comparability_semantic_id=forged_comp.semantic_id,
                expected_comparability_evidence_id=forged_comp.evidence_id)
            forged_profile = qualifier._factory_reachable_profile(forged_profile, forged_comp)
            with self.subTest(periods=periods), self.assertRaises(Error):
                self.qualify(forged_profile)

    def test_calendar_day_boundary_leap_year_and_year_end(self):
        for start, opening in (('2024-03-01', '2024-02-29'),
                               ('2023-03-01', '2023-02-28'),
                               ('2024-01-01', '2023-12-31')):
            self.assertEqual(qualifier._adjacent_opening_date(start, opening), opening)
        for prior in ('2024-02-28', '2024-03-01', '2023-12-30'):
            start = '2024-03-01' if prior.startswith('2024') else '2024-01-01'
            self.assertIsNone(qualifier._adjacent_opening_date(start, prior))

    def test_nonadjacent_boundary_projects_unavailable_without_guess(self):
        # The current upstream resolver admits adjacent fixed-month-end chains only.
        # Exercise the defensive boundary projection; this is not a real nonadjacent capture.
        with patch.object(qualifier, '_target_period',
                          return_value=('2024-01-01', CLOSING, None, CLOSING)):
            result = self.qualify()
        self.assertEqual(result.reasons, (Reason.CANONICAL_OPENING_BALANCE_DATE_UNAVAILABLE,))
        self.assertIsNone(result.opening_balance_date)
        self.assert_empty(result)

    def test_defensive_absent_period_context_stays_absent(self):
        # No native no-series profile can currently be constructed through the full
        # PR5C request factory (its expected C3 IDs are required hashes).
        # Exercise missing-context derivation without claiming authentic admission.
        comp = self.available.upstream_comparability
        security = comp.upstream_security_eps
        bridge = security.upstream_registered_listing_bridge
        temporal = bridge.temporal_boundary
        current = temporal.current_evidence
        current = replace(current, resolution=replace(current.resolution, series=None))
        security = replace(security, upstream_registered_listing_bridge=replace(
            bridge, temporal_boundary=replace(temporal, current_evidence=current)))
        comp = replace(comp, period_decisions=(), upstream_security_eps=security)
        self.assertEqual(qualifier._target_period(comp, require_established=False),
                         (None, None, None, None))
        with self.assertRaises(Error):
            qualifier._target_period(comp, require_established=True)

    def test_no_network_clock_acquisition_or_analytic_fields(self):
        with patch.object(socket, 'create_connection', side_effect=AssertionError('network')),\
             patch.object(SecArchive, '_capture_live', side_effect=AssertionError('capture')):
            result = self.qualify()
        self.assertIs(result.status, Status.OPENING_CLOSING_ASSETS_ESTABLISHED)
        source = Path(qualifier.__file__).read_text()
        tree = ast.parse(source)
        calls = [node for node in ast.walk(tree) if isinstance(node, ast.Call)]
        names = [ast.unparse(node.func) for node in calls]
        for forbidden in ('float', 'datetime.now', 'date.today', 'time.time',
                          'requests.get', 'urlopen', '_capture_live'):
            self.assertFalse(any(name.endswith(forbidden) for name in names))
        self.assertEqual(len(list(Status)), 4)
        contract = Path(__file__).resolve().parents[1] / 'docs/contracts/v2/quality/CURRENT_ANNUAL_OPENING_CLOSING_ASSETS_QUALIFICATION.md'
        # The canonical isolated runner intentionally does not copy nested docs.
        if contract.exists():
            text = contract.read_text()
            for value in (qualifier.CONTRACT_VERSION, qualifier.QUALIFIER_VERSION, qualifier.AUTHORITY,
                          *(item.value for item in qualifier.CurrentAnnualOpeningClosingAssetsLimitation),
                          *(item.value for item in Reason)):
                self.assertIn(value, text)

    def test_each_instant_requires_its_own_usd_unit(self):
        for boundary in (OPENING, CLOSING):
            payload = payload_for()
            units = payload['facts']['us-gaap']['Assets']['units']
            foreign = next(row for row in units['USD'] if row['end'] == boundary)
            units['USD'].remove(foreign)
            units['CAD'] = [foreign]
            result = self.qualify(self.profile_for(payload))
            self.assertEqual(result.reasons, (Reason.EXACT_USD_UNIT_UNAVAILABLE,))
            self.assert_empty(result)

    def test_nonfinite_json_constants_and_duplicate_keys_fail_closed(self):
        for value in (b'NaN', b'Infinity', b'-Infinity', b'1e999999999999999999999999999'):
            content = b'{"cik":0,"facts":{"us-gaap":{"Assets":{"units":{"USD":[{"val":' + value + b'}]}}}}}'
            with tempfile.TemporaryDirectory() as temporary:
                archive = SecArchive(Path(temporary).resolve() / 'archive')
                receipt = archive._capture_live(content, cik='0000000000', captured_at=BOUNDARY_T1)
                with self.assertRaises((ArchiveError, ArithmeticError)):
                    extraction.extract_assets_liabilities(archive.read_object(receipt), receipt)
        with patch.object(qualifier, 'extract_assets_liabilities', side_effect=ArithmeticError('invalid decimal')):
            self.assertEqual(self.qualify().reasons, (Reason.CAPTURE_REPLAY_CONFLICT,))
        content = b'{"cik":0,"cik":1}'
        with tempfile.TemporaryDirectory() as temporary:
            archive = SecArchive(Path(temporary).resolve() / 'archive')
            receipt = archive._capture_live(content, cik='0000000000', captured_at=BOUNDARY_T1)
            with self.assertRaises(ArchiveError):
                extraction.extract_assets_liabilities(archive.read_object(receipt), receipt)

    def test_detached_selectors_and_malformed_native_graph_are_rejected(self):
        for keyword in ('cik', 'period_start', 'opening_balance_date', 'closing_balance_date',
                        'receipt', 'opening_assets', 'qualified'):
            with self.subTest(keyword=keyword), self.assertRaises(TypeError):
                qualifier.qualify_sec_current_annual_opening_closing_assets(
                    self.fixture.current_archive, self.available, **{keyword: None})
        for comp in (None, {}, self.available):
            forged = replace(self.available, upstream_comparability=comp)
            with self.assertRaises(Error):
                self.qualify(forged)


    def test_self_consistent_fabricated_series_dates_cannot_authenticate(self):
        comp = self.available.upstream_comparability
        security = comp.upstream_security_eps
        bridge = security.upstream_registered_listing_bridge
        temporal = bridge.temporal_boundary
        current = temporal.current_evidence
        series = current.resolution.series
        fabricated = replace(series, periods=series.periods[:-1] +
                             (replace(series.periods[-1], period_start='2024-01-02'),))
        current = replace(current, resolution=replace(current.resolution, series=fabricated))
        security = replace(security, upstream_registered_listing_bridge=replace(
            bridge, temporal_boundary=replace(temporal, current_evidence=current)))
        comp = replace(comp, upstream_security_eps=security,
                       period_decisions=qualifier._rebuild_comparable_periods(fabricated, comp.presentation),
                       c3_semantic_id=fabricated.semantic_hash, c3_evidence_id=fabricated.evidence_hash)
        profile = replace(self.available, upstream_comparability=comp,
                          expected_comparability_semantic_id=comp.semantic_id,
                          expected_comparability_evidence_id=comp.evidence_id)
        profile = qualifier._factory_reachable_profile(profile, comp)
        with self.assertRaises(Error):
            self.qualify(profile)



if __name__ == '__main__':
    unittest.main()
