# M1 daily national-index scan — bounded employee research handoff

**Status:** PR #202 DRAFT. Implemented **offline intake/eligibility tool**; autonomous market-data acquisition, worldwide daily publisher snapshots, index-variant adjudication and redistribution entitlements are **NOT IMPLEMENTED**. Nothing is approved for publication.

## Why this boundary exists

The CEO expects a simple Prompt 2 instruction such as **“Full world map daily scan of national equity-market performances.”** The requested outcome is a credible M1 equity index map, not an optional synthetic infographic.

The research employee must attempt all **30** CEO-selected countries and keep the **complete internal audit ledger**, including each researched but excluded market. The exact universe/order is pinned in [the M1 method contract](GLOBAL_MARKET_MAP_M1_SPEC.md). The final map highlights only eligible local-currency **price-index** returns and renders unavailable countries as **ordinary unselected land**, with no gray unavailable category. If Singapore is not eligible, omit its point locator.

An accurate worldwide map needs **two separately controlled inputs**: (1) original financial observations and closed-session context, and (2) permission for this exact public/social display. Free viewability, delayed public quotes and generic source citations **do not convey reuse rights**.

### Lightweight existing-source / cost assessment

| Candidate | Capability | Commercial social-graphic redistribution | Decision |
|---|---|---|---|
| Original exchange sites (e.g. TWSE/JPX/KASE) | Precise index variant and original price observations in some jurisdictions | Exchange-specific licensing; **not established in this PR**. TWSE requires trading-information agreements for some uses | **RESEARCH ONLY / rights HOLD** |
| Yahoo Finance and comparable free portals | Broad practical global discovery leads | Yahoo explicitly disallows redistribution of supplied financial information; underlying venues have distinct rights | **DO NOT use as presumed publishable data feed** |
| EODHD-type broad market-data APIs | Consolidated technical acquisition potential | Proprietary API, terms, subscriptions and rights must be independently assessed; $0 completeness/rights not established | **NO ADOPTION without CEO authorization** |

This PR adopts the narrowest $0-incremental-dependency, standard-library **offline research handoff** rather than installing a questionable scraper or silently assuming data licenses. Operationalizing an automatic global data feed remains a distinct Data & Evidence / Commercial & Compliance work item. There is **no $0 validated universal licensed provider** established by this assessment.

## Repeatable runbook

Use an actual UTC cutoff, after deciding whether the subject means the **latest completed** session in each local market or a specific previously completed market day. Never label a live U.S. session as a completed close. The employee, not the CLI, must investigate publisher/benchmark definitions, calendar and quote rights.

Run from `docs/marketing/visual_kit` on PR #202's **authorized feature branch**:

```bash
python m1_scan_handoff.py init \
  --cutoff-utc 2026-10-20T23:00:00Z \
  --out m1_20261020_research_packet.json
```

The file contains **30 ordered `UNRESEARCHED` rows with null quotes**. Candidate names/currencies are imported from the synthetic example for *assignment labels only*; not one synthetic close or live-data assertion is inherited.

For each row, save:
1. **Attempted authoritative sources** (original exchange/index administrator first), the index's exact series/return variant, currency, session and source capture reference.
2. If qualification fails: `decision=EXCLUDED`, `exclusion_status` in `MISSING|HOLIDAY|CLOSED|STALE|INCOMPARABLE`, a meaningful `research_notes` rationale and no `qualified_quote`. No source URL is required if none exists.
3. If a completed local-price return can be shown: `decision=QUALIFIED` and `qualified_quote` with exact publisher, index name/variant, original HTTPS URL, relative local source capture path + SHA-256, source title, local currency, completed prior/current closes, timestamp-with-offset for each, a retrieval timestamp and explicit rights-evidence URL, **relative local rights-evidence capture path + SHA-256**, and independent rights/facts review references.
4. Put **actual nonempty original-source and rights-document capture files** in a private, access-controlled evidence directory. The qualified row needs `source_capture_path`, `source_capture_sha256`, `rights_capture_path` and `rights_capture_sha256`. Paths must stay beneath the supplied evidence root. The tool opens each file and checks its **actual SHA-256 bytes**; it rejects absent/tampered/out-of-directory captures. Do **not** commit restricted or proprietary captures to a public GitHub branch.
5. For real qualified rows, `rights_decision=APPROVED_FOR_EXACT_USE`, `rights_scope=PUBLIC_BLOSSOM_INDEX_RETURN_GRAPHIC` and `fact_decision=INDEPENDENTLY_CHECKED` are **external reviewer assertions**, not something the script can discover or establish. The named rights/factual reviewer must actually inspect original sources and terms and keep an audit trail. An original-source file capture proves only **which bytes were archived**, not that the material is correct, authentic, properly licensed or permissioned. A string or hash alone is never legal proof.

**Never copy fictional 2026 sample returns or hypothetical example.org URLs into a genuine research packet.**

Diagnostic assessment:

```bash
python m1_scan_handoff.py assess m1_20261020_research_packet.json \
  --report m1_20261020_assessment.json \
  --evidence-root /private/m1_20261020_captures
```

If any country remains `UNRESEARCHED` or fewer than four price-index returns meet qualified input requirements, the tool reports **HOLD**. It blocks swapped/duplicate countries, provisional sessions, invalid numeric closes, future source retrieval, absent original URLs and missing rights/facts review assertions.

Only after independently evidenced full packet review and CEO-approved route should the separate editorial issue metadata be supplied and a **DRAFT ONLY** M1 issue produced:

```bash
python m1_scan_handoff.py assess m1_20261020_research_packet.json \
  --report m1_20261020_assessment.json \
  --issue-metadata m1_20261020_editorial_metadata.json \
  --draft-issue m1_20261020_candidate_draft.json \
  --evidence-root /private/m1_20261020_captures
```

The draft path is *never* an automatic post or audit PASS. The CLI passes the candidate issue through the existing deterministic M1 validator. The map renderer and its release approval are separate. If a complete, source-backed issue survives independent factual/visual review, inspect the actual 1080×1350 and 390px PNG, exact logo SHA and final caption. The CEO must approve **the exact publication candidate** before posting.

## Independent human/employee review criteria

- Independently reopen and preserve original exchange/administrator observations and note the precise local calendar/time zone and series basis.
- Independently recompute daily signed price-index returns; do not splice total-return indices, ETFs or FX into a domestic price-return map.
- Check cited copyright/licensing/redistribution terms for **this social-graphic use**, including any fees or attribution requirements. If ambiguous or commercial risk is material, HOLD and escalate to Commercial & Compliance / CEO.
- Count **all 30 scan decisions**. Audit excluded markets too. Source voids and holiday closure should be genuine research outcomes, never an editorial attempt to inflate coverage.
- Verify the visible subset is truthful, geographically representative enough to justify a *world* headline and not misleadingly described as 30 completed market returns.
- Independently inspect issue JSON, original captures, 1080x1350 PNG, 390px mobile view and English caption. No automated/posting authorization exists.
- Never auto-update CEO-protected constitution, strategy, role charter or decision registry.

## Remaining operational acceptance gate

**The original user goal is not yet closed.** A reproducible *true live-data end-to-end trial* still requires:
1. Verified employee web/source acquisition and durable evidence snapshots for the desired cutoff, not just an instructions document;
2. Individual benchmark identity/price-vs-total-return and session-calendar verification;
3. A rights/redistribution decision for each colored market;
4. A full 30-market research ledger, at least four authentic qualifying closes and independently checked provenance;
5. Native/mobile real-data rendering, a separate exact-asset audit and CEO publication approval.

Until those are observed **PASS**, M1 is an accurately implemented *rendering and research-intake prototype*, **not** an autonomous full-world financial-data feed. Never lower the gate to manufacture a passing visual.
