#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Shared helpers for B-track envelope + SMCT hypo backtests [HYPO][research_only]."""
from __future__ import annotations

import math
from pathlib import Path
from typing import Any

from scripts.logos_shadow_eval_lib import load_kospi_yf_rows

DEFAULT_KOSPI_CSV = Path("research/market_data/kospi_daily_external_yf.csv")
DEFAULT_NEUTRAL_BPS = 2.0
SUBSET_LEGACY_LIGHT_MEDIUM = "legacy_light_medium"
SUBSET_ENVELOPE_TREND_GATE_V1 = "envelope_trend_gate_v1"


def envelope_trend_gate_v1(
    *,
    sma120_slope: float | None,
    drawdown_from_60d_high: float | None,
) -> bool:
    """TA-aligned allow: 120d uptrend and not deep knife (>15% off 60d high)."""
    if sma120_slope is None or sma120_slope <= 0:
        return False
    if drawdown_from_60d_high is not None and drawdown_from_60d_high <= -0.15:
        return False
    return True


def direction_from_return(ret: float, neutral_bps: float = DEFAULT_NEUTRAL_BPS) -> str:
    thr = neutral_bps / 10000.0
    if ret > thr:
        return "bull"
    if ret < -thr:
        return "bear"
    return "neutral"


def compute_rsi(closes: list[float], period: int = 14) -> float | None:
    if len(closes) < period + 1:
        return None
    gains = losses = 0.0
    for i in range(-period, 0):
        delta = closes[i] - closes[i - 1]
        if delta >= 0:
            gains += delta
        else:
            losses -= delta
    if losses == 0:
        return 100.0
    rs = gains / losses
    return 100.0 - (100.0 / (1.0 + rs))


def sma(values: list[float], window: int) -> float | None:
    if len(values) < window:
        return None
    return sum(values[-window:]) / window


def slope_pct(series: list[float | None], lookback: int = 5) -> float | None:
    if len(series) <= lookback:
        return None
    cur = series[-1]
    prev = series[-1 - lookback]
    if cur is None or prev is None or prev == 0:
        return None
    return (cur - prev) / abs(prev)


def build_daily_features(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """One row per trading day with indicators and SMCT stage."""
    out: list[dict[str, Any]] = []
    closes: list[float] = []
    volumes: list[float] = []
    sma60_hist: list[float | None] = []
    sma120_hist: list[float | None] = []

    for row in rows:
        dk = str(row["date"])[:10]
        close = float(row["close"])
        volume = float(row.get("volume") or 0.0)
        closes.append(close)
        volumes.append(volume)

        sma60_v = sma(closes, 60)
        sma120_v = sma(closes, 120)
        sma60_hist.append(sma60_v)
        sma120_hist.append(sma120_v)

        rsi = compute_rsi(closes, 14)
        vol_slice = volumes[-20:]
        vol_mean = sum(vol_slice) / len(vol_slice) if vol_slice else None
        vol_std = (
            math.sqrt(sum((v - vol_mean) ** 2 for v in vol_slice) / len(vol_slice))
            if vol_slice and vol_mean is not None and len(vol_slice) > 1
            else None
        )
        vol_z = (volume - vol_mean) / vol_std if vol_mean is not None and vol_std and vol_std > 0 else None

        hi60 = max(closes[-60:]) if len(closes) >= 60 else None
        dd60 = (close - hi60) / hi60 if hi60 and hi60 > 0 else None

        sma60_slope = slope_pct(sma60_hist, 5)
        sma120_slope = slope_pct(sma120_hist, 5)

        stage = classify_smct_stage(
            rsi=rsi,
            vol_z=vol_z,
            sma60_slope=sma60_slope,
            sma120_slope=sma120_slope,
            drawdown_from_60d_high=dd60,
        )
        subset_allow = stage in ("light", "medium") and (sma120_slope or 0) > 0
        trend_gate = envelope_trend_gate_v1(
            sma120_slope=sma120_slope,
            drawdown_from_60d_high=dd60,
        )

        out.append(
            {
                "date": dk,
                "close": round(close, 4),
                "volume": round(volume, 2),
                "sma60": round(sma60_v, 4) if sma60_v is not None else None,
                "sma120": round(sma120_v, 4) if sma120_v is not None else None,
                "sma60_slope": round(sma60_slope, 6) if sma60_slope is not None else None,
                "sma120_slope": round(sma120_slope, 6) if sma120_slope is not None else None,
                "rsi_14": round(rsi, 4) if rsi is not None else None,
                "vol_zscore_20d": round(vol_z, 4) if vol_z is not None else None,
                "drawdown_from_60d_high": round(dd60, 6) if dd60 is not None else None,
                "smct_stage": stage,
                "smct_subset_allow_envelope": subset_allow,
                "envelope_trend_gate_v1": trend_gate,
            }
        )
    return out


def classify_smct_stage(
    *,
    rsi: float | None,
    vol_z: float | None,
    sma60_slope: float | None,
    sma120_slope: float | None,
    drawdown_from_60d_high: float | None,
) -> str:
    if sma120_slope is not None and sma120_slope <= 0:
        return "severe"
    if drawdown_from_60d_high is not None and drawdown_from_60d_high <= -0.15:
        return "severe"
    if rsi is not None and rsi >= 75 and vol_z is not None and vol_z >= 1.5:
        return "medium"
    if (
        rsi is not None
        and 65 <= rsi < 75
        and vol_z is not None
        and 0.5 <= vol_z < 1.5
        and sma60_slope is not None
        and sma60_slope > 0
    ):
        return "light"
    return "none"


def envelope_signal(arm_id: str, feat: dict[str, Any], *, band_pct: float = 0.06) -> bool:
    close = feat.get("close")
    sma60 = feat.get("sma60")
    sma120 = feat.get("sma120")
    if close is None or sma60 is None or sma60 <= 0:
        return False
    if arm_id == "arm_a_naked_60d_6":
        return float(close) <= float(sma60) * (1.0 - band_pct)
    if arm_id == "arm_b_trend_filtered":
        if (feat.get("sma60_slope") or 0) <= 0:
            return False
        if (feat.get("sma120_slope") or 0) <= 0:
            return False
        return float(close) <= float(sma60) * (1.0 - band_pct)
    if arm_id == "arm_c_120d_up_60d_pullback":
        if (feat.get("sma120_slope") or 0) <= 0 or sma120 is None:
            return False
        if float(close) < float(sma120):
            return False
        lo = float(sma60) * 0.98
        hi = float(sma60) * 1.02
        return lo <= float(close) <= hi
    raise ValueError(f"unknown arm_id: {arm_id}")


def _subset_allows(feat: dict[str, Any], subset_mode: str | None) -> bool:
    if not subset_mode:
        return True
    if subset_mode == SUBSET_LEGACY_LIGHT_MEDIUM:
        return bool(feat.get("smct_subset_allow_envelope"))
    if subset_mode == SUBSET_ENVELOPE_TREND_GATE_V1:
        return bool(feat.get("envelope_trend_gate_v1"))
    raise ValueError(f"unknown subset_mode: {subset_mode}")


def eval_entry_directional_hits(
    features_by_date: dict[str, dict[str, Any]],
    eval_dates: list[str],
    *,
    arm_id: str,
    neutral_bps: float = DEFAULT_NEUTRAL_BPS,
    subset_only: bool = False,
    subset_mode: str | None = None,
    band_pct: float = 0.06,
    signal_sample_limit: int | None = 12,
) -> dict[str, Any]:
    if subset_mode is not None:
        pass
    elif subset_only:
        subset_mode = SUBSET_LEGACY_LIGHT_MEDIUM
    else:
        subset_mode = None

    hits = n_dir = 0
    n_signals = 0
    n_gated_out = 0
    per_signal: list[dict[str, Any]] = []
    sorted_all = sorted(features_by_date.keys())

    for dk in eval_dates:
        feat = features_by_date.get(dk)
        if not feat:
            continue
        if subset_mode and not _subset_allows(feat, subset_mode):
            if envelope_signal(arm_id, feat, band_pct=band_pct):
                n_gated_out += 1
            continue
        if not envelope_signal(arm_id, feat, band_pct=band_pct):
            continue
        idx = sorted_all.index(dk) if dk in sorted_all else -1
        if idx < 0 or idx + 1 >= len(sorted_all):
            continue
        next_dk = sorted_all[idx + 1]
        if next_dk not in features_by_date:
            continue
        c0 = float(feat["close"])
        c1 = float(features_by_date[next_dk]["close"])
        if c0 == 0:
            continue
        ret = (c1 - c0) / c0
        actual = direction_from_return(ret, neutral_bps)
        n_signals += 1
        if actual == "neutral":
            continue
        n_dir += 1
        hit = actual == "bull"
        if hit:
            hits += 1
        per_signal.append(
            {
                "signal_date": dk,
                "next_date": next_dk,
                "actual_direction": actual,
                "hit": hit,
                "smct_stage": feat.get("smct_stage"),
                "envelope_trend_gate_v1": feat.get("envelope_trend_gate_v1"),
            }
        )

    rate = round(hits / n_dir, 6) if n_dir else None
    coverage = round(n_signals / len(eval_dates), 6) if eval_dates else None
    return {
        "directional_hit_rate_raw": rate,
        "n_eval_days": len(eval_dates),
        "n_entry_signals": n_signals,
        "n_directional_next_day": n_dir,
        "directional_hits": hits,
        "signal_coverage": coverage,
        "subset_mode": subset_mode,
        "n_signals_gated_out_by_subset": n_gated_out if subset_mode else 0,
        "per_signal_sample": per_signal if signal_sample_limit is None else per_signal[:signal_sample_limit],
    }


def summarize_severe_knife_signals(per_signal: list[dict[str, Any]]) -> dict[str, Any]:
    """Break down envelope entry signals where SMCT stage is severe (knife-catch risk)."""
    total = len(per_signal)
    severe = [s for s in per_signal if s.get("smct_stage") == "severe"]
    n_severe = len(severe)
    n_dir = sum(1 for s in severe if s.get("actual_direction") in ("bull", "bear"))
    n_bear = sum(1 for s in severe if s.get("actual_direction") == "bear")
    n_bull_hit = sum(1 for s in severe if s.get("hit") is True)
    bear_rows = [
        {
            "signal_date": s.get("signal_date"),
            "next_date": s.get("next_date"),
            "actual_direction": s.get("actual_direction"),
            "envelope_trend_gate_v1": s.get("envelope_trend_gate_v1"),
        }
        for s in severe
        if s.get("actual_direction") == "bear"
    ]
    return {
        "n_signals_total": total,
        "n_severe": n_severe,
        "severe_fraction_of_signals": round(n_severe / total, 6) if total else None,
        "n_severe_directional_next_day": n_dir,
        "n_severe_bear_next_day": n_bear,
        "severe_bear_rate": round(n_bear / n_dir, 6) if n_dir else None,
        "n_severe_bull_hit": n_bull_hit,
        "severe_directional_hit_rate_raw": round(n_bull_hit / n_dir, 6) if n_dir else None,
        "bear_next_day_rows": bear_rows,
    }


def load_kospi_features(csv_path: Path) -> dict[str, dict[str, Any]]:
    rows = load_kospi_yf_rows(csv_path)
    feats = build_daily_features(rows)
    return {str(f["date"]): f for f in feats}


def load_features_from_rows(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    feats = build_daily_features(rows)
    return {str(f["date"]): f for f in feats}


def download_yf_rows(symbol: str, *, start: str = "2020-01-01", end: str = "") -> list[dict[str, Any]]:
    """Download daily OHLCV via yfinance into load_kospi_yf_rows-compatible row dicts."""
    import tempfile

    try:
        import pandas as pd
        import yfinance as yf
    except ImportError as exc:
        raise RuntimeError("pip install pandas yfinance") from exc

    kwargs: dict = {"interval": "1d", "auto_adjust": False, "progress": False}
    if end.strip():
        df = yf.download(symbol, start=start.strip(), end=end.strip(), **kwargs)
    else:
        df = yf.download(symbol, start=start.strip(), **kwargs)
    if df is None or df.empty:
        return []
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [str(c[0]) for c in df.columns]
    df = df.reset_index()
    rename = {c: str(c).strip() for c in df.columns}
    df = df.rename(columns=rename)
    if "Date" not in df.columns:
        return []
    out_cols = ["Date", "Open", "High", "Low", "Close", "Volume"]
    for c in out_cols:
        if c not in df.columns:
            return []
    out = df[out_cols].copy()
    out["Date"] = out["Date"].astype(str).str.slice(0, 10)
    close_num = pd.to_numeric(out["Close"], errors="coerce")
    out = out[close_num.notna() & (close_num > 0)].copy()
    tmp = Path(tempfile.gettempdir()) / f"envelope_hypo_{symbol.replace('^', '').replace('.', '_')}.csv"
    out.to_csv(tmp, index=False)
    return load_kospi_yf_rows(tmp)


def aggregate_signal_metrics(per_symbol: list[dict[str, Any]]) -> dict[str, Any]:
    hits = n_dir = n_signals = 0
    n_eval_days = 0
    for block in per_symbol:
        m = block.get("metrics") or {}
        hits += int(m.get("directional_hits") or 0)
        n_dir += int(m.get("n_directional_next_day") or 0)
        n_signals += int(m.get("n_entry_signals") or 0)
        n_eval_days = max(n_eval_days, int(m.get("n_eval_days") or 0))
    rate = round(hits / n_dir, 6) if n_dir else None
    return {
        "directional_hit_rate_raw": rate,
        "n_eval_days": n_eval_days,
        "n_entry_signals": n_signals,
        "n_directional_next_day": n_dir,
        "directional_hits": hits,
        "signal_coverage": round(n_signals / n_eval_days, 6) if n_eval_days else None,
        "n_symbols": len(per_symbol),
    }


def kospi_metrics_from_frozen_score(score_path: Path) -> dict[str, Any]:
    import json

    doc = json.loads(score_path.read_text(encoding="utf-8"))
    rows = [r for r in (doc.get("rows") or []) if isinstance(r, dict) and r.get("instrument") == "kospi"]
    hits = n = n_dir = dir_hits = 0
    for r in rows:
        pred = str(r.get("predicted_direction") or "").lower()
        act = str(r.get("actual_direction") or "").lower()
        if not pred or not act:
            continue
        n += 1
        if pred == act:
            hits += 1
        if pred != "neutral":
            n_dir += 1
            if pred == act:
                dir_hits += 1
    return {
        "directional_hit_rate_raw": round(hits / n, 6) if n else None,
        "directional_hit_rate_on_directional_calls": round(dir_hits / n_dir, 6) if n_dir else None,
        "n_evaluated": n,
        "n_directional_calls": n_dir,
        "neutral_bps": doc.get("neutral_bps"),
        "eval_date_to": doc.get("eval_date"),
        "oper_score_generated_at_utc": doc.get("generated_at_utc"),
        "note": "read-only from frozen SSOT; not overwritten",
    }
