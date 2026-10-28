# Work Order — M6 GitHub tracked-knowledge preservation inventory

**ID:** `WO-FIN-FS-R1-M6-GITHUB-READONLY-PRESERVATION`  
**Primary role:** Architecture & Audit for knowledge-recovery classification; **execution:** PM has prepared a bounded remote GitHub metadata inventory, **not** an independent Architecture & Audit review.  
**Status:** `GITHUB_TRACKED_INVENTORY_PREPARED / DEVICE_INVENTORIES_NOT_AUTHORIZED / NO_PRESERVATION_MOVE / NO_DELETION`.  
**Why now:** CEO reaffirmed 2026-10-28 *build all 36 design choices first, comprehensive system acceptance afterwards*. M6 is Workstream B, not a new AI-native investment research pilot. It preserves unique knowledge needed to simplify V1/V2 safely without discarding safeguards.

## Objective and expected result

Compare the **exact tracked trees** of V1 operational `main` and the AI-native/V2 integration branch, identify GitHub-only unique paths and changed historical records, and produce a durable metadata manifest plus a concise preservation/reuse map. Do not treat pathname absence as loss or GitHub presence as proof of preserved local archives.

**Inputs and order:** Constitution → Governance → Current State → PM role + Architecture & Audit role → this WO → CEO 2026-10-28 build-first Decision Registry entry → Strategy/Blueprint §8 and §10.0 → `DELIVERY_PLAN.md` and `DECISION_COVERAGE.md` → Git tree metadata and the seven main-only reports. `AGENTS.md` applies. Preserve V1's operational authority and V2 challenger status.

## Authority and prohibitions

Authorized actions: GitHub read-only tree/selected documentation inspection; creation of **new nonprotected inventory documents** on an isolated PR branch. No device remote scan, account/private-portfolio inspection, Mac/PC/Chromebook access, raw archive upload, untracked/ignored files assertion, GitHub cleanup, repository reorganization, file movement/deletion, branch rebase, policy change, new source costs, live tests or production/trading change. Hard $0 external financial-data cost. CEO alone approves merges, protected edits and any subsequent preservation transfer/cleanup. Do not restart paused unattended orchestration.

**Complexity/resource budget:** STANDARD; two Git tree reads, seven V1-only document inspections and static structural checks. No external services or local-machine dependency. Do not repeat scans unless a tree actually changes.

## Deliverable and stop criterion

- `GITHUB_TRACKED_MANIFEST_R1.json`: all tracked file paths in the two exact trees, source Git object IDs, byte counts and four diff states. Excludes file contents and private account data.
- `GITHUB_PRESERVATION_MAP_R1.md`: GitHub-only delta, seven unique V1 report lessons, R1 reuse boundaries, and separate remaining device permissions.
- Stop after verifying both tree snapshots are complete, counts reconcile, selected records are actually consulted, and opening one PR. Do **not** run a comprehensive integrated acceptance, declare all 36 complete, or merge.
