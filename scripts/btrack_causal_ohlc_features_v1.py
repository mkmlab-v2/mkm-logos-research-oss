#!/usr/bin/env python3
"""Causal session-open features for B-track price lens (no eval-day close lookahead)."""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def load_btc_ohlc_by_date(csv_path: Path) -> dict[str, dict[str, float]]:
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from scripts.logos_shadow_eval_lib import load_kospi_yf_rows

    out: dict[str, dict[str, float]] = {}
    for r in load_kospi_yf_rows(csv_path):
        try:
            d = str(r["date"])[:10]
            out[d] = {
                "open": float(r["open"]),
                "high": float(r["high"]),
                "low": float(r["low"]),
                "close": float(r["close"]),
            }
        except (TypeError, ValueError, KeyError):
            continue
    return out


def overnight_return_at_eval(ohlc_by_date: dict[str, dict[str, float]], eval_date: str) -> float | None:
    """(open[eval_date] - close[prev]) / close[prev] — known at eval-day open."""
    ed = str(eval_date)[:10]
    if ed not in ohlc_by_date:
        return None
    prev_dates = sorted(d for d in ohlc_by_date if d < ed)
    if not prev_dates:
        return None
    prev = prev_dates[-1]
    c0 = ohlc_by_date[prev]["close"]
    o1 = ohlc_by_date[ed]["open"]
    if c0 == 0:
        return None
    return (o1 - c0) / c0


def macro_lens_bear(macro_score: float, *, threshold: float = 0.0) -> bool:
    return macro_score < -threshold


def prior_range_position_at_eval(
    ohlc_by_date: dict[str, dict[str, float]], eval_date: str
) -> float | None:
    """(open[eval] - low[prev]) / (high[prev] - low[prev]); causal at eval-day open."""
    ed = str(eval_date)[:10]
    if ed not in ohlc_by_date:
        return None
    prev_dates = sorted(d for d in ohlc_by_date if d < ed)
    if not prev_dates:
        return None
    prev = prev_dates[-1]
    bar_prev = ohlc_by_date[prev]
    bar_eval = ohlc_by_date[ed]
    hi, lo = bar_prev["high"], bar_prev["low"]
    span = hi - lo
    if span <= 0:
        return None
    pos = (bar_eval["open"] - lo) / span
    return max(0.0, min(1.0, pos))


def realized_vol_5d_at_eval(
    closes: dict[str, float],
    eval_date: str,
    *,
    window: int = 5,
) -> float | None:
    """Sample stdev of daily returns on dates strictly before eval_date (causal)."""
    ed = str(eval_date)[:10]
    dates = sorted(d for d in closes if d < ed)
    if len(dates) < 2:
        return None
    rets: list[float] = []
    for i in range(1, len(dates)):
        c0, c1 = closes[dates[i - 1]], closes[dates[i]]
        if c0 == 0:
            continue
        rets.append((c1 - c0) / c0)
    tail = rets[-max(2, int(window)) :]
    if len(tail) < 2:
        return None
    mean = sum(tail) / len(tail)
    var = sum((x - mean) ** 2 for x in tail) / len(tail)
    return var**0.5


def vol_regime_high(
    realized_vol_5d: float | None,
    *,
    threshold: float = 0.03,
) -> bool:
    if realized_vol_5d is None:
        return False
    return float(realized_vol_5d) >= float(threshold)


def last_daily_return_at_eval(closes: dict[str, float], eval_date: str) -> float | None:
    """Return on the last completed session strictly before eval_date."""
    ed = str(eval_date)[:10]
    dates = sorted(d for d in closes if d < ed)
    if len(dates) < 2:
        return None
    d0, d1 = dates[-2], dates[-1]
    c0, c1 = closes[d0], closes[d1]
    if c0 == 0:
        return None
    return (c1 - c0) / c0


def actual_direction_at_eval(
    closes: dict[str, float],
    eval_date: str,
    *,
    neutral_bps: float = 5.0,
) -> str | None:
    """Causal eval-day return sign (matches score builder neutral band)."""
    ed = str(eval_date)[:10]
    if ed not in closes:
        return None
    dates = sorted(d for d in closes if d <= ed)
    if len(dates) < 2:
        return None
    idx = dates.index(ed)
    if idx < 1:
        return None
    prev = dates[idx - 1]
    c0, c1 = closes[prev], closes[ed]
    if c0 == 0:
        return None
    ret = (c1 - c0) / c0
    thr = neutral_bps / 10000.0
    if abs(ret) <= thr:
        return "neutral"
    return "bull" if ret > 0 else "bear"


def drawdown_20d_at_eval(
    closes: dict[str, float],
    eval_date: str,
    *,
    window: int = 20,
) -> float | None:
    """(last completed close / peak_N) - 1 using dates strictly before eval_date."""
    ed = str(eval_date)[:10]
    dates = sorted(d for d in closes if d < ed)
    if len(dates) < 2:
        return None
    tail = dates[-max(2, int(window)) :]
    peak = max(closes[d] for d in tail)
    last = closes[tail[-1]]
    if peak == 0:
        return None
    return last / peak - 1.0


def build_causal_feature_map(
    ohlc_by_date: dict[str, dict[str, float]],
    *,
    vol_threshold: float = 0.03,
) -> dict[str, dict[str, float | bool]]:
    """Per-date causal feature dict for RQ-024/031 and field-regime OHLCV proxy."""
    closes = {d: float(bar["close"]) for d, bar in ohlc_by_date.items()}
    out: dict[str, dict[str, float | bool]] = {}
    for ed in sorted(ohlc_by_date):
        vol5 = realized_vol_5d_at_eval(closes, ed)
        feat: dict[str, float | bool] = {
            "overnight_return": overnight_return_at_eval(ohlc_by_date, ed) or 0.0,
            "prior_range_position": prior_range_position_at_eval(ohlc_by_date, ed) or 0.5,
            "drawdown_20d": drawdown_20d_at_eval(closes, ed) or 0.0,
            "realized_vol_5d": vol5 or 0.0,
            "last_daily_return": last_daily_return_at_eval(closes, ed) or 0.0,
            "vol_regime_high": vol_regime_high(vol5, threshold=vol_threshold),
        }
        out[ed] = feat
    return out
