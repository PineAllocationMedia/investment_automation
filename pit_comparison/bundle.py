"""Strict byte-addressed input contract; no collectors and no model imports."""
from __future__ import annotations

import copy
import hashlib
import json
import math
import re
import stat
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath, PureWindowsPath
from zoneinfo import ZoneInfo

from . import AUTHORITY, PIT_BUNDLE_SCHEMA_VERSION, PIT_INPUT_CONTRACT_VERSION

FAMILIES = ("context", "portfolio", "transactions", "account_locations", "universe",
            "market", "benchmarks", "regime_market", "fx", "manual_inputs",
            "research_facts", "ticker_memory", "prior_state", "config", "provenance")
CONFIG_NAMES = frozenset({"positions.yaml", "benchmarks.yaml", "sectors.yaml", "exposures.yaml",
    "watchlist.yaml", "market_scanner.yaml", "defensive_etfs.yaml", "market_regime.yaml",
    "ticker_aliases.yaml", "proxy_corrections.yaml", "model_tuning.yaml", "tax_parameters.yaml"})
MODES = {"balanced", "rational-aggressive", "family-office", "high-cagr"}
HEX = re.compile(r"^[0-9a-f]{64}$")
FORBIDDEN_FACT_KEYS = set(AUTHORITY) - {"comparison_mode"}
FINAL_FACT_KEYS = {"score_total", "conviction_score", "capital_allocation_score",
                   "allocation_decision", "final_position_action", "expected_cagr_quality"}


class BundleError(ValueError):
    pass


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _pairs(items):
    result = {}
    for key, value in items:
        if key in result:
            raise BundleError(f"Duplicate JSON key: {key}")
        result[key] = value
    return result


def loads(data: bytes | str):
    def invalid(value):
        raise BundleError(f"Nonfinite number: {value}")
    try:
        value = json.loads(data, object_pairs_hook=_pairs, parse_constant=invalid)
        canonical(value)  # also rejects exponent overflow (1e999)
        return value
    except (UnicodeError, json.JSONDecodeError, TypeError, ValueError) as exc:
        raise BundleError(str(exc)) from exc


def canonical(value) -> bytes:
    def check(item):
        if isinstance(item, dict):
            if any(not isinstance(k, str) for k in item):
                raise BundleError("JSON object keys must be strings")
            for child in item.values():
                check(child)
        elif isinstance(item, list):
            for child in item:
                check(child)
        elif isinstance(item, float):
            if not math.isfinite(item):
                raise BundleError("Nonfinite number")
        elif item is not None and type(item) not in (str, int, bool):
            raise BundleError(f"Unsupported JSON type: {type(item).__name__}")
    check(value)
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
                       allow_nan=False) + "\n").encode("utf-8")


def fingerprint(value) -> str:
    return digest(canonical(value))


def relative_path(value: str) -> str:
    if (not isinstance(value, str) or not value or "\\" in value or "\x00" in value
            or PurePosixPath(value).is_absolute() or PureWindowsPath(value).drive
            or any(p in {"", ".", ".."} for p in value.split("/"))
            or unicodedata.normalize("NFC", value) != value):
        raise BundleError(f"Unsafe relative path: {value!r}")
    return value


def inventory(root: Path) -> dict[str, bytes]:
    """lstat before open; no links, devices or hidden/unlisted files."""
    root = Path(root).absolute()
    for parent in (root, *root.parents):
        if parent.is_symlink():
            raise BundleError(f"Symlink root component: {parent}")
    if not root.is_dir():
        raise BundleError("Input root is not a directory")
    files, names, directories = {}, set(), set()
    for path in sorted(root.rglob("*")):
        name = relative_path(path.relative_to(root).as_posix())
        alias = name.casefold()
        if alias in names:
            raise BundleError(f"Path alias: {name}")
        names.add(alias)
        mode = path.lstat()
        if stat.S_ISDIR(mode.st_mode):
            directories.add(name)
            continue
        if not stat.S_ISREG(mode.st_mode) or mode.st_nlink != 1:
            raise BundleError(f"Not a single-link regular file: {name}")
        files[name] = path.read_bytes()
    implied = {str(parent) for name in files for parent in PurePosixPath(name).parents if str(parent) != "."}
    if directories != implied:
        raise BundleError("Unlisted empty directory")
    return files


def timestamp(value: str) -> datetime:
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if result.tzinfo is None:
            raise ValueError("Timezone required")
        return result.astimezone(timezone.utc)
    except (AttributeError, ValueError) as exc:
        raise BundleError(f"Invalid timestamp: {value!r}") from exc


def _embedded(value, *, historical=False):
    if isinstance(value, dict):
        for key, child in value.items():
            if key in FORBIDDEN_FACT_KEYS:
                raise BundleError(f"Authority metadata forbidden in inputs: {key}")
            if key in FINAL_FACT_KEYS and not historical:
                raise BundleError(f"Scored decision is not an input fact: {key}")
            _embedded(child, historical=historical)
    elif isinstance(value, list):
        for child in value:
            _embedded(child, historical=historical)
    elif isinstance(value, str):
        if (value.startswith(("/", "~/", "file:")) or PureWindowsPath(value).drive
                or ".." in value.replace("\\", "/").split("/")):
            raise BundleError("Absolute/traversing embedded path")


def _require(condition, message):
    if not condition:
        raise BundleError(message)


@dataclass
class VerifiedBundle:
    manifest: dict
    data: dict
    files: dict[str, bytes]
    consumed: set[str] = field(default_factory=set)

    def get(self, logical_id):
        if logical_id not in self.data:
            raise BundleError(f"Undeclared logical input: {logical_id}")
        self.consumed.add(logical_id)
        return copy.deepcopy(self.data[logical_id])

    def materialize(self, root: Path):
        root.mkdir(parents=True, exist_ok=False)
        for name, payload in self.files.items():
            path = root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(payload)


def verify_bundle(root: Path, expected_hash: str, *, require_complete=False) -> VerifiedBundle:
    try:
        return _verify_bundle(root, expected_hash, require_complete=require_complete)
    except (TypeError, KeyError, IndexError, AttributeError) as exc:
        raise BundleError("Malformed bundle contract") from exc


def _verify_bundle(root: Path, expected_hash: str, *, require_complete=False) -> VerifiedBundle:
    _require(isinstance(expected_hash, str) and HEX.fullmatch(expected_hash), "External expected SHA-256 required")
    files = inventory(root)
    _require("bundle_manifest.json" in files, "Missing bundle manifest")
    manifest = loads(files["bundle_manifest.json"])
    _require(isinstance(manifest, dict), "Manifest must be an object")
    _require(files["bundle_manifest.json"] == canonical(manifest), "Noncanonical manifest")
    unsigned = {k: v for k, v in manifest.items() if k not in {"bundle_hash", "bundle_id"}}
    actual_hash = fingerprint(unsigned)
    _require(actual_hash == expected_hash == manifest.get("bundle_hash"), "Bundle digest mismatch")
    _require(manifest.get("bundle_id") == "sha256:" + actual_hash, "Bundle ID mismatch")
    _require(manifest.get("bundle_schema_version") == PIT_BUNDLE_SCHEMA_VERSION, "Unsupported bundle schema")
    _require(manifest.get("input_contract_version") == PIT_INPUT_CONTRACT_VERSION, "Unsupported input contract")
    _require(manifest.get("comparison_mode") == "RETROSPECTIVE_PIT", "Only retrospective execution supported")
    _require(not (FORBIDDEN_FACT_KEYS & manifest.keys()), "Authority fields forbidden in manifest")
    declared = manifest.get("files")
    _require(isinstance(declared, list), "Missing files inventory")
    data, declared_paths = {}, set()
    for record in declared:
        _require(isinstance(record, dict), "Invalid file record")
        logical = record.get("logical_id")
        _require(logical in FAMILIES and logical not in data, "Unknown or duplicate logical ID")
        path = relative_path(record.get("path"))
        _require(path == f"inputs/{logical}.json" and path not in declared_paths, "Invalid/duplicate logical path")
        declared_paths.add(path)
        _require(path in files, f"Missing declared input: {path}")
        raw = files[path]
        _require(type(record.get("byte_length")) is int and len(raw) == record["byte_length"], "Byte length mismatch")
        _require(digest(raw) == record.get("sha256"), "Input SHA-256 mismatch")
        data[logical] = loads(raw)
        _embedded(data[logical], historical=logical == "prior_state")
    _require(set(files) == declared_paths | {"bundle_manifest.json"}, "Undeclared input file")
    _require(set(data) == set(FAMILIES), "Missing required logical family")
    _require(manifest.get("logical_inputs") == sorted(FAMILIES), "Logical inventory mismatch")
    identity = fingerprint({"contract": PIT_INPUT_CONTRACT_VERSION,
                            "files": sorted(declared, key=lambda x: x["logical_id"]),
                            "effective_pit_at": manifest.get("effective_pit_at"),
                            "semantic_timezone": manifest.get("semantic_timezone")})
    _require(identity == manifest.get("input_identity"), "Input identity mismatch")
    validate_contract(manifest, data, require_complete=require_complete)
    return VerifiedBundle(manifest, data, files)


def validate_contract(m, d, *, require_complete):
    pit = timestamp(m.get("effective_pit_at"))
    timestamp(m.get("created_at"))
    try:
        ZoneInfo(m["semantic_timezone"])
    except Exception as exc:
        raise BundleError("Invalid semantic timezone") from exc
    _require(m.get("allowed_data_cutoff") == {"available_at_lte": m["effective_pit_at"],
        "historical_revision_policy": "AS_AVAILABLE_AT_T"}, "Explicit cutoff required")
    quality = m.get("pit_quality")
    _require(quality in {"COMPLETE_PIT", "PARTIAL_PIT"}, "Contaminated/invalid PIT classification")
    if require_complete:
        _require(quality == "COMPLETE_PIT", "PARTIAL_PIT cannot execute a complete pair")
    ctx = d["context"]
    _require(isinstance(ctx, dict) and set(ctx) == {"investment_mode", "capital_context", "validation_warnings"}, "Invalid decision context")
    _require(ctx["investment_mode"] in MODES and m.get("investment_mode") == ctx["investment_mode"], "Invalid mode")
    _require(isinstance(ctx["validation_warnings"], list) and all(isinstance(v, str) for v in ctx["validation_warnings"]), "Explicit validation-warning context required")
    cap = ctx["capital_context"]
    _require(isinstance(cap, dict) and set(cap) == {"amount", "currency", "contribution_type"}, "Invalid capital context")
    _require(type(cap["amount"]) in (int, float) and cap["amount"] >= 0 and cap["currency"] == "CAD"
             and bool(cap["contribution_type"]) and m.get("capital_context") == cap, "Invalid capital")
    _require(m.get("portfolio_snapshot_id") == "sha256:" + fingerprint(d["portfolio"]), "Portfolio identity mismatch")
    for key in ("portfolio", "transactions", "account_locations"):
        _require(isinstance(d[key], list) and all(isinstance(r, dict) for r in d[key]), f"Invalid {key}")
    _require(bool(d["portfolio"]), "Portfolio required")
    for row in d["portfolio"]:
        _require(isinstance(row.get("ticker"), str) and bool(row["ticker"].strip()), "Portfolio ticker required")
        _require(isinstance(row.get("account_type"), str), "Explicit portfolio account context required")
        for key in ("shares", "current_value", "current_value_cad", "average_cost", "acquisition_value"):
            if key in row and row[key] is not None:
                _require(type(row[key]) in (int, float) and row[key] >= 0, "Invalid portfolio quantity/value")
        _require(any(type(row.get(k)) in (int, float) and row[k] > 0 for k in ("shares", "current_value", "current_value_cad")), "Empty portfolio position")
        if row.get("average_cost") or row.get("acquisition_value"):
            _require(row.get("average_cost_currency") in {"CAD", "USD", "EUR", "GBP", "CHF", "JPY"}
                     or row.get("acquisition_value_currency") in {"CAD", "USD", "EUR", "GBP", "CHF", "JPY"}, "Cost basis currency required")
    for key in ("market", "benchmarks", "regime_market", "fx", "manual_inputs", "research_facts", "ticker_memory", "config", "universe"):
        _require(isinstance(d[key], dict), f"Invalid {key}")
    _require(set(d["config"]) == CONFIG_NAMES and all(isinstance(v, dict) for v in d["config"].values()), "Missing/unknown effective configuration")
    _require(set(d["universe"]) == {"watchlist_rows", "market_rows", "discovery_rows"}
             and all(isinstance(v, list) for v in d["universe"].values()), "Missing frozen universe/discovery")
    for key in ("market", "benchmarks", "regime_market"):
        for ticker, payload in d[key].items():
            _require(isinstance(payload, dict), f"Invalid {key} payload")
            _require(MARKET_REQUIRED <= payload.keys(), f"Incomplete {key}/{ticker} fields")
            _require(payload["source"] and payload["currency"], "Missing price source/currency")
            _require(type(payload["current_price"]) in (int, float) and payload["current_price"] > 0, "Missing required price")
            _require(timestamp(payload["fetched_at"]) <= pit, "Future market capture")
    # Family availability attestations cannot override contradictory dated facts.
    def check_fact_dates(value, key=""):
        if value is None or value == "" or value == []:
            return
        if isinstance(value, dict):
            for child_key, child in value.items():
                check_fact_dates(child, child_key if key not in {"research_report_field_report_dates", "research_report_field_dates"} else "report_date")
        elif isinstance(value, list):
            for child in value:
                check_fact_dates(child, key)
        elif key in {"fetched_at", "published_at", "available_at", "news_checked_at", "news_context_checked_at", "news_context_published_at", "canadian_checked_at", "last_known_good_at", "market_data_fetch_attempted_at", "market_data_last_success_at"}:
            _require(timestamp(value) <= pit, "Future embedded fact timestamp")
        elif key in {"report_date", "research_report_dates", "sec_edgar_latest_filing_date", "source_date"}:
            from datetime import date
            _require(date.fromisoformat(value) <= pit.astimezone(ZoneInfo(m["semantic_timezone"])).date(), "Future embedded fact date")
    for family in ("market", "benchmarks", "regime_market", "manual_inputs", "research_facts", "ticker_memory"):
        check_fact_dates(d[family])
    _require(d["fx"].get("CAD") == 1 and all(type(v) in (int, float) and v > 0 for v in d["fx"].values()), "Invalid frozen FX")
    state = d["prior_state"]
    _require(isinstance(state, dict) and set(state) == {"status", "analysis", "allocation"}, "Missing prior state")
    _require(state["status"] in {"VERIFIED_EMPTY", "VERIFIED"}, "Unverified prior state")
    _require(m.get("history_policy") == {"selection": "EXPLICIT_ADMISSIBLE_RECORDS", "status": state["status"]}, "History policy mismatch")
    identities, selection_keys = set(), set()
    for kind in ("analysis", "allocation"):
        _require(isinstance(state[kind], list), "Invalid prior records")
        for row in state[kind]:
            _require(isinstance(row, dict) and {"observation_id", "storage_role", "created_at", "analysis_date", "analysis_mode", "model_rules_version", "rows"} <= row.keys(), "Incomplete prior record")
            _require(row["storage_role"] in {"HISTORY", "LATEST"}, "Unknown prior storage role")
            identity = (kind, row["storage_role"], row["observation_id"])
            _require(identity not in identities, "Duplicate prior identity")
            if row["storage_role"] == "LATEST":
                _require(not any(k[0] == kind and k[1] == "LATEST" for k in identities), "Duplicate latest prior snapshot")
            identities.add(identity)
            selection_key = (kind, row["storage_role"], row["analysis_date"], row["created_at"])
            _require(selection_key not in selection_keys, "Ambiguous same-time prior selection")
            selection_keys.add(selection_key)
            _require(timestamp(row["created_at"]) < pit and row["analysis_date"] <= pit.astimezone(ZoneInfo(m["semantic_timezone"])).date().isoformat(), "Future prior state")
            _require(isinstance(row["rows"], list), "Invalid prior rows")
    _require((not state["analysis"] and not state["allocation"]) == (state["status"] == "VERIFIED_EMPTY"), "Empty/missing prior state ambiguity")
    empties = sorted(key for key in FAMILIES if d[key] == {} or d[key] == [])
    _require(m.get("explicit_absences") == empties, "Explicit absence inventory mismatch")
    for row in d["transactions"]:
        _require(bool(row.get("date")) and row["date"] <= pit.date().isoformat(), "Future/undated transaction")
    p = d["provenance"]
    _require(isinstance(p, dict) and set(p) == set(FAMILIES) - {"provenance"}, "Missing family provenance")
    for family, source in p.items():
        _require(isinstance(source, dict), "Invalid provenance")
        if quality == "PARTIAL_PIT" and source.get("status") == "UNKNOWN":
            continue
        _require({"observation_date", "published_at", "available_at", "captured_at", "availability_evidence", "source_version", "source_sha256", "historical_version_verified"} <= source.keys(), f"Incomplete provenance: {family}")
        _require(source["observation_date"] <= pit.date().isoformat(), "Future observation")
        _require(timestamp(source["published_at"]) <= timestamp(source["available_at"]) <= pit, "Future publication/availability")
        _require(timestamp(source["captured_at"]) >= timestamp(source["available_at"]), "Capture precedes availability")
        _require(source["historical_version_verified"] is True and bool(source["availability_evidence"])
                 and bool(source["source_version"]) and HEX.fullmatch(source["source_sha256"]), "Historical version/evidence required")
    _require(m.get("provenance") == {"logical_input": "provenance", "sha256": fingerprint(p)}, "Provenance linkage mismatch")

# Frozen provider record schema from allocation-room-integrity-v7. Null is an
# explicit observed absence; omitting a field is an incomplete record.
MARKET_REQUIRED = frozenset(['adjusted_cagr_10y', 'adjusted_cagr_5y', 'adjusted_current_price', 'adjusted_price_10y_ago', 'adjusted_price_5y_ago', 'adjusted_stock_cagr_10y', 'adjusted_stock_cagr_3y', 'adjusted_stock_cagr_5y', 'adjusted_stock_return_1y', 'beta', 'business_summary', 'buyback_yield', 'cagr_10y', 'cagr_5y', 'canadian_checked_at', 'canadian_confirmed_fields', 'canadian_coverage_status', 'canadian_data_conflicts', 'canadian_data_sources', 'canadian_fundamental_fields', 'canadian_latest_period', 'canadian_resolution_summary', 'canadian_source_health', 'canadian_source_policy', 'capital_expenditures', 'company_city', 'company_state', 'country', 'currency', 'current_price', 'data_fill_rate', 'data_source_notes', 'debt_to_equity', 'diluted_average_shares', 'dividend_yield', 'drawdown_from_12m_high', 'drawdown_from_8m_high', 'earnings_growth', 'earnings_quarterly_growth', 'fcf_conversion', 'fcf_per_share', 'fcf_per_share_growth', 'fetched_at', 'forward_eps', 'forward_pe', 'free_cash_flow', 'free_cash_flow_growth', 'free_cash_flow_margin', 'full_time_employees', 'fund_category', 'fund_family', 'fundamental_fallback_fields', 'gross_margins', 'high_12m', 'high_8m', 'industry', 'last_known_good_at', 'last_known_good_source', 'long_name', 'low_12m', 'market_cap', 'market_data_circuit_breaker_open', 'market_data_fallback_level', 'market_data_fetch_attempted_at', 'market_data_fetch_attempts', 'market_data_fetch_status', 'market_data_last_error', 'market_data_last_success_at', 'market_data_warning_flags', 'net_debt_to_fcf', 'net_income', 'news_checked_at', 'news_context_checked_at', 'news_context_headlines', 'news_context_published_at', 'news_context_search_queries', 'news_context_source_channels', 'news_context_sources', 'news_context_urls', 'news_red_flag_count', 'news_red_flags', 'number_of_analyst_opinions', 'official_confirmed_fields', 'official_data_conflicts', 'official_data_sources', 'official_fundamental_fields', 'official_resolution_summary', 'official_source_policy', 'operating_cash_flow', 'operating_margins', 'payout_ratio', 'peg', 'price_10y_ago', 'price_5y_ago', 'price_above_sma_200', 'profit_margins', 'quote_type', 'quote_type_display', 'return_on_assets', 'return_on_equity', 'revenue_growth', 'revenue_quarterly_growth', 'sbc_to_revenue', 'sec_edgar_cik', 'sec_edgar_company_name', 'sec_edgar_latest_filing_date', 'sec_edgar_latest_fiscal_year', 'sector_name', 'share_count_cagr_3y', 'share_count_cagr_5y', 'share_count_growth_1y', 'share_repurchases', 'shares_outstanding', 'sma_200', 'source', 'statement_fallback_used', 'stock_based_compensation', 'stock_cagr_10y', 'stock_cagr_3y', 'stock_cagr_5y', 'stock_return_1y', 'total_assets', 'total_cash', 'total_debt', 'total_liabilities', 'total_return_basis', 'total_return_price', 'total_return_price_history', 'total_revenue', 'trailing_eps', 'trailing_pe', 'website'])
