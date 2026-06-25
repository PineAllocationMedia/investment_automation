# System Architecture — Investment Automation

## 🧠 Overview

This system is a Python-based investment automation engine designed to:

- simulate investment strategies
- run historical backtests
- evaluate portfolio performance
- support long-term capital growth modeling

---

## 📁 Project Structure

- /src → core logic (strategies, portfolio engine)
- /data → market data inputs
- /backtests → simulation runs
- /reports → output results and analytics
- /config → system parameters
- /tests → validation and unit tests

---

## ⚙️ Core Components

### 1. Data Layer
Responsible for:
- loading market data
- cleaning datasets
- normalizing inputs

### 2. Strategy Engine
Responsible for:
- defining investment strategies (DCA, dividend, factor-based)
- generating buy/sell/hold signals

### 3. Portfolio Engine
Responsible for:
- tracking holdings
- simulating contributions
- rebalancing logic

### 4. Backtesting Engine
Responsible for:
- running historical simulations
- calculating performance metrics
- storing results

---

## 📊 Key Metrics

The system evaluates strategies using:

- CAGR (compound annual growth rate)
- volatility
- maximum drawdown
- Sharpe-like risk-adjusted return
- after-tax return (Canada-aware logic)

---

## 🤖 AI Integration

### Claude (Analysis Role)
- reviews strategies
- detects logical flaws
- evaluates risk assumptions
- suggests improvements

### Codex (Execution Role)
- implements strategies
- writes backtest code
- refactors system
- automates workflows

---

## 🧠 Design Principles

- Simplicity over complexity
- Reproducibility over optimization
- Realistic assumptions over theoretical performance
- Tax-aware modeling for Canadian investor

*This is a very brief summary of the whole system. AI agents seeing this document should analyse and look further into all documents and establish the entire functionning of the system according to all codes.
