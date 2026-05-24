#!/usr/bin/env python3
"""KRX / US equity session calendar hints for commander morning briefing [FACT-LOCK v1].

Weekend: Sat/Sun KST = KRX closed. KRX public holidays are not in v1 (extend later).
NASDAQ morning block uses last completed daily bar date from CSV.
"""

from __future__ import annotations

import sys
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, Optional, Tuple
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
KST = ZoneInfo("Asia/Seoul")
NASDAQ_CSV = ROOT / "research" / "market_data" / "nasdaq_daily_external_yf.csv"


def calendar_kst_today() -> str:
    return datetime.now(KST).strftime("%Y-%m-%d")


def parse_calendar_kst(value: Optional[str] = None) -> date:
    raw = (value or calendar_kst_today()).strip()[:10]
    y, m, d = (int(x) for x in raw.split("-"))
    return date(y, m, d)


def is_krx_trading_day(d: date) -> bool:
    """v1: Mon–Fri only (no KRX holiday file)."""
    return d.weekday() < 5


def krx_session_status(d: Optional[date] = None) -> Dict[str, Any]:
    day = d or parse_calendar_kst()
    open_ = is_krx_trading_day(day)
    if open_:
        label = "개장일(근무일)"
        status = "open"
    elif day.weekday() >= 5:
        label = "휴장(주말)"
        status = "weekend"
    else:
        label = "휴장(비거래일)"
        status = "closed"
    return {
        "calendar_kst": day.isoformat(),
        "trading_today": open_,
        "status": status,
        "label_ko": label,
        "holiday_calendar_v1": False,
    }


def _load_nasdaq_last_session_date() -> Tuple[Optional[str], Optional[float], str]:
    if not NASDAQ_CSV.is_file():
        return None, None, "insufficient_data"
    from scripts.multi_asset_market_adapter_v1 import (  # noqa: WPS433
        NASDAQ_CSV as _NQ,
        _daily_return,
        _load_rows,
    )

    rows = _load_rows(_NQ)
    if len(rows) < 2:
        return None, None, "insufficient_data"
    last_date = str(rows[-1].get("date") or "")[:10]
    ret, direction = _daily_return(_NQ, last_date)
    return last_date, ret, direction


def nasdaq_prior_session_context(calendar: Optional[date] = None) -> Dict[str, Any]:
    cal = calendar or parse_calendar_kst()
    session_date, ret, direction = _load_nasdaq_last_session_date()
    note = "Last completed US daily bar (macro context only)"
    if session_date and session_date < cal.isoformat():
        note = f"직전 완료 미국 거래일 {session_date} (오늘 KST {cal.isoformat()} 장전 참고)"
    return {
        "session_date": session_date,
        "direction": direction,
        "return_pct": round(ret * 100, 4) if ret is not None else None,
        "note_ko": note,
        "scored_at_evening_kst": False,
    }


def build_session_banner_ko(d: Optional[date] = None) -> str:
    krx = krx_session_status(d)
    nas = nasdaq_prior_session_context(d)
    parts = [f"코스피: {krx['label_ko']}"]
    if nas.get("session_date"):
        parts.append(f"나스닥 prior: {nas['session_date']} ({nas.get('direction', '—')})")
    return " · ".join(parts)
