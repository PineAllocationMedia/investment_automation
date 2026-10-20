"""M2 synthetic sector-rotation correctness and mobile research-layout tests."""
import copy
import json
import math
import struct
import tempfile
import unittest
from pathlib import Path
from xml.etree import ElementTree as ET

from render_sector_rotation import (
    SECTORS, _returns, move_text, render_sector_rotation,
    validate_sector_rotation, run,
)
from render_macro_lens import InvalidIssue, payload_hash, release_allowed

EX = Path(__file__).resolve().parents[1] / 'examples' / 'm2_synthetic.json'


def fixture():
    return json.loads(EX.read_text())


def text_spans(svg):
    import fitz
    page = fitz.open(stream=svg.encode('utf-8'), filetype='svg')[0]
    spans = [span for block in page.get_text('dict')['blocks']
             for line in block.get('lines', [])
             for span in line['spans']]
    return spans, page


class M2RotationTests(unittest.TestCase):
    def test_all_eleven_ranked_and_comparable(self):
        p = fixture()
        ranked = validate_sector_rotation(p)
        self.assertEqual(len(ranked), 11)
        self.assertEqual({r['sector'] for r in ranked}, set(SECTORS))
        moves = [_returns(r)[0] for r in ranked]
        self.assertEqual(moves, sorted(moves, reverse=True))
        self.assertEqual(ranked[0]['sector'], 'Information Technology')
        self.assertEqual(ranked[-1]['sector'], 'Energy')
        svg = render_sector_rotation(p)
        for field in ['SECTOR ROTATION', '20-SESSION PRICE RETURN',
                      '20S PRICE MOVE', '11 SECTORS', '20S %',
                      '1D %', 'BREADTH', '7/11 POSITIVE',
                      'LEADER', 'RANKED', 'READING', 'WATCH',
                      'NOT INVESTMENT ADVICE', 'DRAFT', 'SYNTHETIC TEST']:
            self.assertIn(field, svg)
        for sector in SECTORS:
            self.assertIn(sector, svg)
        self.assertEqual(ET.fromstring(svg).attrib['width'], '1080')
        self.assertEqual(ET.fromstring(svg).attrib['height'], '1350')

    def test_no_implicit_synchronization_or_total_return(self):
        svg = render_sector_rotation(fixture())
        self.assertIn('20-SESSION PRICE RETURN', svg)
        self.assertIn('LOCAL', fixture()['basis'])
        self.assertNotIn('TOTAL RETURN', svg)
        self.assertIn('AS OF 2026-10-20 17:05 -0400', svg)
        self.assertNotIn('BUY ', svg)

    def test_missing_sector_hold(self):
        p = fixture()
        p['evidence'].pop()
        with self.assertRaises(InvalidIssue):
            validate_sector_rotation(p)

    def test_duplicate_sector_hold(self):
        p = fixture()
        p['evidence'][1]['sector'] = p['evidence'][0]['sector']
        with self.assertRaises(InvalidIssue):
            validate_sector_rotation(p)

    def test_mixed_index_family_hold(self):
        p = fixture()
        p['evidence'][2]['index_family'] = 'UNRELATED_PROVIDER'
        with self.assertRaises(InvalidIssue):
            validate_sector_rotation(p)

    def test_currency_mismatch_hold(self):
        p = fixture()
        p['evidence'][6]['currency'] = 'CAD'
        with self.assertRaises(InvalidIssue):
            validate_sector_rotation(p)

    def test_mixed_observation_clocks_hold(self):
        p = fixture()
        p['evidence'][0]['observed_at'] = '2026-10-20T16:30:00-04:00'
        with self.assertRaises(InvalidIssue):
            validate_sector_rotation(p)

    def test_stale_close_hold(self):
        p = fixture()
        p['evidence'][1]['observed_at'] = '2026-10-10T16:00:00-04:00'
        with self.assertRaises(InvalidIssue):
            validate_sector_rotation(p)

    def test_synthetic_url_only_example_domains(self):
        p = fixture()
        p['evidence'][0]['source_url'] = 'https://a-provider.org/data'
        with self.assertRaises(InvalidIssue):
            validate_sector_rotation(p)

    def test_bad_source_url_hold(self):
        p = fixture()
        p['evidence'][0]['source_url'] = 'javascript:alert(1)'
        with self.assertRaises(InvalidIssue):
            validate_sector_rotation(p)

    def test_negative_or_nan_index_level_hold(self):
        for val in [-1, math.nan, 0, float('inf')]:
            p = fixture()
            p['evidence'][4]['lookback_close'] = val
            with self.subTest(value=str(val)), self.assertRaises(InvalidIssue):
                validate_sector_rotation(p)

    def test_lookback_metadata_wrong_hold(self):
        p = fixture()
        p['lookback_sessions'] = 19
        with self.assertRaises(InvalidIssue):
            validate_sector_rotation(p)

    def test_ineligible_session_hold(self):
        p = fixture()
        p['evidence'][3]['session_status'] = 'HOLIDAY'
        with self.assertRaises(InvalidIssue):
            validate_sector_rotation(p)

    def test_unsourced_verification_hold(self):
        p = fixture()
        p['evidence'][2]['verification'] = 'UNVERIFIED'
        with self.assertRaises(InvalidIssue):
            validate_sector_rotation(p)

    def test_unauthorized_bases_hold(self):
        for bad in ['ETF_USD_PRICE', 'TOTAL_RETURN_INDEX', None]:
            p = fixture()
            p['basis'] = bad
            with self.subTest(basis=bad), self.assertRaises(InvalidIssue):
                validate_sector_rotation(p)

    def test_release_not_automatically_authorized(self):
        p = fixture()
        approval = {'input_sha256': payload_hash(p), 'independent_audit': 'PASS',
                    'ceo_approved': True, 'auditor_reference': 'test',
                    'ceo_approval_reference': 'test'}
        with self.assertRaises(InvalidIssue):
            release_allowed(p, approval)
        with self.assertRaises(InvalidIssue):
            render_sector_rotation(p, status='RELEASE')
        q = copy.deepcopy(p)
        q['interpretation'] = 'Revised after approval'
        self.assertNotEqual(payload_hash(q), payload_hash(p))

    def test_zero_return_is_not_missing(self):
        p = fixture()
        f = p['evidence'][2]
        f['close'] = f['prior_close'] = f['lookback_close']
        svg = render_sector_rotation(p)
        self.assertIn('0.00%', svg)
        self.assertEqual(move_text(0), '0.00%')

    def test_native_and_mobile_390px_geometry(self):
        try:
            import fitz
        except ImportError:
            self.skipTest('PyMuPDF required for real glyph boxes')
        svg = render_sector_rotation(fixture())
        spans, page = text_spans(svg)
        native = page.get_pixmap(matrix=fitz.Matrix(1, 1), alpha=False)
        self.assertEqual((native.width, native.height), (1080, 1350))
        mobile = page.get_pixmap(matrix=fitz.Matrix(390/1080, 390/1080),
                                alpha=False)
        self.assertEqual(mobile.width, 390)
        self.assertGreaterEqual(mobile.height, 487)
        for sp in spans:
            x0, y0, x1, y1 = sp['bbox']
            self.assertGreaterEqual(x0, 54, sp['text'])
            self.assertLessEqual(x1, 1022, sp['text'])
            self.assertGreaterEqual(y0, 43, sp['text'])
            self.assertLessEqual(y1, 1342, sp['text'])
        # Rows must not collide in real rendered glyph geometry.
        rank_lines = [sp for sp in spans if
                      len(sp['text']) > 4 and
                      sp['text'][:2].isdigit() and sp['text'][2:4] == '  ']
        self.assertEqual(len(rank_lines), 11)
        for upper, lower in zip(rank_lines, rank_lines[1:]):
            self.assertLess(upper['bbox'][3] + 5, lower['bbox'][1])
        interp = next(sp for sp in spans if sp['text'] == 'READING')
        watch = next(sp for sp in spans if sp['text'] == 'WATCH')
        self.assertLess(interp['bbox'][3] + 10, watch['bbox'][1])
        footer = next(sp for sp in spans if
                      sp['text'].startswith('FULL ORIGINAL INDEX SERIES'))
        asof = next(sp for sp in spans if sp['text'].startswith('AS OF '))
        self.assertLess(watch['bbox'][3] + 15, footer['bbox'][1])
        self.assertLess(footer['bbox'][3] + 5, asof['bbox'][1])

    def test_cli_writes_only_after_validation(self):
        try:
            import fitz
        except ImportError:
            self.skipTest('PyMuPDF required')
        with tempfile.TemporaryDirectory() as tmp:
            svg=Path(tmp)/'draft.svg'
            png=Path(tmp)/'draft.png'
            self.assertEqual(run([str(EX), '--output',str(svg), '--png',str(png)]), 0)
            self.assertEqual(struct.unpack('>II',png.read_bytes()[16:24]),(1080,1350))
            self.assertIn('DRAFT', svg.read_text())
            before=svg.read_bytes()
            wrong=fixture()
            wrong['evidence'][0]['verification']='UNKNOWN'
            p=Path(tmp)/'invalid.json'
            p.write_text(json.dumps(wrong))
            self.assertEqual(run([str(p),'--output',str(svg),'--png',str(png)]),2)
            self.assertEqual(svg.read_bytes(), before)


if __name__=='__main__':
    unittest.main()
