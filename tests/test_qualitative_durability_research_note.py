"""Fictional manual notes only; no genuine issuer narrative or private evidence."""
import ast
from dataclasses import fields, FrozenInstanceError, replace
from html import escape
from html.parser import HTMLParser
import inspect
from pathlib import Path
import pickle
import socket
import unittest
from unittest.mock import patch

from src import qualitative_durability_research_note as q


def fictional_note():
    source = q.ManualSourceReferenceV1(
        document_title='Fictional Lantern Systems annual document',
        document_reference='FICTIONAL-DOC-2025', document_date='2025-06-30',
        source_type='FICTIONAL_ISSUER_REPORT', locator='https://issuer.invalid/fictional',
        section_location='Fictional section A — Product discussion',
        operator_supplied_digest='fictional-operator-digest-not-verified')
    advantage = q.QualitativeResearchItemV1(
        source=source, statement_attribution='Fictional Lantern Systems management',
        issuer_statement='The fictional issuer says its workflow tools share a common interface.',
        source_grounded_observation='The operator reports that management makes this assertion.',
        research_interpretation='A shared interface could simplify employee training.',
        possible_economic_mechanism='Training familiarity might contribute to switching friction.',
        competing_explanations_or_vulnerabilities=('Rival interfaces may be equally familiar.',),
        supporting_context=('The same fictional issuer describes bundled onboarding.',),
        contrary_context=('Management also describes competition from simpler substitutes.',),
        missing_corroboration=('No independent customer retention observations supplied.',),
        uncertainties=('Training cost and customer dependence have not been measured.',),
        possible_falsification_evidence=('Independent evidence of easy customer switching.',))
    vulnerability = q.QualitativeResearchItemV1(
        source=replace(source, section_location='Fictional section B — Competitive risks'),
        statement_attribution='The same fictional issuer',
        issuer_statement='The fictional issuer describes rapid changes in customer workflows.',
        possible_economic_mechanism='New workflows could reduce the value of interface familiarity.',
        contrary_context=('Existing training could mitigate some migration costs.',))
    return q.QualitativeDurabilityResearchNoteV1(
        issuer_name='Fictional Lantern Systems', issuer_reference='FICTIONAL-ISSUER-01',
        review_status=q.ManualReviewStatus.OPERATOR_REVIEWED,
        reviewed_by='Fictional operator', reviewed_on='2025-07-02',
        items=(advantage, vulnerability),
        provenance_limitations=('Operator references only; no native narrative receipt.',
                                'Private research use only; redistribution rights not established.'),
        research_conclusion='A possible mechanism and competing vulnerability are described; persistence is unproven.')


class ParsedHTML(HTMLParser):
    def __init__(self, text):
        super().__init__()
        self.tags = []
        self.text = []
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, dict(attrs)))

    def handle_data(self, data):
        self.text.append(data)


class QualitativeResearchNoteTests(unittest.TestCase):
    def test_complete_fictional_fiche_keeps_all_semantic_layers_separate(self):
        note = fictional_note()
        html = q.render_qualitative_durability_research_note_v1(note)
        for marker in (q.AUTHORITY, q.EVIDENCE_STATUS, q.TEMPORAL_MODE,
                       'Statement attribution', 'Issuer statement', 'source-grounded observation',
                       'Research interpretation', 'Possible economic mechanism',
                       'Material competing explanations', 'Supporting context', 'Contrary context',
                       'Missing corroboration', 'Uncertainties', 'Possible falsification evidence',
                       'Manual research conclusion', 'not automated', 'not independently verified'):
            self.assertIn(marker, html)
        for item in note.items:
            self.assertIn(escape(item.issuer_statement), html)
            self.assertIn(escape(item.source.section_location), html)
        self.assertIn(escape(note.research_conclusion), html)
        self.assertNotIn('Microsoft', html)

    def test_empty_note_exposes_missing_information_and_does_not_invent_conclusion(self):
        html = q.render_qualitative_durability_research_note_v1(q.QualitativeDurabilityResearchNoteV1())
        self.assertIn('UNREVIEWED', html)
        self.assertIn('Research items: NOT PROVIDED', html)
        self.assertIn('Manual research conclusion (operator supplied; not automated)</dt><dd>NOT PROVIDED', html)
        self.assertNotIn('OPERATOR_REVIEWED', html)

    def test_missing_source_location_and_all_missing_lists_remain_explicit(self):
        note = q.QualitativeDurabilityResearchNoteV1(items=(q.QualitativeResearchItemV1(),))
        html = q.render_qualitative_durability_research_note_v1(note)
        self.assertIn('Section location (operator supplied; not inferred)</dt><dd>NOT PROVIDED', html)
        self.assertIn('Issuer statement (operator supplied; source grounding unverified)</dt><dd>NOT PROVIDED', html)
        self.assertGreaterEqual(html.count('<li>NOT PROVIDED</li>'), 7)
        self.assertNotIn('No risks', html)
        self.assertNotIn('(operator reviewed;', html)

    def test_same_issuer_source_is_never_declared_independent_corroboration(self):
        html = q.render_qualitative_durability_research_note_v1(fictional_note())
        self.assertIn('Supporting context (not automatically independent corroboration)', html)
        self.assertIn('Operator review does not verify native SEC provenance', html)

    def test_digest_url_accession_and_paths_never_promote_authority(self):
        note = fictional_note()
        for locator in ('https://issuer.invalid/source', '/fictional/private/source.htm',
                        'javascript:alert(1)', '0000000000-25-000001'):
            item = replace(note.items[0], source=replace(note.items[0].source,
                           locator=locator, operator_supplied_digest='a' * 64))
            html = q.render_qualitative_durability_research_note_v1(replace(note, items=(item,)))
            self.assertIn(q.EVIDENCE_STATUS, html)
            self.assertIn('not recomputed or verified', html)
            self.assertIn(escape(locator), html)
            self.assertFalse(any(tag in ('a', 'img', 'script', 'iframe', 'object')
                                 for tag, attrs in ParsedHTML(html).tags))

    def test_text_is_escaped_in_every_operator_text_position(self):
        attack = '<script>alert("x")</script><img src="https://bad.invalid/x" onerror="x"> & \'quoted\''
        source = q.ManualSourceReferenceV1(**{f.name: attack for f in fields(q.ManualSourceReferenceV1)
                                              if f.name != 'document_date'})
        item = q.QualitativeResearchItemV1(
            source=source, **{f.name: (attack,) if f.name in (
                'competing_explanations_or_vulnerabilities', 'supporting_context', 'contrary_context',
                'missing_corroboration', 'uncertainties', 'possible_falsification_evidence') else attack
                for f in fields(q.QualitativeResearchItemV1) if f.name != 'source'})
        note = q.QualitativeDurabilityResearchNoteV1(
            issuer_name=attack, issuer_reference=attack, items=(item,),
            provenance_limitations=(attack,), research_conclusion=attack,
            review_status=q.ManualReviewStatus.OPERATOR_REVIEWED, reviewed_by=attack, reviewed_on='2025-01-01')
        html = q.render_qualitative_durability_research_note_v1(note)
        self.assertNotIn(attack, html)
        self.assertIn(escape(attack), html)
        parsed = ParsedHTML(html)
        self.assertFalse(any(tag in ('script', 'img', 'a', 'iframe') for tag, attrs in parsed.tags))
        self.assertFalse(any(k.startswith('on') or k in ('src', 'href') for tag, attrs in parsed.tags for k in attrs))
        self.assertTrue(any(tag == 'meta' and attrs.get('http-equiv') == 'Content-Security-Policy'
                            and "default-src 'none'" in attrs['content'] for tag, attrs in parsed.tags))

    def test_immutable_nested_values_and_no_mutable_container_admission(self):
        note = fictional_note()
        for obj, field, value in ((note, 'issuer_name', 'Changed'),
                                  (note.items[0], 'issuer_statement', 'Changed'),
                                  (note.items[0].source, 'locator', 'Changed')):
            with self.assertRaises(FrozenInstanceError):
                setattr(obj, field, value)
        for kwargs in ({'items': list(note.items)}, {'items': ({},)}, {'provenance_limitations': ['x']}):
            with self.assertRaises(q.ResearchNoteError):
                replace(note, **kwargs)
        with self.assertRaises(q.ResearchNoteError):
            q.QualitativeResearchItemV1(source={})

    def test_text_and_list_type_bounds_are_checked_without_coercion(self):
        for value in ('', '  ', True, 1, {}, ['text'], 'x' * 10001, 'a\x00b', 'a\u202eb'):
            with self.subTest(value=repr(value)[:50]), self.assertRaises(q.ResearchNoteError):
                q.QualitativeDurabilityResearchNoteV1(issuer_name=value)
        for values in (['x'], (None,), (1,), ('x',) * 21):
            with self.assertRaises(q.ResearchNoteError):
                q.QualitativeResearchItemV1(uncertainties=values)
        with self.assertRaises(q.ResearchNoteError):
            q.QualitativeDurabilityResearchNoteV1(items=(q.QualitativeResearchItemV1(),) * 21)

    def test_review_is_explicit_closed_and_requires_both_operator_and_date(self):
        for kwargs in ({'review_status': 'OPERATOR_REVIEWED'}, {'review_status': True},
                       {'review_status': q.ManualReviewStatus.OPERATOR_REVIEWED},
                       {'reviewed_by': 'Someone'}, {'reviewed_on': '2025-01-01'},
                       {'reviewed_by': 'Someone', 'reviewed_on': '2025-01-01'},
                       {'review_status': q.ManualReviewStatus.OPERATOR_REVIEWED, 'reviewed_by': 'Someone'}):
            with self.subTest(kwargs=kwargs), self.assertRaises(q.ResearchNoteError):
                q.QualitativeDurabilityResearchNoteV1(**kwargs)

    def test_dates_are_exact_metadata_not_clock_based_availability(self):
        for value in ('2025-02-30', '20250101', '2025-1-1', '2025-01-01T00:00:00Z', True):
            with self.assertRaises(q.ResearchNoteError):
                q.ManualSourceReferenceV1(document_date=value)
        note = replace(fictional_note(), reviewed_on='2099-01-01')
        self.assertIn('2099-01-01', q.render_qualitative_durability_research_note_v1(note))
        self.assertEqual(note.temporal_mode, 'CURRENT_CAPTURE_BOUND_ONLY')

    def test_foreign_subclass_and_corrupted_input_rejected_before_render(self):
        class Foreign(q.QualitativeDurabilityResearchNoteV1):
            pass
        for value in ({}, None, True, Foreign()):
            with self.assertRaises(q.ResearchNoteError):
                q.render_qualitative_durability_research_note_v1(value)
        corrupted = fictional_note()
        object.__setattr__(corrupted.items[0].source, 'locator', 99)
        with self.assertRaises(q.ResearchNoteError):
            q.render_qualitative_durability_research_note_v1(corrupted)
        with self.assertRaises(q.ResearchNoteError):
            q.render_qualitative_durability_research_note_v1(object.__new__(q.QualitativeDurabilityResearchNoteV1))

    def test_deterministic_render_roundtrip_and_input_order_without_normalization(self):
        note = fictional_note()
        expected = q.render_qualitative_durability_research_note_v1(note)
        self.assertEqual(expected, q.render_qualitative_durability_research_note_v1(pickle.loads(pickle.dumps(note))))
        text = '  Fictional observation\nSecond line\tcontinues  '
        edited = replace(note, research_conclusion=text)
        self.assertIn(escape(text), q.render_qualitative_durability_research_note_v1(edited))
        reversed_note = replace(note, items=tuple(reversed(note.items)))
        self.assertNotEqual(expected, q.render_qualitative_durability_research_note_v1(reversed_note))

    def test_no_file_network_or_acquisition_side_effects(self):
        note = fictional_note()
        with (patch('builtins.open', side_effect=AssertionError('file IO')),
              patch.object(Path, 'open', side_effect=AssertionError('path IO')),
              patch.object(socket, 'socket', side_effect=AssertionError('network'))):
            html = q.render_qualitative_durability_research_note_v1(note)
        self.assertIn(q.AUTHORITY, html)
        tree = ast.parse(inspect.getsource(q))
        modules = {n.module if isinstance(n, ast.ImportFrom) else n.names[0].name
                   for n in ast.walk(tree) if isinstance(n, (ast.Import, ast.ImportFrom))}
        self.assertEqual(modules, {'dataclasses', 'datetime', 'enum', 'html', 'typing', 'unicodedata'})

    def test_no_numeric_scoring_native_identity_or_automatic_conclusion_surface(self):
        note = fictional_note()
        self.assertEqual({s.value for s in q.ManualReviewStatus}, {'UNREVIEWED', 'OPERATOR_REVIEWED'})
        self.assertEqual(note.authority, 'MANUAL_RESEARCH_ONLY')
        self.assertEqual(note.evidence_status, 'NOT_NATIVE_EVIDENCE_ADMISSION')
        for name in ('score', 'confidence', 'moat', 'allocation', 'semantic_id', 'evidence_id'):
            self.assertFalse(hasattr(note, name))
        with self.assertRaises(TypeError):
            q.QualitativeDurabilityResearchNoteV1(authority='NATIVE_SEC_VERIFIED')
        from src import d1_two_period_operating_profit_continuity as d1
        from src import d2_two_period_reported_trajectory as d2
        with self.assertRaises(d1.D1DiagnosticError):
            d1.analyze_d1_two_period_operating_profit_continuity_v1(note)
        with self.assertRaises(d2.D2DiagnosticError):
            d2.analyze_d2_two_period_reported_trajectory_v1(note)
