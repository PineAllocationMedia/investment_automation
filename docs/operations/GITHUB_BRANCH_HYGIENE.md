# PAM GitHub repository hygiene — operational procedure (nonprotected)

**Effective upon CEO merge of this PR:** operational process for the private PAM repository. **Owner:** organizational Program Manager. **Scope:** GitHub branches, PRs and issues only; no Chromebook/Mac/PC cleanup, financial data, model authority, production, or migration.

## Branch roles and preservation
- `main` is the frozen V1 operational authority, not a convenient common development base.
- `model-v2/expected-return-challenger` is the V2 challenger and AI-native R1 integration branch. Do **not** consolidate V1 and V2 by branch merging or change production without a separate CEO decision.
- Preserve divergent or unmerged refs until their unique commits, dependencies and purpose are explicitly resolved. Specifically preserve `codex/connector-mac-docsonly-proof-wo184-20261016`, `marketing/blossom-profile-scan-20261022` and `marketing/m1-top3-frontrunners-laggards-v1`.
- New development: create one short-lived, well-named branch per bounded Work Order, based on a verified canonical SHA. Target the correct canonical base and open one PR; retain the branch until CEO-authorized merge and safety checks.

## Closing merged branches
An ordinary merged feature branch can be proposed for deletion only when all are true:
1. The relevant PR is actually **merged** into the designated canonical branch; the exact HEAD SHA matches the PR's merged head.
2. That exact commit remains **reachable** from the current canonical successor (ancestry proof; not merely similar content).
3. The branch is neither canonical/protected nor a known divergent, worktree, operational, automation or evidence dependency. Check open PRs and known off-GitHub consumers; stop if unknown.
4. The target branch name and SHA are included in an explicitly authorized deletion scope. Check exact identity **again immediately before deleting**; no moving branch refs, rebasing, force pushes or history rewrite.
5. Each deletion has an auditable log. Reconcile live branch count and PR/commit reachability afterward before closing the cleanup issue.

GitHub branch auto-delete-after-merge is **not enabled** by this document. Enabling any GitHub setting or automation needs a separate explicit CEO decision after verifying it respects canonical and divergent refs. Branch protection/ruleset settings are a separate owner decision, not assumed available on the current private-repository plan.

## CEO-approved one-off cleanup #275
At the 2026-10-28 inspection, 240 branch names and original SHAs in issue [#275](https://github.com/PineAllocationMedia/investment_automation/issues/275) were checked against live GitHub, with 0 mismatches. The CEO explicitly approved deletion of those exact 240 refs only. The pinned manifest in `docs/operations/GITHUB_BRANCH_HYGIENE_APPROVED_20261028.tsv` and manual `scripts/gh_branch_hygiene_cleanup.py` implement fail-closed revalidation. **No actual deletion occurs merely because the code is merged.** Use authenticated `gh` on an explicitly authorized execution machine, with no secret in chat, and review the full 240-row manifest before execution.

From a fresh, read-only code checkout of V2 with the cleanup script available:

```bash
gh auth status
python3 scripts/gh_branch_hygiene_cleanup.py --start 0 --limit 20
# After a successful check-only run, the CEO-approved deletion may be executed:
python3 scripts/gh_branch_hygiene_cleanup.py --execute --start 0 --limit 20 --log /tmp/pam-branch-hygiene-20261028.jsonl
# Advance in bounded 20-branch batches: start=20, 40, ... 220.
```

Only the 240 pinned items are approved, **not** the two newer merged PR #276/#277 branches (reviewed separately), the two canonical references or three divergent branches. Do not move any refs as a substitute for deletion. Stop if local worktrees, external scripts or CI dependencies remain unresolved; the issue's checks cannot prove their absence. **Issue #275 stays open until confirmed actual deletion and audit.**

## Issues, PRs and repository memory
- Close stale/blocked issues only after classification `COMPLETED`, `SUPERSEDED` or `PAUSED` with a linked record; do not mass-close the historical unattended-orchestration issues without evidence or authorization.
- After CEO-authorized merge, record actual merge SHA and update affected nonprotected roadmap, work queue/state and relevant contracts **only if** a durable state transition warrants it; batch Governance Sync rather than writing after every casual message.
- Protect personal financial data, credentials, and private holdings from GitHub issues and PRs. Keep code/history recoverable and never misstate acceptance, CI or deployment.
- The constitutional `CEO_PROTECTED` rules, merge authority and the $0 external financial-data-cost policy remain unchanged.
