#!/usr/bin/env python3
"""Enforce minimum AROON_ORDER_QTY until enough realized samples accumulate."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_ENV = Path("/opt/bitcoin-trading-live/.env")
DEFAULT_EXPECTANCY = Path("/opt/bitcoin-trading-live/docs/final/artifacts/recent_trade_expectancy_latest.json")
DEFAULT_OUT = Path("/opt/bitcoin-trading-live/docs/final/artifacts/min_test_size_guard_latest.json")


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


def _write(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Force min size until realized sample threshold is met.")
    ap.add_argument("--env-file", type=Path, default=DEFAULT_ENV)
    ap.add_argument("--expectancy-json", type=Path, default=DEFAULT_EXPECTANCY)
    ap.add_argument("--min-samples", type=int, default=30)
    ap.add_argument("--min-qty", type=str, default="0.001")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args(argv)

    exp = _read_json(args.expectancy_json)
    sample = exp.get("sample") if isinstance(exp.get("sample"), dict) else {}
    n = int(sample.get("realized_rows_used") or 0)
    cur_qty = _read_env_value(args.env_file, "AROON_ORDER_QTY")
    changed = False
    action = "none"

    if n < int(args.min_samples):
        if cur_qty != args.min_qty:
            _set_env_value(args.env_file, "AROON_ORDER_QTY", args.min_qty)
            changed = True
            action = "forced_min_qty"
        else:
            action = "already_min_qty"
    else:
        action = "threshold_met_no_force"

    payload = {
        "schema": "min_test_size_guard_v1",
        "generated_at_utc": _utc_now(),
        "ok": True,
        "realized_rows_used": n,
        "min_samples": int(args.min_samples),
        "qty_before": cur_qty,
        "qty_after": _read_env_value(args.env_file, "AROON_ORDER_QTY"),
        "changed": changed,
        "action": action,
    }
    _write(args.out, payload)
    print(json.dumps(payload, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
