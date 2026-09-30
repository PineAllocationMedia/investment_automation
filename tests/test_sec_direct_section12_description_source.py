"""PR4D4D2A narrow direct Section-12 description-source identification."""
import ast
from dataclasses import FrozenInstanceError, fields
import inspect
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from economic_facts import sec_direct_section12_description_source as source
from economic_facts.sec_filing_archive import SecFilingArchive
from tests.sec_direct_section12_description_fixtures import (
    HEADING,
    HEADING_WITH_THE,
    SECTION12,
    SECTION12_B,
    description_html,
    description_text,
    source_filing,
)
from tests.sec_original_filing_fixtures import ACCESSION, CIK, T1, T2


class SecDirectSection12DescriptionSourceTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve() / "archive"
        self.archive = SecFilingArchive(self.root)

    def capture(self, raw=None, *, archive=None, captured_at=T1):
        archive = self.archive if archive is None else archive
        return archive._capture_live(
            source_filing() if raw is None else raw,
            cik=CIK,
            accession=ACCESSION,
            captured_at=captured_at,
        )

    def identify(self, receipt=None, *, archive=None):
        archive = self.archive if archive is None else archive
        receipt = self.capture(archive=archive) if receipt is None else receipt
        request = source.SecDirectSection12DescriptionRequest(receipt.receipt_id)
        return source.identify_sec_direct_section12_description_sources(archive, request)

    @staticmethod
    def item(document_type="EX-4.1", payload=None, *, sequence="2",
             filename="rights.htm", description="Opaque metadata"):
        return (document_type, sequence, filename, description,
                description_html() if payload is None else payload)

    def result_for(self, *items, form="10-K"):
        raw = source_filing(form=form, sources=items)
        return self.identify(self.capture(raw))

    def test_exact_public_api_closed_request_and_typed_arguments(self):
        self.assertEqual(set(inspect.signature(
            source.identify_sec_direct_section12_description_sources).parameters),
            {"archive", "request"})
        self.assertEqual([field.name for field in fields(
            source.SecDirectSection12DescriptionRequest)], ["filing_receipt_id"])
        receipt = self.capture()
        for keyword in ("inventory", "cik", "accession", "form", "document_type",
                        "sequence", "filename", "description", "class_name", "ticker",
                        "security_id", "rights", "as_of", "raw", "url", "clock",
                        "candidate", "qualified"):
            with self.subTest(keyword=keyword), self.assertRaises(TypeError):
                source.SecDirectSection12DescriptionRequest(
                    receipt.receipt_id, **{keyword: "caller assertion"})
        request = source.SecDirectSection12DescriptionRequest(receipt.receipt_id)
        for archive, selected in ((object(), request), (self.archive, object())):
            with self.assertRaises(source.SecDirectSection12DescriptionRequestError):
                source.identify_sec_direct_section12_description_sources(archive, selected)

    def test_malformed_receipt_selector_rejected(self):
        for value in (None, 0, True, "", "0" * 63, "0" * 65, "A" * 64,
                      "../" + "0" * 64, "٠" * 64, "0" * 64 + " "):
            with self.subTest(value=value), self.assertRaises(
                    source.SecDirectSection12DescriptionRequestError):
                source.SecDirectSection12DescriptionRequest(value)

    def test_inventory_is_freshly_replayed_and_cannot_be_supplied(self):
        receipt = self.capture()
        real = source.replay_sec_filing_document_inventory
        with patch.object(source, "replay_sec_filing_document_inventory", wraps=real) as replay:
            result = self.identify(receipt)
        replay.assert_called_once()
        self.assertEqual(replay.call_args.args[1].filing_receipt_id, receipt.receipt_id)
        self.assertEqual(result.inventory.receipt, receipt)

    def test_only_annual_forms_are_supported_positively(self):
        for index, form in enumerate(("10-K", "10-K/A")):
            with self.subTest(form=form):
                result = self.result_for(self.item(), form=form)
                self.assertEqual(result.status,
                                 source.SecDirectSection12DescriptionStatus.CAPTURED_DIRECT_SECTION12_DESCRIPTION_SOURCES)
                self.assertEqual(result.filing_form, form)
                self.root = self.root.parent / f"annual-{index}"
                self.archive = SecFilingArchive(self.root)
        for index, form in enumerate(("10-Q", "10-Q/A", "8-K")):
            with self.subTest(form=form):
                result = self.result_for(self.item(), form=form)
                self.assertEqual(result.status,
                                 source.SecDirectSection12DescriptionStatus.UNSUPPORTED_FILING_FORM)
                self.assertEqual(result.candidates, ())
                self.assertEqual(result.issues,
                                 (source.SecDirectSection12DescriptionIssue.UNSUPPORTED_FILING_FORM,))
                self.root = self.root.parent / f"other-{index}"
                self.archive = SecFilingArchive(self.root)

    def test_exact_reviewed_ex4_family_is_structurally_eligible(self):
        items = tuple(self.item(kind, sequence=str(index + 2),
                                filename=f"rights-{index}.htm")
                      for index, kind in enumerate(("EX-4", "EX-4.1", "EX-4.B", "EX-4.H",
                                                   "EX-4.A-1", "EX-4.123")))
        result = self.result_for(*items)
        self.assertEqual(tuple(candidate.document_type for candidate in result.candidates),
                         tuple(item[0] for item in items))

    def test_near_match_and_malformed_types_are_not_considered(self):
        kinds = ("EX-40", "EX-4.", "EX-4..1", "EX-4.A.B", "EX-4_1", "EX-4/1",
                 "EX-4.A_1", "EX-4." + "A" * 17, "EX-10")
        for index, kind in enumerate(kinds):
            with self.subTest(kind=kind):
                result = self.result_for(self.item(kind))
                self.assertEqual(result.status,
                                 source.SecDirectSection12DescriptionStatus.NO_DIRECT_SUPPORTED_DESCRIPTION_SOURCE)
                self.assertEqual(result.candidates, ())
                self.root = self.root.parent / f"type-{index}"
                self.archive = SecFilingArchive(self.root)

    def test_both_exact_content_concepts_are_mandatory(self):
        cases = (
            (description_html(section12="Ordinary legal text"), False),
            (description_html(heading="Ordinary exhibit"), False),
            (description_html(), True),
            (description_html(heading=HEADING_WITH_THE, section12=SECTION12_B), True),
        )
        for index, (payload, positive) in enumerate(cases):
            result = self.result_for(self.item(payload=payload))
            with self.subTest(index=index):
                self.assertEqual(bool(result.candidates), positive)
            self.root = self.root.parent / f"anchor-{index}"
            self.archive = SecFilingArchive(self.root)

    def test_description_filename_sequence_and_ordinal_cannot_qualify(self):
        result = self.result_for(self.item(
            payload=b"Ordinary text only",
            sequence="12",
            filename="description-of-registrants-securities.htm",
            description=HEADING + " " + SECTION12,
        ))
        self.assertEqual(result.status,
                         source.SecDirectSection12DescriptionStatus.NO_DIRECT_SUPPORTED_DESCRIPTION_SOURCE)
        self.assertEqual(result.candidates, ())

    def test_unrelated_metadata_does_not_block_content_positive(self):
        result = self.result_for(self.item(
            filename="unrelated.bin", description="UNRELATED EXACT METADATA"))
        candidate = result.candidates[0]
        self.assertEqual(candidate.filename, "unrelated.bin")
        self.assertEqual(candidate.description, "UNRELATED EXACT METADATA")

    def test_case_and_layout_whitespace_normalization_only(self):
        payload = (
            "<html><body><h1>Description   of\nRegistrant's Securities</h1>"
            "<p>Registered\tPursuant to Section 12 of the Securities\r\n"
            "Exchange Act of 1934</p></body></html>"
        ).encode()
        result = self.result_for(self.item(payload=payload))
        self.assertEqual(len(result.candidates), 1)

    def test_html_entities_are_decoded_deterministically(self):
        payload = (
            "<html><body><h1>DESCRIPTION OF REGISTRANT&#39;S SECURITIES</h1>"
            "<p>REGISTERED PURSUANT TO SECTION 12 OF THE SECURITIES "
            "EXCHANGE ACT OF 19&#51;4</p></body></html>"
        ).encode()
        result = self.result_for(self.item(payload=payload))
        self.assertEqual(len(result.candidates), 1)

    def test_reviewed_curly_apostrophe_heading_variants_are_explicit(self):
        for index, heading in enumerate(("DESCRIPTION OF REGISTRANT’S SECURITIES",
                                         "DESCRIPTION OF THE REGISTRANT’S SECURITIES")):
            result = self.result_for(self.item(payload=description_html(heading=heading)))
            with self.subTest(heading=heading):
                self.assertEqual(len(result.candidates), 1)
                self.assertIn("CURLY_APOSTROPHE",
                              result.candidates[0].matched_heading_anchors[0].value)
            self.root = self.root.parent / f"curly-{index}"
            self.archive = SecFilingArchive(self.root)

    def test_punctuation_misspelling_and_synonym_near_matches_fail(self):
        payloads = (
            description_html(heading="DESCRIPTION OF REGISTRANT, SECURITIES"),
            description_html(section12="REGISTERED PURSUANT TO SECTON 12 OF THE SECURITIES EXCHANGE ACT OF 1934"),
            description_html(heading="OVERVIEW OF REGISTRANT'S SECURITIES"),
            description_html(section12="REGISTERED PURSUANT TO SECTION 12 OF THE SECURITIES EXCHANGE ACT, OF 1934"),
        )
        for index, payload in enumerate(payloads):
            result = self.result_for(self.item(payload=payload))
            with self.subTest(index=index):
                self.assertEqual(result.candidates, ())
            self.root = self.root.parent / f"near-{index}"
            self.archive = SecFilingArchive(self.root)

    def test_script_style_noscript_template_head_and_svg_cannot_create_anchors(self):
        excluded = "".join(
            f"<{tag}>{HEADING} {SECTION12}</{tag}>"
            for tag in ("script", "style", "noscript", "template", "svg"))
        payload = (
            f"<html><head><title>{HEADING} {SECTION12}</title></head>"
            f"<body>{excluded}<p>Ordinary visible text</p></body></html>"
        ).encode()
        result = self.result_for(self.item(payload=payload))
        self.assertEqual(result.status,
                         source.SecDirectSection12DescriptionStatus.NO_DIRECT_SUPPORTED_DESCRIPTION_SOURCE)

    def test_utf8_html_xhtml_and_plain_text_are_supported(self):
        items = (
            self.item("EX-4", description_html(), sequence="2", filename="a.htm"),
            self.item("EX-4.B", description_html(xhtml=True), sequence="3", filename="b.xhtml"),
            self.item("EX-4.H", description_text(), sequence="4", filename="c.txt"),
        )
        result = self.result_for(*items)
        self.assertEqual(tuple(candidate.representation for candidate in result.candidates), (
            source.SecDocumentRepresentation.UTF8_HTML,
            source.SecDocumentRepresentation.UTF8_XHTML,
            source.SecDocumentRepresentation.UTF8_TEXT,
        ))

    def test_unsupported_encoding_binary_pdf_word_and_rtf_are_explicit(self):
        payloads = (
            b"\xff\xfe" + HEADING.encode("utf-16le"),
            b"%PDF-1.7\n" + HEADING.encode() + b" " + SECTION12.encode(),
            b"PK\x03\x04" + HEADING.encode(),
            b"\xd0\xcf\x11\xe0" + HEADING.encode(),
            b"{\\rtf1 " + HEADING.encode() + b" " + SECTION12.encode() + b"}",
            b"text\x00" + HEADING.encode() + b" " + SECTION12.encode(),
        )
        for index, payload in enumerate(payloads):
            result = self.result_for(self.item(payload=payload))
            with self.subTest(index=index):
                self.assertEqual(result.status,
                                 source.SecDirectSection12DescriptionStatus.UNSUPPORTED_DOCUMENT_REPRESENTATION)
                self.assertEqual(result.candidates, ())
            self.root = self.root.parent / f"representation-{index}"
            self.archive = SecFilingArchive(self.root)

    def test_binary_non_ex4_document_is_not_inspected(self):
        result = self.result_for(self.item("EX-10", b"%PDF-1.7\x00"))
        self.assertEqual(result.status,
                         source.SecDirectSection12DescriptionStatus.NO_DIRECT_SUPPORTED_DESCRIPTION_SOURCE)
        self.assertEqual(result.issues, ())

    def test_malformed_or_ambiguous_html_fails_closed(self):
        payloads = (
            b"<html><body><p>unclosed</body></html>",
            b"<html><body><p>misnested</body></p></html>",
            b"<html><body>missing root close</body>",
            b"<document><body>wrong root</body></document>",
            b"<!DOCTYPE svg><html><body>wrong declaration</body></html>",
            b"<html><body id='a' id='b'>duplicate attribute</body></html>",
            (HEADING + " < ambiguous > " + SECTION12).encode(),
        )
        for index, payload in enumerate(payloads):
            result = self.result_for(self.item(payload=payload))
            with self.subTest(index=index):
                self.assertEqual(result.status,
                                 source.SecDirectSection12DescriptionStatus.SOURCE_AMBIGUITY)
                self.assertEqual(result.candidates, ())
            self.root = self.root.parent / f"malformed-{index}"
            self.archive = SecFilingArchive(self.root)

    def test_source_ambiguity_precedes_unsupported_representation(self):
        result = self.result_for(
            self.item("EX-4", b"<html><body>broken</html>", sequence="2", filename="a.htm"),
            self.item("EX-4.B", b"%PDF-1.7", sequence="3", filename="b.pdf"),
        )
        self.assertEqual(result.status, source.SecDirectSection12DescriptionStatus.SOURCE_AMBIGUITY)
        self.assertEqual(set(result.issues), {
            source.SecDirectSection12DescriptionIssue.MALFORMED_OR_AMBIGUOUS_DOCUMENT,
            source.SecDirectSection12DescriptionIssue.UNSUPPORTED_DOCUMENT_REPRESENTATION,
        })

    def test_positive_does_not_hide_uninspectable_eligible_document(self):
        result = self.result_for(
            self.item("EX-4", description_html(), sequence="2", filename="a.htm"),
            self.item("EX-4.B", b"%PDF-1.7", sequence="3", filename="b.pdf"),
        )
        self.assertEqual(len(result.candidates), 1)
        self.assertEqual(result.status,
                         source.SecDirectSection12DescriptionStatus.UNSUPPORTED_DOCUMENT_REPRESENTATION)

    def test_multiple_positive_candidates_are_all_preserved_without_winner(self):
        result = self.result_for(
            self.item("EX-4.H", description_html(heading=HEADING_WITH_THE),
                      sequence="9", filename="z.htm"),
            self.item("EX-4", description_text(), sequence="2", filename="a.txt"),
            self.item("EX-4.B", description_html(section12=SECTION12_B),
                      sequence="7", filename="m.htm"),
        )
        self.assertEqual(tuple(candidate.document_type for candidate in result.candidates),
                         ("EX-4.H", "EX-4", "EX-4.B"))
        self.assertEqual(tuple(candidate.sequence for candidate in result.candidates),
                         ("9", "2", "7"))

    def test_candidate_provenance_and_exact_anchor_identifiers(self):
        result = self.result_for(self.item(
            payload=description_html(heading=HEADING_WITH_THE, section12=SECTION12_B)))
        candidate = result.candidates[0]
        document = result.inventory.documents[1]
        self.assertEqual((candidate.filing_receipt_id, candidate.cik, candidate.accession,
                          candidate.filing_form),
                         (result.inventory.receipt.receipt_id, CIK, ACCESSION, "10-K"))
        self.assertEqual((candidate.document_semantic_id, candidate.document_evidence_id,
                          candidate.payload_sha256, candidate.payload_byte_start,
                          candidate.payload_byte_length),
                         (document.semantic_id, document.evidence_id, document.content_sha256,
                          document.byte_start, document.byte_length))
        self.assertEqual(candidate.matched_heading_anchors, (
            source.HeadingAnchor.DESCRIPTION_OF_THE_REGISTRANTS_SECURITIES,))
        self.assertEqual(candidate.matched_section12_anchors, (
            source.Section12Anchor.REGISTERED_PURSUANT_TO_SECTION_12_B,))

    def test_frozen_slotted_records_and_no_rights_or_identity_fields(self):
        result = self.identify()
        records = (source.SecDirectSection12DescriptionRequest,
                   source.SecDirectSection12DescriptionSource,
                   source.SecDirectSection12DescriptionAssessment)
        forbidden = {
            "issuer_id", "security_id", "class_id", "listing_id", "pam_security_id",
            "rights", "voting_rights", "dividend_rights", "liquidation_rights",
            "conversion_rights", "redemption_rights", "preemption_rights",
            "common_stock", "preferred_stock", "registered_class", "qualified", "admitted",
        }
        for record in records:
            self.assertFalse(forbidden & set(record.__dataclass_fields__))
        for value in (result, result.candidates[0],
                      source.SecDirectSection12DescriptionRequest(result.inventory.receipt.receipt_id)):
            with self.assertRaises((FrozenInstanceError, TypeError)):
                value.extra = True
            self.assertFalse(hasattr(value, "__dict__"))

    def test_deterministic_candidate_and_assessment_identities(self):
        first = self.identify()
        second = self.identify(first.inventory.receipt)
        self.assertEqual(first.semantic_id, second.semantic_id)
        self.assertEqual(first.evidence_id, second.evidence_id)
        self.assertEqual(first.candidates[0].semantic_id, second.candidates[0].semantic_id)
        self.assertEqual(first.candidates[0].evidence_id, second.candidates[0].evidence_id)
        self.assertNotEqual(first.semantic_id, first.evidence_id)
        self.assertNotEqual(first.candidates[0].semantic_id,
                            first.candidates[0].evidence_id)

    def test_identical_recapture_preserves_semantics_and_changes_evidence(self):
        raw = source_filing()
        first = self.identify(self.capture(raw, captured_at=T1))
        second = self.identify(self.capture(raw, captured_at=T2))
        self.assertEqual(first.semantic_id, second.semantic_id)
        self.assertNotEqual(first.evidence_id, second.evidence_id)
        self.assertEqual(first.candidates[0].semantic_id, second.candidates[0].semantic_id)
        self.assertNotEqual(first.candidates[0].evidence_id,
                            second.candidates[0].evidence_id)

    def test_payload_change_changes_semantics_through_d4d1(self):
        first = self.identify()
        changed = self.result_for(self.item(payload=description_html(
            body_extra="<p>Additional exact source text</p>")))
        self.assertNotEqual(first.inventory.documents[1].semantic_id,
                            changed.inventory.documents[1].semantic_id)
        self.assertNotEqual(first.candidates[0].semantic_id,
                            changed.candidates[0].semantic_id)
        self.assertNotEqual(first.semantic_id, changed.semantic_id)

    def test_filesystem_path_does_not_enter_identity(self):
        raw = source_filing()
        first = self.identify(self.capture(raw))
        other_archive = SecFilingArchive(self.root.parent / "other-path")
        second = self.identify(self.capture(raw, archive=other_archive), archive=other_archive)
        self.assertEqual(first.semantic_id, second.semantic_id)
        self.assertEqual(first.evidence_id, second.evidence_id)

    def test_no_network_hyperlink_following_writes_clock_scan_or_prior_lookup(self):
        payload = description_html(body_extra=(
            "<a href='https://www.sec.gov/Archives/prior-accession.htm'>"
            "incorporated by reference</a>"))
        receipt = self.capture(source_filing(sources=(self.item(payload=payload),)))
        before = {path.relative_to(self.root): path.read_bytes()
                  for path in self.root.rglob("*") if path.is_file()}
        with patch("urllib.request.urlopen", side_effect=AssertionError("network forbidden")), \
             patch("os.listdir", side_effect=AssertionError("directory scan forbidden")), \
             patch("os.scandir", side_effect=AssertionError("directory scan forbidden")), \
             patch("time.time", side_effect=AssertionError("clock forbidden")), \
             patch("time.monotonic", side_effect=AssertionError("clock forbidden")):
            result = self.identify(receipt)
        after = {path.relative_to(self.root): path.read_bytes()
                 for path in self.root.rglob("*") if path.is_file()}
        self.assertEqual(before, after)
        self.assertEqual(len(result.candidates), 1)

    def test_no_candidate_and_positive_status_names_make_no_legal_claim(self):
        negative = self.result_for(self.item(payload=b"Ordinary supported text"))
        positive = self.identify()
        self.assertEqual(negative.status.value, "NO_DIRECT_SUPPORTED_DESCRIPTION_SOURCE")
        self.assertEqual(positive.status.value,
                         "CAPTURED_DIRECT_SECTION12_DESCRIPTION_SOURCES")
        for value in (negative.status.value, positive.status.value):
            for forbidden in ("RIGHTS_ESTABLISHED", "CLASS_ESTABLISHED",
                              "ITEM202_COMPLETE", "ITEM601_COMPLIANT"):
                self.assertNotIn(forbidden, value)


class SecDirectSection12DescriptionDependencyTests(unittest.TestCase):
    def test_exact_dependency_direction_and_no_forbidden_calls(self):
        root = Path(__file__).resolve().parents[1]
        module = root / "economic_facts/sec_direct_section12_description_source.py"
        tree = ast.parse(module.read_text())
        allowed_standard = {"dataclasses", "enum", "html.parser", "re"}
        allowed_relative = {"sec_filing_archive", "sec_filing_document_inventory"}
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                self.assertTrue(all(alias.name in allowed_standard for alias in node.names))
            if isinstance(node, ast.ImportFrom):
                self.assertTrue((node.level == 1 and node.module in allowed_relative)
                                or (node.level == 0 and node.module in allowed_standard))
            if isinstance(node, ast.Call):
                name = (node.func.id if isinstance(node.func, ast.Name) else
                        node.func.attr if isinstance(node.func, ast.Attribute) else "")
                self.assertNotIn(name, {"open", "float", "eval", "exec", "__import__",
                                        "now", "today"})

    def test_no_identity_authority_expected_return_model_runtime_or_v1_consumer(self):
        root = Path(__file__).resolve().parents[1]
        module_name = "sec_direct_section12_description_source"
        source_text = (root / "economic_facts" / (module_name + ".py")).read_text()
        tree = ast.parse(source_text)
        imported = {node.module or "" for node in ast.walk(tree)
                    if isinstance(node, ast.ImportFrom)}
        for forbidden in ("security_identity", "sec_current_registered_listing_bridge",
                          "source_authority", "expected_return", "src", "model", "portfolio",
                          "runtime", "main"):
            self.assertFalse(any(name == forbidden or name.startswith(forbidden + ".")
                                 for name in imported))
        for path in [root / "main.py", *(root / "src").rglob("*.py"),
                     *(root / "pit_comparison").rglob("*.py"),
                     *(root / "scripts").rglob("*.py")]:
            self.assertNotIn(module_name, path.read_text(), str(path))

    def test_contract_preserves_property4_obligations_and_nonclaims(self):
        text = (Path(__file__).resolve().parents[1] / "docs" / "contracts" / "v2"
                / "expected_return" / "EXPECTED_RETURN_PR4D4D2A.md").read_text()
        for property_name in ("4A", "4B", "4C", "4D", "4E", "4F", "4G", "4H"):
            self.assertIn("| " + property_name + " |", text)
        for phrase in ("Obligations 5–7 remain unresolved", "direct-only",
                       "incorporation by reference", "No legal-rights extraction",
                       "NO_DIRECT_SUPPORTED_DESCRIPTION_SOURCE", "D4C2"):
            self.assertIn(phrase, text)


if __name__ == "__main__":
    unittest.main()
