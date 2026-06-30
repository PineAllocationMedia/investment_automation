from __future__ import annotations

from typing import Any

from .add_eligibility_engine import ADD_ALLOWED_STATUSES
from .asset_type_engine import is_fallback_benchmark
from .portfolio_risk_engine import TECH_AI_SEMI_FACTORS
from .sizing_engine import (
    EXPECTED_CAGR_QUALITY_SCORE,
    OPPORTUNITY_COST_SCORE,
    compute_business_quality_score,
    compute_high_cagr_potential_score,
)
from .utils import clamp, safe_float


PROMOTION_COLUMNS = [
    "universe",
    "ticker",
    "ticker_display",
    "resolved_ticker",
    "company_name",
    "score_total",
    "conviction_score",
    "expected_cagr_quality",
    "opportunity_cost_status",
    "data_quality",
    "cycle_bubble_risk_level",
    "cycle_bubble_score",
    "promotion_status",
    "reason",
    "next_step",
]

PROMOTION_STATUSES = {
    "PROMOTE_TO_CORE_REVIEW",
    "STRONG_WATCH_ONLY",
    "WAIT_FOR_BETTER_DATA_OR_PRICE",
    "DO_NOT_PROMOTE",
}

WEAKEST_CORE_AUDIT_COLUMNS = [
    "audit_status",
    "current_weakest_ticker",
    "candidate_weakest_ticker",
    "same_result",
    "current_reason",
    "candidate_reason",
    "score_total_current",
    "score_total_candidate",
    "conviction_current",
    "conviction_candidate",
    "durability_current",
    "durability_candidate",
    "cycle_risk_current",
    "cycle_risk_candidate",
    "interpretation",
]


def build_promotion_candidate_rows(
    watchlist_analyses: dict[str, dict[str, Any]],
    market_analyses: dict[str, dict[str, Any]],
    core_analyses: dict[str, dict[str, Any]],
    portfolio_risk: dict[str, Any],
    market_universe: dict[str, dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    market_universe = market_universe or {}
    rows: list[dict[str, Any]] = []
    for universe, analyses in [("WATCHLIST", watchlist_analyses), ("MARKET_UNIVERSE", market_analyses)]:
        for analysis in analyses.values():
            ticker = str(analysis.get("ticker") or "")
            metadata = market_universe.get(ticker, {}) if universe == "MARKET_UNIVERSE" else {}
            rows.append(
                classify_promotion_candidate(
                    analysis=analysis,
                    core_analyses=core_analyses,
                    portfolio_risk=portfolio_risk,
                    universe=universe,
                    company_name=str(metadata.get("company_name") or ""),
                )
            )
    return _limit_manual_promotion_slots(sorted(rows, key=_promotion_sort_key, reverse=True))


def classify_promotion_candidate(
    analysis: dict[str, Any],
    core_analyses: dict[str, dict[str, Any]],
    portfolio_risk: dict[str, Any],
    universe: str,
    company_name: str = "",
) -> dict[str, Any]:
    ticker = str(analysis.get("ticker") or "")
    checks = _promotion_checks(analysis, core_analyses, portfolio_risk)
    status = _promotion_status(checks)
    reason = _promotion_reason(status, checks)
    next_step = _promotion_next_step(status, ticker)
    return {
        "universe": universe,
        "ticker": ticker,
        "ticker_display": analysis.get("ticker_display", ticker),
        "resolved_ticker": analysis.get("resolved_ticker", ticker),
        "company_name": company_name,
        "score_total": analysis.get("score_total"),
        "conviction_score": analysis.get("conviction_score"),
        "expected_cagr_quality": analysis.get("expected_cagr_quality"),
        "opportunity_cost_status": analysis.get("opportunity_cost_status"),
        "data_quality": analysis.get("data_quality"),
        "cycle_bubble_risk_level": analysis.get("cycle_bubble_risk_level"),
        "cycle_bubble_score": analysis.get("cycle_bubble_score"),
        "promotion_status": status,
        "reason": reason,
        "next_step": next_step,
    }


def _promotion_checks(
    analysis: dict[str, Any],
    core_analyses: dict[str, dict[str, Any]],
    portfolio_risk: dict[str, Any],
) -> dict[str, Any]:
    score = safe_float(analysis.get("score_total")) or 0.0
    conviction = safe_float(analysis.get("conviction_score")) or 0.0
    data_quality = str(analysis.get("data_quality") or "")
    quality = str(analysis.get("expected_cagr_quality") or "")
    valuation_ok = analysis.get("quality_but_too_expensive") is not True
    cycle_level = str(analysis.get("cycle_bubble_risk_level") or "LOW")
    cycle_ok = _cycle_ok_for_promotion(analysis)
    profile_ok, profile_reason = _profile_alignment_is_exceptional(analysis)
    source_ready, source_reason = _external_source_status_is_ready(analysis)
    proof_ok, proof_reason = _promotion_proof_is_sufficient(analysis)
    base_quality = (
        score >= 8.5
        and conviction >= 85
        and quality in {"HIGH", "VERY_HIGH"}
        and analysis.get("thesis_status") == "INTACT"
        and analysis.get("liquidation_status") == "GREEN"
        and analysis.get("opportunity_cost_status") == "CLEARLY_BETTER_THAN_VFV"
    )
    clearly_superior, superiority_reason = external_core_fit_status(analysis, core_analyses)
    concentration_ok, concentration_reason = _concentration_impact_is_acceptable(analysis, portfolio_risk)
    fiscal_ok, fiscal_reason = _fiscal_impact_is_acceptable_for_review(analysis)

    return {
        "base_quality": base_quality,
        "score_ok": score >= 8.5,
        "conviction_ok": conviction >= 85,
        "expected_quality_ok": quality in {"HIGH", "VERY_HIGH"},
        "thesis_ok": analysis.get("thesis_status") == "INTACT",
        "liquidation_ok": analysis.get("liquidation_status") == "GREEN",
        "opportunity_ok": analysis.get("opportunity_cost_status") == "CLEARLY_BETTER_THAN_VFV",
        "valuation_ok": valuation_ok,
        "cycle_ok": cycle_ok,
        "cycle_reason": f"risque cycle/bulle/tendance {cycle_level}",
        "profile_ok": profile_ok,
        "profile_reason": profile_reason,
        "source_ready": source_ready,
        "source_reason": source_reason,
        "proof_ok": proof_ok,
        "proof_reason": proof_reason,
        "data_quality_ok": data_quality == "HIGH",
        "clearly_superior": clearly_superior,
        "superiority_reason": superiority_reason,
        "concentration_ok": concentration_ok,
        "concentration_reason": concentration_reason,
        "fiscal_ok": fiscal_ok,
        "fiscal_reason": fiscal_reason,
    }


def _promotion_status(checks: dict[str, Any]) -> str:
    strict_pass = (
        checks["base_quality"]
        and checks["valuation_ok"]
        and checks["cycle_ok"]
        and checks["profile_ok"]
        and checks["source_ready"]
        and checks["proof_ok"]
        and checks["data_quality_ok"]
        and checks["clearly_superior"]
        and checks["concentration_ok"]
        and checks["fiscal_ok"]
    )
    if strict_pass:
        return "PROMOTE_TO_CORE_REVIEW"

    if not checks["base_quality"]:
        return "DO_NOT_PROMOTE"

    if not checks["clearly_superior"]:
        return "STRONG_WATCH_ONLY"

    return "WAIT_FOR_BETTER_DATA_OR_PRICE"


def _promotion_reason(status: str, checks: dict[str, Any]) -> str:
    if status == "PROMOTE_TO_CORE_REVIEW":
        return (
            "Candidate externe exceptionnelle selon les règles: score, conviction, thèse, qualité des données, "
            "valorisation, concentration et avantage vs VFV sont acceptables pour une revue manuelle."
        )
    if status == "STRONG_WATCH_ONLY":
        return f"Très bonne candidate, mais pas assez supérieure au portefeuille actuel. {checks['superiority_reason']}"
    if status == "WAIT_FOR_BETTER_DATA_OR_PRICE":
        blockers = []
        if not checks["valuation_ok"]:
            blockers.append("valorisation trop exigeante")
        if not checks["cycle_ok"]:
            blockers.append(checks["cycle_reason"])
        if not checks["profile_ok"]:
            blockers.append(checks["profile_reason"])
        if not checks["source_ready"]:
            blockers.append(checks["source_reason"])
        if not checks["proof_ok"]:
            blockers.append(checks["proof_reason"])
        if not checks["data_quality_ok"]:
            blockers.append("qualité des données insuffisante")
        if not checks["concentration_ok"]:
            blockers.append(checks["concentration_reason"])
        if not checks["fiscal_ok"]:
            blockers.append(checks["fiscal_reason"])
        return "Attendre avant promotion: " + "; ".join(blockers)

    missing = []
    for label, field in [
        ("score < 8.5", "score_ok"),
        ("conviction < 85", "conviction_ok"),
        ("qualité CAGR insuffisante", "expected_quality_ok"),
        ("thèse non intacte", "thesis_ok"),
        ("liquidation non verte", "liquidation_ok"),
        ("pas clairement meilleure que VFV", "opportunity_ok"),
        ("alignement haut CAGR/core insuffisant", "profile_ok"),
        ("statut scanner/watchlist insuffisant", "source_ready"),
        ("preuves insuffisantes", "proof_ok"),
    ]:
        if not checks[field]:
            missing.append(label)
    return "Ne pas promouvoir maintenant: " + "; ".join(missing)


def _promotion_next_step(status: str, ticker: str) -> str:
    if status == "PROMOTE_TO_CORE_REVIEW":
        return (
            f"À valider manuellement. Si tu acceptes la thèse, ajoute {ticker} dans data/portfolio.csv avec "
            "shares=0. Si tu finis par acheter, mets à jour shares/average_cost/account_type dans portfolio.csv; "
            "la prochaine analyse détectera automatiquement le changement dans l’historique."
        )
    if status == "STRONG_WATCH_ONLY":
        return "Garder dans la watchlist; comparer encore aux meilleures positions core au prochain trimestre."
    if status == "WAIT_FOR_BETTER_DATA_OR_PRICE":
        return "Attendre une meilleure valorisation ou compléter les données manuelles avant promotion."
    return "Ne pas ajouter au Core Portfolio pour l’instant."


def external_core_fit_status(
    analysis: dict[str, Any],
    core_analyses: dict[str, dict[str, Any]],
) -> tuple[bool, str]:
    leaders = _core_leader_positions(core_analyses)
    if leaders:
        candidate_score = _promotion_alignment_score(analysis)
        leader_scores = sorted(((_promotion_alignment_score(row), row) for row in leaders), reverse=True)
        top_scores = [score for score, _ in leader_scores[:3]]
        reference_score = sum(top_scores) / len(top_scores)
        reference_tickers = ", ".join(str(row.get("ticker")) for _, row in leader_scores[:3])
        required_score = max(84.0, reference_score - 2.0)
        if candidate_score >= required_score:
            return (
                True,
                f"Comparable aux meilleurs titres core ({candidate_score:.1f} vs seuil {required_score:.1f}; référence: {reference_tickers}).",
            )
        return (
            False,
            f"Pas assez comparable aux meilleurs titres core ({candidate_score:.1f} vs seuil {required_score:.1f}; référence: {reference_tickers}).",
        )

    weakest = _weakest_core_position(core_analyses)
    if weakest is None:
        return True, "Aucune position core comparable."

    external_score = safe_float(analysis.get("score_total")) or 0.0
    external_conviction = safe_float(analysis.get("conviction_score")) or 0.0
    weakest_score = safe_float(weakest.get("score_total")) or 0.0
    weakest_conviction = safe_float(weakest.get("conviction_score")) or 0.0
    weakest_ticker = weakest.get("ticker")
    weakest_add_status = weakest.get("add_eligibility_status")
    weakest_add_allowed = weakest_add_status in ADD_ALLOWED_STATUSES or (not weakest_add_status and weakest.get("liquidation_status") == "GREEN")
    weakest_has_problem = weakest.get("thesis_status") != "INTACT" or not weakest_add_allowed

    if weakest_has_problem:
        return True, f"Supérieure à {weakest_ticker}, qui présente une thèse ou un signal de liquidation affaibli."
    if external_score >= weakest_score + 0.75 and external_conviction >= weakest_conviction + 7.5:
        return True, f"Supérieure à {weakest_ticker} selon score et conviction."
    return False, f"La position core la plus faible ({weakest_ticker}) n’est pas nettement dépassée."


def promotion_profile_alignment_status(analysis: dict[str, Any]) -> tuple[bool, str]:
    return _profile_alignment_is_exceptional(analysis)


def _core_leader_positions(core_analyses: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    leaders: list[dict[str, Any]] = []
    for ticker, row in core_analyses.items():
        if ticker == "VFV.TO":
            continue
        if (safe_float(row.get("score_total")) or 0.0) < 8.0:
            continue
        if (safe_float(row.get("conviction_score")) or 0.0) < 80:
            continue
        if row.get("thesis_status") != "INTACT" or row.get("liquidation_status") != "GREEN":
            continue
        if row.get("expected_cagr_quality") not in {"HIGH", "VERY_HIGH"}:
            continue
        if row.get("opportunity_cost_status") != "CLEARLY_BETTER_THAN_VFV":
            continue
        if row.get("quality_but_too_expensive") is True:
            continue
        if str(row.get("data_reliability_level") or "").upper() == "LOW":
            continue
        if str(row.get("cycle_bubble_risk_level") or "").upper() == "EXTREME":
            continue
        leaders.append(row)
    return leaders


def _weakest_core_position(core_analyses: dict[str, dict[str, Any]]) -> dict[str, Any] | None:
    candidates = [row for ticker, row in core_analyses.items() if ticker != "VFV.TO"]
    if not candidates:
        return None
    return sorted(
        candidates,
        key=lambda row: (
            0 if row.get("thesis_status") != "INTACT" or not _core_add_allowed(row) else 1,
            safe_float(row.get("score_total")) or 0.0,
            safe_float(row.get("conviction_score")) or 0.0,
        ),
    )[0]


def build_weakest_core_audit_rows(core_analyses: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    """Compare the active weakest-core logic to a composite candidate without changing behavior."""
    current = _weakest_core_position(core_analyses)
    candidate = _weakest_core_position_composite_candidate(core_analyses)
    if current is None and candidate is None:
        return [
            {
                "audit_status": "NO_CORE_CANDIDATES",
                "current_weakest_ticker": "",
                "candidate_weakest_ticker": "",
                "same_result": True,
                "current_reason": "Aucune position core non-benchmark disponible pour la logique active.",
                "candidate_reason": "Aucune position core non-benchmark disponible pour la logique candidate.",
                "score_total_current": "",
                "score_total_candidate": "",
                "conviction_current": "",
                "conviction_candidate": "",
                "durability_current": "",
                "durability_candidate": "",
                "cycle_risk_current": "",
                "cycle_risk_candidate": "",
                "interpretation": "Audit neutre: aucune comparaison weakest core possible.",
            }
        ]

    current_ticker = _analysis_ticker(current) if current else ""
    candidate_ticker = _analysis_ticker(candidate) if candidate else ""
    same_result = bool(current_ticker and candidate_ticker and current_ticker == candidate_ticker)
    current_reason = _active_weakest_reason(current) if current else "Aucune position active retenue."
    candidate_reason = _composite_weakest_reason(candidate) if candidate else "Aucune position candidate retenue."
    missing_fields = _missing_core_audit_fields(current) + _missing_core_audit_fields(candidate)
    if missing_fields:
        audit_status = "LIMITED_DATA_OBSERVE_ONLY"
        interpretation = (
            "Audit neutre: données incomplètes dans la comparaison weakest core "
            f"({', '.join(sorted(set(missing_fields)))}). Ne pas activer la logique candidate sur ce signal seul."
        )
    else:
        audit_status = "MATCH" if same_result else "DIVERGENCE_OBSERVE_ONLY"
        interpretation = (
            "Les deux logiques identifient le même maillon faible; aucune raison d'activer une nouvelle logique."
            if same_result
            else (
                "Observation seulement: la logique composite choisirait un autre weakest core. "
                "La promotion active continue d'utiliser la logique actuelle jusqu'à preuve suffisante."
            )
        )

    return [
        {
            "audit_status": audit_status,
            "current_weakest_ticker": current_ticker,
            "candidate_weakest_ticker": candidate_ticker,
            "same_result": same_result,
            "current_reason": current_reason,
            "candidate_reason": candidate_reason,
            "score_total_current": _round_or_blank(safe_float(current.get("score_total")) if current else None, 2),
            "score_total_candidate": _round_or_blank(safe_float(candidate.get("score_total")) if candidate else None, 2),
            "conviction_current": _round_or_blank(safe_float(current.get("conviction_score")) if current else None, 1),
            "conviction_candidate": _round_or_blank(safe_float(candidate.get("conviction_score")) if candidate else None, 1),
            "durability_current": _round_or_blank(safe_float(current.get("long_term_durability_score")) if current else None, 1),
            "durability_candidate": _round_or_blank(safe_float(candidate.get("long_term_durability_score")) if candidate else None, 1),
            "cycle_risk_current": current.get("cycle_bubble_risk_level", "") if current else "",
            "cycle_risk_candidate": candidate.get("cycle_bubble_risk_level", "") if candidate else "",
            "interpretation": interpretation,
        }
    ]


def _weakest_core_position_composite_candidate(core_analyses: dict[str, dict[str, Any]]) -> dict[str, Any] | None:
    candidates = [
        row
        for ticker, row in core_analyses.items()
        if not is_fallback_benchmark(ticker) and not is_fallback_benchmark(row.get("ticker"))
    ]
    if not candidates:
        return None
    scored = [(_composite_weakest_key(row), row) for row in candidates]
    return sorted(scored, key=lambda item: item[0])[0][1]


def _composite_weakest_key(row: dict[str, Any]) -> tuple[float, float, float, float, str]:
    score_total = safe_float(row.get("score_total"))
    conviction = safe_float(row.get("conviction_score"))
    durability = safe_float(row.get("long_term_durability_score"))
    normalized_score = (score_total * 10.0) if score_total is not None else 50.0
    conviction_score = conviction if conviction is not None else 50.0
    durability_score = durability if durability is not None else 70.0
    cycle_penalty = _cycle_weakness_penalty(row)
    problem_flag = 0.0 if row.get("thesis_status") != "INTACT" or not _core_add_allowed(row) else 1.0
    composite_strength = (
        0.34 * normalized_score
        + 0.30 * conviction_score
        + 0.26 * durability_score
        - cycle_penalty
    )
    return (problem_flag, composite_strength, normalized_score, conviction_score, _analysis_ticker(row))


def _cycle_weakness_penalty(row: dict[str, Any]) -> float:
    level = str(row.get("cycle_bubble_risk_level") or "").upper()
    if level == "EXTREME":
        return 12.0
    if level == "HIGH":
        return 6.0
    return 0.0


def _active_weakest_reason(row: dict[str, Any]) -> str:
    problem = row.get("thesis_status") != "INTACT" or not _core_add_allowed(row)
    return (
        f"Logique active: problème thèse/add/liquidation={problem}; "
        f"score_total={_value_text(row.get('score_total'))}; conviction={_value_text(row.get('conviction_score'))}."
    )


def _composite_weakest_reason(row: dict[str, Any]) -> str:
    problem = row.get("thesis_status") != "INTACT" or not _core_add_allowed(row)
    durability = safe_float(row.get("long_term_durability_score"))
    durability_text = _value_text(durability) if durability is not None else "N/D neutre=70"
    cycle_level = str(row.get("cycle_bubble_risk_level") or "LOW")
    return (
        f"Logique candidate audit-only: problème thèse/add/liquidation={problem}; "
        f"score_total={_value_text(row.get('score_total'))}; conviction={_value_text(row.get('conviction_score'))}; "
        f"durabilité={durability_text}; risque cycle={cycle_level}; pénalité cycle={_cycle_weakness_penalty(row):.1f}."
    )


def _analysis_ticker(row: dict[str, Any] | None) -> str:
    return str((row or {}).get("ticker") or "").strip().upper()


def _missing_core_audit_fields(row: dict[str, Any] | None) -> list[str]:
    if not row:
        return ["missing_position"]
    missing = []
    if safe_float(row.get("score_total")) is None:
        missing.append(f"{_analysis_ticker(row) or 'UNKNOWN'}.score_total")
    if safe_float(row.get("conviction_score")) is None:
        missing.append(f"{_analysis_ticker(row) or 'UNKNOWN'}.conviction_score")
    return missing


def _round_or_blank(value: float | None, digits: int) -> float | str:
    if value is None:
        return ""
    return round(value, digits)


def _value_text(value: Any) -> str:
    number = safe_float(value)
    if number is None:
        return "N/D"
    return f"{number:.2f}"


def _core_add_allowed(row: dict[str, Any]) -> bool:
    add_status = row.get("add_eligibility_status")
    return add_status in ADD_ALLOWED_STATUSES or (not add_status and row.get("liquidation_status") == "GREEN")


def _concentration_impact_is_acceptable(
    analysis: dict[str, Any],
    portfolio_risk: dict[str, Any],
) -> tuple[bool, str]:
    sector = str(analysis.get("sector") or "Unknown")
    sector_weight = safe_float((portfolio_risk.get("concentration_by_sector") or {}).get(sector)) or 0.0
    if sector != "Unknown" and sector_weight > 0.55:
        return False, f"secteur déjà en concentration extrême ({sector})"

    factors = {str(item) for item in (analysis.get("factor_exposure") or [])}
    tech_like = bool(factors & TECH_AI_SEMI_FACTORS)
    tech_weight = safe_float(portfolio_risk.get("tech_ai_semi_weight")) or 0.0
    if tech_like and tech_weight > 0.65:
        return False, "exposition tech/IA/semi-conducteurs déjà très élevée"
    return True, "impact de concentration acceptable pour une revue manuelle"


def _fiscal_impact_is_acceptable_for_review(analysis: dict[str, Any]) -> tuple[bool, str]:
    dividend_yield = _percent_points(analysis.get("dividend_yield")) or 0.0
    if dividend_yield > 4.0:
        return False, "rendement de dividende élevé: localisation fiscale à valider avant promotion"
    return True, "impact fiscal acceptable pour une revue manuelle, à valider avec un comptable"


def _cycle_ok_for_promotion(analysis: dict[str, Any]) -> bool:
    level = str(analysis.get("cycle_bubble_risk_level") or "LOW")
    if level in {"LOW", "MEDIUM"}:
        return True
    if level == "HIGH":
        return (
            (safe_float(analysis.get("score_total")) or 0.0) >= 9.0
            and (safe_float(analysis.get("conviction_score")) or 0.0) >= 90
            and analysis.get("expected_cagr_quality") == "VERY_HIGH"
        )
    return False


def _external_source_status_is_ready(analysis: dict[str, Any]) -> tuple[bool, str]:
    watchlist_status = str(analysis.get("watchlist_status") or "")
    candidate_status = str(analysis.get("candidate_status") or "")
    if watchlist_status and watchlist_status != "HIGH_PRIORITY_WATCH":
        return False, f"statut watchlist insuffisant ({watchlist_status})"
    if candidate_status and candidate_status != "MANUAL_REVIEW_TOP_CANDIDATE":
        return False, f"statut scanner insuffisant ({candidate_status})"
    return True, "statut scanner/watchlist compatible avec une revue de promotion"


def _profile_alignment_is_exceptional(analysis: dict[str, Any]) -> tuple[bool, str]:
    score = safe_float(analysis.get("score_total")) or 0.0
    conviction = safe_float(analysis.get("conviction_score")) or 0.0
    expected = str(analysis.get("expected_cagr_quality") or "")
    cycle_level = str(analysis.get("cycle_bubble_risk_level") or "LOW")
    benchmark_relevance = str(analysis.get("benchmark_relevance_level") or "").upper()
    durability_status = str(analysis.get("long_term_durability_status") or "")
    durability_score = safe_float(analysis.get("long_term_durability_score"))
    business_quality = _business_quality(analysis)
    high_cagr_potential = _high_cagr_potential(analysis)
    intersection = min(business_quality, high_cagr_potential)
    alignment_score = _promotion_alignment_score(analysis)

    blockers: list[str] = []
    if business_quality < 85:
        blockers.append(f"qualité business {business_quality:.1f} < 85")
    if high_cagr_potential < 82:
        blockers.append(f"potentiel haut CAGR {high_cagr_potential:.1f} < 82")
    if intersection < 82:
        blockers.append(f"intersection qualité/CAGR {intersection:.1f} < 82")
    if durability_score is not None and durability_score < 85:
        blockers.append(f"durabilité 15-30 ans {durability_score:.1f} < 85")
    if durability_status in {"SPECULATIVE_OR_UNPROVEN", "HIGH_GROWTH_BUT_FRAGILE"}:
        blockers.append(f"durabilité {durability_status}")
    if durability_status == "DURABLE_BUT_CYCLICAL" and not (
        score >= 9.0 and conviction >= 90 and expected == "VERY_HIGH" and cycle_level in {"LOW", "MEDIUM"}
    ):
        blockers.append("profil durable mais cyclique: exige un niveau exceptionnel avant promotion")
    if benchmark_relevance == "LOW" and not (
        score >= 9.0
        and conviction >= 90
        and expected == "VERY_HIGH"
        and (durability_score or 0.0) >= 92
        and high_cagr_potential >= 88
    ):
        blockers.append("comparaison sectorielle faible: preuves insuffisantes pour une promotion externe")
    if benchmark_relevance == "MEDIUM" and str(analysis.get("universe") or "") in {"WATCHLIST", "MARKET_SCANNER"} and not (
        score >= 9.5
        and conviction >= 92
        and expected == "VERY_HIGH"
        and cycle_level == "LOW"
        and (durability_score or 0.0) >= 92
        and high_cagr_potential >= 90
    ):
        blockers.append("benchmark seulement moyennement pertinent: exige des preuves exceptionnelles avant promotion")
    if alignment_score < 84:
        blockers.append(f"score d’alignement promotion {alignment_score:.1f} < 84")

    if blockers:
        return False, "; ".join(blockers)
    return True, f"alignement haut CAGR/core très fort ({alignment_score:.1f}/100)"


def _promotion_proof_is_sufficient(analysis: dict[str, Any]) -> tuple[bool, str]:
    if analysis.get("ticker_needs_attention"):
        return False, "ticker ou données à vérifier"
    if analysis.get("requires_manual_validation_for_large_allocation") is True:
        return False, "validation manuelle requise avant grosse décision"
    if analysis.get("news_red_flags"):
        return False, "nouvelles gratuites avec signal de risque majeur"

    missing_count = safe_float(analysis.get("score_missing_data_count")) or 0.0
    if missing_count > 1:
        return False, "trop de données critiques manquantes"

    reliability_level = str(analysis.get("data_reliability_level") or "").upper()
    if reliability_level and reliability_level != "HIGH":
        return False, "fiabilité des données pas assez élevée"

    auto_dependency = str(analysis.get("auto_estimate_dependency") or "").upper()
    if auto_dependency == "HIGH":
        return False, "dépendance élevée aux estimations automatiques"

    automation_evidence = str(analysis.get("automation_evidence_level") or "").upper()
    if automation_evidence and automation_evidence not in {"STRONG", "CONFIRMED"}:
        return False, "preuve automatique insuffisante"

    for label, field, threshold in [
        ("qualité business", "business_quality_score", 80),
        ("potentiel high-CAGR", "high_cagr_potential_score", 80),
        ("intersection qualité/CAGR", "quality_cagr_intersection", 80),
    ]:
        value = safe_float(analysis.get(field))
        if value is not None and value < threshold:
            return False, f"{label} sous {threshold}"

    return True, "preuves suffisantes pour une revue manuelle de promotion"


def _limit_manual_promotion_slots(rows: list[dict[str, Any]], max_promotions: int = 3) -> list[dict[str, Any]]:
    promoted = 0
    for row in rows:
        if row.get("promotion_status") != "PROMOTE_TO_CORE_REVIEW":
            continue
        promoted += 1
        if promoted <= max_promotions:
            continue
        row["promotion_status"] = "STRONG_WATCH_ONLY"
        row["reason"] = (
            "Forte candidate externe, mais moins prioritaire que les meilleures candidates de promotion "
            "de cette analyse."
        )
        row["next_step"] = "Garder dans la watchlist; reconsidérer si elle reste supérieure aux prochains rapports."
    return sorted(rows, key=_promotion_sort_key, reverse=True)


def _percent_points(value: Any) -> float | None:
    return safe_float(value)


def _business_quality(analysis: dict[str, Any]) -> float:
    existing = safe_float(analysis.get("business_quality_score"))
    return existing if existing is not None else compute_business_quality_score(analysis)


def _high_cagr_potential(analysis: dict[str, Any]) -> float:
    existing = safe_float(analysis.get("high_cagr_potential_score"))
    return existing if existing is not None else compute_high_cagr_potential_score(analysis)


def _promotion_alignment_score(analysis: dict[str, Any]) -> float:
    score_total_normalized = (safe_float(analysis.get("score_total")) or 0.0) * 10
    conviction = safe_float(analysis.get("conviction_score")) or 0.0
    business_quality = _business_quality(analysis)
    high_cagr_potential = _high_cagr_potential(analysis)
    durability = safe_float(analysis.get("long_term_durability_score"))
    expected_score = EXPECTED_CAGR_QUALITY_SCORE.get(str(analysis.get("expected_cagr_quality")), 20)
    opportunity_score = OPPORTUNITY_COST_SCORE.get(str(analysis.get("opportunity_cost_status")), 0)
    cycle_penalty = safe_float(analysis.get("cycle_bubble_penalty")) or 0.0
    if durability is None:
        durability = min(business_quality, high_cagr_potential)
    return round(
        clamp(
            0.16 * score_total_normalized
            + 0.16 * conviction
            + 0.18 * business_quality
            + 0.22 * high_cagr_potential
            + 0.14 * durability
            + 0.08 * expected_score
            + 0.06 * opportunity_score
            - 0.35 * cycle_penalty,
            0,
            100,
        ),
        2,
    )


def _promotion_sort_key(row: dict[str, Any]) -> tuple[int, float, float]:
    status_rank = {
        "PROMOTE_TO_CORE_REVIEW": 4,
        "STRONG_WATCH_ONLY": 3,
        "WAIT_FOR_BETTER_DATA_OR_PRICE": 2,
        "DO_NOT_PROMOTE": 1,
    }.get(str(row.get("promotion_status")), 0)
    return (
        status_rank,
        safe_float(row.get("conviction_score")) or 0.0,
        safe_float(row.get("score_total")) or 0.0,
    )
