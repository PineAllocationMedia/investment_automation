# CURRENT annual liabilities to positive assets diagnostic

## Contract identity

- Contract version:
  `2026-10-09-current-annual-liabilities-to-positive-assets-diagnostic-v1`
- Methodology version:
  `2026-10-09-exact-rational-liabilities-per-positive-assets-v1`
- Analysis kind: `CURRENT_ANNUAL_LIABILITIES_TO_POSITIVE_ASSETS`
- Result: `CurrentAnnualLiabilitiesToPositiveAssetsResult`
- Public rational type: `LiabilitiesToAssetsRatio`
- Authority:
  `QUALITY_CURRENT_ANNUAL_LIABILITIES_TO_POSITIVE_ASSETS_DIAGNOSTIC_ONLY`

This is one bounded, threshold-free Stage-C Quality diagnostic. It is a
descriptive accounting relationship, not a balance-sheet-quality, leverage,
liquidity or solvency assessment.

## Exact analytical question

For one already-qualified annual reporting date, the diagnostic reports:

```text
reported us-gaap:Liabilities
--------------------------------
reported us-gaap:Assets
```

only when the exact qualified Assets denominator is strictly positive. The
numerator is the exact qualified signed Liabilities value. Zero and negative
Liabilities remain valid reported values and receive no financial judgment.

`Liabilities` is not reinterpreted as interest-bearing debt, and `Assets` is
not reinterpreted as invested capital. The output must not be labeled as
debt/assets, debt/equity, net debt, leverage, liquidity, solvency or
balance-sheet strength.

## Exact public input

The public function accepts exactly one canonical
`economic_facts.sec_current_annual_assets_liabilities.CurrentAnnualAssetsLiabilitiesQualification`.
Subclasses, mappings, dictionaries and duck-typed values are rejected.
Contradictory reconstructions of the exact public type fail closed.

The analyzer performs no source acquisition and does not accept a CIK, date,
raw value, filing, receipt, archive or caller-provided qualification flag. It
does not rerun the upstream qualifier.

The input must preserve the exact upstream contract:

- contract version
  `2026-10-08-current-annual-assets-liabilities-qualification-v1`;
- qualifier version
  `2026-10-08-paired-common-filing-exact-decimal-usd-instant-fact-qualification-v1`;
- evidence kind `CURRENT_ANNUAL_ASSETS_LIABILITIES_QUALIFICATION`;
- accounting namespace `us-gaap` and basis `US_GAAP`;
- concepts `Assets` and `Liabilities`;
- exact unit `USD`;
- authority `QUALITY_BALANCE_SHEET_EVIDENCE_ONLY`; and
- the complete canonical upstream limitation tuple.

The upstream foundation's `NO_LIABILITIES_ASSETS_RATIO` limitation remains
unchanged. That evidence-only authority does not perform arithmetic. This
separate diagnostic contract alone authorizes the bounded analytical ratio.

## Upstream trust-boundary validation

The analyzer validates the canonical native upstream status and ordered reason
types, ordinary-compounder profile state and reasons, paired route-context
presence, source CIK, `period_end`, capture receipt/object provenance,
upstream profile/comparability semantic and evidence identities, selected
observation partitions, supporting accessions and supporting-filing metadata.

The upstream object must be factory-reachable:

- established evidence has empty reasons, exact finite `Decimal` values, full
  route and receipt context, nonempty selected Assets and Liabilities
  observation IDs, and an exact supporting-filing partition;
- non-established evidence has no numeric values and no selected/supporting
  evidence surfaces;
- preliminary unavailable reason families, no-common-accession cases, local
  source conflicts and upstream profile projections must match their native
  states; and
- impossible state/reason/profile combinations fail closed.

The annual balance-sheet facts are instant facts. The diagnostic preserves
`period_end` only and never invents or exposes `period_start`.

## Diagnostic statuses and reasons

Statuses are exactly:

- `AVAILABLE`;
- `NOT_APPLICABLE`;
- `UNAVAILABLE`;
- `UNSUPPORTED`; and
- `SOURCE_CONFLICT`.

Reasons are closed and exactly:

- `UPSTREAM_EVIDENCE_UNAVAILABLE`;
- `UPSTREAM_EVIDENCE_UNSUPPORTED`;
- `UPSTREAM_SOURCE_CONFLICT`;
- `ASSETS_ZERO_DENOMINATOR`; and
- `ASSETS_NEGATIVE_NOT_POSITIVE_DENOMINATOR`.

Projection is exact:

| Upstream qualification state | Diagnostic status / reason |
| --- | --- |
| `PAIRED_ASSETS_LIABILITIES_ESTABLISHED`, Assets > 0 | `AVAILABLE` / no reason |
| `PAIRED_ASSETS_LIABILITIES_ESTABLISHED`, Assets = 0 | `NOT_APPLICABLE` / `ASSETS_ZERO_DENOMINATOR` |
| `PAIRED_ASSETS_LIABILITIES_ESTABLISHED`, Assets < 0 | `NOT_APPLICABLE` / `ASSETS_NEGATIVE_NOT_POSITIVE_DENOMINATOR` |
| `EVIDENCE_UNAVAILABLE` | `UNAVAILABLE` / `UPSTREAM_EVIDENCE_UNAVAILABLE` |
| `EVIDENCE_UNSUPPORTED` | `UNSUPPORTED` / `UPSTREAM_EVIDENCE_UNSUPPORTED` |
| `SOURCE_CONFLICT` | `SOURCE_CONFLICT` / `UPSTREAM_SOURCE_CONFLICT` |

Every non-`AVAILABLE` result has `liabilities_to_assets_ratio=None`.
Missing evidence never becomes zero.

## Exact rational mathematics

For qualified values `L` and strictly positive `A`, the diagnostic uses
`Decimal.as_integer_ratio()` for each input and integer arithmetic only:

```text
L = Ln / Ld
A = An / Ad

L / A = (Ln * Ad) / (Ld * An)
```

The public ratio has:

- an integer numerator;
- a strictly positive integer denominator;
- lowest-term reduction; and
- canonical zero `0/1`.

There is no binary float, Decimal division, rounding, clipping, percentage
conversion, epsilon, threshold or materiality heuristic. A tiny strictly
positive Assets value remains mathematically available.

Examples:

```text
Assets 100, Liabilities 20   -> AVAILABLE, 1/5
Assets 100, Liabilities -20  -> AVAILABLE, -1/5
Assets 100, Liabilities 0    -> AVAILABLE, 0/1
Assets 0,   Liabilities 20   -> NOT_APPLICABLE
Assets -10, Liabilities 20   -> NOT_APPLICABLE
```

## Immutable public result

The result exposes only:

- contract and methodology versions;
- analysis kind, status and closed reasons;
- native upstream status and reasons;
- route-local issuer/security keys and source CIK;
- `period_end`;
- upstream qualification semantic and evidence IDs;
- the exact rational when available;
- diagnostic authority and closed limitations; and
- deterministic `semantic_id`, `evidence_id` and serialization.

It does not duplicate the absolute Assets or Liabilities values, full
observations, supporting filings, capture receipts or raw SEC payloads.

## Semantic and evidence identity

The analytical semantic identity binds the complete stable analytical input
semantics, including:

- this contract/methodology, result status and reasons;
- upstream contract, qualifier, evidence kind, state and reasons;
- upstream native profile state and reasons;
- route-context presence or absence, source CIK and `period_end`;
- accounting namespace, basis, concepts and unit;
- the exact canonical rational representations of both absolute qualified
  Assets and Liabilities values;
- upstream authority and limitations; and
- the diagnostic ratio, authority and limitations.

Therefore `Assets=100, Liabilities=20` and
`Assets=200, Liabilities=40` have different analytical semantic identities even
though both reduce to `1/5`. Equivalent finite Decimal lexical forms have the
same identity without ambient Decimal-context dependence.

Opaque route-key values and capture metadata do not contaminate analytical
semantics. The evidence identity binds the analytical semantic identity plus
the upstream qualification evidence identity. Consequently:

```text
same economics + legitimate recapture
-> same diagnostic semantic_id
-> different diagnostic evidence_id
```

## Authority and prohibited interpretations

Authority is exactly
`QUALITY_CURRENT_ANNUAL_LIABILITIES_TO_POSITIVE_ASSETS_DIAGNOSTIC_ONLY`.
It grants no authority for:

- debt/assets, debt/equity or net-debt claims;
- leverage, liquidity, solvency or balance-sheet-strength conclusions;
- capital-allocation, ROIC, ROA or ROE conclusions;
- historical trends or forward persistence;
- cross-issuer or cross-sector comparability;
- Quality score, grade, weight, aggregate or ranking;
- Durability, Expected Return or Confidence changes;
- recommendation, allocation, sizing or execution;
- production, deployment or V2 promotion; or
- `HISTORICAL_AS_OF` or PIT claims.

V1 remains frozen operational authority and V2 remains a challenger. The
diagnostic imports no investment, scoring, recommendation, allocation,
portfolio or execution engine. `MODEL_RULES_VERSION`, the protected PIT
fingerprint and the protected determinism fingerprint remain unchanged.
