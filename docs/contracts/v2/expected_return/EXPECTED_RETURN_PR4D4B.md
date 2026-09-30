# PR4D4B — Bind SEC Property-4 temporal dossier to CURRENT authority boundary

> This contract establishes only which exact periodic-filing bytes PAM had
> controlled-captured no later than a freshly replayed D1 CURRENT boundary. It
> does not establish publication, public availability, historical completeness,
> economic identity, continuity, Property 4H, or final admission.

## Approved base and scope

After `git fetch origin`, `origin/model-v2/expected-return-challenger` was exactly
`621997f4da0aa4aaa294a461996111ad14faf7d7`, tree
`25c9c4fefe6863931e3db26485248c3f5f4fb868` (post-merged PR #54). The worktree
and index were clean. Branch `codex/v2-sec-temporal-boundary-qualification` was
created directly from that remote commit; divergent and stale refs were preserved.

This PR adds a deterministic, read-only adapter joining the D1 controlled SEC
Companyfacts CURRENT evidence replay to the D4A exact SEC Property-4 temporal
dossier replay. It changes no upstream acquisition, extraction, resolution,
authority, dossier, synthetic identity, Expected Return, model, runtime, V1,
deployment, or Chromebook behavior.

Added:

- `economic_facts/sec_property4_temporal_boundary.py`
- `tests/sec_property4_temporal_boundary_fixtures.py`
- `tests/test_sec_property4_temporal_boundary.py`
- `EXPECTED_RETURN_PR4D4B.md`

Existing-file changes, if required, are limited to test-only dependency allowlists.

## Public API and exact request closure

```python
assess_sec_property4_temporal_boundary(
    current_archive: SecArchive,
    submissions_archive: SecSubmissionsArchive,
    filing_archive: SecFilingArchive,
    request: SecProperty4TemporalBoundaryRequest,
) -> SecProperty4TemporalBoundaryAssessment
```

The frozen/slotted request has exactly:

- `current_request: SeriesResolutionRequest`;
- `parent_submissions_receipt_id`;
- tuple `child_submissions_receipt_ids`;
- tuple `filing_receipt_ids`.

The selectors inherit the exact D1 and D4A validation contracts. The request has
no prebuilt assessment or dossier, caller boundary, separate CIK, ticker,
security/class/listing ID, continuity, completeness, qualification, publication,
availability, D2C snapshot, price, currency, model input, callback, clock, URL,
or source bytes.

## Mandatory internal replay and CIK join

The adapter first calls `assess_sec_current_evidence` with the exact D1 request.
It then constructs a fresh D4A request and calls
`build_sec_property4_temporal_dossier`. Serialized success labels, hashes, and
caller-built output objects cannot bypass either replay.

D1 remains authoritative for its own validation. D4B checks only the core typed
relationship it consumes: successful evidence must be CURRENT, resolved, LIVE,
capture-bound, and internally agree on its boundary; unavailable D1 results must
have no boundary or established claims. Normal D1 unavailability becomes
`CURRENT_AUTHORITY_UNAVAILABLE`; archive, source, contract, and programming
failures propagate.

After both replays, D4A `source_cik` must exactly equal D1
`request.current_request.cik`. A mismatch is an invalid explicit selection and
raises `SecProperty4TemporalBoundaryRequestError`. There is no fuzzy name,
ticker, accession-prefix, or D2C-assisted join.

## The only boundary and the separate clocks

The only `T` is:

```text
D1.current_authority.current_authority_boundary
= D1.observed_available_by
= controlled Companyfacts receipt capture bound
```

No wall clock, D2B source date, D2A capture, latest filing, D2C snapshot, or
caller value can create or advance `T`.

The clocks retain their exact meanings:

| Field | Meaning |
| --- | --- |
| D1 `current_authority_boundary` | controlled Companyfacts capture bound |
| D2A `captured_at` | time PAM controlled-captured those exact filing bytes |
| D2B `acceptanceDateTime` | SEC source acceptance timestamp |
| D2B `filingDate` | source filing-date assertion |
| D2B `reportDate` | source report/period-date assertion |

Explicitly:

```text
acceptanceDateTime != publication
acceptanceDateTime != public availability
filingDate != availability
reportDate != availability
captured_at != original publication
D1 T != historical filing publication timestamp
```

D1 publication remains `UNKNOWN`.

## Capture-by-boundary semantics and T-bounded view

For each D4A accession, the adapter retains exact D2B occurrences, exact source
acceptance timestamps, the D4A semantic/evidence identities, every D2A capture,
and upstream issues. It partitions captures without choosing a winner:

- `captured_at <= T`: `controlled_captures_by_boundary`;
- `captured_at > T`: `post_boundary_captures`;
- when D1 is unavailable: `unclassified_captures`.

`CONTROLLED_CAPTURE_BY_BOUNDARY` means only that PAM possesses at least one exact
controlled D2A capture for the filing semantic no later than `T`. It does not mean
published by, publicly available by, PIT-authoritative, identity-qualified,
continuous, or historically complete.

The output exposes source events on/before `T`, source events after `T`, captures
after `T`, and gaps at `T`. A genuinely later source event is preserved and
excluded from the T-bounded view; its existence is not itself a conflict. An
acceptance timestamp on/before `T` without a D2A capture by `T` is insufficient.
Filing and report dates never substitute for capture time.

The derived series horizon start/end is inspection context only. It is not an
effective interval and conveys no continuous identity or event-free coverage.

## Recaptures, chronology, and no future-evidence leakage

Identical-byte recaptures preserve every exact receipt in evidence identity. One
pre/on-boundary capture is sufficient for the narrow semantic claim; capture
multiplicity does not strengthen semantics. Post-boundary recaptures remain
visible and cannot retroactively repair a gap at `T`. A separately replayed later
D1 boundary can produce a distinct assessment that includes such a capture.

D4A differing-byte conflicts remain `SOURCE_CONFLICT`; there is no earliest,
latest, pre-boundary, or majority winner.

D4B checks only the possible local chronology:

```text
SEC source acceptance timestamp <= controlled filing capture timestamp
```

A capture that precedes its source acceptance timestamp is an internal chronology
conflict. This check does not equate acceptance with publication or availability.

## Statuses, issues, and precedence

Closed assessment statuses are:

- `BOUNDARY_EVIDENCE_ESTABLISHED`;
- `INCOMPLETE_BOUNDARY_EVIDENCE`;
- `SOURCE_CONFLICT`;
- `CURRENT_AUTHORITY_UNAVAILABLE`;
- `NO_RELEVANT_PERIODIC_FILINGS`.

Closed issue categories distinguish D1 unavailability, D4A incompleteness,
D4A conflict, no capture by `T`, source acceptance after `T`, impossible
capture-before-acceptance chronology, and no relevant periodic filings.

D4A `SOURCE_CONFLICT`, `INCOMPLETE_TEMPORAL_EVIDENCE_DOSSIER`, and
`NO_RELEVANT_PERIODIC_FILINGS` retain their distinct D4B outcomes. Chronology
conflict is fail-closed. D1 normal unavailability applies when no stronger D4A
state prevents assessment. Only D4A `CAPTURED` plus valid D1 permits boundary
evaluation.

`BOUNDARY_EVIDENCE_ESTABLISHED` means only: all relevant periodic filing
occurrences in the explicitly replayed D2B reference set whose source event is
on/before `T` have at least one nonconflicting exact controlled D2A capture by
`T`; later source events are excluded. It grants no inventory completeness or
continuity.

## Reference closure limitation

**Reference closure is not historical completeness.** It is also not filing-
history completeness, corporate-action completeness, economic-event
completeness, listing-history completeness, or coverage through `T`.

Even a positive boundary state means only that all relevant periodic filing
occurrences in the explicitly replayed D2B reference set have the required
T-bounded capture evidence. It does not say “history complete through T.”

## Semantic and evidence identity

Domain-separated SHA-256 identities use
`pam:sec-property4-temporal-boundary:{domain}:v1`.

Semantic identity binds the contract, D1 semantic hash, exact D1 boundary, D4A
semantic identity, source CIK, derived series horizon, per-accession semantic
boundary classifications, stable issues, and status. Equal semantic recaptures
are set-canonicalized so multiplicity does not strengthen meaning.

Evidence identity additionally binds D1 evidence hash, D4A evidence identity,
exact D2B occurrence IDs, qualifying/post-boundary/unclassified D2A receipt and
capture evidence, content hashes, capture timestamps, and upstream evidence
identities. Request order is canonicalized. Paths, environment, object IDs,
randomness, and implicit time enter neither identity.

## Explicit authority boundaries

No D2C object or `nasdaq_listed_snapshot.py` is consumed. D2C has no CIK or
durable historical identity authority. No synthetic identity object or
`security_identity.py` qualifier is imported. Filing-local source scopes are not
translated into economic issuer, security, class, listing, or symbol continuity.

No `AuthorityProperty` is added or changed. No source route is added, and
`SEC_COMPANYFACTS_LIVE_CURRENT_V1` retains only its existing powers. D4B is not a
source-authority grant. D1, D4A, D3A/D3B, D2A/D2B, C4–C6, and their published
identities are unchanged.

| Property | State after PR4D4B |
| --- | --- |
| 4A | Unresolved — source CIK is not issuer economic identity. |
| 4B | Unresolved — filing evidence is not durable economic security identity. |
| 4C | Unresolved — source members/text do not prove legal/economic class identity or rights. |
| 4D | Unresolved — replayed occurrences do not prove complete relevant class inventory. |
| 4E | Unresolved — filing contexts do not prove EPS applicability or entitlement. |
| 4F | Unresolved — source claims do not qualify listing, quote currency, or quote unit. |
| 4G | Unresolved — evidence does not prove a complete/scoped listing inventory. |
| 4H | Unresolved — capture-by-boundary is not economic security/listing continuity. |

**Obligations 5–7 remain unresolved**: share-basis comparability,
accounting/reporting-subject comparability, and final economic admission.

There is no Expected Return, C4/C5/C6 real-authority, score, allocation, model,
runtime, V1, deployment, or Chromebook consumer or change.

## Validation

Validation uses fictional offline evidence and the isolated repository runner.
Python was 3.12.14 against the unchanged repository pin 3.12.13. Dependencies and
lockfiles were not changed. No live provider request or positive-capital analysis
was performed.

| Isolated selection | Tests | Result / seconds |
| --- | ---: | --- |
| `test_sec_property4_temporal_boundary.py` | 28 | PASS / 0.643 |
| `test_sec_property4_temporal_dossier.py` | 30 | PASS / 1.309 |
| `test_sec_current_evidence.py` | 41 | PASS / 1.214 |
| `test_sec_submissions_*.py` | 101 | PASS / 2.621 |
| `test_sec_filing_*.py` | 74 | PASS / 2.050 |
| `test_sec_registered_securities.py` | 73 | PASS / 1.661 |
| `test_sec_class_eps_claims.py` | 44 | PASS / 1.023 |
| `test_sec_*.py` | 542 | PASS / 9.237 |
| `test_*authority.py` | 44 | PASS / 0.225 |
| `test_security_identity.py` | 84 | PASS / 1.137 |
| `test_expected_return*.py` | 144 | PASS / 1.195 |
| `test_runtime_isolation.py` | 29 | PASS / 45.964 |
| `test_validation_identity_isolation.py` | 19 | PASS / 0.602 |
| `test_pr2_investment_equivalence.py` | 1 | PASS / 0.178 |
| Complete isolated suite | **2,098** | **PASS / 751.840** |

The complete suite reported no failures or skips, exercised all 64 PIT
equivalence scenarios, and reproduced both protected fingerprints without
regenerating expectations. Final whitespace, staged-diff, committed-HEAD,
remote-base, and clean-tree checks are completed during publication.

Protected expectations remain:

- PIT: `f1e73b27b80e41d96ff5e0fe990b482bad71b7220db0b5bd6a2f470d72786166`
- Determinism: `f8457910665391e39c234274cae4c029802c681211eebc7dba986a63000876f1`
- Model rules: `2026-08-23-allocation-room-integrity-v7`

## Next handoff

The next bottleneck is a **separately reviewed** real identity/listing bridge that
can evidence anchors from economic issuer to economic security, share class, and
listing/wrapper without ticker-only matching. This PR does not pre-authorize that
contract, Property 4H qualification, D2C linkage, merge, deployment, or promotion.
