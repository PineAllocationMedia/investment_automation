"""Read-only, print-ready PAMalised HTML for an already assembled PRIVATE R1 report.

This presentation layer never selects securities, calculates returns, checks sources,
creates a PDF, saves files, uses networks, or upgrades evidence/portfolio authority.
The caller keeps the HTML private; it can be printed to PDF in an authorized UI.
"""
from __future__ import annotations

from html import escape
import re
from typing import Any

_ANNEX = "## Dossier détaillé et traçabilité (annexe)"
_HEADER = "# PAM R1 — Synthèse décisionnelle"
_MAX_CHARS = 2_000_000
_ALLOWED_STATUS = frozenset({"EXPLORATORY", "CONDITIONAL", "COMPONENT_SUPPORTED"})
_INLINE = re.compile(r"(\*\*[^*\n]+\*\*|`[^`\n]+`)")
_RULE = re.compile(r"^\|\s*:?-{3,}:?\s*(?:\|\s*:?-{3,}:?\s*)+\|?$")


def _text(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > 1024:
        raise ValueError("PAMALISED_" + name + "_INVALID")
    return value.strip()


def _inline(source: str) -> str:
    """Allow only two safe markdown typographic marks; never trust embedded HTML."""
    out = []
    for part in _INLINE.split(source):
        if part.startswith("**") and part.endswith("**") and len(part) > 4:
            out.append("<strong>" + escape(part[2:-2]) + "</strong>")
        elif part.startswith("`") and part.endswith("`") and len(part) > 2:
            out.append("<code>" + escape(part[1:-1]) + "</code>")
        else:
            out.append(escape(part))
    return "".join(out)


def _markdown_sections(source: str) -> str:
    """Minimal text-only subset for the existing executive; no arbitrary HTML."""
    lines = source.splitlines()
    output: list[str] = []
    index = 0
    while index < len(lines):
        raw = lines[index]
        line = raw.strip()
        if not line:
            index += 1
            continue
        if line == "---":
            output.append('<hr class="subtle">')
        elif line.startswith("## "):
            output.append('<h2>' + _inline(line[3:]) + '</h2>')
        elif line.startswith("# "):
            # The branded cover already has the title: retain any secondary
            # title only as a small subtitle, not a competing document title.
            output.append('<p class="source-label">' + _inline(line[2:]) + '</p>')
        elif line.startswith("- "):
            items = []
            while index < len(lines) and lines[index].strip().startswith("- "):
                items.append("<li>" + _inline(lines[index].strip()[2:]) + "</li>")
                index += 1
            output.append('<ul>' + ''.join(items) + '</ul>')
            continue
        elif (line.startswith("|") and index + 1 < len(lines)
              and _RULE.fullmatch(lines[index + 1].strip())):
            headings = [part.strip() for part in line.strip("|").split("|")]
            index += 2
            rows = []
            while index < len(lines) and lines[index].strip().startswith("|"):
                cells = [p.strip() for p in lines[index].strip().strip("|").split("|")]
                if len(cells) != len(headings):
                    break
                rows.append('<tr>' + ''.join('<td>' + _inline(p) + '</td>' for p in cells) + '</tr>')
                index += 1
            output.append('<div class="table-scroll"><table><thead><tr>'
                          + ''.join('<th>' + _inline(h) + '</th>' for h in headings)
                          + '</tr></thead><tbody>' + ''.join(rows) + '</tbody></table></div>')
            continue
        else:
            paragraph = [line]
            while (index + 1 < len(lines) and lines[index + 1].strip()
                   and not lines[index + 1].strip().startswith(("## ", "# ", "- ", "|"))
                   and lines[index + 1].strip() != "---"):
                index += 1
                paragraph.append(lines[index].strip())
            output.append('<p>' + _inline(' '.join(paragraph)) + '</p>')
        index += 1
    return '\n'.join(output)


def render_pamalised_html(*, executive_report: str, detailed_report: str,
                           analysis_id: str, as_of: str, strategy: str,
                           report_status: str) -> str:
    """Render a fully local HTML document from the *same validated* R1 pair.

    It has no API for custom investment decisions, unproven charts, inferred
    accounts or new facts. The original detailed text is retained exactly as
    visible text inside the escaped evidence annex.
    """
    aid = _text(analysis_id, "ANALYSIS_ID")
    date = _text(as_of, "DATE")
    mode = _text(strategy, "STRATEGY")
    status = _text(report_status, "STATUS")
    if status not in _ALLOWED_STATUS:
        raise ValueError("PAMALISED_STATUS_INVALID")
    if (not isinstance(executive_report, str) or not isinstance(detailed_report, str)
            or len(executive_report) > _MAX_CHARS or len(detailed_report) > _MAX_CHARS
            or not executive_report.startswith(_HEADER)
            or not detailed_report.startswith("# ")
            or executive_report.count(_ANNEX) != 1
            or not executive_report.endswith(detailed_report.rstrip("\n") + "\n")):
        raise ValueError("PAMALISED_VALIDATED_REPORT_PAIR_REQUIRED")
    first_read = executive_report.split(_ANNEX, 1)[0].rstrip()
    # The annex is *the exact original detail*. Never infer or reformat its
    # source status, evidence IDs, numeric figures or private observations.
    primary = _markdown_sections(first_read)
    details = escape(detailed_report.rstrip("\n"))
    # No external fonts, images, scripts, analytics, linked resources or network.
    css = """
@page { size: A4; margin: 14mm 13mm; }
:root { --dark:#0B2E24; --forest:#123F30; --mid:#56715E;
        --sage:#7F9A85; --cream:#FBF5E8; --pale:#F5EBD9; }
* { box-sizing:border-box; }
body { font-family:Arial,Helvetica,sans-serif; color:var(--dark); background:#fffdfa;
       margin:0; font-size:12px; line-height:1.53; }
.page { max-width:900px; margin:0 auto; padding:35px 42px; }
.brand { display:flex; justify-content:space-between; align-items:center;
         border-bottom:2px solid var(--dark); padding:0 0 16px; margin-bottom:20px; }
.brand strong { font-size:20px; letter-spacing:2px; }
.brand small { display:block; font-size:9px; letter-spacing:1.4px; }
.kicker { color:var(--mid); text-transform:uppercase; letter-spacing:2px; font-weight:700; }
h1 { font-size:35px; line-height:1.12; margin:15px 0 12px; letter-spacing:-.8px; }
h2 { font-size:18px; color:var(--forest); margin:24px 0 10px; padding:7px 0;
     border-bottom:1px solid #d6e0d7; break-after:avoid; }
p { margin:9px 0; overflow-wrap:anywhere; }
ul { margin:10px 0 14px; padding-left:21px; }
li { margin-bottom:5px; overflow-wrap:anywhere; }
.meta { display:grid; grid-template-columns:repeat(3,1fr); gap:8px; margin:22px 0; }
.meta div { background:#e7eee7; border-radius:8px; padding:12px 14px; min-width:0; }
.meta span { display:block; text-transform:uppercase; letter-spacing:.7px; font-size:9px;
             color:var(--mid); margin-bottom:6px; font-weight:bold; }
.meta strong { overflow-wrap:anywhere; font-size:12px; }
.source-label { color:var(--mid); font-size:10px; letter-spacing:.7px; }
.executive { background:#fff; border-left:5px solid var(--forest);
             border-radius:8px; padding:2px 17px 14px; }
.table-scroll { max-width:100%; overflow-x:auto; }
table { border-collapse:collapse; width:100%; table-layout:fixed; margin:12px 0; }
th { background:var(--forest); color:white; text-align:left; font-size:11px; }
th,td { padding:9px 10px; vertical-align:top; overflow-wrap:anywhere; }
tr:nth-child(2n) { background:#e8f0e8; }
tr { break-inside:avoid; }
.subtle { border:0; border-top:1px solid #d7dfd7; margin:22px 0; }
.appendix { break-before:page; margin-top:32px; }
.evidence { padding:15px; border:1px solid #d8dfd8; border-radius:8px;
            white-space:pre-wrap; overflow-wrap:anywhere; font-family:ui-monospace,monospace;
            font-size:10px; line-height:1.42; background:white; }
.status { padding:9px 12px; margin-top:16px; border-radius:6px;
          background:var(--cream); font-size:10px; }
.footer { border-top:1px solid #d8dfd8; margin-top:25px; padding-top:10px;
          font-size:9px; color:var(--mid); }
@media print { body { background:white; print-color-adjust:exact; -webkit-print-color-adjust:exact; }
  .page { max-width:none; padding:0; } h1,h2,.brand,.meta,.executive { break-inside:avoid; }
  .appendix { break-before:page; } }
@media(max-width:600px) { .page { padding:18px; } .meta { grid-template-columns:1fr; }
  h1 { font-size:29px; } }
"""
    return ('<!doctype html>\n<html lang="fr"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            '<meta name="referrer" content="no-referrer">'
            '<title>PAM Financial Systems — rapport d’analyse</title>'
            '<style>' + css + '</style></head><body><main class="page">'
            '<header class="brand"><div><strong>PAM</strong><small>FINANCIAL SYSTEMS</small></div>'
            '<span class="kicker">Rapport d’analyse</span></header>'
            '<div class="kicker">Analyse décisionnelle · document privé</div>'
            '<h1>Rapport d’analyse</h1>'
            '<div class="meta"><div><span>Analyse au</span><strong>' + escape(date)
            + '</strong></div><div><span>Stratégie</span><strong>' + escape(mode)
            + '</strong></div><div><span>État du dossier</span><strong>' + escape(status)
            + '</strong></div></div><p class="source-label">Analyse_ID : '
            + escape(aid) + '</p><section class="executive" aria-label="Synthèse">'
            + primary + '</section>'
            '<section class="appendix" aria-label="Dossier détaillé et traçabilité">'
            '<h2>Dossier détaillé et traçabilité — texte original conservé</h2>'
            '<p>Les faits, hypothèses, calculs, sources et limites figurent '
            'ci-dessous sous leur forme de rapport initiale, sans nouvelle vérification.</p>'
            '<pre class="evidence">' + details + '</pre></section>'
            '<div class="status">REPORT_EXPORT_STATUS: HTML_PRINT_READY_PDF_NOT_GENERATED'
            ' · ARCHIVE_NOT_SAVED sauf preuve indépendante contraire.'
            ' Aucune transaction ni calcul de rendement ajouté par cette présentation.</div>'
            '<footer class="footer">PAM / CONFIDENTIEL · DOCUMENT DE TRAVAIL'
            ' · Décision réservée à l’investisseur / CEO.</footer>'
            '</main></body></html>\n')
