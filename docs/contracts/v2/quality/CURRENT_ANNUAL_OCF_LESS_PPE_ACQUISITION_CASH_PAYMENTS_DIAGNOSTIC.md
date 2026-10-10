# CURRENT Annual OCF Less PP&E Acquisition Cash Payments Diagnostic

## 1. Identity and authority

- Contract version: `2026-10-09-current-annual-ocf-less-ppe-acquisition-cash-payments-diagnostic-v1`
- Methodology version: `2026-10-09-exact-base-ten-ocf-minus-ppe-cash-payments-v1`
- Analysis kind: `CURRENT_ANNUAL_OCF_LESS_PPE_ACQUISITION_CASH_PAYMENTS`
- Result: `CurrentAnnualOCFLessPPEAcquisitionCashPaymentsResult`
- Authority: `QUALITY_CURRENT_ANNUAL_OCF_LESS_PPE_ACQUISITION_CASH_PAYMENTS_DIAGNOSTIC_ONLY`

This is a bounded Stage-C Quality diagnostic. It reports one exact arithmetic
relationship between two already-qualified CURRENT annual US-GAAP cash-flow
facts. It is not a new evidence qualifier and grants no production, investment,
scoring, or promotion authority.

## 2. Exact public boundary

The diagnostic accepts exactly two positional objects, in this order:

1. exact `CurrentAnnualOperatingCashFlowNetIncomeQualification`;
2. exact `CurrentAnnualPPEAcquisitionCashPaymentsQualification`.

Subclasses, mappings, duck-typed objects, detached values, and caller assertions
are rejected. Each qualification must independently satisfy its canonical
contract version, qualifier version, evidence kind, reviewed accounting
semantics, concepts, unit, authority, full ordered limitations, closed native
status/reasons, ordinary-compounder profile state/reasons, identity/provenance
shape, and established or non-established evidence invariants. Malformed or
internally impossible qualifications raise the diagnostic contract error.

The diagnostic does not acquire data, read an archive, access a network, select
a reporting period, requalify SEC evidence, or attempt to reconstruct upstream
factory state that is not exposed by the trusted qualification result.

## 3. Joint factual coherence

`AVAILABLE` requires both inputs to be independently established and to share:

- the same exact ten-digit source CIK;
- the same exact annual period start and end;
- namespace `us-gaap`, accounting basis `US_GAAP`, and unit `USD`;
- OCF concept `NetCashProvidedByUsedInOperatingActivities`;
- PP&E concept `PaymentsToAcquirePropertyPlantAndEquipment`;
- at least one accession present in each input's actual selected supporting
  filings; and
- identical form (`10-K` or `10-K/A`), filing date, and fiscal year for every
  common accession.

Issuer, period, accounting, unit, or concept contradictions are contract errors.
Two otherwise established inputs with no common accession produce
`UNAVAILABLE / NO_COMMON_SUPPORTING_ANNUAL_FILING_ACCESSION`. Any metadata
disagreement on a common accession produces
`SOURCE_CONFLICT / COMMON_SUPPORTING_FILING_METADATA_CONFLICT`; the diagnostic
does not choose a convenient subset to hide a disagreement.

Cross-foundation equality is deliberately **not** required for route-local keys,
capture receipts, source-object hashes, source locations, upstream profile or
comparability identities, or upstream qualification semantic identities. These
surfaces may differ under legitimate independent capture. Each remains validated
inside its own qualification and bound into diagnostic evidence identity.

For legitimately non-established evidence, missing source context remains
missing. It is never fabricated, treated as a mismatch, or converted to zero.

## 4. Exact mathematical rule

For coherent established evidence:

```text
ocf_less_ppe_acquisition_cash_payments =
    operating_cash_flow - ppe_acquisition_cash_payments
```

Both signs are preserved exactly as qualified. A negative PP&E amount is
subtracted as negative; it is not normalized to an outflow. The implementation
aligns finite base-ten Decimal integer coefficients and exponents and constructs
the result directly. It therefore does not use binary float, ambient Decimal
rounding, epsilon, thresholds, clipping, or valuation adjustments. Exact zero is
canonicalized to `Decimal(0)`.

Illustrative mathematics only: `100 - 30 = 70`, `100 - 0 = 100`,
`100 - (-30) = 130`, `-100 - 30 = -130`, and `30 - 30 = 0`.

## 5. Closed states and reasons

Statuses are exactly:

- `AVAILABLE`
- `UNAVAILABLE`
- `UNSUPPORTED`
- `SOURCE_CONFLICT`

The closed reasons are exactly:

- `UPSTREAM_OCF_EVIDENCE_UNAVAILABLE`
- `UPSTREAM_PPE_EVIDENCE_UNAVAILABLE`
- `UPSTREAM_OCF_EVIDENCE_UNSUPPORTED`
- `UPSTREAM_PPE_EVIDENCE_UNSUPPORTED`
- `UPSTREAM_OCF_SOURCE_CONFLICT`
- `UPSTREAM_PPE_SOURCE_CONFLICT`
- `NO_COMMON_SUPPORTING_ANNUAL_FILING_ACCESSION`
- `COMMON_SUPPORTING_FILING_METADATA_CONFLICT`

For non-established inputs, precedence is `SOURCE_CONFLICT > UNSUPPORTED >
UNAVAILABLE`. Distinct OCF and PP&E failure reasons are retained, uniquely and in
deterministic order, together with both native upstream statuses and reasons.
No OCF, PP&E, or calculated numeric value is exposed unless status is
`AVAILABLE`. Subtraction has no `NOT_APPLICABLE` state.

## 6. Result and identities

The immutable serializable result exposes contract/methodology/kind, diagnostic
status/reasons, both native upstream states, shared issuer/period/accounting
semantics, exact reviewed concepts, the three numeric values only when
available, both upstream qualification semantic/evidence IDs, common supporting
accessions, authority, limitations, and diagnostic semantic/evidence IDs.

The diagnostic `semantic_id` binds only stable analytical meaning:

- contract, methodology, kind, diagnostic status and reasons;
- source CIK and annual period;
- namespace, accounting basis, unit, and both concepts;
- canonical exact-Decimal semantics for OCF, PP&E, and the difference; and
- authority and full limitations.

It excludes net income, all upstream semantic IDs, route keys, accessions,
observation IDs, receipts, object hashes, timestamps, locators, and other
evidence-only metadata. Equivalent Decimal lexical forms therefore share one
economic identity. A net-income-only change cannot change diagnostic semantic
identity when OCF, PP&E, issuer, period, and accounting semantics are unchanged.

The `evidence_id` binds the semantic identity plus both actual upstream
qualification semantic/evidence IDs, both complete qualification provenance
surfaces (including profile/comparability identities, receipts, hashes,
timestamps, locators, selected observations, and supporting filings), and the
actual common accessions. Legitimate recapture may therefore preserve
`semantic_id` while changing `evidence_id`.

## 7. Explicit limitations

The immutable result carries a closed limitation inventory denying:

- universal or GAAP-defined free cash flow;
- owner earnings or distributable cash;
- total capex or total reinvestment;
- maintenance-versus-growth capex;
- software, intangible, or lease-investment coverage;
- acquisition or M&A spending coverage;
- reinvestment or capital-allocation quality judgments;
- historical cash-flow trends;
- cross-company or cross-sector comparability;
- good/bad thresholds;
- Quality score, grade, weighting, aggregation, or ranking;
- Durability conclusions;
- Expected Return or Confidence modification;
- recommendation, sizing, allocation, or execution;
- production, deployment, or V2 promotion; and
- `HISTORICAL_AS_OF` or PIT authority.

CURRENT evidence may describe a historical reporting period, but it is not proof
that the evidence was available at a historical cutoff. The diagnostic adds no
provider, external source, dependency, or recurring cost.
