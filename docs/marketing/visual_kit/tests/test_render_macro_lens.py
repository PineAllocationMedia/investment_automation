import copy
import json
import tempfile
import unittest
from pathlib import Path
from xml.etree import ElementTree as ET

from render_macro_lens import InvalidIssue, payload_hash, release_allowed, render, run

ROOT = Path(__file__).resolve().parents[1]
EX = ROOT / 'examples'


def fixture(code):
    return json.loads((EX/f'{code}_synthetic.json').read_text())

class RenderTests(unittest.TestCase):
    def test_templates_draft_svg_parse(self):
        for code in ('t1','t2','t3'):
            with self.subTest(code=code):
                data=fixture(code)
                svg=render(data)
                parsed=ET.fromstring(svg)
                self.assertEqual(parsed.attrib['width'], '1080')
                self.assertIn('DRAFT',svg)
                self.assertIn('NOT INVESTMENT ADVICE',svg)
                self.assertNotIn('crypto',svg)

    def test_html_escaping(self):
        d=fixture('t1')
        d['headline']='Signal & mechanism < not investment advice'
        s=render(d)
        self.assertIn('&amp;',s)
        self.assertIn('&lt;',s)
        ET.fromstring(s)

    def test_reject_missing_evidence(self):
        d=fixture('t1'); d['evidence']=[]
        with self.assertRaises(InvalidIssue): render(d)

    def test_reject_unverified(self):
        d=fixture('t1'); d['evidence'][0]['verification']='UNKNOWN'
        with self.assertRaises(InvalidIssue): render(d)

    def test_reject_bad_urls(self):
        d=fixture('t1'); d['evidence'][0]['source_url']='javascript:alert(1)'
        with self.assertRaises(InvalidIssue): render(d)

    def test_reject_cross_session_comparison(self):
        d=fixture('t2'); d['evidence'][1]['observed_at']='2026-10-19T16:00:00-04:00'
        with self.assertRaises(InvalidIssue): render(d)

    def test_reject_historical_unit_mismatch(self):
        d=fixture('t3'); d['evidence'][1]['unit']='different unit'
        with self.assertRaises(InvalidIssue): render(d)

    def test_reject_overflow(self):
        d=fixture('t1'); d['headline']='words '*12
        with self.assertRaises(InvalidIssue): render(d)

    def test_release_requirements_and_bound_sha(self):
        d=fixture('t1')
        good={'input_sha256':payload_hash(d),'independent_audit':'PASS', 'ceo_approved':True,
              'auditor_reference':'external-audit-2026-xx',
              'ceo_approval_reference':'CEO-approved-final-asset'}
        with self.assertRaises(InvalidIssue): release_allowed(d,good)  # synthetic must never release
        d['evidence'][0]['source_url']='https://www.bankofcanada.ca/reports'
        d['evidence'][0]['verification_note']='Verified against underlying bulletin by reviewer'
        good['input_sha256']=payload_hash(d)
        release_allowed(d,good)
        self.assertNotIn('DRAFT',render(d,'RELEASE'))
        altered=copy.deepcopy(d); altered['headline']='Edited after approval'
        with self.assertRaises(InvalidIssue): release_allowed(altered,good)
        bad=dict(good);bad['ceo_approved']=False
        with self.assertRaises(InvalidIssue): release_allowed(d,bad)

    def test_png_export(self):
        try:
            import fitz
        except ImportError:
            self.skipTest('PyMuPDF optional for PNG output in local test')
        with tempfile.TemporaryDirectory() as tmp:
            output=Path(tmp)/'a.svg'
            png=Path(tmp)/'a.png'
            result=run([str(EX/'t1_synthetic.json'),'--output',str(output),'--png',str(png)])
            self.assertEqual(result,0)
            self.assertGreater(png.stat().st_size,30000)
            from PIL import Image
            with Image.open(png) as im:
                self.assertEqual(im.size,(1080,1350))

if __name__=='__main__':
    unittest.main()