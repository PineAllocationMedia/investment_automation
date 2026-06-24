from __future__ import annotations

import re
import unicodedata
from typing import Any

from .utils import normalize_ticker, safe_float


DEFAULT_BENCHMARK_BY_TICKER = {
    "AAPL": "XLK",
    "GOOGL": "XLC",
    "META": "XLC",
    "AMZN": "XLY",
    "NVDA": "SOXX",
    "COST": "XLP",
    "V": "IPAY",
    "UNH": "XLV",
    "HD": "XLY",
    "ADBE": "IGV",
    "OR.PA": "XLP",
    "RMS.PA": "XLY",
    "AIR.PA": "XLI",
    "TSM": "SOXX",
    "INTU": "IGV",
    "ISRG": "XLV",
    "SPGI": "KCE",
    "MCO": "KCE",
    "DHR": "XLV",
    "LIN": "XLB",
    "ACN": "IGV",
    "BRK-B": "XLF",
    "JPM": "XLF",
    "NVO": "XLV",
    "SAP": "IGV",
    "SONY": "XLC",
    "MELI": "XLY",
    "SHOP": "IGV",
    "ROP": "XLI",
    "TXN": "SOXX",
    "NOW": "IGV",
    "CRM": "IGV",
    "LRCX": "SOXX",
    "KLAC": "SOXX",
    "SNPS": "SOXX",
    "CDNS": "SOXX",
    "NPI.TO": "ICLN",
    "BLX.TO": "ICLN",
    "FTS.TO": "XLU",
    "TRI.TO": "XLC",
    "SLF.TO": "XLF",
    "NTR.TO": "XLB",
    "MFC.TO": "XLF",
    "ENB.TO": "XLE",
    "TD.TO": "XLF",
    "VRT": "XLI",
    "APH": "XLI",
    "WDC": "XLK",
    "ROK": "XLI",
    "BLK": "KCE",
    "NEE": "XLU",
    "C": "XLF",
    "PGR": "KIE",
    "PLD": "VNQ",
    "WELL": "VNQ",
    "BX": "KCE",
    "KKR": "KCE",
    "CCO.TO": "URA",
    "CLS.TO": "XLK",
    "DSG.TO": "IGV",
    "GIB-A.TO": "IGV",
    "FICO": "IGV",
    "ANET": "XLK",
    "ADI": "SOXX",
    "QCOM": "SOXX",
    "MU": "SOXX",
    "MPWR": "SOXX",
    "SMCI": "XLK",
    "AMAT": "SOXX",
    "AMGN": "XLV",
    "GILD": "XLV",
    "ABBV": "XLV",
    "BMY": "XLV",
    "MRK": "XLV",
    "TMO": "XLV",
    "ABT": "XLV",
    "NEM": "GDX",
    "AEM.TO": "GDX",
    "FNV.TO": "GDX",
    "WPM.TO": "GDX",
    "COP": "XLE",
    "RTX": "XLI",
    "HON": "XLI",
    "NVT": "XLI",
    "MOD": "XLI",
    "ETN": "XLI",
    "TT": "XLI",
    "PH": "XLI",
    "PWR": "XLI",
    "RBA.TO": "XLI",
    "AIQUY": "XLB",
    "ECL": "XLB",
    "DOL.TO": "XLP",
    "TJX": "XLY",
    "ALNY": "XLV",
    "STX": "XLK",
}

PAIR_RELEVANCE_OVERRIDES = {
    ("AVGO", "SOXX"): ("HIGH", "SOXX cible directement les semi-conducteurs."),
    ("ASML", "SOXX"): ("HIGH", "SOXX est un proxy pertinent pour la chaîne semi-conducteurs."),
    ("TSM", "SOXX"): ("HIGH", "SOXX cible directement les semi-conducteurs."),
    ("NVDA", "SOXX"): ("HIGH", "SOXX cible directement les semi-conducteurs."),
    ("LRCX", "SOXX"): ("HIGH", "SOXX couvre l’écosystème semi-conducteurs."),
    ("KLAC", "SOXX"): ("HIGH", "SOXX couvre l’écosystème semi-conducteurs."),
    ("TXN", "SOXX"): ("HIGH", "SOXX couvre l’écosystème semi-conducteurs."),
    ("SNPS", "SOXX"): ("HIGH", "SOXX couvre l’écosystème semi-conducteurs."),
    ("CDNS", "SOXX"): ("HIGH", "SOXX couvre l’écosystème semi-conducteurs."),
    ("MA", "IPAY"): ("HIGH", "IPAY est spécialisé dans les paiements numériques."),
    ("V", "IPAY"): ("HIGH", "IPAY est spécialisé dans les paiements numériques."),
    ("MSFT", "IGV"): ("MEDIUM", "IGV est pertinent pour le logiciel, mais Microsoft est plus diversifiée."),
    ("CSU.TO", "IGV"): ("MEDIUM", "IGV aide pour le logiciel, mais CSU est un cas vertical/acquéreur particulier."),
    ("INTU", "IGV"): ("HIGH", "IGV est pertinent pour les logiciels applicatifs."),
    ("ADBE", "IGV"): ("HIGH", "IGV est pertinent pour les logiciels applicatifs."),
    ("NOW", "IGV"): ("HIGH", "IGV est pertinent pour les logiciels applicatifs."),
    ("CRM", "IGV"): ("HIGH", "IGV est pertinent pour les logiciels applicatifs."),
    ("SHOP", "IGV"): ("MEDIUM", "IGV est utile, mais Shopify dépend aussi du commerce en ligne."),
    ("LLY", "XLV"): ("MEDIUM", "XLV est santé/pharma large; utile, mais pas spécifique aux moteurs propres à LLY."),
    ("UNH", "XLV"): ("HIGH", "XLV est pertinent pour la santé américaine."),
    ("NVO", "XLV"): ("MEDIUM", "XLV est santé large; utile, mais pas spécifique aux moteurs propres à NVO."),
    ("ISRG", "XLV"): ("MEDIUM", "XLV est santé large; utile, mais pas spécifique au matériel médical robotisé."),
    ("DHR", "XLV"): ("MEDIUM", "XLV est santé large; utile, mais pas parfaitement ciblé."),
    ("SIEGY", "XLI"): ("MEDIUM", "XLI est industriel large; utile, mais pas spécifique à l’automatisation européenne."),
    ("SBGSY", "XLI"): ("MEDIUM", "XLI est industriel large; utile, mais pas spécifique à Schneider Electric."),
    ("WSP.TO", "XLI"): ("MEDIUM", "XLI est industriel large; utile, mais pas spécifique à l’ingénierie canadienne."),
    ("AIR.PA", "XLI"): ("MEDIUM", "XLI est industriel large; utile, mais pas spécifique à l’aéronautique européenne."),
    ("ROP", "XLI"): ("MEDIUM", "XLI est industriel large; utile, mais Roper est plus mixte logiciel/industrie."),
    ("BAM", "KCE"): ("MEDIUM", "KCE est financier/capital markets; utile, mais imparfait pour les actifs alternatifs."),
    ("SPGI", "KCE"): ("HIGH", "KCE est pertinent pour les services financiers et marchés de capitaux."),
    ("MCO", "KCE"): ("HIGH", "KCE est pertinent pour les services financiers et marchés de capitaux."),
    ("BRK-B", "XLF"): ("MEDIUM", "XLF est financier large; utile, mais Berkshire est très diversifiée."),
    ("JPM", "XLF"): ("HIGH", "XLF est pertinent pour une grande banque américaine."),
    ("AAPL", "XLK"): ("MEDIUM", "XLK est technologie large; utile, mais Apple dépend aussi du hardware et des services."),
    ("GOOGL", "XLC"): ("MEDIUM", "XLC est communication/plateformes; utile, mais Alphabet est diversifiée."),
    ("META", "XLC"): ("HIGH", "XLC est pertinent pour les plateformes de communication, médias sociaux et publicité numérique."),
    ("AMZN", "XLY"): ("MEDIUM", "XLY est consommation discrétionnaire; utile, mais Amazon est aussi cloud et publicité."),
    ("TSLA", "XLY"): ("MEDIUM", "XLY est consommation discrétionnaire; utile, mais Tesla est très spécifique."),
    ("COST", "XLP"): ("HIGH", "XLP est pertinent pour la consommation défensive."),
    ("HD", "XLY"): ("MEDIUM", "XLY est utile, mais Home Depot dépend aussi du cycle immobilier."),
    ("OR.PA", "XLP"): ("MEDIUM", "XLP est consommation défensive large; utile, mais imparfait pour le luxe/beauté européen."),
    ("RMS.PA", "XLY"): ("MEDIUM", "XLY est consommation discrétionnaire; utile, mais imparfait pour le luxe européen."),
    ("LIN", "XLB"): ("MEDIUM", "XLB est matériaux large; utile, mais imparfait pour les gaz industriels."),
    ("NPI.TO", "ICLN"): ("MEDIUM", "ICLN est énergie renouvelable; utile, mais imparfait pour une productrice canadienne."),
    ("BLX.TO", "ICLN"): ("MEDIUM", "ICLN est énergie renouvelable; utile, mais imparfait pour une productrice canadienne."),
    ("FTS.TO", "XLU"): ("HIGH", "XLU est pertinent pour les services publics nord-américains."),
    ("TRI.TO", "XLC"): ("MEDIUM", "XLC est utile pour les données et l'information, mais Thomson Reuters reste un cas spécialisé."),
    ("SLF.TO", "XLF"): ("HIGH", "XLF est pertinent pour les grandes financières et assureurs."),
    ("NTR.TO", "XLB"): ("MEDIUM", "XLB est matériaux large; utile, mais imparfait pour les engrais et l'agriculture."),
    ("MFC.TO", "XLF"): ("HIGH", "XLF est pertinent pour les grandes financières et assureurs."),
    ("ENB.TO", "XLE"): ("MEDIUM", "XLE est énergie large; utile, mais imparfait pour les pipelines."),
    ("TD.TO", "XLF"): ("HIGH", "XLF est pertinent pour les grandes banques nord-américaines."),
    ("VRT", "XLI"): ("MEDIUM", "XLI est industriel large; utile pour l’infrastructure électrique et centres de données."),
    ("APH", "XLI"): ("MEDIUM", "XLI est industriel large; utile pour les composants et connecteurs industriels."),
    ("WDC", "XLK"): ("MEDIUM", "XLK est technologie large; utile pour le hardware et stockage."),
    ("ROK", "XLI"): ("HIGH", "XLI est pertinent pour l’automatisation industrielle."),
    ("BLK", "KCE"): ("HIGH", "KCE est pertinent pour les gestionnaires d’actifs et marchés de capitaux."),
    ("NEE", "XLU"): ("HIGH", "XLU est pertinent pour les services publics et producteurs d’électricité."),
    ("C", "XLF"): ("HIGH", "XLF est pertinent pour une grande banque américaine."),
    ("PGR", "KIE"): ("HIGH", "KIE est pertinent pour les assureurs américains."),
    ("PLD", "VNQ"): ("HIGH", "VNQ est pertinent pour les REIT et l’immobilier coté."),
    ("WELL", "VNQ"): ("HIGH", "VNQ est pertinent pour les REIT et l’immobilier coté."),
    ("BX", "KCE"): ("MEDIUM", "KCE est utile pour les marchés de capitaux, mais imparfait pour les actifs alternatifs."),
    ("KKR", "KCE"): ("MEDIUM", "KCE est utile pour les marchés de capitaux, mais imparfait pour les actifs alternatifs."),
    ("CCO.TO", "URA"): ("HIGH", "URA est pertinent pour l’uranium et le nucléaire."),
    ("CLS.TO", "XLK"): ("MEDIUM", "XLK est technologie large; utile pour la fabrication électronique."),
    ("DSG.TO", "IGV"): ("HIGH", "IGV est pertinent pour les logiciels applicatifs."),
    ("GIB-A.TO", "IGV"): ("HIGH", "IGV est pertinent pour les services TI et logiciels."),
    ("FICO", "IGV"): ("MEDIUM", "IGV est pertinent pour le logiciel analytique, même si FICO est très spécialisé."),
    ("ANET", "XLK"): ("MEDIUM", "XLK est technologie large; utile pour l’équipement réseau."),
    ("ADI", "SOXX"): ("HIGH", "SOXX est pertinent pour les semi-conducteurs analogiques."),
    ("QCOM", "SOXX"): ("HIGH", "SOXX est pertinent pour les semi-conducteurs."),
    ("MU", "SOXX"): ("HIGH", "SOXX est pertinent pour les semi-conducteurs mémoire."),
    ("MPWR", "SOXX"): ("HIGH", "SOXX est pertinent pour les semi-conducteurs de puissance."),
    ("SMCI", "XLK"): ("MEDIUM", "XLK est technologie large; utile pour serveurs et infrastructure matérielle."),
    ("AMAT", "SOXX"): ("HIGH", "SOXX couvre l’écosystème semi-conducteurs."),
    ("AMGN", "XLV"): ("HIGH", "XLV est pertinent pour les grandes biopharmas."),
    ("GILD", "XLV"): ("HIGH", "XLV est pertinent pour les grandes biopharmas."),
    ("ABBV", "XLV"): ("HIGH", "XLV est pertinent pour les grandes pharmas."),
    ("BMY", "XLV"): ("HIGH", "XLV est pertinent pour les grandes pharmas."),
    ("MRK", "XLV"): ("HIGH", "XLV est pertinent pour les grandes pharmas."),
    ("TMO", "XLV"): ("MEDIUM", "XLV est santé large; utile, mais Thermo Fisher dépend aussi des outils de laboratoire."),
    ("ABT", "XLV"): ("HIGH", "XLV est pertinent pour les grandes entreprises de santé."),
    ("NEM", "GDX"): ("HIGH", "GDX est pertinent pour les producteurs aurifères."),
    ("AEM.TO", "GDX"): ("HIGH", "GDX est pertinent pour les producteurs aurifères."),
    ("FNV.TO", "GDX"): ("MEDIUM", "GDX est lié à l’or, mais imparfait pour un modèle de redevances."),
    ("WPM.TO", "GDX"): ("MEDIUM", "GDX est lié aux métaux précieux, mais imparfait pour un modèle de streaming/redevances."),
    ("COP", "XLE"): ("HIGH", "XLE est pertinent pour les grandes entreprises d’énergie."),
    ("RTX", "XLI"): ("HIGH", "XLI est pertinent pour l’aérospatiale et défense industrielle."),
    ("HON", "XLI"): ("HIGH", "XLI est pertinent pour les industriels diversifiés."),
    ("NVT", "XLI"): ("MEDIUM", "XLI est industriel large; utile pour les équipements électriques."),
    ("MOD", "XLI"): ("MEDIUM", "XLI est industriel large; utile pour les équipements thermiques."),
    ("ETN", "XLI"): ("HIGH", "XLI est pertinent pour les équipements électriques industriels."),
    ("TT", "XLI"): ("HIGH", "XLI est pertinent pour les industriels d’efficacité énergétique et HVAC."),
    ("PH", "XLI"): ("HIGH", "XLI est pertinent pour les industriels diversifiés."),
    ("PWR", "XLI"): ("HIGH", "XLI est pertinent pour ingénierie, infrastructures et services industriels."),
    ("RBA.TO", "XLI"): ("MEDIUM", "XLI est industriel large; utile pour l’équipement et les enchères industrielles."),
    ("AIQUY", "XLB"): ("MEDIUM", "XLB est matériaux large; utile, mais imparfait pour les gaz industriels."),
    ("ECL", "XLB"): ("MEDIUM", "XLB est matériaux large; utile pour les chimiques spécialisés."),
    ("DOL.TO", "XLP"): ("MEDIUM", "XLP est consommation défensive; utile, mais imparfait pour Dollarama."),
    ("TJX", "XLY"): ("MEDIUM", "XLY est consommation discrétionnaire; utile pour le commerce de détail."),
    ("ALNY", "XLV"): ("MEDIUM", "XLV est santé large; utile, mais imparfait pour une biotech spécialisée."),
    ("STX", "XLK"): ("MEDIUM", "XLK est technologie large; utile pour le stockage et le hardware."),
}

BENCHMARK_FOCUS_TERMS = {
    "SOXX": {"semiconductor", "semiconductors", "semi", "chip", "chips", "wafer", "memory"},
    "IGV": {"software", "cloud", "saas", "application", "applications"},
    "IPAY": {"payment", "payments", "digital", "fintech"},
    "XLV": {"healthcare", "health", "pharma", "pharmaceutical", "medical", "biotechnology", "biotech", "drug", "therapeutics"},
    "XLI": {"industrial", "industrials", "automation", "engineering", "construction", "infrastructure", "machinery", "aerospace", "defense", "electrical"},
    "XLY": {"consumer", "discretionary", "retail", "ecommerce", "automotive", "luxury", "restaurant", "apparel"},
    "XLP": {"consumer", "staples", "defensive", "retail", "beauty", "food", "beverage", "household"},
    "XLF": {"financial", "financials", "bank", "banks", "lending", "credit"},
    "KCE": {"financial", "financials", "capital", "asset", "management", "ratings"},
    "XLK": {"technology", "tech", "hardware", "software", "storage", "networking", "servers"},
    "XLC": {"communication", "communications", "advertising", "media", "platform", "internet", "content", "entertainment", "social"},
    "XLB": {"materials", "chemicals", "industrial", "gases"},
    "ICLN": {"renewable", "renewables", "clean", "energy", "utilities", "power"},
    "XLU": {"utility", "utilities", "power", "electric", "gas"},
    "XLE": {"energy", "oil", "gas", "pipeline", "pipelines"},
    "KIE": {"insurance", "insurer", "assurance", "financial", "financials"},
    "VNQ": {"reits", "reit", "real", "estate", "property", "properties", "immobilier"},
    "URA": {"uranium", "nuclear", "nucléaire", "nucleaire", "energy"},
    "GDX": {"gold", "or", "miner", "miners", "mining", "royalty", "royalties", "streaming"},
}

AUTO_BENCHMARK_SOURCES = {"AUTO_INFERRED", "AUTO_CONTEXT_INFERRED"}
COMMON_BENCHMARK_TICKERS = set(BENCHMARK_FOCUS_TERMS) | set(DEFAULT_BENCHMARK_BY_TICKER.values()) | {"VFV.TO"}

RELEVANCE_SCORES = {
    "HIGH": 1.0,
    "MEDIUM": 0.6,
    "LOW": 0.25,
    "UNKNOWN": 0.5,
}


def enrich_benchmark_map(
    configured_map: dict[str, str],
    tickers: list[str] | set[str],
) -> tuple[dict[str, str], dict[str, str]]:
    enriched = {normalize_ticker(ticker): normalize_ticker(benchmark) for ticker, benchmark in configured_map.items() if normalize_ticker(ticker)}
    sources = {ticker: "CONFIGURED" for ticker in enriched}
    for ticker in sorted({normalize_ticker(ticker) for ticker in tickers if normalize_ticker(ticker)}):
        if ticker in enriched:
            continue
        inferred = DEFAULT_BENCHMARK_BY_TICKER.get(ticker)
        if inferred:
            enriched[ticker] = inferred
            sources[ticker] = "AUTO_INFERRED"
        else:
            sources[ticker] = "BROAD_MARKET_FALLBACK"
    return enriched, sources


def infer_benchmark_from_context(
    ticker: str,
    sector: str | None = None,
    exposure: dict[str, Any] | None = None,
    market: dict[str, Any] | None = None,
) -> tuple[str | None, str]:
    ticker = normalize_ticker(ticker)
    if not ticker or ticker == "VFV.TO":
        return None, "Aucun ticker d’entreprise à inférer."
    direct = DEFAULT_BENCHMARK_BY_TICKER.get(ticker)
    if direct:
        return direct, f"Benchmark inféré par ticker connu: {direct}."

    context_terms = _context_terms(ticker, sector, exposure, market)
    if not context_terms:
        return None, "Contexte sectoriel insuffisant pour inférer un benchmark."

    scored: list[tuple[int, int, str, set[str]]] = []
    for benchmark, focus_terms in BENCHMARK_FOCUS_TERMS.items():
        matches = focus_terms & context_terms
        if not matches:
            continue
        exactness = _benchmark_exactness_bonus(benchmark, context_terms)
        scored.append((len(matches), exactness, benchmark, matches))
    if not scored:
        return None, "Aucun ETF sectoriel ne correspond assez au contexte détecté."

    scored.sort(reverse=True)
    match_count, exactness, benchmark, matches = scored[0]
    if match_count < 1 or (match_count == 1 and exactness <= 0):
        return None, "Correspondance trop faible pour éviter VFV.TO comme fallback."
    return benchmark, f"Benchmark inféré automatiquement par contexte: {benchmark} ({', '.join(sorted(matches))})."


def compute_benchmark_relevance(
    ticker: str,
    benchmark_ticker: str | None,
    sector: str | None = None,
    exposure: dict[str, Any] | None = None,
    market: dict[str, Any] | None = None,
    benchmark_source: str = "CONFIGURED",
) -> dict[str, Any]:
    ticker = normalize_ticker(ticker)
    benchmark_ticker = normalize_ticker(benchmark_ticker or "VFV.TO")
    benchmark_source = str(benchmark_source or "CONFIGURED").upper()

    if ticker == "VFV.TO":
        return _result("BENCHMARK", "VFV.TO est le benchmark de secours, pas un proxy sectoriel d’entreprise.", benchmark_source)

    if benchmark_ticker == "VFV.TO":
        return _result(
            "LOW",
            "VFV.TO reste utile comme coût d’opportunité, mais ce n’est pas un benchmark sectoriel précis.",
            benchmark_source,
        )

    override = PAIR_RELEVANCE_OVERRIDES.get((ticker, benchmark_ticker))
    if override:
        level, reason = override
        return _result(level, reason, benchmark_source)

    focus_terms = BENCHMARK_FOCUS_TERMS.get(benchmark_ticker, set())
    context_terms = _context_terms(ticker, sector, exposure, market)
    matches = sorted(focus_terms & context_terms)
    if matches:
        if len(matches) >= 2 or benchmark_source in AUTO_BENCHMARK_SOURCES:
            return _result(
                "HIGH",
                f"Le benchmark {benchmark_ticker} correspond bien aux thèmes détectés: {', '.join(matches)}.",
                benchmark_source,
            )
        return _result(
            "MEDIUM",
            f"Le benchmark {benchmark_ticker} correspond partiellement aux thèmes détectés: {', '.join(matches)}.",
            benchmark_source,
        )

    if benchmark_source == "CONFIGURED":
        return _result(
            "MEDIUM",
            f"Benchmark configuré manuellement ({benchmark_ticker}), mais la correspondance sectorielle automatique est imparfaite.",
            benchmark_source,
        )

    if benchmark_source in AUTO_BENCHMARK_SOURCES:
        return _result(
            "MEDIUM",
            f"Benchmark inféré automatiquement ({benchmark_ticker}); utile, mais à interpréter comme proxy imparfait.",
            benchmark_source,
        )

    return _result(
        "LOW",
        f"Benchmark {benchmark_ticker} peu relié aux thèmes détectés; signal informatif seulement.",
        benchmark_source,
    )


def benchmark_multiplier(benchmark: dict[str, Any]) -> float:
    score = safe_float(benchmark.get("benchmark_relevance_score"))
    if score is not None:
        return score
    level = str(benchmark.get("benchmark_relevance_level") or "HIGH").upper()
    return RELEVANCE_SCORES.get(level, 1.0)


def benchmark_relevance_level(benchmark: dict[str, Any]) -> str:
    return str(benchmark.get("benchmark_relevance_level") or "HIGH").upper()


def _result(level: str, reason: str, source: str) -> dict[str, Any]:
    level = level.upper()
    return {
        "benchmark_relevance_level": level,
        "benchmark_relevance_score": RELEVANCE_SCORES.get(level, 1.0 if level == "BENCHMARK" else 0.5),
        "benchmark_relevance_reason": reason,
        "benchmark_source": source,
    }


def _context_terms(
    ticker: str,
    sector: str | None,
    exposure: dict[str, Any] | None,
    market: dict[str, Any] | None,
) -> set[str]:
    exposure = exposure or {}
    market = market or {}
    raw_parts: list[str] = [ticker, sector or ""]
    factor_exposure = exposure.get("factor_exposure") or []
    if isinstance(factor_exposure, str):
        raw_parts.append(factor_exposure)
    else:
        raw_parts.extend(str(item) for item in factor_exposure)
    raw_parts.extend(
        [
            str(market.get("sector_name") or ""),
            str(market.get("industry") or ""),
            str(market.get("long_name") or ""),
        ]
    )
    text = _normalize_text(" ".join(raw_parts))
    terms = set(re.findall(r"[a-z0-9]+", text))
    aliases = {
        "semiconductors": "semiconductor",
        "semi": "semiconductor",
        "pharmaceutical": "pharma",
        "industrials": "industrial",
        "financials": "financial",
        "communications": "communication",
        "payments": "payment",
        "renewables": "renewable",
        "utilities": "utility",
    }
    terms.update(aliases.get(term, term) for term in list(terms))
    return terms


def _benchmark_exactness_bonus(benchmark: str, terms: set[str]) -> int:
    if benchmark == "SOXX" and {"semiconductor", "chip", "wafer", "memory"} & terms:
        return 3
    if benchmark == "IGV" and {"software", "saas", "cloud", "application"} & terms:
        return 3
    if benchmark == "IPAY" and {"payment", "fintech"} & terms:
        return 3
    if benchmark == "XLC" and {"communication", "advertising", "media", "platform", "internet", "content", "social"} & terms:
        return 3
    if benchmark == "XLV" and {"healthcare", "pharma", "biotechnology", "biotech", "medical", "drug", "therapeutics"} & terms:
        return 3
    if benchmark == "KCE" and {"asset", "ratings", "capital"} & terms:
        return 2
    if benchmark == "KIE" and {"insurance", "insurer"} & terms:
        return 3
    if benchmark == "VNQ" and {"reit", "reits", "estate", "property"} & terms:
        return 3
    if benchmark == "GDX" and {"gold", "miner", "mining", "royalty", "streaming"} & terms:
        return 3
    if benchmark == "URA" and {"uranium", "nuclear"} & terms:
        return 3
    return 1


def _normalize_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    return ascii_text.replace("_", " ").replace("&", " ").lower()
