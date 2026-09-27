# PR4D4C2 — Corroborate CURRENT SEC/Nasdaq registered-listing evidence

> **Cross-source corroboration is not durable economic identity, legal
> share-class identity, historical continuity, quote-currency authority, or
> final admission.**

## Approved base and scope

After `git fetch origin`, the approved integration branch
`origin/model-v2/expected-return-challenger` was exactly
`385b9842e425387df301202717aa29f53c068318`, tree
`2653028065ca564f9b32c6360f2cf86f99ef3747` (post-merged PR #56 / PR4D4C1).
The worktree and index were clean. Branch
`codex/v2-current-registered-listing-evidence-bridge` was created directly from
that verified commit; existing divergent and stale refs were preserved.

This PR adds one deterministic, read-only, SEC/Nasdaq-adapter-specific bridge.
It compares exact source claims already available from D4B/D3A, D4C1, and D2C.
It changes no upstream source contract, authority registry, Expected Return,
investment rule, runtime, V1, deployment, or production behavior.

Added:

- `economic_facts/sec_current_registered_listing_bridge.py`;
- `tests/sec_current_registered_listing_bridge_fixtures.py`;
- `tests/test_sec_current_registered_listing_bridge.py`;
- `EXPECTED_RETURN_PR4D4C2.md`.

Only narrow dependency-test allowlist changes are permitted if validation proves
they are required. `PAM_PROJECT_CONSTITUTION.md`, `PAM_ROADMAP.md`,
`DECISIONS.md`, `source_authority.py`, and every upstream evidence contract are
out of scope.

## Why this bridge exists

D4B establishes a D1 CURRENT boundary `T` and a T-bounded view of controlled
periodic-filing captures. D3A registered-security claims are nested inside those
captures. D4C1 independently replays SEC CIK/name/ticker/exchange source rows.
D2C independently replays Nasdaq Listed directory rows.

No input alone establishes economic identity. This bridge answers only:

> By the exact D1 CURRENT boundary `T`, did independently controlled source
> evidence agree that SEC filer CIK `C` and an eligible filing-local registered-
> security claim were associated with the same observed Nasdaq symbol `S`?

That is useful real evidence for a later qualifier. It is not the qualifier.

## Public API and closed request

```python
assess_sec_current_registered_listing_bridge(
    current_archive: SecArchive,
    submissions_archive: SecSubmissionsArchive,
    filing_archive: SecFilingArchive,
    ticker_exchange_archive: SecTickerExchangeArchive,
    nasdaq_listed_archive: NasdaqListedArchive,
    request: SecCurrentRegisteredListingBridgeRequest,
) -> SecCurrentRegisteredListingBridgeAssessment
```

The frozen/slotted request contains exactly:

- `temporal_boundary_request`;
- `sec_ticker_exchange_receipt_id`;
- `nasdaq_listed_receipt_id`.

It accepts no prebuilt assessment, D3A result, D4C1/D2C snapshot, caller CIK,
ticker, exchange, title, source scope, `T`, `as_of`, identity, continuity,
completeness, qualification, admission, price, currency, URL, bytes, callback,
clock, or success flag. The evidence discovers the candidate.

## Mandatory fresh replay chain

Every invocation freshly calls, in this adapter:

```text
assess_sec_property4_temporal_boundary(...)
replay_sec_ticker_exchange_snapshot(...)
replay_nasdaq_listed_snapshot(...)
```

D3A is consumed only from each D4B filing's
`controlled_captures_by_boundary`. No standalone caller D3A object and no
serialized hash or status label can bypass replay. Archive corruption,
unsupported upstream source structure, contract errors, and programming errors
propagate. Normal evidence absence and supported-profile gaps become explicit
bridge states.

The adapter performs no network request, write, directory discovery, implicit
acquisition, latest-receipt selection, or wall-clock read.

## The only temporal boundary

The only qualification boundary is:

```text
T = D4B.current_authority_boundary
```

A positive bridge requires D4B `BOUNDARY_EVIDENCE_ESTABLISHED` and non-null `T`.
The selected D4C1 and D2C receipts must each have `captured_at <= T`. Only D3A
claims inside D4B controlled captures by `T` can participate. Exact equality at
`T` is accepted.

Evidence captured after `T` remains inspectable in the retained upstream
snapshot but cannot supply a target match or repair the earlier assessment. No
`max(T, D4C1 capture, D2C capture)` boundary is created. Replaying a genuinely
later D1 boundary may produce a new positive assessment. Old assessment semantics
are immutable.

## Initial supported profile

The sole closed profile is:

`SEC_NASDAQ_REGISTERED_LISTING_BRIDGE_V1`

Its only reviewed exchange pair is:

```text
D3A exact source exchange text:  NASDAQ
D4C1 exact source exchange text: Nasdaq
```

This is an adapter profile, not a MIC or global venue resolver. There is no case
fold, substring match, punctuation stripping, fuzzy resolver, XNAS mapping,
NYSE/OTC/Other Listed support, ADR/ADS or wrapper inference, foreign-exchange
support, CUSIP/FIGI/ISIN/LEI mapping, or quote-currency qualification.

## D3A eligibility and discovery

For the initial profile a participating D3A assessment must be
`CAPTURED_REGISTERED_SECURITY_CLAIMS`. A participating claim has:

- no claim issues;
- exactly one nonempty title;
- exactly one trading symbol;
- no `NoTradingSymbolFlag`;
- exactly one exchange name;
- the upstream-verified entity CIK;
- a nonempty filing-local `source_security_scope_id`;
- the exact supported D3A exchange text.

`SOURCE_CONFLICT`, `INCOMPLETE_REGISTERED_SECURITY_CLAIMS`, and
`NO_SUPPORTED_REGISTERED_SECURITY_CLAIMS` are never repaired with D4C1 or D2C.
Missing values are never filled heuristically. The caller never supplies the
symbol.

Multiple equivalent pre/on-`T` filings can support one symbol bridge. Every
accession, filing receipt, temporal filing identity, D3A semantic/evidence
identity, and `(accession, source_security_scope_id)` pair remains preserved.
Originals and amendments remain independent evidence. There is no latest,
annual, first, majority, most-frequent, or closest-to-`T` winner.

Incompatible supported symbols or multiple distinct supported source scopes in
one filing fail closed. Filing-local scope IDs are never promoted to durable
PAM security, class, or listing IDs and are not assumed comparable across
filings.

## D4C1 exact target rules

For discovered source CIK `C` and symbol `S`, a target row must have:

- `normalized_sec_cik == C`;
- `source_ticker == S`;
- exact D4C1 exchange text `Nasdaq`.

Company name is retained only in the upstream source evidence and is never a
join key. The target must contain exactly one unique row semantic. Exact
duplicate occurrences of that same semantic are all preserved but do not
strengthen bridge semantics. More than one target semantic is ambiguous. If `S`
is associated with multiple CIKs in `ambiguous_tickers`, the target fails closed.

Ambiguity elsewhere in the D4C1 snapshot is diagnostic upstream evidence and
does not poison a locally unique target. Other tickers for the same CIK are not
chosen over the filing-discovered `S`.

## D2C exact target rules

D2C is already the Nasdaq Listed source. The bridge requires exactly one row
whose exact `Symbol` equals `S` and whose `Test Issue` is exactly `N`. A missing
symbol is incomplete. Any duplicate/conflicting target occurrence fails closed,
even if the rows are byte-equivalent.

An unrelated conflicting D2C symbol does not invalidate a unique target. The
bridge does not match or infer meaning from Security Name, Market Category,
Financial Status, Round Lot Size, ETF, or NextShares.

## No name matching and no D2B metadata

Qualification never compares D4C1 company name, D2C Security Name, or D3A title.
There is no fuzzy normalization, edit distance, abbreviation, suffix stripping,
or token similarity.

**No D2B parent metadata** ticker or exchange is consumed. D4B supplies no
dedicated T-partition for that parent metadata, so using it could leak a capture
made after `T`. D2B filing occurrences participate only through D4B/D4A as
already designed.

## Status and positive meaning

The closed assessment states are:

- `CURRENT_SOURCE_BRIDGE_ESTABLISHED`;
- `INCOMPLETE_SOURCE_BRIDGE`;
- `SOURCE_CONFLICT`;
- `CURRENT_AUTHORITY_UNAVAILABLE`;
- `UNSUPPORTED_SOURCE_PROFILE`;
- `NO_SUPPORTED_REGISTERED_LISTING_CANDIDATE`.

`CURRENT_SOURCE_BRIDGE_ESTABLISHED` means only that, by exact D1 boundary `T`:

1. PAM controlled the filing bytes for an eligible D3A claim;
2. the claim associated CIK `C`, source title, symbol `S`, and the closed Nasdaq
   profile;
3. a controlled D4C1 capture by `T` contained one unambiguous target
   `C ↔ S ↔ Nasdaq` source association;
4. a controlled D2C capture by `T` contained one non-test target symbol row;
5. no target-level contradiction was found in this reviewed evidence.

It does not mean that CIK or symbol is a global/durable identifier; that a title
proves legal rights; that the sources share an independent durable security ID;
that a MIC, wrapper, quote currency, quote unit, listing-effective interval,
complete inventory, or continuity exists; or that admission is granted.

## Deterministic identity

Domain-separated SHA-256 uses:

`pam:sec-current-registered-listing-bridge:{domain}:v1`

Candidate semantic identity binds only the closed contract/profile, exact CIK
and symbol, set-canonicalized D3A title and filing-local scope evidence, supporting
target row semantics, status, and issues. Repeating the same relationship in
another filing does not by itself strengthen that candidate meaning. Candidate
semantics exclude accessions, supporting filing/D3A identities, capture
timestamps, receipt IDs, paths, environment, object identity, and input ordering.

Assessment semantic identity additionally binds exact `T`, D4B semantics,
candidate semantics, status, and issues. Unrelated upstream duplicate/conflict
multiplicity cannot strengthen target meaning.

Evidence identity additionally binds exact D4B evidence, full selected D4C1/D2C
snapshot evidence, every supporting D3A and temporal-filing evidence identity,
filing receipt, target occurrence, and capture timestamp through those upstream
identities. Equivalent duplicate evidence can change evidence identity without
changing bridge semantics.

## Authority, Property 4, and nonclaims

No `AuthorityProperty`, source route, or provider-wide trust is added. The
`SEC_COMPANYFACTS_LIVE_CURRENT_V1` route is unchanged. This module does not
import `security_identity.py`, and no upstream blocker is weakened.

There is **no quote currency**, quote unit, MIC, durable economic identity,
share-class rights qualification, listing-effective interval, continuity,
Property-4 success flag, final admission, Expected Return input, model score,
allocation, runtime consumer, V1 change, deployment, or V2 promotion.

| Property | State after PR4D4C2 |
| --- | --- |
| 4A | Unresolved — source CIK corroboration is not issuer economic identity. |
| 4B | Unresolved — ticker/title corroboration is not durable security identity. |
| 4C | Unresolved — no legal/economic share-class identity or rights. |
| 4D | Unresolved — no complete relevant common-class inventory. |
| 4E | Unresolved — no EPS applicability or entitlement qualification. |
| 4F | Unresolved — no qualified listing, quote currency, or quote unit. |
| 4G | Unresolved — no complete/scoped listing inventory. |
| 4H | Unresolved — CURRENT capture-by-boundary is not historical continuity. |

**Obligations 5–7 remain unresolved**: share-basis comparability,
accounting/reporting-subject comparability, and final economic admission.

## Validation

Validation used fictional, offline evidence through the unchanged isolated test
runner with disposable code/state/HOME, stripped credentials, and denied network.
Python was 3.12.14 against the unchanged repository pin 3.12.13. No dependency,
lockfile, runtime, or model setting changed. No live source, positive-capital
analysis, expectation regeneration, or production operation was performed.

The 30-test D4C2 suite covers request closure and fresh replay, exact `T`
partitioning, D3A eligibility, exact finite profile matching, local D4C1/D2C
ambiguity, multiple filings and amendments, no-winner conflict behavior,
deterministic identities, archive/error propagation, and dependency/authority
isolation.

Completed isolated selections:

| Selection | Tests | Result / seconds |
| --- | ---: | --- |
| `test_sec_current_registered_listing_bridge.py` | 30 | PASS / 1.281 |
| `test_sec_*.py` | 619 | PASS / 10.846 |
| `test_nasdaq_listed_*.py` | 89 | PASS / 2.183 |
| `test_*authority.py` | 44 | PASS / 0.289 |
| `test_security_identity.py` | 84 | PASS / 1.327 |
| `test_expected_return*.py` | 144 | PASS / 1.538 |
| `test_runtime_isolation.py` | 29 | PASS / 49.179 |
| `test_validation_identity_isolation.py` | 19 | PASS / 0.605 |
| `test_pr2_investment_equivalence.py` | 1 | PASS / 0.277 |
| Complete isolated suite | **2,178** | **PASS / 719.152** |

The complete suite reported no failures or skips and exercised D4B, D4A, D3A,
D4C1, D2C, adjacent D2A/D2B SEC layers, CURRENT/source authority, synthetic
identity boundaries, Expected Return boundaries, runtime and validation
isolation, and investment equivalence. It reproduced all 64 protected PIT
equivalence scenarios and both protected fingerprints without regeneration.

Protected expectations remain unchanged:

- PIT: `f1e73b27b80e41d96ff5e0fe990b482bad71b7220db0b5bd6a2f470d72786166`;
- Determinism: `f8457910665391e39c234274cae4c029802c681211eebc7dba986a63000876f1`;
- Model rules: `2026-08-23-allocation-room-integrity-v7`.

Final whitespace, staged-diff, committed-HEAD, remote-base, and clean-worktree
checks are completed during publication. The exact implementation HEAD/tree,
changed-file list, and PR URL are reported in the published handoff.

## Next handoff

The next chantier requires a **separately reviewed** decision about the evidence
needed to move from this corroborated CURRENT source bridge to actual real
economic issuer/security/share-class/listing qualification. Possible evidence
classes include a durable entity anchor, durable security/share-class anchor,
legal rights qualifier, or independent exchange/security identifier. This PR
does not choose or pre-authorize that source, contract, merge, deployment, or
promotion.
