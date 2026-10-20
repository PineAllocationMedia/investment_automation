import copy
import hashlib
import struct
import zlib
import json
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path
from xml.etree import ElementTree as ET

from render_macro_lens import APPROVED_LOGO_SHA256, InvalidIssue, payload_hash, release_allowed, render, run, checked_logo

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
        d['brand_logo_sha256']=APPROVED_LOGO_SHA256
        good['input_sha256']=payload_hash(d)
        release_allowed(d,good)
        with self.assertRaises(InvalidIssue): render(d,'RELEASE')  # exact logo mandatory
        altered=copy.deepcopy(d); altered['headline']='Edited after approval'
        with self.assertRaises(InvalidIssue): release_allowed(altered,good)
        altered_caption=copy.deepcopy(d);altered_caption['caption']='Changed caption after CEO approval'
        with self.assertRaises(InvalidIssue): release_allowed(altered_caption,good)
        bad=dict(good);bad['ceo_approved']=False
        with self.assertRaises(InvalidIssue): release_allowed(d,bad)

    def test_logo_asset_hash_bound_and_release_requires_logo(self):
        d=fixture('t1')
        d['evidence'][0]['source_url']='https://www.bankofcanada.ca/reports'
        d['evidence'][0]['verification_note']='External review recorded independently'
        # Construct a legal square PNG without Pillow or network access.
        def chunk(label, data):
            return struct.pack('>I',len(data))+label+data+struct.pack('>I',zlib.crc32(label+data)&0xffffffff)
        raw=b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',128,128,8,2,0,0,0))
        row=b'\x00'+bytes([244,240,230])*128
        raw+=chunk(b'IDAT',zlib.compress(row*128))+chunk(b'IEND',b'')
        with tempfile.TemporaryDirectory() as tmp:
            logo=Path(tmp)/'logo.png';logo.write_bytes(raw)
            self.assertEqual(checked_logo(logo),raw)
            d['brand_logo_sha256']=hashlib.sha256(raw).hexdigest()
            issue=Path(tmp)/'issue.json';issue.write_text(json.dumps(d))
            good={'input_sha256':payload_hash(d),'independent_audit':'PASS','ceo_approved':True,
                  'auditor_reference':'test-audit','ceo_approval_reference':'test-ceo-approval'}
            manifest=Path(tmp)/'approval.json';manifest.write_text(json.dumps(good))
            # This test fixture is not a real publication; it checks the release contract only.
            out=Path(tmp)/'approved.svg'
            self.assertEqual(run([str(issue),'--release-manifest',str(manifest),'--output',str(out)]),2)
            # A self-declared issue hash is insufficient to approve a brand asset.
            self.assertEqual(run([str(issue),'--release-manifest',str(manifest),'--brand-logo',str(logo),'--output',str(out)]),2)
            # Unit-test only: substitute the synthetic test PNG's hash to exercise the
            # remainder of the release path; production must use canonical SHA.
            with patch('render_macro_lens.APPROVED_LOGO_SHA256', hashlib.sha256(raw).hexdigest()):
                self.assertEqual(run([str(issue),'--release-manifest',str(manifest),'--brand-logo',str(logo),'--output',str(out)]),0)
            self.assertIn('data:image/png;base64',out.read_text())
            issue_data=dict(d,brand_logo_sha256='0'*64);issue.write_text(json.dumps(issue_data))
            self.assertEqual(run([str(issue),'--brand-logo',str(logo),'--output',str(out)]),2)

    def test_canonical_approved_asset_register(self):
        meta=json.loads((ROOT/'assets'/'PAM_MACRO_LENS_LOGO_RECONSTRUCTED_v0.1.json').read_text())
        self.assertEqual(meta['provenance_classification'], 'RECONSTRUCTED')
        self.assertEqual(meta['approval_status'], 'CEO_APPROVED_ASSET_ONLY')
        self.assertEqual(meta['sha256'], APPROVED_LOGO_SHA256)
        self.assertEqual(meta['dimensions_px'], {'width':2048,'height':2048})
        self.assertTrue(meta['approved_file_location']['path'].endswith('.png'))
        # The actual approved binary is in authorized Library custody, not this Git tree.

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
            import struct
            raw=png.read_bytes()
            self.assertTrue(raw.startswith(b'\x89PNG\r\n\x1a\n'))
            self.assertEqual(struct.unpack('>II',raw[16:24]),(1080,1350))

if __name__=='__main__':
    unittest.main()