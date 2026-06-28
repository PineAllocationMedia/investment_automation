from __future__ import annotations

from statistics import mean, pstdev
from typing import Any

from .proxy_calibration import BOOLEAN_FIELDS, PROXY_CALIBRATION_FIELDS, PERCENT_POINT_FIELDS
from .utils import clamp, normalize_ticker, safe_float


PROXY_BIAS_COLUMNS = [
    "field",
    "field_type",
    "status",
    "confidence",
    "sample_count",
    "usable_sample_count",
    "distinct_ticker_count",
    "mean_error_pct",
    "std_error_pct",
    "same_direction_rate",
    "proxy_direction",
    "suggested_factor",
    "raw_factor",
    "max_safe_factor_change",
    "ignored_low_confidence_count",
    "ignored_near_zero_count",
    "ignored_outlier_count",
    "boolean_mismatch_rate",
    "recommendation",
    "reason",
]

USABLE_HISTORY_STATUSES = {"MATCH", "CLOSE", "REVIEW_PROXY"}
ACTIONABLE_BIAS_STATUSES = {"BIAS_CANDIDATE_SAFE_SIGNAL", "BIAS_CANDIDATE_REVIEW", "BOOLEAN_RULE_REVIEW"}
DEFAULT_MIN_SAMPLES = 5
DEFAULT_MIN_DISTINCT_TICKERS = 3
DEFAULT_MIN_ABS_MEAN_ERROR = 0.10
DEFAULT_MAX_ERROR_STD = 0.08
DEFAULT_MIN_DIRECTION_RATE = 0.80
MAX_SAFE_FACTOR_CHANGE = 0.25
MAX_ABS_ERROR_FOR_BIAS_SAMPLE = 0.75
MIN_TRUE_ABS_PERCENT_POINT = 1.0
MIN_TRUE_ABS_NUMERIC = 0.01


def build_proxy_bias_report(
    history_rows: list[dict[str, Any]],
    *,
    min_samples: int = DEFAULT_MIN_SAMPLES,
    min_distinct_tickers: int = DEFAULT_MIN_DISTINCT_TICKERS,
    min_abs_mean_error: float = DEFAULT_MIN_ABS_MEAN_ERROR,
    max_error_std: float = DEFAULT_MAX_ERROR_STD,
    min_direction_rate: float = DEFAULT_MIN_DIRECTION_RATE,
    max_factor_change: float = MAX_SAFE_FACTOR_CHANGE,
) -> list[dict[str, Any]]:
    """Detect possible systematic proxy bias without applying any correction.

    This engine is intentionally conservative because its output may later feed
    a calibration governor. It requires several independent examples moving in
    the same direction before suggesting that a proxy may be biased.
    """

    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in history_rows:
        field = str(row.get("field") or "").strip()
        if field:
            grouped.setdefault(field, []).append(row)

    rows = []
    for field_row in PROXY_CALIBRATION_FIELDS:
        field = field_row["field"]
        field_type = str(field_row.get("value_type") or "").strip() or _field_type(field)
        field_history = grouped.get(field, [])
        if field in BOOLEAN_FIELDS:
            rows.append(
                _boolean_bias_row(
                    field,
                    field_type,
                    field_history,
                    min_samples=min_samples,
                    min_distinct_tickers=min_distinct_tickers,
                )
            )
            continue
        rows.append(
            _numeric_bias_row(
                field,
                field_type,
                field_history,
                min_samples=min_samples,
                min_distinct_tickers=min_distinct_tickers,
                min_abs_mean_error=min_abs_mean_error,
                max_error_std=max_error_std,
                min_direction_rate=min_direction_rate,
                max_factor_change=max_factor_change,
            )
        )
    return rows


def actionable_proxy_bias_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [row for row in rows if str(row.get("status") or "") in ACTIONABLE_BIAS_STATUSES]


def proxy_bias_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    actionable = actionable_proxy_bias_rows(rows)
    safe_signals = [row for row in actionable if row.get("status") == "BIAS_CANDIDATE_SAFE_SIGNAL"]
    review_signals = [row for row in actionable if row.get("status") != "BIAS_CANDIDATE_SAFE_SIGNAL"]
    if safe_signals:
        status = "SYSTEMATIC_BIAS_SIGNAL"
    elif review_signals:
        status = "REVIEW_SIGNALS_ONLY"
    elif rows:
        status = "NO_SYSTEMATIC_BIAS_DETECTED"
    else:
        status = "NO_HISTORY"
    return {
        "status": status,
        "actionable_count": len(actionable),
        "safe_signal_count": len(safe_signals),
        "review_signal_count": len(review_signals),
        "fields": ", ".join(str(row.get("field") or "") for row in actionable),
    }


def _numeric_bias_row(
    field: str,
    field_type: str,
    rows: list[dict[str, Any]],
    *,
    min_samples: int,
    min_distinct_tickers: int,
    min_abs_mean_error: float,
    max_error_std: float,
    min_direction_rate: float,
    max_factor_change: float,
) -> dict[str, Any]:
    samples, counts = _numeric_error_samples(field, rows)
    errors = [sample["error"] for sample in samples]
    tickers = {sample["ticker"] for sample in samples if sample["ticker"]}
    sample_count = len(rows)
    usable_count = len(errors)
    distinct_count = len(tickers)

    if usable_count < min_samples:
        return _base_row(
            field,
            field_type,
            status="INSUFFICIENT_HISTORY",
            confidence="LOW",
            sample_count=sample_count,
            usable_sample_count=usable_count,
            distinct_ticker_count=distinct_count,
            counts=counts,
            max_safe_factor_change=max_factor_change,
            recommendation="Accumuler plus d’exemples fiables avant toute conclusion.",
            reason=f"Il faut au moins {min_samples} exemples numériques utilisables.",
        )
    if distinct_count < min_distinct_tickers:
        return _base_row(
            field,
            field_type,
            status="INSUFFICIENT_DIVERSITY",
            confidence="LOW",
            sample_count=sample_count,
            usable_sample_count=usable_count,
            distinct_ticker_count=distinct_count,
            counts=counts,
            max_safe_factor_change=max_factor_change,
            recommendation="Ajouter des exemples provenant de plusieurs entreprises avant de conclure.",
            reason=f"Les exemples couvrent seulement {distinct_count} ticker(s) distinct(s).",
        )

    mean_error = mean(errors)
    std_error = pstdev(errors) if len(errors) > 1 else 0.0
    positive_count = sum(1 for error in errors if error > 0)
    negative_count = sum(1 for error in errors if error < 0)
    same_direction_rate = max(positive_count, negative_count) / usable_count if usable_count else 0.0
    direction = "PROXY_TOO_HIGH" if mean_error > 0 else "PROXY_TOO_LOW"
    raw_factor = _correction_factor(mean_error)
    capped_factor = _cap_factor(raw_factor, max_factor_change) if raw_factor is not None else None

    has_material_individual_errors = any(abs(error) >= min_abs_mean_error for error in errors)
    if has_material_individual_errors and (same_direction_rate < min_direction_rate or std_error > max_error_std):
        return _base_row(
            field,
            field_type,
            status="CONTRADICTORY_OR_NOISY",
            confidence="LOW",
            sample_count=sample_count,
            usable_sample_count=usable_count,
            distinct_ticker_count=distinct_count,
            mean_error=mean_error,
            std_error=std_error,
            same_direction_rate=same_direction_rate,
            direction=direction,
            raw_factor=raw_factor,
            capped_factor=capped_factor,
            counts=counts,
            max_safe_factor_change=max_factor_change,
            recommendation="Ne pas corriger automatiquement; revoir les sources ou accumuler plus d’exemples.",
            reason="Les erreurs sont matérielles mais contradictoires; elles ne prouvent pas un biais stable.",
        )
    if abs(mean_error) < min_abs_mean_error:
        return _base_row(
            field,
            field_type,
            status="NO_NUMERIC_BIAS",
            confidence="MEDIUM",
            sample_count=sample_count,
            usable_sample_count=usable_count,
            distinct_ticker_count=distinct_count,
            mean_error=mean_error,
            std_error=std_error,
            same_direction_rate=same_direction_rate,
            direction=direction,
            counts=counts,
            max_safe_factor_change=max_factor_change,
            recommendation="Ne rien changer.",
            reason="L’écart moyen est trop petit pour justifier une correction.",
        )
    confidence = _numeric_bias_confidence(usable_count, distinct_count, std_error, same_direction_rate)
    status = "BIAS_CANDIDATE_SAFE_SIGNAL" if confidence == "HIGH" else "BIAS_CANDIDATE_REVIEW"
    return _base_row(
        field,
        field_type,
        status=status,
        confidence=confidence,
        sample_count=sample_count,
        usable_sample_count=usable_count,
        distinct_ticker_count=distinct_count,
        mean_error=mean_error,
        std_error=std_error,
        same_direction_rate=same_direction_rate,
        direction=direction,
        raw_factor=raw_factor,
        capped_factor=capped_factor,
        counts=counts,
        max_safe_factor_change=max_factor_change,
        recommendation="Signal de biais possible à confirmer; ne pas appliquer sans gouverneur de sécurité.",
        reason=_numeric_bias_reason(direction, mean_error, capped_factor, max_factor_change),
    )


def _boolean_bias_row(
    field: str,
    field_type: str,
    rows: list[dict[str, Any]],
    *,
    min_samples: int,
    min_distinct_tickers: int,
) -> dict[str, Any]:
    usable = [
        row
        for row in rows
        if str(row.get("comparison_status") or "").strip() in USABLE_HISTORY_STATUSES
        and str(row.get("confidence") or "MEDIUM").strip().upper() != "LOW"
    ]
    tickers = {normalize_ticker(row.get("ticker")) for row in usable if normalize_ticker(row.get("ticker"))}
    mismatch_count = sum(1 for row in usable if str(row.get("comparison_status") or "").strip() == "REVIEW_PROXY")
    mismatch_rate = mismatch_count / len(usable) if usable else 0.0
    low_confidence_count = sum(1 for row in rows if str(row.get("confidence") or "MEDIUM").strip().upper() == "LOW")
    counts = {
        "ignored_low_confidence_count": low_confidence_count,
        "ignored_near_zero_count": 0,
        "ignored_outlier_count": 0,
    }
    if len(usable) < min_samples:
        status = "INSUFFICIENT_HISTORY"
        confidence = "LOW"
        recommendation = "Accumuler plus d’exemples fiables avant de juger ce proxy vrai/faux."
        reason = f"Il faut au moins {min_samples} exemples utilisables."
    elif len(tickers) < min_distinct_tickers:
        status = "INSUFFICIENT_DIVERSITY"
        confidence = "LOW"
        recommendation = "Ajouter des exemples de plusieurs entreprises avant de juger ce proxy vrai/faux."
        reason = f"Les exemples couvrent seulement {len(tickers)} ticker(s) distinct(s)."
    elif mismatch_rate >= 0.60:
        status = "BOOLEAN_RULE_REVIEW"
        confidence = "MEDIUM" if len(usable) < 8 else "HIGH"
        recommendation = "Revoir la règle qualitative; aucun facteur multiplicatif ne doit être appliqué à un booléen."
        reason = "Le proxy vrai/faux donne souvent la conclusion inverse des données fournies."
    else:
        status = "NO_BOOLEAN_BIAS"
        confidence = "MEDIUM"
        recommendation = "Ne rien changer."
        reason = "Les exemples ne montrent pas de problème répété sur ce champ qualitatif."
    return _base_row(
        field,
        field_type,
        status=status,
        confidence=confidence,
        sample_count=len(rows),
        usable_sample_count=len(usable),
        distinct_ticker_count=len(tickers),
        counts=counts,
        boolean_mismatch_rate=mismatch_rate,
        recommendation=recommendation,
        reason=reason,
    )


def _numeric_error_samples(field: str, rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, int]]:
    samples = []
    ignored_low_confidence = 0
    ignored_near_zero = 0
    ignored_outlier = 0
    min_true_abs = MIN_TRUE_ABS_PERCENT_POINT if field in PERCENT_POINT_FIELDS else MIN_TRUE_ABS_NUMERIC
    for row in rows:
        if str(row.get("comparison_status") or "").strip() not in USABLE_HISTORY_STATUSES:
            continue
        if str(row.get("confidence") or "MEDIUM").strip().upper() == "LOW":
            ignored_low_confidence += 1
            continue
        true_value = safe_float(row.get("true_value"))
        if true_value is None or abs(true_value) < min_true_abs:
            ignored_near_zero += 1
            continue
        error = safe_float(row.get("relative_difference"))
        if error is None:
            error_pct = safe_float(row.get("error_pct"))
            error = error_pct / 100.0 if error_pct is not None else None
        if error is None:
            continue
        if abs(error) > MAX_ABS_ERROR_FOR_BIAS_SAMPLE:
            ignored_outlier += 1
            continue
        samples.append({"ticker": normalize_ticker(row.get("ticker")), "error": error})
    return samples, {
        "ignored_low_confidence_count": ignored_low_confidence,
        "ignored_near_zero_count": ignored_near_zero,
        "ignored_outlier_count": ignored_outlier,
    }


def _correction_factor(mean_error: float) -> float | None:
    denominator = 1.0 + mean_error
    if denominator <= 0.20:
        return None
    return 1.0 / denominator


def _cap_factor(raw_factor: float | None, max_factor_change: float) -> float | None:
    if raw_factor is None:
        return None
    lower = 1.0 - max_factor_change
    upper = 1.0 + max_factor_change
    return clamp(raw_factor, lower, upper)


def _numeric_bias_confidence(
    usable_count: int,
    distinct_count: int,
    std_error: float,
    same_direction_rate: float,
) -> str:
    if usable_count >= 8 and distinct_count >= 5 and std_error <= 0.05 and same_direction_rate >= 0.90:
        return "HIGH"
    return "MEDIUM"


def _numeric_bias_reason(
    direction: str,
    mean_error: float,
    capped_factor: float | None,
    max_factor_change: float,
) -> str:
    factor_text = "aucun facteur calculable" if capped_factor is None else f"facteur suggéré {round(capped_factor, 4)}"
    cap_text = f"plafonné à ±{int(max_factor_change * 100)} %"
    return (
        f"Les exemples montrent un écart moyen de {round(mean_error * 100, 2)} % "
        f"avec une direction {direction}; {factor_text}, {cap_text}."
    )


def _base_row(
    field: str,
    field_type: str,
    *,
    status: str,
    confidence: str,
    sample_count: int,
    usable_sample_count: int,
    distinct_ticker_count: int,
    counts: dict[str, int],
    mean_error: float | None = None,
    std_error: float | None = None,
    same_direction_rate: float | None = None,
    direction: str = "",
    raw_factor: float | None = None,
    capped_factor: float | None = None,
    boolean_mismatch_rate: float | None = None,
    max_safe_factor_change: float = MAX_SAFE_FACTOR_CHANGE,
    recommendation: str = "",
    reason: str = "",
) -> dict[str, Any]:
    return {
        "field": field,
        "field_type": field_type,
        "status": status,
        "confidence": confidence,
        "sample_count": sample_count,
        "usable_sample_count": usable_sample_count,
        "distinct_ticker_count": distinct_ticker_count,
        "mean_error_pct": _rounded_pct(mean_error),
        "std_error_pct": _rounded_pct(std_error),
        "same_direction_rate": round(same_direction_rate, 4) if same_direction_rate is not None else "",
        "proxy_direction": direction,
        "suggested_factor": round(capped_factor, 6) if capped_factor is not None else "",
        "raw_factor": round(raw_factor, 6) if raw_factor is not None else "",
        "max_safe_factor_change": max_safe_factor_change,
        "ignored_low_confidence_count": counts.get("ignored_low_confidence_count", 0),
        "ignored_near_zero_count": counts.get("ignored_near_zero_count", 0),
        "ignored_outlier_count": counts.get("ignored_outlier_count", 0),
        "boolean_mismatch_rate": round(boolean_mismatch_rate, 4) if boolean_mismatch_rate is not None else "",
        "recommendation": recommendation,
        "reason": reason,
    }


def _rounded_pct(value: float | None) -> float | str:
    if value is None:
        return ""
    return round(value * 100, 4)


def _field_type(field: str) -> str:
    if field in BOOLEAN_FIELDS:
        return "boolean"
    if field in PERCENT_POINT_FIELDS:
        return "percent"
    return "number"
