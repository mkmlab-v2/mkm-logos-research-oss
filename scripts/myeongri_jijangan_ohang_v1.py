# -*- coding: utf-8 -*-
"""표면 간지 + 지장간(티어 가중) 오행 분포 → strength dict (합 1)."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Mapping

from scripts.myeongri_jijangan_v1 import JIJI, hidden_stems_for_branch, load_lut

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_WEIGHTS = ROOT / "data" / "myeongni" / "jijangan_ohang_weights_v1.json"

CHEONGAN_ELEMENT = {
    "갑": "목",
    "을": "목",
    "병": "화",
    "정": "화",
    "무": "토",
    "기": "토",
    "경": "금",
    "신": "금",
    "임": "수",
    "계": "수",
}
Jiji_ELEMENT = {
    "인": "목",
    "묘": "목",
    "사": "화",
    "오": "화",
    "진": "토",
    "술": "토",
    "축": "토",
    "미": "토",
    "신": "금",
    "유": "금",
    "해": "수",
    "자": "수",
}

_KEYS = ("year", "month", "day", "hour")
_ELEMENTS = ("목", "화", "토", "금", "수")


@lru_cache(maxsize=1)
def load_tier_weights(path: Path | None = None) -> dict[str, float]:
    p = path or DEFAULT_WEIGHTS
    doc = json.loads(p.read_text(encoding="utf-8"))
    if doc.get("schema") != "jijangan_ohang_weights_v1":
        raise ValueError("weights schema must be jijangan_ohang_weights_v1")
    tw = doc.get("tier_weights") or {}
    out = {}
    for k in ("jeong_gi", "jung_gi", "yeo_gi"):
        if k not in tw:
            raise ValueError(f"tier_weights missing {k}")
        out[k] = float(tw[k])
    return out


def ohang_strength_jijangan_v1(
    saju: Mapping[str, Any] | None,
    *,
    tier_weights_path: Path | None = None,
    lut_path: Path | None = None,
) -> dict[str, float]:
    """
    표면 8글자(천간·지지) 각 1단위 + 각 지지의 지장간 천간에 틀어맞춤 가중 합산 후 정규화.
    """
    weights = load_tier_weights(tier_weights_path)
    load_lut(lut_path)
    inner = dict(saju or {})
    counts = {e: 0.0 for e in _ELEMENTS}

    for key in _KEYS:
        pillar = inner.get(key) or ""
        if len(pillar) >= 1 and pillar[0] in CHEONGAN_ELEMENT:
            counts[CHEONGAN_ELEMENT[pillar[0]]] += 1.0
        if len(pillar) >= 2 and pillar[1] in Jiji_ELEMENT:
            counts[Jiji_ELEMENT[pillar[1]]] += 1.0
        if len(pillar) >= 2:
            ji = pillar[1]
            if ji in JIJI:
                for row in hidden_stems_for_branch(ji, lut_path=lut_path):
                    gan = row["gan"]
                    tier = str(row.get("tier") or "")
                    w = weights.get(tier, 0.0)
                    if gan in CHEONGAN_ELEMENT and w:
                        counts[CHEONGAN_ELEMENT[gan]] += w

    total = sum(counts.values())
    if total <= 0:
        return {
            "wood_strength": 0.2,
            "fire_strength": 0.2,
            "earth_strength": 0.2,
            "metal_strength": 0.2,
            "water_strength": 0.2,
        }
    return {
        "wood_strength": counts["목"] / total,
        "fire_strength": counts["화"] / total,
        "earth_strength": counts["토"] / total,
        "metal_strength": counts["금"] / total,
        "water_strength": counts["수"] / total,
    }
