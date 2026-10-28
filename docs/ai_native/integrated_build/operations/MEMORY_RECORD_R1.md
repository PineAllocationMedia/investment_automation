# M4 R1 — Research memory, corrections and protected-data separation
**Owner:** Command Center for proposed analysis records; PM for GitHub governance routing.  
**State:** `SCHEMA_CANDIDATE / NO_AUTOMATIC_ARCHIVAL`.

## Three memory tiers
- **Tier I — GitHub governed method/policy memory:** CEO-approved instructions, prompt/method versions, decisions, schema and selected de-identified lessons only. Protected changes and merges retain explicit CEO authority. `DECISIONS.md` remains the **only** Decision Registry.
- **Tier II — research record and evidence references:** dated significant analyses, eligible source locators, evidence/assumption IDs, versioned conclusions and subsequent qualified outcomes, only where source rights/privacy allow. A source locator or checksum is not immutable original evidence unless the source actually remains recoverable.
- **Tier III — protected private financial records:** user account snapshots, Blossom/screenshots, holdings, amount/weights, broker and transaction details, tax lots, credentials and sensitive archives. Never embed these in public GitHub, issues, PR bodies, logs or Media work. Separate storage access and retention require authorization.

## Research-history proposal (append-only semantics)
A draft `RESEARCH_HISTORY_PROPOSAL` contains:
```text
ANALYSIS_ID                    unique immutable analytical identity
REPORT_ID / PARENT_REPORT_ID  original report and later addendum linkage
RECORDED_AT / AS_OF / CUTOFF  separate observation, research freeze and reporting time
OBJECTIVE / STRATEGY_VERSION  CEO mandate and actual approved strategy
INSTR_VERSION / METHOD_VERSION actual loaded configuration or UNKNOWN_NOT_LOADED
SOURCE_REFERENCES             exact eligible URLs/accessions, periods, rights and status
FACT_IDS / CALC_IDS           recoverable S/F/K and actual arithmetic checker status
SCENARIO_IDS                  hypotheses, horizon, terminal/distribution assumptions
THESIS / COUNTERCASE          conclusion and strongest opposing case
CONFIDENCE                    factual vs forecast confidence, with reasons
UNKNOWN_OR_CONFLICTED         decisive missing fields with provenance
DECISION_IMPACT               no action / conditional / supported research, not trade execution
PRIVACY_TIER                  I / II / III, with exact routing and review owner
ARCHIVAL_STATUS               PROPOSED_NOT_COMMITTED until real approved write
NEXT_REVIEW                   optional context, not authorization to schedule
```
Do not create an automatic GitHub write from this proposal. If an actual artifact is accessible elsewhere, reference its verified locator and integrity digest; do not pretend ChatGPT Projects can see each other's files.

## Corrections and lessons
Historical reports are **never silently rewritten**. A correction is a new, dated addendum with `PARENT_REPORT_ID`, `CHANGED_FACT_IDS`, `WHY`, `SOURCE_NEW`, `IMPACT` and `APPROVAL` where required. Research outcome reviews distinguish bad evidence, missing data, weak valuation, thesis breaks, normal variance and hindsight; returns alone never justify raising model confidence or changing policy.

Prompt/method improvements have a versioned `CHANGE_PROPOSAL`: motivation, failure case, countercase, prior method, expected benefit, unchanged safeguards, real validation case and one independent non-training case when feasible, reviewer and authorization. Approved operational changes must not amend protected policy or promote V1/V2 without separate CEO authority. This is an **improvement mechanism**, not self-training or an autonomous agent.
