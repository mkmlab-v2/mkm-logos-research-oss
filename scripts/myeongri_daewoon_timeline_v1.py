# -*- coding: utf-8 -*-
"""대운 타임라인 v1: 起運 + 대운 리스트 + 기준시각(as_of_utc) 활성 사이클."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from scripts.myeongri_daewoon_v1 import build_daewoon_list_v1
from scripts.myeongri_qiyun_v1 import compute_qiyun_meta_v1

_DAYS_PER_YEAR = 365.2425


def _parse_as_of_utc(as_of_utc: str | None) -> datetime:
    if not as_of_utc:
        return datetime.now(timezone.utc)
    text = as_of_utc.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    dt = datetime.fromisoformat(text)
    if dt.tzinfo is None:
        raise ValueError("as_of_utc must include timezone, e.g. 2026-05-05T00:00:00Z")
    return dt.astimezone(timezone.utc)


def _active_cycle_index(rows: list[dict[str, Any]], age_years: float) -> int | None:
    for idx, row in enumerate(rows):
        start = float(row["age_start"])
        end = float(row["age_end"])
        if start <= age_years < end:
            return idx
    if rows and age_years >= float(rows[-1]["age_end"]):
        return len(rows) - 1
    return None


def build_myeongri_daewoon_timeline_v1(
    *,
    birth_year: int,
    birth_month: int,
    birth_day: int,
    birth_hour: int,
    month_pillar: str,
    year_gan: str,
    is_male: bool,
    num_cycles: int = 10,
    as_of_utc: str | None = None,
) -> dict[str, Any]:
    """
    대운 타임라인 단일 산출:
    - qiyun_meta: 起運 부동 연령(세)
    - daewoon_rows: 첫 운 시작 연령을 반영한 10년 구간
    - active_cycle: 기준시각에서의 활성 대운
    """
    qiyun = compute_qiyun_meta_v1(
        birth_year,
        birth_month,
        birth_day,
        birth_hour,
        year_gan,
        is_male,
    )
    rows = build_daewoon_list_v1(
        month_pillar,
        year_gan,
        is_male,
        num_cycles=num_cycles,
        qiyun_years_first_cycle=float(qiyun["qiyun_years_float"]),
    )

    as_of = _parse_as_of_utc(as_of_utc)
    birth_utc = datetime(birth_year, birth_month, birth_day, birth_hour, 0, 0, tzinfo=timezone.utc)
    age_years = (as_of - birth_utc).total_seconds() / 86400.0 / _DAYS_PER_YEAR
    idx = _active_cycle_index(rows, age_years)

    active: dict[str, Any] | None = None
    if idx is not None:
        active = dict(rows[idx])
        active["index_zero_based"] = idx

    return {
        "schema": "myeongri_daewoon_timeline_v1",
        "version": "1.0.0",
        "timezone_for_timeline_age": "UTC",
        "as_of_utc": as_of.isoformat().replace("+00:00", "Z"),
        "age_years_at_as_of": age_years,
        "qiyun_meta_v1": qiyun,
        "daewoon_rows": rows,
        "active_cycle": active,
    }

