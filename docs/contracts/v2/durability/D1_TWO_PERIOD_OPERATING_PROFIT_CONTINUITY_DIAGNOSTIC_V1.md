# Contract B — Stage D D1 Two-Period Reported Operating-Profit Continuity Diagnostic v1

**Status:** PROPOSED / NOT IMPLEMENTED / NO RUNTIME AUTHORITY

### 1. Contract identity

| Field               | Proposed value                                                           |
| ------------------- | ------------------------------------------------------------------------ |
| Contract identity   | `STAGE_D_D1_TWO_PERIOD_OPERATING_PROFIT_CONTINUITY_DIAGNOSTIC_V1`        |
| Contract version    | `2026-10-12-d1-two-period-operating-profit-continuity-diagnostic-v1`     |
| Methodology version | `2026-10-12-d1-exact-two-period-reported-operating-profit-comparison-v1` |
| Identity version    | `2026-10-12-d1-analytical-identities-v1`                                 |
| Analysis kind       | `TWO_PERIOD_REPORTED_OPERATING_PROFIT_CONTINUITY`                        |
| Result type         | `D1TwoPeriodOperatingProfitContinuityResultV1`                           |
| Proposed module     | `src.d1_two_period_operating_profit_continuity`                          |
| Authority           | `DURABILITY_D1_REPORTED_OPERATING_PROFIT_COMPARISON_ONLY`                |
| Temporal mode       | `CURRENT_CAPTURE_BOUND_ONLY`                                             |

The diagnostic describes two source-reported annual operating-profit observations and their exact relationship. Its authority is descriptive research only.

### 2. Exact public input

Proposed entrypoint:

`analyze_d1_two_period_operating_profit_continuity_v1(qualification)`

The single public input SHALL be the exact native Contract-A qualification.

Reject:

- Legacy single-period issuer qualifications.
- Research candidates.
- Ordinary Compounder profiles.
- Caller financial dictionaries or detached facts.
- Subclasses, incompatible contract versions or fabricated result types.
- Caller-provided qualification booleans, archive selectors or overridden facts.

The consumer SHALL invoke Contract A's trusted private source-verification boundary before interpreting status or performing arithmetic.

It SHALL calculate exclusively from the independently recomputed source-derived snapshot.

No network access, new receipt choice, current clock, archive mutation or alternate financial source is permitted.

### 3. Closed analytical statuses

Proposed status enum:

- `AVAILABLE`
- `NOT_APPLICABLE`
- `UNAVAILABLE`
- `UNSUPPORTED`
- `SOURCE_CONFLICT`

Mandatory mapping:

| Verified Contract-A condition                                     | D1 state                 | Ratio output                          |
| ----------------------------------------------------------------- | ------------------------ | ------------------------------------- |
| Established; both reported Revenue denominators strictly positive | `AVAILABLE`              | Two exact ratios and exact difference |
| Established; either Revenue denominator zero or negative          | `NOT_APPLICABLE`         | No ratios or ratio difference         |
| `EVIDENCE_UNAVAILABLE`                                            | `UNAVAILABLE`            | None                                  |
| `EVIDENCE_UNSUPPORTED`                                            | `UNSUPPORTED`            | None                                  |
| `SOURCE_CONFLICT`                                                 | `SOURCE_CONFLICT`        | None                                  |
| Invalid/stale/forged replay                                       | Contract/integrity error | No ordinary result                    |

Stable analytical reasons:

- `UPSTREAM_EVIDENCE_UNAVAILABLE`
- `UPSTREAM_EVIDENCE_UNSUPPORTED`
- `UPSTREAM_SOURCE_CONFLICT`
- `PRIOR_REVENUE_ZERO_DENOMINATOR`
- `CURRENT_REVENUE_ZERO_DENOMINATOR`
- `PRIOR_REVENUE_NEGATIVE_NOT_POSITIVE_DENOMINATOR`
- `CURRENT_REVENUE_NEGATIVE_NOT_POSITIVE_DENOMINATOR`

`AVAILABLE` has no analytical reasons. Nonavailable states retain native upstream reasons in a separate field.

If both denominators are nonpositive, emit both applicable analytical reasons, sorted uniquely.

### 4. Exact-rational methodology

Let:

- `R0` = qualified PRIOR Revenue.
- `O0` = qualified PRIOR Operating Income.
- `R1` = qualified CURRENT Revenue.
- `O1` = qualified CURRENT Operating Income.

If `R0 > 0` and `R1 > 0`, define:

`P0 = O0 / R0`

`P1 = O1 / R1`

Both ratios SHALL be represented as reduced signed integer numerator/positive-denominator pairs using the exact native `Decimal.as_integer_ratio()` arithmetic convention.

There is no Decimal division, binary64 conversion, rounding, epsilon, clipping, threshold or normalization.

Define the exact relationship difference:

`DELTA = P1 - P0`

For canonical ratios `P0 = a/b`, `P1 = c/d`:

`DELTA = (c*b - a*d) / (b*d)`

Reduce by GCD, require a positive denominator and canonical zero `0/1`.

Direction:

- `INCREASED` if `DELTA > 0`.
- `UNCHANGED` if `DELTA == 0`.
- `DECREASED` if `DELTA < 0`.

These are observations about the ratio only. They do not imply that Durability improved, weakened or remained stable.

### 5. Operating Income sign continuity

Independently classify each qualified Operating Income amount:

- `POSITIVE` when O > 0.
- `ZERO` when O == 0.
- `NEGATIVE` when O < 0.

Define the factual continuity descriptor:

| PRIOR O          | CURRENT O        | Descriptor                        |
| ---------------- | ---------------- | --------------------------------- |
| Positive         | Positive         | `POSITIVE_IN_BOTH_PERIODS`        |
| Positive         | Zero or negative | `POSITIVE_ONLY_IN_PRIOR_PERIOD`   |
| Zero or negative | Positive         | `POSITIVE_ONLY_IN_CURRENT_PERIOD` |
| Zero or negative | Zero or negative | `POSITIVE_IN_NEITHER_PERIOD`      |

Retain both exact sign classifications, including the distinction between zero and negative.

The descriptor is not a probability, rating, growth estimate or structural thesis verdict.

When Contract A is established but Revenue prevents the full ratio comparison, factual Operating Income amounts and signs may still be preserved under `NOT_APPLICABLE`. The two-ratio relationship remains absent.

When Contract A is not established, no sign-continuity assertion is permitted.

### 6. Immutable analytical result

The proposed frozen result SHALL include:

- Contract, methodology, identity versions and analysis kind.
- Status and sorted analytical reasons.
- Upstream qualification status/reasons.
- Exact Contract-A semantic/evidence identities.
- Source CIK and accounting semantics.
- Exact PRIOR and CURRENT annual periods, when established.
- Four exact reported financial facts, when established.
- PRIOR and CURRENT Operating Income signs.
- Observed sign-continuity descriptor.
- Both reduced exact ratios when applicable.
- Reduced exact ratio difference and categorical direction when applicable.
- Authority and fixed limitations.
- Independent analytical `semantic_id` and `evidence_id`.

No partial ratio shall be emitted as if the full two-period comparison were available.

Non-established upstream evidence produces no four selected financial facts, sign descriptor, ratios, ratio difference or directional relationship.

Provenance remains bound through the upstream qualification; do not duplicate its complete extraction inventory inside the analytical result.

### 7. Identity separation

Analytical semantic identity SHALL bind:

- Analytical contract, methodology and identity versions.
- Analysis kind, status, reasons and upstream semantic identity.
- Issuer and both exact annual periods.
- Four exact reported values, where established.
- Both signs and continuity descriptor, where established.
- Both exact ratios, exact difference and relationship direction, where applicable.
- Accounting semantics, authority and fixed limitations.

It SHALL exclude incidental archive paths, receipt IDs, capture timestamps, row positions, accession identifiers and upstream evidence identity.

Analytical evidence identity SHALL bind the analytical semantic identity plus the verified upstream qualification evidence identity.

Consequently:

- Equal ratios derived from different source facts do not share economic semantic identity.
- An unchanged four-fact comparative result may retain semantic identity across legitimate recaptures.
- Source-object or support changes remain visible in evidence identity.
- Any change in period, facts, result status or material reasons changes semantic identity.
- Hostile ambient Decimal contexts and different equivalent Decimal encodings cannot alter economic identity.

### 8. Exact consumer verification

Before producing any result, the analyzer SHALL:

1. Check the exact upstream native type and version.
2. Validate the upstream closed contract surface.
3. Verify the bound receipt and complete immutable source bytes.
4. Independently reconstruct Contract A's qualification.
5. Compare all public fields and both upstream identities.
6. Use the reconstructed values for one deterministic analytical evaluation.

Matching identity strings, frozen dataclasses and self-consistent forged objects are insufficient without source replay.

The analyzer SHALL reject stale bindings, changed facts, missing source bytes and detached inputs with a typed integrity/contract exception.

No new independent data trust mechanism is required beyond the source-native replay boundary.

### 9. Explicit prohibited interpretations

D1 does not establish:

- An economic moat, switching cost, network effect or pricing power.
- Structural resilience, normalized profitability or business-model superiority.
- Future positive Operating Income or expected future margin.
- Cyclicality resistance, earnings durability across a full economic cycle or reinvestment runway.
- Overall Quality or an aggregate Durability score.
- Increased Confidence or altered Expected Return.
- PR5C comparability, Ordinary Compounder admission or security eligibility.
- Recommendation, ranking, position sizing, allocation, execution, production or deployment authority.
- PIT or `HISTORICAL_AS_OF` evidence.

The two-period diagnostic is independently descriptive and never alters model rules.

V1 remains frozen operational authority. V2 remains a challenger.

### Proposed authentic-positive analytical oracle

Using only the values supplied in the specialist handoff, the expected arithmetic under Contracts A and B would be:

| Expected field              | Value                                           |
| --------------------------- | ----------------------------------------------- |
| Contract A                  | `COMPARATIVE_ISSUER_REPORTED_FACTS_ESTABLISHED` |
| Contract B                  | `AVAILABLE`                                     |
| PRIOR ratio                 | `32132 / 70431`                                 |
| CURRENT ratio               | `155237 / 331839`                               |
| Exact difference            | `90282133 / 7790584203`                         |
| Ratio direction             | `INCREASED`                                     |
| Operating Income continuity | `POSITIVE_IN_BOTH_PERIODS`                      |

The fractional difference is approximately 0.0115886 as a unitless ratio difference, or about 1.159 percentage points when displayed as a margin difference. Neither approximate display is an identity input.

These are proposed expected test values, not an executed native D1 result. Full source inventory adjudication remains necessary before Contract A may emit its established state.
