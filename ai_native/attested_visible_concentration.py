"""CEO-attested visible-profile weight concentration, never brokerage-account proof.

An attestation clarifies which *displayed view* the CEO wishes to discuss;
it never changes the public/profile source into private, certified holdings.
No money, cash, ETF look-through, issuer aggregation or trade is inferred.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Any, Mapping

COMPLETE_FLAGS = (
    "all_rows_visible", "other_group_expanded_or_absent", "cash_visible",
    "weights_comparable", "account_filter_visible", "sync_date_visible",
)
ATTEST = "CEO_ATTESTS_VISIBLE_SCOPE_AS_DISPLAYED"


def prepare_attested_visible_concentration(
    reference: Mapping[str, Any], attestation: Mapping[str, Any],
) -> dict[str, Any]:
    if (not isinstance(reference, Mapping)
            or reference.get("status") != "PUBLIC_REFERENCE_DESCRIPTIVE_ONLY"
            or reference.get("ownership_authority") != "NOT_ESTABLISHED"
            or reference.get("source_authentication") != "NOT_PERFORMED"
            or reference.get("private_holdings_import") != "NONE"
            or reference.get("allocation_authority") != "NONE"
            or reference.get("trading_authority") != "NONE"
            or reference.get("storage") != "NONE"):
        raise ValueError("ATTESTED_VIEW_REFERENCE_AUTHORITY_INVALID")
    if (not isinstance(attestation, Mapping)
            or set(attestation) != {"analysis_id", "analysis_as_of", "scope_attestation"}
            or attestation.get("analysis_id") != reference.get("analysis_id")
            or attestation.get("analysis_as_of") != reference.get("analysis_as_of")
            or attestation.get("scope_attestation") != ATTEST):
        raise ValueError("ATTESTED_VIEW_CASE_OR_SCOPE_INVALID")
    flags = reference.get("coverage")
    if not isinstance(flags, Mapping):
        raise ValueError("ATTESTED_VIEW_COVERAGE_INVALID")
    lacking = [flag for flag in COMPLETE_FLAGS if flags.get(flag) is not True]
    if reference.get("observation_as_of") == "UNKNOWN":
        lacking.append("observation_as_of")
    records = reference.get("positions_private")
    if not isinstance(records, list) or not records:
        raise ValueError("ATTESTED_VIEW_POSITIONS_INVALID")
    parsed: list[Decimal] = []
    for row in records:
        if not isinstance(row, Mapping):
            raise ValueError("ATTESTED_VIEW_POSITION_SCHEMA_INVALID")
        raw = row.get("weight_pct")
        if raw is None or row.get("visibility") != "VISIBLE":
            lacking.append("unobserved_weight_or_row")
            continue
        if not isinstance(raw, str):
            raise ValueError("ATTESTED_VIEW_WEIGHT_INVALID")
        try:
            value = Decimal(raw)
        except Exception as exc:
            raise ValueError("ATTESTED_VIEW_WEIGHT_INVALID") from exc
        if not value.is_finite() or not 0 <= value <= 100 or value.as_tuple().exponent < -2:
            raise ValueError("ATTESTED_VIEW_WEIGHT_INVALID")
        parsed.append(value)
    # Match the reported source total. Never silently rescale a view to 100%.
    total = sum(parsed, Decimal("0"))
    displayed_sum = reference.get("displayed_weight_sum_pct")
    if displayed_sum is None or len(parsed) != len(records):
        lacking.append("displayed_weight_sum_or_full_coverage")
    else:
        try:
            if Decimal(displayed_sum) != total:
                raise ValueError("ATTESTED_VIEW_SOURCE_SUM_CONFLICT")
        except (TypeError, ArithmeticError) as exc:
            raise ValueError("ATTESTED_VIEW_SOURCE_SUM_INVALID") from exc
    # Maximum discrepancy from rounding each individual line to 2dp.
    # This is NOT permission to renormalize. If greater, denominator fails.
    tolerance = Decimal("0.005") * len(records)
    if abs(total - Decimal("100")) > tolerance:
        lacking.append("displayed_sum_not_100_within_rounding")
    complete = not lacking
    ordered = sorted(parsed, reverse=True)
    return {
        "status": ("CONDITIONAL_ATTESTED_DISPLAY_VIEW_CONCENTRATION"
                   if complete else "DISPLAY_VIEW_DENOMINATOR_UNESTABLISHED"),
        "analysis_id": reference["analysis_id"],
        "analysis_as_of": reference["analysis_as_of"],
        "observation_as_of": reference["observation_as_of"],
        "scope_attestation": "CEO_REPORTED_NOT_INDEPENDENTLY_AUTHENTICATED",
        "denominator": ("DISPLAYED_VIEW_ONLY" if complete else "UNKNOWN"),
        "top_one_visible_line_pct": f"{ordered[0]:.2f}" if complete else None,
        "top_five_visible_lines_pct": (
            f"{sum(ordered[:5], Decimal('0')):.2f}" if complete else None),
        "displayed_sum_pct": f"{total:.2f}" if len(parsed) == len(records) else None,
        "rounding_tolerance_pct": f"{tolerance:.3f}",
        "blockers": sorted(set(lacking)),
        "issuer_level_lookthrough": "UNAVAILABLE_WITHOUT_SEPARATE_EVIDENCE",
        "personal_account_verification": "NOT_PERFORMED",
        "brokerage_ownership": "NOT_PROVEN",
        "monetary_denominator": "UNKNOWN",
        "post_contribution_weights": "UNAVAILABLE",
        "financial_policy_or_trading_authority": "NONE",
        "source_authentication": "NOT_PERFORMED",
        "storage": "NONE",
    }


def render_attested_visible_concentration(review: Mapping[str, Any]) -> str:
    if (not isinstance(review, Mapping)
            or review.get("status") not in {
                "CONDITIONAL_ATTESTED_DISPLAY_VIEW_CONCENTRATION",
                "DISPLAY_VIEW_DENOMINATOR_UNESTABLISHED"}
            or review.get("scope_attestation") != "CEO_REPORTED_NOT_INDEPENDENTLY_AUTHENTICATED"
            or review.get("personal_account_verification") != "NOT_PERFORMED"
            or review.get("brokerage_ownership") != "NOT_PROVEN"
            or review.get("monetary_denominator") != "UNKNOWN"
            or review.get("post_contribution_weights") != "UNAVAILABLE"
            or review.get("financial_policy_or_trading_authority") != "NONE"
            or review.get("source_authentication") != "NOT_PERFORMED"
            or review.get("storage") != "NONE"):
        raise ValueError("ATTESTED_VIEW_REPORT_AUTHORITY_INVALID")
    lines = [
        "## Périmètre de vue attesté — concentration affichée conditionnelle",
        "Le CEO rapporte que cette vue est le périmètre à étudier. Ceci ne certifie "
        "ni propriété du compte, ni encaisse, ni relevé courtier, ni portefeuille privé.",
    ]
    if review["status"] == "CONDITIONAL_ATTESTED_DISPLAY_VIEW_CONCENTRATION":
        lines.append(
            "Concentration des **lignes visibles uniquement** : première ligne "
            + review["top_one_visible_line_pct"] + " %, cinq premières "
            + review["top_five_visible_lines_pct"] + " %. Les pourcentages "
            "affichés ne sont pas normalisés. Ce ne sont pas des expositions "
            "agrégées par émetteur ni du look-through de FNB."
        )
    else:
        lines.append(
            "Dénominateur de la vue INSUFFISANT : aucune concentration du "
            "périmètre complet calculable. Vérifier visibilité de toutes les "
            "lignes, encaisse, filtre de compte, date et comparabilité des poids."
        )
    lines.append(
        "Valeur monétaire du compte et poids après nouvelle contribution : "
        "INDISPONIBLES. Analyse conditionnelle seulement; aucune allocation "
        "ni transaction autorisée."
    )
    return "\n".join(lines)
