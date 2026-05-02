# -*- coding: utf-8 -*-
"""起運 v1: 순행=다음 절까지 일수, 역행=이전 절까지 일수 → 3일=1세 근사 (UTC JD 차이)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

try:
    from zoneinfo import ZoneInfo
except ImportError:  # pragma: no cover
    ZoneInfo = None  # type: ignore[misc, assignment]

from scripts.core.solar_longitude_meeus_v1 import _datetime_to_jd_ut
from scripts.core.solar_term_jie_crossings_v1 import (
    next_jie_boundary_jd_ut,
    prev_jie_boundary_jd_ut,
)
from scripts.myeongri_daewoon_v1 import _AGE_DECIMALS, CHEONGAN, daewoon_direction_forward


def birth_jd_ut_seoul(year: int, month: int, day: int, hour: int, minute: int = 0) -> float:
    if ZoneInfo is None:
        raise RuntimeError("zoneinfo required (Python 3.9+)")
    dt = datetime(year, month, day, hour, minute, 0, tzinfo=ZoneInfo("Asia/Seoul"))
    return _datetime_to_jd_ut(dt.astimezone(timezone.utc))


def compute_qiyun_meta_v1(
    year: int,
    month: int,
    day: int,
    hour: int,
    year_gan: str,
    is_male: bool,
) -> dict[str, Any]:
    """대운 방향에 따라 절기까지의 일수·起運 연령(부동)."""
    if year_gan not in CHEONGAN:
        raise ValueError(f"unknown year gan: {year_gan!r}")
    jd_b = birth_jd_ut_seoul(year, month, day, hour)
    ygi = CHEONGAN.index(year_gan)
    forward = daewoon_direction_forward(ygi, is_male)
    if forward:
        jd_term = next_jie_boundary_jd_ut(jd_b)
        days = jd_term - jd_b
    else:
        jd_term = prev_jie_boundary_jd_ut(jd_b)
        days = jd_b - jd_term
    # 대운 첫 운 연령과 JSON 표시 정합 — 반올림 후 years_float = days/3 유지
    days_raw = float(days)
    qiyun_days = round(days_raw, _AGE_DECIMALS)
    if days_raw > 0 and qiyun_days == 0:
        # 극소 양수(6자리에서 0으로만 보이는 경우)는 원값 유지
        qiyun_days = days_raw
    qiyun_years_float = round(float(qiyun_days) / 3.0, _AGE_DECIMALS)
    return {
        "schema": "qiyun_v1",
        "forward": forward,
        "qiyun_days": qiyun_days,
        "qiyun_years_float": qiyun_years_float,
        "birth_jd_ut": jd_b,
        "jie_boundary_jd_ut": jd_term,
        "timezone": "Asia/Seoul",
        "method": "meeus_sun_lon_jie_v1",
    }
