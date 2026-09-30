# Capability Dependency Contracts

> PR5D0E — pure source-neutral dependency declarations only.

## Purpose and placement

This foundation represents the exact capability requirements of one future
analytical output. It is the declaration layer between PR5D0D capability
assessments and the future Partial Analysis Assembler:

```text
economic evidence
        ↓
capability assessment
        ↓
dependency contract
        ↓
future partial-analysis assembler
        ↓
analytical output
```

The canonical rule is:

```text
OUTPUT_AVAILABLE
only if
ITS OWN DECLARED DEPENDENCIES ARE SATISFIED
```

PR5D0E represents the declaration only. It does not decide whether any assessment
satisfies a dependency and does not execute an output.

## Public API

`analysis_capabilities` adds:

- `DEPENDENCY_CONTRACT_VERSION` —
  `2026-09-28-output-dependency-contract-v1`;
- `DependencyContractError`;
- `CapabilityDependency`;
- `OutputDependencyContract`.

Both records are frozen and slotted. Unsupported contract versions and malformed
declarations fail closed.

## Capability dependency

`CapabilityDependency` contains:

```text
dependency_id
capability_id
subject_kind
accepted_states
```

`dependency_id` is the semantic role of this requirement inside its output
contract, not a score or priority. Different roles may require the same capability.
For example, fictional roles `PRIMARY_SECURITY_PRICE` and
`BENCHMARK_SECURITY_PRICE` may both require a fictional source-neutral `PRICE`
capability. Dependency-role IDs are unique within one output contract.

`capability_id` names the exact source-neutral capability required. This foundation
creates no capability registry and declares no production-supported capability.

`subject_kind` states the expected subject domain for the dependency. It does not
bind an actual subject or infer an identity relationship. In particular, ticker,
display-name, or CIK equality cannot establish subject identity.

All three identifiers use conservative uppercase ASCII code grammar.

## Accepted capability states

An automated analytical dependency may accept exactly one of these canonical sets:

```text
SUPPORTED
```

or:

```text
SUPPORTED + PARTIAL
```

`PARTIAL` alone is invalid. `UNSUPPORTED`, `UNAVAILABLE`, `REVIEW_REQUIRED`, and
`CONFLICTED` can never satisfy an automated analytical dependency. Unavailable or
unsupported evidence cannot supply a required capability; evidence requiring review
cannot silently become automated authority; and a conflict cannot be resolved for
downstream convenience.

Accepting `PARTIAL` alongside `SUPPORTED` means the future output contract has
explicitly allowed bounded partial evidence. It does not make `PARTIAL` equivalent
to `SUPPORTED`, and the future assembler must preserve upstream limitations.

`accepted_states` must be an exact, nonempty tuple of exact `CapabilityState`
members. Equivalent caller order and duplicates canonicalize to the same tuple.
The enum declaration order is not treated as an economic ranking.

## Output dependency contract

`OutputDependencyContract` contains:

```text
contract_version
output_id
output_subject_kind
requirements
```

`output_id` identifies one analytical output. `output_subject_kind` declares the
domain on which that output operates. Both are uppercase source-neutral codes; they
do not create an output registry or solve subject identity.

`requirements` is an exact, nonempty tuple of exact `CapabilityDependency`
instances. Every requirement is mandatory, so the foundation has conjunctive
semantics:

```text
requirement A
AND requirement B
AND requirement C
```

Requirements are sorted by dependency role. Caller order therefore changes neither
object equality nor semantic identity. A repeated `dependency_id` fails closed
instead of being overwritten.

There are no generic OR trees, fallback trees, weights, thresholds, majority rules,
priority orderings, dependency graphs, registries, recursive execution, caches, or
invalidation engines. Source/provider-route alternatives normally resolve upstream
into a source-neutral capability. Any genuinely necessary alternative-dependency
semantics require a separate reviewed contract change.

## Deterministic semantic identity

`OutputDependencyContract.semantic_id` is a lowercase SHA-256 identity under the
dedicated domain separator:

```text
pam:analysis-capability-output-dependency-contract:semantic:v1
```

It binds:

- contract version;
- output ID;
- output subject kind;
- every canonical dependency role;
- every required capability ID;
- every expected dependency subject kind;
- every canonical accepted-state set.

It does not depend on caller order, current time, environment, filesystem, branch,
Git state, memory address, or evidence recapture identity. A dependency declaration
is a methodological analytical contract, not captured economic evidence, so it has
no `evidence_id`.

## Authority boundary

These objects are representations, not self-authenticating authority:

> Future consumers must rely only on separately reviewed/pinned output dependency
> contract identities or repository-owned declarations. Arbitrary caller-constructed
> dependency contracts must not be accepted as authority.

PR5D0E creates no consumer and no actual production output contract. A constructible
object grants no analytical, admission, Opportunity Set, recommendation, allocation,
execution, production, or promotion authority.

## Explicit nonclaims

- No capability assessment matching or dependency evaluator exists.
- No subject, issuer, security, listing, scope, or authority-boundary binding exists.
- No ticker, CIK, or display-name shortcut exists.
- No Partial Analysis Assembler or output execution exists.
- No dependency graph, registry, traversal, fallback, or generic OR model exists.
- No score, weight, priority, percentage, threshold, or ranking exists.
- No production Expected Return, Quality, revenue, or other output contract exists.
- No research participation classifier exists.
- No investment or admission field exists.
- PR5C remains blocked; PR5D remains incomplete; PR5E has not started.
- V1 and `MODEL_RULES_VERSION` remain unchanged.

The module remains pure and source-neutral. It uses only the standard library plus
the existing `CapabilityState` type. It requires no provider, runtime, filesystem,
network, environment, clock, economic-fact, Expected Return, scoring, allocation,
or paid-data dependency. PAM's free-core operation therefore remains intact.
