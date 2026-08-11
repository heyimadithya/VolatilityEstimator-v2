"""Build implied volatility smile / surface from options chain."""

from __future__ import annotations

from collections import defaultdict

import numpy as np

from ..estimators.black_scholes import implied_volatility_newton


def build_iv_surface(
    contracts: list[dict],
    spot: float,
    risk_free_rate: float,
    *,
    prefer: str = "call",
    min_oi: int = 10,
) -> dict:
    """
    Invert mid prices with Newton–Raphson. Prefer calls for K >= S and puts for K < S
    (continuity / put-call parity liquidity heuristic).
    """
    by_expiry: dict[str, list[dict]] = defaultdict(list)

    for c in contracts:
        if c.get("openInterest", 0) < min_oi and c.get("volume", 0) < 5:
            continue
        k = float(c["strike"])
        # Prefer OTM options: calls when K>=S, puts when K<S
        if prefer == "otm":
            if k >= spot and c["type"] != "call":
                continue
            if k < spot and c["type"] != "put":
                continue
        elif c["type"] != prefer:
            # still allow both; we'll dedupe by strike later preferring OTM
            pass

        iv_res = implied_volatility_newton(
            market_price=float(c["mid"]),
            spot=spot,
            strike=k,
            t=float(c["t_years"]),
            r=risk_free_rate,
            option_type=c["type"],
        )
        if not iv_res.converged or not np.isfinite(iv_res.iv):
            continue

        by_expiry[c["expiry"]].append(
            {
                "strike": k,
                "moneyness": k / spot,
                "iv": float(iv_res.iv),
                "type": c["type"],
                "mid": float(c["mid"]),
                "t_years": float(c["t_years"]),
                "iterations": iv_res.iterations,
            }
        )

    # Deduplicate strikes per expiry: keep OTM quote
    surface_points: list[dict] = []
    smiles: list[dict] = []

    for expiry, pts in sorted(by_expiry.items()):
        best: dict[float, dict] = {}
        for p in pts:
            k = p["strike"]
            is_otm = (p["type"] == "call" and k >= spot) or (p["type"] == "put" and k < spot)
            if k not in best:
                best[k] = p
            else:
                prev = best[k]
                prev_otm = (prev["type"] == "call" and k >= spot) or (prev["type"] == "put" and k < spot)
                if is_otm and not prev_otm:
                    best[k] = p
        ordered = [best[k] for k in sorted(best)]
        if len(ordered) < 3:
            continue
        smile = {
            "expiry": expiry,
            "t_years": ordered[0]["t_years"],
            "strikes": [p["strike"] for p in ordered],
            "moneyness": [p["moneyness"] for p in ordered],
            "iv": [p["iv"] for p in ordered],
        }
        smiles.append(smile)
        for p in ordered:
            surface_points.append(
                {
                    "expiry": expiry,
                    "t_years": p["t_years"],
                    "strike": p["strike"],
                    "moneyness": p["moneyness"],
                    "iv": p["iv"],
                }
            )

    # Grid for 3D surface (moneyness × maturity)
    maturities = sorted({s["t_years"] for s in smiles})
    money_grid = np.linspace(0.8, 1.2, 21)

    z: list[list[float | None]] = []
    for t in maturities:
        smile = next(s for s in smiles if abs(s["t_years"] - t) < 1e-12)
        xs = np.array(smile["moneyness"])
        ys = np.array(smile["iv"])
        # interpolate in moneyness
        row: list[float | None] = []
        for m in money_grid:
            if m < xs.min() or m > xs.max():
                row.append(None)
            else:
                row.append(float(np.interp(m, xs, ys)))
        z.append(row)

    return {
        "spot": spot,
        "smiles": smiles,
        "points": surface_points,
        "grid": {
            "moneyness": money_grid.tolist(),
            "maturities": maturities,
            "iv": z,
        },
        "n_points": len(surface_points),
        "method": "Black–Scholes inverted via Newton–Raphson on mid quotes (OTM preferred)",
    }
