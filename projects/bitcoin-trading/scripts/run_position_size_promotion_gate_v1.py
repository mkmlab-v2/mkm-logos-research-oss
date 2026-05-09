#!/usr/bin/env python3
"""Position size promotion gate for unstable-stage protection.

Promote from min test size only when all gates pass:
- realized sample size threshold
- positive expectancy threshold
- max loss streak threshold
"""
from __future__ import annotations

import argparse
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_ENV = Path("/opt/bitcoin-trading-live/.env")
DEFAULT_EXPECTANCY = Path("/opt/bitcoin-trading-live/docs/final/artifacts/recent_trade_expectancy_latest.json")
DEFAULT_DECOMP = Path("/opt/bitcoin-trading-live/docs/final/artifacts/recent_loss_decomposition_latest.json")
DEFAULT_OUT = Path("/opt/bitcoin-trading-live/docs/final/artifacts/position_size_promotion_gate_latest.json")


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return obj if isinstance(obj, dict) else {}


def _read_env_value(path: Path, key: str) -> str | None:
    if not path.is_file():
        return None
    for ln in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        if ln.startswith(f"{key}="):
            return ln.split("=", 1)[1].strip()
    return None


def _set_env_value(path: Path, key: str, value: str) -> None:
    lines = path.read_text(encoding="utf-8", errors="ignore").splitlines() if path.is_file() else []
    out: list[str] = []
    replaced = False
    for ln in lines:
        if ln.startswith(f"{key}="):
            out.append(f"{key}={value}")
            replaced = True
        else:
            out.append(ln)
    if not replaced:
        out.append(f"{key}={value}")
    path.write_text("\n".join(out) + "\n", encoding="utf-8")


def _to_int(v: Any, default: int = 0) -> int:
    try:
        return int(v)
    except (TypeError, ValueError):
        return default


def _to_float(v: Any, default: float = 0.0) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def _write(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Promote AROON_ORDER_QTY only when all safety gates pass.")
    ap.add_argument("--env-file", type=Path, default=DEFAULT_ENV)
    ap.add_argument("--expectancy-json", type=Path, default=DEFAULT_EXPECTANCY)
    ap.add_argument("--decomposition-json", type=Path, default=DEFAULT_DECOMP)
    ap.add_argument("--min-qty", default="0.001")
    ap.add_argument("--promoted-qty", default="0.003")
    ap.add_argument("--min-samples", type=int, default=30)
    ap.add_argument("--min-expectancy", type=float, default=0.0)
    ap.add_argument("--max-loss-streak", type=int, default=2)
    ap.add_argument("--pm2-app", default="bitcoin-live-small-24h")
    ap.add_argument("--restart-on-change", action="store_true")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args(argv)

    exp = _read_json(args.expectancy_json)
    dec = _read_json(args.decomposition_json)
    sample = exp.get("sample") if isinstance(exp.get("sample"), dict) else {}
    metrics = exp.get("metrics") if isinstance(exp.get("metrics"), dict) else {}
    summary = dec.get("summary") if isinstance(dec.get("summary"), dict) else {}

    n = _to_int(sample.get("realized_rows_used"), 0)
    expectancy = _to_float(metrics.get("expectancy_per_realized_fill"), 0.0)
    max_loss_streak = _to_int(summary.get("max_loss_streak"), 99)

    gates = {
        "sample_gate": n >= int(args.min_samples),
        "expectancy_gate": expectancy > float(args.min_expectancy),
        "loss_streak_gate": max_loss_streak <= int(args.max_loss_streak),
    }
    all_pass = all(gates.values())

    qty_before = _read_env_value(args.env_file, "AROON_ORDER_QTY")
    target_qty = args.promoted_qty if all_pass else args.min_qty
    changed = qty_before != target_qty
    restarted = False
    restart_note = None

    if changed:
        _set_env_value(args.env_file, "AROON_ORDER_QTY", target_qty)
        if args.restart_on_change:
            p = subprocess.run(
                ["pm2", "restart", args.pm2_app, "--update-env"],
                text=True,
                capture_output=True,
            )
            restarted = p.returncode == 0
            restart_note = (p.stdout or p.stderr or "").strip()[-400:]

    payload = {
        "schema": "position_size_promotion_gate_v1",
        "generated_at_utc": _utc_now(),
        "ok": True,
        "inputs": {
            "realized_rows_used": n,
            "expectancy_per_realized_fill": expectancy,
            "max_loss_streak": max_loss_streak,
        },
        "thresholds": {
            "min_samples": int(args.min_samples),
            "min_expectancy": float(args.min_expectancy),
            "max_loss_streak": int(args.max_loss_streak),
        },
        "gates": gates,
        "decision": "promote" if all_pass else "hold_min",
        "qty_before": qty_before,
        "qty_after": _read_env_value(args.env_file, "AROON_ORDER_QTY"),
        "changed": changed,
        "restart_on_change": bool(args.restart_on_change),
        "pm2_restarted": restarted,
        "pm2_note": restart_note,
    }
    _write(args.out, payload)
    print(json.dumps(payload, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
