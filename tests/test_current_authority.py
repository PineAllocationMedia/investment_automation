"""Private report-assembly invariants; fixture hashes do not prove real facts."""
from dataclasses import FrozenInstanceError, fields
from decimal import Decimal, localcontext
import unittest

from economic_facts import current_authority as c
from economic_facts import source_authority as s


def arguments(**changes):
    value = dict(route_id=s.SEC_COMPANYFACTS_LIVE_CURRENT_V1,
        boundary="2026-03-01T12:00:00Z", reasons=(),
        verified_properties=(s.AuthorityProperty.SOURCE_ACQUISITION_PROVENANCE,
            s.AuthorityProperty.CURRENT_OBSERVED_AVAILABILITY, s.AuthorityProperty.CURRENT_SNAPSHOT_SCOPE),
        upstream_blockers=("SYNTHETIC_UNIT_TEST_BLOCKER",), source_hashes=("a" * 64,),
        upstream_semantic_hash="b" * 64, upstream_evidence_hash="c" * 64,
        verified_evidence_hash="d" * 64)
    value.update(changes)
    return value


class CurrentAuthorityTests(unittest.TestCase):
    def build(self, **changes):
        return c._build_assessment(**arguments(**changes))

    def test_exact_obligation_partition(self):
        result = self.build()
        self.assertEqual(len(result.satisfied_obligations), 3)
        self.assertEqual(len(result.unresolved_obligations), 4)
        self.assertEqual(set(result.satisfied_obligations) | set(result.unresolved_obligations), set(s.AuthorityProperty))
        self.assertFalse(set(result.satisfied_obligations) & set(result.unresolved_obligations))
        self.assertEqual({x.grant.property for x in result.established_claims}, set(result.satisfied_obligations))
        self.assertIn(s.AuthorityProperty.FINAL_ECONOMIC_ADMISSION, result.unresolved_obligations)

    def test_unpermitted_claim_is_rejected_even_with_other_valid_claims(self):
        for prop in (s.AuthorityProperty.SECURITY_SHARE_CLASS_LISTING_IDENTITY,
                     s.AuthorityProperty.SHARE_BASIS_COMPARABILITY,
                     s.AuthorityProperty.ECONOMIC_REPORTING_SUBJECT_COMPARABILITY):
            with self.subTest(property=prop), self.assertRaises(s.SourceAuthorityError):
                self.build(verified_properties=arguments()["verified_properties"] + (prop,))

    def test_final_admission_cannot_be_established(self):
        with self.assertRaises(c.CurrentAuthorityError):
            self.build(verified_properties=(s.AuthorityProperty.FINAL_ECONOMIC_ADMISSION,))
        self.assertNotIn("ADMITTED", {v.value for v in c.AssessmentStatus})

    def test_publication_unknown_and_availability_is_only_capture_bound(self):
        result = self.build()
        self.assertIs(result.publication, s.PublicationSemantics.UNKNOWN)
        self.assertEqual(result.observed_available_by, "2026-03-01T12:00:00Z")
        self.assertEqual(result.observed_available_by, result.current_authority_boundary)
        self.assertNotIn("published_at", {f.name for f in fields(result)})

    def test_limitations_always_retained(self):
        for result in (self.build(), self.build(boundary=None, reasons=(c.AuthorityReason.RESOLUTION_UNAVAILABLE,),
                                              verified_properties=())):
            self.assertEqual(set(result.limitations), set(c.AuthorityLimitation))

    def test_unavailable_never_exposes_established_claims_or_boundary(self):
        for reason in c.AuthorityReason:
            result = self.build(boundary=None, reasons=(reason,), verified_properties=())
            self.assertIs(result.status, c.AssessmentStatus.UNAVAILABLE)
            self.assertEqual(result.established_claims, ())
            self.assertEqual(set(result.unresolved_obligations), set(s.AuthorityProperty))
            self.assertIsNone(result.observed_available_by)

    def test_failure_cannot_carry_boundary_or_claims(self):
        for change in ({}, {"boundary": None}):
            with self.subTest(change=change), self.assertRaises(c.CurrentAuthorityError):
                self.build(reasons=(c.AuthorityReason.RESOLUTION_UNAVAILABLE,), **change)

    def test_missing_required_evidence_rejected(self):
        for change in ({"source_hashes": ()}, {"upstream_semantic_hash": None},
                       {"upstream_evidence_hash": None}, {"verified_properties": ()}):
            with self.subTest(change=change), self.assertRaises(c.CurrentAuthorityError):
                self.build(**change)

    def test_invalid_times_are_not_promoted(self):
        for value in (None, "2026-03-01", "2026-03-01T12:00:00", "2026-02-30T12:00:00Z",
                      "2026-03-01T12:00:00.1Z", "2026-03-01T12:00:00+00:00"):
            with self.subTest(value=value), self.assertRaises(c.CurrentAuthorityError):
                self.build(boundary=value)

    def test_subsecond_boundary_changes_both_identities(self):
        first = self.build()
        later = self.build(boundary="2026-03-01T12:00:00.000001Z")
        self.assertNotEqual(first.semantic_hash, later.semantic_hash)
        self.assertNotEqual(first.evidence_hash, later.evidence_hash)

    def test_hash_identity_is_not_a_document_hash(self):
        result = self.build()
        self.assertEqual(result.source_hashes, ("a" * 64,))
        self.assertNotIn(result.evidence_hash, result.source_hashes)
        self.assertEqual(result.established_claims[0].evidence_hash, "d" * 64)

    def test_bad_types_hashes_and_authority_labels_rejected(self):
        for change in ({"verified_properties": ("REAL",)}, {"reasons": ("REAL",)},
                       {"source_hashes": ["a" * 64]}, {"upstream_semantic_hash": "x"},
                       {"verified_evidence_hash": "x"}, {"upstream_blockers": (False,)}):
            with self.subTest(change=change), self.assertRaises(c.CurrentAuthorityError):
                self.build(**change)

    def test_reordered_properties_and_source_hashes_stable(self):
        props = arguments()["verified_properties"]
        a = self.build(source_hashes=("a" * 64, "e" * 64))
        b = self.build(source_hashes=("e" * 64, "a" * 64, "a" * 64),
                       verified_properties=tuple(reversed(props)))
        self.assertEqual(a, b)

    def test_blocker_order_preserved_but_semantics_order_independent(self):
        a = self.build(upstream_blockers=("FIRST", "SECOND"))
        b = self.build(upstream_blockers=("SECOND", "FIRST"))
        self.assertEqual(b.upstream_blockers, ("SECOND", "FIRST"))
        self.assertEqual(a.semantic_hash, b.semantic_hash)
        self.assertNotEqual(a.evidence_hash, b.evidence_hash)

    def test_evidence_change_does_not_change_economic_semantics(self):
        first = self.build()
        for change in ({"verified_evidence_hash": "f" * 64}, {"upstream_evidence_hash": "e" * 64},
                       {"source_hashes": ("e" * 64,)}):
            with self.subTest(change=change):
                second = self.build(**change)
                self.assertEqual(first.semantic_hash, second.semantic_hash)
                self.assertNotEqual(first.evidence_hash, second.evidence_hash)
        self.assertNotEqual(first.semantic_hash, self.build(upstream_semantic_hash="f" * 64).semantic_hash)

    def test_exact_encoding_does_not_use_decimal_context_or_floats(self):
        value = Decimal("1.234567890123456789000")
        with localcontext() as context:
            context.prec = 2
            for signal in context.traps:
                context.traps[signal] = True
            projected = s._project(value)
            digest = s._hash("test", value)
        self.assertEqual(projected, {"decimal_tuple": [0, list(value.as_tuple().digits), -21]})
        self.assertEqual(digest, s._hash("test", value))
        with self.assertRaises(s.SourceAuthorityError):
            s._project(1.0)

    def test_immutable_neutral_output(self):
        result = self.build()
        with self.assertRaises(FrozenInstanceError):
            result.status = "ADMITTED"
        names = {f.name for f in fields(result)}
        self.assertFalse(names & {"cik", "accession", "ticker", "form", "venue", "sec_receipt_id", "series"})
        self.assertFalse(hasattr(result, "__dict__"))


if __name__ == "__main__":
    unittest.main()
