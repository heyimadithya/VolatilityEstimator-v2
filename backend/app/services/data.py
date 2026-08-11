"""Market data access via Yahoo Finance."""

from __future__ import annotations

from datetime import datetime, timezone
from functools import lru_cache

import numpy as np
import pandas as pd
import yfinance as yf


def _flatten_columns(df: pd.DataFrame) -> pd.DataFrame:
    if isinstance(df.columns, pd.MultiIndex):
        df = df.copy()
        df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]
    return df


def fetch_daily_ohlc(ticker: str, period: str = "5y") -> pd.DataFrame:
    t = yf.Ticker(ticker.upper().strip())
    df = t.history(period=period, auto_adjust=True)
    if df is None or df.empty:
        raise ValueError(f"No daily data for {ticker}")
    df = _flatten_columns(df)
    df = df.rename(columns=str.title)
    need = {"Open", "High", "Low", "Close"}
    if not need.issubset(set(df.columns)):
        raise ValueError(f"Unexpected columns for {ticker}: {list(df.columns)}")
    return df[["Open", "High", "Low", "Close", "Volume"]].dropna()


def fetch_intraday_1m(ticker: str, period: str = "7d") -> pd.DataFrame:
    """
    Yahoo only serves ~7 days of 1-minute bars for most equities.
    """
    t = yf.Ticker(ticker.upper().strip())
    df = t.history(period=period, interval="1m", auto_adjust=True)
    if df is None or df.empty:
        raise ValueError(f"No 1m intraday data for {ticker}")
    df = _flatten_columns(df)
    df = df.rename(columns=str.title)
    return df[["Open", "High", "Low", "Close", "Volume"]].dropna()


def fetch_spot(ticker: str) -> float:
    df = fetch_daily_ohlc(ticker, period="5d")
    return float(df["Close"].iloc[-1])


def _safe_int(value: object) -> int:
    try:
        if value is None:
            return 0
        x = float(value)
        if not np.isfinite(x):
            return 0
        return int(x)
    except (TypeError, ValueError):
        return 0


def _safe_float(value: object, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        x = float(value)
        return x if np.isfinite(x) else default
    except (TypeError, ValueError):
        return default


def fetch_options_chain(
    ticker: str,
    *,
    max_expiries: int = 8,
    risk_free_rate: float = 0.045,
) -> dict:
    """
    Pull listed option expiries and mid prices; return raw chain for IV inversion.
    """
    t = yf.Ticker(ticker.upper().strip())
    spot = fetch_spot(ticker)
    expiries = list(t.options or [])
    if not expiries:
        raise ValueError(f"No options chain for {ticker}")

    expiries = expiries[:max_expiries]
    now = datetime.now(timezone.utc)

    rows: list[dict] = []
    for exp in expiries:
        try:
            chain = t.option_chain(exp)
        except Exception:
            continue
        exp_dt = datetime.strptime(exp, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        t_years = max((exp_dt - now).total_seconds() / (365.25 * 24 * 3600), 1e-4)

        for opt_type, frame in (("call", chain.calls), ("put", chain.puts)):
            if frame is None or frame.empty:
                continue
            for _, row in frame.iterrows():
                bid = _safe_float(row.get("bid"))
                ask = _safe_float(row.get("ask"))
                last = _safe_float(row.get("lastPrice"))
                if bid > 0 and ask > 0:
                    mid = 0.5 * (bid + ask)
                elif last > 0:
                    mid = last
                else:
                    continue
                strike = _safe_float(row.get("strike"))
                if mid <= 0 or strike <= 0:
                    continue
                moneyness = strike / spot
                if moneyness < 0.7 or moneyness > 1.3:
                    continue
                rows.append(
                    {
                        "expiry": exp,
                        "t_years": t_years,
                        "type": opt_type,
                        "strike": strike,
                        "bid": bid,
                        "ask": ask,
                        "mid": mid,
                        "moneyness": moneyness,
                        "volume": _safe_int(row.get("volume")),
                        "openInterest": _safe_int(row.get("openInterest")),
                    }
                )

    return {
        "ticker": ticker.upper(),
        "spot": spot,
        "risk_free_rate": risk_free_rate,
        "asof": now.isoformat(),
        "contracts": rows,
        "expiries": expiries,
    }


def prices_and_returns(daily: pd.DataFrame) -> tuple[np.ndarray, np.ndarray, list[str]]:
    closes = daily["Close"].to_numpy(dtype=float)
    dates = [d.strftime("%Y-%m-%d") for d in daily.index]
    # returns align to dates[1:]
    rets = np.diff(np.log(closes))
    return closes, rets, dates
