"""Fictional wire inputs only; no model imports or market-snapshot conversion."""
import hashlib
import math

from tests.pit_fixtures import PIT


def qualified_entry(ticker="FICTIONAL_ORDINARY_ENTITY", *, payer=False):
    basis = {"currency": "CAD", "share_basis": "FICTIONAL_CLASS_A_SPLIT_RECONCILED_V1"}
    def identity(identifier, adapter, published="2025-02-01T12:00:00Z"):
        return {"observation_id": identifier, "security_id": "FICTIONAL_ORDINARY_ENTITY", "share_class": "A",
            "provenance": {"source_kind": "SYNTHETIC_OFFICIAL", "source_reference": "synthetic-document:" + identifier,
                "source_version": "fictional-source-v1", "source_document_hash": hashlib.sha256(("fictional:" + identifier).encode()).hexdigest(),
                "source_locator": "synthetic-locator:" + identifier, "published_at": published,
                "available_at": published, "captured_at": published, "extractor_id": adapter, "extractor_version": "1"}}
    roots = [{"root_type": "ReportedDilutedEPS", "identity": identity(f"eps-{year}", "SYNTHETIC_REPORTED_DILUTED_EPS_V1", f"{year+1}-02-01T12:00:00Z"),
        "value": value, "basis": dict(basis), "period": {"start": f"{year}-01-01", "end": f"{year}-12-31"}, "accounting_basis": "IFRS"}
        for year, value in zip(range(2020, 2025), (2., 2.2, 2.5, 2.7, 3.))]
    roots += [{"root_type": "ObservedPrice", "identity": identity("price", "SYNTHETIC_OBSERVED_PRICE_V1", "2025-06-02T12:00:00Z"),
        "value": 45., "basis": dict(basis), "observed_on": "2025-06-02"},
        {"root_type": "ProfileQualification", "identity": identity("profile", "SYNTHETIC_PROFILE_QUALIFICATION_V1"),
         "profile": "ORDINARY_COMPOUNDER", "excluded_structures": ["BANK", "INSURER", "REIT", "ASSET_MANAGER", "RESOURCES_MINING", "ENERGY_CYCLICAL", "PIPELINE", "UTILITY_ACCOUNTING", "INVESTMENT_HOLDING", "MIXED_CONGLOMERATE", "TURNAROUND", "LOSS_MAKING"],
         "rationale": "Explicit fictional ordinary profile; each unsupported structure excluded"}]
    period = {"start": "2024-01-01", "end": "2024-12-31"}
    roots.append({"root_type": "OrdinaryAnnualDividend", "identity": identity("dividend", "SYNTHETIC_ORDINARY_ANNUAL_DIVIDEND_V1"),
        "value": .9, "basis": dict(basis), "period": period, "special_dividends_excluded": True} if payer else {
        "root_type": "VerifiedNonpayer", "identity": identity("nonpayer", "SYNTHETIC_VERIFIED_NONPAYER_V1"), "period": period})
    applicability = {"profile": "ORDINARY_COMPOUNDER", "currency": "CAD", "accounting_basis": "IFRS", "valid_from": "2025-01-01", "valid_through": "2025-12-31"}
    policies = {}
    for key, name, rationale in (("mature_growth", "mature", "Fictional mature anchors for mechanics only"),
            ("terminal_valuation", "terminal", "Fictional independently supplied terminal multiples"),
            ("distributions", "distribution", "Fictional continued distribution assumption")):
        policies[key] = {"policy_id": "synthetic-"+name, "schema_version": "2026-09-09-terminal-policy-v1" if name == "terminal" else "2026-09-09-assumption-policy-v1",
            "applicability": dict(applicability), "rationale": rationale, "assumption_id": "synthetic-"+name+"-assumption"}
    policies["mature_growth"]["log_growth"] = dict(zip(("bear", "base", "bull"), map(math.log1p, (.01, .03, .05))))
    policies["terminal_valuation"]["terminal_pe"] = {"bear": 12., "base": 16., "bull": 20.}
    policies["distributions"]["rule"] = "CONSTANT_MATCHED_ORDINARY_PAYOUT" if payer else "CONTINUED_VERIFIED_NONPAYER"
    return {"ticker": ticker, "status": "QUALIFIED_SYNTHETIC", "facts": {
        "contract_version": "2026-09-09-synthetic-qualified-facts-v1", "as_of": PIT,
        "security_id": "FICTIONAL_ORDINARY_ENTITY", "share_class": "A", "basis": basis,
        "accounting_basis": "IFRS", "latest_required_fiscal_end": "2024-12-31", "roots": roots},
        "policies": policies, "unavailable_reasons": []}


def transport(*entries):
    return {"contract_version": "pit-expected-return-inputs-v1", "entries": list(entries)}


def unavailable_entry(ticker="FICTIONAL_ABSENCE"):
    return {"ticker": ticker, "status": "EXPLICITLY_UNAVAILABLE", "facts": None, "policies": None,
            "unavailable_reasons": ["NO_QUALIFIED_EXPECTED_RETURN_INPUT"]}
