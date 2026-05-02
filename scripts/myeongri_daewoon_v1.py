# -*- coding: utf-8 -*-
"""대운(大運) 결정론 v1 — 월주 기준 순행/역행 + 선택적 起運 연령(첫 운 시작)."""

from __future__ import annotations

from typing import Any

CHEONGAN = ["갑", "을", "병", "정", "무", "기", "경", "신", "임", "계"]
JIJI = ["자", "축", "인", "묘", "진", "사", "오", "미", "신", "유", "술", "해"]

# 연속 행 경계 일치·JSON 가독용 (起運 부동 소수 누적 방지)
_AGE_DECIMALS = 6


def _age_bounds(base_age: float, num_cycles: int) -> list[float]:
    """길이 num_cycles+1; k번째 경계 = 첫 운 시작 + k*10세 (반올림 고정)."""
    return [round(base_age + k * 10, _AGE_DECIMALS) for k in range(num_cycles + 1)]


def daewoon_direction_forward(year_gan_idx: int, is_male: bool) -> bool:
    """True=순행, False=역행. 양남음녀 순행 / 음남양녀 역행."""
    is_yang_year = year_gan_idx % 2 == 0
    return (is_yang_year and is_male) or (not is_yang_year and not is_male)


def build_daewoon_list_v1(
    month_pillar: str,
    year_gan: str,
    is_male: bool,
    *,
    num_cycles: int = 10,
    qiyun_years_first_cycle: float | None = None,
) -> list[dict[str, Any]]:
    """
    월주 간지에서 간·지를 한 칸씩 동시에 순행/역행하여 대운 열을 만든다.

    - cycle 1(i=0)은 월주와 동일(기존 sajupy_advanced 스모크와 동일).
    - qiyun_years_first_cycle: 첫 대운 시작 만 나이(세). None이면 0부터 10년 단위(회귀 호환).
    """
    if len(month_pillar) < 2:
        raise ValueError("month_pillar must be a two-character ganji string")
    if year_gan not in CHEONGAN:
        raise ValueError(f"unknown year gan: {year_gan!r}")

    month_gan_idx = CHEONGAN.index(month_pillar[0])
    month_ji_idx = JIJI.index(month_pillar[1])
    year_gan_idx = CHEONGAN.index(year_gan)
    forward = daewoon_direction_forward(year_gan_idx, is_male)
    direction = 1 if forward else -1

    base_age = 0.0 if qiyun_years_first_cycle is None else float(qiyun_years_first_cycle)
    bounds = _age_bounds(base_age, num_cycles)
    out: list[dict[str, Any]] = []
    for i in range(num_cycles):
        g = (month_gan_idx + i * direction) % 10
        j = (month_ji_idx + i * direction) % 12
        pillar = CHEONGAN[g] + JIJI[j]
        age_start = bounds[i]
        age_end = bounds[i + 1]
        row: dict[str, Any] = {
            "age_start": age_start,
            "age_end": age_end,
            "saju": pillar,
            "cycle": i + 1,
            "direction": "forward" if forward else "backward",
            "schema": "daewoon_v1",
        }
        if qiyun_years_first_cycle is not None:
            row["qiyun_applied"] = True
        out.append(row)
    return out
