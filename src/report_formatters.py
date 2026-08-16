from __future__ import annotations

from typing import Any


def escape_markdown_cell(value: Any) -> str:
    return str(value if value is not None else "Donnée pas dispo").replace("|", "/").replace("\n", " ")


def report_value(value: Any) -> str:
    return "Donnée pas dispo" if value is None or value == "" else str(value)


def list_text(values: Any) -> str:
    if not values:
        return "Aucun"
    if isinstance(values, list):
        return ", ".join(str(value) for value in values) if values else "Aucun"
    return str(values)


def mapping_text(values: Any) -> str:
    if not values:
        return "Aucun"
    if isinstance(values, dict):
        return "; ".join(f"{key}: {value}" for key, value in sorted(values.items())) or "Aucun"
    return str(values)


def proxy_corrections_text(values: Any) -> str:
    if not values:
        return "Aucun"
    if not isinstance(values, list):
        return str(values)
    parts = []
    for row in values:
        if not isinstance(row, dict):
            parts.append(str(row))
            continue
        field = row.get("field", "")
        factor = row.get("factor", "")
        confidence = row.get("confidence", "")
        sample_count = row.get("sample_count", "")
        parts.append(f"{field}: facteur={factor}, confiance={confidence}, n={sample_count}")
    return "; ".join(parts) if parts else "Aucun"


def first_signal(values: Any) -> str:
    if not values:
        return ""
    if isinstance(values, list):
        return str(values[0]) if values else ""
    text = str(values).strip()
    if not text or text == "Aucun":
        return ""
    return text.split(";")[0].strip()


def as_list(values: Any) -> list[Any]:
    if values is None or values == "":
        return []
    if isinstance(values, list):
        return values
    return [values]


def uses_yfinance_or_cache(row: dict[str, Any]) -> bool:
    source = str(row.get("source") or "").lower()
    notes = " ".join(str(note).lower() for note in as_list(row.get("data_source_notes")))
    return "yfinance" in source or "yfinance" in notes or "cache local yfinance" in notes


def compact_list(values: list[str], limit: int = 24) -> str:
    clean = [value for value in values if value]
    if not clean:
        return "Aucun"
    if len(clean) <= limit:
        return ", ".join(clean)
    shown = ", ".join(clean[:limit])
    return f"{shown}, ... (+{len(clean) - limit})"


def truthy_report_value(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value or "").strip().lower() in {"true", "1", "yes", "oui", "applied", "appliqué", "applique"}


def compact_sentence(value: Any, limit: int = 220) -> str:
    text = str(value or "").replace("\n", " ").strip()
    if not text:
        return "N/D"
    text = " ".join(text.split())
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 3)].rstrip(" ,.;") + "..."


def _triage_float(value: Any) -> float:
    if value is None or value == "":
        return 0.0
    try:
        return float(str(value).replace("$", "").replace("%", "").replace(" ", "").replace(",", "."))
    except (TypeError, ValueError):
        return 0.0


def _triage_money(value: float) -> str:
    rounded = round(float(value or 0.0), 2)
    if rounded.is_integer():
        return str(int(rounded))
    return f"{rounded:.2f}"


def _triage_sell_signal(row: dict[str, Any]) -> str:
    signal = str(row.get("sell_signal") or "").strip()
    if signal:
        return signal
    for key in ("mechanical_sell_signal", "sell_decision", "recommended_action", "final_position_action"):
        candidate = str(row.get(key) or "").strip()
        if candidate.upper() in {"TRIM_25", "TRIM_50", "LIQUIDATE_PROGRESSIVELY", "LIQUIDATE_URGENT_REVIEW"}:
            return candidate
    return signal


def build_triage_header(
    *,
    mode: str,
    allocation_result: dict,
    sell_rows: list[dict],
    validation_priority_rows: list[dict],
    anomaly_rows: list[dict],
    analyses: dict,
    watchlist_analyses: dict,
    market_analyses: dict,
    discovery_analyses: dict,
    score_stability: dict | None = None,
    walk_forward_status: dict | None = None,
) -> str:
    active_allocations = []
    for row in allocation_result.get("allocations", []) or []:
        amount = _triage_float(row.get("monthly_contribution"))
        if amount <= 0 and "monthly_contribution" not in row:
            amount = _triage_float(row.get("amount", row.get("montant")))
        if amount <= 0:
            continue
        ticker = str(row.get("ticker") or row.get("destination") or row.get("symbol") or "").strip()
        if ticker:
            active_allocations.append(f"+{_triage_money(amount)}$ {ticker}")
    decision_icon = "🟢" if active_allocations else "⚪"
    decision_text = "DÉCISION : " + (" | ".join(active_allocations) if active_allocations else "Aucune contribution ce mois-ci")

    sell_count = 0
    for row in sell_rows or []:
        signal = _triage_sell_signal(row).strip().upper()
        if signal and signal not in {"HOLD", "NONE"}:
            sell_count += 1
    sell_icon = "🔴" if sell_count >= 2 else "🟡" if sell_count == 1 else "🟢"
    sell_text = f"{sell_count} alerte(s) vente à vérifier" if sell_count else "Aucun signal de vente actif"

    validation_count = sum(
        1 for row in validation_priority_rows or [] if str(row.get("priority") or "").strip().upper() in {"HIGH", "CRITICAL"}
    )
    validation_icon = "🔴" if validation_count >= 3 else "🟡" if validation_count else "🟢"
    validation_text = (
        f"{validation_count} donnée(s) prioritaire(s) à valider"
        if validation_count
        else "Données : aucune priorité haute"
    )

    anomaly_count = sum(1 for row in anomaly_rows or [] if row)
    anomaly_icon = "⚠️" if anomaly_count else "🟢"
    anomaly_text = f"{anomaly_count} anomalie(s) détectée(s)" if anomaly_count else "Aucune anomalie détectée"

    counts_text = (
        f"Core {len(analyses or {})} | Watchlist {len(watchlist_analyses or {})} | "
        f"Market {len(market_analyses or {})} | Discovery {len(discovery_analyses or {})} titres analysés"
    )

    lines = [
        "---",
        f"{decision_icon} {decision_text}",
        "",
        f"{sell_icon} {sell_text}",
        "",
        f"{validation_icon} {validation_text}",
        "",
        f"{anomaly_icon} {anomaly_text}",
        "",
        f"📊 {counts_text}",
    ]
    system_action_lines = _triage_system_action_lines(mode, score_stability, walk_forward_status, analyses)
    if system_action_lines:
        lines.extend(["", "─── ACTIONS SYSTÈME REQUISES ───", "", *system_action_lines])
    lines.append("---")
    return "\n".join(lines)


def _triage_system_action_lines(
    mode: str,
    score_stability: dict[str, Any] | None,
    walk_forward_status: dict[str, Any] | None,
    analyses: dict[str, dict[str, Any]] | None = None,
) -> list[str]:
    lines: list[str] = []
    lines.extend(_triage_stale_market_data_lines(analyses))
    if analyses:
        lines.extend(_triage_proxy_calibration_sync_lines())
    walk = walk_forward_status or {}
    walk_status = str(walk.get("status") or "").strip().upper()
    walk_message = str(walk.get("message") or "").strip()
    if walk and ("DORMANT" in walk_status or "WARNING" in walk_status):
        message = _without_leading_warning_icon(walk_message or "Walk-forward à relancer pour ce mode.")
        command = f"python3 main.py walk-forward-backtest --mode {mode}"
        if command not in message:
            message = f"{message} Commande : {command}"
        lines.append(f"⚠️ {message}")

    stability = score_stability or {}
    stability_status = str(stability.get("status") or "").strip().upper()
    stability_message = str(stability.get("message") or "").strip()
    if stability and stability_status in {"UNSTABLE", "WATCH"}:
        lines.append(f"⚠️ {_without_leading_warning_icon(stability_message or 'Stabilité des scores à vérifier.')}")
    return lines


def _triage_proxy_calibration_sync_lines() -> list[str]:
    import json as _json
    from pathlib import Path as _Path

    sync_log_path = _Path(__file__).resolve().parents[1] / "data" / "proxy_calibration_sync_log.json"
    if not sync_log_path.exists():
        return []

    stale: list[str] = []
    warning: list[str] = []
    sync_date = ""
    try:
        with open(sync_log_path, encoding="utf-8") as handle:
            log = _json.load(handle)
        stale = [str(ticker) for ticker in log.get("stale_tickers", []) if ticker]
        warning = [str(ticker) for ticker in log.get("warning_tickers", []) if ticker]
        sync_date = str(log.get("sync_date") or "").strip()
    except Exception:
        return []

    if stale:
        return [
            "⚠ CALIBRATION DONNÉES MARCHÉ — MISE À JOUR REQUISE",
            f"Données Catégorie B périmées (>90j) pour: {compact_list(stale, limit=12)}",
            f"Source: proxy_calibration.csv — dernière sync: {sync_date or 'N/D'}",
            "Action: mettre à jour les valeurs puis relancer:",
            "  python3 main.py sync-manual-inputs",
        ]

    if warning:
        return [
            "⚠ CALIBRATION — MISE À JOUR RECOMMANDÉE BIENTÔT",
            f"Données Catégorie B approchant expiry (75-90j) pour: {compact_list(warning, limit=12)}",
            "Action: python3 main.py sync-manual-inputs après mise à jour CSV",
        ]

    return []


def _triage_stale_market_data_lines(analyses: dict[str, dict[str, Any]] | None) -> list[str]:
    stale_held: list[str] = []
    max_age_hours = 0.0
    circuit_open = False
    for ticker, row in (analyses or {}).items():
        if not isinstance(row, dict):
            continue
        current_value = _triage_float(row.get("current_value")) or 0.0
        if current_value <= 0:
            continue
        age = _triage_float(row.get("market_data_age_hours")) or 0.0
        row_circuit_open = row.get("market_data_circuit_breaker_open") is True
        if age > 48 or row_circuit_open:
            stale_held.append(str(ticker))
            max_age_hours = max(max_age_hours, age)
        if row_circuit_open:
            circuit_open = True

    if not stale_held:
        return []

    lines = [
        "⚠ DONNÉES MARCHÉ POTENTIELLEMENT PÉRIMÉES",
        f"Données de marché > 48h pour {len(stale_held)} position(s) détenue(s).",
        f"Âge maximum détecté : {max_age_hours:.1f} heures.",
    ]
    if circuit_open:
        lines.append("Cause : coupe-circuit yfinance actif.")
    lines.extend(
        [
            "Prix affichés et signaux techniques peuvent ne pas refléter le marché actuel.",
            "Rafraîchir avec --refresh-market-data avant toute décision d'achat réelle.",
        ]
    )
    return lines


def _without_leading_warning_icon(value: str) -> str:
    text = str(value or "").strip()
    for prefix in ("⚠️", "✅", "ℹ️"):
        text = text.removeprefix(prefix).strip()
    return text


def build_compact_decision_section(
    *,
    allocation_result: dict,
    allocation_change_rows: list[dict],
    analyses: dict,
    watchlist_analyses: dict,
    market_analyses: dict,
    discovery_analyses: dict,
    instrument_profiles: list[dict] | None = None,
    decision_quality: dict | None = None,
) -> str:
    allocation_rows = _active_allocation_rows(allocation_result)
    all_analyses = {**(analyses or {}), **(watchlist_analyses or {}), **(market_analyses or {}), **(discovery_analyses or {})}
    profile_by_ticker = {
        str(profile.get("ticker") or "").strip(): profile
        for profile in instrument_profiles or []
        if str(profile.get("ticker") or "").strip()
    }
    change_by_ticker = {
        str(row.get("ticker") or "").strip(): row
        for row in allocation_change_rows or []
        if str(row.get("ticker") or "").strip()
    }

    lines = ["### Allocation recommandée", ""]
    if not allocation_rows:
        lines.extend(["Aucune contribution ce run — portefeuille en surveillance.", ""])
    else:
        allocation_text = " | ".join(
            f"{_allocation_ticker(row)} {_format_money(_allocation_amount(row))} ({_format_percentage(_allocation_percentage(row))})"
            for row in allocation_rows
        )
        lines.extend(["Allocation recommandée", allocation_text, _decision_quality_line(decision_quality)])
        change_text = _allocation_change_summary_for_active_rows(allocation_rows, change_by_ticker)
        if change_text:
            lines.append(f"Vs dernier run : {change_text}")
        lines.append("")

    for row in allocation_rows:
        ticker = _allocation_ticker(row)
        profile = profile_by_ticker.get(ticker, {})
        analysis = all_analyses.get(ticker, {})
        name = _profile_name(ticker, profile, analysis)
        description = _instrument_profile_description(ticker, profile, name)
        reason = compact_sentence(row.get("reason") or row.get("raison"), 150)
        amount_reason = f"{_format_percentage(_allocation_percentage(row))} — {reason}"
        confidence = report_value(row.get("confidence") or row.get("niveau de confiance"))
        previous = _allocation_change_text(change_by_ticker.get(ticker))
        lines.extend(
            [
                f"#### {name} ({ticker})",
                "",
                description,
                "",
                f"Pourquoi ce titre   : {reason}",
                "",
                f"Pourquoi ce montant : {amount_reason}",
                "",
                f"Confiance           : {confidence}",
                "",
                f"Vs dernier run      : {previous}",
                "",
            ]
        )
    return "\n".join(lines).rstrip()


def _active_allocation_rows(allocation_result: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for row in allocation_result.get("allocations", []) or []:
        if _allocation_amount(row) > 0 and _allocation_ticker(row):
            rows.append(row)
    return rows


def _allocation_amount(row: dict[str, Any]) -> float:
    amount = _triage_float(row.get("monthly_contribution"))
    if amount <= 0:
        amount = _triage_float(row.get("amount", row.get("montant")))
    return amount


def _allocation_percentage(row: dict[str, Any]) -> Any:
    if row.get("percentage") not in {None, ""}:
        return row.get("percentage")
    return row.get("pourcentage")


def _allocation_ticker(row: dict[str, Any]) -> str:
    return str(row.get("ticker") or row.get("destination") or row.get("symbol") or "").strip()


def _format_money(value: Any) -> str:
    return f"{_triage_money(_triage_float(value))}$"


def _format_percentage(value: Any) -> str:
    if value is None or value == "":
        return "N/D"
    try:
        number = float(str(value).replace("%", "").replace(" ", "").replace(",", "."))
    except (TypeError, ValueError):
        return "N/D"
    if abs(number) <= 1.0 and number != 0:
        number *= 100
    rounded = round(number, 1)
    if rounded.is_integer():
        return f"{int(rounded)}%"
    return f"{rounded:.1f}%"


def _decision_quality_line(decision_quality: dict[str, Any] | None) -> str:
    if not isinstance(decision_quality, dict) or not decision_quality:
        return "Confiance   : N/D — données de qualité insuffisantes pour évaluation."
    level = str(decision_quality.get("decision_quality_level") or "N/D").strip() or "N/D"
    score = report_value(decision_quality.get("decision_quality_score"))
    detail_lines = build_decision_quality_compact_lines(decision_quality)
    detail = ""
    if detail_lines:
        detail = str(detail_lines[0]).replace("  → ", "", 1).strip()
    return f"Confiance   : {level} ({score}/100)" + (f" — {detail}" if detail else "")


def _allocation_change_summary_for_active_rows(
    allocation_rows: list[dict[str, Any]],
    change_by_ticker: dict[str, dict[str, Any]],
) -> str:
    parts = []
    for row in allocation_rows:
        ticker = _allocation_ticker(row)
        change = change_by_ticker.get(ticker)
        if change:
            parts.append(f"{ticker} {_allocation_change_text(change)}")
    return " | ".join(parts)


def _allocation_change_text(change: dict[str, Any] | None) -> str:
    if not change:
        return "Non disponible"
    amount = _triage_float(change.get("change_amount"))
    status = str(change.get("change_status") or "N/D").strip() or "N/D"
    sign = "+" if amount > 0 else ""
    return f"{sign}{_format_money(amount)} ({status})"


def _profile_name(ticker: str, profile: dict[str, Any], analysis: dict[str, Any]) -> str:
    return str(
        profile.get("name")
        or analysis.get("company_name")
        or analysis.get("company_name_found")
        or analysis.get("long_name")
        or analysis.get("short_name")
        or ticker
    ).strip()


def _instrument_profile_description(ticker: str, profile: dict[str, Any], name: str) -> str:
    if not profile:
        return "Description non disponible pour ce titre."
    instrument_type = str(profile.get("instrument_type") or "").strip().upper()
    business_description = str(profile.get("business_description") or "").strip()
    portfolio_role = str(profile.get("portfolio_role") or "").strip()
    sector = str(profile.get("sector_or_category") or "").strip()
    industry = str(profile.get("industry") or "").strip()
    revenue_model = str(profile.get("revenue_model_or_activity") or "").strip()
    watch_items = str(profile.get("key_watch_items") or "").strip()

    if instrument_type == "ETF":
        parts = [f"{name} est un ETF"]
        if business_description:
            parts.append(f"qui {business_description}")
        sentence = " ".join(parts).rstrip(".") + "."
        if portfolio_role:
            sentence += f" Son rôle dans ce portefeuille : {portfolio_role}."
        return sentence

    category = " / ".join(part for part in [sector, industry] if part)
    first_sentence = f"{name} est une entreprise"
    if category:
        first_sentence += f" classée dans {category}"
    first_sentence = first_sentence.rstrip(".") + "."
    sentences = [first_sentence]
    if business_description:
        sentences.append(f"Activité principale : {business_description.rstrip('.')}.")
    if revenue_model:
        sentences.append(revenue_model.rstrip(".") + ".")
    if portfolio_role:
        sentences.append(f"Son rôle dans ce portefeuille : {portfolio_role.rstrip('.')}.")
    if watch_items:
        sentences.append(f"À surveiller : {watch_items.rstrip('.')}.")
    return " ".join(sentences)


def build_score_stability_signal_lines(score_stability: dict[str, Any] | None) -> list[str]:
    signal = score_stability or {}
    status = str(signal.get("status") or "").strip().upper()
    message = str(signal.get("message") or "").strip()
    if not message:
        return []
    if status == "STABLE":
        return [message, ""]
    return ["### Stabilité des scores", "", message, ""]


def build_decision_quality_compact_lines(decision_quality: dict[str, Any] | None) -> list[str]:
    try:
        if not isinstance(decision_quality, dict) or not decision_quality:
            return ["  → Données de qualité insuffisantes pour évaluation."]

        data_status = str(
            decision_quality.get("data_status") or decision_quality.get("data_quality_status") or ""
        ).strip().upper()
        level = str(decision_quality.get("decision_quality_level") or "").strip().upper()

        if data_status == "NOT_APPLICABLE":
            return ["  → Analyse sans capital — score de robustesse non applicable."]
        if level == "HIGH":
            return ["  → Recommandation robuste — tous les indicateurs au vert."]

        risk_status = str(decision_quality.get("risk_status") or "").strip().upper()
        stability_status = str(decision_quality.get("stability_status") or "").strip().upper()
        sensitivity_status = str(decision_quality.get("sensitivity_status") or "").strip().upper()
        why_not_high = decision_quality.get("why_not_high") or []
        if isinstance(why_not_high, str):
            why_not_high = [why_not_high]
        reason = str(why_not_high[0] if why_not_high else "Voir rapport complet pour détails.").strip()
        if not reason:
            reason = "Voir rapport complet pour détails."
        if len(reason) > 120:
            reason = reason[:119].rstrip(" ,.;") + "…"

        data_label = {
            "ROBUST": "✓ données",
            "WATCH": "⚠ données",
            "WEAK": "✗ données",
            "NO_CORE_ALLOCATION": "— données",
            "NOT_APPLICABLE": "— données",
        }.get(data_status, _short_status(data_status))
        risk_label = {
            "ACCEPTABLE": "✓ risque",
            "WATCH": "⚠ risque",
            "ELEVATED": "✗ risque",
        }.get(risk_status, _short_status(risk_status))
        stability_label = {
            "STABLE": "✓ stabilité",
            "RESPONSIVE": "~ stabilité",
            "LIMITED_HISTORY": "? stabilité",
            "WEAKENING": "✗ stabilité",
            "NO_CORE_ALLOCATION": "— stabilité",
            "NOT_APPLICABLE": "— stabilité",
        }.get(stability_status, _short_status(stability_status))
        sensitivity_label = _short_status(sensitivity_status)

        return [
            "  → données: "
            f"{data_label} | risque: {risk_label} | stabilité: {stability_label} | "
            f"sensibilité: {sensitivity_label}",
            f"  → {reason}",
        ]
    except Exception:
        return ["  → [affichage indisponible]"]


def _short_status(value: str) -> str:
    text = str(value or "N/D").strip()
    return text[:12] if len(text) > 12 else text


def _ranking_float(value: Any) -> float:
    if value is None or value == "":
        return 0.0
    try:
        return float(str(value).replace("%", "").replace("$", "").replace(" ", "").replace(",", "."))
    except (TypeError, ValueError):
        return 0.0


def _ranking_score(row: dict[str, Any]) -> float:
    for key in ("capital_allocation_score", "score_total", "conviction_score"):
        if row.get(key) not in {None, ""}:
            return _ranking_float(row.get(key))
    return 0.0


def _ranking_escape(value: Any) -> str:
    return str(value if value is not None else "Donnée pas dispo").replace("|", "/").replace("\n", " ")


def _ranking_table(headers: list[str], rows: list[dict[str, Any]]) -> str:
    if not rows:
        rows = [{header: "" for header in headers}]
    header_line = "| " + " | ".join(headers) + " |"
    separator = "| " + " | ".join(["---"] * len(headers)) + " |"
    body = ["| " + " | ".join(_ranking_escape(row.get(header, "")) for header in headers) + " |" for row in rows]
    return "\n".join([header_line, separator, *body])


def _promotion_blocking_note(row: dict[str, Any]) -> str:
    status = str(row.get("promotion_status") or "").strip()
    if not status or status == "PROMOTE_TO_CORE_REVIEW":
        return ""
    category = str(row.get("blocking_reason_category") or "UNKNOWN").strip() or "UNKNOWN"
    proximity = str(row.get("promotion_proximity_score") or "0/15").strip() or "0/15"
    return f"<br>  → [{category}] &#124; proximité: {proximity}"


def _ranking_rows(analyses: dict, top_n: int) -> list[dict[str, Any]]:
    ranked = sorted((analyses or {}).values(), key=_ranking_score, reverse=True)
    rows = []
    for index, row in enumerate(ranked[:top_n], start=1):
        allocation_status = (
            row.get("allocation_decision")
            or row.get("final_position_action")
            or row.get("watchlist_status")
            or row.get("candidate_status")
            or row.get("discovery_status")
            or row.get("promotion_status")
            or row.get("decision")
        )
        promotion_blocking_note = _promotion_blocking_note(row)
        if promotion_blocking_note:
            allocation_status = f"{allocation_status or row.get('promotion_status')}{promotion_blocking_note}"
        rows.append(
            {
                "rank": index,
                "ticker": row.get("ticker_display") or row.get("ticker"),
                "score_allocation": row.get("capital_allocation_score", row.get("score_total", row.get("conviction_score", 0.0))),
                "cagr_qualitatif": row.get("expected_cagr_quality"),
                "vs_vfv": row.get("opportunity_cost_status"),
                "thèse": row.get("thesis_status"),
                "vente": row.get("sell_status") or row.get("liquidation_status"),
                "surveillance": row.get("monitoring_status") or row.get("quality_drawdown_status"),
                "statut_allocation": allocation_status,
            }
        )
    return rows


def build_compact_model_health_section(
    *,
    score_stability: dict | None = None,
    walk_forward_status: dict | None = None,
    full_audit_status: dict | None = None,
    model_audit_status: dict | None = None,
    decision_quality: dict | None = None,
    allocation_result: dict | None = None,
    data_freshness_rows: list[dict] | None = None,
) -> str:
    lines = [
        "### Santé du modèle",
        "",
        _model_health_signal_line("Score Stability", score_stability),
        "",
        _model_health_signal_line("Walk-Forward", walk_forward_status),
        "",
        _model_health_signal_line("Audit maître", full_audit_status, audit_style=True),
        "",
        _model_health_signal_line("Audit stabilité", model_audit_status, audit_style=True),
        "",
        "**Confiance dans ce run :**",
        "",
        _decision_quality_line(decision_quality),
        "",
        _robustness_line(allocation_result),
        "",
        *_fragile_data_lines(data_freshness_rows, allocation_result),
    ]
    return "\n".join(lines).rstrip()


def build_compact_data_reliability_section(
    *,
    analyses: dict | None = None,
    watchlist_analyses: dict | None = None,
    source_health_rows: list[dict] | None = None,
    source_conflict_rows: list[dict] | None = None,
    data_freshness_rows: list[dict] | None = None,
    validation_priority_rows: list[dict] | None = None,
) -> str:
    del watchlist_analyses, validation_priority_rows
    core_tickers = {str(ticker) for ticker in (analyses or {}).keys()}
    stale_rows = [
        row
        for row in data_freshness_rows or []
        if _is_core_freshness_row(row, core_tickers)
        and str(row.get("overall_data_freshness_level") or "").strip().upper() in {"WATCH_FRESHNESS", "STALE"}
    ]
    conflict_rows = [
        row for row in source_conflict_rows or [] if str(row.get("severity") or "").strip().upper() == "HIGH_REVIEW"
    ]
    stale_count = len(stale_rows)
    conflict_count = len(conflict_rows)
    if stale_count == 0 and conflict_count == 0:
        verdict = "✅ SOLIDE"
    elif stale_count <= 3 and conflict_count <= 4:
        verdict = "🟡 UTILISABLE AVEC RÉSERVES"
    else:
        verdict = "⚠️ VALIDER AVANT GROSSE DÉCISION"

    lines = ["### Fiabilité des données", "", verdict, ""]
    coverage = _strong_data_coverage_line(analyses or {})
    if coverage:
        lines.extend([coverage, ""])
    lines.extend(["#### Titres à valider", ""])
    validation_lines = _data_reliability_validation_lines(conflict_rows, data_freshness_rows or [], core_tickers)
    lines.extend(validation_lines or ["Aucun titre ne requiert de validation prioritaire ce run."])
    lines.extend(["", "#### Sources utilisées ce run", "", _active_sources_line(source_health_rows)])
    lines.extend(
        [
            "",
            "> Note : ce rapport applique des règles mécaniques sur données gratuites. Toute décision finale doit être validée manuellement.",
        ]
    )
    return "\n".join(lines).rstrip()


def build_compact_portfolio_section(
    *,
    account_performance_rows: list[dict] | None = None,
    portfolio_change_rows: list[dict] | None = None,
    risk_rows: list[dict] | None = None,
    hidden_cluster_rows: list[dict] | None = None,
    market_regime: dict | None = None,
    account_charts: list[str] | None = None,
    account_summary_rows: list[dict] | None = None,
) -> str:
    lines = ["### Portefeuille", ""]
    summary_lines = _account_summary_lines(account_summary_rows or [])
    if summary_lines:
        lines.extend(summary_lines)
        lines.append("")
    for chart in account_charts or []:
        if chart:
            lines.extend([str(chart), ""])
    latest_change = _latest_portfolio_change_line(portfolio_change_rows or [])
    if latest_change:
        lines.extend([latest_change, ""])

    lines.extend(["**Performance vs S&P 500 :**", ""])
    performance_lines = _account_performance_lines(account_performance_rows or [])
    lines.extend(performance_lines or ["Performance : historique insuffisant pour comparer."])
    lines.extend(["", "**Risques du portefeuille :**", ""])
    risk_lines = _portfolio_human_risk_lines(risk_rows or [], hidden_cluster_rows or [], market_regime or {})
    lines.extend(risk_lines or ["Aucun risque majeur compact à afficher ce run."])
    return "\n".join(lines).rstrip()


CLUSTER_LABELS = {
    "RATES_SENSITIVE_GROWTH": (
        "{poids}% de ton portefeuille réagira ensemble si les taux d'intérêt montent ou descendent."
    ),
    "MEGA_CAP_TECH_PLATFORMS": (
        "{poids}% de ton portefeuille est exposé aux mêmes grandes plateformes technologiques."
    ),
    "AI_SEMI_CLOUD_INFRA": (
        "{poids}% de ton portefeuille est concentré sur le thème IA / semi-conducteurs / infrastructure cloud."
    ),
    "INDUSTRIAL_ELECTRIFICATION_AUTOMATION": (
        "{poids}% de ton portefeuille est exposé au thème électrification industrielle et automatisation."
    ),
    "PAYMENTS_FINANCIAL_NETWORKS": (
        "{poids}% de ton portefeuille est exposé aux réseaux de paiement et services financiers."
    ),
    "CANADA_CAD_CLUSTER": (
        "{poids}% de ton portefeuille est exposé au marché canadien et au dollar canadien."
    ),
}


def _model_health_signal_line(label: str, signal: dict[str, Any] | None, *, audit_style: bool = False) -> str:
    if not isinstance(signal, dict) or not signal:
        return f"⚠️ {label:<16}: — Non disponible"
    status = str(signal.get("status") or "N/D").strip() or "N/D"
    icon = "✅" if any(token in status.upper() for token in {"STABLE", "HEALTHY", "OK", "PASS"}) else "⚠️"
    if audit_style:
        message = _audit_compact_message(signal)
    else:
        message = compact_sentence(_clean_signal_message(str(signal.get("message") or ""), status), 90)
    if not message or message == "N/D":
        message = "Non disponible"
    return f"{icon} {label:<16}: {status} — {message}"


def _audit_compact_message(signal: dict[str, Any]) -> str:
    parts = []
    days_since = signal.get("days_since")
    last_score = signal.get("last_score")
    next_audit = signal.get("next_audit_in")
    if days_since not in {None, ""}:
        parts.append(f"récent ({days_since}j)")
    if last_score not in {None, ""}:
        parts.append(f"score {last_score}/100")
    if next_audit not in {None, ""}:
        parts.append(f"prochain dans ~{next_audit}j")
    if parts:
        return compact_sentence(", ".join(parts), 90)
    return compact_sentence(_clean_signal_message(str(signal.get("message") or ""), str(signal.get("status") or "")), 90)


def _clean_signal_message(value: str, status: str = "") -> str:
    text = _without_leading_warning_icon(value)
    status_text = str(status or "").strip()
    if status_text and text.upper().startswith(status_text.upper()):
        text = text[len(status_text):].lstrip(" —:-").strip()
    return text


def _robustness_line(allocation_result: dict[str, Any] | None) -> str:
    if not isinstance(allocation_result, dict) or not allocation_result or not _active_allocation_rows(allocation_result):
        return "Robustesse : N/A — analyse sans capital, aucune sensibilité à tester."
    decision_quality = allocation_result.get("decision_quality") if isinstance(allocation_result.get("decision_quality"), dict) else {}
    status = str(
        allocation_result.get("sensitivity_status")
        or allocation_result.get("robustness_status")
        or allocation_result.get("allocation_sensitivity_status")
        or decision_quality.get("sensitivity_status")
        or "N/D"
    ).strip()
    explanation = compact_sentence(
        allocation_result.get("sensitivity_explanation")
        or allocation_result.get("robustness_explanation")
        or allocation_result.get("sensitivity_summary")
        or "Voir la section robustesse du rapport complet.",
        90,
    )
    return f"Robustesse : {status} — {explanation}"


def _fragile_data_lines(data_freshness_rows: list[dict] | None, allocation_result: dict[str, Any] | None) -> list[str]:
    active_tickers = {_allocation_ticker(row) for row in _active_allocation_rows(allocation_result or {})}
    rows = []
    for row in data_freshness_rows or []:
        level = str(row.get("overall_data_freshness_level") or "").strip().upper()
        if level not in {"WATCH_FRESHNESS", "STALE"}:
            continue
        ticker = str(row.get("ticker") or "").strip()
        universe = str(row.get("universe") or "").strip().upper()
        if universe not in {"CORE", "CORE_PORTFOLIO"} and ticker not in active_tickers:
            continue
        rows.append(row)
    if not rows:
        return ["Données fragiles : Toutes les données sont fraîches ce run."]
    lines = ["Données fragiles :"]
    for row in rows[:5]:
        lines.append(
            f"- {row.get('ticker')} — {report_value(row.get('market_data_warning_flags'))} → "
            f"{compact_sentence(row.get('data_freshness_action'), 70)}"
        )
    return lines


def _is_core_freshness_row(row: dict[str, Any], core_tickers: set[str]) -> bool:
    ticker = str(row.get("ticker") or "").strip()
    universe = str(row.get("universe") or "").strip().upper()
    return universe in {"CORE", "CORE_PORTFOLIO"} or ticker in core_tickers


def _strong_data_coverage_line(analyses: dict[str, dict[str, Any]]) -> str:
    levels = []
    for row in analyses.values():
        level = (
            str(row.get("data_reliability_level") or "").strip().upper()
            or str(row.get("reliability_level") or "").strip().upper()
            or str(row.get("source_reliability") or "").strip().upper()
            or str((row.get("data_quality") or {}).get("reliability_level") or "").strip().upper()
            or str((row.get("reliability") or {}).get("level") or "").strip().upper()
        )
        if level and level not in {"", "NONE", "N/D", "DONNÉE PAS DISPO"}:
            if level in {"HIGH", "ROBUST", "SOLID"}:
                level = "STRONG"
            elif level in {"MEDIUM", "CAUTION", "WATCH"}:
                level = "MODERATE"
            elif level == "LOW":
                level = "WEAK"
            levels.append(level)
    if not levels:
        return ""
    strong_count = sum(1 for level in levels if level == "STRONG")
    moderate_count = sum(1 for level in levels if level == "MODERATE")
    weak_count = len(levels) - strong_count - moderate_count
    percent = round((strong_count / len(levels)) * 100)
    parts = [f"{percent}% des positions ont des données solides"]
    if moderate_count:
        parts.append(f"{moderate_count} avec limites")
    if weak_count:
        parts.append(f"{weak_count} fragile(s)")
    return " — ".join(parts) + "."


def _data_reliability_validation_lines(
    conflict_rows: list[dict[str, Any]],
    data_freshness_rows: list[dict[str, Any]],
    core_tickers: set[str],
) -> list[str]:
    lines = []
    listed_tickers: set[str] = set()
    sorted_conflicts = sorted(conflict_rows, key=lambda row: _ranking_float(row.get("conflict_count")), reverse=True)
    for row in sorted_conflicts[:5]:
        ticker = str(row.get("ticker_display") or row.get("ticker") or "").strip()
        if not ticker:
            continue
        listed_tickers.add(ticker)
        lines.append(
            f"- {ticker} — {report_value(row.get('conflict_count'))} conflits "
            f"({report_value(row.get('conflict_profile'))})"
        )
        lines.append(f"  → {compact_sentence(row.get('recommended_action'), 80)}")

    for row in data_freshness_rows:
        ticker = str(row.get("ticker") or "").strip()
        if not ticker or ticker in listed_tickers or not _is_core_freshness_row(row, core_tickers):
            continue
        flags = str(row.get("market_data_warning_flags") or "").upper()
        if "STALE_CACHE" not in flags and "CIRCUIT_OPEN" not in flags:
            continue
        listed_tickers.add(ticker)
        lines.append(f"- {ticker} — données périmées → Relancer avec --refresh-market-data avant grosse allocation")
        if len(listed_tickers) >= 10:
            break
    return lines


def _active_sources_line(source_health_rows: list[dict[str, Any]] | None) -> str:
    sources = []
    for row in source_health_rows or []:
        status = str(row.get("status") or "").strip().upper()
        if status in {"DISABLED", "NOT_USED"}:
            continue
        source = str(row.get("source") or row.get("name") or "").strip()
        if source:
            sources.append(source)
    if not sources:
        return "Sources : Yahoo Finance, SEC EDGAR, Banque du Canada (par défaut)."
    shown = ", ".join(sources[:8])
    suffix = f", ... (+{len(sources) - 8})" if len(sources) > 8 else ""
    return f"Sources : {shown}{suffix} ({len(sources)} sources actives ce run)"


def _account_summary_lines(rows: list[dict[str, Any]]) -> list[str]:
    clean = [row for row in rows if row]
    if not clean:
        return []
    total_row = next((row for row in clean if str(row.get("compte") or row.get("account_type") or "").upper() == "ALL_ACCOUNTS"), None)
    total_value = _first_non_empty(total_row or {}, "valeur_totale", "total_value_cad")
    account_parts = []
    account_total = 0.0
    position_lines = []
    for row in clean:
        account = str(row.get("compte") or row.get("account_type") or "").strip()
        if not account:
            continue
        value = _first_non_empty(row, "valeur_totale", "total_value_cad")
        if account.upper() != "ALL_ACCOUNTS" and value:
            account_parts.append(f"{account} : {value}")
            account_total += _triage_float(value)
        top_positions = _first_non_empty(row, "principales_positions", "top_positions")
        if account.upper() != "ALL_ACCOUNTS" and top_positions:
            position_lines.append(f"{account} : {top_positions}")
    lines = []
    if not total_value and account_total > 0:
        total_value = f"{account_total:,.2f} $".replace(",", " ")
    if total_value or account_parts:
        prefix = f"Valeur totale : {total_value}" if total_value else "Valeur totale : N/D"
        lines.append(" | ".join([prefix, *account_parts]))
    lines.extend(position_lines)
    return lines


def _latest_portfolio_change_line(rows: list[dict[str, Any]]) -> str:
    for row in rows:
        ticker = str(row.get("ticker") or "").strip()
        change = str(row.get("changement") or row.get("change_type") or "").strip()
        if not ticker and not change:
            continue
        date = str(row.get("date") or row.get("detected_at") or row.get("last_date") or "").strip()
        account = str(row.get("compte") or row.get("account_type") or "").strip()
        account_text = f" ({account})" if account else ""
        return f"Dernier changement : {date or 'date N/D'} — {ticker or 'N/D'}{account_text} {change or 'changement détecté'}"
    return ""


def _account_performance_lines(rows: list[dict[str, Any]]) -> list[str]:
    output = []
    status_labels = {
        "TWR_FLOW_ADJUSTED_AHEAD_OF_SP500": "devant le S&P 500",
        "TWR_FLOW_ADJUSTED_SIMILAR_TO_SP500": "proche du S&P 500",
        "TWR_FLOW_ADJUSTED_BEHIND_SP500": "derrière le S&P 500",
    }
    for row in rows:
        status = str(row.get("twr_status") or "").strip()
        if not status:
            continue
        account = str(row.get("account_type") or "Compte").strip()
        excess = _format_signed_percent(row.get("twr_excess_vs_sp500"))
        label = status_labels.get(status, compact_sentence(status, 30))
        output.append(f"- {account} : {excess} vs VFV depuis début du suivi → {label}")
    return output


def _portfolio_human_risk_lines(
    risk_rows: list[dict[str, Any]],
    hidden_cluster_rows: list[dict[str, Any]],
    market_regime: dict[str, Any],
) -> list[str]:
    lines = []
    regime = _market_regime_line(market_regime)
    if regime:
        lines.append(regime)
    lines.extend(_hidden_cluster_human_lines(hidden_cluster_rows))
    lines.extend(_currency_risk_lines(risk_rows))
    return lines


def _market_regime_line(market_regime: dict[str, Any]) -> str:
    if not market_regime:
        return ""
    status = str(market_regime.get("market_regime_status") or market_regime.get("status") or "").strip()
    score = report_value(market_regime.get("market_regime_score") or market_regime.get("score"))
    status_upper = status.upper()
    icon = "⚠️" if "BUBBLE_RISK" in status_upper or "HIGH_RISK" in status_upper else "🟡" if "WATCH" in status_upper or "MODERATE" in status_upper else "✅"
    implication = compact_sentence(
        market_regime.get("description")
        or market_regime.get("message")
        or market_regime.get("market_regime_interpretation"),
        80,
    )
    return f"{icon} Régime : {status or 'N/D'} ({score}/100) — {implication}"


def _hidden_cluster_human_lines(rows: list[dict[str, Any]]) -> list[str]:
    output = []
    seen: set[str] = set()
    for row in rows:
        level = str(row.get("niveau") or row.get("level") or "").strip().upper()
        if level != "EXTREME":
            continue
        exposure = _triage_float(row.get("exposition_cluster") or row.get("cluster_exposure"))
        if exposure > 1:
            exposure /= 100
        if exposure < 0.50:
            continue
        cluster_names = _cluster_names(row)
        for cluster in cluster_names:
            if not cluster or cluster in seen:
                continue
            seen.add(cluster)
            weight = round(exposure * 100)
            icon = "⚠️" if weight >= 60 else "🟡" if weight >= 45 else "✅"
            template = CLUSTER_LABELS.get(cluster, "{poids}% de ton portefeuille partage une exposition commune au cluster {nom}.")
            output.append(f"{icon} {template.format(poids=weight, nom=cluster)}")
    return output


def _currency_risk_lines(rows: list[dict[str, Any]]) -> list[str]:
    output = []
    for row in rows:
        risk_type = str(row.get("risk_type") or "").strip().lower()
        if risk_type not in {"devise", "currency"}:
            continue
        weight = _extract_percent(row.get("impact") or row.get("poids_concerné") or row.get("weight"))
        icon = "⚠️" if weight >= 80 else "🟡" if weight >= 50 else "✅"
        currency = _currency_label(row)
        output.append(f"{icon} Risque devise : {round(weight)}% de ton portefeuille est en {currency}. Une variation affecte directement ta valeur en CAD.")
    return output


def _cluster_names(row: dict[str, Any]) -> list[str]:
    raw = row.get("clusters") or row.get("cluster") or row.get("name") or ""
    if isinstance(raw, list):
        return [str(item).strip() for item in raw if str(item).strip()]
    text = str(raw).replace(";", ",")
    return [part.strip() for part in text.split(",") if part.strip()]


def _currency_label(row: dict[str, Any]) -> str:
    for key in ("devise", "currency"):
        value = str(row.get(key) or "").strip()
        if value:
            return value
    description = str(row.get("description") or "")
    if ":" in description:
        return description.split(":", 1)[0].strip()
    return "devise étrangère"


def _extract_percent(value: Any) -> float:
    text = str(value or "")
    digits = []
    current = ""
    for char in text:
        if char.isdigit() or char in {".", ","}:
            current += char
        elif current:
            digits.append(current)
            current = ""
    if current:
        digits.append(current)
    return _triage_float(digits[0]) if digits else 0.0


def _format_signed_percent(value: Any) -> str:
    number = _triage_float(value)
    if abs(number) <= 1.0 and number != 0:
        number *= 100
    sign = "+" if number > 0 else ""
    return f"{sign}{number:.1f}%"


def _first_non_empty(row: dict[str, Any], *keys: str) -> str:
    for key in keys:
        value = row.get(key)
        if value not in {None, ""}:
            return str(value)
    return ""


def build_ranking_section(
    analyses: dict,
    watchlist_analyses: dict,
    market_analyses: dict,
    discovery_analyses: dict,
    top_n: int = 15,
) -> str:
    merged = _merge_all_analyses_with_provenance(analyses, watchlist_analyses, market_analyses, discovery_analyses)
    drawdown_rows = _ranking_drawdown_opportunity_rows(merged, limit=8)
    watched_rows = _ranking_non_allocated_rows(merged, limit=min(10, top_n))
    lines = [
        "### Opportunités — drawdown avec thèse intacte",
        "",
    ]
    if drawdown_rows:
        lines.extend([_ranking_table(["ticker", "provenance", "score", "contexte_nouvelles", "lecture"], drawdown_rows), ""])
    else:
        lines.extend(["Aucune opportunité de drawdown identifiée ce run.", ""])
    lines.extend(["### Meilleurs titres surveillés (non alloués)", ""])
    if watched_rows:
        lines.extend(
            [
                _ranking_table(
                    ["rank", "ticker", "provenance", "score", "cagr_qualitatif", "vs_vfv", "pourquoi_pas_alloué"],
                    watched_rows,
                ),
                "",
            ]
        )
    else:
        lines.extend(["Aucun titre ne satisfait les critères de visibilité ce run.", ""])
    return "\n".join(lines).rstrip()


def _merge_all_analyses_with_provenance(
    analyses: dict,
    watchlist_analyses: dict,
    market_analyses: dict,
    discovery_analyses: dict,
) -> list[dict[str, Any]]:
    merged = []
    for label, universe in [
        ("Core", analyses or {}),
        ("Watchlist", watchlist_analyses or {}),
        ("Market", market_analyses or {}),
        ("Discovery", discovery_analyses or {}),
    ]:
        for row in universe.values():
            merged.append({**row, "_provenance": label})
    return merged


def _ranking_drawdown_opportunity_rows(rows: list[dict[str, Any]], *, limit: int) -> list[dict[str, Any]]:
    filtered = [
        row
        for row in rows
        if (
            str(row.get("quality_drawdown_status") or "").strip().upper() == "QUALITY_DRAWDOWN_OPPORTUNITY"
            or str(row.get("monitoring_status") or "").strip().upper() == "QUALITY_DRAWDOWN_OPPORTUNITY"
        )
        and str(row.get("thesis_status") or "").strip().upper() == "INTACT"
        and _sell_status_is_green(row)
    ]
    filtered = sorted(filtered, key=_ranking_score, reverse=True)[:limit]
    return [
        {
            "ticker": row.get("ticker_display") or row.get("ticker"),
            "provenance": row.get("_provenance"),
            "score": row.get("capital_allocation_score", row.get("score_total", row.get("conviction_score", ""))),
            "contexte_nouvelles": row.get("news_context_label") or row.get("contexte_nouvelles") or "—",
            "lecture": compact_sentence(
                row.get("quality_drawdown_label") or row.get("drawdown_lecture") or row.get("monitoring_note") or "",
                120,
            ),
        }
        for row in filtered
    ]


def _ranking_non_allocated_rows(rows: list[dict[str, Any]], *, limit: int) -> list[dict[str, Any]]:
    any_allocated = any(_allocation_marker_contains_allocated(row) for row in rows)
    filtered = []
    for row in rows:
        provenance = str(row.get("_provenance") or "")
        proximity = _promotion_proximity_numerator(row.get("promotion_proximity_score"))
        if str(row.get("thesis_status") or "").strip().upper() != "INTACT":
            continue
        if not _sell_status_is_green(row):
            continue
        if _allocation_marker_contains_allocated(row):
            continue
        if _ranking_score(row) < 70:
            continue
        if not (provenance == "Core" or proximity >= 10 or provenance == "Watchlist"):
            continue
        if provenance == "Market" and proximity < 10:
            continue
        if provenance == "Discovery" and not any(
            truthy_report_value(row.get(field))
            for field in ("morningstar_local", "bncd_local", "local_report_available")
        ):
            continue
        filtered.append(row)

    filtered = sorted(filtered, key=_ranking_score, reverse=True)[:limit]
    output = []
    for index, row in enumerate(filtered, start=1):
        output.append(
            {
                "rank": index,
                "ticker": row.get("ticker_display") or row.get("ticker"),
                "provenance": row.get("_provenance"),
                "score": row.get("capital_allocation_score", row.get("score_total", row.get("conviction_score", ""))),
                "cagr_qualitatif": row.get("expected_cagr_quality"),
                "vs_vfv": row.get("opportunity_cost_status"),
                "pourquoi_pas_alloué": compact_sentence(_ranking_not_allocated_reason(row, any_allocated), 60),
            }
        )
    return output


def _sell_status_is_green(row: dict[str, Any]) -> bool:
    return str(row.get("sell_status") or row.get("liquidation_status") or "").strip().upper() == "GREEN"


def _allocation_marker_contains_allocated(row: dict[str, Any]) -> bool:
    positive_actions = {"BUY / ADD", "ADD_WITH_MONITORING"}
    for key in (
        "allocation_decision",
        "final_position_action",
        "allocation_status",
        "watchlist_status",
        "candidate_status",
        "discovery_status",
    ):
        value = str(row.get(key) or "").strip().upper()
        if value in positive_actions or "ALLOCATED" in value:
            return True
    return False


def _promotion_proximity_numerator(value: Any) -> float:
    text = str(value or "").strip()
    if "/" in text:
        text = text.split("/", 1)[0]
    return _ranking_float(text)


def _ranking_not_allocated_reason(row: dict[str, Any], any_allocated: bool) -> str:
    category = str(row.get("blocking_reason_category") or "").strip()
    if category:
        return category
    for key in ("allocation_decision", "final_position_action", "watchlist_status", "candidate_status", "discovery_status"):
        value = str(row.get(key) or "").strip()
        if value and value.upper() != "ELIGIBLE_BUT_NOT_SELECTED":
            return value.split(";")[0].strip()
    if not any_allocated:
        return "Capital = 0 ce run"
    return "Seuil non atteint"


def build_instrument_profile_section(profiles: list[dict[str, Any]], *, compact: bool = False) -> str:
    if not profiles:
        return ""
    lines = [
        "## Ce que vous achetez",
        "",
        "Cette section est informative seulement: elle explique les titres recommandés sans modifier les scores, l’allocation, le sizing ni les règles de vente.",
        "",
    ]
    for profile in profiles:
        ticker = report_value(profile.get("ticker"))
        name = report_value(profile.get("name"))
        instrument_type = report_value(profile.get("instrument_type"))
        lines.extend([f"### {name} ({ticker})", ""])
        if str(profile.get("instrument_type") or "").lower() == "etf":
            lines.extend(
                [
                    f"- Type: ETF/FNB ({instrument_type})",
                    f"- Objectif / exposition: {report_value(profile.get('business_description'))}",
                    f"- Indice, stratégie ou catégorie: {report_value(profile.get('sector_or_category'))}",
                    f"- Principales positions: {report_value(profile.get('top_holdings'))}",
                    f"- Rôle dans le portefeuille: {report_value(profile.get('portfolio_role'))}",
                    f"- À surveiller: {report_value(profile.get('key_watch_items'))}",
                    f"- Source: {report_value(profile.get('source'))} | Confiance: {report_value(profile.get('source_confidence'))} | Statut: {report_value(profile.get('profile_status'))}",
                ]
            )
        else:
            lines.extend(
                [
                    f"- Type: {instrument_type}",
                    f"- Activité principale: {report_value(profile.get('business_description'))}",
                    f"- Comment l’entreprise gagne son argent: {report_value(profile.get('revenue_model_or_activity'))}",
                    f"- Secteur / industrie: {report_value(profile.get('sector_or_category'))} / {report_value(profile.get('industry'))}",
                    f"- Rôle dans le portefeuille: {report_value(profile.get('portfolio_role'))}",
                    f"- À surveiller: {report_value(profile.get('key_watch_items'))}",
                    f"- Source: {report_value(profile.get('source'))} | Confiance: {report_value(profile.get('source_confidence'))} | Statut: {report_value(profile.get('profile_status'))}",
                ]
            )
        if not compact and profile.get("missing_fields"):
            lines.append(f"- Champs à valider: {report_value(profile.get('missing_fields'))}")
        lines.append("")
    return "\n".join(lines).rstrip()


def align_full_report_navigation(lines: list[str]) -> list[str]:
    target_sections = [
        ("Résumé de la décision", {"Résumé exécutif", "Résumé de la décision"}),
        ("Justificatif de l'allocation", {"Allocation de la cotisation", "Justificatif de l'allocation"}),
        ("Signaux de vente & surveillance", {"Signaux de vente et surveillance", "Signaux de vente & surveillance"}),
        ("Ranking par univers", {"Core Portfolio Analysis", "Ranking par univers"}),
        ("Risques du portefeuille", {"Portfolio Risk", "Risques du portefeuille"}),
        ("Suivi & performance", {"Historique automatique des changements du portefeuille", "Suivi & performance"}),
        ("Surveillance externe", {"Watchlist Analysis", "Surveillance externe / Market Universe", "Surveillance externe"}),
    ]

    def heading_title(line: str) -> str | None:
        if not line.startswith("## ") or ". " not in line:
            return None
        return line.split(". ", 1)[1].strip()

    preamble: list[str] = []
    sections: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    for line in lines:
        title = heading_title(line)
        if title is not None:
            current = {"title": title, "lines": [line]}
            sections.append(current)
            continue
        if current is None:
            preamble.append(line)
        else:
            current["lines"].append(line)

    if not sections:
        return lines

    used_indexes: set[int] = set()
    ordered_sections: list[tuple[str, list[str]]] = []
    for target_title, accepted_titles in target_sections:
        for index, section in enumerate(sections):
            if index in used_indexes:
                continue
            if str(section.get("title")) in accepted_titles:
                used_indexes.add(index)
                ordered_sections.append((target_title, list(section.get("lines", []))))
                break

    for index, section in enumerate(sections):
        if index in used_indexes:
            continue
        ordered_sections.append((str(section.get("title") or ""), list(section.get("lines", []))))

    output = list(preamble)
    for section_number, (title, section_lines) in enumerate(ordered_sections, start=1):
        if not section_lines:
            continue
        section_lines[0] = f"## {section_number}. {title}"
        output.extend(section_lines)
    return output
