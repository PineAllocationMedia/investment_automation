import json
import unittest
from pathlib import Path
from xml.etree import ElementTree as ET
from unittest.mock import patch

import pam_theme as theme
import render_macro_lens as macro
import render_company_lens as company
import render_market_brief as brief
import render_sector_rotation as sector
import render_global_index_map as atlas
import t1_evidence_plus as plus

ROOT = Path(__file__).resolve().parents[1]


class ThemeTests(unittest.TestCase):
    def test_all_families_use_reference_background(self):
        for module in (macro, company, brief, sector, atlas, plus):
            self.assertEqual(module.BG, '#0F2429')
            self.assertEqual(module.AMBER, '#E7C691')

    def test_rendered_background_and_synthetic_safeguard(self):
        cases = [('t1', macro.render), ('t2', macro.render),
                 ('t3', macro.render), ('e1', company.draw_company_lens),
                 ('m4', brief.draw_market_brief),
                 ('m2', sector.render_sector_rotation)]
        for code, render in cases:
            with self.subTest(code=code):
                payload = json.loads((ROOT/'examples'/f'{code}_synthetic.json').read_text())
                svg = render(payload)
                ET.fromstring(svg)
                self.assertIn(theme.BG, svg)
                self.assertNotIn('#11242A', svg)
                self.assertIn('SYNTHETIC', svg)

    def test_theme_revision_invalidates_old_approval(self):
        payload = json.loads((ROOT/'examples'/'t1_synthetic.json').read_text())
        original = macro.payload_hash(payload)
        with patch.object(macro, 'THEME_VERSION', 'different-theme'):
            self.assertNotEqual(original, macro.payload_hash(payload))


if __name__ == '__main__':
    unittest.main()
