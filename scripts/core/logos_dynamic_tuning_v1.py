"""Logos dynamic tuning — compose sandbox 4D + force lexicon + geumhwa decay ([HYPO]).

Does NOT mutate gematria_bridge_v1 production vectors.
"""

from __future__ import annotations

import json
import math
from functools import lru_cache
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
GEUMHWA = ROOT / "docs/verified_knowledge_base/unified_field_theory/geumhwa_exchange.json"
FORCE_AXIS: dict[str, str] = {
    "strong_force": "S",
    "em_force": "L",
    "weak_force": "K",
    "gravity": "M",
}


@lru_cache(maxsize=1)
def load_geumhwa_config(path: str | None = None) -> dict[str, Any]:
    p = Path(path) if path else GEUMHWA
    return json.loads(p.read_text(encoding="utf-8"))


def geumhwa_index(vector_4d: dict[str, float], *, earth_mediation_factor: float = 0.9) -> float:
    k = float(vector_4d.get("K", 0.25))
    m = float(vector_4d.get("M", 0.25))
    return max(0.0, k * (1.0 - m) * earth_mediation_factor)


def geumhwa_decay_factor(
    vector_4d: dict[str, float],
    *,
    session_age: float = 1.0,
    geumhwa_path: Path | None = None,
    eta: float = 0.9,
    earth_mediation_factor: float = 0.9,
) -> float:
    """Fire→gold temporal decay proxy in [0.05, 1.0] ([HYPO], non-gating)."""
    gh = geumhwa_index(vector_4d, earth_mediation_factor=earth_mediation_factor)
    raw = math.exp(-eta * gh * max(0.0, session_age) * 0.15)
    return max(0.05, min(1.0, raw))


def _renorm_sum_one(vec: dict[str, float]) -> dict[str, float]:
    keys = ("S", "L", "K", "M")
    total = sum(max(0.0, float(vec.get(k, 0.0))) for k in keys)
    if total <= 0:
        return {"S": 0.25, "L": 0.25, "K": 0.25, "M": 0.25}
    return {k: max(0.05, float(vec[k]) / total) for k in keys}


def softmax_force_bias(
    vector_4d: dict[str, float],
    *,
    top_primitive: str | None,
    force_id: str | None,
    temperature: float = 0.85,
    bias_strength: float = 0.12,
) -> dict[str, float]:
    """Overlay force-axis bias then softmax-renorm (sandbox sidecar only)."""
    keys = ("S", "L", "K", "M")
    axis_boost = {k: 0.0 for k in keys}
    if force_id and force_id in FORCE_AXIS:
        axis_boost[FORCE_AXIS[force_id]] = bias_strength
    elif top_primitive:
        # fallback axis hints from primitive families
        if top_primitive in ("pathology",):
            axis_boost["S"] = bias_strength * 0.8
        elif top_primitive in ("circulation",):
            axis_boost["L"] = bias_strength * 0.8
        elif top_primitive in ("survival",):
            axis_boost["K"] = bias_strength * 0.8
        elif top_primitive in ("harmony", "valence"):
            axis_boost["M"] = bias_strength * 0.8

    logits = [
        math.log(max(float(vector_4d.get(k, 0.25)), 1e-6)) + axis_boost[k] for k in keys
    ]
    m = max(logits)
    temp = max(0.05, float(temperature))
    exps = [math.exp((x - m) / temp) for x in logits]
    s = sum(exps) or 1.0
    out = {k: exps[i] / s for i, k in enumerate(keys)}
    return _renorm_sum_one(out)


def apply_geumhwa_temporal_overlay(
    vector_4d: dict[str, float],
    *,
    session_age: float = 1.0,
    geumhwa_path: Path | None = None,
) -> dict[str, float]:
    """Apply fire decay on L/K and gold accumulation on M ([HYPO])."""
    decay = geumhwa_decay_factor(vector_4d, session_age=session_age, geumhwa_path=geumhwa_path)
    vec = dict(vector_4d)
    vec["L"] = max(0.05, float(vec.get("L", 0.25)) * decay)
    vec["K"] = max(0.05, float(vec.get("K", 0.25)) * (0.65 + 0.35 * decay))
    vec["M"] = max(0.05, float(vec.get("M", 0.25)) + (1.0 - decay) * 0.04)
    return _renorm_sum_one(vec)


def spread_4d(vector_4d: dict[str, float]) -> float:
    vals = [float(vector_4d[k]) for k in ("S", "L", "K", "M")]
    return max(vals) - min(vals)


def tune_anchor_vector(
    anchor: dict[str, Any],
    *,
    force_id: str | None,
    session_age: float = 1.0,
    temperature: float = 0.85,
    geumhwa_path: Path | None = None,
) -> dict[str, Any]:
    base = anchor.get("vector_4d") or {}
    if not base:
        return {
            "vector_4d_dynamic": None,
            "spread_4d_dynamic": 0.0,
            "geumhwa_index": 0.0,
            "geumhwa_decay_factor": 1.0,
        }
    align = anchor.get("kernel_alignment") or []
    top_primitive = align[0].get("primitive") if align else None
    biased = softmax_force_bias(
        base,
        top_primitive=str(top_primitive) if top_primitive else None,
        force_id=force_id,
        temperature=temperature,
    )
    decayed = apply_geumhwa_temporal_overlay(
        biased, session_age=session_age, geumhwa_path=geumhwa_path
    )
    gh = geumhwa_index(decayed)
    return {
        "vector_4d_sandbox": {k: round(float(base[k]), 6) for k in ("S", "L", "K", "M")},
        "vector_4d_dynamic": {k: round(float(decayed[k]), 6) for k in ("S", "L", "K", "M")},
        "spread_4d_sandbox": round(spread_4d(base), 6),
        "spread_4d_dynamic": round(spread_4d(decayed), 6),
        "geumhwa_index": round(gh, 6),
        "geumhwa_decay_factor": round(
            geumhwa_decay_factor(base, session_age=session_age, geumhwa_path=geumhwa_path), 6
        ),
        "force_id": force_id,
        "top_primitive": top_primitive,
    }


def orb_ui_hints_from_dynamic(
    vector_4d: dict[str, float],
    *,
    geumhwa_index_val: float,
    decay_factor: float,
) -> dict[str, float]:
    """Map dynamic vector to OrbGraphBloom / lattice hints ([HYPO], non-gating)."""
    s, l, k, m = (float(vector_4d[x]) for x in ("S", "L", "K", "M"))
    spread = spread_4d(vector_4d)
    return {
        "pulse_period_ms": round(2800 + (1.0 - l) * 2200 + geumhwa_index_val * 400),
        "intensity_budget": round(min(1.0, max(0.15, 0.35 + s * 0.55 + spread * 2.0)), 4),
        "layout_density": round(min(0.72, max(0.2, 0.28 + m * 0.5)), 4),
        "lattice_mesh_strength": round(min(1.0, max(0.1, spread * 4.0 + k * 0.3)), 4),
        "hub_glow_alpha": round(min(0.85, max(0.12, 0.2 + (1.0 - decay_factor) * 0.45)), 4),
    }
