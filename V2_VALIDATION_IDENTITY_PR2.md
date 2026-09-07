# V2 PR2 — validation identity isolation

## Scope and base

Base: `ec0bf8b3f25730d0954b05d0dee6ab0d8fdfbdb9` on
`model-v2/expected-return-challenger`. Production `main` was independently verified
at `c5fc27c82c29c2a6027eccee245098c4a072fdf1`.
The feature branch was created from the exact integration commit, not the PR1 tip.

This changes validation/evidence semantics only. It neither approves an investment
implementation nor enables V2 decisions, shadow execution, promotion or deployment.
No investment configuration, model-rules constant, runtime restriction, tuning
threshold or tuning policy changes.

## Root causes

A — defective authority logic: Baseline trusted operating flags without explicit
lineage/schema/scope; generic walk-forward permitted missing authority; period
transformation discarded explicit denial; version-only/date-only selection could
mix model lineages. The additional date-only friction join could mix the evaluated
costs of otherwise separated same-date evidence. Its join keys change; its cost
formulas and assumptions do not.

B — reporting issues: old health output could call native V2's absent Baseline a
V1 approval failure. It now reports V2/NONE/NOT_ESTABLISHED as identity diagnostics,
not proof of production approval. Other presentation cleanup is deferred.

C — expected behavior: PR1 runtime isolation remains distinct from model identity.
Its positive-capital and production-purpose blocks remain intact.

## Identity and schemas

`src/model_identity.py` is the single code-owned identity constructor. There is no
CLI authority selector and no identity derived from paths, branch names or runtime
profile. Canonical lineages are V1 and V2; canonical authority values are
PRODUCTION, SHADOW_ONLY and NONE. V2 promotion is deliberately not implemented:
even a dictionary claiming V2/PRODUCTION fails production evidence predicates.

Native records on this branch carry:

```
model_lineage=V2
model_rules_version=2026-08-23-allocation-room-integrity-v7
validation_schema_version=2026-09-06-validation-identity-v4
validation_authority=NONE
baseline_id=""
baseline_status=NOT_ESTABLISHED
baseline_forward_eligible=false
strategy_validation_authority=false
```

The empty string is the canonical no-Baseline representation (including CSV).
The historical V1 config remains byte-for-byte unchanged and is not used to assign
a native V2 Baseline. Runtime launch mistakes do not change the code lineage.

Validation schema: `2026-08-23-validation-architecture-v3` →
`2026-09-06-validation-identity-v4`, because missing metadata no longer authorizes.
Manifest schema: `2026-08-24-decision-run-manifest-v1` →
`2026-09-06-decision-run-manifest-v2`, because lineage/scope participate in its
semantic fingerprint. Run ID/timestamp remain outside that fingerprint as before.
Rules version is unchanged; it is imported, not duplicated by the identity module.

## Authority contracts

Baseline requires explicit V1, PRODUCTION, the current rules and validation schema,
VALIDATION_BASELINE_V1, active start/status, positive finite capital, genuine
purpose, explicit nonlegacy basis, successful execution, critical-input/config
approval, dependency match and clean tracked state. Missing identity denies with
machine-readable reasons. Any supplied false prior eligibility remains false;
historical reads additionally require the original eligibility declaration.

Generic production strategy authority requires V1, PRODUCTION, a nonempty explicit
rules version, the current schema, manual/scheduled decision purpose,
EXPLICIT_DECISION_PURPOSE, POINT_IN_TIME_WALK_FORWARD, and explicit true authority.
JSON `true` and CSV `True` are accepted; missing, null, blank and other values do
not grant. Generic PIT evidence may describe another explicit V1 rules version;
current-version consumers must additionally match their requested rules cohort.
Baseline authority separately requires the current Baseline rules value.

Generic PIT authority and Baseline authority remain distinct. A complete, explicitly
authorized V1 pre-Baseline observation can support generic PIT validation without
being relabelled as Baseline-forward. A complete standalone analysis/allocation
record may contribute a scoped decision observation; it cannot constitute a paired
Baseline observation or an evaluable walk-forward period by itself.

## Pairing, selection and counting

History keys include lineage, rules, schema, authority scope and Baseline ID before
daily selection. Model-audit keys also separate mode and purpose. Walk-forward
constructs timelines independently in each identity partition; a V2 date cannot
replace a V1 snapshot or become a V1 endpoint.

Paired authority requires two records agreeing on all identity dimensions, nonempty
run ID, nonempty manifest fingerprint, mode, purpose and Baseline start. Each side's
eligibility is independently revalidated. Missing/conflicting fields deny both
paired authority grants. Manifest equality is necessary but not sufficient; this
PR does not dereference historical manifests or establish cryptographic approval.

Period conversion preserves scope, identity, rules, schema, run/manifest references
and explicit denial. Coverage, simulation-summary, model-audit, full-audit and
anti-overfitting authority counts recheck identity and scope. Aggregate model-audit
counts must also declare their schema and production scope before raising maturity.
Current V2 production counts are zero. PROPOSAL_ONLY remains unchanged.

Friction period joins include the same identity plus run ID, mode and interval, so
same-date cohorts cannot borrow each other's allocations or cost estimates. No
investment/friction formula is changed. Mixed overall simulation statistics remain
diagnostic; production counts/confidence use explicitly scoped periods.

## Persistence

| Record | Retained identity/provenance |
| --- | --- |
| Decision manifest | lineage, rules, validation schema, authority, nested Baseline/start/status/eligibility, run ID, manifest schema/hash, Git/input/output provenance |
| Failed-run audit | same current identity and run ID; both authority flags false in Baseline metadata |
| Analysis/allocation history and latest snapshots | lineage, rules, schema, scope, Baseline/status/conditions, both authority flags, purpose/basis, run ID, manifest reference/hash |
| Universe snapshot | same identity/authority fields plus run ID and scored universe |
| Run log | lineage, rules, schema, scope, Baseline/status/eligibility, strategy flag, basis, purpose, run ID, existing Git/manifest/output references |
| Audit snapshot meta | complete Baseline snapshot fields including identity, run ID and both flags; existing manifest/output/Git references |
| Walk-forward inventory/period CSV | lineage, rules, schema, scope, run/manifest references, Baseline flag/status, purpose/basis, strategy flag |
| Coverage/summary | explicit requested lineage/rules/schema/scope alongside separately scoped authority counts |
| Allocation-return/friction rows | identity and run ID retained for safe joining; they do not independently grant validation authority |
| Model-audit metrics | explicit current lineage/rules/schema/scope; scoped observation/Baseline counts |

There is no authority-bearing persistence gap requiring a reader to guess a model
lineage. Historical projections never call the current producer identity fallback.

## Historical compatibility

Old artifacts are readable but missing/new-incompatible identity is non-authoritative.
Existing purpose/spacing diagnostics remain available, including unknown legacy
periods. No history is rewritten, assigned the current lineage or promoted under
the new schema. Tests compare original history bytes before/after reader calls.

This stricter reader is delivered only on the V2 integration branch. The existing
V1 production deployment on main is not changed. Recognizing old V1 evidence under
a future stricter V1 reader requires a separately reviewed provenance/rollout
choice; it is not an automatic compatibility fallback in this PR.

## Investment equivalence

`tests/pr2_base_investment_fingerprints.json` contains test-output hashes generated
from a temporary code/config-only archive of the exact base SHA. It is not an
implementation approval registry. The base used the existing `full_strong_analysis`
fixture for MSFT/INTU (actual score, thesis, liquidation, conviction, CAGR,
opportunity-cost and sizing helpers), then pure allocation for all four modes.
No application decision command or operational observation was executed.

The regression compares the analysis dictionary, full pure allocation results and
recommendation projections in balanced, family-office, rational-aggressive and
high-cagr modes. It also compares the critical-config hash and rules version.
Validation metadata and manifest hashes intentionally differ from the base.

## Deferred work

No implementation-fingerprint/Git approval registry, validation_authority.yaml,
V1 implementation allowlist, active V2 Baseline, shadow harness, historical
migration or promotion machinery is introduced. Implementation approval and
verified manifest provenance remain promotion-hardening work. V1 stricter-reader
rollout, V2 shadow evidence collection, eventual production Baseline/start and broad
report/period terminology cleanup require separate review.

## Validation

All tests run with Python 3.12 and the existing isolated runner, which copies only
code/config/tests into a disposable checkout and sets temporary HOME/XDG/state/tmp.
Its network guard denies network access. A dedicated test verifies installed
locked distributions match requirements.lock. Runtime restrictions are unchanged.

Final validation used Python 3.12.14 with dependency_status=MATCH. Commands run
from the V2 workspace (each test runner creates its own isolated disposable tree):

| Command | Result |
| --- | --- |
| `.venv/bin/python -B scripts/run_isolated_tests.py --pattern test_validation_identity_isolation.py` | 19 tests passed |
| `.venv/bin/python -B scripts/run_isolated_tests.py --pattern 'test_baseline*.py'` | 31 tests passed |
| `.venv/bin/python -B scripts/run_isolated_tests.py --pattern 'test_validation*.py'` | 35 tests passed (includes the identity tests) |
| `.venv/bin/python -B scripts/run_isolated_tests.py --pattern 'test_walk_forward*.py'` | 28 tests passed |
| `.venv/bin/python -B scripts/run_isolated_tests.py --pattern test_runtime_isolation.py` | 29 tests passed |
| `.venv/bin/python -B scripts/run_isolated_tests.py --pattern test_pr2_investment_equivalence.py` | 1 test passed; all four modes match the approved base |
| `.venv/bin/python -B scripts/run_isolated_tests.py` | 958 tests passed |
| `git diff --check` | Passed |

These counts overlap; they are not additive. Existing positive validation tests
were updated to use explicitly declared synthetic V1/new-schema fixtures, rather
than relying on missing-authority defaults. Separate new regressions retain the
negative legacy cases. No source runtime guard or production operation was relaxed.
