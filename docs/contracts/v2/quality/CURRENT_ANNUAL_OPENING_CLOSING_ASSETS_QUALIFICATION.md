# CURRENT annual opening and closing Assets qualification

## Versions, scope and authority

Contract: `2026-10-10-current-annual-opening-closing-assets-qualification-v1`.
Qualifier: `2026-10-10-adjacent-common-filing-exact-decimal-usd-assets-instants-qualification-v1`.
Evidence kind: `CURRENT_ANNUAL_OPENING_CLOSING_ASSETS_QUALIFICATION`.
Authority: `QUALITY_OPENING_CLOSING_ASSETS_EVIDENCE_ONLY`.

This foundation preserves exact reported opening and closing `us-gaap:Assets`
from one coherent CURRENT SEC Companyfacts annual presentation. It performs no
average-assets, ROA, ROE, ROIC or capital-efficiency calculation and grants no
investment or production authority. Previously completed accounting periods do
not establish what PAM possessed at a historical cutoff.

Implementation baseline is integration branch
`model-v2/expected-return-challenger`, HEAD
`33fa23affbe896bf0f204d7ead2c2346560b1b45`, tree
`0e992fc46faa83918e7deeb016924227853b0f52` (PR #127 canonical).
Exactly three new files are in scope: this contract,
`economic_facts/sec_current_annual_opening_closing_assets.py`, and
`tests/test_sec_current_annual_opening_closing_assets.py`. Every existing file,
provider, dependency, upstream factory, extraction, diagnostic, governance,
V1/PIT component and model rule is out of scope.

## Public boundary and factory authentication

`qualify_sec_current_annual_opening_closing_assets(archive, profile)` accepts
exactly native `SecArchive` and native
`OrdinaryCompounderMethodProfileQualification`. Subclasses, mappings,
duck-typed inputs, detached comparability and caller-selected issuer, CIK,
period, dates, receipt, source row, amount or outcome are rejected.

The qualifier independently reconstructs the canonical ordinary-compounder
factory projection, preserving the PR #123 / #125 safeguards. Supplied versions,
limitations, SIC metadata, structural decisions, exact reason families,
supporting semantic/evidence identities and expected-versus-actual replay
identities must match that projection. A self-consistent dataclass and hashes
alone do not authenticate a fabricated BANK-to-established profile. Unknown or
factory-impossible states are programming-contract errors and raise
`CurrentAnnualOpeningClosingAssetsError`.

Genuine established, BANK/unsupported, unavailable, turnaround, loss-making,
mixed and replay-conflict profiles retain their native meaning. The expected
comparability semantic and evidence IDs are checked independently against actual
embedded IDs; a canonical mismatch projects upstream `SOURCE_CONFLICT`.

Route issuer/security keys, source CIK, receipt, request and series must agree.
The selected embedded receipt must equal the archive receipt, and source bytes
must match its immutable object hash and length. For source qualification, the
embedded CURRENT evidence assessment must equal independent replay through the
existing `assess_sec_current_evidence` verifier against that same archive/object.
A self-consistent fabricated series or dates cannot replace captured source facts.
No acquisition, network call,
clock read or historical reconstruction occurs. The exact five comparable annual
period decisions must reproduce the embedded series/presentation projection;
malformed or fabricated dates and established chains are contract errors.

## Exact dates

For an established ordinary-compounder profile, the closing date is the latest
comparable annual `period_end`. The opening date is the immediately preceding
comparable annual `period_end`. It must equal latest `period_start` minus exactly
one calendar day, using ISO calendar arithmetic across leap days and year ends.
No 365/366-day subtraction or nearest observation substitution is allowed.

A structurally valid chain lacking that adjacent preceding boundary yields
`EVIDENCE_UNAVAILABLE / CANONICAL_OPENING_BALANCE_DATE_UNAVAILABLE`, with no
manufactured opening date. Legitimate upstream profiles without a period chain
retain absent period/date context and their native upstream reason.

The present canonical EPS resolver itself admits only adjacent fixed-month-end
chains. Tests of the defensive nonadjacent projection and leap-day adjacency
helper prove local mechanics, not a genuine nonadjacent admitted source route.
The current PR5C request factory also requires C3 replay IDs as hashes and cannot
construct a no-series profile; absent-context helper coverage does not claim an
authentic no-series factory demonstration.

## Exact source semantics and common presentation

Reuse the existing lossless
`economic_facts.sec_assets_liabilities.extract_assets_liabilities` through imports.
Only namespace `us-gaap`, concept `Assets`, accounting basis `US_GAAP`, exact
unit `USD` and the canonical source CIK are admissible. Liabilities never supplies
a value. Issuer extensions, alternative tags, derived totals, book-value proxies
and provider financial data are not substitutes.

Each admissible row must have:

- `start is None` and `end` exactly equal to the required opening or closing date;
- `fp = FY`, form `10-K` or `10-K/A`, integer fiscal-year metadata;
- a valid exact ISO filed date and SEC accession;
- a finite exact `Decimal` and no extraction metadata limitation.

Zero and negative finite source values are preserved without economic judgment.
JSON decimals are parsed exactly; numeric facts never pass through binary float.
Malformed source structures and nonfinite evidence fail closed. Missing never
becomes zero. Duration, quarterly/YTD and nearby-period substitutes are rejected.

Establishment requires at least one accession with admissible Assets rows for
**both** required instants. Standalone prior-filing opening facts cannot be paired
with closing facts from a different accession. Only common paired accessions
participate in competing-value analysis. Orphan observations cannot poison an
otherwise coherent pair.

Within each common accession, form, filed date and fiscal year must each be
coherent. Optional `frame` equality is unnecessary. Across all common
presentations, opening amounts must agree exactly and closing amounts must agree
exactly. Any contradiction fails as `SOURCE_CONFLICT`; no latest, majority,
median, maximum, minimum or preferred filing suppresses it.

## Closed capabilities and reasons

| Native profile | Local result / reason |
| --- | --- |
| `ORDINARY_COMPOUNDER_PROFILE_ESTABLISHED` | Source qualification proceeds |
| `PROFILE_UNAVAILABLE` | `EVIDENCE_UNAVAILABLE / UPSTREAM_PROFILE_UNAVAILABLE` |
| `PROFILE_UNSUPPORTED` | `EVIDENCE_UNSUPPORTED / UPSTREAM_PROFILE_UNSUPPORTED` |
| `SOURCE_CONFLICT` | `SOURCE_CONFLICT / UPSTREAM_SOURCE_CONFLICT` |

The four states are `OPENING_CLOSING_ASSETS_ESTABLISHED`, `EVIDENCE_UNAVAILABLE`,
`EVIDENCE_UNSUPPORTED` and `SOURCE_CONFLICT`. Reasons are unique and sorted
lexically by their closed enum value:

- `UPSTREAM_PROFILE_UNAVAILABLE`;
- `UPSTREAM_PROFILE_UNSUPPORTED`;
- `UPSTREAM_SOURCE_CONFLICT`;
- `CANONICAL_ROUTE_IDENTITY_CONFLICT`;
- `CAPTURE_REPLAY_CONFLICT`;
- `SOURCE_CIK_CONFLICT`;
- `CANONICAL_OPENING_BALANCE_DATE_UNAVAILABLE`;
- `CLOSING_ASSETS_UNAVAILABLE`;
- `OPENING_ASSETS_UNAVAILABLE`;
- `EXACT_USD_UNIT_UNAVAILABLE`;
- `FINITE_CLOSING_ASSETS_VALUE_UNAVAILABLE`;
- `FINITE_OPENING_ASSETS_VALUE_UNAVAILABLE`;
- `EXACT_OPENING_CLOSING_INSTANT_PRESENTATION_UNAVAILABLE`;
- `NO_COMMON_ANNUAL_FILING_ACCESSION`;
- `COMPETING_CLOSING_ASSETS_VALUES`;
- `COMPETING_OPENING_ASSETS_VALUES`;
- `COMMON_FILING_METADATA_CONFLICT`;

Missing concept/boundary, wrong USD unit, missing/nonfinite numeric value,
inexact instant/annual presentation, no common filing, competing amounts and
conflicting common-filing metadata remain distinct reasons. Archive/object
replay or malformed source errors project `CAPTURE_REPLAY_CONFLICT`.
Non-established output carries no partial opening/closing amounts, selected
observation IDs, selected source observations or supporting filing evidence.

## Immutable result and identity

`CurrentAnnualOpeningClosingAssetsQualification` is frozen and uses immutable
tuples. Its deterministic `to_dict()` contains versions, kind, state/reasons,
native profile state/reasons, route context, source CIK, annual start/end and
opening/closing dates, namespace/concept/basis/unit, exact amounts, actual
upstream profile/comparability semantic/evidence IDs, capture receipt/object/
timestamp/locator, selected IDs and lossless observations for each instant,
common accessions, coherent supporting filing metadata and authority/limitations.
Selected IDs partition the supporting filings exactly. Source rows retain their
row JSON, source and semantic locators, extraction version and source semantics.

The semantic fingerprint binds stable economic meaning: versions, kind, exact
state/reasons, native profile state/reasons, route-context presence/absence,
source CIK, annual period and both balance dates, accounting semantics, exact
canonical amounts, authority and full limitations. It excludes opaque route
keys, upstream semantic/evidence identities, receipts, object hashes,
timestamps, locators, row IDs and filing provenance. Equal finite Decimal
representations canonicalize identically without rounding or ambient-context
precision dependence. Changing either genuine amount changes semantic identity.

The evidence fingerprint binds semantic identity plus actual upstream semantic
and evidence IDs, route-local keys, capture provenance, selected opening/closing
observation evidence and supporting accessions/metadata. Genuine independently
captured bytes with unchanged economics preserve `semantic_id` and change
`evidence_id`, even when upstream semantic IDs and route keys change. Tests
capture source bytes at separate timestamps and replay the native factory; they
do not substitute artificial IDs to demonstrate recapture. These fictional SEC
fixtures prove mechanics only, not real-issuer availability or source licensing.

## Closed authority limitations

The result denies every authority below; no derived ratio or investment decision
is exposed:

- `ONLY_US_GAAP_ASSETS`;
- `NO_TAXONOMY_SUBSTITUTION`;
- `NO_AVERAGE_ASSETS`;
- `NO_ROA`;
- `NO_ROE`;
- `NO_ROIC`;
- `NO_INVESTED_CAPITAL_INTERPRETATION`;
- `NO_TANGIBLE_BOOK_VALUE`;
- `NO_LIQUIDATION_VALUE`;
- `NO_ASSET_QUALITY_JUDGMENT`;
- `NO_CAPITAL_EFFICIENCY_JUDGMENT`;
- `NO_ASSET_GROWTH_QUALITY_OR_HISTORICAL_TREND`;
- `NO_LEVERAGE_LIQUIDITY_OR_SOLVENCY_CONCLUSION`;
- `NO_CROSS_COMPANY_OR_CROSS_SECTOR_COMPARABILITY`;
- `NO_QUALITY_SCORE_GRADE_RANKING_AGGREGATION_OR_WEIGHTING`;
- `NO_DURABILITY_CONCLUSION`;
- `NO_EXPECTED_RETURN_OR_CONFIDENCE_EFFECT`;
- `NO_RECOMMENDATION_ALLOCATION_SIZING_OR_EXECUTION`;
- `NO_PRODUCTION_DEPLOYMENT_OR_V2_PROMOTION`;
- `NO_HISTORICAL_AS_OF_OR_PIT_AUTHORITY`;

## Validation and preserved authority

Focused adversarial tests cover public types, independent factory reconstruction,
replay mismatch, native unsupported/unavailable/conflict cases, exact period
context and adjacency, source semantics, common-filing metadata, competing
amounts, selected provenance, authentic recapture, equivalent decimals and
isolation. Adjacent Assets/Liabilities, PP&E and OCF foundation regressions,
compilation, Git integrity and canonical `./pam_preflight --base
33fa23affbe896bf0f204d7ead2c2346560b1b45` are required, at its actual selected tier.
Expected tier is `STANDARD`; no downgrade is permitted. Preflight validates the
committed candidate in its disposable detached worktree, so local staging and
commit precede the final canonical preflight. Push and PR creation follow only
successful validation.

V1 remains frozen; V2 remains a challenger. Protected PIT fingerprint
`f1e73b27b80e41d96ff5e0fe990b482bad71b7220db0b5bd6a2f470d72786166`, determinism
fingerprint `f8457910665391e39c234274cae4c029802c681211eebc7dba986a63000876f1`
and `MODEL_RULES_VERSION = 2026-08-23-allocation-room-integrity-v7` remain
unchanged. No promotion, merge or deployment is authorized. Independent
Architecture & Audit review and an owner merge decision remain required.
