# EXPLICIT_UNSUPPORTED_CASE_HANDLING

> Pure, deterministic, read-only explanation of an already-established
> non-available Stage-B analytical state.

## Purpose

`StageBNonAvailableCase` is a local Stage-B explanatory adapter. It preserves
the closed upstream capability state, exact native reasons, and canonical
semantic/evidence lineage without independently diagnosing economics or
deciding whether a capability should exist.

It is not:

- a generic PAM capability framework;
- a confidence engine;
- an error logger;
- a fallback estimator;
- an evidence qualifier; or
- a portfolio decision layer.

The versioned identities are:

```text
EXPLICIT_UNSUPPORTED_CASE_CONTRACT_VERSION
  = 2026-10-04-stage-b-explicit-unsupported-case-v1
EXPLICIT_UNSUPPORTED_CASE_REPRESENTATION_VERSION
  = 2026-10-04-stage-b-explicit-unsupported-case-representation-v1
```

## Closed inputs and analysis kinds

The public adapter accepts exactly one of these runtime types:

- `PR5EAdmissionResult`;
- `VFVForwardERDiagnostic`;
- `CompanyVFVComparisonResult`; or
- `CashLikeCurrentCarryQualification`.

Mappings, dicts, detached diagnostics, generic records, duck-typed objects,
executable-entry evidence, B2 objects, and unrelated evidence or capability
objects are programming-contract errors.

The corresponding analytical meanings are exactly:

```text
COMPANY_EXPECTED_RETURN
VFV_FORWARD_EXPECTED_RETURN
COMPANY_VFV_EXPECTED_RETURN_COMPARATOR
CASH_LIKE_CURRENT_CARRY
```

## Available and non-available behavior

An exact supported input whose analytical result is available returns `None`.
No `NOT_APPLICABLE` object is created.

The only object-producing common capability states are:

```text
UNAVAILABLE
UNSUPPORTED
SOURCE_CONFLICT
```

These states remain distinct. `SOURCE_CONFLICT` is not missing evidence,
unsupported semantics, or low confidence. Unknown future states fail as
programming-contract errors until explicitly reviewed. There is no `PARTIAL`,
`DEFERRED`, `LOW_CONFIDENCE`, generic error, or generic failure state.

For company Expected Return, the adapter consumes the PR5E boundary and reuses
`identify_company_expected_return_problem` solely for the already-reviewed
stable company Expected Return problem identities. It does not bind replay-
sensitive PR5E admission identity as the sole semantic anchor, copy scenario
returns, perform comparator calculations, or gain comparator authority.

For VFV, the comparator, and cash-like current carry, the adapter preserves the
exact native top-level status and reasons and references the canonical upstream
semantic and evidence identities. It copies no analytical values, source
payload, provenance hashes, timestamps, or future assumptions.

Common normalization stops at `analysis_kind` and `capability_status`. Native
reason semantics remain owned upstream; no second reason taxonomy exists.

## B1 and B2 boundaries

B1 is excluded. `ExecutableEntryEvidenceQualification` is not accepted or
imported. B1 facts are not copied, summarized, erased, promoted, or translated
into confidence. Independently qualified B1 facts remain owned by the existing
B1 contract.

B2 is excluded. Externally, B2 remains `UNAVAILABLE / DEFERRED`; `DEFERRED` is
not a state in this adapter. There is no B2 record, proxy friction, inferred
funding, guessed FX cost, quote-authority upgrade, executable-net Expected
Return, or low-confidence guessed output. A separately reviewed canonical B2
contract is required before any extension.

## Partial evidence and confidence

The case references upstream meaning only. Valid upstream subfacts remain valid
and remain owned upstream when an overall capability is unavailable. No fact is
duplicated, erased, promoted, or converted into an analytical number.

The adapter is a sibling of `BoundedConfidenceProjection`; it neither imports
nor calls that module. `StageBNonAvailableCase` has no confidence field and
performs no confidence recomputation, haircut, or numeric translation.
`UNAVAILABLE`, `UNSUPPORTED`, and `SOURCE_CONFLICT` never become `LOW`.

## Identity contract

`semantic_id` binds exactly:

- contract version;
- representation version;
- analysis kind;
- capability status;
- upstream status;
- upstream reasons;
- upstream semantic identity;
- authority; and
- limitations.

`evidence_id` binds exactly the resulting `semantic_id` and upstream evidence
identity. Therefore a status or reason change changes semantic identity, while
an evidence-only recapture with unchanged meaning preserves semantic identity
and changes evidence identity. Analytical numeric output is absent from both
identity domains. Representative non-available identities are pinned in tests.

## Authority and limitations

Every case has only:

```text
CAPABILITY_STATUS_EXPLANATION_ONLY
```

Every case explicitly denies:

```text
NO_ANALYTICAL_NUMERIC_OUTPUT
NO_CONFIDENCE_RECOMPUTATION_OR_HAIRCUT
NO_CAPABILITY_STATE_REINTERPRETATION
NO_RECOMMENDATION_RANKING_ALLOCATION_OR_SIZING
NO_EXECUTION_OR_PRODUCTION_AUTHORITY
NO_V2_PROMOTION_AUTHORITY
NO_PIT_OR_HISTORICAL_AS_OF_AUTHORITY_EXPANSION
NO_B2_CAPABILITY_CREATION
```

The adapter grants no new analytical conclusion, recommendation, ranking,
allocation, sizing, execution, production, deployment, V2 promotion, PIT, or
`HISTORICAL_AS_OF` authority.

## Explicit exclusions

The implementation is deterministic and clock-free. It performs no network,
filesystem, or acquisition work and has no dependency on generic capability
machinery, B1, B2, confidence, recommendation, sizing, broker, or execution
modules. It introduces no investment-policy or model-rule change.
