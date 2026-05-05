# -*- coding: utf-8 -*-
from __future__ import annotations

import pytest

from scripts.build_manseryeok_database_from_sajupy_advanced import (
    calculate_daewoon_cycles,
)
from scripts.myeongri_daewoon_v1 import (
    build_daewoon_list_v1,
    daewoon_direction_forward,
)


def test_daewoon_direction_yang_male_forward():
    # 갑=0 even -> yang, male -> forward
    assert daewoon_direction_forward(0, True) is True


def test_daewoon_direction_yin_male_backward():
    # 을=1 -> yin, male -> backward
    assert daewoon_direction_forward(1, True) is False


def test_daewoon_list_matches_legacy_sajupy_helper():
    month = "기해"
    for year_gan_idx, yg in [(0, "갑"), (1, "을")]:
        for is_male in (True, False):
            a = build_daewoon_list_v1(month, yg, is_male, num_cycles=10)
            b = calculate_daewoon_cycles(month, year_gan_idx, is_male, num_cycles=10)
            for i in range(10):
                assert a[i]["saju"] == b[i]["saju"]
                assert a[i]["age_start"] == b[i]["age_start"]


def test_invalid_month_pillar():
    with pytest.raises(ValueError):
        build_daewoon_list_v1("", "갑", True)


def test_qiyun_applied_consecutive_age_bounds_match():
    """起運 부동 소수여도 연속 행 경계가 단일 bounds에서 나와 일치한다."""
    base = 7.225552467784534  # 예: qiyun_years_float 스타일
    rows = build_daewoon_list_v1(
        "기해",
        "갑",
        True,
        num_cycles=10,
        qiyun_years_first_cycle=base,
    )
    for i in range(len(rows) - 1):
        assert rows[i]["age_end"] == rows[i + 1]["age_start"]
    assert rows[0]["age_start"] == round(base, 6)
