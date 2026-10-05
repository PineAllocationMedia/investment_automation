# CURRENT annual EPS denominator dilution diagnostic

## Contract identity

- Contract version:
  `2026-10-04-current-annual-eps-denominator-dilution-diagnostic-v1`
- Methodology version:
  `2026-10-04-exact-rational-incremental-denominator-ratio-v1`
- Analysis kind: `CURRENT_ANNUAL_EPS_DENOMINATOR_DILUTION`
- Result: `CurrentAnnualEPSDenominatorDilutionResult`
- Authority: `QUALITY_DILUTION_EPS_DENOMINATOR_DIAGNOSTIC_ONLY`

This is one bounded, threshold-free Stage-C Quality diagnostic. It is not a
Quality score or an investment rule.

## Economic question and meaning

The diagnostic answers exactly:

> For the latest annual period already established by the canonical
> denominator-share qualification, how large was the incremental
> weighted-average share denominator recognized for diluted EPS, relative to
> that period's basic weighted-average share denominator?

The result means only the incremental diluted-EPS denominator effect relative
to the basic EPS denominator for one annual reporting period. It is descriptive
and does not say whether the effect is good or bad.

It is not historical realized shareholder dilution, a change in shares
outstanding, stock-based-compensation issuance, option/warrant issuance,
convertible issuance, repurchase effectiveness, capital-allocation quality,
total diluted-EPS impact or a historical dilution trend.

## Exact public input and trust boundary

The analyzer accepts exactly the runtime type:

`economic_facts.sec_current_annual_eps_denominator_shares.CurrentAnnualEPSDenominatorSharesQualification`

Subclasses, dictionaries, mappings, duck types, foreign reconstructed
dataclasses, raw SEC Companyfacts, `SecArchive`, detached basic/diluted values,
caller-selected periods and independently supplied semantic/evidence IDs are
rejected.

The analyzer performs no acquisition, evidence extraction or evidence
requalification. It does not trust a qualification merely because its status
says established. An `AVAILABLE` result requires a coherent closed upstream
object, including:

- exact upstream contract version, qualifier version and evidence kind;
- exact runtime status and reason enums;
- empty reasons for the established state;
- exact accounting namespace/basis, concepts and unit `shares`;
- exact finite, strictly positive `Decimal` basic and diluted denominators;
- diluted denominator greater than or equal to the basic denominator;
- valid period start/end, source CIK and route-local identity hashes;
- valid upstream semantic/evidence identities;
- exact upstream authority
  `QUALITY_DILUTION_EPS_DENOMINATOR_EVIDENCE_ONLY`;
- exact canonical upstream limitations; and
- coherent, nonempty receipt/object, observation, accession and supporting
  filing provenance required by the established upstream result.

A contradictory supposedly-established object is a programming-contract error,
not `UNAVAILABLE`. Non-established objects cannot carry denominator values or
partial selected-observation/supporting-filing output.

## Capability states

The diagnostic defines exactly:

- `AVAILABLE`
- `UNAVAILABLE`
- `UNSUPPORTED`
- `SOURCE_CONFLICT`

Upstream states map without reinterpretation:

| Upstream denominator qualification | Diagnostic state |
| --- | --- |
| `PAIRED_EPS_DENOMINATOR_SHARES_ESTABLISHED` | `AVAILABLE` |
| `EVIDENCE_UNAVAILABLE` | `UNAVAILABLE` |
| `EVIDENCE_UNSUPPORTED` | `UNSUPPORTED` |
| `SOURCE_CONFLICT` | `SOURCE_CONFLICT` |

The result preserves the native upstream status and reasons. An unknown future
upstream state fails as a programming-contract error. Every non-`AVAILABLE`
result has `incremental_denominator_ratio = None`; there is no partial ratio and
missing evidence never becomes zero.

## Calculation

For:

```text
B = basic_weighted_average_shares
D = diluted_weighted_average_shares
```

the only analytical value is:

```text
(D - B) / B
```

which is mathematically equivalent to `(D / B) - 1`.

The absolute difference `D - B` is not exposed as a public analytical field.
There is no percentage, basis-point value, label, threshold, score, grade,
rank, confidence, recommendation, allocation or sizing output.

## Exact rational representation

The public ratio is immutable `EPSDenominatorDilutionRatio` with exactly:

- `numerator: int`
- `denominator: int`

The denominator is strictly positive, the numerator is nonnegative, and the
pair is reduced to lowest terms. Zero is exactly `0/1`. The pair is derived
exactly from the input `Decimal` values through base-ten-to-integer rational
conversion and integer arithmetic. There is no binary float, rounding or
ambient `Decimal`-context dependency.

Examples:

```text
B=100, D=100 → 0/1
B=3, D=4     → 1/3
```

Mathematically equivalent Decimal representations produce the same reduced
ratio.

## Zero semantics

When `B == D`, the result remains `AVAILABLE` with
`EPSDenominatorDilutionRatio(0, 1)`. It means only that the qualified annual
presentation recognized zero incremental diluted-EPS denominator shares beyond
the basic denominator.

Zero does not prove no stock-based compensation, no options or warrants, no
convertibles, no issuance, no historical dilution or no repurchases.

## Immutable result surface

`CurrentAnnualEPSDenominatorDilutionResult` preserves only:

- contract and methodology versions;
- analysis kind and capability status;
- native upstream status and reasons;
- route-local issuer/security keys and source CIK;
- period start/end;
- upstream denominator-qualification semantic/evidence IDs;
- `incremental_denominator_ratio` when available;
- authority and closed limitations;
- derived deterministic `semantic_id` and `evidence_id` properties.

It does not copy the upstream basic or diluted denominator values into the
public result.

## Identity

The result `semantic_id` binds:

- contract and methodology versions;
- analysis kind and capability status;
- native upstream status and reasons;
- route-local issuer/security keys and source CIK;
- period start/end;
- upstream denominator-qualification `semantic_id`;
- the canonical reduced numerator/denominator pair when available;
- authority and limitations.

The reduced integer pair is the exact ratio semantic representation. Capture
timestamp, receipt, archive path, object hash and other evidence-only provenance
do not independently enter analytical semantic identity.

The result `evidence_id` binds exactly:

- result `semantic_id`; and
- upstream denominator-qualification `evidence_id`.

Therefore:

```text
same analytical economics + valid upstream evidence recapture
→ same result semantic_id
→ different result evidence_id
```

A changed denominator pair, ratio, period, status or route meaning changes
semantic identity through the bound upstream semantics and analytical fields.
Equivalent Decimal spellings do not change ratio or analytical semantic
identity.

## Closed limitations

The result pins exactly:

- `NO_ACTUAL_SHAREHOLDER_DILUTION_CLAIM`
- `NO_SHARES_OUTSTANDING_CHANGE_CLAIM`
- `NO_PERIOD_END_SHARES_OUTSTANDING_CLAIM`
- `NO_SBC_CAUSAL_ATTRIBUTION`
- `NO_OPTION_OR_CONVERTIBLE_CAUSAL_ATTRIBUTION`
- `NO_ISSUANCE_CAUSAL_ATTRIBUTION`
- `NO_REPURCHASE_EFFECTIVENESS_CONCLUSION`
- `NO_CAPITAL_ALLOCATION_QUALITY_CONCLUSION`
- `NO_TOTAL_DILUTED_EPS_IMPACT_CLAIM`
- `NO_HISTORICAL_DILUTION_TREND`
- `NO_CROSS_SECTOR_QUALITY_COMPARABILITY`
- `NO_DILUTION_THRESHOLD_GRADE_OR_SCORE`
- `NO_DURABILITY_OR_FORWARD_PERSISTENCE_CLAIM`
- `NO_EXPECTED_RETURN_ADJUSTMENT`
- `NO_CONFIDENCE_SUBSTITUTION`
- `NO_RECOMMENDATION_RANKING_ALLOCATION_OR_SIZING`
- `NO_EXECUTION_PRODUCTION_OR_V2_PROMOTION_AUTHORITY`
- `NO_HISTORICAL_AS_OF_OR_PIT_AUTHORITY`

## CURRENT and PIT boundary

The upstream chain is CURRENT evidence about one historical annual reporting
period. This diagnostic creates no `HISTORICAL_AS_OF` authority, PIT
reconstruction, historical dilution series, proof of knowledge at fiscal year
end or proof of knowledge at filing date.

## Cross-pillar and policy boundaries

The diagnostic has no dependency on or effect on company Expected Return, VFV
Expected Return, the comparator, hurdles, scenarios, valuation or B1/B2. It
makes no Durability or persistence conclusion and has no confidence field;
capability state is not Confidence.

It creates no recommendation, ranking, sizing, allocation, Opportunity Set
admission, Portfolio Room effect, execution, production, deployment or V2
promotion authority.

V1 remains frozen and unimported. No V1 dilution/shareholder-discipline
threshold, label, score, allocation adjustment or recommendation rule is used.
The diagnostic does not modify or aggregate with
`FivePeriodEPSConsistencyResult` and does not create `QualityScore`.

`MODEL_RULES_VERSION` remains
`2026-08-23-allocation-room-integrity-v7`. The protected PIT and determinism
fingerprints remain unchanged.
