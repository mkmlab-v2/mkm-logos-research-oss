# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.9, L:0.9, K:0.5, M:0.4}
# Balance: 92
# Purpose: Provide SSOT month pillar calculation by solar-term boundaries.
# Keywords: saju, month-pillar, solar-term, ssot, oho-dunwol
"""Solar-term SSOT helper for month-pillar calculation.

This module standardizes fallback month-pillar logic across engines:
- month branch by near-solar-term boundary dates (deterministic fallback)
- month stem by 오호둔월법 (Five Tigers Dunjia month rule)

Priority in runtime should still be:
1) external standard DB / ephemeris source (if available)
2) this deterministic fallback
"""

from __future__ import annotations

from dataclasses import dataclass

CHEONGAN = ("갑", "을", "병", "정", "무", "기", "경", "신", "임", "계")
JIJI = ("자", "축", "인", "묘", "진", "사", "오", "미", "신", "유", "술", "해")

# 월지 인덱스: 寅(2)월부터 시작해 순환, 12월 절기(대설) 이후는 子(0)
MONTH_JI_BY_SOLAR_MONTH = {
    1: 1,   # 소한 -> 축월
    2: 2,   # 입춘 -> 인월
    3: 3,   # 경칩 -> 묘월
    4: 4,   # 청명 -> 진월
    5: 5,   # 입하 -> 사월
    6: 6,   # 망종 -> 오월
    7: 7,   # 소서 -> 미월
    8: 8,   # 입추 -> 신월
    9: 9,   # 백로 -> 유월
    10: 10, # 한로 -> 술월
    11: 11, # 입동 -> 해월
    12: 0,  # 대설 -> 자월
}

# 절기 "근사" 기준일 (SSOT fallback). Exact ephemeris source should override this.
SOLAR_TERM_DAY_APPROX = {
    1: 5, 2: 4, 3: 5, 4: 5, 5: 5, 6: 6, 7: 7, 8: 7, 9: 7, 10: 8, 11: 7, 12: 7
}

# 오호둔월법: 해당 연간 그룹의 寅월 시작 천간
FIRST_MONTH_STEM_BY_YEAR_STEM = {
    "갑": "병",
    "기": "병",
    "을": "무",
    "경": "무",
    "병": "경",
    "신": "경",
    "정": "임",
    "임": "임",
    "무": "갑",
    "계": "갑",
}


@dataclass(frozen=True)
class MonthPillarCalcMeta:
    month_ji_idx: int
    month_ji: str
    term_anchor_month: int
    term_anchor_day_approx: int
    used_prev_month_branch: bool
    method: str = "solar_term_ssot_fallback_v1"


def _month_branch_index(month: int, day: int) -> tuple[int, int, int, bool]:
    anchor_day = SOLAR_TERM_DAY_APPROX.get(month, 1)
    after_anchor = day >= anchor_day
    if after_anchor:
        ji_idx = MONTH_JI_BY_SOLAR_MONTH.get(month, 0)
        return ji_idx, month, anchor_day, False
    prev_month = month - 1 if month > 1 else 12
    ji_idx = MONTH_JI_BY_SOLAR_MONTH.get(prev_month, 0)
    return ji_idx, prev_month, SOLAR_TERM_DAY_APPROX.get(prev_month, 1), True


def _month_stem_by_five_tigers(year_stem: str, month_ji_idx: int) -> str:
    first_stem = FIRST_MONTH_STEM_BY_YEAR_STEM[year_stem]  # 寅월 시작 천간
    first_idx = CHEONGAN.index(first_stem)
    # 寅(2)을 0-offset으로 환산해 stem advance를 계산
    advance = (month_ji_idx - 2) % 12
    stem_idx = (first_idx + advance) % 10
    return CHEONGAN[stem_idx]


def calculate_month_pillar_ssot_fallback(year_stem: str, month: int, day: int) -> tuple[str, MonthPillarCalcMeta]:
    if year_stem not in FIRST_MONTH_STEM_BY_YEAR_STEM:
        raise ValueError(f"Unsupported year stem: {year_stem}")
    ji_idx, anchor_month, anchor_day, used_prev = _month_branch_index(month=month, day=day)
    month_ji = JIJI[ji_idx]
    month_stem = _month_stem_by_five_tigers(year_stem=year_stem, month_ji_idx=ji_idx)
    pillar = f"{month_stem}{month_ji}"
    meta = MonthPillarCalcMeta(
        month_ji_idx=ji_idx,
        month_ji=month_ji,
        term_anchor_month=anchor_month,
        term_anchor_day_approx=anchor_day,
        used_prev_month_branch=used_prev,
    )
    return pillar, meta
