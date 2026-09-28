# Capability Contract Foundation

> PR5D0D — pure source-neutral representation only.

## Purpose

This foundation represents whether PAM can support one exact analytical
capability within one exact scope. It implements the capability-coverage layer
between economic evidence and future analytical conclusions. It does not inspect
or resolve economic evidence, assemble partial analysis, classify research
participation, or grant investment authority.

Canonical invariant:

```text
ONE_CAPABILITY_FAILURE != WHOLE_RESEARCH_FAILURE
```

## Public API

`analysis_capabilities` exports only:

- `CAPABILITY_CONTRACT_VERSION` —
  `2026-09-28-capability-assessment-foundation-v1`;
- `CapabilityState`;
- `CapabilityScope`;
- `CapabilityAssessment`;
- `CapabilityContractError`.

The package is stdlib-only. It performs no network, filesystem, environment,
clock, provider, Expected Return, scoring, allocation, or runtime work.

## Capability states

The closed vocabulary is:

```text
SUPPORTED
PARTIAL
UNSUPPORTED
UNAVAILABLE
REVIEW_REQUIRED
CONFLICTED
```

The declaration order is not an economic ranking or a statement about company
quality or investment preference.

- `SUPPORTED` means the exact capability is evidence-backed inside the exact
  scope.
- `PARTIAL` retains useful support plus explicit reasons and limitations; it
  does not satisfy a dependency requiring `SUPPORTED`.
- `UNSUPPORTED` means the case lies outside the implemented contract/profile,
  not that the company is economically poor.
- `UNAVAILABLE` means required evidence is absent or unobtainable through the
  supported route. Absence is not zero, false, or no event.
- `REVIEW_REQUIRED` retains relevant evidence that automation cannot safely
  resolve. It is not support.
- `CONFLICTED` retains the unresolved evidence and conflict reason; caller order,
  latest value, or majority does not select a winner.

## Scope semantics

`CapabilityScope` contains:

```text
subject_kind
subject_identity
authority_boundary
supporting_semantic_ids
```

`subject_identity` must be an exact lowercase SHA-256 semantic identity emitted
by an upstream reviewed contract. A route-local PR5B security key is one future
example. The scope does not create a global issuer/security identity. A ticker,
display name, CIK, listing, or wall-clock-derived `CURRENT` assertion cannot be
substituted for the upstream identity.

`authority_boundary` is optional but, when present, must be explicit canonical
ASCII supplied by the upstream contract. `supporting_semantic_ids` binds any
additional identities required to preserve the scope's meaning. Collections are
deduplicated and lexically sorted, so caller order is not semantic.

## Assessment semantics and invariants

`CapabilityAssessment` contains:

```text
contract_version
capability_id
scope
state
supporting_semantic_ids
supporting_evidence_ids
reason_codes
limitation_codes
```

Capability, reason, limitation, and subject-kind codes use conservative uppercase
ASCII identifier grammar. They are authority-bearing codes, not user prose. This
foundation defines no global capability or reason registry.

Structural fail-closed invariants are:

- `SUPPORTED` requires retained semantic and exact evidence identities;
- `PARTIAL` requires retained support, reasons, and limitations;
- `UNSUPPORTED` requires a reason;
- `UNAVAILABLE` requires a reason and may retain no evidence;
- `REVIEW_REQUIRED` requires retained support and a reason;
- `CONFLICTED` requires retained support and a reason.

Future capability-specific reviewed resolvers remain responsible for legitimately
producing these states. There is no `qualified=True`, `mark_supported`, state
upgrade, evidence interpreter, or generic resolution helper.

## Deterministic identity

`semantic_id` hashes, under a capability-specific domain separator:

- contract version;
- capability ID;
- complete scope;
- state;
- supporting semantic identities;
- reasons;
- limitations.

It deliberately excludes exact evidence identities. `evidence_id` uses a separate
domain and binds `semantic_id` plus exact supporting evidence identities. Therefore
an equivalent recapture may preserve `semantic_id` while changing `evidence_id`.
Neither identity includes time read from a clock, paths, branch names, memory
addresses, or caller ordering.

## Example

```python
from analysis_capabilities import (
    CAPABILITY_CONTRACT_VERSION,
    CapabilityAssessment,
    CapabilityScope,
    CapabilityState,
)

scope = CapabilityScope(
    subject_kind="ROUTE_LOCAL_SECURITY",
    subject_identity=upstream_security_semantic_id,
    authority_boundary="2026-09-28T12:00:00Z",
    supporting_semantic_ids=(upstream_scope_semantic_id,),
)
assessment = CapabilityAssessment(
    contract_version=CAPABILITY_CONTRACT_VERSION,
    capability_id="COMPARABLE_EPS_HISTORY",
    scope=scope,
    state=CapabilityState.UNAVAILABLE,
    reason_codes=("SHARE_BASIS_NOT_ESTABLISHED",),
)
```

This example records only dimensional capability unavailability. It says nothing
about Quality, Durability, Confidence, investment merit, or admission.

## Explicit nonclaims

- No dependency graph or partial-analysis assembler exists.
- No research-participation classifier or runtime type exists.
- No Confidence or Opportunity Set behavior exists.
- No capability registry, global coverage score, percentage, weight, or ranking
  exists.
- No admission, investability, buy/sell, recommendation, allocation, execution,
  production, or promotion field exists.
- No downstream consumer is authorized or implemented.
- PR5C remains blocked; PR5D remains incomplete; PR5E has not started.
- V1 and `MODEL_RULES_VERSION` are unchanged.
- The free-core invariant is preserved: this contract requires no provider or
  paid financial-data subscription.
