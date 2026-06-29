"""CPCV shadow promotion PoC smoke tests."""

from __future__ import annotations

from scripts.build_kospi_cpcv_shadow_promotion_poc_v1 import _split_groups, merge_calendars


def test_split_groups_even() -> None:
    dates = [f"2026-01-{d:02d}" for d in range(1, 13)]
    groups = _split_groups(dates, 6)
    assert len(groups) == 6
    assert sum(len(g) for g in groups) == 12


def test_merge_calendars_has_rows() -> None:
    cal = merge_calendars(("2026-06",))
    assert len(cal.get("rows") or []) > 0
