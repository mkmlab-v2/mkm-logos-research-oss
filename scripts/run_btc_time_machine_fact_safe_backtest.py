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
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
BTC_ROOT = ROOT / "projects" / "bitcoin-trading"
sys.path.insert(0, str(BTC_ROOT))
sys.path.insert(0, str(BTC_ROOT / "src"))
from backtest.light_historical_data_loader import fetch_historical_data_light


DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "btc_time_machine_fact_safe_backtest_latest.json"


@dataclass(frozen=True)
class BacktestConfig:
    warmup: int
    horizon: int
    stride: int
    fee_bps_round_trip: float


def _z_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


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
    for i in range(cfg.warmup, len(df) - cfg.horizon, cfg.stride):
        hist = df["close"].iloc[i - cfg.warmup : i + 1]
        direction = _signal_from_past(hist)
        entry = float(df["close"].iloc[i])
        exit_ = float(df["close"].iloc[i + cfg.horizon])
        raw_ret = (exit_ - entry) / entry
        signed = direction * raw_ret
        fee = cfg.fee_bps_round_trip / 10_000.0
        net_ret = signed - fee
        trades.append(net_ret)

    if not trades:
        return {
            "sample_count": 0,
            "win_rate": 0.0,
            "net_return_pct": 0.0,
            "avg_trade_return_pct": 0.0,
            "profit_factor": None,
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
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run BTC causal time-machine backtest.")
    parser.add_argument("--symbol", default="BTCUSDT")
    parser.add_argument("--start", default="2025-01-01")
    parser.add_argument("--end", default="2025-12-31")
    parser.add_argument("--warmup", type=int, default=30)
    parser.add_argument("--horizon", type=int, default=3)
    parser.add_argument("--stride", type=int, default=1)
    parser.add_argument("--fee-bps-round-trip", type=float, default=8.0)
    parser.add_argument("--csv", default="")
    parser.add_argument("--output", default=str(DEFAULT_OUT))
    args = parser.parse_args()

    start_dt = datetime.fromisoformat(args.start)
    end_dt = datetime.fromisoformat(args.end)
    data_file = args.csv.strip() or None
    df = fetch_historical_data_light(
        start_date=start_dt,
        end_date=end_dt,
        data_file=data_file,
        symbol=args.symbol,
    )
    cfg = BacktestConfig(
        warmup=args.warmup,
        horizon=args.horizon,
        stride=args.stride,
        fee_bps_round_trip=args.fee_bps_round_trip,
    )
    metrics = run_backtest(df, cfg)

    payload = {
        "schema": "btc_time_machine_fact_safe_backtest_v1",
        "generated_at_utc": _z_now(),
        "method": "causal_walk_forward_no_future_leak",
        "symbol": args.symbol,
        "start": args.start,
        "end": args.end,
        "bars": int(len(df)),
        "config": {
            "warmup": cfg.warmup,
            "horizon": cfg.horizon,
            "stride": cfg.stride,
            "fee_bps_round_trip": cfg.fee_bps_round_trip,
        },
        "metrics": metrics,
    }

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
