"""Fail-closed, source-bound synthetic tests for M4 Cross-Asset Market Brief."""
import copy
import json
import math
import struct
import tempfile
import unittest
from pathlib import Path
from xml.etree import ElementTree as ET

from render_market_brief import validate_market_brief, draw_market_brief, run
from render_macro_lens import InvalidIssue, payload_hash, release_allowed

EX = Path(__file__).resolve().parents[1] / 'examples'


def demo(kind='m4'):
    return json.loads((EX / (kind + '_synthetic.json')).read_text())


class M4MarketBriefTests(unittest.TestCase):
    def test_render_five_distinct_source_rows_and_draft_guard(self):
        p = demo()
        rows = validate_market_brief(p)
        self.assertEqual([r['asset_group'] for r in rows],
                         ['EQUITIES','EQUITIES','RATES','FX','COMMODITIES'])
        svg = draw_market_brief(p)
        root = ET.fromstring(svg)
        self.assertEqual(root.attrib['width'], '1080')
        self.assertEqual(root.attrib['height'], '1350')
        for field in ('PAM', 'MARKET BRIEF', 'LATEST COMPLETED SESSIONS',
                      'PUBLISHER / LOCAL CLOSE PER ROW', 'CROSS-ASSET INTERPRETATION',
                      'NEXT CONFIRMATION', 'NOT INVESTMENT ADVICE',
                      'DRAFT', '+0.80%', '-3.00 bp', '-0.96%', 'DEMO ONLY'):
            self.assertIn(field, svg)
        self.assertNotIn('THE MACRO LENS', svg)
        self.assertNotIn('BUY NOW', svg)

    def test_four_row_mode_and_non_synchronous_closes_allowed(self):
        p = demo('m4_four_row')
        p['evidence'][1]['observed_at'] = '2026-10-20T16:30:00-05:00'
        p['evidence'][1]['retrieved_at'] = '2026-10-20T18:00:00-04:00'
        # A 16:30 -05:00 close occurs at 17:30 -04:00, before the issue cutoff.
        self.assertEqual(len(validate_market_brief(p)), 4)
        self.assertIn('LATEST COMPLETED SESSIONS', draw_market_brief(p))

    def test_release_requires_logo_even_if_approval_claimed(self):
        p = demo()
        with self.assertRaises(InvalidIssue):
            draw_market_brief(p, status='RELEASE')
        approval={'input_sha256':payload_hash(p),'independent_audit':'PASS',
                  'ceo_approved':True,'auditor_reference':'synthetic-test',
                  'ceo_approval_reference':'synthetic-test'}
        with self.assertRaises(InvalidIssue):
            release_allowed(p, approval)
        modified=copy.deepcopy(p)
        modified['caption']='caption edited after review'
        self.assertNotEqual(payload_hash(p), payload_hash(modified))

    def test_not_an_api_feed(self):
        p=demo()
        self.assertFalse(any('live' in x for x in p))
        self.assertIn('SYNTHETIC', p['caption'])
        self.assertTrue(all('example.org' in f['source_url'] for f in p['evidence']))

    def test_wrong_group_order_fails(self):
        p=demo()
        p['evidence'][1]['asset_group']='CREDIT'
        with self.assertRaises(InvalidIssue): validate_market_brief(p)

    def test_inadequate_coverage_fails(self):
        p=demo()
        p['evidence'].pop()
        # Remaining four rows contain two equities but no commodity; HOLD.
        with self.assertRaises(InvalidIssue): validate_market_brief(p)

    def test_unauthenticated_source_fails(self):
        p=demo()
        p['evidence'][0]['verification']='UNKNOWN'
        with self.assertRaises(InvalidIssue): validate_market_brief(p)

    def test_bad_url_fails(self):
        p=demo()
        p['evidence'][0]['source_url']='javascript:alert(1)'
        with self.assertRaises(InvalidIssue): validate_market_brief(p)

    def test_level_mismatch_fails(self):
        p=demo()
        p['evidence'][0]['display']='5,102.50'
        with self.assertRaises(InvalidIssue): validate_market_brief(p)

    def test_percent_bp_mix_fails(self):
        p=demo()
        p['evidence'][2]['change_display']='-3.00%'
        with self.assertRaises(InvalidIssue): validate_market_brief(p)

    def test_incorrect_change_sign_fails(self):
        p=demo()
        p['evidence'][4]['change_display']='+0.96%'
        with self.assertRaises(InvalidIssue): validate_market_brief(p)

    def test_rate_observation_mismatch_fails(self):
        p=demo()
        p['evidence'][2]['numeric_change']=-2.0
        with self.assertRaises(InvalidIssue): validate_market_brief(p)

    def test_price_move_mismatch_fails(self):
        p=demo()
        p['evidence'][3]['previous_numeric_value']=1.14
        with self.assertRaises(InvalidIssue): validate_market_brief(p)

    def test_nonfinite_fails(self):
        p=demo()
        p['evidence'][0]['numeric_value']=math.nan
        with self.assertRaises(InvalidIssue): validate_market_brief(p)

    def test_mixed_sessions_explicitly_labeled_not_simultaneous(self):
        p=demo()
        p['evidence'][2]['observed_at']='2026-10-20T16:00:00+01:00'
        # Same session date but different instant is valid; never label as a
        # synchronized intraday comparison or invented same-session performance.
        self.assertIn('LATEST COMPLETED SESSIONS', draw_market_brief(p))

    def test_stale_market_refused(self):
        p=demo()
        p['evidence'][3]['observed_at']='2026-10-10T16:00:00-04:00'
        with self.assertRaises(InvalidIssue): validate_market_brief(p)

    def test_closed_market_not_a_zero(self):
        p=demo()
        p['evidence'][1]['session_status']='HOLIDAY'
        with self.assertRaises(InvalidIssue): validate_market_brief(p)

    def test_retrieved_after_brief_refused(self):
        p=demo()
        p['evidence'][1]['retrieved_at']='2026-10-21T02:00:00-04:00'
        with self.assertRaises(InvalidIssue): validate_market_brief(p)

    def test_date_must_match_local_session(self):
        p=demo()
        p['evidence'][0]['period']='2026-10-19'
        with self.assertRaises(InvalidIssue): validate_market_brief(p)

    def test_oversized_copy_refused(self):
        p=demo()
        p['headline']='Giant institution-sized capital market slogan. '*2
        with self.assertRaises(InvalidIssue): draw_market_brief(p)

    def test_clear_market_tape_columns_and_local_session_clocks(self):
        p=demo()
        svg=draw_market_brief(p)
        for heading in ('MARKET / SOURCE / SESSION', 'LAST', 'SESSION MOVE',
                        'CROSS-ASSET INTERPRETATION', 'NEXT CONFIRMATION'):
            self.assertIn(heading,svg)
        self.assertEqual(svg.count('10-20 16:00-0400'),len(p['evidence']))
        self.assertIn('AS OF 2026-10-20 18:00 -0400',svg)
        self.assertNotIn('AS OF 2026-10-20T',svg)
        self.assertNotIn('SOURCES PER ROW  /',svg)

    def test_two_different_local_close_clocks_are_visible(self):
        p=demo('m4_four_row')
        p['evidence'][1]['observed_at']='2026-10-20T16:30:00-05:00'
        p['evidence'][1]['retrieved_at']='2026-10-20T18:00:00-04:00'
        svg=draw_market_brief(p)
        self.assertIn('10-20 16:00-0400',svg)
        self.assertIn('10-20 16:30-0500',svg)

    def test_source_overflows_are_not_silently_cut(self):
        p=demo()
        p['evidence'][0]['source_title']='W'*24
        with self.assertRaises(InvalidIssue): draw_market_brief(p)

    def test_confirmation_label_never_collides_with_watch_text(self):
        try:
            import fitz
        except ImportError:
            self.skipTest('PyMuPDF required for collision check')
        p=demo()
        svg=draw_market_brief(p)
        page=fitz.open(stream=svg.encode('utf-8'), filetype='svg')[0]
        spans=[sp for block in page.get_text('dict')['blocks']
               for line in block.get('lines', [])
               for sp in line['spans']]
        heading=next(x for x in spans if x['text']=='NEXT CONFIRMATION')
        watch=[x for x in spans if 'Watch for confirmation' in x['text']]
        self.assertEqual(len(watch),1)
        self.assertLessEqual(heading['bbox'][2]+12,watch[0]['bbox'][0])
        footer=next(x for x in spans if x['text'].startswith('PUBLISHER /'))
        self.assertLess(watch[0]['bbox'][3]+20,footer['bbox'][1])

    def test_native_png_and_mobile_text_bounds(self):
        try:
            import fitz
        except ImportError:
            self.skipTest('PyMuPDF needed for text bounds')
        for n in ('m4', 'm4_four_row'):
            with self.subTest(fixture=n):
                p=demo(n)
                svg=draw_market_brief(p)
                page=fitz.open(stream=svg.encode('utf-8'),filetype='svg')[0]
                pix=page.get_pixmap(matrix=fitz.Matrix(1,1),alpha=False)
                self.assertEqual((pix.width,pix.height),(1080,1350))
                spans=[span for block in page.get_text('dict')['blocks']
                       for line in block.get('lines', [])
                       for span in line['spans']]
                for sp in spans:
                    x0,y0,x1,y1=sp['bbox']
                    self.assertGreaterEqual(x0,55,sp['text'])
                    self.assertLessEqual(x1,1022,sp['text'])
                    self.assertGreaterEqual(y0,40,sp['text'])
                    self.assertLessEqual(y1,1342,sp['text'])
                sources=[x for x in spans if 'DEMO ONLY' in x['text']]
                self.assertEqual(len(sources),len(p['evidence']))
                source_footer=next(x for x in spans if x['text'].startswith('PUBLISHER / LOCAL CLOSE PER ROW'))
                asof=next(x for x in spans if x['text'].startswith('AS OF '))
                self.assertLess(source_footer['bbox'][3]+10,asof['bbox'][1])
                self.assertLess(asof['bbox'][2]+15,
                                next(x for x in spans if x['text']=='NOT INVESTMENT ADVICE')['bbox'][0])

    def test_cli_writes_both_outputs_after_validation(self):
        try:
            import fitz
        except ImportError:
            self.skipTest('PyMuPDF required')
        with tempfile.TemporaryDirectory() as tmp:
            svg=Path(tmp)/'draft.svg'
            png=Path(tmp)/'draft.png'
            self.assertEqual(run([str(EX/'m4_synthetic.json'),
                                  '--output',str(svg),'--png',str(png)]),0)
            self.assertTrue(svg.read_text().startswith('<svg'))
            self.assertEqual(struct.unpack('>II',png.read_bytes()[16:24]),(1080,1350))
            p=demo()
            p['evidence'][0]['verification']='UNKNOWN'
            invalid=Path(tmp)/'invalid.json';invalid.write_text(json.dumps(p))
            before=svg.read_bytes()
            self.assertEqual(run([str(invalid),'--output',str(svg),'--png',str(png)]),2)
            self.assertEqual(svg.read_bytes(),before)


if __name__=='__main__':
    unittest.main()
