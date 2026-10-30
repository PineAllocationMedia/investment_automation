# PAM Financial Systems — single GitHub repository archive (R1)

**Authority:** CEO location selection 2026-10-30; human-managed archive option B unchanged.
**Status:** LOCATION_APPROVED / NO_CASE_STORED / CONFIDENTIAL_WRITES_BLOCKED / RECOVERY_NOT_RUN.
**Users:** multiple investors, portfolios, accounts, strategies, securities and later CEO-requested reviews.

## Repository paths (proposals, not verified case files)

```text
archives/r1/README.md
archives/r1/research/<opaque-id>/report.md    # cleartext ONLY after human privacy and rights review
archives/r1/cases/<opaque-id>/manifest.json   # minimal, non-identifying lookup metadata
archives/r1/protected/<opaque-id>.age         # proposed ciphertext ONLY after cryptographic gate
```

All repo readers and connected apps with repo scope may see all paths, manifests and ciphertext; **folders do not isolate permissions**. Use opaque identifiers that do not encode names, broker IDs or source-private identifiers. Repo-private status is necessary but not a confidentiality guarantee. Git commits, PRs, CI and history permanently retain data unless specially remediated; `.gitignore` does not prevent API-based writes or clean existing history.

## First usable manual step: reviewed non-sensitive research

1. Only for an explicit CEO mandate, CC/IR prepares a dated report with source URLs/accessions, method versions, relevant S/F/K/V fact/calc/scenario status, key assumptions, alternative thesis, caveats and provenance. PI adds private information only where actually authorized; **do not copy its sensitive content into the GitHub research report**.
2. A person reviews **the exact content** for consent, rights, personal identifiers, names of other clients, disclosed positions/costs/taxes, restricted source originals and possible reidentification from cross-references. If uncertain, do not upload in plaintext. An independently verified `prepare_archive_locator` function can create only generic *candidate paths* from constrained metadata and never approves material.
3. After explicit authorization, a bounded PR adds ONLY reviewed research and an opaque case index on V2. A branch or open PR is not an approved archive; CEO separately authorizes merge. Corrections should add a dated linked amendment, never silently rewrite original facts.
4. On a new CEO-initiated follow-up, CC/IR uses actual GitHub access to retrieve the merged case, preserving exact case/commit, as-of/source cutoff, method version and evidence qualifications. Missing access or missing record means `BASELINE_NOT_AVAILABLE`. Do not claim a method was loaded merely because its path was cited.

## Tier III — protected material (do not upload yet)

Raw M4 `private_case_envelope` and M3 `private_portfolio_snapshot_envelope` are **plaintext**; unkeyed SHA-256 copy checks are neither encryption nor authenticity. Never upload such bytes to GitHub, PRs, Actions, logs or Media. Real personal or third-party holdings, screenshots, transactions, accounts, tax and private source payloads are BLOCKED.

Before any real protected upload, verify a vetted implementation of authenticated encryption (e.g., standard `age`, not homemade cryptography), encrypt/decrypt **outside GitHub**, ensure encryption keys and credentials never enter repo/GitHub Actions/PR logs, independently review permission scopes, rights and consent, and test an encrypted synthetic round-trip with a second human-controlled recovery from a fresh checkout plus key backup/loss procedure. An `.age` filename alone proves nothing. Ciphertext can still leak time, size, names and linkages. Sources prohibited from copying remain outside even when encrypted. After these checks, CEO must separately release actual sensitive uploads. There is no default agent decryption or automatic Project sync.

**Result statuses:** `ARCHIVE_NOT_SAVED` until actually merged case content; `ARCHIVE_SAVED_READ_UNVERIFIED` until actually read by a suitable Project; `ARCHIVE_SAVED_AND_READ_VERIFIED` only after both steps with evidence. These statuses do not certify source authenticity, security readiness or full R1 acceptance. No background research, trading or automatic archival.

## Manual GitHub repository save / read-back (synthetic transport example)

The paired `archives/r1/cases/R1-SYNTHETIC001/manifest.json` and `archives/r1/research/R1-SYNTHETIC001/report.md` are **synthetic demonstration only**: no investor, company or authentic source data. Their `report_git_blob_sha` is the actual Git blob identifier for the unchanged UTF-8 report. An authorized reader can fetch both paths from a **specific merged V2 commit**, compare the blob IDs and optionally run `ai_native.repository_archive.verify_retrieved_research_report(manifest, report_text, retrieved_path=..., retrieved_blob_sha=...)`. That pure helper compares identity, path and Git object content and intentionally cannot claim rights/privacy approval, financial source authentication, archival durability, Project access or merged status by itself. A synthetic case is explicitly **ineligible as a research history baseline**. The functional real-case workflow remains: CEO asks, CC compiles a report, authorized human reviews the exact non-sensitive text/rights, PM prepares a PR using GitHub, CEO merges, then an actually connected Project reads that commit on a later CEO-initiated request. At present, authentic CC/IR GitHub access, human-reviewed real record, private encryption and restore are `NOT_VERIFIED`.
