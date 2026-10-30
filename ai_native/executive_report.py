"""Decision-first PRIVATE view layered over the existing validated R1 report.

This formatter does not analyze securities, authenticate evidence, rank investments,
claim a complete market scan, open a portfolio, persist data or place trades.
The unchanged detailed report remains available below the executive view.
"""
from __future__ import annotations

from typing import Any, Mapping

_ROOM = frozenset({"NOT_EVALUATED", "ROOM_UNAVAILABLE", "ROOM_CONDITIONAL",
                   "ROOM_EVIDENCE_SUPPORTED"})
_STATUSES = frozenset({"EXPLORATORY", "CONDITIONAL", "COMPONENT_SUPPORTED"})


def _line(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"EXECUTIVE_REPORT_{field}_REQUIRED")
    # Source text is analyst-supplied, not a trusted template or instruction.
    return " ".join(value.split())


def render_executive_report(
    packet: Mapping[str, Any], *,
    detailed_report: str, portfolio_room_status: str,
) -> str:
    """Present one readable decision view plus the original evidence-bearing report.

    Invoke only *after* render_report(packet) has checked its detailed source,
    arithmetic and authority contracts. Labels do not promote specialist
    opinions into independently checked investment decisions.
    """
    if not isinstance(packet, Mapping) or not isinstance(detailed_report, str):
        raise ValueError("EXECUTIVE_REPORT_INPUT_INVALID")
    if not detailed_report.startswith("# ") or not detailed_report.strip():
        raise ValueError("EXECUTIVE_REPORT_DETAIL_REQUIRED")
    if portfolio_room_status not in _ROOM:
        raise ValueError("EXECUTIVE_REPORT_ROOM_STATUS_INVALID")
    status = _line(packet.get("status"), "STATUS")
    if status not in _STATUSES:
        raise ValueError("EXECUTIVE_REPORT_STATUS_INVALID")
    aid = _line(packet.get("analysis_id"), "ID")
    cutoff = _line(packet.get("as_of"), "DATE")
    strategy = _line(packet.get("strategy"), "STRATEGY")
    objective = _line(packet.get("objective"), "OBJECTIVE")
    decision = _line(packet.get("decision_line"), "DECISION")
    countercase = _line(packet.get("countercase"), "COUNTERCASE")
    action = _line(packet.get("next_action"), "NEXT_ACTION")
    summary = packet.get("summary")
    if not isinstance(summary, list) or not 1 <= len(summary) <= 6:
        raise ValueError("EXECUTIVE_REPORT_SUMMARY_INVALID")
    observations = [_line(item, "FINDING") for item in summary[:3]]
    has_research_facts = bool(packet.get("facts"))
    quality = ("IR : appréciation rapportée, à confronter aux sources originales"
               if has_research_facts else "NON ÉVALUÉ — aucun fait IR transmis")
    durability = ("IR : thèse et contre-thèse rapportées, non certifiées"
                  if has_research_facts else "NON ÉVALUÉ — aucun fait IR transmis")

    room = {
        "NOT_EVALUATED": "NON ÉVALUÉ — aucune analyse PI dans ce dossier",
        "ROOM_UNAVAILABLE": "INDISPONIBLE — aucune capacité personnelle démontrée",
        "ROOM_CONDITIONAL": "CONDITIONNEL — données PI rapportées, non authentifiées",
        "ROOM_EVIDENCE_SUPPORTED": (
            "Éléments PI rapportés, sans certification indépendante des positions"),
    }[portfolio_room_status]
    gate = packet.get("strategy_policy_gate")
    requires_policy = (isinstance(gate, Mapping) and
                       gate.get("policy_authority") == "R1_POLICY_REQUIRES_CEO_APPROVAL")
    policy = ("Adaptation R1 soumise à approbation du CEO"
              if requires_policy else
              "Autorité de la méthode à vérifier dans le dossier détaillé")

    rows = [
        "# PAM R1 — Synthèse décisionnelle",
        f"**Dossier :** {aid} | **Date :** {cutoff} | **Mode :** {strategy}",
        f"**Statut :** {status} — recherche et interprétation, aucune transaction.",
        "",
        "## La conclusion",
        decision,
        "",
        f"**Question :** {objective}",
        "",
        "## Ce que les preuves disponibles permettent de retenir",
    ]
    rows.extend(f"- {finding}" for finding in observations)
    if len(summary) > 3:
        rows.append("- Autres observations dans le rapport détaillé ci-dessous.")
    rows.extend([
        "",
        "## Les cinq piliers — limites de conclusion",
        "| Pilier | Ce qui est réellement établi ici |",
        "|---|---|",
        f"| QUALITY | {quality} |",
        f"| DURABILITY | {durability} |",
        "| EXPECTED RETURN | Rendement total normalisé et supériorité au benchmark NON CERTIFIÉS |",
        "| CONFIDENCE | Dépend des preuves vérifiées et des hypothèses; pas de note inventée |",
        f"| PORTFOLIO ROOM | {room} |",
        "",
        f"**Contre-thèse essentielle :** {countercase}",
        "",
        "## Prochaine action",
        action,
        "",
        "## Ce que ce rapport ne prouve pas",
        f"- **Politique :** {policy}.",
        "- **Recherche :** aucun balayage exhaustif du marché ni classement mondial démontré.",
        "- **Coûts et allocation :** aucun rendement net, avantage sur benchmark ou ordre "
        "d'investissement n'est créé par cette mise en page.",
        "- **Mémoire :** archive non enregistrée (ARCHIVE_NOT_SAVED); "
        "aucun dépôt GitHub ni stockage privé effectué.",
        "",
        "---",
        "",
        "## Dossier détaillé et traçabilité (annexe)",
        "Le rapport original ci-dessous est repris sans suppression de ses "
        "réserves, calculs, sources ou identifiants. "
        "Les vérifications de l'assembleur ne certifient pas les publications originales.",
        "",
        detailed_report.rstrip("\n"),
        "",
    ])
    return "\n".join(rows)
