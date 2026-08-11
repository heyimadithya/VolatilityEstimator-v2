"""Black–Scholes pricing and Newton–Raphson implied volatility."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.stats import norm


def _d1_d2(s: float, k: float, t: float, r: float, sigma: float, q: float = 0.0) -> tuple[float, float]:
    if t <= 0 or sigma <= 0 or s <= 0 or k <= 0:
        raise ValueError("invalid BS inputs")
    vol_sqrt_t = sigma * np.sqrt(t)
    d1 = (np.log(s / k) + (r - q + 0.5 * sigma * sigma) * t) / vol_sqrt_t
    d2 = d1 - vol_sqrt_t
    return float(d1), float(d2)


def bs_price(
    spot: float,
    strike: float,
    t: float,
    r: float,
    sigma: float,
    option_type: str = "call",
    q: float = 0.0,
) -> float:
    """European Black–Scholes–Merton price."""
    d1, d2 = _d1_d2(spot, strike, t, r, sigma, q)
    if option_type.lower().startswith("c"):
        return float(spot * np.exp(-q * t) * norm.cdf(d1) - strike * np.exp(-r * t) * norm.cdf(d2))
    return float(strike * np.exp(-r * t) * norm.cdf(-d2) - spot * np.exp(-q * t) * norm.cdf(-d1))


def bs_vega(spot: float, strike: float, t: float, r: float, sigma: float, q: float = 0.0) -> float:
    d1, _ = _d1_d2(spot, strike, t, r, sigma, q)
    return float(spot * np.exp(-q * t) * norm.pdf(d1) * np.sqrt(t))


@dataclass(frozen=True)
class ImpliedVolResult:
    iv: float
    converged: bool
    iterations: int
    price_error: float


def implied_volatility_newton(
    market_price: float,
    spot: float,
    strike: float,
    t: float,
    r: float,
    option_type: str = "call",
    q: float = 0.0,
    *,
    initial_guess: float = 0.25,
    tol: float = 1e-8,
    max_iter: int = 100,
) -> ImpliedVolResult:
    """
    Invert Black–Scholes for σ via Newton–Raphson:

        σ_{n+1} = σ_n − (C(σ_n) − C_mkt) / Vega(σ_n)
    """
    if market_price <= 0 or t <= 0 or spot <= 0 or strike <= 0:
        return ImpliedVolResult(float("nan"), False, 0, float("nan"))

    # Intrinsic bounds
    disc_k = strike * np.exp(-r * t)
    disc_s = spot * np.exp(-q * t)
    if option_type.lower().startswith("c"):
        lower = max(0.0, disc_s - disc_k)
    else:
        lower = max(0.0, disc_k - disc_s)
    if market_price < lower - 1e-8:
        return ImpliedVolResult(float("nan"), False, 0, float("nan"))

    sigma = max(initial_guess, 1e-4)
    err = float("nan")

    for i in range(1, max_iter + 1):
        try:
            price = bs_price(spot, strike, t, r, sigma, option_type, q)
            vega = bs_vega(spot, strike, t, r, sigma, q)
        except ValueError:
            return ImpliedVolResult(float("nan"), False, i, float("nan"))

        err = price - market_price
        if abs(err) < tol:
            return ImpliedVolResult(float(sigma), True, i, float(err))
        if vega < 1e-12:
            # fallback: small bump / bisection-ish restart
            sigma = min(max(sigma * 1.5, 1e-4), 5.0)
            continue
        sigma = sigma - err / vega
        if sigma <= 1e-6 or sigma > 5.0:
            sigma = min(max(sigma, 1e-4), 5.0)

    return ImpliedVolResult(float(sigma), False, max_iter, float(err))
