# PAM local preflight v1

## Purpose

`./pam_preflight --base <ref-or-sha>` validates one exact committed PAM `HEAD`
against one explicit Git base. It is a local orchestration surface over the
existing validation planner and discovered unittest runner. It does not define a
second tier matrix, accept a caller-selected tier, contact GitHub, fetch Git
objects, install dependencies, or grant investment, merge, deployment, production
or V2-promotion authority.

The command is intended for the final committed candidate before PR or review. A
result is not valid for later commits.

## Exact change-set semantics

The supplied base must resolve locally to a commit. The command resolves and
prints the exact base and `HEAD` SHAs, requires a clean tracked/staged/untracked
Git state, and computes the complete changed-path inventory with:

```text
git diff --no-renames --name-only -z <base-sha> <head-sha>
```

The complete path set is passed to `scripts/ci_validation_plan.py`. An empty set
therefore follows the canonical conservative `FULL_PIT` route. Rename detection
is disabled so both a removed sensitive path and its destination remain visible
to the planner. Unknown or ambiguous paths retain the planner's `FULL_PIT`
classification.

## Required order

The implementation stops at the first failed required control:

1. verify the expected repository root and Git availability;
2. resolve the explicit base exactly to a commit;
3. resolve committed `HEAD` exactly to a commit;
4. require a clean index and worktree, including untracked files;
5. compute the complete base-to-`HEAD` path inventory;
6. select the tier through the existing planner;
7. run base-to-`HEAD` `git diff --check`, `git diff --cached --check`, and
   `git show --format= --check <head-sha>`;
8. extract protected identities from their canonical static source and test
   assertions;
9. for non-documentation tiers, require the repository's Python major/minor and
   locked dependency environment;
10. run the planner, runner and preflight unit tests as fast self-checks;
11. compile the same reviewed Python locations compiled by CI;
12. execute `STANDARD` or `FULL_PIT` through
    `scripts/ci_unittest_runner.py`.

`DOCS_ONLY` still performs every Git and protected-integrity control, but skips
environment validation, compilation and unittest execution as canonical CI does.
The fast checks are early-failure checks only and never replace the selected
discovered suite.

## Stable final summary

Every normal completion prints these keys in this order and returns nonzero on
failure:

```text
PAM_PREFLIGHT_STATUS=PASS|FAIL
PAM_PREFLIGHT_BASE_SHA=<sha-or-UNRESOLVED>
PAM_PREFLIGHT_HEAD_SHA=<sha-or-UNRESOLVED>
PAM_PREFLIGHT_GIT_CLEAN=true|false
CI_VALIDATION_TIER=DOCS_ONLY|STANDARD|FULL_PIT|UNRESOLVED
CI_CHANGED_FILE_COUNT=<integer-or-UNRESOLVED>
CI_HEAVY_PIT_REQUIRED=true|false|UNRESOLVED
PAM_MODEL_RULES_VERSION=<identity-or-UNRESOLVED>
PAM_PIT_FINGERPRINT=<identity-or-UNRESOLVED>
PAM_DETERMINISM_FINGERPRINT=<identity-or-UNRESOLVED>
```

Unexpected skips, malformed identities, planner or runner failures, interrupted
execution, incomplete discovery, dependency drift and unavailable required tools
cannot produce `PASS`. There are no skip, fast, docs-only, PIT-disable or manual
tier flags.

## Isolation helper decision

`scripts/run_isolated_tests.py` remains separate. It deliberately copies a
reviewed subset of repository surfaces and creates disposable Git history, so it
cannot establish the exact committed repository `HEAD` required by this contract.
The canonical planner and runner remain the preflight execution architecture.

## Tooling evaluation (report only)

No tool below is installed or configured by this chantier.

| Tool | Expected benefit | Compatibility | Maintenance / noise | Can remain $0 | Recommendation |
| --- | --- | --- | --- | --- | --- |
| Ruff | Fast linting and import/style defect detection | High; Python 3.12 and the current layout are supported, but an initial baseline/config review is required | Low after baseline; potentially noisy at first | Yes, open source and local/CI-capable | `ADD LATER` |
| mypy | Earlier detection of type-contract drift | Moderate; the mixed legacy/new codebase would require gradual scope and third-party typing decisions | Medium to high if enabled broadly | Yes, open source and local/CI-capable | `DEFER` |
| CodeQL | Security/data-flow scanning beyond unit tests | Technically compatible with GitHub-hosted analysis; value is secondary for this private, validation-heavy Python repository and eligibility/cost depend on repository/account terms | Medium alert triage and workflow upkeep | Not guaranteed for a private repository; verify current GitHub terms before adoption | `DEFER` |
| Dependabot | Automated dependency-update visibility and security advisories | High for the pinned requirements files, subject to careful lockfile and FULL_PIT validation | Medium PR churn and update triage | Generally available on GitHub, but current plan/repository terms should be verified | `ADD LATER` |

Tool adoption must be a separate reviewed change. None may weaken the existing
validation tiers or replace deterministic tests.

## Nonclaims and limitations

Preflight assumes the explicit base object and exact candidate `HEAD` already
exist locally; it makes no network call to repair missing objects. It validates
the installed locked environment but does not create or repair it. It does not
wait for GitHub Actions and does not replace independent Architecture & Audit
review. Protected identity reporting observes existing repository authority; it
does not authorize identity updates.
