# CURRENT annual OCF to positive net income diagnostic

## Contract identity

- Contract version:
  `2026-10-05-current-annual-ocf-to-positive-net-income-diagnostic-v1`
- Methodology version:
  `2026-10-05-exact-rational-ocf-per-positive-net-income-v1`
- Analysis kind: `CURRENT_ANNUAL_OCF_TO_POSITIVE_NET_INCOME`
- Result: `CurrentAnnualOCFToPositiveNetIncomeResult`
- Public rational type: `OperatingCashFlowToNetIncomeRatio`
- Authority:
  `QUALITY_CURRENT_ANNUAL_OCF_NET_INCOME_RELATIONSHIP_DIAGNOSTIC_ONLY`

This is one bounded, threshold-free Stage-C Quality diagnostic. It is a
descriptive current-period accounting relationship, not a Quality score or an
investment rule.

## Economic question and meaning

The diagnostic answers exactly:

> For the latest qualified annual period, when reported net income is strictly
> positive, how many dollars of reported operating cash flow were reported per
> dollar of reported net income?

It makes no claim that the relationship is good, bad, superior, sustainable or
predictive. It is not general cash-flow quality, accrual quality, earnings
quality, free-cash-flow quality, profitability quality or aggregate Quality.

## Exact public input and trust boundary

The analyzer accepts exactly the runtime type:

`economic_facts.sec_current_annual_operating_cash_flow_net_income.CurrentAnnualOperatingCashFlowNetIncomeQualification`

Subclasses, dictionaries, mappings, duck types, foreign reconstructed
dataclasses, raw source objects, upstream profiles, detached OCF/net-income
values, caller-selected periods and caller-supplied identities are rejected.

The analyzer performs no acquisition, extraction, requalification, network
access, clock read or historical reconstruction. Exact dataclass type alone is
not sufficient. The trust boundary validates the canonical upstream contract,
state/reason surface, profile projection, route context, accounting semantics,
numeric facts, identities and established-only provenance required by this
analysis. Factory-reachable non-established upstream states remain admissible;
they are not subjected to established-only evidence requirements.

For established upstream evidence, the analyzer requires:

- exact upstream contract, qualifier and evidence kind;
- exact upstream authority and closed limitations;
- exact native status/reason and upstream-profile status/reason types;
- exact namespace `us-gaap`, accounting basis `US_GAAP`, reviewed OCF and net
  income concepts, and unit `USD`;
- coherent route-local identities, source CIK and annual period;
- finite exact `Decimal` OCF and net-income values;
- canonical upstream semantic/evidence identities; and
- coherent nonempty receipt, source object, observation, accession and filing
  evidence surfaces.

Contradictory supposedly-canonical objects and unknown future upstream states
are programming-contract errors.

### Exact non-established upstream families

Non-established acceptance mirrors the upstream qualifier's sequential returns;
it is not generic subset validation.

- A mapped upstream profile state has exactly one reason:
  `UPSTREAM_PROFILE_UNAVAILABLE`, `UPSTREAM_PROFILE_UNSUPPORTED` or
  `UPSTREAM_SOURCE_CONFLICT`, paired with the matching native profile state.
- Preliminary `EVIDENCE_UNAVAILABLE` reasons are exactly the ordered,
  deduplicated result of at most one OCF-side reason and at most one net-income-
  side reason. The OCF side can emit
  `OPERATING_CASH_FLOW_UNAVAILABLE`, `EXACT_USD_UNIT_UNAVAILABLE`,
  `FINITE_OPERATING_CASH_FLOW_VALUE_UNAVAILABLE` or
  `EXACT_ANNUAL_PERIOD_PRESENTATION_UNAVAILABLE`. The net-income side can emit
  `NET_INCOME_UNAVAILABLE`, `EXACT_USD_UNIT_UNAVAILABLE`,
  `FINITE_NET_INCOME_VALUE_UNAVAILABLE` or
  `EXACT_ANNUAL_PERIOD_PRESENTATION_UNAVAILABLE`.
- `NO_COMMON_ANNUAL_FILING_ACCESSION` is a separate singleton later return. It
  cannot coexist with a preliminary unavailable reason.
- Local singleton conflict returns are exactly
  `CANONICAL_ROUTE_IDENTITY_CONFLICT`, `CAPTURE_REPLAY_CONFLICT`,
  `SOURCE_CIK_CONFLICT` and `COMMON_FILING_METADATA_CONFLICT`.
- Competing-value conflict is exactly OCF-only, net-income-only or both
  competing-value reasons together. It cannot coexist with an earlier conflict.

This rejects reconstructed combinations that sequential control flow cannot
emit, including preliminary unavailability plus no-common-accession and replay
conflict plus source-CIK conflict.

### State-specific context and lexical form

Route-local issuer/security keys are either both canonical hashes or both
absent. Receipt-derived fields—receipt ID, object hash, captured-at and source
locator—are either all canonical and present or all absent. Partial receipt
surfaces are impossible.

Mapped profile states may legitimately originate before route or period
establishment and therefore are not forced to carry later context. Local
unavailable and post-route conflict returns require the exact route, period,
source and receipt context necessarily present at those return points. The
route-identity-conflict return requires route, period and source context and may
be the point at which receipt context is absent.

All source CIKs are exact ten-digit strings. Period and filing dates must equal
their `date.isoformat()` representation. Capture timestamps must equal the UTC
`Z` form emitted by `CaptureReceipt` canonicalization, including canonical
fractional-second representation. Merely parseable offsets, basic-format dates
or noncanonical fractional forms are rejected.

## Capability states and reasons

The diagnostic defines exactly:

- `AVAILABLE`
- `NOT_APPLICABLE`
- `UNAVAILABLE`
- `UNSUPPORTED`
- `SOURCE_CONFLICT`

The closed analytical reasons are exactly:

- `UPSTREAM_EVIDENCE_UNAVAILABLE`
- `UPSTREAM_EVIDENCE_UNSUPPORTED`
- `UPSTREAM_SOURCE_CONFLICT`
- `NET_INCOME_ZERO_DENOMINATOR`
- `NET_INCOME_NEGATIVE_NOT_POSITIVE_EARNINGS`

Mapping is exact:

| Canonical upstream condition | Diagnostic state and reason |
| --- | --- |
| Established and `net_income > 0` | `AVAILABLE`, no reasons |
| Established and `net_income == 0` | `NOT_APPLICABLE / NET_INCOME_ZERO_DENOMINATOR` |
| Established and `net_income < 0` | `NOT_APPLICABLE / NET_INCOME_NEGATIVE_NOT_POSITIVE_EARNINGS` |
| `EVIDENCE_UNAVAILABLE` | `UNAVAILABLE / UPSTREAM_EVIDENCE_UNAVAILABLE` |
| `EVIDENCE_UNSUPPORTED` | `UNSUPPORTED / UPSTREAM_EVIDENCE_UNSUPPORTED` |
| `SOURCE_CONFLICT` | `SOURCE_CONFLICT / UPSTREAM_SOURCE_CONFLICT` |

The native upstream status and reasons are preserved separately. Every
non-`AVAILABLE` result has a `None` ratio. `NOT_APPLICABLE` means the analytical
denominator condition is not met; it is not missing evidence, unsupported
evidence, source conflict, Confidence or low confidence.

## Exact calculation

For exact reported values:

```text
C = operating_cash_flow
N = net_income
```

when `N > 0`, the only analytical value is:

```text
C / N
```

If Decimal integer-ratio forms are:

```text
C = c_num / c_den
N = n_num / n_den
```

the analyzer derives:

```text
numerator   = c_num * n_den
denominator = c_den * n_num
```

and reduces the result with integer GCD. It does not use Decimal division,
binary float, rounding, percentage conversion, caps, clipping, epsilon or a
minimum-positive-net-income threshold. A very small positive net income remains
mathematically `AVAILABLE`; the limitation surface explicitly denies a
near-zero-denominator stability claim.

## Exact signed rational representation

`OperatingCashFlowToNetIncomeRatio` is immutable and exposes exactly:

- `numerator: int`
- `denominator: int`

The numerator may be negative, zero or positive. The denominator is strictly
positive, sign is normalized to the numerator, and the pair is in lowest terms.
Zero is exactly `0/1`. Equivalent finite Decimal forms such as `100`, `100.0`,
`100.00` and `1E+2` produce identical rational semantics.

Examples:

```text
OCF=100, NI=80     → AVAILABLE, 5/4
OCF=80,  NI=100    → AVAILABLE, 4/5
OCF=0,   NI=100    → AVAILABLE, 0/1
OCF=-20, NI=100    → AVAILABLE, -1/5
OCF=100, NI=0.0001 → AVAILABLE, 1000000/1
OCF=100, NI=0      → NOT_APPLICABLE
OCF=100, NI=-20    → NOT_APPLICABLE
```

Positive reported earnings can coexist with negative reported operating cash
flow. That signed relationship is preserved without a label or conclusion.

## Immutable result surface

`CurrentAnnualOCFToPositiveNetIncomeResult` exposes only:

- contract and methodology versions;
- analysis kind, analytical status and closed analytical reasons;
- native upstream status and reasons;
- route-local issuer/security keys and source CIK;
- period start/end;
- upstream qualification semantic/evidence IDs;
- exact rational ratio when `AVAILABLE`;
- authority and closed limitations; and
- derived deterministic `semantic_id` and `evidence_id` properties.

It does not copy upstream operating cash flow, net income, filing provenance or
source observations. It has no percentage, score, label, grade, threshold,
rank, Confidence, recommendation, allocation or sizing field.

## Identity

The result `semantic_id` binds:

- contract and methodology versions;
- analysis kind, analytical state and analytical reasons;
- native upstream state and reasons;
- route-local issuer/security keys and source CIK;
- annual period;
- upstream qualification `semantic_id`;
- the reduced signed rational pair when available;
- authority; and
- limitations.

Binding the upstream semantic identity distinguishes different exact OCF/net-
income fact pairs even if they reduce to the same ratio.

The result `evidence_id` binds exactly:

- result `semantic_id`; and
- upstream qualification `evidence_id`.

Therefore:

```text
same economics + legitimate recapture
→ same analytical semantic_id
→ different analytical evidence_id
```

## Closed limitations

The result pins exactly:

- `ONLY_POSITIVE_NET_INCOME_DENOMINATOR`
- `NO_GOOD_BAD_OR_MINIMUM_RATIO`
- `NO_RATIO_MAGNITUDE_QUALITY_ORDERING`
- `NO_NEAR_ZERO_DENOMINATOR_STABILITY_CLAIM`
- `NO_ACCRUALS_QUALITY_CONCLUSION`
- `NO_WORKING_CAPITAL_CAUSAL_ATTRIBUTION`
- `NO_EARNINGS_MANIPULATION_OR_FRAUD_CONCLUSION`
- `NO_FREE_CASH_FLOW_OR_CAPEX_CLAIM`
- `NO_OWNER_EARNINGS_CLAIM`
- `NO_PROFITABILITY_QUALITY_CONCLUSION`
- `NO_HISTORICAL_CASH_CONVERSION_TREND`
- `NO_CROSS_ISSUER_OR_CROSS_SECTOR_COMPARABILITY`
- `NO_DURABILITY_OR_FORWARD_PERSISTENCE_CLAIM`
- `NO_AGGREGATE_QUALITY_SCORE_GRADE_OR_WEIGHT`
- `NO_EXPECTED_RETURN_EFFECT`
- `NO_CONFIDENCE_SUBSTITUTION`
- `NO_RECOMMENDATION_RANKING_ALLOCATION_OR_SIZING`
- `NO_EXECUTION_PRODUCTION_OR_V2_PROMOTION_AUTHORITY`
- `NO_HISTORICAL_AS_OF_OR_PIT_AUTHORITY`

## CURRENT and PIT boundary

The upstream chain is CURRENT evidence about one historical annual reporting
period. This diagnostic creates no `HISTORICAL_AS_OF` or PIT authority and no
claim about what PAM knew at fiscal-period end, filing date or another
historical cutoff. It creates no trend, persistence or forward inference.

## Cross-pillar and policy boundaries

The diagnostic remains separate from
`FIVE_PERIOD_DILUTED_EPS_DIRECTIONAL_CONSISTENCY` and
`CURRENT_ANNUAL_EPS_DENOMINATOR_DILUTION`. It creates no aggregate Quality
score, weighting, ranking, composite result or threshold.

It has no dependency on or effect on Expected Return, Durability, Confidence,
Portfolio Room, recommendation, allocation, sizing, execution, production,
deployment or V2 promotion. V1 remains frozen and unimported.

`MODEL_RULES_VERSION` remains
`2026-08-23-allocation-room-integrity-v7`. The protected PIT and determinism
fingerprints remain unchanged.
