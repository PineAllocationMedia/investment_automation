# PAM local preflight v1

## Purpose

`./pam_preflight --base <ref-or-sha>` validates one exact committed PAM `HEAD`
against the fixed trusted local V2 integration target. The supplied base remains
an explicit operator assertion, but it is accepted only when its resolved commit
equals the independently resolved commit at
`refs/remotes/origin/model-v2/expected-return-challenger`. It is a local
orchestration surface over the existing validation planner and discovered
unittest runner. It does not define a second tier matrix, accept a
caller-selected target or tier, contact GitHub, fetch Git objects, install
dependencies, or grant investment, merge, deployment, production or V2-promotion
authority.

The command is intended for the final committed candidate before PR or review. A
result is not valid for later commits.

## Exact change-set semantics

The trusted remote-tracking target and supplied base must each resolve locally
and independently to the same exact commit. Equality is required; ancestry or a
merge base is insufficient. The operator must fetch and verify target freshness
before preflight because preflight is deliberately network-independent. This
prevents a caller from selecting a later ancestor that hides an earlier sensitive
change and makes the apparent diff cheaper.

The command prints the trusted target, accepted base and `HEAD` SHAs, requires a
clean tracked/staged/untracked Git state, and computes the complete changed-path
inventory with:

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
2. independently resolve the fixed trusted local integration target;
3. resolve the supplied base and require exact equality with that trusted target;
4. resolve committed `HEAD` exactly to a commit;
5. require a clean source index and worktree, including untracked files;
6. compute the complete trusted-base-to-`HEAD` path inventory;
7. select the tier through the existing planner;
8. run base-to-`HEAD` `git diff --check`, `git diff --cached --check`, and
   `git show --format= --check <head-sha>`;
9. create a disposable detached Git worktree at the resolved candidate SHA and
   verify its exact `HEAD` and clean state;
10. extract protected identities from the detached candidate's canonical static
   source and test assertions;
11. for non-documentation tiers, require the exact `major.minor.patch` version in
   `.python-version` and the locked dependency environment, then expose the
   physical resolved temporary directory to validation subprocesses so
   symlink-guarded tests see the same filesystem location on macOS;
12. run the planner, runner and preflight unit tests as fast self-checks from the
   detached exact-HEAD worktree;
13. compile the same reviewed Python locations compiled by CI in that worktree;
14. execute `STANDARD` or `FULL_PIT` through
    `scripts/ci_unittest_runner.py` in that worktree;
15. reverify the original repository `HEAD` and cleanliness plus the detached
    candidate `HEAD` and cleanliness;
16. remove the disposable worktree successfully before reporting `PASS`.

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
PAM_PREFLIGHT_TRUSTED_TARGET_SHA=<sha-or-UNRESOLVED>
PAM_PREFLIGHT_HEAD_SHA=<sha-or-UNRESOLVED>
PAM_PREFLIGHT_GIT_CLEAN=true|false
CI_VALIDATION_TIER=DOCS_ONLY|STANDARD|FULL_PIT|UNRESOLVED
CI_CHANGED_FILE_COUNT=<integer-or-UNRESOLVED>
CI_HEAVY_PIT_REQUIRED=true|false|UNRESOLVED
PAM_MODEL_RULES_VERSION=<identity-or-UNRESOLVED>
PAM_PIT_FINGERPRINT=<identity-or-UNRESOLVED>
PAM_DETERMINISM_FINGERPRINT=<identity-or-UNRESOLVED>
```

Unexpected skips, target/base disagreement, mutable source or detached worktree
state, cleanup failure, malformed identities, malformed or mismatched exact
Python pins, planner or runner failures, interrupted execution, incomplete
discovery, dependency drift and unavailable required tools cannot produce `PASS`.
There are no skip, fast, docs-only, PIT-disable, manual tier or caller-controlled
target flags.

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

Preflight assumes the fixed trusted remote-tracking target, explicit matching
base object and exact candidate `HEAD` already exist locally and are externally
fresh; it makes no network call to repair or refresh them. It validates the exact
Python pin and installed locked environment but does not create or repair either.
The wrapper prefers `PAM_PREFLIGHT_PYTHON` when explicitly set, then `.venv`, then
`python3`; every choice remains subject to the same exact pin and dependency gate.
Validation runs from a disposable detached Git worktree and never checks out,
resets, cleans or detaches the developer worktree. It does not wait for GitHub
Actions and does not replace independent Architecture & Audit review. Protected
identity reporting observes current repository identities; PASS neither requires
them to equal the base nor authorizes their change. A&A and CEO governance retain
that authority decision.
