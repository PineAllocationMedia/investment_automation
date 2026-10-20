"""Structural and mobile-geometry guards for opt-in T1 Research Note pilot.

Fixtures contain SYNTHETIC market data and must never be published.
"""
import copy
import json
import unittest
from pathlib import Path
from xml.etree import ElementTree as ET

from render_macro_lens import InvalidIssue, payload_hash, render, release_allowed

ROOT = Path(__file__).resolve().parents[1]


def fixture(name='t1'):
    return json.loads((ROOT / 'examples' / f'{name}_synthetic.json').read_text())


def note_issue():
    p = fixture()
    p['t1_layout'] = 'RESEARCH_NOTE'
    return p


def elements(svg, name):
    return [el for el in ET.fromstring(svg).iter() if el.tag.endswith(name)]


class ResearchNoteTests(unittest.TestCase):
    def test_opt_in_uses_research_note_without_changing_fact_binding(self):
        p = note_issue()
        svg = render(p)
        self.assertIn('DRAFT', svg)
        self.assertIn('MARKET OBSERVATION', svg)
        self.assertIn('SECOND-ORDER CONSIDERATION', svg)
        self.assertIn('WHAT WOULD CHANGE THE VIEW?', svg)
        self.assertIn('Illustrative signal', svg)
        self.assertIn('DEMO ONLY', svg)
        self.assertIn('SOURCES:', svg)
        self.assertIn('NOT INVESTMENT ADVICE', svg)
        self.assertEqual(len(elements(svg, 'svg')), 1)
        # The old three panel mechanism boxes must not be reused.
        self.assertNotIn('x="68" y="730" width="295"', svg)
        self.assertNotIn('x="393" y="730" width="295"', svg)
        self.assertNotIn('x="718" y="730" width="295"', svg)
        # Ruling marks, not colored card tiles, separate the three mechanisms.
        self.assertIn('M 366 751 L 366 857', svg)
        self.assertIn('M 691 751 L 691 857', svg)

    def test_legacy_classic_stays_byte_identical(self):
        p = fixture()
        old = render(p)
        p['t1_layout'] = 'CLASSIC'
        self.assertEqual(render(p), old)
        self.assertIn('x="68" y="481" width="944" height="156"', old)

    def test_opt_in_style_changes_approval_hash(self):
        p = fixture()
        q = copy.deepcopy(p)
        q['t1_layout'] = 'RESEARCH_NOTE'
        self.assertNotEqual(payload_hash(p), payload_hash(q))
        self.assertEqual(p['caption'], q['caption'])
        self.assertEqual(p['evidence'], q['evidence'])
        self.assertEqual(p['fact_ids'], q['fact_ids'])

    def test_reject_unknown_t1_layout(self):
        p = fixture()
        p['t1_layout'] = 'BUBBLE_GRID'
        with self.assertRaises(InvalidIssue):
            render(p)

    def test_reject_research_note_for_evidence_plus(self):
        p = fixture('t1_evidence_plus')
        p['t1_layout'] = 'RESEARCH_NOTE'
        with self.assertRaises(InvalidIssue):
            render(p)

    def test_reject_t1_layout_for_t2(self):
        p = fixture('t2')
        p['t1_layout'] = 'RESEARCH_NOTE'
        with self.assertRaises(InvalidIssue):
            render(p)

    def test_fail_closed_for_overwide_mechanism(self):
        p = note_issue()
        p['mechanism'][0] = 'W' * 19
        with self.assertRaises(InvalidIssue):
            render(p)

    def test_fail_closed_for_overwide_label(self):
        p = note_issue()
        p['evidence'][0]['label'] = 'W' * 27
        with self.assertRaises(InvalidIssue):
            render(p)

    def test_fail_closed_for_overwide_tripwire(self):
        p = note_issue()
        p['tripwire'] = 'W' * 64
        with self.assertRaises(InvalidIssue):
            render(p)

    def test_wrapped_source_preserved_without_layout_overlap(self):
        p = note_issue()
        p['evidence'][0]['source_title'] = 'National Office for Monthly Price Statistics and Analysis'
        svg = render(p)
        self.assertIn('National Office for Monthly', svg)
        self.assertIn('Statistics and Analysis', svg)
        self.assertEqual(len([e for e in elements(svg, 'text')
                              if (e.text or '').startswith('AS OF ')]), 1)
        self._check_real_geometry(svg)

    def test_two_line_watch_stays_above_wrapped_provenance(self):
        try:
            import fitz
        except ImportError:
            self.skipTest('PyMuPDF required for text bounds')
        p = note_issue()
        p['tripwire'] = ('Higher buyer traffic and more permits would challenge '
                         'the interpretation as mortgage costs ease.')
        p['evidence'][0]['source_title'] = 'National Office for Monthly Price Statistics and Analysis'
        svg = render(p)
        page = fitz.open(stream=svg.encode('utf-8'), filetype='svg')[0]
        spans = [span for block in page.get_text('dict')['blocks']
                 for line in block.get('lines', [])
                 for span in line['spans']]
        watch_lines = [span for span in spans
                       if 1090 <= span['bbox'][1] < 1170]
        provenance_lines = [span for span in spans
                            if 1190 <= span['bbox'][1] < 1290]
        self.assertEqual(len(watch_lines), 2)
        self.assertEqual(len(provenance_lines), 2)
        self.assertLess(watch_lines[-1]['bbox'][3] + 8,
                        provenance_lines[0]['bbox'][1])
        self.assertLess(provenance_lines[-1]['bbox'][3] + 5,
                        next(span for span in spans
                             if span['text'].startswith('AS OF '))['bbox'][1])

    def test_wrapped_signal_label_clears_units(self):
        try:
            import fitz
        except ImportError:
            self.skipTest('PyMuPDF required for text bounds')
        p = note_issue()
        p['evidence'][0]['label'] = 'Illustrative weighted signal index'
        svg = render(p)
        page = fitz.open(stream=svg.encode('utf-8'), filetype='svg')[0]
        spans = [span for block in page.get_text('dict')['blocks']
                 for line in block.get('lines', [])
                 for span in line['spans']]
        label = [x for x in spans if x['text'].startswith('Illustrative')
                 or x['text'].startswith('signal index')]
        unit = next(x for x in spans if x['text'] == 'not market data')
        self.assertEqual(len(label), 2)
        self.assertLess(label[-1]['bbox'][3], unit['bbox'][1])

    def test_mobile_rendered_bounds(self):
        self._check_real_geometry(render(note_issue()))

    def _check_real_geometry(self, svg):
        try:
            import fitz
        except ImportError:
            self.skipTest('PyMuPDF required for actual PNG mobile-geometry checks')
        doc = fitz.open(stream=svg.encode('utf-8'), filetype='svg')
        page = doc[0]
        spans = [span for block in page.get_text('dict')['blocks']
                 for line in block.get('lines', [])
                 for span in line['spans']]
        for span in spans:
            x0, y0, x1, y1 = span['bbox']
            self.assertGreaterEqual(x0, 55, span['text'])
            self.assertLessEqual(x1, 1022, span['text'])
            self.assertGreaterEqual(y0, 55, span['text'])
            self.assertLessEqual(y1, 1342, span['text'])
        watch = next(x for x in spans if x['text'] == 'WHAT WOULD CHANGE THE VIEW?')
        tripwire = next(x for x in spans if x['text'].startswith('Wait for'))
        source = next(x for x in spans if x['text'].startswith('SOURCES:'))
        asof = next(x for x in spans if x['text'].startswith('AS OF '))
        self.assertLess(watch['bbox'][3] + 8, tripwire['bbox'][1])
        self.assertLess(tripwire['bbox'][3] + 8, source['bbox'][1])
        self.assertLess(source['bbox'][3] + 8, asof['bbox'][1])
        px = page.get_pixmap(matrix=fitz.Matrix(1, 1), alpha=False)
        self.assertEqual((px.width, px.height), (1080, 1350))


if __name__ == '__main__':
    unittest.main()
