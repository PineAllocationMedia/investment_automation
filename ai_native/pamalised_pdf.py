"""Private PAMalised PDF bytes from an already validated R1 executive/detail pair.

No network, source lookup, calculations, filesystem write, trade or source upgrade.
ReportLab is an optional BSD-licensed local PDF dependency.
"""
from __future__ import annotations

from html import escape
from io import BytesIO
import re

from .pamalised_report import render_pamalised_html

_ANNEX = "## Dossier détaillé et traçabilité (annexe)"
_MAX_TEXT = 200_000


def _markup(text: str) -> str:
    """Escape untrusted text before rendering ReportLab's limited formatting."""
    parts = re.split(r"(\*\*[^*\n]+\*\*|`[^`\n]+`)", text)
    out = []
    for part in parts:
        if part.startswith("**") and part.endswith("**") and len(part) > 4:
            out.append("<b>" + escape(part[2:-2]) + "</b>")
        elif part.startswith("`") and part.endswith("`") and len(part) > 2:
            out.append('<font face="Courier">' + escape(part[1:-1]) + "</font>")
        else:
            out.append(escape(part))
    return "".join(out)


def render_pamalised_pdf(*, executive_report: str, detailed_report: str,
                         analysis_id: str, as_of: str, strategy: str,
                         report_status: str) -> bytes:
    """Create only in-memory PDF bytes from original R1 pair; no storage."""
    # Same strict source/authority/parity validation as the merged HTML renderer.
    render_pamalised_html(executive_report=executive_report,
                          detailed_report=detailed_report, analysis_id=analysis_id,
                          as_of=as_of, strategy=strategy,
                          report_status=report_status)
    if len(executive_report) > _MAX_TEXT or len(detailed_report) > _MAX_TEXT:
        raise ValueError("PAMALISED_PDF_INPUT_TOO_LARGE")
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import ParagraphStyle
        from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer,
                                       Table, TableStyle, HRFlowable)
    except ImportError as exc:
        raise RuntimeError("PAMALISED_PDF_REPORTLAB_NOT_INSTALLED") from exc

    buffer = BytesIO()
    page_w, page_h = A4
    doc = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=43,
                            rightMargin=43, topMargin=66, bottomMargin=55,
                            title="PAM Financial Systems - Rapport d analyse",
                            author="PAM Financial Systems", pageCompression=1)
    dark = colors.HexColor("#0B2E24")
    forest = colors.HexColor("#123F30")
    sage = colors.HexColor("#7F9A85")
    pale = colors.HexColor("#E4EDE5")
    normal = ParagraphStyle("NormalPAM", fontName="Helvetica", fontSize=9.2,
                            leading=13.2, textColor=dark,
                            spaceAfter=8, wordWrap="LTR", splitLongWords=1)
    small = ParagraphStyle("SmallPAM", parent=normal, fontSize=7.7,
                           leading=10.8, spaceAfter=3)
    heading = ParagraphStyle("HeadingPAM", parent=normal, fontSize=14,
                             leading=18, textColor=forest, spaceBefore=13,
                             spaceAfter=7, keepWithNext=True)
    hero = ParagraphStyle("HeroPAM", parent=normal, fontSize=26,
                          leading=30, spaceAfter=10)
    tiny = ParagraphStyle("TinyPAM", parent=normal, fontSize=7, leading=9)
    white = ParagraphStyle("WhitePAM", parent=small, textColor=colors.white)
    story = [Paragraph("RAPPORT D’ANALYSE", hero),
             Paragraph("Décision et éléments de preuve · document privé", small)]
    meta = [
        Paragraph("<b>ANALYSE AU</b><br/>" + escape(as_of), small),
        Paragraph("<b>STRATÉGIE</b><br/>" + escape(strategy), small),
        Paragraph("<b>STATUT</b><br/>" + escape(report_status), small),
    ]
    tab = Table([meta], colWidths=[(page_w - 86) / 3] * 3, hAlign="LEFT")
    tab.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), pale),
                             ("BOX", (0, 0), (-1, -1), 0.3, sage),
                             ("VALIGN", (0, 0), (-1, -1), "TOP"),
                             ("LEFTPADDING", (0, 0), (-1, -1), 11),
                             ("TOPPADDING", (0, 0), (-1, -1), 10),
                             ("BOTTOMPADDING", (0, 0), (-1, -1), 10)]))
    story.extend([tab, Spacer(1, 9),
                  Paragraph("Analysis_ID : " + escape(analysis_id), small)])

    lines = executive_report.split(_ANNEX, 1)[0].splitlines()
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if not line or line.startswith("# PAM R1 —"):
            i += 1
            continue
        if line.startswith("## "):
            story.append(Paragraph(_markup(line[3:]), heading))
        elif line.startswith("# "):
            story.append(Paragraph(_markup(line[2:]), heading))
        elif line == "---":
            story.append(HRFlowable(width="100%", thickness=0.5, color=sage))
        elif line.startswith("- "):
            story.append(Paragraph("• " + _markup(line[2:]), normal))
        elif line.startswith("|") and i + 1 < len(lines) and re.match(
                r"^\|[\s:|\-]+$", lines[i + 1].strip()):
            columns = [part.strip() for part in line.strip("|").split("|")]
            i += 2
            rows = [[Paragraph(_markup(part), white) for part in columns]]
            while i < len(lines) and lines[i].strip().startswith("|"):
                parts = [part.strip() for part in lines[i].strip().strip("|").split("|")]
                if len(parts) != len(columns):
                    break
                rows.append([Paragraph(_markup(part), small) for part in parts])
                i += 1
            table = Table(rows, colWidths=[(page_w - 86) / len(columns)] * len(columns),
                          repeatRows=1, hAlign="LEFT")
            table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), forest),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, pale]),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
            ]))
            story.append(table)
            continue
        else:
            story.append(Paragraph(_markup(line), normal))
        i += 1

    story.extend([
        Spacer(1, 20),
        HRFlowable(width="100%", color=sage),
        Paragraph("Dossier détaillé et traçabilité", heading),
        Paragraph("Texte du rapport source conservé ci-dessous. Aucune "
                  "source, transaction ou analyse supplémentaire n’est "
                  "créée par cet export.", small),
    ])
    # Escape all original lines. Layout may reflow, but no claim is dropped.
    for line in detailed_report.rstrip("\n").split("\n"):
        story.append(Paragraph(escape(line) if line else "&nbsp;", tiny))
    story.extend([Spacer(1, 12),
                  Paragraph("REPORT_EXPORT_STATUS: PDF_CREATED_LOCALLY; "
                            "CC_WORK_DELIVERY_NOT_VERIFIED; ARCHIVE_NOT_SAVED "
                            "sauf preuve indépendante contraire.", small)])

    def decorate(canvas, document):
        canvas.saveState()
        canvas.setFillColor(forest)
        canvas.rect(0, page_h - 10, page_w, 10, stroke=0, fill=1)
        canvas.setFont("Helvetica-Bold", 12)
        canvas.drawString(43, page_h - 40, "PAM")
        canvas.setFont("Helvetica", 8)
        canvas.drawString(82, page_h - 39, "FINANCIAL SYSTEMS")
        canvas.setStrokeColor(sage)
        canvas.line(43, 43, page_w - 43, 43)
        canvas.setFont("Helvetica", 7)
        canvas.drawString(43, 30, "PAM / CONFIDENTIEL - DOCUMENT DE TRAVAIL")
        canvas.drawRightString(page_w - 43, 30, "PAGE " + str(document.page))
        canvas.restoreState()

    doc.build(story, onFirstPage=decorate, onLaterPages=decorate)
    output = buffer.getvalue()
    if not output.startswith(b"%PDF-"):
        raise ValueError("PAMALISED_PDF_OUTPUT_INVALID")
    return output
