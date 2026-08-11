"""
GARCH(1,1) estimated by maximum likelihood (NumPy + SciPy only).

    r_t = σ_t z_t,  z_t ~ N(0,1)
    σ²_t = ω + α r²_{t-1} + β σ²_{t-1}

Constraints: ω > 0, α ≥ 0, β ≥ 0, α + β < 1 (covariance stationarity).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.optimize import minimize

from .historical import annualize_vol


@dataclass(frozen=True)
class GarchResult:
    omega: float
    alpha: float
    beta: float
    log_likelihood: float
    persistence: float
    unconditional_var: float
    conditional_variance: np.ndarray
    conditional_volatility: np.ndarray
    converged: bool
    message: str


def _garch_variance(returns: np.ndarray, omega: float, alpha: float, beta: float) -> np.ndarray:
    n = len(returns)
    var = np.empty(n)
    if alpha + beta < 1.0 - 1e-12:
        var0 = omega / (1.0 - alpha - beta)
    else:
        var0 = float(np.var(returns))
    var0 = max(var0, 1e-12)
    var[0] = var0
    for t in range(1, n):
        var[t] = omega + alpha * (returns[t - 1] ** 2) + beta * var[t - 1]
        if var[t] <= 0:
            var[t] = 1e-12
    return var


def _neg_loglik(params: np.ndarray, returns: np.ndarray) -> float:
    omega, alpha, beta = params
    if omega <= 0 or alpha < 0 or beta < 0 or alpha + beta >= 1.0:
        return 1e12
    var = _garch_variance(returns, omega, alpha, beta)
    ll = -0.5 * np.sum(np.log(2 * np.pi) + np.log(var) + (returns**2) / var)
    if not np.isfinite(ll):
        return 1e12
    return float(-ll)


def fit_garch11(
    returns: np.ndarray,
    *,
    annualize: bool = True,
) -> GarchResult:
    returns = np.asarray(returns, dtype=float)
    if len(returns) < 50:
        raise ValueError("GARCH fit needs at least ~50 returns for a stable MLE")

    sample_var = float(np.var(returns, ddof=1))
    x0 = np.array(
        [
            max(sample_var * 0.05, 1e-8),
            0.05,
            0.90,
        ],
        dtype=float,
    )

    bounds = [(1e-12, None), (0.0, 1.0 - 1e-6), (0.0, 1.0 - 1e-6)]

    def cons_stationarity(x: np.ndarray) -> float:
        return 0.999 - (x[1] + x[2])

    result = minimize(
        _neg_loglik,
        x0,
        args=(returns,),
        method="SLSQP",
        bounds=bounds,
        constraints={"type": "ineq", "fun": cons_stationarity},
        options={"maxiter": 500, "ftol": 1e-12},
    )

    omega, alpha, beta = (float(x) for x in result.x)
    var = _garch_variance(returns, omega, alpha, beta)
    vol = np.sqrt(var)
    if annualize:
        vol = annualize_vol(vol)

    persistence = alpha + beta
    unc = omega / (1.0 - persistence) if persistence < 1.0 else float("nan")

    return GarchResult(
        omega=omega,
        alpha=alpha,
        beta=beta,
        log_likelihood=float(-result.fun) if np.isfinite(result.fun) else float("nan"),
        persistence=persistence,
        unconditional_var=unc,
        conditional_variance=var,
        conditional_volatility=vol,
        converged=bool(result.success),
        message=str(result.message),
    )
