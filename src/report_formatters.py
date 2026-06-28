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
