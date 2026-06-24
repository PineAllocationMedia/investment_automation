from __future__ import annotations

import configparser
from datetime import datetime
from pathlib import Path
from typing import Any

from .manual_inputs import BOOL_COLUMNS, MANUAL_COLUMNS, NUMERIC_COLUMNS
from .market_scanner import MARKET_UNIVERSE_COLUMNS
from .portfolio_loader import (
    ACCOUNT_LOCATION_COLUMNS,
    ACCOUNT_TYPES,
    PORTFOLIO_COST_CURRENCIES,
    PORTFOLIO_REQUIRED_COLUMNS,
    account_tax_category,
    is_supported_account_type_label,
    normalize_account_type,
    repair_portfolio_raw_row,
)
from .portfolio_transactions import (
    PORTFOLIO_TRANSACTION_COLUMNS,
    TRANSACTION_CURRENCIES,
    TRANSACTION_TYPES,
    normalize_currency,
    normalize_transaction_type,
)
from .proxy_calibration import BOOLEAN_FIELDS as PROXY_CALIBRATION_BOOLEAN_FIELDS
from .proxy_calibration import (
    MISSING_TRUE_VALUE_MARKERS,
    PROXY_CALIBRATION_COLUMNS,
    PROXY_CALIBRATION_FIELD_NAMES,
    PROXY_CALIBRATION_FIELD_TO_FRIENDLY_COLUMN,
)
from .research_reports import RESEARCH_INDEX_COLUMNS
from .add_eligibility_engine import ADD_ALLOWED_STATUSES
from .external_etf_engine import is_external_etf_allocation_candidate
from .utils import normalize_ticker, read_csv_records, safe_bool, safe_float
from .watchlist_engine import WATCHLIST_COLUMNS


def validate_capital(capital: float) -> list[str]:
    if capital < 0:
        return ["Le capital doit être positif ou égal à zéro."]
    return []


def validate_required_columns(path: str | Path, required_columns: list[str]) -> list[str]:
    path = Path(path)
    if not path.exists():
        return [f"Fichier manquant: {path}"]
    records = read_csv_records(path)
    if records:
        columns = set(records[0].keys())
    else:
        header = path.read_text(encoding="utf-8").splitlines()[0] if path.read_text(encoding="utf-8").splitlines() else ""
        columns = set(header.split(",")) if header else set()
    missing = [column for column in required_columns if column not in columns]
    return [f"Colonne manquante dans {path.name}: {column}" for column in missing]


def validate_portfolio_file(path: str | Path) -> list[str]:
    errors = validate_required_columns(path, PORTFOLIO_REQUIRED_COLUMNS)
    for index, row in enumerate(read_csv_records(path), start=2):
        row = repair_portfolio_raw_row(row)
        ticker = normalize_ticker(row.get("ticker"))
        if not ticker:
            errors.append(f"{Path(path).name}:{index} ticker vide.")
        value_text = str(row.get("current_value_cad") or row.get("current_value") or "").strip()
        shares_text = str(row.get("shares") or "").strip()
        average_cost_text = str(row.get("average_cost_cad") or row.get("average_cost") or "").strip()
        acquisition_value_text = str(row.get("acquisition_value_cad") or row.get("acquisition_value") or "").strip()
        cost_currency = str(row.get("average_cost_currency") or row.get("cost_currency") or "").strip().upper()
        account_type = normalize_account_type(row.get("account_type") or row.get("account"))
        value = safe_float(value_text) if value_text else 0.0
        shares = safe_float(shares_text) if shares_text else 0.0
        average_cost = safe_float(average_cost_text) if average_cost_text else None
        acquisition_value = safe_float(acquisition_value_text) if acquisition_value_text else None
        if value is None or value < 0:
            errors.append(f"{Path(path).name}:{index} current_value invalide.")
        if shares is None or shares < 0:
            errors.append(f"{Path(path).name}:{index} shares invalide.")
        if average_cost is not None and average_cost < 0:
            errors.append(f"{Path(path).name}:{index} average_cost invalide.")
        if acquisition_value is not None and acquisition_value < 0:
            errors.append(f"{Path(path).name}:{index} acquisition_value invalide.")
        if cost_currency and cost_currency not in PORTFOLIO_COST_CURRENCIES:
            errors.append(
                f"{Path(path).name}:{index} average_cost_currency invalide: {cost_currency}. Utiliser CAD ou USD."
            )
        if account_type and not is_supported_account_type_label(account_type):
            errors.append(
                f"{Path(path).name}:{index} account_type invalide: {account_type}. Utiliser TFSA, FHSA, RRSP, NON_REGISTERED ou une variante comme TFSA1."
            )
    return errors


def validate_portfolio_transactions_file(path: str | Path) -> list[str]:
    path = Path(path)
    if not path.exists():
        return []
    errors = validate_required_columns(path, PORTFOLIO_TRANSACTION_COLUMNS)
    for index, row in enumerate(read_csv_records(path), start=2):
        if not any(str(row.get(column) or "").strip() for column in PORTFOLIO_TRANSACTION_COLUMNS):
            continue
        transaction_type = normalize_transaction_type(row.get("transaction_type"))
        account_type = normalize_account_type(row.get("account_type"))
        ticker = normalize_ticker(row.get("ticker"))
        date_text = str(row.get("date") or "").strip()
        if not date_text:
            errors.append(f"{path.name}:{index} date requise au format AAAA-MM-JJ.")
        else:
            try:
                datetime.strptime(date_text, "%Y-%m-%d")
            except ValueError:
                errors.append(f"{path.name}:{index} date invalide: {date_text}. Utiliser AAAA-MM-JJ.")
        if account_type and not is_supported_account_type_label(account_type):
            errors.append(
                f"{path.name}:{index} account_type invalide: {account_type}. Utiliser TFSA, FHSA, RRSP, NON_REGISTERED ou une variante comme TFSA1."
            )
        if transaction_type not in TRANSACTION_TYPES:
            errors.append(
                f"{path.name}:{index} transaction_type invalide: {row.get('transaction_type')}. Utiliser BUY, SELL, CASH_CONTRIBUTION, CASH_WITHDRAWAL, DIVIDEND, TRANSFER_IN ou TRANSFER_OUT."
            )
        for column in ["shares", "price", "fees", "cash_amount"]:
            text = str(row.get(column) or "").strip()
            value = safe_float(text) if text else None
            if value is not None and value < 0:
                errors.append(f"{path.name}:{index} {column} ne peut pas être négatif.")
            elif text and value is None:
                errors.append(f"{path.name}:{index} {column} invalide: {text}.")
        for column in ["price_currency", "fees_currency", "cash_currency"]:
            currency = normalize_currency(row.get(column))
            if currency and currency not in TRANSACTION_CURRENCIES:
                errors.append(
                    f"{path.name}:{index} {column} invalide: {currency}. Utiliser CAD, USD, EUR, GBP, CHF ou JPY."
                )
        if transaction_type in {"BUY", "SELL", "TRANSFER_IN", "TRANSFER_OUT"}:
            if not ticker:
                errors.append(f"{path.name}:{index} ticker requis pour {transaction_type}.")
            if safe_float(row.get("shares")) is None or safe_float(row.get("shares")) <= 0:
                errors.append(f"{path.name}:{index} shares requis et positif pour {transaction_type}.")
            if safe_float(row.get("price")) is None or safe_float(row.get("price")) <= 0:
                errors.append(f"{path.name}:{index} price requis et positif pour {transaction_type}.")
        if transaction_type in {"CASH_CONTRIBUTION", "CASH_WITHDRAWAL", "DIVIDEND"}:
            if safe_float(row.get("cash_amount")) is None or safe_float(row.get("cash_amount")) <= 0:
                errors.append(f"{path.name}:{index} cash_amount requis et positif pour {transaction_type}.")
    return errors


def validate_account_locations_file(path: str | Path) -> list[str]:
    errors = validate_required_columns(path, ACCOUNT_LOCATION_COLUMNS)
    for index, row in enumerate(read_csv_records(path), start=2):
        account_type = normalize_account_type(row.get("account_type"))
        if account_type and account_tax_category(account_type) not in ACCOUNT_TYPES:
            errors.append(f"{Path(path).name}:{index} account_type invalide: {account_type}.")
        value = safe_float(row.get("current_value"))
        if value is None or value < 0:
            errors.append(f"{Path(path).name}:{index} current_value invalide.")
    return errors


def validate_manual_inputs_file(path: str | Path) -> list[str]:
    errors = validate_required_columns(path, MANUAL_COLUMNS)
    for index, row in enumerate(read_csv_records(path), start=2):
        ticker = normalize_ticker(row.get("ticker"))
        if not ticker:
            errors.append(f"{Path(path).name}:{index} ticker vide.")
        for column in BOOL_COLUMNS:
            value = str(row.get(column) or "").strip()
            if value and safe_bool(value) is None:
                errors.append(f"{Path(path).name}:{index} booléen invalide pour {column}: {value}.")
        for column in NUMERIC_COLUMNS:
            value = str(row.get(column) or "").strip()
            if value and safe_float(value) is None:
                errors.append(f"{Path(path).name}:{index} nombre invalide pour {column}: {value}.")
        confidence = str(row.get("manual_confidence_level") or "").strip().upper()
        if confidence and confidence not in {"HIGH", "MEDIUM", "LOW"}:
            errors.append(f"{Path(path).name}:{index} manual_confidence_level invalide: {confidence}.")
    return errors


def validate_friendly_manual_inputs_file(path: str | Path) -> list[str]:
    path = Path(path)
    if not path.exists():
        return []
    parser = configparser.ConfigParser(interpolation=None)
    parser.optionxform = str
    try:
        parser.read(path, encoding="utf-8")
    except configparser.Error as exc:
        return [f"{path.name}: format invalide ({exc})."]
    errors: list[str] = []
    for section in parser.sections():
        ticker = normalize_ticker(section)
        if not ticker:
            errors.append(f"{path.name}: section vide.")
        for column in BOOL_COLUMNS:
            value = parser.get(section, column, fallback="").strip()
            if value and safe_bool(value) is None:
                errors.append(f"{path.name}:{section} booléen invalide pour {column}: {value}.")
        for column in NUMERIC_COLUMNS:
            value = parser.get(section, column, fallback="").strip()
            if value and safe_float(value) is None:
                errors.append(f"{path.name}:{section} nombre invalide pour {column}: {value}.")
        confidence = parser.get(section, "manual_confidence_level", fallback="").strip().upper()
        if confidence and confidence not in {"HIGH", "MEDIUM", "LOW"}:
            errors.append(f"{path.name}:{section} manual_confidence_level invalide: {confidence}.")
    return errors


def validate_watchlist_file(path: str | Path) -> list[str]:
    path = Path(path)
    if not path.exists():
        return []
    errors = validate_required_columns(path, WATCHLIST_COLUMNS)
    for index, row in enumerate(read_csv_records(path), start=2):
        ticker = normalize_ticker(row.get("ticker"))
        if not ticker:
            continue
        priority = str(row.get("manual_priority") or "").strip().upper()
        if priority and priority not in {"HIGH", "MEDIUM", "LOW"}:
            errors.append(f"{path.name}:{index} manual_priority invalide: {priority}.")
    return errors


def validate_market_universe_file(path: str | Path) -> list[str]:
    path = Path(path)
    if not path.exists():
        return []
    errors = validate_required_columns(path, MARKET_UNIVERSE_COLUMNS)
    for index, row in enumerate(read_csv_records(path), start=2):
        ticker = normalize_ticker(row.get("ticker"))
        if not ticker:
            errors.append(f"{path.name}:{index} ticker vide.")
    return errors


def validate_research_index_file(path: str | Path) -> list[str]:
    path = Path(path)
    if not path.exists():
        return []
    errors = validate_required_columns(path, RESEARCH_INDEX_COLUMNS)
    for index, row in enumerate(read_csv_records(path), start=2):
        ticker = normalize_ticker(row.get("ticker"))
        file_name = str(row.get("file_name") or "").strip()
        if file_name and not ticker:
            errors.append(f"{path.name}:{index} ticker requis si file_name est rempli.")
    return errors


def validate_proxy_calibration_file(path: str | Path) -> list[str]:
    path = Path(path)
    if not path.exists():
        return []
    rows = read_csv_records(path)
    if rows and "field" in rows[0]:
        return _validate_legacy_proxy_calibration_file(path, rows)
    errors = validate_required_columns(path, PROXY_CALIBRATION_COLUMNS)
    reverse_field_map = {column: field for field, column in PROXY_CALIBRATION_FIELD_TO_FRIENDLY_COLUMN.items()}
    for index, row in enumerate(rows, start=2):
        ticker = normalize_ticker(row.get("ticker"))
        if not ticker:
            continue
        for column, field in reverse_field_map.items():
            true_value = str(row.get(column) or "").strip()
            if not true_value or true_value.upper() in MISSING_TRUE_VALUE_MARKERS:
                continue
            if field in PROXY_CALIBRATION_BOOLEAN_FIELDS and safe_bool(true_value) is None:
                errors.append(f"{path.name}:{index} {column} doit être TRUE ou FALSE.")
            elif field not in PROXY_CALIBRATION_BOOLEAN_FIELDS and safe_float(true_value) is None:
                errors.append(f"{path.name}:{index} {column} doit être un nombre simple.")
        confidence = str(row.get("confidence") or "").strip().upper()
        if confidence and confidence not in {"HIGH", "MEDIUM", "LOW"}:
            errors.append(f"{path.name}:{index} confidence invalide: {confidence}.")
    return errors


def _validate_legacy_proxy_calibration_file(path: Path, rows: list[dict[str, str]]) -> list[str]:
    errors = validate_required_columns(path, ["ticker", "company_name", "field", "true_value"])
    for index, row in enumerate(rows, start=2):
        ticker = normalize_ticker(row.get("ticker"))
        field = str(row.get("field") or "").strip()
        true_value = str(row.get("true_value") or "").strip()
        if not ticker:
            errors.append(f"{path.name}:{index} ticker vide.")
        if field and field not in PROXY_CALIBRATION_FIELD_NAMES:
            errors.append(f"{path.name}:{index} champ inconnu: {field}.")
        if true_value and true_value.upper() not in MISSING_TRUE_VALUE_MARKERS:
            if field in PROXY_CALIBRATION_BOOLEAN_FIELDS and safe_bool(true_value) is None:
                errors.append(f"{path.name}:{index} true_value doit être TRUE ou FALSE pour {field}.")
            elif field not in PROXY_CALIBRATION_BOOLEAN_FIELDS and safe_float(true_value) is None:
                errors.append(f"{path.name}:{index} true_value doit être un nombre simple pour {field}.")
        confidence = str(row.get("confidence") or "").strip().upper()
        if confidence and confidence not in {"HIGH", "MEDIUM", "LOW"}:
            errors.append(f"{path.name}:{index} confidence invalide: {confidence}.")
    return errors


def validate_input_files(project_root: str | Path) -> list[str]:
    root = Path(project_root)
    data_dir = root / "data"
    errors: list[str] = []
    errors.extend(validate_portfolio_file(data_dir / "portfolio.csv"))
    errors.extend(validate_friendly_manual_inputs_file(data_dir / "manual_inputs_friendly.txt"))
    if (data_dir / "account_locations.csv").exists():
        errors.extend(validate_account_locations_file(data_dir / "account_locations.csv"))
    errors.extend(validate_portfolio_transactions_file(data_dir / "portfolio_transactions.csv"))
    errors.extend(validate_watchlist_file(data_dir / "watchlist.csv"))
    errors.extend(validate_market_universe_file(data_dir / "market_universe.csv"))
    errors.extend(validate_research_index_file(data_dir / "research_reports" / "research_index.csv"))
    errors.extend(validate_proxy_calibration_file(data_dir / "proxy_calibration.csv"))
    return errors


def validate_allocation_rules(allocations: list[dict[str, Any]], analyses: dict[str, dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    for allocation in allocations:
        ticker = normalize_ticker(allocation.get("destination"))
        if ticker == "VFV.TO":
            continue
        amount = safe_float(allocation.get("montant")) or 0.0
        if amount <= 0:
            continue
        analysis = analyses.get(ticker, {})
        if analysis.get("universe") == "DEFENSIVE_ETF_FALLBACK" or analysis.get("asset_type") == "ETF_DEFENSIVE_FALLBACK":
            continue
        if is_external_etf_allocation_candidate(analysis):
            continue
        add_status = analysis.get("add_eligibility_status")
        if add_status:
            if add_status not in ADD_ALLOWED_STATUSES:
                errors.append(f"{ticker} reçoit du capital malgré add_eligibility_status={add_status}.")
        elif analysis.get("liquidation_status") != "GREEN":
            errors.append(f"{ticker} reçoit du capital malgré liquidation_status={analysis.get('liquidation_status')}.")
        if analysis.get("thesis_status") != "INTACT":
            errors.append(f"{ticker} reçoit du capital malgré thesis_status={analysis.get('thesis_status')}.")
        if (safe_float(analysis.get("position_weight")) or 0.0) > 0.40:
            errors.append(f"{ticker} reçoit du capital malgré un poids > 40 %.")
    return errors
