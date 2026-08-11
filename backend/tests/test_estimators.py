"""Smoke tests for from-scratch estimators (no market data)."""

from __future__ import annotations

import numpy as np

from app.estimators.black_scholes import bs_price, implied_volatility_newton
from app.estimators.ewma import ewma_volatility
from app.estimators.garch import fit_garch11
from app.estimators.garch_forecast import forecast_garch11
from app.estimators.historical import rolling_volatility
from app.estimators.realized import bipower_variation, realized_variance


def test_rolling_and_ewma() -> None:
    rng = np.random.default_rng(0)
    r = rng.normal(0, 0.01, 400)
    roll = rolling_volatility(r, window=21)
    ewma = ewma_volatility(r, lam=0.94)
    assert np.isfinite(roll[-1])
    assert np.isfinite(ewma[-1])
    assert ewma[-1] > 0


def test_garch_mle() -> None:
    rng = np.random.default_rng(1)
    n = 800
    r = np.empty(n)
    var = 0.0001
    for t in range(n):
        shock = rng.normal()
        r[t] = np.sqrt(var) * shock
        var = 1e-6 + 0.05 * r[t] ** 2 + 0.9 * var
    fit = fit_garch11(r)
    assert fit.converged or fit.persistence < 1.0
    assert 0 <= fit.alpha < 1
    assert 0 <= fit.beta < 1
    assert fit.alpha + fit.beta < 1.0
    fc = forecast_garch11(r[-1], fit.conditional_variance[-1], fit.omega, fit.alpha, fit.beta, 5)
    assert len(fc) == 5
    assert np.all(np.isfinite(fc))


def test_newton_iv() -> None:
    spot, strike, t, r, sigma = 100.0, 100.0, 0.5, 0.03, 0.22
    price = bs_price(spot, strike, t, r, sigma, "call")
    iv = implied_volatility_newton(price, spot, strike, t, r, "call")
    assert iv.converged
    assert abs(iv.iv - sigma) < 1e-5


def test_realized() -> None:
    close = np.array([100.0, 100.2, 99.8, 100.5, 100.1, 100.3])
    rv = realized_variance(close)
    bv = bipower_variation(close)
    assert rv > 0 and bv > 0


if __name__ == "__main__":
    test_rolling_and_ewma()
    test_garch_mle()
    test_newton_iv()
    test_realized()
    print("ok")
