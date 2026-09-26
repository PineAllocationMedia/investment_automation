"""PR4D3B offline source extraction and strict non-authority boundaries."""
import ast
from dataclasses import FrozenInstanceError
import hashlib
import inspect
import os
from pathlib import Path
import socket
import tempfile
import time
import unittest
from unittest.mock import patch

from economic_facts import sec_class_eps_claims as s
from economic_facts import sec_filing_archive as a
from economic_facts import sec_registered_securities as registered
from tests.sec_class_eps_fixtures import (
    PROFILES,
    common_shares,
    context,
    diluted_eps,
    inline,
    numeric_fact,
    submission,
)
from tests.sec_original_filing_fixtures import ACCESSION, CIK, T1, T2, filing
from tests.sec_registered_security_fixtures import submission as registered_submission


class ClassEPSClaimTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve() / "filings"
        self.archive = a.SecFilingArchive(self.root)

    def capture(self, raw=None, captured_at=T1):
        return self.archive._capture_live(submission() if raw is None else raw, cik=CIK,
                                          accession=ACCESSION, captured_at=captured_at)

    def replay(self, receipt):
        return s.extract_sec_class_eps_claims(
            self.archive, s.SecClassEPSExtractionRequest(receipt.receipt_id))

    def extract(self, **kwargs):
        return self.replay(self.capture(submission(**kwargs)))

    def unsupported(self, payload, *, form="10-K"):
        with self.assertRaises(s.UnsupportedSecClassEPSSource):
            self.replay(self.capture(filing(form=form, payload=payload)))

    def test_exact_2025_profile_and_primary_provenance(self):
        raw, payload = submission(), inline()
        receipt = self.capture(raw)
        result = self.replay(receipt)
        self.assertEqual(result.status, s.ExtractionStatus.CAPTURED_CLASS_EPS_SOURCE_CLAIMS)
        self.assertEqual(result.taxonomy_profile, s.SourceTaxonomyProfile(*PROFILES[2025]))
        primary = result.primary_document
        self.assertEqual((primary.receipt_id, primary.cik, primary.accession, primary.form),
                         (receipt.receipt_id, CIK, ACCESSION, "10-K"))
        self.assertEqual(raw[primary.byte_start:primary.byte_start + primary.byte_length], payload)
        self.assertEqual(primary.content_sha256, hashlib.sha256(payload).hexdigest())
        self.assertEqual([fact.fact_kind for fact in result.occurrences], [
            s.SourceFactKind.COMMON_STOCK_SHARES_OUTSTANDING,
            s.SourceFactKind.DILUTED_EPS,
        ])
        self.assertEqual(result.occurrences[0].source_value, "1000000")
        self.assertEqual(result.occurrences[1].source_value, "2.50")
        self.assertEqual(result.occurrences[0].representation.unit_ref, "u-shares")
        self.assertEqual(result.occurrences[1].representation.decimals, "2")

    def test_exact_2026_profile_succeeds_without_qname_normalization(self):
        first = self.extract(year=2025)
        second = self.extract(year=2026)
        self.assertEqual(second.status, s.ExtractionStatus.CAPTURED_CLASS_EPS_SOURCE_CLAIMS)
        self.assertEqual(second.taxonomy_profile, s.SourceTaxonomyProfile(*PROFILES[2026]))
        self.assertTrue(second.occurrences[0].concept_name.startswith("{" + PROFILES[2026][0] + "}"))
        self.assertTrue(second.occurrences[1].concept_name.startswith("{" + PROFILES[2026][1] + "}"))
        self.assertNotEqual(first.semantic_id, second.semantic_id)

    def test_mixed_taxonomy_profiles_fail_closed_both_directions(self):
        mixed = (
            inline(year=2025).replace(PROFILES[2025][1].encode(), PROFILES[2026][1].encode()),
            inline(year=2026).replace(PROFILES[2026][1].encode(), PROFILES[2025][1].encode()),
        )
        for payload in mixed:
            with self.subTest(payload=payload[:100]):
                self.unsupported(payload)

    def test_nested_or_unused_mixed_namespace_fails_closed(self):
        self.unsupported(inline(namespaces='xmlns:future="http://fasb.org/us-gaap/2026"'))
        self.unsupported(inline(extra='<div xmlns:old="http://xbrl.sec.gov/dei/2026">x</div>'))

    def test_unknown_taxonomy_years_fail_closed(self):
        for old, new in ((PROFILES[2025][0], "http://xbrl.sec.gov/dei/2024"),
                         (PROFILES[2025][1], "http://fasb.org/us-gaap/2027")):
            self.unsupported(inline().replace(old.encode(), new.encode()))

    def test_supported_forms_and_8k_exclusion(self):
        for form in ("10-K", "10-K/A", "10-Q", "10-Q/A"):
            with self.subTest(form=form):
                result = self.replay(self.capture(filing(form=form, payload=inline())))
                self.assertEqual(result.primary_document.form, form)
        for form in ("8-K", "8-K/A", "20-F", "6-K"):
            with self.subTest(form=form), self.assertRaises(s.UnsupportedSecClassEPSSource):
                self.replay(self.capture(filing(form=form, payload=inline())))

    def test_one_common_stock_outstanding_source_claim(self):
        result = self.extract()
        claim = next(claim for claim in result.claims if claim.fact_kind is
                     s.SourceFactKind.COMMON_STOCK_SHARES_OUTSTANDING)
        self.assertEqual(claim.assertions[0].source_value, "1000000")
        self.assertIsNotNone(claim.source_class_scope_id)
        self.assertEqual(result.contexts[0].period.kind, "INSTANT")

    def test_multiple_class_members_remain_distinct(self):
        contexts = (context("a", kind="instant", member="fiction:ClassAMember")
                    + context("b", kind="instant", member="fiction:ClassBMember")
                    + context("eps"))
        # Equal numeric text must not collapse distinct source members.
        facts = common_shares("100", "a") + common_shares("100", "b") + diluted_eps()
        result = self.extract(contexts=contexts, facts=facts)
        common = [claim for claim in result.claims if claim.fact_kind is
                  s.SourceFactKind.COMMON_STOCK_SHARES_OUTSTANDING]
        self.assertEqual(len(common), 2)
        self.assertEqual(len({claim.source_class_scope_id for claim in common}), 2)
        self.assertEqual({dimension.member for source in result.contexts
                          for dimension in source.dimensions},
                         {"{https://fiction.invalid/2025}ClassAMember",
                          "{https://fiction.invalid/2025}ClassBMember"})

    def test_undimensioned_common_stock_assertion_is_preserved_without_one_class_claim(self):
        result = self.extract(contexts=context("shares", kind="instant") + context("eps"))
        common = result.occurrences[0]
        self.assertIsNone(common.source_class_scope_id)
        self.assertEqual(result.contexts[0].dimensions, ())
        self.assertNotIn("complete", s.SecClassEPSExtractionAssessment.__dataclass_fields__)

    def test_custom_member_names_are_opaque(self):
        strange = "fiction:PreferredLookingButOpaqueMember"
        result = self.extract(contexts=(context("shares", kind="instant", member=strange)
                                        + context("eps", member=strange)),
                              facts=common_shares() + diluted_eps())
        self.assertEqual(result.contexts[0].dimensions[0].source_member, strange)
        self.assertFalse(any(hasattr(record, "instrument_type") for record in result.contexts))
        self.assertEqual(result.occurrences[0].source_class_scope_id,
                         result.occurrences[1].source_class_scope_id)

    def test_undimensioned_diluted_eps_is_retained_not_assigned_to_class(self):
        result = self.extract()
        eps = next(fact for fact in result.occurrences if fact.fact_kind is s.SourceFactKind.DILUTED_EPS)
        self.assertIsNone(eps.source_class_scope_id)
        self.assertEqual(result.contexts[1].dimensions, ())
        self.assertNotEqual(eps.source_class_scope_id, result.occurrences[0].source_class_scope_id)

    def test_dimensioned_diluted_eps_retains_exact_member(self):
        member = "fiction:ClassAMember"
        result = self.extract(contexts=(context("shares", kind="instant", member=member)
                                        + context("eps", member=member)))
        self.assertEqual(result.occurrences[0].source_class_scope_id,
                         result.occurrences[1].source_class_scope_id)
        self.assertEqual(result.contexts[1].dimensions[0].source_member, member)

    def test_multiple_class_specific_eps_contexts_remain_distinct(self):
        contexts = (context("shares", kind="instant", member="fiction:ClassAMember")
                    + context("a", member="fiction:ClassAMember")
                    + context("b", member="fiction:ClassBMember"))
        facts = common_shares() + diluted_eps("2.50", "a") + diluted_eps("1.75", "b")
        result = self.extract(contexts=contexts, facts=facts)
        eps = [claim for claim in result.claims if claim.fact_kind is s.SourceFactKind.DILUTED_EPS]
        self.assertEqual(len(eps), 2)
        self.assertEqual({claim.assertions[0].source_value for claim in eps}, {"2.50", "1.75"})

    def test_dimensioned_and_undimensioned_eps_is_explicit_conflict(self):
        contexts = (context("shares", kind="instant", member="fiction:ClassAMember")
                    + context("all") + context("class", member="fiction:ClassAMember"))
        facts = common_shares() + diluted_eps("2.50", "all") + diluted_eps("2.50", "class")
        result = self.extract(contexts=contexts, facts=facts)
        self.assertEqual(result.status, s.ExtractionStatus.SOURCE_CONFLICT)
        self.assertIn(s.ClaimIssue.DIMENSIONED_AND_UNDIMENSIONED_EPS, result.issues)
        self.assertEqual(len([f for f in result.occurrences if f.fact_kind is s.SourceFactKind.DILUTED_EPS]), 2)

    def test_duplicate_facts_retain_occurrence_provenance(self):
        base = self.extract()
        duplicate = self.extract(facts=common_shares() + common_shares() + diluted_eps())
        self.assertEqual(len(duplicate.occurrences), 3)
        self.assertEqual(len({fact.occurrence_id for fact in duplicate.occurrences}), 3)
        self.assertEqual(base.semantic_id, duplicate.semantic_id)
        self.assertNotEqual(base.evidence_id, duplicate.evidence_id)

    def test_conflicting_source_values_keep_all_assertions(self):
        result = self.extract(facts=common_shares("100") + common_shares("200") + diluted_eps())
        self.assertEqual(result.status, s.ExtractionStatus.SOURCE_CONFLICT)
        claim = next(claim for claim in result.claims if claim.fact_kind is
                     s.SourceFactKind.COMMON_STOCK_SHARES_OUTSTANDING)
        self.assertEqual({assertion.source_value for assertion in claim.assertions}, {"100", "200"})
        self.assertEqual(len(claim.occurrence_ids), 2)

    def test_different_periods_are_not_conflicts_or_winner_selected(self):
        contexts = (context("shares", kind="instant", member="fiction:ClassAMember")
                    + context("new") + context("old", start="2024-01-01", end="2024-12-31"))
        facts = common_shares() + diluted_eps("2.50", "new") + diluted_eps("1.50", "old")
        result = self.extract(contexts=contexts, facts=facts)
        self.assertEqual(result.status, s.ExtractionStatus.CAPTURED_CLASS_EPS_SOURCE_CLAIMS)
        self.assertEqual(len(result.occurrences), 3)

    def test_foreign_cik_context_fails_closed_as_conflict(self):
        result = self.extract(contexts=(context("shares", kind="instant",
                                                       member="fiction:ClassAMember", cik="0000000099")
                                        + context("eps")))
        self.assertEqual(result.status, s.ExtractionStatus.SOURCE_CONFLICT)
        self.assertIn(s.ClaimIssue.CONTEXT_ENTITY_MISMATCH, result.issues)

    def test_missing_one_target_family_is_explicitly_incomplete(self):
        for facts, issue in ((common_shares(), s.ClaimIssue.MISSING_DILUTED_EPS_SOURCE_ASSERTION),
                             (diluted_eps(), s.ClaimIssue.MISSING_COMMON_STOCK_SOURCE_ASSERTION)):
            with self.subTest(issue=issue):
                result = self.extract(facts=facts)
                self.assertEqual(result.status, s.ExtractionStatus.INCOMPLETE_CLASS_EPS_SOURCE_CLAIMS)
                self.assertIn(issue, result.issues)

    def test_no_target_facts_is_not_absence_or_completeness_claim(self):
        result = self.extract(facts='<ix:nonNumeric name="dei:TradingSymbol" contextRef="eps">FICT</ix:nonNumeric>')
        self.assertEqual(result.status, s.ExtractionStatus.NO_SUPPORTED_CLASS_EPS_SOURCE_CLAIMS)
        self.assertEqual(result.occurrences, ())
        self.assertIn(s.ClaimIssue.MISSING_COMMON_STOCK_SOURCE_ASSERTION, result.issues)
        self.assertIn(s.ClaimIssue.MISSING_DILUTED_EPS_SOURCE_ASSERTION, result.issues)

    def test_unsupported_dimensions_fail_closed(self):
        base = context("shares", kind="instant", member="fiction:ClassAMember")
        unsupported = base.replace(
            "</xbrli:segment>",
            '<xbrldi:explicitMember dimension="fiction:OtherAxis">fiction:OtherMember'
            '</xbrldi:explicitMember></xbrli:segment>')
        self.unsupported(inline(contexts=unsupported + context("eps")))

    def test_wrong_period_types_fail_closed(self):
        self.unsupported(inline(contexts=context("shares") + context("eps")))
        self.unsupported(inline(contexts=(context("shares", kind="instant")
                                         + context("eps", kind="instant"))))

    def test_unsupported_inline_numeric_representations_fail_closed(self):
        variants = (
            common_shares(attrs=' format="ixt:num-dot-decimal"'),
            common_shares(attrs=' scale="3"'),
            common_shares(attrs=' sign="-"'),
            common_shares(attrs=' xsi:nil="true"'),
            common_shares(attrs=' continuedAt="next"'),
            common_shares(value="1,000"),
            common_shares(value=" 1000 "),
            common_shares().replace("<ix:nonFraction", "<ix:nonNumeric", 1).replace(
                "</ix:nonFraction>", "</ix:nonNumeric>", 1),
        )
        for fact in variants:
            with self.subTest(fact=fact):
                self.unsupported(inline(facts=fact + diluted_eps()))

    def test_exact_uninterpreted_lexical_and_accuracy_attributes_are_retained(self):
        result = self.extract(facts=(common_shares("+00100.00", decimals="-2")
                                     + diluted_eps("-0.25", precision="3")))
        self.assertEqual([fact.source_value for fact in result.occurrences], ["+00100.00", "-0.25"])
        self.assertEqual(result.occurrences[0].representation.decimals, "-2")
        self.assertEqual(result.occurrences[1].representation.precision, "3")

    def test_malformed_non_inline_and_non_utf8_primary_fail_closed(self):
        for payload in (b"<html>not namespaced</html>", b"<html", b"\xff",
                        b'<html xmlns="http://www.w3.org/1999/xhtml"><body>table only</body></html>'):
            with self.subTest(payload=payload):
                self.unsupported(payload)

    def test_only_explicit_receipt_is_read_with_no_latest_selection(self):
        old = self.capture()
        self.capture(submission(facts=common_shares() + diluted_eps("9.99")), T2)
        self.assertEqual(self.replay(old).occurrences[1].source_value, "2.50")
        with patch.object(a.SecFilingArchive, "read_receipt", wraps=self.archive.read_receipt) as read:
            self.replay(old)
            self.assertTrue(all(call.args == (old.receipt_id,) for call in read.call_args_list))

    def test_closed_request_and_exact_types(self):
        self.assertEqual(set(inspect.signature(s.extract_sec_class_eps_claims).parameters),
                         {"archive", "request"})
        self.assertEqual(set(s.SecClassEPSExtractionRequest.__dataclass_fields__),
                         {"filing_receipt_id"})
        for value in (None, b"0" * 64, "", "../receipt", True, ("0" * 64,)):
            with self.assertRaises(s.SecClassEPSRequestError):
                s.SecClassEPSExtractionRequest(value)
        class RequestSubclass(s.SecClassEPSExtractionRequest):
            pass
        with self.assertRaises(s.SecClassEPSRequestError):
            s.extract_sec_class_eps_claims(self.archive, RequestSubclass("0" * 64))

    def test_archive_membership_and_corruption_propagate(self):
        receipt = self.capture()
        with self.assertRaises(a.FilingArchiveError):
            s.extract_sec_class_eps_claims(a.SecFilingArchive(self.root.parent / "other"),
                s.SecClassEPSExtractionRequest(receipt.receipt_id))
        path = self.root / "objects" / receipt.content_sha256
        path.chmod(0o600)
        path.write_bytes(path.read_bytes().replace(b"2.50", b"9.99"))
        with self.assertRaises(a.FilingArchiveError):
            self.replay(receipt)

    def test_replay_uses_no_network_writes_directory_scan_or_clock(self):
        receipt = self.capture()
        with patch.object(socket, "socket", side_effect=AssertionError("network")), \
             patch.object(a.SecFilingArchive, "_publish", side_effect=AssertionError("write")), \
             patch.object(os, "listdir", side_effect=AssertionError("scan")), \
             patch.object(os, "scandir", side_effect=AssertionError("scan")), \
             patch.object(time, "time", side_effect=AssertionError("clock")):
            self.replay(receipt)

    def test_semantic_and_evidence_identities_and_recapture(self):
        first = self.replay(self.capture())
        second = self.replay(self.capture(captured_at=T2))
        self.assertEqual(first.semantic_id, second.semantic_id)
        self.assertNotEqual(first.evidence_id, second.evidence_id)
        formatted = self.replay(self.capture(submission().replace(b"><", b">\n<"), T2))
        self.assertEqual(first.semantic_id, formatted.semantic_id)
        self.assertNotEqual(first.evidence_id, formatted.evidence_id)

    def test_records_are_frozen_and_slotted(self):
        result = self.extract()
        records = (result, result.primary_document, result.taxonomy_profile, *result.contexts,
                   *(context.period for context in result.contexts), *result.occurrences,
                   *(fact.representation for fact in result.occurrences), *result.claims)
        for record in records:
            self.assertFalse(hasattr(record, "__dict__"))
            with self.assertRaises(FrozenInstanceError):
                setattr(record, next(iter(record.__dataclass_fields__)), None)

    def test_shared_reader_preserves_d3a_published_fixture_identities(self):
        receipt = self.archive._capture_live(registered_submission(), cik=CIK,
                                             accession=ACCESSION, captured_at=T1)
        result = registered.extract_sec_registered_security_claims(
            self.archive, registered.SecRegisteredSecurityExtractionRequest(receipt.receipt_id))
        self.assertEqual(result.primary_document.evidence_id,
                         "ae3b0d9d0a721374b7d3f355b8d6ad826987deffc44a362aec624cd6a5065177")
        self.assertEqual(result.semantic_id,
                         "84e9c6921b10377369f079f4fd7fab6e8822543f3310b4a341da2d857705b069")
        self.assertEqual(result.evidence_id,
                         "d10207c2a5d4677cd5acc8e1dc0ca15e7255b9a9a390511c6d84cddf72dd70c5")

    def test_actual_output_cannot_enter_d1_c4_pr4b1_or_expected_return(self):
        from economic_facts.current_authority import CurrentAuthorityError
        from economic_facts.sec_current_evidence import assess_sec_current_evidence
        from economic_facts.security_identity import IdentityContractError, qualify_security_identity
        from src.expected_return_assumptions import construct_expected_return
        from src.expected_return_engine import ExpectedReturnError, calculate_expected_return
        from src.expected_return_policy import ConstructorContractError
        result = self.extract()
        with self.assertRaises(CurrentAuthorityError):
            assess_sec_current_evidence(self.archive, result)
        with self.assertRaises(IdentityContractError):
            qualify_security_identity(result, result, result)
        with self.assertRaises(ConstructorContractError):
            construct_expected_return(result)
        with self.assertRaises(ExpectedReturnError):
            calculate_expected_return(result)


class ClassEPSBoundaryTests(unittest.TestCase):
    def test_exact_dependency_direction_and_no_reverse_consumers(self):
        root = Path(__file__).resolve().parents[1]
        module = root / "economic_facts/sec_class_eps_claims.py"
        allowed = {"dataclasses", "datetime", "enum", "re", "lxml"}
        for node in ast.walk(ast.parse(module.read_text())):
            if isinstance(node, ast.Import):
                self.assertTrue(all(name.name in allowed for name in node.names))
            if isinstance(node, ast.ImportFrom):
                self.assertTrue((node.level == 1 and node.module in
                                 {"sec_filing_archive", "sec_primary_document"})
                                or (node.level == 0 and node.module in allowed))
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                self.assertNotIn(node.func.id, {"open", "float", "eval", "exec", "__import__"})
        for file in [root / "main.py", *(root / "src").rglob("*.py"),
                     *(root / "economic_facts").rglob("*.py"),
                     *(root / "pit_comparison").rglob("*.py"),
                     *(root / "scripts").rglob("*.py")]:
            if file == module:
                continue
            self.assertNotIn("sec_class_eps_claims", file.read_text(), str(file))

    def test_output_has_no_authority_or_economic_identity_fields(self):
        for record in (s.SecClassEPSExtractionAssessment, s.ClassEPSSourceClaim,
                       s.ClassEPSFactOccurrence, s.SourceContext):
            self.assertFalse(set(record.__dataclass_fields__) & {
                "qualified", "admitted", "authority", "as_of", "complete",
                "applicable", "entitled", "issuer_identity", "security_identity",
                "listing_identity", "pam_security_id", "quote_currency", "eps",
            })

    def test_documented_properties_4a_through_4h_and_5_through_7_unresolved(self):
        text = (Path(__file__).resolve().parents[1] / "EXPECTED_RETURN_PR4D3B.md").read_text()
        for obligation in ("4A", "4B", "4C", "4D", "4E", "4F", "4G", "4H"):
            self.assertIn("| " + obligation + " |", text)
        self.assertIn("Obligations 5–7 remain unresolved", text)


if __name__ == "__main__":
    unittest.main()
