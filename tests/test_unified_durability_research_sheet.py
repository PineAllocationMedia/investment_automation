"""Fictional financial captures and narrative only; synthetic mechanics, not SEC proof."""
import ast
from copy import deepcopy
from dataclasses import asdict, replace
from decimal import localcontext, Inexact, Rounded, FloatOperation
import hashlib
from html import escape
from html.parser import HTMLParser
import inspect
import json
import os
from pathlib import Path
import pickle
import socket
from unittest.mock import patch

from economic_facts.sec_archive import ArchiveError, SecArchive
from economic_facts.sec_revenue_operating_income import CONCEPTS
from src import unified_durability_research_sheet as sheet
from src import qualitative_durability_research_note as manual
from tests.sec_d1_two_period_fixtures import D1Fixture, comparative, payload, row, OTHER, a
from tests.test_qualitative_durability_research_note import fictional_note


class SheetHTML(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.tags = []
        self.section_stack = []
        self.text = {key: [] for key in ('financial', 'qualitative', 'synthesis')}
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        self.tags.append((tag, attrs))
        if tag == 'section':
            self.section_stack.append(attrs.get('id', self.section_stack[-1] if self.section_stack else None))

    def handle_endtag(self, tag):
        if tag == 'section':
            self.section_stack.pop()

    def handle_data(self, value):
        if self.section_stack and self.section_stack[-1] in self.text:
            self.text[self.section_stack[-1]].append(value)


class UnifiedResearchSheetTests(D1Fixture):
    def render(self, source=None, note=None, **kwargs):
        return sheet.render_unified_durability_research_sheet_v1(self.evaluate(source, **kwargs), note)

    def assert_failure(self, html):
        financial = ''.join(SheetHTML(html).text['financial'])
        self.assertIn('INTEGRITY_FAILURE', financial)
        self.assertIn('not UNAVAILABLE', financial)
        self.assertNotIn('<table>', html)
        self.assertNotIn('Native Contract A evidence identity', financial)
        return financial

    def test_complete_fictional_financial_context_and_distinct_identities(self):
        q = self.evaluate()
        first = sheet.d1.analyze_d1_two_period_operating_profit_continuity_v1(q)
        second = sheet.d2.analyze_d2_two_period_reported_trajectory_v1(q)
        html = sheet.render_unified_durability_research_sheet_v1(q, fictional_note())
        parsed = SheetHTML(html)
        financial = ''.join(parsed.text['financial'])
        for value in (q.source_cik, 'US_GAAP', 'USD', q.captured_at,
                      q.prior_period_start, q.prior_period_end, q.current_period_start,
                      q.current_period_end, '80', '10', '100', '20', 'POSITIVE',
                      'POSITIVE_IN_BOTH_PERIODS', '1 / 8', '1 / 5', '3 / 40', '1 / 4', 'INCREASED',
                      q.semantic_id, q.evidence_id, first.semantic_id, first.evidence_id,
                      second.semantic_id, second.evidence_id, q.capture_receipt_id, q.source_object_hash):
            self.assertIn(value, financial)
        self.assertIn('Native Contract A evidence identity', financial)
        self.assertIn('Analytical evidence identity', financial)
        self.assertIn('Native qualification reasons', financial)
        self.assertIn('Analytical reasons', financial)
        self.assertIn('Upstream reasons', financial)
        self.assertEqual(financial.count(q.evidence_id), 3)

    def test_one_valid_standalone_document_three_distinct_primary_sections(self):
        html = self.render(note=fictional_note())
        parsed = SheetHTML(html)
        for tag in ('html', 'head', 'body'):
            self.assertEqual(sum(name == tag for name, attrs in parsed.tags), 1)
        self.assertEqual(html.count('<!doctype html>'), 1)
        self.assertEqual([attrs['id'] for tag, attrs in parsed.tags if tag == 'section' and 'id' in attrs],
                         ['financial', 'qualitative', 'synthesis'])
        self.assertFalse(parsed.section_stack)

    def test_financial_analyzers_derive_from_same_reconstructed_bound_input(self):
        q = self.evaluate()
        first = sheet.d1.analyze_d1_two_period_operating_profit_continuity_v1
        second = sheet.d2.analyze_d2_two_period_reported_trajectory_v1
        with (patch.object(sheet.d1, 'analyze_d1_two_period_operating_profit_continuity_v1', wraps=first) as d1,
              patch.object(sheet.d2, 'analyze_d2_two_period_reported_trajectory_v1', wraps=second) as d2,
              patch.object(a, '_qualify_extraction', wraps=a._qualify_extraction) as replay):
            html = sheet.render_unified_durability_research_sheet_v1(q)
        self.assertIn('<table>', html)
        self.assertEqual(replay.call_count, 3)
        self.assertIs(d1.call_args.args[0], d2.call_args.args[0])
        self.assertIsNot(d1.call_args.args[0], q)

    def test_other_legitimate_recapture_cannot_supply_paired_diagnostic(self):
        q = self.evaluate()
        other = self.evaluate(timestamp='2025-08-02T00:00:00Z')
        result = sheet.d2.analyze_d2_two_period_reported_trajectory_v1(other)
        self.assertEqual(q.semantic_id, other.semantic_id)
        self.assertNotEqual(q.evidence_id, other.evidence_id)
        with patch.object(sheet.d2, 'analyze_d2_two_period_reported_trajectory_v1', return_value=result):
            html = sheet.render_unified_durability_research_sheet_v1(q)
        self.assert_failure(html)
        self.assertNotIn(other.evidence_id, html)

    def test_other_issuer_source_cannot_be_paired(self):
        q = self.evaluate()
        source = comparative()
        source['cik'] = 42
        receipt = self.archive._capture_live(json.dumps(source).encode(), cik='0000000042',
                                             captured_at='2025-08-01T00:00:00Z')
        other = a.qualify_sec_current_annual_issuer_two_period_revenue_operating_income_v1(
            self.archive, receipt.receipt_id)
        result = sheet.d2.analyze_d2_two_period_reported_trajectory_v1(other)
        with patch.object(sheet.d2, 'analyze_d2_two_period_reported_trajectory_v1', return_value=result):
            self.assert_failure(sheet.render_unified_durability_research_sheet_v1(q))

    def test_reporting_context_and_status_mismatch_fail_closed(self):
        q = self.evaluate()
        original = sheet.d2.analyze_d2_two_period_reported_trajectory_v1(q)
        for result in (replace(original, source_cik='0000000042'),
                       replace(original, prior_period_start='2022-01-01'),
                       replace(original, status=sheet.d2.S.UNAVAILABLE), {}, None):
            with patch.object(sheet.d2, 'analyze_d2_two_period_reported_trajectory_v1', return_value=result):
                self.assert_failure(sheet.render_unified_durability_research_sheet_v1(q))

    def test_forged_detached_financial_dicts_and_analytical_results_refused(self):
        q = self.evaluate()
        forged = replace(q)
        object.__setattr__(forged, '_archive_replay_binding', q._archive_replay_binding)
        object.__setattr__(forged, 'source_cik', '0000000042')
        values = ({}, None, True, asdict(q), replace(q), deepcopy(q), pickle.loads(pickle.dumps(q)),
                  forged, sheet.d1.analyze_d1_two_period_operating_profit_continuity_v1(q),
                  sheet.d2.analyze_d2_two_period_reported_trajectory_v1(q))
        for value in values:
            with self.subTest(type=type(value)):
                self.assert_failure(sheet.render_unified_durability_research_sheet_v1(value))
        with self.assertRaises(TypeError):
            sheet.render_unified_durability_research_sheet_v1(q, d1_result=values[-2])

    def test_all_nonestablished_states_suppress_financial_values_and_periods(self):
        conflict = comparative()
        conflict['facts']['us-gaap'][CONCEPTS[0]]['units']['USD'].append(row(999, accn=OTHER))
        for source, status in ((payload(), 'UNAVAILABLE'), (comparative(fp='Q4'), 'UNSUPPORTED'),
                                (conflict, 'SOURCE_CONFLICT')):
            q = self.evaluate(source)
            html = sheet.render_unified_durability_research_sheet_v1(q)
            financial = ''.join(SheetHTML(html).text['financial'])
            self.assertIn(status, financial)
            self.assertNotIn('INTEGRITY_FAILURE', financial)
            self.assertNotIn('<table>', html)
            self.assertNotIn('<dd>INCREASED</dd>', html)
            self.assertNotIn('<dd>UNCHANGED</dd>', html)
            self.assertNotIn('<dd>POSITIVE</dd>', html)
            for reason in q.reasons:
                self.assertIn(reason.value, financial)
            self.assertIn('No comparative financial facts or periods are established', financial)

    def test_not_applicable_preserves_d1_signs_but_no_ratios_or_d2_trajectory(self):
        for r0 in (0, -80, 80):
            for r1 in (0, -100, 100):
                if r0 > 0 and r1 > 0:
                    continue
                html = self.render(comparative(r0, -1, r1, 0))
                financial = ''.join(SheetHTML(html).text['financial'])
                self.assertEqual(html.count('<dd>NOT_APPLICABLE</dd>'), 2)
                self.assertIn('<table>', html)
                self.assertIn('NEGATIVE', financial)
                self.assertIn('ZERO', financial)
                self.assertIn('POSITIVE_IN_NEITHER_PERIOD', financial)
                for label in ('Ratio direction', 'Revenue direction', 'Operating Income direction',
                              'Relative Revenue change (exact rational)'):
                    self.assertIn(escape(label) + '</dt><dd>NOT PROVIDED</dd>', html)
                self.assertNotIn('1 / ', financial)

    def test_missing_and_altered_archive_failures_do_not_become_unavailable(self):
        for source in (comparative(), comparative(r0=0), payload(), comparative(fp='Q4')):
            for change in ('object_missing', 'object_altered', 'receipt_missing'):
                q = self.evaluate(source)
                path = self.root / 'objects' / q.source_object_hash
                receipt = self.root / 'receipts' / (q.capture_receipt_id + '.json')
                if change == 'object_missing':
                    path.unlink()
                elif change == 'object_altered':
                    raw = path.read_bytes()
                    path.unlink()
                    path.write_bytes(raw + b' ')
                    path.chmod(0o400)
                else:
                    receipt.unlink()
                html = sheet.render_unified_durability_research_sheet_v1(q, fictional_note())
                self.assert_failure(html)
                self.assertNotIn(str(self.root), html)
                self.assertIn('Fictional Lantern Systems', html)
                if path.exists():
                    path.unlink()

    def test_native_integrity_exception_text_is_not_rendered(self):
        q = self.evaluate()
        with patch.object(a, '_verified_comparative_snapshot', side_effect=ArchiveError('<script>private-path</script>')):
            html = sheet.render_unified_durability_research_sheet_v1(q)
        self.assert_failure(html)
        self.assertNotIn('private-path', html)

    def test_missing_manual_content_and_conclusion_remain_not_provided(self):
        html = self.render()
        parsed = SheetHTML(html)
        self.assertIn('Research items: NOT PROVIDED', ''.join(parsed.text['qualitative']))
        self.assertIn('NOT PROVIDED', ''.join(parsed.text['synthesis']))
        self.assertIn('UNREVIEWED', ''.join(parsed.text['qualitative']))
        self.assertNotIn('OPERATOR_REVIEWED', html)

    def test_manual_review_matching_names_and_references_do_not_authenticate_join(self):
        q = self.evaluate()
        note = replace(fictional_note(), issuer_name=q.source_cik, issuer_reference=q.source_cik)
        html = sheet.render_unified_durability_research_sheet_v1(q, note)
        qualitative = ''.join(SheetHTML(html).text['qualitative'])
        for marker in ('OPERATOR_REVIEWED', 'MANUAL_RESEARCH_ONLY', 'NOT_NATIVE_EVIDENCE_ADMISSION',
                       'CURRENT_CAPTURE_BOUND_ONLY', 'not independently authenticated',
                       'not automatically independent corroboration'):
            self.assertIn(marker, qualitative)
        self.assertIn('no native narrative receipt', qualitative)
        self.assertNotIn(q.evidence_id, qualitative)

    def test_manual_conclusion_appears_only_in_synthesis_never_generated(self):
        note = fictional_note()
        html = self.render(note=note)
        parsed = SheetHTML(html)
        self.assertNotIn(note.research_conclusion, ''.join(parsed.text['qualitative']))
        self.assertIn(note.research_conclusion, ''.join(parsed.text['synthesis']))
        self.assertEqual(html.count(escape(note.research_conclusion)), 1)

    def test_hostile_operator_text_is_inert_and_document_security_retained(self):
        attack = '<script>alert("x")</script><img src="https://bad.invalid/x" onerror="x">'
        source = manual.ManualSourceReferenceV1(locator='javascript:alert(1)', section_location=attack)
        note = replace(fictional_note(), issuer_name=attack, research_conclusion=attack,
                       items=(manual.QualitativeResearchItemV1(source=source, issuer_statement=attack),))
        html = self.render(note=note)
        parsed = SheetHTML(html)
        self.assertNotIn(attack, html)
        self.assertIn(escape(attack), html)
        self.assertFalse(any(tag in ('script', 'img', 'iframe', 'a', 'object', 'form') for tag, attrs in parsed.tags))
        self.assertFalse(any(k.startswith('on') or k in ('src', 'href') for tag, attrs in parsed.tags for k in attrs))
        self.assertTrue(any(tag == 'meta' and attrs.get('http-equiv') == 'Content-Security-Policy'
                            and "default-src 'none'" in attrs['content'] for tag, attrs in parsed.tags))

    def test_exact_fractional_decimal_render_under_hostile_context(self):
        raw = json.dumps(comparative()).encode()
        for old, new in ((b'"val": 80', b'"val": 3.000'), (b'"val": 100', b'"val": 0.750'),
                         (b'"val": 10', b'"val": -0.125'), (b'"val": 20', b'"val": 0.125')):
            raw = raw.replace(old, new)
        q = self.evaluate(raw=raw)
        normal = sheet.render_unified_durability_research_sheet_v1(q)
        with localcontext() as ctx:
            ctx.prec = 1
            for signal in (Inexact, Rounded, FloatOperation):
                ctx.traps[signal] = True
            hostile = sheet.render_unified_durability_research_sheet_v1(q)
        self.assertEqual(normal, hostile)
        for value in ('3.000', '0.750', '-0.125', '-1 / 24', '1 / 6', '5 / 24', '-3 / 4'):
            self.assertIn(value, normal)

    def test_read_only_replay_no_network_capture_or_persistence_and_deterministic_output(self):
        q = self.evaluate()
        note = fictional_note()
        before = {str(p.relative_to(self.root)): p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        original_open = os.open
        def read_only_open(path, flags, *args, **kwargs):
            self.assertFalse(flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND))
            return original_open(path, flags, *args, **kwargs)
        with (patch.object(os, 'open', side_effect=read_only_open),
              patch.object(socket, 'socket', side_effect=AssertionError('network')),
              patch.object(SecArchive, '_capture', side_effect=AssertionError('capture')),
              patch.object(Path, 'write_bytes', side_effect=AssertionError('write')),
              patch.object(Path, 'write_text', side_effect=AssertionError('write'))):
            first = sheet.render_unified_durability_research_sheet_v1(q, note)
            second = sheet.render_unified_durability_research_sheet_v1(q, note)
        self.assertEqual(first, second)
        self.assertEqual(before, {str(p.relative_to(self.root)): p.read_bytes() for p in self.root.rglob('*') if p.is_file()})

    def test_qualitative_fragment_and_byte_exact_existing_standalone_regression(self):
        for note, expected in ((manual.QualitativeDurabilityResearchNoteV1(),
                               'bdeddee2b365f86984dc88d6e1d72a9590ab5ecb0d5361061bd4059fa2d27c75'),
                              (fictional_note(), '68bab2d6d3259d1dca7e23f208c467cd2dd6a4e13f5c72674cae980329ad3019')):
            # Mechanical HTML baseline from canonical b099691, not an evidence digest.
            standalone = manual.render_qualitative_durability_research_note_v1(note)
            self.assertEqual(hashlib.sha256(standalone.encode()).hexdigest(), expected)
            fragment = manual.render_qualitative_durability_research_note_fragment_v1(note)
            self.assertFalse(any(tag in ('html', 'head', 'body') for tag, attrs in SheetHTML(fragment).tags))
            self.assertIn('MANUAL_RESEARCH_ONLY', fragment)
        for option in (None, 'false', 0):
            with self.assertRaises(manual.ResearchNoteError):
                manual.render_qualitative_durability_research_note_fragment_v1(fictional_note(), include_conclusion=option)

    def test_wrong_manual_type_and_no_operational_runtime_imports(self):
        q = self.evaluate()
        with self.assertRaises(manual.ResearchNoteError):
            sheet.render_unified_durability_research_sheet_v1(q, {})
        modules = {node.module if isinstance(node, ast.ImportFrom) else node.names[0].name
                   for node in ast.walk(ast.parse(inspect.getsource(sheet)))
                   if isinstance(node, (ast.Import, ast.ImportFrom))}
        self.assertEqual(modules, {'decimal', 'enum', 'html', 'economic_facts',
                                  'economic_facts.sec_archive', 'src'})
