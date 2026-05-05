"""Aroon (Chande) — window 기준 Up/Down (0~100).

고점/저점이 윈도우 내에서 얼마나 "최근"인지로 추세 강도를 나타낸다.
"""
from __future__ import annotations


def aroon_up_down(highs: list[float], lows: list[float], period: int) -> tuple[float, float]:
    """
    마지막 ``period`` 개 봉만 사용. highs/lows 는 시간순(과거 → 현재).

    Aroon Up   = 100 * (period - periods_since_highest_high) / period
    Aroon Down = 100 * (period - periods_since_lowest_low) / period

    periods_since_* 는 윈도우의 **가장 오래된 봉을 0**, 가장 최근 봉을 period-1 로 둔 인덱스 기준
    최고/최저가가 나온 봉까지의 거리(최신에 가까울수록 작음).
    """
    if period < 2:
        raise ValueError("period must be >= 2")
    if len(highs) != len(lows):
        raise ValueError("highs/lows length mismatch")
    if len(highs) < period:
        raise ValueError(f"need at least {period} bars, got {len(highs)}")

    wh = highs[-period:]
    wl = lows[-period:]
    i_h = max(range(period), key=lambda i: wh[i])
    i_l = min(range(period), key=lambda i: wl[i])
    periods_since_hh = (period - 1) - i_h
    periods_since_ll = (period - 1) - i_l
    a_up = 100.0 * (period - periods_since_hh) / period
    a_dn = 100.0 * (period - periods_since_ll) / period
    return (a_up, a_dn)
