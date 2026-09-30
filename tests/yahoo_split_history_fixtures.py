"""Fictional Yahoo Chart split-history bytes; never real market evidence."""
import json


def split_event(epoch, numerator, denominator, *, ratio=None):
    return {
        "date": epoch,
        "numerator": numerator,
        "denominator": denominator,
        "splitRatio": ratio if ratio is not None else f"{numerator}:{denominator}",
    }


def split_chart_response(*, symbol="FICT", events=(), provider_error=None,
                         result_count=1):
    splits = {str(event["date"]): event for event in events}
    result = [{
        "meta": {"symbol": symbol},
        "timestamp": [],
        "events": {"splits": splits},
        "indicators": {},
    } for _ in range(result_count)]
    return json.dumps({"chart": {"result": result, "error": provider_error}},
                      sort_keys=True, separators=(",", ":")).encode()
