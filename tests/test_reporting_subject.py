"""Reporting-subject mechanics, provenance/replay attacks and scope boundaries."""
import ast
import builtins
from dataclasses import FrozenInstanceError, fields, replace
from decimal import Decimal, localcontext
from enum import Enum
import hashlib
import inspect
import json
import socket
import unittest
from unittest.mock import patch

from economic_facts import reporting_subject as r
from economic_facts import share_basis as s
from economic_facts import security_identity as i
from economic_facts.sec_eps_series import AdmissionBlocker
from tests import reporting_subject_fixtures as f
from tests import share_basis_fixtures as basis
from tests import security_identity_fixtures as identities

R = r.ReportingSubjectReason
O = r.ComparabilityOutcome


class ReportingSubjectTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.chain = f.upstream()
        cls.series, cls.identity, cls.basis, cls.witness = cls.chain

    def setUp(self):
        self.claims = f.snapshot(self.series)

    def qualify(self, claims=None, *, documents=None, request=None, chain=None, evidence=None):
        series, identity, share_basis, witness = chain or self.chain
        return r.qualify_reporting_subject(series, identity, share_basis,
            request or f.request(series, identity, share_basis), evidence or f.bundle(witness,
                *(documents if documents is not None else (f.document(claims or f.snapshot(series)),))))

    def invariants(self, result, series=None):
        series = series or self.series
        self.assertEqual(len(result.period_decisions), 5)
        self.assertIs(result.authority, r.Authority.SYNTHETIC_TEST_ONLY)
        self.assertEqual(result.limitations, (R.SYNTHETIC_EVIDENCE_ONLY,))
        self.assertEqual(set(result.downstream_blockers), set(series.downstream_admission_blockers))
        for decision, period in zip(result.period_decisions, series.periods):
            self.assertIs(decision.reported_value, period.value)
            self.assertEqual(decision.reported_value.as_tuple(), period.value.as_tuple())
            self.assertEqual(decision.annual_supporting_observation_ids, period.supporting_observation_ids)
            self.assertEqual(decision.filing_version_ids, period.version_ids)
            self.assertEqual(set(decision.filing_version_observations), set(r._references(period)))

    def success(self, claims=None, **kwargs):
        result = self.qualify(claims, **kwargs)
        self.assertIs(result.outcome, O.COMPARABLE_WITHIN_SYNTHETIC_SCOPE, result.reasons)
        self.assertEqual(result.reasons, ())
        self.assertIsNotNone(result.qualified_subject_anchor)
        self.assertTrue(all(d.qualified_subject_anchor == result.qualified_subject_anchor
                            for d in result.period_decisions))
        self.invariants(result, kwargs.get("chain", self.chain)[0])
        return result

    def blocked(self, claims=None, *reasons, **kwargs):
        result = self.qualify(claims, **kwargs)
        self.assertNotEqual(result.outcome, O.COMPARABLE_WITHIN_SYNTHETIC_SCOPE)
        self.assertTrue(set(reasons) <= set(result.reasons), result.reasons)
        for name in ("qualified_subject_anchor", "qualified_issuer_anchor", "qualified_security_anchor",
                     "qualified_class_id", "qualified_share_basis_semantic_hash"):
            self.assertIsNone(getattr(result, name))
        self.assertTrue(all(d.qualified_subject_anchor is None for d in result.period_decisions))
        self.invariants(result, kwargs.get("chain", self.chain)[0])
        return result

    def test_continuous_positive_history(self):
        result = self.success()
        self.assertEqual(result.qualified_subject_anchor, f.SUBJECT)
        self.assertEqual(result.qualified_share_basis_semantic_hash, self.basis.qualified_target_basis.semantic_hash)

    def test_zero_eps(self):
        self.success(chain=f.upstream(f.signed_series(0)))

    def test_negative_eps(self):
        self.success(chain=f.upstream(f.signed_series(-7)))

    def test_exact_decimal_and_low_precision_context(self):
        chain = f.upstream(f.signed_series(Decimal("-0.123456789012345678901234567890")))
        with localcontext() as context:
            context.prec = 3
            self.success(chain=chain)

    def test_signed_zero_representation(self):
        self.success(chain=f.upstream(f.signed_series(Decimal("-0.000"))))

    def same_subject_event(self, name):
        # An event is descriptive source provenance, deliberately not an economic
        # transaction input or a condition that changes the subject anchor.
        return self.success(documents=(f.document(self.claims, source_reference="synthetic:document:" + name),))

    def test_ordinary_acquisition(self):
        self.same_subject_event("ordinary-acquisition")

    def test_ordinary_divestiture(self):
        self.same_subject_event("ordinary-divestiture")

    def test_normal_accounting_policy_change(self):
        self.same_subject_event("normal-policy-change")

    def test_discontinued_operations_total_eps(self):
        result = self.same_subject_event("total-eps-includes-discontinued")
        self.assertEqual(result.measurement_profile, r.MEASUREMENT_PROFILE)

    def test_transition_before_required_interval(self):
        original = self.claims.spans[0]
        claims = replace(self.claims, spans=(
            replace(original, effective_start="2017-01-01", effective_end="2018-12-31", references=()),
            replace(original, subject_anchor=f.SUCCESSOR, effective_start="2019-01-01")))
        self.assertEqual(self.success(claims).qualified_subject_anchor, f.SUCCESSOR)

    def test_transition_inside_history(self):
        self.blocked(f.transition(self.series), R.REPORTING_SUBJECT_DISCONTINUITY)

    def test_reverse_acquisition_subject_reset(self):
        self.blocked(f.transition(self.series), R.REPORTING_SUBJECT_DISCONTINUITY,
                     documents=(f.document(f.transition(self.series),
                         source_reference="synthetic:document:reverse-acquisition-reset"),))

    def test_carve_out_subject_replacement(self):
        self.blocked(f.transition(self.series), R.REPORTING_SUBJECT_DISCONTINUITY,
                     documents=(f.document(f.transition(self.series),
                         source_reference="synthetic:document:carve-out-replacement"),))

    def test_transition_after_latest_eps(self):
        self.blocked(f.transition(self.series, "2025-06-01", "2025-05-31"),
                     R.REPORTING_SUBJECT_DISCONTINUITY)

    def test_transition_on_boundary_date(self):
        self.blocked(f.transition(self.series, "2026-03-02", "2026-03-01"),
                     R.REPORTING_SUBJECT_DISCONTINUITY)

    def test_transition_after_boundary(self):
        claims = replace(self.claims, spans=(*self.claims.spans,
            replace(self.claims.spans[0], subject_anchor=f.SUCCESSOR,
                effective_start="2026-03-03", effective_end="2027-01-01", references=())))
        self.success(claims)

    def test_same_numbers_different_subjects(self):
        chain = f.upstream(f.signed_series(2))
        self.blocked(f.transition(chain[0]), R.REPORTING_SUBJECT_DISCONTINUITY, chain=chain)

    def test_full_cross_form_lineage(self):
        self.assertEqual({v.form for p in self.series.periods for v in p.filing_versions},
                         {"10-K", "8-K", "10-Q", "10-Q/A"})
        self.success()

    def test_representative_only(self):
        refs = tuple(ref for ref in self.claims.spans[0].references
                     if any(ref.observation_id == p.representative_observation_id for p in self.series.periods))
        self.blocked(replace(self.claims, spans=(replace(self.claims.spans[0], references=refs),)),
                     R.REPORTING_SUBJECT_COVERAGE_INCOMPLETE)

    def test_annual_only(self):
        annual = {o for p in self.series.periods for o in p.supporting_observation_ids}
        refs = tuple(ref for ref in self.claims.spans[0].references if ref.observation_id in annual)
        self.blocked(replace(self.claims, spans=(replace(self.claims.spans[0], references=refs),)),
                     R.REPORTING_SUBJECT_COVERAGE_INCOMPLETE)

    def test_each_cross_form_cannot_be_omitted(self):
        for form in ("8-K", "10-Q", "10-Q/A"):
            with self.subTest(form=form):
                omitted = {o for p in self.series.periods for v in p.filing_versions if v.form == form
                           for o in v.observation_ids}
                refs = tuple(ref for ref in self.claims.spans[0].references if ref.observation_id not in omitted)
                self.blocked(replace(self.claims, spans=(replace(self.claims.spans[0], references=refs),)),
                             R.REPORTING_SUBJECT_COVERAGE_INCOMPLETE)

    def test_one_unassigned_observation(self):
        self.blocked(replace(self.claims, spans=(replace(self.claims.spans[0],
            references=self.claims.spans[0].references[1:]),)), R.REPORTING_SUBJECT_COVERAGE_INCOMPLETE)

    def test_conflicting_assignment(self):
        self.blocked(replace(self.claims, spans=(*self.claims.spans,
            replace(self.claims.spans[0], subject_anchor=f.SUCCESSOR))),
            R.REPORTING_SUBJECT_EVIDENCE_CONFLICT, R.REPORTING_SUBJECT_DISCONTINUITY)

    def test_gap(self):
        claims = f.transition(self.series)
        claims = replace(claims, spans=(claims.spans[0], replace(claims.spans[1],
            subject_anchor=f.SUBJECT, effective_start="2022-01-02")))
        self.blocked(claims, R.REPORTING_SUBJECT_COVERAGE_INCOMPLETE)

    def test_conflicting_overlap(self):
        claims = f.transition(self.series)
        self.blocked(replace(claims, spans=(claims.spans[0],
            replace(claims.spans[1], effective_start="2021-12-31"))), R.REPORTING_SUBJECT_EVIDENCE_CONFLICT)

    def test_incomplete_status(self):
        self.blocked(replace(self.claims, coverage=r.CoverageStatus.INCOMPLETE),
                     R.REPORTING_SUBJECT_COVERAGE_INCOMPLETE)

    def test_no_documents(self):
        self.blocked(None, R.REPORTING_SUBJECT_COVERAGE_INCOMPLETE, documents=())

    def test_no_spans(self):
        self.blocked(replace(self.claims, spans=()), R.REPORTING_SUBJECT_COVERAGE_INCOMPLETE)

    def test_no_stitching_partial_snapshots(self):
        refs = self.claims.spans[0].references
        documents = tuple(f.document(replace(self.claims, coverage=r.CoverageStatus.INCOMPLETE,
            spans=(replace(self.claims.spans[0], references=part),)),
            source_reference=f"synthetic:document:partial-{n}")
            for n, part in enumerate((refs[::2], refs[1::2])))
        self.blocked(None, R.REPORTING_SUBJECT_COVERAGE_INCOMPLETE, documents=documents)

    def test_two_complete_snapshots_disagree(self):
        other = replace(self.claims, spans=(replace(self.claims.spans[0], subject_anchor=f.SUCCESSOR),))
        self.blocked(None, R.REPORTING_SUBJECT_EVIDENCE_CONFLICT,
            documents=(f.document(self.claims), f.document(other, source_reference="synthetic:document:other")))

    def test_two_complete_snapshots_corroborate(self):
        self.success(documents=(f.document(self.claims),
            f.document(self.claims, source_reference="synthetic:document:other")))

    def test_reordering_evidence_and_references(self):
        other = replace(self.claims, spans=(replace(self.claims.spans[0],
            references=tuple(reversed(self.claims.spans[0].references))),))
        a, b = f.document(self.claims), f.document(other, source_reference="synthetic:document:other")
        self.assertEqual(self.success(documents=(a, b)), self.success(documents=(b, a)))
        self.assertEqual(self.success(documents=(a,)).semantic_hash, self.success(documents=(b,)).semantic_hash)

    def test_equivalent_span_segmentation(self):
        claims = f.transition(self.series)
        claims = replace(claims, spans=(claims.spans[0], replace(claims.spans[1], subject_anchor=f.SUBJECT)))
        split = self.success(claims)
        self.assertEqual(split.semantic_hash, self.success().semantic_hash)
        reversed_claims = replace(claims, spans=tuple(reversed(claims.spans)))
        self.assertEqual(split.semantic_hash, self.success(reversed_claims).semantic_hash)

    def test_transition_chronology_changes_semantics(self):
        a = self.blocked(f.transition(self.series), R.REPORTING_SUBJECT_DISCONTINUITY)
        b = self.blocked(f.transition(self.series, "2023-01-01", "2022-12-31"), R.REPORTING_SUBJECT_DISCONTINUITY)
        self.assertNotEqual(a.semantic_hash, b.semantic_hash)

    def test_late_capture(self):
        self.blocked(None, R.UPSTREAM_BOUNDARY_NOT_QUALIFIED,
            documents=(f.document(self.claims, captured_at="2026-03-02T12:00:00.000001Z"),))

    def test_exact_boundary(self):
        self.assertEqual(self.success().qualification_boundary, self.basis.qualification_boundary)

    def test_later_boundary_requires_and_accepts_new_exact_chain(self):
        captured = "2026-03-02T12:00:00.000002Z"
        identity, witness = basis.identity_fixture(self.series, captured_at=captured)
        request = basis.request(self.series, identity)
        evidence = basis.bundle(witness, basis.document(basis.snapshot(self.series, identity),
                                                       captured_at=captured))
        qualification = s.qualify_share_basis(self.series, identity, request, evidence)
        chain = (self.series, identity, qualification, r.ShareBasisQualificationWitness(request, evidence))
        result = self.success(chain=chain, documents=(f.document(self.claims, captured_at=captured),))
        self.assertEqual(result.qualification_boundary, captured)

    def test_historical_request_cannot_hide_corrupt_evidence(self):
        source = replace(f.document(self.claims), content_sha256="0" * 64)
        with self.assertRaises(r.ReportingSubjectContractError):
            self.qualify(documents=(source,), request=f.request(*self.chain[:3],
                mode=r.ReportingSubjectMode.HISTORICAL_AS_OF))

    def test_coverage_ends_before_boundary(self):
        self.blocked(replace(self.claims, spans=(replace(self.claims.spans[0], effective_end="2026-03-01"),)),
                     R.REPORTING_SUBJECT_COVERAGE_INCOMPLETE)

    def test_historical_unsupported(self):
        result = self.blocked(None, R.HISTORICAL_COMPARABILITY_UNSUPPORTED,
            request=f.request(*self.chain[:3], mode=r.ReportingSubjectMode.HISTORICAL_AS_OF))
        self.assertIs(result.outcome, O.COMPARABILITY_UNSUPPORTED)

    def test_unsuccessful_identity_replay(self):
        claims = replace(identities.snapshot(self.series), continuity=i.Continuity.SUCCESSOR)
        chain = f.upstream(self.series, identity_claims=claims)
        self.blocked(None, R.UPSTREAM_NOT_QUALIFIED, chain=chain)

    def test_unsuccessful_basis_replay(self):
        self.blocked(None, R.UPSTREAM_NOT_QUALIFIED, chain=f.upstream(self.series, basis_documents=()))

    def test_forged_basis_result(self):
        for key, value in (("qualification_boundary", "2026-03-03T12:00:00Z"),
                           ("semantic_hash", "0" * 64), ("downstream_blockers", ())):
            with self.subTest(field=key), self.assertRaises(r.ReportingSubjectContractError):
                chain = (*self.chain[:2], replace(self.basis, **{key: value}), self.witness)
                self.qualify(chain=chain)

    def test_altered_series_value(self):
        period = replace(self.series.periods[0], value=Decimal("999"))
        series = replace(self.series, periods=(period, *self.series.periods[1:]))
        with self.assertRaises(r.ReportingSubjectContractError):
            self.qualify(chain=(series, *self.chain[1:]))

    def test_altered_series_semantic_hash(self):
        with self.assertRaises(r.ReportingSubjectContractError):
            self.qualify(chain=(replace(self.series, semantic_hash="0" * 64), *self.chain[1:]))

    def test_altered_series_evidence_hash(self):
        with self.assertRaises(r.ReportingSubjectContractError):
            self.qualify(chain=(replace(self.series, evidence_hash="0" * 64), *self.chain[1:]))

    def test_forged_identity(self):
        with self.assertRaises(r.ReportingSubjectContractError):
            self.qualify(chain=(self.series, replace(self.identity, qualification_as_of="2026-03-03T12:00:00Z"),
                                self.basis, self.witness))

    def test_request_linkage(self):
        with self.assertRaises(r.ReportingSubjectContractError):
            self.qualify(request=f.request(*self.chain[:3], share_basis_evidence_hash="0" * 64))

    def test_forged_nested_witness(self):
        witness = replace(self.witness, request=replace(self.witness.request, series_evidence_hash="0" * 64))
        with self.assertRaises(r.ReportingSubjectContractError):
            self.qualify(chain=(*self.chain[:3], witness))

    def test_foreign_reference(self):
        ref = self.claims.spans[0].references[0]
        for change in ({"observation_id": "0" * 64}, {"version_id": "0" * 64}, {"period_start": "1900-01-01"}):
            with self.subTest(change=change), self.assertRaises(r.ReportingSubjectContractError):
                self.qualify(replace(self.claims, spans=(replace(self.claims.spans[0],
                    references=(replace(ref, **change),)),)))

    def test_source_series_link(self):
        with self.assertRaises(r.ReportingSubjectContractError):
            self.qualify(replace(self.claims, series_evidence_hash="0" * 64))

    def test_source_issuer_link(self):
        with self.assertRaises(r.ReportingSubjectContractError):
            self.qualify(replace(self.claims, spans=(replace(self.claims.spans[0],
                issuer_anchor="synthetic:issuer:foreign"),)))

    def test_bytes_tampering(self):
        source = f.document(self.claims)
        with self.assertRaises(r.ReportingSubjectContractError):
            self.qualify(documents=(replace(source, source_bytes=source.source_bytes + b" "),))

    def test_stale_digest(self):
        with self.assertRaises(r.ReportingSubjectContractError):
            self.qualify(documents=(replace(f.document(self.claims), content_sha256="0" * 64),))

    def test_locator_tampering(self):
        with self.assertRaises(r.ReportingSubjectContractError):
            self.qualify(documents=(replace(f.document(self.claims), source_locator="/other"),))

    def test_reencoded_wrong_locator(self):
        with self.assertRaises(r.ReportingSubjectContractError):
            self.qualify(documents=(f.document(self.claims, source_locator="/other"),))

    def test_timestamp_detached_from_bytes(self):
        with self.assertRaises(r.ReportingSubjectContractError):
            self.qualify(documents=(replace(f.document(self.claims), captured_at="2026-03-02T11:30:00Z"),))

    def test_timestamp_chronology(self):
        with self.assertRaises(r.ReportingSubjectContractError):
            self.qualify(documents=(f.document(self.claims, published_at="2026-03-03T10:00:00Z"),))

    def test_date_only_is_not_promoted_to_intraday_time(self):
        with self.assertRaises(r.ReportingSubjectContractError):
            self.qualify(documents=(f.document(self.claims, captured_at="2026-03-02"),))

    def test_invalid_interval(self):
        for value in ("garbage", "2019-12-31"):
            with self.subTest(value=value), self.assertRaises(r.ReportingSubjectContractError):
                self.qualify(replace(self.claims, spans=(replace(self.claims.spans[0], effective_end=value),)))

    def test_duplicate_json_key(self):
        source = f.document(self.claims)
        raw = b'{"source_locator":"/claims",' + source.source_bytes[1:]
        with self.assertRaises(r.ReportingSubjectContractError):
            self.qualify(documents=(replace(source, source_bytes=raw,
                content_sha256=hashlib.sha256(raw).hexdigest()),))

    def test_nonfinite_json(self):
        source = f.document(self.claims)
        raw = source.source_bytes.replace(b'"/claims"', b'NaN')
        with self.assertRaises(r.ReportingSubjectContractError):
            self.qualify(documents=(replace(source, source_bytes=raw,
                content_sha256=hashlib.sha256(raw).hexdigest()),))

    def test_mutable_nested_collection(self):
        with self.assertRaises(r.ReportingSubjectContractError):
            self.qualify(replace(self.claims, spans=list(self.claims.spans)))

    def test_subclass_input(self):
        class Subclass(r.ReportingSubjectRequest):
            pass
        request = f.request(*self.chain[:3])
        with self.assertRaises(r.ReportingSubjectContractError):
            self.qualify(request=Subclass(*(getattr(request, field.name) for field in fields(request))))

    def test_unknown_enum(self):
        class Foreign(Enum):
            CURRENT_SNAPSHOT = "CURRENT_SNAPSHOT"
        for mode in ("CURRENT_SNAPSHOT", Foreign.CURRENT_SNAPSHOT):
            with self.subTest(mode=mode), self.assertRaises(r.ReportingSubjectContractError):
                self.qualify(request=f.request(*self.chain[:3], mode=mode))

    def test_unknown_versions(self):
        with self.assertRaises(r.ReportingSubjectContractError):
            self.qualify(request=f.request(*self.chain[:3], contract_version="future"))
        with self.assertRaises(r.ReportingSubjectContractError):
            self.qualify(documents=(f.document(self.claims, extraction_version="future"),))

    def test_records_are_frozen(self):
        with self.assertRaises(FrozenInstanceError):
            self.claims.coverage = r.CoverageStatus.INCOMPLETE
        with self.assertRaises(FrozenInstanceError):
            self.success().qualified_subject_anchor = f.SUCCESSOR

    def test_evidence_bytes_distinct_same_semantics(self):
        source = f.document(self.claims)
        raw = json.dumps(json.loads(source.source_bytes), indent=2).encode()
        other = replace(source, source_bytes=raw, content_sha256=hashlib.sha256(raw).hexdigest())
        a, b = self.success(documents=(source,)), self.success(documents=(other,))
        self.assertEqual(a.semantic_hash, b.semantic_hash)
        self.assertNotEqual(a.evidence_hash, b.evidence_hash)

    def test_source_metadata_in_evidence_identity(self):
        a = self.success()
        b = self.success(documents=(f.document(self.claims, available_at="2026-03-02T11:01:00Z"),))
        self.assertEqual(a.semantic_hash, b.semantic_hash)
        self.assertNotEqual(a.evidence_hash, b.evidence_hash)

    def test_offline_blockers_preserved(self):
        result = self.success()
        self.assertIn(AdmissionBlocker.OFFLINE_CAPTURE_NOT_AUTHENTICATED, result.downstream_blockers)
        self.assertEqual(len(result.downstream_blockers), 7)
        self.assertEqual(tuple(r.Authority), (r.Authority.SYNTHETIC_TEST_ONLY,))

    def test_live_capture_fixture_does_not_upgrade_synthetic_qualification(self):
        # Private offline fixture publication only: no acquisition call or real trust.
        chain = f.upstream(f.signed_series(2, live=True))
        result = self.success(chain=chain)
        self.assertNotIn(AdmissionBlocker.OFFLINE_CAPTURE_NOT_AUTHENTICATED, result.downstream_blockers)
        self.assertEqual(len(result.downstream_blockers), 6)
        self.assertIn(AdmissionBlocker.ECONOMIC_COMPARABILITY_NOT_ESTABLISHED, result.downstream_blockers)

    def test_source_profile_cannot_be_changed(self):
        for change in ({"concept": "IncomeLossFromContinuingOperationsPerDilutedShare"},
                       {"namespace": "custom"}, {"unit": "EUR/shares"},
                       {"resolver_version": "future"}):
            with self.subTest(change=change), self.assertRaises(r.ReportingSubjectContractError):
                self.qualify(chain=(replace(self.series, **change), *self.chain[1:]))

    def test_acquisition_contract_cannot_be_changed(self):
        series = replace(self.series, capture_authority=replace(self.series.capture_authority,
            acquisition_contract="future"))
        # Even self-consistent synthetic C4/C5 replay cannot bless another source profile.
        chain = f.upstream(series)
        with self.assertRaises(r.ReportingSubjectContractError):
            self.qualify(chain=chain)

    def test_missing_exact_record_field_is_closed_error(self):
        malformed = object.__new__(r.ReportingSubjectRequest)
        with self.assertRaises(r.ReportingSubjectContractError):
            self.qualify(request=malformed)

    def test_no_io_at_qualification(self):
        evidence = f.bundle(self.witness, f.document(self.claims))
        with patch.object(builtins, "open", side_effect=AssertionError("filesystem")), \
             patch.object(socket, "socket", side_effect=AssertionError("network")):
            self.success(evidence=evidence)

    def test_no_model_or_provider_or_transform_capability(self):
        tree = ast.parse(inspect.getsource(r))
        imports = [node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)]
        self.assertFalse(any(name and (name.startswith("src") or "provider" in name) for name in imports))
        calls = [node.func.id for node in ast.walk(tree)
                 if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)]
        self.assertNotIn("float", calls)
        self.assertNotIn("open", calls)
        attributes = {node.func.attr for node in ast.walk(tree)
                      if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)}
        self.assertFalse(attributes & {"now", "today", "utcnow", "getenv", "read_text", "write_text"})
        self.assertEqual(tuple(inspect.signature(r.qualify_reporting_subject).parameters),
                         ("series", "identity", "share_basis", "request", "evidence"))
        request_fields = {field.name for field in fields(r.ReportingSubjectRequest)}
        for forbidden in ("comparable", "as_of", "measurement_profile", "numerator", "adjusted_eps",
                          "organic_growth", "price", "dividend", "analyst_estimate", "quality_score",
                          "durability_score", "portfolio", "allocation", "adjustment_factor"):
            self.assertNotIn(forbidden, request_fields)
            with self.subTest(field=forbidden), self.assertRaises(TypeError):
                replace(f.request(*self.chain[:3]), **{forbidden: True})

    def test_core_identity_is_jurisdiction_neutral(self):
        self.assertEqual({field.name for field in fields(r.ReportingSubjectSpan)},
                         {"subject_anchor", "issuer_anchor", "effective_start", "effective_end", "references"})
        for name in ("cik", "ticker", "accession", "venue", "form"):
            self.assertNotIn(name, {field.name for field in fields(r.ReportingSubjectSpan)})


if __name__ == "__main__":
    unittest.main()
