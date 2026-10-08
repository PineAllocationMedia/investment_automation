# CURRENT annual operating income to positive revenue diagnostic

## Contract identity

- Contract version:
  `2026-10-08-current-annual-operating-income-to-positive-revenue-diagnostic-v1`
- Methodology version:
  `2026-10-08-exact-rational-operating-income-per-positive-revenue-v1`
- Analysis kind:
  `CURRENT_ANNUAL_OPERATING_INCOME_TO_POSITIVE_REVENUE`
- Result: `CurrentAnnualOperatingIncomeToPositiveRevenueResult`
- Public rational type: `OperatingIncomeToRevenueRatio`
- Authority:
  `QUALITY_CURRENT_ANNUAL_OPERATING_INCOME_TO_POSITIVE_REVENUE_DIAGNOSTIC_ONLY`

This is one bounded, threshold-free Stage-C Quality diagnostic. It is a
descriptive mathematical relationship, not a profitability judgment, Quality
score, investment rule or universally comparable operating margin.

## Purpose and exact concept meaning

The diagnostic reports exactly:

```text
reported us-gaap:OperatingIncomeLoss
--------------------------------------------------------------
reported us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax
```

for one already-qualified annual period when that exact revenue denominator is
strictly positive. Both facts are exact finite `Decimal` values in exact unit
`USD` from the same canonical paired annual filing/period selected upstream.

The reviewed revenue concept does not establish universal or comprehensive
company-revenue completeness. The output is therefore described as operating
income relative to the qualified positive reported Revenue concept, not simply
as a universally comparable operating margin.

No alternative revenue concept, `SalesRevenueNet`, issuer extension, adjusted
or non-GAAP revenue, EBIT, EBITDA, adjusted operating income, inferred value or
normalized value is accepted.

## Exact public input and trust boundary

The analyzer accepts exactly the runtime type:

`economic_facts.sec_current_annual_revenue_operating_income.CurrentAnnualRevenueOperatingIncomeQualification`

Subclasses, dictionaries, mappings, duck types, foreign reconstructed
dataclasses, raw Companyfacts, upstream profiles, detached facts,
caller-selected periods and caller assertions of qualification are rejected.
The diagnostic performs no acquisition, extraction, period selection,
requalification or source replay.

Exact dataclass type alone is not sufficient. The fail-closed trust boundary
validates the canonical public surfaces needed for consumption:

- exact upstream contract, qualifier, evidence kind, authority and limitations;
- exact native status/reason and upstream-profile status/reason types;
- exact namespace `us-gaap`, accounting basis `US_GAAP`, reviewed concepts and
  unit `USD`;
- coherent route-local identity, source CIK and annual period surfaces;
- established/non-established fact presence;
- finite exact `Decimal` facts for established evidence;
- canonical upstream semantic and evidence identities; and
- coherent nonempty receipt, source-object, observation, accession and filing
  evidence surfaces for established evidence.

Contradictory supposedly-canonical objects, impossible state/reason
combinations, malformed identity surfaces and unknown future upstream states
are programming-contract errors.

### Exact non-established upstream families

Non-established acceptance mirrors the upstream qualifier's sequential return
paths rather than accepting arbitrary reason subsets:

- mapped profile states carry exactly one matching reason:
  `UPSTREAM_PROFILE_UNAVAILABLE`, `UPSTREAM_PROFILE_UNSUPPORTED` or
  `UPSTREAM_SOURCE_CONFLICT`;
- preliminary `EVIDENCE_UNAVAILABLE` reasons contain at most one revenue-side
  reason and at most one operating-income-side reason, ordered and deduplicated;
- `NO_COMMON_ANNUAL_FILING_ACCESSION` is a separate singleton later return;
- local singleton conflicts are exactly
  `CANONICAL_ROUTE_IDENTITY_CONFLICT`, `CAPTURE_REPLAY_CONFLICT`,
  `SOURCE_CIK_CONFLICT` or `COMMON_FILING_METADATA_CONFLICT`; and
- competing-value conflict is revenue-only, operating-income-only or both.

Mapped upstream-profile states may occur before route or receipt context exists.
Local unavailable and post-route conflict states require the context necessarily
present at their upstream return point. Partial route or receipt surfaces are
rejected. CIKs, dates and UTC `Z` timestamps must use canonical lexical forms.

## State and reason model

The exact states are:

- `AVAILABLE`
- `NOT_APPLICABLE`
- `UNAVAILABLE`
- `UNSUPPORTED`
- `SOURCE_CONFLICT`

The exact analytical reasons are:

- `UPSTREAM_EVIDENCE_UNAVAILABLE`
- `UPSTREAM_EVIDENCE_UNSUPPORTED`
- `UPSTREAM_SOURCE_CONFLICT`
- `REVENUE_ZERO_DENOMINATOR`
- `REVENUE_NEGATIVE_NOT_POSITIVE_DENOMINATOR`

| Canonical upstream condition | Diagnostic result |
| --- | --- |
| Established and `revenue > 0` | `AVAILABLE`, no reasons, exact ratio present |
| Established and `revenue == 0` | `NOT_APPLICABLE / REVENUE_ZERO_DENOMINATOR` |
| Established and `revenue < 0` | `NOT_APPLICABLE / REVENUE_NEGATIVE_NOT_POSITIVE_DENOMINATOR` |
| `EVIDENCE_UNAVAILABLE` | `UNAVAILABLE / UPSTREAM_EVIDENCE_UNAVAILABLE` |
| `EVIDENCE_UNSUPPORTED` | `UNSUPPORTED / UPSTREAM_EVIDENCE_UNSUPPORTED` |
| `SOURCE_CONFLICT` | `SOURCE_CONFLICT / UPSTREAM_SOURCE_CONFLICT` |

Native upstream status and reasons are preserved separately. Every
non-`AVAILABLE` result has no ratio. Missing evidence never becomes zero, and a
non-established state cannot expose a partial calculation.

## Exact rational arithmetic

For exact values:

```text
O = operating_income
R = revenue
```

when `R > 0`, the only quantitative result is `O / R`. Using exact
`Decimal.as_integer_ratio()` forms:

```text
O = o_num / o_den
R = r_num / r_den

numerator   = o_num * r_den
denominator = o_den * r_num
```

The integers are reduced with GCD. `OperatingIncomeToRevenueRatio` is immutable;
its denominator is strictly positive, its numerator may be positive, zero or
negative, and canonical zero is `0/1`.

The calculation uses no binary float, Decimal division, rounding, percentage
conversion, epsilon, clipping, arbitrary denominator threshold or hostile
Decimal-context-dependent operation. A very small but strictly positive exact
revenue remains `AVAILABLE`.

Examples:

```text
Revenue 100, Operating Income 20   -> AVAILABLE, 1/5
Revenue 100, Operating Income -20  -> AVAILABLE, -1/5
Revenue 100, Operating Income 0    -> AVAILABLE, 0/1
Revenue 0                           -> NOT_APPLICABLE
Revenue -100                        -> NOT_APPLICABLE
```

## Immutable result surface

The result exposes only contract/methodology identity, analysis kind, analytical
state/reasons, native upstream state/reasons, route/source/period traceability,
actual upstream semantic/evidence IDs, the optional exact rational, authority,
closed limitations and derived deterministic identities.

It does not copy raw revenue, raw operating income, filing provenance or source
observations. It has no percentage, score, label, grade, threshold, Confidence,
recommendation, allocation or sizing field.

## Semantic identity

The diagnostic `semantic_id` binds:

- contract and methodology versions;
- analysis kind, state and diagnostic reasons;
- native upstream state and reasons;
- source CIK and exact annual period;
- canonical accounting namespace, basis, concepts and unit;
- exact revenue and operating-income values represented as reduced integer
  rationals when present;
- exact reduced diagnostic ratio when available;
- authority and closed limitations; and
- stable route-context presence/absence.

Consequently `Revenue=100, Operating Income=20` and `Revenue=200, Operating
Income=40` have different semantic IDs even though both ratios are `1/5`.
Equivalent exact Decimal representations have identical semantics.

Receipt identity, captured-at timestamp, source-object hash, selected
observation IDs, supporting filing identities, upstream evidence IDs and opaque
capture-bound route-key values are excluded from decisive analytical semantics.
Actual upstream identities and route-local IDs remain exposed for traceability.

## Evidence identity and recapture invariant

The diagnostic `evidence_id` binds exactly:

- the diagnostic `semantic_id`; and
- the actual upstream qualification `evidence_id`.

Therefore:

```text
same qualified economics + legitimate recapture
-> same diagnostic semantic_id
-> different diagnostic evidence_id
```

## Temporal authority

The input is a CURRENT qualification concerning one historical annual reporting
period. The diagnostic creates no `HISTORICAL_AS_OF`, PIT, filing-date knowledge,
historical margin trend, forward profitability or persistence authority. It does
not imply what PAM knew at fiscal-period end or filing date.

## Closed limitations and nonclaims

The result explicitly denies authority for:

- good/bad profitability;
- comprehensive-total-revenue completeness;
- a universally comparable operating margin;
- profitability Quality, pricing power, cost discipline or moat;
- historical margin expansion/contraction or profitability consistency;
- Durability or forward persistence;
- ROIC, ROE or ROA;
- free-cash-flow quality;
- cross-issuer or cross-sector comparability;
- aggregate Quality score, Quality grade, weighting or ranking;
- Expected Return or Confidence change;
- recommendation, allocation, sizing or execution;
- production, deployment or V2 promotion; and
- PIT or `HISTORICAL_AS_OF` authority.

The runtime pins the corresponding closed limitation enum. No limitation can be
removed by a caller.

## Deterministic and pure execution boundary

The module is pure and deterministic. It imports no acquisition, provider,
network, clock, filesystem, investment-engine, allocation or execution module.
It consumes only existing canonical evidence and adds no provider route or paid
data dependency.

The diagnostic is separate from all other Stage-C diagnostics and introduces no
Quality aggregation, threshold or investment-rule change. `MODEL_RULES_VERSION`
remains `2026-08-23-allocation-room-integrity-v7`; protected PIT and determinism
fingerprints remain unchanged.
