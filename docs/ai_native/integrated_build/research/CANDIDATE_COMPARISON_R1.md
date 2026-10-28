# Investment Research R1 — Guarded comparisons of candidate scenarios

**Implementation:** `ai_native.candidate_comparison.compare_candidates`.  
**Primary specialist:** Investment Research, subject-matter review pending.  
**Status:** `SCENARIO_ARITHMETIC_CONDITIONAL / NOT_SOURCE_AUTHENTICATED / NOT_AN_ALLOCATION_RANKING`.

## Why

M2 already calculates BEAR/BASE/BULL per-share terminal-return scenarios from **supplied** price/terminal/distribution assumptions. This connector makes two-to-six simultaneous candidate comparisons feasible in a **private, same-mandate** manual CC→IR→CC or CC→IR→PI→CC session, without fabricating probabilities, cross-currency returns, platform prices or benchmark Expected Return.

It uses the *original actual implementation* `evaluate_valuation_scenarios` per candidate, not another valuation formula. Each candidate supplies:
- `candidate_id` (unique), `role=SECURITY | REFERENCE_ETF`, `research_method_version`, `research_status=SPECIALIST_REPORTED | UNKNOWN`, `portfolio_room_status=ROOM_CONDITIONAL | ROOM_UNAVAILABLE | NOT_EVALUATED`, and `principal_failure_ref`.
- `valuation_inputs` with **all fields** of the single-security M2 scenario checker: same `analysis_id`, `analysis_as_of`, explicit security, quote date/source and native currency; source-based terminal values, methods, assumptions and distributions (or explicitly UNKNOWN); horizon and basis flags.
- Shared outer `analysis_id`, `analysis_as_of`, explicitly chosen `strategy_id`, `account_currency`, and 2–6 candidate records. All horizons must agree, securities and IDs must be distinct.

## Comparison rules

Each candidate preserves its original BEAR/BASE/BULL results, source refs, type of return, reported research/Portfolio Room statuses and strongest failure-reference. A pairwise **difference in displayed annualized percentage points** is computed per scenario **only** when all are true:

1. Both securities have the same account-native currency; the helper has **no FX translation model**, so even two USD holdings with a CAD account do not yield account-relative differences.
2. Exact quote observation dates match; both have the same analysis cutoff and horizon. The same share-class/corporate-action basis was separately asserted for each security; no independent issuer identity certification occurs.
3. Both scenarios report the **same return measure**: price-only CAGR with price-only CAGR; or conditional year-end cash-flow IRR with the same IRR type. Unknown distributions are never converted into zero.
4. No candidate mixes return-measure types across its own BEAR/BASE/BULL labels. These labels must be monotone in their **reported numerical** outcomes, else comparison is withheld pending definition review.

When comparable, `delta_first_minus_second_pp` is **arithmetic** on the rounded reported scenario results, not predicted outperformance or a risk-adjusted return. Otherwise `NOT_COMPARABLE` plus explicit reason codes and `null` delta are returned; the original research is kept rather than silently rejected. The ETF benchmark role does **not** certify VFV's forward Expected Return; no historical return is used as a forward input by this component.

**Mandatory missing pieces:** original financial source verification; normalized issuer business economics; defensible scenario probabilities; account FX, cash-flow/tax/fee treatment; liquidity, jurisdiction and benchmark source rights; accepted strategy, PI room/risk evidence, alternative opportunity costs. No trade, ranking, optimization, company admission, source-rights approval, or Investment Research method installation is granted. The numeric comparison, research narrative and private account context must not be copied into public GitHub or PAM Media.

## R1 manual usage

```python
from ai_native.candidate_comparison import compare_candidates
comparison = compare_candidates(
    analysis_id="SYN-MULTI",
    analysis_as_of="2026-10-28",
    strategy_id="EXPLORATORY",
    account_currency="CAD",
    candidates=[candidate_A, candidate_B],  # synthetic, full valuation input records
)
# For an IR route, pass the same dict as candidate_comparison_inputs
# to complete_manual_session(...). Keep both outputs PRIVATE.
```

The M7a opt-in `candidate_comparison_inputs` confirms exact request identity, date and **strategy**, runs the guarded comparisons, returns `candidate_comparison_private`, and makes the executive report `CONDITIONAL` with a warning that neither alpha nor portfolio superiority has been verified. `session_bridge.complete_manual_session` forwards it **only** for routes with an actual IR capsule; PI-only and CC-direct routes reject it. No automatic cross-Project transfer, user-account access or persistence.

**Checks:** 20 local synthetic unit tests PASS with the actual Git-verified `valuation_scenarios.py`; Python compilation PASS. The current M7a and session-bridge integration patches were inspected against canonical source, but **full canonical-repo / end-to-end regression has not been executed**. This does not complete the original 36-decision acceptance.
