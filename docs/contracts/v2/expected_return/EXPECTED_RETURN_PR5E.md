# PR5E — Final admission and real Expected Return adapter

> PR5E is the unique final admission boundary for the first bounded real route.
> It remains diagnostic challenger infrastructure and grants no V1, production,
> recommendation, allocation, execution, deployment, or promotion authority.

## Verified base and scope

| Item | Verified value |
| --- | --- |
| Canonical branch | `origin/model-v2/expected-return-challenger` |
| Base commit | `bfdb84b1222a0b7c11571700cd03c63e495fad17` |
| Base tree | `69a93587c93fa28dc1ecf7f6bdb22acc3e3452c3` |
| Implementation branch | `codex/v2-pr5e-real-expected-return-adapter` |

The starting worktree and index were clean. Existing divergent local refs were
preserved. PR5E does not modify PR5D2 or any upstream economic/source module.

## One public boundary

```python
admit_real_expected_return_pr5e(
    current_archive,
    submissions_archive,
    filing_archive,
    ticker_exchange_archive,
    nasdaq_listed_archive,
    quote_archive,
    split_history_archive,
    request,
) -> PR5EAdmissionResult
```

The closed request contains the exact `PR5D2RealExpectedReturnRootsRequest` and
expected PR5D2 semantic/evidence identities. The function accepts no detached
PR5D2 result, caller-authored `as_of`, qualification boolean, same-basis
assertion, policy object, provenance object, or caller-generated fact.

Every call freshly executes `assemble_expected_return_pr5d_bundle()`. Expected
PR5D2 semantic/evidence identity mismatch is `SOURCE_CONFLICT` even if a replay
otherwise looks usable.

Closed PR5E statuses are:

- `REAL_EXPECTED_RETURN_ADMITTED`;
- `UNAVAILABLE`;
- `UNSUPPORTED`; and
- `SOURCE_CONFLICT`.

PR5D2 `PR5D_REAL_ROOTS_ESTABLISHED` alone may continue. Upstream unavailable,
unsupported, and conflict states preserve their meaning. PR5E never weakens an
upstream failure to obtain a calculation.

## Exact supported route and facts

The positive route is the PR5D2 free SEC + Yahoo route for one route-local
selected ordinary common class, five comparable positive annual diluted-EPS
observations, an action-aware quote-to-EPS basis bridge, verified nonpayer
status, `ORDINARY_COMPOUNDER` methodology applicability, and the pinned approved
policies.

It creates exactly these PR4B1 roots:

```text
1 ObservedPrice
5 ReportedDilutedEPS
1 VerifiedNonpayer
1 ProfileQualification
```

It creates no `OrdinaryAnnualDividend`. The payer route remains unsupported.
Missing, conflicting, or structurally unsupported evidence remains closed.

The PR4B1 `security_id` is exactly PR5D2's `route_local_security_key`; the share
class is exactly the canonical selected common class. Neither value is promoted
to a universal security, ticker, CUSIP-like, issuer-wide, or global class
identity.

`ProfileQualification` means only that the existing ordinary-company EPS,
payout, and terminal-P/E methodology is structurally applicable. It is not a
Quality, Durability, management, growth, ranking, recommendation, or valuation
claim.

## Deterministic admitted share basis

The PR5E admitted share-basis identity is a domain-separated SHA-256 identity
that binds at least:

- PR5E contract and adapter versions;
- route-local security key and canonical selected common class;
- historical qualified basis identity;
- basis-bridge semantic and evidence identities;
- admitted quote semantic and evidence identities;
- exact bridge multiplier numerator and denominator;
- route inventory semantic/evidence identities;
- recent SEC share-basis semantic/evidence identities;
- Yahoo split-history semantic/evidence identities; and
- every reconciled corporate-action record and its retained source identities.

This is an evidence-bound identity for the reviewed route. It does not broaden
PR5D2's `BOUNDED_FREE_SOURCE_CONTINUITY_ONLY` conclusion or claim universal
corporate-action completeness.

## EPS and price adaptation

Each retained PR5C EPS value crosses the binary64 boundary exactly once:

```text
exact Decimal
-> exact Fraction
-> exact multiplication by PR5D2 numerator/denominator
-> float at the PR5E boundary
```

PR5C values are not mutated. No rounding, discretionary normalization, adjusted
EPS substitution, or intermediate float conversion occurs. All five exact
periods and their upstream lineage remain bound into the admitted facts.

The final conversion is also an explicit availability boundary. Conversion
overflow, a non-finite result, or positive-source underflow to `0.0` returns
PR5E `UNAVAILABLE` with
`EPS_BINARY64_REPRESENTATION_UNAVAILABLE`. PR5E does not clip, saturate,
quantize, round, or substitute another economic value.

The price root comes only from PR5D2's admitted Yahoo
`meta.regularMarketPrice` path. Its USD-per-share meaning, provider market date,
receipt object hash, locator, and quote identity are retained. PR5E never uses
previous close, chart close, adjusted close, bid/ask, cache, manual value, or a
fallback provider.

The exact admitted price crosses its Decimal-to-binary64 boundary once. The
same finite and strictly-positive representability checks apply; failure returns
PR5E `UNAVAILABLE` with
`PRICE_BINARY64_REPRESENTATION_UNAVAILABLE`. It is not reclassified as an
upstream source conflict or unsupported security.

The nonpayer root comes only from the freshly replayed route-local two-concept
verified-zero result. Missing dividend data never becomes nonpayer evidence and
no general multi-class dividend authority is created.

## Real-capable PR4B1 provenance

PR4B1 retains its original synthetic contract and dataclass wire shape unchanged.
PR5E adds a separate real facts contract, separate real provenance type, separate
real source kinds, and four `PR5E_REAL_*` adapter identities. No real identity
equals or reuses a `SYNTHETIC_*` adapter.

Real provenance states exactly:

```text
publication_semantics = UNKNOWN
published_at = None
availability_semantics = CAPTURE_BOUND
available_at = exact capture timestamp
captured_at = exact capture timestamp
```

SEC `acceptanceDateTime`, filing dates, Yahoo provider market time, and capture
time are not renamed as publication time. PR4A preserves the separate real
evidence shape. Capture-bound evidence remains usable but is conservatively
capped at `LOW` confidence and emits capture-bound warnings; a recent capture
does not silently create `HIGH` confidence or a stronger CURRENT factual claim.

PR4A schema identity is separated by evidence family:

- `2026-09-08-expected-return-diagnostic-v1` remains the exact legacy
  synthetic schema and accepts only legacy `Evidence`, including its original
  publication/availability chronology and freshness vocabulary;
- `2026-09-30-pr5e-real-expected-return-diagnostic-v1` is the additive PR5E
  real schema and accepts only `RealEvidence` with `published_at=None`,
  `publication_semantics=UNKNOWN`, `availability_semantics=CAPTURE_BOUND`, and
  `available_at == captured_at`.

Either schema rejects the other evidence family, and the real schema rejects a
mixed legacy/real tuple. PR4B1 selects the legacy schema only for the synthetic
facts contract and the real schema only for the PR5E real facts contract. The
PR4A methodology version and numerical mathematics are unchanged.

Synthetic PR4B1 behavior, facts contract, provenance shape, policy mechanics,
and numerical output remain unchanged.

## Time and policy semantics

PR5E calls no clock. Its deterministic analytical `as_of` is the maximum exact
capture timestamp found in the freshly reconstructed evidence graph required by
the successful PR5D2 route. It is execution/reference metadata only and creates
no first-publication, historical availability, freshness-beyond-capture,
`HISTORICAL_AS_OF`, or PIT authority.

PR5E freshly calls `get_owner_approved_policy_proposal()` and verifies the
proposal version/hash plus the mature, terminal, and selected nonpayer policy
hashes retained by PR5D2. It then calls only:

```python
construct_expected_return(
    qualified_facts,
    mature_policy=proposal.proposal.mature_policy,
    terminal_policy=proposal.proposal.terminal_policy,
    distribution_policy=proposal.proposal.nonpayer_distribution_policy,
)
```

PR5E never calls `calculate_expected_return()` directly. Existing PR4B1 owns
assumption construction and invokes existing PR4A. No numerical policy or model
rule changes.

## Dependency and authority boundary

```text
economic/source evidence
-> PR5C / PR5D1
-> expected_return_pr5d_bundle
-> expected_return_pr5e_adapter
-> expected_return_assumptions
-> expected_return_engine
```

There is no reverse import from PR4B1/PR4A into PR5E. No V1 module, `main.py`,
scanner, portfolio/allocation component, operational runtime, recommendation,
execution, PIT transport, or production consumer imports PR5E.

PR5E establishes only final admission for this bounded diagnostic route. It:

- does not change V1 or production authority;
- does not promote V2;
- does not establish historical/PIT authority;
- does not establish exact publication timestamps when unknown;
- does not support payers;
- does not create universal security identity;
- does not expand PR5D2 corporate-action completeness;
- does not create Quality, Durability, Confidence-policy, Opportunity Set,
  recommendation, allocation, execution, or deployment authority; and
- does not change `MODEL_RULES_VERSION` or any investment rule.

## Validation contract

Focused tests cover fresh replay, exact expected identities, all four closed
statuses, identity-conflict precedence, route/class preservation, deterministic
share-basis identity, exact rational bridge arithmetic, exactly five EPS roots,
exact admitted quote use, verified nonpayer and payer exclusion, methodology-only
profile adaptation, distinct real adapters, UNKNOWN publication,
CAPTURE_BOUND availability, deterministic no-clock `as_of`, policy
reconstruction/hash checks, exact PR4B1 policy invocation, absence of a direct
PR4A call, unchanged synthetic shape/behavior, consumer isolation, limitations,
immutability, repeated-input determinism, closed legacy-versus-real PR4A schema
separation, and closed price/EPS binary64 overflow and positive-underflow
handling.

Because `src/**` changes, the complete final change set requires `FULL_PIT`.
Protected PIT/determinism fingerprints and `MODEL_RULES_VERSION` must remain:

- PIT: `f1e73b27b80e41d96ff5e0fe990b482bad71b7220db0b5bd6a2f470d72786166`;
- determinism: `f8457910665391e39c234274cae4c029802c681211eebc7dba986a63000876f1`;
- model rules: `2026-08-23-allocation-room-integrity-v7`.
