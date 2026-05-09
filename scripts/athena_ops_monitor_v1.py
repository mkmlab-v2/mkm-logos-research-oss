from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Operational monitor for 24/7 automation status."
    )
    parser.add_argument(
        "--metrics-path",
        required=True,
        help="Input metrics JSON path.",
    )
    parser.add_argument(
        "--output-path",
        default="reports/athena_ops_status_latest.json",
        help="Output status JSON path.",
    )
    parser.add_argument(
        "--slow-latency-ms",
        type=float,
        default=500.0,
        help="Latency threshold for SLOW mode.",
    )
    parser.add_argument(
        "--safe-latency-ms",
        type=float,
        default=1200.0,
        help="Latency threshold for SAFE mode.",
    )
    parser.add_argument(
        "--loss-cut-pct",
        type=float,
        default=2.0,
        help="Daily loss percentage threshold for SAFE mode.",
    )
    parser.add_argument(
        "--position-cut-pct",
        type=float,
        default=90.0,
        help="Position usage percentage threshold for SAFE mode.",
    )
    return parser.parse_args()


def _num(value: Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def evaluate_mode(
    metrics: dict[str, Any],
    slow_latency_ms: float,
    safe_latency_ms: float,
    loss_cut_pct: float,
    position_cut_pct: float,
) -> tuple[str, list[str]]:
    reasons: list[str] = []
    latency = _num(metrics.get("api_latency_ms"), 0.0)
    loss_pct = _num(metrics.get("daily_loss_pct"), 0.0)
    pos_usage_pct = _num(metrics.get("position_usage_pct"), 0.0)
    connected = bool(metrics.get("exchange_connected", True))

    if not connected:
        reasons.append("exchange_disconnected")
    if latency >= safe_latency_ms:
        reasons.append(f"latency_ge_safe:{latency:.1f}")
    if loss_pct >= loss_cut_pct:
        reasons.append(f"loss_ge_cut:{loss_pct:.4f}")
    if pos_usage_pct >= position_cut_pct:
        reasons.append(f"position_ge_cut:{pos_usage_pct:.2f}")

    if reasons:
        return "SAFE", reasons

    if latency >= slow_latency_ms:
        return "SLOW", [f"latency_ge_slow:{latency:.1f}"]

    return "NORMAL", []


def main() -> int:
    args = parse_args()
    metrics_path = Path(args.metrics_path)
    if not metrics_path.exists():
        print("ops_monitor_failed=missing_metrics")
        return 3

    metrics = json.loads(metrics_path.read_text(encoding="utf-8-sig"))
    mode, reasons = evaluate_mode(
        metrics=metrics,
        slow_latency_ms=args.slow_latency_ms,
        safe_latency_ms=args.safe_latency_ms,
        loss_cut_pct=args.loss_cut_pct,
        position_cut_pct=args.position_cut_pct,
    )

    result = {
        "schema": "athena_ops_status_v1",
        "ts_utc": datetime.now(timezone.utc).isoformat(),
        "mode": mode,
        "reasons": reasons,
        "input_metrics": {
            "api_latency_ms": metrics.get("api_latency_ms", None),
            "daily_loss_pct": metrics.get("daily_loss_pct", None),
            "position_usage_pct": metrics.get("position_usage_pct", None),
            "exchange_connected": metrics.get("exchange_connected", None),
        },
    }
    output_path = Path(args.output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"ops_mode={mode} output_path={output_path.as_posix()}")
    return 0 if mode != "SAFE" else 2


if __name__ == "__main__":
    raise SystemExit(main())
