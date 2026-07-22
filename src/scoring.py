from __future__ import annotations

from typing import Any

from .benchmark_relevance_engine import benchmark_relevance_level
from .business_profile_engine import detect_business_profile
from .utils import first_present, safe_float


def percent_points(value: Any) -> float | None:
    number = safe_float(value)
    if number is None:
        return None
    if -1.5 <= number <= 1.5:
        return number * 100
    return number


def ratio_value(value: Any) -> float | None:
    return safe_float(value)


def display_value(value: Any) -> str:
    if value is None:
        return "Donnée pas dispo"
    return str(value)


def display_number(value: Any) -> str:
    number = safe_float(value)
    if number is None:
        return "Donnée pas dispo"
    return f"{number:.2f}"


def compute_fundamental_score(
    ticker: str,
    manual: dict[str, Any],
    market: dict[str, Any],
    benchmark: dict[str, Any],
) -> dict[str, Any]:
    def _magnitude_score(value: float, threshold: float) -> float:
        """
        Continuous score in [0.0, 1.0] based on value/threshold ratio.
        Returns 0.0 if value < threshold (below threshold = no credit).
        Breakpoints: 0.4 at 1x, 0.7 at 1.75x, 1.0 at 2.5x.
        Linear interpolation between breakpoints.
        """
        if threshold <= 0:
            return 0.0
        if value < threshold:
            return 0.0
        ratio = value / threshold
        if ratio >= 2.5:
            return 1.0
        if ratio >= 1.75:
            return round(0.7 + (ratio - 1.75) * (0.3 / 0.75), 4)
        return round(0.4 + (ratio - 1.0) * (0.3 / 0.75), 4)

    criteria: dict[str, dict[str, Any]] = {}
    passed: list[str] = []
    failed: list[str] = []
    manual_required: list[str] = []
    score = 0.0
    possible_if_missing_positive = 0.0
    profile = detect_business_profile(ticker, market)
    roic_threshold = float(profile["roic_threshold"])
    eps_hist_threshold = float(profile["eps_hist_threshold"])
    eps_est_threshold = float(profile["eps_est_threshold"])
    sector_cagr_threshold = float(profile["sector_cagr_threshold"])
    forward_pe_limit = float(profile["forward_pe_limit"])
    peg_limit = float(profile["peg_limit"])

    def add_criterion(
        code: str,
        label: str,
        points: float | None,
        max_points: float,
        detail: str,
        missing_fields: list[str] | None = None,
    ) -> None:
        nonlocal score, possible_if_missing_positive
        missing_fields = missing_fields or []
        criteria[code] = {
            "label": label,
            "points": points,
            "max_points": max_points,
            "detail": detail,
            "missing_fields": missing_fields,
        }
        if points is None:
            possible_if_missing_positive += max_points
            manual_required.append(f"{code}: {', '.join(missing_fields) or label}")
        else:
            score += points
            possible_if_missing_positive += points
            if points >= max_points:
                passed.append(f"{code}: {label}")
            elif points <= 0:
                failed.append(f"{code}: {label}")
            else:
                passed.append(f"{code}: {label} partiel")

    roic = percent_points(manual.get("roic_5y_avg"))
    if roic is None:
        add_criterion("C1", profile["roic_label"], None, 1.0, "MANUAL_REQUIRED", ["roic_5y_avg"])
    else:
        _c1_pts = _magnitude_score(roic, roic_threshold)
        add_criterion(
            "C1",
            profile["roic_label"],
            _c1_pts,
            1.0,
            f"Capital/proxy={roic:.1f} %, seuil profil={roic_threshold:.1f} %, "
            f"{f'ratio={roic/roic_threshold:.2f}×' if roic_threshold > 0 else 'ratio=N/D'}",
        )

    margin_stable = manual.get("net_margin_stable_or_expanding")
    if margin_stable is None:
        add_criterion(
            "C2",
            "Marge nette stable ou en expansion",
            None,
            1.0,
            "MANUAL_REQUIRED",
            ["net_margin_stable_or_expanding"],
        )
    else:
        add_criterion("C2", "Marge nette stable ou en expansion", 1.0 if margin_stable else 0.0, 1.0, str(margin_stable))

    eps_5y = percent_points(manual.get("eps_growth_5y"))
    if eps_5y is None:
        add_criterion(
            "C3",
            f"Croissance EPS 5 ans > {eps_hist_threshold:.0f} %",
            None,
            1.0,
            "MANUAL_REQUIRED",
            ["eps_growth_5y"],
        )
    else:
        _c3_pts = _magnitude_score(eps_5y, eps_hist_threshold)
        add_criterion(
            "C3",
            f"Croissance EPS 5 ans > {eps_hist_threshold:.0f} %",
            _c3_pts,
            1.0,
            f"EPS 5 ans={eps_5y:.1f} %, seuil profil={eps_hist_threshold:.1f} %, "
            f"{f'ratio={eps_5y/eps_hist_threshold:.2f}×' if eps_hist_threshold > 0 else 'ratio=N/D'}",
        )

    moat_clear = manual.get("moat_clear")
    if moat_clear is None:
        add_criterion("C4", "Avantage compétitif clair", None, 1.0, "MANUAL_REQUIRED", ["moat_clear"])
    else:
        add_criterion("C4", "Avantage compétitif clair", 1.0 if moat_clear else 0.0, 1.0, str(moat_clear))

    eps_est = percent_points(manual.get("eps_growth_estimated_3_5y"))
    if eps_est is None:
        add_criterion(
            "C5",
            f"Croissance EPS estimée 3-5 ans > {eps_est_threshold:.0f} %",
            None,
            1.0,
            "MANUAL_REQUIRED",
            ["eps_growth_estimated_3_5y"],
        )
    else:
        _c5_pts = _magnitude_score(eps_est, eps_est_threshold)
        add_criterion(
            "C5",
            f"Croissance EPS estimée 3-5 ans > {eps_est_threshold:.0f} %",
            _c5_pts,
            1.0,
            f"EPS estimé={eps_est:.1f} %, seuil profil={eps_est_threshold:.1f} %, "
            f"{f'ratio={eps_est/eps_est_threshold:.2f}×' if eps_est_threshold > 0 else 'ratio=N/D'}",
        )

    sector_cagr = percent_points(manual.get("sector_cagr_estimated"))
    if sector_cagr is None:
        add_criterion(
            "C6",
            f"Marché adressable en expansion > {sector_cagr_threshold:.0f} %",
            None,
            1.0,
            "MANUAL_REQUIRED",
            ["sector_cagr_estimated"],
        )
    else:
        _c6_pts = _magnitude_score(sector_cagr, sector_cagr_threshold)
        add_criterion(
            "C6",
            f"Marché adressable en expansion > {sector_cagr_threshold:.0f} %",
            _c6_pts,
            1.0,
            f"Secteur={sector_cagr:.1f} %, seuil profil={sector_cagr_threshold:.1f} %, "
            f"{f'ratio={sector_cagr/sector_cagr_threshold:.2f}×' if sector_cagr_threshold > 0 else 'ratio=N/D'}",
        )

    benchmark_usable = safe_float(benchmark.get("benchmark_usable_cagr"))
    benchmark_period = str(benchmark.get("benchmark_usable_period") or "Donnée pas dispo")
    benchmark_above = benchmark.get("benchmark_above_sma_200")
    relevance_level = benchmark_relevance_level(benchmark)
    criterion_7_points = 0.0
    missing_c7: list[str] = []
    if benchmark_usable is None:
        missing_c7.append("benchmark_cagr_available")
        benchmark_detail = "ETF rendement historique=Donnée pas dispo"
    else:
        benchmark_detail = f"ETF rendement historique ({benchmark_period})={benchmark_usable:.1%}"
    if benchmark_usable is not None and benchmark_usable >= 0.06:
        criterion_7_points += 0.5
    if benchmark_above is None:
        missing_c7.append("benchmark_above_sma_200")
    elif benchmark_above:
        criterion_7_points += 0.5
    raw_criterion_7_points = criterion_7_points
    criterion_7_points = _adjust_benchmark_criterion_points(criterion_7_points, relevance_level, len(missing_c7))
    add_criterion(
        "C7",
        "Aucun déclin structurel du secteur",
        None if len(missing_c7) == 2 else criterion_7_points,
        1.0,
        (
            f"{benchmark_detail}, au-dessus SMA200={display_value(benchmark_above)}, "
            f"pertinence benchmark={relevance_level}"
        ),
        missing_c7,
    )
    if len(missing_c7) == 1:
        manual_required.append(f"C7: {missing_c7[0]}")
        possible_if_missing_positive += _missing_benchmark_criterion_upside(relevance_level)

    forward_pe = first_present(manual.get("forward_pe_manual"), market.get("forward_pe"))
    peg = first_present(manual.get("peg_manual"), market.get("peg"))
    forward_pe = ratio_value(forward_pe)
    peg = ratio_value(peg)
    missing_c8 = []
    criterion_8_points = 0.0
    if forward_pe is None:
        missing_c8.append("forward_pe")
    elif forward_pe <= forward_pe_limit:
        criterion_8_points += 0.5
    if peg is None:
        missing_c8.append("peg")
    elif peg <= peg_limit:
        criterion_8_points += 0.5
    add_criterion(
        "C8",
        f"Forward PE <= {forward_pe_limit:.0f} et PEG <= {peg_limit:.1f}",
        None if len(missing_c8) == 2 else criterion_8_points,
        1.0,
        f"Forward PE={display_number(forward_pe)}, PEG={display_number(peg)}, limites profil={forward_pe_limit:.0f}/{peg_limit:.1f}",
        missing_c8,
    )
    if len(missing_c8) == 1:
        manual_required.append(f"C8: {missing_c8[0]}")
        possible_if_missing_positive += 0.5
    if ticker in {"LLY", "AVGO"}:
        criteria["C8"]["note"] = "exception de croissance possible, à justifier manuellement"

    valuation_ok = manual.get("valuation_vs_5y_avg_ok")
    if valuation_ok is None:
        add_criterion(
            "C9",
            "Pas plus de 30 % au-dessus de sa moyenne de valorisation 5 ans",
            None,
            1.0,
            "MANUAL_REQUIRED",
            ["valuation_vs_5y_avg_ok"],
        )
    else:
        add_criterion("C9", "Valorisation vs moyenne 5 ans acceptable", 1.0 if valuation_ok else 0.0, 1.0, str(valuation_ok))

    current_price = first_present(market.get("current_price"), manual.get("current_price_manual"))
    fair_value = manual.get("fair_value")
    current_price = ratio_value(current_price)
    fair_value = ratio_value(fair_value)
    ratio = current_price / fair_value if current_price and fair_value and fair_value > 0 else None
    if ratio is None:
        add_criterion(
            "C10",
            "Pas en euphorie extrême",
            None,
            1.0,
            "MANUAL_REQUIRED",
            ["current_price", "fair_value"],
        )
    else:
        c10_points = 1.0 if ratio <= 1.20 else 0.5 if ratio <= 1.40 else 0.0
        add_criterion("C10", "Pas en euphorie extrême", c10_points, 1.0, f"Prix / juste valeur={ratio:.2f}")

    missing_count = len({item.split(":")[0] + item.split(":")[-1] for item in manual_required})
    confidence_level = "HIGH" if missing_count <= 1 else "MEDIUM" if missing_count <= 3 else "LOW"
    score_confirmed = round(score, 2)

    # Data gap haircut: applied when missing_count >= 3.
    # Calibrated to discriminate moderate vs. severe data gaps without
    # depressing the entire universe when manual fields are absent by default.
    # missing_count 0-2: no haircut (normal yfinance coverage gap)
    # missing_count 3-4: -0.2 per criterion beyond 2 (mild penalty)
    # missing_count 5+:  -0.25 per criterion beyond 2, capped at -1.0
    _score_data_gap_haircut = 0.0
    if missing_count >= 3:
        if missing_count <= 4:
            _score_data_gap_haircut = round((missing_count - 2) * 0.2, 2)
        else:
            _score_data_gap_haircut = round(min(1.0, (missing_count - 2) * 0.25), 2)
        score = round(max(0.0, score - _score_data_gap_haircut), 2)
        possible_if_missing_positive = round(
            max(0.0, possible_if_missing_positive - _score_data_gap_haircut), 2
        )

    # Data gap flag: visible signal for reporting and auditing.
    _score_data_gap_flag = missing_count >= 3
    if missing_count == 0:
        _score_data_gap_label = "COMPLET"
    elif missing_count <= 2:
        _score_data_gap_label = "PARTIEL_MINEUR"
    elif missing_count <= 4:
        _score_data_gap_label = "PARTIEL_MODERE"
    else:
        _score_data_gap_label = "PARTIEL_SEVERE"

    return {
        "ticker": ticker,
        "score_total": round(score, 2),
        "score_confirmed": score_confirmed,
        "score_possible_if_missing_data_positive": round(min(10.0, possible_if_missing_positive), 2),
        "score_missing_data_count": missing_count,
        "score_data_gap_haircut": _score_data_gap_haircut,
        "score_data_gap_flag": _score_data_gap_flag,
        "score_data_gap_label": _score_data_gap_label,
        "passed_criteria": passed,
        "failed_criteria": failed,
        "manual_required_criteria": manual_required,
        "confidence_level": confidence_level,
        "criteria": criteria,
        "roic_5y_avg": roic,
        "eps_growth_5y": eps_5y,
        "eps_growth_estimated_3_5y": eps_est,
        "sector_cagr_estimated": sector_cagr,
        "forward_pe": forward_pe,
        "peg": peg,
        "current_price": current_price,
        "fair_value": fair_value,
        "price_to_fair_value": ratio,
        "criterion_7_validated": raw_criterion_7_points >= 1.0 and len(missing_c7) == 0 and relevance_level != "LOW",
        "business_profile": profile["business_profile"],
        "business_profile_label": profile["business_profile_label"],
        "business_profile_reason": profile["profile_reason"],
        "profile_roic_threshold": roic_threshold,
        "profile_eps_hist_threshold": eps_hist_threshold,
        "profile_eps_est_threshold": eps_est_threshold,
        "profile_sector_cagr_threshold": sector_cagr_threshold,
        "profile_forward_pe_limit": forward_pe_limit,
        "profile_peg_limit": peg_limit,
        "profile_weak_growth_threshold": float(profile["weak_growth_threshold"]),
        "profile_serious_growth_floor": float(profile["serious_growth_floor"]),
    }


def _adjust_benchmark_criterion_points(raw_points: float, relevance_level: str, missing_count: int) -> float:
    if missing_count == 2:
        return raw_points
    relevance_level = relevance_level.upper()
    if relevance_level == "LOW":
        if raw_points >= 1.0:
            return 0.5
        if raw_points >= 0.5:
            return 0.35
        return 0.25
    if relevance_level == "MEDIUM":
        if raw_points >= 1.0:
            return 0.75
        if raw_points >= 0.5:
            return 0.5
        return 0.25
    return raw_points


def _missing_benchmark_criterion_upside(relevance_level: str) -> float:
    if relevance_level.upper() == "LOW":
        return 0.25
    if relevance_level.upper() == "MEDIUM":
        return 0.35
    return 0.5
