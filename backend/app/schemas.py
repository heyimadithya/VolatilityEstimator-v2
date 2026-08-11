"""Pydantic response models."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class AnalyzeRequest(BaseModel):
    ticker: str = Field(..., min_length=1, max_length=16, examples=["SPY"])
    period: str = "5y"
    rolling_window: int = Field(21, ge=5, le=252)
    ewma_lambda: float = Field(0.94, gt=0.0, lt=1.0)
    include_realized: bool = True
    include_iv: bool = True
    risk_free_rate: float = Field(0.045, ge=0.0, le=0.2)
    forecast_horizon: int = Field(10, ge=1, le=60)


class HealthResponse(BaseModel):
    status: str
    version: str


class AnalyzeResponse(BaseModel):
    ticker: str
    spot: float
    asof: str
    dates: list[str]
    closes: list[float]
    returns: list[float]
    models: dict[str, Any]
    realized: dict[str, Any] | None = None
    iv_surface: dict[str, Any] | None = None
    notes: list[str]
