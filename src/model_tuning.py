from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from .utils import CONFIG_DIR, DATA_DIR, clamp, load_yaml, read_csv_records, safe_bool, safe_float, write_csv_records, write_yaml


MODEL_TUNING_VERSION = 1
MODEL_TUNING_PATH = CONFIG_DIR / "model_tuning.yaml"
MODEL_TUNING_HISTORY_PATH = DATA_DIR / "model_tuning_history.csv"

TUNING_HISTORY_COLUMNS = [
    "applied_at",
    "mode",
    "parameter",
    "previous_value",
    "new_value",
    "delta",
    "suggestion_id",
    "safety_level",
    "reason",
]

TUNABLE_PARAMETER_LIMITS = {
    "vfv_adjustment": {"default": 0.0, "min": -0.05, "max": 0.05},
    "defensive_reserve_adjustment": {"default": 0.0, "min": -0.10, "max": 0.10},
    "min_capital_score_adjustment": {"default": 0.0, "min": -5.0, "max": 5.0},
    "cycle_budget_adjustment": {"default": 0.0, "min": -0.10, "max": 0.10},
    "cycle_individual_cap_adjustment": {"default": 0.0, "min": -0.05, "max": 0.05},
    "single_stock_cap_adjustment": {"default": 0.0, "min": -0.10, "max": 0.10},
    "target_weight_adjustment": {"default": 0.0, "min": -0.05, "max": 0.05},
    "quality_drawdown_score_adjustment": {"default": 0.0, "min": -5.0, "max": 5.0},
    "stability_strength_adjustment": {"default": 0.0, "min": -2.0, "max": 2.0},
}

LOCKED_GUARDRAILS = [
    "Ne jamais acheter une thèse BROKEN, WEAKENING ou UNCERTAIN.",
    "Ne jamais renforcer une position ORANGE ou RED.",
    "Ne jamais ignorer la comparaison à VFV.TO.",
    "Ne jamais promouvoir automatiquement une action externe au portefeuille.",
    "Ne jamais transformer un ETF spéculatif, avec levier, crypto ou options en fallback défensif.",
    "Ne jamais supprimer la note de non-conseil financier.",
]


def default_model_tuning() -> dict[str, Any]:
    return {
        "version": MODEL_TUNING_VERSION,
        "description": (
            "Réglages secondaires du modèle. Les règles vitales restent verrouillées dans le code. "
            "Modifier seulement après audit ou avec prudence."
        ),
        "last_updated": "",
        "safe_auto_apply": {
            "enabled": True,
            "min_distinct_allocation_dates": 4,
            "min_days_between_same_parameter_tuning": 45,
            "max_safe_changes_per_run": 3,
            "max_abs_vfv_adjustment_per_run": 0.01,
            "max_abs_score_adjustment_per_run": 1.0,
            "max_abs_pct_adjustment_per_run": 0.02,
        },
        "locked_guardrails": LOCKED_GUARDRAILS,
        "modes": {mode: _default_mode_tuning() for mode in ["balanced", "family-office", "rational-aggressive", "high-cagr"]},
    }


def _default_mode_tuning() -> dict[str, Any]:
    return {
        "vfv_adjustment": 0.0,
        "defensive_reserve_adjustment": 0.0,
        "min_capital_score_adjustment": 0.0,
        "cycle_budget_adjustment": 0.0,
        "cycle_individual_cap_adjustment": 0.0,
        "single_stock_cap_adjustment": 0.0,
        "target_weight_adjustment": 0.0,
        "quality_drawdown_score_adjustment": 0.0,
        "stability_strength_adjustment": 0.0,
    }


def create_model_tuning_template(path: str | Path = MODEL_TUNING_PATH, *, overwrite: bool = False) -> None:
    path = Path(path)
    if path.exists() and not overwrite:
        return
    write_yaml(path, default_model_tuning())


def load_model_tuning(path: str | Path = MODEL_TUNING_PATH) -> dict[str, Any]:
    path = Path(path)
    if not path.exists():
        return default_model_tuning()
    loaded = load_yaml(path)
    if not isinstance(loaded, dict):
        return default_model_tuning()
    return normalize_model_tuning(loaded)


def normalize_model_tuning(tuning: dict[str, Any]) -> dict[str, Any]:
    normalized = default_model_tuning()
    normalized.update({key: value for key, value in tuning.items() if key not in {"modes", "safe_auto_apply", "locked_guardrails"}})
    if isinstance(tuning.get("safe_auto_apply"), dict):
        normalized["safe_auto_apply"].update(tuning.get("safe_auto_apply") or {})
    if isinstance(tuning.get("locked_guardrails"), list):
        normalized["locked_guardrails"] = tuning["locked_guardrails"]
    modes = tuning.get("modes") if isinstance(tuning.get("modes"), dict) else {}
    for mode, defaults in normalized["modes"].items():
        provided = modes.get(mode) if isinstance(modes, dict) else {}
        if isinstance(provided, dict):
            for parameter in TUNABLE_PARAMETER_LIMITS:
                defaults[parameter] = _bounded_parameter(parameter, provided.get(parameter))
    return normalized


def mode_tuning(mode: str, tuning: dict[str, Any] | None = None) -> dict[str, Any]:
    loaded = normalize_model_tuning(tuning or load_model_tuning())
    return dict((loaded.get("modes") or {}).get(str(mode or ""), _default_mode_tuning()))


def tuning_value(mode: str, parameter: str, default: float = 0.0, tuning: dict[str, Any] | None = None) -> float:
    if parameter not in TUNABLE_PARAMETER_LIMITS:
        return default
    value = mode_tuning(mode, tuning).get(parameter)
    if value is None:
        value = default
    return _bounded_parameter(parameter, value)


def apply_tuning_suggestion(
    *,
    mode: str,
    parameter: str,
    delta: float,
    suggestion_id: str,
    safety_level: str,
    reason: str,
    tuning_path: str | Path = MODEL_TUNING_PATH,
    history_path: str | Path = MODEL_TUNING_HISTORY_PATH,
) -> dict[str, Any]:
    if parameter not in TUNABLE_PARAMETER_LIMITS:
        raise ValueError(f"Paramètre non ajustable: {parameter}")
    tuning_path = Path(tuning_path)
    history_path = Path(history_path)
    tuning = load_model_tuning(tuning_path)
    modes = tuning.setdefault("modes", {})
    mode_row = modes.setdefault(mode, _default_mode_tuning())
    previous = _bounded_parameter(parameter, mode_row.get(parameter))
    new_value = _bounded_parameter(parameter, previous + delta)
    mode_row[parameter] = new_value
    tuning["last_updated"] = datetime.now().isoformat(timespec="seconds")
    write_yaml(tuning_path, tuning)

    record = {
        "applied_at": datetime.now().isoformat(timespec="seconds"),
        "mode": mode,
        "parameter": parameter,
        "previous_value": previous,
        "new_value": new_value,
        "delta": round(new_value - previous, 6),
        "suggestion_id": suggestion_id,
        "safety_level": safety_level,
        "reason": reason,
    }
    history = read_csv_records(history_path)
    history.append(record)
    write_csv_records(history_path, history, TUNING_HISTORY_COLUMNS)
    return record


def can_auto_apply_value(value: Any) -> bool:
    bool_value = safe_bool(value)
    if bool_value is not None:
        return bool_value
    return str(value or "").strip().upper() in {"TRUE", "YES", "OUI", "1"}


def _bounded_parameter(parameter: str, value: Any) -> float:
    limits = TUNABLE_PARAMETER_LIMITS[parameter]
    numeric = safe_float(value)
    if numeric is None:
        numeric = safe_float(limits.get("default")) or 0.0
    return round(clamp(numeric, safe_float(limits.get("min")) or 0.0, safe_float(limits.get("max")) or 0.0), 6)
