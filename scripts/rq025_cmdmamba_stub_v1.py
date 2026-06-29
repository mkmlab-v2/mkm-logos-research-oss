#!/usr/bin/env python3
"""[HYPO][NON_GATING] RQ-025 layer-4 CMDMamba stub — EMA/vol/selective-delta features (numpy only).

Not CMDMamba model inference; research placeholder for low-latency state-delta channel.
"""
from __future__ import annotations

import numpy as np

SCHEMA = "rq025_cmdmamba_stub_v1"
_IMPLEMENTATION = "cmdmamba_ema_vol_selective_delta_stub_v1"


def _ema(series: np.ndarray, alpha: float) -> float:
    s = np.asarray(series, dtype=float).reshape(-1)
    if s.size == 0:
        return 0.0
    v = float(s[0])
    for x in s[1:]:
        v = alpha * float(x) + (1.0 - alpha) * v
    return v


def cmdmamba_window_features(series: np.ndarray, *, window: int = 12) -> dict[str, float]:
    """Low-latency state-delta proxy from trailing scalar history."""
    s = np.asarray(series, dtype=float).reshape(-1)
    if s.size < 2:
        last = float(s[-1]) if s.size else 0.0
        return {
            "ema_fast": last,
            "ema_slow": last,
            "ema_cross": 0.0,
            "volatility": 0.0,
            "selective_delta": 0.0,
        }
    tail = s[-window:] if s.size >= window else s
    ema_f = _ema(tail, 0.4)
    ema_s = _ema(tail, 0.15)
    cross = ema_f - ema_s
    diffs = np.diff(tail)
    vol = float(np.std(diffs)) if diffs.size else 0.0
    weights = np.exp(-np.arange(diffs.size, dtype=float)[::-1] / max(diffs.size, 1))
    weights = weights / max(float(np.sum(weights)), 1e-9)
    selective = float(np.sum(weights * diffs)) if diffs.size else 0.0
    return {
        "ema_fast": ema_f,
        "ema_slow": ema_s,
        "ema_cross": cross,
        "volatility": vol,
        "selective_delta": selective,
    }


def expand_cmdmamba_series_features(
    dates: list[str],
    values_by_date: dict[str, float],
    *,
    window: int = 12,
    prefix: str,
) -> dict[str, dict[str, float]]:
    out: dict[str, dict[str, float]] = {}
    sorted_dates = sorted(dates)
    hist: list[float] = []
    for dk in sorted_dates:
        if dk in values_by_date and np.isfinite(values_by_date[dk]):
            hist.append(float(values_by_date[dk]))
        feats = cmdmamba_window_features(np.array(hist, dtype=float), window=window)
        out[dk] = {f"{prefix}_{k}": v for k, v in feats.items()}
    return out
