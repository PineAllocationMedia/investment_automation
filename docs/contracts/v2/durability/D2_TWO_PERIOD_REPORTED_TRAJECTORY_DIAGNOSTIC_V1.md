# Stage-D D2 — Two-Period Reported Revenue and Operating-Income Trajectory v1

Status: IMPLEMENTED / PENDING INDEPENDENT REVIEW. Work Order:
`WO-V2-STAGE-D-D2-REPORTED-TRAJECTORY`; responsible role: Codex Development.
No merge, production or investment authority is granted.

| Identity | Value |
|---|---|
| Contract | `STAGE_D_D2_TWO_PERIOD_REPORTED_TRAJECTORY_DIAGNOSTIC_V1` |
| Version | `2026-10-26-d2-two-period-reported-trajectory-diagnostic-v1` |
| Methodology | `2026-10-26-d2-exact-two-period-reported-trajectory-v1` |
| Identity version | `2026-10-26-d2-analytical-identities-v1` |
| Analysis kind | `TWO_PERIOD_REPORTED_REVENUE_OPERATING_INCOME_TRAJECTORY` |
| Module | `src.d2_two_period_reported_trajectory` |
| Result | `D2TwoPeriodReportedTrajectoryResultV1` |
| Authority | `DURABILITY_D2_TWO_PERIOD_REPORTED_TRAJECTORY_DIAGNOSTIC_ONLY` |
| Temporal mode | `CURRENT_CAPTURE_BOUND_ONLY` |

## Input and trust boundary

`analyze_d2_two_period_reported_trajectory_v1(qualification)` accepts exactly one
argument: the exact native
`CurrentAnnualIssuerTwoPeriodRevenueOperatingIncomeQualificationV1` from
[Contract A](CURRENT_ANNUAL_ISSUER_TWO_PERIOD_REVENUE_OPERATING_INCOME_QUALIFICATION_V1.md).
Its native implementation and PR #151 are canonical; the older proposed headers
on the D1 documents describe their adoption history, not absence of runtime code.

Before interpreting status or computing, D2 invokes Contract A's existing
`_verified_comparative_snapshot`. That boundary verifies the exact contract,
native archive binding, original receipt, complete source-object hash/length,
reconstructed inventory, every public field and both identities. D2 evaluates
only the reconstructed snapshot. Dictionaries, caller facts, foreign results,
subclasses, copied/detached qualifications and modified or stale bindings fail
with `D2DiagnosticError` or the native `ArchiveError`/qualification integrity
error. Integrity failures never become ordinary negative descriptive statuses.
LIVE is local acquisition provenance, not remote cryptographic SEC attestation.

## Closed states and exact calculation

| Verified Contract-A condition | D2 state | Financial output |
|---|---|---|
| Established; both Revenue values > 0 | `AVAILABLE` | Four facts, periods, both directions, exact relative Revenue change |
| Established; either Revenue value <= 0 | `NOT_APPLICABLE` | Four facts and periods only; all three trajectory fields absent |
| `EVIDENCE_UNAVAILABLE` | `UNAVAILABLE` | No comparative facts, periods or trajectory |
| `EVIDENCE_UNSUPPORTED` | `UNSUPPORTED` | No comparative facts, periods or trajectory |
| `SOURCE_CONFLICT` | `SOURCE_CONFLICT` | No comparative facts, periods or trajectory |

`AVAILABLE` has no analytical reasons. Other analytical reasons are the separate
closed enum: `UPSTREAM_EVIDENCE_UNAVAILABLE`, `UPSTREAM_EVIDENCE_UNSUPPORTED`,
`UPSTREAM_SOURCE_CONFLICT`, `PRIOR_REVENUE_ZERO`, `CURRENT_REVENUE_ZERO`,
`PRIOR_REVENUE_NEGATIVE`, `CURRENT_REVENUE_NEGATIVE`. Emit all applicable
nonpositive-Revenue reasons, sorted uniquely. Preserve native upstream status
and reasons separately; a missing capability is not a negative issuer judgment.

Let R0/O0 be PRIOR reported Revenue/Operating Income and R1/O1 be CURRENT.
For `AVAILABLE`, `revenue_direction` compares R1 with R0 and
`operating_income_direction` compares O1 with O0. Each is exactly `INCREASED`,
`UNCHANGED` or `DECREASED`, without epsilon or thresholds. Operating Income may
be positive, zero or negative: a smaller loss is an increase in the reported
amount, not proof of a stronger business.

`revenue_relative_change = (R1 - R0) / R0` is a `RevenueRelativeChange` integer
numerator/denominator pair, reduced with positive denominator and zero `0/1`.
Convert original Decimal values to exact rational values **before subtraction**;
no Decimal arithmetic, binary floats, rounding, clipping or ambient precision
dependence is allowed. No relative Operating Income growth is computed.

The frozen result retains the four original Decimal values and exact PRIOR and
CURRENT start/end dates when established, source CIK, accounting semantics
(`US_GAAP`, `us-gaap`, `USD`), both upstream identities, status/reasons, contract
versions, authority and fixed limitations. Only qualified
`RevenueFromContractWithCustomerExcludingAssessedTax` and `OperatingIncomeLoss`
are supported. No normalization, organic-growth reconstruction, currency
adjustment or operational-perimeter continuity is implied.

## Identity

`semantic_id` binds D2 contract/methodology/identity versions, analysis kind,
status, analytical and upstream reasons, upstream semantic identity, issuer,
periods, exact facts, directions, rational change, accounting semantics,
authority and fixed limitations. It reuses PAM's canonical Decimal identity
encoder, so equivalent Decimal encodings have equal economic semantics.
It excludes receipt paths, capture timestamps, source-row order, accessions and
upstream evidence identity. Contract A's semantic identity is already economic,
without these incidental provenance fields.

`evidence_id` binds the D2 semantic identity and verified upstream evidence
identity. Same economics across legitimate recapture retain semantic identity;
recapture/source-support changes alter evidence identity. Changed amounts,
periods or material statuses/reasons change semantic identity even if a relative
change happens to match. An identity string alone authenticates no input.

## Precise future consumer: bounded Durability context

The future V2 research/compact-report interface may contain a **Reported annual
context** section. This is an interface contract only; no such D2 consumer is
implemented or connected to an operational report in this change.

For `AVAILABLE`, show issuer/CIK; exact prior/current annual date ranges; both
reported Revenue and Operating Income amounts with USD/concept labels; the two
observed D2 directions; exact relative Revenue numerator/denominator (a rounded
percentage may be presentation-only); and D1's operating-income-to-Revenue ratio
direction, separately labeled. Show qualification status, upstream semantic and
evidence references, CURRENT capture date obtained from that bound qualification,
and the descriptive limitations. Pair D1/D2 only when both reference the same
verified Contract-A evidence identity; otherwise show them separately without
suggesting a common comparison.

For `NOT_APPLICABLE`, show that Revenue is nonpositive with the analytical reasons
and qualified dates/facts, but no D2 direction or change. For `UNAVAILABLE`,
`UNSUPPORTED` or `SOURCE_CONFLICT`, show that explicit state and separate upstream
and analytical reasons with provenance references; leave all comparative financial
cells blank. Never display zero, flat, deterioration or a guessed substitute.
Integrity errors must stop rendering that diagnostic and surface an evidence
integrity failure, not an ordinary unavailable business result.

D1 describes the reported operating-margin relationship; D2 describes changes in
the underlying reported amounts. Revenue 100→200 and Operating Income 20→30, for
example, have both D2 directions increased while D1 margin decreases. Neither
two-point observation establishes sustainable growth, a moat, competitive
advantage, a full-cycle trend or future economic persistence. Acquisitions, mix,
currency and reporting changes may affect reported observations without being
isolated here. No thresholds or aggregate Durability/Quality score are authorized.

## EXISTING TECHNOLOGY & RESOURCE REUSE ASSESSMENT

REUSE native Contract-A replay and PAM canonical analytical identity utilities;
BUILD only this bounded analytical projection. REUSE Python 3.12 standard-library
[`fractions.Fraction`](https://docs.python.org/3.12/library/fractions.html) for
exact Decimal conversion and rational arithmetic, rather than mislabeling a
Revenue change with PAM's Operating-Income/Revenue ratio type. Official
[CPython source](https://github.com/python/cpython/blob/v3.12.13/Lib/fractions.py)
and [license](https://docs.python.org/3.12/license.html) were checked: PSF License
v2 permits royalty-free use/modification/distribution, including commercial use,
subject to its notice/license obligations. No Python code is copied or modified;
no new package, weights, dataset, API, installation or financial source is added.

This existing-runtime candidate meets $0 mandatory incremental external cost:
no subscription, access charge, paid tier, hardware purchase, hosting or external
compute is needed. Runtime remains the repository-pinned 3.12.13, not the latest
documentation patch. No broader candidate search is warranted for two comparisons
and one exact rational expression. Main limitations are rational-integer size and
the existing full-source replay's time/memory demand; inherited replay complexity
and resource ceilings were not independently benchmarked here. Consulted
[execution environments](../../../operations/PAM_EXECUTION_ENVIRONMENTS.md):
existing CPU/Python only, no GPU/downloads/cache service. Mac tests establish only
local compatibility; Chromebook/Linux compatibility is plausible but NOT VERIFIED,
with its Python mismatch and unknown effective memory limits preserved. No
dependency, operational, licensing-risk or spending authority is expanded.

## Validation and independent handoff

Base: `model-v2/expected-return-challenger`,
`b869440c7486d20898850b3acee88ddcc6549252`, tree
`204633cd9723dc07f1af1a36e6e9a3f6ed750e0b`. Compared with the Work Order's
`cd8e5ef4b83a748594216bcf9412e90906a0c07d`, only the marketing editorial log
changed (PR #236); no material D2 dependency changed. Existing local refs preserved.
Scope: this contract, one new D2 module and one targeted D2 test module only.
D1, Contract A, Stage C, V1, configuration, four modes, fingerprints and
`MODEL_RULES_VERSION` remain unchanged. Required tier: `FULL_PIT`, plus targeted
and adjacent D1/Contract-A/issuer-Quality regression tests and Git integrity.

Local validation on implementation commit
`9ce8b40b88462a56654920ee61fb98ccce26a3d7`: pinned Python 3.12.13 / locked
dependencies MATCH; 32 D1/D2 and 117 adjacent tests PASS; canonical isolated
detached-worktree preflight PASS (43 quick checks, compilation, 3,604 FULL_PIT
tests, 64 four-mode equivalence cases, both protected fingerprints and model rules
unchanged). The subsequent documentation-only resource-cost clarification and
validation record leave that tested code and test content identical.

Authentic-positive D2 status: **NOT VERIFIED / PENDING**. No original Microsoft
receipt/source archive was supplied or found among repository files; no replacement
was acquired. Synthetic fixtures, including supplied amount arithmetic, prove
mechanics only. D1's authentic PASS does not transfer to D2. Architecture & Audit
must independently replay the preserved original archive, verify receipt/object,
native established Contract A, native D2 `AVAILABLE`, both directions, exact
Revenue change and provenance/identities without unauthorized source publication
before a final `MERGE READY` finding. Next chantier is that bounded review;
merge remains a separate CEO decision. No unresolved product decision is needed
for this bounded diagnostic.
