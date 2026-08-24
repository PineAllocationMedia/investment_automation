from __future__ import annotations

import hashlib
import importlib.metadata
import json
import platform
from pathlib import Path
from typing import Any


EXPECTED_PYTHON_MAJOR_MINOR = "3.12"


def load_locked_dependencies(lock_path: str | Path) -> dict[str, str]:
    path = Path(lock_path)
    dependencies: dict[str, str] = {}
    if not path.exists():
        return dependencies
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "==" not in line:
            continue
        name, version = line.split("==", 1)
        dependencies[_normalize_distribution_name(name)] = version.strip()
    return dict(sorted(dependencies.items()))


def dependency_environment(lock_path: str | Path) -> dict[str, Any]:
    locked = load_locked_dependencies(lock_path)
    installed: dict[str, str] = {}
    missing: list[str] = []
    drift: list[dict[str, str]] = []
    for name, expected in locked.items():
        try:
            actual = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            missing.append(name)
            continue
        installed[name] = actual
        if actual != expected:
            drift.append({"package": name, "expected": expected, "actual": actual})
    payload = {
        "python_version": platform.python_version(),
        "python_implementation": platform.python_implementation(),
        "expected_python_major_minor": EXPECTED_PYTHON_MAJOR_MINOR,
        "platform_system": platform.system(),
        "platform_machine": platform.machine(),
        "locked_packages": locked,
        "installed_locked_packages": dict(sorted(installed.items())),
        "missing_packages": sorted(missing),
        "version_drift": sorted(drift, key=lambda row: row["package"]),
    }
    payload["dependency_fingerprint"] = _fingerprint(
        {
            "python_version": payload["python_version"],
            "python_implementation": payload["python_implementation"],
            "platform_system": payload["platform_system"],
            "platform_machine": payload["platform_machine"],
            "installed_locked_packages": payload["installed_locked_packages"],
        }
    )
    payload["dependency_lock_fingerprint"] = _fingerprint(locked)
    payload["dependency_status"] = _dependency_status(payload)
    return payload


def _dependency_status(payload: dict[str, Any]) -> str:
    python_ok = str(payload.get("python_version") or "").startswith(EXPECTED_PYTHON_MAJOR_MINOR + ".")
    if not python_ok or payload.get("missing_packages") or payload.get("version_drift"):
        return "DRIFT"
    if not payload.get("locked_packages"):
        return "LOCK_MISSING"
    return "MATCH"


def _normalize_distribution_name(value: str) -> str:
    return value.strip().lower().replace("_", "-")


def _fingerprint(payload: Any) -> str:
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
