# CI validation routing

## Purpose

PAM keeps narrow logical pull requests. CI routing, not giant PR aggregation, is
the primary latency optimization.

The prior `Baseline V1 CI` workflow ran complete unittest discovery for every
pull request. A recent successful run executed 2,452 tests in about 890 seconds.
Most wall-clock time came from
`tests/test_pit_adapter_equivalence.py`, especially its four-mode by sixteen-
scenario isolated V1/V2 actual/oracle proof.

That proof remains intact. CI1 routes it according to its reviewed dependency
surface instead of rerunning it for unrelated documentation and economic-fact
changes.

## Deterministic tiers

The planner receives the complete base-to-head changed-file set and selects the
highest required tier:

```text
DOCS_ONLY < STANDARD < FULL_PIT
```

No workflow input or caller-supplied flag can request a cheaper tier. An empty,
invalid, unresolvable or unclassified change set fails toward `FULL_PIT` or fails
the job before validation can be reported as successful.

### DOCS_ONLY

Selected only when every changed path ends in `.md`.

- prints the complete changed-file inventory and tier;
- runs full-diff whitespace validation;
- skips PIT source fetches, Python setup, dependency installation, compilation
  and unittest execution.

JSON, YAML, text and configuration files are not documentation-only for this
policy.

### STANDARD

Selected for the reviewed heavyweight-independent surface:

- `economic_facts/**`;
- ordinary `tests/test_*.py` modules;
- ordinary `tests/*_fixtures.py` helpers;
- Markdown mixed with either of the above.

The standard route fetches the exact pinned PIT objects still needed by ordinary
PIT tests, installs the locked Python environment, compiles all reviewed Python
locations, and runs the entire discovered unittest inventory minus exactly
`tests.test_pit_adapter_equivalence`.

It is not a hand-maintained test shortlist. A new normally discovered ordinary
test enters `STANDARD` automatically.

### FULL_PIT

Runs `STANDARD` plus every test in the complete heavyweight adapter-equivalence
module. The partition is checked for no overlap, a nonempty heavy set and exact
union equivalence with full discovery before tests run.

`FULL_PIT` is required for:

- `.github/workflows/ci.yml`;
- `main.py`;
- `.python-version`, `requirements.txt` and `requirements.lock`;
- `src/**`;
- `pit_comparison/**`;
- `tests/pit_*` and `tests/test_pit_*`;
- `tests/__init__.py`;
- the CI planner and unittest runner;
- the tests of those CI helpers;
- every unknown or ambiguous path.

The dependency boundary is intentionally conservative. The heavyweight proof
exports exact pinned `main.py`, environment and `src/**` blobs, runs the
`pit_comparison/**` harness, and consumes `tests/pit_*` fixtures/oracle material.
Accordingly, any `src/**` change remains `FULL_PIT` even when a current source
file looks unrelated.

By contrast, `economic_facts/**` is outside the pinned V1/V2 investment-source
export and adapter-equivalence execution graph. It may use `STANDARD`, while its
ordinary tests still run with the rest of the discovered suite.

## Complete diff and rename safety

Pull requests use the exact GitHub base SHA; pushes use the valid event `before`
SHA. A missing base object is fetched exactly. The workflow evaluates:

```text
git diff --no-renames --name-only <base-sha> HEAD
```

Disabling rename detection ensures a sensitive old path and its new destination
are both classified. Whitespace validation uses the same complete base-to-head
diff rather than `HEAD^`.

Every run prints:

```text
CI_VALIDATION_TIER=<tier>
CI_CHANGED_FILE_COUNT=<n>
CI_CHANGED_FILE=<path>
CI_HEAVY_PIT_REQUIRED=true|false
```

## Compatibility and cancellation

The workflow remains named `Baseline V1 CI` and its principal job remains
`test`, preserving the existing required-check identity. PR/ref-specific
concurrency cancels an obsolete in-progress run only when a newer run for the
same PR or ref starts; unrelated pull requests do not cancel one another.

Local `python -m unittest discover -s tests -q` behavior is unchanged. The
heavyweight test module has no default skip and no scenario, mode or fingerprint
expectation was removed.

## Examples

```text
README.md + PAM_ROADMAP.md
→ DOCS_ONLY

economic_facts/new_fact.py + tests/test_new_fact.py
→ STANDARD

src/expected_return_engine.py
→ FULL_PIT

.github/workflows/ci.yml
→ FULL_PIT
```

## Nonclaims

CI1 changes validation orchestration only. It does not change investment rules,
Expected Return mathematics, V1 behavior, production or deployment behavior,
evidence authority, admission semantics, capability states, protected fingerprints
or `MODEL_RULES_VERSION`. It does not make synthetic qualification real-data
authority and does not promote V2.
