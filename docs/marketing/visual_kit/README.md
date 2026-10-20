# PAM Macro Lens Visual Kit v1.0

**Target:** Blossom @therealpam; native drafting canvas 1080×1350 (4:5). **Status:** proposed repository implementation; no publishing or market-data access. Companion: `docs/marketing/MACRO_LENS_PLAYBOOK.md` and `MACRO_LENS_TEMPLATES.md`.

## M1 Global Equity Index Map (CEO-review prototype, not publishable)

**Daily M1 USD ETF shortcut (proposed PR #203):** [real-price CSV → real-data DRAFT map → independent Prompt 3 QA → CEO approval](M1_PRACTICAL_DAILY_WORKFLOW.md). The older 30-country source/capture/rights attestations should not prevent an internal research preview of original, attributed public closing-price facts. Actual source terms still matter; PR #203 is unmerged until separately approved.

The **M1 family** has a CEO-directed DEFAULT: an unspecified daily/world market map uses [USD U.S.-listed single-country ETF proxies](M1_US_COUNTRY_ETF_MODE.md), first researching appropriate ETF existence/listing for **all 30 countries** (not blindly trusting 25 old tickers). The [local-currency domestic-index map](GLOBAL_MARKET_MAP_M1_SPEC.md) remains an explicit opt-in. These modes measure different things and must never be mixed. The ETF candidate registry names up to **25 fund proxies** among the same 30 selected countries, with five no-proxy backgrounds. ETF returns include FX and U.S.-session repricing; never label them domestic stock-index performance. Both modes preserve full 30-country internal research decisions, country omissions as ordinary land, distinct synthetic render proofs, and external source/rights/factual review. The [M1 index-first methodology for **30 CEO-selected markets**](GLOBAL_MARKET_MAP_M1_SPEC.md), [offline renderer](render_global_index_map.py) and [explicit synthetic demo](examples/m1_global_index_synthetic.json) implement a local-currency domestic equity-index return map. The complete 30-candidate list, including Saudi Arabia → Egypt → Algeria after Turkey, remains internally **scan-checked**. **Only markets with qualified observations are colored**; missing, closed, stale, unlicensed or incomparable candidates receive ordinary unselected background land, not a gray unavailable color, legend or on-map omission message. The graphic says `N MARKETS SHOWN` (no `N/30` denominator), and the Singapore point exists only when eligible. The synthetic example plots **25 fictional returns** and omits five noneligible entries visually. A real edition requires independently reviewed complete 30-market daily scan decisions, original-source price-index comparability and quotation rights, source audit, exact native/390px review, approved pine logo and CEO approval of the exact asset and caption. PR #202 additionally includes the [offline M1 scan intake and rights-aware eligibility handoff](M1_DAILY_SCAN_HANDOFF.md) and [CLI](m1_scan_handoff.py), with zero source fetching or inherited synthetic prices. The employee must independently research every market and obtain actual source/rights review; **no live automatic market scanner or licensed world-index feed is implemented**. This is a governed research-intake and renderer contract, not a claim of source completeness or permission to post.


## E1 Company Lens (merged PR #201; publication approval still separate)

A bounded [E1 three-fact company research renderer](render_company_lens.py) and [single-filing methodology](E1_COMPANY_LENS.md) are proposed on a separate PR. E1 is a **distinct issuer-filing research plate**: thesis + original filing/event, exactly three historical reported figures with period/GAAP or non-GAAP/SEC-section provenance, three labeled editorial readings, counter-case and observable monitor. The [synthetic fictional-company example](examples/e1_synthetic.json) is strictly DRAFT, with a provisional P seal and example.org URL. No issuer feed, real company analysis, source/license validation, trading recommendation or publication authority is introduced. **Merged in PR #201; no specific real-data post has been approved.**

## Proposed M2 Sector Rotation renderer (separate CEO-review PR)

The [M2 Sector Rotation specification](M2_SECTOR_ROTATION.md) and [M2 deterministic renderer](render_sector_rotation.py) create a **distinct zero-centered 11-sector performance ranking** with two shared-index time horizons (source-bound 20-session price return and one-session return), computed positive-sector breadth and leader–laggard spread. [Synthetic DRAFT-only example](examples/m2_synthetic.json). This is a **candidate on its own PR**, not canonical until CEO merge. Sector index source rights, universe/20-session-count verification, accurate close prices, independent visual/factual audit and distinct post approval remain external human gates. M2 is not a live scan, total-return signal, performance claim or stock recommendation; synthetic source-free values cannot be released.

## Separate M4 Cross-Asset Market Brief implementation pilot

A bounded **M4 Daily Market Brief** proof-of-renderer lives in [render_market_brief.py](render_market_brief.py) with its own [cross-asset schema and methodology](M4_DAILY_MARKET_BRIEF.md). Unlike Macro Lens T1–T3, M4 uses a five-or-four-observation institutional research table spanning equity indices, rate yields, FX and commodity prices, with distinct percent versus basis-point comparisons and actual observed/prior-session dates. This design is **not an automated market scan or live-data feed**, and no fully audited real M4 post or blanket data-redistribution right is established by merging the renderer. See [synthetic never-publish example](examples/m4_synthetic.json) and explicit M4 negative regressions. The M4 renderer is a **separate entrypoint** and does not affect the T1/T2/T3 code paths, logo hash or release authority.

## What it actually does

Produces consistent branded SVG graphics, plus optional PNG, from manually sourced, reviewed issue JSON. Three real layouts share PAM identity but use different compositions:

- **T1 / The Mechanism:** a sourced signal, three causal or conditional text links, blind spot, tripwire.
- **T2 / The Divergence:** comparable A/B evidence cards, a cautious explanation, blind spot, tripwire.
- **T3 / The Regime Shift:** same series/units in two periods; then versus now, interpretation, tripwire. **Never invents a chart or historical path.**

The program has **no market data feed**, no publishing API, no autonomous recurring job and no factual validation of underlying linked sources. It checks source references, timestamps with timezone, completeness, length, matched periods/units where required, and blocks unresolved records and risky display overflow. A `VERIFIED` field is a **human research assertion, not proof**: an independent fact checker must open sources and recompute material claims. Image-generation tools must not fill these graphics with invented market figures.

## Brand identity — CEO-approved RECONSTRUCTED pine emblem (2026-10-19)

The CEO supplied a screenshot of the existing Blossom `@therealpam` profile emblem: a pine branch and hanging cone in forest green on a warm-ivory circle. The historical source file has **not** been recovered. A new 2048×2048 RGBA PNG was reconstructed from that screenshot; the CEO explicitly approved **v0.1 as PAM Macro Lens's production master on 2026-10-19**. This is **RECONSTRUCTED**, not the recovered or pixel-identical historical original. Do not describe it as a restored original.

Canonical, versioned provenance record: [PAM_MACRO_LENS_LOGO_RECONSTRUCTED_v0.1.json](assets/PAM_MACRO_LENS_LOGO_RECONSTRUCTED_v0.1.json).

- **Approved master custody:** ChatGPT Library → `/PAM/Brand Assets/PAM_Macro_Lens_logo_RECONSTRUCTED_v0.1_APPROVED_2048.png`. The binary is **not committed to this repo**; move an authorized copy from Library to the rendering host before production use.
- **Size:** 2048×2048 PNG (RGBA, transparent corners), 1,868,624 bytes. **Exact SHA-256:** `a352aa5dc6b9c5f1a142a36747eb4361a2d22cbc628805ee9a4e28da51ca9c75`.
- **Runtime binding:** supply that exact file through `--brand-logo /authorized/local/path/logo.png`, and put the **same SHA-256** in `brand_logo_sha256` in the issue JSON. The renderer rejects an unapproved PNG in release mode, even when an issue author changes their self-declared hash. The image bytes are embedded in the final SVG.
- **Provenance limit:** source avatar screenshot is small and partly occluded; the pine-cone scales and needle strokes differ from the historical design. The reconstructed file is the **approved new master**, not evidence of the old original.
- **Authority limit:** CEO *logo* approval is not CEO *post* approval. Every post still requires independent factual and visual audits of the **exact image + caption** and separate explicit CEO publication approval. No automatic merge, publication, or deployment.

Production handoff: retrieve the asset from its durable Library location, preserve bytes, verify the SHA-256 below and then supply the verified file to the renderer. **Never** use the screenshot, the provisional P badge, a different reconstruction, or an unverified logo as a release fallback. If the approved bytes are unavailable, **HOLD**.

```bash
python -c "import hashlib,sys; print(hashlib.sha256(open(sys.argv[1],'rb').read()).hexdigest())" /authorized/local/path/logo.png
```

The dark forest/ivory editorial design and circular seal remain unchanged; this is a narrow asset provenance + release-policy reconciliation, not a branding redesign.

## T1 Evidence+ (optional controlled pilot)

T1 Classic remains the default and renders exactly as before. An optional T1 `t1_variant: EVIDENCE_PLUS` adds **up to two source-linked supporting indicators** and **at most one zero-anchored monthly bar chart** (three or four consecutive verified observations) while preserving the hero fact, causal stages, blind spot and tripwire. The plotted numeric values are read directly from registered `evidence` records; unregistered raw chart values, non-finite figures, mismatched figure labels, mixed units or missing months halt rendering. The footer includes **all displayed evidence sources**.

See [T1 Evidence+ pilot contract](T1_EVIDENCE_PLUS.md) and [synthetic example](examples/t1_evidence_plus_synthetic.json). If the extra information fails to clarify the story or mobile readability suffers, use Classic. No chart is required. Factual truth still requires external source verification and final-artifact review; the machine validates only structural consistency. Existing logo-hash and CEO release safeguards are unchanged.

## Future Blossom visual system — specification only

The [PAM Blossom Research Visual System roadmap](../BLOSSOM_VISUAL_SYSTEM_ROADMAP.md) proposes additional market, equity, sector and portfolio-thought families with three analytical **depth** tiers. **None** of those proposed family renderers or associated market-data feeds are implemented by this repository change; the current executable renderer remains T1/T2/T3, with optional T1 Evidence+. Consult the [M1 Global Equity Market Map methodology](GLOBAL_MARKET_MAP_M1_SPEC.md) for required country universe, instrument-return comparability, geodata rights, session/FX/source/legend gates **before** building a map. Consult the [institutional T1 restyle brief](INSTITUTIONAL_T1_RESTYLE_PROPOSAL.md) before proposing changes to the current rounded-card layout.

For branding, the exact approved pine-logo bytes remain unchanged. A `©` symbol is **not** part of that logo and should not be added next to the masthead. If rights ownership is verified and CEO/Compliance approve a small footer notice, it may be developed as a separate optional typography element; there is **no copyright-notice renderer implementation in this roadmap**. A © mark does not grant market-data redistribution rights or substitute for source attribution.

## Optional T1 Research Note — implemented renderer pilot (CEO visual approval pending)

The existing `T1` default appearance remains **CLASSIC** for backward compatibility. For a source-backed T1 **Classic** issue only, add `"t1_layout": "RESEARCH_NOTE"` to an otherwise unchanged issue JSON to select an alternative institutional research-note geometry. That mode replaces the rounded signal/mechanism tiles with aligned typography, three ruled mechanism columns and an enlarged, unboxed WATCH statement. It **does not** add market data, change the economic fact fields, alter the caption, change the logo, or create a new source/release pathway. `t1_layout` is included in the existing `payload_hash`, so layout changes invalidate an earlier SHA-bound publication approval.

- `t1_layout` omitted or `"CLASSIC"`: existing unchanged T1 Classic illustration.
- `"RESEARCH_NOTE"`: **opt-in** T1 Classic editorial layout requiring actual 390px PNG visual inspection.
- `t1_variant: EVIDENCE_PLUS`: **unchanged old Evidence+ composition**, and explicitly incompatible with Research Note until independently restyled and tested.
- `T2`/`T3`: unchanged layouts; T1-only field is rejected.
- Any long headline, unusual glyph, source byline, chart or footer collision: renderer may HOLD; shorten nonessential copy accurately or return to Classic. Do not fabricate/omit sources.

Synthetic, **never-publish** example: [T1 Research Note fixture](examples/t1_research_note_synthetic.json). The exact approved logo bytes must still be provided and SHA-bound for final branded rendering; without them a draft shows a provisional P seal.

```bash
python docs/marketing/visual_kit/render_macro_lens.py \
  docs/marketing/visual_kit/examples/t1_research_note_synthetic.json \
  --output /tmp/research-note-draft.svg --png /tmp/research-note-draft.png
```

This is a controlled visual implementation, **not** an editorial-quality auto-PASS. Compare a real factual issue in the old and new layouts using identical evidence/caption/logo, inspect a native PNG and 390px view, perform independent source/visual review of the exact candidate, and obtain separate CEO approval for the final image and caption before publication. The CEO has not approved this pilot's exact new appearance merely by requesting its implementation.

## Institutional editorial design — mandatory visual review

Use the [Institutional Editorial Design Gate](INSTITUTIONAL_EDITORIAL_STANDARD.md) when assessing any actual T1 Classic, T1 Evidence+, T2 or T3 PNG. A sober mobile-first macro research note is the editorial target: meaningful hierarchy, restrained rounded containers, nondecorative dividers, source-backed evidence and a readable mechanism. Technical CI verifies deterministic renderer behavior, **not** that a draft looks appropriately professional. Inspect at 1080×1350 and at 390px feed width, mark each of the six design gates PASS/HOLD and escalate a visibly childish or cluttered render as **VISUAL HOLD** before CEO post approval. The current renderer's appearance is not automatically changed by this documentation; design improvements require their own reviewed implementation PR, rendered proof and fresh independent factual/visual audit. This is a more demanding **editorial acceptance standard**, not a change to factual or publishing authority.

## Default source labels and independent provenance

**Keep the published graphic short by default:** populate each displayed evidence record's `source_title` with a **concise, accurate and recognizable publisher label** (for example `U.S. BLS`, `BEA`, `Federal Reserve`, `Statistics Canada`) only when that label unambiguously identifies the original publisher. The renderer **does not auto-abbreviate** `source_title`; it repeats the supplied labels and safely wraps long ones when necessary. Do not abbreviate an obscure agency into an ambiguous acronym or silently omit any materially distinct source used in the displayed indicators/chart. If an accurate short label cannot fit, use supported wrapping or HOLD. Preserve exact source publisher, official release/article title, full original URL and all observation/retrieval/publication dates, figures, units and calculations in the independent evidence register. Concise on-image attribution never reduces the independent auditor's evidence requirements.

## Clean-slate retest after replacing old concepteur/audit chats

The repository stores the **template, renderer and approval gates**; it does not guarantee the old conversation's exact live issue JSON, Blossom caption, 14-claim register, primary source snapshots or final render are recoverable. **Before deleting the only copies of a test's materials**, save the exact issue JSON, evidence register, caption, source links and draft SVG/PNG in a deliberately retained, authorized location if the goal is to reproduce the same proposal. Otherwise start a **new independent source-verification pass from original authoritative releases**, create a self-contained evidence register and label it as a new test/revision; do not invent missing prior inputs or re-use a prior PASS. The new concepteur should follow the canonical branch, use the exact approved SHA-matching logo from Library, render **DRAFT**, and supply the full review packet. A **separate auditor** must independently open primary sources and audit that exact graphic plus caption. CEO review of the exact final artifact is still required for publication. Do not post automatically.

## Minimal usage

Run from repository root (Python 3.11+):

```bash
python docs/marketing/visual_kit/render_macro_lens.py \
  docs/marketing/visual_kit/examples/t1_synthetic.json \
  --output /tmp/macro-lens-draft.svg \
  --png /tmp/macro-lens-draft.png
```

SVG: Python standard library only. PNG: PyMuPDF (`fitz`), already pinned in the repository `requirements.txt`. Rendering is offline, self-contained, with no external API call or obligatory paid service. No installation or hardware assumptions beyond normal local Python and the dependency, which may be absent on a given host (in that case omit `--png`). All static assets are code; fonts are system fallback only; no redistributed fonts. PNG path must be writable. SVG can be opened directly in a browser.

Example JSON files contain **synthetic layout-only** tokens, not actual verified economic information. Generated previews have **DRAFT · NOT AUDITED** and a provisional P-brand mark. Never publish them, even if they look finished. The exporter actively rejects a release manifest paired to these fixtures.

## Draft to approved final

1. Research **one meaningful topic**, compile an internal evidence register and independent sources, record full URL, date, precise observation time, currency/units/period, calculations and verification notes. Store the original source outside the image. Create a JSON issue like one of the examples, replacing every synthetic field with real, checked content. Do not copy synthetic metadata into a real draft.
2. Run the renderer. On schema, source, timestamp or layout problems it exits with `HOLD` (exit code 2) instead of fabricating data or silently truncating text. SVG carries a DRAFT watermark. Keep the caption in the editorial handoff (outside the image JSON); independently review caption as well.
3. Give the **exact actual draft image + its final caption + source register** to a skeptical independent reviewer. Correct errors and rerender until the final image is factually consistent and legible at actual Blossom feed size. If the underlying data can't be verified, do not publish.
4. Obtain **explicit CEO approval of that exact final artifact and caption**. The caption is included in the hashed JSON, so any change invalidates prior authorization. A separate audit manifest can be recorded, e.g.:

```json
{
  "input_sha256": "PUT_RENDERER_OUTPUT_INPUT_SHA256_HERE",
  "independent_audit": "PASS",
  "auditor_reference": "external fact-check record link/ID",
  "ceo_approved": true,
  "ceo_approval_reference": "explicit approval of exact asset and caption"
}
```

5. Only then render a non-watermarked final graphic:

```bash
python docs/marketing/visual_kit/render_macro_lens.py approved_issue.json \
  --release-manifest independent_review_and_ceo_approval.json \
  --brand-logo /path/to/official_pam_logo.png \
  --output /tmp/macro-lens-approved.svg \
  --png /tmp/macro-lens-approved.png
```

The input SHA-256 binds the manifest to a specific JSON payload including `brand_logo_sha256`; the CLI separately hashes the PNG bytes and rejects any mismatch. Release is blocked unless the exact CEO-approved reconstructed logo file is supplied and its hash matches the canonical approved hash; any content change invalidates that manifest. **The manifest is not cryptographically authenticated**, does not prove a human actually reviewed it, does not validate remote claims, and should be managed through CEO-controlled procedures. Publication itself is separate and manual unless the CEO explicitly authorizes a supported publishing workflow.

## Fact sheet JSON contract

Required top-level fields:

| Field | Requirement |
|---|---|
| `schema_version` | `"1.0"` |
| `issue_id` | `ML-YYYYMMDD-NN` |
| `template` | `T1`, `T2`, `T3` |
| `account` | `@therealpam` |
| `issue_at` | ISO-8601 timestamp with explicit UTC offset |
| `headline`, `deck`, `blind_spot`, `tripwire` | Concise public text; strict length and layout limits |
| `caption` | Exact proposed English Blossom caption; excluded from SVG layout but INCLUDED in hash-bound review |
| `brand_logo_sha256` | SHA-256 of the exact CEO-approved reconstructed v0.1 PNG listed in `assets/PAM_MACRO_LENS_LOGO_RECONSTRUCTED_v0.1.json`; required with `--brand-logo` and for final release. Omit in synthetic draft examples. |
| `evidence` | 1+ records with claim ID, label, display, unit, period, observation timestamp, retrieval timestamp, original HTTPS source, short title, verification note, classification and review status |
| `fact_ids` | T1: one evidence claim ID; T2/T3: two IDs |
| `mechanism` | T1: exactly three short text links |
| `interpretation` | T2/T3: qualified explanatory statement |

T2 requires equal periods and exact observation timestamps to avoid deceptive juxtapositions. T3 requires a matching metric label/unit and genuinely different periods and observation times. Stronger economic comparability checks still require human review. The tool omits charts rather than invent historical shapes.

## Reusable editorial handoff

```text
Issue and topic:
Why now:
Template choice (T1/T2/T3):
Verified source list + observation times:
Mechanism / alternative explanation:
Draft SVG/PNG + caption:
Independent visual and factual audit verdict:
CEO approval of exact final asset:
Published Blossom URL (only after actual publication):
Observed metrics and editorial experiment ID:
```

## Tests and scope

```bash
cd docs/marketing/visual_kit
python -m unittest discover -s tests -v
```

The tests use only synthetic mock observations. They cover XML escaping, all three layouts, unit/session comparability, missing/unverified evidence, unsafe URLs, oversized text, draft watermark, SHA-linked authorization, logo-asset hash binding and local PNG dimensions. They do **not** establish source truth, macroeconomic accuracy, independent compliance approval, actual Blossom upload behavior or follower conversion.

This is a pure documentation/graphic creation utility. **No product/model changes, investment decisions, data sources, scheduling, account publication privileges or spending authority are introduced.** Keep Marketing & GTM charter and CEO merge/publication gates intact.

### Lightweight reuse & resource assessment

- **REUSE:** Python standard library for file validation, XML escaping, structured deterministic SVG; no new dependency for SVG. Existing pinned PyMuPDF handles optional SVG→PNG conversion. Licensing: Python PSF, PyMuPDF AGPL/commercial dual license; **potential commercial redistribution/use implications must be reviewed by Commercial & Compliance before external distribution of this renderer**, although local internal research use is the proposed pilot. Do not claim the dependency has no legal constraints.
- **ADAPT:** Basic no-cost platform SVG/browser display uses normal browsers. Not relying on third-party web rendering, AI-generated charts, subscription services or data APIs.
- **BUILD (bounded):** small bespoke design layouts, because brand-specific information architecture and strict fail-closed fields are the functionality sought. No external monetary outlay required for an SVG-only pilot. PNG export uses already pinned dependency; compatibility with each actual PAM host has not been established. Chromebook/WSL resource footprints unmeasured and no production host change proposed.