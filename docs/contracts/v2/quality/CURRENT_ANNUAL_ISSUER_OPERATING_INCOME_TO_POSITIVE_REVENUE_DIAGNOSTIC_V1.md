# CURRENT annual issuer Operating Income / positive Revenue route — proposed v1

**PROPOSED / NOT_IMPLEMENTED / NO_RUNTIME_AUTHORITY**

Work Order: `WO-STAGE-C-ISSUER-LEVEL-REPORTED-PROFITABILITY-NATIVE-PATH-V1`.
Phase 1 only. SHALL denotes proposed requirements pending independent Architecture
& Audit review and CEO approval, not implemented or ratified methodology.

## 1. Separate route, existing economic diagnostic

| Field | Proposed value |
| --- | --- |
| Contract identity | `CURRENT_ANNUAL_ISSUER_OPERATING_INCOME_TO_POSITIVE_REVENUE_DIAGNOSTIC_V1` |
| Contract version | `2026-10-12-current-annual-issuer-operating-income-to-positive-revenue-diagnostic-v1` |
| Route | `CURRENT_ANNUAL_ISSUER_REPORTED_PROFITABILITY_NATIVE_V1` |
| Analysis kind (unchanged) | `CURRENT_ANNUAL_OPERATING_INCOME_TO_POSITIVE_REVENUE` |
| Methodology version (reused) | `2026-10-08-exact-rational-operating-income-per-positive-revenue-v1` |
| Identity version | `2026-10-12-issuer-operating-income-positive-revenue-identities-v1` |
| Proposed module | `src.current_annual_issuer_operating_income_to_positive_revenue` |
| Proposed entrypoint | `analyze_current_annual_issuer_operating_income_to_positive_revenue_v1(qualification)` |
| Result type | `CurrentAnnualIssuerOperatingIncomeToPositiveRevenueResultV1` |
| Authority, if subsequently implemented and approved | `QUALITY_CURRENT_ISSUER_OPERATING_INCOME_TO_POSITIVE_REVENUE_DIAGNOSTIC_ONLY` |

This is a new native issuer route for one existing economic diagnostic, not an
eighth distinct Quality diagnostic. The only proposed analysis is the exact signed
relationship of source-reported Operating Income to strictly positive Revenue for
one qualified annual interval. It is CURRENT issuer-level Quality research diagnosis,
not overall company Quality or Ordinary Compounder eligibility.

The [legacy diagnostic](CURRENT_ANNUAL_OPERATING_INCOME_TO_POSITIVE_REVENUE_DIAGNOSTIC.md)
retains its existing profile-dependent foundation, pure entrypoint, types, versions,
authority and behavior. This proposal neither widens its inputs nor redirects callers.

## 2. Exact input and independent verification

The sole public input SHALL be the exact proposed
`CurrentAnnualIssuerRevenueOperatingIncomeQualificationV1` from the
[new issuer qualification contract](CURRENT_ANNUAL_ISSUER_REVENUE_OPERATING_INCOME_QUALIFICATION_V1.md).
No archive or receipt override, subclass, dictionary, duck type, detached financial
facts, raw source, research candidate, legacy native qualification, profile or caller
qualification assertion is accepted. Incompatible versions and future enum members
are errors, never implicit migration.

Before examining availability or calculating, trusted consumer code SHALL:

1. Check exact native result and nested enum/record types, versions, kind, authority,
   temporal mode and complete fixed limitation set.
2. Validate source CIK, accounting basis, ordered exact concepts, USD, canonical
   dates/capture metadata, state/reason reachability, immutable inventory, fact
   presence/absence and coherent selected observation/filing partitions.
3. Use the factory-established private replay binding to read the exact immutable
   archive receipt and object. Verify membership, LIVE contract, source identity,
   bytes/hash/length and extraction as specified upstream.
4. Recompute the entire new native qualification from that source with trusted
   code, including all annual surveillance and exclusion inventory. Compare every
   public field, selected fact, support partition, provenance field and semantic/
   evidence identity against the supplied result. Recomputed IDs on forged fields
   alone do not pass. Do not invoke caller-provided validation methods or callbacks.
5. Calculate only from that fully verified replay snapshot. No unchecked reread or
   mutable caller field may replace the verified facts after validation.

This new route explicitly performs bounded local archive replay through its input's
binding. Its arithmetic is pure; its public validation boundary is read-only I/O.
It performs no network, acquisition, clock read, archive mutation, implicit receipt
selection or new qualification-policy selection. It does not change the legacy
analyzer's no-filesystem/no-replay contract. The binding's path/object identity is
not economic evidence and is neither exported nor hashed.

Detached serialization is not a native input; restore by rerunning the upstream
factory with the exact archive and receipt. Unavailable archive, stale/corrupt
binding, receipt mismatch and fabricated exact-type objects raise contract/integrity
errors. These are not economic `UNAVAILABLE` or `SOURCE_CONFLICT` results. A perfectly
matching reconstruction gains only the claim freshly proved by source replay.
The boundary retains SecArchive's trusted-local-process assumptions; it does not
claim resistance to arbitrary Python execution or replacement of all trust anchors.

## 3. Closed analytical states

Use separate native analytical enum types with the established diagnostic vocabulary.
Validate nonpositive upstream states just as rigorously as established ones.
Preserve native upstream status/reasons separately from analytical reasons.

| Verified upstream condition | Analytical state | Exact analytical reasons | Ratio |
| --- | --- | --- | --- |
| `PAIRED_ISSUER_REPORTED_FACTS_ESTABLISHED`, Revenue > 0 | `AVAILABLE` | Empty | Exact signed rational |
| Same established state, Revenue = 0 | `NOT_APPLICABLE` | `REVENUE_ZERO_DENOMINATOR` | None |
| Same established state, Revenue < 0 | `NOT_APPLICABLE` | `REVENUE_NEGATIVE_NOT_POSITIVE_DENOMINATOR` | None |
| `EVIDENCE_UNAVAILABLE` | `UNAVAILABLE` | `UPSTREAM_EVIDENCE_UNAVAILABLE` | None |
| `EVIDENCE_UNSUPPORTED` | `UNSUPPORTED` | `UPSTREAM_EVIDENCE_UNSUPPORTED` | None |
| `SOURCE_CONFLICT` | `SOURCE_CONFLICT` | `UPSTREAM_SOURCE_CONFLICT` | None |

No other states/reasons or mixed analytical reason families are accepted. Every
non-AVAILABLE result has no ratio. Zero/negative Revenue is a valid source-reported
fact when established, but is outside the positive-denominator analysis. Missing
facts never become zero. Unsupported evidence is not a low-Quality judgment.

## 4. Exact rational methodology

Use the existing immutable `OperatingIncomeToRevenueRatio` representation or an
identical narrow representation with explicit version compatibility; do not change
its meaning or extend its authority. For exact finite Decimals O and R, when R > 0:

```text
(o_num, o_den) = O.as_integer_ratio()
(r_num, r_den) = R.as_integer_ratio()
numerator = o_num * r_den
denominator = o_den * r_num
```

Reduce integers by GCD, require denominator > 0 and canonical zero `0/1`.
No Decimal division, binary64 conversion, rounding, percentages, epsilon, clipping,
absolute-value numerator, adjusted earnings or arbitrary minimum revenue threshold.
A tiny exact positive Revenue remains applicable; a negative Operating Income
produces a negative ratio. Hostile ambient Decimal context must not change results.

| Revenue | Operating Income | Result |
| --- | --- | --- |
| 100 | 20 | `AVAILABLE`, 1/5 |
| 100 | -20 | `AVAILABLE`, -1/5 |
| 100 | 0 | `AVAILABLE`, 0/1 |
| 0 | Any established finite amount | `NOT_APPLICABLE`, no ratio |
| -100 | Any established finite amount | `NOT_APPLICABLE`, no ratio |

This is Operating Income relative to the qualified reported Revenue concept, not
a universal operating margin, a profitability judgment or a normalized ratio.

## 5. Output, identities and lineage

The frozen result SHALL expose versions, route, analysis kind, native analytical
status/reasons, native upstream status/reasons, source CIK and target period when
known, accounting semantics, actual upstream semantic/evidence IDs, optional exact
rational, authority, fixed limitations and separate derived identities. It SHALL
not fabricate issuer/security keys or expose scores, weights, percentages, grades,
rankings, recommendations or portfolio fields. Full source observations and private
archive binding remain upstream, not duplicated into the analytical output.

Lineage SHALL be independently reconstructible:

```text
exact LIVE receipt + immutable object
→ exact extraction inventory + annual/common-filing adjudication
→ new native issuer qualification and its semantic/evidence IDs
→ new issuer diagnostic and its semantic/evidence IDs
```

Use separately domain-separated SHA-256 identities and exact deterministic canonical
serialization consistent with the upstream contract. Analytical semantic identity
binds route/contract/methodology/identity versions, analysis kind, analytical and
upstream states/reasons, source CIK, target period, accounting meaning, exact
Revenue and Operating Income when established, ratio when available, authority and
limitations. Bind the upstream semantic identity as well, including its material
conflict meaning. Original scalar facts may be identity inputs without becoming
duplicated public output fields.

Evidence identity binds exactly the analytical semantic identity and the actual
verified upstream evidence identity. Receipt IDs, timestamps, source-object hashes,
row order/locators, filing accession evidence and archive paths do not directly
enter analytical semantics. Archive paths never enter evidence identity either.

Consequences: recapture with unchanged qualified economics preserves semantic
identity and changes evidence identity; changed issuer, facts, period, capability
or material conflict changes semantics. Revenue/Operating Income `100/20` and
`200/40` remain semantically distinct although both ratios are 1/5. Equivalent
Decimal forms remain semantically equal. Route/version domains prevent collisions
with legacy diagnostics or research candidates even when amounts match.

## 6. Authority, limitations and isolation

The proposed authority permits only CURRENT issuer-level research diagnosis of
this exact relationship. The fixed limitation set SHALL explicitly deny:

- Ordinary Compounder eligibility, security-class admission, EPS comparability,
  corporate-action/share-basis and cross-period legal/accounting-subject continuity.
- Complete issuer filing coverage, absolutely newest-period claims, universal
  total-revenue completeness and cross-issuer/sector comparability.
- Normalized profitability, good/bad company Quality, aggregate Quality score,
  pricing power, moat, historical trend, Durability or persistence conclusions.
- Expected Return, Confidence changes, ranking, recommendation, allocation, sizing,
  investment admission, execution, production, deployment or V2 promotion.
- Publication-time knowledge, historical availability, PIT or `HISTORICAL_AS_OF` authority.

All limitations are mandatory; a caller cannot remove them. Existing PR4C3, PR5B,
PR5C v1, Ordinary Compounder v2 and Quality v1 behavior remain unchanged. Research
`CANDIDATE_COHERENT` remains research-only; no conversion/admission function is added.
New qualifications SHALL be rejected by legacy analyzers, and the new analyzer
SHALL reject legacy qualifications and research candidates. No generic framework,
new dependency, external service, paid source, model-rule change or aggregation.
V1 remains frozen, V2 challenger, tuning `PROPOSAL_ONLY`.

## 7. Future validation and approval gates

No tests or Python implementation are authorized by this phase. Later implementation
SHALL cover all [upstream adversarial and authentic-positive requirements](CURRENT_ANNUAL_ISSUER_REVENUE_OPERATING_INCOME_QUALIFICATION_V1.md)
and at least:

- Complete closed upstream-to-analytical state mapping; valid unavailable evidence
  versus programming/integrity failures, with no partially selected numerical output.
- Exact positive, negative, zero, tiny and large numerical cases, equal ratios from
  different facts, recurring rational values and hostile Decimal contexts.
- Fabricated exact-type objects with self-consistent hashes, changed nested facts,
  omitted newer evidence, wrong receipt, corrupt source after construction, missing
  binding, incompatible versions and detached/research/legacy type injection.
- Independent full source replay; matching identities are necessary but insufficient
  without capture verification. No network, mutation or clock dependence.
- Recapture and row-order identities, full provenance preservation, source-independent
  incidental archive paths and legacy type/behavior isolation in both directions.

Future targeted and adjacent regressions include the existing
[Revenue diagnostic tests](../../../../tests/test_current_annual_operating_income_to_positive_revenue.py),
[legacy foundation tests](../../../../tests/test_sec_current_annual_revenue_operating_income.py)
and [research surveillance tests](../../../../tests/test_sec_current_annual_reported_fact_research_candidate.py),
plus archive/receipt/extraction tests. Canonical preflight classifies the complete
future diff; run STANDARD or FULL_PIT as required using pinned runtime and locked
dependencies, never override stricter classification. Preserve
`MODEL_RULES_VERSION=2026-08-23-allocation-room-integrity-v7`, PIT
`f1e73b27b80e41d96ff5e0fe990b482bad71b7220db0b5bd6a2f470d72786166` and determinism
`f8457910665391e39c234274cae4c029802c681211eebc7dba986a63000876f1`.

Authentic-positive validation requires independently verified immutable LIVE capture,
native established issuer qualification and associated native AVAILABLE diagnostic,
with full source-to-result replay. Synthetic success alone is insufficient. No
such result is claimed in this draft.

The supplied `CONDITIONAL` design audit is not implementation approval. Independent
Architecture & Audit must review these proposed contracts, including the replay
binding, before the Program Manager obtains CEO contract approval and a separate
Phase-2 release. The October 11 Option A decision remains authoritative: a new
issuer-positive chain counts toward Stage-C exit only after an explicit CEO-approved
Option A supplement. Even then, closure and Stage-D transition remain separate CEO
decisions. This route is not an eighth diagnostic or automatic completion authority.

## 8. Resource assessment and Phase-1 handoff

EXISTING TECHNOLOGY & RESOURCE REUSE ASSESSMENT: REUSE existing exact rational
arithmetic/identity conventions; ADAPT only the independently replayed native input
boundary. See the [companion assessment and verified base](CURRENT_ANNUAL_ISSUER_REVENUE_OPERATING_INCOME_QUALIFICATION_V1.md).
No external adoption, new license, subscription, hardware, service or spending is
required by this proposed local design. Commercial source redistribution remains
unestablished, and new-route resource usage/Chromebook compatibility remain UNKNOWN.

Exactly the two new Markdown contracts are in scope. Source, tests, existing
contracts, governance/protected documents and model rules are out of scope.
Phase-1 validation is document/Git integrity and canonical preflight on the exact
candidate, expected DOCS_ONLY, with delivered tree equal to the validated snapshot.
No implementation tests, financial execution or authentic capture are run here.

After successful validation, commit/push/open the draft-contract PR targeting
`model-v2/expected-return-challenger`, report CI/mergeability as observed without
waiting and stop. Next action: independent Architecture & Audit review. No merge,
Phase-2 implementation, governance sync, Stage-C closure or authority promotion.
