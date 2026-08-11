"""
GARCH(1,1) multi-step forecast helpers.
"""

from __future__ import annotations

import numpy as np

from .historical import annualize_vol


def forecast_garch11(
    last_return: float,
    last_variance: float,
    omega: float,
    alpha: float,
    beta: float,
    horizon: int = 10,
    *,
    annualize: bool = True,
) -> np.ndarray:
    """
    One-step: σ²_{t+1} = ω + α r²_t + β σ²_t
    Multi-step: σ²_{t+h} = ω + (α+β) σ²_{t+h-1}   (h ≥ 2)
    """
    if horizon < 1:
        raise ValueError("horizon must be >= 1")

    forecasts = np.empty(horizon)
    var_next = omega + alpha * (last_return**2) + beta * last_variance
    forecasts[0] = max(var_next, 1e-18)

    for h in range(1, horizon):
        forecasts[h] = omega + (alpha + beta) * forecasts[h - 1]

    vol = np.sqrt(forecasts)
    if annualize:
        vol = annualize_vol(vol)
    return vol
