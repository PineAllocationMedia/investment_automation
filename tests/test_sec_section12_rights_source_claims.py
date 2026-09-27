"""PR4D4D2B class-scoped Section-12 rights-topic source passages."""
import ast
from dataclasses import FrozenInstanceError, fields
import inspect
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from economic_facts import sec_section12_rights_source_claims as claims
from economic_facts.sec_filing_archive import SecFilingArchive, digest
from tests.sec_direct_section12_description_fixtures import (
    HEADING,
    SECTION12,
    description_html,
    description_text,
)
from tests.sec_original_filing_fixtures import ACCESSION, CIK, T1, T2
from tests.sec_section12_rights_source_claims_fixtures import (
    RIGHTS_TEXT,
    rights_html,
    rights_source_filing,
    rights_source_item,
)


class SecSection12RightsSourceClaimsTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve() / "archive"
        self.archive = SecFilingArchive(self.root)

    def capture(self, raw=None, *, archive=None, captured_at=T1):
        archive = self.archive if archive is None else archive
        return archive._capture_live(
            rights_source_filing() if raw is None else raw,
            cik=CIK,
            accession=ACCESSION,
            captured_at=captured_at,
        )

    def extract(self, receipt=None, *, archive=None):
        archive = self.archive if archive is None else archive
        receipt = self.capture(archive=archive) if receipt is None else receipt
        request = claims.SecSection12RightsSourceClaimsRequest(receipt.receipt_id)
        return claims.extract_sec_section12_rights_source_claims(archive, request)

    def result_for(self, *items, form="10-K"):
        return self.extract(self.capture(rights_source_filing(*items, form=form)))

    def reset_archive(self, suffix):
        self.root = self.root.parent / suffix
        self.archive = SecFilingArchive(self.root)

    def test_exact_public_api_closed_request_and_typed_arguments(self):
        self.assertEqual(set(inspect.signature(
            claims.extract_sec_section12_rights_source_claims).parameters),
            {"archive", "request"})
        self.assertEqual([field.name for field in fields(
            claims.SecSection12RightsSourceClaimsRequest)], ["filing_receipt_id"])
        receipt = self.capture()
        for keyword in ("assessment", "candidate", "document", "cik", "accession",
                        "form", "class_name", "ticker", "exchange", "security_id",
                        "topic", "rights_value", "as_of", "raw", "url", "clock",
                        "qualified", "admitted"):
            with self.subTest(keyword=keyword), self.assertRaises(TypeError):
                claims.SecSection12RightsSourceClaimsRequest(
                    receipt.receipt_id, **{keyword: "caller assertion"})
        request = claims.SecSection12RightsSourceClaimsRequest(receipt.receipt_id)
        for archive, selected in ((object(), request), (self.archive, object())):
            with self.assertRaises(claims.SecSection12RightsSourceClaimsRequestError):
                claims.extract_sec_section12_rights_source_claims(archive, selected)

    def test_receipt_selector_is_exact(self):
        for value in (None, 0, True, "", "0" * 63, "0" * 65, "A" * 64,
                      "../" + "0" * 64, "٠" * 64, "0" * 64 + " "):
            with self.subTest(value=value), self.assertRaises(
                    claims.SecSection12RightsSourceClaimsRequestError):
                claims.SecSection12RightsSourceClaimsRequest(value)

    def test_d4d2a_is_freshly_replayed_and_cannot_be_supplied(self):
        receipt = self.capture()
        real = claims.identify_sec_direct_section12_description_sources
        with patch.object(claims, "identify_sec_direct_section12_description_sources",
                          wraps=real) as replay:
            result = self.extract(receipt)
        replay.assert_called_once()
        self.assertEqual(replay.call_args.args[1].filing_receipt_id, receipt.receipt_id)
        self.assertEqual(result.upstream_assessment.inventory.receipt, receipt)

    def test_upstream_non_success_states_are_distinct_and_cannot_be_cherry_picked(self):
        cases = (
            (rights_source_item(payload=b"ordinary text"), "10-K",
             claims.SecSection12RightsSourceIssue.UPSTREAM_NO_DIRECT_SUPPORTED_DESCRIPTION_SOURCE),
            (rights_source_item(payload=b"<html><body>broken</html>"), "10-K",
             claims.SecSection12RightsSourceIssue.UPSTREAM_SOURCE_AMBIGUITY),
            (rights_source_item(payload=b"%PDF-1.7"), "10-K",
             claims.SecSection12RightsSourceIssue.UPSTREAM_UNSUPPORTED_DOCUMENT_REPRESENTATION),
            (rights_source_item(), "10-Q",
             claims.SecSection12RightsSourceIssue.UPSTREAM_UNSUPPORTED_FILING_FORM),
        )
        for index, (item, form, issue) in enumerate(cases):
            result = self.result_for(item, form=form)
            with self.subTest(issue=issue):
                self.assertEqual(result.status,
                    claims.SecSection12RightsSourceClaimsStatus.UPSTREAM_DIRECT_SOURCE_UNAVAILABLE)
                self.assertEqual(result.issues, (issue,))
                self.assertEqual(result.class_scopes, ())
                self.assertEqual(result.passages, ())
            self.reset_archive(f"upstream-{index}")

        positive_and_ambiguous = self.result_for(
            rights_source_item(payload=rights_html(), sequence="2", filename="good.htm"),
            rights_source_item(payload=b"<html><body>broken</html>",
                               document_type="EX-4.B", sequence="3", filename="bad.htm"),
        )
        self.assertTrue(positive_and_ambiguous.upstream_assessment.candidates)
        self.assertEqual(positive_and_ambiguous.status,
            claims.SecSection12RightsSourceClaimsStatus.UPSTREAM_DIRECT_SOURCE_UNAVAILABLE)
        self.assertEqual(positive_and_ambiguous.class_scopes, ())
        self.assertEqual(positive_and_ambiguous.passages, ())

    def test_utf8_html_and_xhtml_supported_but_text_is_explicitly_unsupported(self):
        html_result = self.result_for(rights_source_item(payload=rights_html()))
        self.assertEqual(html_result.status,
            claims.SecSection12RightsSourceClaimsStatus.CAPTURED_SECTION12_RIGHTS_SOURCE_CLAIMS)
        self.reset_archive("xhtml")
        xhtml_result = self.result_for(rights_source_item(payload=rights_html(xhtml=True)))
        self.assertEqual(xhtml_result.status,
            claims.SecSection12RightsSourceClaimsStatus.CAPTURED_SECTION12_RIGHTS_SOURCE_CLAIMS)
        self.reset_archive("text")
        text = description_text() + b"\nCOMMON STOCK\nVoting rights.\n"
        text_result = self.result_for(rights_source_item(payload=text))
        self.assertEqual(text_result.status,
            claims.SecSection12RightsSourceClaimsStatus.UNSUPPORTED_RIGHTS_EXTRACTION_PROFILE)
        self.assertEqual(text_result.issues, (
            claims.SecSection12RightsSourceIssue.UNSUPPORTED_RIGHTS_EXTRACTION_REPRESENTATION,))

    def test_common_stock_heading_grammar_is_closed(self):
        positives = ("COMMON STOCK", "CLASS A COMMON STOCK", "CLASS B COMMON STOCK",
                     "class c common stock")
        for index, heading in enumerate(positives):
            result = self.result_for(rights_source_item(payload=rights_html(
                blocks=(("h2", heading), ("p", "Voting rights.")))))
            with self.subTest(heading=heading):
                self.assertEqual(len(result.class_scopes), 1)
                self.assertEqual(result.class_scopes[0].exact_class_heading, heading)
            self.reset_archive(f"heading-positive-{index}")

        for index, heading in enumerate(("COMMON SHARES", "ORDINARY SHARES",
                                         "ORDINARY STOCK", "PREFERRED STOCK")):
            result = self.result_for(rights_source_item(payload=rights_html(
                blocks=(("h2", heading), ("p", "Voting rights.")))))
            with self.subTest(heading=heading):
                self.assertEqual(result.status,
                    claims.SecSection12RightsSourceClaimsStatus.NO_SUPPORTED_COMMON_STOCK_SCOPE)
            self.reset_archive(f"heading-negative-{index}")

    def test_malformed_class_token_fails_closed(self):
        for index, heading in enumerate(("CLASS AA COMMON STOCK", "CLASS A-1 COMMON STOCK",
                                         "CLASS _ COMMON STOCK")):
            result = self.result_for(rights_source_item(payload=rights_html(
                blocks=(("h2", heading), ("p", "Voting rights.")))))
            with self.subTest(heading=heading):
                self.assertEqual(result.status,
                    claims.SecSection12RightsSourceClaimsStatus.SOURCE_AMBIGUITY)
                self.assertIn(
                    claims.SecSection12RightsSourceIssue.UNSUPPORTED_COMMON_STOCK_HEADING_STRUCTURE,
                    result.issues)
            self.reset_archive(f"malformed-token-{index}")

    def test_security_boundaries_stop_common_scope_without_creating_claims(self):
        for index, boundary in enumerate(("PREFERRED STOCK", "CLASS A PREFERRED STOCK",
                                          "DEBT SECURITIES", "WARRANTS",
                                          "DEPOSITARY SHARES")):
            result = self.result_for(rights_source_item(payload=rights_html(blocks=(
                ("h2", "COMMON STOCK"),
                ("p", "Holders have voting rights."),
                ("h2", boundary),
                ("p", "Preferred conversion redemption dividend liquidation rights."),
            ))))
            with self.subTest(boundary=boundary):
                self.assertEqual(len(result.class_scopes), 1)
                self.assertEqual(len(result.passages), 1)
                self.assertEqual(result.passages[0].matched_topics,
                                 (claims.SecSection12RightsSourceTopic.VOTING,))
                self.assertNotIn(4, result.class_scopes[0].body_block_ordinals)
            self.reset_archive(f"boundary-{index}")

    def test_multiple_and_duplicate_common_scopes_are_preserved_without_primary(self):
        result = self.result_for(rights_source_item(payload=rights_html(blocks=(
            ("h2", "CLASS A COMMON STOCK"), ("p", "One vote."),
            ("h2", "CLASS B COMMON STOCK"), ("p", "Dividends may be declared."),
            ("h2", "CLASS A COMMON STOCK"), ("p", "Upon liquidation."),
        ))))
        self.assertEqual(tuple(scope.exact_class_heading for scope in result.class_scopes),
                         ("CLASS A COMMON STOCK", "CLASS B COMMON STOCK",
                          "CLASS A COMMON STOCK"))
        self.assertEqual(len({scope.source_class_scope_id for scope in result.class_scopes}), 3)
        self.assertFalse(hasattr(result, "primary_class_scope"))
        self.assertEqual(tuple(passage.matched_topics for passage in result.passages), (
            (claims.SecSection12RightsSourceTopic.VOTING,),
            (claims.SecSection12RightsSourceTopic.DIVIDEND,),
            (claims.SecSection12RightsSourceTopic.LIQUIDATION,),
        ))

    def test_closed_topic_taxonomy_and_exact_reviewed_anchors(self):
        self.assertEqual({item.value for item in claims.SecSection12RightsSourceTopic}, {
            "DIVIDEND", "VOTING", "LIQUIDATION", "FURTHER_CALLS_OR_ASSESSMENTS",
            "PREEMPTIVE", "CONVERSION", "REDEMPTION", "SINKING_FUND",
        })
        result = self.extract()
        passage = result.passages[0]
        self.assertEqual(set(passage.matched_topics), set(claims.SecSection12RightsSourceTopic))
        self.assertEqual(passage.exact_source_text, RIGHTS_TEXT)
        self.assertEqual(passage.source_text_sha256, digest(RIGHTS_TEXT.encode()))
        self.assertIn(claims.SecSection12RightsTopicAnchor.WINDING_HYPHEN_UP,
                      passage.matched_topic_anchor_ids)
        self.assertIn(claims.SecSection12RightsTopicAnchor.NON_HYPHEN_ASSESSABLE,
                      passage.matched_topic_anchor_ids)

    def test_each_topic_anchor_family_is_detected_as_source_topic_only(self):
        cases = (
            ("A dividend may be paid.", claims.SecSection12RightsSourceTopic.DIVIDEND),
            ("The holders cast votes.", claims.SecSection12RightsSourceTopic.VOTING),
            ("Upon winding up.", claims.SecSection12RightsSourceTopic.LIQUIDATION),
            ("No further calls or assessment.",
             claims.SecSection12RightsSourceTopic.FURTHER_CALLS_OR_ASSESSMENTS),
            ("No pre-emptive right.", claims.SecSection12RightsSourceTopic.PREEMPTIVE),
            ("The shares are convertible.", claims.SecSection12RightsSourceTopic.CONVERSION),
            ("The shares are redeemable.", claims.SecSection12RightsSourceTopic.REDEMPTION),
            ("No sinking fund applies.", claims.SecSection12RightsSourceTopic.SINKING_FUND),
        )
        for index, (text, topic) in enumerate(cases):
            result = self.result_for(rights_source_item(payload=rights_html(
                blocks=(("h2", "COMMON STOCK"), ("p", text)))))
            with self.subTest(topic=topic):
                self.assertEqual(result.passages[0].matched_topics, (topic,))
            self.reset_archive(f"topic-{index}")

    def test_one_block_is_one_passage_with_multiple_topics_and_no_concatenation(self):
        first = "Holders have one vote and receive dividends."
        second = "Upon liquidation, assets are distributed."
        result = self.result_for(rights_source_item(payload=rights_html(blocks=(
            ("h2", "COMMON STOCK"), ("p", first), ("p", "Neutral intervening text."),
            ("p", second),
        ))))
        self.assertEqual([passage.exact_source_text for passage in result.passages],
                         [first, second])
        self.assertNotIn(first + second,
                         [passage.exact_source_text for passage in result.passages])
        self.assertLess(result.passages[0].block_ordinal, result.passages[1].block_ordinal)

    def test_no_topic_is_inferred_from_absence_metadata_or_upstream_anchors(self):
        result = self.result_for(rights_source_item(
            payload=rights_html(blocks=(("h2", "COMMON STOCK"),
                                        ("p", "Exact neutral source passage."))),
            filename="voting-dividend-liquidation.htm",
            description="PREEMPTIVE CONVERSION REDEMPTION SINKING FUND"))
        self.assertEqual(result.status,
            claims.SecSection12RightsSourceClaimsStatus.NO_SUPPORTED_RIGHTS_SOURCE_CLAIMS)
        self.assertEqual(result.passages, ())
        self.assertEqual(len(result.class_scopes), 1)

    def test_rights_outside_scope_and_preferred_rights_do_not_leak(self):
        result = self.result_for(rights_source_item(payload=rights_html(blocks=(
            ("p", "Voting dividends before any class scope."),
            ("h2", "COMMON STOCK"), ("p", "Neutral common text."),
            ("h2", "PREFERRED STOCK"),
            ("p", "Conversion redemption liquidation dividend voting sinking fund."),
        ))))
        self.assertEqual(result.status,
            claims.SecSection12RightsSourceClaimsStatus.NO_SUPPORTED_RIGHTS_SOURCE_CLAIMS)
        self.assertEqual(result.passages, ())

    def test_exact_decoded_source_text_kind_hash_and_order_are_preserved(self):
        first = "One vote & dividends."
        second = "Upon liquidation."
        payload = rights_html(blocks=(
            ("h2", "COMMON STOCK"),
            ("p", "One vote &amp; dividends."),
            ("blockquote", second),
        ))
        result = self.result_for(rights_source_item(payload=payload))
        self.assertEqual(tuple(item.exact_source_text for item in result.passages),
                         (first, second))
        self.assertEqual(tuple(item.structural_element_kind for item in result.passages),
                         ("p", "blockquote"))
        self.assertEqual(result.passages[0].source_text_sha256,
                         digest(first.encode("utf-8")))
        self.assertEqual(tuple(item.block_ordinal for item in result.passages), (3, 4))

    def test_nested_layout_containers_do_not_duplicate_visible_blocks(self):
        payload = (
            f"<html><head><title>x</title></head><body><div><h1>{HEADING}</h1>"
            f"<p>{SECTION12}</p><section><h2>COMMON STOCK</h2>"
            "<div><p>Voting rights.</p></div></section></div></body></html>"
        ).encode()
        result = self.result_for(rights_source_item(payload=payload))
        self.assertEqual(len(result.passages), 1)
        self.assertEqual(result.passages[0].exact_source_text, "Voting rights.")

    def test_script_style_and_other_technical_subtrees_cannot_supply_claims(self):
        excluded = "".join(
            f"<{tag}>Voting dividends liquidation conversion redemption sinking fund</{tag}>"
            for tag in ("script", "style", "noscript", "template", "svg", "math", "canvas"))
        payload = rights_html(blocks=(
            ("h2", "COMMON STOCK"),
            ("p", excluded + "Neutral visible text."),
        ))
        result = self.result_for(rights_source_item(payload=payload))
        self.assertEqual(result.status,
            claims.SecSection12RightsSourceClaimsStatus.NO_SUPPORTED_RIGHTS_SOURCE_CLAIMS)

    def test_matching_normalization_is_only_whitespace_and_ascii_case(self):
        positive = self.result_for(rights_source_item(payload=rights_html(blocks=(
            ("h2", " common\n stock "), ("p", "VOTING\tRIGHTS"),
        ))))
        self.assertEqual(positive.passages[0].matched_topics,
                         (claims.SecSection12RightsSourceTopic.VOTING,))
        self.reset_archive("near")
        near = "votting distributions pre—emptive convertibility redemptive sinking-fund"
        negative = self.result_for(rights_source_item(payload=rights_html(blocks=(
            ("h2", "COMMON STOCK"), ("p", near),
        ))))
        self.assertEqual(negative.status,
            claims.SecSection12RightsSourceClaimsStatus.NO_SUPPORTED_RIGHTS_SOURCE_CLAIMS)

    def test_oversized_block_and_ambiguous_direct_body_text_fail_closed(self):
        oversized = self.result_for(rights_source_item(payload=rights_html(blocks=(
            ("h2", "COMMON STOCK"), ("p", "V" * (claims.MAX_BLOCK_CHARACTERS + 1)),
        ))))
        self.assertEqual(oversized.status,
            claims.SecSection12RightsSourceClaimsStatus.SOURCE_AMBIGUITY)
        self.assertIn(claims.SecSection12RightsSourceIssue.SOURCE_SAFETY_BOUND_EXCEEDED,
                      oversized.issues)
        self.reset_archive("direct-body")
        direct = self.result_for(rights_source_item(payload=rights_html(
            body_prefix="COMMON STOCK Voting rights.")))
        self.assertEqual(direct.status,
            claims.SecSection12RightsSourceClaimsStatus.SOURCE_AMBIGUITY)

    def test_one_unsupported_candidate_prevents_global_success_but_keeps_valid_claims(self):
        result = self.result_for(
            rights_source_item(payload=rights_html(), sequence="2", filename="a.htm"),
            rights_source_item(payload=description_text() + b"\nCOMMON STOCK\nVoting rights",
                               document_type="EX-4.B", sequence="3", filename="b.txt"),
        )
        self.assertEqual(result.status,
            claims.SecSection12RightsSourceClaimsStatus.UNSUPPORTED_RIGHTS_EXTRACTION_PROFILE)
        self.assertTrue(result.class_scopes)
        self.assertTrue(result.passages)
        self.assertEqual(len(result.source_issues), 1)

    def test_multiple_candidates_are_processed_independently_in_source_order(self):
        result = self.result_for(
            rights_source_item(payload=rights_html(blocks=(
                ("h2", "CLASS A COMMON STOCK"), ("p", "Voting rights."))),
                sequence="2", filename="a.htm"),
            rights_source_item(payload=rights_html(blocks=(
                ("h2", "CLASS B COMMON STOCK"), ("p", "Dividend rights."))),
                document_type="EX-4.B", sequence="3", filename="b.htm"),
        )
        self.assertEqual(tuple(scope.exact_class_heading for scope in result.class_scopes),
                         ("CLASS A COMMON STOCK", "CLASS B COMMON STOCK"))
        self.assertEqual(tuple(passage.source_class_heading for passage in result.passages),
                         ("CLASS A COMMON STOCK", "CLASS B COMMON STOCK"))

    def test_source_class_scope_identity_is_document_local(self):
        result = self.result_for(
            rights_source_item(payload=rights_html(), sequence="2", filename="a.htm"),
            rights_source_item(payload=rights_html(), document_type="EX-4.B",
                               sequence="3", filename="b.htm"),
        )
        self.assertEqual(tuple(scope.exact_class_heading for scope in result.class_scopes),
                         ("COMMON STOCK", "COMMON STOCK"))
        self.assertNotEqual(result.class_scopes[0].source_class_scope_id,
                            result.class_scopes[1].source_class_scope_id)

    def test_scope_passage_and_assessment_identities_are_deterministic(self):
        first = self.extract()
        second = self.extract(first.upstream_assessment.inventory.receipt)
        self.assertEqual((first.semantic_id, first.evidence_id),
                         (second.semantic_id, second.evidence_id))
        self.assertEqual(first.class_scopes[0].source_class_scope_id,
                         first.class_scopes[0].semantic_id)
        self.assertEqual(first.passages[0].source_class_scope_id,
                         first.class_scopes[0].semantic_id)
        self.assertEqual(first.class_scopes[0].passage_semantic_ids,
                         (first.passages[0].semantic_id,))
        self.assertNotEqual(first.semantic_id, first.evidence_id)
        self.assertNotEqual(first.passages[0].semantic_id, first.passages[0].evidence_id)

    def test_identical_recapture_preserves_semantics_and_changes_evidence(self):
        raw = rights_source_filing()
        first = self.extract(self.capture(raw, captured_at=T1))
        second = self.extract(self.capture(raw, captured_at=T2))
        self.assertEqual(first.semantic_id, second.semantic_id)
        self.assertNotEqual(first.evidence_id, second.evidence_id)
        self.assertEqual(first.class_scopes[0].semantic_id,
                         second.class_scopes[0].semantic_id)
        self.assertNotEqual(first.class_scopes[0].evidence_id,
                            second.class_scopes[0].evidence_id)
        self.assertEqual(first.passages[0].semantic_id, second.passages[0].semantic_id)
        self.assertNotEqual(first.passages[0].evidence_id, second.passages[0].evidence_id)

    def test_changed_passage_or_heading_changes_semantics(self):
        first = self.extract()
        self.reset_archive("changed-passage")
        changed_passage = self.result_for(rights_source_item(payload=rights_html(blocks=(
            ("h2", "COMMON STOCK"), ("p", RIGHTS_TEXT + " Additional voting text."),
        ))))
        self.assertNotEqual(first.passages[0].semantic_id,
                            changed_passage.passages[0].semantic_id)
        self.reset_archive("changed-heading")
        changed_heading = self.result_for(rights_source_item(payload=rights_html(blocks=(
            ("h2", "CLASS A COMMON STOCK"), ("p", RIGHTS_TEXT),
        ))))
        self.assertNotEqual(first.class_scopes[0].semantic_id,
                            changed_heading.class_scopes[0].semantic_id)

    def test_filesystem_path_does_not_enter_identity(self):
        raw = rights_source_filing()
        first = self.extract(self.capture(raw))
        other_archive = SecFilingArchive(self.root.parent / "other-path")
        second = self.extract(self.capture(raw, archive=other_archive), archive=other_archive)
        self.assertEqual(first.semantic_id, second.semantic_id)
        self.assertEqual(first.evidence_id, second.evidence_id)

    def test_records_are_frozen_and_expose_no_interpreted_legal_values(self):
        result = self.extract()
        records = (claims.SecSection12RightsSourceClaimsRequest,
                   claims.SecSection12SourceClassScope,
                   claims.SecSection12RightsSourcePassage,
                   claims.SecSection12RightsSourceClaimsAssessment)
        forbidden = {
            "registered_class", "class_id", "security_id", "listing_id", "ticker",
            "exchange", "instrument_type", "ordinary_common_equity", "qualified",
            "admitted", "has_voting_rights", "votes_per_share", "preemptive_rights",
            "conversion_rights", "redeemable", "dividend_rate",
            "liquidation_preference", "conversion_ratio", "redemption_price",
            "par_value", "authorized_shares", "item202_complete", "rights_complete",
            "property4c_complete", "as_of", "effective_at", "published_at",
        }
        for record in records:
            self.assertFalse(forbidden & set(record.__dataclass_fields__), record)
        for value in (result, result.class_scopes[0], result.passages[0]):
            with self.assertRaises((FrozenInstanceError, TypeError)):
                value.extra = True
            self.assertFalse(hasattr(value, "__dict__"))

    def test_no_network_writes_clock_scans_latest_or_external_fetch(self):
        receipt = self.capture()
        before = {path.relative_to(self.root): path.read_bytes()
                  for path in self.root.rglob("*") if path.is_file()}
        with patch("urllib.request.urlopen", side_effect=AssertionError("network forbidden")), \
             patch("os.listdir", side_effect=AssertionError("directory scan forbidden")), \
             patch("os.scandir", side_effect=AssertionError("directory scan forbidden")), \
             patch("time.time", side_effect=AssertionError("clock forbidden")), \
             patch("time.monotonic", side_effect=AssertionError("clock forbidden")):
            result = self.extract(receipt)
        after = {path.relative_to(self.root): path.read_bytes()
                 for path in self.root.rglob("*") if path.is_file()}
        self.assertEqual(before, after)
        self.assertEqual(result.status,
            claims.SecSection12RightsSourceClaimsStatus.CAPTURED_SECTION12_RIGHTS_SOURCE_CLAIMS)


class SecSection12RightsSourceClaimsDependencyTests(unittest.TestCase):
    def test_exact_dependency_direction_and_no_forbidden_imports_or_calls(self):
        root = Path(__file__).resolve().parents[1]
        module = root / "economic_facts/sec_section12_rights_source_claims.py"
        tree = ast.parse(module.read_text())
        allowed_standard = {"dataclasses", "enum", "html.parser", "re"}
        allowed_relative = {"sec_filing_archive", "sec_direct_section12_description_source"}
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
                                        "now", "today", "listdir", "scandir"})
        imported = {node.module or "" for node in ast.walk(tree)
                    if isinstance(node, ast.ImportFrom)}
        for forbidden in ("sec_registered_securities", "sec_current_registered_listing_bridge",
                          "security_identity", "source_authority", "expected_return", "src",
                          "model", "portfolio", "runtime", "main"):
            self.assertFalse(any(name == forbidden or name.startswith(forbidden + ".")
                                 for name in imported))

    def test_no_model_runtime_v1_or_existing_evidence_consumer(self):
        root = Path(__file__).resolve().parents[1]
        module_name = "sec_section12_rights_source_claims"
        allowed = root / "economic_facts" / (module_name + ".py")
        for path in [root / "main.py", *(root / "src").rglob("*.py"),
                     *(root / "pit_comparison").rglob("*.py"),
                     *(root / "scripts").rglob("*.py"),
                     *(root / "economic_facts").rglob("*.py")]:
            if path == allowed:
                continue
            self.assertNotIn(module_name, path.read_text(), str(path))

    def test_contract_preserves_all_property4_and_remaining_obligations(self):
        text = (Path(__file__).resolve().parents[1]
                / "EXPECTED_RETURN_PR4D4D2B.md").read_text()
        for property_name in ("4A", "4B", "4C", "4D", "4E", "4F", "4G", "4H"):
            self.assertIn("| " + property_name + " |", text)
        for phrase in ("Obligations 5–7 remain unresolved", "not legal-right values",
                       "No D3A/D4C2 join", "no Item-202 completeness"):
            self.assertIn(phrase, text)


if __name__ == "__main__":
    unittest.main()
