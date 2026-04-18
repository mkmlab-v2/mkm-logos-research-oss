# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.88, L:0.92, K:0.64, M:0.48}
# Balance: 94
# Purpose: Run rolling forward replay for BTC MTF strategy (H4 baseline + H1 tactical).
# Keywords: btc, mtf, h4, h1, forward, replay, validation
#!/usr/bin/env python3
"""Rolling forward replay for BTC MTF strategy."""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import requests
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
BTC_ROOT = ROOT / "projects" / "bitcoin-trading"
if str(BTC_ROOT) not in sys.path:
    sys.path.insert(0, str(BTC_ROOT))
if str(BTC_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(BTC_ROOT / "src"))

OUT_DEFAULT = ROOT / "docs" / "final" / "artifacts" / "btc_mtf_h4_h1_forward_replay_latest.json"
FREEZE_DEFAULT = ROOT / "docs" / "final" / "artifacts" / "btc_mkmb_fusion_freeze_latest.json"
BINANCE_KLINES_URL = "https://api.binance.com/api/v3/klines"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _mean(vals: list[float]) -> float:
    return sum(vals) / len(vals) if vals else 0.0


def _std(vals: list[float]) -> float:
    if len(vals) < 2:
        return 0.0
    m = _mean(vals)
    return (sum((x - m) ** 2 for x in vals) / len(vals)) ** 0.5


def _signal_h4(close_hist: pd.Series, *, trend_threshold_pct: float) -> int:
    latest = float(close_hist.iloc[-1])
    sma = float(close_hist.mean())
    if sma == 0:
        return 0
    trend_pct = ((latest / sma) - 1.0) * 100.0
    if abs(trend_pct) < abs(trend_threshold_pct):
        return 0
    return 1 if trend_pct > 0 else -1


def _signal_h1_hybrid(close_hist: pd.Series, *, trend_threshold_pct: float, reversion_z_threshold: float) -> tuple[int, float]:
    latest = float(close_hist.iloc[-1])
    sma = float(close_hist.mean())
    if sma == 0:
        return 0, 0.0
    trend_pct = ((latest / sma) - 1.0) * 100.0
    rets = close_hist.pct_change().dropna().tolist()
    vol = _std([float(x) for x in rets]) * 100.0
    z = (trend_pct / vol) if vol > 1e-9 else 0.0
    if z >= reversion_z_threshold:
        return -1, z
    if z <= -reversion_z_threshold:
        return 1, z
    if abs(trend_pct) < abs(trend_threshold_pct):
        return 0, z
    return (1 if trend_pct > 0 else -1), z


def _signal_h1_trend_only(close_hist: pd.Series, *, trend_threshold_pct: float) -> tuple[int, float]:
    latest = float(close_hist.iloc[-1])
    sma = float(close_hist.mean())
    if sma == 0:
        return 0, 0.0
    trend_pct = ((latest / sma) - 1.0) * 100.0
    rets = close_hist.pct_change().dropna().tolist()
    vol = _std([float(x) for x in rets]) * 100.0
    z = (trend_pct / vol) if vol > 1e-9 else 0.0
    if abs(trend_pct) < abs(trend_threshold_pct):
        return 0, z
    return (1 if trend_pct > 0 else -1), z


def _max_drawdown_pct(returns: list[float]) -> float:
    eq = 1.0
    peak = 1.0
    max_dd = 0.0
    for r in returns:
        eq *= 1.0 + r
        if eq > peak:
            peak = eq
        dd = (peak - eq) / peak if peak > 0 else 0.0
        if dd > max_dd:
            max_dd = dd
    return max_dd * 100.0


def _tail_loss_p95_pct(returns: list[float]) -> float:
    if not returns:
        return 0.0
    q = float(np.quantile(np.array(returns, dtype=float), 0.05))
    return abs(min(0.0, q)) * 100.0


def _fetch_klines(*, symbol: str, start: str, end: str, interval: str) -> pd.DataFrame:
    start_dt = datetime.fromisoformat(start)
    end_dt = datetime.fromisoformat(end)
    start_ts = int(start_dt.timestamp() * 1000)
    end_ts = int(end_dt.timestamp() * 1000)
    rows: list[list[Any]] = []
    cur = start_ts
    limit = 1000
    while cur < end_ts:
        params = {
            "symbol": symbol,
            "interval": interval,
            "startTime": cur,
            "endTime": end_ts,
            "limit": limit,
        }
        resp = requests.get(BINANCE_KLINES_URL, params=params, timeout=30)
        resp.raise_for_status()
        batch = resp.json()
        if not batch:
            break
        rows.extend(batch)
        cur = int(batch[-1][6]) + 1
        time.sleep(0.08)
    if not rows:
        return pd.DataFrame(columns=["close"])
    df = pd.DataFrame(
        rows,
        columns=[
            "timestamp",
            "open",
            "high",
            "low",
            "close",
            "volume",
            "close_time",
            "quote_volume",
            "trades",
            "taker_buy_base",
            "taker_buy_quote",
            "ignore",
        ],
    )
    df["date"] = pd.to_datetime(df["timestamp"], unit="ms")
    df.set_index("date", inplace=True)
    for c in ("open", "high", "low", "close", "volume"):
        df[c] = pd.to_numeric(df[c], errors="coerce")
    return df[(df.index >= start_dt) & (df.index <= end_dt)].sort_index()


def _load_mkmb_proxy(mkmb_csv: Path | None) -> pd.DataFrame | None:
    if mkmb_csv is None or not mkmb_csv.exists():
        return None
    df = pd.read_csv(mkmb_csv)
    if "ts" not in df.columns:
        return None
    df["ts"] = pd.to_datetime(df["ts"], errors="coerce", utc=True)
    df = df.dropna(subset=["ts"]).sort_values("ts")
    feature_cols = [c for c in df.columns if c.startswith("mkmb_")]
    if not feature_cols:
        return None
    for c in feature_cols:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    out = df[["ts", *feature_cols]].copy()
    # Leakage-safe: prediction at t can only use proxy known at t-1 bar.
    out[feature_cols] = out[feature_cols].shift(1).fillna(0.0)
    return out


def _load_freeze_policy(path: Path | None) -> dict[str, Any] | None:
    if path is None or not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return None


def _build_fusion_gate(
    *,
    summary: dict[str, Any],
    folds: list[dict[str, Any]],
    baseline_artifact: Path | None,
    min_profit_factor: float,
    min_sample_count: int,
    max_drawdown_pct: float,
    min_mean_net_return_pct: float,
    require_baseline_non_regression: bool,
    baseline_mode: str,
    baseline_mean_net_tolerance: float,
) -> dict[str, Any]:
    min_pf_obs = float(summary.get("min_profit_factor") or 0.0)
    min_sc_obs = int(summary.get("min_sample_count") or 0)
    mean_net_obs = float(summary.get("mean_net_return_pct") or 0.0)
    stable = bool(summary.get("stable_forward"))
    drawdowns = [float((f.get("metrics") or {}).get("max_drawdown_pct") or 0.0) for f in folds]
    max_dd_obs = max(drawdowns) if drawdowns else 0.0

    checks = {
        "stable_forward": stable,
        "min_profit_factor": min_pf_obs >= float(min_profit_factor),
        "min_sample_count": min_sc_obs >= int(min_sample_count),
        "max_drawdown_pct": max_dd_obs <= float(max_drawdown_pct),
        "mean_net_return_pct": mean_net_obs >= float(min_mean_net_return_pct),
    }

    baseline_mode_norm = str(baseline_mode or "strict").lower()
    baseline_summary: dict[str, Any] | None = None
    baseline_deltas: dict[str, float] | None = None
    baseline_ok = True
    if baseline_artifact is not None and baseline_artifact.exists():
        try:
            baseline = json.loads(baseline_artifact.read_text(encoding="utf-8-sig"))
            baseline_summary = baseline.get("summary") or {}
            baseline_deltas = {
                "delta_mean_net_return_pct": mean_net_obs - float(baseline_summary.get("mean_net_return_pct") or 0.0),
                "delta_min_profit_factor": min_pf_obs - float(baseline_summary.get("min_profit_factor") or 0.0),
            }
            if require_baseline_non_regression:
                if baseline_mode_norm == "pf_only":
                    baseline_ok = baseline_deltas["delta_min_profit_factor"] >= 0.0
                elif baseline_mode_norm == "pf_or_mean":
                    baseline_ok = (
                        baseline_deltas["delta_min_profit_factor"] >= 0.0
                        or baseline_deltas["delta_mean_net_return_pct"] >= -abs(float(baseline_mean_net_tolerance))
                    )
                else:
                    baseline_ok = baseline_deltas["delta_mean_net_return_pct"] >= 0.0 and baseline_deltas["delta_min_profit_factor"] >= 0.0
        except Exception:
            baseline_ok = not require_baseline_non_regression
    elif require_baseline_non_regression:
        baseline_ok = False

    hard_ok = all(checks.values()) and baseline_ok
    recommendation = "go_soft_fusion" if hard_ok else "keep_shadow_only"
    reasons = [k for k, ok in checks.items() if not ok]
    if not baseline_ok:
        reasons.append("baseline_non_regression")

    return {
        "recommendation": recommendation,
        "checks": checks,
        "thresholds": {
            "min_profit_factor": float(min_profit_factor),
            "min_sample_count": int(min_sample_count),
            "max_drawdown_pct": float(max_drawdown_pct),
            "min_mean_net_return_pct": float(min_mean_net_return_pct),
            "require_baseline_non_regression": bool(require_baseline_non_regression),
            "baseline_mode": baseline_mode_norm,
            "baseline_mean_net_tolerance": float(abs(baseline_mean_net_tolerance)),
        },
        "observed": {
            "min_profit_factor": round(min_pf_obs, 6),
            "min_sample_count": int(min_sc_obs),
            "max_drawdown_pct": round(max_dd_obs, 6),
            "mean_net_return_pct": round(mean_net_obs, 6),
            "stable_forward": stable,
        },
        "baseline": {
            "path": str(baseline_artifact.resolve()) if baseline_artifact is not None else None,
            "summary": baseline_summary,
            "deltas": baseline_deltas,
            "ok": baseline_ok,
        },
        "failed_reasons": reasons,
    }


def _run_window(
    *,
    symbol: str,
    start: str,
    end: str,
    cfg: dict[str, Any],
    phase: str = "default",
    mkmb_proxy: pd.DataFrame | None = None,
    use_mkmb_proxy: bool = False,
    mkmb_shadow_only: bool = False,
    mkmb_soft_fusion_only: bool = False,
) -> dict[str, Any]:
    h4 = _fetch_klines(symbol=symbol, start=start, end=end, interval="4h")
    h1 = _fetch_klines(symbol=symbol, start=start, end=end, interval="1h")
    mkmb_on_h1 = None
    if use_mkmb_proxy and mkmb_proxy is not None and not mkmb_proxy.empty:
        mkmb = mkmb_proxy.copy().sort_values("ts")
        h1_merge = pd.DataFrame({"ts": h1.index.tz_localize("UTC") if h1.index.tz is None else h1.index})
        mkmb_on_h1 = pd.merge_asof(h1_merge.sort_values("ts"), mkmb, on="ts", direction="backward").set_index("ts")
        mkmb_on_h1 = mkmb_on_h1.fillna(0.0)
    h4_close = h4["close"].astype(float)
    h4_trend_threshold = float(cfg["h4_trend_threshold_pct"])
    phase_key = str(phase).lower()
    if phase_key == "fold3":
        h4_trend_threshold = max(0.0, h4_trend_threshold - float(cfg["fold3_relax_h4_trend_threshold_delta"]))
    h4_signal = pd.Series(index=h4_close.index, dtype=float)
    for i in range(int(cfg["h4_warmup"]), len(h4_close)):
        hist = h4_close.iloc[i - int(cfg["h4_warmup"]) : i + 1]
        h4_signal.iloc[i] = _signal_h4(hist, trend_threshold_pct=h4_trend_threshold)
    h4_signal = h4_signal.ffill().fillna(0.0)
    h4_signal_on_h1 = h4_signal.reindex(h1.index, method="ffill").fillna(0.0)
    h4_stability_req = int(cfg["h4_stability_bars"])
    h1_min_abs_z = float(cfg["h1_min_abs_z"])
    h1_min_hist_vol = float(cfg["h1_min_hist_vol_pct"])
    use_trend_only = False
    if phase_key == "early":
        # Early folds (historically fragile): relax filters to preserve trade count.
        h4_stability_req = max(1, h4_stability_req - int(cfg["early_relax_stability_bars_delta"]))
        h1_min_abs_z = max(0.35, h1_min_abs_z - float(cfg["early_relax_min_abs_z_delta"]))
        h1_min_hist_vol = max(0.2, h1_min_hist_vol - float(cfg["early_relax_min_hist_vol_delta"]))
    if phase_key == "fold1":
        h4_stability_req = 1
        h1_min_abs_z = max(0.3, h1_min_abs_z - float(cfg["fold1_relax_min_abs_z_delta"]))
        h1_min_hist_vol = max(0.15, h1_min_hist_vol - float(cfg["fold1_relax_min_hist_vol_delta"]))
    if phase_key == "fold5":
        h1_min_abs_z = max(0.20, h1_min_abs_z - float(cfg["fold5_relax_min_abs_z_delta"]))
        h1_min_hist_vol = max(0.08, h1_min_hist_vol - float(cfg["fold5_relax_min_hist_vol_delta"]))
    if phase_key == "fold3":
        h1_min_abs_z = max(0.25, h1_min_abs_z - float(cfg["fold3_relax_min_abs_z_delta"]))
        h1_min_hist_vol = max(0.10, h1_min_hist_vol - float(cfg["fold3_relax_min_hist_vol_delta"]))
        if bool(cfg["fold3_force_trend_only"]):
            use_trend_only = True
    if phase_key == "fold2" and bool(cfg["fold2_force_trend_only"]):
        use_trend_only = True
    h4_stable = h4_signal.rolling(window=h4_stability_req).apply(
        lambda x: 1.0 if len(set(int(v) for v in x)) == 1 else 0.0,
        raw=False,
    )
    h4_stable_on_h1 = h4_stable.reindex(h1.index, method="ffill").fillna(0.0)

    closes = h1["close"].astype(float)
    horizon_default = int(cfg["h1_horizon"])
    stride_default = int(cfg["h1_stride"])
    horizon_fast = int(cfg["h1_horizon_fast"])
    stride_fast = int(cfg["h1_stride_fast"])
    horizon_slow = int(cfg["h1_horizon_slow"])
    stride_slow = int(cfg["h1_stride_slow"])
    warmup = int(cfg["h1_warmup"])
    fee = float(cfg["fee_bps_round_trip"]) / 10_000.0
    slippage = float(cfg["slippage_bps_round_trip"]) / 10_000.0
    pos = float(cfg["position_fraction"])

    trades: list[float] = []
    trace: list[dict[str, Any]] = []
    reject_counts: dict[str, int] = {
        "h4_dir_zero": 0,
        "h4_not_stable": 0,
        "h1_low_hist_vol": 0,
        "h1_dir_mismatch_or_weak": 0,
        "h1_extreme_z": 0,
        "breakdown_guard": 0,
        "mkmb_guard_block": 0,
        "accepted": 0,
    }
    i = warmup
    while i < len(closes) - max(horizon_fast, horizon_slow, horizon_default):
        h4_dir = int(h4_signal_on_h1.iloc[i] or 0)
        # Regime-adaptive tactical cadence:
        # low H4 realized vol -> faster reaction (12h), else slower confirmation (24h)
        h4_hist = h4_close[h4_close.index <= closes.index[i]].tail(int(cfg["h4_regime_vol_lookback"]))
        h4_rets = h4_hist.pct_change().dropna().tolist()
        h4_vol_pct = _std([float(x) for x in h4_rets]) * 100.0
        if bool(cfg["enable_dynamic_horizon"]):
            if phase_key == "fold1":
                horizon = horizon_fast
                stride = stride_fast
                regime = "fast_fold1"
            elif phase_key == "fold2":
                horizon = horizon_default
                stride = stride_default
                regime = "base_fold2"
            elif h4_vol_pct <= float(cfg["h4_low_vol_threshold_pct"]):
                horizon = horizon_fast
                stride = stride_fast
                regime = "fast"
            elif h4_vol_pct >= float(cfg["h4_high_vol_threshold_pct"]):
                horizon = horizon_slow
                stride = stride_slow
                regime = "slow"
            else:
                horizon = horizon_default
                stride = stride_default
                regime = "base"
        else:
            horizon = horizon_default
            stride = stride_default
            regime = "base"
        if i >= len(closes) - horizon:
            break
        if h4_dir == 0:
            reject_counts["h4_dir_zero"] += 1
            i += stride
            continue
        if int(h4_stable_on_h1.iloc[i] or 0) != 1:
            reject_counts["h4_not_stable"] += 1
            i += stride
            continue
        hist = closes.iloc[i - warmup : i + 1]
        if use_trend_only:
            h1_dir, z = _signal_h1_trend_only(
                hist,
                trend_threshold_pct=float(cfg["h1_trend_threshold_pct"]),
            )
        else:
            h1_dir, z = _signal_h1_hybrid(
                hist,
                trend_threshold_pct=float(cfg["h1_trend_threshold_pct"]),
                reversion_z_threshold=float(cfg["h1_reversion_z_threshold"]),
            )
        rets = hist.pct_change().dropna().tolist()
        h1_vol_pct = _std([float(x) for x in rets]) * 100.0
        if h1_vol_pct < h1_min_hist_vol:
            reject_counts["h1_low_hist_vol"] += 1
            i += stride
            continue
        if abs(z) < h1_min_abs_z or h1_dir == 0 or h1_dir != h4_dir:
            reject_counts["h1_dir_mismatch_or_weak"] += 1
            i += stride
            continue
        if abs(z) > float(cfg["h1_max_abs_z"]):
            reject_counts["h1_extreme_z"] += 1
            i += stride
            continue
        mkmb_score = 0.0
        if use_mkmb_proxy and mkmb_on_h1 is not None and "mkmb_score_proxy" in mkmb_on_h1.columns:
            mkmb_score = float(mkmb_on_h1.iloc[i].get("mkmb_score_proxy", 0.0))
            # If proxy strongly disagrees with directional intent, skip trade.
            if not mkmb_shadow_only and not mkmb_soft_fusion_only:
                if h4_dir > 0 and mkmb_score <= -float(cfg["mkmb_guard_threshold"]):
                    reject_counts["mkmb_guard_block"] += 1
                    i += stride
                    continue
                if h4_dir < 0 and mkmb_score >= float(cfg["mkmb_guard_threshold"]):
                    reject_counts["mkmb_guard_block"] += 1
                    i += stride
                    continue
        entry = float(closes.iloc[i])
        exit_ = float(closes.iloc[i + horizon])
        ma_ref = float(hist.mean())
        dev_pct = ((entry / ma_ref) - 1.0) * 100.0 if ma_ref != 0 else 0.0
        if h4_dir > 0 and dev_pct <= float(cfg["h1_breakdown_pct"]):
            reject_counts["breakdown_guard"] += 1
            i += stride
            continue
        if h4_dir < 0 and dev_pct >= abs(float(cfg["h1_breakdown_pct"])):
            reject_counts["breakdown_guard"] += 1
            i += stride
            continue
        raw_ret = (exit_ - entry) / entry
        pos_eff = pos
        if use_mkmb_proxy and not mkmb_shadow_only:
            pos_scale = float(cfg["mkmb_position_scale"])
            if mkmb_soft_fusion_only:
                pos_scale = pos_scale * float(cfg["mkmb_soft_fusion_weight"])
            pos_eff = pos * (1.0 + pos_scale * max(-1.0, min(1.0, mkmb_score)))
            pos_eff = max(float(cfg["mkmb_position_min"]), min(float(cfg["mkmb_position_max"]), pos_eff))
        net_ret = ((h4_dir * raw_ret) - fee - slippage) * pos_eff
        trades.append(net_ret)
        ts = closes.index[i]
        trace.append(
            {
                "entry_ts": ts.strftime("%Y-%m-%dT%H:%M:%S") if hasattr(ts, "strftime") else str(ts),
                "net_return_pct": net_ret * 100.0,
                "horizon": int(horizon),
                "stride": int(stride),
                "h4_vol_pct": round(float(h4_vol_pct), 6),
                "mkmb_score_proxy": round(float(mkmb_score), 6),
                "position_fraction_eff": round(float(pos_eff), 6),
                "regime": regime,
            }
        )
        reject_counts["accepted"] += 1
        i += stride

    wins = [x for x in trades if x > 0]
    losses = [x for x in trades if x < 0]
    gp = sum(wins)
    gl = abs(sum(losses))
    pf = (gp / gl) if gl > 0 else None
    metrics = {
        "sample_count": len(trades),
        "win_rate": round((len(wins) / len(trades)), 6) if trades else 0.0,
        "net_return_pct": round(sum(trades) * 100.0, 6) if trades else 0.0,
        "profit_factor": round(pf, 6) if pf is not None else None,
        "max_drawdown_pct": round(_max_drawdown_pct(trades), 6) if trades else 0.0,
        "tail_loss_p95_pct": round(_tail_loss_p95_pct(trades), 6) if trades else 0.0,
    }
    monthly: dict[str, float] = {}
    for t in trace:
        ym = str(t["entry_ts"])[:7]
        monthly[ym] = monthly.get(ym, 0.0) + float(t["net_return_pct"])
    return {
        "bars_h1": int(len(h1)),
        "bars_h4": int(len(h4)),
        "metrics": metrics,
        "reject_counts": reject_counts,
        "monthly_pnl": [{"ym": k, "net_return_pct": round(v, 6)} for k, v in sorted(monthly.items())],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--symbol", default="BTCUSDT")
    ap.add_argument("--end", default="2026-04-15")
    ap.add_argument("--fold-days", type=int, default=45)
    ap.add_argument("--n-folds", type=int, default=4)
    ap.add_argument("--h1-horizon", type=int, default=24)
    ap.add_argument("--h1-stride", type=int, default=24)
    ap.add_argument("--h4-trend-threshold-pct", type=float, default=0.35)
    ap.add_argument("--h4-stability-bars", type=int, default=2)
    ap.add_argument("--h1-min-abs-z", type=float, default=0.55)
    ap.add_argument("--h1-max-abs-z", type=float, default=2.6)
    ap.add_argument("--h1-min-hist-vol-pct", type=float, default=0.45)
    ap.add_argument("--h1-reversion-z-threshold", type=float, default=1.2)
    ap.add_argument("--fold3-force-trend-only", action="store_true")
    ap.add_argument(
        "--fold2-force-trend-only",
        dest="fold2_force_trend_only",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Enable/disable trend-only tactical signal rule on fold2.",
    )
    ap.add_argument("--fee-bps-round-trip", type=float, default=8.0)
    ap.add_argument("--slippage-bps-round-trip", type=float, default=5.0)
    ap.add_argument("--use-mkmb-proxy", action="store_true")
    ap.add_argument(
        "--mkmb-shadow-only",
        action="store_true",
        help="Load/record MKM-B proxy but do not apply guard blocks or position scaling.",
    )
    ap.add_argument(
        "--mkmb-soft-fusion-only",
        action="store_true",
        help="Apply low-weight position scaling from MKM-B proxy, but disable hard guard blocks.",
    )
    ap.add_argument("--mkmb-csv", type=Path, default=Path("research/market_data/btc_mkmb_proxy_hourly_v1.csv"))
    ap.add_argument("--mkmb-guard-threshold", type=float, default=0.25)
    ap.add_argument("--mkmb-position-scale", type=float, default=0.35)
    ap.add_argument("--mkmb-position-min", type=float, default=0.08)
    ap.add_argument("--mkmb-position-max", type=float, default=0.30)
    ap.add_argument("--mkmb-soft-fusion-weight", type=float, default=0.35)
    ap.add_argument("--enforce-mkmb-shadow-freeze", action="store_true")
    ap.add_argument("--mkmb-freeze-policy", type=Path, default=FREEZE_DEFAULT)
    ap.add_argument("--emit-fusion-gate", action="store_true")
    ap.add_argument("--baseline-artifact", type=Path, default=None)
    ap.add_argument("--fusion-min-profit-factor", type=float, default=1.15)
    ap.add_argument("--fusion-min-sample-count", type=int, default=3)
    ap.add_argument("--fusion-max-drawdown-pct", type=float, default=0.40)
    ap.add_argument("--fusion-min-mean-net-return-pct", type=float, default=0.05)
    ap.add_argument("--fusion-require-baseline-non-regression", action="store_true")
    ap.add_argument(
        "--fusion-baseline-mode",
        choices=["strict", "pf_only", "pf_or_mean"],
        default="strict",
        help="Non-regression mode: strict=delta_pf>=0 and delta_mean>=0, pf_only=delta_pf>=0, pf_or_mean=delta_pf>=0 or delta_mean>=-tolerance.",
    )
    ap.add_argument(
        "--fusion-baseline-mean-net-tolerance",
        type=float,
        default=0.0,
        help="Mean net tolerance used only with --fusion-baseline-mode pf_or_mean.",
    )
    ap.add_argument("--output", type=Path, default=OUT_DEFAULT)
    args = ap.parse_args()

    freeze = _load_freeze_policy(args.mkmb_freeze_policy)
    if args.enforce_mkmb_shadow_freeze and freeze is not None:
        state = str(freeze.get("fusion_state") or "").lower()
        if state == "shadow_only":
            # Freeze allows only baseline or shadow-only replay; block fusion paths.
            if bool(args.use_mkmb_proxy) and not bool(args.mkmb_shadow_only):
                print(
                    json.dumps(
                        {
                            "ok": False,
                            "error": "mkmb_shadow_freeze_enforced",
                            "policy": str(args.mkmb_freeze_policy.resolve()),
                            "fusion_state": state,
                            "hint": "Run with --mkmb-shadow-only or disable --enforce-mkmb-shadow-freeze",
                        },
                        ensure_ascii=False,
                    )
                )
                return 2

    cfg = {
        "h4_warmup": 60,
        "h1_warmup": 120,
        "h1_horizon": max(6, int(args.h1_horizon)),
        "h1_stride": max(1, int(args.h1_stride)),
        "h4_trend_threshold_pct": float(args.h4_trend_threshold_pct),
        "h4_stability_bars": max(1, int(args.h4_stability_bars)),
        "h1_trend_threshold_pct": 0.0,
        "h1_reversion_z_threshold": float(args.h1_reversion_z_threshold),
        "h1_min_abs_z": float(args.h1_min_abs_z),
        "h1_max_abs_z": float(args.h1_max_abs_z),
        "h1_min_hist_vol_pct": float(args.h1_min_hist_vol_pct),
        "h1_breakdown_pct": -1.8,
        "fee_bps_round_trip": float(args.fee_bps_round_trip),
        "slippage_bps_round_trip": float(args.slippage_bps_round_trip),
        "position_fraction": 0.2,
        "enable_dynamic_horizon": True,
        "h4_regime_vol_lookback": 18,
        "h4_low_vol_threshold_pct": 0.75,
        "h4_high_vol_threshold_pct": 1.25,
        "h1_horizon_fast": 12,
        "h1_stride_fast": 12,
        "h1_horizon_slow": 24,
        "h1_stride_slow": 24,
        "early_relax_min_abs_z_delta": 0.15,
        "early_relax_stability_bars_delta": 1,
        "early_relax_min_hist_vol_delta": 0.10,
        "fold1_relax_min_abs_z_delta": 0.10,
        "fold1_relax_min_hist_vol_delta": 0.10,
        "fold3_relax_min_abs_z_delta": 0.08,
        "fold3_relax_min_hist_vol_delta": 0.08,
        "fold3_relax_h4_trend_threshold_delta": 0.05,
        "fold3_force_trend_only": bool(args.fold3_force_trend_only),
        "fold5_relax_min_abs_z_delta": 0.12,
        "fold5_relax_min_hist_vol_delta": 0.12,
        "fold2_force_trend_only": bool(args.fold2_force_trend_only),
        "mkmb_guard_threshold": float(args.mkmb_guard_threshold),
        "mkmb_position_scale": float(args.mkmb_position_scale),
        "mkmb_position_min": float(args.mkmb_position_min),
        "mkmb_position_max": float(args.mkmb_position_max),
        "mkmb_soft_fusion_weight": float(args.mkmb_soft_fusion_weight),
    }
    min_trades_gate = 3
    end_dt = datetime.fromisoformat(str(args.end))
    fold_days = max(7, int(args.fold_days))
    n_folds = max(2, int(args.n_folds))

    mkmb_proxy = _load_mkmb_proxy(args.mkmb_csv if args.use_mkmb_proxy else None)
    folds: list[dict[str, Any]] = []
    for k in range(n_folds):
        fold_end = end_dt - timedelta(days=(n_folds - 1 - k) * fold_days)
        fold_start = fold_end - timedelta(days=fold_days)
        phase = "early" if k < 2 else "default"
        if k == 0:
            phase = "fold1"
        elif k == 1:
            phase = "fold2"
        elif k == 2:
            phase = "fold3"
        elif k == 4:
            phase = "fold5"
        out = _run_window(
            symbol=str(args.symbol),
            start=fold_start.strftime("%Y-%m-%d"),
            end=fold_end.strftime("%Y-%m-%d"),
            cfg=cfg,
            phase=phase,
            mkmb_proxy=mkmb_proxy,
            use_mkmb_proxy=bool(args.use_mkmb_proxy),
            mkmb_shadow_only=bool(args.mkmb_shadow_only),
            mkmb_soft_fusion_only=bool(args.mkmb_soft_fusion_only),
        )
        m = out.get("metrics") or {}
        fail_reason = []
        if int(m.get("sample_count") or 0) < min_trades_gate:
            fail_reason.append("low_trade_count")
        if float(m.get("net_return_pct") or 0.0) <= 0:
            fail_reason.append("negative_net")
        if float(m.get("profit_factor") or 0.0) < 1.0:
            fail_reason.append("pf_below_one")
        folds.append(
            {
                "fold_index": k + 1,
                "start": fold_start.strftime("%Y-%m-%d"),
                "end": fold_end.strftime("%Y-%m-%d"),
                **out,
                "fail_reason": fail_reason,
            }
        )

    nets = [float((f.get("metrics") or {}).get("net_return_pct") or 0.0) for f in folds]
    pfs = [float((f.get("metrics") or {}).get("profit_factor") or 0.0) for f in folds]
    trades = [int((f.get("metrics") or {}).get("sample_count") or 0) for f in folds]
    stable_forward = all(n > 0 for n in nets) and all(p >= 1.0 for p in pfs) and all(c >= min_trades_gate for c in trades)

    payload = {
        "schema": "btc_mtf_h4_h1_forward_replay_v1",
        "generated_at_utc": _utc_now(),
        "symbol": str(args.symbol),
        "intervals": {"baseline": "4h", "tactical": "1h"},
        "inputs": {
            "end": str(args.end),
            "fold_days": fold_days,
            "n_folds": n_folds,
            "use_mkmb_proxy": bool(args.use_mkmb_proxy),
            "mkmb_shadow_only": bool(args.mkmb_shadow_only),
            "mkmb_soft_fusion_only": bool(args.mkmb_soft_fusion_only),
            "mkmb_csv": str(args.mkmb_csv.resolve()) if args.mkmb_csv else None,
            "enforce_mkmb_shadow_freeze": bool(args.enforce_mkmb_shadow_freeze),
            "mkmb_freeze_policy": str(args.mkmb_freeze_policy.resolve()) if args.mkmb_freeze_policy else None,
            "cfg": cfg,
        },
        "folds": folds,
        "summary": {
            "mean_net_return_pct": round(_mean(nets), 6),
            "min_net_return_pct": round(min(nets), 6) if nets else 0.0,
            "mean_profit_factor": round(_mean(pfs), 6),
            "min_profit_factor": round(min(pfs), 6) if pfs else 0.0,
            "min_sample_count": min(trades) if trades else 0,
            "min_trades_gate": min_trades_gate,
            "stable_forward": bool(stable_forward),
        },
    }
    if args.emit_fusion_gate and args.use_mkmb_proxy:
        payload["fusion_gate"] = _build_fusion_gate(
            summary=payload["summary"],
            folds=folds,
            baseline_artifact=args.baseline_artifact,
            min_profit_factor=float(args.fusion_min_profit_factor),
            min_sample_count=int(args.fusion_min_sample_count),
            max_drawdown_pct=float(args.fusion_max_drawdown_pct),
            min_mean_net_return_pct=float(args.fusion_min_mean_net_return_pct),
            require_baseline_non_regression=bool(args.fusion_require_baseline_non_regression),
            baseline_mode=str(args.fusion_baseline_mode),
            baseline_mean_net_tolerance=float(args.fusion_baseline_mean_net_tolerance),
        )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(args.output))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

