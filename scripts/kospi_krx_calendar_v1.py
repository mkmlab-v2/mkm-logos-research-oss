#!/usr/bin/env python3
"""KRX weekday calendar with explicit non-trading days [HYPO][research_only]."""
from __future__ import annotations

import json
from datetime import date, timedelta
from functools import lru_cache
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_NON_TRADING = ROOT / "data/commander/krx_non_trading_days_v1.json"


@lru_cache(maxsize=1)
def load_krx_non_trading_days(path: str | None = None) -> dict[str, dict[str, Any]]:
    p = Path(path) if path else DEFAULT_NON_TRADING
    if not p.is_file():
        return {}
    doc = json.loads(p.read_text(encoding="utf-8-sig"))
    out: dict[str, dict[str, Any]] = {}
    for ent in doc.get("entries") or []:
        dk = str(ent.get("date") or "")[:10]
        if len(dk) == 10:
            out[dk] = ent
    return out


def krx_weekdays(d0: date, d1: date) -> list[str]:
    out: list[str] = []
    d = d0
    while d <= d1:
        if d.weekday() < 5:
            out.append(d.isoformat())
        d += timedelta(days=1)
    return out


def krx_trading_days(d0: date, d1: date, *, non_trading_path: Path | None = None) -> list[str]:
    holidays = load_krx_non_trading_days(
        str(non_trading_path or DEFAULT_NON_TRADING) if non_trading_path else None
    )
    return [dk for dk in krx_weekdays(d0, d1) if dk not in holidays]


def last_krx_trading_day_on_or_before(d: date, *, non_trading_path: Path | None = None) -> str | None:
    """Most recent KRX trading session date on or before ``d`` (YYYY-MM-DD)."""
    d0 = d - timedelta(days=21)
    days = krx_trading_days(d0, d, non_trading_path=non_trading_path)
    return days[-1] if days else None


def exclude_krx_non_trading(days: list[str], *, non_trading_path: Path | None = None) -> tuple[list[str], list[str]]:
    holidays = load_krx_non_trading_days(
        str(non_trading_path or DEFAULT_NON_TRADING) if non_trading_path else None
    )
    kept: list[str] = []
    excluded: list[str] = []
    for dk in days:
        if dk in holidays:
            excluded.append(dk)
        else:
            kept.append(dk)
    return kept, excluded
