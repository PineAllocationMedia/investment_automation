from __future__ import annotations

from collections import Counter
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

from .baseline_identity import VALIDATION_BASELINE_ID, combined_baseline_snapshot_authority
from .mode_artifacts import write_csv_records_mode_pair, write_text_mode_pair
from .model_version import MODEL_RULES_VERSION
from .model_identity import MODEL_LINEAGE, evidence_cohort, matches_current_cohort
from .utils import DISCLAIMER, load_json, markdown_to_html, pct, safe_float, today_iso
from .validation_evidence import (
    RunPurpose,
    VALIDATION_SCHEMA_VERSION,
    evidence_maturity,
    purpose_is_genuine_decision,
    snapshot_run_purpose,
    EvidenceClass,
    walk_forward_period_has_strategy_validation_authority,
)


MODEL_AUDIT_COLUMNS = [
    "section",
    "metric",
    "status",
    "value",
    "interpretation",
    "impact",
]


def run_model_audit(
    reports_dir: str | Path,
    period: str = "12m",
    mode: str | None = None,
    current_model_rules_version: str | None = None,
    current_model_lineage: str = MODEL_LINEAGE,
) -> dict[str, Any]:
    reports_dir = Path(reports_dir)
    audit = build_model_audit(
        reports_dir,
        period,
        mode=mode,
        current_model_rules_version=current_model_rules_version,
        current_model_lineage=current_model_lineage,
    )
    write_model_audit_outputs(reports_dir, audit)
    return audit


def build_model_audit(
    reports_dir: str | Path,
    period: str = "12m",
    mode: str | None = None,
    current_model_rules_version: str | None = None,
    current_model_lineage: str = MODEL_LINEAGE,
) -> dict[str, Any]:
    reports_dir = Path(reports_dir)
    history_dir = reports_dir / "history"
    period_days = _period_to_days(period)
    normalized_mode = _normalize_mode(mode)
    allocation_records, raw_allocation_count = _load_daily_records(
        history_dir,
        "allocation_*.json",
        payload_key="allocations",
        period_days=period_days,
        fallback_path=_latest_snapshot_path(reports_dir, "allocation", normalized_mode),
        mode=normalized_mode,
    )
    analysis_records, raw_analysis_count = _load_daily_records(
        history_dir,
        "analysis_*.json",
        payload_key="analyses",
        period_days=period_days,
        fallback_path=_latest_snapshot_path(reports_dir, "analysis", normalized_mode),
        mode=normalized_mode,
    )

    record_keys = sorted(set(allocation_records) | set(analysis_records))
    samples = [
        _audit_sample(
            sample_date=record_key[0],
            run_purpose=record_key[2],
            allocation_record=allocation_records.get(record_key, {}),
            analysis_record=analysis_records.get(record_key, {}),
        )
        for record_key in record_keys
    ]
    samples = [sample for sample in samples if sample["allocation_map"] or sample["analyses_by_ticker"]]
    samples.sort(
        key=lambda sample: (
            str(sample.get("date") or ""),
            str(sample.get("created_at") or ""),
            str(sample.get("model_rules_version") or ""),
            str(sample.get("run_purpose") or ""),
        )
    )

    current_version = str(current_model_rules_version or MODEL_RULES_VERSION)
    current_version_samples = [
        sample for sample in samples if matches_current_cohort(sample, lineage=current_model_lineage, rules_version=current_version)
    ]
    current_decision_samples = [
        sample for sample in current_version_samples if purpose_is_genuine_decision(sample.get("run_purpose"))
        and sample.get("strategy_validation_authority") is True
    ]
    metrics = _audit_metrics(
        current_decision_samples,
        raw_allocation_count,
        raw_analysis_count,
        period,
        period_days,
        normalized_mode,
        total_samples=samples,
        current_model_rules_version=current_version,
        current_model_lineage=current_model_lineage,
    )
    rows = _audit_rows(metrics)
    markdown = _audit_markdown(metrics, rows)
    return {
        "period": period,
        "mode": normalized_mode,
        "period_days": period_days,
        "metrics": metrics,
        "rows": rows,
        "markdown": markdown,
    }


def write_model_audit_outputs(reports_dir: str | Path, audit: dict[str, Any]) -> None:
    reports_dir = Path(reports_dir)
    markdown = str(audit.get("markdown") or "")
    mode = str(audit.get("mode") or "")
    write_text_mode_pair(reports_dir, "latest_model_audit.md", mode, markdown)
    write_text_mode_pair(reports_dir, "latest_model_audit.html", mode, markdown_to_html(markdown))
    write_csv_records_mode_pair(reports_dir, "latest_model_audit.csv", mode, audit.get("rows") or [], MODEL_AUDIT_COLUMNS)


def _load_daily_records(
    history_dir: Path,
    pattern: str,
    payload_key: str,
    period_days: int | None,
    fallback_path: Path,
    mode: str | None = None,
) -> tuple[dict[tuple[str, ...], dict[str, Any]], int]:
    records: list[dict[str, Any]] = []
    if history_dir.exists():
        for path in history_dir.glob(pattern):
            payload = load_json(path)
            rows = payload.get(payload_key) if isinstance(payload, dict) else None
            if not isinstance(rows, list) or not rows:
                continue
            if mode is not None and not _payload_mode_matches(payload, mode):
                continue
            sample_date = _payload_date(payload, path)
            if not sample_date or not _within_period(sample_date, period_days):
                continue
            records.append(
                {
                    "path": str(path),
                    "analysis_date": sample_date,
                    "created_at": str(payload.get("created_at") or path.stem),
                    "model_rules_version": str(payload.get("model_rules_version") or ""),
                    "analysis_mode": _normalize_mode(payload.get("analysis_mode")),
                    "run_purpose": snapshot_run_purpose(payload),
                    "rows": rows,
                    "payload": payload,
                }
            )
    raw_count = len(records)

    if not records:
        payload = load_json(fallback_path)
        rows = payload.get(payload_key) if isinstance(payload, dict) else None
        sample_date = _payload_date(payload, fallback_path)
        if (
            isinstance(rows, list)
            and rows
            and sample_date
            and _within_period(sample_date, period_days)
            and (mode is None or _payload_mode_matches(payload, mode))
        ):
            records.append(
                {
                    "path": str(fallback_path),
                    "analysis_date": sample_date,
                    "created_at": str(payload.get("created_at") or fallback_path.stem),
                    "model_rules_version": str(payload.get("model_rules_version") or ""),
                    "analysis_mode": _normalize_mode(payload.get("analysis_mode")),
                    "run_purpose": snapshot_run_purpose(payload),
                    "rows": rows,
                    "payload": payload,
                }
            )
            raw_count = 1

    records.sort(key=lambda row: (str(row.get("analysis_date")), str(row.get("created_at"))))
    latest_by_date_version_and_purpose: dict[tuple[str, ...], dict[str, Any]] = {}
    for record in records:
        key = (
            str(record["analysis_date"]),
            str(record.get("model_rules_version") or "UNKNOWN"),
            str(record.get("run_purpose") or RunPurpose.UNKNOWN_LEGACY.value),
            *evidence_cohort(record.get("payload") or {}),
            str(record.get("analysis_mode") or ""),
        )
        latest_by_date_version_and_purpose[key] = record
    return latest_by_date_version_and_purpose, raw_count


def _audit_sample(
    sample_date: str,
    run_purpose: str,
    allocation_record: dict[str, Any],
    analysis_record: dict[str, Any],
) -> dict[str, Any]:
    allocation_rows = allocation_record.get("rows") or []
    analysis_rows = analysis_record.get("rows") or []
    allocation_map = _allocation_map(allocation_rows)
    analyses_by_ticker = {
        str(row.get("ticker") or "").upper(): row
        for row in analysis_rows
        if str(row.get("ticker") or "").strip()
    }
    baseline_metadata = _combined_baseline_authority(allocation_record, analysis_record, run_purpose)
    available = [r["payload"] for r in (allocation_record, analysis_record) if isinstance(r.get("payload"), dict)]
    if len(available) == 1:
        baseline_metadata["strategy_validation_authority"] = walk_forward_period_has_strategy_validation_authority({
            **available[0], "evidence_class": available[0].get("evidence_class") or EvidenceClass.POINT_IN_TIME_WALK_FORWARD.value,
        })
    return {
        "date": sample_date,
        "created_at": max(
            str(allocation_record.get("created_at") or ""),
            str(analysis_record.get("created_at") or ""),
        ),
        "run_purpose": run_purpose,
        "allocation_map": allocation_map,
        "analyses_by_ticker": analyses_by_ticker,
        "decision_quality": (allocation_record.get("payload") or {}).get("decision_quality", {}),
        "model_rules_version": allocation_record.get("model_rules_version") or analysis_record.get("model_rules_version") or "",
        **baseline_metadata,
    }


def _combined_baseline_authority(
    allocation_record: dict[str, Any],
    analysis_record: dict[str, Any],
    run_purpose: str,
) -> dict[str, Any]:
    payloads = [
        record.get("payload")
        for record in (allocation_record, analysis_record)
        if isinstance(record.get("payload"), dict)
    ]
    return combined_baseline_snapshot_authority(payloads, run_purpose=run_purpose)


def _audit_metrics(
    samples: list[dict[str, Any]],
    raw_allocation_count: int,
    raw_analysis_count: int,
    period: str,
    period_days: int | None,
    mode: str | None = None,
    *,
    total_samples: list[dict[str, Any]] | None = None,
    current_model_rules_version: str = "",
    current_model_lineage: str = MODEL_LINEAGE,
) -> dict[str, Any]:
    total_samples = list(total_samples if total_samples is not None else samples)
    sample_count = len(samples)
    allocation_samples = [sample for sample in samples if sample.get("allocation_map")]
    allocation_sample_count = len(allocation_samples)
    dates = [str(sample["date"]) for sample in samples]
    span_days = _span_days(dates)
    raw_count = max(raw_allocation_count, raw_analysis_count)
    same_day_collapsed = max(0, raw_count - len(total_samples))
    versions = Counter(str(sample.get("model_rules_version") or "UNKNOWN") for sample in total_samples)
    decision_samples = [sample for sample in total_samples if purpose_is_genuine_decision(sample.get("run_purpose"))]
    decision_versions = Counter(str(sample.get("model_rules_version") or "UNKNOWN") for sample in decision_samples)
    current_version_samples = [
        sample
        for sample in total_samples
        if matches_current_cohort(sample, lineage=current_model_lineage, rules_version=current_model_rules_version)
    ]
    baseline_forward_samples = [
        sample
        for sample in current_version_samples
        if sample.get("baseline_forward_eligible") is True
        and str(sample.get("baseline_id") or "") == VALIDATION_BASELINE_ID
    ]
    current_version_unknown_samples = [
        sample
        for sample in current_version_samples
        if str(sample.get("run_purpose") or "") == RunPurpose.UNKNOWN_LEGACY.value
    ]
    current_version_non_decision_samples = [
        sample
        for sample in current_version_samples
        if not purpose_is_genuine_decision(sample.get("run_purpose"))
        and str(sample.get("run_purpose") or "") != RunPurpose.UNKNOWN_LEGACY.value
    ]
    cross_version_samples = [
        sample
        for sample in total_samples
        if str(sample.get("model_rules_version") or "") != current_model_rules_version
    ]
    cross_version_decision_samples = [
        sample for sample in cross_version_samples if purpose_is_genuine_decision(sample.get("run_purpose"))
    ]
    cross_version_observation_count = len(cross_version_samples)
    unknown_version_observation_count = sum(
        1 for sample in total_samples if not str(sample.get("model_rules_version") or "").strip()
    )
    version_sequence = [str(sample.get("model_rules_version") or "UNKNOWN") for sample in decision_samples]
    version_transition_count = sum(1 for before, after in zip(version_sequence, version_sequence[1:]) if before != after)

    primary_tickers = [_primary_core_ticker(sample.get("allocation_map") or {}) for sample in allocation_samples]
    primary_changes = _change_count(primary_tickers)
    transitions = max(0, allocation_sample_count - 1)
    primary_change_rate = primary_changes / transitions if transitions else 0.0
    turnover_values = _allocation_turnovers(allocation_samples)
    avg_turnover = _average(turnover_values) or 0.0
    max_turnover = max(turnover_values) if turnover_values else 0.0

    vfv_values = [_ticker_pct(sample.get("allocation_map") or {}, "VFV.TO") for sample in allocation_samples]
    vfv_values = [value for value in vfv_values if value is not None]
    avg_vfv = _average(vfv_values) or 0.0
    min_vfv = min(vfv_values) if vfv_values else 0.0
    max_vfv = max(vfv_values) if vfv_values else 0.0
    vfv_range = max_vfv - min_vfv if vfv_values else 0.0
    avg_core = _average([_core_allocation_pct(sample.get("allocation_map") or {}) for sample in allocation_samples]) or 0.0

    max_single_values = [_max_single_core_pct(sample.get("allocation_map") or {}) for sample in allocation_samples]
    avg_max_single = _average(max_single_values) or 0.0
    avg_allocated_core_count = _average([_allocated_core_count(sample.get("allocation_map") or {}) for sample in allocation_samples]) or 0.0
    unique_recommended = sorted({ticker for ticker in primary_tickers if ticker})

    decision_scores = [
        safe_float((sample.get("decision_quality") or {}).get("decision_quality_score"))
        for sample in samples
    ]
    decision_scores = [value for value in decision_scores if value is not None]
    avg_decision_quality = _average(decision_scores)
    dq_levels = Counter(str((sample.get("decision_quality") or {}).get("decision_quality_level") or "") for sample in samples)

    allocated_risk = [_allocated_risk_snapshot(sample) for sample in allocation_samples]
    high_cycle_day_rate = _rate(item["has_high_cycle"] for item in allocated_risk)
    extreme_cycle_day_rate = _rate(item["has_extreme_cycle"] for item in allocated_risk)
    low_data_day_rate = _rate(item["has_low_data"] for item in allocated_risk)
    concentration_day_rate = _rate((item["max_single"] or 0.0) >= 0.50 for item in allocated_risk)

    confidence = _confidence_status(allocation_sample_count or sample_count, span_days)
    health_score = _model_health_score(
        sample_count=allocation_sample_count,
        primary_change_rate=primary_change_rate,
        avg_turnover=avg_turnover,
        avg_vfv=avg_vfv,
        vfv_range=vfv_range,
        avg_core=avg_core,
        avg_decision_quality=avg_decision_quality,
        high_cycle_day_rate=high_cycle_day_rate,
        extreme_cycle_day_rate=extreme_cycle_day_rate,
        avg_max_single=avg_max_single,
    )
    health_status = _health_status(
        sample_count=allocation_sample_count,
        health_score=health_score,
        confidence=confidence,
        primary_change_rate=primary_change_rate,
        avg_turnover=avg_turnover,
        avg_vfv=avg_vfv,
        avg_core=avg_core,
        avg_max_single=avg_max_single,
    )

    metrics = {
        "period": period,
        "mode": mode,
        "period_days": period_days,
        "dates": dates,
        "sample_count": sample_count,
        "allocation_sample_count": allocation_sample_count,
        "raw_snapshot_count": raw_count,
        "same_day_collapsed_count": same_day_collapsed,
        "span_days": span_days,
        "model_versions": dict(versions),
        "decision_model_versions": dict(decision_versions),
        "audit_scope": "CURRENT_VERSION_AUDIT",
        "current_model_rules_version": current_model_rules_version,
        "current_model_lineage": current_model_lineage,
        "validation_schema_version": VALIDATION_SCHEMA_VERSION,
        "validation_authority": "PRODUCTION" if current_model_lineage == "V1" else "NONE",
        "total_history_observation_count": len(total_samples),
        "current_version_total_observation_count": len(current_version_samples),
        "current_version_decision_observation_count": sample_count,
        "current_version_non_decision_observation_count": len(current_version_non_decision_samples),
        "current_version_unknown_purpose_observation_count": len(current_version_unknown_samples),
        "cross_version_decision_observation_count": len(cross_version_decision_samples),
        "current_version_observation_count": sample_count,
        "baseline_id": VALIDATION_BASELINE_ID if current_model_lineage == "V1" else "",
        "baseline_forward_observation_count": len(baseline_forward_samples),
        "baseline_forward_periods": len(baseline_forward_samples),
        "baseline_evidence_maturity": evidence_maturity(len(baseline_forward_samples)),
        "cross_version_observation_count": cross_version_observation_count,
        "unknown_version_observation_count": unknown_version_observation_count,
        "version_transition_count": version_transition_count,
        "cross_version_diagnostic": {
            "scope": "CROSS_VERSION_DIAGNOSTIC",
            "model_versions": dict(decision_versions),
            "all_observation_model_versions": dict(versions),
            "observation_count": len(total_samples),
            "decision_observation_count": len(decision_samples),
            "cross_version_decision_observation_count": len(cross_version_decision_samples),
            "version_transition_count": version_transition_count,
            "ordinary_instability_counted": False,
        },
        "evidence_maturity": evidence_maturity(allocation_sample_count or sample_count),
        "confidence": confidence,
        "health_status": health_status,
        "health_score": health_score,
        "primary_tickers": primary_tickers,
        "unique_recommended": unique_recommended,
        "primary_changes": primary_changes,
        "primary_change_rate": primary_change_rate,
        "avg_allocation_turnover": avg_turnover,
        "max_allocation_turnover": max_turnover,
        "avg_vfv": avg_vfv,
        "min_vfv": min_vfv,
        "max_vfv": max_vfv,
        "vfv_range": vfv_range,
        "avg_core": avg_core,
        "avg_max_single": avg_max_single,
        "avg_allocated_core_count": avg_allocated_core_count,
        "avg_decision_quality": avg_decision_quality,
        "decision_quality_levels": dict(dq_levels),
        "high_cycle_day_rate": high_cycle_day_rate,
        "extreme_cycle_day_rate": extreme_cycle_day_rate,
        "low_data_day_rate": low_data_day_rate,
        "concentration_day_rate": concentration_day_rate,
        "recommendation": _audit_recommendation(health_status, confidence, allocation_sample_count or sample_count),
    }
    metrics["threshold_review"] = _threshold_review(metrics)
    return metrics


def _audit_rows(metrics: dict[str, Any]) -> list[dict[str, Any]]:
    threshold_review = metrics.get("threshold_review") or {}
    rows = [
        _row(
            "Portée",
            "Évidence forward Baseline V1",
            metrics.get("baseline_evidence_maturity", "INSUFFICIENT"),
            f"{metrics.get('baseline_forward_observation_count', 0)} observation(s)",
            (
                f"{metrics.get('baseline_id')}: seules les décisions post-déploiement explicitement admissibles "
                "comptent dans cette maturité."
            ),
            "Le contexte P2/OOS historique reste distinct et inchangé.",
        ),
        _row(
            "Portée",
            "Audit de version courant",
            metrics.get("audit_scope", "CURRENT_VERSION_AUDIT"),
            (
                f"{metrics.get('current_version_decision_observation_count', 0)} décision(s) comparable(s) sur "
                f"{metrics.get('current_version_total_observation_count', 0)} observation(s) de version courante"
            ),
            (
                f"Version courante: {metrics.get('current_model_rules_version')}; maturité: {metrics.get('evidence_maturity')}; "
                f"hors décision: {metrics.get('current_version_non_decision_observation_count', 0)}; "
                f"but inconnu: {metrics.get('current_version_unknown_purpose_observation_count', 0)}."
            ),
            "Les métriques primaires utilisent seulement les décisions scheduled/manual de la version courante.",
        ),
        _row(
            "Portée",
            "Diagnostic inter-versions",
            "CROSS_VERSION_DIAGNOSTIC",
            (
                f"{metrics.get('cross_version_decision_observation_count', 0)} décision(s) hors version courante; "
                f"{metrics.get('version_transition_count', 0)} transition(s)"
            ),
            "Les versions antérieures restent visibles, mais leurs transitions ne comptent pas comme instabilité interne.",
            "Préserve l'historique sans créer une fausse métrique homogène.",
        ),
        _row(
            "Résumé",
            "Santé du modèle",
            metrics["health_status"],
            f"{metrics['health_score']:.0f}/100",
            _health_interpretation(metrics["health_status"]),
            "Indique si la mécanique récente semble saine, trop volatile, trop défensive ou trop concentrée.",
        ),
        _row(
            "Résumé",
            "Confiance de l’audit",
            metrics["confidence"],
            f"{metrics['sample_count']} date(s) distincte(s), {metrics['allocation_sample_count']} avec allocation, {metrics['span_days']} jour(s) de recul",
            _confidence_interpretation(metrics["confidence"]),
            "Plus il y a de dates distinctes espacées dans le temps, plus l’audit est représentatif.",
        ),
        _row(
            "Revue des seuils",
            "Diagnostic de calibration",
            threshold_review.get("status", "N/D"),
            threshold_review.get("summary_value", ""),
            threshold_review.get("interpretation", ""),
            "Suggestion seulement: l’agent ne modifie jamais automatiquement ses règles ou seuils.",
        ),
        _row(
            "Mémoire",
            "Analyses intra-journée regroupées",
            "OK",
            str(metrics["same_day_collapsed_count"]),
            "Plusieurs observations du même but/version le même jour comptent comme une seule référence.",
            "Un diagnostic ne peut pas remplacer une décision du même jour; chaque but reste séparément auditable.",
        ),
        _row(
            "Stabilité",
            "Changement du titre principal",
            _rate_status(metrics["primary_change_rate"], 0.35, 0.65, inverse=True),
            pct(metrics["primary_change_rate"]),
            f"{metrics['primary_changes']} changement(s) du principal titre recommandé.",
            "Un peu de variation est sain; trop de rotation peut signaler une recommandation trop sensible.",
        ),
        _row(
            "Stabilité",
            "Rotation moyenne de l’allocation",
            _rate_status(metrics["avg_allocation_turnover"], 0.20, 0.45, inverse=True),
            pct(metrics["avg_allocation_turnover"]),
            "Mesure la part moyenne de cotisation qui change de destination entre deux dates.",
            "Aide à détecter une recommandation qui bouge trop sans vraie raison long terme.",
        ),
        _row(
            "VFV",
            "Part moyenne VFV",
            _vfv_level(metrics["avg_vfv"]),
            pct(metrics["avg_vfv"]),
            f"Fourchette observée: {pct(metrics['min_vfv'])} à {pct(metrics['max_vfv'])}.",
            "VFV doit servir de filet; une part durablement trop élevée peut devenir trop défensive pour ton profil.",
        ),
        _row(
            "VFV",
            "Volatilité VFV",
            _rate_status(metrics["vfv_range"], 0.10, 0.25, inverse=True),
            pct(metrics["vfv_range"]),
            "Variation entre la plus petite et la plus grande part VFV observée.",
            "Permet de voir si VFV monte pour une raison ponctuelle ou si la règle est trop nerveuse.",
        ),
        _row(
            "Profil",
            "Exposition core moyenne",
            _rate_status(metrics["avg_core"], 0.65, 0.80),
            pct(metrics["avg_core"]),
            f"Nombre moyen de titres core financés: {metrics['avg_allocated_core_count']:.1f}.",
            "Mesure si la cotisation va surtout vers des compounders potentiels plutôt que vers le filet VFV.",
        ),
        _row(
            "Profil",
            "Qualité moyenne de la recommandation",
            _score_status(metrics["avg_decision_quality"]),
            "N/D" if metrics["avg_decision_quality"] is None else f"{metrics['avg_decision_quality']:.1f}/100",
            "Moyenne du score de qualité déjà calculé par l’agent après chaque analyse.",
            "Confirme si les recommandations passées étaient robustes, pas seulement offensives.",
        ),
        _row(
            "Risque",
            "Concentration du plus gros bloc",
            _rate_status(metrics["avg_max_single"], 0.35, 0.55, inverse=True),
            pct(metrics["avg_max_single"]),
            "Part moyenne du plus gros titre individuel dans la cotisation.",
            "Un gros bloc est acceptable pour high CAGR, mais l’audit surveille l’excès répété.",
        ),
        _row(
            "Risque",
            "Exposition aux cycles/bulles sur titres financés",
            _rate_status(metrics["high_cycle_day_rate"], 0.25, 0.50, inverse=True),
            pct(metrics["high_cycle_day_rate"]),
            f"Risque extrême observé sur {pct(metrics['extreme_cycle_day_rate'])} des dates.",
            "Vérifie si le modèle devient trop dépendant d’un thème chaud ou cyclique.",
        ),
        _row(
            "Données",
            "Titres financés avec données faibles",
            _rate_status(metrics["low_data_day_rate"], 0.10, 0.25, inverse=True),
            pct(metrics["low_data_day_rate"]),
            "Part des dates où au moins un titre financé avait une qualité de données faible.",
            "Aide à savoir si les recommandations reposent trop sur des angles morts.",
        ),
    ]
    rows.extend(threshold_review.get("rows") or [])
    return rows


def _audit_markdown(metrics: dict[str, Any], rows: list[dict[str, Any]]) -> str:
    dates = metrics.get("dates") or []
    date_text = ", ".join(dates[-6:]) if dates else "aucune"
    recommended = ", ".join(metrics.get("unique_recommended") or []) or "aucun titre core financé"
    version_text = ", ".join(f"{version} ({count})" for version, count in (metrics.get("model_versions") or {}).items()) or "N/D"
    mode_text = metrics.get("mode") or "tous les modes"
    threshold_review = metrics.get("threshold_review") or {}
    threshold_rows = [row for row in rows if row.get("section") == "Revue des seuils"]
    audit_rows = [row for row in rows if row.get("section") != "Revue des seuils"]
    lines = [
        "# Audit du modèle d’allocation",
        "",
        f"- Date de création: {today_iso()}",
        f"- Période demandée: {metrics.get('period')}",
        f"- Mode analysé: {mode_text}",
        f"- Historique primaire utilisé: {metrics.get('sample_count')} décision(s) comparable(s) sur {metrics.get('span_days')} jour(s)",
        f"- Évidence {metrics.get('baseline_id')}: {metrics.get('baseline_forward_observation_count', 0)} observation(s); maturité {metrics.get('baseline_evidence_maturity')}",
        f"- Dates avec allocation exploitable: {metrics.get('allocation_sample_count')}",
        f"- Dates récentes incluses: {date_text}",
        f"- Observations du même but/version le même jour regroupées: {metrics.get('same_day_collapsed_count')}",
        f"- Versions de règles observées: {version_text}",
        f"- Portée primaire: CURRENT_VERSION_AUDIT `{metrics.get('current_model_rules_version')}` ({metrics.get('current_version_decision_observation_count')} décision(s) scheduled/manual)",
        f"- Contexte de version courante: {metrics.get('current_version_total_observation_count')} observation(s), dont {metrics.get('current_version_non_decision_observation_count')} hors décision et {metrics.get('current_version_unknown_purpose_observation_count')} au but inconnu",
        f"- Diagnostic séparé: CROSS_VERSION_DIAGNOSTIC ({metrics.get('cross_version_decision_observation_count')} décision(s) hors version; {metrics.get('version_transition_count')} transition(s) entre décisions comparables)",
        f"- Maturité des preuves comparables: {metrics.get('evidence_maturity')} (décrit le recul, pas un skill prouvé)",
        "",
        f"> {DISCLAIMER}",
        "",
        "## Résumé",
        "",
        f"- Santé du modèle: **{metrics.get('health_status')}** ({metrics.get('health_score'):.0f}/100)",
        f"- Confiance de l’audit: **{metrics.get('confidence')}**",
        f"- Revue des seuils: **{threshold_review.get('status', 'N/D')}**",
        f"- Titres principaux recommandés au moins une fois: {recommended}",
        f"- Conclusion: {metrics.get('recommendation')}",
        "",
        "## Revue des seuils",
        "",
        "- Cette section ne modifie pas les règles. Elle indique seulement quels seuils mériteraient une revue manuelle si la tendance se répète.",
        "",
        _markdown_table(threshold_rows, MODEL_AUDIT_COLUMNS),
        "",
        "## Tableau d’audit",
        "",
        _markdown_table(audit_rows, MODEL_AUDIT_COLUMNS),
        "",
        "## Comment l’interpréter",
        "",
        "- Cet audit ne choisit pas l’allocation du mois. Il vérifie si le moteur reste sain dans le temps.",
        "- Quand un mode est indiqué, l’audit ignore les analyses faites avec les autres modes.",
        "- Les observations de même but et version faites plusieurs fois dans la même journée sont regroupées; un diagnostic ne remplace jamais une décision du même jour.",
        "- Les métriques de stabilité primaires utilisent seulement SCHEDULED_DECISION et MANUAL_DECISION sous le MODEL_RULES_VERSION courant.",
        "- Les diagnostics, tests, analyses zéro-capital, maintenances et buts legacy inconnus restent visibles sans augmenter la maturité primaire.",
        "- Avant 4 dates distinctes, les conclusions sont surtout préliminaires. Elles deviennent plus utiles après plusieurs mois de cotisations réelles.",
        "- Une certaine variation est normale: le but n’est pas de figer les mêmes titres, mais d’éviter les changements causés seulement par du bruit de marché.",
        "",
        "## Limites",
        "",
        "- L’audit mesure la cohérence mécanique du modèle, pas la performance future garantie.",
        "- Si la version courante a peu d'historique, la confiance reste faible; les versions antérieures ne sont jamais mélangées pour la gonfler.",
        "- Les résultats dépendent des données gratuites, des tickers, des rapports ajoutés et de la qualité du portefeuille saisi.",
        "",
    ]
    return "\n".join(lines)


def _allocation_map(rows: list[dict[str, Any]]) -> dict[str, dict[str, float]]:
    output: dict[str, dict[str, float]] = {}
    for row in rows:
        ticker = str(row.get("ticker") or row.get("destination") or "").strip().upper()
        if not ticker:
            continue
        amount = safe_float(row.get("amount"))
        if amount is None:
            amount = safe_float(row.get("montant"))
        amount = amount or 0.0
        percentage = safe_float(row.get("percentage"))
        if percentage is None:
            percentage = safe_float(row.get("pourcentage"))
        if percentage is None:
            percentage = 0.0
        if percentage > 1.5:
            percentage = percentage / 100.0
        bucket = output.setdefault(ticker, {"amount": 0.0, "percentage": 0.0})
        bucket["amount"] += amount
        bucket["percentage"] += percentage
    total_pct = sum(row["percentage"] for row in output.values())
    total_amount = sum(row["amount"] for row in output.values())
    if total_pct <= 0 and total_amount > 0:
        for row in output.values():
            row["percentage"] = row["amount"] / total_amount
    return output


def _allocated_risk_snapshot(sample: dict[str, Any]) -> dict[str, Any]:
    allocations = sample.get("allocation_map") or {}
    analyses = sample.get("analyses_by_ticker") or {}
    allocated_core = [ticker for ticker, row in allocations.items() if ticker != "VFV.TO" and (row.get("percentage") or 0.0) > 0]
    cycle_levels = [str((analyses.get(ticker) or {}).get("cycle_bubble_risk_level") or "") for ticker in allocated_core]
    data_levels = [str((analyses.get(ticker) or {}).get("data_quality") or "") for ticker in allocated_core]
    return {
        "has_high_cycle": any(level in {"HIGH", "EXTREME"} for level in cycle_levels),
        "has_extreme_cycle": any(level == "EXTREME" for level in cycle_levels),
        "has_low_data": any(level == "LOW" for level in data_levels),
        "max_single": _max_single_core_pct(allocations),
    }


def _period_to_days(period: str) -> int | None:
    text = str(period or "12m").strip().lower()
    if text in {"all", "tout"}:
        return None
    try:
        if text.endswith("d"):
            return max(1, int(text[:-1]))
        if text.endswith("m"):
            return max(1, int(round(float(text[:-1]) * 30.4375)))
        if text.endswith("y"):
            return max(1, int(round(float(text[:-1]) * 365.25)))
        return max(1, int(text))
    except ValueError:
        return 365


def _within_period(sample_date: str, period_days: int | None) -> bool:
    if period_days is None:
        return True
    parsed = _date_from_text(sample_date)
    if parsed is None:
        return True
    return parsed >= date.today() - timedelta(days=period_days)


def _latest_snapshot_path(reports_dir: Path, snapshot_type: str, mode: str | None) -> Path:
    normalized_mode = _normalize_mode(mode)
    if snapshot_type == "allocation":
        if normalized_mode:
            return reports_dir / f"latest_allocation_snapshot_{_mode_slug(normalized_mode)}.json"
        return reports_dir / "latest_allocation_snapshot.json"
    if normalized_mode:
        return reports_dir / f"latest_analysis_snapshot_{_mode_slug(normalized_mode)}.json"
    return reports_dir / "latest_analysis_snapshot.json"


def _payload_mode_matches(payload: Any, mode: str | None) -> bool:
    expected = _normalize_mode(mode)
    if expected is None:
        return True
    if not isinstance(payload, dict):
        return False
    return _normalize_mode(payload.get("analysis_mode")) == expected


def _normalize_mode(value: Any) -> str | None:
    text = str(value or "").strip().lower()
    return text or None


def _mode_slug(value: Any) -> str:
    text = _normalize_mode(value) or "unknown"
    return "".join(char if char.isalnum() or char in {"-", "_"} else "-" for char in text)


def _payload_date(payload: Any, path: Path) -> str:
    if isinstance(payload, dict):
        analysis_date = str(payload.get("analysis_date") or "").strip()
        if analysis_date:
            return analysis_date[:10]
        created_at = str(payload.get("created_at") or "").strip()
        if created_at:
            return created_at[:10]
    stem = path.stem
    for prefix in ["analysis_", "allocation_"]:
        if stem.startswith(prefix) and len(stem) >= len(prefix) + 8:
            raw = stem.removeprefix(prefix)[:8]
            if raw.isdigit():
                return f"{raw[:4]}-{raw[4:6]}-{raw[6:8]}"
    return ""


def _date_from_text(value: str) -> date | None:
    try:
        return datetime.fromisoformat(str(value)[:10]).date()
    except ValueError:
        return None


def _span_days(dates: list[str]) -> int:
    parsed = [_date_from_text(value) for value in dates]
    parsed = [value for value in parsed if value is not None]
    if len(parsed) < 2:
        return 0
    return (max(parsed) - min(parsed)).days


def _primary_core_ticker(allocation_map: dict[str, dict[str, float]]) -> str:
    candidates = [
        (row.get("percentage") or 0.0, row.get("amount") or 0.0, ticker)
        for ticker, row in allocation_map.items()
        if ticker != "VFV.TO" and ((row.get("percentage") or 0.0) > 0 or (row.get("amount") or 0.0) > 0)
    ]
    if not candidates:
        return ""
    return max(candidates)[2]


def _ticker_pct(allocation_map: dict[str, dict[str, float]], ticker: str) -> float | None:
    row = allocation_map.get(ticker)
    if not row:
        return 0.0
    return safe_float(row.get("percentage")) or 0.0


def _core_allocation_pct(allocation_map: dict[str, dict[str, float]]) -> float:
    return sum((row.get("percentage") or 0.0) for ticker, row in allocation_map.items() if ticker != "VFV.TO")


def _max_single_core_pct(allocation_map: dict[str, dict[str, float]]) -> float:
    values = [(row.get("percentage") or 0.0) for ticker, row in allocation_map.items() if ticker != "VFV.TO"]
    return max(values) if values else 0.0


def _allocated_core_count(allocation_map: dict[str, dict[str, float]]) -> int:
    return sum(1 for ticker, row in allocation_map.items() if ticker != "VFV.TO" and (row.get("percentage") or 0.0) > 0)


def _change_count(values: list[str]) -> int:
    changes = 0
    previous: str | None = None
    for value in values:
        if previous is not None and value != previous:
            changes += 1
        previous = value
    return changes


def _allocation_turnovers(samples: list[dict[str, Any]]) -> list[float]:
    turnovers = []
    for previous, current in zip(samples, samples[1:]):
        previous_map = previous.get("allocation_map") or {}
        current_map = current.get("allocation_map") or {}
        tickers = set(previous_map) | set(current_map)
        turnover = 0.5 * sum(
            abs((current_map.get(ticker, {}).get("percentage") or 0.0) - (previous_map.get(ticker, {}).get("percentage") or 0.0))
            for ticker in tickers
        )
        turnovers.append(round(turnover, 4))
    return turnovers


def _average(values: list[float | None]) -> float | None:
    numbers = [value for value in values if value is not None]
    if not numbers:
        return None
    return sum(numbers) / len(numbers)


def _rate(values: Any) -> float:
    items = [bool(value) for value in values]
    if not items:
        return 0.0
    return sum(1 for value in items if value) / len(items)


def _confidence_status(sample_count: int, span_days: int) -> str:
    if sample_count <= 1:
        return "VERY_LIMITED"
    if sample_count <= 3:
        return "PRELIMINARY"
    if sample_count <= 6:
        return "USEFUL_EARLY"
    if span_days < 90:
        return "USEFUL_BUT_SHORT_SPAN"
    if span_days < 270:
        return "SOLID"
    return "REPRESENTATIVE"


def _model_health_score(
    *,
    sample_count: int,
    primary_change_rate: float,
    avg_turnover: float,
    avg_vfv: float,
    vfv_range: float,
    avg_core: float,
    avg_decision_quality: float | None,
    high_cycle_day_rate: float,
    extreme_cycle_day_rate: float,
    avg_max_single: float,
) -> float:
    score = 100.0
    if sample_count <= 1:
        score -= 35
    elif sample_count <= 3:
        score -= 18
    if sample_count >= 4:
        if primary_change_rate > 0.75:
            score -= 22
        elif primary_change_rate > 0.50:
            score -= 12
        if avg_turnover > 0.55:
            score -= 18
        elif avg_turnover > 0.35:
            score -= 9
    if avg_vfv > 0.35:
        score -= 22
    elif avg_vfv > 0.25:
        score -= 10
    if vfv_range > 0.25:
        score -= 15
    elif vfv_range > 0.10:
        score -= 6
    if avg_core < 0.55:
        score -= 18
    elif avg_core < 0.70:
        score -= 8
    if avg_decision_quality is not None:
        if avg_decision_quality < 55:
            score -= 18
        elif avg_decision_quality < 70:
            score -= 8
    if extreme_cycle_day_rate > 0.35:
        score -= 14
    elif high_cycle_day_rate > 0.60:
        score -= 9
    if avg_max_single > 0.60:
        score -= 12
    elif avg_max_single > 0.45:
        score -= 6
    return round(max(0.0, min(100.0, score)), 1)


def _health_status(
    *,
    sample_count: int,
    health_score: float,
    confidence: str,
    primary_change_rate: float,
    avg_turnover: float,
    avg_vfv: float,
    avg_core: float,
    avg_max_single: float,
) -> str:
    if sample_count <= 1:
        return "DATA_TOO_SHORT"
    if avg_vfv > 0.40 or avg_core < 0.50:
        return "TOO_DEFENSIVE"
    if sample_count >= 4 and (primary_change_rate > 0.80 or avg_turnover > 0.60):
        return "TOO_VOLATILE"
    if avg_max_single > 0.65:
        return "TOO_CONCENTRATED"
    if health_score >= 82 and confidence not in {"VERY_LIMITED", "PRELIMINARY"}:
        return "STRONG"
    if health_score >= 65:
        return "GOOD_BUT_WATCH"
    return "NEEDS_REVIEW"


def _audit_recommendation(health_status: str, confidence: str, sample_count: int) -> str:
    if sample_count <= 1:
        return "L’audit fonctionne, mais il n’y a pas encore assez d’historique pour juger la stabilité du modèle."
    if health_status == "STRONG":
        return "La mécanique récente semble saine et alignée avec un profil haut CAGR long terme, tout en gardant des garde-fous."
    if health_status == "GOOD_BUT_WATCH":
        return "Le modèle est utilisable, mais il faut continuer de surveiller la volatilité des recommandations, VFV et la concentration."
    if health_status == "TOO_DEFENSIVE":
        return "Le modèle semble envoyer trop souvent la cotisation vers VFV ou trop peu vers les titres core; il faudrait vérifier si les garde-fous sont trop stricts."
    if health_status == "TOO_VOLATILE":
        return "Les recommandations changent beaucoup; il faudrait vérifier si la variation vient de vraies dégradations ou de bruit de marché."
    if health_status == "TOO_CONCENTRATED":
        return "La logique high CAGR fonctionne, mais les plus gros blocs reviennent trop souvent concentrés; surveiller les plafonds de sizing."
    return "Audit à surveiller: les données historiques sont utilisables, mais certains signaux justifient une revue manuelle."


def _threshold_review(metrics: dict[str, Any]) -> dict[str, Any]:
    allocation_count = int(metrics.get("allocation_sample_count") or 0)
    avg_vfv = safe_float(metrics.get("avg_vfv")) or 0.0
    avg_core = safe_float(metrics.get("avg_core")) or 0.0
    vfv_range = safe_float(metrics.get("vfv_range")) or 0.0
    primary_change_rate = safe_float(metrics.get("primary_change_rate")) or 0.0
    avg_turnover = safe_float(metrics.get("avg_allocation_turnover")) or 0.0
    avg_max_single = safe_float(metrics.get("avg_max_single")) or 0.0
    concentration_rate = safe_float(metrics.get("concentration_day_rate")) or 0.0
    high_cycle_rate = safe_float(metrics.get("high_cycle_day_rate")) or 0.0
    extreme_cycle_rate = safe_float(metrics.get("extreme_cycle_day_rate")) or 0.0
    low_data_rate = safe_float(metrics.get("low_data_day_rate")) or 0.0
    decision_quality = safe_float(metrics.get("avg_decision_quality"))

    rows = [
        _row(
            "Revue des seuils",
            "Modification automatique des règles",
            "DISABLED",
            "0 changement automatique",
            "L’audit observe les règles, mais ne les réécrit jamais tout seul.",
            "Toute modification de seuil doit être validée manuellement après plusieurs mois de données.",
        )
    ]

    status = "THRESHOLDS_OK"
    interpretation = "Les seuils semblent cohérents avec le profil high CAGR long terme selon l’historique disponible."

    if allocation_count < 4:
        status = "INSUFFICIENT_HISTORY"
        interpretation = "Pas encore assez de dates avec allocation pour proposer une vraie calibration des seuils."
        rows.append(
            _row(
                "Revue des seuils",
                "Historique nécessaire",
                "WAIT",
                f"{allocation_count} date(s) avec allocation",
                "Attendre au moins 4 dates distinctes, idéalement 6 à 12 mois, avant de juger les seuils.",
                "Évite de modifier le modèle sur la base de tests trop rapprochés.",
            )
        )
    else:
        if avg_vfv > 0.30 or avg_core < 0.65:
            status = "SLIGHTLY_TOO_DEFENSIVE"
            interpretation = "Les seuils ou redirections pourraient être un peu trop prudents pour ton profil si cette tendance persiste."
            rows.append(
                _row(
                    "Revue des seuils",
                    "Seuils VFV / redirection",
                    "WATCH",
                    f"VFV moyen {pct(avg_vfv)}, core moyen {pct(avg_core)}",
                    "Si VFV reste élevé malgré plusieurs titres core solides, les règles de redirection pourraient être trop strictes.",
                    "À considérer seulement si 3 titres core ou plus ont des données solides et restent régulièrement écartés.",
                )
            )
        if primary_change_rate > 0.65 or avg_turnover > 0.45:
            status = _dominant_threshold_status(status, "TOO_VOLATILE")
            rows.append(
                _row(
                    "Revue des seuils",
                    "Stabilité des recommandations",
                    "WATCH",
                    f"titre principal change {pct(primary_change_rate)}, rotation {pct(avg_turnover)}",
                    "Les seuils semblent peut-être trop sensibles aux variations mensuelles de valorisation, cycle ou données.",
                    "Surveiller avant d’augmenter l’amortisseur de stabilité; le modèle doit garder la capacité de changer d’avis si un titre se dégrade réellement.",
                )
            )
        if avg_max_single > 0.55 or concentration_rate > 0.33:
            status = _dominant_threshold_status(status, "TOO_CONCENTRATED")
            rows.append(
                _row(
                    "Revue des seuils",
                    "Plafonds de sizing",
                    "WATCH",
                    f"plus gros bloc moyen {pct(avg_max_single)}",
                    "Les grosses allocations restent compatibles avec un profil high CAGR, mais elles ne doivent pas devenir mécaniquement excessives.",
                    "Si cette tendance persiste, envisager un plafond marginal un peu plus strict pour les nouvelles cotisations.",
                )
            )
        if high_cycle_rate > 0.65 or extreme_cycle_rate > 0.30:
            status = _dominant_threshold_status(status, "CYCLE_EXPOSURE_TO_WATCH")
            rows.append(
                _row(
                    "Revue des seuils",
                    "Cycle / bulle / tendance",
                    "WATCH",
                    f"cycle élevé {pct(high_cycle_rate)}, extrême {pct(extreme_cycle_rate)}",
                    "Le modèle finance souvent des titres exposés à des thèmes chauds ou cycliques.",
                    "Ne pas exclure les meilleurs compounders, mais garder un ajustement de sizing si le thème devient dominant.",
                )
            )
        if low_data_rate > 0.15 or (decision_quality is not None and decision_quality < 60):
            status = _dominant_threshold_status(status, "DATA_TOO_WEAK")
            rows.append(
                _row(
                    "Revue des seuils",
                    "Seuils de qualité des données",
                    "WATCH",
                    f"données faibles {pct(low_data_rate)}",
                    "Les seuils pourraient laisser passer trop de recommandations avec données faibles.",
                    "Prioriser les rapports BNCD/Morningstar ou données manuelles avant d’assouplir quoi que ce soit.",
                )
            )
        if avg_vfv < 0.05 and avg_max_single > 0.45:
            status = _dominant_threshold_status(status, "SLIGHTLY_TOO_AGGRESSIVE")
            rows.append(
                _row(
                    "Revue des seuils",
                    "Offensivité du mode high-CAGR",
                    "WATCH",
                    f"VFV moyen {pct(avg_vfv)}, plus gros bloc {pct(avg_max_single)}",
                    "Le modèle pourrait devenir très offensif si VFV disparaît presque toujours et qu’un seul titre reçoit une grosse part.",
                    "À surveiller pour conserver la discipline long terme malgré l’objectif haut CAGR.",
                )
            )

    if len(rows) == 1 and status == "THRESHOLDS_OK":
        rows.append(
            _row(
                "Revue des seuils",
                "Action recommandée",
                "KEEP_RULES",
                "Aucun ajustement suggéré",
                "Les seuils ne montrent pas de dérive importante dans l’historique disponible.",
                "Continuer l’utilisation normale et réévaluer après quelques nouvelles cotisations.",
            )
        )
    elif status != "INSUFFICIENT_HISTORY":
        rows.append(
            _row(
                "Revue des seuils",
                "Action recommandée",
                "NO_AUTO_CHANGE",
                "Surveillance seulement",
                "Les observations sont utiles, mais pas suffisantes pour modifier automatiquement les règles.",
                "Conserver les seuils actuels; revoir seulement si le même signal persiste sur plusieurs mois.",
            )
        )

    return {
        "status": status,
        "summary_value": _threshold_summary_value(metrics),
        "interpretation": _threshold_interpretation(status, interpretation),
        "rows": rows,
    }


def _threshold_interpretation(status: str, fallback: str) -> str:
    return {
        "INSUFFICIENT_HISTORY": "Pas encore assez de dates avec allocation pour proposer une vraie calibration des seuils.",
        "THRESHOLDS_OK": "Les seuils semblent cohérents avec le profil high CAGR long terme selon l’historique disponible.",
        "SLIGHTLY_TOO_DEFENSIVE": "Les règles semblent peut-être un peu trop prudentes si VFV ou les refus de titres core restent élevés.",
        "SLIGHTLY_TOO_AGGRESSIVE": "Les règles semblent peut-être un peu trop offensives si VFV disparaît presque toujours et que les gros blocs persistent.",
        "TOO_VOLATILE": "Les seuils semblent peut-être trop sensibles aux variations récentes de marché, valorisation ou données.",
        "TOO_CONCENTRATED": "Les seuils de sizing ou concentration méritent une surveillance si les gros blocs persistent.",
        "CYCLE_EXPOSURE_TO_WATCH": "Les seuils restent utilisables, mais l’exposition répétée aux thèmes cycliques ou chauds doit être surveillée.",
        "DATA_TOO_WEAK": "Les seuils de qualité des données pourraient être trop permissifs si cette situation persiste.",
    }.get(status, fallback)


def _dominant_threshold_status(current: str, candidate: str) -> str:
    rank = {
        "THRESHOLDS_OK": 0,
        "CYCLE_EXPOSURE_TO_WATCH": 1,
        "SLIGHTLY_TOO_AGGRESSIVE": 2,
        "SLIGHTLY_TOO_DEFENSIVE": 2,
        "TOO_CONCENTRATED": 3,
        "TOO_VOLATILE": 4,
        "DATA_TOO_WEAK": 5,
        "INSUFFICIENT_HISTORY": 6,
    }
    return candidate if rank.get(candidate, 0) > rank.get(current, 0) else current


def _threshold_summary_value(metrics: dict[str, Any]) -> str:
    return (
        f"VFV {pct(safe_float(metrics.get('avg_vfv')) or 0.0)}, "
        f"core {pct(safe_float(metrics.get('avg_core')) or 0.0)}, "
        f"rotation {pct(safe_float(metrics.get('avg_allocation_turnover')) or 0.0)}"
    )


def _row(section: str, metric: str, status: str, value: str, interpretation: str, impact: str) -> dict[str, Any]:
    return {
        "section": section,
        "metric": metric,
        "status": status,
        "value": value,
        "interpretation": interpretation,
        "impact": impact,
    }


def _rate_status(value: float, medium: float, high: float, inverse: bool = False) -> str:
    if inverse:
        if value >= high:
            return "HIGH_RISK"
        if value >= medium:
            return "WATCH"
        return "OK"
    if value >= high:
        return "STRONG"
    if value >= medium:
        return "OK"
    return "WATCH"


def _score_status(value: float | None) -> str:
    if value is None:
        return "N/D"
    if value >= 80:
        return "STRONG"
    if value >= 65:
        return "OK"
    if value >= 55:
        return "WATCH"
    return "WEAK"


def _vfv_level(value: float) -> str:
    if value > 0.35:
        return "TOO_HIGH"
    if value > 0.25:
        return "WATCH"
    return "OK"


def _health_interpretation(status: str) -> str:
    return {
        "DATA_TOO_SHORT": "Audit techniquement valide, mais historique trop court pour conclure fortement.",
        "STRONG": "Le modèle semble stable, offensif avec discipline, et cohérent avec le profil long terme.",
        "GOOD_BUT_WATCH": "Le modèle est utilisable, avec quelques points à surveiller.",
        "TOO_DEFENSIVE": "Le modèle semble trop souvent préférer VFV ou éviter les titres core.",
        "TOO_VOLATILE": "Le modèle change trop souvent de recommandation principale.",
        "TOO_CONCENTRATED": "Le modèle concentre fortement les cotisations dans un petit nombre de titres.",
        "NEEDS_REVIEW": "Quelques signaux méritent une revue manuelle avant de conclure.",
    }.get(status, "Statut non reconnu.")


def _confidence_interpretation(status: str) -> str:
    return {
        "VERY_LIMITED": "0 ou 1 date distincte: l’audit sert surtout de point de départ.",
        "PRELIMINARY": "2 à 3 dates distinctes: premières tendances seulement.",
        "USEFUL_EARLY": "4 à 6 dates avec allocation: l’audit devient utile, mais reste jeune.",
        "USEFUL_BUT_SHORT_SPAN": "Plusieurs dates, mais période courte: utile pour détecter une volatilité récente.",
        "SOLID": "Historique assez solide pour juger la mécanique récente.",
        "REPRESENTATIVE": "Historique étalé sur une longue période: conclusions plus représentatives.",
    }.get(status, "Niveau de confiance non reconnu.")


def _markdown_table(rows: list[dict[str, Any]], columns: list[str]) -> str:
    if not rows:
        return "Aucune donnée à afficher."
    header = "| " + " | ".join(columns) + " |"
    separator = "| " + " | ".join(["---"] * len(columns)) + " |"
    body = []
    for row in rows:
        body.append("| " + " | ".join(_cell(row.get(column)) for column in columns) + " |")
    return "\n".join([header, separator, *body])


def _cell(value: Any) -> str:
    return str(value if value is not None else "").replace("\n", " ").replace("|", "/")
