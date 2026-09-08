# PR3: immutable retrospective PIT comparisons

This is diagnostic infrastructure. It does not collect operational inputs, run the
normal application, evaluate outcomes, select a winning model, or create Baseline
evidence. The only execution mode is `RETROSPECTIVE_PIT`.

## Source and architecture

The parent lives in `pit_comparison/` and imports no `src` module. It verifies an
existing bundle against a caller-supplied digest, exports source from exact Git
objects, snapshots the harness, prepares two disposable workers, validates both
results, and publishes their exact artifact hashes together.

The preserved V1 is commit `c5fc27c82c29c2a6027eccee245098c4a072fdf1`, tree
`26a69bb0b2185ab141af0763da2d965602c8346b`. The initial V2 is commit
`2d7abc5ca23f6cf8225793f10034e8e6bae1d41e`, tree
`8489fb82b5c75701ea0c4a229e001e259fa1a2fe`.
The source allowlist is `main.py`, flat `src/*.py`, `.python-version`,
`requirements.txt`, and `requirements.lock`. Git configuration is used only to
read exact local objects. No repository archive or Git bundle is constructed.
Config, data, reports, caches, deployment files, credentials and Git history are
absent from worker source exports.

Every source manifest records commit, tree, lineage, each exported file's length
and SHA-256, and an aggregate source-export SHA-256. Effective input configuration
has a separate hash. The worker verifies source bytes before imports and after
calculation. V1's lineage is external comparison provenance; its code is unchanged.
V2 must activate its native restricted runtime and report V2/NONE identity.
Both retain rules `2026-08-23-allocation-room-integrity-v7` and validation schema
`2026-08-23-validation-architecture-v3`.

The revision-aware adapter accepts only the two reviewed `main.py` orchestration
hashes. A future orchestration change requires explicit adapter review and new
original-behavior equivalence tests. An explicit V2 commit identifies every run;
this PR does not authorize new investment semantics.

## Existing-bundle CLI

Use the locked Python 3.12 environment:

```sh
.venv/bin/python -B scripts/run_pit_comparison.py \
  --bundle /dedicated/pit/bundles/sha256/DIGEST \
  --expected-bundle-hash DIGEST --inspect

.venv/bin/python -B scripts/run_pit_comparison.py \
  --bundle /dedicated/pit/bundles/sha256/DIGEST \
  --expected-bundle-hash DIGEST \
  --store /dedicated/pit/comparison_store \
  --v2-revision 2d7abc5ca23f6cf8225793f10034e8e6bae1d41e
```

These are syntax examples, not real certified bundles. The digest must come from
outside the bundle. The CLI has no collection, promotion or evaluator option.
The comparison store must be separate from the repository, supplied bundle,
normal reports/history/backups and recognized application state locations.
It creates only comparisons, temporary staging and failure artifacts.

## Bundle contract

Schemas: `pit-bundle-v1`, `decision-inputs-v1`, `pit-comparison-v1`; adapter:
`allocation-room-v7-adapter-v1`. An input directory contains exactly
`bundle_manifest.json` and one `inputs/<logical_id>.json` file per family below.
`bundle.py` is the executable contract; `tests/pit_fixtures.py` illustrates only
synthetic data, never a production collector.

The manifest declares schema versions, `bundle_id=sha256:<digest>`, bundle hash,
input identity, effective PIT instant, semantic IANA timezone, artifact creation
instant, mode, CAD contribution context, portfolio snapshot hash, explicit
availability cutoff, quality, history policy, provenance linkage, logical input
inventory, exact file hashes/lengths and explicit empty-family declarations.

Canonical JSON uses sorted string keys, UTF-8, compact separators, a terminal
newline, finite native JSON values and no numerical rounding. Duplicate keys,
NaN/infinities (including overflowed exponents) and unsupported containers fail.
Input files retain their exact bytes and may use noncanonical whitespace; the
manifest must be canonical. Hashes cover the actual input bytes. Aggregate bundle
hashing excludes only its own hash and derived ID. Input identity includes the
contract, full file inventory, PIT instant and timezone, independently of models
and output artifacts. Self-consistent rewriting cannot satisfy the caller's old
expected digest.

Regular files/directories only: reject links (including detectable hardlinks),
special files, linked ancestors, absolute/embedded escaping paths, traversal,
case/Unicode path collisions, duplicate IDs, missing files, unlisted files and
unlisted empty directories. Workers receive byte-identical materializations and
independently require the same expected hash before model imports.

| Logical family | Frozen content and consumption |
| --- | --- |
| context | Four supported modes, explicit CAD capital/contribution context and upstream validation warnings; allocation, sizing and decision quality consume these. |
| portfolio | Raw declared holdings/cost/account rows; original cost-basis guard, portfolio parsers, alias resolution, lot aggregation, FX enrichment and weights. |
| transactions | Explicit raw transaction list, including verified empty; native transaction parsing/currency requirements. |
| account_locations | Explicit optional account-location rows; native merge with portfolio lots and tax-location calculations. |
| universe | Separate watchlist, market and discovery rows; native loaders retain alias handling, exclusions, prioritization and candidate caps. |
| market | Frozen post-provider observations upstream of analysis; complete v7 provider field inventory with explicit null observed absences, required positive prices/currency/source and admissible timestamps. |
| benchmarks | Same provider record contract for every benchmark required by the selected source's benchmark map/common benchmarks. |
| regime_market | Explicit records required by the native regime configuration; verified empty only when no records are required. |
| fx | Exact historically admissible positive CAD conversion rates; CAD=1; every required quote, cost and transaction currency must exist. No implicit USD fallback. |
| manual_inputs | Normalized manual facts/provenance, before research/manual merge and scoring; original resolution and manual precedence. |
| research_facts | Normalized extracted facts, field dates/confidence/provenance, before original merge and scoring. No PDF/document retrieval. |
| ticker_memory | Explicit normalized sector/exposure memory applied by native enrichment functions. |
| prior_state | Verified empty or explicit admissible analysis/allocation observations; immutable materialization read only by native history/stability selectors. |
| config | All 12 consumed configuration objects, materialized as JSON (a YAML subset) for unchanged native loaders. |
| provenance | Required availability/version evidence for each other family; verified contract gate and explicit consumption accounting. |

The 12 configurations are positions, benchmarks, sectors, exposures, watchlist,
market_scanner, defensive_etfs, market_regime, ticker_aliases, proxy_corrections,
model_tuning and tax_parameters, with their `.yaml` names. Explicit `{}` means
use that selected source's native defaults; it is not a missing config file.
Source hashes also bind code-defined defaults. Operational preflight warnings
are an explicit input because they affect the decision-quality annotation.

Normalized manual/research facts are the existing loaders' output interface.
Any parser-derived freshness/provenance metadata must itself describe the state
at T. PR3 does not reconstruct it from present-day documents. The bundle cannot
contain current-run scored analyses/final actions as input facts; prior scored
observations are allowed only inside the explicitly historical family. Extra
observations may be frozen, but every required ticker/FX/benchmark must exist.
Consumption accounting covers every logical family; it is not a claim that every
optional provider field affects every decision.

## Historical admissibility and clock

Each family attests observation date, publication time, availability time and
evidence, capture time, source version/hash, and verified historical version.
Publication <= availability <= T; capture may be later only with historical
version evidence. Known embedded news/research/SEC/market dates cannot contradict
the cutoff. A fiscal date alone is insufficient. Evidence assertions are
validated structurally; this harness cannot authenticate a false source claim.
No real historical timestamp or dataset has been certified in this PR.
**PR3 does not prove that usable COMPLETE historical PIT bundles currently exist.**
The repository does not establish the portfolio snapshots, provider vintages,
research versions, discovery state, analyst estimates and prior decision state
needed for arbitrary historical reconstruction. Current-data substitution is
not permitted.

Only `COMPLETE_PIT` executes. `PARTIAL_PIT` is inspectable and can declare unknown
provenance, but cannot publish a semantic pair. `CONTAMINATED_UNUSABLE` fails.
Missing prior state cannot become empty: status is `VERIFIED` or `VERIFIED_EMPTY`.
Each prior record declares observation ID, `HISTORY`/`LATEST` role, created time,
analysis date, mode, rules and rows. Identity and selection ties are validated;
multiple same-day records retain separate IDs and chronological selection.
Native mode/rules/day filtering, lookback and latest fallback remain unchanged.
Native readers see only these immutable records, never operational history.

Market/research freshness receives the PIT clock through existing `now`/`today`
parameters, including the evidence-provenance leaf seam when callers pass None.
For market freshness, the supplied clock uses the observation's UTC offset
because the unchanged native function strips that offset before subtraction;
this preserves elapsed hours across semantic timezones. The utility date used by native history selection is scoped to the disposable
worker's semantic date. Thresholds are unchanged. Artifact UTC creation time,
process IDs, hash-seed probes, containment read counts, execution IDs and source
provenance stay outside semantic fingerprints.

## Application containment

`containment_level=APPLICATION_GUARDED`. This protects trusted application code
against accidental I/O. It is not an OS sandbox or a defense against hostile
native extensions, deliberate Python introspection/guard removal, external
concurrent filesystem mutation, or a compromised interpreter/dependency.

Before model imports, every subprocess gets sanitized environment variables,
disposable HOME/XDG/TMP directories, closed inherited descriptors and separate
source/runtime roots. Python site startup and user site are disabled; cwd and
PYTHONPATH injection are removed. The pinned environment's dependency directories
are explicitly supplied without running `.pth`/`sitecustomize` startup. Hash seeds
are deliberately honored so tests can perturb them.

Python audit/path guards reject socket creation/use and DNS, process/exec/spawn/
fork operations, unexpected reads, outside writes, immutable source/input writes,
peer/store access, link creation, descriptor-relative access and unsupported raw
input-descriptor APIs. Known provider imports and retrieval entry points fail
fatally, including yfinance, requests, SEC/BoC, Canadian data, discovery,
instrument enrichment and URL retrieval. A fatal requests interface prevents its
HTTP stack from probing sockets during import. No provider is instantiated.

Reads allow only the disposable source, harness, verified input/runtime roots,
explicit Python/dependency roots and platform zoneinfo data. Metadata-only access
to declared root ancestors and fixed platform roots permits Python/PR1 path
resolution; it grants no content access to `/etc` or other system state. Pinned
dependency symlinks are a narrow exception; bundle/source links are rejected.
Successful read-path checks are cached within one disposable process; link
creation is blocked and immutable inputs/source are reverified afterward.

V2 sets its restricted profile/root/forbidden roots before importing `src` and
asserts native identity afterward. PR1 checks remain active. Its exception
construction is observed to retain a violation even when application code catches
a native denial. `check_analysis` is neither replaced nor bypassed; normal
`run_analysis` is disabled. Every caught harness or native denial irreversibly
produces `CONTAINMENT_FAILED` and cannot publish a successful pair.

## Adapter and original-behavior gate

The adapter calls native parsing/alias resolution, `build_position_analyses`,
history/sell discipline, winner protection, cycle/cash-flow/shareholder/durability/
market-growth/drawdown/regime/euphoria/double-counting/hidden-cluster passes,
eligibility refresh, external classifications/gates, tax and allocation universe,
P3 deep averaging-down, native capital-allocation scoring, stability, native
`allocate_capital` (including P4B), final decisions, sensitivity and decision
quality. Formulas, thresholds and ranking/selection rules are not copied.

Differences from normal application execution are input acquisition, explicitly
frozen warning context, PIT clock binding and omitted operational side effects:
preflight collection, providers, cache maintenance, synchronization, logging,
report/history generation, validation/Baseline evidence and notifications. All
investment calculations and recommendation reasons are retained. Positive
capital is evaluated solely through the dedicated function adapter.

`tests/pit_reference.py` is an independent orchestration oracle: it extracts and
executes unchanged decision statements from each exact exported `main.py` using
AST boundaries. Provider/storage acquisition has synthetic readers; the optional
account-location read is enabled because that input is explicit. It does not call
normal `run_analysis` or adapter `evaluate`. It shares only the input-binding seams
and lossless output projection. Full analyses, allocation, rankings, concentration,
tax and portfolio dictionaries must equal the original oracle and then V1 must
equal V2 exactly, not merely within a rounded tolerance.

The matrix independently checks one elapsed market-data hour across UTC observations
and the Toronto semantic calendar. The matrix uses four modes and 16 scenarios: mixed lots/accounts/CAD/USD,
liquidation, winner, ties, drawdown, valid missing fields, concentration, empty
history, proxy corrections, regime, latest fallback, same-day observations,
validation warnings, dated research, zero capital and sizing boundary. Existing
P3/P4B/winner/tax/concentration/stability regression tests remain part of the full
suite. A dated research assertion checks 32 semantic days at T independently of
the host date. Repeated pair runs reverse model order and change the actual
interpreter hash seed; process/probe metadata proves these perturbations occurred.
Input mtimes are set to a different epoch, and a second byte representation with
reordered JSON object keys must retain the same semantic result. The host wall
clock is not globally modified; PIT ages are asserted against controlled facts.

The code-only `tests/pit_source_revisions.json` records both pinned source
inventories and compressed V1 blobs only where they differ from current source.
Common/V2 files are read from the test checkout with exact hash verification.
This supports existing shallow CI without fetching historical operational files.
It contains no portfolio, reports, configs or real PIT data. This fixture cannot
silently follow future source drift.

## Results, authority and publication

Both child results and the parent hard-code:

```text
comparison_mode=RETROSPECTIVE_PIT
run_purpose=DIAGNOSTIC
validation_authority=NONE
strategy_validation_authority=false
baseline_forward_eligible=false
genuine_forward_evidence=false
```

Results contain all universe analyses/reasons/current metrics, final actions,
liquidation/eligibility, native allocation including VFV/cash/defensive choices,
concentration, tax, descriptive rankings, consumed families, locked dependency
status, exact source/config/harness provenance, and a lossless semantic digest.
Unknown future score/CAGR/expected-return fields are `NOT_COMPARABLE` unless
explicitly registered as corresponding. There is no winner/composite score.

UUID comparison and execution IDs link both analyses and allocation in each
result. A specification hash binds bundle/input identity, decision context,
selected sources, effective config and adapter/harness versions. No date-based
pair reconstruction occurs. The parent requires both successes, matching
identities/revisions/context, complete consumption, passing containment, authority
and semantic hashes. The manifest links exact result-byte SHA-256 values and the
difference artifact hash. A local `verify_pair` rechecks these links.

The parent writes an exclusive staging directory, verifies the whole pair and
rechecks the supplied bundle, then renames staging into
`comparisons/<comparison_id>` on the same filesystem. Failed attempts leave only
`failures/<comparison_id>/failure.json`; staging is removed and no half-pair is
published. IDs are never reused. This is atomic visibility and verified byte
integrity, not an OS write-once filesystem or crash-durable database. An external
rewriter with control of an entire completed store is outside this trust model;
retain externally trusted artifact/spec hashes when distributing results.

## Validation and deferred work

Run all tests only in disposable code/state with the repository's existing wrapper:

```sh
.venv/bin/python -B scripts/run_isolated_tests.py --pattern 'test_pit_bundle.py'
.venv/bin/python -B scripts/run_isolated_tests.py --pattern 'test_pit_comparison_boundary.py'
.venv/bin/python -B scripts/run_isolated_tests.py --pattern 'test_pit_comparison.py'
.venv/bin/python -B scripts/run_isolated_tests.py --pattern 'test_pit_adapter_equivalence.py'
.venv/bin/python -B scripts/run_isolated_tests.py --pattern 'test_pit_source_export.py'
.venv/bin/python -B scripts/run_isolated_tests.py --pattern 'test_runtime_isolation.py'
.venv/bin/python -B scripts/run_isolated_tests.py --pattern 'test_validation_identity_isolation.py'
.venv/bin/python -B scripts/run_isolated_tests.py
git diff --check
```

The wrapper now copies the new harness package along with its previous code-only
allowlist. Existing GitHub CI discovers the new tests automatically; its Python
pin, dependency lock and workflow are unchanged. Local execution uses locked
Python 3.12 packages and checks worker dependency status before calculation.

Deferred: prospective collector, `SHADOW_ONLY`, prospective challenger execution,
outcome evaluator, new V2 expected-return semantics, V2 Baseline, promotion,
implementation approval registry, stronger OS containment and production
scheduling. No merge/deploy, production scheduling, Chromebook, Drive, systemd,
operational analysis/history, real PIT bundle, Baseline observation or tuning is
part of this PR.

### Recorded local acceptance

Python 3.12.14 with every installed locked package matching `requirements.lock`:
`python -B scripts/run_isolated_tests.py` passed **974 tests in 425.803 seconds**.
This includes 64 original-oracle/V1/V2 equivalence cases (256 fresh calculation
workers), caught-denial worker tests, bundle, boundary, source-export and pairing
tests, plus the existing 29 PR1 and 19 PR2 regressions. No model imports or
operational analyses were executed in the original checkout.

The 64-case semantic fingerprint aggregate is
`f1e73b27b80e41d96ff5e0fe990b482bad71b7220db0b5bd6a2f470d72786166`.
The repeated rational-aggressive synthetic fixture, including reversed order,
changed hash seeds, changed mtimes and reordered JSON keys, yields
`f8457910665391e39c234274cae4c029802c681211eebc7dba986a63000876f1`.
An additional synthetic comparison using the actual Git-object exporter, rather
than the code-only test fixture exporter, produced that same semantic digest for
both models with passing containment.

V1 source-export hash:
`a599feb1f16ec63c1815dba697333ab43f2f0fd73c533e67fd88dd6dd599fdf8`.
V2 source-export hash:
`a7164882968217bc9676ef87bebf4d151ad1ed069c9bc9459ed10ed15f97a3b1`.
Whitespace checks passed. GitHub CI status is reported on the PR so this document
does not claim a remote run before it occurs.
