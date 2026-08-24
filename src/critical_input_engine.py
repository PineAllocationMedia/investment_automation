from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .utils import normalize_ticker, read_csv_records, safe_float
from .validation_evidence import purpose_is_genuine_decision
from .validators import validate_input_files


HARD_FAIL = "HARD_FAIL"
DEGRADED_ADVISORY = "DEGRADED_ADVISORY"
NONCRITICAL = "NONCRITICAL"

REQUIRED_CONFIG_FILES = {
    "backtest_benchmarks.yaml",
    "baseline.yaml",
    "benchmarks.yaml",
    "defensive_etfs.yaml",
    "exposures.yaml",
    "market_regime.yaml",
    "market_scanner.yaml",
    "model_tuning.yaml",
    "positions.yaml",
    "proxy_corrections.yaml",
    "rules.yaml",
    "sectors.yaml",
    "source_hierarchy.yaml",
    "tax_parameters.yaml",
    "ticker_aliases.yaml",
    "transaction_friction.yaml",
    "watchlist.yaml",
}


class CriticalInputError(RuntimeError):
    def __init__(self, audit: dict[str, Any]):
        self.audit = audit
        messages = [str(row.get("message") or "") for row in audit.get("hard_failures", [])]
        super().__init__("; ".join(messages) or "Critical input validation failed.")


def decision_capable_run(*, capital: Any, run_purpose: Any) -> bool:
    numeric_capital = safe_float(capital)
    return numeric_capital is not None and numeric_capital > 0


def audit_static_critical_inputs(
    project_root: str | Path,
    *,
    capital: Any,
    run_purpose: Any,
    mode: str | None = None,
) -> dict[str, Any]:
    root = Path(project_root)
    decision_capable = decision_capable_run(capital=capital, run_purpose=run_purpose)
    strict_static_inputs = decision_capable or purpose_is_genuine_decision(run_purpose)
    issues: list[dict[str, str]] = []
    numeric_capital = safe_float(capital)
    if numeric_capital is None or numeric_capital < 0:
        issues.append(_issue(HARD_FAIL, "INVALID_CAPITAL", "Capital must be a finite number greater than or equal to zero."))
    if mode is not None and mode not in {"balanced", "family-office", "rational-aggressive", "high-cagr"}:
        issues.append(_issue(HARD_FAIL, "INVALID_ANALYSIS_MODE", f"Unsupported analysis mode: {mode}."))
    portfolio_path = root / "data" / "portfolio.csv"
    if not portfolio_path.exists():
        issues.append(_issue(HARD_FAIL, "MISSING_PORTFOLIO", "data/portfolio.csv is required; analyze will not create or fabricate it."))
    else:
        try:
            from .portfolio_loader import load_portfolio

            portfolio_rows = load_portfolio(portfolio_path)
        except Exception as exc:  # noqa: BLE001
            issues.append(_issue(HARD_FAIL, "UNREADABLE_PORTFOLIO", f"data/portfolio.csv cannot be read safely: {exc}"))
            portfolio_rows = []
        if strict_static_inputs and not portfolio_rows:
            issues.append(_issue(HARD_FAIL, "EMPTY_PORTFOLIO", "A decision-capable analysis requires at least one usable portfolio row."))
        if strict_static_inputs:
            try:
                issues.extend(_cost_basis_consistency_issues(portfolio_path))
            except Exception as exc:  # noqa: BLE001
                issues.append(_issue(HARD_FAIL, "COST_BASIS_AUDIT_FAILED", f"Portfolio cost-basis consistency cannot be audited: {exc}"))

    try:
        validation_messages = validate_input_files(root)
    except Exception as exc:  # noqa: BLE001
        validation_messages = []
        issues.append(_issue(HARD_FAIL, "INPUT_VALIDATION_FAILED", f"Critical input validation could not complete safely: {exc}"))
    for message in validation_messages:
        classification = _validation_issue_classification(message, decision_capable=strict_static_inputs)
        issues.append(_issue(classification, "INPUT_VALIDATION", message))

    issues.extend(_config_integrity_issues(root))
    return _audit_payload(issues, decision_capable=decision_capable)


def audit_runtime_critical_inputs(
    *,
    portfolio_rows: list[dict[str, Any]],
    market_data: dict[str, dict[str, Any]],
    capital: Any,
    run_purpose: Any,
) -> dict[str, Any]:
    decision_capable = decision_capable_run(capital=capital, run_purpose=run_purpose)
    issues: list[dict[str, str]] = []
    if not decision_capable:
        return _audit_payload(issues, decision_capable=False)

    vfv = market_data.get("VFV.TO") or {}
    if safe_float(vfv.get("current_price")) is None:
        issues.append(
            _issue(
                HARD_FAIL,
                "VFV_MARKET_DATA_UNUSABLE",
                "VFV.TO has no usable current price; the common capital hurdle and fallback allocation cannot be audited safely.",
            )
        )

    unsafe_sources = {"acquisition_value_fallback", "no_position"}
    for row in portfolio_rows:
        shares = safe_float(row.get("shares")) or 0.0
        current_value = safe_float(row.get("current_value_cad") or row.get("current_value")) or 0.0
        source = str(row.get("portfolio_valuation_source") or "")
        ticker = str(row.get("ticker") or "UNKNOWN")
        if shares > 0 and (source in unsafe_sources or current_value <= 0):
            issues.append(
                _issue(
                    HARD_FAIL,
                    "UNSAFE_PORTFOLIO_VALUE_BASIS",
                    f"{ticker} has shares but no safe current-value basis (source={source or 'UNKNOWN'}).",
                )
            )
        elif source == "manual_current_value_fallback":
            issues.append(
                _issue(
                    DEGRADED_ADVISORY,
                    "MANUAL_PORTFOLIO_VALUE_FALLBACK",
                    f"{ticker} uses an explicit manual current-value fallback because price or FX data is unavailable.",
                )
            )
    return _audit_payload(issues, decision_capable=True)


def merge_input_audits(*audits: dict[str, Any]) -> dict[str, Any]:
    issues: list[dict[str, str]] = []
    decision_capable = False
    for audit in audits:
        issues.extend(audit.get("issues", []))
        decision_capable = decision_capable or bool(audit.get("decision_capable"))
    return _audit_payload(issues, decision_capable=decision_capable)


def audit_baseline_environment_authority(baseline_metadata: dict[str, Any]) -> dict[str, Any]:
    """Hard-fail only frozen, positive-capital Baseline decisions with environment drift."""
    issues: list[dict[str, str]] = []
    reasons = set(baseline_metadata.get("baseline_authority_reasons") or [])
    environment_reasons = {
        "BASELINE_DEPENDENCY_ENVIRONMENT_INVALID",
        "BASELINE_TRACKED_GIT_STATE_INVALID",
    }
    if reasons - environment_reasons:
        return _audit_payload(
            issues,
            decision_capable=decision_capable_run(
                capital=baseline_metadata.get("capital"),
                run_purpose=baseline_metadata.get("run_purpose"),
            ),
        )
    if "BASELINE_DEPENDENCY_ENVIRONMENT_INVALID" in reasons:
        issues.append(
            _issue(
                HARD_FAIL,
                "BASELINE_DEPENDENCY_ENVIRONMENT_INVALID",
                "An active positive-capital Baseline decision requires dependency_status=MATCH.",
            )
        )
    if "BASELINE_TRACKED_GIT_STATE_INVALID" in reasons:
        issues.append(
            _issue(
                HARD_FAIL,
                "BASELINE_TRACKED_GIT_STATE_INVALID",
                "An active positive-capital Baseline decision requires a clean tracked Git worktree.",
            )
        )
    return _audit_payload(
        issues,
        decision_capable=decision_capable_run(
            capital=baseline_metadata.get("capital"),
            run_purpose=baseline_metadata.get("run_purpose"),
        ),
    )


def _validation_issue_classification(message: str, *, decision_capable: bool) -> str:
    lowered = message.lower()
    if "portfolio.csv" in lowered:
        return HARD_FAIL
    if "portfolio_transactions.csv" in lowered:
        return HARD_FAIL if decision_capable else DEGRADED_ADVISORY
    if any(name in lowered for name in ("watchlist.csv", "market_universe.csv", "research_index.csv", "proxy_calibration.csv", "manual_inputs_friendly.txt")):
        return DEGRADED_ADVISORY
    return DEGRADED_ADVISORY


def _config_integrity_issues(root: Path) -> list[dict[str, str]]:
    config_dir = root / "config"
    issues: list[dict[str, str]] = []
    try:
        import yaml  # type: ignore
    except Exception as exc:  # pragma: no cover - required dependency is tested separately.
        return [_issue(HARD_FAIL, "YAML_DEPENDENCY_MISSING", f"PyYAML is required to validate critical configuration: {exc}")]
    parsed_payloads: dict[str, Any] = {}
    for filename in sorted(REQUIRED_CONFIG_FILES):
        path = config_dir / filename
        if not path.exists():
            issues.append(_issue(HARD_FAIL, "MISSING_CRITICAL_CONFIG", f"Required configuration is missing: config/{filename}."))
            continue
        try:
            payload = yaml.safe_load(path.read_text(encoding="utf-8"))
        except Exception as exc:  # noqa: BLE001
            issues.append(_issue(HARD_FAIL, "CORRUPT_CRITICAL_CONFIG", f"config/{filename} is not valid YAML: {exc}"))
            continue
        if not isinstance(payload, dict):
            issues.append(_issue(HARD_FAIL, "INVALID_CRITICAL_CONFIG_ROOT", f"config/{filename} must contain a YAML mapping."))
            continue
        parsed_payloads[filename] = payload
    baseline = parsed_payloads.get("baseline.yaml") or {}
    approved_fingerprint = str(baseline.get("approved_config_fingerprint") or "").strip().lower()
    if approved_fingerprint:
        actual_fingerprint = critical_config_fingerprint(root)
        if actual_fingerprint != approved_fingerprint:
            issues.append(
                _issue(
                    HARD_FAIL,
                    "BASELINE_CONFIG_FINGERPRINT_MISMATCH",
                    f"Critical configuration fingerprint {actual_fingerprint} differs from approved Baseline fingerprint {approved_fingerprint}.",
                )
            )
    return issues


def critical_config_fingerprint(root: str | Path) -> str:
    root = Path(root)
    import yaml  # type: ignore

    payloads: dict[str, Any] = {}
    for filename in sorted(REQUIRED_CONFIG_FILES - {"baseline.yaml"}):
        path = root / "config" / filename
        if not path.exists():
            payloads[filename] = "MISSING"
            continue
        try:
            payloads[filename] = yaml.safe_load(path.read_text(encoding="utf-8"))
        except Exception as exc:  # noqa: BLE001
            payloads[filename] = {"INVALID": type(exc).__name__}
    encoded = json.dumps(
        payloads,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _cost_basis_consistency_issues(portfolio_path: Path) -> list[dict[str, str]]:
    currencies_by_ticker: dict[str, set[str]] = {}
    issues: list[dict[str, str]] = []
    for index, row in enumerate(read_csv_records(portfolio_path), start=2):
        ticker = normalize_ticker(row.get("ticker"))
        if not ticker:
            continue
        has_generic_cost = any(
            str(row.get(field) or "").strip()
            for field in ("average_cost", "avg_cost", "cost_per_share", "acquisition_value", "total_cost", "cost_basis")
        )
        has_explicit_cad_cost = any(
            str(row.get(field) or "").strip()
            for field in ("average_cost_cad", "acquisition_value_cad")
        )
        currency = str(row.get("average_cost_currency") or row.get("cost_currency") or "").strip().upper()
        if has_generic_cost and not currency and not has_explicit_cad_cost:
            issues.append(
                _issue(
                    HARD_FAIL,
                    "COST_BASIS_CURRENCY_MISSING",
                    f"portfolio.csv:{index} {ticker} has a cost basis without an explicit CAD/USD currency.",
                )
            )
        if has_explicit_cad_cost:
            currency = "CAD"
        if has_generic_cost or has_explicit_cad_cost:
            currencies_by_ticker.setdefault(ticker, set()).add(currency or "UNKNOWN")
    for ticker, currencies in sorted(currencies_by_ticker.items()):
        if len(currencies) > 1:
            issues.append(
                _issue(
                    HARD_FAIL,
                    "INCONSISTENT_TICKER_COST_BASIS_CURRENCIES",
                    f"{ticker} has mixed cost-basis currencies across portfolio rows: {', '.join(sorted(currencies))}.",
                )
            )
    return issues


def _audit_payload(issues: list[dict[str, str]], *, decision_capable: bool) -> dict[str, Any]:
    unique: list[dict[str, str]] = []
    seen: set[tuple[str, str, str]] = set()
    for row in issues:
        key = (row["classification"], row["code"], row["message"])
        if key not in seen:
            seen.add(key)
            unique.append(row)
    return {
        "decision_capable": decision_capable,
        "status": "HARD_FAIL" if any(row["classification"] == HARD_FAIL for row in unique) else (
            "DEGRADED_ADVISORY" if unique else "PASS"
        ),
        "issues": unique,
        "hard_failures": [row for row in unique if row["classification"] == HARD_FAIL],
        "advisories": [row for row in unique if row["classification"] == DEGRADED_ADVISORY],
        "noncritical": [row for row in unique if row["classification"] == NONCRITICAL],
    }


def _issue(classification: str, code: str, message: str) -> dict[str, str]:
    return {"classification": classification, "code": code, "message": message}
