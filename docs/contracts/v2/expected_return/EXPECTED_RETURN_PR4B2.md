# PR4B2 — Frozen PIT Expected Return diagnostic transport

PR4B2 proves:

> Frozen, already-qualified PR4B1-compatible Expected Return inputs can travel through the retrospective PIT laboratory and produce deterministic V2 diagnostics without changing existing investment decisions.

PR4B2 does **not** prove:

> Current real repository/provider data is sufficient to create those qualified facts.

All new numeric examples are fictional transport tests. They are not investment evidence, forecasts for actual companies, production policies, or policy recommendations.

## Starting state and source identity

After fetching origin, the integration ref was exactly `a95ff74fe0cd448d4b4436dc8506363caabac9d0`, tree `e5acd0bd8d2fae99879116ab1c0e362af4b4ed6a`. Preserved V1 was exactly `c5fc27c82c29c2a6027eccee245098c4a072fdf1`. The local worktree was clean on `codex/v2-expected-return-assumptions`, HEAD `5914124cbb5b7244be87ad9ddafaecbb3059d5a8`. The implementation branch `codex/v2-expected-return-pit-diagnostics` was created directly from fetched integration V2. Its PR base is `model-v2/expected-return-challenger`, never `main`.

The exporter default V2 source changes deliberately:

| Identity | Old | New |
| --- | --- | --- |
| V2 commit | `2d7abc5ca23f6cf8225793f10034e8e6bae1d41e` | `a95ff74fe0cd448d4b4436dc8506363caabac9d0` |
| V2 tree | `8489fb82b5c75701ea0c4a229e001e259fa1a2fe` | `e5acd0bd8d2fae99879116ab1c0e362af4b4ed6a` |

PR4B2 itself remains harness code, identified independently by `harness_hash`. No future feature commit is used as the model-source pin. The source allowlist remains required top-level source files plus direct `src/*.py`; it admits no recursive arbitrary source, tests, operational files, or repository archive. The V2 fixture inventory was regenerated with `git ls-tree -rz` and `git cat-file blob` against the exact new commit. Unchanged bytes can reference checked-in code only with matching SHA-256; differing bytes are stored compressed. Existing authenticity tests compare every fixture blob's Git object ID to the pinned tree and compare full fixture/export bytes to a real Git-derived export. The V1 fixture is unchanged. The three Expected Return modules are explicitly asserted present in the V2 export.

CI's exact-commit fetch is repinned too, retaining the same shallow, allowlisted source-object workflow. No `main.py` bytes or approved `SUPPORTED_MAIN_HASHES` change.

## Contracts and separate paths

| Contract | Old | New |
| --- | --- | --- |
| `PIT_BUNDLE_SCHEMA_VERSION` | `pit-bundle-v1` | `pit-bundle-v2` |
| `PIT_INPUT_CONTRACT_VERSION` | `decision-inputs-v1` | `decision-inputs-v2` |
| `PIT_COMPARISON_SCHEMA_VERSION` | `pit-comparison-v1` | `pit-comparison-v2` |
| `PIT_ADAPTER_VERSION` | `allocation-room-v7-adapter-v1` | unchanged |
| `PIT_EXPECTED_RETURN_INPUT_CONTRACT_VERSION` | absent | `pit-expected-return-inputs-v1` |
| `PIT_EXPECTED_RETURN_DIAGNOSTIC_ADAPTER_VERSION` | absent | `pit-expected-return-diagnostic-adapter-v1` |
| `PIT_EXPECTED_RETURN_DIAGNOSTIC_SCHEMA_VERSION` | absent | `pit-expected-return-diagnostic-v1` |

The authoritative path rejects old bundle/input/result schemas; it does not silently accept v1 artifacts as v2.

```text
Decision PIT path:
verified frozen decision inputs -> existing adapter/model decisions
-> detached canonical semantic_result -> existing semantic_fingerprint
-> existing differences.json

Expected Return diagnostic path (only after the above decision freeze):
verified expected_return_inputs -> closed JSON decoder
-> V1: NOT_AVAILABLE_IN_MODEL (no constructor import)
-> V2: frozen PR4B1 constructor -> frozen PR4A calculator
-> diagnostic_result -> separate diagnostic_fingerprint
-> diagnostic_differences.json (NOT_COMPARABLE)

Both paths -> existing containment/consumption/source/input rechecks
-> validated atomic pair publication
```

There is no reverse dependency. The diagnostic adapter receives only the dedicated input value, lineage, and effective PIT time, with no decision-model object, analysis dictionaries, bundle object, or source path. Its imports from `src` occur only in the V2 branch, after frozen-source selection. `src/`, `main.py`, and the investment adapter have no changes. Static regressions prohibit investment modules from reading diagnostic fields or importing Expected Return modules.

## Exact wire envelope

There are now exactly 16 logical families. `expected_return_inputs` is the only addition, stored as `inputs/expected_return_inputs.json`, with ordinary content hashes, input identity, and family provenance. It is not hidden in another family.

Empty, but complete and executable:

```json
{"contract_version":"pit-expected-return-inputs-v1","entries":[]}
```

Explicit absence example:

```json
{
  "contract_version": "pit-expected-return-inputs-v1",
  "entries": [{
    "ticker": "FICTIONAL_ABSENCE",
    "status": "EXPLICITLY_UNAVAILABLE",
    "facts": null,
    "policies": null,
    "unavailable_reasons": ["NO_QUALIFIED_EXPECTED_RETURN_INPUT"]
  }]
}
```

Qualified entry keys are exactly `ticker`, `status`, `facts`, `policies`, `unavailable_reasons`. Status is `QUALIFIED_SYNTHETIC`; reasons must be `[]`. Facts is the exact `QualifiedFacts` shape below. Policies is exactly `{mature_growth, terminal_valuation, distributions}`: each value is the matching policy object or explicit JSON `null`. A null policy can yield PR4B1 economic unavailability; an omitted policy key is malformed. The entire policies object cannot be null for a qualified entry.

All objects are closed (every listed field required; no extras). The wire shapes below use braces to list exact fields. `text` means trimmed nonempty JSON string; `number` means finite binary64-compatible JSON number, excluding booleans; arrays are JSON lists. Version fields must equal the listed constants. No tagged root other than these five is allowed.

```text
QualifiedFacts = {
  contract_version: "2026-09-09-synthetic-qualified-facts-v1",
  as_of: timestamp, security_id: text, share_class: text,
  basis: ShareBasis, accounting_basis: text,
  latest_required_fiscal_end: date, roots: Root[]
}
ShareBasis = {currency: text, share_basis: text}
AnnualPeriod = {start: date, end: date}
Identity = {observation_id: text, security_id: text, share_class: text,
            provenance: Provenance}
Provenance = {
  source_kind: "SYNTHETIC_OFFICIAL" | "SYNTHETIC_MANUAL",
  source_reference: text, source_version: text,
  source_document_hash: lowercase SHA-256, source_locator: text,
  published_at: timestamp, available_at: timestamp, captured_at: timestamp,
  extractor_id: matching synthetic adapter below, extractor_version: "1"
}
Root = one of:
{root_type: "ObservedPrice", identity: Identity, value: number,
 basis: ShareBasis, observed_on: date}
{root_type: "ReportedDilutedEPS", identity: Identity, value: number,
 basis: ShareBasis, period: AnnualPeriod, accounting_basis: text}
{root_type: "OrdinaryAnnualDividend", identity: Identity, value: number,
 basis: ShareBasis, period: AnnualPeriod, special_dividends_excluded: boolean}
{root_type: "VerifiedNonpayer", identity: Identity, period: AnnualPeriod}
{root_type: "ProfileQualification", identity: Identity, profile: Profile,
 excluded_structures: Profile[], rationale: text}
Applicability = {profile: text, currency: text, accounting_basis: text,
                 valid_from: date, valid_through: date}
ScenarioValues = {bear: number, base: number, bull: number}
MatureGrowthPolicy = {
  policy_id: text, schema_version: "2026-09-09-assumption-policy-v1",
  applicability: Applicability, log_growth: ScenarioValues,
  rationale: text, assumption_id: text
}
TerminalValuationPolicy = {
  policy_id: text, schema_version: "2026-09-09-terminal-policy-v1",
  applicability: Applicability, terminal_pe: ScenarioValues,
  rationale: text, assumption_id: text
}
DistributionPolicy = {
  policy_id: text, schema_version: "2026-09-09-assumption-policy-v1",
  applicability: Applicability,
  rule: "CONSTANT_MATCHED_ORDINARY_PAYOUT" | "CONTINUED_VERIFIED_NONPAYER",
  rationale: text, assumption_id: text
}
```

`Profile` is exactly: `ORDINARY_COMPOUNDER`, `BANK`, `INSURER`, `REIT`, `ASSET_MANAGER`, `RESOURCES_MINING`, `ENERGY_CYCLICAL`, `PIPELINE`, `UTILITY_ACCOUNTING`, `INVESTMENT_HOLDING`, `MIXED_CONGLOMERATE`, `TURNAROUND`, `LOSS_MAKING`, `UNKNOWN`. Admitting an enum does not make its economic route supported.

| Root | Required adapter |
| --- | --- |
| ObservedPrice | `SYNTHETIC_OBSERVED_PRICE_V1` |
| ReportedDilutedEPS | `SYNTHETIC_REPORTED_DILUTED_EPS_V1` |
| OrdinaryAnnualDividend | `SYNTHETIC_ORDINARY_ANNUAL_DIVIDEND_V1` |
| VerifiedNonpayer | `SYNTHETIC_VERIFIED_NONPAYER_V1` |
| ProfileQualification | `SYNTHETIC_PROFILE_QUALIFICATION_V1` |

The executable shapes are in `pit_comparison/expected_return_transport.py`; tests compare their field sets to the exact PR4B1 dataclasses. `tests/pit_expected_return_fixtures.py` contains the complete fictional qualified example, built independently as JSON-compatible dictionaries without model imports or market helpers.

JSON object order and entry order are immaterial to diagnostic semantics. Entry tickers are unique and sorted for output; duplicate entries fail. PR4B1 canonicalizes root and exclusion ordering. Scenario labels retain their meaning; crossing scenarios are never silently sorted. Explicit absence reasons are unique and sorted for output. An empty entries array is recorded in the bundle's `explicit_absences`. Absence of the required family, malformed shapes, unknown status, nonfinite numbers, or fake facts attached to an absence all fail closed.

The ticker is a transport locator only. PR4B1 checks `security_id`, `share_class`, basis, source-root identities, and economic consistency independently; ticker equality never proves them.

## Responsibility and chronology

`bundle.py` calls the model-independent transport validator. It checks closed shapes, scalar types, enums, versions, document hashes, timestamps and obvious chronology. It does not import any model module or reproduce PR4B1 economics. Full semantic checks remain inside the selected frozen V2 constructor: identity reconciliation, duplicate economic roots, annual EPS sequence, profile qualification, supported basis, policy validity/applicability, payout and growth safeguards.

The new family deliberately requires:

```text
facts.as_of == effective_pit_at
published_at <= available_at <= captured_at <= effective_pit_at
family provenance captured_at <= effective_pit_at
```

Dates must also precede their publication. Existing general archival provenance can still accept a later capture when a historical version is verified. That exception does not apply to Expected Return roots or its family provenance. Future `available_at` and future `captured_at` are rejected. This is a temporary restriction: historical archival-evidence extension requires separate review, not weakening PR4B1 during transport.

## Result, fingerprint, and pair contracts

Successful worker top-level keys remain the six `AUTHORITY` fields plus:

```text
schema_version, status, comparison_id, execution_id, bundle_hash, input_identity,
effective_pit_at, investment_mode, capital_context, artifact_created_at,
runtime_diagnostics, model_provenance, containment, consumed_logical_inputs,
completeness_status, semantic_result, semantic_fingerprint,
diagnostic_result, diagnostic_fingerprint
```

Only the last two are new. `validate_result()` enforces this exact top-level key set and still enforces the exact existing decision object:

```text
{investment_mode, capital, analyses, allocation, rankings,
 concentration, tax, portfolio}
```

`diagnostic_result` contains exactly the six authority fields plus:

```text
schema_version, adapter_version, input_contract_version, model_lineage,
status, comparison_status, coverage, versions, counts, entries, linkage
versions = {constructor, facts, methodology, calculator_schema,
            assumption_policy, terminal_policy}
counts = {declared, built, unavailable, not_available_in_model}
linkage = {comparison_id, execution_id, bundle_hash, input_identity,
           source_export_hash}
entry = {ticker, input_status, status, security_id, share_class,
         unavailable_reasons, policy_hashes, lineage_hash,
         confidence, overall_confidence, scenarios}
confidence[] = {component, root_ids, source_authority, freshness, completeness,
                consistency, assumption_dependence, category}
scenarios = {} or {bear: Scenario, base: Scenario, bull: Scenario}
Scenario = {annualized_return, starting_eps_per_share, growth_rates,
            dividends_per_share, terminal_eps_per_share, terminal_pe,
            terminal_price}
```

`policy_hashes` maps supplied policy names to PR4B1 hashes. `lineage_hash` is PR4B1's hash of qualified roots, policies, derivations, and confidence. No IRR or confidence formula is reproduced in the harness.

V1 status is `NOT_AVAILABLE_IN_MODEL`, comparison status `NOT_COMPARABLE`, all version values null, and per-entry numeric/constructor fields absent via null or empty containers. V1 retrieves and validates the family but imports neither PR4A nor PR4B1 and never maps heuristic `expected_cagr`/`expected_cagr_quality` to Expected Return.

V2 top status is `COMPLETED`. Per qualified entry, `BUILT` and `UNAVAILABLE` both succeed. Explicit absence yields `UNAVAILABLE` without fabricated facts. Coverage is always `DECLARED_INPUTS_ONLY`; no comprehensive real-ticker coverage is claimed. Undeclared tickers are not looked up in any other family. A `ConstructorContractError` is a failed worker, not ordinary unavailability; a pair cannot publish after it.

For `FICTIONAL_ORDINARY_ENTITY`, the independently checked nonpayer example is `BUILT`, with overall confidence `LOW`, constructor `2026-09-09-qualified-history-constructor-v1`, facts `2026-09-09-synthetic-qualified-facts-v1`, methodology `2026-09-08-normalized-eps-cashflow-irr-v1`, and calculator schema `2026-09-08-expected-return-diagnostic-v1`. Bear/base/bull annualized values are respectively `-0.003467440923891662`, `0.06089762040432094`, and `0.12115309470015583`, solely as mechanical test outputs. Unsupported profile, missing applicable policy, and payout above earnings produce explicit successful `UNAVAILABLE` entries.

`diagnostic_fingerprint` is SHA-256 over canonical diagnostic JSON **excluding only `linkage`**. Execution links are validated exactly and independently covered by result-artifact hashes. This makes fingerprints stable across process IDs, paths, time of artifact creation, UUIDs, hash seeds and filesystem order, while policy/root semantic changes affect the V2 fingerprint. Linkage cannot be silently substituted across executions, even when fingerprints legitimately match.

`differences.json` keeps its existing decision-only behavior. `diagnostic_differences.json` has the authority fields, its own schema/adapter version, `comparison_status=NOT_COMPARABLE`, reason `V1_HAS_NO_COMPATIBLE_NUMERIC_EXPECTED_RETURN`, and a `models` map. Each lineage links its exact execution, diagnostic fingerprint, status, coverage, counts, and per-entry ticker/status/reasons. It does not compare numeric returns, choose winners, score performance, or claim alpha. The manifest's `diagnostic_differences={path,sha256}` links its bytes independently; each execution link adds `diagnostic_fingerprint`.

`verify_pair()` retains all existing decision checks and additionally validates strict sidecar structure, authority, versions, lineage/source/bundle/execution linkage, content fingerprints, execution fingerprint links, the separate difference artifact's hash, and exact recomputation of that artifact from the two sidecars. Rehashing a tampered difference file alone does not bypass the content check. Cross-lineage and cross-execution substitutions fail. Pair publication remains atomic.

Both workers explicitly retrieve `bundle.get("expected_return_inputs")` after freezing decisions. The invariant `bundle.consumed == set(bundle.data)` is unchanged. No family is globally marked consumed.

## Authority, isolation, and proof

Every sidecar and comparison artifact retains:

```text
comparison_mode = RETROSPECTIVE_PIT
run_purpose = DIAGNOSTIC
validation_authority = NONE
strategy_validation_authority = False
baseline_forward_eligible = False
genuine_forward_evidence = False
```

The constructor result cannot become Baseline, forward, tuning, or production evidence. `MODEL_RULES_VERSION` stays `2026-08-23-allocation-room-integrity-v7`; neither V1 validation schema nor PR4A methodology changes.

The tests assert both established decision fingerprints directly, without regenerating their authority:

- 64-case aggregate: `f1e73b27b80e41d96ff5e0fe990b482bad71b7220db0b5bd6a2f470d72786166`.
- Determinism: `f8457910665391e39c234274cae4c029802c681211eebc7dba986a63000876f1`.

The existing 64-case oracle still compares decisions only. A separate diagnostic test layer checks independent typed PR4B1 construction, versions, policy hashes, lineage hash, scenario returns, confidence and unavailable reasons. Frozen-worker tests compare empty and populated input bundles for both V1 and V2: the entire decision object, fingerprints, allocation, rankings, analyses, concentration, tax, portfolio and `differences.json` stay identical. Other tests cover hash seeds, ordering, mutations, malformed qualified entries, old schemas, explicit absence, chronology, complete input consumption and artifact tampering/substitution.

Existing application and native containment, HTTP sentinels, frozen-source and bundle rechecks remain active. Static import/read checks and a dynamic test denying file/network access guard against new acquisition paths. All runs use checked-in synthetic fixture data, not a current portfolio or historical operational bundle. Existing decision-fixture ticker labels are preserved for the established oracle; new Expected Return identities and locators are fictional only.

## Real-data blockers

No Yahoo/yfinance, SEC, Morningstar, research, manual-provider, Drive, or other real source adapter is certified as a PR4B1 qualified root. The harness cannot upgrade market snapshot EPS, estimated growth, price CAGR, PEG, fair value, dividend yield, payout ratio, or business-profile text into this contract. Real-company execution still requires separately reviewed upstream authentication and availability evidence, reconciled security/share-class/currency/accounting/share basis, consecutive reported annual diluted EPS, matched verified dividend status, explicit fail-closed profile qualification, explicit applicable economic policies, and any future archival chronology extension.

No production integration, provider collection, operational analysis, real stock Expected Return, deployment, merge, tuning, Baseline evidence, backtest, or walk-forward is part of this change.

## Executed validation

Local runtime: CPython **3.12.14**, all **33** locked packages `MATCH`, no missing packages or version drift. The repository's `.python-version` remains unchanged at `3.12.13`; CI continues using that pin. Dependency-lock fingerprint: `f9fdbc657e0161ca0ad056120df9e2cd6e5c27ab7352261e3640f6274724f82f`.

All commands below use disposable code/state, sanitized HOME, and denied network access through the existing isolated runner. Counts overlap across focused runs. The final diagnostic rerun includes the latest V2-import and parent-lineage checks.

| Exact command | Result |
| --- | --- |
| `.venv/bin/python scripts/run_isolated_tests.py --pattern 'test_pit*.py'` | 39 passed, 395.747 s; includes the 64-case / 256-worker decision matrix |
| `.venv/bin/python scripts/run_isolated_tests.py --pattern 'test_pit_expected_return_diagnostics.py'` | 19 passed, 31.653 s |
| `.venv/bin/python scripts/run_isolated_tests.py --pattern 'test_expected_return*.py'` | 144 passed, 0.805 s |
| `.venv/bin/python scripts/run_isolated_tests.py --pattern 'test_*isolation.py'` | 48 passed, 35.735 s; includes runtime and validation identity isolation |
| `.venv/bin/python scripts/run_isolated_tests.py --pattern 'test_pr2_investment_equivalence.py'` | 1 passed, 0.087 s |
| `.venv/bin/python scripts/run_isolated_tests.py` | **1,142 passed, 463.277 s** |

Both established decision fingerprints were asserted unchanged in the full suite. The exact exported-source hashes were:

- V1: `30edb712f236bb1b6fc2fdceeb728cfa0f64a8e18233894bf63ff9c4724d99df`.
- V2: `02659be45577f64433aed1050df8254b5709a06b0c04fc9deb7bf6554b31ac0c`.

`git diff --check` and staged diff checks passed. The protected source/decision/version/lock files had no diff. No application analysis command or real-data execution was used.
