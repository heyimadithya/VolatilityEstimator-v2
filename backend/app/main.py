"""FastAPI application — Volatility Estimator V2."""

from __future__ import annotations

from datetime import datetime, timezone

import numpy as np
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .estimators import (
    ewma_volatility,
    fit_garch11,
    forecast_garch11,
    full_sample_volatility,
    rolling_volatility,
    estimate_realized_volatility,
)
from .schemas import AnalyzeRequest, AnalyzeResponse, HealthResponse
from .services.data import (
    fetch_daily_ohlc,
    fetch_intraday_1m,
    fetch_options_chain,
    prices_and_returns,
)
from .services.iv_surface import build_iv_surface

app = FastAPI(
    title="Volatility Estimator",
    description=(
        "From-scratch volatility stack: rolling, EWMA, GARCH(1,1) MLE, "
        "intraday realized measures, and Black–Scholes implied-vol surface."
    ),
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:4173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _clean(xs: np.ndarray) -> list[float | None]:
    out: list[float | None] = []
    for x in xs:
        if x is None or not np.isfinite(x):
            out.append(None)
        else:
            out.append(float(x))
    return out


@app.get("/api/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok", version="2.0.0")


@app.post("/api/analyze", response_model=AnalyzeResponse)
def analyze(req: AnalyzeRequest) -> AnalyzeResponse:
    ticker = req.ticker.upper().strip()
    notes: list[str] = []

    try:
        daily = fetch_daily_ohlc(ticker, period=req.period)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Market data error: {e}") from e

    closes, returns, dates = prices_and_returns(daily)
    spot = float(closes[-1])
    ret_dates = dates[1:]

    rolling = rolling_volatility(returns, window=req.rolling_window)
    ewma = ewma_volatility(returns, lam=req.ewma_lambda)

    try:
        garch = fit_garch11(returns)
        garch_vol = garch.conditional_volatility
        garch_fc = forecast_garch11(
            last_return=float(returns[-1]),
            last_variance=float(garch.conditional_variance[-1]),
            omega=garch.omega,
            alpha=garch.alpha,
            beta=garch.beta,
            horizon=req.forecast_horizon,
        )
        garch_block = {
            "params": {
                "omega": garch.omega,
                "alpha": garch.alpha,
                "beta": garch.beta,
                "persistence": garch.persistence,
                "unconditional_vol": float(
                    np.sqrt(garch.unconditional_var) * np.sqrt(252)
                )
                if np.isfinite(garch.unconditional_var)
                else None,
                "log_likelihood": garch.log_likelihood,
                "converged": garch.converged,
                "message": garch.message,
            },
            "series": _clean(garch_vol),
            "latest": float(garch_vol[-1]) if np.isfinite(garch_vol[-1]) else None,
            "forecast": {
                "horizon_days": list(range(1, req.forecast_horizon + 1)),
                "volatility": _clean(garch_fc),
            },
        }
    except Exception as e:
        notes.append(f"GARCH fit failed: {e}")
        garch_block = {"error": str(e)}

    models = {
        "sample": {
            "volatility": full_sample_volatility(returns),
            "n_returns": int(len(returns)),
        },
        "rolling": {
            "window": req.rolling_window,
            "series": _clean(rolling),
            "latest": float(rolling[-1]) if np.isfinite(rolling[-1]) else None,
        },
        "ewma": {
            "lambda": req.ewma_lambda,
            "series": _clean(ewma),
            "latest": float(ewma[-1]) if np.isfinite(ewma[-1]) else None,
        },
        "garch": garch_block,
    }

    realized_block = None
    if req.include_realized:
        try:
            intra = fetch_intraday_1m(ticker, period="7d")
            rv = estimate_realized_volatility(intra)
            realized_block = {
                "dates": rv.dates,
                "realized_vol": rv.realized_vol,
                "bipower_vol": rv.bipower_vol,
                "parkinson_vol": rv.parkinson_vol,
                "average_rv": rv.average_rv,
                "n_days": rv.n_days,
                "bars_per_day_median": rv.bars_per_day_median,
                "note": rv.note,
            }
        except Exception as e:
            notes.append(f"Realized vol unavailable: {e}")

    iv_block = None
    if req.include_iv:
        try:
            chain = fetch_options_chain(ticker, risk_free_rate=req.risk_free_rate)
            iv_block = build_iv_surface(
                chain["contracts"],
                spot=chain["spot"],
                risk_free_rate=req.risk_free_rate,
                prefer="otm",
            )
            if iv_block["n_points"] == 0:
                notes.append("Options chain fetched but no IVs converged (illiquid quotes).")
                iv_block = None
        except Exception as e:
            notes.append(f"IV surface unavailable: {e}")

    return AnalyzeResponse(
        ticker=ticker,
        spot=spot,
        asof=datetime.now(timezone.utc).isoformat(),
        dates=ret_dates,
        closes=[float(x) for x in closes[1:]],
        returns=[float(x) for x in returns],
        models=models,
        realized=realized_block,
        iv_surface=iv_block,
        notes=notes,
    )
