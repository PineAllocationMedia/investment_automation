# Work Order — M2 bounded non-ranking opportunity research triage

**ID:** `WO-FIN-FS-R1-M2-OPPORTUNITY-TRIAGE`  
**Primary role:** Program Manager / Chief of Staff (direct implementation on CEO-requested continuation; Investment Research methodology unchanged).  
**Complexity:** STANDARD. **Status:** CANDIDATE / PR REVIEW REQUIRED.

**Objective / why now:** After CEO-confirmed PR #279 merge and issue #275 closeout, implement a missing concrete piece of the approved 36-decision R1 release: a private, manual, provenance-aware research queue for 1–30 nominated securities. Prior T09–T13 research demonstrates an exploratory multi-country sample but not a live investability screen. Decision #19 remains PARTIAL until real discovery, checks and acceptance.

**Authority and sources:** CEO approved build-first R1 sequence 2026-10-28; Constitution → Governance → Current State → PM charter → this WO; `AGENTS.md`, R1 delivery plan, decision coverage #19, M1 session bridge, M2 source-fusion ledger and M7a report assembler. Base V2 exactly as verified after PR #279. No CEO-protected file edits.

**Output:** `ai_native/opportunity_triage.py`, bounded unit tests, optional `opportunity_triage_inputs` supported only on IR-capable M7a routes, 5 construction-seam tests, nonprotected research/runbook documents, narrow decision-coverage update (#19 remains PARTIAL), explicit capability/limits and private no-ranking status.

**Evidence & validation:** Sources must come exclusively from original supplied IR fact references and private M2 observations at the same analysis ID/cutoff. Refuse unknown IDs and mismatched request envelopes; keep gaps explicit and never imply issuer data were fetched. Unit tests are synthetic; integration/full checkout tests must be honestly identified as executed or NOT_RUN.

**Prohibitions / resources:** No automatic cross-Project invocation, public portfolio inference, listing/screening, policy selection, quality/durability/ER computation, ranking, buy/trade suggestion, source authentication, rights escalation, actual private holdings in GitHub, schedules, external data spending (hard $0), device cleanup, production, V1/main changes, branch retirement, protected amendments or self-merge.

**Handoff / end:** Stop after proposed PR on `model-v2/expected-return-challenger`, do not merge; CEO decides. Remaining work: observed multi-source permitted discovery, analyst candidate judgment, actual three-Project CC→IR→PI→CC demo and end-of-assembly acceptance.
