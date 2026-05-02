# -*- coding: utf-8 -*-
"""12절(節) 황경 교차 시각 — tropical, Meeus 태양 경도. 대운 起運 일수용."""

from __future__ import annotations

from scripts.core.solar_longitude_meeus_v1 import sun_apparent_ecliptic_longitude_deg

# 월절 12: 立春 … 小寒 (태양 황경 °, 순서는 연중 순환)
JIE_SOLAR_LONGITUDE_DEG: tuple[float, ...] = (
    315.0,
    345.0,
    15.0,
    45.0,
    75.0,
    105.0,
    135.0,
    165.0,
    195.0,
    225.0,
    255.0,
    285.0,
)


def _sun_lon(jd_ut: float) -> float:
    return sun_apparent_ecliptic_longitude_deg(jd_ut)


def _crossed_forward(lon_prev: float, lon_curr: float, target: float) -> bool:
    """lon_prev → lon_curr (시간 증가, 짧은 구간) 동안 target 황경을 지나는지."""
    tt = target % 360.0
    lp = lon_prev % 360.0
    lc = lon_curr % 360.0
    if lc >= lp:
        return lp < tt <= lc
    return lp < tt <= 360.0 or 0.0 <= tt <= lc


def _bisect_lon_equal(jd_lo: float, jd_hi: float, target: float) -> float:
    """[jd_lo, jd_hi]에서 경도가 target에 가장 가까운 시각(단조 증가 가정)."""
    tgt = target % 360.0
    for _ in range(90):
        if jd_hi - jd_lo < 1e-9:
            break
        mid = (jd_lo + jd_hi) / 2.0
        lm = _sun_lon(mid)
        if lm < tgt:
            jd_lo = mid
        else:
            jd_hi = mid
    return (jd_lo + jd_hi) / 2.0


def _first_crossing_after(jd_start: float, target_lon: float, max_days: float = 400.0) -> float:
    """jd_start 이후 첫 target_lon 교차 시각 (UTC JD)."""
    step = 1.0 / 24.0
    jd_prev = jd_start
    lon_prev = _sun_lon(jd_prev)
    jd = jd_start
    while jd - jd_start < max_days:
        jd += step
        lon_jd = _sun_lon(jd)
        if _crossed_forward(lon_prev, lon_jd, target_lon):
            return _bisect_lon_equal(jd - step, jd, target_lon % 360.0)
        lon_prev = lon_jd
    raise RuntimeError(f"no forward crossing for lon={target_lon} within {max_days}d")


def _last_crossing_before(jd_end: float, target_lon: float, max_days: float = 400.0) -> float:
    """jd_end 이전 마지막 target_lon 교차 시각."""
    step = 1.0 / 24.0
    jd_hi = jd_end
    lon_hi = _sun_lon(jd_hi)
    jd = jd_hi
    while jd_end - jd < max_days:
        jd_lo = jd - step
        lon_lo = _sun_lon(jd_lo)
        if _crossed_forward(lon_lo, lon_hi, target_lon):
            return _bisect_lon_equal(jd_lo, jd_hi, target_lon % 360.0)
        jd = jd_lo
        lon_hi = lon_lo
    raise RuntimeError(f"no backward crossing for lon={target_lon} within {max_days}d")


def next_jie_boundary_jd_ut(jd_ut_birth: float) -> float:
    """생시 이후 가장 가까운 12절 입절 시각(UTC JD)."""
    candidates: list[float] = []
    for T in JIE_SOLAR_LONGITUDE_DEG:
        try:
            c = _first_crossing_after(jd_ut_birth + 1e-9, T)
            candidates.append(c)
        except RuntimeError:
            continue
    if not candidates:
        raise RuntimeError("next_jie: no boundary found")
    return min(candidates)


def prev_jie_boundary_jd_ut(jd_ut_birth: float) -> float:
    """생시 이전 가장 가까운 12절 입절 시각(UTC JD)."""
    candidates: list[float] = []
    for T in JIE_SOLAR_LONGITUDE_DEG:
        try:
            c = _last_crossing_before(jd_ut_birth - 1e-9, T)
            candidates.append(c)
        except RuntimeError:
            continue
    if not candidates:
        raise RuntimeError("prev_jie: no boundary found")
    return max(candidates)

