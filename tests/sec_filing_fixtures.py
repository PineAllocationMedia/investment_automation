"""Fictional SEC-style bytes only. Zero CIK is a fixture identifier."""
import copy
import json

CIK = "0000000000"
T1 = "2025-03-01T12:00:00Z"
T2 = "2026-03-01T12:00:00Z"
BETWEEN = "2025-09-01T12:00:00Z"


def row(year=2024, value=2, **changes):
    result = {"start": f"{year}-01-01", "end": f"{year}-12-31", "val": value,
              "fy": year, "fp": "FY", "form": "10-K", "filed": f"{year+1}-02-01",
              "accn": f"0000000000-{(year+1) % 100:02d}-000001", "frame": f"CY{year}"}
    result.update(changes)
    return result


def source(rows=None, *, units=None):
    return {"cik": 0, "entityName": "Fictional Archive Fixture",
            "facts": {"us-gaap": {"EarningsPerShareDiluted": {
                "label": "Diluted earnings per share", "description": "Fictional fixture",
                "units": units if units is not None else {"USD/shares": rows if rows is not None else
                    [row(year, value) for year, value in zip(range(2020, 2025), (1, 1.2, 1.4, 1.8, 2))]}}}}}


def raw(payload=None, *, reverse=False):
    def reorder(value):
        if type(value) is dict:
            return {key: reorder(child) for key, child in reversed(list(value.items()))}
        if type(value) is list:
            return [reorder(child) for child in value]
        return value
    payload = copy.deepcopy(source() if payload is None else payload)
    return json.dumps(reorder(payload) if reverse else payload, separators=(",", ":")).encode()


def amendment():
    return row(2024, 1.75, fy=2025, form="10-K/A", filed="2026-02-01", accn="0000000000-26-000002")
