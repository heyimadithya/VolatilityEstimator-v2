# Volatility Estimator V2 — Personal Interview Guide

> Write this in your own words in interviews. This doc is your cheat sheet: what the project is, the math, the stack, and what every file does — explained simply.

---

## 1. One-sentence pitch (say this first)

**“I built a full-stack tool that estimates how wild a stock’s price moves — using rolling volatility, EWMA, GARCH fitted from scratch, intraday realized volatility, and an implied-vol surface from options — with a Python API and a React UI.”**

---

## 2. What is this project? (12-year-old version)

Imagine a stock price as a ball bouncing.

- Some days it barely moves → **calm**
- Some days it jumps a lot → **wild**

**Volatility** is a number that answers: *“How bouncy is this ball right now?”*

Banks, traders, and risk teams need that number to:

- price options (bets on future prices)
- size trades (how big a position is safe)
- measure risk (how bad can losses get)

My project is an app where you type a ticker like `SPY`, and it:

1. Downloads price history
2. Runs several math models that estimate volatility
3. Shows charts and numbers in a clean website

I didn’t just call a “magic library” that does GARCH for me. I wrote the formulas and the fitting code myself with NumPy and SciPy.

---

## 3. Why does it matter for a Quant Intern role?

Interviewers care less about “I made a website” and more about:

| Level | What it proves | What I built |
| --- | --- | --- |
| Basic | I understand returns & stdev | Rolling historical volatility |
| Strong | I understand clustering & forecasting | EWMA + GARCH(1,1) MLE from scratch |
| Elite | I can handle harder market data | Intraday realized vol + options IV surface |

**Honest caveat to say in interviews:**  
True exchange *tick* / order-book data is expensive. I used Yahoo Finance **1-minute bars** as a practical stand-in, and applied the same realized-vol ideas you’d use on tick data.

---

## 4. Exact tech stack

### Backend (brain)
| Piece | What it is | Why I used it |
| --- | --- | --- |
| **Python 3.13** | Language | Standard for quant / data work |
| **FastAPI** | Web API framework | Fast, typed endpoints, easy JSON |
| **Uvicorn** | ASGI server | Runs the FastAPI app |
| **NumPy** | Array math | Returns, variances, loops over series |
| **SciPy** | Scientific computing | `minimize` for GARCH MLE; `norm` for Black–Scholes |
| **Pandas** | Tables / time series | OHLC frames, grouping by day |
| **yfinance** | Market data client | Daily prices, 1-minute bars, options chains |
| **Pydantic** | Request/response schemas | Validates ticker, windows, rates |

**Not used on purpose:** packages like `arch` that fit GARCH for you. That was intentional — so I can explain every step.

### Frontend (face)
| Piece | What it is | Why I used it |
| --- | --- | --- |
| **React 19** | UI library | Interactive charts & forms |
| **TypeScript** | Typed JavaScript | Safer props/API types |
| **Vite** | Dev server + bundler | Fast refresh, proxies `/api` → backend |
| **Recharts** | 2D charts | Rolling / EWMA / GARCH / smile plots |
| **Plotly** (`plotly.js-dist-min` + `react-plotly.js`) | Heatmap | IV surface grid |
| **CSS** (custom) | Styling | No Tailwind/Bootstrap — intentional look |

### Tooling / other
| Piece | Role |
| --- | --- |
| **Yahoo Finance** | Free market data source |
| **npm** | Frontend package manager |
| **venv** | Isolated Python environment |
| **Windows `.bat` scripts** | One-click start for API / web |

### Architecture (how pieces talk)

```
Browser (React)  --POST /api/analyze-->  FastAPI
                                           |
                                           +--> yfinance (prices, options)
                                           +--> estimators (math)
                                           +--> JSON back to React charts
```

Vite in dev proxies `/api` to `http://127.0.0.1:8000` so the frontend doesn’t fight CORS during local work.

---

## 5. Core ideas before the formulas

### Price → return
Prices go 100 → 102. Talking in **percent moves** is cleaner than raw dollars.

I use **log returns**:

\[
r_t = \ln(P_t) - \ln(P_{t-1})
\]

Kid version: “How much did it stretch or shrink from yesterday, on a log scale that adds nicely over time.”

### Volatility ≈ “typical size of returns”
If returns are usually tiny, vol is low. If returns are huge, vol is high.

### Annualizing (√252)
Markets have about **252 trading days** a year. Daily vol × √252 ≈ yearly vol, so we can compare numbers the way desks talk (“15% vol”).

### Volatility clustering
Wild days often follow wild days; calm follows calm. That’s why plain “average of last 30 days” is only a start — EWMA and GARCH take clustering seriously.

---

## 6. Mathematical models (formulas + plain English)

### A) Rolling historical volatility (Basic)

**Idea:** Look at the last \(N\) days of returns. Measure how spread out they are (standard deviation). Slide that window forward every day.

\[
\sigma_t^{\text{daily}} = \sqrt{\frac{1}{N-1}\sum_{i=t-N+1}^{t}(r_i - \bar{r})^2}
\]

\[
\sigma_t^{\text{ann}} = \sigma_t^{\text{daily}} \cdot \sqrt{252}
\]

**Kid version:** “Take the last 21 homework scores, see how spread out they are, then pretend a full school year of days to get a yearly number.”

**Limit:** Treats day 1 and day 21 in the window as equally important. Markets care more about *yesterday*.

**Where in code:** `backend/app/estimators/historical.py`

---

### B) EWMA — Exponentially Weighted Moving Average (Strong)

**Idea:** Yesterday’s shock matters more than a shock from a month ago.

RiskMetrics-style recursion:

\[
\sigma_t^2 = \lambda \sigma_{t-1}^2 + (1-\lambda) r_{t-1}^2
\]

- \(\lambda\) close to 1 (I default **0.94**) → memory lasts longer  
- \((1-\lambda)\) → how hard the newest squared return hits

**Kid version:** “Your ‘wildness meter’ mostly remembers the old reading, but also updates a little with today’s bounce.”

**Where in code:** `backend/app/estimators/ewma.py`

---

### C) GARCH(1,1) with Maximum Likelihood (Strong — star of the show)

**Idea:** Volatility has a personality with three knobs:

\[
\sigma_t^2 = \omega + \alpha r_{t-1}^2 + \beta \sigma_{t-1}^2
\]

| Symbol | Name | Kid meaning |
| --- | --- | --- |
| \(\omega\) | omega | Baseline “always a little movement” |
| \(\alpha\) | ARCH weight | How much *yesterday’s surprise return* boosts today’s vol |
| \(\beta\) | GARCH weight | How much *yesterday’s vol* sticks around |
| \(\alpha+\beta\) | persistence | If near 1, shocks die out slowly |

**Returns model:** \(r_t = \sigma_t z_t\) with \(z_t \sim \mathcal{N}(0,1)\) (Gaussian shocks).

**Fitting (MLE):** I don’t guess \(\omega,\alpha,\beta\). I pick the values that make the observed returns *most likely* under that Gaussian story — by **minimizing negative log-likelihood** with SciPy’s `SLSQP`, with constraints:

- \(\omega > 0\)
- \(\alpha \ge 0\), \(\beta \ge 0\)
- \(\alpha + \beta < 1\) (stationary / mean-reverting variance)

Gaussian log-likelihood piece (conceptually):

\[
\ell = -\tfrac{1}{2}\sum_t \left( \ln(2\pi) + \ln(\sigma_t^2) + \frac{r_t^2}{\sigma_t^2} \right)
\]

**Forecast:**  
One step: plug in last return & variance.  
Further steps: use \(\sigma_{t+h}^2 = \omega + (\alpha+\beta)\sigma_{t+h-1}^2\).

**Kid version:** “GARCH is a weather app for market storminess. I teach it on history by asking: which settings best explain the storms we already saw?”

**Where in code:**  
- Fit: `backend/app/estimators/garch.py`  
- Forecast: `backend/app/estimators/garch_forecast.py`

---

### D) Intraday realized volatility (Elite-ish)

Daily close-to-close misses what happens *during* the day. With many tiny returns inside a day:

**Realized variance (RV):**

\[
RV = \sum_i r_i^2
\]

Then annualize: \(\sqrt{RV \times 252}\).

**Bipower variation (jump-robust):**

\[
BV = \frac{\pi}{2}\sum_i |r_i||r_{i-1}|
\]

Kid version: “If one crazy jump happened, RV gets huge; bipower is less fooled by single jumps.”

**Parkinson (high-low):**

\[
\hat{\sigma}^2_{\text{Park}} = \frac{1}{4\ln 2}\,\overline{\left(\ln\frac{H}{L}\right)^2}
\]

Uses the day’s high and low range, not only closes.

**Where in code:** `backend/app/estimators/realized.py`  
**Data:** 1-minute OHLC from Yahoo (~7 days available).

---

### E) Black–Scholes + Newton–Raphson implied volatility (Elite)

Options have market prices. The Black–Scholes formula prices an option if you *assume* a volatility \(\sigma\).

**Problem:** Market gives the price; we want the \(\sigma\) that makes BS match that price → **implied volatility (IV)**.

**Newton–Raphson** (root finding):

\[
\sigma_{n+1} = \sigma_n - \frac{C(\sigma_n) - C_{\text{market}}}{\nu(\sigma_n)}
\]

- \(C(\sigma)\) = BS model price at guess \(\sigma\)
- \(\nu\) = **vega** = \(\partial C/\partial\sigma\) (how price moves if vol moves)

Repeat until model price ≈ market mid quote.

**Smile / surface:** Do this for many strikes and expiries → plot IV vs moneyness \(K/S\) and maturity \(T\). Markets often show a **smile/smirk** (not one flat vol).

**Where in code:**  
- BS + Newton: `backend/app/estimators/black_scholes.py`  
- Surface builder: `backend/app/services/iv_surface.py`

---

## 7. What happens when I click “Estimate”?

1. React sends `POST /api/analyze` with ticker, history length, rolling window, EWMA λ, etc.
2. FastAPI pulls daily OHLC from Yahoo.
3. Builds log returns.
4. Runs rolling, EWMA, GARCH (+ forecast).
5. Tries 1-minute bars → realized measures.
6. Tries options chain → Newton IV → smile + heatmap grid.
7. Returns one JSON blob; React draws metrics and charts.

---

## 8. Every important file / folder (and what it’s for)

Skip explaining `node_modules/`, `.venv/`, and build caches in interviews — those are dependencies, not *your* logic.

### Root

| Path | Purpose |
| --- | --- |
| `README.md` | Public project readme: how to run, short math, recruiter table |
| `INTERVIEW_GUIDE.md` | **This file** — your personal deep explainer |
| `.gitignore` | Tells Git to ignore `.venv`, `node_modules`, `dist`, caches |
| `.venv/` | Local Python environment (installed packages live here) |
| `scripts/run-api.bat` | Windows helper: starts FastAPI on port 8000 |
| `scripts/run-web.bat` | Windows helper: starts Vite on port 5173 |

### Backend

| Path | Purpose |
| --- | --- |
| `backend/requirements.txt` | Python package list (fastapi, numpy, scipy, …) |
| `backend/app/__init__.py` | Marks `app` as a Python package |
| `backend/app/main.py` | **API entrypoint**: CORS, `/api/health`, `/api/analyze` orchestration |
| `backend/app/schemas.py` | Pydantic models for request/response shapes |
| `backend/app/estimators/__init__.py` | Re-exports estimator functions |
| `backend/app/estimators/historical.py` | Log returns, rolling vol, full-sample vol, √252 annualize |
| `backend/app/estimators/ewma.py` | EWMA variance/volatility recursion |
| `backend/app/estimators/garch.py` | GARCH(1,1) variance path + SciPy MLE fit |
| `backend/app/estimators/garch_forecast.py` | Multi-step GARCH vol forecasts |
| `backend/app/estimators/realized.py` | RV, bipower, Parkinson on intraday bars |
| `backend/app/estimators/black_scholes.py` | BS price, vega, Newton–Raphson IV |
| `backend/app/services/__init__.py` | Marks services package |
| `backend/app/services/data.py` | Yahoo download: daily, 1m, options chain helpers |
| `backend/app/services/iv_surface.py` | Turn inverted IVs into smiles + moneyness×maturity grid |
| `backend/tests/test_estimators.py` | Smoke tests (synthetic GARCH, Newton IV round-trip, etc.) |

### Frontend

| Path | Purpose |
| --- | --- |
| `frontend/package.json` | npm scripts + React/Recharts/Plotly deps |
| `frontend/package-lock.json` | Locked dependency versions |
| `frontend/vite.config.ts` | Vite + React plugin + `/api` proxy to backend |
| `frontend/tsconfig.json` | TypeScript compiler settings |
| `frontend/index.html` | HTML shell, fonts, mounts `#root` |
| `frontend/src/main.tsx` | React bootstrap (`createRoot`) |
| `frontend/src/App.tsx` | Main page: form, sections, wires charts |
| `frontend/src/vite-env.d.ts` | TypeScript ambient types (Vite + Plotly module) |
| `frontend/src/lib/api.ts` | `fetch('/api/analyze')`, TypeScript types, `%` formatters |
| `frontend/src/styles/global.css` | Theme, layout, typography, responsive rules |
| `frontend/src/components/VolComparisonChart.tsx` | Rolling vs EWMA vs GARCH time series (Recharts) |
| `frontend/src/components/RealizedVolChart.tsx` | Intraday RV / bipower / Parkinson chart |
| `frontend/src/components/SmileChart.tsx` | One expiry’s IV vs moneyness |
| `frontend/src/components/IvSurfacePlot.tsx` | IV heatmap (Plotly, lazy-loaded) |
| `frontend/dist/` | Production build output (`npm run build`) — generated |

---

## 9. Likely interview Q&A (practice these)

### “What is volatility?”
How much prices tend to move. High vol = bigger swings. We usually quote it annualized.

### “Why log returns?”
They add over time, handle compounding cleanly, and are the usual input to vol models.

### “Why not only rolling stdev?”
It weights old and new the same and doesn’t model persistence. EWMA/GARCH react faster and match clustering.

### “What is GARCH persistence?”
\(\alpha+\beta\). Near 1 means a vol shock fades slowly. Mine on SPY often lands high (e.g. ~0.95–0.96) — typical for equities.

### “How did you fit GARCH?”
Maximum likelihood under Gaussian innovations; SciPy `minimize` with bounds and \(\alpha+\beta<1\).

### “What is implied vol?”
The σ you must plug into Black–Scholes to match the option’s market price. I solve for it with Newton–Raphson using vega.

### “What is the vol smile?”
IV is not constant across strikes. Plotting IV vs \(K/S\) often curves — a smile/smirk. Across expiries it becomes a surface.

### “What was hard?”
Good answers:
- Keeping GARCH constraints so the optimizer doesn’t go unstable
- Dirty options quotes (NaNs in volume/OI) — I sanitize before int casts
- Yahoo 1-minute history is short (~7 days)
- Plotly is heavy — I lazy-load the surface chart

### “What would you add next?”
- Student-t innovations for fat tails  
- HAR model on realized vol  
- Proper paid tick data / microstructure noise filters  
- Put–call parity checks / American early-exercise awareness  
- Backtest: does GARCH forecast beat EWMA on RMSE?

---

## 10. How to run (so you can demo live)

```bat
scripts\run-api.bat
scripts\run-web.bat
```

- API: http://127.0.0.1:8000  
- UI: http://127.0.0.1:5173  
- Health check: `GET /api/health`

Manual:

```bat
:: terminal 1
set PYTHONPATH=backend
.venv\Scripts\uvicorn.exe app.main:app --reload --host 127.0.0.1 --port 8000

:: terminal 2
cd frontend
npx vite --host 127.0.0.1 --port 5173
```

---

## 11. Resume / LinkedIn blurb (copy-paste and tweak)

**Volatility Estimator (V2)** — Full-stack research app estimating equity volatility via rolling statistics, RiskMetrics EWMA, and GARCH(1,1) maximum-likelihood estimation implemented in NumPy/SciPy (no GARCH wrappers). Added intraday realized/bipower/Parkinson measures from 1-minute bars and Black–Scholes implied-volatility smiles/surfaces inverted with Newton–Raphson on options mid quotes. FastAPI backend, React/TypeScript frontend, Yahoo Finance data.

---

## 12. Words you should be comfortable saying out loud

- Log return, annualize, √252  
- Volatility clustering  
- EWMA / RiskMetrics / λ  
- GARCH(1,1), ω, α, β, persistence  
- Maximum likelihood estimation (MLE)  
- Conditional vs unconditional volatility  
- Realized variance, bipower variation  
- Black–Scholes, vega, implied volatility  
- Newton–Raphson  
- Moneyness \(K/S\), smile, surface  
- FastAPI, React, NumPy, SciPy  

If you can explain those in kid words *and* write the formulas, you’re interview-ready on this project.
