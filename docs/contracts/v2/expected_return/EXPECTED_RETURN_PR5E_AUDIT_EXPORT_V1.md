# PR5E bounded audit export v1

Work Order: `WO-V2-PR5E-AUDIT-MANIFEST-EXPORT-V1`, Codex Development,
CEO-authorized implementation only, 2026-10-11.
Base: `model-v2/expected-return-challenger`, HEAD
`27f7d66012c65f4be09d3801dcc09cef85f8f52d`, tree
`22655775870d4d3d447e12ce1dc371842c9479ae`.

## Scope and API

`src.expected_return_pr5e_audit_export.export_pr5e_audit(result) -> bytes`
accepts exactly one native `PR5EAdmissionResult`. It checks native versions,
enums, status/reasons, fixed limitations, upstream linkage and reconstructs the
existing native admission identity projection using PR5E `_result`. This is an
internal consistency check, not source authentication or new admission.
It does not acquire sources, replay archives, construct assumptions, calculate
Expected Return, modify the input or write files.

`verify_pr5e_audit(artifact: bytes, expected_artifact_digest: str) -> str`
returns the matching external artifact SHA-256, or raises `AuditExportError`.
The expected digest is mandatory and must be separately trusted. Passing a digest
calculated from the received artifact alone does not establish external trust.
There is no unanchored success API. The verifier can be called in an independent
process, and the module can be loaded alone with `runpy.run_path`; its verification
path imports no PAM analytical, source, PIT or V1 modules.

```python
from hashlib import sha256
from pathlib import Path
from src.expected_return_pr5e_audit_export import export_pr5e_audit, verify_pr5e_audit

artifact = export_pr5e_audit(existing_native_result)
trusted_digest = sha256(artifact).hexdigest()  # retain through a trusted channel
Path("audit.json").write_bytes(artifact)       # caller-controlled storage
# In a separate process: expected_digest comes from that trusted channel.
verify_pr5e_audit(Path("audit.json").read_bytes(), expected_digest)
```

## Wire format and identities

One JSON artifact has exactly `manifest` and `payload` objects. All bytes are
canonical ASCII JSON: Python `json.dumps(sort_keys=True, separators=(",", ":"),
ensure_ascii=True, allow_nan=False)` followed by exactly one LF. No BOM, alternate
whitespace, alternate escapes, duplicate keys, extra fields, numbers or trailing
content are accepted. Only objects, arrays, strings and schema-permitted nulls
are used; booleans have no supported field. Arrays preserve native ordering except
reference records, which are sorted by their unique path. No Unicode normalization
or timestamp invention occurs. The analytical as-of, when present, must be the native
canonical UTC `datetime.isoformat()` representation. The parser requires exact bytes
and limits each artifact to 4 MiB; recursive/malformed input fails closed. Memory is
proportional to this bounded artifact, with no streaming/storage framework.

The manifest contains exactly:

- `schema_version`: `2026-10-11-pr5e-audit-export-v1`;
- `coverage`: `PR5E_IDENTITY_STATUS_AND_PROVENANCE_PROJECTION_ONLY`;
- `boundaries`: the exact ordered four strings defined in `BOUNDARIES`;
- `payload_sha256`: SHA-256 of canonical payload bytes, including its LF.

The external artifact digest is SHA-256 of the entire canonical artifact, including
the manifest and final LF. It is deliberately not embedded in the bytes it hashes.
Payload and artifact hashes are recalculated, never trusted by assertion. All hash
fields accept exactly 64 lowercase hexadecimal characters.

The payload preserves these native top-level fields exactly:
`contract_version`, `adapter_version`, `status`, `reasons`,
`pr5d2_semantic_id`, `pr5d2_evidence_id`, `admission_semantic_id`,
`admission_evidence_id`, `admitted_share_basis_identity`, `analytical_as_of`,
`limitations`. Enums are represented by their native string values; tuple fields
become arrays. Unsupported native/adapter/upstream versions fail closed. The pinned
wire constants are intentional: the independently loadable verifier must not silently
follow future runtime contract changes.

`upstream` contains exactly PR5D2 `contract_version`, `assembler_version`,
`semantic_id`, `evidence_id`, `upstream_semantic_ids`, `upstream_evidence_ids`.
Top-level PR5D2 identities must equal the corresponding nested identities.
Semantic identities remain distinct from evidence identities: evidence changes
can change artifact identity without changing analytical semantics.

`evidence_references` contains `{path, value}` records. Paths start at
`upstream_pr5d2` or `qualified_facts`; slash-separated native dataclass field names
and tuple indexes identify their locations. Recursion follows dataclasses and
tuples only, without dereferencing archives or accessing files. It retains only
existing exact string values of these named fields:
`receipt_id`, `content_sha256`, `source_object_hash`, `table_sha256`,
`source_reference`, `source_document_hash`, `source_locator`,
`response_structure_locator`, `filing_receipt_id`, `accession`,
`document_filename`, `captured_at`, `filing_captured_at`.
Nulls and other representations at these locations are not reference records.
Duplicated evidence at different native paths remains distinguishable.

## Coverage exclusions and authority

This is a bounded projection, not full-result serialization. It excludes native
economic values, period decisions, corporate-action records, policy details,
qualification decision bodies, facts bodies, construction requests/outputs,
diagnostic numerical outputs and all source archive bytes. Only the identity fields
and named references above are covered. Excluded content remains represented by
opaque native identities, which the offline verifier does not recompute: there is
insufficient content for native replay. The verifier validates the wire schema,
cross-field consistency and artifact hashes, not the correctness of economic
analysis or completeness/authenticity of underlying SEC/provider evidence.

Internally rehashed wholesale substitution can only be rejected relative to the
separately trusted expected artifact digest. A substituted artifact with its own
trusted digest proves only its own byte integrity. Exporting an exact dataclass
does not prove that the original factory ran or its sources were authentic.

Supported statuses are native admitted, `UNAVAILABLE`, `UNSUPPORTED` and
`SOURCE_CONFLICT`, with their native reasons. Synthetic legitimate native fixtures
prove mechanics only; no authentic-positive issuer campaign is supplied.
The export grants no financial, historical/PIT, shadow, recommendation, allocation,
execution, production, deployment or promotion authority. V1 stays frozen, V2 stays
challenger, Stage C stays ACTIVE / INCOMPLETE and Stage N is not activated/completed.

## Existing technology & resource reuse assessment

| Candidate / source | Decision and fit | License / cost / limits |
| --- | --- | --- |
| Native [PR5E](../../../../src/expected_return_pr5e_adapter.py) and [PR5D2](../../../../src/expected_return_pr5d_bundle.py) | REUSE native enums, identities, admission identity reconstruction and native fixture paths | Existing repository code; no outside licensing or dependency acquisition. Repository-wide commercial rights are not newly adjudicated by this change. No mandatory incremental expenditure. |
| [PIT bundle](../../../../pit_comparison/bundle.py) and [decision manifest](../../../../src/decision_manifest_engine.py) | ADAPT duplicate-key rejection, compact sorted JSON, SHA-256 and external anchor pattern; avoid importing PIT/V1 semantics or file inventory | Existing code, no outside code copied or new dependency. Their serialization formats/authority are different, so a narrow versioned projection is necessary. No mandatory incremental expenditure. |
| Python 3.12 stdlib [JSON](https://docs.python.org/3.12/library/json.html), hashlib, dataclasses | REUSE in pinned 3.12.13 / existing locked environment; source docs checked 2026-10-11 | [PSF license](https://docs.python.org/3.12/license.html) permits use/modification/distribution subject to notices. No weights/datasets/services/downloads, API fees or new install. Zero mandatory incremental external expenditure; source-data redistribution rights are separate and not expanded. |

No mandatory subscriptions, cloud, hardware, paid upgrades or financial-data expense.
Non-cash costs are small schema maintenance and bounded in-memory parsing. No GPU,
instruction-set-specific library, cache or persistent storage requirement. Mac local
validation is recorded in the PR handoff. Chromebook/Linux fit is plausible for one
bounded artifact under the documented two-core/2.7-GiB/no-swap profile, but execution,
peak RAM and latency were not benchmarked there. System Python 3.11.2 compatibility
is not established; the approved validation runtime is 3.12.13. No Chromebook
production changes or external compute are authorized.

## Validation and handoff

Focused tests cover deterministic native export across independent processes,
semantic/evidence separation, all native states, malformed/corrupt/missing content,
unsupported versions, duplicate keys, external-anchor mismatch, offline operation,
explicit authority boundaries and preservation of inputs/source archive bytes.
The existing PR5E import-isolation test permits this one new bounded consumer;
V1/runtime/production imports remain forbidden. Required tier: FULL_PIT plus canonical
`./pam_preflight --base 27f7d66012c65f4be09d3801dcc09cef85f8f52d`, protected PIT and
determinism fingerprints, unchanged MODEL_RULES_VERSION and Git integrity checks.

Only this module, focused tests and this contract are in scope. All economic/source
contracts, V1 code, governance and roadmap are out of scope. No model rules change.
After validation, commit/push and one PR; no merge/deploy/CI waiting. Architecture &
Audit review and CEO merge approval remain required. Subsequent bridge/storage work
requires a separate Work Order; no additional implementation is implied here.
