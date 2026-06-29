#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Market psychology row -> Sasang TY/SY/TE/SE + lens machine_readables (B-track v2 SSOT)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

AXES = ("TY", "SY", "TE", "SE")
ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "docs/final/artifacts/market_psych_to_sasang_axis_manifest_v2.json"


def _safe_float(v: Any) -> float:
    try:
        if v is None or v == "":
            return 0.0
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def clip01(x: float) -> float:
    return max(0.0, min(1.0, float(x)))


def clip11(x: float) -> float:
    return max(-1.0, min(1.0, float(x)))


def load_manifest(path: Path | None = None) -> dict[str, Any]:
    p = path or DEFAULT_MANIFEST
    doc = json.loads(p.read_text(encoding="utf-8"))
    if doc.get("schema") != "market_psych_to_sasang_axis_manifest_v2":
        raise ValueError(f"unexpected manifest schema: {doc.get('schema')}")
    return doc


def validate_psych_csv_fields(fieldnames: list[str] | None, manifest: dict[str, Any]) -> None:
    if not fieldnames:
        raise ValueError("CSV has no header")
    lower = [str(f or "").lower() for f in fieldnames]
    for hint in manifest.get("forbidden_csv_field_hints") or []:
        for fld in lower:
            if hint in fld:
                raise ValueError(f"forbidden field hint '{hint}' in column '{fld}'")
    required = {"timestamp_utc", "fear_score", "greed_score"}
    missing = required - {f.lower() for f in fieldnames}
    if missing:
        raise ValueError(f"missing required columns: {sorted(missing)}")


def _derived_features(row: dict[str, str]) -> dict[str, float]:
    ret_5d = _safe_float(row.get("ret_5d"))
    vol_ratio = _safe_float(row.get("vol_ratio")) or 1.0
    rsi = _safe_float(row.get("rsi_14_norm"))
    if rsi <= 0 and "rsi_14_norm" not in row:
        rsi = 0.5
    greed = _safe_float(row.get("greed_score"))
    fear = _safe_float(row.get("fear_score"))
    panic = _safe_float(row.get("panic_ratio"))
    fomo = _safe_float(row.get("fomo_index"))
    vol_s = _safe_float(row.get("volatility_score"))
    rng = _safe_float(row.get("range_pct"))
    mom = _safe_float(row.get("momentum_20_60"))
    ret_20 = _safe_float(row.get("ret_20d"))
    dd = _safe_float(row.get("drawdown_20d"))
    trend = _safe_float(row.get("trend_strength"))

    heat = clip01(0.45 + 1.2 * ret_5d + 0.35 * greed + 0.2 * fomo)
    cold = clip01(0.45 - 1.2 * ret_5d + 0.35 * fear + 0.2 * panic)
    vol_ratio_dev = clip01(abs(vol_ratio - 1.0))
    vol_struct = clip01(0.5 * vol_s + 0.3 * rng + 0.2 * vol_ratio_dev)
    direction = clip11(0.55 * ret_5d + 0.25 * ret_20 + 0.2 * mom)

    return {
        "ret_5d": ret_5d,
        "ret_20d": ret_20,
        "greed_score": greed,
        "fear_score": fear,
        "panic_ratio": panic,
        "fomo_index": fomo,
        "volatility_score": vol_s,
        "dispersion_score": _safe_float(row.get("dispersion_score")),
        "range_pct": rng,
        "vol_ratio": vol_ratio,
        "vol_ratio_dev": vol_ratio_dev,
        "drawdown_20d": dd,
        "momentum_20_60": mom,
        "trend_strength": trend,
        "rsi_14_norm": rsi,
        "ret_5d_pos": max(0.0, ret_5d),
        "calm_inverse_vol": clip01(1.0 - vol_s),
        "low_panic": clip01(1.0 - panic),
        "rsi_neutral": clip01(1.0 - abs(rsi - 0.5) * 2.0),
        "heat_proxy": heat,
        "cold_proxy": cold,
        "vol_structure_proxy": vol_struct,
        "direction_score": direction,
    }


def _normalize(v: dict[str, float]) -> dict[str, float]:
    s = sum(float(v.get(a) or 0) for a in AXES)
    if s <= 0:
        return {a: 0.25 for a in AXES}
    return {a: float(v[a]) / s for a in AXES}


def _axis_raw(manifest: dict[str, Any], feats: dict[str, float]) -> dict[str, float]:
    weights = manifest.get("axis_raw_weights") or {}
    raw: dict[str, float] = {}
    for axis in AXES:
        wmap = weights.get(axis) or {}
        raw[axis] = sum(float(wmap.get(k) or 0) * float(feats.get(k) or 0) for k in wmap)
        raw[axis] = max(0.0, raw[axis])
    return raw


def _stress_to_state(stress: float) -> str:
    if stress >= 0.75:
        return "crisis"
    if stress >= 0.55:
        return "stress"
    if stress >= 0.35:
        return "watch"
    return "calm"


def byungjeung_from_stress(stress: float, prev_stress: float | None) -> dict[str, Any]:
    prev = prev_stress if prev_stress is not None else stress
    delta = stress - prev
    state = _stress_to_state(stress)
    if delta > 0.08:
        hint = "aggravating"
    elif delta < -0.08:
        hint = "recovering"
    else:
        hint = "stable_transition"
    return {
        "stress_index": round(stress, 6),
        "stress_delta": round(delta, 6),
        "byungjeung_state": state,
        "transition_hint": hint,
    }


def map_row_to_sasang(
    row: dict[str, str],
    *,
    manifest: dict[str, Any] | None = None,
    neutral_band: float = 0.06,
    prev_stress: float | None = None,
) -> dict[str, Any]:
    """Map one CSV row to normalized axis + direction + lens proxies."""
    m = manifest or load_manifest()
    feats = _derived_features(row)
    raw = _axis_raw(m, feats)
    axis = _normalize(raw)
    stress = 0.6 * axis["TE"] + 0.4 * axis["SE"]
    score = axis["TY"] + axis["SY"] - axis["TE"] - axis["SE"]
    if abs(score) < neutral_band:
        pred, mt = "neutral", "sideways"
    elif score > 0:
        pred, mt = "bull", "bull"
    else:
        pred, mt = "bear", "bear"
    top = max(AXES, key=lambda a: axis[a])
    bj = byungjeung_from_stress(stress, prev_stress)
    return {
        "axis_normalized": {k: round(axis[k], 6) for k in AXES},
        "axis_raw": {k: round(raw[k], 6) for k in AXES},
        "top_axis": top,
        "predicted_direction": pred,
        "mapping_target": mt,
        "fusion_direction_score": round(score, 6),
        "machine_readables": {
            "heat_proxy": round(feats["heat_proxy"], 6),
            "cold_proxy": round(feats["cold_proxy"], 6),
            "volatility_rarefaction_proxy": round(feats["vol_structure_proxy"], 6),
            "direction_score": round(feats["direction_score"], 6),
        },
        "features": {k: round(feats[k], 6) for k in sorted(feats)},
        "byungjeung": bj,
    }


def map_v1_heuristic_row(row: dict[str, str], neutral_band: float = 0.06) -> dict[str, Any]:
    """Legacy v1 linear map (for ablation baseline)."""
    from scripts.run_sasang_dna_market_reasoning_v1 import _build_market_axis_row, _normalize

    market_axis, metrics = _build_market_axis_row(row)
    axis = _normalize(market_axis)
    score = axis["TY"] + axis["SY"] - axis["TE"] - axis["SE"]
    if abs(score) < neutral_band:
        pred, mt = "neutral", "sideways"
    elif score > 0:
        pred, mt = "bull", "bull"
    else:
        pred, mt = "bear", "bear"
    stress = 0.6 * axis["TE"] + 0.4 * axis["SE"]
    return {
        "axis_normalized": {k: round(axis[k], 6) for k in AXES},
        "predicted_direction": pred,
        "mapping_target": mt,
        "fusion_direction_score": round(score, 6),
        "top_axis": max(AXES, key=lambda a: axis[a]),
        "market_metrics_v1": metrics,
        "stress_index": round(stress, 6),
    }
