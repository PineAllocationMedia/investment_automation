"""PR4D4D1 exact embedded-document inventory; no rights interpretation."""
import ast
from dataclasses import FrozenInstanceError, fields
import hashlib
import inspect
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from economic_facts import sec_filing_document_inventory as inventory
from economic_facts.sec_filing_archive import FilingArchiveError, SecFilingArchive
from economic_facts.sec_primary_document import read_primary_document
from tests.sec_filing_document_inventory_fixtures import embedded_document, filing_inventory
from tests.sec_original_filing_fixtures import ACCESSION, CIK, T1, T2


class SecFilingDocumentInventoryTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve() / "archive"
        self.archive = SecFilingArchive(self.root)

    def capture(self, raw=None, *, root=None, captured_at=T1, cik=CIK, accession=ACCESSION):
        archive = self.archive if root is None else SecFilingArchive(root)
        return archive._capture_live(
            filing_inventory() if raw is None else raw,
            cik=cik,
            accession=accession,
            captured_at=captured_at,
        )

    def replay(self, receipt=None, *, archive=None):
        receipt = self.capture() if receipt is None else receipt
        archive = self.archive if archive is None else archive
        return inventory.replay_sec_filing_document_inventory(
            archive,
            inventory.SecFilingDocumentInventoryRequest(receipt.receipt_id),
        )

    @staticmethod
    def documents(*, form="10-K", primary_description="Primary exact metadata",
                  exhibit_type="EX-4.1", exhibit_description="Opaque exact metadata",
                  exhibit_payload=b"Opaque exhibit bytes"):
        return (
            embedded_document(document_type=form, sequence="1", filename="primary.htm",
                              description=primary_description, payload=b"Primary bytes"),
            embedded_document(document_type=exhibit_type, sequence="2", filename="exhibit.htm",
                              description=exhibit_description, payload=exhibit_payload),
        )

    def test_exact_public_api_and_closed_request(self):
        self.assertEqual(set(inspect.signature(
            inventory.replay_sec_filing_document_inventory).parameters), {"archive", "request"})
        self.assertEqual([field.name for field in fields(
            inventory.SecFilingDocumentInventoryRequest)], ["filing_receipt_id"])
        receipt = self.capture()
        for keyword in ("cik", "accession", "form", "document_type", "sequence", "filename",
                        "description", "rights", "security_id", "listing_id", "as_of", "raw",
                        "url", "clock", "qualified"):
            with self.subTest(keyword=keyword), self.assertRaises(TypeError):
                inventory.SecFilingDocumentInventoryRequest(
                    receipt.receipt_id, **{keyword: "caller assertion"})

    def test_malformed_selector_and_exact_types_rejected(self):
        for value in (None, 0, True, "", "0" * 63, "0" * 65, "A" * 64, "../" + "0" * 64,
                      "٠" * 64, "0" * 64 + " "):
            with self.subTest(value=value), self.assertRaises(
                    inventory.SecFilingDocumentInventoryRequestError):
                inventory.SecFilingDocumentInventoryRequest(value)
        receipt = self.capture()
        request = inventory.SecFilingDocumentInventoryRequest(receipt.receipt_id)
        for archive, selected in ((object(), request), (self.archive, object())):
            with self.assertRaises(inventory.SecFilingDocumentInventoryRequestError):
                inventory.replay_sec_filing_document_inventory(archive, selected)

    def test_explicit_membership_required_and_no_latest_selection(self):
        receipt = self.capture()
        other = SecFilingArchive(self.root.parent / "other")
        with self.assertRaises(FilingArchiveError):
            inventory.replay_sec_filing_document_inventory(
                other, inventory.SecFilingDocumentInventoryRequest(receipt.receipt_id))
        self.assertEqual({name for name in vars(SecFilingArchive) if not name.startswith("_")},
                         {"read_receipt", "read_object"})

    def test_exact_inventory_fields_status_and_source_order(self):
        assessment = self.replay()
        self.assertEqual(assessment.status,
                         inventory.SecFilingDocumentInventoryStatus.CAPTURED_FILING_DOCUMENT_INVENTORY)
        self.assertEqual((assessment.cik, assessment.accession, assessment.form),
                         (CIK, ACCESSION, "10-K"))
        self.assertEqual(tuple(document.document_ordinal for document in assessment.documents),
                         (0, 1, 2))
        self.assertEqual(tuple(document.document_type for document in assessment.documents),
                         ("10-K", "EX-4.B", "EX-10"))
        self.assertEqual(tuple(document.sequence for document in assessment.documents),
                         ("1", "2", "3"))
        self.assertEqual(tuple(document.filename for document in assessment.documents),
                         ("fictional.htm", "fictional-ex4b.htm", "fictional-ex10.txt"))
        self.assertEqual(tuple(document.description for document in assessment.documents),
                         ("Fictional annual filing",
                          "DESCRIPTION OF REGISTRANT'S SECURITIES", None))

    def test_exact_payload_offsets_lengths_and_hashes(self):
        raw = filing_inventory()
        receipt = self.capture(raw)
        assessment = self.replay(receipt)
        expected = (
            b"<html>Primary fictional filing</html>",
            b"<html>Opaque fictional exhibit <a href='prior.htm'>reference</a></html>",
            b"Opaque fictional contract bytes: \xff\x00",
        )
        for document, payload in zip(assessment.documents, expected):
            with self.subTest(document=document.filename):
                self.assertEqual(raw[document.byte_start:
                                     document.byte_start + document.byte_length], payload)
                self.assertEqual(document.byte_length, len(payload))
                self.assertEqual(document.content_sha256, hashlib.sha256(payload).hexdigest())

    def test_primary_document_provenance_equivalence_and_identity_unchanged(self):
        raw = filing_inventory()
        receipt = self.capture(raw)
        primary, payload = read_primary_document(
            raw, receipt, supported_forms=inventory.SUPPORTED_FORMS)
        prior_identity = primary.evidence_id
        document = self.replay(receipt).documents[0]
        self.assertEqual(
            (document.filing_receipt_id, document.cik, document.accession,
             document.filing_form, document.document_ordinal, document.sequence,
             document.filename, document.byte_start, document.byte_length,
             document.content_sha256),
            (primary.receipt_id, primary.cik, primary.accession, primary.form,
             primary.document_ordinal, primary.sequence, primary.filename,
             primary.byte_start, primary.byte_length, primary.content_sha256),
        )
        self.assertEqual(payload, raw[document.byte_start:document.byte_start + document.byte_length])
        self.assertEqual(primary.evidence_id, prior_identity)

    def test_all_and_only_d2a_supported_forms(self):
        for form in ("10-K", "10-K/A", "10-Q", "10-Q/A", "8-K"):
            with self.subTest(form=form):
                raw = filing_inventory(form=form, documents=self.documents(form=form))
                receipt = self.capture(raw, captured_at=T1)
                self.assertEqual(self.replay(receipt).form, form)
                self.root = self.root.parent / ("archive-" + form.replace("/", "-"))
                self.archive = SecFilingArchive(self.root)
        for form in ("8-K/A", "20-F", "6-K"):
            with self.subTest(form=form):
                raw = filing_inventory(form=form, documents=self.documents(form=form))
                receipt = self.capture(raw)
                with self.assertRaises(inventory.UnsupportedSecFilingDocumentInventorySource):
                    self.replay(receipt)
                self.root = self.root.parent / ("unsupported-" + form.replace("/", "-"))
                self.archive = SecFilingArchive(self.root)

    def test_three_field_and_four_field_metadata_description_semantics(self):
        documents = (
            embedded_document(document_type="10-K", sequence="1", filename="primary.htm",
                              description=None, payload=b"Primary"),
            embedded_document(document_type="EX-4.H", sequence="2", filename="rights.htm",
                              description="  Punctuation: A/B; (Exact)!  ", payload=b"Opaque"),
            embedded_document(document_type="EX-10", sequence="3", filename="contract.htm",
                              description="", payload=b"Also opaque"),
        )
        result = self.replay(self.capture(filing_inventory(documents=documents)))
        self.assertEqual(tuple(document.description for document in result.documents),
                         (None, "  Punctuation: A/B; (Exact)!  ", ""))
        self.assertEqual(result.documents[1].document_type, "EX-4.H")
        self.assertEqual(result.documents[1].filename, "rights.htm")

    def test_description_bound_and_malformed_metadata_rejected(self):
        for description in ("x" * 4097, "bad\vmetadata"):
            documents = self.documents(exhibit_description=description)
            receipt = self.capture(filing_inventory(documents=documents))
            with self.subTest(description=description[:20]), self.assertRaises(
                    inventory.UnsupportedSecFilingDocumentInventorySource):
                self.replay(receipt)
            self.root = self.root.parent / ("next-" + str(len(description)))
            self.archive = SecFilingArchive(self.root)

        for index, (old, new) in enumerate((
            (b"<TYPE>EX-4.1", b"<TYPE> EX-4.1"),
            (b"<SEQUENCE>2", b"<SEQUENCE>2 "),
            (b"<FILENAME>exhibit.htm", b"<FILENAME> exhibit.htm"),
        )):
            self.root = self.root.parent / ("exact-metadata-" + str(index))
            self.archive = SecFilingArchive(self.root)
            raw = filing_inventory(documents=self.documents()).replace(old, new)
            receipt = self.capture(raw)
            with self.subTest(field=old), self.assertRaises(
                    inventory.UnsupportedSecFilingDocumentInventorySource):
                self.replay(receipt)

    def test_type_description_and_payload_create_no_classification(self):
        assessment = self.replay()
        forbidden = {"is_rights_exhibit", "is_security_description", "security_id", "class_id",
                     "listing_id", "issuer_id", "rights", "instrument_type", "common_stock",
                     "preferred_stock", "debt", "wrapper", "ticker", "exchange", "currency",
                     "qualified"}
        self.assertTrue(forbidden.isdisjoint(
            {field.name for field in fields(inventory.SecFilingDocumentProvenance)}))
        self.assertEqual(assessment.documents[1].document_type, "EX-4.B")
        self.assertEqual(assessment.documents[2].document_type, "EX-10")
        self.assertEqual(assessment.status.value, "CAPTURED_FILING_DOCUMENT_INVENTORY")

    def test_payload_binary_html_links_and_reference_text_remain_opaque(self):
        payload = (b"\xff\x00<a href='https://www.sec.gov/Archives/prior.txt'>"
                   b"incorporated by reference; voting dividend liquidation rights</a>")
        raw = filing_inventory(documents=self.documents(exhibit_payload=payload))
        receipt = self.capture(raw)
        with patch("urllib.request.urlopen", side_effect=AssertionError("network forbidden")):
            assessment = self.replay(receipt)
        exhibit = assessment.documents[1]
        self.assertEqual(raw[exhibit.byte_start:exhibit.byte_start + exhibit.byte_length], payload)

    def test_receipt_and_source_object_corruption_propagate(self):
        receipt = self.capture()
        receipt_path = self.root / "receipts" / (receipt.receipt_id + ".json")
        receipt_path.chmod(0o600)
        receipt_path.write_bytes(receipt.to_bytes()[:-1])
        with self.assertRaises(FilingArchiveError):
            self.replay(receipt)

        self.root = self.root.parent / "object-corruption"
        self.archive = SecFilingArchive(self.root)
        receipt = self.capture()
        object_path = self.root / "objects" / receipt.content_sha256
        for raw in (filing_inventory()[:-1], filing_inventory() + b"x",
                    b"x" * len(filing_inventory())):
            object_path.chmod(0o600)
            object_path.write_bytes(raw)
            with self.subTest(length=len(raw)), self.assertRaises(FilingArchiveError):
                self.replay(receipt)

    def test_cik_accession_and_form_mismatches_rejected(self):
        cases = (
            (filing_inventory(cik="0000000002"), dict(cik=CIK, accession=ACCESSION)),
            (filing_inventory(accession="0000000002-26-000002"),
             dict(cik=CIK, accession=ACCESSION)),
            (filing_inventory().replace(b"FORM TYPE:\t\t10-K", b"FORM TYPE:\t\t10-Q"),
             dict(cik=CIK, accession=ACCESSION)),
        )
        for index, (raw, selectors) in enumerate(cases):
            self.root = self.root.parent / ("mismatch-" + str(index))
            self.archive = SecFilingArchive(self.root)
            receipt = self.capture(raw, **selectors)
            with self.subTest(index=index), self.assertRaises(
                    inventory.UnsupportedSecFilingDocumentInventorySource):
                self.replay(receipt)

    def test_declared_count_and_unbalanced_envelopes_rejected(self):
        raw = filing_inventory()
        cases = (
            raw.replace(b"PUBLIC DOCUMENT COUNT:\t\t3", b"PUBLIC DOCUMENT COUNT:\t\t2"),
            raw.replace(b"</DOCUMENT>\n", b"", 1),
            raw.replace(b"</TEXT>\n", b"", 1),
            raw.replace(b"<TEXT>\n", b"", 1),
            raw + b"<DOCUMENT>\n",
        )
        for index, source in enumerate(cases):
            self.root = self.root.parent / ("envelope-" + str(index))
            self.archive = SecFilingArchive(self.root)
            receipt = self.capture(source)
            with self.subTest(index=index), self.assertRaises(
                    inventory.UnsupportedSecFilingDocumentInventorySource):
                self.replay(receipt)

    def test_reserved_delimiters_and_empty_payload_rejected(self):
        for index, payload in enumerate((b"", b" \t", b"before\n<DOCUMENT>\nafter",
                                         b"before\n</TEXT>forged\nafter",
                                         b"<SEC-HEADER>forged")):
            documents = self.documents(exhibit_payload=payload)
            self.root = self.root.parent / ("payload-" + str(index))
            self.archive = SecFilingArchive(self.root)
            receipt = self.capture(filing_inventory(documents=documents))
            with self.subTest(payload=payload), self.assertRaises(
                    inventory.UnsupportedSecFilingDocumentInventorySource):
                self.replay(receipt)

    def test_duplicate_sequence_filename_invalid_sequence_and_unsafe_filename_rejected(self):
        bad_exhibits = (
            embedded_document(document_type="EX-4", sequence="1", filename="exhibit.htm",
                              payload=b"Opaque"),
            embedded_document(document_type="EX-4", sequence="2", filename="primary.htm",
                              payload=b"Opaque"),
            embedded_document(document_type="EX-4", sequence="0", filename="exhibit.htm",
                              payload=b"Opaque"),
            embedded_document(document_type="EX-4", sequence="2", filename="../exhibit.htm",
                              payload=b"Opaque"),
        )
        primary = self.documents()[0]
        for index, exhibit in enumerate(bad_exhibits):
            self.root = self.root.parent / ("identity-" + str(index))
            self.archive = SecFilingArchive(self.root)
            receipt = self.capture(filing_inventory(documents=(primary, exhibit)))
            with self.subTest(index=index), self.assertRaises(
                    inventory.UnsupportedSecFilingDocumentInventorySource):
                self.replay(receipt)

    def test_primary_form_rules_rejected(self):
        cases = (
            self.documents(form="10-Q"),
            (self.documents()[0], embedded_document(document_type="10-K", sequence="2",
                                                    filename="second.htm", payload=b"Second primary")),
        )
        for index, documents in enumerate(cases):
            self.root = self.root.parent / ("primary-" + str(index))
            self.archive = SecFilingArchive(self.root)
            receipt = self.capture(filing_inventory(form="10-K", documents=documents))
            with self.subTest(index=index), self.assertRaises(
                    inventory.UnsupportedSecFilingDocumentInventorySource):
                self.replay(receipt)

    def test_frozen_slotted_records_and_exact_fields(self):
        assessment = self.replay()
        expected_document_fields = {
            "filing_receipt_id", "cik", "accession", "filing_form", "document_ordinal",
            "document_type", "sequence", "filename", "description", "byte_start",
            "byte_length", "content_sha256",
        }
        self.assertEqual(set(inventory.SecFilingDocumentProvenance.__dataclass_fields__),
                         expected_document_fields)
        self.assertEqual(set(inventory.SecFilingDocumentInventoryAssessment.__dataclass_fields__),
                         {"contract_version", "receipt", "cik", "accession", "form",
                          "documents", "status"})
        for value in (assessment, assessment.documents[0],
                      inventory.SecFilingDocumentInventoryRequest(assessment.receipt.receipt_id)):
            with self.assertRaises((FrozenInstanceError, TypeError)):
                value.extra = True
            self.assertFalse(hasattr(value, "__dict__"))

    def test_deterministic_document_and_inventory_identities(self):
        first = self.replay()
        second = self.replay(first.receipt)
        self.assertEqual(first.semantic_id, second.semantic_id)
        self.assertEqual(first.evidence_id, second.evidence_id)
        self.assertEqual(tuple(document.semantic_id for document in first.documents),
                         tuple(document.semantic_id for document in second.documents))
        self.assertEqual(tuple(document.evidence_id for document in first.documents),
                         tuple(document.evidence_id for document in second.documents))
        self.assertNotEqual(first.semantic_id, first.evidence_id)
        self.assertTrue(all(document.semantic_id != document.evidence_id
                            for document in first.documents))

    def test_identical_recapture_preserves_semantics_and_changes_evidence(self):
        raw = filing_inventory()
        first = self.replay(self.capture(raw, captured_at=T1))
        second = self.replay(self.capture(raw, captured_at=T2))
        self.assertEqual(first.semantic_id, second.semantic_id)
        self.assertNotEqual(first.evidence_id, second.evidence_id)
        self.assertEqual(tuple(document.semantic_id for document in first.documents),
                         tuple(document.semantic_id for document in second.documents))
        self.assertNotEqual(tuple(document.evidence_id for document in first.documents),
                            tuple(document.evidence_id for document in second.documents))

    def test_changed_payload_or_metadata_changes_semantics(self):
        base = self.replay()
        variants = (
            filing_inventory(documents=self.documents(exhibit_payload=b"Changed bytes")),
            filing_inventory(documents=self.documents(exhibit_description="Changed metadata")),
            filing_inventory(documents=self.documents(exhibit_type="EX-4.B")),
        )
        for index, raw in enumerate(variants):
            self.root = self.root.parent / ("semantic-" + str(index))
            self.archive = SecFilingArchive(self.root)
            changed = self.replay(self.capture(raw))
            with self.subTest(index=index):
                self.assertNotEqual(base.semantic_id, changed.semantic_id)
                self.assertNotEqual(base.documents[1].semantic_id,
                                    changed.documents[1].semantic_id)

    def test_path_and_line_endings_do_not_change_document_semantics(self):
        raw_lf = filing_inventory()
        raw_crlf = filing_inventory(newline=b"\r\n", documents=(
            embedded_document(document_type="10-K", sequence="1", filename="fictional.htm",
                              description="Fictional annual filing",
                              payload=b"<html>Primary fictional filing</html>", newline=b"\r\n"),
            embedded_document(document_type="EX-4.B", sequence="2", filename="fictional-ex4b.htm",
                              description="DESCRIPTION OF REGISTRANT'S SECURITIES",
                              payload=b"<html>Opaque fictional exhibit <a href='prior.htm'>reference</a></html>",
                              newline=b"\r\n"),
            embedded_document(document_type="EX-10", sequence="3", filename="fictional-ex10.txt",
                              description=None, payload=b"Opaque fictional contract bytes: \xff\x00",
                              newline=b"\r\n"),
        ))
        first = self.replay(self.capture(raw_lf))
        other_root = self.root.parent / "other-path"
        other_archive = SecFilingArchive(other_root)
        other_receipt = self.capture(raw_lf, root=other_root)
        same_path_independent = self.replay(other_receipt, archive=other_archive)
        self.assertEqual(first.semantic_id, same_path_independent.semantic_id)
        self.assertEqual(first.evidence_id, same_path_independent.evidence_id)

        crlf_root = self.root.parent / "crlf"
        crlf_archive = SecFilingArchive(crlf_root)
        crlf_receipt = self.capture(raw_crlf, root=crlf_root)
        crlf = self.replay(crlf_receipt, archive=crlf_archive)
        self.assertEqual(tuple(document.semantic_id for document in first.documents),
                         tuple(document.semantic_id for document in crlf.documents))
        self.assertNotEqual(tuple(document.byte_start for document in first.documents),
                            tuple(document.byte_start for document in crlf.documents))
        self.assertNotEqual(first.evidence_id, crlf.evidence_id)

    def test_replay_has_no_network_writes_clock_or_directory_scan(self):
        receipt = self.capture()
        before = {path.relative_to(self.root): path.read_bytes()
                  for path in self.root.rglob("*") if path.is_file()}
        with patch("urllib.request.urlopen", side_effect=AssertionError("network forbidden")), \
             patch("os.listdir", side_effect=AssertionError("directory scan forbidden")), \
             patch("os.scandir", side_effect=AssertionError("directory scan forbidden")), \
             patch("time.time", side_effect=AssertionError("clock forbidden")), \
             patch("time.monotonic", side_effect=AssertionError("clock forbidden")):
            assessment = self.replay(receipt)
        after = {path.relative_to(self.root): path.read_bytes()
                 for path in self.root.rglob("*") if path.is_file()}
        self.assertEqual(before, after)
        self.assertEqual(assessment.receipt, receipt)


class SecFilingDocumentInventoryDependencyTests(unittest.TestCase):
    def test_exact_dependency_direction_and_no_reverse_consumers(self):
        root = Path(__file__).resolve().parents[1]
        module = root / "economic_facts" / "sec_filing_document_inventory.py"
        tree = ast.parse(module.read_text())
        allowed_standard = {"dataclasses", "enum", "re"}
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                self.assertTrue(all(alias.name in allowed_standard for alias in node.names))
            if isinstance(node, ast.ImportFrom):
                self.assertTrue((node.level == 1 and node.module == "sec_filing_archive")
                                or (node.level == 0 and node.module in allowed_standard))
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                self.assertNotIn(node.func.id, {"float", "eval", "exec", "open", "__import__"})
        for file in (root / "economic_facts").glob("*.py"):
            if file in {module,
                        root / "economic_facts/sec_direct_section12_description_source.py",
                        root / "economic_facts/sec_section12_rights_source_claims.py"}:
                continue
            self.assertNotIn("sec_filing_document_inventory", file.read_text(), str(file))

    def test_no_authority_identity_model_or_runtime_surface(self):
        source = (Path(__file__).resolve().parents[1]
                  / "economic_facts" / "sec_filing_document_inventory.py").read_text()
        tree = ast.parse(source)
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imported.add(node.module or "")
        for forbidden in ("source_authority", "security_identity", "sec_current_registered_listing_bridge",
                          "expected_return", "src", "pit_comparison", "runtime"):
            self.assertFalse(any(name == forbidden or name.startswith(forbidden + ".")
                                 for name in imported))


if __name__ == "__main__":
    unittest.main()
