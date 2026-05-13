# -*- coding: utf-8 -*-
from __future__ import annotations

from datetime import date

from scripts.build_btrack_session_instant_myeongni_panel_v1 import (
    SessionPanelParams,
    iter_session_rows,
)


def test_iter_session_rows_two_days_all_calendar():
    p = SessionPanelParams(
        date_from=date(2024, 6, 12),
        date_to=date(2024, 6, 13),
        iana_tz="Asia/Seoul",
        hour=9,
        minute=0,
        second=0,
        calendar_mode="all",
        dst_fold=0,
    )
    rows = list(iter_session_rows(p))
    assert len(rows) == 2
    for r in rows:
        assert r["session_local_date"]
        assert "year_pillar" in r and r["year_pillar"]
        assert r["quant_status"] in ("ok", "insufficient_day_stem")
        assert r["elem_fire"] != ""


def test_krx_weekdays_skips_weekend():
    p = SessionPanelParams(
        date_from=date(2024, 6, 14),  # Fri
        date_to=date(2024, 6, 17),  # Mon
        iana_tz="Asia/Seoul",
        hour=9,
        minute=0,
        second=0,
        calendar_mode="krx_weekdays",
        dst_fold=0,
    )
    rows = list(iter_session_rows(p))
    dates = {r["session_local_date"] for r in rows}
    assert "2024-06-15" not in dates and "2024-06-16" not in dates
    assert "2024-06-14" in dates and "2024-06-17" in dates
