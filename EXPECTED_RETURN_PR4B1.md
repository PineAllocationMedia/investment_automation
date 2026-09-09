# PR4B1 — Qualified Expected Return assumption constructor

> PR4B1 defines how qualified facts would be transformed. It does not establish that current repository/provider snapshots satisfy that fact contract.

> No production mature-growth, payout or terminal-valuation defaults are established in PR4B1.

This is synthetic diagnostic infrastructure. It neither acquires real facts nor
makes investment decisions. All accepted adapter identities are explicitly
synthetic. Numerical economic policies live only in
`tests/expected_return_assumption_fixtures.py`. There are no tickers, market-cap
thresholds, analyst inputs, portfolio inputs or operational entry points.

## Starting state and scope

Authoritative V2 base: `e8f3c5bd5f274b4f514b723b8afd7a61196a4671` on
`model-v2/expected-return-challenger`. Preserved V1: `main` at
`c5fc27c82c29c2a6027eccee245098c4a072fdf1`. Both origin refs were verified after
fetch. The original clean local checkout was
`codex/v2-expected-return-foundation` at
`a0d1ff2df9ba67ddc359ea46f7dfe205dc27fbdc`. Implementation branch
`codex/v2-expected-return-assumptions` starts directly at the V2 base.

Only the two new pure source modules, two new test modules, this document and the
narrow PR4A import-isolation regression change. PR4A calculator source, production
paths, configuration, model identity and PIT code remain unchanged.

## Architecture and purity boundary

```text
Closed QualifiedFacts + optional explicit typed policies
  -> validate exact root classes, semantic adapters, identity, chronology, periods
  -> explicit ordinary-profile qualification and exclusions
  -> select latest five required consecutive positive annual diluted EPS facts
       last three -> MEDIAN_LATEST_THREE_DILUTED_EPS_V1 -> normalized starting EPS
       adjacent pairs -> ANNUAL_DILUTED_EPS_LOG_RATIO_V1
         -> HISTORICAL_LOG_{BEAR,BASE,BULL}_V1
         + mature policy + qualified profile -> LOG_GROWTH_FADE_7Y_V1:{scenario}
           -> LOG_TO_DECIMAL_GROWTH_V1:{scenario} -> seven decimal growth rates
  latest ordinary dividend + exactly matching reported EPS + payout policy
    -> CONSTANT_MATCHED_ORDINARY_PAYOUT_V1
    + normalized EPS + growth path + profile -> DIVIDEND_SCHEDULE_V1:{scenario}
  OR latest verified nonpayer + continued-nonpayer policy
    -> CONTINUED_VERIFIED_NONPAYER_V1 + profile -> seven zero distributions
  profile + explicit terminal policy -> INDEPENDENT_TERMINAL_PE_V1:{scenario}
  each component's derived nodes/roots -> CONFIDENCE_MIN_V1:{component}
  -> exact PR4A ExpectedReturnRequest
  -> PR4A calculate_expected_return -> ExpectedReturnDiagnostic
```

The only semantic module dependencies are
`expected_return_assumptions -> expected_return_policy` and
`expected_return_assumptions -> expected_return_engine`. The policy and calculator
modules depend on standard library code. No inverse dependency is added. Static
AST tests allowlist exact imports and prohibit runtime/I/O/dynamic execution
calls. Existing investment and PIT source cannot import the new modules. PR4A's
existing guard permits only the exact constructor source path as a new consumer.

The constructor does not read files, environment, clocks, Git, runtime context,
providers or network. Tests execute through the repository's disposable isolated
wrapper, never an application analysis. A fresh-process determinism test loads
these modules under a synthetic package without running the existing `src`
package initializer. The initializer itself is outside this PR's changes.

## Contracts and independent versions

| Identity | Value |
| --- | --- |
| Facts contract | `2026-09-09-synthetic-qualified-facts-v1` |
| Constructor | `2026-09-09-qualified-history-constructor-v1` |
| Assumption-policy schema | `2026-09-09-assumption-policy-v1` |
| Terminal-policy schema | `2026-09-09-terminal-policy-v1` |
| PR4A methodology, unchanged | `2026-09-08-normalized-eps-cashflow-irr-v1` |
| Investment rules, unchanged | `2026-08-23-allocation-room-integrity-v7` |

All operational inputs and returned records are frozen dataclasses, enums,
scalars and immutable tuples. Mappings, subclasses of admitted facts, arbitrary
PR4A `Evidence`, foreign objects and caller-generated derived nodes are rejected.
`QualifiedFacts` binds contract version, explicit offset `as_of`, security ID,
share class, currency/share basis, accounting basis, explicitly required latest
fiscal end, and root tuple. The latest fiscal end is a qualification supplied by
the caller, not guessed from the last available positive observation.

Every root contains an `Identity` with observation ID, security ID, share class
and typed `Provenance`. Provenance requires source kind, source reference,
source version, SHA-256 source-document hash, source locator, publication,
availability and capture timestamps, extractor identity and extractor version.
All text identities must be nonempty and trimmed. The extractor version must be
`1`; the typed adapter identity must match the exact economic root class.

| Closed root type | Required economic fields | Type-implied semantics / adapter |
| --- | --- | --- |
| `ObservedPrice` | Positive value, `ShareBasis`, observation date | Observed currency/share point price; `SYNTHETIC_OBSERVED_PRICE_V1` |
| `ReportedDilutedEPS` | Finite value, `ShareBasis`, `AnnualPeriod`, IFRS or US GAAP basis | Reported annual diluted currency/share EPS; `SYNTHETIC_REPORTED_DILUTED_EPS_V1` |
| `OrdinaryAnnualDividend` | Nonnegative ordinary amount, `ShareBasis`, `AnnualPeriod`, `special_dividends_excluded=True` | Verified annual ordinary currency/share distribution; `SYNTHETIC_ORDINARY_ANNUAL_DIVIDEND_V1` |
| `VerifiedNonpayer` | `AnnualPeriod` | Explicit verified nonpayer status over that annual period; `SYNTHETIC_VERIFIED_NONPAYER_V1` |
| `ProfileQualification` | Typed profile, explicit excluded structures, rationale | Company qualification; `SYNTHETIC_PROFILE_QUALIFICATION_V1` |

`ShareBasis` binds currency and explicit reconciled split/share-basis identity.
`AnnualPeriod` has exact start/end dates and represents a 365/366-day annual
period. The first contract does not support 52/53-week fiscal calendars or
partial-year accounting changes. Fact type, unit and period type are implied by
the exact class rather than caller-controlled strings. Nonmonetary qualification
facts have no meaningless currency, diluted denominator or accounting fields.
Their security/share class remains mandatory.

`SourceKind` is restricted to `SYNTHETIC_OFFICIAL` and `SYNTHETIC_MANUAL`.
Adapters here are semantic attestations in synthetic inputs, not implementations
of real acquisition. The contract does not cryptographically prove that a caller
truthfully attested a document's contents. Renaming a known foreign origin or
using a price adapter on an EPS fact fails; externally falsifying every
attestation is not an authenticity guarantee claimed by this PR.

## Profile gate

Only explicit `ORDINARY_COMPOUNDER` qualification with every unsupported
structure explicitly excluded is admitted. Missing, unknown or unsupported
profile yields `UNSUPPORTED_OR_MISSING_PROFILE`; incomplete exclusions yield
`AMBIGUOUS_PROFILE`. Contradictory or duplicate qualifications are contract errors.
No positive-EPS, ticker, market-cap, text-search or default-open inference occurs.

Unsupported structures: bank, insurer, REIT, asset manager, resources/mining,
energy cyclical, pipeline, materially different utility accounting, investment
holding company, mixed/conglomerate, turnaround and loss-making. The profile
must also be economically consistent with the required positive EPS route.
The existing business-profile classifier is not imported or called.

## EPS sequence and normalization

Sort qualified annual EPS by explicit fiscal end, then take the latest five.
The final observation must end on `latest_required_fiscal_end`. Every subsequent
start must be exactly the prior end plus one day. All required values must be
positive, with the same security, share class, currency, reconciled share basis
and accounting basis. All observations, including older unused observations,
remain in the result, root hash inventory and PR4A evidence.

The starting fundamental is:

```text
starting_normalized_eps = median(latest three of the five required annual EPS)
```

This is an explicit methodology assumption, not a new reported fact. The latest
three must remain consecutive and comparable. A bad required year is never
removed or replaced with an older positive year. Too few observations, missing
middle/latest period or a nonpositive required EPS yields unavailable.

Duplicate fiscal ends, including multiple source revisions, are contract
errors. PR4B1 defines no revision ordering or selection mechanism. A future
qualified acquisition contract must resolve revisions explicitly; this constructor
never selects by tuple order, capture time or an arbitrary source preference.
Currency/share/split/accounting conflicts and duplicate root IDs also fail as
contract errors. Duplicate economic roots under changed observation wrappers
are rejected using security, share class, document hash, source locator and
semantic adapter identity. An independent same-period EPS wrapper is still
rejected by the period uniqueness gate.

## Historical growth and seven-year fade

Five observations create four explicit intervals:

```text
x_i = ln(E_i / E_(i-1))
historical_bear = min(x_i)
historical_base = median(x_i)
historical_bull = max(x_i)
```

The implementation evaluates `log(E_i) - log(E_(i-1))` to avoid overflow of the
intermediate ratio. For four intervals the median averages the two middle log
values. Each interval retains both endpoint roots. Each order-statistic node
retains all four candidate intervals, including the candidates excluded by
min/max selection, so ties and contributing observations remain auditable.

For each scenario's historical anchor `h` and supplied mature log anchor `L`:

| Year | Log-growth value |
| --- | --- |
| 1–2 | `h` |
| 3 | `0.75*h + 0.25*L` |
| 4 | `0.50*h + 0.50*L` |
| 5 | `0.25*h + 0.75*L` |
| 6–7 | `L` |

The immutable methodology weights are exactly `(1, 1, .75, .50, .25, 0, 0)`.
They are not fitted or tuned. A separate lineage transformation converts each
log value using `expm1(log_growth)` (equivalently `exp(log_growth)-1`) for PR4A.
The anchors describe historical fundamental variability, not probabilities,
confidence intervals, price volatility or backtest-calibrated forecasts.
Temporary historical margin expansion/compression receives the same explicit
fade and is not independently perpetuated as a contextual growth premium.

## Policy contracts, identity and applicability

Each policy requires policy ID, supported schema version, typed applicability,
rationale and assumption ID. `Applicability` requires ordinary-compounder
profile, currency, accounting basis and inclusive valid-from/valid-through dates.
Qualification and supplied basis must match; validity is checked at the explicit
as-of date. Exactly one optional policy per role is supplied, so there is no
hidden selection precedence. Duplicate policy/assumption identities are errors.
A valid policy that does not apply has the same economic unavailability behavior
as a missing policy. Malformed or unsupported policies raise contract errors.

`MatureGrowthPolicy` adds finite bear/base/bull mature **log-growth** anchors.
`TerminalValuationPolicy` adds positive finite bear/base/bull terminal P/E values
and uses its own independently versioned schema. Both require
`bear <= base <= bull`; neither values nor scenario labels are sorted silently.
Missing applicable inputs produce `MISSING_MATURE_GROWTH_POLICY` or
`MISSING_TERMINAL_VALUATION_POLICY`.

`DistributionPolicy` adds a typed rule selecting either
`CONSTANT_MATCHED_ORDINARY_PAYOUT` or `CONTINUED_VERIFIED_NONPAYER`. There is no
implicit payout mode. Missing policy yields `MISSING_DISTRIBUTION_POLICY`; a
payer/nonpayer rule mismatch yields `INAPPLICABLE_DISTRIBUTION_POLICY`.

Policy hashes are computed properties, not trusted caller-supplied hashes.
SHA-256 covers canonical JSON of exact policy type, all identity/schema fields,
applicability, numerical assumptions and rationale. Mature policy hashes also
bind the fade transformation ID and exact weights. Map ordering and record
construction order do not matter; numeric integer/float equivalents normalize
together. Semantic changes alter hashes. Host time, randomness, memory address
and filesystem location are absent.

No production numerical mature-growth, payout, terminal-P/E, scenario-spread,
valuation-band or profile-premium defaults exist. No stock return, sector return,
market-cap formula, analyst growth, ROIC-retention formula, PEG, fair value,
current P/E, quality/durability/conviction score or calibration substitutes for
a missing policy. Current price is used only by the calculator; it does not
select growth, payout or terminal multiples.

## Dividends, buybacks and dilution

The payer route accepts one positive verified annual ordinary distribution for
the **latest required annual EPS period**. Dates must match exactly, as must
currency and reconciled share basis. An older convenient annual dividend,
misaligned year, snapshot yield or unknown zero is insufficient.

```text
payout_reference = latest ordinary annual dividend / matching reported annual EPS
D_(scenario,year) = payout_reference * projected EPS_(scenario,year)
```

The denominator is the matching reported EPS, never the arbitrary normalized
starting median. Projected EPS starts from that median and compounds the
constructed decimal growth rates. Projection here exists solely to produce the
explicit dividend schedule; terminal price and IRR remain PR4A calculations.
The explicit payout policy attests that continued constant normalized payout is
applicable. Special distributions must already be excluded; a root that includes
them is a contract error. No event aggregation or special-dividend extrapolation
is implemented.

Verified nonpayer status must also cover the latest annual period. It produces
seven zeros only under the explicit continued-nonpayer policy. Missing status or
a zero ordinary-dividend record without verified nonpayer status yields
`MISSING_DIVIDEND_STATUS`. Payer and nonpayer facts together are contradictory.
Mismatched status/dividend periods yield `DIVIDEND_EPS_PERIOD_MISMATCH`.

Per-share EPS already incorporates share-count effects. There is no buyback yield,
shareholder-yield addition, or second dilution subtraction. Two synthetic
identity tests prepare direct EPS histories using
`1 + g_EPS = (1 + g_earnings)/(1 + g_diluted_shares)` for moderate dilution and
strong share-count decline. These tests verify the calculator return as well as
the growth path, with no additional share-count return term. Share-count and
attributable-earnings input routes are deferred; direct diluted EPS needs neither.

## Confidence

Each component has a `ConfidenceAssessment` exposing roots and all five
categories. The result uses the categorical minimum, never averaging, a numeric
probability, a score or a return haircut:

```text
NONE < LOW < MEDIUM < HIGH
component = min(source_authority, freshness, completeness,
                consistency, assumption_dependence)
```

| Dimension | Explicit mapping |
| --- | --- |
| Source authority | Synthetic official attestation: HIGH; synthetic manual attestation: LOW. Minimum across unique component roots. Other source kinds are contract errors. |
| Price freshness | As-of UTC date minus observed date: HIGH through 7 days; MEDIUM through 30; otherwise LOW. |
| Profile freshness | Completed elapsed days since publication: HIGH through 365; MEDIUM through 730; otherwise LOW. |
| Annual-series freshness | As-of UTC date minus required latest fiscal end: HIGH through 550 days; MEDIUM through 730; otherwise LOW. Required historical observations use this endpoint rather than being penalized for their intentional age. |
| Completeness | HIGH after the mandatory route gates pass; missing requirements prevent a build. |
| Consistency | HIGH after identity, chronology, uniqueness, basis and period gates pass; contradictory inputs are errors. |
| Assumption dependence | Fundamental: HIGH ceiling for explicitly supported median normalization; growth, distributions and terminal valuation: LOW ceiling. |

Thus authoritative, fresh, complete, comparable EPS can support HIGH starting
fundamental confidence. Current-price evidence also constrains that component,
matching PR4A's treatment. Seven-year growth and independent terminal valuation
remain at most LOW regardless of historical source quality. Continued payout and
nonpayer assumptions are also capped LOW. Shared roots cannot increase any level.

Unavailable constructor results carry reasons and no request, diagnostic or
completed component assessments. NONE remains the PR4A categorical bottom for
unavailable/unusable components; PR4B1 does not manufacture a partially qualified
request. Known HIGH/MEDIUM freshness maps to PR4A `CURRENT` with the already
computed categorical ceiling. Known LOW maps to `STALE`; it never becomes
unknown freshness. PR4A retains its unchanged additional evidence checks.
Changing source authority or freshness changes confidence and lineage, not the
numerical growth, dividends, terminal multiples or returns.

## Lineage, chronology and determinism

`ConstructionResult` exposes immutable input roots, policy hashes, `LineageNode`
records, component root IDs, shared evidence roots, confidence assessments,
request and diagnostic. Each node has a stable transformation ID, content-derived
ID, sorted parent IDs, exact transitive root IDs, directly used policy hashes,
value and availability/capture timestamps. Policy ancestry is also reachable
through parent nodes. Confidence nodes depend on the actual component output
nodes. The result's lineage hash binds all root metadata (including source hash
and locator), constructor/facts identities, as-of, target basis and latest
required period, policies, nodes, confidence, components and status reasons.

The internally generated graph only references preexisting roots/nodes. Child
availability and capture equal the maximum respective parent times. No
caller-supplied transformation, lineage cycle, renamed prohibited root or
parent-after-child assertion can enter the operational graph: foreign derived
records are rejected at the closed input boundary. Tests separately verify
transitive root closure, acyclicity and chronological ordering of generated nodes.

Every root must obey the unchanged stricter rule:

```text
published_at <= available_at <= captured_at <= as_of
```

A reported annual period/observed price cannot postdate publication. Explicit
UTC offsets are required and normalized. There is no post-as-of archival-capture
exception. No `now()`/`today()` is called. Reordering root tuples, profile exclusion
sets, record constructor keywords, JSON dictionary keys, hash seeds, timezone or
locale does not change semantic output. Equivalent timestamp offsets normalize
together. Duplicate wrappers are rejected rather than being counted as separate
confirmations. Root metadata changes change the lineage digest even when the
numeric return is unchanged.

## Status and PR4A integration

`BUILT` means a valid, fully qualified PR4A request and diagnostic were generated.
The normal synthetic diagnostic is PR4A `DEGRADED` because assumption-heavy
components are deliberately LOW. The authority is `DIAGNOSTIC_ONLY`, with the
unchanged seven-year `NOMINAL_PRETAX_EQUITY_CASHFLOW_IRR` basis.

`UNAVAILABLE` means missing/inapplicable policy, unsupported/incomplete economic
facts, missing/nonpositive/gapped history, unsupported dividend alignment, or an
unrepresentable constructed growth/EPS/distribution/calculator path. It preserves
validated inputs, supplied policy hashes and any already-generated lineage;
request and diagnostic are absent. Extreme paths are never clipped or tuned.
Constructed scenario ordering is checked; crossed paths are unavailable.

`ConstructorContractError` is a `ValueError` for malformed/contradictory typed
inputs: unknown types or adapters, invalid schema/units/identity/chronology,
conflicting bases, duplicate roots or fiscal periods, impossible annual periods,
unsupported caller transformations and malformed policies. It is deliberately
raised rather than converted into economic unavailability. Unexpected bugs and
PR4A contract failures propagate. Only PR4A's specific numerical-domain error is
translated to `UNREPRESENTABLE_PR4A_CALCULATION`.

Each scenario uses PR4A's exact immutable `Scenario`, `References` and `Assumption`
records. Assumptions carry calculated values, supporting root IDs, policy version,
rationale and a stable transformation/lineage reference. Root evidence maps to
PR4A's exact `Evidence` records; richer document/adapter metadata remains in the
constructor envelope and bound lineage IDs. The constructor calls
`calculate_expected_return` exactly once on success. It contains no discounting,
IRR solver, terminal-price formula or return haircut.

## Synthetic coverage and validation

The test suite covers stable and high-growth/fading histories, temporary margin
expansion and compression, dilution and buyback identities, matched ordinary
payer, verified nonpayer, unknown dividend status, weak evidence, direct EPS
without share history, prohibited renamed ancestry, every unsupported profile,
terminal contraction/expansion, high current multiple with independent terminal
policy, excellent descriptive facts with poor mathematical return and the
reverse, unresolved revisions, and every missing policy.

Independent assertions cover normalization, four interval calculations, anchors,
exact log fade and decimal conversion, scenario ordering, payout arithmetic,
PR4A returns, schema/hash identity, malformed scalar/period/provenance contracts,
source/hash/locator mutation, confidence invariance, shared roots, immutable
outputs, and cross-process determinism. Formula expectations do not call the
same production helper twice. Isolation tests preserve the existing investment
and PIT boundaries.

Run using Python 3.12 with all packages matching `requirements.lock`:

```sh
.venv/bin/python -B scripts/run_isolated_tests.py --pattern 'test_expected_return_assumptions.py'
.venv/bin/python -B scripts/run_isolated_tests.py --pattern 'test_expected_return_engine.py'
.venv/bin/python -B scripts/run_isolated_tests.py --pattern 'test_runtime_isolation.py'
.venv/bin/python -B scripts/run_isolated_tests.py --pattern 'test_validation_identity_isolation.py'
.venv/bin/python -B scripts/run_isolated_tests.py --pattern 'test_pr2_investment_equivalence.py'
.venv/bin/python -B scripts/run_isolated_tests.py --pattern 'test_pit_bundle.py'
.venv/bin/python -B scripts/run_isolated_tests.py --pattern 'test_pit_comparison_boundary.py'
.venv/bin/python -B scripts/run_isolated_tests.py --pattern 'test_pit_comparison.py'
.venv/bin/python -B scripts/run_isolated_tests.py --pattern 'test_pit_adapter_equivalence.py'
.venv/bin/python -B scripts/run_isolated_tests.py --pattern 'test_pit_source_export.py'
.venv/bin/python -B scripts/run_isolated_tests.py
git diff --check
```

Required unchanged PR3 semantic fingerprints:

- 64-case aggregate: `f1e73b27b80e41d96ff5e0fe990b482bad71b7220db0b5bd6a2f470d72786166`.
- Determinism: `f8457910665391e39c234274cae4c029802c681211eebc7dba986a63000876f1`.

Local acceptance: Python **3.12.14**, all **33** installed locked packages verified
against `requirements.lock`, and **1,118 tests passed in 461.659 seconds** through
the complete isolated wrapper. Both fingerprints above matched in the targeted
runs and the complete suite. `git diff --check` and the staged whitespace check
passed. Remote CI is reported separately on the PR; no remote success is assumed.

| Targeted pattern | Tests | Result |
| --- | ---: | --- |
| `test_expected_return_assumptions.py` | 64 | PASS |
| `test_expected_return_engine.py` | 75 | PASS |
| `test_runtime_isolation.py` | 29 | PASS |
| `test_validation_identity_isolation.py` | 19 | PASS |
| `test_pr2_investment_equivalence.py` | 1 | PASS |
| `test_pit_bundle.py` | 6 | PASS |
| `test_pit_comparison_boundary.py` | 3 | PASS |
| `test_pit_comparison.py` | 4 | PASS |
| `test_pit_adapter_equivalence.py` | 2 (64-case matrix) | PASS |
| `test_pit_source_export.py` | 6 | PASS |

These tests use disposable synthetic comparison fixtures;
no positive-capital or zero-capital application run, real PIT comparison,
backtest or walk-forward is performed.

## Real-data limitations and deferred PR4B2

Current upstream snapshots have not been demonstrated to supply this qualified
contract: explicit ordinary-profile qualification/exclusions; five consecutive
comparable annual diluted EPS with reconciled security/currency/share/accounting
basis; resolved revisions and conflicts; document-level source hash/locator and
extractor identity; admissible publication/availability/capture chronology;
matched ordinary annual dividend or verified nonpayer status; and applicable,
independently governed economic policies. Current `forward_eps` also lacks the
required target-period/vintage/basis contract and is not supported here.

No real adapter authenticates these facts yet. Current real-company qualified
Expected Return remains unavailable. This PR does not certify provider snapshots,
PIT completeness, analyst estimates or actual portfolio Expected Return.

PR4B2 will separately address frozen PIT transport and its acquisition-contract
requirements. This PR changes no PIT bundle, adapter, worker, runner, schema,
fixture pin or exporter. The archival post-T capture exception remains deferred.
There is no V1/production decision change, rules bump, merge, deployment, Drive,
Chromebook activity, real provider call, operational analysis, Baseline evidence
or tuning.
