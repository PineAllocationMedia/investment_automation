"""F4: verify specialist-returned method text against reviewed R1 Git blob pins.

Content matching demonstrates only that supplied bytes match a repository
reference. It does NOT prove a ChatGPT Project fetched, read, loaded or followed
a method, or that its project settings or financial policy are approved.
Receipts are opt-in, private and processed without storing method contents.
"""
from __future__ import annotations

from datetime import date
import hashlib
from typing import Any, Mapping

from .method_manifest import prepare_method_manifest
from .method_handoff_bundle import MAX_METHOD_BYTES, MAX_BUNDLE_DOCUMENT_BYTES
from .strategy_research_brief import prepare_strategy_research_brief

ROUTES = frozenset({
    "PROJECT_GITHUB_RETRIEVAL_REPORTED",
    "OPERATOR_PASTED_METHOD_TEXT",
    "NOT_RETRIEVED",
})


def _date(value: Any, name: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"METHOD_RECEIPT_{name}_INVALID")
    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"METHOD_RECEIPT_{name}_INVALID") from exc
    if parsed.isoformat() != value:
        raise ValueError(f"METHOD_RECEIPT_{name}_INVALID")
    return value


def evaluate_returned_method_text(
    *, request: Mapping[str, Any], specialist: str,
    receipt: Mapping[str, Any],
) -> dict[str, Any]:
    """Compare an original specialist reply's method text to the pinned manifest.

    A self-reported GitHub retrieval route is not independently authenticated.
    Any wrong/missing document produces a BLOCKED result, never a partial pass.
    No method raw text is copied into the result.
    """
    if not isinstance(request, Mapping) or request.get("ceo_initiated") is not True:
        raise ValueError("METHOD_RECEIPT_CEO_REQUEST_REQUIRED")
    if specialist not in {"IR", "PI"}:
        raise ValueError("METHOD_RECEIPT_SPECIALIST_INVALID")
    if not isinstance(receipt, Mapping) or set(receipt) != {
        "analysis_id", "analysis_as_of", "strategy_id", "specialist",
        "reported_retrieval", "documents",
    }:
        raise ValueError("METHOD_RECEIPT_EXACT_SCHEMA_REQUIRED")
    aid = request.get("analysis_id")
    mode = request.get("strategy_id")
    if not isinstance(aid, str) or not aid.strip() or len(aid) > 256:
        raise ValueError("METHOD_RECEIPT_ANALYSIS_ID_INVALID")
    as_of = _date(request.get("as_of"), "AS_OF")
    if (receipt.get("analysis_id") != aid
            or receipt.get("analysis_as_of") != as_of
            or receipt.get("strategy_id") != mode
            or receipt.get("specialist") != specialist):
        raise ValueError("METHOD_RECEIPT_MANDATE_OR_SPECIALIST_MISMATCH")
    if not isinstance(mode, str):
        raise ValueError("METHOD_RECEIPT_MODE_INVALID")
    route = receipt["reported_retrieval"]
    if not isinstance(route, str) or route not in ROUTES:
        raise ValueError("METHOD_RECEIPT_RETRIEVAL_ROUTE_INVALID")
    expected_ref = prepare_strategy_research_brief(mode)[
        "design_reference_not_loaded_or_approved"
    ]
    manifest = prepare_method_manifest(specialist, expected_ref)
    expected = manifest["documents"]
    documents = receipt["documents"]
    if not isinstance(documents, list) or len(documents) > 25:
        raise ValueError("METHOD_RECEIPT_DOCUMENTS_INVALID")
    if route == "NOT_RETRIEVED":
        if documents:
            raise ValueError("METHOD_RECEIPT_UNRETRIEVED_CANNOT_CARRY_TEXT")
        outcome = "METHOD_NOT_RETRIEVED_OR_LOADED"
        problems = [d["path"] for d in expected]
    else:
        # Exact document sequence makes role/mode/pin substitution detectable.
        if len(documents) != len(expected):
            outcome = "INCOMPLETE_METHOD_TEXT_BLOCKED"
            problems = [d["path"] for d in expected]
        else:
            problems = []
            size = 0
            for row, pin in zip(documents, expected):
                if (not isinstance(row, Mapping)
                        or set(row) != {"path", "content"}
                        or row.get("path") != pin["path"]):
                    raise ValueError("METHOD_RECEIPT_PATH_OR_ORDER_MISMATCH")
                content = row["content"]
                if not isinstance(content, str):
                    raise ValueError("METHOD_RECEIPT_TEXT_INVALID")
                raw = content.encode("utf-8")
                size += len(raw)
                if len(raw) > MAX_METHOD_BYTES or size > MAX_BUNDLE_DOCUMENT_BYTES:
                    raise ValueError("METHOD_RECEIPT_TEXT_TOO_LARGE")
                actual = hashlib.sha1(
                    b"blob " + str(len(raw)).encode("ascii") + b"\x00" + raw
                ).hexdigest()
                if actual != pin["git_blob_sha"]:
                    problems.append(pin["path"])
            outcome = (
                "RETURNED_TEXT_MATCHES_PINNED_GIT_BLOBS_ONLY"
                if not problems else "STALE_OR_CHANGED_METHOD_TEXT_BLOCKED"
            )
    return {
        "status": "F4_SPECIALIST_RETURNED_METHOD_CONTENT_CHECK",
        "analysis_id": aid,
        "analysis_as_of": as_of,
        "specialist": specialist,
        "strategy_id": mode,
        "reported_retrieval": route,
        "expected_reference_commit": manifest["reference_commit"],
        "document_count_expected": len(expected),
        "content_result": outcome,
        "mismatched_or_missing_reference_paths": problems,
        "reference_role": "PINNED_DESIGN_NOT_FINANCIAL_POLICY_APPROVAL",
        "received_content_check": "GIT_BLOB_SHA1_OF_RETURNED_TEXT_ONLY",
        "actual_project_retrieval": "SPECIALIST_REPORTED_NOT_INDEPENDENTLY_VERIFIED",
        "actual_project_method_read_or_application": "NOT_INDEPENDENTLY_VERIFIED",
        "actual_project_settings": "NOT_INSPECTED",
        "investment_policy_authority": "NOT_GRANTED",
        "portfolio_or_trade_authority": "NONE",
        "storage": "NONE",
    }


def render_returned_method_receipt(review: Mapping[str, Any]) -> str:
    """No original method content, issuer data, personal IDs or source text."""
    if (not isinstance(review, Mapping)
            or review.get("status") != "F4_SPECIALIST_RETURNED_METHOD_CONTENT_CHECK"
            or review.get("specialist") not in {"IR", "PI"}
            or review.get("content_result") not in {
                "RETURNED_TEXT_MATCHES_PINNED_GIT_BLOBS_ONLY",
                "STALE_OR_CHANGED_METHOD_TEXT_BLOCKED",
                "INCOMPLETE_METHOD_TEXT_BLOCKED",
                "METHOD_NOT_RETRIEVED_OR_LOADED",
            }
            or review.get("actual_project_retrieval") !=
                "SPECIALIST_REPORTED_NOT_INDEPENDENTLY_VERIFIED"
            or review.get("actual_project_method_read_or_application") !=
                "NOT_INDEPENDENTLY_VERIFIED"
            or review.get("actual_project_settings") != "NOT_INSPECTED"
            or review.get("investment_policy_authority") != "NOT_GRANTED"
            or review.get("portfolio_or_trade_authority") != "NONE"
            or review.get("storage") != "NONE"):
        raise ValueError("METHOD_RECEIPT_REPORT_AUTHORITY_INVALID")
    role = review["specialist"]
    label = review["content_result"]
    return (
        f"## F4 — Méthodes {role}: {label}\n"
        "Comparaison des octets renvoyés par le spécialiste avec le manifeste "
        "GitHub épinglé. Un texte concordant ne démontre ni l'accès effectif "
        "du Project à GitHub, ni sa lecture/application, ni les paramètres "
        "actifs du Project. En cas d'absence ou d'écart, méthode NON CHARGÉE "
        "ou NON VÉRIFIÉE pour toute conclusion qui en dépend. "
        "Aucune nouvelle politique ni allocation n'est autorisée."
    )
