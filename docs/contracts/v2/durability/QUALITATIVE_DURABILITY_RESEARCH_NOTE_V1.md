# Qualitative Durability Research Note v1

Work Order: `WO-V2-STAGE-D-QUALITATIVE-RESEARCH-NOTE-V1`.
Version: `2026-10-26-qualitative-durability-research-note-v1`.
Status: implemented candidate, pending independent review and CEO merge.

## Purpose and fixed authority

This component presents manually supplied private research. It is not a narrative
evidence-admission engine, automated company classifier or investment decision path.
Every rendered note carries these fixed semantics, including when operator-reviewed:

- `MANUAL_RESEARCH_ONLY`
- `NOT_NATIVE_EVIDENCE_ADMISSION`
- `CURRENT_CAPTURE_BOUND_ONLY`

Structural validation never establishes source authenticity, rights, economic
truth, native SEC qualification or independent corroboration. A supplied path,
URL, accession or digest alone establishes none of these. No source is opened,
retrieved, hashed, reconciled or admitted. No native semantic/evidence identity
is generated. Review metadata are operator assertions, not authenticated review
credentials. Dates are exact supplied calendar labels, not clock-based freshness
or historical availability evidence; no publication date creates PIT authority.

## Minimal immutable interface

Module: `src.qualitative_durability_research_note`.

| Record | Fields |
|---|---|
| `ManualSourceReferenceV1` | Document title/reference/date/type, opaque locator, exact supplied section location, operator-supplied digest |
| `QualitativeResearchItemV1` | Optional manual source, statement attribution, issuer statement, operator-supplied source-grounded observation, research interpretation, possible economic mechanism, material competing explanations/vulnerabilities, supporting and contrary context, missing corroboration, uncertainties, possible falsification evidence |
| `QualitativeDurabilityResearchNoteV1` | Issuer name/reference, manual review status/person/date, ordered research items, operator provenance limitations, explicit manual research conclusion; fixed contract/authority/temporal markers |

Records are frozen, slotted dataclasses. Collections must be exact immutable tuples;
nested records must have the exact declared native presentation type. Strings are
preserved rather than coerced, summarized or interpreted. Optional scalar fields
use `None`, and missing collections use `()`. Empty/whitespace-only strings,
nontext values, unsupported control characters (including bidirectional format
controls), mutable containers, foreign records and invalid review states raise
`ResearchNoteError`. No caller-supplied authority override is accepted.

Closed manual review states: `UNREVIEWED` (default) and `OPERATOR_REVIEWED`.
Reviewed notes require both an operator name and exact `YYYY-MM-DD` review date;
unreviewed notes cannot carry those review assertions. Operator review does not
require complete source fields or convert a research interpretation into verified
evidence. Document dates are optional exact `YYYY-MM-DD` labels. Limits: 10,000
characters per text field, 20 research items, and 20 entries per text tuple.
These are presentation bounds, not source-coverage guarantees or resource benchmarks.

`render_qualitative_durability_research_note_v1(note) -> str` returns deterministic
standalone HTML for the exact note type. It revalidates the complete nested structure
before rendering. This is structural checking, not forgery/source authentication.
It preserves explicit input order; no clock, random identity, environment lookup,
filesystem access, acquisition, persistence or operational runtime is involved.
Copying a valid manual presentation record is allowed and grants no evidence authority.

All operator text is HTML-escaped and placed in text positions. Locators are inert
text, not active links. There are no scripts or external assets; a restrictive
content-security policy blocks external loads and scripts. The formatter does not
write a report or publish content. A caller controls any separate private display
or persistence and must preserve the fixed authority markers and limitations.

Missing values render as `NOT PROVIDED`, including sources, section locations,
interpretations, contrary context, corroboration and conclusions. Missing risks
never become “no risks”; absent conclusions remain absent. No quotation, location,
mechanism, source type, verification verdict or moat claim is inferred. Free text
is not semantically fact-checked or classified; the fixed presentation boundary
does not certify whatever an operator writes.

## Accepted design reference and future consumer

The CEO supplied the approved structure of the private Microsoft two-passage example,
independently reviewed under `WO-V2-STAGE-D-FIRST-QUALITATIVE-DURABILITY-REVIEW`,
with supplied result `QUALITATIVE_RESEARCH_EXAMPLE_ACCEPTABLE`. This is an attributed
design reference, not source verification performed by this implementation. No
original filing, genuine issuer narrative, private archive bytes, archive paths
or private source digest are included in the repository or test fixtures.

The representation supports the example's distinction between issuer attribution,
the operator's source-grounded observation, a proposed mechanism, competing
explanations/vulnerabilities, supporting/contrary context, missing independent
corroboration, possible falsification evidence and an explicit bounded conclusion.
The formatter does not generate that conclusion. Supporting and contrary statements
from the same issuer/filing do not become independent economic corroboration.
An unknown-origin source modification can be recorded in provenance limitations;
the component does not resolve it or declare a supplied digest authentic.
Private-use review establishes no public-display or commercial-redistribution rights.

Future consumer: a separate private V2 qualitative research section can display
the returned HTML after manual review, alongside independently sourced
[D1](D1_TWO_PERIOD_OPERATING_PROFIT_CONTINUITY_DIAGNOSTIC_V1.md) and
[D2](D2_TWO_PERIOD_REPORTED_TRAJECTORY_DIAGNOSTIC_V1.md) context. No such integration
is implemented. There is no common native evidence identity across manual narrative
and financial source families, and no inference that D1/D2 changes were caused by
the proposed qualitative mechanism. Neither this note nor its review status changes
D1/D2, Quality, Durability or Confidence scores, Expected Return, admission,
recommendations, ranking, allocation, sizing, execution, V1 or its compact report.
No sustained growth, moat, forward persistence, historical/PIT, production,
deployment or V2 promotion authority is granted. Stage D remains incomplete.

## EXISTING TECHNOLOGY & RESOURCE REUSE ASSESSMENT

ADAPT the explicit version/authority/limitation pattern of bounded V2 diagnostics.
Reuse their presentation discipline, not their native qualification or evidence
identity surfaces. Existing `src.research_reports` imports V1 runtime/manual-input
and investment-field machinery; `src.report_formatters` also imports V1 runtime.
Neither is reused or modified. V1 keyword-based moat handling and historical
Durability scoring are unsuitable for this bounded V2 presentation authority.

REUSE the pinned Python standard library:
[`dataclasses`](https://docs.python.org/3.12/library/dataclasses.html) for records
and [`html.escape`](https://docs.python.org/3.12/library/html.html) for safe text
presentation, with explicit type validation and a small fixed template. BUILD only
this projection; no generalized renderer, parser or schema framework. These
existing-runtime components have no mandatory incremental acquisition, integration,
subscription, API, hosting, model/download, hardware or operating charge: **$0
default satisfied**. The [PSF v2 license](https://docs.python.org/3.12/license.html)
permits royalty-free use, modification and distribution, including commercial use,
subject to notice/license obligations. No Python source is copied or modified,
and no new software/data/model license or source-redistribution permission is assumed.
Official documentation was checked; runtime stays pinned to 3.12.13 rather than
the newer documentation patch. No dependency or spending adoption is requested.

Consulted [execution environments](../../../operations/PAM_EXECUTION_ENVIRONMENTS.md):
CPU-only, no accelerator, network, cache service or downloads. Rendering cost scales
with supplied bounded text; no measured peak RAM or runtime ceiling is claimed.
Mac validation does not establish Chromebook deployment compatibility; its older
system Python and unknown effective memory limits remain limitations. Chromebook
compatibility is NOT VERIFIED. No new external compute is required.

## Scope, validation and handoff

Verified base: `model-v2/expected-return-challenger`,
`be23ebeb32b2ad713f0f3e14f8d000e0dc075bf5`, tree
`88c74aca001b432cc4d79f8d04d8d7705f62e058`. Scope: one new source module, one
fictional test module and this contract. Other source, tests, contracts, configuration,
protected governance and workflows are unchanged. No model-rule change is intended.

Targeted tests cover complete/missing fictional fiches, explicit review metadata,
source trust boundaries, deterministic immutable records, hostile text/markup,
invalid types/control characters, no I/O and rejection by native D1/D2 analyzers.
Adjacent D1/D2 and research/report-formatting regressions and full `FULL_PIT`
preflight are required. Exact commands/results and final commit/tree are retained
in the PR handoff. Protected PIT/determinism fingerprints, model rules and four
operational modes must remain unchanged. No fresh real-issuer evidence qualification
is claimed. CEO-reported exhausted Actions free minutes do not bar publication;
no GitHub CI success, paid execution, manual rerun or protection bypass is assumed.

Next step: independent bounded review, then separate CEO merge decision. No
autonomous follow-up, new acquisition, D3 diagnostic or Stage-D closure is activated.
