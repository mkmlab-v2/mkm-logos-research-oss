# -*- coding: utf-8 -*-
"""오행 강도 dict → (S,L,K,M) 단순체 매핑.

Used by ``scripts/myeongri_complete_fusion.py``. This is a deterministic B-track
projection (5 오행 → 4축), not 천문급 만세력 정밀도. Replace when SSOT table exists.
"""

from __future__ import annotations

from typing import Any, Dict


def _ohang_data_to_4d(oh: Dict[str, Any]) -> Dict[str, float]:
    """Map wood/fire/earth/metal/water strengths to normalized S,L,K,M (sum≈1)."""
    w = float(oh.get("wood_strength", 0.2))
    f = float(oh.get("fire_strength", 0.2))
    e = float(oh.get("earth_strength", 0.2))
    m = float(oh.get("metal_strength", 0.2))
    wt = float(oh.get("water_strength", 0.2))
    # 5→4: 목·화·금은 각각 S,L,K; 토+수는 M에 합산(응축 축).
    raw = {"S": w, "L": f, "K": m, "M": e + wt}
    ssum = sum(raw.values())
    if ssum <= 0.0:
        return {"S": 0.25, "L": 0.25, "K": 0.25, "M": 0.25}
    return {k: raw[k] / ssum for k in ("S", "L", "K", "M")}


__all__ = ["_ohang_data_to_4d"]
