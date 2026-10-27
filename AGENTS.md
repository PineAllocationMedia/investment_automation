# AGENTS.md

> Tool-neutral operating instructions for any AI or automated development agent working on PAM.

---

## 1. Mandatory reading order

For substantive governed work, use minimum necessary context in this order:

1. Read `PAM_PROJECT_CONSTITUTION.md`.
2. Read `governance/PAM_GOVERNANCE.md`.
3. Read `governance/PAM_CURRENT_STATE.md`.
4. Read the acting role's own `governance/roles/<ROLE>.md` charter.
5. Read the assigned Work Order, when one exists.
6. Read only the task-specific technical contracts and source documents needed.

Read `governance/PAM_STRATEGY.md` when strategy, product or commercial context is
relevant. Do not force every role to read `PAM_ROADMAP.md`, `DECISIONS.md` or
`README.md` in full for every task. Read relevant roadmap and Decision Registry
portions when current sequencing or historical rationale matters. Read
`BASELINE_V1_FREEZE.md` if V1 or production behavior could be affected, and
`AUDIT_GUIDE.md` only for V1 audit workflows.

Do not use `README.md` or `AUDIT_GUIDE.md` as the sole description of PAM's long-term V2/product direction.

---

## 2. Verify reality before acting

Never trust a stale document for exact Git state.

Before implementation:

- `git fetch origin`;
- verify the intended base branch;
- verify exact base SHA/tree;
- inspect current working tree/index;
- preserve divergent local refs;
- inspect the actual implementation before changing it.

At the time this file was first created, the V2 integration branch was:

`model-v2/expected-return-challenger`

after PR4C6 merge commit:

`1da91db1b3c33ac0f65b4f84efb909b9048ae1e1`

This is historical context, not a permanent expected SHA.

---

## 3. Role boundaries

The canonical role charters are in `governance/roles/`; follow
[Governance §4](governance/PAM_GOVERNANCE.md#4-roles-routing-and-ownership) for
invocation, coordination and transitional authority. PAM Financial Systems and
PAM Media & Communication share specialist expertise; these are activities, not
autonomous divisions, new agents, legal entities or separate repositories.

Roles are callable when legitimately invoked within an authorized mandate;
permanent role activation classes are retired. Availability grants no continuous
execution, self-activation, automated inter-role communication, autonomous role
invocation, new spending or autonomous work generation. Preserve Work Order,
blocker and capability statuses; removing a role label never authorizes a task.

The Program Manager coordinates organizational priorities, dependencies, shared
resources and meaningful conflicts. Reversible ordinary steps already covered by
an explicitly approved mandate need no repeated PM approval; keep PM visibility
for meaningful commitments, dependencies and outcomes. Every Work Order retains
one primary responsible role. Required validation and meaningful independent
assurance remain; low-risk documentation does not automatically need exhaustive
independent audits. Material financial, security, evidence, authority and
production risks retain mandatory assurance.

No role may expand its own authority or originate amendments to its own charter;
mechanical implementation of a specifically CEO-directed protected amendment is
subject to separate CEO review and merge. No protected policy change, material
financial/model-policy decision, canonical merge, deployment or V2 promotion may
be performed without explicit CEO authorization. Never fabricate data or
unsupported financial conclusions. Existing charter limits remain binding.

Repository instruction changes do not update external ChatGPT or independently
configured Codex instructions. The organization-level foundation remains
authoritative; conflicting legacy external text cannot expand authority. Until
the affected external instructions are aligned, Governance's narrow transition
rule bars new discretion beyond an existing approved mandate.

### Owner

Only the owner decides:

- merges;
- deployment;
- production authority;
- investment-philosophy changes;
- commercialization direction;
- regulatory posture;
- final promotion of V2.

### Review / reasoning agents

Default responsibilities:

- inspect;
- audit;
- diagnose;
- classify defects;
- compare architecture options;
- recommend;
- write precise implementation prompts.

Do not claim something was changed, merged, deployed or deleted unless it actually was.

### Implementation agents

When explicitly authorized:

- investigate first;
- use the exact approved base;
- make the smallest safe change;
- add regression tests;
- validate;
- commit/push/open PR when requested;
- stop before merge unless explicitly authorized.

---

## 4. Permanent safeguards

Unless explicitly superseded by an approved contract:

- V1 `main` remains frozen operational authority.
- V2 remains a challenger.
- Tuning remains `PROPOSAL_ONLY`.
- Historical diagnostics are not automatically PIT evidence.
- Synthetic qualification is not real-data authority.
- Missing data does not become a guessed value.
- Data uncertainty reduces confidence/admission rather than being hidden.
- Investment rules must not be altered because an output looks strange.
- No automatic self-modification of investment rules.
- No autonomous promotion of V2.
- No production deployment as a side effect of development work.

Planning toward potential V1/V2 architectural convergence is authorized; an
independent technical study and separate CEO authorization are required before
code migration. Branch roles, V1 behavior, evidence histories, model fingerprints
and shadow/promotion gates remain unchanged; one codebase never promotes V2.

New unattended Codex/development-orchestration implementation is paused under
[Governance §12](governance/PAM_GOVERNANCE.md#12-unattended-development-orchestration-pause).
Preserve experiments, issues, security findings, blockers and mock-only evidence;
do not install, uninstall, disable, restart or operate infrastructure as a side
effect. Restart requires a new explicit CEO decision and appropriate safety/cost
evidence. The separately approved monthly blocker-signal watch remains unchanged;
its signals do not reopen blockers or invoke specialists. Instruction alignment
certifies no runtime worker, security boundary or spending control.

---

## 5. Product direction

PAM Financial Systems prioritizes personal and family use. Its analytical direction
remains:

> **financial research intelligence + portfolio intelligence**

Research and portfolio workflows should prioritize:

- research;
- explanation;
- evidence/provenance;
- screening;
- monitoring;
- comparisons;
- watchlists;
- portfolio analytics;
- thesis tracking;
- alerts.

The user retains the final investment decision.

Private multiportfolio analysis, independently and consolidated, is a future
product/design objective, not an implemented capability. Financial
commercialization is deferred as an immediate priority; it remains an option
requiring a separate CEO decision. Preserve research/advice regulatory separation;
do not redesign PAM primarily as a personalized recommendation bot without an
explicit owner decision.

PAM Media & Communication preserves Marketing & GTM's bounded approved Blossom
mandate. Editorial planning, research, drafts, revisions and learning retain PM
visibility and shared-resource coordination; CEO approval before publication and
Macro Lens sourcing/factual/visual assurance remain mandatory. No autonomous
posting, new channel commitment, paid campaign, unauthorized affiliate activity,
new product launch, new commercial commitment, unapproved spending or financial
data publication authority is granted. Follow
[Strategy](governance/PAM_STRATEGY.md) and the
[Marketing charter](governance/roles/MARKETING_GTM.md) for the authoritative scope.

### CEO-selected AI-native Financial Systems direction

On 2026-10-27, the CEO selected a 36-decision future AI-native design;
see [the Master Blueprint](docs/strategy/PAM_FINANCIAL_SYSTEMS_AI_NATIVE_REFORM.md)
and the Constitution/Strategy for its controlled strategic status. This
does **not** supersede current V1 frozen authority, V2 challenger contracts,
the High-CAGR rules, existing data/provenance/PIT gates or the unattended
development-orchestration pause.

Proposed Project environments are Financial Systems Command Center,
Investment Research and Portfolio Intelligence; the organizational Program
Manager continues to coordinate both activities. Never imply automatic
cross-Project messaging, Work/Blossom access or reliable scheduled research.
Keep verified facts separate from AI assumptions and preserve numerical
checks where accuracy requires; use only the explicit approved investment
strategy. Protected private portfolio data must not be placed in general
repository memory or used by Media. The $0 external financial-data-cost
constraint and separate rights checks still apply.

`RESEARCH-READY`, `PORTFOLIO-READY` and `ROUTINE-READY` are
separately evaluated research/workflow milestones, **not** deployment or
model-promotion authority. Pilot construction, read-only legacy/device audit,
data access and any later cleanup require their own bounded CEO-approved
Work Orders. Do not alter legacy V1/V2 code or validation contracts in an
AI-native documentation or governance alignment task.

---

## 6. Investment architecture

V2 pillars:

1. QUALITY
2. DURABILITY
3. EXPECTED RETURN
4. CONFIDENCE
5. PORTFOLIO ROOM

Style:

> High-CAGR Quality Compounder — Asymmetric

Canonical principle:

> Be aggressive with economic risk, not information uncertainty.

Do not introduce mean-variance optimization, covariance-driven allocation or opaque complexity merely because it is mathematically sophisticated.

---

## 7. Evidence architecture

Preferred flow:

```text
source
→ immutable capture
→ extraction
→ qualification
→ economic facts
→ analytical assumptions
→ expected return / quality / durability / confidence
→ portfolio context
→ research output
```

Keep source semantics, evidence authority and model inference separate.

Do not let:

- source-specific identifiers;
- country-specific filing types;
- ticker conventions;
- exchange conventions;

define core economic contracts.

---

## 8. Defect-review protocol

For any surprising behavior, classify:

- A — defective logic
- B — correct logic / misleading reporting
- C — expected behavior
- D — mixed

Then repair the smallest real defect.

If logic is correct and reporting is confusing, prefer a reporting fix.

If the issue hides a product or investment-philosophy decision, stop and ask the owner.

---

## 9. Coding / PR discipline

Prefer one narrow chantier at a time.

Every implementation prompt or PR should make explicit:

- base branch/SHA;
- files in scope;
- files out of scope;
- invariants;
- supported/unsupported cases;
- authority limitations;
- regression tests;
- full-suite expectations;
- whether model rules change.

Avoid opportunistic refactors.

Do not modify unrelated code because it is nearby.

---

## 9.1 EXISTING TECHNOLOGY & RESOURCE REUSE BEFORE BUILD

Before designing or implementing a substantive new capability, technical component,
parser, analytical engine, data workflow, reporting feature, infrastructure service
or comparable system, perform a proportionate pre-existing technology/resource
assessment. When applicable, complete it before implementation authorization.

- Search only relevant ecosystems: GitHub and authoritative source repositories,
  Hugging Face models/datasets/components, PyPI or conda-forge packages, public,
  institutional or standards-based resources, existing algorithms, libraries,
  APIs, tools and other credible free resources. Do not search every platform
  automatically; normally compare no more than three credible candidates.
- Verify actual sources, current licenses and maintained versions. Assess functional
  suitability, reliability/correctness evidence, maintenance/releases, version
  compatibility, documentation/tests, security and supply-chain concerns,
  performance, integration/maintenance complexity and total cost of ownership.
  Separate vendor claims from independently verified characteristics. Consider
  dependency reuse, component adaptation, safe study of design patterns or rejection;
  build custom solutions when necessary.
- Independently check source-code and model architecture/code licenses, model
  weights licenses, dataset licenses/provenance, redistribution/modification rights,
  commercial-use permission, access restrictions, acceptable-use conditions and
  applicable terms. Software licensing is separate from data licensing and
  source-use restrictions. Free download does not imply open-source licensing or
  commercial-use permission. Prefer suitable permissive licenses; assess GPL/AGPL,
  custom, proprietary, dual-licensed, non-commercial, unclear or commercially
  restricted resources before incorporation. Preserve copyright, license,
  attribution, NOTICE and modification obligations. Material licensing or
  commercial-use uncertainty requires Commercial & Compliance review; the CEO
  retains material legal-risk and commercialization authority.
- Consult [PAM execution environments](docs/operations/PAM_EXECUTION_ENVIRONMENTS.md).
  When relevant, assess CPU architecture/instruction sets and processing demand,
  peak/sustained RAM, swap assumptions, GPU/accelerators, installation/dependency
  footprint, model weights/download size, caches/temporary storage, runtime/Python
  compatibility, execution time, operational overhead and continuing API, hosting,
  cloud or external-service costs. Preserve PAM's approved cost constraints;
  this assessment grants no spending exception. Distinguish development-Mac
  compatibility, plausible Chromebook/Linux compatibility, separately authorized
  external-compute requirements and compatibility not established. Mac success
  does not establish Chromebook compatibility; unknown capacities remain UNKNOWN.
- By default, any technology/resource recommended for adoption must be obtainable,
  integrable and operational without mandatory incremental external financial
  expenditure, unless the CEO explicitly authorizes an exception before adoption.
  Check acquisition/licensing costs, mandatory subscriptions/access fees, API charges,
  usage limits and paid-tier dependencies, purchased integration software/services
  or additional hardware, hosting/cloud/storage/external compute and other operating
  expenses, recurring fees, renewals and mandatory upgrades. An advertised free tier
  is insufficient when realistic intended use requires paid access. Open-source
  availability proves neither zero-cost operation nor commercial-use permission;
  assess commercial use, modification, distribution and redistribution rights
  separately from monetary cost, and hardware fit against PAM's existing environments.
  Explicitly state whether each credible candidate meets this default; unverified
  cost compatibility is `UNKNOWN`, never assumed compliant. Candidates requiring
  mandatory spending cannot be recommended for adoption under the default gate;
  reject them or escalate for an explicit CEO exception. Never invent free
  alternatives or verification evidence. Developer effort, maintenance complexity
  and execution time are non-cash costs that remain important selection criteria.
  This default grants no spending/adoption authority or exception to PAM's existing
  `$0` external financial-data-cost constraint; it does not ban future paid
  infrastructure/services separately authorized by the CEO.
- Substantive implementation Work Orders must include a compact
  `EXISTING TECHNOLOGY & RESOURCE REUSE ASSESSMENT`: candidate names/source links,
  licensing/commercial-use status, technical/hardware fit, major limitations/risks,
  a `REUSE / ADAPT / BUILD` recommendation and concise rationale. Trivial bug fixes,
  pure documentation, isolated contract corrections or work without a meaningful
  reusable component may give a brief justified `NOT APPLICABLE` instead.
- If no credible candidates, internet access or required verification are available,
  report the limitation. Never invent candidates/results or claim an unperformed
  search. Keep the assessment lightweight and proportional; avoid broad research,
  excessive bureaucracy and unnecessary implementation delay. No retroactive
  reevaluation of completed chantiers is required.
- The assessment grants no automatic permission to install dependencies, copy code,
  download/execute model weights, introduce external APIs, accept licensing risk,
  change architecture or financial methodology, expand source authority, relax
  qualification, merge or deploy. Preserve immutable capture, exact evidence
  provenance, qualification contracts, security boundaries, reproducibility,
  deterministic analytical contracts, V1 frozen authority and V2 challenger status.

---

## 9.2 ENGINEERING ROUTING CHECKPOINT — REUSE AND ESCALATION

For substantive new infrastructure or agent/orchestration capabilities, the Program
Manager must check `§9.1` **before** selecting BUILD or routing an implementation
Work Order. Record a compact `REUSE / ADAPT / BUILD` result (normally no more than
three credible outside candidates, plus the current PAM baseline), including actual
source/license, $0 usage and billing surfaces, hardware fit, security limits and
unknowns. An existing tool is not an isolation, payment or worker-authorization
certificate; missing proof stays BLOCKED/UNKNOWN. Document a proportionate
`NOT APPLICABLE` reason for trivial fixes rather than imposing a broad search.

When repeated fixes fail at the **same architectural invariant**, stop the
patch/audit loop and route one bounded root-cause/alternative review before
another implementation. A useful trigger is two failed corrections with no new
discriminating evidence, or one independently demonstrated structural mismatch.
The Program Manager should give the CEO a short choice: continue with a new
specific proof, adapt/reuse, change architecture, or stop. Do not create repeated
studies or treat a previous sunk cost as justification to keep building.

Before a Work Order starts, verify: exact question, one responsible role,
current repository/device state as applicable, existing component candidates,
hard safety and financial gates, measurable PASS/STOP tests, remaining unknowns,
and the **smallest safe next step**. Confirm whether a requested action needs a
separate CEO authority grant. Missing required context must not become assumed
PASS. Do not silently route a specialist without invocation, fabricate a handoff,
or let a new issue/agent output expand the permission envelope.

After an important blocker or failed experiment, record only durable factual
lessons in non-protected operational governance and/or the existing execution
environment reference, with evidence status and provenance. Prefer one batched
Governance Sync PR; protected files remain proposal-only without separate explicit
CEO authorization. Preserve historical evidence, canonical sequencing and
existing accepted mock-only scope.

This checkpoint operationalizes §9.1; it does not change the Constitution, role
charters, V1/V2 authority, execution security, #154 financial gates or CEO-only
merge/deployment decisions.

---

## 10. Validation defaults

Use the repository's pinned Python / locked dependencies and isolated test runner.

For substantive V2 work, preserve and verify as applicable:

- targeted tests;
- adjacent-layer regression tests;
- the validation tier determined from the complete change set:
  - `DOCS_ONLY` — documentation integrity for an all-Markdown diff;
  - `STANDARD` — complete discovered ordinary suite minus only the isolated
    heavyweight PIT adapter-equivalence module;
  - `FULL_PIT` — the complete ordinary suite plus that heavyweight PIT module;
- unknown or ambiguous paths must fail toward `FULL_PIT`;
- `git diff --check`;
- `git diff --cached --check`;
- `git show --format= --check HEAD`;
- protected PIT fingerprint;
- protected determinism fingerprint;
- unchanged `MODEL_RULES_VERSION` when no investment-rule change is intended.

Current protected identities at creation:

- PIT: `f1e73b27b80e41d96ff5e0fe990b482bad71b7220db0b5bd6a2f470d72786166`
- Determinism: `f8457910665391e39c234274cae4c029802c681211eebc7dba986a63000876f1`
- Model rules: `2026-08-23-allocation-room-integrity-v7`

If these legitimately change in a future approved architecture, update the canonical documents deliberately.

---

## 11. Forbidden shortcuts

Do not:

- fabricate portfolio inputs to bypass validation;
- run positive-capital development analysis unless explicitly requested;
- use contaminated historical data as alpha proof;
- silently accept caller assertions like `qualified=True`;
- remove blockers merely to make a real issuer pass;
- broaden source authority without evidence;
- convert CURRENT evidence into HISTORICAL_AS_OF authority;
- normalize EPS inside a comparability layer;
- merge or deploy because tests pass;
- touch Chromebook production during normal V2 development.

---

## 12. Global expansion

Long-term coverage should be global where legally and technically supportable.

Coverage maturity should conceptually distinguish:

1. DISCOVERY
2. OBSERVABLE
3. V2 ADMISSIBLE

Do not equate “we can fetch a ticker” with “we can safely admit it into the stock picker.”

Licensing / terms of use are part of source architecture.

---

## 13. Current V2 evidence chain

At creation:

```text
PR4C3  five-year reported diluted EPS
  ↓
PR4C4  issuer/security/common-class/listing identity
  ↓
PR4C5  corporate actions / share basis
  ↓
PR4C6  accounting reporting-subject continuity
  ↓
future real admission / adapter
  ↓
Expected Return inputs
```

Each synthetic layer proves mechanics, not real admission.

---

## 14. Updating project memory

After a normal merged PR:

- update `PAM_ROADMAP.md` if project state/next work changed;
- update the feature contract if needed;
- add to `DECISIONS.md` only for meaningful design decisions;
- do **not** edit `PAM_PROJECT_CONSTITUTION.md` unless a foundational principle changed.

This prevents documentation drift.

---

## 15. Agent handoff format

Before ending a substantial chantier, leave enough information for another agent to continue:

- exact base/head/merge state;
- what was implemented;
- what remains unsupported;
- tests;
- blockers;
- next recommended chantier;
- any unresolved product decision.

Do not rely on conversation memory as the only handoff.

---

## 16. Conflict handling

If two documents conflict:

1. identify the conflict explicitly;
2. check `PAM_PROJECT_CONSTITUTION.md`;
3. check the most specific active technical contract;
4. check owner instructions;
5. do not silently reinterpret investment philosophy.

---

## 17. Security and privacy

Never commit:

- passwords;
- API secrets;
- tokens;
- private user identifiers;
- private SEC User-Agent contact values;
- local credentials.

Do not reproduce secrets found in logs or Git metadata in reports.

---

## 18. Short operating mantra

> Verify the state.
> Understand the contract.
> Change the smallest thing.
> Preserve provenance.
> Fail closed.
> Test adversarially.
> Do not promote authority implicitly.
> Leave a clean handoff.
