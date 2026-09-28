# Research Participation Classifier

> PR5D0G — pure, source-neutral classification of one research subject.

## Purpose and architecture placement

PR5D0G is the final foundation in the current capability-architecture interlude:

```text
economic evidence
        ↓
CapabilityAssessment
        ↓
OutputDependencyContract
        ↓
OutputAvailability
        ↓
ResearchParticipation
```

The classifier describes how a subject may participate in research. It does not
calculate an analytical or economic value and grants no admission, Opportunity
Set, recommendation, allocation, execution, production, or promotion authority.

## Public contract

`analysis_capabilities` exports:

- `RESEARCH_PARTICIPATION_CONTRACT_VERSION` —
  `2026-09-28-research-participation-v1`;
- `ResearchParticipationContractError`;
- `ResearchParticipationState`;
- `ResearchOutputRequirement`;
- `ResearchParticipationContract`;
- `ResearchParticipation`;
- `classify_research_participation`.

All records are frozen and slotted. The module is deterministic, source-neutral,
and pure. It uses no provider, network, filesystem, environment, clock, economic-
fact resolver, analytical calculator, or V1 model.

## Four descriptive states

The closed vocabulary is:

```text
FULL_ANALYSIS_ELIGIBLE
PARTIAL_ANALYSIS
RESEARCH_CANDIDATE
UNSUPPORTED_RESEARCH_PROFILE
```

Declaration order is not an economic ranking. These states describe current
research participation only. They do not mean buy, sell, hold, good company, bad
company, investable, admitted, or allocation eligible.

## Reviewed research-profile contract

`ResearchParticipationContract` declares:

```text
contract_version
profile_id
subject_kind
profile_support_capability_id
output_requirements
```

The `profile_id` identifies an analytical research profile, not a user's risk
tolerance or investment profile. `subject_kind` fixes the common research-subject
domain. `profile_support_capability_id` identifies the exact upstream capability
whose assessment says whether that economic or instrument profile is supported by
the architecture.

Each `ResearchOutputRequirement` declares exactly:

```text
output_id
dependency_contract_semantic_id
```

Requirements form a nonempty tuple, use canonical uppercase output IDs, have
unique output IDs, and sort by output ID. Each requirement pins the lowercase
SHA-256 semantic identity of the exact reviewed `OutputDependencyContract`.
A same-name output assembled under different dependency semantics is malformed
and cannot count.

The profile contract's `semantic_id` binds its version, profile ID, subject kind,
profile-support capability ID, and every canonical output/dependency-contract
pair under a dedicated domain separator. It contains no evidence recapture,
clock, Git, branch, path, environment, provider, or caller-order identity.

PR5D0G defines no production research-profile constant. Fictional contracts can
prove the mechanics, but future real consumers must use separately reviewed,
repository-owned contracts and resolver paths.

## Explicit profile support

The classifier consumes one exact `CapabilityAssessment` for profile support. Its
capability ID must equal the contract's `profile_support_capability_id`, and its
scope must equal the explicit research-subject scope. The classifier never creates
or infers this assessment.

The critical invariant is:

```text
DATA_SCARCITY != UNSUPPORTED_RESEARCH_PROFILE
```

Only this exact condition yields `UNSUPPORTED_RESEARCH_PROFILE`:

```text
profile_support_assessment.state == CapabilityState.UNSUPPORTED
```

Missing outputs, all outputs `UNAVAILABLE`, profile-support `UNAVAILABLE`,
`PARTIAL`, `REVIEW_REQUIRED`, or `CONFLICTED`, provider failure, and data scarcity
cannot produce that state. `UNSUPPORTED` means the reviewed profile lies outside
the implemented contract; it is not an economic criticism.

This explicit input preserves the distinction:

```text
profile support SUPPORTED + outputs missing
→ RESEARCH_CANDIDATE

profile support UNSUPPORTED
→ UNSUPPORTED_RESEARCH_PROFILE
```

## Common subject scope and supplied outputs

The explicit subject scope's `subject_kind` must equal the contract's
`subject_kind`. Every supplied `OutputAvailability.output_scope` must equal that
scope exactly. Internal PR5D0F dependencies may use other scopes through their
reviewed bindings, but participation operates on one common output subject. It
does not infer identity from ticker, CIK, company name, listing, or neighboring
outputs.

Only declared output IDs may be supplied. At most one current availability may be
supplied per output ID. Unknown, duplicate, wrong-scope, or wrong dependency-
contract results are malformed and fail closed. No latest, majority, best-status,
or caller-order rule selects among duplicates.

A declared output may be absent. That is ordinary missing research coverage, not
a malformed request. The classifier retains `REQUIRED_OUTPUT_MISSING` and does not
manufacture an `OutputAvailability`.

## Meaningful output and exact derivation

An output is meaningfully available when its status is `AVAILABLE` or
`AVAILABLE_WITH_LIMITATIONS`. `UNAVAILABLE` does not count as a meaningful output,
but its reasons and limitations remain retained.

State precedence is exact:

1. Explicit profile-support `UNSUPPORTED` yields
   `UNSUPPORTED_RESEARCH_PROFILE`, even when an individual output remains
   available.
2. Otherwise `FULL_ANALYSIS_ELIGIBLE` requires profile support `SUPPORTED`, every
   required output present, and every required output exactly `AVAILABLE`.
3. Otherwise at least one meaningful declared output yields `PARTIAL_ANALYSIS`.
4. Otherwise the result is `RESEARCH_CANDIDATE`.

`AVAILABLE_WITH_LIMITATIONS` is meaningful for partial analysis but never
sufficient for full analysis. A missing required output also prevents full
analysis. Profile-support `PARTIAL`, `UNAVAILABLE`, `REVIEW_REQUIRED`, and
`CONFLICTED` prevent full analysis but do not erase legitimately available
individual outputs.

## Reasons and limitations

Reasons are deterministic, sorted, and deduplicated:

- full analysis has no classifier failure reason;
- partial analysis includes `COMPLETE_RESEARCH_PROFILE_NOT_SATISFIED`;
- a research candidate includes `NO_MEANINGFUL_ANALYTICAL_OUTPUT_AVAILABLE`;
- unsupported profile includes `RESEARCH_PROFILE_UNSUPPORTED`;
- absent declared outputs add `REQUIRED_OUTPUT_MISSING` where partial/candidate
  completeness is being explained;
- relevant profile-support and unavailable/limited output reasons remain visible.

Limitations are deterministic, sorted, and deduplicated from relevant profile-
support assessment limitations and supplied limited/unavailable outputs. Missing
outputs do not create invented limitations. Full analysis has no result-level
limitations.

## Deterministic identities

`ResearchParticipation.semantic_id` uses a dedicated semantic domain and binds:

- classifier contract version;
- research-profile contract semantic identity;
- complete subject scope;
- profile-support assessment semantic identity;
- derived participation state;
- canonical supplied output IDs and each output semantic identity;
- derived reasons and limitations.

It excludes exact evidence recapture IDs. `evidence_id` uses a separate domain and
additionally binds the profile-support assessment evidence ID and every supplied
output evidence ID in output-ID context. Equivalent recapture can therefore retain
the same semantic identity while changing evidence identity. Neither identity
depends on caller order, a clock, path, environment, branch, or Git SHA.

## Structural validity is not authority

```text
structural validity != production authority
```

Caller-constructible contracts, assessments, availabilities, and results can be
structurally coherent without authenticating evidence or becoming approved
production inputs. Future real use requires reviewed repository-owned profile and
dependency contracts plus reviewed profile-support and evidence resolver paths.

`FULL_ANALYSIS_ELIGIBLE` is not Opportunity Set admission. `PARTIAL_ANALYSIS` is
not allocation eligibility. Movement between participation states is not a trading
signal for an existing position; Position Lifecycle remains separate.

## No score and no downstream implementation

The classifier has no weight, score, percentage, threshold, completeness scalar,
or ranking. Exact dimensional output statuses remain visible rather than being
compressed into authority-bearing coverage.

PR5D0G implements no Expected Return, Quality, Durability, Confidence, Opportunity
Set, comparison, ranking, recommendation, portfolio logic, or capital allocation.
It changes no admission authority, investment rule, V1 behavior, or
`MODEL_RULES_VERSION`.

## Free-core invariant and next frontier

PAM's supported core system remains operable without a paid financial-data
subscription. PR5D0G needs no provider.

PR5D0G closes the current capability-architecture interlude:

```text
PR5D0D → PR5D0E → PR5D0F → PR5D0G
```

Immediate implementation returns to Stage A Real Fact Admission:

```text
PR5C → PR5D → PR5E → first real end-to-end V2 Expected Return
```

Confidence and Opportunity Set remain later conceptual stages, not the next PR.
