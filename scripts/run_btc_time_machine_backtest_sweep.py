# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.9, L:0.8, K:0.5, M:0.6}
# Balance: 91
# Purpose: Sweep BTC time-machine backtest periods/configs for evidence scaling.
# Keywords: btc, backtest, sweep, timeseries, fact-safe
"""Run BTC causal time-machine sweep and emit best configuration summary."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

try:
    from scripts.run_btc_time_machine_fact_safe_backtest import BacktestConfig, run_backtest
except ModuleNotFoundError:  # direct execution fallback
    from run_btc_time_machine_fact_safe_backtest import BacktestConfig, run_backtest

import sys

ROOT = Path(__file__).resolve().parents[1]
BTC_ROOT = ROOT / "projects" / "bitcoin-trading"
sys.path.insert(0, str(BTC_ROOT))
sys.path.insert(0, str(BTC_ROOT / "src"))
from backtest.light_historical_data_loader import fetch_historical_data_light

OUT_PATH = ROOT / "docs" / "final" / "artifacts" / "btc_time_machine_sweep_latest.json"


def _z_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _score(metrics: dict) -> float:
    sample = float(metrics.get("sample_count") or 0.0)
    net = float(metrics.get("net_return_pct") or 0.0)
    pf = float(metrics.get("profit_factor") or 0.0)
    wr = float(metrics.get("win_rate") or 0.0)
    # Conservative blended score prioritizing sample support and risk-adjusted stability.
    return net * 0.5 + pf * 10.0 + wr * 10.0 + sample * 0.01


def run_sweep() -> dict:
    periods = [
        ("2024-01-01", "2024-12-31"),
        ("2025-01-01", "2025-12-31"),
        ("2026-01-01", "2026-12-31"),
    ]
    configs = [
        BacktestConfig(warmup=20, horizon=1, stride=1, fee_bps_round_trip=8.0),
        BacktestConfig(warmup=20, horizon=3, stride=1, fee_bps_round_trip=8.0),
        BacktestConfig(warmup=30, horizon=3, stride=1, fee_bps_round_trip=8.0),
        BacktestConfig(warmup=30, horizon=7, stride=1, fee_bps_round_trip=8.0),
    ]
    rows: list[dict] = []
    for start, end in periods:
        df = fetch_historical_data_light(
            start_date=datetime.fromisoformat(start),
            end_date=datetime.fromisoformat(end),
            symbol="BTCUSDT",
        )
        for cfg in configs:
            metrics = run_backtest(df, cfg)
            row = {
                "period": f"{start}..{end}",
                "bars": int(len(df)),
                "config": {
                    "warmup": cfg.warmup,
                    "horizon": cfg.horizon,
                    "stride": cfg.stride,
                    "fee_bps_round_trip": cfg.fee_bps_round_trip,
                },
                "metrics": metrics,
                "score": round(_score(metrics), 6),
            }
            rows.append(row)
    rows_sorted = sorted(rows, key=lambda r: r["score"], reverse=True)
    best = rows_sorted[0] if rows_sorted else None
    return {
        "schema": "btc_time_machine_sweep_v1",
        "generated_at_utc": _z_now(),
        "symbol": "BTCUSDT",
        "rows": rows_sorted,
        "best": best,
    }


def main() -> int:
    doc = run_sweep()
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(OUT_PATH))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
