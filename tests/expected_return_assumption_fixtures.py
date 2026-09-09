"""Fictional data and numerical policies ONLY for PR4B1 mechanical tests."""
from dataclasses import replace
import hashlib
import math

from src import expected_return_assumptions as a
from src import expected_return_policy as p

AS_OF = "2026-06-30T18:00:00Z"
BASIS = a.ShareBasis("CAD", "FICTIONAL_CLASS_A_SPLIT_RECONCILED_V1")
APPLICABILITY = p.Applicability("ORDINARY_COMPOUNDER", "CAD", "IFRS", "2026-01-01", "2026-12-31")


def identity(identifier, adapter, *, published="2026-02-01T12:00:00Z", weak=False):
    return a.Identity(identifier, "FICTIONAL_ORDINARY_ENTITY", "A", a.Provenance(
        a.SourceKind.SYNTHETIC_MANUAL if weak else a.SourceKind.SYNTHETIC_OFFICIAL,
        "synthetic-document:" + identifier, "fictional-source-v1",
        hashlib.sha256(("fictional:" + identifier).encode()).hexdigest(),
        "synthetic-locator:" + identifier, published, published, published, adapter, "1"))


def policies(*, payer=False, mature=(.01, .03, .05), terminal=(12., 16., 20.)):
    return dict(
        mature_policy=p.MatureGrowthPolicy("synthetic-mature", p.EXPECTED_RETURN_ASSUMPTION_POLICY_SCHEMA_VERSION,
            APPLICABILITY, p.ScenarioValues(*(math.log1p(v) for v in mature)),
            "Fictional mature anchors for mechanics only", "synthetic-mature-assumption"),
        terminal_policy=p.TerminalValuationPolicy("synthetic-terminal", p.EXPECTED_RETURN_TERMINAL_POLICY_SCHEMA_VERSION,
            APPLICABILITY, p.ScenarioValues(*terminal),
            "Fictional independently supplied terminal multiples", "synthetic-terminal-assumption"),
        distribution_policy=p.DistributionPolicy("synthetic-distribution", p.EXPECTED_RETURN_ASSUMPTION_POLICY_SCHEMA_VERSION,
            APPLICABILITY, p.DistributionRule.CONSTANT_MATCHED_ORDINARY_PAYOUT if payer else p.DistributionRule.CONTINUED_VERIFIED_NONPAYER,
            "Fictional continued distribution assumption", "synthetic-distribution-assumption"))


def facts(*, eps=(2., 2.2, 2.5, 2.7, 3.), price=45., payer=False, weak=False):
    roots = []
    start_year = 2026 - len(eps)
    for year, value in enumerate(eps, start_year):
        roots.append(a.ReportedDilutedEPS(identity("eps-" + str(year), a.AdapterIdentity.SYNTHETIC_REPORTED_DILUTED_EPS_V1,
            published=f"{year + 1}-02-01T12:00:00Z", weak=weak), value, BASIS,
            a.AnnualPeriod(f"{year}-01-01", f"{year}-12-31"), "IFRS"))
    roots.append(a.ObservedPrice(identity("price", a.AdapterIdentity.SYNTHETIC_OBSERVED_PRICE_V1,
        published="2026-06-30T12:00:00Z", weak=weak), price, BASIS, "2026-06-30"))
    roots.append(a.ProfileQualification(identity("profile", a.AdapterIdentity.SYNTHETIC_PROFILE_QUALIFICATION_V1, weak=weak),
        a.Profile.ORDINARY_COMPOUNDER, a.UNSUPPORTED_STRUCTURES, "Explicit fictional ordinary profile; each unsupported structure excluded"))
    period = a.AnnualPeriod("2025-01-01", "2025-12-31")
    roots.append(a.OrdinaryAnnualDividend(identity("dividend", a.AdapterIdentity.SYNTHETIC_ORDINARY_ANNUAL_DIVIDEND_V1, weak=weak),
        .9, BASIS, period, True) if payer else a.VerifiedNonpayer(
            identity("nonpayer", a.AdapterIdentity.SYNTHETIC_VERIFIED_NONPAYER_V1, weak=weak), period))
    return a.QualifiedFacts(a.EXPECTED_RETURN_FACTS_CONTRACT_VERSION, AS_OF, "FICTIONAL_ORDINARY_ENTITY", "A",
        BASIS, "IFRS", "2025-12-31", tuple(roots))


def change_root(fixture, identifier, **changes):
    return replace(fixture, roots=tuple(replace(r, **changes) if r.identity.observation_id == identifier else r for r in fixture.roots))


def change_provenance(fixture, identifier, **changes):
    return replace(fixture, roots=tuple(replace(r, identity=replace(r.identity, provenance=replace(r.identity.provenance, **changes)))
        if r.identity.observation_id == identifier else r for r in fixture.roots))


def without(fixture, identifier):
    return replace(fixture, roots=tuple(r for r in fixture.roots if r.identity.observation_id != identifier))


# Earnings/share-count identities are test-only input preparation. No share-count
# or descriptive margin context is an accepted constructor economic root.
IDENTITY_CASES = (
    ("moderate_dilution", 1.21, 1.10),
    ("strong_buyback", 1.05, .90),
)
HISTORY_CASES = (
    ("stable_mature", (2., 2., 2., 2., 2.)),
    ("high_growth_fade", (1., 1.4, 1.9, 2.6, 3.5)),
    ("temporary_margin_expansion", (1., 1., 1.1, 1.5, 2.)),
    ("margin_compression", (3., 2.9, 2.6, 2.4, 2.)),
)
