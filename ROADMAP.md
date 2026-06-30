# Investment Automation — Master Roadmap

## 🎯 Mission

Build a robust, tax-aware, long-term investment automation system for a Canadian investor (Quebec), focused on compounding capital with minimal complexity and strong risk control.

The system must be:
- reproducible
- backtestable
- transparent
- robust across market regimes
- optimized for after-tax returns (Canada)

---

# 🟢 Phase 1 — Core Infrastructure (FOUNDATION)

## Objective: stabilize and structure the system

### Data & Architecture
- [ ] Standardize project structure (src/, data/, backtests/, reports/)
- [ ] Centralize configuration (config.py or config module)
- [ ] Define data ingestion pipeline (prices, dividends, fundamentals)
- [ ] Ensure reproducible environment (requirements.txt / venv lock)

### Backtesting Engine
- [ ] DCA strategy baseline implementation
- [ ] Portfolio simulation engine
- [ ] Performance metrics (CAGR, volatility, max drawdown)
- [ ] Transaction cost modeling (basic)

### Logging & Reproducibility
- [ ] Structured logging of all backtests
- [ ] Save all simulation outputs in /reports
- [ ] Version control all strategy changes

---

# 🟡 Phase 2 — Investment Intelligence Layer (double check following the current main.py and mechanisms)

## Objective: move from simple simulation → decision system

### Stock Scoring System
- [ ] Quality scoring (profitability, stability, margins)
- [ ] Dividend sustainability analysis
- [ ] Volatility & risk scoring
- [ ] Composite investment score

### Portfolio Construction
- [ ] Multi-asset portfolio allocation
- [ ] Sector diversification rules
- [ ] Position sizing model
- [ ] Risk parity or heuristic allocation

### Strategy Engine
- [ ] Compare multiple strategies (DCA, dividend growth, factor-based)
- [ ] Multi-strategy backtesting framework
- [ ] Benchmark comparison (e.g., VFV / S&P 500 ETF)

---

# 🔵 Phase 3 — Canadian Tax-Aware Optimization (CRITICAL)

## Objective: model real net returns for Quebec investor

### Account Modeling
- [ ] TFSA (CELI) simulation (tax-free growth)
- [ ] RRSP simulation (tax-deferred growth)
- [ ] Taxable account modeling

### Tax Logic
- [ ] Canadian dividend tax treatment
- [ ] US withholding tax impact (TFSA / taxable accounts)
- [ ] After-tax return calculation engine

### Asset Location Optimization
- [ ] Optimal placement of assets across accounts
- [ ] Dividend vs growth allocation strategy
- [ ] CAD vs USD exposure considerations

---

# 🟣 Phase 4 — Automation & Decision System

## Objective: autonomous investment system

### Portfolio Automation
- [ ] Automated portfolio rebalancing rules
- [ ] Drift detection (allocation deviation)
- [ ] Periodic contribution allocation engine

### Reporting System
- [ ] Monthly performance reports
- [ ] Risk exposure summaries
- [ ] Strategy performance comparison reports

### Alert System
- [ ] Risk threshold alerts
- [ ] Strategy underperformance detection
- [ ] Dividend cuts / anomalies detection

---

# 🔴 Phase 5 — AI Integration (Claude + Codex)

## Objective: human + AI hybrid investment system

### Claude Role (Analysis Layer)
- Portfolio critique
- Strategy validation
- Bias detection (overfitting, survivorship bias)
- Risk review

### Codex Role (Execution Layer)
- Code generation and refactoring
- Backtest implementation
- Automation scripts

### AI Workflow
- Claude proposes improvements → Codex implements → system backtests → results stored
- Continuous improvement loop

---

# Planned Refactors — Do Not Implement Until Triggered

### REFACTOR-01 — utils decomposition
- Trigger: feature addition pace slows down
- Goal: split utils.py into focused submodules by responsibility
- Risk: high if done mid-development — coordinate with Claude first
- Status: deferred

### REFACTOR-02 — report_generator decoupling
- Trigger: before any API, dashboard, or external output work begins
- Goal: engines emit structured data objects, single output layer handles formatting
- Risk: architectural — requires full design before any Codex implementation
- Status: deferred

---

# Future Enhancements — Trigger-Based

### ENHANCEMENT-01 — RMT covariance denoising
- What: use Random Matrix Theory (Marchenko-Pastur) to clean the 
  correlation matrix before any statistical risk calculation
- Trigger: only if a statistical correlation engine is added to 
  portfolio_risk_engine, or if allocation_engine adopts mean-variance 
  optimization alongside the current scoring system
- Why not now: model does not use covariance matrices — technique 
  has no surface to operate on in current architecture
- Risk: low implementation risk when triggered, but adds complexity 
  to the risk layer
- Status: deferred — revisit after REFACTOR-02

---

# 🧠 Global System Principles

These rules MUST always be respected:

## Investment Principles
- Long-term horizon (10–50 years)
- Prefer robustness over optimization
- Avoid overfitting to historical data
- Focus on after-tax returns (Canada-specific)
- Favor simplicity over complexity

## Engineering Principles
- Reproducible results only
- Every strategy must be backtestable
- No hidden assumptions in code
- All changes must be logged and justified

---

# 📌 Success Definition

The system is successful when it can:

- simulate portfolios realistically over decades
- compare strategies objectively
- optimize after-tax returns for Canadian accounts
- remain stable under different market regimes
- be understood and improved by AI (Claude + Codex)
- Propose the most efficient and optimized allocation, gestion and investment of recurrent money contribution into a saving accounts
- Analyses, evaluates and filters out the best actual investment position options depending on chosen mode to maximize chances of being a better option than S&P 500 (Kinda like Blackrock and their Aladin computer)
