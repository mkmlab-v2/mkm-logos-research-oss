# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.9, L:0.8, K:0.4, M:0.6}
# Balance: 90
# Purpose: Run causal BTC time-machine backtest for Fact-Safe evidence.
# Keywords: btc, backtest, time-machine, fact-safe, leakage-free
"""Causal BTC time-machine backtest for Fact-Safe evidence."""

from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
BTC_ROOT = ROOT / "projects" / "bitcoin-trading"
sys.path.insert(0, str(BTC_ROOT))
sys.path.insert(0, str(BTC_ROOT / "src"))
from backtest.light_historical_data_loader import fetch_historical_data_light


DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "btc_time_machine_fact_safe_backtest_latest.json"
FALLBACK_BTC_FIXTURE = ROOT / "projects" / "bitcoin-trading" / "tests" / "fixtures" / "btc_smoke_daily.csv"


@dataclass(frozen=True)
class BacktestConfig:
    warmup: int
    horizon: int
    stride: int
    fee_bps_round_trip: float
    slippage_bps_round_trip: float = 5.0
    max_position_fraction: float = 0.2
    daily_loss_cap_pct: float = 1.5
    skip_if_vol_shock_pct: float = 8.0


def _maybe_get_numba():
    try:
        from numba import njit
    except Exception:
        return None
    return njit


def _maybe_get_torch():
    try:
        import torch
    except Exception:
        return None
    if not torch.cuda.is_available():
        return None
    return torch


def _cuda_device_name() -> str | None:
    torch = _maybe_get_torch()
    if torch is None:
        return None
    try:
        return str(torch.cuda.get_device_name(torch.cuda.current_device()))
    except Exception:
        return "cuda-available"


def _run_backtest_cpu(close_values: np.ndarray, day_keys: np.ndarray, cfg: BacktestConfig) -> dict[str, Any]:
    trades: list[float] = []
    skipped_vol_shock = 0
    skipped_daily_loss_cap = 0
    daily_pnl: dict[str, float] = {}
    equity = 1.0
    peak_equity = 1.0
    max_drawdown = 0.0
    max_loss_streak = 0
    loss_streak = 0

    for i in range(cfg.warmup, len(close_values) - cfg.horizon, cfg.stride):
        hist = close_values[i - cfg.warmup : i + 1]
        latest = float(hist[-1])
        sma = float(hist.mean())
        direction = 1 if latest >= sma else -1
        entry = float(close_values[i])
        exit_ = float(close_values[i + cfg.horizon])
        raw_ret = (exit_ - entry) / entry
        if abs(raw_ret) * 100.0 >= cfg.skip_if_vol_shock_pct:
            skipped_vol_shock += 1
            continue
        signed = direction * raw_ret
        fee = cfg.fee_bps_round_trip / 10_000.0
        slippage = cfg.slippage_bps_round_trip / 10_000.0
        net_ret = (signed - fee - slippage) * cfg.max_position_fraction
        day_key = str(day_keys[i])
        day_realized = daily_pnl.get(day_key, 0.0)
        daily_loss_cap = cfg.daily_loss_cap_pct / 100.0
        if day_realized <= -daily_loss_cap and net_ret < 0:
            skipped_daily_loss_cap += 1
            continue
        daily_pnl[day_key] = day_realized + net_ret
        trades.append(net_ret)
        equity *= 1.0 + net_ret
        peak_equity = max(peak_equity, equity)
        drawdown = (peak_equity - equity) / peak_equity if peak_equity > 0 else 0.0
        max_drawdown = max(max_drawdown, drawdown)
        if net_ret < 0:
            loss_streak += 1
            max_loss_streak = max(max_loss_streak, loss_streak)
        else:
            loss_streak = 0

    if not trades:
        return {
            "sample_count": 0,
            "win_rate": 0.0,
            "net_return_pct": 0.0,
            "avg_trade_return_pct": 0.0,
            "profit_factor": None,
            "max_drawdown_pct": 0.0,
            "max_loss_streak": 0,
            "skipped_vol_shock": skipped_vol_shock,
            "skipped_daily_loss_cap": skipped_daily_loss_cap,
        }
    wins = [x for x in trades if x > 0]
    losses = [x for x in trades if x < 0]
    gross_profit = sum(wins)
    gross_loss = abs(sum(losses))
    profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else None
    net_return = sum(trades)

    return {
        "sample_count": len(trades),
        "win_rate": round(len(wins) / len(trades), 6),
        "net_return_pct": round(net_return * 100.0, 6),
        "avg_trade_return_pct": round((net_return / len(trades)) * 100.0, 6),
        "profit_factor": round(profit_factor, 6) if profit_factor is not None else None,
        "max_drawdown_pct": round(max_drawdown * 100.0, 6),
        "max_loss_streak": int(max_loss_streak),
        "skipped_vol_shock": skipped_vol_shock,
        "skipped_daily_loss_cap": skipped_daily_loss_cap,
    }


def _build_numba_runner():
    njit = _maybe_get_numba()
    if njit is None:
        return None

    @njit(cache=True)
    def _run_numba(
        close_values: np.ndarray,
        day_ids: np.ndarray,
        warmup: int,
        horizon: int,
        stride: int,
        fee_bps_round_trip: float,
        slippage_bps_round_trip: float,
        max_position_fraction: float,
        daily_loss_cap_pct: float,
        skip_if_vol_shock_pct: float,
    ) -> np.ndarray:
        n = len(close_values)
        max_trades = n
        trades = np.zeros(max_trades, dtype=np.float64)
        trade_count = 0
        skipped_vol_shock = 0
        skipped_daily_loss_cap = 0
        daily_pnl = np.zeros(n, dtype=np.float64)
        equity = 1.0
        peak_equity = 1.0
        max_drawdown = 0.0
        max_loss_streak = 0
        loss_streak = 0

        fee = fee_bps_round_trip / 10_000.0
        slippage = slippage_bps_round_trip / 10_000.0
        daily_loss_cap = daily_loss_cap_pct / 100.0

        for i in range(warmup, n - horizon, stride):
            hist = close_values[i - warmup : i + 1]
            latest = hist[-1]
            sma = np.mean(hist)
            direction = 1.0 if latest >= sma else -1.0
            entry = close_values[i]
            exit_ = close_values[i + horizon]
            raw_ret = (exit_ - entry) / entry
            if abs(raw_ret) * 100.0 >= skip_if_vol_shock_pct:
                skipped_vol_shock += 1
                continue
            signed = direction * raw_ret
            net_ret = (signed - fee - slippage) * max_position_fraction
            day_idx = day_ids[i]
            day_realized = daily_pnl[day_idx]
            if day_realized <= -daily_loss_cap and net_ret < 0:
                skipped_daily_loss_cap += 1
                continue
            daily_pnl[day_idx] = day_realized + net_ret
            trades[trade_count] = net_ret
            trade_count += 1
            equity *= 1.0 + net_ret
            if equity > peak_equity:
                peak_equity = equity
            drawdown = (peak_equity - equity) / peak_equity if peak_equity > 0 else 0.0
            if drawdown > max_drawdown:
                max_drawdown = drawdown
            if net_ret < 0:
                loss_streak += 1
                if loss_streak > max_loss_streak:
                    max_loss_streak = loss_streak
            else:
                loss_streak = 0

        if trade_count == 0:
            return np.array(
                [
                    0.0,
                    0.0,
                    0.0,
                    np.nan,
                    max_drawdown * 100.0,
                    float(max_loss_streak),
                    float(skipped_vol_shock),
                    float(skipped_daily_loss_cap),
                ],
                dtype=np.float64,
            )

        trade_slice = trades[:trade_count]
        wins = trade_slice[trade_slice > 0]
        losses = trade_slice[trade_slice < 0]
        gross_profit = np.sum(wins) if len(wins) > 0 else 0.0
        gross_loss = abs(np.sum(losses)) if len(losses) > 0 else 0.0
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else np.nan
        net_return = float(np.sum(trade_slice))
        win_rate = float(len(wins)) / float(trade_count)

        return np.array(
            [
                float(trade_count),
                win_rate,
                net_return * 100.0,
                (net_return / float(trade_count)) * 100.0,
                profit_factor,
                max_drawdown * 100.0,
                float(max_loss_streak),
                float(skipped_vol_shock),
                float(skipped_daily_loss_cap),
            ],
            dtype=np.float64,
        )

    return _run_numba


def _run_backtest_cuda(close_values: np.ndarray, day_keys: np.ndarray, cfg: BacktestConfig) -> dict[str, Any] | None:
    torch = _maybe_get_torch()
    if torch is None:
        return None

    device = torch.device("cuda")
    n = int(len(close_values))
    if n <= cfg.warmup + cfg.horizon:
        return {
            "sample_count": 0,
            "win_rate": 0.0,
            "net_return_pct": 0.0,
            "avg_trade_return_pct": 0.0,
            "profit_factor": None,
            "max_drawdown_pct": 0.0,
            "max_loss_streak": 0,
            "skipped_vol_shock": 0,
            "skipped_daily_loss_cap": 0,
        }

    # CPU에서 day id 생성 (문자열 매핑), 연산 핵심은 GPU 텐서로 수행
    unique_days: dict[Any, int] = {}
    day_ids_np = np.empty(n, dtype=np.int64)
    next_id = 0
    for i, d in enumerate(day_keys):
        did = unique_days.get(d)
        if did is None:
            did = next_id
            unique_days[d] = did
            next_id += 1
        day_ids_np[i] = did

    close_t = torch.as_tensor(close_values, dtype=torch.float64, device=device)
    day_ids_t = torch.as_tensor(day_ids_np, dtype=torch.int64, device=device)
    daily_pnl_t = torch.zeros(max(1, next_id), dtype=torch.float64, device=device)

    fee = cfg.fee_bps_round_trip / 10_000.0
    slippage = cfg.slippage_bps_round_trip / 10_000.0
    daily_loss_cap = cfg.daily_loss_cap_pct / 100.0

    trades: list[float] = []
    skipped_vol_shock = 0
    skipped_daily_loss_cap = 0
    equity = 1.0
    peak_equity = 1.0
    max_drawdown = 0.0
    max_loss_streak = 0
    loss_streak = 0

    for i in range(cfg.warmup, n - cfg.horizon, cfg.stride):
        hist = close_t[i - cfg.warmup : i + 1]
        latest = float(hist[-1].item())
        sma = float(hist.mean().item())
        direction = 1.0 if latest >= sma else -1.0

        entry = float(close_t[i].item())
        exit_ = float(close_t[i + cfg.horizon].item())
        raw_ret = (exit_ - entry) / entry
        if abs(raw_ret) * 100.0 >= cfg.skip_if_vol_shock_pct:
            skipped_vol_shock += 1
            continue

        signed = direction * raw_ret
        net_ret = (signed - fee - slippage) * cfg.max_position_fraction
        day_idx = int(day_ids_t[i].item())
        day_realized = float(daily_pnl_t[day_idx].item())
        if day_realized <= -daily_loss_cap and net_ret < 0:
            skipped_daily_loss_cap += 1
            continue
        daily_pnl_t[day_idx] = daily_pnl_t[day_idx] + net_ret

        trades.append(net_ret)
        equity *= 1.0 + net_ret
        peak_equity = max(peak_equity, equity)
        drawdown = (peak_equity - equity) / peak_equity if peak_equity > 0 else 0.0
        max_drawdown = max(max_drawdown, drawdown)
        if net_ret < 0:
            loss_streak += 1
            max_loss_streak = max(max_loss_streak, loss_streak)
        else:
            loss_streak = 0

    if not trades:
        return {
            "sample_count": 0,
            "win_rate": 0.0,
            "net_return_pct": 0.0,
            "avg_trade_return_pct": 0.0,
            "profit_factor": None,
            "max_drawdown_pct": 0.0,
            "max_loss_streak": 0,
            "skipped_vol_shock": skipped_vol_shock,
            "skipped_daily_loss_cap": skipped_daily_loss_cap,
        }

    wins = [x for x in trades if x > 0]
    losses = [x for x in trades if x < 0]
    gross_profit = sum(wins)
    gross_loss = abs(sum(losses))
    profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else None
    net_return = sum(trades)

    return {
        "sample_count": len(trades),
        "win_rate": round(len(wins) / len(trades), 6),
        "net_return_pct": round(net_return * 100.0, 6),
        "avg_trade_return_pct": round((net_return / len(trades)) * 100.0, 6),
        "profit_factor": round(profit_factor, 6) if profit_factor is not None else None,
        "max_drawdown_pct": round(max_drawdown * 100.0, 6),
        "max_loss_streak": int(max_loss_streak),
        "skipped_vol_shock": skipped_vol_shock,
        "skipped_daily_loss_cap": skipped_daily_loss_cap,
    }


def _z_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_btc_data_with_fallback(
    start_dt: datetime,
    end_dt: datetime,
    symbol: str,
    data_file: str | None,
) -> tuple[pd.DataFrame, str]:
    try:
        df = fetch_historical_data_light(
            start_date=start_dt,
            end_date=end_dt,
            data_file=data_file,
            symbol=symbol,
        )
        return df, "primary"
    except Exception as exc:
        if FALLBACK_BTC_FIXTURE.exists():
            print(
                f"[WARN] primary BTC data fetch failed ({exc.__class__.__name__}: {exc}); "
                f"fallback fixture={FALLBACK_BTC_FIXTURE}",
                file=sys.stderr,
            )
            df = pd.read_csv(FALLBACK_BTC_FIXTURE)
            lowered = {c.lower(): c for c in df.columns}
            date_col = lowered.get("date") or lowered.get("timestamp")
            if not date_col:
                raise RuntimeError(f"fallback fixture missing date/timestamp column: {FALLBACK_BTC_FIXTURE}")
            if date_col.lower() == "timestamp":
                df["date"] = pd.to_datetime(df[date_col], unit="ms", errors="coerce")
            else:
                df["date"] = pd.to_datetime(df[date_col], errors="coerce")
            df = df.dropna(subset=["date"]).set_index("date").sort_index()
            for col in ("open", "high", "low", "close", "volume"):
                src_col = lowered.get(col)
                if src_col and src_col in df.columns:
                    df[col] = pd.to_numeric(df[src_col], errors="coerce")
            df = df[(df.index >= start_dt) & (df.index <= end_dt)]
            if "close" not in df.columns:
                raise RuntimeError(f"fallback fixture missing close column: {FALLBACK_BTC_FIXTURE}")
            return df, "fixture_fallback"
        raise


def _signal_from_past(close_hist: pd.Series) -> int:
    """
    Causal signal: compare latest close vs SMA of history.
    Returns +1 (BUY bias), -1 (SELL bias).
    """
    latest = float(close_hist.iloc[-1])
    sma = float(close_hist.mean())
    return 1 if latest >= sma else -1


def run_backtest(df: pd.DataFrame, cfg: BacktestConfig) -> dict[str, Any]:
    if "close" not in df.columns or len(df) <= cfg.warmup + cfg.horizon:
        return {
            "sample_count": 0,
            "win_rate": 0.0,
            "net_return_pct": 0.0,
            "avg_trade_return_pct": 0.0,
            "profit_factor": None,
        }

    trades: list[float] = []
    skipped_vol_shock = 0
    skipped_daily_loss_cap = 0
    daily_pnl: dict[str, float] = {}
    equity = 1.0
    peak_equity = 1.0
    max_drawdown = 0.0
    max_loss_streak = 0
    loss_streak = 0
    for i in range(cfg.warmup, len(df) - cfg.horizon, cfg.stride):
        hist = df["close"].iloc[i - cfg.warmup : i + 1]
        direction = _signal_from_past(hist)
        entry = float(df["close"].iloc[i])
        exit_ = float(df["close"].iloc[i + cfg.horizon])
        raw_ret = (exit_ - entry) / entry
        if abs(raw_ret) * 100.0 >= cfg.skip_if_vol_shock_pct:
            skipped_vol_shock += 1
            continue
        signed = direction * raw_ret
        fee = cfg.fee_bps_round_trip / 10_000.0
        slippage = cfg.slippage_bps_round_trip / 10_000.0
        net_ret = (signed - fee - slippage) * cfg.max_position_fraction
        day_key = str(df.index[i].date()) if hasattr(df.index[i], "date") else f"bar-{i}"
        day_realized = daily_pnl.get(day_key, 0.0)
        daily_loss_cap = cfg.daily_loss_cap_pct / 100.0
        if day_realized <= -daily_loss_cap and net_ret < 0:
            skipped_daily_loss_cap += 1
            continue
        daily_pnl[day_key] = day_realized + net_ret
        trades.append(net_ret)
        equity *= 1.0 + net_ret
        peak_equity = max(peak_equity, equity)
        drawdown = (peak_equity - equity) / peak_equity if peak_equity > 0 else 0.0
        max_drawdown = max(max_drawdown, drawdown)
        if net_ret < 0:
            loss_streak += 1
            max_loss_streak = max(max_loss_streak, loss_streak)
        else:
            loss_streak = 0

    if not trades:
        return {
            "sample_count": 0,
            "win_rate": 0.0,
            "net_return_pct": 0.0,
            "avg_trade_return_pct": 0.0,
            "profit_factor": None,
            "max_drawdown_pct": 0.0,
            "max_loss_streak": 0,
            "skipped_vol_shock": skipped_vol_shock,
            "skipped_daily_loss_cap": skipped_daily_loss_cap,
        }

    wins = [x for x in trades if x > 0]
    losses = [x for x in trades if x < 0]
    gross_profit = sum(wins)
    gross_loss = abs(sum(losses))
    profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else None
    net_return = sum(trades)

    return {
        "sample_count": len(trades),
        "win_rate": round(len(wins) / len(trades), 6),
        "net_return_pct": round(net_return * 100.0, 6),
        "avg_trade_return_pct": round((net_return / len(trades)) * 100.0, 6),
        "profit_factor": round(profit_factor, 6) if profit_factor is not None else None,
        "max_drawdown_pct": round(max_drawdown * 100.0, 6),
        "max_loss_streak": int(max_loss_streak),
        "skipped_vol_shock": skipped_vol_shock,
        "skipped_daily_loss_cap": skipped_daily_loss_cap,
    }


def run_backtest_with_engine(df: pd.DataFrame, cfg: BacktestConfig, engine: str = "cpu") -> tuple[dict[str, Any], str]:
    close_values = df["close"].to_numpy(dtype=np.float64)
    day_keys = np.array(
        [str(ts.date()) if hasattr(ts, "date") else f"bar-{i}" for i, ts in enumerate(df.index)],
        dtype=object,
    )

    if engine == "cuda":
        metrics = _run_backtest_cuda(close_values=close_values, day_keys=day_keys, cfg=cfg)
        if metrics is not None:
            return metrics, "cuda"
    if engine == "numba":
        numba_runner = _build_numba_runner()
        if numba_runner is not None:
            unique_days = {}
            day_ids = np.empty(len(day_keys), dtype=np.int64)
            next_id = 0
            for i, d in enumerate(day_keys):
                did = unique_days.get(d)
                if did is None:
                    did = next_id
                    unique_days[d] = did
                    next_id += 1
                day_ids[i] = did
            arr = numba_runner(
                close_values,
                day_ids,
                cfg.warmup,
                cfg.horizon,
                cfg.stride,
                cfg.fee_bps_round_trip,
                cfg.slippage_bps_round_trip,
                cfg.max_position_fraction,
                cfg.daily_loss_cap_pct,
                cfg.skip_if_vol_shock_pct,
            )
            sample_count = int(arr[0])
            profit_factor = None if np.isnan(arr[4]) else round(float(arr[4]), 6)
            metrics = {
                "sample_count": sample_count,
                "win_rate": round(float(arr[1]), 6),
                "net_return_pct": round(float(arr[2]), 6),
                "avg_trade_return_pct": round(float(arr[3]), 6),
                "profit_factor": profit_factor,
                "max_drawdown_pct": round(float(arr[5]), 6),
                "max_loss_streak": int(arr[6]),
                "skipped_vol_shock": int(arr[7]),
                "skipped_daily_loss_cap": int(arr[8]),
            }
            return metrics, "numba"
    metrics = _run_backtest_cpu(close_values=close_values, day_keys=day_keys, cfg=cfg)
    return metrics, "cpu"


def main() -> int:
    parser = argparse.ArgumentParser(description="Run BTC causal time-machine backtest.")
    parser.add_argument("--symbol", default="BTCUSDT")
    parser.add_argument("--start", default="2025-01-01")
    parser.add_argument("--end", default="2025-12-31")
    parser.add_argument("--warmup", type=int, default=30)
    parser.add_argument("--horizon", type=int, default=3)
    parser.add_argument("--stride", type=int, default=1)
    parser.add_argument("--fee-bps-round-trip", type=float, default=8.0)
    parser.add_argument("--slippage-bps-round-trip", type=float, default=5.0)
    parser.add_argument("--max-position-fraction", type=float, default=0.2)
    parser.add_argument("--daily-loss-cap-pct", type=float, default=1.5)
    parser.add_argument("--skip-if-vol-shock-pct", type=float, default=8.0)
    parser.add_argument("--csv", default="")
    parser.add_argument("--output", default=str(DEFAULT_OUT))
    parser.add_argument("--engine", choices=["cpu", "numba", "cuda"], default="cpu")
    parser.add_argument("--benchmark-all-engines", action="store_true")
    args = parser.parse_args()

    start_dt = datetime.fromisoformat(args.start)
    end_dt = datetime.fromisoformat(args.end)
    data_file = args.csv.strip() or None
    df, data_source_mode = _load_btc_data_with_fallback(
        start_dt=start_dt,
        end_dt=end_dt,
        data_file=data_file,
        symbol=args.symbol,
    )
    cfg = BacktestConfig(
        warmup=args.warmup,
        horizon=args.horizon,
        stride=args.stride,
        fee_bps_round_trip=args.fee_bps_round_trip,
        slippage_bps_round_trip=args.slippage_bps_round_trip,
        max_position_fraction=args.max_position_fraction,
        daily_loss_cap_pct=args.daily_loss_cap_pct,
        skip_if_vol_shock_pct=args.skip_if_vol_shock_pct,
    )
    t0 = time.perf_counter()
    metrics, engine_used = run_backtest_with_engine(df, cfg, engine=args.engine)
    elapsed_ms = max(0.001, round((time.perf_counter() - t0) * 1000.0, 3))
    bars = int(len(df))
    bars_per_sec = round((bars / (elapsed_ms / 1000.0)), 6) if elapsed_ms > 0 else None

    benchmark: dict[str, Any] | None = None
    if args.benchmark_all_engines:
        benchmark = {}
        for eng in ("cpu", "numba", "cuda"):
            t_eng = time.perf_counter()
            _m, used_eng = run_backtest_with_engine(df, cfg, engine=eng)
            ms_eng = max(0.001, round((time.perf_counter() - t_eng) * 1000.0, 3))
            benchmark[eng] = {
                "requested": eng,
                "used": used_eng,
                "elapsed_ms": ms_eng,
                "bars_per_sec": round((bars / (ms_eng / 1000.0)), 6) if ms_eng > 0 else None,
            }

    payload = {
        "schema": "btc_time_machine_fact_safe_backtest_v1",
        "generated_at_utc": _z_now(),
        "method": "causal_walk_forward_no_future_leak",
        "symbol": args.symbol,
        "start": args.start,
        "end": args.end,
        "bars": bars,
        "data_source_mode": data_source_mode,
        "data_source_file": (str(FALLBACK_BTC_FIXTURE) if data_source_mode == "fixture_fallback" else data_file),
        "config": {
            "warmup": cfg.warmup,
            "horizon": cfg.horizon,
            "stride": cfg.stride,
            "fee_bps_round_trip": cfg.fee_bps_round_trip,
            "slippage_bps_round_trip": cfg.slippage_bps_round_trip,
            "max_position_fraction": cfg.max_position_fraction,
            "daily_loss_cap_pct": cfg.daily_loss_cap_pct,
            "skip_if_vol_shock_pct": cfg.skip_if_vol_shock_pct,
        },
        "metrics": metrics,
        "performance": {
            "elapsed_ms": elapsed_ms,
            "bars_per_sec": bars_per_sec,
            "benchmark_all_engines": benchmark,
        },
        "engine": {
            "requested": args.engine,
            "used": engine_used,
            "cuda_device": _cuda_device_name() if engine_used == "cuda" else None,
        },
    }

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
