#!/usr/bin/env python3
"""
Onset-envelope autocorrelation BPM estimate (v1 · B-track / gate helper).

No librosa dependency — numpy only. Returns low confidence for non-rhythmic beds.
"""

from __future__ import annotations

from typing import Sequence


def measure_bpm_v1(
    samples: Sequence[float],
    sample_rate: int,
    *,
    min_bpm: float = 60.0,
    max_bpm: float = 180.0,
) -> tuple[float | None, float]:
    """Return (bpm, confidence 0..1). bpm is None when signal is too short or flat."""
    try:
        import numpy as np
    except ImportError:
        return None, 0.0

    x = np.asarray(samples, dtype=np.float64).reshape(-1)
    if x.size < max(1024, sample_rate // 4):
        return None, 0.0

    x = x - float(np.mean(x))
    peak = float(np.max(np.abs(x)))
    if peak < 1e-6:
        return None, 0.0
    x = x / peak

    target_sr = min(int(sample_rate), 22050)
    step = max(1, int(sample_rate) // target_sr)
    if step > 1:
        x = x[::step]
        sr = int(sample_rate) // step
    else:
        sr = int(sample_rate)

    env = np.abs(np.diff(x, prepend=x[0]))
    win = min(512, max(32, len(env) // 32))
    kernel = np.ones(win, dtype=np.float64) / float(win)
    env = np.convolve(env, kernel, mode="same")
    env = env - float(np.mean(env))
    if float(np.std(env)) < 1e-9:
        return None, 0.0

    ac = np.correlate(env, env, mode="full")
    ac = ac[len(ac) // 2 :]
    if ac[0] <= 0:
        return None, 0.0

    min_lag = max(1, int(sr * 60.0 / max_bpm))
    max_lag = min(len(ac) - 1, int(sr * 60.0 / min_bpm))
    if max_lag <= min_lag:
        return None, 0.0

    seg = ac[min_lag : max_lag + 1]
    peak_idx = int(np.argmax(seg)) + min_lag
    bpm = 60.0 * sr / float(peak_idx)
    confidence = float(seg.max() / (ac[0] + 1e-12))
    confidence = min(1.0, max(0.0, confidence))
    if confidence < 0.08:
        return None, confidence
    return float(bpm), confidence


def bpm_delta_pct(observed: float, target: float) -> float:
    if target <= 0:
        return 100.0
    return abs(observed - target) / target * 100.0
