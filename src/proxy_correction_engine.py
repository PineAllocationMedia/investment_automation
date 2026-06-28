from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from typing import Any

from .proxy_calibration import BOOLEAN_FIELDS, PROXY_CALIBRATION_FIELD_NAMES
from .utils import load_yaml, read_csv_records, safe_bool, safe_float, today_iso, write_csv_records, write_yaml


MAX_PROXY_CORRECTION_CHANGE = 0.25
MIN_PROXY_CORRECTION_FACTOR = 1.0 - MAX_PROXY_CORRECTION_CHANGE
MAX_PROXY_CORRECTION_FACTOR = 1.0 + MAX_PROXY_CORRECTION_CHANGE
MIN_PROXY_CORRECTION_SAMPLES = 5
MEDIUM_CONFIDENCE_MIN_SAMPLES = 8

PROXY_CORRECTION_NUMERIC_FIELDS = [field for field in PROXY_CALIBRATION_FIELD_NAMES if field not in BOOLEAN_FIELDS]
PROXY_CORRECTION_PARAMETER_PREFIX = "proxy_correction:"

PROXY_CORRECTION_HISTORY_COLUMNS = [
    "applied_at",
    "mode",
    "parameter",
    "field",
    "previous_value",
    "new_value",
    "delta",
    "suggestion_id",
    "safety_level",
    "confidence",
    "sample_count",
    "mean_error_pct",
    "std_error_pct",
    "reason",
]

PROXY_CORRECTION_AUDIT_COLUMNS = [
    "field",
    "status",
    "risk_level",
    "factor",
    "confidence",
    "sample_count",
    "last_updated",
    "days_since_update",
    "bias_status",
    "bias_confidence",
    "bias_sample_count",
    "current_suggested_factor",
    "factor_gap",
    "max_safe_factor_change",
    "recommended_action",
    "reason",
]

LOW_RISK_PROXY_CORRECTION_STATUSES = {
    "DISABLED",
    "NO_ACTIVE_CORRECTIONS",
    "ACTIVE_OK",
    "ACTIVE_NEEDS_MORE_FRESH_EVIDENCE",
}
REVIEW_PROXY_CORRECTION_STATUSES = {
    "CONFIG_WARNING",
    "REVIEW_FACTOR_NEAR_LIMIT",
    "REVIEW_STALE_CORRECTION",
    "REVIEW_NO_LONGER_CONFIRMED",
    "REVIEW_NOISY_EVIDENCE",
    "REVIEW_CONFLICTING_EVIDENCE",
}


def create_proxy_corrections_template(path: str | Path, overwrite: bool = False) -> None:
    path = Path(path)
    if path.exists() and not overwrite:
        return
    write_yaml(
        path,
        {
            "version": 1,
            "enabled": False,
            "generated_date": today_iso(),
            "max_factor_change": MAX_PROXY_CORRECTION_CHANGE,
            "notes": (
                "Corrections de proxy validées. Laisser enabled: false sauf si une correction "
                "a été confirmée par l'audit et les garde-fous."
            ),
            "corrections": {},
        },
    )


def create_proxy_correction_history(path: str | Path) -> None:
    write_csv_records(path, [], PROXY_CORRECTION_HISTORY_COLUMNS)


def load_proxy_corrections(path: str | Path) -> dict[str, Any]:
    payload = load_yaml(path)
    enabled = safe_bool(payload.get("enabled"))
    enabled = bool(enabled) if enabled is not None else False
    max_change = safe_float(payload.get("max_factor_change"))
    if max_change is None or max_change <= 0 or max_change > MAX_PROXY_CORRECTION_CHANGE:
        max_change = MAX_PROXY_CORRECTION_CHANGE

    active: dict[str, dict[str, Any]] = {}
    warnings: list[str] = []
    if not enabled:
        return {
            "enabled": False,
            "active_corrections": active,
            "warnings": warnings,
            "max_factor_change": max_change,
        }

    corrections = payload.get("corrections") or {}
    if not isinstance(corrections, dict):
        warnings.append("corrections doit être un dictionnaire YAML.")
        corrections = {}
    for field, raw_correction in corrections.items():
        field_name = str(field or "").strip()
        correction = raw_correction if isinstance(raw_correction, dict) else {}
        accepted, warning = _validated_correction(field_name, correction, max_change)
        if accepted:
            active[field_name] = accepted
        if warning:
            warnings.append(warning)

    return {
        "enabled": enabled,
        "active_corrections": active,
        "warnings": warnings,
        "max_factor_change": max_change,
    }


def build_proxy_correction_audit(
    correction_state: dict[str, Any] | None,
    bias_rows: list[dict[str, Any]] | None = None,
    *,
    as_of: date | None = None,
) -> list[dict[str, Any]]:
    """Audit active proxy corrections without changing model behavior.

    This is the post-activation governor: it keeps corrections visible and
    highlights cases where fresh evidence no longer supports them. It never
    auto-disables a correction during analysis.
    """

    state = correction_state or {}
    max_change = safe_float(state.get("max_factor_change")) or MAX_PROXY_CORRECTION_CHANGE
    max_change = min(max_change, MAX_PROXY_CORRECTION_CHANGE)
    rows: list[dict[str, Any]] = []
    for warning in state.get("warnings") or []:
        rows.append(
            _proxy_correction_audit_row(
                field="",
                status="CONFIG_WARNING",
                risk_level="MEDIUM",
                max_safe_factor_change=max_change,
                recommended_action="Lire config/proxy_corrections.yaml et corriger la ligne invalide.",
                reason=str(warning),
            )
        )

    active = state.get("active_corrections") or {}
    if not state.get("enabled"):
        return rows or [
            _proxy_correction_audit_row(
                field="",
                status="DISABLED",
                risk_level="LOW",
                max_safe_factor_change=max_change,
                recommended_action="Aucune action.",
                reason="La couche de correction des proxies est désactivée; les estimations automatiques restent brutes.",
            )
        ]
    if not active:
        return rows or [
            _proxy_correction_audit_row(
                field="",
                status="NO_ACTIVE_CORRECTIONS",
                risk_level="LOW",
                max_safe_factor_change=max_change,
                recommended_action="Aucune action.",
                reason="Aucune correction active ne modifie les proxies.",
            )
        ]

    bias_by_field = {str(row.get("field") or "").strip(): row for row in bias_rows or []}
    for field, correction in sorted(active.items()):
        rows.append(_audit_active_proxy_correction(field, correction, bias_by_field.get(field), max_change, as_of=as_of))
    return rows


def proxy_correction_audit_summary(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "Aucun audit de correction proxy disponible."
    review_count = sum(1 for row in rows if str(row.get("status") or "") in REVIEW_PROXY_CORRECTION_STATUSES)
    active_count = sum(1 for row in rows if str(row.get("field") or "").strip())
    if review_count:
        return f"{review_count} correction(s) proxy à revoir; aucune désactivation automatique."
    if any(row.get("status") == "DISABLED" for row in rows):
        return "Corrections proxy désactivées."
    if active_count:
        return f"{active_count} correction(s) proxy active(s), aucun signal de surcorrection majeur."
    return "Aucune correction proxy active."


def apply_proxy_correction(
    field: str,
    value: Any,
    correction_state: dict[str, Any] | None,
) -> tuple[Any, dict[str, Any] | None]:
    correction = ((correction_state or {}).get("active_corrections") or {}).get(field)
    if not correction or field in BOOLEAN_FIELDS:
        return value, None
    number = safe_float(value)
    if number is None:
        return value, None
    factor = safe_float(correction.get("factor"))
    if factor is None:
        return value, None
    adjusted = number * factor
    precision = 2 if field == "fair_value" else 3
    return round(adjusted, precision), {
        "field": field,
        "factor": factor,
        "raw_value": number,
        "adjusted_value": round(adjusted, precision),
        "confidence": correction.get("confidence", ""),
        "sample_count": correction.get("sample_count", ""),
        "last_updated": correction.get("last_updated", ""),
        "source": correction.get("source", "proxy_corrections.yaml"),
    }


def apply_proxy_correction_suggestion(
    *,
    mode: str,
    suggestion: dict[str, Any],
    config_path: str | Path,
    history_path: str | Path,
) -> dict[str, Any]:
    field = proxy_correction_field_from_parameter(suggestion.get("parameter")) or str(
        suggestion.get("proxy_correction_field") or ""
    ).strip()
    if not field:
        raise ValueError("Champ de correction proxy manquant.")
    factor = safe_float(suggestion.get("proxy_correction_factor") or suggestion.get("suggested_value"))
    if factor is None:
        raise ValueError(f"Facteur de correction proxy invalide pour {field}.")
    confidence = str(suggestion.get("proxy_correction_confidence") or "").strip().upper()
    sample_count = int(safe_float(suggestion.get("proxy_correction_sample_count")) or 0)
    candidate = {
        "status": "ACTIVE",
        "factor": factor,
        "confidence": confidence,
        "sample_count": sample_count,
        "mean_error_pct": suggestion.get("proxy_correction_mean_error_pct", ""),
        "std_error_pct": suggestion.get("proxy_correction_std_error_pct", ""),
        "last_updated": today_iso(),
        "source": "latest_proxy_bias_report.csv",
    }
    accepted, warning = _validated_correction(field, candidate, MAX_PROXY_CORRECTION_CHANGE)
    if not accepted:
        raise ValueError(warning or f"Correction proxy refusée pour {field}.")

    config_path = Path(config_path)
    if not config_path.exists():
        create_proxy_corrections_template(config_path)
    payload = load_yaml(config_path)
    if not isinstance(payload, dict):
        payload = {}
    payload.setdefault("version", 1)
    payload["enabled"] = True
    payload["last_updated"] = datetime.now().isoformat(timespec="seconds")
    payload["max_factor_change"] = MAX_PROXY_CORRECTION_CHANGE
    corrections = payload.get("corrections")
    if not isinstance(corrections, dict):
        corrections = {}
    previous = corrections.get(field) if isinstance(corrections.get(field), dict) else {}
    previous_factor = safe_float((previous or {}).get("factor"))
    corrections[field] = {
        "status": "ACTIVE",
        "factor": round(factor, 6),
        "confidence": confidence,
        "sample_count": sample_count,
        "mean_error_pct": suggestion.get("proxy_correction_mean_error_pct", ""),
        "std_error_pct": suggestion.get("proxy_correction_std_error_pct", ""),
        "last_updated": today_iso(),
        "source": "latest_proxy_bias_report.csv",
    }
    payload["corrections"] = corrections
    write_yaml(config_path, payload)

    record = {
        "applied_at": datetime.now().isoformat(timespec="seconds"),
        "mode": mode,
        "parameter": f"{PROXY_CORRECTION_PARAMETER_PREFIX}{field}",
        "field": field,
        "previous_value": previous_factor if previous_factor is not None else "",
        "new_value": round(factor, 6),
        "delta": round(factor - (previous_factor if previous_factor is not None else 1.0), 6),
        "suggestion_id": str(suggestion.get("suggestion_id") or ""),
        "safety_level": str(suggestion.get("safety_level") or "SAFE"),
        "confidence": confidence,
        "sample_count": sample_count,
        "mean_error_pct": suggestion.get("proxy_correction_mean_error_pct", ""),
        "std_error_pct": suggestion.get("proxy_correction_std_error_pct", ""),
        "reason": str(suggestion.get("reason") or ""),
    }
    history = read_csv_records(history_path)
    history.append(record)
    write_csv_records(history_path, history, PROXY_CORRECTION_HISTORY_COLUMNS)
    return record


def proxy_correction_audit_requires_review(row: dict[str, Any]) -> bool:
    return str(row.get("status") or "") in REVIEW_PROXY_CORRECTION_STATUSES


def proxy_correction_field_from_parameter(parameter: Any) -> str:
    text = str(parameter or "").strip()
    if not text.startswith(PROXY_CORRECTION_PARAMETER_PREFIX):
        return ""
    return text.replace(PROXY_CORRECTION_PARAMETER_PREFIX, "", 1).strip()


def _validated_correction(
    field: str,
    correction: dict[str, Any],
    max_change: float,
) -> tuple[dict[str, Any] | None, str]:
    if field not in PROXY_CORRECTION_NUMERIC_FIELDS:
        return None, f"{field}: correction ignorée, champ non numérique ou inconnu."
    status = str(correction.get("status") or "").strip().upper()
    if status != "ACTIVE":
        return None, f"{field}: correction ignorée, status doit être ACTIVE."
    factor = safe_float(correction.get("factor"))
    if factor is None:
        return None, f"{field}: correction ignorée, factor invalide."
    lower = 1.0 - max_change
    upper = 1.0 + max_change
    if factor < lower or factor > upper:
        return None, f"{field}: correction ignorée, factor {factor} dépasse la borne ±{int(max_change * 100)}%."

    confidence = str(correction.get("confidence") or "").strip().upper()
    sample_count = int(safe_float(correction.get("sample_count")) or 0)
    if sample_count < MIN_PROXY_CORRECTION_SAMPLES:
        return None, f"{field}: correction ignorée, seulement {sample_count} exemple(s)."
    if confidence == "HIGH":
        pass
    elif confidence == "MEDIUM" and sample_count >= MEDIUM_CONFIDENCE_MIN_SAMPLES:
        pass
    else:
        return None, f"{field}: correction ignorée, confiance insuffisante ({confidence or 'N/D'})."

    return {
        "factor": factor,
        "confidence": confidence,
        "sample_count": sample_count,
        "mean_error_pct": correction.get("mean_error_pct", ""),
        "std_error_pct": correction.get("std_error_pct", ""),
        "last_updated": str(correction.get("last_updated") or "").strip(),
        "source": str(correction.get("source") or "proxy_corrections.yaml").strip(),
    }, ""


def _audit_active_proxy_correction(
    field: str,
    correction: dict[str, Any],
    bias_row: dict[str, Any] | None,
    max_change: float,
    *,
    as_of: date | None = None,
) -> dict[str, Any]:
    factor = safe_float(correction.get("factor"))
    days_since_update = _days_since(correction.get("last_updated"), as_of=as_of)
    bias_status = str((bias_row or {}).get("status") or "").strip()
    bias_confidence = str((bias_row or {}).get("confidence") or "").strip()
    bias_sample_count = int(safe_float((bias_row or {}).get("usable_sample_count") or (bias_row or {}).get("sample_count")) or 0)
    current_factor = safe_float((bias_row or {}).get("suggested_factor"))
    factor_gap = round(current_factor - factor, 6) if factor is not None and current_factor is not None else ""
    status = "ACTIVE_OK"
    risk_level = "LOW"
    action = "Conserver la correction; continuer à accumuler de vraies données."
    reason = "La correction active reste dans les bornes et aucun signal frais ne la contredit."

    if factor is not None and abs(factor - 1.0) >= max(0.0, max_change * 0.88):
        status = "REVIEW_FACTOR_NEAR_LIMIT"
        risk_level = "MEDIUM"
        action = "Valider avec plus d’exemples avant d’augmenter ou de conserver longtemps cette correction."
        reason = "Le facteur est proche de la borne maximale autorisée; le risque de surcorrection augmente."

    if days_since_update is not None and days_since_update >= 365:
        status = "REVIEW_STALE_CORRECTION"
        risk_level = "MEDIUM"
        action = "Relancer improvement-audit après quelques vraies données récentes ou réviser manuellement."
        reason = "La correction est ancienne; elle peut ne plus représenter les données actuelles."

    if bias_row:
        direction = str(bias_row.get("proxy_direction") or "").strip()
        expected_direction = "PROXY_TOO_LOW" if (factor or 1.0) > 1.0 else "PROXY_TOO_HIGH"
        if bias_status == "CONTRADICTORY_OR_NOISY":
            status = "REVIEW_NOISY_EVIDENCE"
            risk_level = "MEDIUM"
            action = "Ne pas renforcer la correction; accumuler plus de données avant toute nouvelle application."
            reason = "Les nouvelles observations sont matérielles mais bruyantes ou contradictoires."
        elif bias_status == "NO_NUMERIC_BIAS" and bias_sample_count >= MIN_PROXY_CORRECTION_SAMPLES:
            status = "REVIEW_NO_LONGER_CONFIRMED"
            risk_level = "MEDIUM"
            action = "Réviser la correction; elle ne doit pas être augmentée tant que l’évidence n’est pas revenue."
            reason = "Les nouvelles observations ne montrent plus un biais numérique assez clair."
        elif (
            bias_status in {"BIAS_CANDIDATE_SAFE_SIGNAL", "BIAS_CANDIDATE_REVIEW"}
            and direction
            and direction != expected_direction
        ):
            status = "REVIEW_CONFLICTING_EVIDENCE"
            risk_level = "HIGH"
            action = "Revue manuelle prioritaire; ne pas appliquer de nouvelle correction automatique sur ce champ."
            reason = "Le signal frais pointe dans la direction opposée à la correction active."
        elif bias_status in {"INSUFFICIENT_HISTORY", "INSUFFICIENT_DIVERSITY"} and status == "ACTIVE_OK":
            status = "ACTIVE_NEEDS_MORE_FRESH_EVIDENCE"
            risk_level = "LOW"
            action = "Conserver, mais ajouter des exemples avant d’élargir la correction."
            reason = "La correction active n’est pas contredite, mais l’évidence fraîche reste limitée."

    return _proxy_correction_audit_row(
        field=field,
        status=status,
        risk_level=risk_level,
        factor=factor,
        confidence=correction.get("confidence", ""),
        sample_count=correction.get("sample_count", ""),
        last_updated=correction.get("last_updated", ""),
        days_since_update=days_since_update if days_since_update is not None else "",
        bias_status=bias_status,
        bias_confidence=bias_confidence,
        bias_sample_count=bias_sample_count if bias_row else "",
        current_suggested_factor=current_factor if current_factor is not None else "",
        factor_gap=factor_gap,
        max_safe_factor_change=max_change,
        recommended_action=action,
        reason=reason,
    )


def _proxy_correction_audit_row(
    *,
    field: str,
    status: str,
    risk_level: str,
    factor: Any = "",
    confidence: Any = "",
    sample_count: Any = "",
    last_updated: Any = "",
    days_since_update: Any = "",
    bias_status: Any = "",
    bias_confidence: Any = "",
    bias_sample_count: Any = "",
    current_suggested_factor: Any = "",
    factor_gap: Any = "",
    max_safe_factor_change: Any = "",
    recommended_action: str = "",
    reason: str = "",
) -> dict[str, Any]:
    return {
        "field": field,
        "status": status,
        "risk_level": risk_level,
        "factor": factor,
        "confidence": confidence,
        "sample_count": sample_count,
        "last_updated": last_updated,
        "days_since_update": days_since_update,
        "bias_status": bias_status,
        "bias_confidence": bias_confidence,
        "bias_sample_count": bias_sample_count,
        "current_suggested_factor": current_suggested_factor,
        "factor_gap": factor_gap,
        "max_safe_factor_change": max_safe_factor_change,
        "recommended_action": recommended_action,
        "reason": reason,
    }


def _days_since(value: Any, *, as_of: date | None = None) -> int | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        parsed = date.fromisoformat(text[:10])
    except ValueError:
        return None
    return max(0, ((as_of or date.today()) - parsed).days)
