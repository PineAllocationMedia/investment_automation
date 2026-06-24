from __future__ import annotations

import re
from typing import Any

from .add_eligibility_engine import ADD_ALLOWED_STATUSES
from .asset_type_engine import is_etf_asset_analysis
from .utils import normalize_ticker, safe_float


COMPANY_DOSSIER_COLUMNS = [
    "ticker",
    "ticker_display",
    "target_status",
    "allocation_amount",
    "source_quality",
    "sources_used",
    "missing_sources",
    "business_model",
    "competitive_advantage",
    "crisis_protection",
    "pricing_power",
    "management_quality",
    "sector_health",
    "key_risks",
    "portfolio_fit",
    "dossier_text",
]


THEME_PATTERNS: list[tuple[str, str, str]] = [
    ("moat", "effets de réseau", r"\bnetwork effects?\b|\bplatform\b|\bmarketplace\b|\busers?\b|\badvertisers?\b"),
    ("moat", "coûts de changement", r"\bswitching costs?\b|\bmission[- ]critical\b|\bworkflow\b|\benterprise\b"),
    ("moat", "marque et distribution", r"\bbrand\b|\bglobal\b|\bdistribution\b|\binstalled base\b|\becosystem\b"),
    ("moat", "propriété intellectuelle", r"\bpatents?\b|\bintellectual property\b|\bproprietary\b|\bresearch and development\b"),
    ("moat", "échelle et données", r"\bscale\b|\bdata\b|\bmachine learning\b|\bartificial intelligence\b|\bAI\b"),
    ("moat", "avantage de coût", r"\bcost advantage\b|\befficien(?:t|cy)\b|\blow[- ]cost\b"),
    ("crisis", "revenus récurrents", r"\bsubscription\b|\brecurring\b|\bmaintenance\b|\bcontract\b"),
    ("crisis", "produit ou service essentiel", r"\bmission[- ]critical\b|\bessential\b|\bhealthcare\b|\bpharmaceutical\b|\bpayment\b"),
    ("crisis", "diversification", r"\bdiversified\b|\bvarious\b|\bmultiple\b|\bglobal\b"),
    ("crisis", "bilan ou cash-flow", r"\bcash flow\b|\bbalance sheet\b|\bfree cash flow\b|\bliquidity\b"),
    ("pricing", "pouvoir de prix", r"\bpricing power\b|\bpremium\b|\bprice increases?\b"),
    ("pricing", "valeur mesurable au client", r"\breturn on investment\b|\bROI\b|\bperformance\b|\bproductivity\b|\bautomation\b"),
    ("pricing", "service critique difficile à remplacer", r"\bsticky\b|\bswitching costs?\b|\bmission[- ]critical\b"),
    ("pricing", "marges soutenues", r"\bmargin(?:s)?\b|\bprofitability\b|\boperating leverage\b"),
]


SECTOR_FALLBACKS: list[tuple[str, dict[str, str]]] = [
    (
        "semiconductor",
        {
            "competitive_advantage": "L'avantage concurrentiel provient souvent de la complexité technique, de la propriété intellectuelle, de relations clients profondes et d'une exécution industrielle difficile à reproduire.",
            "crisis_protection": "La protection en crise est moyenne: les meilleurs acteurs restent stratégiques, mais le secteur peut traverser des cycles de demande et de capex violents.",
            "pricing_power": "Le pouvoir de prix existe surtout quand les produits sont critiques ou difficiles à remplacer, mais il peut se comprimer dans les creux cycliques.",
        },
    ),
    (
        "software|cloud|internet|interactive media|application",
        {
            "competitive_advantage": "L'avantage concurrentiel provient souvent des coûts de changement, des effets d'écosystème, de la distribution, des données et de la récurrence des revenus.",
            "crisis_protection": "La protection en crise vient surtout du caractère critique des logiciels, de contrats récurrents et de marges élevées, mais la valorisation peut rester sensible aux taux.",
            "pricing_power": "Le pouvoir de prix est le plus solide quand le produit augmente la productivité du client ou devient intégré dans ses processus essentiels.",
        },
    ),
    (
        "advertising|communication services|media",
        {
            "competitive_advantage": "L'avantage concurrentiel provient souvent de l'audience, des données, des effets de réseau et de la capacité à mesurer la performance pour les annonceurs.",
            "crisis_protection": "La protection en crise est imparfaite, car les budgets publicitaires sont cycliques; elle dépend de la force de la plateforme et de la rentabilité.",
            "pricing_power": "Le pouvoir de prix est indirect: il vient de la capacité à livrer un meilleur retour sur budget publicitaire que les alternatives.",
        },
    ),
    (
        "pharma|health|biotech|drug",
        {
            "competitive_advantage": "L'avantage concurrentiel vient souvent des brevets, du pipeline clinique, de l'expertise réglementaire, de la fabrication spécialisée et de la force commerciale.",
            "crisis_protection": "La demande santé peut être plus résiliente que la consommation cyclique, mais les résultats cliniques, brevets et remboursements restent déterminants.",
            "pricing_power": "Le pouvoir de prix dépend de la valeur clinique, du remboursement et des brevets; il doit être surveillé parce qu'il est politiquement sensible.",
        },
    ),
    (
        "payment|financial|bank|asset|insurance",
        {
            "competitive_advantage": "L'avantage concurrentiel provient souvent de l'échelle, de la confiance, de la marque, du réseau de partenaires et de la discipline du capital.",
            "crisis_protection": "La résilience dépend de la qualité du bilan, de la diversification des revenus et de la sensibilité aux cycles de crédit, de taux ou de marchés.",
            "pricing_power": "Le pouvoir de prix existe surtout quand le réseau ou le service réduit la friction pour les clients et conserve une forte valeur ajoutée.",
        },
    ),
    (
        "industrial|machinery|engineering|construction",
        {
            "competitive_advantage": "L'avantage concurrentiel vient souvent de la réputation, de l'expertise technique, de la base installée, des contrats longs et de la capacité d'exécution.",
            "crisis_protection": "La protection en crise varie selon les commandes et l'exposition aux cycles industriels, mais les services essentiels et l'infrastructure peuvent amortir la volatilité.",
            "pricing_power": "Le pouvoir de prix dépend de la spécialisation, de la criticité du service et de la capacité à répercuter l'inflation dans les contrats.",
        },
    ),
    (
        "consumer|retail|restaurant|luxury",
        {
            "competitive_advantage": "L'avantage concurrentiel vient souvent de la marque, de l'échelle, de l'expérience client, de la chaîne d'approvisionnement et de la fidélité.",
            "crisis_protection": "La protection en crise dépend de la nature essentielle ou premium de la demande et de la capacité à préserver les marges pendant les ralentissements.",
            "pricing_power": "Le pouvoir de prix est plus fort quand la marque ou l'expérience justifie une prime sans détruire le volume.",
        },
    ),
]


CURATED_COMPANY_CONTEXTS = {
    "GOOGL": {
        "business": "Alphabet est une plateforme de recherche, publicité numérique, YouTube, Android et Google Cloud.",
        "moat": "Son rempart spécifique vient surtout de l'échelle des données, de la distribution mondiale, de l'intégration de son écosystème et des effets d'habitude autour de Search, YouTube et Android.",
        "pricing": "Sa monétisation dépend de la qualité du ciblage publicitaire, de l'inventaire vidéo, du cloud et de l'intégration de l'IA, pas seulement d'une hausse directe des prix.",
        "risk": "Risques principaux: réglementation, concurrence IA/recherche et cyclicité des budgets publicitaires.",
    },
    "META": {
        "business": "Meta est une plateforme sociale et publicitaire centrée sur Facebook, Instagram, WhatsApp, Messenger et ses outils publicitaires.",
        "moat": "Son avantage vient des effets de réseau, de la taille de l'audience, des données d'engagement, des outils annonceurs et de la capacité à lancer de nouveaux formats à grande échelle.",
        "pricing": "Son pouvoir économique dépend de la valeur mesurable offerte aux annonceurs et de l'efficacité publicitaire sans détériorer l'expérience utilisateur.",
        "risk": "Risques principaux: réglementation, dépendance à la publicité, cycles de budgets marketing et dépenses lourdes en IA ou Reality Labs.",
    },
    "APP": {
        "business": "AppLovin est une entreprise de logiciel publicitaire et de monétisation d'applications mobiles.",
        "moat": "Son rempart repose sur ses modèles de ciblage, sa plateforme publicitaire, ses données de performance et l'intégration entre acquisition d'utilisateurs, enchères et monétisation.",
        "pricing": "Sa capacité à capter de la valeur dépend de la performance livrée aux annonceurs; si le retour sur budget publicitaire s'améliore, la plateforme peut capter davantage de budget client.",
        "risk": "Risques principaux: concurrence publicitaire mobile, changements de plateformes, confidentialité, cycles marketing et concentration client.",
    },
    "MSFT": {
        "business": "Microsoft combine logiciel d'entreprise, cloud Azure, Windows, Office, LinkedIn, sécurité, développeurs et IA.",
        "moat": "Son rempart vient des coûts de changement, de la distribution enterprise, de l'écosystème Office/Azure/Windows, des relations clients et de l'intégration de l'IA dans des produits critiques.",
        "pricing": "Son pouvoir de prix vient des abonnements, de la criticité des outils et de la capacité à ajouter des modules cloud, sécurité et IA dans une base installée massive.",
        "risk": "Risques principaux: concurrence cloud, dépenses d'infrastructure IA, réglementation et pression sur les multiples si la croissance ralentit.",
    },
    "AAPL": {
        "business": "Apple combine matériel premium, services, logiciel, semi-conducteurs internes et écosystème iPhone.",
        "moat": "Son avantage vient de la marque, de l'écosystème, de la fidélité client, de l'intégration matériel/logiciel/services et de coûts de changement élevés.",
        "pricing": "Son pouvoir de prix repose sur la valeur perçue des appareils, l'écosystème et les services récurrents.",
        "risk": "Risques principaux: maturité du smartphone, dépendance à l'iPhone, Chine, réglementation de l'App Store et valorisation exigeante.",
    },
    "AVGO": {
        "business": "Broadcom combine semi-conducteurs spécialisés, connectivité, infrastructure réseau et logiciels d'infrastructure.",
        "moat": "Son rempart vient de produits critiques, de positions fortes dans certaines niches, de relations clients profondes et d'une discipline d'acquisition/intégration.",
        "pricing": "Le pouvoir de prix dépend de la criticité des composants et logiciels, mais reste lié aux cycles d'investissement en semi-conducteurs et infrastructure.",
        "risk": "Risques principaux: cyclicité des semi-conducteurs, concentration client, intégration d'acquisitions et attentes élevées liées à l'IA.",
    },
    "LLY": {
        "business": "Eli Lilly est une pharmaceutique centrée sur médicaments brevetés, innovation clinique et franchises thérapeutiques à forte croissance.",
        "moat": "Son avantage repose sur la propriété intellectuelle, les essais cliniques, les capacités réglementaires, l'échelle commerciale et les barrières scientifiques.",
        "pricing": "Le pouvoir de prix dépend des brevets, de la valeur clinique et du remboursement, avec un encadrement important par assureurs, gouvernements et concurrence.",
        "risk": "Risques principaux: concentration de produits, résultats cliniques, pressions réglementaires sur les prix et capacité manufacturière.",
    },
    "MA": {
        "business": "Mastercard exploite un réseau mondial de paiements et de services liés aux transactions numériques.",
        "moat": "Son rempart vient des effets de réseau entre consommateurs, marchands, banques et processeurs, de la marque, de l'acceptation mondiale et de la fiabilité de l'infrastructure.",
        "pricing": "Son pouvoir économique vient du volume de transactions, de la migration du cash vers le numérique et des services à valeur ajoutée.",
        "risk": "Risques principaux: réglementation des frais, concurrence fintech, réseaux alternatifs et sensibilité aux volumes de consommation.",
    },
}


def build_company_dossier_rows(
    analyses: dict[str, dict[str, Any]],
    allocation_rows: list[dict[str, Any]],
    qualitative_moat_rows: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    qualitative_by_ticker = {
        normalize_ticker(row.get("ticker")): row
        for row in qualitative_moat_rows or []
        if normalize_ticker(row.get("ticker"))
    }
    allocation_amounts = {
        normalize_ticker(row.get("ticker")): safe_float(row.get("amount")) or 0.0
        for row in allocation_rows
        if (safe_float(row.get("amount")) or 0.0) > 0
    }
    targets: list[tuple[str, dict[str, Any], str, float]] = []
    for raw_ticker, analysis in analyses.items():
        ticker = normalize_ticker(raw_ticker or analysis.get("ticker"))
        if not ticker:
            continue
        is_allocated = ticker in allocation_amounts and ticker != "VFV.TO"
        is_eligible = analysis.get("add_eligibility_status") in ADD_ALLOWED_STATUSES
        has_sell_review = str(analysis.get("sell_decision") or analysis.get("recommended_action") or "").upper() in {
            "REVIEW_TRIM_25",
            "REVIEW_TRIM_50",
            "REVIEW_LIQUIDATE_PROGRESSIVELY",
            "LIQUIDATE_PROGRESSIVELY",
            "LIQUIDATE_URGENT_REVIEW",
        }
        if not (is_allocated or is_eligible or has_sell_review):
            continue
        target_status = "RECOMMANDÉ" if is_allocated else "VENTE_A_VALIDER" if has_sell_review else "ÉLIGIBLE_NON_RETENU"
        targets.append((ticker, analysis, target_status, allocation_amounts.get(ticker, 0.0)))

    rows = [
        build_company_dossier(
            analysis,
            qualitative_by_ticker.get(ticker),
            target_status=target_status,
            allocation_amount=amount,
        )
        for ticker, analysis, target_status, amount in targets
    ]
    return sorted(
        rows,
        key=lambda row: (
            {"RECOMMANDÉ": 0, "VENTE_A_VALIDER": 1, "ÉLIGIBLE_NON_RETENU": 2}.get(str(row.get("target_status")), 9),
            -(safe_float(row.get("allocation_amount")) or 0.0),
            -(safe_float(row.get("capital_allocation_score")) or 0.0),
            str(row.get("ticker") or ""),
        ),
    )


def build_company_dossier(
    analysis: dict[str, Any],
    qualitative_row: dict[str, Any] | None = None,
    *,
    target_status: str = "",
    allocation_amount: float = 0.0,
) -> dict[str, Any]:
    ticker = normalize_ticker(analysis.get("ticker")) or str(analysis.get("ticker") or "")
    company = _company_name(ticker, analysis)
    if analysis.get("benchmark_role") is True or is_etf_asset_analysis(analysis):
        return _etf_dossier(analysis, ticker, company, target_status, allocation_amount)

    source_quality, sources, missing = _source_profile(analysis, qualitative_row)
    business_model = _business_model_text(company, analysis)
    competitive_advantage = _competitive_advantage_text(analysis, qualitative_row)
    crisis_protection = _crisis_protection_text(analysis, qualitative_row)
    pricing_power = _pricing_power_text(analysis, qualitative_row)
    management_quality = _management_quality_text(analysis)
    sector_health = _sector_health_text(analysis)
    key_risks = _key_risks_text(analysis)
    portfolio_fit = _portfolio_fit_text(analysis, allocation_amount)
    (
        source_quality,
        sources,
        business_model,
        competitive_advantage,
        pricing_power,
        key_risks,
    ) = _apply_curated_context_if_needed(
        analysis,
        source_quality,
        sources,
        missing,
        business_model,
        competitive_advantage,
        pricing_power,
        key_risks,
    )
    dossier_text = _dossier_paragraph(
        company=company,
        source_quality=source_quality,
        sources=sources,
        business_model=business_model,
        competitive_advantage=competitive_advantage,
        crisis_protection=crisis_protection,
        pricing_power=pricing_power,
        management_quality=management_quality,
        sector_health=sector_health,
        key_risks=key_risks,
        portfolio_fit=portfolio_fit,
    )
    return {
        "ticker": ticker,
        "ticker_display": analysis.get("ticker_display") or ticker,
        "target_status": target_status,
        "allocation_amount": round(allocation_amount, 2),
        "source_quality": source_quality,
        "sources_used": "; ".join(sources),
        "missing_sources": "; ".join(missing),
        "business_model": business_model,
        "competitive_advantage": competitive_advantage,
        "crisis_protection": crisis_protection,
        "pricing_power": pricing_power,
        "management_quality": management_quality,
        "sector_health": sector_health,
        "key_risks": key_risks,
        "portfolio_fit": portfolio_fit,
        "dossier_text": dossier_text,
    }


def _source_profile(analysis: dict[str, Any], qualitative_row: dict[str, Any] | None) -> tuple[str, list[str], list[str]]:
    sources: list[str] = []
    missing: list[str] = []
    local_status = str((qualitative_row or {}).get("source_status") or "")
    local_sources = str((qualitative_row or {}).get("sources") or "").strip()
    if local_status == "LOCAL_RESEARCH_REPORT" and local_sources:
        sources.append(f"rapports locaux BNCD/Morningstar/annuel: {local_sources}")
    else:
        missing.append("rapport local BNCD/Morningstar/annuel")

    if str(analysis.get("business_summary") or "").strip():
        sources.append("profil d'activité Yahoo Finance/yfinance")
    else:
        missing.append("résumé d'activité gratuit Yahoo Finance")

    official_sources = _clean_list(analysis.get("official_data_sources"))
    if official_sources or analysis.get("sec_edgar_cik"):
        sources.append("SEC EDGAR companyfacts")
    elif str(analysis.get("country") or "").lower() in {"united states", "usa", "us"}:
        missing.append("données SEC exploitables")

    if _clean_list(analysis.get("news_context_sources")):
        sources.append("nouvelles publiques gratuites")
    if _clean_list(analysis.get("market_growth_thesis_sources")):
        sources.append("sources publiques de thèse de marché")
    if _clean_list(analysis.get("data_source_notes")) or analysis.get("source"):
        sources.append("métriques financières gratuites yfinance/cache local")

    source_count = len(sources)
    has_local = any("rapports locaux" in source for source in sources)
    has_summary = any("profil d'activité" in source for source in sources)
    has_official = any("SEC EDGAR" in source for source in sources)
    if has_local and has_summary and (has_official or source_count >= 4):
        quality = "FULL_SOURCE_BACKED"
    elif has_local or (has_summary and source_count >= 3):
        quality = "PARTIAL_SOURCE_BACKED"
    elif has_summary or has_official or source_count >= 2:
        quality = "BASIC_AUTOMATED"
    else:
        quality = "LIMITED_SOURCE"
    return quality, _unique(sources), _unique(missing)


def _apply_curated_context_if_needed(
    analysis: dict[str, Any],
    source_quality: str,
    sources: list[str],
    missing: list[str],
    business_model: str,
    competitive_advantage: str,
    pricing_power: str,
    key_risks: str,
) -> tuple[str, list[str], str, str, str, str]:
    ticker = normalize_ticker(analysis.get("ticker")) or ""
    context = CURATED_COMPANY_CONTEXTS.get(ticker.replace(".TO", "").replace(".V", ""))
    if not context:
        return source_quality, sources, business_model, competitive_advantage, pricing_power, key_risks
    missing_text = " ".join(missing).lower()
    needs_context = (
        "résumé d'activité gratuit yahoo finance" in missing_text
        or "utilise cette classification" in business_model.lower()
        or "source qualitative détaillée doit encore être renforcée" in competitive_advantage.lower()
    )
    if not needs_context:
        return source_quality, sources, business_model, competitive_advantage, pricing_power, key_risks
    sources = _unique(sources + ["fiche interne prudente du modèle"])
    if source_quality == "LIMITED_SOURCE":
        source_quality = "BASIC_AUTOMATED"
    business_model = context["business"]
    competitive_advantage = f"Fiche interne prudente: {context['moat']}"
    pricing_power = f"Fiche interne prudente: {context['pricing']}"
    key_risks = f"{key_risks} Fiche interne prudente: {context['risk']}"
    return source_quality, sources, business_model, competitive_advantage, pricing_power, key_risks


def _business_model_text(company: str, analysis: dict[str, Any]) -> str:
    sector = str(analysis.get("sector") or analysis.get("sector_name") or "").strip()
    industry = str(analysis.get("industry") or "").strip()
    summary = str(analysis.get("business_summary") or "").strip()
    themes = _themes_from_text(summary)
    if themes:
        return (
            f"{company} est classée dans {sector or 'un secteur à confirmer'}"
            f"{f' / {industry}' if industry and industry.lower() not in sector.lower() else ''}; "
            f"le profil gratuit détecte surtout {_human_list(themes[:5])}."
        )
    if sector or industry:
        return f"{company} est classée dans {sector or 'secteur non précisé'}{f' / {industry}' if industry else ''}; le modèle utilise cette classification pour cadrer l'analyse qualitative."
    return f"Le modèle ne dispose pas d'un profil d'activité gratuit assez complet pour {company}; la fiche reste donc prudente."


def _competitive_advantage_text(analysis: dict[str, Any], qualitative_row: dict[str, Any] | None) -> str:
    local = _theme_text(qualitative_row, "competitive_advantage_themes")
    if local:
        return f"Les sources locales mentionnent {local} comme éléments d'avantage concurrentiel."
    summary_themes = _category_themes(analysis, "moat")
    if summary_themes:
        return f"Le profil d'activité gratuit fait ressortir {summary_themes}; le modèle les traite comme indices de moat à confirmer."
    if analysis.get("moat_clear") is True:
        return "Le moat est marqué clair dans les données du modèle, mais la source qualitative détaillée doit encore être renforcée si la position grossit."
    return _sector_fallback(analysis, "competitive_advantage")


def _crisis_protection_text(analysis: dict[str, Any], qualitative_row: dict[str, Any] | None) -> str:
    local = _theme_text(qualitative_row, "crisis_protection_themes")
    if local:
        return f"Les sources locales indiquent {local} comme protections possibles en période difficile."
    summary_themes = _category_themes(analysis, "crisis")
    if summary_themes:
        return f"Les indices automatiques de résilience repérés sont {summary_themes}, à confirmer par rapport annuel ou analyse professionnelle."
    parts = []
    if analysis.get("balance_sheet_strong") is True:
        parts.append("bilan jugé solide")
    if (safe_float(analysis.get("free_cash_flow_margin")) or 0.0) > 0.10:
        parts.append("free cash flow positif et significatif")
    if analysis.get("profit_margins") is not None and (safe_float(analysis.get("profit_margins")) or 0.0) > 0.10:
        parts.append("marges positives")
    if parts:
        return f"La protection en crise est appuyée par {_human_list(parts)}, mais elle ne supprime pas le risque de cycle ou de valorisation."
    return _sector_fallback(analysis, "crisis_protection")


def _pricing_power_text(analysis: dict[str, Any], qualitative_row: dict[str, Any] | None) -> str:
    local = _theme_text(qualitative_row, "pricing_power_themes")
    if local:
        return f"Les sources locales mentionnent {local} comme indices de pouvoir de prix."
    summary_themes = _category_themes(analysis, "pricing")
    if summary_themes:
        return f"Les indices automatiques de pouvoir de prix sont {summary_themes}; ils servent de support qualitatif, pas de garantie."
    if analysis.get("net_margin_stable_or_expanding") is True or analysis.get("margin_stable_or_expanding") is True:
        return "Les marges stables ou en expansion suggèrent un certain pouvoir économique, mais la cause exacte doit être validée."
    return _sector_fallback(analysis, "pricing_power")


def _management_quality_text(analysis: dict[str, Any]) -> str:
    parts: list[str] = []
    if analysis.get("management_quality_good") is True:
        parts.append("qualité de gestion marquée favorable")
    elif analysis.get("management_quality_good") is False:
        parts.append("qualité de gestion à surveiller")
    else:
        parts.append("qualité de gestion directe non pleinement observable automatiquement")
    if analysis.get("balance_sheet_strong") is True:
        parts.append("bilan solide")
    elif analysis.get("balance_sheet_strong") is False:
        parts.append("bilan prudent à vérifier")
    fcf_margin = safe_float(analysis.get("free_cash_flow_margin"))
    if fcf_margin is not None:
        parts.append(f"marge FCF {fcf_margin:.1%}")
    share_count = safe_float(analysis.get("share_count_cagr_5y") or analysis.get("share_count_growth_1y"))
    if share_count is not None:
        parts.append(f"variation du nombre d'actions {share_count:.1%}")
    shareholder = analysis.get("shareholder_discipline_status")
    if shareholder:
        parts.append(f"discipline actionnariale {str(shareholder).lower()}")
    return "; ".join(parts) + "."


def _sector_health_text(analysis: dict[str, Any]) -> str:
    parts = []
    status = analysis.get("market_growth_thesis_status")
    if status:
        parts.append(f"thèse de marché {str(status).replace('_', ' ').lower()}")
    score = safe_float(analysis.get("market_growth_thesis_score"))
    if score is not None:
        parts.append(f"score de thèse {score:.0f}/100")
    benchmark_10y = safe_float(analysis.get("benchmark_10y_cagr"))
    benchmark_5y = safe_float(analysis.get("benchmark_5y_cagr"))
    if benchmark_10y is not None:
        parts.append(f"benchmark 10 ans {benchmark_10y:.1%}")
    elif benchmark_5y is not None:
        parts.append(f"benchmark 5 ans {benchmark_5y:.1%}")
    themes = _clean_list(analysis.get("market_growth_thesis_themes"))
    if themes:
        parts.append(f"thèmes: {_human_list(themes[:4])}")
    if parts:
        return "; ".join(parts) + "."
    return "La santé du secteur est évaluée surtout par classification sectorielle, benchmark et données de marché gratuites; elle reste à valider si la position grossit."


def _key_risks_text(analysis: dict[str, Any]) -> str:
    risks: list[str] = []
    if analysis.get("regulatory_risk_high") is True:
        risks.append("risque réglementaire élevé")
    if analysis.get("geopolitical_risk_high") is True:
        risks.append("risque géopolitique élevé")
    if analysis.get("single_product_dependency_high") is True:
        risks.append("dépendance produit élevée")
    if analysis.get("quality_but_too_expensive") is True:
        risks.append("qualité possiblement trop chère")
    cycle = str(analysis.get("cycle_bubble_risk_level") or "").replace("_", " ").lower()
    if cycle and cycle not in {"normal", "n/d"}:
        risks.append(f"risque cycle/bulle {cycle}")
    if str(analysis.get("news_context_status") or "").upper() in {"FUNDAMENTAL_RISK_POSSIBLE", "NEGATIVE_CONTEXT"}:
        risks.append("nouvelles récentes à valider")
    sell_status = str(analysis.get("sell_status") or analysis.get("liquidation_status") or "").upper()
    if sell_status in {"YELLOW", "ORANGE", "RED"}:
        risks.append(f"signal de vente/surveillance {sell_status}")
    if not risks:
        return "Aucun risque bloquant clair n'est détecté, mais la valorisation, la concurrence et l'exécution restent à surveiller."
    return _human_list(_unique(risks)) + "."


def _portfolio_fit_text(analysis: dict[str, Any], allocation_amount: float) -> str:
    score = safe_float(analysis.get("capital_allocation_score"))
    conviction = safe_float(analysis.get("conviction_score"))
    opportunity = str(analysis.get("opportunity_cost_status") or "N/D").replace("_", " ").lower()
    expected = str(analysis.get("expected_cagr_quality") or "N/D").replace("_", " ").lower()
    thesis = str(analysis.get("thesis_status") or "N/D").replace("_", " ").lower()
    base = (
        f"Fit portefeuille: score allocation {score:.1f}/100" if score is not None else "Fit portefeuille: score allocation non disponible"
    )
    if conviction is not None:
        base += f", conviction {conviction:.0f}/100"
    base += f", qualité CAGR {expected}, thèse {thesis}, coût d'opportunité {opportunity}."
    if allocation_amount > 0:
        base += " La position reçoit du capital parce que ce profil reste admissible après concentration et garde-fous."
    else:
        base += " La position est utile à surveiller, mais elle ne reçoit pas forcément de capital dans cette analyse."
    return base


def _dossier_paragraph(
    *,
    company: str,
    source_quality: str,
    sources: list[str],
    business_model: str,
    competitive_advantage: str,
    crisis_protection: str,
    pricing_power: str,
    management_quality: str,
    sector_health: str,
    key_risks: str,
    portfolio_fit: str,
) -> str:
    source_text = _human_list(sources[:4]) if sources else "sources automatiques limitées"
    return " ".join(
        [
            f"Fiche qualitative automatique de {company}: niveau de preuve {source_quality}, sources utilisées: {source_text}.",
            business_model,
            f"Avantage concurrentiel et rempart: {competitive_advantage} Protection en crise: {crisis_protection} Pouvoir de prix: {pricing_power}",
            f"Gestion et secteur: {management_quality} {sector_health}",
            f"Risques à surveiller: {key_risks} {portfolio_fit}",
        ]
    )


def _etf_dossier(
    analysis: dict[str, Any],
    ticker: str,
    company: str,
    target_status: str,
    allocation_amount: float,
) -> dict[str, Any]:
    text = (
        f"{company} est traité comme un ETF ou benchmark. Le modèle n'analyse donc pas un moat, une équipe de gestion ou un pouvoir de prix comme pour une compagnie; "
        "il analyse plutôt son rôle de diversification, de stabilisateur ou de coût d'opportunité."
    )
    return {
        "ticker": ticker,
        "ticker_display": analysis.get("ticker_display") or ticker,
        "target_status": target_status,
        "allocation_amount": round(allocation_amount, 2),
        "source_quality": "ETF_CLASSIFICATION",
        "sources_used": "classification interne; données yfinance/cache local",
        "missing_sources": "",
        "business_model": text,
        "competitive_advantage": "N/A pour ETF.",
        "crisis_protection": "Diversification selon la composition de l'ETF.",
        "pricing_power": "N/A pour ETF.",
        "management_quality": "N/A pour ETF.",
        "sector_health": "Analysé par rôle, catégorie, volatilité et benchmark.",
        "key_risks": "Risque de marché lié aux actifs détenus par l'ETF.",
        "portfolio_fit": _portfolio_fit_text(analysis, allocation_amount),
        "dossier_text": text,
    }


def _company_name(ticker: str, analysis: dict[str, Any]) -> str:
    name = str(
        analysis.get("company_name")
        or analysis.get("company_name_found")
        or analysis.get("long_name")
        or ticker
    ).strip()
    if name and name.upper() != ticker.upper():
        return f"{ticker} ({name})"
    return ticker


def _category_themes(analysis: dict[str, Any], category: str) -> str:
    summary = str(analysis.get("business_summary") or "").strip()
    found: list[str] = []
    for pattern_category, label, pattern in THEME_PATTERNS:
        if pattern_category == category and re.search(pattern, summary, flags=re.IGNORECASE) and label not in found:
            found.append(label)
    return _human_list(found[:5]) if found else ""


def _themes_from_text(text: str) -> list[str]:
    if not text:
        return []
    candidates = []
    lower = text.lower()
    keyword_map = [
        ("cloud", "cloud"),
        ("artificial intelligence", "IA"),
        ("machine learning", "IA"),
        ("advertising", "publicité"),
        ("search", "recherche"),
        ("software", "logiciels"),
        ("subscription", "abonnements"),
        ("semiconductor", "semi-conducteurs"),
        ("payment", "paiements"),
        ("pharmaceutical", "pharmaceutique"),
        ("medical", "santé"),
        ("retail", "commerce de détail"),
        ("industrial", "industrie"),
        ("automation", "automatisation"),
        ("marketplace", "plateforme"),
        ("e-commerce", "commerce électronique"),
        ("logistics", "logistique"),
        ("data", "données"),
        ("security", "cybersécurité"),
    ]
    for keyword, label in keyword_map:
        if keyword in lower and label not in candidates:
            candidates.append(label)
    return candidates[:6]


def _theme_text(row: dict[str, Any] | None, field: str) -> str:
    if not row:
        return ""
    values = _clean_list(row.get(field))
    values = [value for value in values if value and value.upper() not in {"N/A ETF", "AUCUN"}]
    return _human_list(values[:5]) if values else ""


def _sector_fallback(analysis: dict[str, Any], field: str) -> str:
    text = " ".join(
        str(analysis.get(key) or "")
        for key in ["sector", "sector_name", "industry", "business_profile", "business_profile_label"]
    ).lower()
    for pattern, values in SECTOR_FALLBACKS:
        if re.search(pattern, text, flags=re.IGNORECASE):
            return values[field]
    return "Le modèle n'a pas assez de sources qualitatives spécifiques; il reste volontairement prudent et évite de surinterpréter le moat."


def _clean_list(values: Any) -> list[str]:
    if values is None or values == "":
        return []
    if isinstance(values, list):
        raw = values
    else:
        raw = re.split(r"[;,]", str(values))
    clean = []
    for value in raw:
        text = str(value).strip()
        if text and text.lower() not in {"aucun", "none", "n/d", "nan"}:
            clean.append(text)
    return _unique(clean)


def _unique(values: list[str]) -> list[str]:
    output: list[str] = []
    seen: set[str] = set()
    for value in values:
        clean = str(value).strip()
        key = clean.lower()
        if clean and key not in seen:
            output.append(clean)
            seen.add(key)
    return output


def _human_list(values: list[str]) -> str:
    clean = [str(value).strip() for value in values if str(value).strip()]
    if not clean:
        return ""
    if len(clean) == 1:
        return clean[0]
    return ", ".join(clean[:-1]) + " et " + clean[-1]
