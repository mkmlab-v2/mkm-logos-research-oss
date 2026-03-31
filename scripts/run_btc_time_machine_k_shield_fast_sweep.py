"""Fast K-shield sweep for 2025 BTC time-machine backtest."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
BTC_ROOT = ROOT / "projects" / "bitcoin-trading"
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(BTC_ROOT))
sys.path.insert(0, str(BTC_ROOT / "src"))

from backtest.light_historical_data_loader import fetch_historical_data_light
from run_btc_time_machine_fact_safe_backtest import BacktestConfig, run_backtest

OUT_PATH = ROOT / "docs" / "final" / "artifacts" / "btc_k_shield_fast_sweep_2025_latest.json"


def _z_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _score(metrics: dict[str, Any]) -> float:
    net = float(metrics.get("net_return_pct") or 0.0)
    pf = float(metrics.get("profit_factor") or 0.0)
    mdd = float(metrics.get("max_drawdown_pct") or 0.0)
    return net + (pf * 5.0) - (mdd * 0.8)


def run_fast_sweep() -> dict[str, Any]:
    df = fetch_historical_data_light(
        start_date=datetime.fromisoformat("2025-01-01"),
        end_date=datetime.fromisoformat("2025-12-31"),
        symbol="BTCUSDT",
    )
    configs: list[tuple[str, BacktestConfig]] = [
        (
            "baseline_h3",
            BacktestConfig(
                warmup=30,
                horizon=3,
                stride=1,
                fee_bps_round_trip=8.0,
                slippage_bps_round_trip=5.0,
                max_position_fraction=0.2,
                daily_loss_cap_pct=1.5,
                skip_if_vol_shock_pct=8.0,
            ),
        ),
        (
            "k_shield_h3_soft",
            BacktestConfig(
                warmup=30,
                horizon=3,
                stride=1,
                fee_bps_round_trip=8.0,
                slippage_bps_round_trip=5.0,
                max_position_fraction=0.15,
                daily_loss_cap_pct=1.2,
                skip_if_vol_shock_pct=6.5,
            ),
        ),
        (
            "baseline_h1",
            BacktestConfig(
                warmup=20,
                horizon=1,
                stride=1,
                fee_bps_round_trip=8.0,
                slippage_bps_round_trip=5.0,
                max_position_fraction=0.2,
                daily_loss_cap_pct=1.5,
                skip_if_vol_shock_pct=8.0,
            ),
        ),
        (
            "k_shield_h1_soft",
            BacktestConfig(
                warmup=20,
                horizon=1,
                stride=1,
                fee_bps_round_trip=8.0,
                slippage_bps_round_trip=5.0,
                max_position_fraction=0.15,
                daily_loss_cap_pct=1.2,
                skip_if_vol_shock_pct=6.5,
            ),
        ),
    ]

    rows = []
    for name, cfg in configs:
        metrics = run_backtest(df, cfg)
        rows.append(
            {
                "name": name,
                "config": cfg.__dict__,
                "metrics": metrics,
                "score": round(_score(metrics), 6),
            }
        )

    best = sorted(rows, key=lambda r: r["score"], reverse=True)[0]
    return {
        "schema": "btc_k_shield_fast_sweep_v2",
        "generated_at_utc": _z_now(),
        "period": "2025-01-01..2025-12-31",
        "rows": rows,
        "best_by_balanced_score": best,
        "note": "Balanced score = net + 5*PF - 0.8*MDD",
    }


def main() -> int:
    doc = run_fast_sweep()
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(OUT_PATH))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
