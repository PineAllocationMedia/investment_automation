# VFV CURRENT Evidence Foundation

> One evidence-only Vanguard Canada route for VFV. This contract establishes
> typed CURRENT facts; it does not implement a VFV Expected Return or comparator.

## Verified base and scope

After `git fetch origin`, the canonical integration ref was exactly:

| Item | Verified value |
| --- | --- |
| Branch | `origin/model-v2/expected-return-challenger` |
| Commit | `73f007b165bb3781a8f523e573dbb76d00306758` |
| Tree | `90ec06cf3ea31e2424f84956a2e914da210d60ec` |
| Implementation branch | `codex/vfv-current-evidence-foundation` |

The checkout and index were clean before implementation. V1 remains unchanged and
frozen operational authority. V2 remains a challenger.

## Contract identity

```text
VFV_CURRENT_EVIDENCE_CONTRACT_VERSION
  = 2026-09-30-vfv-current-evidence-foundation-v1
VANGUARD_VFV_ARTIFACT_RECEIPT_VERSION
  = 2026-09-30-vanguard-vfv-artifact-receipt-v1
VANGUARD_VFV_ACQUISITION_VERSION
  = 2026-09-30-vanguard-vfv-current-acquisition-v1
VFV_CURRENT_EXTRACTION_VERSION
  = 2026-09-30-vfv-current-evidence-extraction-v1
VFV_CURRENT_QUALIFICATION_VERSION
  = 2026-09-30-vfv-current-evidence-qualification-v1
```

The top-level result is `VFVCurrentEvidenceQualification`. Its `semantic_id` and
`evidence_id` are deterministic. Runtime clocks, random UUIDs, filesystem paths and
object identity never enter either identity.

## Exact source route

V1 supports Vanguard Canada first-party evidence only. The fixed product route is:

```text
https://www.vanguard.ca/en/product/etf/equity/9563/vanguard-sp-500-index-etf
```

The official product page exposes these reviewed related-document relationships:

```text
Factsheet
  -> https://fund-docs.vanguard.com/VFV_SandP_500_Index_ETF_9563_FS_EN_CA.pdf

ETF facts
  -> https://fund-docs.vanguard.com/VFV_SnP_500_Index_ETF_ETF_9563_EN_FACTS.pdf
```

The document acquisition path freshly replays the exact product-page receipt and
resolves the exact named relationship from those retained bytes. It accepts no PDF
URL, latest-file search, ticker, product ID or alternate provider. Both the captured
relationship and the exact reviewed HTTPS host/path profile must agree. Redirects
are rejected.

There is no S&P, TMX, Yahoo/yfinance, paid-vendor, research-report or manual-value
fallback.

## Source authority

The registry contains exactly two new route identities:

```text
VANGUARD_CANADA_VFV_PRODUCT_CURRENT_V1
VANGUARD_CANADA_VFV_DOCUMENT_CURRENT_V1
```

The product route permits only acquisition provenance, capture-bound CURRENT
availability/snapshot scope, current observed market price, and quote currency/unit.
The document route permits only acquisition provenance and capture-bound CURRENT
availability/snapshot scope. Neither route permits `FINAL_ECONOMIC_ADMISSION`.

Both routes preserve:

```text
immutable_capture_required = True
publication_semantics      = UNKNOWN
availability_semantics     = CAPTURE_BOUND
pit_capability             = UNSUPPORTED
failure_policy             = FAIL_CLOSED
license_status             = UNKNOWN
use_status                 = REVIEW_REQUIRED
```

Legal/use metadata remains separate from factual truth and cannot increase factual
authority.

## Immutable archive

`VanguardVFVArchive` supports only `PRODUCT_PAGE`, `ETF_FACTS` and `FACTSHEET`.
There is no generic artifact family. The public archive surface is replay-only:
`read_receipt` and `read_object`. Publication is private to the reviewed acquisition
path; a private fixture helper exists only for tests.

Every `VanguardVFVArtifactReceipt` binds:

```text
schema_version
source_owner
artifact_family
source_url
content_type
content_sha256
byte_length
artifact_date
retrieved_at
acquisition_contract_version
parent_product_receipt_id
```

The archive stores exact response bytes under their SHA-256, publishes without
overwrite, rejects unsafe paths/symlinks/non-regular members, and verifies byte
length and hash on replay. `artifact_date` is nullable and retrieval time never
substitutes for a missing artifact date. Retrieval time must be exact and
offset-aware. The product page has no parent. Each PDF requires the exact retained
product-page parent.

## Acquisition APIs

```python
acquire_vanguard_vfv_product_page(*, archive_root)

acquire_vanguard_vfv_document(
    *, archive_root, product_page_receipt_id, artifact_family
)
```

The document family is exactly `ETF_FACTS` or `FACTSHEET`. Acquisition uses HTTPS
certificate/hostname verification, a fixed user agent, disabled ambient proxies,
redirect rejection, bounded socket/deadline/body/header limits, identity-only
content encoding, strict content types and PDF magic validation. It performs one
request with no retry, cache, source substitution or fallback.

## Offline extraction and qualification

`extract_vfv_current_artifact` freshly replays one receipt. HTML extraction is
bounded to retained text/table semantics. PDF extraction occurs offline from the
exact retained bytes. Unknown content remains in the immutable object but does not
gain a fact role.

`VFVCurrentEvidenceRequest` contains only the three exact receipt IDs and the
expected semantic/evidence identity pair for each freshly replayed extraction.
It contains no economic value, chronology, ticker, URL, product ID, identity claim,
qualification state or success boolean. An expected identity mismatch produces
`SOURCE_CONFLICT / REPLAY_IDENTITY_MISMATCH`.

Success establishes these typed objects:

- `VFVFundIdentity`: legal/current route identity, listing/currency, tracked economic
  index and the evidenced underlying U.S.-domiciled Vanguard vehicle;
- `VFVMarketObservation`: exact issuer daily CAD market price and optional separately
  labelled issuer daily NAV;
- `VFVExpenseFacts`: management fee, MER and TER as separate exact percentages, with
  explicit completed-period semantics for MER and TER;
- `VFVDistributionFacts` and `VFVDistributionEvent`: exact latest event chronology and
  explicit issuer trailing-12-month yield;
- `VFVTrailingValuation`: one provider trailing weighted P/E for the fund portfolio;
- `VFVCurrencyExposureFacts`: CAD listing/base, explicitly evidenced USD exposure and
  unhedged state.

The reviewed positive identity is extracted and corroborated from evidence; it is
not returned merely because the route is named VFV:

```text
Vanguard S&P 500 Index ETF
ETF Units
Toronto Stock Exchange
VFV
CA92205Y1051
CAD listed currency
CAD base currency
S&P 500 Index
Vanguard S&P 500 ETF
United States domicile
```

Ticker remains a locator, not sufficient identity authority. ETF Facts is primary
for fund/unit/ticker/exchange/current legal presentation; product-page and Factsheet
facts corroborate where present. ISIN and underlying-vehicle semantics require
positive retained evidence. Identity disagreement fails closed.

`tracked_economic_index` and optional `performance_series_label` are different
fields. A CAD/NTR performance label is never relabelled as the tracked economic
index and creates no inferred tax or net-return semantics.

## Contradiction and chronology rules

- same expense metric, same explicit completed period, different value is conflict;
- different explicit periods are not conflict;
- the most recent explicitly evidenced completed period is selected;
- observations are never averaged and expenses are never arithmetically combined;
- different market-price dates are not conflicts and archive recency is never scanned;
- NAV never substitutes for required market price;
- latest quarterly distribution is never annualized or extrapolated;
- event chronology requires `ex_date <= record_date <= payment_date`;
- field-effective/document dates cannot be after their own capture date;
- publication time remains unknown and is never inferred from a document/effective/
  page/retrieval date.

Archive corruption, hash mismatch, unsafe paths and programming-contract violations
remain exceptions rather than economic availability states.

## Status model

The closed statuses are exactly `AVAILABLE`, `UNAVAILABLE`, `UNSUPPORTED` and
`SOURCE_CONFLICT`; there is no degraded result. Reasons are partitioned exactly:

| Status | Reasons |
| --- | --- |
| `SOURCE_CONFLICT` | `REPLAY_IDENTITY_MISMATCH`, `IDENTITY_MISMATCH`, `TRACKED_INDEX_DISAGREEMENT`, `SAME_METRIC_SAME_DATE_CONFLICT`, `FIELD_CHRONOLOGY_INVALID` |
| `UNSUPPORTED` | `SOURCE_STRUCTURE_UNSUPPORTED`, `REQUIRED_FIELD_UNSUPPORTED_BY_REVIEWED_FREE_SOURCE` |
| `UNAVAILABLE` | `MISSING_REQUIRED_PRIMARY_ARTIFACT`, `MUTABLE_PAGE_NOT_CAPTURED`, `PRICE_UNAVAILABLE`, `REQUIRED_FIELD_UNAVAILABLE`, `EXPENSE_PERIOD_AMBIGUOUS` |

## Field-specific provenance and identity

Every qualified role has exactly one `VFVFactEvidence` record with a closed
`VFVFactRole`. Each record retains the exact receipt/family/URL/content hash/source
locator, nullable artifact date, field-effective date, capture-bound availability,
retrieval time and extraction version.

For v1:

```text
publication_timestamp = None
publication_semantics = UNKNOWN
availability_timestamp = retrieved_at
availability_semantics = CAPTURE_BOUND
```

There is no synthetic `current_at`. `latest_capture_at` is descriptive replay
metadata only and does not enter semantic identity.

Semantic identity binds the contract and qualification versions, status/reasons,
all qualified facts and semantics, field-effective dates, limitations, factual
route hashes and upstream extraction semantic identities. Evidence identity adds
receipt IDs, exact hashes, retrieval times, URLs/locators, full route-profile hashes
and upstream extraction evidence identities. Equivalent later recapture therefore
preserves semantic identity while changing evidence identity.

## Authority boundary and excluded fields

Positive factual authority is exactly `CURRENT_ONLY`. Every result retains the
complete no-history, no-PIT, no-first-publication, capture-bound, no-executable-quote,
no-forward-estimate, no-Expected-Return, no-recommendation/allocation, no-execution/
production, VFV-first-route and no-generic-benchmark limitations.

It also states that public availability is not commercial authority, commercial
ingestion/redistribution and S&P reuse are not authorized, use is current private
internal research only, TMX is not a primary source, and CUSIP is not exposed.

The qualification deliberately exposes no P/B, ROE, underlying dividend yield,
historical growth/return/CAGR/performance statistic, historical distribution growth,
CUSIP, forward EPS/growth/P/E, provider forward ER, bid, ask or broker executable
price. Missing forward estimates are outside this evidence contract and do not make
the evidence foundation unavailable.

## Non-goals and isolation

This chantier adds no VFV Expected Return, terminal valuation, scenario policy,
comparator/spread, expense arithmetic policy, forecast, cash-like logic, broker
cost, Quality, Durability, Confidence, Opportunity Set, recommendation, allocation,
execution, deployment or promotion. The new modules import no Expected Return
engine/assumption/PR5E adapter, `main`, allocation or runtime consumer. Existing V1
and production consumers import none of the new modules.

The expected validation tier is `STANDARD`: every ordinary discovered test runs,
while the isolated heavyweight PIT adapter-equivalence module is not regenerated or
executed solely for this change. `MODEL_RULES_VERSION` remains unchanged.
