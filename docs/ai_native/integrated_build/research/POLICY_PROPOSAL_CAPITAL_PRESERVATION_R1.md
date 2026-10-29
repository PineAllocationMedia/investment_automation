# R1 strategy policy proposal — Capital Preservation

**Status:** `PROPOSAL_ONLY / NOT_APPROVED / NOT_LOADED` (2026-10-29).
**Scope:** CEO-confirmed R1 strategy D; this text is **not a new authorized investment rule**, nor a substitute for a separately approved CEO policy. **Accountable owner:** Program Manager for the decision package; independent Investment Research / Portfolio Intelligence / material-risk review before proposed approval. 
**Dependencies:** [R1 delivery plan](../DELIVERY_PLAN.md); [36-decision Blueprint](../../../strategy/PAM_FINANCIAL_SYSTEMS_AI_NATIVE_REFORM.md); `PAM_PROJECT_CONSTITUTION.md` §§3–4; `governance/PAM_GOVERNANCE.md`; R1 source/valuation/portfolio contracts.

## Intended role — proposal, not operational instruction

Capital Preservation should evaluate **maintaining the investor's stated capital objective, meeting liquidity needs, and limiting permanent impairment**, not simply apply High-CAGR's equity, VFV, opportunity-cost hurdles, concentration or reserve assumptions. Preserve the five common lenses (Quality, Durability, Expected Return, Confidence, Portfolio Room); their *interpretation and decision response* must be specific to this mandate and independently approved.

**Provisional design preference for CEO consideration:** Capital safety and required liquidity take precedence over maximizing compound returns. Include inflation/purchasing-power and reinvestment risks explicitly. Do **not** treat this preference as policy until approved.

## CEO policy choices to resolve before decision-grade operation

| Decision field | Concrete choices for CEO review — **all unapproved** | Current authorization |
|---|---|---|
| Objective / capital measure | A. Nominal capital preservation; B. Inflation-adjusted purchasing-power preservation; C. Liability/withdrawal-matching; D. explicit hybrid with priority order | `UNKNOWN` |
| Time horizon / required liquidity | Define dates and withdrawal schedule; immediate-access need; whether liabilities are CAD, USD or other currency. No default term. | `UNKNOWN` |
| Risk budget / loss definition | Define acceptable probability, size and duration of temporary loss **and** unacceptable permanent loss; distinguish issuer default, market-price drawdown, inflation, FX and liquidity loss. | `UNKNOWN` |
| Eligible vehicles and issuer risk | Decide eligible insured deposits, sovereign bills/bonds, government/credit funds, GICs/term deposits, investment-grade credit, equities, ETFs and cash-like instruments; specify guarantees, lockups, credit ratings and currency constraints; never assume coverage/insurance. | `UNKNOWN` |
| Benchmark and alternative | Choose an instrument/currency/duration-matched reference, e.g. a *verified* permitted cash/T-bill or government-bond total-return series, with inflation/liability comparator if appropriate. VFV is **not** automatically the hurdle. | `UNKNOWN` |
| Diversification, concentration, currency, duration | Define sovereign/issuer/credit limits; interest-rate duration and inflation sensitivity; account-currency vs spending-currency matching; foreign-asset and ETF look-through constraints. | `UNKNOWN` |
| Liquidity / reserve policy | Decide whether a **standing strategic liquidity reserve** is permitted or required for this new R1 mandate. This may differ from existing V2 modes' reserve-last hierarchy; any actual conflict requires an explicit, narrowly scoped CEO policy decision, **not** a silent override. | `UNKNOWN / CEO_POLICY_GATE` |
| Expected Return and evidence grade | Nominal/real after-cost total return distribution over mandate horizon; rate changes, default/reinvestment/inflation scenarios; never extrapolate yields as guaranteed returns. Define acceptable data support for `EXPLORATORY` vs decision-grade. | `UNKNOWN` |
| Contribution allocation / selling | Prefer newly supplied capital and liquidity matching; specify when rebalancing, liquidation, maturity rolling or thesis-driven sale would be reviewed; include fees, FX, tax and account withdrawal costs. No executable orders. | `UNKNOWN` |

## Proposed R1 specialist behavior **only after approval**

- **CC**: collect the capital definition, loss/liquidity budget, date and spending currency; if decisive fields are missing, ask for those or maintain `UNKNOWN` and exploratory status. An ordinary High-CAGR request never silently becomes preservation.
- **IR**: assess issuer/vehicle, real-vs-nominal economics, credit, duration, inflation, reinvestment, guarantees, rate changes and liquidity on sourced, as-of-consistent facts. Apply scenario/quote math only to evidence-backed inputs; never mark a government instrument risk-free across currencies or holding periods.
- **PI**: on dated private scoped holdings, examine liquidity gaps, concentration and account/tax/FX costs; issue only qualified new-contribution percentages when the selected *approved* policy and source facts justify them. Selling remains a separate human decision.
- **CC report**: show protection objective and horizon, supported vs unsupported capital-risk routes, five contextual lenses, cost/FX/rights gaps, liquidity timing, scenarios, worst credible outcome and next human check. No numeric safety score or policy-sounding decision when the method is not approved.

## Target acceptance cases after implementation (NOT_RUN)

1. A short-liability CAD mandate vs a long-duration foreign bond; test real economic, FX and liquidity risks.
2. An apparently safe high yield with insufficient credit/source assurance; return `EVIDENCE_RESOLUTION`, not safety certification.
3. A partially visible portfolio, uncertain cash and unknown liquidation/FX costs; Portfolio Room must remain conditional.
4. Changing `strategy_id` without changed issuer/price facts must not change the underlying facts.
5. Before CEO policy approval / method actually loaded, only neutral exploratory research and explicit `STRATEGY_POLICY_NOT_APPROVED` or equivalent gating; no preservation allocation.

**Approval request:** CEO to select / approve the policy fields above after proportionate independent technical/economic review. Then create an explicitly versioned implementation contract, actual four-strategy IR/PI/report wiring and checked evidence. Any protected canonical text change requires **separate explicit CEO authorization**. This file is not an approval record; status stays `PROPOSAL_ONLY`.
