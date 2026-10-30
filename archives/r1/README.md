# PAM R1 archive entrypoint — one private repo

PAM Financial Systems archives may cover different issuers, people, accounts, strategies and portfolios. Read the [governed archive procedure](../../docs/ai_native/integrated_build/operations/GITHUB_SINGLE_REPO_ARCHIVE_R1.md).

- `research/<opaque-id>/report.md`: human-reviewed, rights-cleared **non-sensitive research** only.
- `cases/<opaque-id>/manifest.json`: opaque, non-identifying locator only; no account data, holdings or private case payload.
- `protected/<opaque-id>.age`: encrypted-only **after** independently verified cryptography, consent, keys outside GitHub, restoration and separate CEO release. **Protected uploads BLOCKED.**

Any agent with repository read access may see filenames and ciphertext; folders are NOT per-agent access controls. Never commit raw private-case JSON, passwords, keys or confidential personal/third-party data. No actual case has yet been stored or recovered.

## Non-sensitive synthetic transport example (not a financial case)

A demonstration pair at [synthetic manifest](cases/R1-SYNTHETIC001/manifest.json) / [synthetic report](research/R1-SYNTHETIC001/report.md) shows how a real GitHub blob and opaque manifest can be stored and re-fetched **after a CEO-controlled merge**. Neither record is an investor analysis, a verified original source, an accepted private archive or a historical baseline for financial follow-up.
