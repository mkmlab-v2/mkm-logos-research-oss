# -*- coding: utf-8 -*-
"""Deterministic 4D (S,L,K,M) geometry for gematria–myeongri blend experiments.

No LLM, no LoRA, no trading signals. Callers supply upstream vectors; this module
only performs convex blend + renormalization and L2/cosine metrics.

B-track / [HYPO] when upstream vectors are hypothetical or research-only.
"""

from __future__ import annotations

import math
from typing import Any, Dict, Mapping, Tuple

MATH_MODULE_ID = "gematria_myeongri_math_v1"
MATH_MODULE_VERSION = "1.0.0"

_AXES: Tuple[str, ...] = ("S", "L", "K", "M")


def axes() -> Tuple[str, ...]:
    return _AXES


def coerce_4d(d: Mapping[str, Any]) -> Dict[str, float]:
    """Return a plain float dict on S,L,K,M keys (missing keys default to 0.0)."""
    return {k: float(d.get(k, 0.0)) for k in _AXES}


def renorm_4d(v: Mapping[str, float]) -> Dict[str, float]:
    s = sum(float(v[k]) for k in _AXES)
    if s <= 0.0:
        return {k: 0.25 for k in _AXES}
    return {k: float(v[k]) / s for k in _AXES}


def blend_convex_renorm(
    vanilla: Mapping[str, Any],
    myeongri: Mapping[str, Any],
    weight_myeongri: float,
) -> Dict[str, float]:
    """Convex combination (1-w)*vanilla + w*myeongri, then simplex renormalize."""
    w = max(0.0, min(1.0, float(weight_myeongri)))
    a = coerce_4d(vanilla)
    b = coerce_4d(myeongri)
    raw = {k: (1.0 - w) * a[k] + w * b[k] for k in _AXES}
    return renorm_4d(raw)


def l2_distance(a: Mapping[str, float], b: Mapping[str, float]) -> float:
    va, vb = coerce_4d(a), coerce_4d(b)
    return math.sqrt(sum((va[k] - vb[k]) ** 2 for k in _AXES))


def cosine_similarity(a: Mapping[str, float], b: Mapping[str, float]) -> float:
    va, vb = coerce_4d(a), coerce_4d(b)
    dot = sum(va[k] * vb[k] for k in _AXES)
    na = math.sqrt(sum(va[k] ** 2 for k in _AXES))
    nb = math.sqrt(sum(vb[k] ** 2 for k in _AXES))
    if na <= 0.0 or nb <= 0.0:
        return 0.0
    return float(dot / (na * nb))


def geometric_metrics(
    vanilla: Mapping[str, Any],
    myeongri: Mapping[str, Any],
    hybrid: Mapping[str, Any],
) -> Dict[str, float]:
    """L2 and cosine pairs used by the gematria–myeongri spike artifact."""
    v, m, h = coerce_4d(vanilla), coerce_4d(myeongri), coerce_4d(hybrid)
    return {
        "l2_vanilla_myeongri": round(l2_distance(v, m), 8),
        "l2_vanilla_hybrid": round(l2_distance(v, h), 8),
        "cosine_vanilla_myeongri": round(cosine_similarity(v, m), 8),
        "cosine_vanilla_hybrid": round(cosine_similarity(v, h), 8),
    }
