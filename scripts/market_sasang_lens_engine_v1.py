# -*- coding: utf-8 -*-
"""시장 사상 렌즈 v1 — 4분면 softmax·불확실도·veto (결정론, LLM 없음)."""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

from scripts.track_b_commander_gate_v1 import HUMAN_COMMANDER_GATE_V1

QUADRANTS = ("taeyang", "soyang", "taeeum", "soeum")


def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))


def load_policy(path: Path) -> dict[str, Any]:
    doc = json.loads(path.read_text(encoding="utf-8"))
    if doc.get("schema") != "market_sasang_lens_policy_v1":
        raise ValueError("policy schema must be market_sasang_lens_policy_v1")
    return doc


def softmax_4(logits: tuple[float, float, float, float], temperature: float) -> dict[str, float]:
    t = temperature if temperature > 1e-9 else 1e-9
    scaled = [x / t for x in logits]
    m = max(scaled)
    exps = [math.exp(x - m) for x in scaled]
    s = sum(exps)
    if s <= 0.0:
        return {k: 0.25 for k in QUADRANTS}
    return {
        "taeyang": exps[0] / s,
        "soyang": exps[1] / s,
        "taeeum": exps[2] / s,
        "soeum": exps[3] / s,
    }


def entropy_norm_4(p: dict[str, float]) -> float:
    """Normalized entropy in [0,1] for 4-way distribution (max entropy = ln(4))."""
    h = 0.0
    for k in QUADRANTS:
        x = float(p.get(k) or 0.0)
        if x > 1e-15:
            h -= x * math.log(x)
    return _clamp01(h / math.log(4.0))


def logits_from_features(
    *,
    heat: float,
    cold: float,
    vol: float,
    direction_score: float,
    policy: dict[str, Any],
) -> tuple[float, float, float, float]:
    lm = policy["logit_mapping"]
    h = _clamp01(heat)
    c = _clamp01(cold)
    v = _clamp01(vol)
    imb = max(-1.0, min(1.0, h - c))
    d = max(-1.0, min(1.0, direction_score))
    wdt = float(lm.get("w_direction_tilt", 0.0))

    ty = (
        float(lm["w_heat_taeyang"]) * h
        + float(lm["w_imbalance_pos_taeyang"]) * max(imb, 0.0)
        + float(lm["bias_taeyang"])
        + wdt * d
    )
    sy = (
        float(lm["w_heat_soyang"]) * h
        + float(lm["w_vol_soyang"]) * v
        + float(lm["bias_soyang"])
        + wdt * d * 0.5
    )
    te = (
        float(lm["w_cold_taeeum"]) * c
        + float(lm["w_imbalance_neg_taeeum"]) * max(-imb, 0.0)
        + float(lm["bias_taeeum"])
        - wdt * d * 0.45
    )
    se = (
        float(lm["w_cold_soeum"]) * c
        + float(lm["w_vol_inverse_soeum"]) * (1.0 - v)
        + float(lm["bias_soeum"])
        - wdt * d * 0.35
    )
    return (ty, sy, te, se)


def build_market_sasang_lens_payload(
    *,
    sasang_lens_doc: dict[str, Any] | None,
    policy: dict[str, Any],
    policy_path: str,
    source_input_path: str,
) -> dict[str, Any]:
    scores = (sasang_lens_doc or {}).get("scores") or {}
    upstream_conf = float(scores.get("confidence") or 0.0)
    direction_score = float(scores.get("direction_score") or 0.0)

    stream = (sasang_lens_doc or {}).get("sasang_stream_outputs") or {}
    mr = stream.get("machine_readables") if isinstance(stream.get("machine_readables"), dict) else {}
    heat = float(mr.get("heat_proxy")) if isinstance(mr.get("heat_proxy"), (int, float)) else 0.5
    cold = float(mr.get("cold_proxy")) if isinstance(mr.get("cold_proxy"), (int, float)) else 0.5
    vol = (
        float(mr.get("volatility_rarefaction_proxy"))
        if isinstance(mr.get("volatility_rarefaction_proxy"), (int, float))
        else 0.5
    )

    temperature = float(policy.get("softmax_temperature") or 1.0)
    logits = logits_from_features(
        heat=heat,
        cold=cold,
        vol=vol,
        direction_score=direction_score,
        policy=policy,
    )
    state_vec = softmax_4(logits, temperature)
    total_mass = sum(state_vec.values())
    ent_norm = entropy_norm_4(state_vec)

    ub = policy.get("uncertainty_blend") or {}
    w_e = float(ub.get("w_entropy") or 0.5)
    w_c = float(ub.get("w_one_minus_upstream_confidence") or 0.5)
    composite_uncertainty = _clamp01(w_e * ent_norm + w_c * (1.0 - _clamp01(upstream_conf)))

    vr = policy.get("veto_rules") or {}
    max_ent = float(vr.get("max_entropy_norm_for_signal") or 1.0)
    min_up = float(vr.get("min_upstream_confidence") or 0.0)
    reason_codes: list[str] = []
    force_hold = False
    if ent_norm >= max_ent:
        force_hold = True
        reason_codes.append("HIGH_ENTROPY_SOFTMAX")
    if upstream_conf < min_up:
        force_hold = True
        reason_codes.append("LOW_UPSTREAM_CONFIDENCE")
    if total_mass < float(vr.get("min_total_mass") or 0.99):
        force_hold = True
        reason_codes.append("SOFTMAX_MASS_DRIFT")

    # Direction hint for fusion stub alignment (same bull/bear/neutral vocabulary)
    if direction_score > 0.08:
        dir_hint = "bull"
    elif direction_score < -0.08:
        dir_hint = "bear"
    else:
        dir_hint = "neutral"

    return {
        "schema": "market_sasang_lens_v1",
        "version": "1.0.0",
        "lens_id": "market_sasang",
        "engine_id": "market_sasang_lens_v1",
        "hypothesis_tier": "B",
        "boundary_ack": True,
        "a_track_autotrigger_forbidden": True,
        "clinical_bridge_forbidden": True,
        "human_commander_gate_v1": dict(HUMAN_COMMANDER_GATE_V1),
        "policy": {
            "schema": policy.get("schema"),
            "version": policy.get("version"),
            "policy_path": policy_path,
        },
        "state_vector_sasang_softmax": {k: round(state_vec[k], 8) for k in QUADRANTS},
        "state_vector_sum_check": round(total_mass, 8),
        "uncertainty": {
            "entropy_norm_4way": round(ent_norm, 8),
            "upstream_lens_confidence": round(_clamp01(upstream_conf), 8),
            "composite_uncertainty": round(composite_uncertainty, 8),
        },
        "veto": {
            "force_hold": force_hold,
            "reason_codes": reason_codes,
            "veto_policy_version": str(policy.get("version") or ""),
        },
        "fusion_bridge": {
            "compatible_with": ["independent_lens_fusion_stub_v0", "report_independent_lens_fusion_stub_v0.py"],
            "direction_hint": dir_hint,
            "score_hint": round(max(-1.0, min(1.0, direction_score)), 8),
            "use_in_fusion_inputs": {
                "suggested_weight_key": "market_sasang_lens_v1",
                "prefer_field": "state_vector_sasang_softmax",
                "downweight_when_veto": True,
            },
        },
        "provenance": {
            "upstream_artifact_path": source_input_path,
            "upstream_lens_schema": (sasang_lens_doc or {}).get("schema"),
        },
        "note": "Market Sasang lens: numeric B-track; not medical advice; coordinator reads state_vector + veto + uncertainty.",
    }
