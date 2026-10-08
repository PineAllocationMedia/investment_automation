# CURRENT annual assets and liabilities qualification

## Contract identity

- Contract version:
  `2026-10-08-current-annual-assets-liabilities-qualification-v1`
- Qualifier version:
  `2026-10-08-paired-common-filing-exact-decimal-usd-instant-fact-qualification-v1`
- Evidence kind:
  `CURRENT_ANNUAL_ASSETS_LIABILITIES_QUALIFICATION`
- Result type:
  `CurrentAnnualAssetsLiabilitiesQualification`
- Authority:
  `QUALITY_BALANCE_SHEET_EVIDENCE_ONLY`

This is one bounded Stage-C Quality evidence foundation. It establishes two
paired accounting facts only. It performs no arithmetic and creates no
balance-sheet diagnostic or conclusion.

## Economic question

The qualifier answers exactly:

> At the latest annual reporting date already established by PAM's supported
> ordinary-compounder route, can PAM establish one coherent CURRENT SEC
> Companyfacts presentation of total assets and total liabilities?

The exact reviewed concepts are:

- `us-gaap:Assets`; and
- `us-gaap:Liabilities`.

The accounting basis is `US_GAAP` and the unit is exactly `USD`. Issuer
extensions, debt concepts, current assets or liabilities, stockholders' equity,
tangible assets, invested capital, reconstructed totals, inferred totals and
all alternative tags do not substitute. Missing exact concepts remain evidence
unavailable.

## Exact public input

The public function accepts exactly:

1. `economic_facts.sec_archive.SecArchive`; and
2. `economic_facts.sec_ordinary_compounder_profile.OrdinaryCompounderMethodProfileQualification`.

Subclasses, mappings, dictionaries and duck-typed substitutes are rejected.
The caller cannot provide a CIK, date, receipt, accession, raw value,
qualification state, route identity or detached Companyfacts/comparability
object.

The profile must use upstream contract
`2026-10-07-sec-ordinary-compounder-method-profile-v2`. It supplies the
canonical route context, reporting subject/source CIK, authenticated expected-
versus-actual comparability identities, comparability chain and embedded
Companyfacts receipt. The qualifier rereads only the immutable object selected
by that receipt from the supplied archive. It performs no acquisition, network
access, clock read or historical reconstruction.

## Lossless extraction boundary

`economic_facts/sec_assets_liabilities.py` extracts only the two reviewed
concepts from exact captured Companyfacts bytes and receipt. Each immutable
observation preserves:

- source CIK, namespace, concept and unit;
- exact base-ten `Decimal` value;
- source `start` when present and exact `end`, FY, FP, form, filed date,
  accession and optional frame;
- source object hash, receipt identity and captured-at provenance;
- capture source locator, row source locator and semantic locator;
- canonical row JSON and source semantics; and
- separate observation semantic and evidence identities.

JSON numeric values are parsed directly as `Decimal`; binary float conversion
is forbidden. Duplicate JSON keys and malformed source structures fail closed.
Missing is not zero. Non-finite values cannot establish facts. Extraction does
not perform period qualification or analysis.

## Instant-fact and establishment semantics

`Assets` and `Liabilities` are instant facts. The target date is exactly the
latest annual `period_end` in the canonical five-period comparability chain.
The public result has `period_end` and deliberately has no `period_start`.

`PAIRED_ASSETS_LIABILITIES_ESTABLISHED` requires all of the following:

- the exact canonical upstream profile is established with coherent native
  state and reasons;
- expected comparability semantic/evidence identities match the actual embedded
  comparability identities;
- the embedded comparability and its five-period annual chain remain canonical;
- the latest annual `period_end` is derived from that chain, never selected by
  the caller;
- the embedded Companyfacts receipt/object replays from the supplied archive;
- route-local identities, source CIK, request, receipt and series agree;
- both exact reviewed concepts exist under `us-gaap` in exact unit `USD`;
- both values are finite exact `Decimal` values, including zero or negative
  values when reported;
- each admissible observation has no duration `start` and ends exactly on the
  target annual `period_end`;
- presentation is annual `FY` on form `10-K` or `10-K/A`;
- at least one accession contains admissible observations for both concepts;
- each common accession has one coherent form, filed date and fiscal year;
- all admissible common paired Assets observations agree on one exact value; and
- all admissible common paired Liabilities observations agree on one exact
  value.

The qualifier never fabricates or requires a duration start, infers an earlier
balance-sheet date, performs beginning/end averaging, averages values,
interpolates, normalizes, converts currency or chooses arbitrarily among
competing values. A duration-style row with `start` cannot establish this
instant-fact pair. An observation appearing for only one concept cannot
establish the pair, but it does not poison an otherwise coherent common pair.
`frame` equality is not required.

## Capability states and reasons

The exact states are:

- `PAIRED_ASSETS_LIABILITIES_ESTABLISHED`;
- `EVIDENCE_UNAVAILABLE`;
- `EVIDENCE_UNSUPPORTED`; and
- `SOURCE_CONFLICT`.

Upstream projection is exact:

| Upstream profile state | Result state and reason |
| --- | --- |
| `PROFILE_UNAVAILABLE` | `EVIDENCE_UNAVAILABLE` / `UPSTREAM_PROFILE_UNAVAILABLE` |
| `PROFILE_UNSUPPORTED` | `EVIDENCE_UNSUPPORTED` / `UPSTREAM_PROFILE_UNSUPPORTED` |
| `SOURCE_CONFLICT` | `SOURCE_CONFLICT` / `UPSTREAM_SOURCE_CONFLICT` |

Reasons are closed and deterministically ordered:

- `UPSTREAM_PROFILE_UNAVAILABLE`;
- `UPSTREAM_PROFILE_UNSUPPORTED`;
- `UPSTREAM_SOURCE_CONFLICT`;
- `CANONICAL_ROUTE_IDENTITY_CONFLICT`;
- `CAPTURE_REPLAY_CONFLICT`;
- `SOURCE_CIK_CONFLICT`;
- `ASSETS_UNAVAILABLE`;
- `LIABILITIES_UNAVAILABLE`;
- `EXACT_USD_UNIT_UNAVAILABLE`;
- `FINITE_ASSETS_VALUE_UNAVAILABLE`;
- `FINITE_LIABILITIES_VALUE_UNAVAILABLE`;
- `EXACT_ANNUAL_TARGET_PERIOD_END_PRESENTATION_UNAVAILABLE`;
- `NO_COMMON_ANNUAL_FILING_ACCESSION`;
- `COMPETING_ASSETS_VALUES`;
- `COMPETING_LIABILITIES_VALUES`; and
- `COMMON_FILING_METADATA_CONFLICT`.

Unknown future states and factory-impossible reconstructed upstream
state/reason combinations fail closed. Exact dataclass or enum identity alone
does not make an impossible reconstruction canonical.

Every non-established result exposes `None` for both numeric values and empty
selected-observation/supporting-filing surfaces. Partial numeric qualification
is forbidden.

## Replay trust boundary

The qualifier independently validates the upstream contract/qualifier versions,
native state and reason types/order/coherence, route context, CIK, annual chain,
profile/comparability identities, and capture receipt/object replay. It rebuilds
the bounded upstream profile projection needed here and requires equality with
the supplied profile.

PR #115 replay provenance remains authenticated directly:

```text
expected comparability semantic ID != actual comparability semantic ID
OR
expected comparability evidence ID != actual comparability evidence ID
→ REPLAY_IDENTITY_MISMATCH
```

A reason-only conflict with matching identities, an expected-ID mutation without
its canonical state/reason effect, or contradictory route provenance is rejected
or fails closed as appropriate.

## Immutable output and provenance

The result exposes only:

- contract/qualifier versions, evidence kind, state and closed reasons;
- native upstream profile state and reasons;
- route-local issuer/security keys and source CIK;
- exact target `period_end` and accounting semantics;
- exact Assets and Liabilities values when established;
- actual upstream profile/comparability semantic and evidence identities;
- receipt, object, captured-at and capture-source-locator provenance;
- selected observation IDs for each concept;
- supporting accessions and immutable filing metadata;
- authority and closed limitations; and
- deterministic `semantic_id` and `evidence_id`.

For established results, supporting accessions are sorted and unique. Each
supporting filing has exactly one coherent form, filed date and fiscal year and
nonempty sorted unique observation IDs for both concepts. Selected IDs are an
exact partition of filing IDs.

## Identity

`semantic_id` binds:

- contract/qualifier versions, evidence kind, state and reasons;
- native profile state and reasons;
- stable route-context presence/absence and source CIK;
- exact target `period_end`, namespace, basis, concepts and unit;
- canonical exact Assets/Liabilities values when established; and
- authority and limitations.

Opaque route-local key values, capture metadata, receipt/object identities,
selected observation IDs, supporting filing provenance and upstream evidence
IDs do not directly determine economic semantic identity. Mixed route-key
presence is invalid.

`evidence_id` binds the foundation `semantic_id` plus:

- actual upstream profile/comparability semantic identities;
- upstream profile/comparability evidence identities;
- actual route-local issuer/security keys;
- receipt/object identity and capture provenance;
- selected Assets/Liabilities observation IDs; and
- supporting accession/filing provenance.

Therefore:

```text
same economics + legitimate recapture
→ same semantic_id
→ different evidence_id
```

A later legitimate CURRENT capture with unchanged issuer, reporting date,
concepts, unit and economics preserves `semantic_id` while changing
`evidence_id`. Different absolute Assets or Liabilities values produce different
semantics even if a hypothetical ratio would be equal. This contract computes
no ratio. Equivalent finite Decimal forms canonicalize identically without
rounding, float conversion or ambient Decimal-context dependence.

## Authority and closed limitations

Authority is exactly `QUALITY_BALANCE_SHEET_EVIDENCE_ONLY`. The output grants no
authority for:

- treating `Liabilities` as interest-bearing debt;
- treating `Assets` as invested capital;
- liabilities/assets, debt/assets, debt/equity or current ratios;
- net debt, leverage, liquidity, working capital or solvency conclusions;
- balance-sheet strength;
- ROA, ROE or ROIC;
- capital-allocation conclusions;
- tangible-book or liquidation value;
- historical balance-sheet trend;
- cross-issuer or cross-sector comparability;
- Quality score, grade, aggregate, weight or ranking;
- Durability or persistence;
- Expected Return or Confidence change;
- recommendation, allocation or sizing;
- execution, production, deployment or V2 promotion; or
- `HISTORICAL_AS_OF` or PIT authority.

## CURRENT, V1 and model-policy boundary

This is CURRENT evidence about one historical annual reporting date. It does
not prove what PAM knew at that date, filing time or any earlier cutoff. No PIT
reconstruction or historical trend is created.

V1 remains frozen and V2 remains challenger-only. Existing Quality capabilities,
Expected Return, Durability, Confidence, Portfolio Room and downstream portfolio
behavior remain untouched. No ratio, threshold, grade, score, weight, aggregate
Quality object or investment rule is introduced.

`MODEL_RULES_VERSION` remains
`2026-08-23-allocation-room-integrity-v7`. The protected PIT and determinism
fingerprints remain unchanged. No production, deployment or V2-promotion
authority is granted.
