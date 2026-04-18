# -*- coding: utf-8 -*-
from __future__ import annotations

import pytest

from scripts.saju_birth_resolver_v1 import (
    normalize_iana_tz,
    resolve_from_local_civil,
    resolve_from_utc_instant,
    try_zoneinfo,
)


def test_normalize_iana_tz_ok():
    assert normalize_iana_tz(" Asia/Seoul ") == "Asia/Seoul"


def test_normalize_iana_tz_bad():
    with pytest.raises(ValueError, match="invalid"):
        normalize_iana_tz("Not/A/Real_Zone_Xyz")


def test_resolve_utc_seoul_matches_ganji_cohort_wall():
    r = resolve_from_utc_instant("1992-03-12T17:00:00Z", "Asia/Seoul")
    assert r.engine_year == 1992
    assert r.engine_month == 3
    assert r.engine_day == 13
    assert r.engine_hour == 2
    assert r.warnings == ()


def test_resolve_utc_new_york():
    r = resolve_from_utc_instant("2000-06-15T04:00:00Z", "America/New_York")
    assert r.local_datetime.hour == 0  # EDT
    assert r.engine_month == 6
    assert r.engine_day == 15


def test_dst_gap_local_raises():
    with pytest.raises(ValueError, match="local_civil_invalid"):
        resolve_from_local_civil(2024, 3, 10, 2, 30, 0, "America/New_York")


def test_local_valid_round_trip():
    r = resolve_from_local_civil(2024, 1, 15, 12, 0, 0, "Europe/Berlin")
    assert r.birth_instant_utc.year == 2024
    assert r.warnings == ()


def test_try_zoneinfo():
    assert try_zoneinfo("Pacific/Auckland") is True
    assert try_zoneinfo("Invalid/Zone") is False
