# Volatility Estimator
From-scratch volatility research app for equities: classical estimators, GARCH(1,1) MLE, intraday realized measures, and a Black–Scholes implied-volatility surface.
**Created by Adithya Kannan**
**Stack:** FastAPI + NumPy/SciPy · React (Vite) · Yahoo Finance data
Full-stack toolkit to pull real market prices and estimate volatility with classical and advanced models — then explore the results in an interactive React UI.
V2 goes beyond rolling / EWMA: it fits **GARCH(1,1) from scratch** (NumPy/SciPy MLE, no `arch` wrappers), computes **intraday realized volatility**, and builds a **Black–Scholes implied-volatility surface** via Newton–Raphson.
**Stack:** FastAPI + NumPy/SciPy · React (Vite) · Yahoo Finance (`yfinance`)
**Live demo (GitHub Pages):** https://heyimadithya.github.io/VolatilityEstimatorV2/
> GitHub Pages serves the **static React UI** only (no Python process). The hosted site loads a cached SPY demo when the API is unreachable. For live tickers, run the FastAPI backend locally (below).
> GitHub Pages hosts the **static React UI** only. On the live site, Estimate loads a cached SPY demo when no API is available. For live tickers, run the FastAPI backend locally (below).
---
## Features
### Multiple volatility measures
- **Historical / rolling volatility** — fixed trailing window (e.g. 21-day or 30-day), annualized with √252.
- **EWMA volatility** — RiskMetrics-style recursion with configurable decay λ (e.g. 0.94, 0.97, 0.99).
- **GARCH(1,1)** — conditional variance fitted by maximum likelihood in SciPy (`ω`, `α`, `β`), plus multi-step forecasts.
- Side-by-side charts so you can see how each measure reacts to market regimes.
### Real market data support
Fetch daily (and short-horizon 1-minute) data from Yahoo Finance using `yfinance`. The UI / API accept any Yahoo ticker, including:
- **Indian stocks** — e.g. `MRF.NS`, `RELIANCE.NS`
- **US names / ETFs** — e.g. `AAPL`, `GOOGL`, `TSLA`, `MSFT`, `META`, `SPY`
- **Crypto** — e.g. `BTC-USD`, `ETH-USD`, `DOGE-USD`
- **Commodities and indices** — e.g. `GC=F`, `CL=F`, `^GSPC`
Availability of options chains and 1-minute bars depends on the ticker and Yahoo coverage.
### Intraday realized volatility (V2)
- Realized variance from 1-minute returns
- Bipower variation (more robust to jumps)
- Parkinson high–low range estimator
### Implied volatility surface (V2)
- Options mid quotes from Yahoo chains
- Black–Scholes inverted with **Newton–Raphson** (using vega)
- Smile charts and a moneyness × maturity IV heatmap
### Interactive research UI
- Enter ticker, history length, rolling window, and EWMA λ
- View model metrics, GARCH parameters, forecasts, realized series, and the IV surface
- FastAPI backend + React frontend (Vite proxy in local dev)
---
## Why this is V2
| Layer | What recruiters look for | Implementation |
| Layer | What it shows | Implementation |
| --- | --- | --- |
| Basic | Rolling historical σ | Sample stdev over a trailing window, annualized √252 |
| Strong | Volatility clustering | EWMA (RiskMetrics) + **GARCH(1,1) fit by MLE in SciPy** — not `arch` |
| Elite | Messy / rich data | 1-minute realized variance, bipower variation, Parkinson; options mid quotes inverted with **Newton–Raphson** |
| Strong | Volatility clustering | EWMA (RiskMetrics) + **GARCH(1,1) MLE in SciPy** — not `arch` |
| Elite | Richer / messier data | 1-minute realized measures; options IV surface via Newton–Raphson |
True exchange tick / LOB feeds are proprietary. Intraday work uses liquid 1-minute OHLC (Yahoo ~7 day window) as a microstructure-aware proxy, with methods that transfer to tick tapes.
True exchange tick / order-book feeds are proprietary. Intraday work uses liquid 1-minute OHLC (Yahoo ~7 day window) as a practical proxy.
---
## Math (short)
**Rolling**

[14 lines collapsed]

$$\sigma_{n+1} = \sigma_n - \frac{C(\sigma_n)-C_{\mathrm{mkt}}}{\nu(\sigma_n)}$$
---
## Customization
### In the UI
- Change the **ticker** (any Yahoo symbol).
- Set **history** (`1Y` / `2Y` / `5Y` / `10Y`).
- Set **rolling window** (e.g. 21, 30, 60).
- Tune **EWMA λ**:
  - `0.90` — very reactive
  - `0.94` — classic RiskMetrics default (balanced)
  - `0.97` / `0.99` — smoother
### Via the API
`POST /api/analyze`
```json
{
  "ticker": "AAPL",
  "period": "5y",
  "rolling_window": 21,
  "ewma_lambda": 0.94,
  "include_realized": true,
  "include_iv": true,
  "risk_free_rate": 0.045,
  "forecast_horizon": 10
}
```
Examples to try: `RELIANCE.NS`, `TSLA`, `BTC-USD`, `SPY`, `^GSPC`.
---
## Intended use
- Learning and explaining volatility concepts (rolling vs EWMA vs GARCH).
- Comparing risk behaviour across stocks, indices, crypto, and commodities.
- Building intuition for how vol clusters and mean-reverts across regimes.
- Exploring implied-vol smiles / surfaces from listed options.
- Generating research inputs for further portfolio or trading strategy work.
---
## Project layout
```
backend/app/
  estimators/     # historical, ewma, garch, realized, black_scholes
  services/       # market data + IV surface builder
  main.py         # FastAPI
frontend/src/     # React UI
INTERVIEW_GUIDE.md
backend/
  app/
    estimators/     # historical, ewma, garch, realized, black_scholes
    services/       # Yahoo data + IV surface builder
    main.py         # FastAPI entrypoint
  requirements.txt
  tests/
frontend/           # React + TypeScript UI (Vite)
scripts/            # Windows helpers: run-api.bat, run-web.bat
INTERVIEW_GUIDE.md  # Interview cheat sheet (math + stack + files)
```
## Run locally
---
Requires Python 3.11+ and Node 20+.
## Installation
Clone the repository:
```bash
# Backend
git clone https://github.com/heyimadithya/VolatilityEstimatorV2.git
cd VolatilityEstimatorV2
```
### Backend
Requires **Python 3.11+**.
```bash
python -m venv .venv
# Windows:
# Windows
.venv\Scripts\activate
pip install -r backend\requirements.txt
uvicorn app.main:app --reload --app-dir backend --port 8000
# Frontend (new terminal)
# macOS / Linux
# source .venv/bin/activate
pip install -r backend/requirements.txt
```
### Frontend
Requires **Node 20+**.
```bash
cd frontend
npm install
npm run dev
cd ..
```
