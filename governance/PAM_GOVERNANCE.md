# PAM Governance

> Canonical administrative operating model for PAM.

## 1. Authority model

The CEO / Owner retains final authority over the Constitution, Governance,
Strategy, investment philosophy, model authority, material model policy,
commercialization direction, regulatory posture, role authority, material legal
risk decisions, production authority, deployment and canonical merges.

The following document classes are `CEO_PROTECTED`:

- `PAM_PROJECT_CONSTITUTION.md`;
- `governance/PAM_GOVERNANCE.md`;
- `governance/PAM_STRATEGY.md`;
- `DECISIONS.md`, the canonical Decision Registry;
- `governance/roles/*.md`, the role charters.

Roles may read, criticize and propose amendments to these documents. They may
prepare a Governance Amendment Proposal. They may not amend a protected document
as an ordinary operational action. A protected amendment requires explicit CEO
approval, and the CEO may explicitly order an amendment at any time.

```text
PROPOSAL AUTHORITY != AMENDMENT AUTHORITY
NO SELF-EXPANSION OF AUTHORITY
NO SELF-AMENDMENT OF ROLE CHARTER
```

No role may reinterpret a protected document as permission to gain new powers.

## 2. Decision Registry

`DECISIONS.md` remains PAM's one canonical Decision Registry. Do not create a
duplicate registry. It is append-only institutional history: prior decisions are
not silently rewritten. A correction or supersession is recorded in a new entry
and links the earlier entry through `SUPERSEDED_BY` where appropriate.

Appending an already-approved CEO decision may be performed through an authorized
Governance Sync. A substantive policy change still requires CEO approval.

## 3. Merge and production authority

Only the CEO / Owner authorizes merges to canonical branches. A role may declare
work technically ready, but that declaration never grants merge authority.

Technical review states are:

- `MERGE READY`;
- `CORRECTION REQUIRED`;
- `BLOCKED`.

No role may deploy, grant production authority or promote V2 unless the CEO has
explicitly authorized that separate action.

## 4. Roles, routing and ownership

The Program Manager is the primary CEO interface and normally routes work to the
minimum necessary specialist. The CEO may override routing at any time.

PAM Financial Systems and PAM Media & Communication are organizational activities,
not autonomous agents, legal entities or separate repositories. The CEO retains
overarching strategy. Specialists remain shared according to their mandates;
the PM coordinates shared priorities, dependencies and meaningful cross-activity
conflicts, with visibility into material commitments and outcomes.

Every Work Order has exactly one primary responsible role:

```text
SINGLE OWNER PER WORK ORDER
```

Other roles are consulted only when needed. A specialist decides only within its
charter; the Program Manager coordinates cross-role work; the CEO decides
protected, strategic and authority-bearing matters.

Default escalation:

```text
Role
  ↓
Program Manager
  ↓
CEO
```

Specialists are available when legitimately invoked within an authorized mandate.
Permanent role activation classes `ACTIVE`, `ON_CALL`, `WATCH`, `DORMANT` and
`ACTIVE BY TASK` are retired. Availability is not continuous work or permission
for self-activation, autonomous coordination, recurring execution or unsupervised
Codex tasks. Do not manufacture work merely because a role exists.

Preserve Work Order and blocker statuses such as `QUEUED`, `BLOCKED`, `COMPLETED`
and `TRIGGER-BASED`, and capability statuses such as `UNAVAILABLE` or `UNSUPPORTED`.
Removing a role label does not complete, reopen or authorize a task or capability.

### Bounded ordinary-work discretion

Reversible ordinary steps already covered by an explicitly approved mandate do
not need unnecessary repeated PM approval. Marketing & GTM may organize editorial
planning, research and draft preparation within its already-approved Blossom
mandate, with PM visibility and shared-resource coordination. CEO approval before
publication remains required. No autonomous posting, paid campaign, new product
launch, new commercial commitment, unauthorized data publication or unapproved
spending is permitted. Escalate meaningful cross-activity conflicts through the
PM; protected and authority-bearing decisions remain CEO-only. Ordinary
operational discretion is not protected authority or permission to expand scope.

### Transitional charter and instruction consistency

WO-PAM-REFORM-02 establishes organization-level policy only; individual charters,
AGENTS.md and external agent instructions await separately authorized migration
under WO-PAM-REFORM-03. Stale permanent activation labels do not control role
availability, but all existing role-specific authorization constraints and
prohibitions remain binding. No new discretionary authority beyond an existing
approved mandate may be exercised until the affected charter and external agent
instructions are updated. This transition grants no self-amendment or ability to
resolve an authority ambiguity in favor of broader powers; escalate it instead.

## 5. AI resource governance

Finite AI subscription resources are an organizational resource. Apply:

- `MINIMUM NECESSARY CONTEXT`;
- `MINIMUM NECESSARY CAPABILITY`;
- `REPORT PROPORTIONALITY`.

Use the smallest context, model capability, reasoning and output compatible with
reliable completion. Never sacrifice correctness merely to save resources.

Output budgets are `SHORT`, `STANDARD` and `DETAILED`. The default is `STANDARD`.
Use `DETAILED` only when the task genuinely needs a durable detailed reference.

## 6. Codex task recommendation

Every Codex task must be accompanied by exactly one recommended model, one
reasoning level and one short reason. Use the minimum sufficient capability with
high confidence. The recommendation is displayed immediately before—and is not
part of—the Codex prompt:

```text
Model: <one model>
Reasoning: Low / Medium / High / XHigh
Why: <short reason>

<separate Codex prompt>
```

Do not list alternative models unless the CEO explicitly asks.

## 7. Work Orders

A Work Order is a bounded mission from the Program Manager to one primary role.
It states the objective, why now, minimum context, mandatory sources, authority,
prohibited actions, deliverable, output budget, task complexity, resource
guidance, repository-change expectation and status.

The Work Order grants only the authority it states. Difficulty does not authorize
scope expansion or a new architecture program.

## 8. Handoffs and Team Inbox

Normal inter-role communication uses a compact Handoff Packet. Transfer full
conversation histories or detailed supporting material only when necessary.

`PAM_TEAM_INBOX.md` contains durable unresolved inter-role questions, not chat or
conversation history. A handoff does not transfer decision or merge authority.

## 9. Governance Sync

Normal conversation must not cause constant repository writes. Batch durable
institutional changes through a Governance Sync when justified by a canonical
merge, durable CEO decision, specialist handoff changing canonical state, blocker
closure, milestone or stage transition, or enough queued updates to warrant one
repository mutation.

```text
MINIMUM NECESSARY REPOSITORY MUTATION
```

Do not perform a Governance Sync for casual discussion without durable
consequence. A Governance Sync never grants authority to amend a `CEO_PROTECTED`
document. Such a change requires pre-existing explicit CEO amendment
authorization. `DECISIONS.md` may append an approved decision; it may not silently
rewrite history.

## 10. Operational memory

- `PAM_CURRENT_STATE.md` is the two-to-five-minute canonical snapshot.
- `PAM_WORK_QUEUE.md` records committed operational work and its state.
- `PAM_TEAM_INBOX.md` records durable unresolved inter-role questions.
- `PAM_WORKLOG.md` records compact institutional completion history.
- `PAM_OPPORTUNITY_BACKLOG.md` holds ideas that are not committed work.

Only a `PROMOTED` opportunity may become a Work Order or roadmap candidate.

## 11. Non-autonomy rule

ChatGPT roles and projects do not pretend to wake or coordinate one another
autonomously. They work only when legitimately invoked or routed within an
authorized mandate. Callable-role availability and ordinary-work discretion do
not authorize recurring execution or unsupervised Codex tasks. Do not create
fictional employee activity, conversations or logs. The separate previously
authorized monthly blocker-signal watch retains only its existing signal scope;
it does not invoke specialists or reopen blockers automatically.

## 12. Unattended development-orchestration pause

By CEO decision dated 2026-10-26, new implementation work toward unattended
Codex/development orchestration is paused. Preserve historical research,
experiments, GitHub issues, security findings, blockers and evidence. Mock-only
tests remain mock-only, never real-worker certification. The pause does not
authorize installing, uninstalling, disabling, restarting or operating
infrastructure, changing billing or spending, or modifying production.

The separate previously authorized monthly blocker-signal monitoring remains
unchanged. Any restart of unattended development requires a new explicit CEO
decision and appropriate safety/cost evidence; earlier orchestration objectives,
queued work or generic automation principles do not override this pause. It is
neither a host-strategy replacement nor permission to close issues or erase
historical acceptance limits. Bounded, explicitly authorized attended work remains
subject to its own mandate and all existing safety and financial gates.

## 13. AI-native Financial Systems coordination and readiness

The CEO-selected 2026-10-27 Financial Systems reform is described in
[`docs/strategy/PAM_FINANCIAL_SYSTEMS_AI_NATIVE_REFORM.md`](../docs/strategy/PAM_FINANCIAL_SYSTEMS_AI_NATIVE_REFORM.md).
The organizational Program Manager retains coordination across **both** PAM
activities. The proposed Financial Systems Command Center is a task-specific
research environment, not an additional autonomous governor or a replacement
for the Program Manager. Research and Portfolio Intelligence are likewise
proposed Project environments, not self-invoking roles.

No cross-Project interaction, account/broker visibility, Blossom browsing,
scheduled access, external integration or unattended execution is assumed.
Use verifiable supported interactions, the smallest practical handoffs and
explicitly recorded user effort; human transfer is the fallback until tested.

Financial research controls continue to require traceable source facts,
explicit assumptions, risk-proportionate independent checks and versioned
methods. Significant research records belong in tiered memory; secret or
private portfolio data require separately protected storage and permissions.
No automatic rule improvement, data authority or research-output promotion.

`RESEARCH-READY`, `PORTFOLIO-READY` and `ROUTINE-READY` are
**scoped experimental capability milestones**, each requiring a documented
evaluation and explicit owner acceptance. They confer no production,
investment-policy, trade, deployment, V1 replacement, V2 promotion or
legacy-retirement authority. The V1/V2 shadow and promotion gates remain
separate and unchanged.

Preparing a three-Project pilot and performing read-only Mac/Chromebook/PC
inventories are separate Work Orders needing explicit bounded authority.
Device access, movement, deletion or cleanup is not granted here. Existing
unattended-development pause, $0 external financial-data-cost constraint,
source licensing and the authorized Media & Communication scope persist.
