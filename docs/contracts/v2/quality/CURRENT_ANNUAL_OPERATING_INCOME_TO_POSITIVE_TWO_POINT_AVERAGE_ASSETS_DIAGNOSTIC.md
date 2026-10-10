# CURRENT annual operating income to positive two-point average Assets

## Identity and bounded scope

Contract: `2026-10-10-current-annual-operating-income-to-positive-two-point-average-assets-diagnostic-v1`.
Methodology: `2026-10-10-exact-rational-operating-income-per-positive-two-point-average-assets-v1`.
Analysis kind: `CURRENT_ANNUAL_OPERATING_INCOME_TO_POSITIVE_TWO_POINT_AVERAGE_ASSETS`.
Result: `CurrentAnnualOperatingIncomeToPositiveTwoPointAverageAssetsResult`.
Rational type: `OperatingIncomeToTwoPointAverageAssetsRatio`.
Authority: `QUALITY_CURRENT_ANNUAL_OPERATING_INCOME_TO_POSITIVE_TWO_POINT_AVERAGE_ASSETS_DIAGNOSTIC_ONLY`.

Implementation base: integration branch `model-v2/expected-return-challenger`,
HEAD `d78cfcef4ed2a0b325882853534c8f3d0b5f7ccf`, tree
`d0daff7aa0811a96a6d3527cdfaeb61ecc937448` (PR #128 canonical).
Exactly three new files are authorized: this contract,
`src/current_annual_operating_income_to_positive_two_point_average_assets.py`, and
`tests/test_current_annual_operating_income_to_positive_two_point_average_assets.py`.
Every existing file, upstream factory, acquisition/extraction/replay path, provider,
dependency, governance document, V1/PIT component and model rule is out of scope.

This Stage-C diagnostic describes signed reported annual Operating Income per
unit of the arithmetic mean of two reported Assets endpoints. The mean is an
analytical approximation, not a sourced accounting fact or a daily/time-weighted
measure. The relationship is not ROA, ROE, ROIC or an investment conclusion.
CURRENT evidence never grants HISTORICAL_AS_OF or PIT authority.

## Input boundary and public-contract validation

`analyze_current_annual_operating_income_to_positive_two_point_average_assets(income, assets)`
accepts exactly two positional native immutable qualifications:

1. `CurrentAnnualRevenueOperatingIncomeQualification`, pinned to
   `2026-10-07-current-annual-revenue-operating-income-qualification-v1`,
   qualifier `2026-10-07-paired-common-filing-exact-decimal-usd-qualification-v1`,
   kind `CURRENT_ANNUAL_REVENUE_OPERATING_INCOME_QUALIFICATION`, authority
   `QUALITY_PROFITABILITY_EVIDENCE_ONLY`.
2. `CurrentAnnualOpeningClosingAssetsQualification`, pinned to
   `2026-10-10-current-annual-opening-closing-assets-qualification-v1`, qualifier
   `2026-10-10-adjacent-common-filing-exact-decimal-usd-assets-instants-qualification-v1`,
   kind `CURRENT_ANNUAL_OPENING_CLOSING_ASSETS_QUALIFICATION`, authority
   `QUALITY_OPENING_CLOSING_ASSETS_EVIDENCE_ONLY`.

Subclasses, mappings, duck types, detached facts, extra arguments, keyword inputs
and caller-selected dates, values, filing accessions or qualification states are
rejected. The dedicated
`CurrentAnnualOperatingIncomeToPositiveTwoPointAverageAssetsError` reports
invalid or contradictory supposedly canonical public objects.

Validation checks exact native result and enum types, pinned versions/kinds,
accounting concepts, unit, authorities, complete native limitation inventories,
closed status/reason/profile families, finite Decimal amounts, coherent presence
or absence of route/capture context, exact hash/date/timestamp shapes, selected
observation partitions and coherent annual supporting filings. The Assets
qualification also exposes lossless selected observations; their native types,
values, dates, accounting semantics, receipt/object/time, extraction version,
locators, row JSON projection, source semantics and filing metadata must agree
with its public result. A blocked qualification carries no partial amounts,
selected observations, observation IDs or supporting filings. Impossible status,
reason and profile combinations raise the contract error.

This is bounded validation of public results, not authentication by reconstruction
of the entire upstream factory. It does not receive an archive or profile,
acquire data, select raw source evidence, run extraction, read source objects,
replay SEC evidence or requalify either input. Hash-shaped public identifiers do
not independently prove source authenticity. Source authority remains upstream.

Revenue is validated as part of the paired qualification and bounds availability,
but is not an analytical operand. A genuine Revenue-only change therefore changes
evidence, not this diagnostic's economic meaning. Zero/negative finite Revenue
is allowed when the native paired foundation is established.

## Cross-foundation coherence and common annual filings

Two established inputs must have identical exact ten-digit CIK, annual start and
annual end; namespace `us-gaap`, basis `US_GAAP`, exact `USD`; reported
`OperatingIncomeLoss` and `Assets`. Opening Assets date must equal annual start
minus exactly one calendar day; closing Assets date must equal annual end. No
nearest date or 365/366-day offset is substituted. Contradictory issuer, period,
date, concept, unit or accounting semantics are contract errors. Present common
issuer/period context is also checked when a native upstream blocker is present.

Capture receipts, source hashes, capture times, opaque route keys, profile and
comparability identities, and qualification semantic/evidence IDs need not match.
Independent authentic captures are accepted when facts and filing evidence agree.

Intersect the two qualifications' selected `supporting_accessions`. Require at
least one common annual accession; otherwise return
`UNAVAILABLE / NO_COMMON_SUPPORTING_ANNUAL_FILING_ACCESSION`. For **every** shared
accession compare exact singleton form, filed date and integer fiscal-year tuples.
Any disagreement returns
`SOURCE_CONFLICT / COMMON_SUPPORTING_FILING_METADATA_CONFLICT`. Never choose a
convenient or latest shared accession. Valid nonshared filings remain provenance
and do not poison a coherent intersection. Each native qualification already
requires its own paired observations to share its supporting annual filings.

## Exact arithmetic and endpoint policy

Let `I` be Operating Income and `Ao`, `Ac` opening and closing Assets.
The analytical relationship is `I / ((Ao + Ac) / 2) = 2I / (Ao + Ac)`.
Require each Assets endpoint independently positive. Operating Income is signed.
After establishment, economic coherence and the common-filing join pass:

| Endpoint | Result / reason |
| --- | --- |
| `Ao == 0` | `NOT_APPLICABLE / OPENING_ASSETS_ZERO_ENDPOINT` |
| `Ao < 0` | `NOT_APPLICABLE / OPENING_ASSETS_NEGATIVE_NOT_POSITIVE_ENDPOINT` |
| `Ac == 0` | `NOT_APPLICABLE / CLOSING_ASSETS_ZERO_ENDPOINT` |
| `Ac < 0` | `NOT_APPLICABLE / CLOSING_ASSETS_NEGATIVE_NOT_POSITIVE_ENDPOINT` |

Retain both failed endpoint reasons, sorted uniquely. A positive sum does not
rescue a zero or negative endpoint. Never calculate a ratio for a non-AVAILABLE
result, normalize a negative value, or turn missing values into zero.

Use exact finite `Decimal.as_integer_ratio()` values:
`I = In/Id`, `Ao = On/Od`, `Ac = Cn/Cd`.
Compute solely with integers:

```text
S = On*Cd + Cn*Od
numerator = 2*In*Od*Cd
denominator = Id*S
```

`OperatingIncomeToTwoPointAverageAssetsRatio` is frozen and exposes only integer
`numerator` and `denominator`. Normalize a positive denominator, GCD-reduce, and
represent exact zero as `0/1`. No binary float, Decimal division, context-dependent
addition/multiplication, rounding, epsilon, clipping, percentages or thresholds.
Equivalent finite Decimal representations yield equal canonical results, even
under deliberately low ambient Decimal precision.

## Closed result states and precedence

Exactly five diagnostic statuses: `AVAILABLE`, `NOT_APPLICABLE`, `UNAVAILABLE`,
`UNSUPPORTED`, `SOURCE_CONFLICT`. Every non-AVAILABLE result has ratio `None`.
Reasons are unique and lexically sorted:

- `UPSTREAM_REVENUE_OPERATING_INCOME_EVIDENCE_UNAVAILABLE`;
- `UPSTREAM_OPENING_CLOSING_ASSETS_EVIDENCE_UNAVAILABLE`;
- `UPSTREAM_REVENUE_OPERATING_INCOME_EVIDENCE_UNSUPPORTED`;
- `UPSTREAM_OPENING_CLOSING_ASSETS_EVIDENCE_UNSUPPORTED`;
- `UPSTREAM_REVENUE_OPERATING_INCOME_SOURCE_CONFLICT`;
- `UPSTREAM_OPENING_CLOSING_ASSETS_SOURCE_CONFLICT`;
- `NO_COMMON_SUPPORTING_ANNUAL_FILING_ACCESSION`;
- `COMMON_SUPPORTING_FILING_METADATA_CONFLICT`;
- `OPENING_ASSETS_ZERO_ENDPOINT`;
- `OPENING_ASSETS_NEGATIVE_NOT_POSITIVE_ENDPOINT`;
- `CLOSING_ASSETS_ZERO_ENDPOINT`;
- `CLOSING_ASSETS_NEGATIVE_NOT_POSITIVE_ENDPOINT`;

If either native input is non-established, retain each source-specific blocker
and both native upstream statuses/reason tuples unchanged. Overall precedence:
`SOURCE_CONFLICT > UNSUPPORTED > UNAVAILABLE`. The filing join and endpoint policy
are evaluated only for two established inputs. Unknown/factory-impossible public
projections raise the diagnostic error instead of acquiring ordinary status.

## Public result and stable identities

The frozen result exposes exactly the following dataclass fields, plus computed
`semantic_id`, `evidence_id` and deterministic `to_dict()`:

- `contract_version`;
- `methodology_version`;
- `analysis_kind`;
- `status`;
- `reasons`;
- `upstream_revenue_operating_income_status`;
- `upstream_revenue_operating_income_reasons`;
- `upstream_opening_closing_assets_status`;
- `upstream_opening_closing_assets_reasons`;
- `source_cik`;
- `period_start`;
- `period_end`;
- `opening_balance_date`;
- `closing_balance_date`;
- `accounting_namespace`;
- `accounting_basis`;
- `unit`;
- `operating_income_concept`;
- `assets_concept`;
- `operating_income_to_two_point_average_assets_ratio`;
- `upstream_revenue_operating_income_qualification_semantic_id`;
- `upstream_revenue_operating_income_qualification_evidence_id`;
- `upstream_opening_closing_assets_qualification_semantic_id`;
- `upstream_opening_closing_assets_qualification_evidence_id`;
- `common_supporting_accessions`;
- `authority`;
- `limitations`;

Serialization is wrapped under
`current_annual_operating_income_to_positive_two_point_average_assets`.
It does not expose Revenue, Operating Income, either Assets operand, or a
calculated average-Assets financial fact. Private fingerprint slots are not
serialized dataclass fields. Reconstructing the public dataclass without the
private fingerprints does not manufacture a valid analyzer-produced identity.

Semantic identity binds versions, kind, status/reasons, both native upstream
states/reasons and native profile states/reasons, source CIK, annual/balance dates,
accounting/unit/concepts, authority, complete limitations, exact canonical operands
and reduced ratio. The private analytical fingerprint binds all three available
operands even on NOT_APPLICABLE or failed-join results. Scaling all three values
can preserve the reduced ratio but must change semantic identity. Each genuine
operand change changes semantic identity.

Revenue, all upstream identities, opaque keys, captures, accessions, filing
metadata and observation provenance are excluded from analytical semantics.
Evidence identity binds semantic identity, both actual qualification
semantic/evidence pairs, complete supplied native qualification/provenance
payloads and common selected accessions. Authentic recapture, Revenue-only
variation, filing variation or source-row reordering preserves economics and
changes evidence when provenance changes. These tests use native capture and
qualification factories, not substituted hash identifiers.

## Closed limitations

The exact limitation inventory is:

- `ONLY_QUALIFIED_REPORTED_OPERATING_INCOME_AND_ASSETS`;
- `ONLY_POSITIVE_OPENING_AND_CLOSING_ASSETS`;
- `TWO_POINT_MEAN_IS_ANALYTICAL_APPROXIMATION`;
- `REVENUE_FOUNDATION_AVAILABILITY_BOUNDS_DIAGNOSTIC`;
- `NO_ROA`;
- `NO_ROE`;
- `NO_ROIC`;
- `NO_INVESTED_CAPITAL_INTERPRETATION`;
- `NO_NOPAT_OR_TAX_ADJUSTMENT`;
- `NO_DAILY_OR_TIME_WEIGHTED_AVERAGE_ASSETS`;
- `NO_NORMALIZED_OR_ADJUSTED_OPERATING_INCOME`;
- `NO_ASSET_QUALITY_JUDGMENT`;
- `NO_CAPITAL_ALLOCATION_EFFECTIVENESS`;
- `NO_LEVERAGE_LIQUIDITY_OR_SOLVENCY_CONCLUSION`;
- `NO_HISTORICAL_CAPITAL_EFFICIENCY_TREND`;
- `NO_FORWARD_PERSISTENCE`;
- `NO_CROSS_COMPANY_OR_CROSS_SECTOR_COMPARABILITY`;
- `NO_QUALITY_SCORE_GRADE_AGGREGATION_THRESHOLD_RANKING_OR_WEIGHT`;
- `NO_DURABILITY_CONCLUSION`;
- `NO_EXPECTED_RETURN_OR_CONFIDENCE_EFFECT`;
- `NO_RECOMMENDATION_ALLOCATION_SIZING_OR_EXECUTION`;
- `NO_PRODUCTION_DEPLOYMENT_OR_V2_PROMOTION`;
- `NO_HISTORICAL_AS_OF_OR_PIT_AUTHORITY`;

No investment/model rule changes, aggregate Quality, scoring/grades/thresholds,
Durability, Expected Return, Confidence, recommendation, allocation, execution,
production, deployment or V2 promotion is implemented.

## Validation and handoff requirements

Fictional fixtures prove mechanics only, not real-issuer availability, licensing,
coverage or admission. Tests cover native inputs, malformed public contracts and
provenance, all sixteen upstream status pairings, blocker precedence, issuer/period/
balance-date coherence, authentic independent capture identities, one/multiple/no
common filings, every common metadata field, nonshared extras, signed/zero income,
all endpoint failures, exact high precision at low ambient precision, reduction,
equivalent Decimal forms, scaled/changed operands, genuine recapture and Revenue-only
variation, source-row ordering and absence of acquisition/replay/investment behavior.

Run focused and adjacent foundation/diagnostic isolated tests, Python compilation,
exact three-file and whitespace checks, then canonical
`./pam_preflight --base d78cfcef4ed2a0b325882853534c8f3d0b5f7ccf` at its actual
planner-selected `FULL_PIT` tier, including the complete heavyweight PIT module.
The canonical preflight requires a clean committed candidate, so the local commit
is created after focused/adjacent validation and before preflight. Push and PR
creation follow only after the full required gate passes.

Protected PIT identity remains
`f1e73b27b80e41d96ff5e0fe990b482bad71b7220db0b5bd6a2f470d72786166`;
determinism remains
`f8457910665391e39c234274cae4c029802c681211eebc7dba986a63000876f1`;
`MODEL_RULES_VERSION` remains `2026-08-23-allocation-room-integrity-v7`.
Independent Architecture & Audit clearance and CEO merge decision remain required.
Stop after push/PR/handoff; no merge, deployment, CI or mergeability polling.
