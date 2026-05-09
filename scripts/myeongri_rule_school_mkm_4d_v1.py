# -*- coding: utf-8 -*-
"""rule_school_mkm_4d_v1 정책 로드 — 표면 vs 지장간 4D 블렌드 가중."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_POLICY = ROOT / "data" / "myeongni" / "rule_school_mkm_4d_v1.json"
DEFAULT_CONFLICT_POLICY = ROOT / "data" / "myeongni" / "myeongni_conflict_arbitration_v1.json"


def blend_vector_4d_rule_school(
    vector_surface: dict[str, float],
    vector_jijangan: dict[str, float],
    w_surface: float,
    w_jijangan: float,
) -> dict[str, float]:
    """S,L,K,M 에 대해 가중 합 후 재정규화(합 1)."""
    keys = ("S", "L", "K", "M")
    out = {
        k: w_surface * float(vector_surface.get(k, 0.0))
        + w_jijangan * float(vector_jijangan.get(k, 0.0))
        for k in keys
    }
    ssum = sum(out.values())
    if ssum <= 0.0:
        return {k: 0.25 for k in keys}
    return {k: out[k] / ssum for k in keys}


def load_rule_school_mkm_4d_v1(path: Path | None = None) -> dict[str, Any]:
    p = path or DEFAULT_POLICY
    doc = json.loads(p.read_text(encoding="utf-8"))
    if doc.get("schema") != "rule_school_mkm_4d_v1":
        raise ValueError("policy schema must be rule_school_mkm_4d_v1")
    vb = doc.get("vector_4d_blend") or {}
    ws = float(vb.get("w_surface", 0.0))
    wj = float(vb.get("w_jijangan", 0.0))
    if ws < 0 or wj < 0:
        raise ValueError("blend weights must be non-negative")
    if abs(ws + wj - 1.0) > 1e-6:
        raise ValueError(f"w_surface + w_jijangan must sum to 1; got {ws + wj}")
    return doc


def load_myeongni_conflict_arbitration_v1(path: Path | None = None) -> dict[str, Any]:
    """Compatibility loader for legacy conflict arbitration verifier."""
    p = path or DEFAULT_CONFLICT_POLICY
    doc = json.loads(p.read_text(encoding="utf-8"))
    if doc.get("schema") != "myeongni_conflict_arbitration_v1":
        raise ValueError("policy schema must be myeongni_conflict_arbitration_v1")
    return doc


def apply_myeongni_conflict_arbitration_v1(
    vector_4d: dict[str, float],
    *,
    ohang_surface: dict[str, float],
    ohang_jijangan: dict[str, float],
    policy: dict[str, Any],
) -> tuple[dict[str, float], dict[str, Any]]:
    """Compatibility adapter used by edge-case and sweep scripts.

    This keeps old scripts runnable after module consolidation.
    """
    out = {k: float(vector_4d.get(k, 0.0)) for k in ("S", "L", "K", "M")}
    rules = policy.get("arbitration_rules") or {}
    r1 = rules.get("rule_1_eokbu_vs_jogoo") or {}
    r2 = rules.get("rule_2_surface_vs_jijangan") or {}
    r3 = rules.get("rule_3_gyukguk_vs_4d_vector") or {}

    fire_surface = float(ohang_surface.get("fire_strength", 0.0))
    fire_jijangan = float(ohang_jijangan.get("fire_strength", 0.0))
    surface_vals = [float(v) for v in ohang_surface.values()] if ohang_surface else [0.0]
    jijangan_vals = [float(v) for v in ohang_jijangan.values()] if ohang_jijangan else [0.0]
    # Use stronger imbalance signal so extreme skew cases trigger HOLD guards as intended.
    jogoo_abs = max(max(surface_vals) - min(surface_vals), max(jijangan_vals) - min(jijangan_vals))
    jogoo_cut = float((r1.get("threshold") or {}).get("jogoo_imbalance_abs", 1.0))
    k_multiplier = float(r1.get("k_multiplier_if_triggered", 1.0))
    jogoo_triggered = jogoo_abs >= jogoo_cut
    if jogoo_triggered:
        out["K"] = out["K"] * max(k_multiplier, 1.0)

    # Lightweight surface/jijangan blend contribution.
    w_surface = float((r2.get("weights") or {}).get("surface_stem", 1.0))
    w_jijangan = float((r2.get("weights") or {}).get("jijangan_root", 1.0))
    total_w = w_surface + w_jijangan
    if total_w > 0:
        l_target = (w_surface * fire_surface + w_jijangan * fire_jijangan) / total_w
        out["L"] = (out["L"] + l_target) / 2.0

    ssum = sum(out.values())
    if ssum <= 0:
        out = {k: 0.25 for k in ("S", "L", "K", "M")}
    else:
        out = {k: out[k] / ssum for k in ("S", "L", "K", "M")}

    band = r3.get("stability_band") or {}
    stable = (
        float(band.get("l_min", -1e9)) <= out["L"] <= float(band.get("l_max", 1e9))
        and float(band.get("k_min", -1e9)) <= out["K"] <= float(band.get("k_max", 1e9))
    )
    label = str(r3.get("upgrade_label_if_stable", "WATCH")) if stable else "WATCH"
    meta = {
        "jogoo_triggered": jogoo_triggered,
        "k_multiplier_applied": k_multiplier if jogoo_triggered else 1.0,
        "vector_policy_label": label,
        "jogoo_imbalance_abs": jogoo_abs,
    }
    return out, meta
