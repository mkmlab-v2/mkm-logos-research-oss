#!/usr/bin/env python3
# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.9, L:0.8, K:0.3, M:0.9}
# Balance: 91
# Purpose: Compute 48h scheduler stability metrics and gate.
# Keywords: stability, 48h, scheduler health, governance
from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"
DEFAULT_HEALTH_HISTORY = ART / "genius_governance_scheduler_health_history_log.jsonl"
DEFAULT_RECOVERY_HISTORY = ART / "genius_governance_scheduler_auto_recovery_history_log.jsonl"
DEFAULT_OUT = ART / "genius_governance_scheduler_stability_48h_latest.json"


def _iso_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_utc(ts: str) -> datetime | None:
    try:
        return datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except Exception:
        return None


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        if not line.strip():
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            rows.append(obj)
    return rows


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--health-history-jsonl", type=Path, default=DEFAULT_HEALTH_HISTORY)
    ap.add_argument("--recovery-history-jsonl", type=Path, default=DEFAULT_RECOVERY_HISTORY)
    ap.add_argument("--window-hours", type=int, default=48)
    ap.add_argument("--min-pass-ratio", type=float, default=0.95)
    ap.add_argument("--max-hold-streak", type=int, default=1)
    ap.add_argument("--max-recovery-attempts", type=int, default=2)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    now = datetime.now(timezone.utc)
    window_start = now - timedelta(hours=int(args.window_hours))

    health_rows = _read_jsonl(args.health_history_jsonl)
    health_window = []
    for row in health_rows:
        dt = _parse_utc(str(row.get("ts_utc") or ""))
        if dt is None or dt < window_start:
            continue
        health_window.append(row)

    statuses = [str(r.get("health_status") or "UNKNOWN").upper() for r in health_window]
    pass_count = sum(1 for s in statuses if s == "PASS")
    hold_count = sum(1 for s in statuses if s == "HOLD")
    total = len(statuses)
    pass_ratio = (pass_count / total) if total > 0 else 0.0

    max_streak = 0
    cur = 0
    for s in statuses:
        if s == "HOLD":
            cur += 1
            max_streak = max(max_streak, cur)
        else:
            cur = 0

    recovery_rows = _read_jsonl(args.recovery_history_jsonl)
    recovery_window = []
    for row in recovery_rows:
        dt = _parse_utc(str(row.get("ts_utc") or ""))
        if dt is None or dt < window_start:
            continue
        recovery_window.append(row)
    recovery_attempts = sum(1 for r in recovery_window if bool(r.get("attempted")))

    stable = (
        total > 0
        and pass_ratio >= float(args.min_pass_ratio)
        and max_streak <= int(args.max_hold_streak)
        and recovery_attempts <= int(args.max_recovery_attempts)
    )

    out = {
        "schema": "genius_governance_scheduler_stability_48h_v1",
        "generated_at_utc": _iso_now(),
        "inputs": {
            "health_history_jsonl": str(args.health_history_jsonl).replace("\\", "/"),
            "recovery_history_jsonl": str(args.recovery_history_jsonl).replace("\\", "/"),
            "window_hours": int(args.window_hours),
            "min_pass_ratio": float(args.min_pass_ratio),
            "max_hold_streak": int(args.max_hold_streak),
            "max_recovery_attempts": int(args.max_recovery_attempts),
        },
        "current": {
            "window_rows": total,
            "pass_count": pass_count,
            "hold_count": hold_count,
            "pass_ratio": round(pass_ratio, 4),
            "max_hold_streak": max_streak,
            "recovery_attempts": recovery_attempts,
            "stable_48h": stable,
        },
        "status": "PASS" if stable else "HOLD",
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "output_json": str(args.output_json).replace("\\", "/"), "status": out["status"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
