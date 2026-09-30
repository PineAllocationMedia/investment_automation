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

Canonical role states are `ACTIVE`, `ON_CALL`, `WATCH` and `DORMANT`. A charter's
existence does not imply continuous activity. `ACTIVE BY TASK` means the role is
active only for an explicitly bounded task. Do not manufacture weekly work merely
because a role exists.

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
autonomously. They work only when invoked, routed or otherwise legitimately
activated. Do not create fictional employee activity, conversations or logs.
