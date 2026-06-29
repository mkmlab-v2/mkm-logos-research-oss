#!/usr/bin/env python3
"""
Numeric conditioning helpers for MusicGen (B-track [HYPO]).

- Synthetic melody guide from tempo_bpm_target (+ optional root_pc)
- Optional BPM time-stretch post-align when detector confidence is sufficient
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np

try:
    from scripts.audio.detect_bpm_v1 import bpm_delta_pct, measure_bpm_v1
except ModuleNotFoundError:
    from detect_bpm_v1 import bpm_delta_pct, measure_bpm_v1


def clamp_tempo_for_lens_gate(
    tempo_bpm: float,
    *,
    harmonic_ref: float = 90.0,
    max_delta_pct: float = 12.0,
) -> tuple[float, dict[str, Any]]:
    """
    Clamp tempo so harmonic-fold lens (observed~180, half~90) stays within gate tolerance.

    B-track operational guard — not a claim of MusicGen parametric BPM control.
    """
    raw = float(tempo_bpm)
    max_t = harmonic_ref / (1.0 - max_delta_pct / 100.0)
    min_t = harmonic_ref / (1.0 + max_delta_pct / 100.0)
    clamped = max(min_t, min(max_t, raw))
    clamped = round(clamped, 2)
    meta = {
        "raw_tempo_bpm_target": raw,
        "clamped_tempo_bpm_target": clamped,
        "lens_safe_clamp_applied": abs(clamped - raw) > 1e-6,
        "harmonic_ref_bpm": harmonic_ref,
        "max_delta_pct": max_delta_pct,
        "safe_band": [round(min_t, 2), round(max_t, 2)],
    }
    return clamped, meta


def extract_numeric_conditioning(conditioning: dict[str, Any] | None) -> dict[str, Any]:
    """Pull numeric fields from sasang_music_conditioning_v1."""
    if not conditioning:
        return {}
    cond = conditioning.get("conditioning") or {}
    out: dict[str, Any] = {}
    for key in ("tempo_bpm_target", "root_pc", "velocity_0_1", "mode_hint", "duration_seconds", "sample_rate"):
        if cond.get(key) is not None:
            out[key] = cond[key]
    return out


def root_pc_to_hz(root_pc: int, *, reference_a4_hz: float = 440.0) -> float:
    pc = int(root_pc) % 12
    return reference_a4_hz * (2.0 ** ((pc - 9) / 12.0))


def build_melody_guide_mono(
    *,
    tempo_bpm: float,
    duration_seconds: float,
    sample_rate: int,
    root_pc: int | None = None,
    velocity_0_1: float | None = None,
) -> np.ndarray:
    """Low-amplitude beat + root guide for musicgen-melody conditioning."""
    bpm = max(20.0, min(300.0, float(tempo_bpm)))
    duration_seconds = max(0.5, min(120.0, float(duration_seconds)))
    sr = int(sample_rate)
    n = int(duration_seconds * sr)
    arr = np.zeros(n, dtype=np.float64)
    spb = 60.0 / bpm
    amp = 0.08 + 0.12 * float(velocity_0_1 if velocity_0_1 is not None else 0.5)
    root_hz = root_pc_to_hz(root_pc if root_pc is not None else 0)

    beat_len = max(256, int(0.04 * sr))
    t = np.linspace(0.0, 1.0, beat_len, endpoint=False)
    click = np.sin(2.0 * math.pi * 880.0 * t) * np.exp(-8.0 * t)
    root_burst_len = max(512, int(0.12 * sr))
    tr = np.linspace(0.0, 1.0, root_burst_len, endpoint=False)
    root_burst = np.sin(2.0 * math.pi * root_hz * tr) * np.exp(-4.0 * tr)

    n_beats = int(duration_seconds / spb) + 1
    for beat in range(n_beats):
        start = int(beat * spb * sr)
        if start >= n:
            break
        end_click = min(n, start + len(click))
        arr[start:end_click] += click[: end_click - start] * amp
        if beat % 4 == 0:
            end_root = min(n, start + len(root_burst))
            arr[start:end_root] += root_burst[: end_root - start] * (amp * 0.6)

    peak = float(np.max(np.abs(arr))) or 1.0
    return (arr / peak * 0.35).astype(np.float32)


def guidance_scale_from_velocity(velocity_0_1: float | None, *, default: float = 3.0) -> float:
    if velocity_0_1 is None:
        return default
    v = max(0.0, min(1.0, float(velocity_0_1)))
    return round(1.5 + v * 3.5, 2)


def _best_harmonic_bpm(observed: float, target: float) -> tuple[float, float]:
    candidates = [
        (float(observed), bpm_delta_pct(observed, target)),
        (float(observed / 2.0), bpm_delta_pct(observed / 2.0, target)) if observed >= 2.0 else (observed, 999.0),
        (float(observed * 2.0), bpm_delta_pct(observed * 2.0, target)),
    ]
    best_bpm, best_delta = min(candidates, key=lambda row: row[1])
    return best_bpm, best_delta


def time_stretch_to_target_bpm(
    samples: np.ndarray,
    sample_rate: int,
    target_bpm: float,
    *,
    min_confidence: float = 0.25,
    max_delta_pct: float = 12.0,
) -> tuple[np.ndarray, dict[str, Any] | None]:
    """Resample-based stretch when observed BPM differs from target."""
    observed, confidence = measure_bpm_v1(samples.tolist(), sample_rate)
    meta: dict[str, Any] = {
        "bpm_observed_before": observed,
        "bpm_confidence": confidence,
        "bpm_target": float(target_bpm),
    }
    if observed is None or confidence < min_confidence or target_bpm <= 0:
        meta["applied"] = False
        meta["reason"] = "low_confidence_or_missing_bpm"
        return samples, meta

    harmonic_bpm, harmonic_delta = _best_harmonic_bpm(float(observed), float(target_bpm))
    meta["bpm_harmonic_before"] = harmonic_bpm
    meta["bpm_delta_pct_harmonic"] = harmonic_delta
    if harmonic_delta <= max_delta_pct:
        meta["applied"] = False
        meta["reason"] = "harmonic_within_tolerance"
        return samples, meta

    duration_factor = harmonic_bpm / float(target_bpm)
    duration_factor = max(0.5, min(2.0, duration_factor))
    new_len = max(128, int(len(samples) * duration_factor))
    x_old = np.linspace(0.0, 1.0, num=len(samples), endpoint=False)
    x_new = np.linspace(0.0, 1.0, num=new_len, endpoint=False)
    stretched = np.interp(x_new, x_old, samples.astype(np.float64)).astype(np.float32)
    meta["applied"] = True
    meta["duration_factor"] = duration_factor
    meta["samples_before"] = int(len(samples))
    meta["samples_after"] = int(len(stretched))
    return stretched, meta


def resolve_melody_model_id(base_model_id: str) -> str:
    if "melody" in base_model_id.lower():
        return base_model_id
    env = __import__("os").environ.get("MKM_AUDIO_MUSICGEN_MELODY_MODEL", "").strip()
    if env:
        return env
    if base_model_id.endswith("-small"):
        return base_model_id.replace("-small", "-melody")
    if base_model_id.endswith("-medium"):
        return base_model_id.replace("-medium", "-melody")
    return "facebook/musicgen-melody"
