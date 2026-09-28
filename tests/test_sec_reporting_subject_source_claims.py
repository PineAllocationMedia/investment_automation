"""PR5C0A controlled source foundation; no continuity or blocker discharge."""
import ast
from dataclasses import fields
import inspect
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from economic_facts import sec_reporting_subject_source_claims as source
from economic_facts.sec_filing_archive import SecFilingArchive
from economic_facts.sec_submissions_archive import SecSubmissionsArchive
from tests.sec_reporting_subject_source_claims_fixtures import reporting_subject_filing
from tests.sec_submissions_fixtures import CIK, NAME, T1, T2, reference, root, row


class SecReportingSubjectSourceClaimsTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        base = Path(temporary.name).resolve()
        self.submissions = SecSubmissionsArchive(base / "submissions")
        self.filings = SecFilingArchive(base / "filings")

    def parent(self, rows, *, refs=None):
        return self.submissions._capture_live(
            root(rows=rows, refs=refs), cik=CIK, captured_at=T1)

    def filing(self, filing_row, *, blocks=(), exhibit_blocks=(), captured_at=T2):
        return self.filings._capture_live(
            reporting_subject_filing(
                cik=CIK,
                accession=filing_row["accessionNumber"],
                form=filing_row["form"],
                blocks=blocks,
                exhibit_blocks=exhibit_blocks,
                primary_filename=filing_row["primaryDocument"],
            ),
            cik=CIK,
            accession=filing_row["accessionNumber"],
            captured_at=captured_at,
        )

    def assess(self, parent, *filings, children=()):
        return source.build_sec_reporting_subject_source_foundation(
            self.submissions,
            self.filings,
            source.SecReportingSubjectSourceRequest(
                parent.receipt_id,
                tuple(child.receipt_id for child in children),
                tuple(filing.receipt_id for filing in filings),
            ),
        )

    def test_exact_public_api_and_structurally_closed_request(self):
        self.assertEqual(set(inspect.signature(
            source.build_sec_reporting_subject_source_foundation).parameters),
            {"submissions_archive", "filing_archive", "request"})
        self.assertEqual([field.name for field in fields(
            source.SecReportingSubjectSourceRequest)], [
                "parent_submissions_receipt_id", "child_submissions_receipt_ids",
                "filing_receipt_ids"])
        parent = self.parent([])
        for keyword in ("history_complete", "same_subject", "no_reverse_acquisition",
                        "no_predecessor", "continuous", "qualified", "subject_id", "cik"):
            with self.subTest(keyword=keyword), self.assertRaises(TypeError):
                source.SecReportingSubjectSourceRequest(
                    parent.receipt_id, **{keyword: True})

    def test_malformed_duplicate_and_untyped_requests_fail(self):
        for value in (None, True, "", "0" * 63, "A" * 64, "../" + "0" * 64):
            with self.subTest(value=value), self.assertRaises(
                    source.SecReportingSubjectSourceRequestError):
                source.SecReportingSubjectSourceRequest(value)
        with self.assertRaises(source.SecReportingSubjectSourceRequestError):
            source.SecReportingSubjectSourceRequest("0" * 64, (), ("1" * 64, "1" * 64))
        request = source.SecReportingSubjectSourceRequest("0" * 64)
        for archives in ((object(), self.filings), (self.submissions, object())):
            with self.assertRaises(source.SecReportingSubjectSourceRequestError):
                source.build_sec_reporting_subject_source_foundation(*archives, request)

    def test_ordinary_complete_source_set_does_not_claim_continuity_or_no_transition(self):
        annual = row(form="10-K", items="")
        parent = self.parent([annual])
        filing = self.filing(annual, blocks=("Ordinary annual financial statements.",))
        assessment = self.assess(parent, filing)
        self.assertEqual(assessment.status,
                         source.ReportingSubjectSourceStatus.CAPTURED_REPORTING_SUBJECT_SOURCE_SET)
        self.assertEqual(assessment.explicit_claims, ())
        self.assertEqual(len(assessment.filing_universe), 1)
        self.assertIn("NO_REPORTING_SUBJECT_CONTINUITY_CONCLUSION", assessment.limitations)
        self.assertIn("ABSENCE_OF_A_TRANSITION_CLAIM_IS_NOT_CONTINUITY_EVIDENCE",
                      assessment.limitations)
        self.assertFalse(any("CONTINUITY_ESTABLISHED" in item for item in assessment.limitations))

    def test_incomplete_referenced_history_stays_incomplete(self):
        annual = row(form="10-K")
        parent = self.parent([annual], refs=[reference()])
        filing = self.filing(annual)
        assessment = self.assess(parent, filing)
        self.assertEqual(assessment.status,
                         source.ReportingSubjectSourceStatus.INCOMPLETE_REPORTING_SUBJECT_SOURCE_SET)
        self.assertIn(source.ReportingSubjectSourceIssue.D2B_REFERENCE_CLOSURE_INCOMPLETE,
                      {item.issue for item in assessment.source_issues})

    def test_missing_relevant_filing_capture_stays_incomplete(self):
        parent = self.parent([row(form="10-Q")])
        assessment = self.assess(parent)
        self.assertEqual(assessment.status,
                         source.ReportingSubjectSourceStatus.INCOMPLETE_REPORTING_SUBJECT_SOURCE_SET)
        self.assertEqual(assessment.filing_universe[0].captures, ())

    def test_explicit_predecessor_successor_claims_preserve_exact_passage_and_provenance(self):
        annual = row(form="10-K")
        passage = "Legacy Alpha, Inc. was the predecessor, and New Alpha, Inc. is the successor."
        parent = self.parent([annual])
        filing = self.filing(annual, blocks=(passage,))
        assessment = self.assess(parent, filing)
        kinds = {claim.kind for claim in assessment.explicit_claims}
        self.assertTrue({source.ReportingSubjectClaimKind.PREDECESSOR_REFERENCE,
                         source.ReportingSubjectClaimKind.SUCCESSOR_REFERENCE,
                         source.ReportingSubjectClaimKind.PREDECESSOR_SUCCESSOR_TRANSITION} <= kinds)
        claim = next(claim for claim in assessment.explicit_claims
                     if claim.kind is source.ReportingSubjectClaimKind.PREDECESSOR_SUCCESSOR_TRANSITION)
        self.assertEqual(claim.exact_source_passage, passage)
        self.assertEqual(claim.evidence_occurrences[0].filing_receipt_id, filing.receipt_id)
        self.assertEqual(claim.evidence_occurrences[0].filing_captured_at, T2)

    def test_explicit_accounting_acquirer_label_is_source_local(self):
        current = row(form="8-K", items="2.01, 5.01, 9.01")
        passage = ("Legacy Alpha, Inc. was determined to be the accounting acquirer and "
                   "continuing reporting entity.")
        assessment = self.assess(self.parent([current]), self.filing(current, blocks=(passage,)))
        kinds = {claim.kind for claim in assessment.explicit_claims}
        self.assertIn(source.ReportingSubjectClaimKind.ACCOUNTING_ACQUIRER_REFERENCE, kinds)
        self.assertIn(source.ReportingSubjectClaimKind.ACCOUNTING_ACQUIRER_BECOMES_REPORTING_ENTITY,
                      kinds)
        claim = next(claim for claim in assessment.explicit_claims
                     if claim.kind is source.ReportingSubjectClaimKind.ACCOUNTING_ACQUIRER_REFERENCE)
        self.assertEqual(claim.subject_labels[0].exact_source_label, "Legacy Alpha, Inc.")
        self.assertEqual(claim.subject_labels[0].role, "ACCOUNTING_ACQUIRER")
        self.assertNotEqual(claim.subject_labels[0].source_local_id, assessment.source_cik)

    def test_reverse_acquisition_and_reverse_recapitalization_remain_distinct(self):
        current = row(form="8-K", items="5.06")
        assessment = self.assess(
            self.parent([current]),
            self.filing(current, blocks=(
                "The transaction was accounted for as a reverse acquisition.",
                "The shell transaction is a reverse recapitalization.",
            )))
        kinds = {claim.kind for claim in assessment.explicit_claims}
        self.assertIn(source.ReportingSubjectClaimKind.REVERSE_ACQUISITION_REFERENCE, kinds)
        self.assertIn(source.ReportingSubjectClaimKind.REVERSE_RECAPITALIZATION_REFERENCE, kinds)

    def test_item_signals_never_create_subject_transition_claims(self):
        current = row(form="8-K", items="2.01,4.01,5.01,5.03,5.06,9.01")
        assessment = self.assess(
            self.parent([current]),
            self.filing(current, blocks=("The registrant completed an ordinary asset acquisition.",)))
        self.assertEqual(assessment.explicit_claims, ())
        self.assertEqual({item.kind for item in assessment.filing_signals},
                         set(source.ReportingSubjectSignalKind))
        self.assertEqual(assessment.status,
                         source.ReportingSubjectSourceStatus.CAPTURED_REPORTING_SUBJECT_SOURCE_SET)

    def test_name_or_fiscal_year_change_alone_is_not_subject_reset(self):
        current = row(form="8-K", items="5.03")
        assessment = self.assess(
            self.parent([current]),
            self.filing(current, blocks=(
                "The registrant changed its name and adopted a December fiscal year end.",)))
        self.assertEqual(assessment.explicit_claims, ())
        self.assertEqual([item.kind for item in assessment.filing_signals],
                         [source.ReportingSubjectSignalKind.FISCAL_YEAR_CHANGE_SIGNAL])

    def test_period_labels_and_embedded_financial_statement_claims_remain_visible(self):
        annual = row(form="10-K")
        assessment = self.assess(
            self.parent([annual]),
            self.filing(annual, blocks=("Predecessor Period", "Successor Period"),
                        exhibit_blocks=("Carve-out financial statements",
                                        "Combined financial statements")))
        kinds = {claim.kind for claim in assessment.explicit_claims}
        self.assertIn(source.ReportingSubjectClaimKind.PREDECESSOR_PERIOD_LABEL, kinds)
        self.assertIn(source.ReportingSubjectClaimKind.SUCCESSOR_PERIOD_LABEL, kinds)
        self.assertIn(source.ReportingSubjectClaimKind.CARVE_OUT_FINANCIAL_STATEMENTS_REFERENCE,
                      kinds)
        self.assertIn(source.ReportingSubjectClaimKind.COMBINED_FINANCIAL_STATEMENTS_REFERENCE,
                      kinds)
        self.assertEqual({claim.document_ordinal for claim in assessment.explicit_claims
                          if claim.kind in {
                              source.ReportingSubjectClaimKind.CARVE_OUT_FINANCIAL_STATEMENTS_REFERENCE,
                              source.ReportingSubjectClaimKind.COMBINED_FINANCIAL_STATEMENTS_REFERENCE}},
                         {1})

    def test_unknown_restructuring_language_fails_closed(self):
        annual = row(form="10-K")
        passage = "A bespoke restructuring changed the financial statements in an unexplained way."
        assessment = self.assess(
            self.parent([annual]), self.filing(annual, blocks=(passage,)))
        self.assertEqual(assessment.status,
                         source.ReportingSubjectSourceStatus.UNSUPPORTED_SOURCE_PROFILE)
        self.assertIn(source.ReportingSubjectClaimKind.UNINTERPRETED_RESTRUCTURING_LANGUAGE,
                      {claim.kind for claim in assessment.explicit_claims})
        self.assertEqual(next(item.exact_source_text for item in assessment.source_issues
                              if item.issue is source.ReportingSubjectSourceIssue.
                              UNINTERPRETED_RESTRUCTURING_LANGUAGE), passage)

    def test_unreviewed_8k_item_metadata_fails_closed_without_claim(self):
        current = row(form="8-K", items="2.01, 7.99")
        assessment = self.assess(self.parent([current]), self.filing(current))
        self.assertEqual(assessment.status,
                         source.ReportingSubjectSourceStatus.CAPTURED_REPORTING_SUBJECT_SOURCE_SET)
        self.assertEqual([signal.kind for signal in assessment.filing_signals],
                         [source.ReportingSubjectSignalKind.ACQUISITION_DISPOSITION_SIGNAL])
        self.assertEqual(assessment.explicit_claims, ())
        self.assertIn(source.ReportingSubjectSourceIssue.UNREVIEWED_8K_ITEM_METADATA,
                      {item.issue for item in assessment.source_issues})

    def test_inline_xbrl_visible_text_is_supported_but_hidden_text_is_not_a_claim(self):
        annual = row(form="10-K")
        visible = ("<ix:nonnumeric name='dei:EntityRegistrantName'>Fictional</ix:nonnumeric> "
                   "The transaction was accounted for as a reverse acquisition.")
        hidden = ("<ix:hidden><ix:nonnumeric name='fake:Note'>"
                  "Hidden reverse recapitalization.</ix:nonnumeric></ix:hidden>")
        assessment = self.assess(
            self.parent([annual]), self.filing(annual, blocks=(hidden, visible)))
        kinds = [claim.kind for claim in assessment.explicit_claims]
        self.assertEqual(kinds.count(
            source.ReportingSubjectClaimKind.REVERSE_ACQUISITION_REFERENCE), 1)
        self.assertNotIn(source.ReportingSubjectClaimKind.REVERSE_RECAPITALIZATION_REFERENCE,
                         kinds)
        self.assertEqual(assessment.status,
                         source.ReportingSubjectSourceStatus.CAPTURED_REPORTING_SUBJECT_SOURCE_SET)

    def test_differing_recaptures_conflict_and_no_latest_wins(self):
        annual = row(form="10-K")
        parent = self.parent([annual])
        first = self.filing(annual, blocks=("Alpha Inc. was the predecessor.",), captured_at=T1)
        second = self.filing(annual, blocks=("Beta Inc. was the predecessor.",), captured_at=T2)
        assessment = self.assess(parent, second, first)
        self.assertEqual(assessment.status, source.ReportingSubjectSourceStatus.SOURCE_CONFLICT)
        self.assertEqual(len(assessment.filing_universe[0].captures), 2)
        self.assertEqual({claim.exact_source_passage for claim in assessment.explicit_claims},
                         {"Alpha Inc. was the predecessor.", "Beta Inc. was the predecessor."})

    def test_original_and_amendment_incompatible_subject_labels_conflict(self):
        original = row(number=1, form="8-K", items="2.01", reportDate="2026-01-15")
        amendment = row(number=2, form="8-K/A", items="9.01", reportDate="2026-01-15")
        assessment = self.assess(
            self.parent([original, amendment]),
            self.filing(original, blocks=(
                "Alpha Operating Inc. was determined to be the accounting acquirer.",)),
            self.filing(amendment, blocks=(
                "Beta Operating Inc. was determined to be the accounting acquirer.",)),
        )
        self.assertEqual(assessment.status, source.ReportingSubjectSourceStatus.SOURCE_CONFLICT)
        self.assertIn(source.ReportingSubjectSourceIssue.INCOMPATIBLE_SUBJECT_LABELS,
                      {item.issue for item in assessment.conflicts})

    def test_8ka_is_in_source_universe_and_document_replay(self):
        amendment = row(form="8-K/A", items="9.01")
        filing = self.filing(amendment, blocks=(
            "The transaction was accounted for as a reverse acquisition.",))
        assessment = self.assess(self.parent([amendment]), filing)
        self.assertEqual(assessment.filing_universe[0].captures[0].document_inventory.form,
                         "8-K/A")
        self.assertEqual(assessment.status,
                         source.ReportingSubjectSourceStatus.CAPTURED_REPORTING_SUBJECT_SOURCE_SET)

    def test_equivalent_recapture_preserves_semantics_and_enriches_evidence(self):
        annual = row(form="10-K")
        raw = reporting_subject_filing(
            cik=CIK, accession=annual["accessionNumber"], form="10-K",
            blocks=("Alpha Inc. was the predecessor.",),
            primary_filename=annual["primaryDocument"])
        first = self.filings._capture_live(raw, cik=CIK,
                                           accession=annual["accessionNumber"], captured_at=T1)
        second = self.filings._capture_live(raw, cik=CIK,
                                            accession=annual["accessionNumber"], captured_at=T2)
        one = self.assess(self.parent([annual]), first)
        both = self.assess(one.submissions_inventory.parent, second, first)
        self.assertEqual(one.semantic_id, both.semantic_id)
        self.assertNotEqual(one.evidence_id, both.evidence_id)
        self.assertEqual(len(both.explicit_claims[0].evidence_occurrences), 2)

    def test_caller_permutation_does_not_change_identities(self):
        annual = row(number=1, form="10-K")
        quarter = row(number=2, form="10-Q", reportDate="2026-03-31")
        parent = self.parent([annual, quarter])
        first = self.filing(annual, blocks=("Alpha Inc. was the predecessor.",))
        second = self.filing(quarter, blocks=("Successor Period",))
        left = self.assess(parent, first, second)
        right = self.assess(parent, second, first)
        self.assertEqual((left.semantic_id, left.evidence_id),
                         (right.semantic_id, right.evidence_id))

    def test_foreign_cik_and_accession_receipts_fail(self):
        annual = row(form="10-K")
        parent = self.parent([annual])
        foreign_raw = reporting_subject_filing(
            cik="0000000456", accession=annual["accessionNumber"], form="10-K")
        foreign = self.filings._capture_live(
            foreign_raw, cik="0000000456", accession=annual["accessionNumber"], captured_at=T2)
        with self.assertRaises(source.SecReportingSubjectSourceRequestError):
            self.assess(parent, foreign)
        other = row(number=9, form="10-K")
        other_receipt = self.filing(other)
        with self.assertRaises(source.SecReportingSubjectSourceRequestError):
            self.assess(parent, other_receipt)

    def test_replay_is_offline_read_only_and_has_no_clock(self):
        annual = row(form="10-K")
        parent = self.parent([annual])
        filing = self.filing(annual)
        roots = (self.submissions.root, self.filings.root)
        before = [{path.relative_to(root): path.read_bytes()
                   for path in root.rglob("*") if path.is_file()} for root in roots]
        with patch("urllib.request.urlopen", side_effect=AssertionError("network forbidden")), \
             patch("os.listdir", side_effect=AssertionError("directory scan forbidden")), \
             patch("os.scandir", side_effect=AssertionError("directory scan forbidden")), \
             patch("time.time", side_effect=AssertionError("clock forbidden")):
            self.assess(parent, filing)
        after = [{path.relative_to(root): path.read_bytes()
                  for path in root.rglob("*") if path.is_file()} for root in roots]
        self.assertEqual(before, after)

    def test_no_continuity_blocker_or_admission_surface(self):
        names = set(vars(source))
        for forbidden in ("AdmissionBlocker", "qualify_reporting_subject", "AuthorityProperty",
                          "CONTINUITY_ESTABLISHED", "NO_SUBJECT_CHANGE", "NO_PREDECESSOR"):
            self.assertNotIn(forbidden, names)
        result_fields = {field.name for field in fields(
            source.SecReportingSubjectSourceAssessment)}
        self.assertFalse(result_fields & {"qualified", "continuous", "admission_blockers",
                                          "same_subject", "authority"})


class SecReportingSubjectSourceDependencyTests(unittest.TestCase):
    def test_exact_dependency_direction_and_no_synthetic_or_model_imports(self):
        root_dir = Path(__file__).resolve().parents[1]
        module = root_dir / "economic_facts/sec_reporting_subject_source_claims.py"
        tree = ast.parse(module.read_text())
        allowed_relative = {"sec_filing_archive", "sec_filing_document_inventory",
                            "sec_submissions_archive", "sec_submissions_inventory"}
        allowed_standard = {"dataclasses", "enum", "html.parser", "re"}
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name for alias in node.names)
                self.assertTrue(all(alias.name in allowed_standard for alias in node.names))
            elif isinstance(node, ast.ImportFrom):
                imported.add(node.module or "")
                self.assertTrue((node.level == 1 and node.module in allowed_relative)
                                or (node.level == 0 and node.module in allowed_standard))
            elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                self.assertNotIn(node.func.id, {"open", "eval", "exec", "__import__", "float"})
        for forbidden in ("reporting_subject", "share_basis", "security_identity",
                          "source_authority", "expected_return", "src", "pit_comparison"):
            self.assertFalse(any(name == forbidden or name.startswith(forbidden + ".")
                                 for name in imported))

    def test_no_reverse_model_runtime_or_v1_consumers(self):
        root_dir = Path(__file__).resolve().parents[1]
        needle = "sec_reporting_subject_source_claims"
        allowed = {"test_sec_reporting_subject_source_claims.py"}
        for directory in ("src", "pit_comparison", "economic_facts", "scripts"):
            for path in (root_dir / directory).rglob("*.py"):
                if path.name == "sec_reporting_subject_source_claims.py":
                    continue
                self.assertNotIn(needle, path.read_text(), str(path))
        self.assertEqual(allowed, {"test_sec_reporting_subject_source_claims.py"})


if __name__ == "__main__":
    unittest.main()
