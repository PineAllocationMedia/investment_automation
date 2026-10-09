# CURRENT annual PP&E acquisition cash-payments qualification

## Contract identity

- Contract version:
  `2026-10-09-current-annual-ppe-acquisition-cash-payments-qualification-v1`
- Qualifier version:
  `2026-10-09-exact-annual-decimal-usd-ppe-cash-payments-v1`
- Evidence kind:
  `CURRENT_ANNUAL_PPE_ACQUISITION_CASH_PAYMENTS_QUALIFICATION`
- Result type:
  `CurrentAnnualPPEAcquisitionCashPaymentsQualification`
- Authority:
  `QUALITY_PPE_ACQUISITION_CASH_PAYMENTS_EVIDENCE_ONLY`

This is one bounded Stage-C evidence foundation. It establishes one exact
reported accounting fact only. It is not an analytical diagnostic, free-cash-
flow calculation, Quality score or investment decision.

## Economic question

The qualifier answers exactly:

> For the latest annual fiscal period already established by PAM's supported
> ordinary-compounder route, can PAM establish one coherent CURRENT SEC
> Companyfacts presentation of exact reported cash payments to acquire
> property, plant and equipment?

The exact reviewed accounting surface is:

- namespace: `us-gaap`;
- concept: `PaymentsToAcquirePropertyPlantAndEquipment`;
- unit: `USD`; and
- accounting basis: `US_GAAP`.

The concept is a duration fact. Issuer extensions, alternative capex tags,
inferred totals, taxonomy fallbacks, provider-derived values and synonyms do
not substitute. Missing exact evidence remains unavailable.

## Exact public boundary

The public function accepts exactly:

1. `economic_facts.sec_archive.SecArchive`; and
2. `economic_facts.sec_ordinary_compounder_profile.OrdinaryCompounderMethodProfileQualification`.

Subclasses, mappings, dictionaries and duck-typed substitutes are rejected.
The caller cannot supply a CIK, date, period, receipt, accession, observation,
raw value, qualification state or detached comparability object.

Issuer and security context, source CIK, latest annual period and Companyfacts
receipt are derived exclusively from the canonical embedded ordinary-compounder
route. The qualifier authenticates the PR #115 expected-versus-actual
comparability replay surface and rereads only the exact immutable object
selected by the embedded receipt from the supplied archive. It performs no
acquisition, network access, clock read or historical reconstruction.

## Extraction boundary

`economic_facts/sec_ppe_acquisition_cash_payments.py` extracts only the
reviewed concept. Each immutable observation preserves:

- source CIK, namespace, concept, unit and accounting basis;
- exact finite base-ten `Decimal` value;
- exact start and end dates, FY, FP, form, filed date and accession;
- optional frame without treating it as a qualification substitute;
- source object hash, capture receipt and captured-at provenance;
- capture, row and semantic locators;
- canonical source-row JSON and source semantics; and
- separate source-observation semantic and evidence identities.

JSON fractional numbers are parsed directly as `Decimal`; binary float
conversion is forbidden. Malformed source structures fail closed. Missing is
not zero. Non-finite and malformed values cannot establish evidence.

## Canonical annual presentation

The target is the latest exact annual period in the canonical five-period
comparability chain. An admissible observation requires:

- `start` equal to the canonical latest annual `period_start`;
- `end` equal to the canonical latest annual `period_end`;
- fiscal presentation `FY`;
- form `10-K` or `10-K/A`;
- a valid ISO filed date;
- a valid SEC accession;
- exact namespace, concept, `USD` unit and source CIK;
- a finite value whose runtime type is exactly `Decimal`; and
- no extraction metadata limitation.

Quarterly, YTD-only, partial-period and unmatched-duration facts are not
substitutes.

One or more admissible observations establish the result only when every
admissible observation reports the same exact economic value and each
supporting accession has coherent intrinsic form, filed-date and fiscal-year
metadata. Multiple same-value filings are preserved as evidence. Valid zero
and negative reported values are preserved without normalization or economic
interpretation.

Competing admissible values produce `SOURCE_CONFLICT`. The qualifier never
selects a latest, majority, maximum or minimum value to hide a conflict. It
never averages, rounds, converts currency, normalizes signs or infers a value.

## States and closed reasons

The result uses exactly:

- `PPE_ACQUISITION_CASH_PAYMENTS_ESTABLISHED`;
- `EVIDENCE_UNAVAILABLE`;
- `EVIDENCE_UNSUPPORTED`; and
- `SOURCE_CONFLICT`.

Upstream projection is exact:

| Upstream profile state | Result state and reason |
| --- | --- |
| `PROFILE_UNAVAILABLE` | `EVIDENCE_UNAVAILABLE` / `UPSTREAM_PROFILE_UNAVAILABLE` |
| `PROFILE_UNSUPPORTED` | `EVIDENCE_UNSUPPORTED` / `UPSTREAM_PROFILE_UNSUPPORTED` |
| `SOURCE_CONFLICT` | `SOURCE_CONFLICT` / `UPSTREAM_SOURCE_CONFLICT` |

The closed reason vocabulary is:

- `UPSTREAM_PROFILE_UNAVAILABLE`;
- `UPSTREAM_PROFILE_UNSUPPORTED`;
- `UPSTREAM_SOURCE_CONFLICT`;
- `CANONICAL_ROUTE_IDENTITY_CONFLICT`;
- `CAPTURE_REPLAY_CONFLICT`;
- `SOURCE_CIK_CONFLICT`;
- `PPE_ACQUISITION_CASH_PAYMENTS_UNAVAILABLE`;
- `EXACT_USD_UNIT_UNAVAILABLE`;
- `FINITE_PPE_ACQUISITION_CASH_PAYMENTS_VALUE_UNAVAILABLE`;
- `EXACT_ANNUAL_PERIOD_PRESENTATION_UNAVAILABLE`;
- `COMPETING_PPE_ACQUISITION_CASH_PAYMENTS_VALUES`; and
- `ANNUAL_FILING_METADATA_CONFLICT`.

Reasons are unique and deterministically ordered. Unknown future states and
factory-impossible reconstructed supposedly-canonical upstream objects are
programming-contract errors, not analytical unavailability.

Every non-established result has no numeric value and empty selected-
observation, supporting-accession and supporting-filing surfaces.

## Immutable result and provenance

The immutable result exposes:

- contract, qualifier and evidence-kind identities;
- exact state and closed reasons;
- native upstream state and reasons;
- route-local issuer/security keys and source CIK;
- canonical period and exact accounting semantics;
- exact PP&E acquisition cash payments when established;
- upstream profile/comparability semantic and evidence identities;
- receipt, object, capture timestamp and capture-source locator;
- selected observation IDs;
- supporting accessions and coherent filing metadata;
- authority and closed limitations; and
- deterministic `semantic_id` and `evidence_id`.

Supporting accessions and observation IDs are sorted and unique. Supporting
filings are an exact partition of selected observations and retain one coherent
form, filed date and fiscal year per accession.

## Semantic and evidence identity

`semantic_id` binds:

- contract and qualifier versions;
- evidence kind, state and reasons;
- native upstream capability state and reasons;
- stable issuer context through source CIK;
- exact annual start and end;
- namespace, accounting basis, concept and unit;
- canonical exact qualified value;
- authority and limitations.

Opaque route-local keys, actual upstream identities, archive paths, receipt and
object identities, capture time, capture locator, source-row position and
selected observations do not directly determine economic semantic identity.

`evidence_id` additionally binds:

- actual upstream profile and comparability semantic/evidence identities;
- route-local issuer and security keys;
- immutable capture receipt and source-object identities;
- capture timestamp and source locator;
- selected source-observation IDs; and
- supporting accession and filing provenance.

Therefore:

```text
same economics + legitimate recapture
→ same semantic_id
→ different evidence_id

changed exact economic value
→ changed semantic_id
```

Equivalent finite Decimal spellings such as `100`, `100.0`, `100.00` and
`1E+2` have one semantic numeric representation. Source-row reordering cannot
change economic semantic identity. Canonicalization is deterministic,
context-independent, non-rounding and never binary64.

## Closed authority and limitations

Authority is exactly
`QUALITY_PPE_ACQUISITION_CASH_PAYMENTS_EVIDENCE_ONLY`.

The result establishes only exact reported PP&E acquisition cash payments for
one qualified annual period. It grants no authority for:

- universal or total capex;
- maintenance versus growth capex;
- total reinvestment;
- intangible, software or lease investment;
- acquisition or M&A spending;
- depreciation replacement;
- free cash flow or owner earnings;
- ROIC, ROA or ROE;
- reinvestment or capital-allocation quality;
- good/bad spending judgment;
- historical trend;
- cross-issuer or cross-sector comparison;
- Quality score, grade, aggregate or ranking;
- Durability, Expected Return or Confidence modification;
- recommendation, allocation or execution;
- production, deployment or V2 promotion; or
- PIT or `HISTORICAL_AS_OF`.

The SEC concept is not silently broadened beyond its exact source meaning.

## CURRENT, V1 and model-policy boundary

This is CURRENT evidence about one historical annual reporting period. It does
not prove what PAM knew at fiscal-period end, filing time or an earlier cutoff.
A later legitimate recapture may change evidence identity while preserving
economic semantic identity. No PIT reconstruction or historical trend is
created.

V1, Expected Return, Durability, Confidence, Portfolio Room and downstream
portfolio behavior remain untouched. No ratio, threshold, grade, score,
weight, Quality aggregate or investment rule is introduced.

`MODEL_RULES_VERSION` remains
`2026-08-23-allocation-room-integrity-v7`. The protected PIT and determinism
fingerprints remain unchanged. No production, deployment or V2-promotion
authority is granted.
