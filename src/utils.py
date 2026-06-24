from __future__ import annotations

import csv
import html
import json
import math
import os
import tempfile
from datetime import date, datetime
from pathlib import Path
from typing import Any, Iterable


DISCLAIMER = (
    "Ceci n’est pas un conseil financier. Ce rapport applique seulement les règles "
    "mécaniques du guide fourni. Les données gratuites peuvent être incomplètes, "
    "retardées ou erronées. Toute décision finale doit être validée manuellement."
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIG_DIR = PROJECT_ROOT / "config"
DATA_DIR = PROJECT_ROOT / "data"
REPORTS_DIR = PROJECT_ROOT / "reports"
CACHE_DIR = DATA_DIR / "cached_market_data"
RESEARCH_REPORTS_DIR = DATA_DIR / "research_reports"
BNCD_MORNINGSTAR_DIR = RESEARCH_REPORTS_DIR / "bncd_morningstar"

TRUE_VALUES = {"true", "1", "yes", "y", "oui", "o", "vrai"}
FALSE_VALUES = {"false", "0", "no", "n", "non", "faux"}
CONFIDENCE_LEVELS = {"HIGH", "MEDIUM", "LOW"}


def ensure_directories() -> None:
    for path in [CONFIG_DIR, DATA_DIR, REPORTS_DIR, CACHE_DIR, RESEARCH_REPORTS_DIR, BNCD_MORNINGSTAR_DIR]:
        path.mkdir(parents=True, exist_ok=True)


def today_iso() -> str:
    return date.today().isoformat()


def safe_float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return float(value)
    if isinstance(value, (int, float)):
        if math.isnan(value) or math.isinf(value):
            return None
        return float(value)
    text = str(value).strip()
    if not text:
        return None
    text = text.replace("%", "").replace(",", ".")
    try:
        result = float(text)
    except ValueError:
        return None
    if math.isnan(result) or math.isinf(result):
        return None
    return result


def safe_bool(value: Any) -> bool | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if not text:
        return None
    if text in TRUE_VALUES:
        return True
    if text in FALSE_VALUES:
        return False
    return None


def parse_confidence(value: Any) -> str:
    text = str(value or "").strip().upper()
    if text in CONFIDENCE_LEVELS:
        return text
    return "MEDIUM"


def clamp(value: float, lower: float, upper: float) -> float:
    return max(lower, min(upper, value))


def pct(value: float | None, digits: int = 1) -> str:
    if value is None:
        return "N/D"
    return f"{value * 100:.{digits}f} %"


def money(value: float | None) -> str:
    if value is None:
        return "N/D"
    return f"{value:,.2f} $".replace(",", " ")


def normalize_ticker(ticker: Any) -> str:
    return str(ticker or "").strip().upper()


def parse_scalar(text: str) -> Any:
    text = text.strip()
    if not text:
        return ""
    if text.startswith("[") and text.endswith("]"):
        inner = text[1:-1].strip()
        if not inner:
            return []
        return [parse_scalar(part.strip()) for part in inner.split(",")]
    if (text.startswith('"') and text.endswith('"')) or (
        text.startswith("'") and text.endswith("'")
    ):
        return text[1:-1]
    bool_value = safe_bool(text)
    if bool_value is not None:
        return bool_value
    number = safe_float(text)
    if number is not None:
        if "." not in text and "," not in text:
            return int(number)
        return number
    return text


def load_yaml(path: str | Path) -> dict[str, Any]:
    path = Path(path)
    if not path.exists():
        return {}
    try:
        import yaml  # type: ignore

        with path.open("r", encoding="utf-8") as handle:
            loaded = yaml.safe_load(handle) or {}
            return loaded if isinstance(loaded, dict) else {}
    except Exception:
        return _load_simple_yaml(path)


def write_yaml(path: str | Path, payload: dict[str, Any]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        import yaml  # type: ignore

        write_text(path, yaml.safe_dump(payload, sort_keys=False, allow_unicode=True))
    except Exception:
        write_text(path, _dump_simple_yaml(payload))


def _dump_simple_yaml(payload: dict[str, Any], indent: int = 0) -> str:
    lines: list[str] = []
    prefix = " " * indent
    for key, value in payload.items():
        if isinstance(value, dict):
            lines.append(f"{prefix}{key}:")
            lines.append(_dump_simple_yaml(value, indent + 2))
        elif isinstance(value, list):
            lines.append(f"{prefix}{key}:")
            for item in value:
                if isinstance(item, dict):
                    lines.append(f"{prefix}  -")
                    lines.append(_dump_simple_yaml(item, indent + 4))
                else:
                    lines.append(f"{prefix}  - {item}")
        else:
            lines.append(f"{prefix}{key}: {value}")
    return "\n".join(line for line in lines if line is not None) + "\n"


def _load_simple_yaml(path: Path) -> dict[str, Any]:
    data: dict[str, Any] = {}
    current_key: str | None = None
    with path.open("r", encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.rstrip("\n")
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            indent = len(line) - len(line.lstrip(" "))
            stripped = line.strip()
            if indent == 0 and ":" in stripped:
                key, value = stripped.split(":", 1)
                key = key.strip()
                value = value.strip()
                current_key = key
                if value:
                    data[key] = parse_scalar(value)
                else:
                    data[key] = {}
            elif indent >= 2 and stripped.startswith("- ") and current_key:
                if not isinstance(data.get(current_key), list):
                    data[current_key] = []
                data[current_key].append(parse_scalar(stripped[2:]))
            elif indent >= 2 and ":" in stripped and current_key:
                if not isinstance(data.get(current_key), dict):
                    data[current_key] = {}
                key, value = stripped.split(":", 1)
                data[current_key][key.strip()] = parse_scalar(value.strip())
    return data


def read_csv_records(path: str | Path) -> list[dict[str, str]]:
    path = Path(path)
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        return [dict(row) for row in reader]


def write_csv_records(path: str | Path, rows: Iterable[dict[str, Any]], fieldnames: list[str]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with _atomic_writer(path, mode="w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fieldnames})


def write_text(path: str | Path, content: str) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with _atomic_writer(path, mode="w", encoding="utf-8") as handle:
        handle.write(content)


def load_json(path: str | Path) -> dict[str, Any]:
    path = Path(path)
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def save_json(path: str | Path, payload: dict[str, Any]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    write_text(path, json.dumps(payload, indent=2, sort_keys=True))


class _AtomicWriter:
    def __init__(self, path: Path, mode: str, encoding: str | None, newline: str | None) -> None:
        self.path = path
        self.mode = mode
        self.encoding = encoding
        self.newline = newline
        self.temp_path: Path | None = None
        self.handle: Any = None

    def __enter__(self) -> Any:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd, temp_name = tempfile.mkstemp(prefix=f".{self.path.name}.", suffix=".tmp", dir=str(self.path.parent))
        os.close(fd)
        self.temp_path = Path(temp_name)
        kwargs: dict[str, Any] = {}
        if "b" not in self.mode:
            kwargs["encoding"] = self.encoding
            if self.newline is not None:
                kwargs["newline"] = self.newline
        self.handle = self.temp_path.open(self.mode, **kwargs)
        return self.handle

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> bool:
        assert self.temp_path is not None
        try:
            if self.handle and not self.handle.closed:
                self.handle.flush()
                try:
                    os.fsync(self.handle.fileno())
                except OSError:
                    pass
                self.handle.close()
            if exc_type is None:
                os.replace(self.temp_path, self.path)
            elif self.temp_path.exists():
                self.temp_path.unlink()
        finally:
            self.handle = None
        return False


def _atomic_writer(
    path: str | Path,
    mode: str = "w",
    encoding: str | None = "utf-8",
    newline: str | None = None,
) -> _AtomicWriter:
    return _AtomicWriter(Path(path), mode=mode, encoding=encoding, newline=newline)


def markdown_to_html(markdown_text: str) -> str:
    try:
        import markdown  # type: ignore

        body = markdown.markdown(markdown_text, extensions=["tables", "md_in_html"])
    except Exception:
        body = "<pre>" + html.escape(markdown_text) + "</pre>"
    return (
        "<!doctype html>\n<html lang=\"fr\">\n<head>\n<meta charset=\"utf-8\">\n"
        "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">\n"
        "<title>Rapport trimestriel d’investissement</title>\n"
        "<style>body{font-family:Arial,sans-serif;line-height:1.5;max-width:1100px;"
        "margin:32px auto;padding:0 18px;color:#1f2933}table{border-collapse:collapse;"
        "width:100%;margin:16px 0}th,td{border:1px solid #d9e2ec;padding:7px;"
        "text-align:left;font-size:14px}th{background:#f0f4f8}code{background:#f0f4f8;"
        "padding:2px 4px}img{max-width:100%;height:auto}details{border:1px solid #d9e2ec;"
        "border-radius:6px;padding:10px 12px;margin:14px 0;background:#fbfdff}summary{font-weight:700;"
        "cursor:pointer}.note{background:#fff8db;border-left:4px solid #f0b429;padding:10px 12px}</style>\n</head>\n<body>\n"
        f"{body}\n</body>\n</html>\n"
    )


def first_present(*values: Any) -> Any:
    for value in values:
        if value is not None and value != "":
            return value
    return None


def weighted_average(rows: list[dict[str, Any]], value_key: str, weight_key: str) -> float | None:
    numerator = 0.0
    denominator = 0.0
    for row in rows:
        value = safe_float(row.get(value_key))
        weight = safe_float(row.get(weight_key))
        if value is None or weight is None:
            continue
        numerator += value * weight
        denominator += weight
    if denominator == 0:
        return None
    return numerator / denominator


def file_age_hours(path: str | Path) -> float | None:
    path = Path(path)
    if not path.exists():
        return None
    modified = datetime.fromtimestamp(path.stat().st_mtime)
    return (datetime.now() - modified).total_seconds() / 3600
