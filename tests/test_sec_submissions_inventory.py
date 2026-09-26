"""Fictional inventory replay, adversarial evidence and authority isolation."""
import ast
from dataclasses import asdict, replace
import json
import os
from pathlib import Path
import socket
import tempfile
import unittest
from unittest.mock import patch

from economic_facts import sec_submissions_archive as a
from economic_facts import sec_submissions_inventory as i
from tests.sec_submissions_fixtures import CIK, T1, T2, NAME, NAME2, root, history, row, reference, encode


class SubmissionsInventoryTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.archive = a.SecSubmissionsArchive(Path(temporary.name).resolve() / "archive")

    def parent(self, *, rows=None, refs=None, captured_at=T1, **changes):
        return self.archive._capture_live(root(rows, refs, **changes), cik=CIK, captured_at=captured_at)

    def child(self, parent, *, name=NAME, rows=None, captured_at=T2):
        return self.archive._capture_live(history(rows), cik=CIK, captured_at=captured_at,
                                          parent_receipt_id=parent.receipt_id, history_filename=name)

    def replay(self, parent, *children):
        return i.replay_sec_submissions_inventory(self.archive, i.SecSubmissionsInventoryRequest(
            parent.receipt_id, tuple(child.receipt_id for child in children)))

    def test_zero_references_closes_only_captured_reference_set(self):
        result = self.replay(self.parent())
        self.assertEqual(result.status, i.InventoryStatus.CAPTURED_REFERENCE_CLOSURE_COMPLETE)
        self.assertEqual(result.missing_history_filenames, ())
        self.assertEqual(len(result.occurrences), 1)
        self.assertEqual(dict(result.occurrences[0].fields), row())

    def test_empty_recent_and_child_arrays_supported(self):
        parent = self.parent(rows=[], refs=[reference()])
        result = self.replay(parent, self.child(parent, rows=[]))
        self.assertEqual(result.occurrences, ())
        self.assertEqual(result.observed_history_row_counts, ((NAME, 0),))
        self.assertEqual(result.status, i.InventoryStatus.CAPTURED_REFERENCE_CLOSURE_COMPLETE)

    def test_missing_child_is_normal_incomplete_evidence(self):
        parent = self.parent(refs=[reference(), reference(NAME2)])
        child = self.child(parent, rows=[row(2)])
        result = self.replay(parent, child)
        self.assertEqual(result.status, i.InventoryStatus.CAPTURED_REFERENCE_CLOSURE_INCOMPLETE)
        self.assertEqual(result.missing_history_filenames, (NAME2,))
        self.assertEqual(len(result.references), 2)
        self.assertEqual(len(result.occurrences), 2)

    def test_multiple_children_and_request_permutation(self):
        parent = self.parent(refs=[reference(), reference(NAME2)])
        left, right = self.child(parent, rows=[row(2)]), self.child(parent, name=NAME2, rows=[row(3)])
        result = self.replay(parent, left, right)
        reverse = self.replay(parent, right, left)
        self.assertEqual(result, reverse)
        self.assertEqual(result.evidence_id, reverse.evidence_id)
        self.assertEqual(result.status, i.InventoryStatus.CAPTURED_REFERENCE_CLOSURE_COMPLETE)

    def test_foreign_parent_child_cannot_substitute_old_or_new(self):
        old = self.parent(refs=[reference()])
        new = self.parent(refs=[reference()], captured_at=T2)
        for parent, foreign in ((old, self.child(new)), (new, self.child(old))):
            with self.assertRaises(i.InventoryRequestError):
                self.replay(parent, foreign)
        self.assertEqual(self.replay(old).status, i.InventoryStatus.CAPTURED_REFERENCE_CLOSURE_INCOMPLETE)

    def test_unreferenced_child_and_selector_mismatch_rejected(self):
        parent = self.parent(refs=[reference()])
        child = self.child(parent)
        forged = replace(child, history_filename=NAME2, endpoint=a.endpoint_for(CIK, NAME2))
        # Deliberately attacker-written receipt is not publication/qualification.
        target = self.archive.root / "receipts" / (forged.receipt_id + ".json")
        target.write_bytes(forged.to_bytes())
        with self.assertRaises(i.InventoryRequestError):
            self.replay(parent, forged)
        with self.assertRaises(i.InventoryRequestError):
            self.replay(parent, parent)

    def test_duplicate_receipts_and_multiple_recaptures_are_invalid(self):
        parent = self.parent(refs=[reference()])
        first = self.child(parent)
        second = self.child(parent, captured_at="2026-09-20T12:00:03Z")
        for children in ((first, first), (first, second)):
            with self.assertRaises(i.InventoryRequestError):
                self.replay(parent, *children)

    def test_malformed_requests(self):
        for parent, children in (("../x", ()), ("a" * 64, []), ("a" * 64, ("bad",)),
                                 (True, ()), ("a" * 64, ("b" * 64,) * 1001)):
            with self.assertRaises(i.InventoryRequestError):
                i.SecSubmissionsInventoryRequest(parent, children)
        with self.assertRaises(i.InventoryRequestError):
            i.replay_sec_submissions_inventory(self.archive, {})

    def test_supplied_missing_receipt_is_integrity_failure(self):
        parent = self.parent(refs=[reference()])
        with self.assertRaises(a.SubmissionsArchiveError):
            i.replay_sec_submissions_inventory(self.archive, i.SecSubmissionsInventoryRequest(parent.receipt_id, ("0" * 64,)))

    def test_corrupt_child_is_integrity_failure(self):
        parent = self.parent(refs=[reference()])
        child = self.child(parent)
        target = self.archive.root / "objects" / child.content_sha256
        target.chmod(0o600)
        target.write_bytes(b"x" * child.byte_length)
        with self.assertRaises(a.SubmissionsArchiveError):
            self.replay(parent, child)

    def test_source_conflicts_retain_every_occurrence(self):
        parent = self.parent(refs=[reference()])
        child = self.child(parent, rows=[row(form="10-K/A")])
        result = self.replay(parent, child)
        self.assertEqual(result.status, i.InventoryStatus.INVENTORY_CONFLICT)
        self.assertEqual(result.conflicting_accessions, (row()["accessionNumber"],))
        self.assertEqual(len(result.occurrences), 2)
        self.assertEqual({dict(entry.fields)["form"] for entry in result.occurrences}, {"10-K", "10-K/A"})

    def test_any_changed_field_same_accession_is_conservatively_conflicting(self):
        for changes in ({"size": 1201}, {"filingDate": "2026-02-02"}, {"primaryDocDescription": "changed"}):
            parent = self.parent(rows=[row(), row(**changes)])
            self.assertEqual(self.replay(parent).status, i.InventoryStatus.INVENTORY_CONFLICT)

    def test_identical_duplicates_retain_positions_and_equivalence(self):
        parent = self.parent(rows=[row(), row()], refs=[reference()])
        child = self.child(parent)
        result = self.replay(parent, child)
        self.assertEqual(result.status, i.InventoryStatus.CAPTURED_REFERENCE_CLOSURE_COMPLETE)
        self.assertEqual(len(result.occurrences), 3)
        self.assertEqual(len({entry.semantic_id for entry in result.occurrences}), 1)
        self.assertEqual(len({entry.occurrence_id for entry in result.occurrences}), 3)
        self.assertEqual({entry.section for entry in result.occurrences}, {"filings.recent", "history"})
        self.assertEqual({entry.receipt_id for entry in result.occurrences}, {parent.receipt_id, child.receipt_id})

    def test_row_reference_permutation_preserves_semantics_not_evidence(self):
        left = self.parent(rows=[row(), row(2)], refs=[reference(), reference(NAME2)])
        right = self.parent(rows=[row(2), row()], refs=[reference(NAME2), reference()])
        first, second = self.replay(left), self.replay(right)
        self.assertEqual(first.semantic_id, second.semantic_id)
        self.assertNotEqual(first.evidence_id, second.evidence_id)
        self.assertNotEqual(first.references[0].position, second.references[0].position)
        self.assertEqual(first.occurrences[0].position, 0)

    def test_recapture_changes_evidence_not_semantics_and_preserves_times(self):
        old = self.parent(refs=[reference()])
        new = self.parent(refs=[reference()], captured_at=T2)
        left = self.replay(old, self.child(old))
        right = self.replay(new, self.child(new, captured_at="2026-09-21T12:00:00Z"))
        self.assertEqual(left.semantic_id, right.semantic_id)
        self.assertNotEqual(left.evidence_id, right.evidence_id)
        self.assertEqual(left.parent.captured_at, T1)
        self.assertEqual(left.children[0].captured_at, T2)
        self.assertEqual(right.children[0].captured_at, "2026-09-21T12:00:00Z")

    def test_domain_separated_identities(self):
        result = self.replay(self.parent())
        occurrence = result.occurrences[0]
        values = {result.parent.content_sha256, result.parent.receipt_id, result.semantic_id,
                  result.evidence_id, occurrence.semantic_id, occurrence.occurrence_id}
        self.assertEqual(len(values), 6)
        self.assertTrue(all(len(value) == 64 for value in values))

    def test_all_forms_and_scalar_extensions_preserved(self):
        forms = ("10-K/A", "S-1", "15-12G", "DEF 14A", "4", "UNKNOWN / LABEL")
        rows = [row(n + 1, form=form, unfamiliar=None) for n, form in enumerate(forms)]
        result = self.replay(self.parent(rows=rows, newScalar="source assertion"))
        self.assertEqual([dict(entry.fields) for entry in result.occurrences], rows)
        self.assertIn(b'"newScalar":"source assertion"', result.metadata_json)

    def test_declared_count_is_not_unreviewed_completeness_check(self):
        parent = self.parent(refs=[reference(filingCount=999)])
        result = self.replay(parent, self.child(parent, rows=[row(2)]))
        self.assertEqual(dict(result.references[0].fields)["filingCount"], 999)
        self.assertEqual(result.observed_history_row_counts, ((NAME, 1),))
        self.assertEqual(result.status, i.InventoryStatus.CAPTURED_REFERENCE_CLOSURE_COMPLETE)

    def test_declared_date_range_containment_conflict_not_exact_extrema(self):
        parent = self.parent(refs=[reference(filingFrom="2026-02-02")])
        result = self.replay(parent, self.child(parent, rows=[row(2)]))
        self.assertEqual(result.status, i.InventoryStatus.INVENTORY_CONFLICT)
        self.assertEqual(result.range_conflicts, (NAME,))
        self.assertEqual(len(result.occurrences), 2)
        parent2 = self.parent(refs=[reference(filingTo="2026-02-01")])
        self.assertEqual(self.replay(parent2, self.child(parent2, rows=[row(2)])).status,
                         i.InventoryStatus.CAPTURED_REFERENCE_CLOSURE_COMPLETE)

    def test_optional_reference_assertions_can_be_absent(self):
        parent = self.parent(refs=[{"name": NAME, "newScalar": "retained"}])
        result = self.replay(parent, self.child(parent, rows=[row(2)]))
        self.assertEqual(dict(result.references[0].fields), {"name": NAME, "newScalar": "retained"})

    def test_aggregate_replay_limits(self):
        parent = self.parent(refs=[reference()])
        child = self.child(parent, rows=[row(2)])
        for name, limit in (("MAX_REPLAY_BYTES", parent.byte_length), ("MAX_REPLAY_ROWS", 1), ("MAX_REPLAY_CELLS", len(row()))):
            with patch.object(i, name, limit), self.assertRaises(a.UnsupportedSubmissionsStructure):
                self.replay(parent, child)

    def test_offline_replay_never_writes_networks_or_selects_latest(self):
        parent = self.parent(refs=[reference()])
        child = self.child(parent)
        self.parent(refs=[reference()], captured_at="2026-09-21T12:00:00Z")
        before = {str(path.relative_to(self.archive.root)): path.read_bytes()
                  for path in self.archive.root.rglob("*") if path.is_file()}
        real_open = os.open
        def read_only(path, flags, *args, **kwargs):
            self.assertFalse(flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC))
            return real_open(path, flags, *args, **kwargs)
        with patch.object(os, "open", side_effect=read_only), \
             patch.object(os, "mkdir", side_effect=AssertionError("write forbidden")), \
             patch.object(socket, "create_connection", side_effect=AssertionError("network forbidden")), \
             patch.object(os, "scandir", side_effect=AssertionError("latest search forbidden")):
            result = self.replay(parent, child)
        after = {str(path.relative_to(self.archive.root)): path.read_bytes()
                 for path in self.archive.root.rglob("*") if path.is_file()}
        self.assertEqual(before, after)
        self.assertEqual(result.parent, parent)

    def test_programming_errors_propagate(self):
        parent = self.parent()
        with patch.object(a.SecSubmissionsArchive, "read_object", side_effect=RuntimeError("defect")), \
             self.assertRaises(RuntimeError):
            self.replay(parent)

    def test_no_authority_or_time_injection_in_request_or_assessment(self):
        self.assertEqual(set(i.SecSubmissionsInventoryRequest.__dataclass_fields__), {"parent_receipt_id", "child_receipt_ids"})
        result = self.replay(self.parent())
        for fields in (asdict(result), asdict(result.parent)):
            self.assertTrue({"published_at", "available_at", "as_of", "coverage", "authority", "identity",
                             "admitted", "qualified", "complete_history"}.isdisjoint(fields))
        from economic_facts.current_authority import CurrentAuthorityError
        from economic_facts.sec_current_evidence import assess_sec_current_evidence
        from economic_facts.sec_archive import ArchiveError, SecArchive
        with self.assertRaises(CurrentAuthorityError):
            assess_sec_current_evidence(self.archive, result)
        with self.assertRaises(ArchiveError):
            SecArchive(self.archive.root).read_receipt(result.parent.receipt_id)

    def test_parent_is_decoded_once_for_many_children(self):
        parent = self.parent(refs=[reference(), reference(NAME2)])
        left = self.child(parent, rows=[row(2)])
        right = self.child(parent, name=NAME2, rows=[row(3)])
        with patch.object(i, "_parse_resource", wraps=i._parse_resource) as parse:
            self.replay(parent, left, right)
        self.assertEqual([call.args[2] for call in parse.call_args_list].count("ROOT"), 1)

    def test_tampered_child_chronology_fails_integrity(self):
        parent = self.parent(refs=[reference()])
        child = self.child(parent)
        forged = replace(child, captured_at="2026-09-19T12:00:00Z")
        (self.archive.root / "receipts" / (forged.receipt_id + ".json")).write_bytes(forged.to_bytes())
        with self.assertRaises(a.SubmissionsArchiveError):
            self.replay(parent, forged)

    def test_equal_json_fields_ignore_object_key_order(self):
        parent = self.parent()
        changed = encode(dict(reversed(list(json.loads(root()).items()))))
        other = self.archive._capture_live(changed, cik=CIK, captured_at=T1)
        self.assertEqual(self.replay(parent).semantic_id, self.replay(other).semantic_id)
        self.assertNotEqual(self.replay(parent).evidence_id, self.replay(other).evidence_id)


class SubmissionsDependencyTests(unittest.TestCase):
    def test_closed_one_way_dependencies_and_no_reverse_consumers(self):
        root_dir = Path(__file__).resolve().parents[1]
        new = {"sec_submissions_archive", "sec_submissions_acquisition", "sec_submissions_inventory"}
        allowed = {
            "sec_submissions_archive": set(),
            "sec_submissions_inventory": {"sec_submissions_archive"},
            "sec_submissions_acquisition": {"sec_submissions_archive", "sec_acquisition"},
        }
        stdlib = {"dataclasses", "datetime", "enum", "hashlib", "http", "json", "os", "pathlib",
                  "re", "stat", "time", "urllib"}
        for name in new:
            for node in ast.walk(ast.parse((root_dir / "economic_facts" / (name + ".py")).read_text())):
                if isinstance(node, ast.ImportFrom):
                    if node.level:
                        modules = {node.module} if node.module else {alias.name for alias in node.names}
                        self.assertTrue(modules <= allowed[name], (name, modules))
                    else:
                        self.assertIn(node.module.split('.')[0], stdlib)
                elif isinstance(node, ast.Import):
                    self.assertTrue(all(alias.name.split('.')[0] in stdlib for alias in node.names))
        for directory in ("src", "pit_comparison", "economic_facts", "scripts"):
            for path in (root_dir / directory).rglob("*.py"):
                if path.stem in new | {"sec_property4_temporal_dossier"}:
                    continue
                for node in ast.walk(ast.parse(path.read_text())):
                    if isinstance(node, ast.Import):
                        self.assertFalse(any(set(alias.name.split('.')) & new for alias in node.names), str(path))
                    elif isinstance(node, ast.ImportFrom):
                        self.assertFalse(set((node.module or '').split('.')) & new, str(path))
                        self.assertFalse({alias.name for alias in node.names} & new, str(path))
