from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .add_eligibility_engine import ADD_ALLOWED_STATUSES
from .research_reports import (
    RESEARCH_INDEX_COLUMNS,
    SUPPORTED_REPORT_EXTENSIONS,
    date_from_filename,
    extract_report_text,
    infer_ticker_from_filename,
)
from .utils import (
    BNCD_MORNINGSTAR_DIR,
    RESEARCH_REPORTS_DIR,
    normalize_ticker,
    read_csv_records,
    safe_float,
)


QUALITATIVE_MOAT_COLUMNS = [
    "ticker",
    "ticker_display",
    "target_status",
    "allocation_amount",
    "eligibility_status",
    "source_status",
    "source_confidence",
    "sources",
    "source_dates",
    "moat_label",
    "competitive_advantage_themes",
    "crisis_protection_themes",
    "pricing_power_themes",
    "qualitative_text",
]

MAX_SOURCES_PER_TICKER = 3


THEME_PATTERNS: list[tuple[str, str, str]] = [
    ("moat", "wide moat", r"\bwide moat\b"),
    ("moat", "narrow moat", r"\bnarrow moat\b"),
    ("moat", "coûts de changement", r"\bswitching costs?\b|co[uû]ts? de changement"),
    ("moat", "effets de réseau", r"\bnetwork effects?\b|effets? de r[eé]seau"),
    ("moat", "actifs incorporels", r"\bintangible assets?\b|actifs? incorporels?"),
    ("moat", "marque forte", r"\bbrand\b|marque forte|capital de marque"),
    ("moat", "brevets ou propriété intellectuelle", r"\bpatents?\b|intellectual property|propri[eé]t[eé] intellectuelle"),
    ("moat", "avantage de coût", r"\bcost advantage\b|avantage de co[uû]t"),
    ("moat", "échelle efficiente", r"\befficient scale\b|[eé]chelle efficiente"),
    ("moat", "écosystème", r"\becosystem\b|[eé]cosyst[eè]me"),
    ("moat", "base installée", r"\binstalled base\b|base install[eé]e"),
    ("moat", "produit ou service critique", r"\bmission[- ]critical\b|critique pour (?:les )?clients"),
    ("crisis", "revenus récurrents", r"\brecurring revenue\b|revenus? r[eé]currents?"),
    ("crisis", "abonnements", r"\bsubscription\b|abonnements?"),
    ("crisis", "flux de trésorerie solides", r"\bcash flow\b|flux de tr[eé]sorerie"),
    ("crisis", "bilan solide", r"\bstrong balance sheet\b|\bsound balance sheet\b|bilan solide|faible endettement|low debt"),
    ("crisis", "diversification", r"\bdiversified\b|diversification"),
    ("crisis", "résilience", r"\bresilien(?:t|ce)\b|r[eé]silien(?:t|ce)"),
    ("crisis", "demande défensive", r"\bdefensive\b|noncyclical|non-cyclical|d[eé]fensif"),
    ("crisis", "produit ou service critique", r"\bmission[- ]critical\b|critique pour (?:les )?clients"),
    ("pricing", "pouvoir de prix", r"\bpricing power\b|pouvoir de prix"),
    ("pricing", "hausses de prix", r"\bprice increases?\b|raise prices?|augmentation(?:s)? de prix|hausse(?:s)? de prix"),
    ("pricing", "capacité de répercuter l’inflation", r"\bpass[- ]through\b|inflation|r[eé]percuter"),
    ("pricing", "offre premium", r"\bpremium\b"),
    ("pricing", "marges soutenues", r"\bmargin expansion\b|marges? stables?|marges? en expansion|stable margins?"),
    ("pricing", "clients captifs ou produit critique", r"\bmission[- ]critical\b|\bsticky\b|switching costs?"),
]

MOAT_LABEL_PATTERNS = [
    ("wide moat", r"\bwide moat\b"),
    ("narrow moat", r"\bnarrow moat\b"),
    ("no moat", r"\bno moat\b|\bno economic moat\b"),
]


def build_qualitative_moat_rows(
    analyses: dict[str, dict[str, Any]],
    allocation_rows: list[dict[str, Any]],
    *,
    report_dir: str | Path = BNCD_MORNINGSTAR_DIR,
    index_path: str | Path = RESEARCH_REPORTS_DIR / "research_index.csv",
) -> list[dict[str, Any]]:
    targets = _qualitative_targets(analyses, allocation_rows)
    known_tickers = sorted(targets.keys())
    files_by_ticker = _report_files_by_ticker(Path(report_dir), Path(index_path), known_tickers)
    rows = []
    for ticker, target in targets.items():
        analysis = target["analysis"]
        if ticker == "VFV.TO" or analysis.get("benchmark_role") is True:
            rows.append(_benchmark_row(target))
            continue
        rows.append(_qualitative_row_for_target(target, files_by_ticker.get(ticker, [])))
    return rows


def qualitative_moat_markdown(rows: list[dict[str, Any]]) -> list[str]:
    if not rows:
        return [
            "### Lecture qualitative sourcée des titres retenus ou admissibles",
            "",
            "Aucun titre individuel recommandé ou admissible n’a été trouvé pour cette analyse.",
            "",
        ]

    lines = [
        "### Lecture qualitative sourcée des titres retenus ou admissibles",
        "",
        "Cette section ajoute une couche qualitative, mais seulement à partir de rapports locaux fiables comme BNCD/Morningstar, NBF, rapports annuels ou présentations investisseurs déposés dans `data/research_reports/bncd_morningstar`. Si aucune source exploitable n’est trouvée, l’agent refuse d’inventer une histoire qualitative.",
        "",
    ]
    for row in rows:
        ticker = row.get("ticker_display") or row.get("ticker")
        status = row.get("target_status") or ""
        lines.extend(
            [
                f"**{ticker} — {status}.** {row.get('qualitative_text')}",
                "",
            ]
        )
    return lines


def _qualitative_targets(
    analyses: dict[str, dict[str, Any]],
    allocation_rows: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    allocated_amounts = {
        normalize_ticker(row.get("ticker")): safe_float(row.get("amount")) or 0.0
        for row in allocation_rows
        if (safe_float(row.get("amount")) or 0.0) > 0
    }
    targets: dict[str, dict[str, Any]] = {}
    for ticker, analysis in analyses.items():
        ticker = normalize_ticker(ticker or analysis.get("ticker"))
        if not ticker:
            continue
        is_allocated = ticker in allocated_amounts
        is_eligible = analysis.get("add_eligibility_status") in ADD_ALLOWED_STATUSES
        if not is_allocated and not is_eligible:
            continue
        target_status = "RECOMMANDÉ" if is_allocated else "ÉLIGIBLE_NON_RETENU"
        targets[ticker] = {
            "ticker": ticker,
            "ticker_display": analysis.get("ticker_display") or ticker,
            "target_status": target_status,
            "allocation_amount": allocated_amounts.get(ticker, 0.0),
            "analysis": analysis,
        }

    return dict(
        sorted(
            targets.items(),
            key=lambda item: (
                0 if item[1]["target_status"] == "RECOMMANDÉ" else 1,
                -(safe_float(item[1].get("allocation_amount")) or 0.0),
                -(safe_float(item[1]["analysis"].get("capital_allocation_score")) or 0.0),
                item[0],
            ),
        )
    )


def _report_files_by_ticker(report_dir: Path, index_path: Path, known_tickers: list[str]) -> dict[str, list[Path]]:
    indexed = _indexed_reports(index_path)
    files: dict[str, list[Path]] = {ticker: [] for ticker in known_tickers}
    if not report_dir.exists():
        return files
    for path in sorted(report_dir.glob("*")):
        if not path.is_file() or path.name == "README.md" or path.suffix.lower() not in SUPPORTED_REPORT_EXTENSIONS:
            continue
        index_row = indexed.get(path.name, {})
        ticker = normalize_ticker(index_row.get("ticker")) or infer_ticker_from_filename(path.name, known_tickers)
        if ticker in files:
            files[ticker].append(path)
    for ticker, paths in files.items():
        files[ticker] = sorted(paths, key=_report_sort_key, reverse=True)[:MAX_SOURCES_PER_TICKER]
    return files


def _qualitative_row_for_target(target: dict[str, Any], paths: list[Path]) -> dict[str, Any]:
    ticker = target["ticker"]
    analysis = target["analysis"]
    if not paths:
        return _missing_source_row(target, "Aucun rapport local fiable trouvé pour ce ticker.")

    docs = []
    errors = []
    for path in paths:
        text, error = extract_report_text(path)
        if error:
            errors.append(f"{path.name}: {error}")
            continue
        if text and len(text.strip()) >= 100:
            docs.append({"path": path, "text": text})
    if not docs:
        reason = "Les rapports locaux existent, mais aucun texte suffisamment exploitable n’a pu être extrait."
        if errors:
            reason += " " + " ".join(errors[:2])
        return _missing_source_row(target, reason)

    evidence = _extract_evidence(" ".join(doc["text"] for doc in docs))
    source_names = [doc["path"].name for doc in docs]
    source_dates = [date_from_filename(name) for name in source_names if date_from_filename(name)]
    paragraph = _build_paragraph(
        ticker=ticker,
        company_name=analysis.get("company_name") or analysis.get("company_name_found") or ticker,
        evidence=evidence,
        sources=source_names,
    )
    return {
        "ticker": ticker,
        "ticker_display": target.get("ticker_display") or ticker,
        "target_status": target.get("target_status"),
        "allocation_amount": round(safe_float(target.get("allocation_amount")) or 0.0, 2),
        "eligibility_status": analysis.get("add_eligibility_status"),
        "source_status": "LOCAL_RESEARCH_REPORT",
        "source_confidence": _source_confidence(evidence),
        "sources": "; ".join(source_names),
        "source_dates": "; ".join(sorted(set(source_dates), reverse=True)),
        "moat_label": evidence.get("moat_label") or "",
        "competitive_advantage_themes": ", ".join(evidence.get("moat_themes", [])),
        "crisis_protection_themes": ", ".join(evidence.get("crisis_themes", [])),
        "pricing_power_themes": ", ".join(evidence.get("pricing_themes", [])),
        "qualitative_text": paragraph,
    }


def _benchmark_row(target: dict[str, Any]) -> dict[str, Any]:
    ticker = target["ticker"]
    text = (
        f"{ticker} est un ETF de marché large, pas une entreprise avec moat, management et pouvoir de prix à analyser comme une action individuelle. "
        "Son rôle qualitatif dans le modèle est de servir de coût d’opportunité et de filet de sécurité quand les titres individuels ne compensent pas assez le risque. "
        "La résilience vient surtout de la diversification du S&P 500, pas d’un avantage concurrentiel propre à une seule compagnie. "
        "Source: classification interne du modèle et structure connue de VFV.TO comme ETF S&P 500."
    )
    return {
        "ticker": ticker,
        "ticker_display": target.get("ticker_display") or ticker,
        "target_status": target.get("target_status"),
        "allocation_amount": round(safe_float(target.get("allocation_amount")) or 0.0, 2),
        "eligibility_status": "BENCHMARK_FALLBACK",
        "source_status": "BENCHMARK_ETF",
        "source_confidence": "HIGH",
        "sources": "Structure ETF / benchmark interne",
        "source_dates": "",
        "moat_label": "N/A ETF",
        "competitive_advantage_themes": "diversification",
        "crisis_protection_themes": "marché large",
        "pricing_power_themes": "N/A ETF",
        "qualitative_text": text,
    }


def _missing_source_row(target: dict[str, Any], reason: str) -> dict[str, Any]:
    ticker = target["ticker"]
    analysis = target["analysis"]
    text = (
        f"Analyse qualitative sourcée non disponible pour {ticker} avec les rapports locaux actuels. "
        "Pour éviter un texte générique, l’agent n’invente pas son avantage concurrentiel, son rempart spécifique, sa résistance en crise ou son pouvoir de prix. "
        "Ajoutez un rapport BNCD/Morningstar, NBF, un rapport annuel ou une présentation investisseurs dont le nom contient le ticker pour activer cette section. "
        f"Raison technique: {reason}"
    )
    return {
        "ticker": ticker,
        "ticker_display": target.get("ticker_display") or ticker,
        "target_status": target.get("target_status"),
        "allocation_amount": round(safe_float(target.get("allocation_amount")) or 0.0, 2),
        "eligibility_status": analysis.get("add_eligibility_status"),
        "source_status": "SOURCE_MISSING",
        "source_confidence": "NONE",
        "sources": "",
        "source_dates": "",
        "moat_label": "",
        "competitive_advantage_themes": "",
        "crisis_protection_themes": "",
        "pricing_power_themes": "",
        "qualitative_text": text,
    }


def _extract_evidence(text: str) -> dict[str, Any]:
    sentences = _split_sentences(text)
    themes = {"moat": [], "crisis": [], "pricing": []}
    for sentence in sentences:
        for category, label, pattern in THEME_PATTERNS:
            if re.search(pattern, sentence, flags=re.IGNORECASE) and label not in themes[category]:
                themes[category].append(label)

    moat_label = ""
    for label, pattern in MOAT_LABEL_PATTERNS:
        if re.search(pattern, text, flags=re.IGNORECASE):
            moat_label = label
            break
    if moat_label:
        themes["moat"] = [theme for theme in themes["moat"] if theme not in {"wide moat", "narrow moat"}]

    return {
        "moat_label": moat_label,
        "moat_themes": themes["moat"][:6],
        "crisis_themes": themes["crisis"][:5],
        "pricing_themes": themes["pricing"][:5],
    }


def _build_paragraph(ticker: str, company_name: str, evidence: dict[str, Any], sources: list[str]) -> str:
    label = evidence.get("moat_label")
    moat_themes = evidence.get("moat_themes", [])
    crisis_themes = evidence.get("crisis_themes", [])
    pricing_themes = evidence.get("pricing_themes", [])

    if label and moat_themes:
        first = (
            f"Les sources locales utilisées décrivent {company_name} comme une entreprise à {label} "
            f"et mentionnent surtout {_human_list(moat_themes)} comme sources d’avantage concurrentiel."
        )
    elif moat_themes:
        first = (
            f"Les sources locales utilisées ne donnent pas une conclusion de moat complète, mais elles mentionnent "
            f"{_human_list(moat_themes)} comme éléments d’avantage concurrentiel pour {company_name}."
        )
    else:
        first = (
            f"Les sources locales utilisées pour {company_name} ne fournissent pas assez d’éléments exploitables "
            "pour décrire précisément son avantage concurrentiel sans extrapoler."
        )

    if moat_themes:
        second = (
            f"Le rempart le plus spécifique qui ressort est lié à {_human_list(moat_themes[:3])}, "
            "ce qui peut rendre l’offre plus difficile à remplacer si ces éléments restent confirmés."
        )
    else:
        second = "Le rempart unique spécifique n’est donc pas assez documenté dans les sources locales disponibles."

    if crisis_themes:
        third = (
            f"Pour les périodes de crise, les protections documentées tournent autour de {_human_list(crisis_themes)}, "
            "ce qui peut soutenir la résilience sans supprimer le risque propre à l’entreprise."
        )
    else:
        third = (
            "La résistance aux crises n’est pas assez confirmée par les sources locales actuelles; "
            "elle doit être validée avec un rapport analyste ou un rapport annuel plus détaillé."
        )

    if pricing_themes:
        fourth = (
            f"Le pouvoir de prix semble appuyé par {_human_list(pricing_themes)}, "
            f"mais l’agent le traite comme une observation sourcée à surveiller plutôt qu’une garantie. Sources: {_compact_sources(sources)}."
        )
    else:
        fourth = (
            "Le pouvoir de monter les prix sans casser la demande n’est pas assez documenté dans les sources locales actuelles. "
            f"Sources: {_compact_sources(sources)}."
        )

    return " ".join([first, second, third, fourth])


def _source_confidence(evidence: dict[str, Any]) -> str:
    categories = sum(
        1
        for key in ["moat_themes", "crisis_themes", "pricing_themes"]
        if evidence.get(key)
    )
    if evidence.get("moat_label") and categories >= 3:
        return "HIGH"
    if categories >= 2:
        return "MEDIUM"
    if categories >= 1:
        return "LOW"
    return "VERY_LOW"


def _split_sentences(text: str) -> list[str]:
    cleaned = re.sub(r"\s+", " ", text.replace("\x00", " ")).strip()
    if not cleaned:
        return []
    sentences = re.split(r"(?<=[.!?])\s+", cleaned)
    return [sentence.strip() for sentence in sentences if 20 <= len(sentence.strip()) <= 420]


def _human_list(values: list[str]) -> str:
    clean = [value for value in values if value]
    if not clean:
        return "aucun élément clairement détecté"
    if len(clean) == 1:
        return clean[0]
    return ", ".join(clean[:-1]) + " et " + clean[-1]


def _compact_sources(sources: list[str]) -> str:
    if not sources:
        return "aucune source locale exploitable"
    if len(sources) <= 2:
        return "; ".join(sources)
    return "; ".join(sources[:2]) + f"; +{len(sources) - 2} autre(s)"


def _report_sort_key(path: Path) -> tuple[int, str, str]:
    name = path.name.upper()
    quality = 2 if "STOCK_ANALYST_REPORT" in name or "COMPANY_REPORT" in name else 1
    report_date = date_from_filename(path.name)
    return (quality, report_date, path.name)


def _indexed_reports(index_path: Path) -> dict[str, dict[str, Any]]:
    if not index_path.exists():
        return {}
    rows = {}
    for row in read_csv_records(index_path):
        file_name = str(row.get("file_name") or "").strip()
        if file_name:
            rows[file_name] = {field: row.get(field, "") for field in RESEARCH_INDEX_COLUMNS}
    return rows
