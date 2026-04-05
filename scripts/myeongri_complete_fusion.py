# -*- coding: utf-8 -*-
"""명리 완전 융합: PerfectManseryeok 사주 → 오행 분포 → 4D (S,L,K,M)."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from scripts.manseryeok_perfect_final import PerfectManseryeok
from tools.core.myeongri_4d_correction import _ohang_data_to_4d


def _four_pillars_to_ohang_strength(saju_block: Dict[str, Any]) -> Dict[str, float]:
    cheongan_ohang = {
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
    jiji_ohang = {
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
    oheng_count = {"목": 0, "화": 0, "토": 0, "금": 0, "수": 0}
    inner = saju_block.get("saju") or {}
    for key in ("year", "month", "day", "hour"):
        p = inner.get(key) or ""
        if len(p) >= 1 and p[0] in cheongan_ohang:
            oheng_count[cheongan_ohang[p[0]]] += 1
        if len(p) >= 2 and p[1] in jiji_ohang:
            oheng_count[jiji_ohang[p[1]]] += 1
    total = sum(oheng_count.values())
    if total == 0:
        return {
            "fire_strength": 0.2,
            "water_strength": 0.2,
            "wood_strength": 0.2,
            "metal_strength": 0.2,
            "earth_strength": 0.2,
        }
    return {
        "wood_strength": oheng_count["목"] / total,
        "fire_strength": oheng_count["화"] / total,
        "earth_strength": oheng_count["토"] / total,
        "metal_strength": oheng_count["금"] / total,
        "water_strength": oheng_count["수"] / total,
    }


class MyeongriCompleteFusion:
    def __init__(self) -> None:
        self._manseryeok = PerfectManseryeok()

    def calculate_complete_fusion(
        self,
        birth_year: int,
        birth_month: int,
        birth_day: int,
        birth_hour: int,
        is_solar: bool = False,
        is_male: bool = True,
    ) -> Dict[str, Any]:
        raw = self._manseryeok.calculate_full_saju_perfect(
            birth_year,
            birth_month,
            birth_day,
            birth_hour,
            is_solar,
            is_male,
        )
        oh = _four_pillars_to_ohang_strength(raw)
        vector_4d = _ohang_data_to_4d(oh)
        return {
            "vector_4d": vector_4d,
            "ohang_strength": oh,
            "saju": raw.get("saju"),
            "lambda": 0.25,
        }
