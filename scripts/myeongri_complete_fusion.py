# -*- coding: utf-8 -*-
"""명리 완전 융합: PerfectManseryeok 사주 → 오행 분포 → 4D (S,L,K,M)."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, Optional

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from scripts.manseryeok_perfect_final import PerfectManseryeok
from scripts.myeongri_jijangan_v1 import jijangan_overlay_for_saju
from scripts.myeongri_jijangan_ohang_v1 import build_myeongni_core_vector_v1
from scripts.myeongri_rule_school_mkm_4d_v1 import (
    blend_vector_4d_rule_school,
    load_rule_school_mkm_4d_v1,
)
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
    def __init__(self, rule_school_policy_path: Optional[Path] = None) -> None:
        self._manseryeok = PerfectManseryeok()
        self._rule_school_policy_path = (
            rule_school_policy_path
            if rule_school_policy_path is not None
            else _PROJECT_ROOT / "data" / "myeongni" / "rule_school_mkm_4d_v1.json"
        )

    def calculate_complete_fusion(
        self,
        birth_year: int,
        birth_month: int,
        birth_day: int,
        birth_hour: int,
        is_solar: bool = False,
        is_male: bool = True,
        *,
        precomputed_full_saju: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """precomputed_full_saju: ``PerfectManseryeok.calculate_full_saju_perfect`` 결과를 넣으면 만세력 재호출 생략."""
        if precomputed_full_saju is not None:
            raw = precomputed_full_saju
        else:
            raw = self._manseryeok.calculate_full_saju_perfect(
                birth_year,
                birth_month,
                birth_day,
                birth_hour,
                is_solar,
                is_male,
            )
        oh_surface = _four_pillars_to_ohang_strength(raw)
        vector_4d = _ohang_data_to_4d(oh_surface)
        saju = raw.get("saju") or {}
        core_vector = build_myeongni_core_vector_v1(saju)
        oh_jij = core_vector["element_strength"]
        vector_jij = _ohang_data_to_4d(oh_jij)
        policy = load_rule_school_mkm_4d_v1(self._rule_school_policy_path)
        wb = policy["vector_4d_blend"]
        vector_rule = blend_vector_4d_rule_school(
            vector_4d,
            vector_jij,
            float(wb["w_surface"]),
            float(wb["w_jijangan"]),
        )
        return {
            "vector_4d": vector_4d,
            "ohang_strength": oh_surface,
            "ohang_strength_jijangan_v1": oh_jij,
            "myeongni_core_vector_v1": core_vector,
            "vector_4d_jijangan_v1": vector_jij,
            "vector_4d_rule_school_v1": vector_rule,
            "rule_school_mkm_4d_v1": {
                "version": policy.get("version"),
                "policy_path": str(self._rule_school_policy_path.resolve()),
                "vector_4d_blend": policy.get("vector_4d_blend"),
            },
            "saju": saju,
            "jijangan_v1": jijangan_overlay_for_saju(saju),
            "daewoon_v1": raw.get("daewoon"),
            "daewoon_qiyun_v1": raw.get("daewoon_qiyun_v1"),
            "lambda": 0.25,
        }
