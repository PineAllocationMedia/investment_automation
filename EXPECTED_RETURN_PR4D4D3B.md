# PR4D4D3B — Temporal common-stock source correspondence series

> A time-ordered series of filing-local source correspondences is not durable
> class continuity, economic security identity, ticker permanence, proof that no
> corporate action occurred, Property 4C/4H resolution, or admission.

## Approved base and scope

After `git fetch origin`, the approved integration branch
`origin/model-v2/expected-return-challenger` was exactly
`b8cb04e62d3faa36d4eed7409f28bcdc5a9f5573`, tree
`3037df6b42dfa702de2f3f490155a9b0e185419e` (post-merged PR #61 /
PR4D4D3A). The worktree and index were clean. Branch
`codex/v2-sec-temporal-common-stock-source-series` was created directly from
that verified remote commit; the prior local D4D3A branch and all other refs
were preserved.

This PR adds one deterministic, read-only downstream D4D3B adapter:

- `economic_facts/sec_temporal_common_stock_source_series.py`;
- `tests/sec_temporal_common_stock_source_series_fixtures.py`;
- `tests/test_sec_temporal_common_stock_source_series.py`;
- `EXPECTED_RETURN_PR4D4D3B.md`.

Existing tests may receive only narrow dependency-boundary allowlist entries for
this new downstream consumer. No upstream production module, source authority,
Expected Return, investment rule, runtime, V1, roadmap, decision log, dependency,
deployment, or production behavior changes.

## Purpose and exact question

D4D3B composes multiple independently replayed D4D3A filing-local source
correspondences into a deterministic sequence under one exact CURRENT boundary.
It answers only:

> Across the explicitly selected controlled filing receipts observed by PAM by
> the same CURRENT boundary `T`, what independently established D4D3A common-
> stock source correspondences exist, in SEC source-acceptance order, and which
> directly observed source features remain stable or vary?

It does not answer whether the observations are the same legal/economic class,
whether a ticker permanently identifies a class, whether continuity was
uninterrupted, whether rights remained effective, or whether a corporate action
occurred.

```text
TEMPORAL SERIES OF SOURCE CORRESPONDENCE
!= durable class continuity
!= economic security identity
!= absence of corporate actions
!= ticker permanence
!= legal-right continuity
!= Property 4C resolution
!= admission
```

## Public API and bounded explicit request

```python
assess_sec_temporal_common_stock_source_series(
    current_archive: SecArchive,
    submissions_archive: SecSubmissionsArchive,
    filing_archive: SecFilingArchive,
    ticker_exchange_archive: SecTickerExchangeArchive,
    nasdaq_listed_archive: NasdaqListedArchive,
    request: SecTemporalCommonStockSourceSeriesRequest,
) -> SecTemporalCommonStockSourceSeriesAssessment
```

The frozen/slotted request contains exactly:

- `registered_listing_bridge_request: SecCurrentRegisteredListingBridgeRequest`;
- `rights_claims_requests: tuple[SecSection12RightsSourceClaimsRequest, ...]`.

The rights-request tuple must contain 2–32 exact requests and every filing
receipt ID must be unique. Caller order has no semantics. The request has no
caller CIK, accession, title, ticker, class, source scope, identity, boundary,
continuity flag, earliest/latest selector, prebuilt assessment, bytes, URL,
callback, clock, qualification, or admission assertion.

The initial profile remains limited to observations that individually satisfy
the existing D4D3A/D4C2 SEC–Nasdaq CURRENT profile. It is not a general ticker-
change or continuity engine. Unsupported or incompatible evidence fails closed;
that limitation is not evidence that no ticker or class change occurred.

## Mandatory fresh replay and one exact T

Every call freshly invokes D4C2 exactly once for the common request, then
constructs and freshly invokes one D4D3A request for every explicit rights
request. No prebuilt D4C2 or D4D3A assessment can bypass replay.

The common D4C2 assessment must be `CURRENT_SOURCE_BRIDGE_ESTABLISHED` with
exactly one positive candidate. Every positive D4D3A replay must agree exactly
with that common replay on:

- D4C2 semantic identity;
- D4C2 evidence identity;
- `current_authority_boundary`;
- successful D4C2 candidate semantic identity; and
- successful D4C2 candidate evidence identity.

Any disagreement is a source conflict. Every selected observation must itself
be `CURRENT_SOURCE_CLASS_BRIDGE_ESTABLISHED` with exactly one positive D4D3A
candidate. A candidate is never cherry-picked from a non-positive assessment.

There is exactly one boundary:

```text
T = common fresh D4C2.current_authority_boundary
```

D4D3B creates no per-observation boundary, `max(capture)`, latest-filing time,
historical-availability time, or wall-clock time.

## Source-event chronology

For each positive D4D3A candidate, the exact accession must occur exactly once
in `D4C2.temporal_boundary.filings`, and every selected receipt for that
observation must occur in the filing's `controlled_captures_by_boundary`.

Only D4B `source_acceptance_events` whose relation is
`ON_OR_BEFORE_CURRENT_BOUNDARY` supply ordering. Exactly one distinct exact
`acceptance_timestamp` is required per accession-level observation. Zero is
incomplete chronology; multiple exact timestamps are ambiguous source
chronology and a conflict.

Canonical ordering is:

1. parsed exact source acceptance timestamp;
2. exact accession;
3. semantic observation identity.

Receipt `captured_at`, caller order, filename, ticker, heading order, and wall
clock never order observations.

The acceptance timestamp retains only its upstream D4B meaning. It is not called
publication time, public-availability time, effective time, rights-effective
time, or `known_by` time.

## Same-accession recaptures

Multiple selected receipts may refer to one accession. D4D3B groups them before
counting temporal observations.

- Identical D4D3A candidate semantics form one semantic observation. Every
  receipt and evidence identity remains preserved; recapture does not increase
  the distinct-accession count.
- Different D4D3A candidate semantics for one accession produce
  `SAME_ACCESSION_SEMANTIC_CONFLICT`. Competing semantic/evidence identities are
  retained; no latest, earliest, majority, or capture-time winner is selected.

An equivalent recapture preserves observation semantics while enriching its
evidence identity.

## Temporal observation record

The frozen/slotted observation retains, as source evidence:

- exact SEC acceptance timestamp(s), accession, source CIK and source symbol;
- canonical source-label evidence, exact D3A titles and opaque suffixes;
- exact D4D2B headings and filing-local D3A/D4D2B scope IDs;
- D4D3A candidate and assessment semantic/evidence identities;
- every selected filing receipt;
- D4D2B rights assessment, passage semantic/evidence and source-topic evidence;
- cross-observation descriptive passage signatures derived only from exact
  passage text hashes, structural kinds, lexical topics/anchors, and issues;
- D4B temporal-filing identities and acceptance-event occurrence IDs; and
- observation status and issues.

It contains no `class_id`, `security_id`, `economic_class_id`,
`durable_class_id`, `continuity_id`, `same_class`, `ticker_permanent`, or
`rights_effective` field.

## Descriptive source signals only

For a complete positive series, the closed descriptive signal set is:

- `CANONICAL_CLASS_LABEL_STABLE`;
- `EXACT_D3A_TITLE_VARIATION`;
- `D3A_TITLE_SUFFIX_VARIATION`;
- `EXACT_D4D2B_HEADING_VARIATION`;
- `RIGHTS_PASSAGE_SEMANTICS_VARIATION`;
- `RIGHTS_TOPIC_SET_VARIATION`.

Signals report only direct source-level stability or variation. Same symbol
creates no signal and no durable identity rule.

For example, two exact titles that both canonicalize to `CLASS A COMMON STOCK`
may produce `CANONICAL_CLASS_LABEL_STABLE` while a changed opaque par-value
suffix produces `D3A_TITLE_SUFFIX_VARIATION`. D4D3B does not interpret the
variation as a split, recapitalization, amendment, entitlement change, or a
different/same economic class. Changed rights-passage source semantics may be
reported, but the adapter does not decide whether legal rights changed.

## Positive meaning, sample limits, and no continuity claim

`CAPTURED_TEMPORAL_COMMON_STOCK_SOURCE_SERIES` requires at least two distinct
accessions, each with an independently positive D4D3A source correspondence,
unambiguous D4B acceptance chronology, controlled receipt evidence by the same
`T`, and no selected failure. Two recaptures of one accession are insufficient.

This status means only that PAM has an ordered explicit sample of at least two
filing-local source correspondences. The selected sample and D2B reference
closure do not prove all economically relevant events were observed, that no
charter amendment, merger, reclassification, conversion, split, reverse split,
redemption, recapitalization, designation change, or ticker change occurred, or
that no unselected filing mattered.

Stable observations are not gap-free continuity. Same canonical source label is
not the same legal class. Same ticker is not durable identity. Source variation
is not a corporate-action inference. This PR has no corporate-action authority.

## Deterministic identities

Domain-separated SHA-256 uses:

```text
pam:sec-temporal-common-stock-source-series:{domain}:v1
```

Observation semantics bind the contract/profile, source acceptance chronology,
accession, source CIK/symbol, source title/heading/scope/passage/topic semantics,
D4D3A candidate semantics, D4B temporal-filing semantics, status, and issues.
Observation evidence additionally binds every equivalent recapture receipt,
D4D3A evidence identity, rights/passage evidence, D4B temporal-filing evidence,
and source-event occurrence ID.

Series semantics bind the common D4C2 semantics, exact `T`, set-canonicalized
D4D3A assessment semantics, ordered observation semantics, descriptive signals,
status, and issues. Series evidence additionally binds common D4C2 evidence,
every selected D4D3A evidence identity, and ordered observation evidence.

Caller permutation, filesystem path, environment, wall clock, randomness, and
object identity enter neither identity. Equivalent same-accession recapture
preserves observation and series semantics while enriching evidence.

## Authority, Property 4, and remaining obligations

No `AuthorityProperty`, source route, provider-wide trust, Expected Return
input, Quality/Durability/Confidence fact, portfolio/allocation logic, admission
logic, runtime consumer, V1 behavior, deployment, production authority, or V2
promotion is added. `source_authority.py` and `MODEL_RULES_VERSION` are unchanged.

| Property | State after PR4D4D3B |
| --- | --- |
| 4A | Unresolved — source CIK is not economic issuer identity. |
| 4B | Unresolved — ordered source correspondence is not durable security identity. |
| 4C | Unresolved — source-label stability/variation is not legal/economic class identity or rights qualification. |
| 4D | Unresolved — the explicit selected sample is not a complete relevant class inventory. |
| 4E | Unresolved — no EPS applicability or entitlement qualification. |
| 4F | Unresolved — no qualified listing, quote currency, or quote unit. |
| 4G | Unresolved — no complete/scoped listing inventory. |
| 4H | Unresolved — ordered observations do not prove uninterrupted continuity. |

**Obligations 5–7 remain unresolved**: share-basis comparability,
accounting/reporting-subject comparability, and final economic admission.

## Validation

Validation uses invented offline evidence and the unchanged isolated runner. It
covers request closure and bounds, fresh D4C2/D4D3A replay, exact replay
agreement, upstream fail-closed states, one exact `T`, controlled receipt
membership, exact acceptance-event chronology, deterministic ordering,
same-accession recaptures/conflicts, field preservation, descriptive signals,
identity determinism/sensitivity, path and caller-order invariance, no network,
writes, clocks, scans or latest selection, dependency direction, authority/model
isolation, adjacent layers, the complete suite, and protected fingerprints.

No live provider request, positive-capital analysis, protected-expectation
regeneration, deployment, merge, or production operation is performed.

Python was 3.12.14 against the unchanged repository pin 3.12.13. Completed
isolated selections:

| Selection | Tests | Result / seconds |
| --- | ---: | --- |
| `test_sec_temporal_common_stock_source_series.py` | 23 | PASS / 1.506 |
| `test_sec_*.py` | 762 | PASS / 10.300 |
| `test_nasdaq_listed_*.py` | 89 | PASS / 1.698 |
| `test_*authority.py` | 44 | PASS / 0.154 |
| `test_security_identity.py` | 84 | PASS / 0.658 |
| `test_expected_return*.py` | 144 | PASS / 0.768 |
| `test_runtime_isolation.py` | 29 | PASS / 25.680 |
| `test_validation_identity_isolation.py` | 19 | PASS / 0.330 |
| `test_pr2_investment_equivalence.py` | 1 | PASS / 0.128 |
| Complete isolated suite | **2,318** | **PASS / 432.099** |

The complete suite reported no failures or skips and exercised all 64 protected
PIT equivalence scenarios. Dependencies and `requirements.lock` are unchanged.

Protected expectations remain:

- PIT: `f1e73b27b80e41d96ff5e0fe990b482bad71b7220db0b5bd6a2f470d72786166`;
- determinism: `f8457910665391e39c234274cae4c029802c681211eebc7dba986a63000876f1`;
- model rules: `2026-08-23-allocation-room-integrity-v7`.

Final executable test counts/timings, HEAD/tree, whitespace checks, and PR URL are
recorded in the published implementation handoff.

## Next handoff

D4D3B does not pre-authorize another implementation. Review this temporal
source-evidence output before choosing the next identity step. A likely future
requirement is a separately controlled corporate-action/security-transition
evidence layer able to observe explicit reclassifications, splits, conversions,
mergers, redemptions, recapitalizations, or security-designation changes before
source stability can be interpreted as durable class continuity. The alternative
future path remains narrowly reviewed legal-right value extraction from D4D2B
passages. Neither path is authorized here.
