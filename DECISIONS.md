# Investment Automation — Decisions Log

## 🎯 Purpose

This file tracks all major design and investment decisions made in the system.

Each decision must include:
- what was changed
- why it was changed
- expected impact

This ensures long-term consistency and prevents model drift.

---

# 📌 Decisions

## 2026-06-24 — Adopt long-term DCA as core strategy

### Decision
The system uses Dollar Cost Averaging (DCA) as the baseline investment strategy.

### Reason
- Reduces timing risk
- Improves behavioral discipline
- More robust than market timing

### Expected impact
More stable long-term returns with lower variance.

---

## 2026-06-24 — Avoid market timing strategies

### Decision
No strategy based on short-term market prediction is allowed.

### Reason
- Market timing is not statistically reliable
- High risk of overfitting in backtests

### Expected impact
Improved robustness and reduced model fragility.

---

## 2026-06-24 — Introduce Canadian tax-aware logic

### Decision
All investment evaluation must consider Canadian tax structure (TFSA, RRSP, taxable accounts).

### Reason
- Real investor is based in Canada (Quebec)
- After-tax return is more important than gross return

### Expected impact
More realistic portfolio optimization aligned with real-world returns.

---

# 🧠 Rule

No major change can be applied to the system without being documented here.
