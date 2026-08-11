"""
Intraday / high-frequency realized volatility estimators.

True exchange tick tapes are proprietary; we use liquid 1-minute bars
(Yahoo Finance) as a microstructure-aware proxy and apply standard
realized-measure estimators used in the RV literature.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .historical import TRADING_DAYS


@dataclass(frozen=True)
class RealizedVolResult:
    dates: list[str]
    realized_vol: list[float]  # annualized
    bipower_vol: list[float]
    parkinson_vol: list[float]
    average_rv: float
    n_days: int
    bars_per_day_median: float
    note: str


def _session_groups(df: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Group intraday bars by calendar date (UTC-naive index assumed local session)."""
    if not isinstance(df.index, pd.DatetimeIndex):
        raise ValueError("intraday frame needs a DatetimeIndex")
    out: dict[str, pd.DataFrame] = {}
    for day, chunk in df.groupby(df.index.date):
        out[str(day)] = chunk
    return out


def realized_variance(close: np.ndarray) -> float:
    """RV = Σ r²_i over the session (close-to-close log returns within the day)."""
    close = np.asarray(close, dtype=float)
    close = close[np.isfinite(close) & (close > 0)]
    if len(close) < 3:
        return float("nan")
    r = np.diff(np.log(close))
    return float(np.sum(r**2))


def bipower_variation(close: np.ndarray) -> float:
    """
    Barndorff-Nielsen & Shephard bipower variation (jump-robust):

        BV = (π/2) Σ |r_i| |r_{i-1}|
    """
    close = np.asarray(close, dtype=float)
    close = close[np.isfinite(close) & (close > 0)]
    if len(close) < 4:
        return float("nan")
    r = np.diff(np.log(close))
    return float((np.pi / 2.0) * np.sum(np.abs(r[1:]) * np.abs(r[:-1])))


def parkinson_variance(high: np.ndarray, low: np.ndarray) -> float:
    """Parkinson (1980) high-low range estimator for one session."""
    high = np.asarray(high, dtype=float)
    low = np.asarray(low, dtype=float)
    mask = np.isfinite(high) & np.isfinite(low) & (high > 0) & (low > 0) & (high >= low)
    high, low = high[mask], low[mask]
    if len(high) < 2:
        return float("nan")
    hl = np.log(high / low)
    return float(np.mean(hl**2) / (4.0 * np.log(2.0)))


def estimate_realized_volatility(intraday: pd.DataFrame) -> RealizedVolResult:
    """
    Expect columns: Open, High, Low, Close (case-insensitive accepted via normalize).
    Index: timestamps.
    """
    cols = {c.lower(): c for c in intraday.columns}
    for need in ("high", "low", "close"):
        if need not in cols:
            raise ValueError(f"intraday data missing '{need}' column")

    high_c, low_c, close_c = cols["high"], cols["low"], cols["close"]
    groups = _session_groups(intraday)

    dates: list[str] = []
    rv_ann: list[float] = []
    bv_ann: list[float] = []
    pk_ann: list[float] = []
    bars: list[int] = []

    for day, chunk in sorted(groups.items()):
        close = chunk[close_c].to_numpy(dtype=float)
        high = chunk[high_c].to_numpy(dtype=float)
        low = chunk[low_c].to_numpy(dtype=float)

        rv = realized_variance(close)
        bv = bipower_variation(close)
        pk = parkinson_variance(high, low)

        # Annualize daily integrated variance → vol
        def ann(v: float) -> float:
            if not np.isfinite(v) or v < 0:
                return float("nan")
            return float(np.sqrt(v * TRADING_DAYS))

        dates.append(day)
        rv_ann.append(ann(rv))
        bv_ann.append(ann(bv))
        pk_ann.append(ann(pk))
        bars.append(len(chunk))

    valid = [x for x in rv_ann if np.isfinite(x)]
    return RealizedVolResult(
        dates=dates,
        realized_vol=rv_ann,
        bipower_vol=bv_ann,
        parkinson_vol=pk_ann,
        average_rv=float(np.mean(valid)) if valid else float("nan"),
        n_days=len(dates),
        bars_per_day_median=float(np.median(bars)) if bars else 0.0,
        note=(
            "Computed from 1-minute OHLC bars (Yahoo). "
            "RV = Σ r²; bipower variation is jump-robust; "
            "Parkinson uses high-low ranges. Full LOB tick tapes require paid feeds."
        ),
    )
