"""Exponentially Weighted Moving Average (EWMA) volatility — RiskMetrics style."""

from __future__ import annotations

import numpy as np

from .historical import TRADING_DAYS, annualize_vol


def ewma_variance(
    returns: np.ndarray,
    lam: float = 0.94,
    *,
    init_window: int = 21,
) -> np.ndarray:
    """
    Recursion (RiskMetrics):

        σ²_t = λ σ²_{t-1} + (1 − λ) r²_{t-1}

    Initialized with sample variance over the first `init_window` returns.
    """
    returns = np.asarray(returns, dtype=float)
    n = len(returns)
    var = np.full(n, np.nan)
    if n < 2:
        return var
    if not (0.0 < lam < 1.0):
        raise ValueError("lam must be in (0, 1)")

    w = min(init_window, n)
    seed = float(np.var(returns[:w], ddof=1)) if w >= 2 else float(returns[0] ** 2)
    var[0] = seed

    for t in range(1, n):
        var[t] = lam * var[t - 1] + (1.0 - lam) * (returns[t - 1] ** 2)

    return var


def ewma_volatility(
    returns: np.ndarray,
    lam: float = 0.94,
    *,
    annualize: bool = True,
    init_window: int = 21,
) -> np.ndarray:
    var = ewma_variance(returns, lam=lam, init_window=init_window)
    vol = np.sqrt(var)
    if annualize:
        vol = annualize_vol(vol)
    return vol
