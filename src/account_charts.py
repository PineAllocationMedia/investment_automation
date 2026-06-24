from __future__ import annotations

import html
import math
import re
from pathlib import Path
from typing import Any

from .utils import money, pct, safe_float


ACCOUNT_CHART_COLUMNS = [
    "account_type",
    "total_value_cad",
    "positions_count",
    "chart_path",
    "top_positions",
    "note",
]

CHART_RELATIVE_DIR = "charts"
SMALL_POSITION_THRESHOLD = 0.03
MAX_SLICES = 8

_COLORS = [
    "#2563eb",
    "#16a34a",
    "#dc2626",
    "#9333ea",
    "#f59e0b",
    "#0891b2",
    "#db2777",
    "#4b5563",
]


def build_account_allocation_chart_rows(
    account_rows: list[dict[str, Any]],
    charts_dir: str | Path,
    *,
    small_position_threshold: float = SMALL_POSITION_THRESHOLD,
    max_slices: int = MAX_SLICES,
) -> list[dict[str, Any]]:
    """Generate SVG pie charts for each account and return report rows."""
    charts_path = Path(charts_dir)
    charts_path.mkdir(parents=True, exist_ok=True)
    _clear_old_account_charts(charts_path)

    accounts = _aggregate_by_account(account_rows)
    output: list[dict[str, Any]] = []
    for account_type, holdings in sorted(accounts.items()):
        total_value = sum(value for _, value in holdings)
        if total_value <= 0:
            continue
        slices = _group_slices(holdings, total_value, small_position_threshold, max_slices)
        filename = f"account_{_safe_filename(account_type)}.svg"
        path = charts_path / filename
        path.write_text(_pie_svg(account_type, slices, total_value, len(holdings)), encoding="utf-8")
        output.append(
            {
                "account_type": account_type,
                "total_value_cad": round(total_value, 2),
                "positions_count": len(holdings),
                "chart_path": f"{CHART_RELATIVE_DIR}/{filename}",
                "top_positions": _top_positions_text(holdings, total_value),
                "note": _chart_note(slices, len(holdings)),
            }
        )
    return output


def account_chart_rows_for_report(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            **row,
            "total_value_cad": money(safe_float(row.get("total_value_cad"))),
        }
        for row in rows
    ]


def account_charts_markdown(rows: list[dict[str, Any]]) -> list[str]:
    if not rows:
        return [
            "### Répartition actuelle par compte",
            "",
            "Aucun graphique généré: aucune position avec une valeur positive n’a été trouvée par compte.",
            "",
        ]

    lines = [
        "### Répartition actuelle par compte",
        "",
        "Ces diagrammes utilisent la valeur actuelle estimée en CAD. Les petites lignes peuvent être regroupées dans `Autres` pour garder le graphique lisible.",
        "",
    ]
    for row in rows:
        account_type = row.get("account_type") or "UNKNOWN"
        chart_path = row.get("chart_path")
        lines.extend(
            [
                f"#### {account_type}",
                "",
                f"![Répartition du compte {account_type}]({chart_path})",
                "",
            ]
        )
    return lines


def _aggregate_by_account(rows: list[dict[str, Any]]) -> dict[str, list[tuple[str, float]]]:
    buckets: dict[str, dict[str, float]] = {}
    for row in rows:
        ticker = str(row.get("ticker") or "").strip().upper()
        account_type = str(row.get("account_type") or "UNKNOWN").strip().upper() or "UNKNOWN"
        value = safe_float(row.get("current_value")) or safe_float(row.get("current_value_cad")) or 0.0
        if not ticker or value <= 0:
            continue
        account_bucket = buckets.setdefault(account_type, {})
        account_bucket[ticker] = account_bucket.get(ticker, 0.0) + value
    return {
        account_type: sorted(holdings.items(), key=lambda item: item[1], reverse=True)
        for account_type, holdings in buckets.items()
    }


def _group_slices(
    holdings: list[tuple[str, float]],
    total_value: float,
    small_position_threshold: float,
    max_slices: int,
) -> list[dict[str, Any]]:
    if len(holdings) <= 1:
        return [{"label": holdings[0][0], "value": holdings[0][1]}] if holdings else []

    keep_limit = max(1, max_slices - 1)
    kept: list[tuple[str, float]] = []
    other_value = 0.0
    for index, (ticker, value) in enumerate(holdings):
        weight = value / total_value if total_value > 0 else 0.0
        if index < keep_limit and weight >= small_position_threshold:
            kept.append((ticker, value))
        else:
            other_value += value
    if not kept and holdings:
        ticker, value = holdings[0]
        kept.append((ticker, value))
        other_value = sum(v for _, v in holdings[1:])
    slices = [{"label": ticker, "value": value} for ticker, value in kept]
    if other_value > 0:
        slices.append({"label": "Autres", "value": other_value})
    return slices


def _pie_svg(account_type: str, slices: list[dict[str, Any]], total_value: float, positions_count: int) -> str:
    width = 760
    height = max(360, 150 + 30 * len(slices))
    cx = 170
    cy = 190
    radius = 118
    legend_x = 330
    legend_y = 112
    title = html.escape(f"Répartition du compte {account_type}")
    subtitle = html.escape(f"Valeur totale estimée: {money(total_value)} CAD | Positions: {positions_count}")

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="{title}">',
        '<rect width="100%" height="100%" fill="#ffffff"/>',
        f'<text x="28" y="38" font-family="Arial, sans-serif" font-size="22" font-weight="700" fill="#111827">{title}</text>',
        f'<text x="28" y="66" font-family="Arial, sans-serif" font-size="13" fill="#4b5563">{subtitle}</text>',
    ]

    start_angle = -90.0
    if len(slices) == 1:
        color = _COLORS[0]
        parts.append(f'<circle cx="{cx}" cy="{cy}" r="{radius}" fill="{color}"/>')
    else:
        for index, item in enumerate(slices):
            value = safe_float(item.get("value")) or 0.0
            angle = 360.0 * value / total_value if total_value > 0 else 0.0
            end_angle = start_angle + angle
            parts.append(_slice_path(cx, cy, radius, start_angle, end_angle, _COLORS[index % len(_COLORS)]))
            start_angle = end_angle

    for index, item in enumerate(slices):
        label = html.escape(str(item.get("label") or ""))
        value = safe_float(item.get("value")) or 0.0
        weight = value / total_value if total_value > 0 else 0.0
        y = legend_y + index * 30
        color = _COLORS[index % len(_COLORS)]
        parts.extend(
            [
                f'<rect x="{legend_x}" y="{y - 13}" width="14" height="14" rx="3" fill="{color}"/>',
                f'<text x="{legend_x + 24}" y="{y}" font-family="Arial, sans-serif" font-size="14" fill="#111827">{label}</text>',
                f'<text x="{legend_x + 210}" y="{y}" font-family="Arial, sans-serif" font-size="14" fill="#4b5563">{html.escape(pct(weight, 1))}</text>',
                f'<text x="{legend_x + 300}" y="{y}" font-family="Arial, sans-serif" font-size="14" fill="#4b5563">{html.escape(money(value))}</text>',
            ]
        )

    parts.append(
        '<text x="28" y="330" font-family="Arial, sans-serif" font-size="12" fill="#6b7280">'
        "Les montants sont approximatifs et dépendent des prix gratuits disponibles au moment de l’analyse."
        "</text>"
    )
    parts.append("</svg>")
    return "\n".join(parts)


def _slice_path(cx: float, cy: float, radius: float, start_angle: float, end_angle: float, color: str) -> str:
    start = _polar_to_cartesian(cx, cy, radius, end_angle)
    end = _polar_to_cartesian(cx, cy, radius, start_angle)
    large_arc = 1 if end_angle - start_angle > 180 else 0
    d = [
        f"M {cx:.3f} {cy:.3f}",
        f"L {start[0]:.3f} {start[1]:.3f}",
        f"A {radius:.3f} {radius:.3f} 0 {large_arc} 0 {end[0]:.3f} {end[1]:.3f}",
        "Z",
    ]
    return f'<path d="{" ".join(d)}" fill="{color}" stroke="#ffffff" stroke-width="2"/>'


def _polar_to_cartesian(cx: float, cy: float, radius: float, angle_degrees: float) -> tuple[float, float]:
    angle = math.radians(angle_degrees)
    return (cx + radius * math.cos(angle), cy + radius * math.sin(angle))


def _top_positions_text(holdings: list[tuple[str, float]], total_value: float) -> str:
    parts = []
    for ticker, value in holdings[:5]:
        weight = value / total_value if total_value > 0 else 0.0
        parts.append(f"{ticker} {pct(weight, 0)}")
    return ", ".join(parts)


def _chart_note(slices: list[dict[str, Any]], positions_count: int) -> str:
    if any(row.get("label") == "Autres" for row in slices):
        return "Certaines petites positions sont regroupées dans Autres."
    if positions_count <= 1:
        return "Une seule position positive dans ce compte."
    return "Toutes les positions positives du compte sont affichées."


def _safe_filename(value: str) -> str:
    text = re.sub(r"[^A-Za-z0-9_.-]+", "_", value.strip().upper())
    return text.strip("_") or "UNKNOWN"


def _clear_old_account_charts(charts_path: Path) -> None:
    for path in charts_path.glob("account_*.svg"):
        try:
            path.unlink()
        except OSError:
            pass
