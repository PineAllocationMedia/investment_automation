"""PAMalisé: reference-composed private PDF for already validated R1 inputs.

Six investor-facing modules reproduce the CEO-supplied PDF's geometry, palette,
flow, tables and cards. Sections are conditional on actual supplied IR/PI packets.
The full original detail is retained as a separate annex. No network, memory,
broker action, invented return, fictitious allocation or background execution.
"""
from __future__ import annotations

from html import escape, unescape
from io import BytesIO
from pathlib import Path
from decimal import Decimal, InvalidOperation
from typing import Mapping, Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Table, TableStyle,
                                Spacer, PageBreak, HRFlowable)
from reportlab.lib.utils import ImageReader

DARK = "#0B2E24"
GREEN = "#123F30"
MID = "#56715E"
SAGE = "#7F9A85"
CREAM = "#FBF5E8"
CREAM2 = "#F5EBD9"
PALE = "#E5EEE7"
GREY = "#F1F3F0"
W, H = A4
WIDTH = W - 86


def _safe(value: Any, unknown: str = "NON DISPONIBLE", limit: int = 1450) -> str:
    if not isinstance(value, str) or not value.strip():
        return unknown
    clean = " ".join(value.strip().split())
    if len(clean) > limit:
        clean = clean[:max(0, limit - 24)].rstrip() + " … (suite en annexe)"
    return escape(clean)


def _extract_decision(executive: str) -> str:
    section = executive.split("## La conclusion\n", 1)
    if len(section) < 2:
        return "Aucune conclusion soutenue extraite"
    return section[1].split("\n\n", 1)[0].strip()


def _view(model: Mapping[str, Any], executive: str, detail: str,
          logo: bytes | None = None) -> bytes:
    if not isinstance(model, Mapping):
        raise ValueError("PAMALISE_MODEL_REQUIRED")
    req = model.get("request", {})
    ir = model.get("ir_capsule") or {}
    pi = model.get("pi_delta") or {}
    if not isinstance(req, Mapping) or not isinstance(ir, Mapping) or not isinstance(pi, Mapping):
        raise ValueError("PAMALISE_MODEL_STRUCTURE_INVALID")
    analysis = _safe(req.get("analysis_id"), limit=120)
    date = _safe(req.get("as_of"), limit=30)
    mode = _safe(req.get("strategy_id"), limit=80)
    horizon = _safe(req.get("horizon"), limit=80)
    objective = _safe(req.get("objective"), limit=240)
    decision = _safe(ir.get("decision_line") or _extract_decision(executive), limit=320)
    countercase = _safe(ir.get("countercase"), limit=330)
    next_action = _safe(ir.get("next_action") or pi.get("next_action"), limit=300)
    summary = ([s for s in ir.get("summary", []) if isinstance(s, str) and s.strip()]
               if isinstance(ir.get("summary", []), list) else [])
    facts = ([x for x in ir.get("facts", []) if isinstance(x, Mapping)]
             if isinstance(ir.get("facts", []), list) else [])
    portfolio_needed = bool(req.get("portfolio_needed"))
    room = _safe(pi.get("room_status"), limit=60) if portfolio_needed else "NON ÉVALUÉ"
    pi_summary = (_safe(pi.get("summary"), limit=300) if portfolio_needed
                  else "Aucune analyse personnelle demandée")
    pi_date = (_safe(pi.get("portfolio_as_of"), limit=40) if portfolio_needed else "S/O")
    room_status = pi.get("room_status")
    position_scope = (
        "Données PI rapportées; preuve à examiner"
        if room_status == "ROOM_EVIDENCE_SUPPORTED" else
        "Conditionnelles, non certifiées"
        if room_status == "ROOM_CONDITIONAL" else
        "Partielles / non vérifiées"
    )
    contribution = model.get("new_contribution_summary_private")
    allocation_text = None
    if isinstance(contribution, Mapping):
        pct = contribution.get("allocations_pct")
        if (contribution.get("analysis_id") == req.get("analysis_id")
                and contribution.get("gross_status") == "GROSS_PROJECTION_ONLY"
                and isinstance(pct, Mapping) and 1 <= len(pct) <= 12
                and all(isinstance(k, str) and 0 < len(k) <= 80
                        and isinstance(v, str) for k, v in pct.items())):
            try:
                numbers = {k: Decimal(v) for k, v in pct.items()}
            except InvalidOperation:
                numbers = {}
            if (len(numbers) == len(pct)
                    and all(n.is_finite() and Decimal("0") <= n <= Decimal("100")
                            for n in numbers.values())
                    and sum(numbers.values(), Decimal("0")) == Decimal("100")):
                allocation_text = " · ".join(
                    _safe(k, limit=80) + " : " + format(n, ".1f") + " %"
                    for k, n in numbers.items()
                ) + " (projection arithmétique, non recommandation)"

    # Lato matches the CEO's prototype. No font is fetched or bundled:
    # use an installed local Lato, otherwise an explicit Helvetica fallback.
    base_font, bold_font = "Helvetica", "Helvetica-Bold"
    try:
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        for folder in (Path("/usr/share/fonts/truetype/lato"),
                       Path("/Library/Fonts")):
            regular = folder / "Lato-Regular.ttf"
            bold = folder / "Lato-Bold.ttf"
            if regular.is_file() and bold.is_file():
                pdfmetrics.registerFont(TTFont("PAM_Lato", str(regular)))
                pdfmetrics.registerFont(TTFont("PAM_Lato_Bold", str(bold)))
                pdfmetrics.registerFontFamily("PAM_Lato", normal="PAM_Lato",
                                              bold="PAM_Lato_Bold",
                                              italic="PAM_Lato", boldItalic="PAM_Lato_Bold")
                base_font, bold_font = "PAM_Lato", "PAM_Lato_Bold"
                break
    except Exception:
        base_font, bold_font = "Helvetica", "Helvetica-Bold"

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4, leftMargin=43, rightMargin=43,
        topMargin=88, bottomMargin=51,
        title="PAM Financial Systems - Rapport d analyse",
        author="PAM Financial Systems",
    )
    normal = ParagraphStyle(
        "body", fontName=base_font, fontSize=9.5, leading=14,
        textColor=colors.HexColor(DARK), spaceAfter=7,
    )
    small = ParagraphStyle("small", parent=normal, fontSize=8.2,
                           leading=12, spaceAfter=4)
    tiny = ParagraphStyle("tiny", parent=normal, fontSize=7.2,
                          leading=10, spaceAfter=3)
    big = ParagraphStyle("big", parent=normal, fontName=bold_font,
                         fontSize=23, leading=28, spaceAfter=10)
    headline = ParagraphStyle(
        "head", parent=normal, fontName=bold_font, fontSize=14,
        leading=17, spaceBefore=12, spaceAfter=8,
    )
    mini = ParagraphStyle(
        "mini", parent=normal, fontName=bold_font, fontSize=7.4,
        leading=10, textColor=colors.HexColor(MID),
    )
    white = ParagraphStyle("white", parent=normal, textColor=colors.white,
                           fontSize=9, leading=14)
    whitebig = ParagraphStyle(
        "whitebig", parent=white, fontName=bold_font,
        fontSize=17, leading=21,
    )
    pale = colors.HexColor(PALE)
    dark = colors.HexColor(GREEN)
    sage = colors.HexColor(SAGE)
    story = []

    def P(value, style=normal):
        # Pre-escaped source strings may be passed by the presentation helpers.
        # Unescape once then escape once; never interpret source-provided HTML.
        return Paragraph(_safe(unescape(value) if isinstance(value, str)
                               else value), style)

    def raw(value, style=normal):
        return Paragraph(value, style)

    def box(text, background=PALE, style=normal, pad=12):
        t = Table([[raw(text, style)]], colWidths=[WIDTH])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor(background)),
            ("LEFTPADDING", (0, 0), (-1, -1), pad),
            ("RIGHTPADDING", (0, 0), (-1, -1), pad),
            ("TOPPADDING", (0, 0), (-1, -1), pad),
            ("BOTTOMPADDING", (0, 0), (-1, -1), pad),
        ]))
        return t

    def tiles(items):
        n = len(items)
        width = (WIDTH - 8 * (n - 1)) / n
        cells = []
        for title, value in items:
            t = Table([[raw(_safe(title), mini)], [P(value, small)]],
                      colWidths=[width])
            t.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), pale),
                ("TOPPADDING", (0, 0), (-1, 0), 10),
                ("BOTTOMPADDING", (0, -1), (-1, -1), 12),
                ("LEFTPADDING", (0, 0), (-1, -1), 9),
                ("RIGHTPADDING", (0, 0), (-1, -1), 9),
            ]))
            cells.append(t)
        out = []
        for i, item in enumerate(cells):
            if i:
                out.append(Spacer(8, 1))
            out.append(item)
        tab = Table([out], colWidths=[
            width if i % 2 == 0 else 8 for i in range(2 * n - 1)
        ])
        tab.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ]))
        return tab

    def heading(number, title, description):
        story.extend([
            raw(_safe(number + " / " + title.upper()), mini),
            Spacer(1, 5), P(title, big), P(description, small), Spacer(1, 11),
        ])

    def label(value):
        story.append(P(value, headline))

    def table(headers, rows):
        if not rows:
            return
        widths = [WIDTH / len(headers)] * len(headers)
        data = [[raw(_safe(s), white) for s in headers]] + [
            [P(str(x), tiny) for x in row] for row in rows
        ]
        tab = Table(data, colWidths=widths, repeatRows=1, hAlign="LEFT")
        tab.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), dark),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [pale, colors.white]),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 9),
            ("RIGHTPADDING", (0, 0), (-1, -1), 9),
            ("TOPPADDING", (0, 0), (-1, -1), 9),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
        ]))
        story.append(tab)

    def page():
        story.append(PageBreak())

    # 01: Actual decision and mandate, never an inferred allocation.
    story.extend([
        raw("RAPPORT PAMALISÉ / ANALYSE DU MANDAT", mini),
        Spacer(1, 8), P("Rapport d’analyse de portefeuille", big),
        P("Comprendre la décision, les mécanismes de risque et les éléments "
          "qui pourraient modifier la conclusion.", small),
        Spacer(1, 14),
    ])
    story.append(tiles([
        ("ANALYSE AU", date), ("STRATÉGIE", mode), ("HORIZON", horizon),
        ("DONNÉES", "IR / PI rapportées, non certifiées" if ir or pi
         else "NON ÉVALUÉES"),
    ]))
    story.append(Spacer(1, 13))
    story.append(box(
        "<b>MANDAT</b> " + objective + "<br/><br/><b>TRAÇABILITÉ</b> "
        "Analysis_ID " + analysis + " · Méthode " +
        _safe(req.get("ir_method_version"), "UNKNOWN_NOT_LOADED") +
        " · Décideur CEO / investisseur.", CREAM, small,
    ))
    label("01 | L’essentiel en 60 secondes")
    story.append(box(
        '<font color="#FFFFFF"><b>CONCLUSION PRINCIPALE</b><br/><br/>' +
        decision + "<br/><br/>Aucune transaction n’est initiée par ce rapport.</font>",
        GREEN, whitebig, 19,
    ))
    story.append(Spacer(1, 13))
    story.append(tiles([
        ("CONVICTION", "SOURCE IR NON CERTIFIÉE" if ir else "NON ÉVALUÉE"),
        ("RISQUE DÉTERMINANT", countercase), ("FRAÎCHEUR", date),
    ]))
    story.append(Spacer(1, 12))
    label("Allocation envisagée")
    story.append(tiles([
        ("PORTEFEUILLE CONSTATÉ", pi_summary if portfolio_needed else "NON ÉVALUÉ"),
        ("PROPOSITION / SIMULATION", allocation_text or "NON ÉTABLIE - aucun poids inféré"),
    ]))
    story.append(Spacer(1, 12))
    story.append(box(
        "<b>LA NUANCE QUI COMPTE</b> La conclusion reste soumise "
        "aux limites de preuve décrites ci-dessous.", PALE, small,
    ))
    page()

    # 02: Actual research, not a fabricated market ranking.
    if ir:
        heading("02", "Les opportunités retenues",
                "Rendre comparables les idées sans confondre qualité "
                "de l’entreprise et attrait du prix.")
        label("Thèses et observations effectivement reçues")
        if summary:
            for i, part in enumerate(summary[:4]):
                story.append(box(
                    '<font color="#123F30"><b>%02d / OBSERVATION IR</b></font>'
                    "<br/><br/>%s" % (i + 1, _safe(part)), GREY, normal, 13,
                ))
                story.append(Spacer(1, 9))
        else:
            story.append(box(
                "Aucune thèse IR fournie dans les entrées validées.",
                GREY, small,
            ))
        label("Faits soumis à contrôle")
        table(["ID / STATUT", "OBSERVATION", "DATE / SOURCE"], [
            [fact.get("id", "ND"), fact.get("claim", "ND"),
             fact.get("period", "ND")] for fact in facts[:4]
        ])
        story.append(Spacer(1, 12))
        story.append(box(
            "<b>POURQUOI PAS SIMPLEMENT LA RÉFÉRENCE ?</b><br/><br/>"
            "Comparaison de rendement total économique avec l’indice/ETF "
            "de référence : NON CERTIFIÉE par le présent rapport.", CREAM, small,
        ))
        page()

    # 03: Do not turn a Blossom public/profile observation into personal Room.
    if portfolio_needed:
        heading("03", "Ce que cela change dans le portefeuille",
                "Séparer les positions réellement confirmées "
                "de toute allocation hypothétique.")
        story.append(tiles([
            ("POSITIONS", position_scope),
            ("PORTÉE", "PI : source rapportée"),
            ("APRÈS ALLOCATION", allocation_text or "Simulation NON ÉTABLIE"),
        ]))
        label("Comparaison avant / après")
        story.append(tiles([
            ("AVANT", "ND - dénominateur non confirmé"),
            ("APRÈS", allocation_text or "ND - simulation non établie"),
        ]))
        story.append(Spacer(1, 13))
        label("Expositions et concentrations")
        table(["DIMENSION", "OBSERVÉ", "SIMULÉ", "LECTURE"], [
            ["PORTFOLIO ROOM", room, "ND", "Données PI rapportées"],
            ["DATE DE LA VUE", pi_date, "S/O",
             "Date de capture ≠ date des positions"],
            ["CASH / FX / FRAIS", "ND", "ND", "Pas de zéro inféré"],
        ])
        story.append(Spacer(1, 12))
        story.append(box(
            "<b>CHEVAUCHEMENTS CACHÉS</b><br/><br/>Non représentés : "
            "liens entre titres et ETF non suffisamment documentés.",
            CREAM, small,
        ))
        page()

    # 04/05: Risk and durability appear only when IR actually returned content.
    if ir:
        heading("04", "Risques et points de bascule",
                "La question utile : quel fait observable changerait le jugement ?")
        story.append(box(
            "<b>CLIMAT DE MARCHÉ / CYCLE / BULLE</b><br/><br/>Lecture macro "
            "non établie indépendamment pour ce dossier; aucun signal "
            "de marché n’est présumé.", CREAM, normal, 16,
        ))
        story.append(Spacer(1, 17))
        label("Scénarios et limites")
        story.append(box(
            "Aucun stress test admissible dans les champs de ce rendu. "
            "Voir l’annexe pour les scénarios éventuellement présents; "
            "aucune perte ou corrélation n’est inventée.",
            GREY, normal, 18,
        ))
        label("De l’observation à la décision")
        story.append(tiles([
            ("01 / FAIT REÇU", summary[0] if summary else "Source insuffisante"),
            ("02 / THÈSE IMPACTÉE", countercase),
            ("03 / RÉEXAMEN", next_action),
        ]))
        story.append(Spacer(1, 14))
        story.append(box(
            "<b>SIGNAUX D’ACTION / SURVEILLANCE</b><br/><br/>Condition de "
            "réexamen : " + next_action + "<br/><br/>Vente : exceptionnelle, "
            "à justifier et autoriser séparément.", PALE, small,
        ))
        page()
        heading("05", "Durabilité et radar des marchés",
                "Différencier marché potentiel, capacité à capter "
                "la valeur et prix payé.")
        label("Convictions à l’horizon du mandat")
        story.append(tiles([
            ("AUJOURD’HUI", "Faits IR reçus"),
            ("MOYEN TERME", "Non chiffré"),
            ("LONG TERME", horizon),
        ]))
        label("Marchés et modèles d’affaires")
        if facts:
            table(["FAIT", "STATUT", "LECTURE"], [
                [fact.get("id", "ND"), fact.get("status", "ND"),
                 fact.get("claim", "ND")] for fact in facts[:5]
            ])
        else:
            story.append(box(
                "Aucune donnée source assez étayée pour une matrice de marchés.",
                GREY, normal,
            ))
        label("Radar des événements utiles")
        story.append(box(
            "<b>01 / CE QUI A CHANGÉ</b><br/>BASELINE_NOT_AVAILABLE si "
            "aucun dossier antérieur comparable n’est reçu.", GREY, small,
        ))
        story.append(Spacer(1, 8))
        story.append(box(
            "<b>02 / PROCHAIN CATALYSEUR</b><br/>Non daté / "
            "non vérifié : aucune échéance inventée.", CREAM, small,
        ))
        story.append(Spacer(1, 8))
        story.append(box(
            "<b>03 / IDÉE À APPROFONDIR</b><br/>" + next_action, GREY, small,
        ))
        page()

    # 06: Actual source IDs and stated limitations, no invented performance.
    heading("06", "Suivi, performance et traçabilité",
            "Conserver les hypothèses historiques "
            "et rendre la conclusion reproductible.")
    label("Depuis le dernier rapport")
    for key, text in [
        ("CHOIX / ALLOCATION", "BASELINE_NOT_AVAILABLE / non comparable"),
        ("THÈSE / CONVICTION", "Aucun changement historique certifié"),
        ("MÉTHODE / DONNÉES",
         _safe(req.get("ir_method_version"), "UNKNOWN_NOT_LOADED")),
    ]:
        story.append(box("<b>" + key + "</b><br/>" + text, PALE, small))
        story.append(Spacer(1, 9))
    label("Historique et performance théorique")
    story.append(box(
        "SÉRIE NON DÉMONTRÉE DANS CE RENDU - une courbe nécessite flux, "
        "devises, frais, dates et benchmark comparables vérifiés.", GREY, small, 18,
    ))
    label("Provenance et limites")
    table(["SOURCE", "DATE / COUVERTURE", "RÔLE / LIMITE"], [
        [fact.get("id", "ND"), fact.get("period", "ND"),
         fact.get("status", "ND")] for fact in facts[:5]
    ])
    story.append(Spacer(1, 13))
    story.append(box(
        '<font color="#FFFFFF"><b>DÉCISION RÉSERVÉE '
        "À L’INVESTISSEUR / CEO</b><br/><br/>" + decision +
        " Aucune transaction automatique.</font>", GREEN, white, 15,
    ))

    # The original report is retained verbatim in the source session and
    # represented completely as recoverable text in the exported annex.
    page()
    heading("A", "Dossier détaillé et traçabilité",
            "Annexe technique du rapport original, "
            "conservée sans modification des faits.")
    for line in detail.splitlines():
        if not line.strip():
            story.append(Spacer(1, 3))
        else:
            story.append(P(line, tiny))
    story.append(P(
        "REPORT_EXPORT_STATUS: PDF_CREATED_LOCALLY · "
        "ARCHIVE_NOT_SAVED · CC_WORK_DELIVERY_NOT_VERIFIED", tiny,
    ))

    def chrome(canvas, document):
        canvas.saveState()
        canvas.setFillColor(dark)
        canvas.rect(0, H - 8, W, 8, stroke=0, fill=1)
        if logo:
            try:
                canvas.drawImage(
                    ImageReader(BytesIO(logo)), 43, H - 66, 39, 39, mask="auto",
                )
            except Exception:
                pass
        else:
            canvas.setFillColor(colors.HexColor(CREAM2))
            canvas.roundRect(43, H - 66, 39, 39, 4, stroke=0, fill=1)
            canvas.setStrokeColor(sage)
            canvas.setLineWidth(1)
            canvas.line(61, H - 57, 62, H - 36)
            canvas.line(62, H - 43, 53, H - 49)
            canvas.line(62, H - 43, 69, H - 51)
        canvas.setFillColor(dark)
        canvas.setFont(bold_font, 12)
        canvas.drawString(88, H - 41, "PAM")
        canvas.setFont(base_font, 6)
        canvas.drawString(88, H - 52, "FINANCIAL SYSTEMS")
        canvas.setFont(base_font, 7)
        canvas.drawRightString(W - 43, H - 40, "RAPPORT D’ANALYSE")
        canvas.setStrokeColor(colors.HexColor("#DADFD9"))
        canvas.line(43, H - 74, W - 43, H - 74)
        canvas.line(43, 43, W - 43, 43)
        canvas.setFillColor(colors.HexColor(MID))
        canvas.setFont("Helvetica", 7)
        canvas.drawString(43, 30, "PAM / CONFIDENTIEL · DOCUMENT DE TRAVAIL")
        canvas.drawRightString(W - 43, 30, "PAMALISÉ · %02d" % document.page)
        canvas.restoreState()

    doc.build(story, onFirstPage=chrome, onLaterPages=chrome)
    return buffer.getvalue()


def render_reference_style_pdf(*, executive_report: str, detailed_report: str,
                               request: Mapping[str, Any],
                               ir_capsule: Mapping[str, Any] | None = None,
                               pi_delta: Mapping[str, Any] | None = None,
                               logo: bytes | None = None,
                               new_contribution_summary_private: Mapping[str, Any] | None = None) -> bytes:
    """Layout only, never evidence admission; validate before calling."""
    if not isinstance(executive_report, str) or not isinstance(detailed_report, str):
        raise ValueError("PAMALISE_PAIR_REQUIRED")
    if "## Dossier détaillé et traçabilité (annexe)" not in executive_report:
        raise ValueError("PAMALISE_REPORT_INCOMPLETE")
    if not executive_report.endswith(detailed_report.rstrip("\n") + "\n"):
        raise ValueError("PAMALISE_SOURCE_PARITY_REQUIRED")
    if len(executive_report) > 200_000 or len(detailed_report) > 200_000:
        raise ValueError("PAMALISE_INPUT_TOO_LARGE")
    return _view(dict(request=request, ir_capsule=ir_capsule or {},
                      pi_delta=pi_delta or {},
                      new_contribution_summary_private=new_contribution_summary_private),
                 executive_report, detailed_report, logo)
