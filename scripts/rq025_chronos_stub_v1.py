#!/usr/bin/env python3
"""[HYPO][NON_GATING] RQ-025 layer-3 Chronos stub — persistence/MA/residual features (numpy only).

Not Amazon Chronos inference; research placeholder until local Chronos-Forward reproduce.
"""
from __future__ import annotations

import numpy as np

SCHEMA = "rq025_chronos_stub_v1"
_IMPLEMENTATION = "chronos_persist_ma_residual_stub_v1"


def chronos_window_features(series: np.ndarray, *, window: int = 16) -> dict[str, float]:
    """Trailing-window zero-shot-ish features (persistence + MA residual + trend)."""
    s = np.asarray(series, dtype=float).reshape(-1)
    if s.size < 1:
        return {
            "persist_forecast": 0.0,
            "ma_forecast": 0.0,
            "residual": 0.0,
            "autocorr_lag1": 0.0,
            "trend_slope": 0.0,
        }
    tail = s[-window:] if s.size >= window else s
    persist = float(tail[-1])
    ma = float(np.mean(tail))
    residual = float(tail[-1] - ma)
    if tail.size >= 3 and float(np.std(tail)) > 1e-9:
        lag1 = float(np.corrcoef(tail[:-1], tail[1:])[0, 1])
        if not np.isfinite(lag1):
            lag1 = 0.0
    else:
        lag1 = 0.0
    if tail.size >= 2:
        x = np.arange(tail.size, dtype=float)
        slope = float(np.polyfit(x, tail, 1)[0])
    else:
        slope = 0.0
    return {
        "persist_forecast": persist,
        "ma_forecast": ma,
        "residual": residual,
        "autocorr_lag1": lag1,
        "trend_slope": slope,
    }


def expand_chronos_series_features(
    dates: list[str],
    values_by_date: dict[str, float],
    *,
    window: int = 16,
    prefix: str,
) -> dict[str, dict[str, float]]:
    """Causal-as-of history per date; keys prefixed for logistic WF."""
    out: dict[str, dict[str, float]] = {}
    sorted_dates = sorted(dates)
    hist: list[float] = []
    for dk in sorted_dates:
        if dk in values_by_date and np.isfinite(values_by_date[dk]):
            hist.append(float(values_by_date[dk]))
        feats = chronos_window_features(np.array(hist, dtype=float), window=window)
        out[dk] = {f"{prefix}_{k}": v for k, v in feats.items()}
    return out
