#!/usr/bin/env python3
# @MKM12-METADATA
# Type: Engine
# Vector: {S:0.9, L:0.8, K:0.4, M:0.7}
# Balance: 91
# Purpose: Evaluate control/treatment/shadow trade performance and emit promotion gate decision JSON.
# Keywords: trading, promotion-gate, control, treatment, shadow, metrics

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PNL_KEYS = ("realized_pnl", "realized_pnl_usdt", "pnl", "pnl_usdt", "profit", "net_pnl")
HIT_KEYS = ("is_win", "win", "hit", "is_profit", "profitable")
EXIT_KEYS = ("closed", "is_closed", "status")
TIMESTAMP_KEYS = ("timestamp", "closed_at", "exit_time", "updated_at", "time")


@dataclass
class StrategyMetrics:
    name: str
    trades: int
    wins: int
    losses: int
    hit_rate: float
    net_pnl: float
    avg_pnl: float
    profit_factor: float
    max_drawdown: float


def _parse_args() -> argparse.Namespace:
    base_dir = Path(__file__).resolve().parent.parent / "exports" / "cursor_trade_history"
    parser = argparse.ArgumentParser(
        description="Evaluate strategy promotion gate from trade history JSON files."
    )
    parser.add_argument("--control-file", type=Path, default=base_dir / "trades_control.json")
    parser.add_argument("--treatment-file", type=Path, default=base_dir / "trades_treatment.json")
    parser.add_argument(
        "--shadow-file",
        type=Path,
        default=base_dir / "trades_treatment_v2_shadow.json",
        help="New theory strategy trade file for promotion evaluation.",
    )
    parser.add_argument(
        "--output-file",
        type=Path,
        default=base_dir / "strategy_promotion_gate_latest.json",
    )
    parser.add_argument("--min-trades", type=int, default=40)
    parser.add_argument("--min-trading-days", type=int, default=21)
    parser.add_argument("--min-net-pnl-uplift-ratio", type=float, default=0.05)
    parser.add_argument("--min-hit-rate-uplift", type=float, default=0.03)
    parser.add_argument("--max-mdd-worsen", type=float, default=0.01)
    parser.add_argument("--min-profit-factor", type=float, default=1.15)
    parser.add_argument("--min-winning-weeks", type=int, default=2)
    parser.add_argument("--required-weeks", type=int, default=3)
    return parser.parse_args()


def _load_array(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        return []
    return [row for row in payload if isinstance(row, dict)]


def _to_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _is_closed(trade: dict[str, Any]) -> bool:
    status = str(trade.get("status", "")).strip().lower()
    if status in {"open", "pending"}:
        return False
    if status in {"closed", "filled", "done"}:
        return True
    for key in EXIT_KEYS:
        value = trade.get(key)
        if isinstance(value, bool):
            return value
    return True


def _extract_pnl(trade: dict[str, Any]) -> float | None:
    for key in PNL_KEYS:
        if key in trade:
            pnl = _to_float(trade.get(key))
            if pnl is not None:
                return pnl
    return None


def _extract_hit(trade: dict[str, Any], pnl: float | None) -> bool | None:
    for key in HIT_KEYS:
        if key in trade:
            value = trade.get(key)
            if isinstance(value, bool):
                return value
            if isinstance(value, (int, float)):
                return float(value) > 0
            if isinstance(value, str):
                low = value.strip().lower()
                if low in {"win", "true", "1", "profit"}:
                    return True
                if low in {"loss", "false", "0"}:
                    return False
    if pnl is None:
        return None
    return pnl > 0


def _extract_timestamp(trade: dict[str, Any]) -> datetime | None:
    for key in TIMESTAMP_KEYS:
        raw = trade.get(key)
        if raw is None:
            continue
        if isinstance(raw, (int, float)):
            seconds = float(raw) / 1000.0 if float(raw) > 1_000_000_000_000 else float(raw)
            try:
                return datetime.fromtimestamp(seconds, tz=timezone.utc)
            except (OSError, ValueError):
                continue
        if isinstance(raw, str):
            value = raw.strip()
            if value.endswith("Z"):
                value = value[:-1] + "+00:00"
            try:
                dt = datetime.fromisoformat(value)
                return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
            except ValueError:
                continue
    return None


def _max_drawdown(pnls: list[float]) -> float:
    equity = 0.0
    peak = 0.0
    max_dd = 0.0
    for pnl in pnls:
        equity += pnl
        peak = max(peak, equity)
        max_dd = min(max_dd, equity - peak)
    return abs(max_dd)


def _build_metrics(name: str, trades: list[dict[str, Any]]) -> StrategyMetrics:
    closed = [t for t in trades if _is_closed(t)]
    pnls: list[float] = []
    wins = 0
    losses = 0
    gross_profit = 0.0
    gross_loss = 0.0

    for trade in closed:
        pnl = _extract_pnl(trade)
        hit = _extract_hit(trade, pnl)
        if pnl is not None:
            pnls.append(pnl)
            if pnl > 0:
                gross_profit += pnl
            elif pnl < 0:
                gross_loss += abs(pnl)
        if hit is True:
            wins += 1
        elif hit is False:
            losses += 1

    trades_count = len(closed)
    hit_rate = (wins / trades_count) if trades_count else 0.0
    net_pnl = sum(pnls)
    avg_pnl = (net_pnl / trades_count) if trades_count else 0.0
    profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else (999.0 if gross_profit > 0 else 0.0)
    mdd = _max_drawdown(pnls)
    return StrategyMetrics(
        name=name,
        trades=trades_count,
        wins=wins,
        losses=losses,
        hit_rate=hit_rate,
        net_pnl=net_pnl,
        avg_pnl=avg_pnl,
        profit_factor=profit_factor,
        max_drawdown=mdd,
    )


def _count_distinct_days(trades: list[dict[str, Any]]) -> int:
    days: set[str] = set()
    for t in trades:
        ts = _extract_timestamp(t)
        if ts is not None:
            days.add(ts.astimezone(timezone.utc).date().isoformat())
    return len(days)


def _weekly_win_count(shadow: list[dict[str, Any]], baseline: StrategyMetrics) -> int:
    weekly: dict[tuple[int, int], float] = {}
    for t in shadow:
        ts = _extract_timestamp(t)
        pnl = _extract_pnl(t)
        if ts is None or pnl is None:
            continue
        y, w, _ = ts.isocalendar()
        weekly[(y, w)] = weekly.get((y, w), 0.0) + pnl
    winning = 0
    baseline_weekly_avg = baseline.net_pnl / 3.0 if baseline.trades > 0 else 0.0
    for pnl in weekly.values():
        if pnl > baseline_weekly_avg:
            winning += 1
    return winning


def main() -> int:
    args = _parse_args()
    control = _load_array(args.control_file)
    treatment = _load_array(args.treatment_file)
    shadow = _load_array(args.shadow_file)

    control_metrics = _build_metrics("control", control)
    treatment_metrics = _build_metrics("treatment", treatment)
    shadow_metrics = _build_metrics("treatment_v2_shadow", shadow)
    baseline = treatment_metrics if treatment_metrics.trades >= control_metrics.trades else control_metrics

    distinct_days = _count_distinct_days(shadow)
    weekly_wins = _weekly_win_count(shadow, baseline)
    pnl_uplift = (
        (shadow_metrics.net_pnl - baseline.net_pnl) / abs(baseline.net_pnl)
        if baseline.net_pnl != 0
        else (1.0 if shadow_metrics.net_pnl > 0 else 0.0)
    )
    hit_uplift = shadow_metrics.hit_rate - baseline.hit_rate
    mdd_worsen = shadow_metrics.max_drawdown - baseline.max_drawdown

    checks = {
        "min_trades": shadow_metrics.trades >= args.min_trades,
        "min_trading_days": distinct_days >= args.min_trading_days,
        "net_pnl_uplift": pnl_uplift >= args.min_net_pnl_uplift_ratio,
        "hit_rate_uplift": hit_uplift >= args.min_hit_rate_uplift,
        "max_drawdown_guard": mdd_worsen <= args.max_mdd_worsen,
        "profit_factor": shadow_metrics.profit_factor >= args.min_profit_factor,
        "weekly_consistency": weekly_wins >= args.min_winning_weeks,
    }
    passed = all(checks.values())

    report = {
        "schema": "strategy_promotion_gate_v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "inputs": {
            "control_file": str(args.control_file),
            "treatment_file": str(args.treatment_file),
            "shadow_file": str(args.shadow_file),
        },
        "thresholds": {
            "min_trades": args.min_trades,
            "min_trading_days": args.min_trading_days,
            "min_net_pnl_uplift_ratio": args.min_net_pnl_uplift_ratio,
            "min_hit_rate_uplift": args.min_hit_rate_uplift,
            "max_mdd_worsen": args.max_mdd_worsen,
            "min_profit_factor": args.min_profit_factor,
            "min_winning_weeks": args.min_winning_weeks,
            "required_weeks": args.required_weeks,
        },
        "metrics": {
            "control": asdict(control_metrics),
            "treatment": asdict(treatment_metrics),
            "shadow": asdict(shadow_metrics),
        },
        "comparison": {
            "baseline": baseline.name,
            "distinct_trading_days_shadow": distinct_days,
            "weekly_wins_shadow": weekly_wins,
            "weekly_required_window": args.required_weeks,
            "net_pnl_uplift_ratio_vs_baseline": pnl_uplift,
            "hit_rate_uplift_vs_baseline": hit_uplift,
            "max_drawdown_worsen_vs_baseline": mdd_worsen,
        },
        "checks": checks,
        "decision": {
            "promotion_ready": passed,
            "recommended_mode": "promote_limited_capital" if passed else "hold_shadow",
        },
    }

    args.output_file.parent.mkdir(parents=True, exist_ok=True)
    args.output_file.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"[OK] wrote: {args.output_file}")
    print(f"promotion_ready={passed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
