# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.9, L:0.8, K:0.5, M:0.6}
# Balance: 91
# Purpose: Sweep BTC time-machine backtest periods/configs for evidence scaling.
# Keywords: btc, backtest, sweep, timeseries, fact-safe
"""Run BTC causal time-machine sweep and emit best configuration summary."""

from __future__ import annotations

import argparse
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

# Default windows: long evidence (10y / 15y) + recent calendar years.
DEFAULT_PERIODS: list[tuple[str, str]] = [
    ("2016-01-01", "2025-12-31"),
    ("2011-01-01", "2025-12-31"),
    ("2024-01-01", "2024-12-31"),
    ("2025-01-01", "2025-12-31"),
    ("2026-01-01", "2026-12-31"),
]


def _parse_periods_spec(spec: str) -> list[tuple[str, str]]:
    """Parse 'start:end,start:end' (ISO dates). Whitespace allowed."""
    out: list[tuple[str, str]] = []
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        if ":" not in part:
            raise ValueError(f"Invalid period segment (expected start:end): {part!r}")
        start_s, end_s = part.split(":", 1)
        out.append((start_s.strip(), end_s.strip()))
    if not out:
        raise ValueError("Empty --periods")
    return out


def _z_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _score(metrics: dict) -> float:
    sample = float(metrics.get("sample_count") or 0.0)
    net = float(metrics.get("net_return_pct") or 0.0)
    pf = float(metrics.get("profit_factor") or 0.0)
    wr = float(metrics.get("win_rate") or 0.0)
    max_dd = float(metrics.get("max_drawdown_pct") or 0.0)
    loss_streak = float(metrics.get("max_loss_streak") or 0.0)
    pf_penalty = 0.0 if pf >= 1.0 else (1.0 - pf) * 20.0
    # Conservative blended score with explicit drawdown and loss-duration penalty.
    return net * 0.45 + pf * 10.0 + wr * 10.0 + sample * 0.01 - max_dd * 0.6 - loss_streak * 0.5 - pf_penalty


def run_sweep(periods: list[tuple[str, str]] | None = None) -> dict:
    periods = list(periods) if periods is not None else list(DEFAULT_PERIODS)
    min_samples_for_best = 50
    max_drawdown_for_best_pct = 20.0
    max_vol_shock_skip_rate_pct = 60.0
    configs = [
        BacktestConfig(warmup=20, horizon=1, stride=1, fee_bps_round_trip=8.0, slippage_bps_round_trip=5.0),
        # K-shield soft profile: keeps horizon=1 while tightening volatility shock and risk caps.
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
        BacktestConfig(warmup=20, horizon=3, stride=1, fee_bps_round_trip=8.0, slippage_bps_round_trip=7.0),
        BacktestConfig(warmup=30, horizon=3, stride=1, fee_bps_round_trip=10.0, slippage_bps_round_trip=7.0),
        BacktestConfig(warmup=30, horizon=7, stride=1, fee_bps_round_trip=10.0, slippage_bps_round_trip=9.0),
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
            samples = float(metrics.get("sample_count") or 0.0)
            vol_skip = float(metrics.get("skipped_vol_shock") or 0.0)
            vol_skip_rate_pct = (vol_skip / (samples + vol_skip) * 100.0) if (samples + vol_skip) > 0 else 0.0
            eligible_for_best = (
                samples >= min_samples_for_best
                and float(metrics.get("max_drawdown_pct") or 0.0) <= max_drawdown_for_best_pct
                and vol_skip_rate_pct <= max_vol_shock_skip_rate_pct
            )
            row = {
                "period": f"{start}..{end}",
                "bars": int(len(df)),
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
                "eligible_for_best": eligible_for_best,
                "vol_shock_skip_rate_pct": round(vol_skip_rate_pct, 6),
                "score": round(_score(metrics), 6),
            }
            rows.append(row)
    rows_sorted = sorted(rows, key=lambda r: r["score"], reverse=True)
    eligible_rows = [r for r in rows_sorted if r.get("eligible_for_best")]
    best = eligible_rows[0] if eligible_rows else None
    return {
        "schema": "btc_time_machine_sweep_v1",
        "generated_at_utc": _z_now(),
        "symbol": "BTCUSDT",
        "periods": [f"{a}..{b}" for a, b in periods],
        "best_selection_constraints": {
            "min_samples_for_best": min_samples_for_best,
            "max_drawdown_for_best_pct": max_drawdown_for_best_pct,
            "max_vol_shock_skip_rate_pct": max_vol_shock_skip_rate_pct,
        },
        "rows": rows_sorted,
        "best": best,
    }


def main() -> int:
    ap = argparse.ArgumentParser(
        description="BTC causal time-machine sweep (Fact-Safe configs × periods)."
    )
    ap.add_argument(
        "--periods",
        default="",
        help="Override windows: 'YYYY-MM-DD:YYYY-MM-DD,...' (comma-separated start:end).",
    )
    ap.add_argument(
        "--output",
        "-o",
        default=str(OUT_PATH),
        help=f"Output JSON path (default: {OUT_PATH})",
    )
    args = ap.parse_args()
    if args.periods.strip():
        plist = _parse_periods_spec(args.periods.strip())
    else:
        plist = list(DEFAULT_PERIODS)
    doc = run_sweep(periods=plist)
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
