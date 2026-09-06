from __future__ import annotations

from .runtime_context import RUNTIME

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
    research_needed_rows: list[dict] | None = None,
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

    anomaly_count = sum(1 for row in anomaly_rows or [] if row)
    anomaly_icon = "⚠️" if anomaly_count else "🟢"
    anomaly_text = f"{anomaly_count} anomalie(s) détectée(s)" if anomaly_count else "Aucune anomalie détectée"

    counts_text = (
        f"Core {len(analyses or {})} | Watchlist {len(watchlist_analyses or {})} | "
        f"Market {len(market_analyses or {})} | Discovery {len(discovery_analyses or {})} titres analysés"
    )
    research_status, research_actions = _triage_research_report_maintenance_state(research_needed_rows)
    proxy_status, proxy_actions = _triage_proxy_calibration_maintenance_state()

    lines = [
        "---",
        f"{decision_icon} {decision_text}",
        "",
        f"{sell_icon} {sell_text}",
        "",
        f"{anomaly_icon} {anomaly_text}",
        "",
        research_status,
        "",
        proxy_status,
        "",
        f"📊 {counts_text}",
    ]
    system_action_lines = _triage_system_action_lines(
        score_stability,
        analyses,
        [*research_actions, *proxy_actions],
    )
    if system_action_lines:
        lines.extend(["", "─── ACTIONS SYSTÈME REQUISES ───", "", *system_action_lines])
    lines.append("---")
    return "\n".join(lines)


def _triage_system_action_lines(
    score_stability: dict[str, Any] | None,
    analyses: dict[str, dict[str, Any]] | None = None,
    maintenance_action_lines: list[str] | None = None,
) -> list[str]:
    lines: list[str] = []
    lines.extend(_triage_stale_market_data_lines(analyses))
    lines.extend(maintenance_action_lines or [])
    stability = score_stability or {}
    stability_status = str(stability.get("status") or "").strip().upper()
    stability_message = str(stability.get("message") or "").strip()
    if stability and stability_status in {"UNSTABLE", "WATCH"}:
        lines.append(f"⚠️ {_without_leading_warning_icon(stability_message or 'Stabilité des scores à vérifier.')}")
    return lines


def _triage_research_report_maintenance_state(
    research_needed_rows: list[dict[str, Any]] | None,
) -> tuple[str, list[str]]:
    from datetime import datetime as _Datetime

    rows = [row for row in research_needed_rows or [] if isinstance(row, dict)]
    tickers = {
        str(row.get("ticker") or "").strip()
        for row in rows
        if str(row.get("ticker") or "").strip()
    }
    if not tickers:
        return "🟢 Rapports BNCD/Morningstar : aucune recherche prioritaire active.", []

    report_dir = RUNTIME.path("data") / "research_reports" / "bncd_morningstar"
    report_files = []
    try:
        report_files = [
            path
            for path in report_dir.iterdir()
            if path.is_file() and path.suffix.lower() in {".pdf", ".txt", ".md"} and path.name != "README.md"
        ]
    except OSError:
        report_files = []

    reminder_days = 60
    if report_files:
        latest_timestamp = max(path.stat().st_mtime for path in report_files)
        latest_update = _Datetime.fromtimestamp(latest_timestamp)
        age_days = max(0, (_Datetime.now() - latest_update).days)
        if age_days < reminder_days:
            remaining_days = reminder_days - age_days
            return (
                "🟢 Rapports BNCD/Morningstar : "
                f"dépôt actualisé le {latest_update.date().isoformat()} ({age_days}j); "
                f"prochain rappel dans ~{remaining_days}j.",
                [],
            )

    high_priorities = {"HAUTE", "TRES_HAUTE", "TRÈS_HAUTE", "HIGH", "CRITICAL"}
    high_tickers = {
        str(row.get("ticker") or "").strip()
        for row in rows
        if str(row.get("ticker") or "").strip()
        and str(row.get("priority") or "").strip().upper() in high_priorities
    }
    priority_note = f" ({len(high_tickers)} priorité haute)" if high_tickers else ""
    status = "🟡 Rapports BNCD/Morningstar : mise à jour périodique recommandée."
    actions = [
        "⚠ RAPPORTS BNCD/MORNINGSTAR — RAFRAÎCHISSEMENT RECOMMANDÉ",
        f"{len(tickers)} titre(s) figurent dans la file de recherche{priority_note}.",
        "Action: lancer python3 main.py research-needed --limit 30 puis déposer les nouveaux rapports dans",
        "  data/research_reports/bncd_morningstar/",
    ]
    return status, actions


def _triage_proxy_calibration_maintenance_state() -> tuple[str, list[str]]:
    import csv as _csv
    from datetime import date as _Date
    from datetime import datetime as _Datetime

    calibration_path = RUNTIME.path("data") / "proxy_calibration.csv"
    if not calibration_path.exists():
        return (
            "🟡 Calibration des proxys : fichier de calibration absent.",
            [
                "⚠ DOCUMENT DE CALIBRATION DES PROXYS — CRÉATION REQUISE",
                "Action: créer data/proxy_calibration.csv puis lancer python3 main.py sync-manual-inputs",
            ],
        )

    try:
        with open(calibration_path, encoding="utf-8", newline="") as handle:
            rows = list(_csv.DictReader(handle))
    except Exception:
        return "⚪ Calibration des proxys : état indisponible.", []

    dated_tickers: list[tuple[str, int]] = []
    today = _Date.today()
    for row in rows:
        ticker = str(row.get("ticker") or "").strip()
        raw_date = str(row.get("source_date") or "").strip()
        try:
            source_date = _Datetime.strptime(raw_date[:10], "%Y-%m-%d").date()
        except (TypeError, ValueError):
            continue
        dated_tickers.append((ticker, max(0, (today - source_date).days)))

    if not dated_tickers:
        return (
            "🟡 Calibration des proxys : aucune date source exploitable.",
            [
                "⚠ DOCUMENT DE CALIBRATION DES PROXYS — DATES À COMPLÉTER",
                "Action: renseigner source_date dans data/proxy_calibration.csv puis lancer",
                "  python3 main.py sync-manual-inputs",
            ],
        )

    # [DECISION 2026-08-16] La calibration des proxys est une maintenance
    # structurelle annuelle : rappel un mois avant l'echeance, puis action.
    warn_days = 330
    stale_days = 365
    stale = [ticker for ticker, age in dated_tickers if age > stale_days]
    warning = [ticker for ticker, age in dated_tickers if warn_days < age <= stale_days]

    if stale:
        return (
            f"🔴 Calibration des proxys : {len(stale)} donnée(s) datée(s) expirée(s).",
            [
                "⚠ DOCUMENT DE CALIBRATION DES PROXYS — MISE À JOUR REQUISE",
                f"Données de calibration périmées (>{stale_days}j) pour: "
                f"{compact_list(stale, limit=12)}",
                "Action: mettre à jour data/proxy_calibration.csv puis lancer",
                "  python3 main.py sync-manual-inputs",
            ],
        )

    if warning:
        return (
            f"🟡 Calibration des proxys : {len(warning)} donnée(s) datée(s) approchent leur échéance.",
            [
                "⚠ DOCUMENT DE CALIBRATION DES PROXYS — MISE À JOUR RECOMMANDÉE BIENTÔT",
                f"Données de calibration âgées de {warn_days + 1} à {stale_days}j pour: "
                f"{compact_list(warning, limit=12)}",
                "Action: mettre à jour data/proxy_calibration.csv puis lancer",
                "  python3 main.py sync-manual-inputs",
            ],
        )

    oldest_age = max(age for _ticker, age in dated_tickers)
    remaining_days = max(0, warn_days + 1 - oldest_age)
    return (
        "🟢 Calibration des proxys : "
        f"à jour; prochain contrôle dans ~{remaining_days}j.",
        [],
    )


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
    data_status = str(
        decision_quality.get("data_status") or decision_quality.get("data_quality_status") or ""
    ).strip().upper()
    if data_status == "NOT_APPLICABLE":
        return (
            "Confiance   : N/A — aucune allocation active à évaluer; "
            "ce suivi sans capital ne mesure pas la certitude des conclusions d’investissement."
        )
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
        _model_health_signal_line("Walk-Forward", walk_forward_status, automated_operation=True),
        "",
        "Avec le runner de production, le walk-forward est prévu automatiquement après la génération "
        "du rapport, si l’analyse réussit et que le rapport compact est présent. "
        "Le statut ci-dessus reflète les artefacts disponibles à la génération, pas le résultat de cette étape. "
        "Consulter le journal du run ou sa notification pour son résultat. "
        "Une nouvelle exécution ne garantit pas de nouvelles périodes simulables.",
        "",
        _model_health_signal_line("Audit maître", full_audit_status, audit_style=True),
        "",
        _model_health_signal_line("Audit stabilité", model_audit_status, audit_style=True),
        "",
        "En production, la maintenance planifiée évalue les audits dus et lance l’audit maître, "
        "ou sinon l’audit de stabilité dû, après réussite des contrôles préalables et du health-check. "
        "Un statut absent ou périmé ne demande pas de lancement manuel dans ce workflow. "
        "En cas de blocage ou d’échec, consulter le journal de maintenance ou sa notification.",
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
        verdict = "✅ DONNÉES SUFFISANTES POUR LE SUIVI HABITUEL"
        practical_reading = "Aucune prudence supplémentaire liée aux données n'est requise ce run."
    elif stale_count <= 3 and conflict_count <= 4:
        verdict = "🟡 UTILISABLE POUR LE SUIVI HABITUEL"
        practical_reading = "Poursuis le workflow normal; vérifie seulement un titre signalé avant un achat inhabituellement important."
    else:
        verdict = "⚠️ PRUDENCE AVANT UN ACHAT IMPORTANT"
        practical_reading = "Le suivi habituel reste lisible; évite de surdimensionner un titre signalé sans rapport récent."

    lines = ["### Confiance dans les données", "", verdict, "", practical_reading, ""]
    coverage = _strong_data_coverage_line(analyses or {})
    if coverage:
        lines.extend([coverage, ""])
    lines.extend(
        [
            "**Action pour toi :** aucune validation technique champ par champ. Suis uniquement les rappels "
            "BNCD/Morningstar et calibration des proxys affichés en tête du rapport.",
            "",
            "#### Points de prudence avant un gros achat",
            "",
        ]
    )
    validation_lines = _data_reliability_validation_lines(conflict_rows, data_freshness_rows or [], core_tickers)
    lines.extend(validation_lines or ["Aucun point de prudence prioritaire ce run."])
    lines.extend(
        [
            "",
            "<details>",
            "<summary>Détails techniques des sources</summary>",
            "",
            _active_sources_line(source_health_rows),
            "",
            "> Le modèle combine des sources gratuites et locales; les écarts restent visibles pour audit.",
            "",
            "</details>",
        ]
    )
    return "\n".join(lines).rstrip()


def build_compact_external_monitoring_section(
    *,
    mode: str,
    allocation_result: dict | None = None,
    core_analyses: dict | None = None,
    watchlist_analyses: dict | None = None,
    market_analyses: dict | None = None,
    discovery_analyses: dict | None = None,
    external_candidate_rows: list[dict] | None = None,
    blocked_validation_rows: list[dict] | None = None,
    promotion_rows: list[dict] | None = None,
    external_etf_rows: list[dict] | None = None,
    policy_note: str = "",
) -> str:
    core_tickers = {str(ticker) for ticker in (core_analyses or {})}
    external_tickers = {
        str(ticker)
        for universe in (watchlist_analyses or {}, market_analyses or {}, discovery_analyses or {})
        for ticker in universe
        if str(ticker) not in core_tickers
    }
    allocated_external = []
    for row in _active_allocation_rows(allocation_result or {}):
        ticker = _allocation_ticker(row)
        universe = str(row.get("universe") or "").strip().upper()
        if ticker not in external_tickers and universe not in {"WATCHLIST", "MARKET_SCANNER", "DISCOVERY_IDEAS"}:
            continue
        allocated_external.append((ticker, _allocation_amount(row)))

    candidates = [
        row
        for row in external_candidate_rows or []
        if str(row.get("ticker") or "").strip()
        and str(row.get("status") or "").strip() != "AUCUNE_CANDIDATE_EXTERNE_PRIORITAIRE"
    ]
    blocked = [
        row
        for row in blocked_validation_rows or []
        if str(row.get("ticker") or "").strip()
        and str(row.get("ticker") or "").strip() != "AUCUN_CANDIDAT_BLOQUE"
    ]

    lines = ["## 6. Radar externe", "", "### Ce qu’il faut retenir", ""]
    if allocated_external:
        allocation_text = " | ".join(f"{ticker} {_format_money(amount)}" for ticker, amount in allocated_external)
        lines.extend(
            [
                f"🟢 **Allocation externe active :** {allocation_text}.",
                "Le moteur l’a déjà intégrée à la recommandation de la section 1; aucune promotion manuelle n’est requise.",
            ]
        )
    else:
        lines.append("⚪ **Aucun titre externe financé dans cette recommandation.**")

    lines.append("")
    if candidates:
        shown = ", ".join(str(row.get("ticker")) for row in candidates[:3])
        lines.append(f"🟡 **À garder sur le radar :** {shown}. Ce sont des titres surveillés, pas des achats à exécuter.")
    else:
        lines.append("✅ **Radar calme :** aucun candidat externe prioritaire ce run.")

    lines.append("")
    if blocked:
        blocked_text = ", ".join(str(row.get("ticker")) for row in blocked[:5])
        lines.append(f"⚠️ **Rapport requis avant allocation :** {blocked_text}.")
    else:
        lines.append("✅ **Validation personnelle :** aucun candidat proche d’une allocation n’est bloqué par un rapport manquant.")

    lines.extend(["", _external_user_action_line(allocated_external, blocked), ""])
    if candidates:
        lines.extend(
            [
                "### Prochains candidats surveillés",
                "",
                "| candidat | provenance | lecture |",
                "| --- | --- | --- |",
            ]
        )
        for row in candidates[:3]:
            lines.append(
                "| "
                + " | ".join(
                    [
                        escape_markdown_cell(row.get("ticker")),
                        escape_markdown_cell(_external_source_label(row.get("source"))),
                        escape_markdown_cell(_external_status_label(row.get("status"))),
                    ]
                )
                + " |"
            )
        lines.extend(["", "Ils seront réévalués automatiquement aux prochains runs.", ""])

    lines.extend(
        [
            "<details>",
            "<summary>Comprendre le radar et voir les détails techniques</summary>",
            "",
            policy_note or f"Le mode `{mode}` applique ses filtres actifs avant toute allocation externe.",
            "",
            "#### Tous les candidats externes affichés",
            "",
            *_compact_external_detail_table(candidates),
            "",
            "#### Promotions vers le Core Portfolio",
            "",
            *_compact_promotion_detail_table(promotion_rows or []),
            "",
            "#### ETF externes",
            "",
            *_compact_external_etf_detail_table(external_etf_rows or []),
            "",
            "</details>",
        ]
    )
    return "\n".join(lines).rstrip()


def _external_user_action_line(allocated_external: list[tuple[str, float]], blocked: list[dict]) -> str:
    if allocated_external and blocked:
        return (
            "**Action pour toi :** exécuter uniquement les montants de la section 1; actualiser un rapport "
            "BNCD/Morningstar seulement pour un candidat bloqué que tu souhaites approfondir."
        )
    if allocated_external:
        return "**Action pour toi :** exécuter uniquement les montants déjà indiqués dans la section 1."
    if blocked:
        return (
            "**Action pour toi :** aucune transaction. Actualiser un rapport BNCD/Morningstar seulement si "
            "tu souhaites approfondir l’un des candidats bloqués."
        )
    return "**Action pour toi :** aucune. Le modèle réévaluera automatiquement ces titres aux prochains runs."


def _external_source_label(value: Any) -> str:
    return {
        "MARKET_UNIVERSE": "Market",
        "MARKET_SCANNER": "Market",
        "DISCOVERY": "Discovery",
        "DISCOVERY_IDEAS": "Discovery",
        "WATCHLIST": "Watchlist",
    }.get(str(value or "").strip().upper(), str(value or "N/D"))


def _external_status_label(value: Any) -> str:
    return {
        "PROMISING_BUT_INCOMPLETE": "Prometteur, mais pas encore retenu",
        "MANUAL_REVIEW_TOP_CANDIDATE": "Revue prioritaire, sans achat automatique",
        "ADD_TO_MARKET_UNIVERSE_REVIEW": "Idée à intégrer au radar Market",
    }.get(str(value or "").strip().upper(), compact_sentence(value, 90))


def _compact_external_detail_table(rows: list[dict]) -> list[str]:
    if not rows:
        return ["Aucun candidat externe prioritaire."]
    lines = ["| provenance | ticker | statut | score | raison |", "| --- | --- | --- | --- | --- |"]
    for row in rows:
        lines.append(
            "| "
            + " | ".join(
                escape_markdown_cell(row.get(key)) for key in ("source", "ticker", "status", "score", "raison")
            )
            + " |"
        )
    return lines


def _compact_promotion_detail_table(rows: list[dict]) -> list[str]:
    if not rows:
        return ["Aucune promotion fondée vers le Core Portfolio."]
    lines = ["| source | ticker | statut | prochaine étape |", "| --- | --- | --- | --- |"]
    for row in rows:
        lines.append(
            "| "
            + " | ".join(
                escape_markdown_cell(row.get(key)) for key in ("source", "ticker", "statut", "prochaine_étape")
            )
            + " |"
        )
    return lines


def _compact_external_etf_detail_table(rows: list[dict]) -> list[str]:
    meaningful = [row for row in rows if str(row.get("ticker") or "").strip()]
    if not meaningful:
        return ["Aucun ETF externe admissible ou à surveiller."]
    lines = ["| ticker | statut | score | fit mode |", "| --- | --- | --- | --- |"]
    for row in meaningful:
        lines.append(
            "| "
            + " | ".join(
                escape_markdown_cell(row.get(key)) for key in ("ticker", "statut", "score", "fit_mode")
            )
            + " |"
        )
    return lines


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
    portfolio_risk_rows = _portfolio_human_risk_rows(risk_rows or [], hidden_cluster_rows or [], market_regime or {})
    if portfolio_risk_rows:
        lines.append(_ranking_table(["risque", "niveau", "exposition", "lecture"], portfolio_risk_rows))
        lines.extend(["", "★ Risque prioritaire à considérer; les autres indicateurs restent informatifs."])
    else:
        lines.append("Aucun risque majeur compact à afficher ce run.")
    return "\n".join(lines).rstrip()


CLUSTER_TABLE_DETAILS = {
    "RATES_SENSITIVE_GROWTH": (
        "Sensibilité aux taux",
        "Les positions concernées peuvent réagir ensemble aux variations de taux.",
    ),
    "MEGA_CAP_TECH_PLATFORMS": (
        "Grandes plateformes technologiques",
        "Une même tendance technologique peut affecter plusieurs positions simultanément.",
    ),
    "AI_SEMI_CLOUD_INFRA": (
        "IA / semi-conducteurs / cloud",
        "Le portefeuille partage une exposition importante à ce même thème de croissance.",
    ),
    "INDUSTRIAL_ELECTRIFICATION_AUTOMATION": (
        "Électrification et automatisation",
        "Plusieurs positions dépendent du même cycle d'investissement industriel.",
    ),
    "PAYMENTS_FINANCIAL_NETWORKS": (
        "Paiements et réseaux financiers",
        "Plusieurs positions partagent les mêmes moteurs économiques et réglementaires.",
    ),
    "CANADA_CAD_CLUSTER": (
        "Marché canadien et dollar CAD",
        "Une même évolution économique canadienne peut affecter plusieurs positions.",
    ),
    "HEALTHCARE_INNOVATION": (
        "Innovation en santé",
        "Plusieurs positions peuvent réagir aux mêmes cycles cliniques et réglementaires.",
    ),
}


def _model_health_signal_line(
    label: str,
    signal: dict[str, Any] | None,
    *,
    audit_style: bool = False,
    automated_operation: bool = False,
) -> str:
    if not isinstance(signal, dict) or not signal:
        return f"⚠️ {label:<16}: — Non disponible"
    status = str(signal.get("status") or "N/D").strip() or "N/D"
    icon = "✅" if any(token in status.upper() for token in {"STABLE", "HEALTHY", "OK", "PASS"}) else "⚠️"
    if audit_style:
        message = _audit_compact_message(signal)
    else:
        message = _clean_signal_message(str(signal.get("message") or ""), status)
        if automated_operation:
            message = _operational_status_message(message)
        message = compact_sentence(message, 90)
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
    message = _clean_signal_message(str(signal.get("message") or ""), str(signal.get("status") or ""))
    return compact_sentence(_operational_status_message(message), 90)


def _operational_status_message(message: str) -> str:
    """Keep artifact facts; compact workflow guidance replaces legacy CLI advice.

    Signal payloads remain unchanged for CLI users and maintenance planning.
    Remove advice before truncation so even short/absent signals cannot leak a
    manual command, or present the 21-day stale threshold as a runner schedule.
    """
    for marker in ("Continuer à relancer", "Relancer", "Lancer", "Prochaine exécution"):
        index = message.casefold().find(marker.casefold())
        if index >= 0:
            message = message[:index].rstrip()
    return message


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
    excluded_count = 0
    for row in analyses.values():
        level = (
            str(row.get("data_reliability_level") or "").strip().upper()
            or str(row.get("reliability_level") or "").strip().upper()
            or str(row.get("source_reliability") or "").strip().upper()
            or str((row.get("data_quality") or {}).get("reliability_level") or "").strip().upper()
            or str((row.get("reliability") or {}).get("level") or "").strip().upper()
        )
        if level in {"ETF", "BENCHMARK", "ETF_OR_BENCHMARK", "ETF_OR_FUND", "NOT_APPLICABLE"}:
            excluded_count += 1
            continue
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
    parts = [f"{percent}% des {len(levels)} entreprises détenues ont des données solides"]
    if moderate_count:
        parts.append(f"{moderate_count} avec limites")
    if weak_count:
        parts.append(f"{weak_count} fragile(s)")
    result = " — ".join(parts) + "."
    if excluded_count:
        result += f" {excluded_count} ETF/indice(s) exclus de cette mesure fondamentale."
    return result


def _data_reliability_validation_lines(
    conflict_rows: list[dict[str, Any]],
    data_freshness_rows: list[dict[str, Any]],
    core_tickers: set[str],
) -> list[str]:
    table_rows = []
    listed_tickers: set[str] = set()
    sorted_conflicts = sorted(conflict_rows, key=lambda row: _ranking_float(row.get("conflict_count")), reverse=True)
    for row in sorted_conflicts[:5]:
        ticker = str(row.get("ticker_display") or row.get("ticker") or "").strip()
        if not ticker:
            continue
        listed_tickers.add(ticker)
        table_rows.append(
            {
                "titre": ticker,
                "signal": f"{report_value(row.get('conflict_count'))} écart(s) entre sources",
                "quand_agir": "Seulement avant un achat important",
            }
        )

    for row in data_freshness_rows:
        ticker = str(row.get("ticker") or "").strip()
        if not ticker or ticker in listed_tickers or not _is_core_freshness_row(row, core_tickers):
            continue
        flags = str(row.get("market_data_warning_flags") or "").upper()
        if "STALE_CACHE" not in flags and "CIRCUIT_OPEN" not in flags:
            continue
        listed_tickers.add(ticker)
        table_rows.append(
            {
                "titre": ticker,
                "signal": "Données de marché périmées",
                "quand_agir": "Rafraîchir avant un achat important",
            }
        )
        if len(listed_tickers) >= 10:
            break
    if not table_rows:
        return []
    return [
        _ranking_table(["titre", "signal", "quand_agir"], table_rows),
        "",
        "Action commune : si l'un de ces titres reçoit un montant important, actualiser son rapport "
        "BNCD/Morningstar; sinon aucune action immédiate.",
    ]


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


def _portfolio_human_risk_rows(
    risk_rows: list[dict[str, Any]],
    hidden_cluster_rows: list[dict[str, Any]],
    market_regime: dict[str, Any],
) -> list[dict[str, str]]:
    rows = []
    regime = _market_regime_risk_row(market_regime)
    if regime:
        rows.append(regime)
    cluster_rows = _portfolio_cluster_risk_rows(risk_rows)
    rows.extend(cluster_rows or _hidden_cluster_human_rows(hidden_cluster_rows))
    rows.extend(_currency_risk_rows(risk_rows))
    return rows


def _market_regime_risk_row(market_regime: dict[str, Any]) -> dict[str, str]:
    if not market_regime:
        return {}
    status = str(market_regime.get("market_regime_status") or market_regime.get("status") or "").strip()
    score = report_value(market_regime.get("market_regime_score") or market_regime.get("score"))
    status_upper = status.upper()
    level = (
        "⚠️ Élevé"
        if "BUBBLE_RISK" in status_upper or "HIGH_RISK" in status_upper
        else "🟡 À surveiller"
        if "WATCH" in status_upper or "MODERATE" in status_upper
        else "✅ Normal"
    )
    implication = compact_sentence(
        market_regime.get("description")
        or market_regime.get("message")
        or market_regime.get("market_regime_interpretation"),
        80,
    )
    status_labels = {
        "BUBBLE_RISK": "Risque de bulle",
        "HIGH_RISK": "Risque de marché élevé",
        "WATCH": "Régime à surveiller",
        "MODERATE": "Risque de marché modéré",
    }
    label = status_labels.get(status_upper, status or "Régime de marché")
    return {
        "risque": f"★ {label}" if level == "⚠️ Élevé" else label,
        "niveau": level,
        "exposition": f"{score}/100",
        "lecture": implication,
    }


def _hidden_cluster_human_rows(rows: list[dict[str, Any]]) -> list[dict[str, str]]:
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
            weight = exposure * 100
            label, reading = _cluster_table_details(cluster)
            output.append(_portfolio_risk_row(label, weight, reading))
    return output


def _portfolio_cluster_risk_rows(rows: list[dict[str, Any]]) -> list[dict[str, str]]:
    output = []
    seen: set[str] = set()
    for row in rows:
        risk_type = str(row.get("risk_type") or "").strip().lower()
        if "cluster" not in risk_type:
            continue
        description = str(row.get("description") or "").strip()
        cluster = description.split(":", 1)[0].strip()
        if not cluster or cluster in seen:
            continue
        weight = _extract_percent(row.get("impact") or row.get("weight"))
        if weight <= 0:
            continue
        seen.add(cluster)
        label, reading = _cluster_table_details(cluster)
        output.append(_portfolio_risk_row(label, weight, reading))
    return output


def _currency_risk_rows(rows: list[dict[str, Any]]) -> list[dict[str, str]]:
    output = []
    for row in rows:
        risk_type = str(row.get("risk_type") or "").strip().lower()
        if risk_type not in {"devise", "currency"}:
            continue
        weight = _extract_percent(row.get("impact") or row.get("poids_concerné") or row.get("weight"))
        currency = _currency_label(row)
        output.append(
            _portfolio_risk_row(
                f"Devise {currency}",
                weight,
                f"Une variation du {currency} affecte directement la valeur du portefeuille en CAD.",
                high_threshold=80,
                watch_threshold=50,
            )
        )
    return output


def _cluster_table_details(cluster: str) -> tuple[str, str]:
    return CLUSTER_TABLE_DETAILS.get(
        cluster,
        (
            cluster.replace("_", " ").title(),
            "Plusieurs positions partagent cette même exposition.",
        ),
    )


def _portfolio_risk_row(
    label: str,
    weight: float,
    reading: str,
    *,
    high_threshold: float = 60,
    watch_threshold: float = 45,
) -> dict[str, str]:
    level = "⚠️ Élevé" if weight >= high_threshold else "🟡 À surveiller" if weight >= watch_threshold else "✅ Modéré"
    return {
        "risque": f"★ {label}" if level == "⚠️ Élevé" else label,
        "niveau": level,
        "exposition": _format_percentage(weight / 100),
        "lecture": reading,
    }


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
        "**Comment lire ces deux listes**",
        "",
        "- **Drawdown** : le prix a fortement baissé, mais la thèse reste intacte. C'est un signal de prix intéressant, pas une recommandation d'achat automatique.",
        "- **Meilleurs titres non alloués** : classement général des candidats solides que le modèle n'a pas retenus. La dernière colonne indique le blocage.",
        "- Un même titre peut apparaître dans les deux listes : son prix peut être intéressant tout en restant bloqué par un autre garde-fou.",
        "",
        "### Opportunités — drawdown avec thèse intacte",
        "",
    ]
    if drawdown_rows:
        lines.extend([_ranking_table(["ticker", "provenance", "score", "contexte_nouvelles", "lecture"], drawdown_rows), ""])
    else:
        lines.extend(["Aucune opportunité de drawdown identifiée ce run.", ""])
    lines.extend(["### Meilleurs titres surveillés (non alloués — classement général)", ""])
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
            "contexte_nouvelles": (
                row.get("news_context_label")
                or row.get("news_context_status")
                or row.get("contexte_nouvelles")
                or "—"
            ),
            "lecture": compact_sentence(
                row.get("quality_drawdown_label")
                or row.get("quality_drawdown_reason")
                or row.get("drawdown_lecture")
                or row.get("monitoring_note")
                or "",
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
        labels = {
            "DATA_INSUFFICIENT": "Données insuffisantes",
            "CYCLE_RISK": "Risque cyclique trop élevé",
            "NOT_SUPERIOR_TO_CORE": "Pas assez supérieur aux positions actuelles",
            "FUNDAMENTALS_BELOW_BAR": "Fondamentaux sous le seuil",
            "PROMOTION_SLOT_LIMIT": "Moins prioritaire que les meilleurs candidats",
            "UNKNOWN": "Raison à confirmer",
        }
        return labels.get(category.upper(), category)
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
