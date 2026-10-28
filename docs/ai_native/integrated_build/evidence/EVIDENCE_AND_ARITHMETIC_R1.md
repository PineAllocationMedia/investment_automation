# M5 R1 — Source-neutral fact compatibility and bounded arithmetic

**Primary specialist role:** Data & Evidence. **Status:** CANDIDATE / COMPONENT-TESTED LOCALLY / NOT INTEGRATED.  
**Module:** `ai_native.evidence_math.audit_calculation` (Python stdlib only). **Scope:** arithmetic checks on caller-supplied facts in the Financial Systems integrated build, not a replacement of V1/V2 qualification contracts.

## Why this module exists
M2's source-fusion research often combines issuer publications, financial platforms and different accounting standards. M3's portfolio input is dated and separately scoped; M4's report renderer is intentionally read-only. This very small deterministic calculation boundary helps prevent AI-generated growth, margin and cash proxy arithmetic from silently combining different currencies, fiscal periods, issuers, reporting bases, or inaccessible source claims. It **does not** make the underlying financial fact true.

## Input schema
Call `audit_calculation(operation, left, right, as_of="YYYY-MM-DD")`. Each fact is a mapping with string values:
`id`, `economic_issuer`, `metric`, `value` (decimal string), `currency`, `unit`, `accounting_basis`, `consolidation`, `period_start`, `period_end`, `observed_at`, `source_url`, `rights_status=PERMITTED|UNCERTAIN|RESTRICTED`, `verification_status=VERIFIED|INDICATIVE|CONFLICTED|MISSING`.

The `VERIFIED` label is *caller-supplied*; this module neither opens the URL nor certifies an original-source check. Fact IDs remain recoverable and are not re-identified as independent evidence. `observed_at` measures record observation, not historical public availability. Input numeric units must already be on the same scale; the tool never converts FX, ADRs, currencies, units or accounting concepts. `unit` is the numeric magnitude (e.g., `MILLIONS`); `currency` separately indicates denomination.

## Closed list of supported calculations

| Operation | Left / right metric | Calculation | Non-negotiable boundary |
|---|---|---|---|
| `OPERATING_MARGIN` | `OPERATING_INCOME` / `REVENUE` | operating income ÷ positive revenue × 100 | Exactly same issuer, basis, consolidation, monetary unit/currency, date span; concept comparability still requires human review |
| `REVENUE_GROWTH_YOY` | current `REVENUE` / prior `REVENUE` | (current ÷ positive prior − 1) × 100 | Full-year periods adjacent with consistent 360–371 days and at most 2-day duration difference; disallows 52/53-week mechanical comparison |
| `CFO_LESS_PPE` | `CFO` / `PPE_CASH_OUTFLOW` | CFO − nonnegative PPE cash outflow magnitude | **Descriptive proxy only**, NEVER normalized FCF or owner earnings; no lease/intangible/acquisition normalizations presumed |

The result is `FORMALLY_CALCULATED` with two-decimal display, precise fact IDs, original evidence labels, rights statuses, `source_verification=NOT_PERFORMED`, `decision_grade=false`, and `temporal_authority=CURRENT_OBSERVATION_ONLY`. When incompatible, return `UNAVAILABLE` with explicit reason codes instead of silent corrections or source substitution. Known restricted use and unresolved `CONFLICTED/MISSING` inputs block the calculation. `UNCERTAIN` source-use rights preserve a caution and require separate human review; no license is granted.

### Example — synthetic records, not an issuer analysis
```python
from ai_native.evidence_math import audit_calculation
# Supply two independently sourced facts according to the schema above.
result = audit_calculation("OPERATING_MARGIN", op_income_fact, revenue_fact, as_of="2026-10-28")
# FORMALLY_CALCULATED means arithmetic only. Never promote to original-source VERIFIED.
```

## Integration and trust
Use this helper as an **optional component check** in a genuinely accessible IR session or Work process, passing a complete fact record and returning K calculation IDs in IR_CAPSULE/EVIDENCE_ANNEX. An inaccessible GitHub URL does not mean a ChatGPT Project loaded or ran Python. M4 cannot independently verify source labels. Do not use this helper to infer portfolio allocations, expected returns, FX, backtested PIT or compliance with any investment-admission gate.

**Review gaps:** applicability to nonstandard accounting periods and taxonomy-specific revenue/operating-income concepts requires explicit economic analysis; the simple adjacency/duration gate is intentionally conservative and may refuse valid reports. Provenance rights may be uncertain; no automated cross-source authentication is claimed. No automatic schedules, recurring research, personal holdings or external spending.
