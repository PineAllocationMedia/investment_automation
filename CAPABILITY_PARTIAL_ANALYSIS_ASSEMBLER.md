# Capability Partial Analysis Assembler

> PR5D0F — pure, source-neutral analytical-output dependency availability only.

## Purpose and architecture placement

The assembler determines whether the declared prerequisites for one future
analytical output are available. It combines an immutable dependency contract,
explicit dependency-role bindings, and immutable capability assessments:

```text
economic evidence
        ↓
CapabilityAssessment
        ↓
OutputDependencyContract
        ↓
PR5D0F Partial Analysis Assembler
        ↓
analytical-output availability
        ↓
future analytical calculation
```

The canonical rule is conjunctive:

```text
ANALYTICAL OUTPUT DEPENDENCIES ARE AVAILABLE
only if
EVERY DECLARED DEPENDENCY IS SATISFIED
```

PR5D0F does not calculate the analytical output. It does not calculate Expected
Return, Quality, revenue growth, EPS growth, a score, a ranking, or any other
economic value. It evaluates one output independently and creates no global
security-wide pass/fail bit.

## Public API

`analysis_capabilities` exports:

- `ASSEMBLER_CONTRACT_VERSION` —
  `2026-09-28-partial-analysis-assembler-v1`;
- `AssemblyContractError`;
- `OutputAvailabilityStatus`;
- `DependencyBinding`;
- `DependencyResolutionStatus`;
- `DependencyResolution`;
- `OutputAvailability`;
- `assemble_output_availability`.

The records are frozen and slotted. Collections are canonical, unique, sorted,
and caller-order independent. The module is deterministic and pure: it uses no
network, filesystem, environment, clock, Git state, provider, economic-fact
resolver, calculator, allocation logic, or V1 model.

## Output availability states

The closed output-level states are:

### `AVAILABLE`

Every dependency is satisfied by one semantic `SUPPORTED` assessment. This means
only that the prerequisites for the declared output are satisfied. It does not
mean the output has been calculated, the research profile is complete, or the
subject is investable or admitted.

### `AVAILABLE_WITH_LIMITATIONS`

Every dependency is satisfied, and at least one dependency explicitly accepts
`PARTIAL` and is satisfied by a `PARTIAL` assessment. The relevant upstream reason
and limitation codes are preserved. `PARTIAL` is never promoted to `SUPPORTED`.

### `UNAVAILABLE`

At least one mandatory dependency is unsatisfied. A missing binding, mismatched
subject kind, mismatched authority boundary, unestablished cross-scope
relationship, missing assessment, ambiguous semantic assessment, or unaccepted
capability state makes that output unavailable. An independent supported
capability cannot fill the gap.

## Explicit dependency binding

`DependencyBinding` contains:

```text
dependency_id
scope
relationship_semantic_ids
relationship_evidence_ids
```

`dependency_id` names one exact requirement role in the output contract. `scope`
is one exact `CapabilityScope`. Relationship identities retain upstream-reviewed
semantic and exact-evidence proof when the bound subject differs from the output
subject.

Every supplied binding must refer to a declared role, and a role may have at most
one binding. Duplicate or unknown roles are malformed assembly requests and raise
`AssemblyContractError`. A legitimate declared role with no binding is ordinary
missing coverage: its resolution is `UNSATISFIED_MISSING_BINDING`, and the output
is `UNAVAILABLE`.

The assembler never binds by ticker, CIK, display name, exchange symbol, nearest
subject, or first assessment. It consumes only explicit upstream subject
identities and bindings.

## Output scope and subject-kind discipline

`assemble_output_availability` requires one explicit `CapabilityScope` for the
analytical output subject. Its `subject_kind` must exactly equal the dependency
contract's `output_subject_kind`; a mismatch is a malformed request and raises.

For every dependency, the binding scope's `subject_kind` must exactly equal the
requirement's expected `subject_kind`. A mismatch is an unsatisfied dependency,
not permission to infer an issuer/security/listing relationship.

## Same-scope and cross-scope relationships

When `binding.scope == output_scope`, the dependency is directly bound and needs
no relationship identities.

When the scopes differ, both collections must be nonempty:

```text
relationship_semantic_ids
relationship_evidence_ids
```

If either is absent, the resolution is
`UNSATISFIED_RELATIONSHIP` with
`CROSS_SCOPE_RELATIONSHIP_NOT_ESTABLISHED`.

The assembler retains but does not interpret or authenticate these identities.
A caller-invented SHA-256-looking string does not establish a real issuer,
security, class, listing, or other relationship. Future real consumers must use a
separately reviewed relationship resolver.

## Strict authority-boundary equality in v1

Assembler v1 requires every bound dependency scope to have exactly the same
`authority_boundary` value as the output scope, including `None`:

```text
CURRENT_T1 == CURRENT_T1  → compatible
CURRENT_T1 != CURRENT_T2  → unavailable
CURRENT_T1 != None        → unavailable
None == None              → compatible
```

Mismatch produces `UNSATISFIED_BOUNDARY` with
`AUTHORITY_BOUNDARY_MISMATCH`. The assembler reads no wall clock, infers no
`CURRENT`, selects no latest boundary, and performs no temporal reconciliation.

## Exact assessment matching

The assessment input is an exact tuple of exact `CapabilityAssessment` objects.
For one requirement and binding, a candidate must satisfy both:

```text
assessment.capability_id == requirement.capability_id
assessment.scope == binding.scope
```

No closest, latest, majority, most-positive, first-element, ticker, CIK, or name
selection exists. No matching assessment produces
`UNSATISFIED_MISSING_ASSESSMENT` with
`CAPABILITY_ASSESSMENT_MISSING`.

## Equivalent recaptures and semantic ambiguity

Multiple matching assessments with one shared `semantic_id` are equivalent
recaptures. The assembler treats them as one semantic assessment while retaining
every distinct assessment `evidence_id` deterministically. It never selects a
latest recapture or discards an older exact evidence identity.

Multiple matching assessments with different `semantic_id` values are ambiguous.
The assembler retains all semantic and exact evidence identities, upstream states,
reasons, and limitations, then returns
`UNSATISFIED_AMBIGUOUS_ASSESSMENT` with
`AMBIGUOUS_CAPABILITY_ASSESSMENT`. Caller order, recapture count, majority, and
state favorability cannot choose a winner.

## State acceptance

Exactly one semantic matching assessment satisfies a dependency only when its
state is in the requirement's reviewed `accepted_states`:

```text
required SUPPORTED; actual SUPPORTED
→ SATISFIED_SUPPORTED

required SUPPORTED + PARTIAL; actual PARTIAL
→ SATISFIED_PARTIAL

required SUPPORTED; actual PARTIAL
→ UNSATISFIED_STATE
```

`UNSUPPORTED`, `UNAVAILABLE`, `REVIEW_REQUIRED`, and `CONFLICTED` never satisfy an
automated dependency under the PR5D0E contract. Rejection produces
`CAPABILITY_STATE_NOT_ACCEPTED`; the assessment's upstream state, reasons,
limitations, semantic identity, and exact evidence identity remain visible.

## Dependency resolutions and reason preservation

Each `DependencyResolution` retains:

```text
dependency role and required capability
expected subject kind and accepted states
bound scope
typed resolution status
assessment semantic and evidence identities
relationship semantic and evidence identities
upstream state or states
upstream reason and limitation codes
assembler reason codes
```

For `AVAILABLE_WITH_LIMITATIONS`, the output-level result propagates reasons and
limitations from every accepted partial dependency. For `UNAVAILABLE`, it
propagates assembler failure reasons plus all retained upstream reasons and
limitations. All collections are deterministic sorted tuples. Missing evidence is
reported as assembly coverage failure, not as an economic criticism.

## Deterministic identities

`OutputAvailability.semantic_id` uses the dedicated domain separator:

```text
pam:partial-analysis-output-availability:semantic:v1
```

It binds the assembler contract version, dependency-contract semantic identity,
output identity and scope, output status, canonical dependency resolutions,
assessment semantic identities, relationship semantic identities, and output
reasons and limitations. It excludes exact recapture evidence identities.

`OutputAvailability.evidence_id` uses a separate evidence domain. It additionally
binds every retained assessment evidence identity and relationship evidence
identity in its dependency-role context. Semantically equivalent recaptures can
therefore preserve `semantic_id` while changing `evidence_id`.

Neither identity binds current time, path, branch, Git SHA, caller ordering, or
object address.

## Fictional example

```python
availability = assemble_output_availability(
    dependency_contract=fictional_output_contract,
    output_scope=fictional_issuer_scope,
    bindings=(
        DependencyBinding("FICTIONAL_REVENUE_ROLE", fictional_issuer_scope),
        DependencyBinding(
            "FICTIONAL_LISTING_ROLE",
            fictional_listing_scope,
            relationship_semantic_ids=(fictional_relationship_semantic_id,),
            relationship_evidence_ids=(fictional_relationship_evidence_id,),
        ),
    ),
    assessments=(
        fictional_supported_revenue_assessment,
        fictional_partial_listing_assessment,
    ),
)
```

If the contract explicitly accepts `PARTIAL` for the fictional listing role and
every other role is supported, the result is `AVAILABLE_WITH_LIMITATIONS`. No
revenue value, growth rate, score, recommendation, or allocation is calculated.

## Authority and nonclaims

The assembler is structurally deterministic, not self-authenticating:

- arbitrary caller-created `CapabilityAssessment` objects do not create trusted
  economic authority;
- arbitrary caller-created `OutputDependencyContract` objects do not create an
  approved analytical contract;
- arbitrary caller-created relationship hashes do not prove a real relationship;
- future real consumers must obtain all three through separately reviewed,
  repository-owned or resolver-owned paths.

PR5D0F adds no production consumer and no economic output execution. It adds no
research-participation classifier, Confidence formula, Opportunity Set gate,
admission, investability, recommendation, ranking, allocation, execution,
production, or promotion authority. It changes no V1 behavior or model rule.

The free-core invariant remains intact. The assembler needs no provider and no
paid financial-data subscription. Narrower free/public coverage stays explicit
rather than being repaired with guessed facts.
