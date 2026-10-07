# CURRENT annual revenue and operating-income qualification

## Contract identity

- Contract version:
  `2026-10-07-current-annual-revenue-operating-income-qualification-v1`
- Qualifier version:
  `2026-10-07-paired-common-filing-exact-decimal-usd-qualification-v1`
- Evidence kind:
  `CURRENT_ANNUAL_REVENUE_OPERATING_INCOME_QUALIFICATION`
- Result type:
  `CurrentAnnualRevenueOperatingIncomeQualification`
- Authority:
  `QUALITY_PROFITABILITY_EVIDENCE_ONLY`

This is one bounded Stage-C evidence foundation. It establishes two paired
accounting facts only. It does not calculate or diagnose operating margin.

## Economic question

The qualifier answers exactly:

> For the latest annual fiscal period already established by PAM's supported
> ordinary-compounder route, can PAM establish one coherent CURRENT SEC
> Companyfacts presentation of revenue and operating income?

The exact reviewed concepts are:

- `us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax`; and
- `us-gaap:OperatingIncomeLoss`.

The reviewed unit is exactly `USD`. `SalesRevenueNet`, other revenue concepts,
issuer extensions, `ProfitLoss`, gross profit, EBIT/EBITDA proxies, adjusted
operating income, provider-derived values and all other supposed synonyms do
not substitute.

## Exact public input

The public function accepts exactly:

1. `economic_facts.sec_archive.SecArchive`; and
2. `economic_facts.sec_ordinary_compounder_profile.OrdinaryCompounderMethodProfileQualification`.

Subclasses, mappings, dictionaries and duck-typed substitutes are rejected.
The caller cannot provide a CIK, period, receipt, accession, raw value,
qualification state, route identity or detached comparability object.

Issuer and security context, source CIK, latest annual period and Companyfacts
receipt are derived from the profile's canonical embedded comparability and
security evidence graph. The qualifier rereads only the exact immutable object
selected by that embedded receipt. It performs no acquisition, network access,
clock read or historical reconstruction.

## Extraction boundary

`economic_facts/sec_revenue_operating_income.py` extracts only the two
reviewed concepts. Each immutable observation preserves:

- source CIK, namespace, concept and unit;
- exact base-ten `Decimal` value;
- start and end dates, FY, FP, form, filed date, accession and optional frame;
- source object hash, receipt identity and captured-at provenance;
- capture source locator, row source locator and semantic locator;
- canonical row JSON and source semantics; and
- separate source-observation semantic and evidence identities.

JSON numeric values are parsed directly as `Decimal`; binary float conversion
is forbidden. Malformed source structures fail closed rather than becoming
silent absence. Missing is not zero. Non-finite values cannot establish facts.

## Canonical period and establishment

The target is the latest exact annual period in the canonical five-period
comparability chain. The state
`PAIRED_REVENUE_OPERATING_INCOME_ESTABLISHED` requires all of the
following:

- the upstream profile is exactly established and its canonical state/reason
  surface is coherent;
- the embedded comparability is exactly established and coherent;
- the five canonical period decisions remain exact, positive diluted-EPS
  matches in strict chronological order;
- the latest period is derived from that chain, never selected by the caller;
- the embedded Companyfacts receipt/object replays from the supplied archive;
- source, receipt, request, series, CIK and route-local identities agree;
- both exact reviewed concepts exist under `us-gaap` in exact unit `USD`;
- both values are finite exact `Decimal` values, including zero or negative
  values when reported;
- observations match the exact canonical annual start/end dates;
- observations are annual `FY` presentations on form `10-K` or `10-K/A`;
- at least one accession contains admissible observations for both concepts;
- each common accession has one coherent intrinsic form, filed date and FY
  presentation across both concepts;
- all admissible common paired revenue presentations agree on one
  exact value; and
- all admissible common paired operating-income presentations agree on one exact
  value.

The qualifier never averages, rounds, interpolates, normalizes, converts
currency or arbitrarily chooses among competing values. Conflict analysis is
restricted to admissible common paired accessions. An orphan observation for
only one concept does not poison a coherent common pair and is excluded from
selected evidence. `frame` equality is not required.

## Capability states and reasons

The result uses exactly:

- `PAIRED_REVENUE_OPERATING_INCOME_ESTABLISHED`;
- `EVIDENCE_UNAVAILABLE`;
- `EVIDENCE_UNSUPPORTED`; and
- `SOURCE_CONFLICT`.

Upstream projection is exact:

| Upstream profile state | Result state and reason |
| --- | --- |
| `PROFILE_UNAVAILABLE` | `EVIDENCE_UNAVAILABLE` / `UPSTREAM_PROFILE_UNAVAILABLE` |
| `PROFILE_UNSUPPORTED` | `EVIDENCE_UNSUPPORTED` / `UPSTREAM_PROFILE_UNSUPPORTED` |
| `SOURCE_CONFLICT` | `SOURCE_CONFLICT` / `UPSTREAM_SOURCE_CONFLICT` |

For an established profile, missing concepts, exact unit, finite values, exact
annual presentations or a common pair produce `EVIDENCE_UNAVAILABLE` with the
corresponding closed reason. Competing paired values, contradictory common-
filing metadata, replay mismatch, CIK mismatch or route/source incoherence
produce `SOURCE_CONFLICT`.

Unknown future states and factory-impossible reconstructed supposedly-canonical
profile objects are programming-contract errors. Exact dataclass or enum
identity alone does not make an impossible reconstruction canonical. The
validation is deliberately bounded: it checks the canonical state/reason,
metadata, decision-inventory, identity and established-comparability surfaces
needed here without reimplementing the upstream factory.

Reasons are closed and deterministically ordered:

- `UPSTREAM_PROFILE_UNAVAILABLE`;
- `UPSTREAM_PROFILE_UNSUPPORTED`;
- `UPSTREAM_SOURCE_CONFLICT`;
- `CANONICAL_ROUTE_IDENTITY_CONFLICT`;
- `CAPTURE_REPLAY_CONFLICT`;
- `SOURCE_CIK_CONFLICT`;
- `REVENUE_UNAVAILABLE`;
- `OPERATING_INCOME_UNAVAILABLE`;
- `EXACT_USD_UNIT_UNAVAILABLE`;
- `FINITE_REVENUE_VALUE_UNAVAILABLE`;
- `FINITE_OPERATING_INCOME_VALUE_UNAVAILABLE`;
- `EXACT_ANNUAL_PERIOD_PRESENTATION_UNAVAILABLE`;
- `NO_COMMON_ANNUAL_FILING_ACCESSION`;
- `COMPETING_REVENUE_VALUES`;
- `COMPETING_OPERATING_INCOME_VALUES`; and
- `COMMON_FILING_METADATA_CONFLICT`.

Every non-established result has `None` for both numeric values and empty
selected-observation and supporting-filing surfaces. Partial numeric output is
forbidden.

## Immutable output and provenance

The result exposes:

- contract, qualifier and evidence identities;
- capability status and closed reasons;
- native upstream profile status and reasons;
- route-local issuer/security keys and source CIK;
- target period and accounting semantics;
- exact revenue and operating income when established;
- upstream profile/comparability semantic and evidence identities;
- receipt, object, captured-at and capture-source-locator provenance;
- selected observation IDs for each concept;
- supporting accessions and immutable filing metadata;
- authority and closed limitations; and
- deterministic `semantic_id` and `evidence_id`.

For established results, supporting accessions are sorted and unique. Each
supporting filing has exactly one coherent form, filed date and fiscal year,
and nonempty sorted unique observation IDs for both concepts. Selected IDs are
an exact partition of filing IDs. An observation ID cannot be reused across
accessions or masquerade as evidence for both concepts.

## Identity

`semantic_id` binds:

- versions, evidence kind, capability state and reasons;
- native profile state and reasons;
- paired route-context presence or absence and source CIK;
- exact period, namespace, accounting basis, concepts and unit;
- canonical exact numeric values when established; and
- authority and limitations.

Opaque route-local keys and upstream profile/comparability IDs remain public
traceability and evidence inputs, but do not determine economic semantic
identity. `ROUTE_CONTEXT_PRESENT` versus `ROUTE_CONTEXT_ABSENT` is the only
route-context meaning bound into semantics. Mixed route-key presence is
invalid. Semantic identity also does not bind incidental archive paths,
temporary filenames, capture timestamps, receipts, object hashes, selected
observation evidence or supporting-filing provenance.

`evidence_id` binds the semantic identity plus:

- actual upstream profile/comparability semantic identities;
- upstream profile/comparability evidence identities;
- actual route-local issuer/security keys;
- receipt/object identity and capture provenance;
- selected observation evidence identities; and
- supporting accession/filing provenance.

Therefore:

```text
same economics + legitimate recapture
→ same semantic_id
→ different evidence_id
```

A later legitimate CURRENT capture with unchanged issuer, period, concepts,
unit and economics also preserves `semantic_id` while changing `evidence_id`,
even when its capture-bound route keys change. Conversely, issuer, period,
concept, unit, capability state/reason, revenue or operating-income changes
change semantic identity. Equal-margin economics such as `100 / 20` and
`200 / 40` remain semantically distinct because this contract binds both exact
reported values and performs no ratio calculation.

Equivalent finite Decimal forms such as `100`, `100.0`, `100.00` and `1E+2`
have one semantic numeric representation. Canonicalization is deterministic,
context-independent, non-rounding and never binary64.

## Authority and limitations

Authority is exactly `QUALITY_PROFITABILITY_EVIDENCE_ONLY`. The output pins
these limitations:

- only the exact reviewed US-GAAP revenue and operating-income concepts;
- no taxonomy, non-GAAP, normalized or adjusted-earnings substitution;
- no operating, gross, net or free-cash-flow margin;
- no good/bad profitability or profitability-Quality conclusion;
- no margin stability/expansion, pricing-power or cost-discipline conclusion;
- no ROIC, ROE, ROA or earnings-quality conclusion;
- no historical profitability trend;
- no cross-issuer comparability;
- no cross-sector comparability;
- no moat conclusion;
- no Durability or persistence conclusion;
- no Confidence score or substitution;
- no Expected Return effect;
- no aggregate Quality score, grade or weight;
- no recommendation, ranking, allocation or sizing;
- no execution, production or V2-promotion authority; and
- no `HISTORICAL_AS_OF` or PIT authority.

## CURRENT and PIT boundary

This is CURRENT evidence about one historical annual reporting period. It does
not prove what PAM knew at fiscal-period end, filing time or any earlier cutoff.
A later legitimate recapture may change evidence identity while preserving
economic semantic identity. No PIT reconstruction or historical trend is
created.

## V1 and model-policy boundary

V1, Expected Return, Durability, Confidence, Portfolio Room and downstream
portfolio behavior remain untouched. No ratio, threshold, grade, score,
weight, aggregate Quality object or investment rule is introduced.

`MODEL_RULES_VERSION` remains
`2026-08-23-allocation-room-integrity-v7`. The protected PIT and determinism
fingerprints remain unchanged. No production, deployment or V2-promotion
authority is granted.
