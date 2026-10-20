"""E1 Company Lens source-contract and rendered mobile geometry regression tests."""
import copy
import json
import math
import struct
import tempfile
import unittest
from pathlib import Path
from xml.etree import ElementTree as ET

from render_company_lens import validate_company_lens, draw_company_lens, run
from render_macro_lens import InvalidIssue, payload_hash, release_allowed

FIXTURE=Path(__file__).resolve().parents[1]/'examples'/'e1_synthetic.json'


def demo():
    return json.loads(FIXTURE.read_text(encoding='utf-8'))


class E1CompanyLensTests(unittest.TestCase):
    def test_three_historical_facts_and_inference_hierarchy(self):
        p=demo()
        facts=validate_company_lens(p)
        self.assertEqual(len(facts),3)
        self.assertEqual([x['metric'] for x in facts],
                         ['Reported revenue','Operating income',
                          'Cash from operations'])
        svg=draw_company_lens(p)
        root=ET.fromstring(svg)
        self.assertEqual((int(root.attrib['width']),int(root.attrib['height'])),
                         (1080,1350))
        for token in ('COMPANY LENS','THREE REPORTED FACTS','COUNTER-CASE',
                      'WHAT TO MONITOR','EDITORIAL READING','ORIGINAL SEC SOURCE',
                      'REPORTED','GAAP','DRAFT','SYNTHETIC TEST',
                      '4,280','620','735','NOT INVESTMENT ADVICE'):
            self.assertIn(token,svg)
        self.assertNotIn('BUY NOW',svg)

    def test_missing_one_fact_fails(self):
        p=demo();p['evidence'].pop()
        with self.assertRaises(InvalidIssue): validate_company_lens(p)

    def test_duplicate_claim_fails(self):
        p=demo();p['evidence'][1]['claim_id']=p['evidence'][0]['claim_id']
        with self.assertRaises(InvalidIssue): validate_company_lens(p)

    def test_malformed_company_identity_fails(self):
        for key,val in [('ticker','bear $'),('cik','123'),('reporting_currency','CAD/USD')]:
            p=demo();p[key]=val
            with self.subTest(field=key),self.assertRaises(InvalidIssue):
                validate_company_lens(p)

    def test_numeric_display_mismatch_fails(self):
        p=demo();p['evidence'][0]['display']='9,280'
        with self.assertRaises(InvalidIssue): validate_company_lens(p)

    def test_nonfinite_numbers_fail(self):
        for v in (float('nan'),float('inf'),None):
            p=demo();p['evidence'][2]['numeric_value']=v
            with self.subTest(value=str(v)),self.assertRaises(InvalidIssue):
                validate_company_lens(p)

    def test_metrics_cannot_impersonate_guidance(self):
        p=demo();p['evidence'][0]['fact_kind']='FORWARD_GUIDANCE'
        with self.assertRaises(InvalidIssue):validate_company_lens(p)

    def test_gaap_non_gaap_labeled_not_silently_mixed(self):
        p=demo();p['evidence'][0]['basis']='UNSPECIFIED'
        with self.assertRaises(InvalidIssue):validate_company_lens(p)
        p=demo();p['evidence'][0]['basis']='NON_GAAP'
        self.assertEqual(validate_company_lens(p)[0]['basis'],'NON_GAAP')
        self.assertIn('NON_GAAP',draw_company_lens(p))

    def test_single_fiscal_period_not_asynchronous_facts(self):
        p=demo();p['evidence'][2]['fiscal_period']='FY2025'
        with self.assertRaises(InvalidIssue):validate_company_lens(p)

    def test_missing_original_primary_and_section_fail(self):
        p=demo();p['evidence'][1]['source_url']='https://elsewhere.example.org/article'
        with self.assertRaises(InvalidIssue):validate_company_lens(p)
        p=demo();p['evidence'][0]['source_section']=''
        with self.assertRaises(InvalidIssue):validate_company_lens(p)

    def test_filing_not_future(self):
        p=demo();p['filed_at']='2026-10-21T08:00:00-04:00'
        with self.assertRaises(InvalidIssue):validate_company_lens(p)
        p=demo();p['evidence'][2]['retrieved_at']='2026-10-21T11:00:00-04:00'
        with self.assertRaises(InvalidIssue):validate_company_lens(p)

    def test_rights_and_live_sec_edgar_gate(self):
        p=demo();p['rights_note']='REVIEWED_FOR_EXACT_USE'
        with self.assertRaises(InvalidIssue):validate_company_lens(p)
        p=demo();p['primary_filing_url']='https://www.sec.gov/Archives/edgar/data/1/demo.htm'
        with self.assertRaises(InvalidIssue):validate_company_lens(p)
        p=demo();p['rights_note']='REVIEWED_FOR_EXACT_USE'
        p['cik']='0001234567'
        p['primary_filing_url']='https://www.sec.gov/Archives/edgar/data/1234567/demo.htm'
        for f in p['evidence']:
            f['source_url']=p['primary_filing_url']
        self.assertEqual(len(validate_company_lens(p)),3)
        # A syntactically permissible SEC URL is not actual source verification.
        self.assertNotEqual(p['primary_filing_url'],demo()['primary_filing_url'])

    def test_fake_or_unverified_source_fails(self):
        p=demo();p['evidence'][0]['verification']='UNKNOWN'
        with self.assertRaises(InvalidIssue):validate_company_lens(p)
        p=demo();p['evidence'][0]['source_url']='javascript:alert(1)'
        with self.assertRaises(InvalidIssue):validate_company_lens(p)

    def test_synthetic_cannot_gain_release_authority(self):
        p=demo()
        with self.assertRaises(InvalidIssue):draw_company_lens(p,status='RELEASE')
        approval={'input_sha256':payload_hash(p),'independent_audit':'PASS',
                  'ceo_approved':True,'auditor_reference':'synthetic-auditor',
                  'ceo_approval_reference':'synthetic-ceo'}
        with self.assertRaises(InvalidIssue):release_allowed(p,approval)
        q=copy.deepcopy(p);q['caption']='changed caption'
        self.assertNotEqual(payload_hash(q),payload_hash(p))

    def test_overflow_copy_refused(self):
        p=demo();p['headline']='INFINITELY LONG UNBOUNDED STAGGERING HEADER '*3
        with self.assertRaises(InvalidIssue):draw_company_lens(p)

    def test_native_png_glyph_bounds_and_distinct_conclusions(self):
        try:
            import fitz
        except ImportError:
            self.skipTest('PyMuPDF needed for actual glyph bounds')
        svg=draw_company_lens(demo())
        page=fitz.open(stream=svg.encode('utf-8'),filetype='svg')[0]
        pix=page.get_pixmap(matrix=fitz.Matrix(1,1),alpha=False)
        self.assertEqual((pix.width,pix.height),(1080,1350))
        mobile=page.get_pixmap(matrix=fitz.Matrix(390/1080,390/1080),alpha=False)
        self.assertEqual(mobile.width,390)
        self.assertGreaterEqual(mobile.height,487)
        spans=[sp for b in page.get_text('dict')['blocks']
               for l in b.get('lines',[]) for sp in l['spans']]
        for sp in spans:
            x0,y0,x1,y1=sp['bbox']
            self.assertGreaterEqual(x0,56,sp['text'])
            self.assertLessEqual(x1,1022,sp['text'])
            self.assertGreaterEqual(y0,42,sp['text'])
            self.assertLessEqual(y1,1340,sp['text'])
        sections=[sp for sp in spans if sp['text']=='EDITORIAL READING']
        self.assertEqual(len(sections),3)
        counter=next(sp for sp in spans if sp['text']=='COUNTER-CASE')
        watch=next(sp for sp in spans if sp['text']=='WHAT TO MONITOR')
        disclaimer=next(sp for sp in spans if sp['text']=='NOT INVESTMENT ADVICE')
        self.assertLess(sections[-1]['bbox'][3]+22,counter['bbox'][1])
        self.assertLess(counter['bbox'][3]+55,watch['bbox'][1])
        self.assertLess(watch['bbox'][3]+80,disclaimer['bbox'][1])

    def test_cli_writes_only_complete_render(self):
        try:
            import fitz
        except ImportError:
            self.skipTest('Requires PyMuPDF')
        with tempfile.TemporaryDirectory() as temp:
            dest=Path(temp);svg=dest/'draft.svg';png=dest/'draft.png'
            self.assertEqual(run([str(FIXTURE),'--output',str(svg),'--png',str(png)]),0)
            self.assertEqual(struct.unpack('>II',png.read_bytes()[16:24]),(1080,1350))
            before=svg.read_bytes()
            p=demo();p['evidence'][0]['display']='999'
            invalid=dest/'invalid.json';invalid.write_text(json.dumps(p))
            self.assertEqual(run([str(invalid),'--output',str(svg),'--png',str(png)]),2)
            self.assertEqual(svg.read_bytes(),before)


if __name__=='__main__':
    unittest.main()
