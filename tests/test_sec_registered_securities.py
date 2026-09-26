"""PR4D3A offline extraction, adversarial source semantics and negative authority boundaries."""
import ast
from contextlib import ExitStack
from dataclasses import FrozenInstanceError, asdict, replace
import hashlib
import inspect
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from economic_facts import sec_filing_archive as a
from economic_facts import sec_registered_securities as s
from tests.sec_original_filing_fixtures import ACCESSION, CIK, T1, T2, document, filing
from tests.sec_registered_security_fixtures import context, fact, inline, security, submission


class RegisteredSecurityTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve() / "filings"
        self.archive = a.SecFilingArchive(self.root)

    def capture(self, raw=None, captured_at=T1):
        return self.archive._capture_live(submission() if raw is None else raw, cik=CIK,
                                          accession=ACCESSION, captured_at=captured_at)

    def replay(self, receipt):
        return s.extract_sec_registered_security_claims(
            self.archive, s.SecRegisteredSecurityExtractionRequest(receipt.receipt_id))

    def extract(self, **kwargs):
        return self.replay(self.capture(submission(**kwargs)))

    def unsupported(self, payload):
        with self.assertRaises(s.UnsupportedRegisteredSecuritySource):
            self.replay(self.capture(filing(payload=payload)))

    def test_one_source_claim_exact_provenance(self):
        raw, payload = submission(), inline()
        receipt = self.capture(raw)
        result = self.replay(receipt)
        self.assertEqual(result.status, s.ExtractionStatus.CAPTURED_REGISTERED_SECURITY_CLAIMS)
        primary = result.primary_document
        self.assertEqual((primary.receipt_id, primary.cik, primary.accession, primary.form, primary.endpoint),
                         (receipt.receipt_id, CIK, ACCESSION, "10-K", receipt.endpoint))
        self.assertEqual((primary.sequence, primary.filename, primary.document_ordinal), ("1", "fictional.htm", 0))
        self.assertEqual(raw[primary.byte_start:primary.byte_start + primary.byte_length], payload)
        self.assertEqual(primary.content_sha256, hashlib.sha256(payload).hexdigest())
        self.assertEqual(len(result.claims), 1)
        self.assertEqual(result.claims[0].titles, ("Class A Common Stock, $0.01 par value",))
        self.assertEqual(result.claims[0].trading_symbols, ("FICT",))
        self.assertEqual(result.claims[0].exchange_names, ("NASDAQ",))
        self.assertEqual(result.claims[0].issues, ())
        self.assertEqual([f.fact_name for f in result.occurrences], ["{" + s.DEI + "}" + n
                                                                  for n in s.FACT_NAMES if n != "NoTradingSymbolFlag"])
        for f in result.occurrences:
            self.assertEqual(f.primary_document_id, primary.evidence_id)
            self.assertEqual(f.context_ref, "c1")
            self.assertGreater(f.element_ordinal, 0)
            self.assertGreater(f.source_line, 0)
        self.assertEqual(result.contexts[0].entity_identifier, CIK)

    def test_supported_forms_and_amendments(self):
        for form in ("10-K", "10-K/A", "10-Q", "10-Q/A"):
            with self.subTest(form=form):
                result = self.replay(self.capture(filing(form=form, payload=inline())))
                self.assertEqual(result.primary_document.form, form)
                self.assertEqual(result.status, s.ExtractionStatus.CAPTURED_REGISTERED_SECURITY_CLAIMS)

    def test_8k_and_other_forms_never_semantically_extracted(self):
        for form in ("8-K", "8-K/A", "20-F", "6-K"):
            with self.subTest(form=form), self.assertRaises(s.UnsupportedRegisteredSecuritySource):
                self.replay(self.capture(filing(form=form, payload=inline())))

    def test_only_explicit_receipt_no_latest(self):
        old = self.capture()
        self.capture(submission(facts=security(symbol="NEW")), T2)
        self.assertEqual(self.replay(old).claims[0].trading_symbols, ("FICT",))
        with patch.object(a.SecFilingArchive, "read_receipt", wraps=self.archive.read_receipt) as read:
            self.replay(old)
            self.assertTrue(all(call.args == (old.receipt_id,) for call in read.call_args_list))

    def test_missing_receipt_and_other_archive_membership(self):
        receipt = self.capture()
        with self.assertRaises(a.FilingArchiveError):
            s.extract_sec_registered_security_claims(a.SecFilingArchive(self.root.parent / "other"),
                s.SecRegisteredSecurityExtractionRequest(receipt.receipt_id))
        with self.assertRaises(a.FilingArchiveError):
            s.extract_sec_registered_security_claims(self.archive, s.SecRegisteredSecurityExtractionRequest("0" * 64))

    def test_object_hash_corruption(self):
        receipt = self.capture()
        path = self.root / "objects" / receipt.content_sha256
        path.chmod(0o600)
        path.write_bytes(path.read_bytes().replace(b"FICT", b"FAKE"))
        with self.assertRaises(a.FilingArchiveError):
            self.replay(receipt)

    def test_object_length_corruption(self):
        receipt = self.capture()
        path = self.root / "objects" / receipt.content_sha256
        path.chmod(0o600)
        path.write_bytes(path.read_bytes()[:-1])
        with self.assertRaises(a.FilingArchiveError):
            self.replay(receipt)

    def test_detached_modified_receipt_not_accepted(self):
        receipt = replace(self.capture(), captured_at=T2)
        with self.assertRaises(a.FilingArchiveError):
            self.replay(receipt)

    def test_closed_request_and_exact_types(self):
        self.assertEqual(set(inspect.signature(s.extract_sec_registered_security_claims).parameters), {"archive", "request"})
        self.assertEqual(set(s.SecRegisteredSecurityExtractionRequest.__dataclass_fields__), {"filing_receipt_id"})
        for value in (None, b"0" * 64, "", "https://fiction.invalid", "../receipt", True, ("0" * 64,)):
            with self.assertRaises(s.RegisteredSecurityRequestError):
                s.SecRegisteredSecurityExtractionRequest(value)
        for request in (self.capture(), submission(), {"filing_receipt_id": "0" * 64}, "0" * 64):
            with self.assertRaises(s.RegisteredSecurityRequestError):
                s.extract_sec_registered_security_claims(self.archive, request)
        class RequestSubclass(s.SecRegisteredSecurityExtractionRequest):
            pass
        with self.assertRaises(s.RegisteredSecurityRequestError):
            s.extract_sec_registered_security_claims(self.archive, RequestSubclass("0" * 64))

    def test_records_frozen_slotted(self):
        result = self.extract()
        for record in (result, result.primary_document, *result.contexts, *result.occurrences, *result.claims):
            self.assertFalse(hasattr(record, "__dict__"))
            with self.assertRaises(FrozenInstanceError):
                setattr(record, next(iter(record.__dataclass_fields__)), None)

    def test_multiple_securities_never_joined_by_same_symbol_or_name(self):
        result = self.extract(contexts=context("a", member="fiction:AMember") + context("b", member="fiction:BMember"),
                              facts=security("a") + security("b"))
        self.assertEqual(len(result.claims), 2)
        self.assertEqual(len({c.source_security_scope_id for c in result.claims}), 2)
        self.assertEqual(result.status, s.ExtractionStatus.CAPTURED_REGISTERED_SECURITY_CLAIMS)
        self.assertEqual(result.contexts[0].dimensions[0].source_member, "fiction:AMember")

    def test_multiple_exchange_contexts_visible_under_explicit_source_scope(self):
        result = self.extract(contexts=context("a", member="fiction:AMember", exchange="fiction:NasdaqMember")
                              + context("b", member="fiction:AMember", exchange="fiction:OtherMember"),
                              facts=security("a") + security("b", symbol="FICT2", exchange="OTHER TEXT"))
        self.assertEqual(len(result.claims), 2)
        self.assertEqual(len({c.source_security_scope_id for c in result.claims}), 1)
        self.assertEqual({c.exchange_names for c in result.claims}, {("NASDAQ",), ("OTHER TEXT",)})
        self.assertEqual(result.status, s.ExtractionStatus.CAPTURED_REGISTERED_SECURITY_CLAIMS)

    def test_symbol_absent_explicit_no_trading_symbol(self):
        result = self.extract(facts=security(no_symbol=True))
        self.assertEqual(result.claims[0].trading_symbols, ())
        self.assertEqual(result.claims[0].no_trading_symbol_flags, ("true",))
        self.assertEqual(result.status, s.ExtractionStatus.CAPTURED_REGISTERED_SECURITY_CLAIMS)
        other = self.extract(facts=security(no_symbol=True).replace(">true<", ">1<"))
        self.assertEqual(other.claims[0].no_trading_symbol_flags, ("1",))

    def test_false_or_unknown_no_symbol_not_inferred(self):
        for flag in ("false", "0", "Yes", "☑", " true "):
            self.unsupported(inline(facts=security(no_symbol=True).replace(">true<", ">" + flag + "<")))

    def test_duplicate_identical_occurrences_not_extra_securities(self):
        base = self.extract()
        duplicate = self.extract(facts=security() + security())
        self.assertEqual(len(duplicate.claims), 1)
        self.assertEqual(len(duplicate.occurrences), 6)
        self.assertEqual(len({f.occurrence_id for f in duplicate.occurrences}), 6)
        self.assertEqual(base.semantic_id, duplicate.semantic_id)
        self.assertNotEqual(base.evidence_id, duplicate.evidence_id)

    def test_contradictory_values_keep_every_value_no_vote(self):
        result = self.extract(facts=security() + fact("TradingSymbol", "OTHER") + fact("TradingSymbol", "FICT"))
        self.assertEqual(result.status, s.ExtractionStatus.SOURCE_CONFLICT)
        self.assertEqual(result.claims[0].trading_symbols, ("FICT", "OTHER"))
        self.assertEqual(len(result.occurrences), 5)
        self.assertIn(s.ClaimIssue.CONTRADICTORY_FACTS, result.claims[0].issues)

    def test_symbol_and_no_symbol_conflict(self):
        result = self.extract(facts=security() + fact("NoTradingSymbolFlag", "true"))
        self.assertEqual(result.status, s.ExtractionStatus.SOURCE_CONFLICT)
        self.assertIn(s.ClaimIssue.SYMBOL_AND_NO_SYMBOL, result.claims[0].issues)

    def test_missing_paired_fact_incomplete_retains_occurrences(self):
        for name, value, issue in (("Security12bTitle", "Class A Common Stock, $0.01 par value", s.ClaimIssue.MISSING_TITLE),
                                  ("TradingSymbol", "FICT", s.ClaimIssue.MISSING_SYMBOL_ASSERTION),
                                  ("SecurityExchangeName", "NASDAQ", s.ClaimIssue.MISSING_EXCHANGE)):
            with self.subTest(name=name):
                result = self.extract(facts=security().replace(fact(name, value), ""))
                self.assertEqual(result.status, s.ExtractionStatus.INCOMPLETE_REGISTERED_SECURITY_CLAIMS)
                self.assertIn(issue, result.claims[0].issues)
                self.assertEqual(len(result.occurrences), 2)

    def test_adjacent_html_mismatched_contexts_never_paired(self):
        result = self.extract(contexts=context("c1", member="fiction:AMember") + context("b", member="fiction:BMember"),
                              facts=security().replace(fact("TradingSymbol", "FICT"), fact("TradingSymbol", "FICT", "b")))
        self.assertEqual(result.status, s.ExtractionStatus.INCOMPLETE_REGISTERED_SECURITY_CLAIMS)
        self.assertEqual(len(result.claims), 2)
        self.assertFalse(any(c.titles and c.trading_symbols for c in result.claims))

    def test_equivalent_context_ids_pair_by_exact_aspects(self):
        base = self.extract()
        other = self.extract(contexts=context() + context("equivalent"),
                             facts=security().replace('contextRef="c1"', 'contextRef="equivalent"', 1))
        self.assertEqual(len(other.claims), 1)
        self.assertEqual(other.claims[0].context_refs, ("c1", "equivalent"))
        self.assertEqual(base.semantic_id, other.semantic_id)
        self.assertNotEqual(base.evidence_id, other.evidence_id)

    def test_different_periods_never_paired(self):
        result = self.extract(contexts=context() + context("old", start="2024-01-01", end="2024-12-31"),
                              facts=security().replace(fact("TradingSymbol", "FICT"), fact("TradingSymbol", "FICT", "old")))
        self.assertEqual(result.status, s.ExtractionStatus.INCOMPLETE_REGISTERED_SECURITY_CLAIMS)
        self.assertEqual(len(result.claims), 2)

    def test_wrong_entity_context_conflict_without_changing_envelope_cik(self):
        result = self.extract(contexts=context(cik="0000000099"))
        self.assertEqual(result.status, s.ExtractionStatus.SOURCE_CONFLICT)
        self.assertEqual(result.primary_document.cik, CIK)
        self.assertEqual(result.contexts[0].entity_identifier, "0000000099")

    def test_conflicting_titles_across_exchange_contexts(self):
        result = self.extract(contexts=context("a", exchange="fiction:XMember") + context("b", exchange="fiction:YMember"),
                              facts=security("a") + security("b", title="Other class"))
        self.assertEqual(result.status, s.ExtractionStatus.SOURCE_CONFLICT)
        self.assertTrue(all(s.ClaimIssue.INCONSISTENT_SECURITY_TITLE in c.issues for c in result.claims))

    def test_dimensioned_and_undimensioned_source_scopes_are_ambiguous(self):
        for second in (context("b", member="fiction:AMember"), context("b", exchange="fiction:XMember")):
            result = self.extract(contexts=context() + second, facts=security() + security("b"))
            self.assertEqual(result.status, s.ExtractionStatus.SOURCE_CONFLICT)
            self.assertTrue(all(s.ClaimIssue.AMBIGUOUS_DIMENSION_SCOPE in c.issues for c in result.claims))

    def test_no_supported_facts_is_not_listing_absence(self):
        result = self.extract(facts=fact("DocumentType", "10-K"))
        self.assertEqual(result.status, s.ExtractionStatus.NO_SUPPORTED_REGISTERED_SECURITY_CLAIMS)
        self.assertEqual((result.contexts, result.occurrences, result.claims), ((), (), ()))

    def test_non_inline_document_no_table_heuristics(self):
        self.unsupported(b'<html><body><table><tr><td>Class A</td><td>FICT</td><td>NASDAQ</td></tr></table></body></html>')

    def test_malformed_xml_no_html_recovery(self):
        for raw in (inline().replace(b'</body>', b'</broken>'), inline()[:-8],
                    inline().replace(b'<head>', b'<head><br>'), inline().replace(b'FICT', b'F\x00ICT')):
            self.unsupported(raw)

    def test_duplicate_context_ids_even_identical_rejected(self):
        self.unsupported(inline(contexts=context() + context()))
        self.unsupported(inline(contexts=context() + context(cik="0000000099")))

    def test_unknown_contextref_rejected(self):
        self.unsupported(inline(facts=security("not-present")))

    def test_duplicate_fact_ids_rejected(self):
        self.unsupported(inline(facts=security() + fact("TradingSymbol", "FICT", attrs=' id="f1"') * 2))

    def test_qname_resolution_uses_namespaces_not_prefixes(self):
        base = self.extract()
        renamed = inline().replace(b'xmlns:dei=', b'xmlns:renamed=').replace(b'dei:', b'renamed:')
        result = self.replay(self.capture(filing(payload=renamed)))
        self.assertEqual(base.semantic_id, result.semantic_id)
        self.assertNotEqual(base.evidence_id, result.evidence_id)
        self.assertEqual(result.occurrences[0].source_name, 'renamed:Security12bTitle')

    def test_unreviewed_taxonomy_or_forged_dei_prefix_rejected(self):
        for namespace in (b'https://fiction.invalid/dei', b'http://xbrl.sec.gov/dei/2099'):
            self.unsupported(inline().replace(s.DEI.encode(), namespace))
        self.unsupported(inline().replace(b'xmlns:dei=', b'xmlns:unbound='))

    def test_taxonomy_profiles_are_exact_literal_pairs(self):
        self.assertEqual(s.TAXONOMY_PROFILES, (
            ("http://xbrl.sec.gov/dei/2025", "http://fasb.org/us-gaap/2025"),
            ("http://xbrl.sec.gov/dei/2026", "http://fasb.org/us-gaap/2026"),
        ))

    def test_2026_preserves_2025_claim_values_pairing_and_conflicts(self):
        variants = (
            {},
            dict(facts=security(no_symbol=True)),
            dict(contexts=context("a", member="fiction:AMember") + context("b", member="fiction:BMember"),
                 facts=security("a") + security("b")),
            dict(contexts=context("a", member="fiction:AMember", exchange="fiction:XMember")
                 + context("b", member="fiction:AMember", exchange="fiction:YMember"),
                 facts=security("a") + security("b", exchange="OTHER", symbol="FICT2")),
            dict(facts=security() + security() + fact("TradingSymbol", "OTHER")),
            dict(facts=fact("Security12bTitle", "Unpaired source title")),
        )
        for variant in variants:
            with self.subTest(variant=variant):
                old_raw = inline(**variant)
                new_raw = old_raw.replace(b'http://xbrl.sec.gov/dei/2025', b'http://xbrl.sec.gov/dei/2026').replace(
                    b'http://fasb.org/us-gaap/2025', b'http://fasb.org/us-gaap/2026')
                old = self.replay(self.capture(filing(payload=old_raw)))
                new = self.replay(self.capture(filing(payload=new_raw)))
                self.assertEqual(old.status, new.status)
                # Namespace identity remains intentional source semantics; no production normalization.
                self.assertNotEqual(old.semantic_id, new.semantic_id)
                self.assertNotEqual(old.evidence_id, new.evidence_id)
                def claims_by_context(result):
                    return {c.context_refs: (c.titles, c.trading_symbols, c.no_trading_symbol_flags,
                                            c.exchange_names, c.issues, len(c.occurrence_ids)) for c in result.claims}
                self.assertEqual(claims_by_context(old), claims_by_context(new))
                self.assertEqual(len({c.source_security_scope_id for c in old.claims}),
                                 len({c.source_security_scope_id for c in new.claims}))
                for old_fact, new_fact in zip(old.occurrences, new.occurrences, strict=True):
                    self.assertEqual(new_fact.fact_name, old_fact.fact_name.replace(
                        'http://xbrl.sec.gov/dei/2025', 'http://xbrl.sec.gov/dei/2026'))
                    for field in ('source_name', 'source_value', 'context_ref', 'source_fact_id',
                                  'language', 'element_ordinal', 'source_line'):
                        self.assertEqual(getattr(old_fact, field), getattr(new_fact, field))
                self.assertEqual(new.primary_document.content_sha256, hashlib.sha256(new_raw).hexdigest())

    def test_mixed_2025_dei_2026_gaap_fails_closed(self):
        for ctx in (context(), context(member="fiction:AMember", exchange="fiction:XMember")):
            self.unsupported(inline(contexts=ctx).replace(
                b'http://fasb.org/us-gaap/2025', b'http://fasb.org/us-gaap/2026'))

    def test_mixed_2026_dei_2025_gaap_fails_closed(self):
        for ctx in (context(), context(member="fiction:AMember", exchange="fiction:XMember")):
            self.unsupported(inline(contexts=ctx).replace(
                b'http://xbrl.sec.gov/dei/2025', b'http://xbrl.sec.gov/dei/2026'))

    def test_mixed_generations_in_nested_namespace_scopes_fail_closed(self):
        for namespace in ('http://xbrl.sec.gov/dei/2026', 'http://fasb.org/us-gaap/2026'):
            self.unsupported(inline(extra=f'<div xmlns:other="{namespace}"/>'))
        other_fact = fact('TradingSymbol', 'FICT', attrs=' xmlns:dei="http://xbrl.sec.gov/dei/2026"')
        self.unsupported(inline(facts=security() + other_fact))
        other_context = context('b', member='fiction:BMember').replace(
            '<xbrli:context ', '<xbrli:context xmlns:us-gaap="http://fasb.org/us-gaap/2026" ')
        self.unsupported(inline(contexts=context() + other_context, facts=security() + security('b')))

    def test_unknown_taxonomy_years_fail_closed_even_without_class_dimension(self):
        for namespace in (b'http://xbrl.sec.gov/dei/2025', b'http://fasb.org/us-gaap/2025'):
            for year in (b'2027', b'2099', b'2024'):
                self.unsupported(inline().replace(namespace, namespace[:-4] + year))
        self.unsupported(inline().replace(b'http://xbrl.sec.gov/dei/2025', b'http://xbrl.sec.gov/dei/2099').replace(
            b'http://fasb.org/us-gaap/2025', b'http://fasb.org/us-gaap/2099'))

    def test_2026_profile_uses_namespace_uris_not_prefix_spelling(self):
        raw = inline(contexts=context(member='fiction:AMember', exchange='fiction:XMember')).replace(
            b'http://xbrl.sec.gov/dei/2025', b'http://xbrl.sec.gov/dei/2026').replace(
            b'http://fasb.org/us-gaap/2025', b'http://fasb.org/us-gaap/2026')
        renamed = raw.replace(b'xmlns:dei=', b'xmlns:d=').replace(b'dei:', b'd:').replace(
            b'xmlns:us-gaap=', b'xmlns:g=').replace(b'us-gaap:', b'g:')
        original = self.replay(self.capture(filing(payload=raw)))
        result = self.replay(self.capture(filing(payload=renamed)))
        self.assertEqual(result.status, s.ExtractionStatus.CAPTURED_REGISTERED_SECURITY_CLAIMS)
        self.assertEqual(original.semantic_id, result.semantic_id)
        self.assertNotEqual(original.evidence_id, result.evidence_id)

    def test_unreviewed_dimensions_and_typed_members_rejected(self):
        raw = inline(contexts=context(member="fiction:AMember"))
        self.unsupported(raw.replace(b'us-gaap:StatementClassOfStockAxis', b'fiction:UnknownAxis'))
        self.unsupported(raw.replace(b'explicitMember', b'typedMember'))
        self.unsupported(raw.replace(b'fiction:AMember', b'unknown:AMember'))

    def test_duplicate_dimension_rejected(self):
        ctx = context(member="fiction:AMember")
        dimension = '<xbrldi:explicitMember dimension="us-gaap:StatementClassOfStockAxis">fiction:BMember</xbrldi:explicitMember>'
        self.unsupported(inline(contexts=ctx.replace('</xbrli:segment>', dimension + '</xbrli:segment>')))

    def test_context_scenario_instant_and_invalid_dates_rejected(self):
        self.unsupported(inline(contexts=context().replace('</xbrli:context>', '<xbrli:scenario/></xbrli:context>')))
        self.unsupported(inline(contexts=context().replace('<xbrli:startDate>2025-01-01</xbrli:startDate>', '').replace('endDate', 'instant')))
        for start, end in (("2025-02-30", "2025-12-31"), ("2026-01-01", "2025-12-31"),
                           ("2025-01-01Z", "2025-12-31")):
            self.unsupported(inline(contexts=context(start=start, end=end)))

    def test_context_mixed_content_and_displaced_resources_rejected(self):
        self.unsupported(inline(contexts=context().replace('<xbrli:entity>', '<xbrli:entity>unmodeled')))
        self.unsupported(inline(contexts=context(member="fiction:AMember").replace(
            '<xbrli:segment>', '<xbrli:segment>unmodeled')))
        self.unsupported(inline().replace(b'<ix:resources>', b'<div><ix:resources>').replace(
            b'</ix:resources>', b'</ix:resources></div>'))
        self.unsupported(inline(extra='<ix:header><ix:resources/></ix:header>'))
        self.unsupported(inline(contexts="", extra=context()))

    def test_comments_cannot_hide_context_leaf_text(self):
        self.unsupported(inline(contexts=context().replace('2025-01-01</xbrli:startDate>',
            '2025-01-01<!--comment-->hidden</xbrli:startDate>')))
        self.unsupported(inline(contexts=context().replace(CIK + '</xbrli:identifier>',
            CIK + '<!--comment-->99</xbrli:identifier>')))
        split_identifier = context().replace(CIK + '</xbrli:identifier>',
            CIK[:5] + '<!--comment-->' + CIK[5:] + '</xbrli:identifier>')
        result = self.extract(contexts=split_identifier)
        self.assertEqual(result.contexts[0].entity_identifier, CIK)

    def test_non_inline_fact_and_multiple_targets_rejected(self):
        self.unsupported(inline(extra='<dei:TradingSymbol contextRef="c1">OTHER</dei:TradingSymbol>'))
        self.unsupported(inline(extra='<ix:nonNumeric name="dei:DocumentType" contextRef="c1" target="foreign">10-K</ix:nonNumeric>'))

    def test_non_utf8_or_alternate_encoding_declaration_rejected(self):
        self.unsupported(inline().replace(b'FICT', b'F\xffICT'))
        self.unsupported(b'<?xml version="1.0" encoding="ISO-8859-1"?>' + inline())
        self.unsupported(inline().decode().encode('utf-16'))

    def test_plain_source_strings_do_not_read_embedded_urls(self):
        text = 'https://fiction.invalid/claim file:///etc/passwd $(echo hidden)'
        result = self.extract(facts=security(title=text, exchange='Unmapped Exchange'))
        self.assertEqual(result.claims[0].titles, (text,))
        self.assertEqual(result.claims[0].exchange_names, ('Unmapped Exchange',))

    def test_unsupported_fact_value_mechanisms_fail_closed(self):
        for attrs in (' format="dei:Unknown"', ' continuedAt="elsewhere"', ' escape="true"',
                      ' xsi:nil="true"', ' tupleRef="tuple1"', ' target="other"'):
            self.unsupported(inline(facts=security() + fact("TradingSymbol", "FICT", attrs=attrs)))
        for markup in ('F<ix:exclude>not part</ix:exclude>ICT', fact("TradingSymbol", "FICT"),
                       '<script>FICT</script>', '<style>FICT</style>'):
            self.unsupported(inline(facts=fact("Security12bTitle", markup, markup=True)))

    def test_unicode_whitespace_and_inline_markup_source_preserved(self):
        title = '  Société e\u0301 & Δ – "Class A" \u00a0 '
        result = self.extract(facts=security(title=title))
        self.assertEqual(result.claims[0].titles, (title,))
        markup = fact("Security12bTitle", '  Société <b>e\u0301</b> &amp; Δ  ', markup=True)
        result = self.extract(facts=security().replace(fact("Security12bTitle", "Class A Common Stock, $0.01 par value"), markup))
        self.assertEqual(result.claims[0].titles, ('  Société e\u0301 & Δ  ',))

    def test_instrument_words_are_never_classified(self):
        for title in ("Common Stock", "Preferred Stock", "ADR", "Warrant", "Fund Units", "Unknown"):
            result = self.extract(facts=security(title=title))
            self.assertEqual(result.claims[0].titles, (title,))
            self.assertNotIn("instrument_type", asdict(result.claims[0]))

    def test_source_language_and_fact_id_preserved(self):
        result = self.extract(facts=security() + fact("TradingSymbol", "FICT", attrs=' id="fact1" xml:lang="en-US"'))
        self.assertEqual(result.occurrences[-1].source_fact_id, "fact1")
        self.assertEqual(result.occurrences[-1].language, "en-US")

    def test_empty_and_oversized_values_rejected(self):
        for text in ("", "  ", "X" * (s.MAX_VALUE_LENGTH + 1)):
            self.unsupported(inline(facts=security(symbol=text)))

    def test_resource_bounds(self):
        for constant, limit in (("MAX_ELEMENTS", 3), ("MAX_CONTEXTS", 0), ("MAX_FACTS", 2), ("MAX_VALUE_LENGTH", 2)):
            with patch.object(s, constant, limit):
                self.unsupported(inline())

    def test_dtd_external_entities_never_resolved(self):
        for prefix in (b'<!DOCTYPE html SYSTEM "file:///etc/passwd">',
                       b'<!DOCTYPE html SYSTEM "https://fiction.invalid/remote.dtd">',
                       b'<!DOCTYPE html [<!ENTITY secret SYSTEM "file:///etc/passwd">]>',
                       b'<!DOCTYPE html [<!ENTITY a "xxxxxxxx"><!ENTITY b "&a;&a;">]>'):
            self.unsupported(prefix + inline())
        self.unsupported(inline().replace(b'FICT', b'&undefined;'))

    def test_external_references_and_scripts_inert_no_io(self):
        extra = ('<script src="https://fiction.invalid/script.js">throw new Error("executed")</script>'
                 '<img src="file:///etc/passwd"/><link href="https://fiction.invalid/css"/>'
                 '<xi:include xmlns:xi="http://www.w3.org/2001/XInclude" href="file:///etc/passwd"/>'
                 '<a href="https://fiction.invalid/filing">external reference</a>')
        receipt = self.capture(submission(extra=extra))
        real_open = os.open
        opens = []
        def read_only(path, flags, *args, **kwargs):
            self.assertEqual(flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND), 0)
            opens.append(str(path))
            return real_open(path, flags, *args, **kwargs)
        with ExitStack() as stack:
            stack.enter_context(patch('os.open', side_effect=read_only))
            for target in ('socket.socket', 'socket.getaddrinfo', 'urllib.request.urlopen',
                           'os.mkdir', 'os.listdir', 'os.scandir', 'os.link', 'os.unlink',
                           'time.time', 'time.monotonic', 'time.perf_counter',
                           'pathlib.Path.write_bytes', 'pathlib.Path.write_text'):
                stack.enter_context(patch(target, side_effect=AssertionError(target)))
            stack.enter_context(patch.object(a.SecFilingArchive, '_capture_live', side_effect=AssertionError('write')))
            stack.enter_context(patch.object(a, 'datetime', wraps=a.datetime))
            a.datetime.now.side_effect = AssertionError('clock')
            a.datetime.utcnow.side_effect = AssertionError('clock')
            result = self.replay(receipt)
            self.assertEqual(result.status, s.ExtractionStatus.CAPTURED_REGISTERED_SECURITY_CLAIMS)
            self.assertEqual(len(result.evidence_id), 64)
        self.assertNotIn('passwd', opens)

    def test_identical_recapture_semantics_stable_evidence_changes(self):
        first, second = self.replay(self.capture()), self.replay(self.capture(captured_at=T2))
        self.assertEqual(first.semantic_id, second.semantic_id)
        self.assertNotEqual(first.evidence_id, second.evidence_id)
        self.assertNotEqual(first.occurrences[0].occurrence_id, second.occurrences[0].occurrence_id)

    def test_fact_order_deterministic_semantics_occurrence_order_retained(self):
        first = self.extract()
        reversed_facts = fact("SecurityExchangeName", "NASDAQ") + fact("TradingSymbol", "FICT") + fact("Security12bTitle", "Class A Common Stock, $0.01 par value")
        second = self.extract(facts=reversed_facts)
        self.assertEqual(first.semantic_id, second.semantic_id)
        self.assertNotEqual(first.evidence_id, second.evidence_id)
        self.assertNotEqual(first.occurrences[0].fact_name, second.occurrences[0].fact_name)
        self.assertEqual(first, self.replay(first.receipt))

    def test_context_order_and_dimension_order_semantics_stable(self):
        c1, c2 = context("a", member="fiction:AMember"), context("b", member="fiction:BMember")
        first = self.extract(contexts=c1+c2, facts=security("a")+security("b"))
        second = self.extract(contexts=c2+c1, facts=security("b")+security("a"))
        self.assertEqual(first.semantic_id, second.semantic_id)
        self.assertEqual([c.context_semantic_id for c in first.claims], sorted(c.context_semantic_id for c in first.claims))
        ctx = context(member="fiction:AMember", exchange="fiction:XMember")
        start, rest = ctx.split('<xbrli:segment>')
        dim, end = rest.split('</xbrli:segment>')
        pieces = [p + '</xbrldi:explicitMember>' for p in dim.split('</xbrldi:explicitMember>')[:-1]]
        first = self.extract(contexts=ctx)
        second = self.extract(contexts=start+'<xbrli:segment>'+''.join(reversed(pieces))+'</xbrli:segment>'+end)
        self.assertEqual(first.semantic_id, second.semantic_id)
        self.assertNotEqual(first.evidence_id, second.evidence_id)

    def test_formatting_changes_only_evidence_without_source_string_changes(self):
        first = self.extract()
        raw = submission().replace(b'><', b'>\n<')
        second = self.replay(self.capture(raw))
        self.assertEqual(first.semantic_id, second.semantic_id)
        self.assertNotEqual(first.evidence_id, second.evidence_id)
        changed_value = self.extract(facts=security(title=" Class A Common Stock, $0.01 par value"))
        self.assertNotEqual(first.semantic_id, changed_value.semantic_id)

    def test_primary_exact_bytes_crlf_and_opaque_exhibits(self):
        raw = filing(payload=inline() + b'\n', extra=document("EX-99", "2", "opaque.bin", b'\xff\x01'))
        raw = raw.replace(b'\n', b'\r\n')
        result = self.replay(self.capture(raw))
        p = result.primary_document
        self.assertEqual(raw[p.byte_start:p.byte_start+p.byte_length], inline() + b'\r\n')
        self.assertEqual(p.content_sha256, hashlib.sha256(inline() + b'\r\n').hexdigest())
        self.assertEqual(len(result.occurrences), 3)

    def test_envelope_selectors_count_and_primary_ambiguity_rejected(self):
        raws = (filing(cik="0000000099", payload=inline()),
                filing(accession="0000000001-26-000099", payload=inline()),
                submission().replace(b'PUBLIC DOCUMENT COUNT:\t\t1', b'PUBLIC DOCUMENT COUNT:\t\t2'),
                filing(payload=inline(), extra=document("10-K", "2", "other.htm", inline())),
                submission().replace(b'<SEQUENCE>1', b'<SEQUENCE>0'),
                submission().replace(b'<FILENAME>fictional.htm', b'<FILENAME>../fictional.htm'),
                submission().replace(b'FILER:', b'SUBJECT COMPANY:'),
                submission().replace(b'\t\tCENTRAL INDEX KEY:\t' + CIK.encode() + b'\n', b'').replace(
                    b'\tBUSINESS ADDRESS:\n', b'\tBUSINESS ADDRESS:\n\t\tCENTRAL INDEX KEY:\t' + CIK.encode() + b'\n'),
                submission().replace(b'\tCOMPANY DATA:', b'\tUNKNOWN DATA:'),
                submission().replace(b'FILER:', b'UNKNOWN TOP: field\nFILER:'),
                submission().replace(b'</TEXT>', b'</MISSING>'))
        for raw in raws:
            with self.subTest(raw=raw[:30]), self.assertRaises(s.UnsupportedRegisteredSecuritySource):
                self.replay(self.capture(raw))

    def test_no_primary_fallback_to_exhibit(self):
        with self.assertRaises(s.UnsupportedRegisteredSecuritySource):
            self.replay(self.capture(filing(extra=document("EX-99", "2", "supported.htm", inline()))))

    def test_paths_never_enter_identities(self):
        receipt = self.capture()
        first = self.replay(receipt)
        archive = a.SecFilingArchive(self.root.parent / "second")
        archive._capture_live(submission(), cik=CIK, accession=ACCESSION, captured_at=T1)
        second = s.extract_sec_registered_security_claims(archive, s.SecRegisteredSecurityExtractionRequest(receipt.receipt_id))
        self.assertEqual(first.semantic_id, second.semantic_id)
        self.assertEqual(first.evidence_id, second.evidence_id)

    def test_actual_extraction_cannot_enter_d1_c4_or_expected_return(self):
        from economic_facts.sec_current_evidence import assess_sec_current_evidence
        from economic_facts.current_authority import CurrentAuthorityError
        from economic_facts.security_identity import qualify_security_identity, IdentityContractError
        from src.expected_return_assumptions import construct_expected_return
        from src.expected_return_policy import ConstructorContractError
        from src.expected_return_engine import calculate_expected_return, ExpectedReturnError
        result = self.extract()
        with self.assertRaises(CurrentAuthorityError):
            assess_sec_current_evidence(self.archive, result)
        with self.assertRaises(IdentityContractError):
            qualify_security_identity(result, result, result)
        with self.assertRaises(ConstructorContractError):
            construct_expected_return(result)
        with self.assertRaises(ExpectedReturnError):
            calculate_expected_return(result)


class RegisteredSecurityBoundaryTests(unittest.TestCase):
    def test_exact_dependency_direction_no_nasdaq_d2b_d1_c4_or_model_consumers(self):
        root = Path(__file__).resolve().parents[1]
        module = root / 'economic_facts/sec_registered_securities.py'
        allowed = {'dataclasses', 'datetime', 'enum', 're', 'lxml'}
        for node in ast.walk(ast.parse(module.read_text())):
            if isinstance(node, ast.Import):
                self.assertTrue(all(n.name in allowed for n in node.names))
            if isinstance(node, ast.ImportFrom):
                self.assertTrue((node.level == 1 and node.module in
                                 {'sec_filing_archive', 'sec_primary_document'}) or
                                (node.level == 0 and node.module in allowed))
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                self.assertNotIn(node.func.id, {'open', 'float', 'eval', 'exec', '__import__'})
        for file in [root / 'main.py', *(root / 'src').rglob('*.py'), *(root / 'economic_facts').rglob('*.py'),
                     *(root / 'pit_comparison').rglob('*.py'), *(root / 'scripts').rglob('*.py')]:
            if file in {module, root / 'economic_facts/sec_primary_document.py'}:
                continue
            self.assertNotIn('sec_registered_securities', file.read_text(), str(file))

    def test_no_authority_status_or_economic_output_fields(self):
        self.assertEqual({v.value for v in s.ExtractionStatus}, {
            'CAPTURED_REGISTERED_SECURITY_CLAIMS', 'INCOMPLETE_REGISTERED_SECURITY_CLAIMS',
            'SOURCE_CONFLICT', 'NO_SUPPORTED_REGISTERED_SECURITY_CLAIMS'})
        for record in (s.SecRegisteredSecurityExtractionAssessment, s.RegisteredSecurityContextClaims,
                       s.RegisteredSecurityFactOccurrence, s.SourceContext):
            self.assertFalse(set(record.__dataclass_fields__) & {
                'qualified', 'admitted', 'authority', 'as_of', 'quote_currency', 'instrument_type',
                'issuer_identity', 'security_identity', 'listing_identity', 'eps', 'established_claims'})

    def test_extractor_request_not_accepted_by_d1_or_c4(self):
        from economic_facts.sec_current_evidence import assess_sec_current_evidence
        from economic_facts.current_authority import CurrentAuthorityError
        from economic_facts.security_identity import qualify_security_identity, IdentityContractError
        request = s.SecRegisteredSecurityExtractionRequest('0' * 64)
        with self.assertRaises(CurrentAuthorityError):
            assess_sec_current_evidence(None, request)
        with self.assertRaises(IdentityContractError):
            qualify_security_identity(request, request, request)

    def test_documented_all_property_4_and_remaining_obligations_unresolved(self):
        text = (Path(__file__).resolve().parents[1] / 'EXPECTED_RETURN_PR4D3A.md').read_text()
        for obligation in ('4A', '4B', '4C', '4D', '4E', '4F', '4G', '4H'):
            self.assertIn('| ' + obligation + ' |', text)
        self.assertIn('Obligations 5–7 remain unresolved', text)


if __name__ == '__main__':
    unittest.main()
