"""PR5C0B controlled source claims; never share-basis qualification."""
import ast
from dataclasses import fields
import inspect
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from economic_facts import sec_share_basis_source_claims as source
from economic_facts.sec_filing_archive import SecFilingArchive
from economic_facts.sec_submissions_archive import SecSubmissionsArchive
from tests.sec_share_basis_source_claims_fixtures import share_basis_filing
from tests.sec_submissions_fixtures import CIK, T1, T2, reference, root, row


class SecShareBasisSourceClaimsTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        base = Path(temporary.name).resolve()
        self.submissions = SecSubmissionsArchive(base / "submissions")
        self.filings = SecFilingArchive(base / "filings")

    def parent(self, rows, *, refs=None):
        return self.submissions._capture_live(
            root(rows=rows, refs=refs), cik=CIK, captured_at=T1)

    def filing(self, filing_row, *, blocks=(), exhibit_blocks=(), captured_at=T2,
               source_form=None):
        return self.filings._capture_live(
            share_basis_filing(
                cik=CIK,
                accession=filing_row["accessionNumber"],
                form=source_form or filing_row["form"],
                blocks=blocks,
                exhibit_blocks=exhibit_blocks,
                primary_filename=filing_row["primaryDocument"],
            ),
            cik=CIK,
            accession=filing_row["accessionNumber"],
            captured_at=captured_at,
        )

    def assess(self, parent, *filings, children=()):
        return source.build_sec_share_basis_source_foundation(
            self.submissions,
            self.filings,
            source.SecShareBasisSourceRequest(
                parent.receipt_id,
                tuple(child.receipt_id for child in children),
                tuple(filing.receipt_id for filing in filings),
            ),
        )

    def test_exact_public_api_and_closed_request(self):
        self.assertEqual(set(inspect.signature(
            source.build_sec_share_basis_source_foundation).parameters),
            {"submissions_archive", "filing_archive", "request"})
        self.assertEqual([field.name for field in fields(source.SecShareBasisSourceRequest)], [
            "parent_submissions_receipt_id", "child_submissions_receipt_ids",
            "filing_receipt_ids"])
        parent = self.parent([])
        for keyword in ("same_basis", "no_split", "no_corporate_action",
                        "basis_complete", "qualified", "security_id", "ticker"):
            with self.subTest(keyword=keyword), self.assertRaises(TypeError):
                source.SecShareBasisSourceRequest(
                    parent.receipt_id, **{keyword: True})

    def test_malformed_duplicate_and_untyped_requests_fail(self):
        for value in (None, True, "", "0" * 63, "A" * 64, "../" + "0" * 64):
            with self.subTest(value=value), self.assertRaises(
                    source.SecShareBasisSourceRequestError):
                source.SecShareBasisSourceRequest(value)
        with self.assertRaises(source.SecShareBasisSourceRequestError):
            source.SecShareBasisSourceRequest("0" * 64, (), ("1" * 64, "1" * 64))
        request = source.SecShareBasisSourceRequest("0" * 64)
        for archives in ((object(), self.filings), (self.submissions, object())):
            with self.assertRaises(source.SecShareBasisSourceRequestError):
                source.build_sec_share_basis_source_foundation(*archives, request)

    def test_ordinary_source_set_preserves_universe_without_no_action_claim(self):
        rows = [row(number=index + 1, form=form, items="") for index, form in enumerate(
            ("10-K", "10-K/A", "10-Q", "10-Q/A", "8-K", "8-K/A"))]
        parent = self.parent(rows)
        filings = tuple(self.filing(item, blocks=("Ordinary financial statements.",))
                        for item in rows)
        assessment = self.assess(parent, *filings)
        self.assertEqual(assessment.status,
                         source.ShareBasisSourceStatus.CAPTURED_SHARE_BASIS_SOURCE_SET)
        self.assertEqual(len(assessment.filing_universe), 6)
        self.assertEqual(assessment.explicit_claims, ())
        self.assertIn("EMPTY_DETECTED_EVENT_INVENTORY_IS_NOT_NO_ACTION_EVIDENCE",
                      assessment.limitations)
        self.assertIn("NO_SPLIT_BASIS_NOT_ESTABLISHED_DISCHARGE",
                      assessment.limitations)

    def test_affirmative_forward_split_ratio_effective_date_and_scope(self):
        annual = row(form="10-K")
        passage = ("A 2-for-1 stock split of our Common Stock became effective on "
                   "January 15, 2026.")
        assessment = self.assess(self.parent([annual]),
                                 self.filing(annual, blocks=(passage,)))
        action = next(claim for claim in assessment.explicit_claims
                      if claim.kind is source.ShareBasisClaimKind.STOCK_SPLIT_REFERENCE)
        self.assertEqual(action.lifecycle,
                         source.CorporateActionLifecycle.EFFECTIVE_OR_IMPLEMENTED_REFERENCE)
        self.assertEqual(action.claim_level,
                         source.SourceClaimLevel.AFFIRMATIVE_LIFECYCLE_ACTION_CLAIM)
        self.assertEqual((action.ratio.new_units, action.ratio.old_units), (2, 1))
        self.assertEqual(action.effective_date.normalized_date, "2026-01-15")
        self.assertEqual(action.class_link.scope,
                         source.SecurityClassSourceScope.ISSUER_COMMON_STOCK_GENERIC)
        self.assertEqual(action.exact_source_passage, passage)

    def test_affirmative_reverse_split_every_shares_ratio(self):
        current = row(form="8-K", items="3.03, 5.03, 8.01")
        passage = ("Every 10 shares of Class A Common Stock became 1 share when the "
                   "reverse stock split was implemented effective on 2026-02-01.")
        assessment = self.assess(self.parent([current]),
                                 self.filing(current, blocks=(passage,)))
        claim = next(claim for claim in assessment.explicit_claims
                     if claim.kind is source.ShareBasisClaimKind.REVERSE_STOCK_SPLIT_REFERENCE)
        self.assertEqual((claim.ratio.new_units, claim.ratio.old_units), (1, 10))
        self.assertEqual(claim.class_link.scope,
                         source.SecurityClassSourceScope.NAMED_COMMON_CLASS_EXPLICIT)
        self.assertEqual({signal.kind for signal in assessment.filing_signals}, {
            source.ShareBasisSignalKind.MATERIAL_MODIFICATION_TO_RIGHTS_SIGNAL,
            source.ShareBasisSignalKind.ARTICLES_OR_BYLAWS_AMENDMENT_SIGNAL,
            source.ShareBasisSignalKind.OTHER_EVENTS_SIGNAL,
        })

    def test_proposed_approved_cancelled_and_not_implemented_lifecycles(self):
        passages = (
            ("The Company may seek approval for a 1-for-10 reverse stock split.",
             source.CorporateActionLifecycle.ANNOUNCED_OR_PROPOSED_REFERENCE),
            ("Stockholders approved a 1-for-10 reverse stock split.",
             source.CorporateActionLifecycle.APPROVED_REFERENCE),
            ("The proposed 1-for-10 reverse stock split was cancelled.",
             source.CorporateActionLifecycle.CANCELLED_OR_NOT_IMPLEMENTED_REFERENCE),
            ("The Company did not effect a 1-for-10 reverse stock split.",
             source.CorporateActionLifecycle.CANCELLED_OR_NOT_IMPLEMENTED_REFERENCE),
        )
        for index, (passage, expected) in enumerate(passages, start=1):
            with self.subTest(passage=passage):
                current = row(number=index, form="8-K")
                assessment = self.assess(self.parent([current]),
                                         self.filing(current, blocks=(passage,)))
                claim = next(claim for claim in assessment.explicit_claims
                             if claim.kind is
                             source.ShareBasisClaimKind.REVERSE_STOCK_SPLIT_REFERENCE)
                self.assertEqual(claim.lifecycle, expected)
                if expected is not source.CorporateActionLifecycle.EFFECTIVE_OR_IMPLEMENTED_REFERENCE:
                    self.assertNotEqual(claim.lifecycle,
                                        source.CorporateActionLifecycle.EFFECTIVE_OR_IMPLEMENTED_REFERENCE)

    def test_explicit_lifecycle_negation_precedes_positive_tokens(self):
        passages = (
            "The board did not approve the reverse stock split.",
            "The reverse stock split was not approved.",
            "The reverse stock split was not effective on January 15, 2026.",
            "The reverse stock split did not become effective.",
            "The approved reverse stock split will not be implemented.",
            "The reverse stock split was not authorized.",
            "The reverse stock split did not receive approval.",
            "The reverse stock split will not be effected.",
            "The reverse stock split will not become effective.",
            "The reverse stock split was never effected.",
            "The reverse stock split was never implemented.",
        )
        for index, passage in enumerate(passages, start=1):
            with self.subTest(passage=passage):
                current = row(number=index, form="8-K")
                assessment = self.assess(self.parent([current]),
                                         self.filing(current, blocks=(passage,)))
                claim = next(claim for claim in assessment.explicit_claims
                             if claim.kind is
                             source.ShareBasisClaimKind.REVERSE_STOCK_SPLIT_REFERENCE)
                self.assertEqual(
                    claim.lifecycle,
                    source.CorporateActionLifecycle.CANCELLED_OR_NOT_IMPLEMENTED_REFERENCE,
                )

    def test_affirmative_lifecycle_grammar_remains_supported(self):
        passages = (
            ("Stockholders approved a 1-for-10 reverse stock split.",
             source.CorporateActionLifecycle.APPROVED_REFERENCE),
            ("The 1-for-10 reverse stock split became effective on January 15, 2026.",
             source.CorporateActionLifecycle.EFFECTIVE_OR_IMPLEMENTED_REFERENCE),
            ("The 1-for-10 reverse stock split was implemented on January 15, 2026.",
             source.CorporateActionLifecycle.EFFECTIVE_OR_IMPLEMENTED_REFERENCE),
        )
        for index, (passage, expected) in enumerate(passages, start=1):
            with self.subTest(passage=passage):
                current = row(number=index, form="8-K")
                assessment = self.assess(self.parent([current]),
                                         self.filing(current, blocks=(passage,)))
                claim = next(claim for claim in assessment.explicit_claims
                             if claim.kind is
                             source.ShareBasisClaimKind.REVERSE_STOCK_SPLIT_REFERENCE)
                self.assertEqual(claim.lifecycle, expected)

    def test_conditional_ratio_without_action_is_not_completed_event(self):
        current = row(form="8-K")
        passage = "If approved, every 10 shares would become one share."
        assessment = self.assess(self.parent([current]),
                                 self.filing(current, blocks=(passage,)))
        self.assertFalse(any(claim.lifecycle is
                             source.CorporateActionLifecycle.EFFECTIVE_OR_IMPLEMENTED_REFERENCE
                             for claim in assessment.explicit_claims))
        self.assertFalse(any(claim.kind is
                             source.ShareBasisClaimKind.REVERSE_STOCK_SPLIT_REFERENCE
                             for claim in assessment.explicit_claims))

    def test_ambiguous_ratio_is_retained_and_unsupported(self):
        current = row(form="8-K")
        assessment = self.assess(
            self.parent([current]),
            self.filing(current, blocks=("The proposed stock split ratio is 1:10.",)))
        self.assertEqual(assessment.status,
                         source.ShareBasisSourceStatus.UNSUPPORTED_SOURCE_PROFILE)
        self.assertIn(source.ShareBasisSourceIssue.AMBIGUOUS_RATIO_ORIENTATION,
                      {item.issue for item in assessment.source_issues})
        ratio = next(claim for claim in assessment.explicit_claims
                     if claim.kind is source.ShareBasisClaimKind.SPLIT_RATIO_REFERENCE)
        self.assertIsNone(ratio.ratio)

    def test_conflicting_source_local_ratios_are_conflict(self):
        current = row(form="8-K")
        passage = "The 2-for-1 and 3-for-1 stock split became effective on 2026-01-01."
        assessment = self.assess(self.parent([current]),
                                 self.filing(current, blocks=(passage,)))
        self.assertEqual(assessment.status, source.ShareBasisSourceStatus.SOURCE_CONFLICT)
        self.assertIn(source.ShareBasisSourceIssue.CONFLICTING_SOURCE_LOCAL_RATIOS,
                      {item.issue for item in assessment.conflicts})

    def test_explicit_record_date_is_distinct_from_effective_and_filing_dates(self):
        current = row(form="8-K")
        passage = ("The 3-for-2 stock split has a record date of January 10, 2026 "
                   "and became effective on January 20, 2026.")
        assessment = self.assess(self.parent([current]),
                                 self.filing(current, blocks=(passage,)))
        claim = next(claim for claim in assessment.explicit_claims
                     if claim.kind is source.ShareBasisClaimKind.STOCK_SPLIT_REFERENCE)
        self.assertEqual(claim.record_date.normalized_date, "2026-01-10")
        self.assertEqual(claim.effective_date.normalized_date, "2026-01-20")
        self.assertNotEqual(claim.record_date, claim.effective_date)

    def test_declaration_effective_market_effective_record_and_ex_dates_stay_separate(self):
        current = row(form="8-K")
        passage = ("The 2-for-1 stock split was announced on January 2, 2026, has a "
                   "record date of January 10, 2026, an ex-date of January 11, 2026, "
                   "became effective on January 12, 2026, and has a market effective "
                   "date of January 13, 2026.")
        assessment = self.assess(self.parent([current]),
                                 self.filing(current, blocks=(passage,)))
        claim = next(claim for claim in assessment.explicit_claims
                     if claim.kind is source.ShareBasisClaimKind.STOCK_SPLIT_REFERENCE)
        self.assertEqual(claim.declaration_date.normalized_date, "2026-01-02")
        self.assertEqual(claim.record_date.normalized_date, "2026-01-10")
        self.assertEqual(claim.ex_date.normalized_date, "2026-01-11")
        self.assertEqual(claim.effective_date.normalized_date, "2026-01-12")
        self.assertEqual(claim.market_effective_date.normalized_date, "2026-01-13")
        self.assertEqual({claim.declaration_date.kind, claim.record_date.kind,
                          claim.ex_date.kind, claim.effective_date.kind,
                          claim.market_effective_date.kind}, set(source.ActionDateKind))

    def test_ambiguous_effective_date_is_retained_but_unsupported(self):
        current = row(form="8-K")
        passage = "The 1-for-5 reverse stock split effective date remains to be determined."
        assessment = self.assess(self.parent([current]),
                                 self.filing(current, blocks=(passage,)))
        self.assertEqual(assessment.status,
                         source.ShareBasisSourceStatus.UNSUPPORTED_SOURCE_PROFILE)
        self.assertIn(source.ShareBasisSourceIssue.AMBIGUOUS_ACTION_DATE,
                      {item.issue for item in assessment.source_issues})
        date_claim = next(claim for claim in assessment.explicit_claims
                          if claim.kind is
                          source.ShareBasisClaimKind.ACTION_EFFECTIVE_DATE_REFERENCE)
        self.assertIsNone(date_claim.effective_date)

    def test_conflicting_effective_dates_in_one_source_local_action_are_conflict(self):
        current = row(form="8-K")
        passage = ("The 1-for-5 reverse stock split became effective on January 10, 2026 "
                   "and effective on January 11, 2026.")
        assessment = self.assess(self.parent([current]),
                                 self.filing(current, blocks=(passage,)))
        self.assertEqual(assessment.status, source.ShareBasisSourceStatus.SOURCE_CONFLICT)
        self.assertIn(source.ShareBasisSourceIssue.CONFLICTING_SOURCE_LOCAL_EFFECTIVE_DATES,
                      {item.issue for item in assessment.conflicts})

    def test_retrospective_all_periods_share_per_share_and_eps_claims(self):
        annual = row(form="10-K")
        passage = ("All historical share and per-share amounts and earnings per share "
                   "for all periods presented have been retroactively adjusted to reflect "
                   "the 2-for-1 stock split.")
        assessment = self.assess(self.parent([annual]),
                                 self.filing(annual, blocks=(passage,)))
        kinds = {claim.kind for claim in assessment.explicit_claims}
        self.assertTrue({
            source.ShareBasisClaimKind.RETROACTIVE_SHARE_ADJUSTMENT_REFERENCE,
            source.ShareBasisClaimKind.RETROACTIVE_PER_SHARE_ADJUSTMENT_REFERENCE,
            source.ShareBasisClaimKind.HISTORICAL_EPS_ADJUSTED_FOR_ACTION_REFERENCE,
        } <= kinds)
        for claim in assessment.explicit_claims:
            if claim.kind in kinds - {source.ShareBasisClaimKind.STOCK_SPLIT_REFERENCE,
                                     source.ShareBasisClaimKind.SPLIT_RATIO_REFERENCE}:
                self.assertEqual(claim.retrospective_scope,
                                 source.RetrospectivePresentationScope.ALL_PERIODS_PRESENTED)

    def test_explicit_retrospective_negation_is_not_affirmative_adjustment(self):
        affirmative_adjustments = {
            source.ShareBasisClaimKind.RETROACTIVE_SHARE_ADJUSTMENT_REFERENCE,
            source.ShareBasisClaimKind.RETROACTIVE_PER_SHARE_ADJUSTMENT_REFERENCE,
            source.ShareBasisClaimKind.HISTORICAL_EPS_ADJUSTED_FOR_ACTION_REFERENCE,
        }
        passages = (
            "Historical EPS was not retroactively adjusted.",
            "Per-share amounts were not retrospectively adjusted.",
            "The Company did not restate prior share amounts to reflect the stock split.",
        )
        for index, passage in enumerate(passages, start=1):
            with self.subTest(passage=passage):
                annual = row(number=index, form="10-K")
                assessment = self.assess(self.parent([annual]),
                                         self.filing(annual, blocks=(passage,)))
                self.assertTrue(affirmative_adjustments.isdisjoint(
                    claim.kind for claim in assessment.explicit_claims))

    def test_retrospective_specific_and_vague_scope_remain_bounded(self):
        annual = row(form="10-K")
        assessment = self.assess(self.parent([annual]), self.filing(annual, blocks=(
            "Per share amounts for the year ended December 31, 2025 were retroactively adjusted.",
            "Historical EPS was retroactively adjusted where applicable.",
        )))
        scopes = {claim.retrospective_scope for claim in assessment.explicit_claims
                  if claim.kind in {
                      source.ShareBasisClaimKind.RETROACTIVE_PER_SHARE_ADJUSTMENT_REFERENCE,
                      source.ShareBasisClaimKind.HISTORICAL_EPS_ADJUSTED_FOR_ACTION_REFERENCE}}
        self.assertEqual(scopes, {
            source.RetrospectivePresentationScope.SPECIFIC_PERIOD_REFERENCE,
            source.RetrospectivePresentationScope.VAGUE_OR_UNRESOLVED,
        })

    def test_other_basis_affecting_actions_remain_distinct(self):
        cases = (
            ("A stock dividend was implemented for our Common Stock.",
             source.ShareBasisClaimKind.STOCK_DIVIDEND_REFERENCE),
            ("Class B Common Stock was converted into Class A Common Stock.",
             source.ShareBasisClaimKind.SHARE_CLASS_CONVERSION_REFERENCE),
            ("The recapitalization was completed.",
             source.ShareBasisClaimKind.RECAPITALIZATION_REFERENCE),
            ("The merger was completed through an exchange of Common Stock.",
             source.ShareBasisClaimKind.MERGER_SECURITY_EXCHANGE_REFERENCE),
            ("The spin-off was completed and affected the Common Stock share basis.",
             source.ShareBasisClaimKind.SPIN_OFF_REFERENCE),
            ("A share redenomination was implemented.",
             source.ShareBasisClaimKind.SHARE_REDENOMINATION_REFERENCE),
            ("A share consolidation was implemented.",
             source.ShareBasisClaimKind.SHARE_CONSOLIDATION_REFERENCE),
        )
        for index, (passage, expected) in enumerate(cases, start=1):
            with self.subTest(expected=expected):
                current = row(number=index, form="8-K")
                assessment = self.assess(self.parent([current]),
                                         self.filing(current, blocks=(passage,)))
                self.assertIn(expected, {claim.kind for claim in assessment.explicit_claims})

    def test_multiple_common_classes_and_other_security_scope_stay_explicit(self):
        annual = row(form="10-K")
        assessment = self.assess(self.parent([annual]), self.filing(annual, blocks=(
            "Class A Common Stock and Class B Common Stock were affected by the stock split.",
            "Preferred Stock warrants were affected by the recapitalization.",
        )))
        scopes = {claim.class_link.scope for claim in assessment.explicit_claims}
        self.assertIn(source.SecurityClassSourceScope.MULTIPLE_CLASSES_OR_AMBIGUOUS, scopes)
        self.assertIn(source.SecurityClassSourceScope.OTHER_SECURITY, scopes)
        self.assertTrue(all(claim.class_link.source_local_id != assessment.source_cik
                            for claim in assessment.explicit_claims))

    def test_reviewed_exhibit_is_consumed_and_other_documents_remain_inventory_only(self):
        current = row(form="8-K", items="9.01")
        assessment = self.assess(
            self.parent([current]),
            self.filing(current, blocks=("Ordinary event report.",), exhibit_blocks=(
                "A 1-for-4 reverse stock split was implemented effective on 2026-03-01.",
            )))
        claim = next(claim for claim in assessment.explicit_claims
                     if claim.kind is source.ShareBasisClaimKind.REVERSE_STOCK_SPLIT_REFERENCE)
        self.assertEqual(claim.document_ordinal, 1)
        self.assertEqual(claim.evidence_occurrences[0].filing_receipt_id,
                         assessment.filing_universe[0].captures[0].receipt.receipt_id)

    def test_incomplete_history_and_missing_capture_are_distinct(self):
        annual = row(form="10-K")
        assessment = self.assess(self.parent([annual], refs=[reference()]))
        self.assertEqual(assessment.status,
                         source.ShareBasisSourceStatus.INCOMPLETE_SHARE_BASIS_SOURCE_SET)
        issues = {item.issue for item in assessment.source_issues}
        self.assertIn(source.ShareBasisSourceIssue.D2B_REFERENCE_CLOSURE_INCOMPLETE, issues)
        self.assertIn(source.ShareBasisSourceIssue.MISSING_RELEVANT_FILING_CAPTURE, issues)

    def test_differing_recapture_bytes_are_conflict_and_equivalent_enriches_evidence(self):
        annual = row(form="10-K")
        parent = self.parent([annual])
        first = self.filing(annual, blocks=("A 2-for-1 stock split was implemented.",))
        equivalent = self.filing(annual, blocks=("A 2-for-1 stock split was implemented.",),
                                 captured_at="2026-09-22T00:00:03Z")
        one = self.assess(parent, first)
        two = self.assess(parent, equivalent, first)
        self.assertEqual(one.semantic_id, two.semantic_id)
        self.assertNotEqual(one.evidence_id, two.evidence_id)
        different = self.filing(annual, blocks=("A 3-for-1 stock split was implemented.",),
                                captured_at="2026-09-22T00:00:04Z")
        conflict = self.assess(parent, first, different)
        self.assertEqual(conflict.status, source.ShareBasisSourceStatus.SOURCE_CONFLICT)
        self.assertEqual(len(conflict.filing_universe[0].captures), 2)

    def test_form_mismatch_and_foreign_filing_fail_closed(self):
        annual = row(form="10-K")
        mismatch = self.filing(annual, source_form="10-Q")
        assessment = self.assess(self.parent([annual]), mismatch)
        self.assertEqual(assessment.status, source.ShareBasisSourceStatus.SOURCE_CONFLICT)
        foreign_row = row(number=2, form="10-K")
        foreign = self.filings._capture_live(
            share_basis_filing(cik="0000000002", accession=foreign_row["accessionNumber"]),
            cik="0000000002", accession=foreign_row["accessionNumber"], captured_at=T2)
        with self.assertRaises(source.SecShareBasisSourceRequestError):
            self.assess(self.parent([foreign_row]), foreign)

    def test_replay_is_offline_and_permutation_invariant(self):
        first_row = row(number=1, form="10-K")
        second_row = row(number=2, form="8-K")
        parent = self.parent([first_row, second_row])
        first = self.filing(first_row, blocks=("A 2-for-1 stock split was implemented.",))
        second = self.filing(second_row, blocks=("The stock split record date was 2026-01-02.",))
        with patch("urllib.request.urlopen", side_effect=AssertionError("network")):
            left = self.assess(parent, first, second)
            right = self.assess(parent, second, first)
        self.assertEqual(left.semantic_id, right.semantic_id)
        self.assertEqual(left.evidence_id, right.evidence_id)


class SecShareBasisSourceDependencyTests(unittest.TestCase):
    def test_source_module_has_no_synthetic_model_runtime_or_v1_dependency(self):
        path = Path(source.__file__)
        tree = ast.parse(path.read_text(encoding="utf-8"))
        imports = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imports.add(node.module or "")
        prohibited = ("share_basis", "expected_return", "model", "runtime", "portfolio")
        self.assertFalse(any(any(term in name for term in prohibited) for name in imports))

    def test_source_module_is_not_a_reverse_dependency_of_authority_paths(self):
        root_path = Path(__file__).resolve().parents[1]
        needle = "sec_share_basis_source_claims"
        consumers = []
        for base in (root_path / "src", root_path / "scripts", root_path / "model",
                     root_path / "runtime", root_path / "pit"):
            if not base.exists():
                continue
            for path in base.rglob("*.py"):
                if needle in path.read_text(encoding="utf-8"):
                    consumers.append(str(path.relative_to(root_path)))
        self.assertEqual(consumers, [])


if __name__ == "__main__":
    unittest.main()
