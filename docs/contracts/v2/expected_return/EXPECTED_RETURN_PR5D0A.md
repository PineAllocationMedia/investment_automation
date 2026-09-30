# PR5D0A — Expected Return policy governance foundation

> Proposal/governance infrastructure only. This contract chooses no production
> economic assumption, grants no policy authority, and creates no operational
> Expected Return consumer.

## Reviewed base and exact scope

After `git fetch origin`, the approved integration ref was exactly:

| Item | Verified value |
| --- | --- |
| Branch | `origin/model-v2/expected-return-challenger` |
| Commit | `8f224757c924a55638eabbdc0b775d32b201814d` |
| Tree | `c32e8f62d4d3c489bd4f6eee6ba8e2d5b51382b8` |
| Implementation branch | `codex/v2-pr5d0a-er-policy-governance` |

The starting worktree and index were clean. The prior local PR5C0B branch was
preserved. This PR adds one pure deterministic policy-proposal boundary:

- `src/expected_return_policy_governance.py`;
- `tests/test_expected_return_policy_governance.py`;
- this contract; and
- one minimal roadmap update.

PR4A mathematics and PR4B1 policy transformations remain unchanged. No V1,
runtime, model, portfolio, scanner, provider, source, deployment, production,
configuration, dependency, or investment-rule file is changed.

## One exact capability

PR5D0A answers one bounded question:

> Do four complete, already typed PR4B1 policy candidates form one internally
> coherent proposal whose content can be reviewed under one deterministic
> identity?

The required candidates are exactly:

1. one `MatureGrowthPolicy`;
2. one `TerminalValuationPolicy`;
3. one payer `DistributionPolicy` using
   `CONSTANT_MATCHED_ORDINARY_PAYOUT`; and
4. one nonpayer `DistributionPolicy` using
   `CONTINUED_VERIFIED_NONPAYER`.

The two distribution roles do not classify a real issuer. A future PR5D path
must choose between them only from controlled payer/nonpayer evidence.

## Public API

```python
build_expected_return_policy_proposal(
    *,
    proposal_id: str,
    mature_policy: MatureGrowthPolicy,
    terminal_policy: TerminalValuationPolicy,
    payer_distribution_policy: DistributionPolicy,
    nonpayer_distribution_policy: DistributionPolicy,
    rationale: str | None = None,
) -> ExpectedReturnPolicyProposalAssessment
```

All arguments are keyword-only. All four policies are mandatory. The function
has no default policy, policy selector, tuning callback, approval flag, authority
flag, current-policy flag, issuer input, ticker, expected-return target,
portfolio input, market condition, performance result, or optimization score.

The returned records are frozen and slotted:

- `ExpectedReturnPolicyProposal` retains the proposal ID, exact four existing
  typed policies, optional trimmed proposal rationale, contract version, fixed-
  role policy hashes, and computed proposal hash;
- `ExpectedReturnPolicyProposalAssessment` exposes the one closed status
  `PROPOSAL_ONLY`, the proposal, its hash, and explicit limitations.

The contract version is
`2026-09-28-expected-return-policy-proposal-v1`.

## Existing contracts remain authoritative

PR5D0A reuses without forking:

- `Applicability`;
- `ScenarioValues`;
- `MatureGrowthPolicy`;
- `TerminalValuationPolicy`;
- `DistributionPolicy`;
- `DistributionRule`;
- `validate_policy`; and
- each policy's existing computed `policy_hash`.

Every candidate is passed through the existing PR4B1 validator. Malformed
scenario ordering, schema, numerical value, rationale, assumption identity,
currency, accounting basis, date interval, profile, or distribution rule remains
a `ConstructorContractError`. PR5D0A does not sort, repair, normalize, convert,
or reinterpret an existing policy.

## Cross-policy closure

All four policies must have exactly identical applicability across:

```text
profile
currency
accounting_basis
valid_from
valid_through
```

The existing validator restricts the initial profile to
`ORDINARY_COMPOUNDER`, currencies to its exact three-uppercase-letter contract,
accounting basis to `IFRS` or `US_GAAP`, and validity to a non-reversed inclusive
interval. PR5D0A performs no currency conversion and broadens no accounting
standard.

Across the complete proposal:

- every policy ID must be unique;
- every assumption ID must be unique;
- every existing policy hash must be unique;
- the payer role must use only `CONSTANT_MATCHED_ORDINARY_PAYOUT`; and
- the nonpayer role must use only `CONTINUED_VERIFIED_NONPAYER`.

Two payer rules, two nonpayer rules, reversed roles, duplicate identities,
duplicate hashes, or conflicting applicability fail as contract errors. There is
no caller-order selection rule and no policy precedence.

## Deterministic proposal identity

The proposal hash is SHA-256 over the existing canonical JSON projection of:

```text
proposal record domain
proposal contract version
proposal ID
optional proposal rationale
fixed role -> exact existing policy hash mapping
```

The roles are always ordered mature growth, terminal valuation, payer
distribution, then nonpayer distribution. Keyword/dictionary construction order
does not affect the result. Host time, filesystem path, environment, Git state,
randomness, machine name, object identity, and caller tuple ordering are absent.

Because each existing policy hash already binds its exact type, schema,
applicability, policy and assumption IDs, rationale, numerical assumptions, rule,
and relevant PR4B1 transformation identity, every economic or semantic change
changes the proposal identity. Changing the proposal ID or proposal-level
rationale also changes it.

The proposal hash is computed from content. It is not accepted from the caller.

## Proposal-only authority boundary

The only result status is:

```text
PROPOSAL_ONLY
```

It is fixed by the result type and is not an input. Supplying the four policies,
passing validation, or obtaining a stable hash grants no investment authority.
There is no callable or record field by which a caller can promote the result.

Future owner approval is intentionally not implemented. It requires a separate
reviewed repository change that:

1. states the exact owner-selected numerical policies;
2. constructs the exact four existing typed policies;
3. computes the deterministic proposal/bundle hash;
4. pins that exact hash and version in reviewed code or data;
5. accepts no caller approval boolean;
6. selects no value dynamically; and
7. updates no policy automatically.

Any later policy-value change requires another explicit reviewed repository
change. Historical outcomes, model performance, analyst forecasts, market peers,
current P/E, Quality, Durability, Confidence, benchmark returns, or model output
cannot self-promote or rewrite a policy.

## No numerical policy decision

Production code in PR5D0A constructs no policy and contains no mature-growth,
terminal-P/E, valuation-premium, sector, market-cap, quality, interest-rate, or
distribution numerical default. All test policies and values are explicitly
fictional and live only in the test module.

This PR therefore does not choose owner policy values and does not change an
investment rule. `MODEL_RULES_VERSION` remains
`2026-08-23-allocation-room-integrity-v7`.

## Purity and dependency direction

The implementation imports only standard-library dataclass support and the
existing pure policy module. It performs no network call, provider call,
filesystem read/write, environment read, clock call, Git call, subprocess,
randomness, persistence, or dynamic import.

The dependency direction is only:

```text
expected_return_policy.py
        ↓
expected_return_policy_governance.py
        ↓
future separately reviewed exact owner-policy artifact
        ↓
future PR5D / PR5E
```

`expected_return_assumptions.py`, PR4A, PIT diagnostics, model/runtime code,
portfolio code, scanners, V1, and production paths do not import or consume this
proposal. A proposal is governance preparation, not a constructor input.

## Explicit nonclaims

Every assessment exposes limitations stating that PR5D0A provides no:

- observed price or quote semantics;
- dividend or nonpayer verification;
- `ORDINARY_COMPOUNDER` qualification;
- share-basis qualification;
- reporting-subject qualification;
- Expected Return admission;
- investment recommendation; or
- authoritative economic values.

It also creates no real issuer connection, final admission, allocation,
production behavior, deployment, source authority, or V2 promotion.

## Relationship to PR5C and future sourcing

PR5D0A advances independently because deterministic proposal governance does not
depend on real issuer admission. It does not complete PR5D and does not unblock
PR5C.

The controlled public SEC/free-Nasdaq evidence graph still does not provide
complete positive no-transformation coverage from the oldest retained EPS period
through CURRENT T. Therefore:

- `SPLIT_BASIS_NOT_ESTABLISHED` remains unresolved; and
- `ECONOMIC_COMPARABILITY_NOT_ESTABLISHED` remains unresolved.

An empty detected-event inventory remains insufficient. No PR5C qualifier or
blocker-discharge mechanism is added.

Potential future corporate-action sources include commercial Nasdaq products
with broader historical action coverage. Whether to purchase, license, integrate,
or rely on any such product is a future owner sourcing/permitted-use decision.
PR5D0A adds no credential, client, purchase, licensing assumption, integration,
or coverage claim, and does not assert that any commercial source closes PR5C.

## Explicit answers

```text
Does PR5D0A choose production policy values? NO.

Does PR5D0A approve any policy? NO.

Can a caller set an approval boolean? NO.

Does PR5D0A complete PR5D? NO.

Does PR5D0A unblock PR5C? NO.

Does PR5D0A change investment rules? NO.

Can policy tuning self-promote? NO.
```

## Validation expectations

Focused tests cover the valid four-policy route, deterministic identity,
keyword-order invariance, mature/terminal/applicability/rationale identity
changes, exact distribution pairing, duplicate policy/assumption/hash rejection,
cross-policy applicability, existing-validator propagation, immutable records,
no production defaults or caller authority inputs, pure dependencies, forbidden
operations, and absence of model/runtime/V1/constructor consumers.

Adjacent Expected Return policy/assumption and dependency/isolation tests remain
required. Validation uses the pinned Python environment and isolated runner. No
real issuer, provider, positive-capital, model, portfolio, backtest, deployment,
or production analysis is performed.

Protected identities must remain:

- PIT: `f1e73b27b80e41d96ff5e0fe990b482bad71b7220db0b5bd6a2f470d72786166`;
- determinism: `f8457910665391e39c234274cae4c029802c681211eebc7dba986a63000876f1`;
- model rules: `2026-08-23-allocation-room-integrity-v7`; and
- frozen V1 commit/tree: `c5fc27c82c29c2a6027eccee245098c4a072fdf1` /
  `26a69bb0b2185ab141af0763da2d965602c8346b`.
