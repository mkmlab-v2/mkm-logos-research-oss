#!/usr/bin/env python3
"""[HYPO][NON_GATING] RQ-025 layer-2 TimeAPN stub — Haar DWT level-1 features (numpy only)."""
from __future__ import annotations

import numpy as np

SCHEMA = "rq025_timeapn_dwt_stub_v1"
_IMPLEMENTATION = "haar_dwt_level1_stub_v1"


def haar_dwt_level1(x: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """One-level Haar DWT; returns (approximation, detail) half-length arrays."""
    v = np.asarray(x, dtype=float).reshape(-1)
    n = v.size
    if n < 2:
        return v.copy(), np.zeros(0, dtype=float)
    if n % 2 == 1:
        v = np.concatenate([v, [v[-1]]])
        n = v.size
    a = (v[0::2] + v[1::2]) / np.sqrt(2.0)
    d = (v[0::2] - v[1::2]) / np.sqrt(2.0)
    return a, d


def timeapn_window_features(series: np.ndarray, *, window: int = 8) -> dict[str, float]:
    """Trailing-window DWT energy features for a scalar series ending at t."""
    s = np.asarray(series, dtype=float).reshape(-1)
    if s.size < 3:
        return {"dwt_detail_energy": 0.0, "dwt_approx_last": float(s[-1]) if s.size else 0.0}
    tail = s[-window:] if s.size >= window else s
    _, detail = haar_dwt_level1(tail)
    approx, _ = haar_dwt_level1(tail)
    detail_energy = float(np.mean(detail**2)) if detail.size else 0.0
    approx_last = float(approx[-1]) if approx.size else float(tail[-1])
    return {
        "dwt_detail_energy": detail_energy,
        "dwt_approx_last": approx_last,
    }


def expand_macro_series_features(
    dates: list[str],
    values_by_date: dict[str, float],
    *,
    window: int = 8,
    prefix: str,
) -> dict[str, dict[str, float]]:
    """For each date, compute TimeAPN stub features from causal-as-of history."""
    out: dict[str, dict[str, float]] = {}
    sorted_dates = sorted(dates)
    hist: list[float] = []
    for dk in sorted_dates:
        if dk in values_by_date and np.isfinite(values_by_date[dk]):
            hist.append(float(values_by_date[dk]))
        feats = timeapn_window_features(np.array(hist, dtype=float), window=window)
        out[dk] = {f"{prefix}_{k}": v for k, v in feats.items()}
    return out
