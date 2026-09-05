import base64
import shutil
import tempfile
import unittest
from html.parser import HTMLParser
from pathlib import Path
from unittest.mock import patch
from xml.etree import ElementTree

from src.account_charts import (
    MAX_EMBEDDED_CHART_BYTES,
    build_account_allocation_chart_rows,
    embed_account_charts_in_html,
)
from src.report_generator import compact_account_charts_markdown, generate_reports
from src.utils import markdown_to_html


class _Images(HTMLParser):
    def __init__(self, source):
        super().__init__()
        self.images = []
        self.feed(source)

    def handle_starttag(self, tag, attrs):
        if tag == "img":
            self.images.append(dict(attrs))


class CompactReportPortabilityTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.reports = self.root / "reports"
        self.holdings = [
            {"ticker": "FIXTURE_A", "account_type": "TFSA1", "current_value": 1000},
            {"ticker": "FIXTURE_B", "account_type": "TFSA1", "current_value": 500},
            {"ticker": "FIXTURE_C", "account_type": "FHSA", "current_value": 250},
        ]
        self.rows = build_account_allocation_chart_rows(self.holdings, self.reports / "charts")
        self.markdown = "\n".join(compact_account_charts_markdown(self.rows))
        self.original_html = markdown_to_html(self.markdown)

    def render(self):
        return embed_account_charts_in_html(self.original_html, self.reports, self.rows)

    def assert_embedded(self, source, expected):
        images = _Images(source).images
        self.assertEqual(len(images), len(expected))
        for image, content in zip(images, expected):
            self.assertTrue(image["src"].startswith("data:image/svg+xml;base64,"))
            decoded = base64.b64decode(image["src"].split(",", 1)[1], validate=True)
            self.assertEqual(decoded, content)
            self.assertEqual(ElementTree.fromstring(decoded).tag, "{http://www.w3.org/2000/svg}svg")
        self.assertNotIn('src="charts/account_', source)

    def test_generated_svgs_are_embedded_exactly_for_multiple_accounts(self):
        self.assertEqual([row["account_type"] for row in self.rows], ["FHSA", "TFSA1", "ALL_ACCOUNTS"])
        expected = [(self.reports / row["chart_path"]).read_bytes() for row in self.rows]
        self.assert_embedded(self.render(), expected)
        self.assertEqual(self.render(), self.render())
        self.assertEqual(self.markdown, "\n".join(compact_account_charts_markdown(self.rows)))
        self.assertIn('src="charts/account_TFSA1.svg"', self.original_html)

    def test_standalone_copy_keeps_chart_content_after_chart_directory_is_removed(self):
        expected = [(self.reports / row["chart_path"]).read_bytes() for row in self.rows]
        source = self.reports / "latest_report_compact_high_cagr.html"
        source.write_text(self.render(), encoding="utf-8")
        downloaded = self.root / "downloaded.html"
        shutil.copy2(source, downloaded)
        shutil.rmtree(self.reports / "charts")
        self.assertFalse((self.reports / "charts").exists())
        self.assert_embedded(downloaded.read_text(encoding="utf-8"), expected)

    def test_missing_chart_has_visible_fallback_and_other_charts_still_embed(self):
        (self.reports / self.rows[0]["chart_path"]).unlink()
        rendered = self.render()
        self.assertIn("Graphique indisponible — Répartition FHSA", rendered)
        self.assert_embedded(rendered, [(self.reports / row["chart_path"]).read_bytes() for row in self.rows[1:]])

    def test_unreadable_chart_has_fallback_without_crashing(self):
        with patch.object(Path, "open", side_effect=PermissionError("fixture unreadable")):
            rendered = self.render()
        self.assertEqual(rendered.count("Graphique indisponible"), 3)
        self.assertIn("illisible", rendered)
        self.assertEqual(_Images(rendered).images, [])
        self.assertNotIn('src="charts/account_', rendered)

    def test_empty_or_oversized_chart_has_fallback(self):
        path = self.reports / self.rows[0]["chart_path"]
        for content in (b"", b" " * (MAX_EMBEDDED_CHART_BYTES + 1)):
            with self.subTest(size=len(content)):
                path.write_bytes(content)
                rendered = self.render()
                self.assertIn("Graphique indisponible — Répartition FHSA", rendered)
                self.assertEqual(len(_Images(rendered).images), 2)

    def test_total_embedding_budget_is_bounded_and_deterministic(self):
        first = (self.reports / self.rows[0]["chart_path"]).read_bytes()
        budget = 4 * ((len(first) + 2) // 3)
        with patch("src.account_charts.MAX_EMBEDDED_CHARTS_BASE64_BYTES", budget):
            rendered = self.render()
            self.assertEqual(rendered, self.render())
        self.assert_embedded(rendered, [first])
        self.assertEqual(rendered.count("Graphique indisponible"), 2)

    def test_only_known_chart_assets_are_read(self):
        unknown = self.reports / "charts" / "account_UNKNOWN.svg"
        unknown.write_text("must not be embedded", encoding="utf-8")
        source = markdown_to_html("![Unknown](charts/account_UNKNOWN.svg)")
        with patch.object(Path, "open") as read:
            rendered = embed_account_charts_in_html(source, self.reports, self.rows)
        read.assert_not_called()
        self.assertIn("Graphique indisponible — Unknown", rendered)
        self.assertEqual(_Images(rendered).images, [])

    def test_traversal_and_arbitrary_asset_paths_in_rows_are_rejected(self):
        for src in (
            "charts/account_../../secret.svg",
            "charts/account_%2e%2e%2fsecret.svg",
            "charts/account_sub/nested.svg",
            "charts/other.svg",
            "../secret.svg",
            str(self.root / "secret.svg"),
            "https://example.com/account_remote.svg",
        ):
            with self.subTest(src=src), patch.object(Path, "open") as read:
                rendered = embed_account_charts_in_html(
                    markdown_to_html(f"![Unsafe]({src})"), self.reports, [{"chart_path": src}]
                )
                read.assert_not_called()
                self.assertIn("Graphique indisponible — Unsafe", rendered)
                self.assertEqual(_Images(rendered).images, [])

    def test_file_symlink_is_rejected(self):
        path = self.reports / self.rows[0]["chart_path"]
        outside = self.root / "outside.svg"
        path.rename(outside)
        path.symlink_to(outside)
        rendered = self.render()
        self.assertIn("Graphique indisponible — Répartition FHSA", rendered)
        self.assertEqual(len(_Images(rendered).images), 2)

    def test_chart_directory_symlink_is_rejected(self):
        charts = self.reports / "charts"
        outside = self.root / "outside"
        charts.rename(outside)
        charts.symlink_to(outside, target_is_directory=True)
        with patch.object(Path, "open") as read:
            rendered = self.render()
        read.assert_not_called()
        self.assertEqual(rendered.count("Graphique indisponible"), 3)
        self.assertEqual(_Images(rendered).images, [])

    def test_non_chart_rendering_is_preserved_verbatim(self):
        markdown = """# Rapport & détails

**Gras**, *italique*, `code`, [lien](https://example.com).

| A | B |
| --- | --- |
| 1 | 2 |

<details markdown="1"><summary>Détails</summary>

Texte **interne**.

</details>

![Autre](charts/other.svg)
![Distant](https://example.com/chart.svg)

    <img src="charts/account_TFSA1.svg">

<!-- <img src="charts/account_TFSA1.svg"> -->
"""
        original = markdown_to_html(markdown)
        self.assertEqual(embed_account_charts_in_html(original, self.reports, self.rows), original)
        self.assertEqual(embed_account_charts_in_html(original, self.reports, []), original)
        # In a mixed document only the chart tag changes, including multiline tags.
        chart = '<img\n alt="Répartition &amp; test"\n src="charts/account_TFSA1.svg">'
        rendered = embed_account_charts_in_html(original + chart + "\nfin", self.reports, self.rows)
        self.assertTrue(rendered.startswith(original))
        self.assertTrue(rendered.endswith("\nfin"))
        self.assertIn('alt="Répartition &amp; test"', rendered)

    def test_fallback_escapes_alt_text(self):
        source = '<img src="charts/account_MISSING.svg" alt="&lt;script&gt;&amp;&quot;">'
        rendered = embed_account_charts_in_html(source, self.reports, [])
        self.assertIn("Graphique indisponible — &lt;script&gt;&amp;&quot;", rendered)
        self.assertNotIn("<script>", rendered)

    def test_generate_reports_embeds_telegram_output_and_preserves_markdown_and_full_html(self):
        # Reporting only, zero capital, no analysis command or operational history writes.
        with patch("src.report_generator.DATA_DIR", self.root / "data"), patch(
            "src.report_generator.today_iso", return_value="2026-09-05"
        ):
            generate_reports(
                self.reports, "high-cagr", 0, {}, {"allocations": []}, {}, [], self.holdings, [], []
            )
        expected = [(self.reports / row["chart_path"]).read_bytes() for row in self.rows]
        compact = (self.reports / "latest_report_compact.html").read_text(encoding="utf-8")
        delivered = (self.reports / "latest_report_compact_high_cagr.html").read_text(encoding="utf-8")
        self.assertEqual(compact, delivered)
        self.assert_embedded(delivered, expected)
        for name in ("latest_report", "latest_report_compact"):
            markdown = (self.reports / f"{name}.md").read_text(encoding="utf-8")
            self.assertIn("![Répartition TFSA1](charts/account_TFSA1.svg)", markdown)
            self.assertNotIn("data:image", markdown)
            self.assertEqual(markdown, (self.reports / f"{name}_high_cagr.md").read_text(encoding="utf-8"))
        full_markdown = (self.reports / "latest_report.md").read_text(encoding="utf-8")
        full_html = (self.reports / "latest_report.html").read_text(encoding="utf-8")
        self.assertEqual(full_html, markdown_to_html(full_markdown))
        self.assertIn('src="charts/account_TFSA1.svg"', full_html)


if __name__ == "__main__":
    unittest.main()
