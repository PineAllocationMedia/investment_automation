"""Process labels must never contaminate genuine-source artwork."""
import json
import unittest
import tempfile
from pathlib import Path

from artwork_status_guard import assert_clean_artwork, synthetic_issue, run
from render_macro_lens import render as macro
from render_company_lens import draw_company_lens
from render_market_brief import draw_market_brief
from render_sector_rotation import render_sector_rotation

ROOT = Path(__file__).resolve().parents[1]
def fixture(name):
    return json.loads((ROOT / 'examples' / (name + '_synthetic.json')).read_text(encoding='utf-8'))


class ArtworkStatusGuardTests(unittest.TestCase):
    def test_uploaded_meta_banner_and_footer_are_rejected(self):
        for label in ('DRAFT / NOT AUDITED',
                      'PREPARED 2026-10-23 / DRAFT NOT AUDITED',
                      'AUDIT ONLY', 'NOT FOR PUBLICATION',
                      'INTERNAL REVIEW', 'PENDING APPROVAL'):
            with self.subTest(label=label), self.assertRaises(ValueError):
                assert_clean_artwork('<svg><text>' + label + '</text></svg>')

    def test_svg_only_checks_visible_labels(self):
        assert_clean_artwork('<svg><!-- DRAFT manifest note --><text>SEC EDGAR</text>'
                             '<text>NOT INVESTMENT ADVICE</text></svg>')
        with self.assertRaises(ValueError):
            assert_clean_artwork('<svg><text><tspan>DRAFT</tspan></text></svg>')

    def test_synthetic_remains_labeled_in_each_family(self):
        for name, renderer in [
            ('t1', macro), ('t2', macro), ('t3', macro),
            ('e1', draw_company_lens), ('m2', render_sector_rotation),
            ('m4', draw_market_brief)
        ]:
            with self.subTest(name=name):
                self.assertIn('DRAFT', renderer(fixture(name)))

    def test_all_non_synthetic_source_candidate_previews_are_clean(self):
        # Fixtures here remain factually fictitious. Replacing URL/rights metadata
        # only tests presentation paths, NOT real source verification.
        for name in ('t1','t2','t3'):
            p=fixture(name)
            for f in p['evidence']:
                f['source_url']='https://www.bls.gov/news.release/cpi.t01.htm'
                f['verification_note']='layout-only evidence metadata'
            svg=macro(p, status='DRAFT')
            assert_clean_artwork(svg)
            self.assertNotIn('DRAFT', svg)
        p=fixture('e1')
        p['rights_note']='REVIEWED_FOR_EXACT_USE'
        p['cik']='0001234567'
        p['primary_filing_url']='https://www.sec.gov/Archives/edgar/data/1234567/demo.htm'
        for f in p['evidence']:
            f['source_url']=p['primary_filing_url']
        svg=draw_company_lens(p,status='DRAFT')
        assert_clean_artwork(svg)
        self.assertNotIn('DRAFT', svg)
        p=fixture('m2')
        p['rights_note']='REVIEWED_FOR_EXACT_USE'
        for f in p['evidence']:
            f['source_url']='https://www.spglobal.com/spdji/en/indices/equity/sp-500/'
            f['verification_note']='layout-only evidence metadata'
        svg=render_sector_rotation(p,status='DRAFT')
        assert_clean_artwork(svg)
        self.assertNotIn('DRAFT', svg)
        p=fixture('m4')
        for f in p['evidence']:
            f['source_url']='https://www.federalreserve.gov/releases/h15/'
            f['verification_note']='layout-only evidence metadata'
        svg=draw_market_brief(p,status='DRAFT')
        assert_clean_artwork(svg)
        self.assertNotIn('DRAFT', svg)

    def test_lint_cli_blocks_unreviewed_status_on_bespoke_svg(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'graphic.svg'
            path.write_text('<svg><text>DRAFT / NOT AUDITED</text></svg>')
            self.assertEqual(run([str(path)]),2)
            path.write_text('<svg><text>SEC EXHIBIT 99.1</text></svg>')
            self.assertEqual(run([str(path)]),0)


if __name__ == '__main__':
    unittest.main()
