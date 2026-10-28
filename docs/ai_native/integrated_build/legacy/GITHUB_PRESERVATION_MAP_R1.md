# M6 — GitHub tracked-knowledge preservation and AI-native reuse map (R1)

**Work Order:** `WO-FIN-FS-R1-M6-GITHUB-READONLY-PRESERVATION`  
**Observation date:** 2026-10-28. **Scope:** exact tracked Git trees, **not a full local/device inventory**.  
**Sources:** GitHub REST tree reads with `recursive=1` (both responses `truncated=false`), the seven V1-only technical reports read at `main`, V1 `BASELINE_V1_FREEZE.md`, Architecture & Audit charter, CEO build-first decision and integrated R1 delivery plan. The [machine-readable manifest](./GITHUB_TRACKED_MANIFEST_R1.json) holds every GitHub tracked path and both object identities.

## 1. Verified tree boundary

| Snapshot | Commit | Tree | Tracked files |
|---|---|---|---:|
| V1 operational `main` | `c5fc27c82c29c2a6027eccee245098c4a072fdf1` | `26a69bb0b2185ab141af0763da2d965602c8346b` | 288 |
| V2/AI-native `model-v2/expected-return-challenger` | `400978d3352bd23a9ddc54341b95cf27773507db` | `e3d099480b64783429ccf1fc5a20a61d9bd9c3eb` | 826 |

**Union of distinct tracked paths:** 833. By the *same exact path*: `232` identical Git blob IDs; `49` different blobs; `7` unique to `main`; `545` unique to the V2 integration tree. Conservation: 288 = 7 + 232 + 49; 826 = 545 + 232 + 49; 833 = 7 + 545 + 232 + 49.

These are **file-path comparisons**, not counts of unique intellectual ideas, lost files, or verified backups. A rename/copy, Git history, local-only data or other branch can change the knowledge classification without changing these arithmetic counts.

## 2. Seven V1-only historical reports: preserve by reference, do not move

| Canonical V1-only path | Git blob SHA | Unique documented lesson and R1 implication |
|---|---|---|
| [`ALLOCATION_ROOM_INTEGRITY_IMPACT.md`](https://github.com/PineAllocationMedia/investment_automation/blob/c5fc27c82c29c2a6027eccee245098c4a072fdf1/ALLOCATION_ROOM_INTEGRITY_IMPACT.md) | `831644c61f03edd5f9f1fac9a2f805203faf06fb` | Shared emerging-satellite capacity and allocation-room integrity; V1's numeric High-CAGR caps are **historical policy**, not automatic R1 global strategy or portfolio rule |
| [`COMPACT_REPORT_OPERATIONAL_GUIDANCE_AUDIT.md`](https://github.com/PineAllocationMedia/investment_automation/blob/c5fc27c82c29c2a6027eccee245098c4a072fdf1/COMPACT_REPORT_OPERATIONAL_GUIDANCE_AUDIT.md) | `d768a7957dc759224e767761ba6f9eae8755a015` | Report triage distinguishes genuinely actionable evidence from dormant or stale diagnostic surfaces; R1 must not turn "no evidence" into compulsory action or a recurring schedule |
| [`DEEP_DRAWDOWN_ALLOCATION_SAFEGUARD_IMPACT.md`](https://github.com/PineAllocationMedia/investment_automation/blob/c5fc27c82c29c2a6027eccee245098c4a072fdf1/DEEP_DRAWDOWN_ALLOCATION_SAFEGUARD_IMPACT.md) | `ea704c97026b0e3c358e2ce8e05689a250f588df` | Mixed lots and realistic account exposure, structural thesis vs price drawdown; preserve exceptional lifecycle reasoning without copying automatic buy-the-dip policy |
| [`MIXED_COST_BASIS_REPORTING_AUDIT.md`](https://github.com/PineAllocationMedia/investment_automation/blob/c5fc27c82c29c2a6027eccee245098c4a072fdf1/MIXED_COST_BASIS_REPORTING_AUDIT.md) | `721ebb9f3e71c1c0283d7d1ff50019d5d02589ba` | Multi-currency acquisition cost must not be summed without compatible FX/date/account basis; PI should label unsupported basis/after-tax outcomes unavailable |
| [`PROVENANCE_FRESHNESS_IMPACT.md`](https://github.com/PineAllocationMedia/investment_automation/blob/c5fc27c82c29c2a6027eccee245098c4a072fdf1/PROVENANCE_FRESHNESS_IMPACT.md) | `cdb4653695e1626aeb5cf035d2efe43cb5adbc29` | Manual, sourced, proxy and cached facts have distinct provenance and freshness precedence; R1 should carry them with claim-level status, never silently upgrade |
| [`RESEARCH_SEMANTIC_INTEGRITY_REPORT.md`](https://github.com/PineAllocationMedia/investment_automation/blob/c5fc27c82c29c2a6027eccee245098c4a072fdf1/RESEARCH_SEMANTIC_INTEGRITY_REPORT.md) | `98fec410b7852a1ea93ef32235ed5fcbfa0a946d` | Broker targets differ from fundamental fair-value estimates; analyst confidence and source authority are separate; R1 valuation must not conflate them |
| [`VALIDATION_ARCHITECTURE_IMPACT.md`](https://github.com/PineAllocationMedia/investment_automation/blob/c5fc27c82c29c2a6027eccee245098c4a072fdf1/VALIDATION_ARCHITECTURE_IMPACT.md) | `7d21eaac5a1cd49ac951b2632c4b46d824296a71` | Historical current-score/backtest and walk-forward diagnostics must not become authentic forward/PIT authority; R1 research or post-assembly evaluation must preserve this boundary |

**Preservation outcome:** `GITHUB_REFERENCE_RETAINED`, not duplicated, archived, copied, deleted or migrated. These seven report paths are absent from the V2 *tree at the same path*, but each remains reachable in `main` at the pinned blob identity. This does **not** prove a full content-level uniqueness test across renamed paths or other branches.

## 3. V2-only tracked knowledge and selective reuse

The V2 tree adds 545 path-only files, including the integrated AI-native CC/IR/PI instruction candidates, CEO-confirmed R1 snapshots, source/valuation/portfolio methods, math, report and in-memory handoff components, governance, research evidence, tests and Media documentation. By exact root, the largest V2-only groups are `docs/` (252), `tests/` (145), `economic_facts/` (69), `src/` (28), `governance/` (20), `pit_comparison/` (9), `scripts/` (7), `ai_native/` (5) and `analysis_capabilities/` (5). These are counts of paths, **not evidence of migration readiness or live feature installation**.

Selective knowledge reuse—not wholesale runtime porting:

- **V1 baseline and risk controls:** cite `BASELINE_V1_FREEZE.md` in `main`; production baseline remains frozen; preserve provenance, contribution-room, anti-look-ahead, versioning and cost semantics as knowledge. Avoid copying hard-coded allocation caps into a new strategy without explicit CEO policy.
- **V2 research/evidence chain:** use `economic_facts/`, `pit_comparison/` and documented qualification findings as references for issuer identity, period/basis, valuation and authentic PIT checks. Their mere presence does not automatically qualify new global securities or authorize using proprietary source content.
- **AI-native minimal runtime:** `ai_native/{contribution_math,evidence_math,reporting,integrated_flow}.py` and `docs/ai_native/integrated_build/` supply bounded components; source acquisition, real private Blossom access, secure case retention and full 36-decision acceptance remain unresolved. Preserve genuinely reusable prompts and evidence checks without duplicating obsolete V1/V2 stacks.
- **Media & Communication:** `docs/marketing/` and approved Blossom editorial records remain separate, unchanged in scope. Never mix private portfolio data into these paths.

## 4. Missing independent inventories and CEO gates

**NOT SEEN:** local Mac, PC/WSL, Chromebook filesystem or untracked/unpushed branches; uncommitted working trees, ignored files, caches, terminal history, ZIPs, downloads, actual production V1 Chromebook state, private brokerage/Blossom account records, licensing permissions for local archives and third-party document bytes. GitHub's tracked trees cannot establish that these local artifacts exist, are unique or are safely backed up.

Later M6 device scopes require **separate bounded CEO authorization**, with minimal read-only path/size/hash/type inventory, device-by-device restrictions and independent verification of GitHub counterparts. Preserve before transferring; confirm recoverability before cleanup; no deletion, movement, uploads of secrets, client portfolios or restricted binaries without separate explicit approval. Desktop inventories are **not a prerequisite for continuing independent authorized R1 functional assembly work**.

## 5. Development sequence and next handoff

The binding 2026-10-28 sequence is **complete functional assembly for all 36 decisions first**, with necessary small component/security/arithmetic checks during construction, then one comprehensive integrated assessment and separate readiness/production gates. Do not replace construction with an early "first real financial pilot." M7c's three GitHub access receipts are installation-context evidence only, not a whole-system pass. The M6 GitHub inventory is one Workstream B sub-deliverable; the other workstream must continue closing material functional gaps, especially supported cost economics, governed memory/storage, context-sensitive prompt assembly and actual allowed handoffs.

**Status:** `M6_GITHUB_TRACKED_INVENTORY_COMPLETE_FOR_PINNED_TREES / LOCAL_DEVICE_INVENTORIES_BLOCKED_BY_SEPARATE_AUTHORITY / NO_MIGRATION_OR_CLEANUP`. Architecture & Audit specialist review is not claimed; keep source/report distinctions explicit. No gate READY or production authority follows.
