# Volatility Estimator

From-scratch volatility research app for equities: classical estimators, GARCH(1,1) MLE, intraday realized measures, and a Black–Scholes implied-volatility surface.

**Stack:** FastAPI + NumPy/SciPy · React (Vite) · Yahoo Finance data

**Live demo (GitHub Pages):** https://heyimadithya.github.io/VolatilityEstimatorV2/

> GitHub Pages serves the **static React UI** only (no Python process). The hosted site loads a cached SPY demo when the API is unreachable. For live tickers, run the FastAPI backend locally (below).

## Why this is V2

| Layer | What recruiters look for | Implementation |
| --- | --- | --- |
| Basic | Rolling historical σ | Sample stdev over a trailing window, annualized √252 |
| Strong | Volatility clustering | EWMA (RiskMetrics) + **GARCH(1,1) fit by MLE in SciPy** — not `arch` |
| Elite | Messy / rich data | 1-minute realized variance, bipower variation, Parkinson; options mid quotes inverted with **Newton–Raphson** |

True exchange tick / LOB feeds are proprietary. Intraday work uses liquid 1-minute OHLC (Yahoo ~7 day window) as a microstructure-aware proxy, with methods that transfer to tick tapes.

## Math (short)

**Rolling**

$$\sigma_t = \sqrt{\frac{1}{N-1}\sum_{i=t-N+1}^{t}(r_i-\bar r)^2}\cdot\sqrt{252}$$

**EWMA**

$$\sigma_t^2 = \lambda\sigma_{t-1}^2 + (1-\lambda)r_{t-1}^2$$

**GARCH(1,1)**

$$\sigma_t^2 = \omega + \alpha r_{t-1}^2 + \beta\sigma_{t-1}^2$$

Parameters \((\omega,\alpha,\beta)\) maximize Gaussian log-likelihood under \(\omega>0\), \(\alpha,\beta\ge 0\), \(\alpha+\beta<1\).

**Implied vol** — Newton update on Black–Scholes:

$$\sigma_{n+1} = \sigma_n - \frac{C(\sigma_n)-C_{\mathrm{mkt}}}{\nu(\sigma_n)}$$

## Project layout

```
backend/app/
  estimators/     # historical, ewma, garch, realized, black_scholes
  services/       # market data + IV surface builder
  main.py         # FastAPI
frontend/src/     # React UI
INTERVIEW_GUIDE.md
```

## Run locally

Requires Python 3.11+ and Node 20+.

```bash
# Backend
python -m venv .venv
# Windows:
.venv\Scripts\activate
pip install -r backend\requirements.txt
uvicorn app.main:app --reload --app-dir backend --port 8000

# Frontend (new terminal)
cd frontend
npm install
npm run dev
```

Or use `scripts\run-api.bat` and `scripts\run-web.bat`.

Open http://localhost:5173 — the Vite proxy forwards `/api` to the API.

## GitHub Pages

On every push to `main`, `.github/workflows/deploy-pages.yml` builds the frontend with base path `/VolatilityEstimatorV2/` and deploys to GitHub Pages.

## API

`POST /api/analyze`

```json
{
  "ticker": "SPY",
  "period": "5y",
  "rolling_window": 21,
  "ewma_lambda": 0.94,
  "include_realized": true,
  "include_iv": true,
  "risk_free_rate": 0.045
}
```

## Disclaimer

Educational research tool. Not investment advice. Options and intraday coverage vary by ticker and Yahoo availability.
