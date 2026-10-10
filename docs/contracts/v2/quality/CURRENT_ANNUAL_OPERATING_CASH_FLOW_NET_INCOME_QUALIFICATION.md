# CURRENT annual operating-cash-flow and net-income qualification

## Contract identity

- Contract version:
  `2026-10-10-current-annual-operating-cash-flow-net-income-qualification-v2`
- Qualifier version:
  `2026-10-05-paired-common-filing-exact-decimal-usd-qualification-v1`
- Evidence kind:
  `CURRENT_ANNUAL_OPERATING_CASH_FLOW_NET_INCOME_QUALIFICATION`
- Result type:
  `CurrentAnnualOperatingCashFlowNetIncomeQualification`
- Authority:
  `QUALITY_CASH_CONVERSION_EVIDENCE_ONLY`

This is one bounded Stage-C evidence foundation. It establishes two paired
accounting facts only. It does not calculate or diagnose cash conversion.

## Economic question

The qualifier answers exactly:

> For the latest annual fiscal period already established by PAM's supported
> ordinary-compounder route, can PAM establish one coherent CURRENT SEC
> Companyfacts presentation of operating cash flow and net income?

The exact reviewed concepts are:

- `us-gaap:NetCashProvidedByUsedInOperatingActivities`; and
- `us-gaap:NetIncomeLoss`.

The reviewed unit is exactly `USD`. `ProfitLoss`, issuer extensions, adjusted
earnings, EBITDA, free cash flow, provider-derived values and all other
synonyms or proxies do not substitute.

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

`economic_facts/sec_operating_cash_flow_net_income.py` extracts only the two
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
`PAIRED_OPERATING_CASH_FLOW_NET_INCOME_ESTABLISHED` requires all of the
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
- all admissible common paired operating-cash-flow presentations agree on one
  exact value; and
- all admissible common paired net-income presentations agree on one exact
  value.

The qualifier never averages, rounds, interpolates, normalizes, converts
currency or arbitrarily chooses among competing values. Conflict analysis is
restricted to admissible common paired accessions. An orphan observation for
only one concept does not poison a coherent common pair and is excluded from
selected evidence. `frame` equality is not required.

## Capability states and reasons

The result uses exactly:

- `PAIRED_OPERATING_CASH_FLOW_NET_INCOME_ESTABLISHED`;
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
- `OPERATING_CASH_FLOW_UNAVAILABLE`;
- `NET_INCOME_UNAVAILABLE`;
- `EXACT_USD_UNIT_UNAVAILABLE`;
- `FINITE_OPERATING_CASH_FLOW_VALUE_UNAVAILABLE`;
- `FINITE_NET_INCOME_VALUE_UNAVAILABLE`;
- `EXACT_ANNUAL_PERIOD_PRESENTATION_UNAVAILABLE`;
- `NO_COMMON_ANNUAL_FILING_ACCESSION`;
- `COMPETING_OPERATING_CASH_FLOW_VALUES`;
- `COMPETING_NET_INCOME_VALUES`; and
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
- exact operating cash flow and net income when established;
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

### Version boundary

The legacy contract
`2026-10-05-current-annual-operating-cash-flow-net-income-qualification-v1`
bound actual route-local issuer/security keys and upstream profile/comparability
semantic IDs into `semantic_id`. Those upstream IDs can be capture-sensitive;
therefore genuine recapture could change the legacy semantic ID with unchanged
qualified economics. This was an identity-contract defect, not evidence of
incorrect accounting values.

The v2 contract corrects only the semantic/evidence projection. The qualifier
methodology remains
`2026-10-05-paired-common-filing-exact-decimal-usd-qualification-v1`.
Previously produced v1 semantic and evidence IDs remain version-scoped legacy
identities. They must not be silently equated to v2 IDs. No cache migration,
persistence rewrite, bulk requalification or dual-version execution is provided
or authorized.

### v2 economic semantics

`semantic_id` binds:

- contract and qualifier versions, evidence kind, native capability state and
  closed reasons;
- native upstream profile capability state and reasons;
- issuer and security route-context presence/absence, represented separately as
  booleans, and source CIK;
- exact annual start/end, namespace, accounting basis, concepts and reviewed unit;
- canonical exact OCF and Net Income values when established; and
- authority and the complete limitation inventory.

Actual route keys and upstream profile/comparability semantic or evidence IDs
are excluded. So are receipts, object hashes, timestamps, locators, observation
IDs, accessions and supporting-filing provenance. No indirectly capture-sensitive
identifier substitutes for these fields. Missing route context stays distinct
from present context. Non-established outcomes preserve their true state,
reasons and available context, with both numeric facts absent.

### v2 evidence provenance

`evidence_id` binds the corrected semantic identity plus:

- actual route-local issuer/security keys;
- upstream profile/comparability semantic **and** evidence identities;
- receipt/object identity, capture timestamp and source locator;
- selected OCF and Net Income observation identities; and
- supporting accessions and full filing metadata.

All existing public provenance fields remain exposed. Evidence is neither
removed nor suppressed to obtain semantic stability.

```text
same qualified economics + authentic independent or later CURRENT recapture
→ same semantic_id
→ different evidence_id when provenance changes

changed qualified OCF or Net Income
→ different semantic_id
```

Equivalent finite Decimal forms such as `100`, `100.0`, `100.00` and `1E+2`
have one semantic numeric representation. Canonicalization is deterministic,
context-independent, non-rounding and never binary64. Signed values are
preserved and all exact zero forms have one representation. Both absolute
accounting amounts are bound independently: equal prospective OCF/NI ratios
from different absolute pairs do not collapse to one semantic identity.

## Authority and limitations

Authority is exactly `QUALITY_CASH_CONVERSION_EVIDENCE_ONLY`. The output pins
these limitations:

- only the exact reviewed US-GAAP OCF and net-income concepts;
- no non-GAAP or normalized-earnings substitution;
- no free-cash-flow or capex claim;
- no cash-conversion ratio or diagnostic;
- no accruals-quality conclusion;
- no working-capital causal attribution;
- no profitability-quality conclusion;
- no historical cash-conversion trend;
- no cross-sector comparability;
- no Durability or persistence conclusion;
- no Confidence conclusion;
- no Expected Return effect;
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
