# Five-period diluted-EPS directional consistency

## Contract identity

- Contract version: `2026-10-04-five-period-diluted-eps-consistency-v1`
- Methodology version: `2026-10-04-exact-decimal-directional-consistency-v1`
- Analysis kind: `FIVE_PERIOD_DILUTED_EPS_DIRECTIONAL_CONSISTENCY`

This is the first bounded Stage-C Quality slice. It is one transparent,
read-only diagnostic, not a composite Quality model.

## Economic meaning

The diagnostic answers exactly:

> Across the five comparable annual diluted-EPS periods already proven by PAM
> for this bounded ordinary-company route, how consistently did reported
> per-share earnings increase, remain unchanged, or decrease?

It describes four transitions between five already-qualified annual periods.
It does not infer overall corporate Quality, future growth, persistence, moat,
profit margins, ROIC/ROE, cash conversion, balance-sheet strength,
capital-allocation quality, dilution quality, valuation, Expected Return or
investment attractiveness.

## Exact input and supported scope

The only accepted runtime input is the exact type:

`economic_facts.sec_ordinary_compounder_profile.OrdinaryCompounderMethodProfileQualification`

Subclasses, mappings, dictionaries, duck types, detached comparability objects,
raw EPS series, Companyfacts, Expected Return outputs, V1 dictionaries,
convenience-provider values and caller-asserted facts are rejected.

The diagnostic consumes the profile's canonical embedded
`upstream_comparability`; callers cannot pair a profile with an unrelated
comparability object. `AVAILABLE` requires all of the following:

- profile status is exactly `ORDINARY_COMPOUNDER_PROFILE_ESTABLISHED`;
- embedded outcome is exactly `COMPARABLE_REAL_EPS_ESTABLISHED`;
- canonical profile, comparability and route-local linkages are coherent;
- exactly five period decisions exist;
- all five outcomes are exactly `EXACT_MATCH`;
- period endpoints are strictly ordered and distinct;
- each `c3_value` is an exact finite `Decimal`;
- the established ordinary-company profile remains internally coherent.

Contradictory supposedly-established objects are programming-contract errors,
not `UNAVAILABLE` analyses.

This slice inherits the existing ordinary-compounder profile boundary without
adding sector classification. Banks, insurers, REITs, asset managers,
resources/mining, energy cyclicals, pipelines, utility-accounting profiles,
investment holdings, unresolved mixed conglomerates, turnaround profiles and
loss-making profiles cannot silently receive an available trace.

## Capability states

The result defines exactly:

- `AVAILABLE`
- `UNAVAILABLE`
- `UNSUPPORTED`
- `SOURCE_CONFLICT`

The upstream profile state maps without reinterpretation:

| Upstream profile status | Result status |
| --- | --- |
| `ORDINARY_COMPOUNDER_PROFILE_ESTABLISHED` | `AVAILABLE` |
| `PROFILE_UNAVAILABLE` | `UNAVAILABLE` |
| `PROFILE_UNSUPPORTED` | `UNSUPPORTED` |
| `SOURCE_CONFLICT` | `SOURCE_CONFLICT` |

Unknown future states fail closed as programming-contract errors. Native
profile status and reasons are preserved. No Quality-specific reason taxonomy
is introduced.

`UNAVAILABLE` and `SOURCE_CONFLICT` are capability states; neither means
`LOW_CONFIDENCE`.

## Calculation and output

For adjacent periods, the only calculation is:

```text
delta_diluted_eps = current_diluted_eps - prior_diluted_eps
```

Exact `Decimal` sign determines direction:

- positive: `INCREASED`;
- zero: `UNCHANGED`;
- negative: `DECREASED`.

There is no float conversion, rounding, CAGR, percentage growth,
interpolation, annualization or substituted EPS.

An available result contains exactly four immutable
`FivePeriodEPSInterval` records and exact increase, unchanged and decrease
counts summing to four. A non-available result contains an empty interval tuple
and `None` for every count; zero is never substituted for absent analysis and
no partial Quality trace is constructed.

The immutable `FivePeriodEPSConsistencyResult` also preserves contract and
methodology versions, analysis kind, capability state, native upstream status
and reasons, route-local issuer/security keys, separate upstream profile and
comparability semantic/evidence identities, authority and limitations.

## Identity

The result `semantic_id` binds only:

- contract and methodology versions;
- analysis kind and capability status;
- exact upstream profile status and native reasons;
- route-local issuer/security keys when available;
- upstream profile and comparability semantic IDs;
- the exact four interval semantic records for available results, including
  endpoints, exact prior/current EPS, exact delta and direction;
- exact counts, authority and limitations.

It does not independently add timestamps, receipts, source bytes or
evidence-only provenance IDs to the semantic domain.

The result `evidence_id` binds exactly the result semantic ID plus upstream
profile and comparability evidence IDs. Consequently, evidence-only recapture
preserves result semantics while changing result evidence identity.

## Evidence and authority

The upstream chain is CURRENT evidence that establishes one qualified
five-period historical presentation. It is not five historical point-in-time
observations and grants no `HISTORICAL_AS_OF` authority.

Authority is exactly:

`QUALITY_EPS_CONSISTENCY_DIAGNOSTIC_ONLY`

Limitations are exactly:

- `NO_COMPOSITE_QUALITY_SCORE`
- `NO_CROSS_SECTOR_COMPARABILITY`
- `NO_PROFIT_MARGIN_OR_ROIC_CLAIM`
- `NO_CASH_CONVERSION_OR_BALANCE_SHEET_CLAIM`
- `NO_CAPITAL_ALLOCATION_DILUTION_OR_MOAT_CLAIM`
- `NO_DURABILITY_OR_FORWARD_PERSISTENCE_CLAIM`
- `NO_EXPECTED_RETURN_ADJUSTMENT`
- `NO_CONFIDENCE_SUBSTITUTION`
- `NO_RECOMMENDATION_RANKING_ALLOCATION_OR_SIZING`
- `NO_EXECUTION_PRODUCTION_OR_V2_PROMOTION_AUTHORITY`
- `NO_HISTORICAL_AS_OF_OR_PIT_AUTHORITY`

## Separation from other pillars and policy

Four increases do not establish a high-quality company. This result creates no
score, grade, Quality threshold, acceptable-decline count, growth hurdle,
weight or master Quality score.

It does not import, invoke, read or alter Expected Return. It adds no bonus,
haircut, multiplier or hurdle effect. It makes no Durability or forward
persistence conclusion. It has no confidence field and does not convert missing
or conflicting evidence into low confidence.

It creates no recommendation, ranking, allocation, sizing, add/hold/sell
state, Opportunity Set admission, portfolio-room effect, monitoring escalation
or execution instruction.

## V1 freeze and operational boundary

V1 Quality and policy engines remain untouched and unimported. This diagnostic
does not use V1 thresholds, scores, labels, allocation adjustments,
`safe_float` or `clamp`. `MODEL_RULES_VERSION` remains unchanged.

The runtime performs no network acquisition, provider fetch, filesystem access,
environment lookup or clock read. It grants no production, deployment,
execution, V2-promotion or historical-PIT authority.
