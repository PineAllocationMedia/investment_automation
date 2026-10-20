"""M1 publication-looking exact image, 3+3 ranking and SHA-bound Prompt 3 audit.

All prices and reviewer records in this module are SYNTHETIC TEST FIXTURES.
No test output may be represented as a live market observation or authorization.
"""
import csv
import hashlib
import json
import struct
import tempfile
import unittest
import zlib
from pathlib import Path
from unittest.mock import patch
from xml.etree import ElementTree as ET

import m1_etf_daily
import render_global_index_map as m1
from m1_etf_daily import COLUMNS, init_csv, records, review
from render_macro_lens import InvalidIssue, payload_hash

ROOT=Path(__file__).resolve().parents[1]


def _chunk(name,data):
    return struct.pack('>I',len(data))+name+data+struct.pack(
        '>I',zlib.crc32(name+data)&0xffffffff)


def mock_png():
    """Valid 128px square PNG, NOT the approved historical PAM brand asset."""
    raw=b''.join(b'\x00'+b'\x20\x44\x39\xff'*128 for _ in range(128))
    return (b'\x89PNG\r\n\x1a\n'+
            _chunk(b'IHDR',struct.pack('>IIBBBBB',128,128,8,6,0,0,0))+
            _chunk(b'IDAT',zlib.compress(raw))+_chunk(b'IEND',b''))


def quote_sheet(path):
    init_csv(path)
    data=records(path)
    for i,e in enumerate(data):
        if e['ticker']:
            # Fictional, visibly declared test numbers.
            move=(i%9-4)*.45
            e.update(prior_close='100',close=str(100*(1+move/100)),
                     source_url='https://www.ishares.com/us/products/etf-investments',
                     prior_source_url='https://www.ishares.com/us/products/etf-investments',
                     source_name='TEST SOURCE NOT VERIFIED DAILY PRICES',
                     corporate_action_status='NO_KNOWN_EVENT',
                     source_use_status='REVIEW_PENDING',
                     notes='ALL PRICES FICTIONAL TEST VALUES')
    with path.open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=COLUMNS)
        w.writeheader();w.writerows(data)


class M1SixRankExactAssetTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.quotes=self.root/'fictional.csv'
        quote_sheet(self.quotes)
        self.logo=self.root/'mock_logo.png'
        self.logo.write_bytes(mock_png())
        self.logo_sha=hashlib.sha256(self.logo.read_bytes()).hexdigest()
        self.issue=self.root/'issue.json'
        self.svg=self.root/'candidate.svg'
        self.png=self.root/'candidate.png'
        self.mobile=self.root/'mobile.png'
        self.manifest=self.root/'asset_manifest.json'
        self.args=['build',str(self.quotes),'--session-date','2026-10-19',
                   '--prior-date','2026-10-16','--cutoff-utc','2026-10-20T18:30:00Z',
                   '--issue-id','GM-20261020-09','--brand-logo',str(self.logo),
                   '--out-issue',str(self.issue),'--svg',str(self.svg),
                   '--png',str(self.png),'--mobile-png',str(self.mobile),
                   '--asset-manifest',str(self.manifest)]

    def build_candidate(self):
        with patch.object(m1_etf_daily,'APPROVED_LOGO_SHA256',self.logo_sha),\
             patch.object(m1,'APPROVED_LOGO_SHA256',self.logo_sha):
            return m1_etf_daily.main(self.args)

    def mock_pass(self,manifest):
        return {'issue_sha256':manifest['issue_sha256'],
                'png_sha256':manifest['assets']['png']['sha256'],
                'svg_sha256':manifest['assets']['svg']['sha256'],
                'mobile_png_sha256':manifest['assets']['mobile_png']['sha256'],
                'caption_sha256':manifest['caption_sha256'],
                'fact_verdict':'PASS','corporate_actions_verdict':'PASS',
                'source_use_verdict':'NO_KNOWN_RESTRICTION',
                'visual_verdict':'PASS',
                'auditor_reference':'SYNTHETIC_TEST_AUDITOR',
                'source_use_review_reference':'SYNTHETIC_TEST_TERMS'}

    def test_six_unique_top_three_bottom_three_on_etf_and_index_maps(self):
        for filename in ('m1_us_etf_synthetic.json','m1_global_index_synthetic.json'):
            p=json.loads((ROOT/'examples'/filename).read_text())
            svg=m1.render_global_map(p)
            eligible=sorted([e for e in p['evidence'] if e['missing_status']=='ELIGIBLE'],
                            key=lambda x:(-m1._return(x),x['economy_id']))
            self.assertGreaterEqual(len(eligible),6)
            self.assertIn('TOP 3 FRONTRUNNERS',svg)
            self.assertIn('BOTTOM 3 LAGGARDS',svg)
            found=ET.fromstring(svg)
            cells=[x.text for x in found.iter() if x.tag.endswith('text')
                   and x.attrib.get('y') in ('1020','1074','1128')]
            for rank,e in enumerate(eligible[:3],1):
                suffix=(e['etf_ticker'] if p['return_basis']==m1.ETF_BASIS
                        else e['instrument_name'].split()[0])
                prefix=f"{rank}.  {e['economy_id']} / {suffix}"
                self.assertTrue(any((cell or '').startswith(prefix) for cell in cells),prefix)
            for rank,e in enumerate(reversed(eligible[-3:]),1):
                suffix=(e['etf_ticker'] if p['return_basis']==m1.ETF_BASIS
                        else e['instrument_name'].split()[0])
                prefix=f"{rank}.  {e['economy_id']} / {suffix}"
                self.assertTrue(any((cell or '').startswith(prefix) for cell in cells),prefix)
            leaders={e['economy_id'] for e in eligible[:3]}
            laggards={e['economy_id'] for e in eligible[-3:]}
            self.assertTrue(leaders.isdisjoint(laggards))

    def test_sparse_drafts_never_duplicate_markets_in_two_rankings(self):
        p=json.loads((ROOT/'examples'/'m1_us_etf_synthetic.json').read_text())
        eligible=[e for e in p['evidence'] if e['missing_status']=='ELIGIBLE']
        for e in eligible[4:]:
            e.update(missing_status='MISSING',session_status='UNVERIFIED',
                     close_price=None,prior_close_price=None,signed_return_pct=None,
                     observed_at=None,prior_observed_at=None,retrieved_at=None,
                     close_session_date=None,prior_session_date=None)
        svg=m1.render_global_map(p)
        self.assertIn('TOP 3 FRONTRUNNERS',svg)
        self.assertIn('BOTTOM 3 LAGGARDS',svg)
        self.assertIn('3.  —',svg)
        self.assertEqual(svg.count('3.  —'),2)

    def test_default_cli_requires_complete_brand_asset_and_sha_manifest(self):
        # Failing without a brand/image packet is deliberate; never claim
        # publication-looking when only a typographic P placeholder is present.
        stripped=[t for t in self.args if t not in (str(self.logo),)]
        stripped.remove('--brand-logo')
        self.assertEqual(m1_etf_daily.main(stripped),2)
        self.assertFalse(self.svg.exists())

    def test_exact_prompt2_unwatermarked_image_manifest_then_audit_without_rerender(self):
        self.assertEqual(self.build_candidate(),0)
        p=json.loads(self.issue.read_text())
        manifest=json.loads(self.manifest.read_text())
        svg=self.svg.read_text(encoding='utf-8')
        self.assertIn('TOP 3 FRONTRUNNERS',svg)
        self.assertIn('BOTTOM 3 LAGGARDS',svg)
        self.assertNotIn('DRAFT ·',svg)
        self.assertNotIn('DRAFT &#183;',svg)
        self.assertEqual(p['artifact_intent'],'EXACT_ARTIFACT_AWAITING_PROMPT3')
        self.assertFalse(manifest['publication_approved'])
        self.assertEqual(manifest['issue_sha256'],payload_hash(p))
        before=self.png.read_bytes()
        self.assertEqual(manifest['assets']['png']['sha256'],
                         hashlib.sha256(before).hexdigest())
        self.assertEqual(struct.unpack('>II',before[16:24]),(1080,1350))
        self.assertEqual(struct.unpack('>II',self.mobile.read_bytes()[16:24])[0],390)
        qa=self.mock_pass(manifest)
        with patch.object(m1_etf_daily,'APPROVED_LOGO_SHA256',self.logo_sha):
            approved=review(p,qa,manifest)
        self.assertEqual(approved['rights_note'],'PUBLIC_FACTS_QA_PASSED')
        self.assertEqual(self.png.read_bytes(),before)
        self.assertEqual(approved['caption'],p['caption'])

    def test_reject_changed_pixel_or_caption_or_missing_audit_hash(self):
        self.assertEqual(self.build_candidate(),0)
        p=json.loads(self.issue.read_text())
        manifest=json.loads(self.manifest.read_text())
        qa=self.mock_pass(manifest)
        with patch.object(m1_etf_daily,'APPROVED_LOGO_SHA256',self.logo_sha):
            for field in ('png_sha256','svg_sha256','mobile_png_sha256','caption_sha256'):
                bad=dict(qa);bad[field]='0'*64
                with self.subTest(field=field),self.assertRaises(InvalidIssue):
                    review(p,bad,manifest)
            changed=json.loads(json.dumps(p))
            changed['caption']+=' Unapproved alteration.'
            with self.assertRaises(InvalidIssue):
                review(changed,qa,manifest)
            self.png.write_bytes(self.png.read_bytes()+b'MODIFIED')
            with self.assertRaises(InvalidIssue):
                review(p,qa,manifest)

    def test_synthetic_demo_cannot_be_a_clean_pre_audit_candidate(self):
        p=json.loads((ROOT/'examples'/'m1_us_etf_synthetic.json').read_text())
        p['artifact_intent']='EXACT_ARTIFACT_AWAITING_PROMPT3'
        with patch.object(m1,'APPROVED_LOGO_SHA256',self.logo_sha):
            with self.assertRaises(InvalidIssue):
                m1.render_global_map(p,self.logo.read_bytes(),status='REVIEW_CANDIDATE')


    def test_one_through_five_supported_returns_never_block_clean_first_render(self):
        # All quotes and brand bytes in this test are invented fixtures.
        for n in (1,2,3,4,5):
            with self.subTest(genuine_candidate_count=n):
                rows=records(self.quotes)
                available=0
                for row in rows:
                    if not row['ticker']:
                        continue
                    available+=1
                    if available>n:
                        for k in ('prior_close','close','source_url',
                                  'prior_source_url','source_name',
                                  'corporate_action_status','source_use_status'):
                            row[k]=''
                with self.quotes.open('w',newline='',encoding='utf-8') as fp:
                    w=csv.DictWriter(fp,fieldnames=COLUMNS)
                    w.writeheader();w.writerows(rows)
                self.assertEqual(self.build_candidate(),0)
                p=json.loads(self.issue.read_text())
                svg=self.svg.read_text()
                self.assertEqual(p['map_product'],'MARKET_ATLAS_V1')
                self.assertEqual(len([e for e in p['evidence']
                                      if e['missing_status']=='ELIGIBLE']),n)
                self.assertIn('MARKET ATLAS',svg)
                self.assertIn('TOP 3 FRONTRUNNERS',svg)
                self.assertIn('BOTTOM 3 LAGGARDS',svg)
                self.assertNotIn('DRAFT ·',svg)
                self.assertNotIn('AUDIT ONLY',svg)
                self.assertNotIn('NOT FOR PUBLICATION',svg)
                self.assertEqual(json.loads(self.manifest.read_text())
                                 ['publication_approved'],False)
                self.assertEqual(struct.unpack('>II',
                                 self.png.read_bytes()[16:24]),(1080,1350))
                # Reinitialize full fictional set for the next isolated n.
                quote_sheet(self.quotes)

    def test_market_atlas_fixed_headline_and_panel_geometry(self):
        self.assertEqual(self.build_candidate(),0)
        p=json.loads(self.issue.read_text())
        base=m1.render_global_map(p,self.logo.read_bytes(),
                                  status='REVIEW_CANDIDATE')
        varied=json.loads(json.dumps(p))
        varied['headline']='The world in one U.S. session'
        for e in varied['evidence']:
            if e['missing_status']=='ELIGIBLE':
                e['close_price']=e['prior_close_price']*1.001
                e['signed_return_pct']=m1._return(e)
        variant=m1.render_global_map(varied,self.logo.read_bytes(),
                                     status='REVIEW_CANDIDATE')
        for fixed in ('MARKET ATLAS','TOP 3 FRONTRUNNERS',
                      'BOTTOM 3 LAGGARDS','NOT PLOTTED',
                      'EXACT 0.00%','ETF LEADERS &amp; LAGGARDS'):
            self.assertIn(fixed,base)
            self.assertIn(fixed,variant)
        def panel_positions(svg):
            root=ET.fromstring(svg)
            return [(el.attrib.get('x'),el.attrib.get('y'))
                    for el in root.iter() if el.tag.endswith('text')
                    and el.text in ('TOP 3 FRONTRUNNERS',
                                    'BOTTOM 3 LAGGARDS')]
        self.assertEqual(panel_positions(base),panel_positions(variant))
        self.assertNotIn('DRAFT ·',variant)


if __name__=='__main__':
    unittest.main()
