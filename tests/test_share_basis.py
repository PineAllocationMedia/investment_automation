"""Split-only synthetic qualification: evidence, chronology and no-transformation gates."""
import ast
import builtins
from dataclasses import FrozenInstanceError, fields, replace
from decimal import Decimal, localcontext
import hashlib
import inspect
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import unittest
from unittest.mock import patch

from economic_facts import share_basis as s
from economic_facts import security_identity as i
from economic_facts.sec_eps_series import AdmissionBlocker
from tests import share_basis_fixtures as f
from tests import security_identity_fixtures as identities
from tests.sec_eps_series_fixtures import annual_rows

R = s.ShareBasisReason
O = s.ShareBasisOutcome


class ShareBasisTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.series = f.series_fixture()
        cls.identity, cls.witness = f.identity_fixture(cls.series)

    def setUp(self):
        self.claims = f.snapshot(self.series, self.identity)

    def qualify(self, claims=None, *, documents=None, request=None, identity=None, witness=None, series=None):
        return s.qualify_share_basis(series or self.series, identity or self.identity,
            request or f.request(self.series, self.identity), f.bundle(witness or self.witness,
                *(documents if documents is not None else (f.document(claims or self.claims),))))

    def check_invariants(self, result):
        self.assertEqual(len(result.period_decisions), 5)
        self.assertIs(result.authority, s.Authority.SYNTHETIC_TEST_ONLY)
        self.assertEqual(result.limitations, (R.SYNTHETIC_EVIDENCE_ONLY,))
        self.assertIs(result.transformation_mode, s.TransformationMode.NONE)
        self.assertEqual(set(result.downstream_blockers), set(self.series.downstream_admission_blockers))
        for period, decision in zip(self.series.periods, result.period_decisions):
            self.assertIs(decision.reported_value, period.value)
            self.assertEqual(decision.reported_value.as_tuple(), period.value.as_tuple())
            self.assertEqual(decision.annual_supporting_observation_ids, period.supporting_observation_ids)
            self.assertEqual(decision.filing_version_ids, period.version_ids)
            self.assertEqual({r.observation_id for r in decision.filing_version_observations},
                             {o for v in period.filing_versions for o in v.observation_ids})

    def success(self, claims=None, **kwargs):
        result = self.qualify(claims, **kwargs)
        self.assertIs(result.outcome, O.COMPARABLE_BASIS_ESTABLISHED, result.reasons)
        self.assertEqual(result.reasons, ())
        self.assertIsNotNone(result.qualified_target_basis)
        self.assertTrue(all(d.qualified_target_basis == result.qualified_target_basis for d in result.period_decisions))
        self.check_invariants(result)
        return result

    def blocked(self, claims=None, *reasons, **kwargs):
        result = self.qualify(claims, **kwargs)
        self.assertNotEqual(result.outcome, O.COMPARABLE_BASIS_ESTABLISHED)
        self.assertTrue(set(reasons) <= set(result.reasons), result.reasons)
        self.assertIsNone(result.qualified_target_basis)
        self.assertTrue(all(d.qualified_target_basis is None for d in result.period_decisions))
        self.assertTrue(all(d.blockers for d in result.period_decisions))
        self.check_invariants(result)
        return result

    def action_claims(self, *events):
        return f.snapshot(self.series, self.identity, events)

    def test_no_action_complete_coverage(self):
        result = self.success()
        self.assertEqual(len(result.epochs), 1)
        self.assertEqual(result.qualified_target_basis.basis_id, f.BASELINE)

    def test_no_action_incomplete_coverage(self):
        self.blocked(replace(self.claims, coverage=replace(self.claims.coverage, status=s.CoverageStatus.INCOMPLETE)),
                     R.CORPORATE_ACTION_COVERAGE_GAP)

    def test_empty_inventory_unknown_coverage(self):
        for coverage in (None, replace(self.claims.coverage, status=s.CoverageStatus.UNKNOWN)):
            self.blocked(replace(self.claims, coverage=coverage), R.CORPORATE_ACTION_COVERAGE_GAP)

    def test_empty_bundle(self):
        self.blocked(None, R.CORPORATE_ACTION_COVERAGE_GAP, documents=())

    def test_two_for_one_already_reflected_everywhere(self):
        result = self.success(self.action_claims(f.split()))
        self.assertEqual(len(result.epochs), 2)
        self.assertEqual(result.epochs[-1].split_ratio.new_units, 2)

    def test_three_for_two(self):
        self.success(self.action_claims(f.split(new=3, old=2)))

    def test_reverse_one_for_five(self):
        self.success(self.action_claims(f.split(new=1, old=5)))

    def test_multiple_ordered_splits(self):
        a, b = f.split(effective_at="2022-05-01"), f.split("two", 3, 2)
        claims = self.action_claims(a, b)
        result = self.success(replace(claims, events=(b, a)))
        self.assertEqual([e.event_id for e in result.epochs[1:]], [a.event_id, b.event_id])
        self.assertEqual(self.success(claims).semantic_hash, result.semantic_hash)

    def test_forward_then_numerical_inverse_remain_two_material_events(self):
        a, b = f.split(effective_at="2022-05-01"), f.split("two", 1, 2)
        result = self.success(self.action_claims(a, b))
        self.assertEqual(len(result.epochs), 3)
        self.assertNotEqual(result.epochs[0].semantic_hash, result.epochs[-1].semantic_hash)
        self.assertNotEqual(result.semantic_hash, self.success().semantic_hash)

    def test_split_after_latest_fiscal_end_is_target(self):
        event = f.split(effective_at="2025-03-15")
        self.assertGreater(event.effective_at, self.series.periods[-1].period_end)
        self.assertEqual(self.success(self.action_claims(event)).qualified_target_basis.event_id, event.event_id)

    def test_split_before_oldest_period_after_anchor_is_material(self):
        result = self.success(self.action_claims(f.split(effective_at="2019-06-01")))
        self.assertEqual(len(result.epochs), 2)

    def test_missing_baseline(self):
        self.blocked(replace(self.claims, baseline=None), R.BASELINE_BASIS_UNRESOLVED)

    def test_baseline_after_oldest_period(self):
        self.blocked(replace(self.claims, baseline=replace(self.claims.baseline, anchored_on="2020-01-02")),
                     R.BASELINE_BASIS_UNRESOLVED)

    def test_baseline_wrong_security_or_class(self):
        for change in (dict(security_anchor="synthetic:security:other"), dict(class_id="other"), dict(basis_id="ticker")):
            self.blocked(replace(self.claims, baseline=replace(self.claims.baseline, **change)), R.BASELINE_BASIS_UNRESOLVED)

    def test_coverage_starts_at_baseline_not_oldest_eps(self):
        self.blocked(replace(self.claims, coverage=replace(self.claims.coverage, start="2020-01-01")),
                     R.CORPORATE_ACTION_COVERAGE_GAP)

    def test_coverage_through_boundary_not_latest_fiscal_end(self):
        self.blocked(replace(self.claims, coverage=replace(self.claims.coverage, through="2024-12-31")),
                     R.CORPORATE_ACTION_COVERAGE_GAP)

    def test_coverage_all_categories_required_individually(self):
        for kind in s.CorporateActionKind:
            self.blocked(replace(self.claims, coverage=replace(self.claims.coverage,
                kinds=tuple(k for k in s.CorporateActionKind if k is not kind))), R.CORPORATE_ACTION_COVERAGE_GAP)

    def test_explicit_coverage_gap(self):
        gap = s.CoverageGap("2023-01-01", "2023-01-02", tuple(s.CorporateActionKind), "Fictional missing day")
        self.blocked(replace(self.claims, coverage=replace(self.claims.coverage, gaps=(gap,))),
                     R.CORPORATE_ACTION_COVERAGE_GAP)

    def test_partial_coverage_snapshots_never_stitched(self):
        a = replace(self.claims, coverage=replace(self.claims.coverage, through="2022-12-31"))
        b = replace(self.claims, coverage=replace(self.claims.coverage, start="2023-01-01"))
        self.blocked(None, R.CORPORATE_ACTION_COVERAGE_GAP, documents=(f.document(a), f.document(b)))

    def test_event_inventory_exactly_bound_to_coverage(self):
        claims = self.action_claims(f.split())
        self.blocked(replace(claims, coverage=replace(claims.coverage, event_ids=())), R.CORPORATE_ACTION_COVERAGE_GAP)
        self.blocked(replace(self.claims, coverage=replace(self.claims.coverage,
            event_ids=("synthetic:event:missing",))), R.CORPORATE_ACTION_COVERAGE_GAP)

    def test_announced_cancelled_never_implemented(self):
        a = f.split(lifecycle=s.EventLifecycle.ANNOUNCED, implementation=s.Implementation.NEVER_IMPLEMENTED,
                    effective_at=None, recorded_at="2026-02-25T12:00:00Z")
        b = replace(a, notice_id="synthetic:notice:cancel", lifecycle=s.EventLifecycle.CANCELLED,
                    recorded_at="2026-02-26T12:00:00Z",
                    relationships=(s.NoticeRelationship(s.NoticeRelationshipKind.SUPERSEDES, a.notice_id),))
        claims = f.snapshot(self.series, self.identity, (a, b), basis=f.BASELINE)
        result = self.success(claims)
        self.assertEqual(len(result.epochs), 1)
        self.assertIn(a.notice_id, result.excluded_notice_ids)
        self.assertIn(a.event_id, result.informational_event_ids)

    def test_cancellation_cannot_erase_implemented_event(self):
        a = f.split(recorded_at="2026-02-25T12:00:00Z")
        b = replace(a, notice_id="synthetic:notice:cancel", lifecycle=s.EventLifecycle.CANCELLED,
                    implementation=s.Implementation.NEVER_IMPLEMENTED, recorded_at="2026-02-26T12:00:00Z",
                    relationships=(s.NoticeRelationship(s.NoticeRelationshipKind.SUPERSEDES, a.notice_id),))
        result = self.blocked(self.action_claims(a, b), R.CORPORATE_ACTION_CONFLICT)
        self.assertIn(a, result.considered_events)

    def test_cancelled_unknown_implementation_blocks(self):
        self.blocked(self.action_claims(f.split(lifecycle=s.EventLifecycle.CANCELLED,
                     implementation=s.Implementation.UNRESOLVED)), R.EVENT_IMPLEMENTATION_UNCONFIRMED)

    def test_announced_or_approved_and_scheduled_date_passed_insufficient(self):
        for lifecycle in (s.EventLifecycle.ANNOUNCED, s.EventLifecycle.APPROVED):
            self.blocked(self.action_claims(f.split(lifecycle=lifecycle, implementation=s.Implementation.UNRESOLVED,
                effective_at=None, scheduled_at="2025-03-15")), R.EVENT_IMPLEMENTATION_UNCONFIRMED)

    def test_implementation_unconfirmed(self):
        self.blocked(self.action_claims(f.split(implementation=s.Implementation.UNRESOLVED)),
                     R.EVENT_IMPLEMENTATION_UNCONFIRMED)

    def test_missing_effective_date(self):
        self.blocked(self.action_claims(f.split(effective_at=None)), R.EVENT_EFFECTIVE_DATE_UNRESOLVED)

    def test_future_proposal_informational_with_complete_coverage(self):
        event = f.split(lifecycle=s.EventLifecycle.ANNOUNCED, implementation=s.Implementation.UNRESOLVED,
                        scheduled_at="2026-04-01", effective_at=None)
        claims = f.snapshot(self.series, self.identity, (event,), basis=f.BASELINE)
        result = self.success(claims)
        self.assertEqual(len(result.epochs), 1)
        self.blocked(replace(claims, coverage=None), R.CORPORATE_ACTION_COVERAGE_GAP)

    def test_future_confirmed_implementation_conflict(self):
        self.blocked(self.action_claims(f.split(effective_at="2026-04-01")), R.CORPORATE_ACTION_CONFLICT)

    def test_same_date_effective_boundary_not_midnight(self):
        self.blocked(self.action_claims(f.split(effective_at="2026-03-02")), R.EVENT_EFFECTIVE_DATE_UNRESOLVED)

    def test_same_day_explicit_instants_prove_order(self):
        a = f.split(effective_at="2025-03-15T10:00:00Z")
        b = f.split("two", effective_at="2025-03-15T11:00:00Z")
        self.assertEqual(len(self.success(self.action_claims(a, b)).epochs), 3)

    def test_same_date_distinct_events_unordered(self):
        self.blocked(self.action_claims(f.split(), f.split("two")), R.EVENT_ORDER_UNRESOLVED)

    def test_same_day_mixed_precision_unordered(self):
        self.blocked(self.action_claims(f.split(), f.split("two", effective_at="2025-03-15T11:00:00Z")),
                     R.EVENT_ORDER_UNRESOLVED)

    def test_same_timestamp_events_unordered(self):
        self.blocked(self.action_claims(f.split(effective_at="2025-03-15T11:00:00Z"),
                     f.split("two", effective_at="2025-03-15T11:00:00Z")), R.EVENT_ORDER_UNRESOLVED)

    def test_ambiguous_ratio_orientation(self):
        event = f.split(ratio=s.SplitRatio(2, 1, s.RatioOrientation.UNRESOLVED))
        self.blocked(self.action_claims(event), R.EVENT_TERMS_UNRESOLVED)

    def test_one_to_one_not_a_split(self):
        for terms in ((1, 1), (5, 5)):
            self.blocked(self.action_claims(f.split(new=terms[0], old=terms[1])), R.EVENT_TERMS_UNRESOLVED)

    def test_missing_ratio(self):
        self.blocked(self.action_claims(f.split(ratio=None)), R.EVENT_TERMS_UNRESOLVED)

    def test_ratio_direction_must_match_event_kind(self):
        self.blocked(self.action_claims(f.split(kind=s.CorporateActionKind.REVERSE_SPLIT)), R.EVENT_TERMS_UNRESOLVED)

    def test_conflicting_ratios_no_latest_winner(self):
        a = f.split()
        b = replace(a, notice_id="synthetic:notice:other", ratio=s.SplitRatio(3, 1, s.RatioOrientation.NEW_UNITS_PER_OLD_UNITS))
        self.blocked(self.action_claims(a, b), R.CORPORATE_ACTION_CONFLICT)

    def test_large_integer_terms_no_binary64(self):
        new, old = 10**100 + 1, 10**100
        result = self.success(self.action_claims(f.split(new=new, old=old)))
        self.assertEqual(result.epochs[-1].split_ratio.new_units, new)
        self.assertEqual(result.epochs[-1].split_ratio.old_units, old)

    def test_ratio_canonical_semantics_original_terms_retained(self):
        a, b = self.success(self.action_claims(f.split())), self.success(self.action_claims(f.split(new=4, old=2)))
        self.assertEqual(a.semantic_hash, b.semantic_hash)
        self.assertNotEqual(a.evidence_hash, b.evidence_hash)
        self.assertEqual(b.considered_events[0].ratio.new_units, 4)
        self.assertEqual(b.epochs[-1].split_ratio.new_units, 2)

    def test_malformed_ratio_scalars_raise_contract_error(self):
        for bad in (True, False, 0, -1, 2.0, "2", Decimal(2)):
            for field in ("new_units", "old_units"):
                ratio = replace(f.split().ratio, **{field: bad})
                source = f.document(self.action_claims(f.split()))
                claims = self.action_claims(f.split(ratio=ratio))
                with self.subTest(bad=bad, field=field), self.assertRaises(s.ShareBasisContractError):
                    self.qualify(documents=(replace(source, claims=claims),))

    def test_stock_dividend_unsupported(self):
        self.unsupported(s.CorporateActionKind.STOCK_DIVIDEND)

    def test_class_conversion_unsupported(self):
        self.unsupported(s.CorporateActionKind.SHARE_CLASS_CONVERSION)

    def test_recapitalization_unsupported(self):
        self.unsupported(s.CorporateActionKind.RECAPITALIZATION)

    def test_merger_exchange_unsupported(self):
        self.unsupported(s.CorporateActionKind.MERGER_SECURITY_EXCHANGE)

    def test_spinoff_unsupported(self):
        self.unsupported(s.CorporateActionKind.SPIN_OFF)

    def test_redenomination_unusual_consolidation_other_unsupported(self):
        for kind in (s.CorporateActionKind.REDENOMINATION, s.CorporateActionKind.UNUSUAL_CONSOLIDATION,
                     s.CorporateActionKind.OTHER_BASIS_AFFECTING):
            self.unsupported(kind)

    def unsupported(self, kind):
        result = self.blocked(self.action_claims(f.split(kind=kind)), R.UNSUPPORTED_CORPORATE_ACTION)
        self.assertIs(result.outcome, O.BASIS_UNSUPPORTED)
        self.assertIs(result.considered_events[0].kind, kind)

    def test_associated_restructuring_unsupported(self):
        self.blocked(self.action_claims(f.split(structure=s.ActionStructure.ASSOCIATED_RESTRUCTURING)),
                     R.UNSUPPORTED_CORPORATE_ACTION)

    def test_unresolved_action_structure(self):
        self.blocked(self.action_claims(f.split(structure=s.ActionStructure.UNRESOLVED)), R.EVENT_TERMS_UNRESOLVED)

    def test_cash_fractional_settlement_unsupported(self):
        result = self.blocked(self.action_claims(f.split(fractional_treatment=s.FractionalTreatment.CASH_SETTLEMENT)),
                             R.FRACTIONAL_SETTLEMENT_UNSUPPORTED)
        self.assertIs(result.outcome, O.BASIS_UNSUPPORTED)

    def test_fractional_treatment_unresolved(self):
        self.blocked(self.action_claims(f.split(fractional_treatment=s.FractionalTreatment.UNRESOLVED)),
                     R.FRACTIONAL_TREATMENT_UNRESOLVED)

    def test_security_continuation_unresolved(self):
        self.blocked(self.action_claims(f.split(continuation=s.SecurityContinuation.UNRESOLVED)),
                     R.SECURITY_CONTINUATION_UNRESOLVED)

    def test_event_another_security_or_class(self):
        for changes in (dict(security_anchor="synthetic:security:other"), dict(class_id="other")):
            self.blocked(self.action_claims(f.split(**changes)), R.EVENT_SECURITY_UNRESOLVED)

    def test_mixed_reported_bases(self):
        claims = self.action_claims(f.split())
        a = replace(claims.reported_bases[0], basis_id=f.BASELINE,
                    event_treatments=(s.EventTreatmentEvidence(f.split().event_id, s.ReportedEventTreatment.NOT_INCORPORATED),))
        self.blocked(replace(claims, reported_bases=(a,) + claims.reported_bases[1:]),
                     R.MIXED_REPORTED_BASES, R.BASIS_NORMALIZATION_REQUIRED)

    def test_all_known_different_basis_needs_normalization(self):
        claims = self.action_claims(f.split())
        changed = tuple(replace(c, basis_id=f.BASELINE, event_treatments=(
            s.EventTreatmentEvidence(f.split().event_id, s.ReportedEventTreatment.NOT_INCORPORATED),))
            for c in claims.reported_bases)
        result = self.blocked(replace(claims, reported_bases=changed), R.BASIS_NORMALIZATION_REQUIRED)
        self.assertTrue(all(d.compatibility is s.BasisCompatibility.DIFFERENT_BASIS for d in result.period_decisions))

    def test_unknown_basis_not_normalization(self):
        for basis in (None, "synthetic:basis:unproven"):
            claims = replace(self.claims, reported_bases=tuple(replace(c, basis_id=basis) for c in self.claims.reported_bases))
            result = self.blocked(claims, R.REPORTED_BASIS_UNRESOLVED)
            self.assertNotIn(R.BASIS_NORMALIZATION_REQUIRED, result.reasons)

    def test_missing_treatment_every_possible_observation(self):
        claims = self.action_claims(f.split())
        for n in range(len(claims.reported_bases)):
            changed = list(claims.reported_bases)
            changed[n] = replace(changed[n], event_treatments=())
            self.blocked(replace(claims, reported_bases=tuple(changed)), R.REPORTED_EVENT_TREATMENT_UNRESOLVED)

    def test_missing_basis_evidence_every_possible_observation(self):
        for n in range(len(self.claims.reported_bases)):
            self.blocked(replace(self.claims, reported_bases=self.claims.reported_bases[:n]
                + self.claims.reported_bases[n + 1:]), R.SUPPORTING_VERSION_COVERAGE_GAP)

    def test_explicit_enumeration_multiple_references_allowed(self):
        claim = replace(self.claims.reported_bases[0], references=f.references(self.series))
        self.success(replace(self.claims, reported_bases=(claim,)))

    def test_representative_only_cannot_establish_other_versions(self):
        representatives = {p.representative_observation_id for p in self.series.periods}
        self.blocked(replace(self.claims, reported_bases=tuple(c for c in self.claims.reported_bases
            if c.references[0].observation_id in representatives)), R.SUPPORTING_VERSION_COVERAGE_GAP)

    def test_cross_forms_not_promoted_to_annual_support(self):
        result = self.success()
        for p, d in zip(self.series.periods, result.period_decisions):
            self.assertEqual({v.form for v in p.filing_versions}, {"10-K", "8-K", "10-Q", "10-Q/A"})
            self.assertGreater(len(d.filing_version_observations), len(d.annual_supporting_observation_ids))

    def test_each_cross_form_requires_explicit_treatment(self):
        claims = self.action_claims(f.split())
        for form in ("8-K", "10-Q", "10-Q/A"):
            refs = {o for p in self.series.periods for v in p.filing_versions if v.form == form for o in v.observation_ids}
            changed = tuple(replace(c, event_treatments=()) if c.references[0].observation_id in refs else c
                            for c in claims.reported_bases)
            self.blocked(replace(claims, reported_bases=changed), R.REPORTED_EVENT_TREATMENT_UNRESOLVED)

    def test_partial_report_snapshots_never_stitched(self):
        a = replace(self.claims, reported_bases=self.claims.reported_bases[:12])
        b = replace(self.claims, reported_bases=self.claims.reported_bases[12:])
        self.blocked(None, R.SUPPORTING_VERSION_COVERAGE_GAP, documents=(f.document(a), f.document(b)))

    def test_unresolved_treatment(self):
        claims = self.action_claims(f.split())
        changed = tuple(replace(c, event_treatments=(s.EventTreatmentEvidence(f.split().event_id,
            s.ReportedEventTreatment.UNRESOLVED),)) for c in claims.reported_bases)
        self.blocked(replace(claims, reported_bases=changed), R.REPORTED_EVENT_TREATMENT_UNRESOLVED)

    def test_basis_and_treatment_contradiction(self):
        claims = self.action_claims(f.split())
        changed = tuple(replace(c, event_treatments=(s.EventTreatmentEvidence(f.split().event_id,
            s.ReportedEventTreatment.NOT_INCORPORATED),)) for c in claims.reported_bases)
        self.blocked(replace(claims, reported_bases=changed), R.REPORTED_BASIS_CONFLICT)

    def test_intermediate_epoch_requires_prefix_event_treatments(self):
        a, b = f.split(effective_at="2022-05-01"), f.split("two")
        claims = self.action_claims(a, b)
        changed = tuple(replace(c, basis_id=a.successor_basis_id, event_treatments=(
            s.EventTreatmentEvidence(a.event_id, s.ReportedEventTreatment.INCORPORATED),
            s.EventTreatmentEvidence(b.event_id, s.ReportedEventTreatment.NOT_INCORPORATED))) for c in claims.reported_bases)
        self.blocked(replace(claims, reported_bases=changed), R.BASIS_NORMALIZATION_REQUIRED)

    def test_conflicting_report_sources_retained(self):
        other = replace(self.claims, reported_bases=tuple(replace(c, basis_id=None) for c in self.claims.reported_bases))
        result = self.blocked(None, R.REPORTED_BASIS_CONFLICT, documents=(f.document(self.claims), f.document(other)))
        self.assertEqual(len(result.considered_evidence_ids), 2)

    def test_conflicting_complete_action_snapshots(self):
        self.blocked(None, R.CORPORATE_ACTION_CONFLICT,
            documents=(f.document(self.claims), f.document(self.action_claims(f.split()))))

    def test_correction_supersession_exact_notice(self):
        for relation in s.NoticeRelationshipKind:
            a = f.split(lifecycle=s.EventLifecycle.ANNOUNCED, implementation=s.Implementation.UNRESOLVED,
                        recorded_at="2025-01-01T12:00:00Z", effective_at=None)
            b = f.split(notice_id="synthetic:notice:implementation", relationships=(s.NoticeRelationship(relation, a.notice_id),))
            result = self.success(self.action_claims(a, b))
            self.assertIn(a.notice_id, result.excluded_notice_ids)
            self.assertIn(a, result.considered_events)

    def test_supersession_cycle_rejected(self):
        a = f.split(relationships=(s.NoticeRelationship(s.NoticeRelationshipKind.SUPERSEDES, "synthetic:notice:two"),))
        b = replace(a, notice_id="synthetic:notice:two", relationships=(s.NoticeRelationship(s.NoticeRelationshipKind.SUPERSEDES, a.notice_id),))
        with self.assertRaises(s.ShareBasisContractError):
            self.qualify(self.action_claims(a, b))

    def test_missing_or_cross_event_notice_reference(self):
        a = f.split(relationships=(s.NoticeRelationship(s.NoticeRelationshipKind.AMENDS, "synthetic:notice:missing"),))
        with self.assertRaises(s.ShareBasisContractError):
            self.qualify(self.action_claims(a))
        b = f.split("missing")
        with self.assertRaises(s.ShareBasisContractError):
            self.qualify(self.action_claims(a, b))

    def test_correction_chronology_must_follow_original(self):
        a = f.split()
        b = replace(a, notice_id="synthetic:notice:two", recorded_at="2025-01-01T12:00:00Z",
            relationships=(s.NoticeRelationship(s.NoticeRelationshipKind.AMENDS, a.notice_id),))
        with self.assertRaises(s.ShareBasisContractError):
            self.qualify(self.action_claims(a, b))

    def test_reused_successor_basis_fails(self):
        self.blocked(self.action_claims(f.split(successor_basis_id=f.BASELINE)), R.CORPORATE_ACTION_CONFLICT)

    def test_historical_mode_unsupported_five_decisions(self):
        result = self.blocked(None, R.HISTORICAL_BASIS_UNSUPPORTED,
            request=f.request(self.series, self.identity, mode=s.ShareBasisMode.HISTORICAL_AS_OF))
        self.assertIs(result.outcome, O.BASIS_UNSUPPORTED)

    def test_identity_exact_replay_success(self):
        with patch.object(s, "qualify_security_identity", wraps=i.qualify_security_identity) as replay:
            self.success()
        replay.assert_called_once_with(self.series, self.witness.request, self.witness.evidence)

    def test_failed_exact_identity_returns_unavailable(self):
        identity, witness = f.identity_fixture(self.series, claims=replace(identities.snapshot(self.series), continuity=i.Continuity.UNRESOLVED))
        claims = f.snapshot(self.series, identity)
        self.blocked(claims, R.SECURITY_IDENTITY_NOT_QUALIFIED, identity=identity, witness=witness,
                     request=f.request(self.series, identity))

    def test_mutated_identity_every_field_rejected(self):
        for field, value in (("semantic_hash", "f" * 64), ("evidence_hash", "f" * 64),
                             ("qualification_as_of", "2026-03-03T12:00:00Z"), ("reasons", (i.IdentityReason.IDENTITY_EVIDENCE_CONFLICT,)),
                             ("downstream_blockers", ()), ("security", None), ("considered_evidence_ids", ())):
            identity = replace(self.identity, **{field: value})
            with self.subTest(field=field), self.assertRaises(s.ShareBasisContractError):
                self.qualify(identity=identity, request=f.request(self.series, identity))

    def test_identity_mutated_nested_descriptive_value_rejected(self):
        identity = replace(self.identity, issuer=replace(self.identity.issuer, descriptive_names=("Changed",)))
        with self.assertRaises(s.ShareBasisContractError):
            self.qualify(identity=identity)

    def test_series_value_mutation_with_unchanged_hashes_rejected_by_replay(self):
        period = replace(self.series.periods[0], value=Decimal("999"))
        with self.assertRaises(s.ShareBasisContractError):
            self.qualify(series=replace(self.series, periods=(period,) + self.series.periods[1:]))

    def test_broken_series_inventory_rejected_by_profile(self):
        period = replace(self.series.periods[0], supporting_observation_ids=())
        with self.assertRaises(s.ShareBasisContractError):
            self.qualify(series=replace(self.series, periods=(period,) + self.series.periods[1:]))

    def test_later_capture_cannot_extend_identity_validity(self):
        claims = replace(self.claims, coverage=replace(self.claims.coverage, through="2026-03-03"))
        result = self.blocked(None, R.IDENTITY_BOUNDARY_NOT_QUALIFIED,
            documents=(f.document(claims, captured_at="2026-03-03T12:00:00Z"),))
        self.assertEqual(result.qualification_boundary, "2026-03-03T12:00:00Z")

    def test_new_exact_identity_replay_can_cover_new_boundary(self):
        timestamp = "2026-03-03T12:00:00Z"
        identity, witness = f.identity_fixture(self.series, captured_at=timestamp)
        claims = f.snapshot(self.series, identity)
        claims = replace(claims, coverage=replace(claims.coverage, through="2026-03-03"))
        self.success(documents=(f.document(claims, captured_at=timestamp),), identity=identity,
                     witness=witness, request=f.request(self.series, identity))

    def test_intraday_identity_extension_fails_even_same_calendar_date(self):
        self.blocked(None, R.IDENTITY_BOUNDARY_NOT_QUALIFIED,
            documents=(f.document(self.claims, captured_at="2026-03-02T12:00:00.000001Z"),))

    def test_series_authority_and_identity_boundary_floor(self):
        result = self.success(documents=(f.document(self.claims, published_at="2026-02-27T12:00:00Z",
            available_at="2026-02-27T12:00:00Z", captured_at="2026-02-27T12:00:00Z"),))
        self.assertEqual(result.qualification_boundary, self.identity.qualification_as_of)

    def test_byte_hash_tampering(self):
        source = f.document(self.claims)
        for change in (dict(source_bytes=source.source_bytes + b" "), dict(content_sha256="0" * 64)):
            with self.assertRaises(s.ShareBasisContractError):
                self.qualify(documents=(replace(source, **change),))

    def test_locator_tampering(self):
        with self.assertRaises(s.ShareBasisContractError):
            self.qualify(documents=(replace(f.document(self.claims), source_locator="/other"),))

    def test_chronology_tampering_detected_even_when_order_still_valid(self):
        with self.assertRaises(s.ShareBasisContractError):
            self.qualify(documents=(replace(f.document(self.claims), captured_at="2026-03-03T12:00:00Z"),))

    def test_invalid_chronology_in_fictional_bytes(self):
        for change in (dict(available_at="2026-03-03T12:00:00Z"), dict(captured_at="2026-03-02"),
                       dict(published_at="2026-03-02T12:00:00Z")):
            with self.assertRaises(s.ShareBasisContractError):
                self.qualify(documents=(f.document(self.claims, **change),))

    def test_detached_claims_rejected(self):
        with self.assertRaises(s.ShareBasisContractError):
            self.qualify(documents=(replace(f.document(self.claims), claims=replace(self.claims, baseline=None)),))

    def test_unknown_source_fields_duplicate_keys_and_float_ratios_rejected(self):
        source = f.document(self.action_claims(f.split()))
        parsed = json.loads(source.source_bytes)
        parsed["override"] = True
        for raw in (json.dumps(parsed).encode(), b'{"claims":{},"claims":{}}', b'{"claims":NaN}',
                    source.source_bytes.replace(b'"new_units":2', b'"new_units":2.0')):
            with self.assertRaises(s.ShareBasisContractError):
                self.qualify(documents=(replace(source, source_bytes=raw, content_sha256=hashlib.sha256(raw).hexdigest()),))

    def test_broken_request_and_source_hash_linkage(self):
        for field in ("series_semantic_hash", "series_evidence_hash", "identity_semantic_hash", "identity_evidence_hash"):
            with self.assertRaises(s.ShareBasisContractError):
                self.qualify(request=replace(f.request(self.series, self.identity), **{field: "f" * 64}))
            with self.assertRaises(s.ShareBasisContractError):
                self.qualify(replace(self.claims, **{field: "f" * 64}))

    def test_unknown_observation_or_version_is_contract_error(self):
        claim = self.claims.reported_bases[0]
        for field in ("observation_id", "version_id", "period_start", "period_end"):
            ref = replace(claim.references[0], **{field: "forged"})
            with self.assertRaises(s.ShareBasisContractError):
                self.qualify(replace(self.claims, reported_bases=(replace(claim, references=(ref,)),)))

    def test_unknown_event_treatment_linkage(self):
        claim = replace(self.claims.reported_bases[0], event_treatments=(
            s.EventTreatmentEvidence("synthetic:event:forged", s.ReportedEventTreatment.INCORPORATED),))
        with self.assertRaises(s.ShareBasisContractError):
            self.qualify(replace(self.claims, reported_bases=(claim,)))

    def test_attempted_adjustment_and_caller_overrides_closed(self):
        req = f.request(self.series, self.identity)
        for field in ("adjusted_eps", "adjustment_factor", "transform", "as_of", "price", "portfolio", "quality", "durability", "allocation"):
            with self.assertRaises(TypeError):
                s.ShareBasisRequest(**{f.name: getattr(req, f.name) for f in fields(req)}, **{field: 1})
        for value in ("NORMALIZE", "NONE", 1, True, lambda x: x):
            with self.assertRaises(s.ShareBasisContractError):
                self.qualify(request=replace(req, transformation_mode=value))
        self.assertEqual(list(s.TransformationMode), [s.TransformationMode.NONE])
        self.assertEqual(list(s.Authority), [s.Authority.SYNTHETIC_TEST_ONLY])
        self.assertEqual(list(inspect.signature(s.qualify_share_basis).parameters), ["series", "identity", "request", "evidence"])

    def test_mutable_inputs_and_subclasses(self):
        class Subrequest(s.ShareBasisRequest):
            pass
        req = f.request(self.series, self.identity)
        with self.assertRaises(s.ShareBasisContractError):
            self.qualify(request=Subrequest(*(getattr(req, f.name) for f in fields(req))))
        for change in (dict(events=[]), dict(reported_bases=list(self.claims.reported_bases))):
            with self.assertRaises(s.ShareBasisContractError):
                self.qualify(documents=(replace(f.document(self.claims), claims=replace(self.claims, **change)),))
        with self.assertRaises(s.ShareBasisContractError):
            s.qualify_share_basis(self.series, self.identity, req, replace(f.bundle(self.witness), documents=[]))

    def test_results_and_evidence_are_frozen_and_slotted(self):
        result = self.success()
        for value in (result, result.period_decisions[0], self.claims, self.witness, result.epochs[0]):
            self.assertFalse(hasattr(value, "__dict__"))
            with self.assertRaises(FrozenInstanceError):
                setattr(value, fields(value)[0].name, None)

    def test_duplicate_and_reordered_documents_stability(self):
        a = f.document(self.claims)
        b = f.document(self.claims, source_reference="synthetic:document:two")
        self.assertEqual(self.qualify(documents=(a, b)), self.qualify(documents=(b, a, a)))

    def test_reordered_claims_and_duplicates_semantics(self):
        a, b = f.split(effective_at="2022-01-01"), f.split("two")
        claims = self.action_claims(a, b)
        other = replace(claims, events=(b, a, a), reported_bases=tuple(replace(c,
            event_treatments=c.event_treatments[::-1]) for c in claims.reported_bases[::-1]) + (claims.reported_bases[0],),
            coverage=replace(claims.coverage, kinds=claims.coverage.kinds[::-1], event_ids=claims.coverage.event_ids[::-1]))
        self.assertEqual(self.success(claims).semantic_hash, self.success(other).semantic_hash)

    def test_equivalent_source_bytes_semantics_evidence_separate(self):
        source = f.document(self.claims)
        raw = json.dumps(json.loads(source.source_bytes), indent=2).encode()
        changed = replace(source, source_bytes=raw, content_sha256=hashlib.sha256(raw).hexdigest())
        a, b = self.qualify(documents=(source,)), self.qualify(documents=(changed,))
        self.assertEqual(a.semantic_hash, b.semantic_hash)
        self.assertNotEqual(a.evidence_hash, b.evidence_hash)

    def test_source_locator_version_and_capture_bound_in_evidence(self):
        a = self.success()
        b = self.success(documents=(f.document(self.claims, source_reference="synthetic:document:two"),))
        self.assertEqual(a.semantic_hash, b.semantic_hash)
        self.assertNotEqual(a.evidence_hash, b.evidence_hash)
        for field in ("source_version", "extraction_version", "source_locator"):
            with self.assertRaises(s.ShareBasisContractError):
                self.qualify(documents=(f.document(self.claims, **{field: "unknown"}),))

    def test_semantic_hash_sensitive_to_ratio_and_effective_chronology(self):
        base = self.success(self.action_claims(f.split()))
        for event in (f.split(new=3), f.split(effective_at="2025-03-16")):
            self.assertNotEqual(base.semantic_hash, self.success(self.action_claims(event)).semantic_hash)

    def test_failure_evidence_binds_exclusions_and_conflicts(self):
        a = self.blocked(replace(self.claims, coverage=None), R.CORPORATE_ACTION_COVERAGE_GAP)
        b = self.blocked(replace(self.claims, coverage=replace(self.claims.coverage, status=s.CoverageStatus.INCOMPLETE)),
                         R.CORPORATE_ACTION_COVERAGE_GAP)
        self.assertNotEqual(a.evidence_hash, b.evidence_hash)

    def test_positive_zero_negative_decimals_preserved_every_period_success_failure(self):
        for n in range(5):
            for value in (0, -2, 7):
                rows = annual_rows()
                rows[n]["val"] = value
                series = identities.resolve_series_fixture(rows).series
                identity, witness = f.identity_fixture(series)
                claims = f.snapshot(series, identity)
                for changed in (claims, replace(claims, coverage=None)):
                    result = s.qualify_share_basis(series, identity, f.request(series, identity),
                        f.bundle(witness, f.document(changed)))
                    for p, d in zip(series.periods, result.period_decisions):
                        self.assertIs(d.reported_value, p.value)
                        self.assertEqual(d.reported_value.as_tuple(), p.value.as_tuple())

    def test_decimal_context_independence(self):
        claims = self.action_claims(f.split(new=10**80 + 1, old=10**80))
        with localcontext() as ctx:
            ctx.prec = 2
            for signal in ctx.traps:
                ctx.traps[signal] = True
            first = self.qualify(claims)
        self.assertEqual(first, self.qualify(claims))

    def test_no_real_admission_blocker_discharged(self):
        result = self.success()
        for blocker in (AdmissionBlocker.SPLIT_BASIS_NOT_ESTABLISHED,
                        AdmissionBlocker.ECONOMIC_COMPARABILITY_NOT_ESTABLISHED,
                        AdmissionBlocker.SECURITY_SHARE_CLASS_AND_LISTING_NOT_ESTABLISHED):
            self.assertIn(blocker, result.downstream_blockers)

    def test_no_network_io_clock_environment_or_subprocess(self):
        source = f.document(self.claims)
        with patch.object(socket, "socket", side_effect=AssertionError), \
             patch.object(builtins, "open", side_effect=AssertionError), \
             patch.object(Path, "write_text", side_effect=AssertionError), \
             patch.object(os, "getenv", side_effect=AssertionError), \
             patch.object(subprocess, "run", side_effect=AssertionError):
            self.success(documents=(source,))

    def test_static_capability_boundary_no_eps_arithmetic(self):
        text = inspect.getsource(s)
        tree = ast.parse(text)
        allowed = {"dataclasses", "datetime", "decimal", "enum", "functools", "hashlib", "json", "math", "re", "types", "typing"}
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                self.assertTrue(all(a.name in allowed for a in node.names))
            if isinstance(node, ast.ImportFrom):
                self.assertTrue(node.module in allowed or (node.level == 1 and node.module in
                    {None, "sec_eps_series", "security_identity"}))
            if isinstance(node, ast.BinOp):
                self.assertNotIsInstance(node.op, (ast.Mult, ast.Div, ast.Pow))
                if isinstance(node.op, ast.FloorDiv):
                    self.assertIsInstance(node.left, ast.Attribute)
                    self.assertIn(node.left.attr, ("new_units", "old_units"))
            if isinstance(node, ast.Call):
                name = node.func.id if isinstance(node.func, ast.Name) else node.func.attr if isinstance(node.func, ast.Attribute) else ""
                self.assertNotIn(name, {"float", "normalize", "quantize", "Decimal", "open", "write", "now", "today", "getenv",
                                       "run", "eval", "exec", "__import__"})
        for forbidden in ("yfinance", "adjusted_eps", "adjustment_factor", "src.", "portfolio", "allocation", "price_provider"):
            self.assertNotIn(forbidden, text)

    def test_hash_seed_process_determinism(self):
        script = '''from tests import share_basis_fixtures as f
from economic_facts.share_basis import qualify_share_basis
import sys
series = f.series_fixture()
identity, witness = f.identity_fixture(series)
result = qualify_share_basis(series, identity, f.request(series, identity),
    f.bundle(witness, f.document(f.snapshot(series, identity, (f.split(),)))))
assert not any(n.startswith(('src.', 'economic_facts.sec_acquisition')) for n in sys.modules)
print(result.semantic_hash, result.evidence_hash)
'''
        outputs = [subprocess.check_output([sys.executable, "-B", "-c", script],
                   env={**os.environ, "PYTHONHASHSEED": seed}, text=True) for seed in ("1", "73")]
        self.assertEqual(*outputs)

    def test_subsecond_chronology_not_lexicographic_order(self):
        a = f.split(effective_at="2025-03-15T10:00:00Z")
        b = f.split("two", effective_at="2025-03-15T10:00:00.000001Z")
        result = self.success(self.action_claims(a, b))
        self.assertEqual([e.event_id for e in result.epochs[1:]], [a.event_id, b.event_id])

    def test_explicit_intraday_implementation_at_boundary(self):
        event = f.split(effective_at="2026-03-02T11:00:00Z", recorded_at="2026-03-02T11:30:00Z")
        source = f.document(self.action_claims(event), published_at=f.CAPTURED, available_at=f.CAPTURED)
        self.success(documents=(source,))

    def test_same_day_date_only_implementation_notice_cannot_invent_time(self):
        event = f.split(effective_at="2025-03-15", recorded_at="2025-03-15T12:00:00Z")
        self.blocked(self.action_claims(event), R.EVENT_IMPLEMENTATION_UNCONFIRMED)

    def test_cancelled_or_future_event_cannot_be_claimed_incorporated(self):
        for event in (f.split(lifecycle=s.EventLifecycle.CANCELLED, implementation=s.Implementation.NEVER_IMPLEMENTED),
                      f.split(lifecycle=s.EventLifecycle.ANNOUNCED, implementation=s.Implementation.UNRESOLVED,
                              effective_at=None, scheduled_at="2026-04-01")):
            claims = f.snapshot(self.series, self.identity, (event,), basis=f.BASELINE)
            changed = tuple(replace(c, event_treatments=(s.EventTreatmentEvidence(event.event_id,
                s.ReportedEventTreatment.INCORPORATED),)) for c in claims.reported_bases)
            self.blocked(replace(claims, reported_bases=changed), R.REPORTED_BASIS_CONFLICT)

    def test_known_event_before_anchor_is_retained_in_baseline(self):
        event = f.split(effective_at="2018-06-01")
        result = self.success(f.snapshot(self.series, self.identity, (event,), basis=f.BASELINE))
        self.assertEqual(len(result.epochs), 1)
        self.assertIn(event.event_id, result.informational_event_ids)
        self.assertIn(event, result.considered_events)

    def test_event_at_baseline_date_is_ambiguous(self):
        self.blocked(self.action_claims(f.split(effective_at="2019-01-01")), R.BASELINE_BASIS_UNRESOLVED)

    def test_valid_bytes_with_nonpositive_ratio_still_contract_error(self):
        for new, old in ((0, 1), (1, 0), (-1, 2), (2, -1)):
            with self.assertRaises(s.ShareBasisContractError):
                self.qualify(self.action_claims(f.split(new=new, old=old)))

    def test_unknown_enums_in_nested_inputs(self):
        source = f.document(self.action_claims(f.split()))
        for change in (dict(lifecycle="EFFECTIVE"), dict(implementation=True), dict(kind="STOCK_SPLIT"),
                       dict(fractional_treatment="NONE")):
            with self.assertRaises(s.ShareBasisContractError):
                self.qualify(documents=(replace(source, claims=self.action_claims(f.split(**change))),))

    def test_unknown_contract_versions_and_real_authority_rejected(self):
        with self.assertRaises(s.ShareBasisContractError):
            self.qualify(request=f.request(self.series, self.identity, contract_version="other"))
        with self.assertRaises(s.ShareBasisContractError):
            self.qualify(documents=(replace(f.document(self.claims), authority="REAL"),))
        with self.assertRaises(s.ShareBasisContractError):
            s.qualify_share_basis(self.series, self.identity, f.request(self.series, self.identity),
                replace(f.bundle(self.witness), contract_version="other"))

    def test_invalid_dates_and_reversed_intervals_raise(self):
        for claims in (replace(self.claims, baseline=replace(self.claims.baseline, anchored_on="2019-1-01")),
                       replace(self.claims, coverage=replace(self.claims.coverage, start="2027-01-01")),
                       self.action_claims(f.split(effective_at="2025-02-30"))):
            with self.assertRaises(s.ShareBasisContractError):
                self.qualify(claims)

    def test_notice_published_after_document_rejected(self):
        with self.assertRaises(s.ShareBasisContractError):
            self.qualify(self.action_claims(f.split(recorded_at="2026-03-03T12:00:00Z")))

    def test_identity_witness_byte_tampering_rejected(self):
        doc = self.witness.evidence.documents[0]
        witness = replace(self.witness, evidence=replace(self.witness.evidence,
            documents=(replace(doc, source_bytes=doc.source_bytes + b" "),)))
        with self.assertRaises(s.ShareBasisContractError):
            self.qualify(witness=witness)

    def test_identity_witness_wrong_target_rejected(self):
        witness = replace(self.witness, request=replace(self.witness.request, security_anchor="synthetic:security:other"))
        with self.assertRaises(s.ShareBasisContractError):
            self.qualify(witness=witness)

    def test_conflicting_treatments_in_one_exact_disclosure(self):
        claims = self.action_claims(f.split())
        claim = claims.reported_bases[0]
        changed = replace(claim, event_treatments=claim.event_treatments + (
            s.EventTreatmentEvidence(f.split().event_id, s.ReportedEventTreatment.NOT_INCORPORATED),))
        self.blocked(replace(claims, reported_bases=(changed,) + claims.reported_bases[1:]), R.REPORTED_BASIS_CONFLICT)

    def test_report_claim_wrong_security_or_class_blocks(self):
        for changes in (dict(security_anchor="synthetic:security:other"), dict(class_id="other")):
            claim = replace(self.claims.reported_bases[0], **changes)
            self.blocked(replace(self.claims, reported_bases=(claim,) + self.claims.reported_bases[1:]), R.REPORTED_BASIS_CONFLICT)

    def test_repeated_qualification_is_idempotent_and_not_a_transform_pipeline(self):
        claims = self.action_claims(f.split())
        a = self.success(claims)
        self.assertEqual(a, self.success(claims))
        with self.assertRaises(s.ShareBasisContractError):
            self.qualify(series=a)

    def test_high_precision_eps_from_real_upstream_fixture_pipeline(self):
        from economic_facts.sec_archive import SecArchive
        from economic_facts.sec_eps_series import resolve_annual_diluted_eps
        from tests.sec_eps_series_fixtures import request as series_request
        from tests.sec_filing_fixtures import raw, source, CIK, T2
        import tempfile
        content = raw(source(annual_rows())).replace(b'"val":6', b'"val":-6.123456789012345678901234567890123456789')
        with tempfile.TemporaryDirectory() as temporary:
            archive = SecArchive(Path(temporary).resolve() / "archive")
            receipt = archive.capture(content, cik=CIK, captured_at=T2, source_locator="fixture:exact-decimal")
            series = resolve_annual_diluted_eps(archive, series_request(receipt)).series
        identity, witness = f.identity_fixture(series)
        evidence = f.bundle(witness, f.document(f.snapshot(series, identity, (f.split(),))))
        first = s.qualify_share_basis(series, identity, f.request(series, identity), evidence)
        with localcontext() as ctx:
            ctx.prec = 2
            for signal in ctx.traps:
                ctx.traps[signal] = True
            second = s.qualify_share_basis(series, identity, f.request(series, identity), evidence)
        self.assertEqual(first, second)
        self.assertIs(first.period_decisions[-1].reported_value, series.periods[-1].value)
        self.assertEqual(first.period_decisions[-1].reported_value,
                         Decimal("-6.123456789012345678901234567890123456789"))

    def test_exact_decimal_spelling_in_period_decision(self):
        # PR4C3 normally canonicalizes spelling. This remains structurally valid
        # upstream input, witnessed anew by PR4C4, to exercise exact pass-through.
        for value in (Decimal("-0.000"), Decimal("6.000"), Decimal("-2.5000")):
            series = replace(self.series, periods=tuple(replace(p, value=value) for p in self.series.periods))
            semantic = dict(contract=series.contract_version, resolver=series.resolver_version,
                cik=series.cik, namespace=series.namespace, concept=series.concept, unit=series.unit,
                accounting_basis=series.accounting_basis, mode=series.mode, period_policy=series.period_policy,
                periods=[(p.period_start, p.period_end, p.value) for p in series.periods])
            series = replace(series, semantic_hash=s.series_profile._hash(semantic))
            identity, witness = f.identity_fixture(series)
            result = s.qualify_share_basis(series, identity, f.request(series, identity),
                f.bundle(witness, f.document(f.snapshot(series, identity))))
            self.assertIs(result.outcome, O.COMPARABLE_BASIS_ESTABLISHED)
            self.assertTrue(all(d.reported_value is value for d in result.period_decisions))
            self.assertTrue(all(d.reported_value.as_tuple() == value.as_tuple() for d in result.period_decisions))

    def test_forged_series_semantic_hash_rejected_even_after_identity_replay(self):
        series = replace(self.series, semantic_hash="f" * 64)
        identity, witness = f.identity_fixture(series)
        with self.assertRaises(s.ShareBasisContractError):
            s.qualify_share_basis(series, identity, f.request(series, identity),
                f.bundle(witness, f.document(f.snapshot(series, identity))))
