#!/usr/bin/env python3
"""Multi-asset market adapter for P31 briefing score — KOSPI / BTC / NASDAQ [HYPO].

Timezone Fact-Lock (KST):
- KOSPI: same-calendar-day daily close vs prior close (15:30 settle).
- BTC: 12h snapshot (morning seal price vs evening spot) when seal present; else daily.
- NASDAQ: NOT scored at 20:30 — pending_until_morning (US session opens ~22:30 KST May DST).
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
KST = ZoneInfo("Asia/Seoul")

KOSPI_CSV = ROOT / "research" / "market_data" / "kospi_daily_external_yf.csv"
BTC_CSV = ROOT / "research" / "market_data" / "btc_daily_external_yf.csv"
NASDAQ_CSV = ROOT / "research" / "market_data" / "nasdaq_daily_external_yf.csv"


def _load_rows(csv_path: Path) -> List[Dict[str, Any]]:
    from scripts.logos_shadow_eval_lib import load_kospi_yf_rows  # noqa: WPS433

    return load_kospi_yf_rows(csv_path)


def _daily_return(csv_path: Path, date_kst: str) -> Tuple[Optional[float], str]:
    rows = _load_rows(csv_path)
    by_date = {str(r.get("date") or "")[:10]: r for r in rows if r.get("date")}
    if date_kst not in by_date:
        return None, "insufficient_data"
    dates = sorted(by_date.keys())
    idx = dates.index(date_kst)
    if idx < 1:
        return None, "insufficient_data"
    close = float(by_date[date_kst].get("close") or 0)
    prev = float(by_date[dates[idx - 1]].get("close") or 0)
    if prev <= 0:
        return None, "insufficient_data"
    ret = (close - prev) / prev
    if ret > 0.001:
        return ret, "up"
    if ret < -0.001:
        return ret, "down"
    return ret, "flat"


def _btc_spot_price() -> Optional[float]:
    try:
        import yfinance as yf

        t = yf.Ticker("BTC-USD")
        hist = t.history(period="1d", interval="1h")
        if hist is None or hist.empty:
            hist = t.history(period="5d")
        if hist is None or hist.empty:
            return None
        return float(hist["Close"].iloc[-1])
    except Exception:
        return None


def fetch_market_seal() -> Dict[str, Any]:
    """Prices at morning briefing seal (best-effort)."""
    from scripts.commander_market_session_calendar_v1 import (  # noqa: WPS433
        calendar_kst_today,
        krx_session_status,
        nasdaq_prior_session_context,
        parse_calendar_kst,
    )

    cal_str = calendar_kst_today()
    cal_day = parse_calendar_kst(cal_str)
    krx = krx_session_status(cal_day)
    nas = nasdaq_prior_session_context(cal_day)

    if krx.get("trading_today"):
        kospi_ret, kospi_dir = _daily_return(KOSPI_CSV, cal_str)
    else:
        kospi_ret, kospi_dir = None, "market_closed"

    btc_spot = _btc_spot_price()
    return {
        "sealed_at_kst": datetime.now(KST).strftime("%Y-%m-%d %H:%M KST"),
        "calendar_kst": cal_str,
        "krx_session": krx,
        "session_banner_ko": (
            f"코스피 {krx['label_ko']}"
            + (
                f" · 나스닥 prior {nas['session_date']} ({nas.get('direction', '—')})"
                if nas.get("session_date")
                else ""
            )
        ),
        "kospi": {
            "direction": kospi_dir,
            "return_pct": _pct(kospi_ret),
            "trading_today": krx.get("trading_today"),
            "status_ko": krx.get("label_ko"),
        },
        "btc_usd": {"price": btc_spot},
        "nasdaq_prior_session": {
            "session_date": nas.get("session_date"),
            "direction": nas.get("direction"),
            "return_pct": nas.get("return_pct"),
            "note": nas.get("note_ko"),
        },
    }


def _pct(ret: Optional[float]) -> Optional[float]:
    if ret is None:
        return None
    return round(ret * 100, 4)


def _latest_nasdaq_completed_daily() -> Tuple[Optional[float], str]:
    if not NASDAQ_CSV.is_file():
        return None, "insufficient_data"
    rows = _load_rows(NASDAQ_CSV)
    if len(rows) < 2:
        return None, "insufficient_data"
    last = rows[-1]
    prev = rows[-2]
    d = str(last.get("date") or "")[:10]
    return _daily_return(NASDAQ_CSV, d)


def build_evening_asset_panel(
    calendar_kst: str,
    *,
    morning_seal: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    from scripts.commander_market_session_calendar_v1 import (  # noqa: WPS433
        krx_session_status,
        parse_calendar_kst,
    )

    if krx_session_status(parse_calendar_kst(calendar_kst)).get("trading_today"):
        k_ret, k_dir = _daily_return(KOSPI_CSV, calendar_kst)
    else:
        k_ret, k_dir = None, "market_closed"
    seal = morning_seal or {}
    btc_seal_price = ((seal.get("btc_usd") or {}).get("price"))
    btc_now = _btc_spot_price()
    btc_ret, btc_dir = None, "insufficient_data"
    if btc_seal_price and btc_now and btc_seal_price > 0:
        btc_ret = (btc_now - btc_seal_price) / btc_seal_price
        if btc_ret > 0.001:
            btc_dir = "up"
        elif btc_ret < -0.001:
            btc_dir = "down"
        else:
            btc_dir = "flat"

    return {
        "calendar_kst": calendar_kst,
        "kospi": {
            "window": "09:00-15:30_daily_close",
            "direction": k_dir,
            "return_pct": _pct(k_ret),
        },
        "btc": {
            "window": "08:10-20:30_snapshot",
            "direction": btc_dir,
            "return_pct": _pct(btc_ret),
            "seal_price": btc_seal_price,
            "evening_price": btc_now,
        },
        "nasdaq": {
            "window": "pending_until_morning_0750",
            "direction": "pending_until_morning",
            "return_pct": None,
            "note": "US cash session not closed at 20:30 KST — score at next 07:50 preflight",
        },
    }


def score_prediction_multi_asset(
    pred: Dict[str, Any],
    *,
    assets: Dict[str, Any],
) -> Dict[str, Any]:
    """Route prediction to asset-specific direction."""
    against = pred.get("score_against") or []
    k_dir = (assets.get("kospi") or {}).get("direction") or "insufficient_data"
    b_dir = (assets.get("btc") or {}).get("direction") or "insufficient_data"
    n_st = (assets.get("nasdaq") or {}).get("direction") or "pending_until_morning"

    against_s = [str(a) for a in against]
    if pred.get("prediction_id", "").startswith("btrack:") or any("btc" in a for a in against_s):
        mdir = b_dir if b_dir != "insufficient_data" else k_dir
    elif any("nasdaq" in a for a in against_s):
        return {
            "prediction_id": pred.get("prediction_id"),
            "kind": pred.get("kind"),
            "outcome": "pending_until_morning",
            "note": "NASDAQ 20:30 채점 유예 — 익일 07:50 정산",
            "asset": "nasdaq",
        }
    else:
        mdir = k_dir

    from scripts.score_commander_evening_briefing_v1 import _score_prediction  # noqa: WPS433

    scored = _score_prediction(pred, market_direction=mdir)
    scored["asset"] = "btc" if "btrack" in str(pred.get("prediction_id")) else "kospi"
    if assets.get("btc", {}).get("window"):
        scored["btc_window"] = assets["btc"].get("window")
    return scored
