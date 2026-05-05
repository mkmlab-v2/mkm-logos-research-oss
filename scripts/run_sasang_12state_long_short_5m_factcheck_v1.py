#!/usr/bin/env python3
"""Run BTCUSDT 5m long-only vs short-only fact-check with 12-state lens."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"
DEFAULT_OUT = ART / "sasang_12state_long_short_5m_factcheck_latest.json"
DEFAULT_CACHE = ART / "btcusdt_5m_1y_latest.csv"


def _now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _max_drawdown(equity: pd.Series) -> float:
    peak = equity.cummax()
    dd = (peak - equity) / peak.replace(0, 1.0)
    return float(dd.max()) if len(dd) else 0.0


def _cvar95(r: pd.Series) -> float:
    if r.empty:
        return 0.0
    q = r.quantile(0.05)
    tail = r[r <= q]
    return float(tail.mean()) if len(tail) else 0.0


def _fetch_binance_klines_5m_1y(symbol: str) -> pd.DataFrame:
    end_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    start_ms = int((datetime.now(timezone.utc) - timedelta(days=365)).timestamp() * 1000)
    step_limit = 1000
    rows: list[list[Any]] = []
    cursor = start_ms
    url = "https://api.binance.com/api/v3/klines"

    while cursor < end_ms:
        params = {
            "symbol": symbol,
            "interval": "5m",
            "startTime": cursor,
            "endTime": end_ms,
            "limit": step_limit,
        }
        resp = requests.get(url, params=params, timeout=25)
        resp.raise_for_status()
        chunk = resp.json()
        if not isinstance(chunk, list) or not chunk:
            break
        rows.extend(chunk)
        last_open = int(chunk[-1][0])
        next_cursor = last_open + (5 * 60 * 1000)
        if next_cursor <= cursor:
            break
        cursor = next_cursor
        if len(chunk) < step_limit:
            break

    if not rows:
        raise SystemExit("no klines rows from binance")

    cols = [
        "open_time",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "close_time",
        "quote_asset_volume",
        "num_trades",
        "taker_buy_base",
        "taker_buy_quote",
        "ignore",
    ]
    df = pd.DataFrame(rows, columns=cols)
    for c in ("open", "high", "low", "close", "volume"):
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df["open_time"] = pd.to_datetime(df["open_time"], unit="ms", utc=True)
    df = df.dropna(subset=["open", "high", "low", "close"]).reset_index(drop=True)
    return df


def _compute_indicators(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["ret"] = out["close"].pct_change().fillna(0.0)
    out["ema12"] = out["close"].ewm(span=12, adjust=False).mean()
    out["ema26"] = out["close"].ewm(span=26, adjust=False).mean()
    out["macd"] = out["ema12"] - out["ema26"]
    out["macd_signal"] = out["macd"].ewm(span=9, adjust=False).mean()
    out["macd_cross_up"] = ((out["macd"] > out["macd_signal"]) & (out["macd"].shift(1) <= out["macd_signal"].shift(1))).astype(int)

    delta = out["close"].diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = (-delta.clip(upper=0)).rolling(14).mean()
    rs = gain / loss.replace(0, pd.NA)
    out["rsi14"] = pd.to_numeric((100 - (100 / (1 + rs))), errors="coerce").fillna(50.0)

    tr = pd.concat(
        [
            (out["high"] - out["low"]).abs(),
            (out["high"] - out["close"].shift(1)).abs(),
            (out["low"] - out["close"].shift(1)).abs(),
        ],
        axis=1,
    ).max(axis=1)
    out["atr14"] = tr.rolling(14).mean().bfill()

    plus_dm = (out["high"].diff()).clip(lower=0.0)
    minus_dm = (-out["low"].diff()).clip(lower=0.0)
    tr14 = tr.rolling(14).sum().replace(0, pd.NA)
    plus_di = 100 * (plus_dm.rolling(14).sum() / tr14)
    minus_di = 100 * (minus_dm.rolling(14).sum() / tr14)
    dx = (100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, pd.NA)).fillna(0.0)
    out["adx14"] = dx.rolling(14).mean().fillna(15.0)

    vroll = out["volume"].rolling(96)
    out["vol_z"] = ((out["volume"] - vroll.mean()) / vroll.std().replace(0, pd.NA)).fillna(0.0)
    bw = ((out["high"].rolling(20).max() - out["low"].rolling(20).min()) / out["close"].replace(0, pd.NA)).fillna(0.0)
    out["bw_z"] = ((bw - bw.rolling(96).mean()) / bw.rolling(96).std().replace(0, pd.NA)).fillna(0.0)
    out["ma20"] = out["close"].rolling(20).mean().bfill()
    out["ma_dist_z"] = (((out["close"] - out["ma20"]).abs() / out["ma20"].replace(0, pd.NA)) - ((out["close"] - out["ma20"]).abs() / out["ma20"].replace(0, pd.NA)).rolling(96).mean()) / (
        ((out["close"] - out["ma20"]).abs() / out["ma20"].replace(0, pd.NA)).rolling(96).std().replace(0, pd.NA)
    )
    out["ma_dist_z"] = out["ma_dist_z"].fillna(0.0)
    return out


def _assign_state(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    recent_cross = out["macd_cross_up"].rolling(3).max().fillna(0).astype(int)
    stage = pd.Series("onset", index=out.index)
    stage[(out["rsi14"].ge(70) | out["rsi14"].le(30)) & out["bw_z"].ge(1.0) & out["ma_dist_z"].ge(1.2)] = "peak"

    # Simple exhaustion proxy: price up but macd down vs 12 bars ago, or inverse.
    div = ((out["close"] > out["close"].shift(12)) & (out["macd"] < out["macd"].shift(12))) | (
        (out["close"] < out["close"].shift(12)) & (out["macd"] > out["macd"].shift(12))
    )
    stage[div.fillna(False)] = "exhaustion"
    onset_cond = (out["vol_z"].ge(1.2) & out["adx14"].ge(20) & recent_cross.eq(1))
    stage[onset_cond] = "onset"

    ret_1h = out["close"].pct_change(12).fillna(0.0)
    constitution = pd.Series("taeeum", index=out.index)
    constitution[(ret_1h > 0.006) & (out["adx14"] >= 22)] = "taeyang"
    constitution[(ret_1h > 0.001) & (ret_1h <= 0.006)] = "soyanga"
    constitution[ret_1h < -0.002] = "soeum"

    out["stage"] = stage
    out["constitution"] = constitution
    out["state_id"] = out["constitution"] + "_" + out["stage"]
    return out


def _evaluate_strategy(df: pd.DataFrame, mode: str, fee_oneway_bps: float, slippage_roundtrip_bps: float) -> dict[str, Any]:
    out = df.copy()
    if mode == "long_only":
        sig = ((out["constitution"].isin(["taeyang", "soyanga"])) & (out["stage"] != "exhaustion")).astype(int)
        side = 1.0
    elif mode == "short_only":
        sig = ((out["constitution"].isin(["soeum"])) | (out["stage"] == "exhaustion")).astype(int)
        side = -1.0
    else:
        raise ValueError(mode)

    # one-bar holding on signal, costs paid per round-trip
    fut_ret = out["close"].shift(-1) / out["close"] - 1.0
    friction = ((fee_oneway_bps * 2.0) + slippage_roundtrip_bps) / 10000.0
    trade_ret = sig * (side * fut_ret - friction)
    trade_ret = trade_ret.fillna(0.0)

    equity = (1.0 + trade_ret).cumprod()
    active = int(sig.sum())
    wins = int(((trade_ret > 0) & (sig > 0)).sum())
    wr = (wins / active) if active else 0.0
    avg = float(trade_ret[sig > 0].mean()) if active else 0.0
    total = float(equity.iloc[-1] - 1.0) if len(equity) else 0.0

    return {
        "mode": mode,
        "active_trades": active,
        "win_rate": wr,
        "avg_trade_return": avg,
        "total_return": total,
        "mdd": _max_drawdown(equity),
        "cvar95": _cvar95(trade_ret[sig > 0] if active else pd.Series(dtype=float)),
        "fee_oneway_bps": fee_oneway_bps,
        "slippage_roundtrip_bps": slippage_roundtrip_bps,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--symbol", default="BTCUSDT")
    ap.add_argument("--input-csv", type=Path, default=None, help="Optional pre-fetched 5m csv")
    ap.add_argument("--cache-csv", type=Path, default=DEFAULT_CACHE)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--fee-oneway-bps", type=float, default=4.0, help="0.04%% taker fee")
    ap.add_argument("--slippage-roundtrip-bps", type=float, default=4.0)
    args = ap.parse_args()

    if args.input_csv is not None and args.input_csv.is_file():
        df = pd.read_csv(args.input_csv)
        if "open_time" in df.columns:
            df["open_time"] = pd.to_datetime(df["open_time"], utc=True, errors="coerce")
    else:
        df = _fetch_binance_klines_5m_1y(args.symbol)
        args.cache_csv.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(args.cache_csv, index=False)

    df = _compute_indicators(df)
    df = _assign_state(df)
    df = df.dropna(subset=["close"]).reset_index(drop=True)

    long_res = _evaluate_strategy(df, "long_only", args.fee_oneway_bps, args.slippage_roundtrip_bps)
    short_res = _evaluate_strategy(df, "short_only", args.fee_oneway_bps, args.slippage_roundtrip_bps)

    both_down = (long_res["total_return"] < 0.0) and (short_res["total_return"] < 0.0)
    out = {
        "schema": "sasang_12state_long_short_5m_factcheck_v1",
        "generated_at_utc": _now_utc(),
        "research_only": True,
        "track_wall": {"track_b_only": True, "a_track_autobind_forbidden": True},
        "inputs": {
            "symbol": args.symbol,
            "rows": int(len(df)),
            "window": "1y_5m",
            "fee_oneway_bps": args.fee_oneway_bps,
            "slippage_roundtrip_bps": args.slippage_roundtrip_bps,
        },
        "results": [long_res, short_res],
        "summary": {
            "both_down_after_friction": both_down,
            "recommended_policy": "use_as_veto_filter_not_directional_scalper",
        },
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.output_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
