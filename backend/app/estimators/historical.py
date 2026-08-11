"""Historical / rolling volatility estimators."""

from __future__ import annotations

import numpy as np


TRADING_DAYS = 252


def log_returns(prices: np.ndarray) -> np.ndarray:
    prices = np.asarray(prices, dtype=float)
    if prices.ndim != 1 or len(prices) < 2:
        raise ValueError("Need a 1-D price series with at least 2 observations")
    return np.diff(np.log(prices))


def annualize_vol(daily_vol: np.ndarray | float, trading_days: int = TRADING_DAYS) -> np.ndarray | float:
    return np.asarray(daily_vol) * np.sqrt(trading_days)


def rolling_volatility(
    returns: np.ndarray,
    window: int = 21,
    *,
    annualize: bool = True,
    ddof: int = 1,
) -> np.ndarray:
    """
    Rolling sample standard deviation of returns.

    σ_t = sqrt( 1/(N-1) Σ (r_i - r̄)^2 ) over the trailing window,
    optionally annualized by √252.
    """
    returns = np.asarray(returns, dtype=float)
    n = len(returns)
    out = np.full(n, np.nan)
    if window < 2 or n < window:
        return out

    # O(n) rolling variance via cumulative sums
    c1 = np.cumsum(returns)
    c2 = np.cumsum(returns * returns)

    for t in range(window - 1, n):
        i0 = t - window + 1
        s1 = c1[t] - (c1[i0 - 1] if i0 > 0 else 0.0)
        s2 = c2[t] - (c2[i0 - 1] if i0 > 0 else 0.0)
        mean = s1 / window
        var = (s2 - window * mean * mean) / (window - ddof)
        out[t] = np.sqrt(max(var, 0.0))

    if annualize:
        out = annualize_vol(out)
    return out


def full_sample_volatility(returns: np.ndarray, *, annualize: bool = True) -> float:
    returns = np.asarray(returns, dtype=float)
    if len(returns) < 2:
        return float("nan")
    vol = float(np.std(returns, ddof=1))
    return float(annualize_vol(vol)) if annualize else vol
