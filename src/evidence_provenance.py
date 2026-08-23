from __future__ import annotations

from datetime import date, datetime
from typing import Any


HUMAN_MANUAL = "HUMAN_MANUAL"
RESEARCH_REPORT = "RESEARCH_REPORT"
OFFICIAL_CURRENT_DATA = "OFFICIAL_CURRENT_DATA"
AUTO_ESTIMATED = "AUTO_ESTIMATED"
PROXY_CALIBRATION_SYNC = "PROXY_CALIBRATION_SYNC"

CALIBRATION_CONTEXT_FIELDS = {"manual_confidence_level", "notes"}


# Calibration observations expire according to their economic persistence.
# Valuation and forward-looking fields move quickly; balance-sheet and margin
# fields are reviewed on a quarterly/semiannual cadence; durable qualitative
# fields receive a longer, but still finite, life.
CALIBRATION_FIELD_MAX_AGE_DAYS = {
    "forward_pe_manual": 90,
    "peg_manual": 90,
    "fair_value": 90,
    "eps_growth_estimated_3_5y": 90,
    "valuation_vs_5y_avg_ok": 90,
    "forward_pe_growth_acceptable": 90,
    "balance_sheet_strong": 120,
    "margin_or_profitability_under_pressure": 120,
    "net_margin_stable_or_expanding": 180,
    "sector_cagr_estimated": 365,
    "roic_5y_avg": 548,
    "eps_growth_5y": 548,
    "moat_clear": 730,
    "management_quality_good": 730,
}


def field_freshness(
    field: str,
    source_date: Any,
    today: date | None = None,
) -> dict[str, Any]:
    today = today or date.today()
    parsed = parse_source_date(source_date)
    max_age_days = CALIBRATION_FIELD_MAX_AGE_DAYS.get(field, 180)
    if parsed is None:
        return {
            "status": "UNKNOWN_DATE",
            "source_date": None,
            "age_days": None,
            "max_age_days": max_age_days,
            "currently_authoritative": False,
        }
    age_days = max(0, (today - parsed).days)
    status = "CURRENT" if age_days <= max_age_days else "STALE"
    return {
        "status": status,
        "source_date": parsed.isoformat(),
        "age_days": age_days,
        "max_age_days": max_age_days,
        "currently_authoritative": status == "CURRENT",
    }


def calibration_field_freshness(
    field: str,
    source_date: Any,
    today: date | None = None,
) -> dict[str, Any]:
    return field_freshness(field, source_date, today=today)


def field_is_confirmed(payload: dict[str, Any], field: str) -> bool:
    manual_fields = field_set(payload.get("manual_override_fields"))
    research_fields = field_set(payload.get("research_report_fields"))
    official_fields = field_set(payload.get("official_confirmed_manual_fields"))
    calibration_fields = field_set(payload.get("calibration_synced_fields")) | field_set(
        payload.get("calibration_applied_fields")
    )
    auto_fields = field_set(payload.get("auto_estimated_fields"))

    if field in manual_fields:
        return True
    if field in research_fields:
        return research_field_is_currently_authoritative(payload, field)
    if field in official_fields:
        return True
    if field in calibration_fields or field in auto_fields:
        return False
    # Preserve the established contract for direct, already-confirmed payloads
    # that predate field-level provenance metadata.
    return True


def research_field_is_currently_authoritative(
    payload: dict[str, Any],
    field: str,
    today: date | None = None,
) -> bool:
    if research_field_confidence(payload, field) == "LOW":
        return False
    freshness = research_field_freshness(payload, field, today=today)
    # Legacy payloads without any P1B field-date/freshness metadata retain the
    # established confirmation contract. Newly parsed P1B evidence always has
    # this metadata and therefore fails closed on stale or unknown dates.
    return freshness is None or bool(freshness.get("currently_authoritative"))


def research_field_freshness(
    payload: dict[str, Any],
    field: str,
    today: date | None = None,
) -> dict[str, Any] | None:
    values = payload.get("research_report_field_freshness")
    if isinstance(values, dict) and field in values and isinstance(values.get(field), dict):
        metadata = dict(values[field])
        status = str(metadata.get("status") or "UNKNOWN_DATE").strip().upper()
        metadata["status"] = status
        metadata["currently_authoritative"] = status == "CURRENT" and bool(
            metadata.get("currently_authoritative", True)
        )
        return metadata

    field_dates = payload.get("research_report_field_report_dates")
    has_p1b_date_metadata = bool(payload.get("research_report_freshness_policy_applied")) or (
        isinstance(field_dates, dict) and field in field_dates
    )
    if not has_p1b_date_metadata:
        return None
    source_date = field_dates.get(field) if isinstance(field_dates, dict) else None
    if not source_date:
        report_dates = payload.get("research_report_dates") or []
        if isinstance(report_dates, str):
            report_dates = [part.strip() for part in report_dates.split(",") if part.strip()]
        parsed_dates = [parse_source_date(value) for value in report_dates]
        parsed_dates = [value for value in parsed_dates if value is not None]
        source_date = max(parsed_dates).isoformat() if parsed_dates else None
    return field_freshness(field, source_date, today=today)


def research_field_confidence(payload: dict[str, Any], field: str) -> str:
    values = payload.get("research_report_field_confidence") or {}
    if isinstance(values, dict):
        confidence = str(values.get(field) or "").strip().upper()
        return confidence or "MEDIUM"
    text = str(values or "")
    for part in text.replace(",", ";").split(";"):
        if ":" not in part:
            continue
        key, value = part.split(":", 1)
        if key.strip() == field:
            return str(value).strip().upper() or "MEDIUM"
    return "MEDIUM"


def field_set(value: Any) -> set[str]:
    if not value:
        return set()
    if isinstance(value, str):
        return {part.strip() for part in value.replace(";", ",").split(",") if part.strip()}
    return {str(part).strip() for part in value if str(part).strip()}


def parse_source_date(value: Any) -> date | None:
    text = str(value or "").strip()
    if not text or len(text) == 4:
        return None
    for fmt in ("%Y-%m-%d", "%Y/%m/%d"):
        try:
            return datetime.strptime(text[:10], fmt).date()
        except ValueError:
            continue
    return None


def values_equivalent(left: Any, right: Any) -> bool:
    if isinstance(left, bool) or isinstance(right, bool):
        return _bool_value(left) is not None and _bool_value(left) == _bool_value(right)
    left_number = _number_value(left)
    right_number = _number_value(right)
    if left_number is not None and right_number is not None:
        return abs(left_number - right_number) <= 1e-9
    return str(left or "").strip().casefold() == str(right or "").strip().casefold()


def _bool_value(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    text = str(value or "").strip().lower()
    if text in {"true", "yes", "oui", "1"}:
        return True
    if text in {"false", "no", "non", "0"}:
        return False
    return None


def _number_value(value: Any) -> float | None:
    if isinstance(value, bool) or value is None or value == "":
        return None
    try:
        return float(str(value).strip().replace("%", "").replace(",", "."))
    except (TypeError, ValueError):
        return None
