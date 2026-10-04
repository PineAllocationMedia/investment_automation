# BOUNDED_CONFIDENCE_PROPAGATION

> Pure, deterministic, read-only projection of confidence semantics already
> established by an available canonical analytical output.

## Purpose

`BoundedConfidenceProjection` exposes existing confidence or bounded evidence
context without recalculating confidence or any economic value. It preserves the
analytical surface's capability state, top-level status and reasons, stable
semantic/evidence lineage, and native confidence representation.

This is a local Stage B adapter. It is not the later full V2 Stage E Confidence
architecture and creates no universal confidence methodology.

The versioned identities are:

```text
BOUNDED_CONFIDENCE_PROJECTION_CONTRACT_VERSION
  = 2026-10-04-bounded-confidence-projection-v1
BOUNDED_CONFIDENCE_PROJECTION_VERSION
  = 2026-10-04-bounded-confidence-projection-representation-v1
```

## Closed inputs

The public projection function accepts exactly one of:

- `PR5EAdmissionResult` for company Expected Return;
- `VFVForwardERDiagnostic`;
- `CompanyVFVComparisonResult`; or
- `CashLikeCurrentCarryQualification`.

Mappings, generic confidence records, detached `ExpectedReturnDiagnostic`
objects, executable-entry evidence, B2 outputs, conviction objects and
decision/allocation surfaces are programming-contract errors.

The closed analysis kinds are:

```text
COMPANY_EXPECTED_RETURN
VFV_FORWARD_EXPECTED_RETURN
COMPANY_VFV_EXPECTED_RETURN_COMPARATOR
CASH_LIKE_CURRENT_CARRY
```

## Common envelope

The immutable projection carries:

- contract and representation versions;
- analysis kind;
- common capability status;
- exact upstream top-level status and reasons;
- confidence representation;
- explicit upstream semantic/evidence identities;
- bounded native detail;
- `CONFIDENCE_PROJECTION_ONLY` authority;
- limitations; and
- deterministic projection semantic/evidence identities.

The common capability status is exactly `AVAILABLE`, `UNAVAILABLE`,
`UNSUPPORTED`, or `SOURCE_CONFLICT`. Confidence representation is exactly
`NATIVE_CATEGORICAL`, `EVIDENCE_CONTEXT_ONLY`, or `NOT_APPLICABLE`.

The envelope normalizes only analytical kind, capability availability,
representation type, top-level status/reasons, identity binding, and projection
authority/limitations. It does not normalize the native confidence objects into
one methodology.

## Company Expected Return

The accepted boundary is the exact PR5E admitted result. A positive projection
requires:

```text
PR5E status = REAL_EXPECTED_RETURN_ADMITTED
construction status = BUILT
diagnostic status = AVAILABLE or DEGRADED
bear/base/bull numeric scenario structure present
```

`DEGRADED` remains common `AVAILABLE`. The projection reuses
`identify_company_expected_return_problem` for its already-reviewed stable
company Expected Return identities. This reuse grants no comparator authority.

The native detail preserves the diagnostic `ConfidenceComponents`,
`overall_confidence`, and every constructor `ConfidenceAssessment` exactly. It
does not floor, combine, or recalculate them. Impossible admitted structure is a
programming-contract error rather than economic unavailability.

## VFV forward Expected Return

An available diagnostic produces `AVAILABLE / NATIVE_CATEGORICAL` and exposes
the exact existing `VFVForwardERConfidence`. Its current `LOW` value stays
`LOW`; no discount, scenario change, probability, executable return or new
calculation is introduced.

## Company–VFV comparator

An available comparison produces `AVAILABLE / NATIVE_CATEGORICAL` and exposes
the exact existing `local_comparator_confidence`. The comparator owns that
confidence. The projection does not recompute a minimum from the company and
VFV inputs and does not copy or recalculate returns or spreads.

## Cash-like current carry

An available qualification produces `AVAILABLE / EVIDENCE_CONTEXT_ONLY`. Its
detail contains only:

- authority scope;
- freshness;
- availability semantics; and
- publication semantics.

No `LOW`, `MEDIUM`, or `HIGH` category is assigned. The projection does not copy
the carry rate, provider/source identifiers, locators, hashes, timestamps or any
seven-year return. It means only that PAM qualified CURRENT/capture-bound
evidence for the current carry fact. It creates no confidence in future rates,
rollover, seven-year cash Expected Return, opportunity cost or reserve policy.

## Non-available behavior

For every supported analytical surface:

```text
UNAVAILABLE     -> UNAVAILABLE     / NOT_APPLICABLE / detail=None
UNSUPPORTED     -> UNSUPPORTED     / NOT_APPLICABLE / detail=None
SOURCE_CONFLICT -> SOURCE_CONFLICT / NOT_APPLICABLE / detail=None
```

The exact upstream status and reasons remain visible. Native `NONE` values on a
non-available VFV or comparator result are not exposed as substantive confidence.
There is no cross-input precedence algorithm and no generic unsupported-case
framework in this slice.

## Identity contract

Both identities bind the projection contract and representation versions.

`semantic_id` binds confidence-projection meaning: kind, capability state,
representation, upstream status/reasons, stable upstream semantic identity,
native confidence/evidence-context meaning, projection authority and limitations.

`evidence_id` additionally binds the exact upstream evidence identity. For the
company surface it also binds the complete propagated `ConfidenceAssessment`
records, including `root_ids`.

Company semantic identity includes every material `ConfidenceAssessment` field
except `root_ids`. Consequently:

```text
equivalent recapture + unchanged confidence semantics
-> same projection semantic_id
-> changed projection evidence_id

changed company root lineage only
-> same projection semantic_id
-> changed projection evidence_id
```

VFV uses the diagnostic semantic/evidence identities and binds its exact native
confidence into projection semantics. The comparator does the same with its
result identities and local confidence. Cash uses the qualification identities
and additionally binds the four bounded evidence-context fields. Raw company/VFV
returns, comparator spreads, cash rates and provenance payloads are not copied
into projection identity material.

Representative positive identities are pinned in tests. Any material change to
the projection representation, semantic fields, confidence interpretation or
identity serialization requires explicit version review.

## Numeric and authority boundary

The projection contains no analytical numeric result field. It neither copies
nor calculates company returns, VFV returns, comparator spreads, cash carry,
execution costs or executable-net Expected Return.

Every projection has only `CONFIDENCE_PROJECTION_ONLY` authority and explicitly
grants no recommendation, ranking, allocation, sizing, execution, production,
V2 promotion, PIT or `HISTORICAL_AS_OF` expansion. LOW confidence never causes an
Expected Return haircut. Missing capability never becomes a guessed value with
LOW confidence.

The implementation is deterministic and clock-free. It performs no network,
filesystem or acquisition work and does not import or use the legacy confidence
range engine or its conviction, numeric-band or sizing semantics.

## Explicit exclusions

This slice adds no new confidence algorithm, score, probability, confidence band,
economic output, capability precedence, B1 change, B2 capability, executable-net
Expected Return, source authority, broker/account/funding fact, decision authority,
investment-rule change, `MODEL_RULES_VERSION` change, production consumer or V2
promotion.
