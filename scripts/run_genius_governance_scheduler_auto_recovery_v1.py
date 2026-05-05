#!/usr/bin/env python3
# @MKM12-METADATA
# Type: Engine
# Vector: {S:0.9, L:0.7, K:0.7, M:0.8}
# Balance: 90
# Purpose: Trigger automated recovery when scheduler health stays HOLD consecutively.
# Keywords: auto recovery, scheduler health, hold streak, scheduled task
from __future__ import annotations

import argparse
import json
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"
DEFAULT_HISTORY = ART / "genius_governance_scheduler_health_history_log.jsonl"
DEFAULT_RECOVERY_HISTORY = ART / "genius_governance_scheduler_auto_recovery_history_log.jsonl"
DEFAULT_OUT = ART / "genius_governance_scheduler_auto_recovery_latest.json"


def _iso_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_utc(ts: str) -> datetime | None:
    try:
        return datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except Exception:
        return None


def _read_tail(path: Path, n: int = 10) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    lines = [ln for ln in path.read_text(encoding="utf-8-sig").splitlines() if ln.strip()]
    rows: list[dict[str, Any]] = []
    for ln in lines[-n:]:
        try:
            obj = json.loads(ln)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            rows.append(obj)
    return rows


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--health-history-jsonl", type=Path, default=DEFAULT_HISTORY)
    ap.add_argument("--recovery-history-jsonl", type=Path, default=DEFAULT_RECOVERY_HISTORY)
    ap.add_argument("--hold-streak-threshold", type=int, default=2)
    ap.add_argument("--cooldown-minutes", type=int, default=120)
    ap.add_argument("--recovery-task-name", type=str, default=r"\MKM_GeniusHumanReview_HoldRehearsal_Monthly")
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    rows = _read_tail(args.health_history_jsonl, n=max(10, args.hold_streak_threshold + 2))
    statuses = [str(r.get("health_status") or "UNKNOWN").upper() for r in rows]
    hold_streak = 0
    for s in reversed(statuses):
        if s == "HOLD":
            hold_streak += 1
        else:
            break
    should_recover = hold_streak >= int(args.hold_streak_threshold)

    now = datetime.now(timezone.utc)
    recovery_rows = _read_tail(args.recovery_history_jsonl, n=50)
    last_recovery_ts = None
    for rr in reversed(recovery_rows):
        if bool(rr.get("attempted")):
            dt = _parse_utc(str(rr.get("ts_utc") or ""))
            if dt is not None:
                last_recovery_ts = dt
                break
    in_cooldown = False
    if last_recovery_ts is not None:
        in_cooldown = now < last_recovery_ts + timedelta(minutes=int(args.cooldown_minutes))

    attempted = False
    recovery_exit_code = None
    recovery_note = "no_action"
    if should_recover and not in_cooldown:
        attempted = True
        cp = subprocess.run(["schtasks", "/Run", "/TN", args.recovery_task_name], check=False, capture_output=True, text=True, encoding="utf-8", errors="replace")
        recovery_exit_code = cp.returncode
        recovery_note = "triggered" if cp.returncode == 0 else "trigger_failed"
    elif should_recover and in_cooldown:
        recovery_note = "cooldown_active"
    elif not should_recover:
        recovery_note = "hold_streak_below_threshold"

    out = {
        "schema": "genius_governance_scheduler_auto_recovery_v1",
        "generated_at_utc": _iso_now(),
        "inputs": {
            "health_history_jsonl": str(args.health_history_jsonl).replace("\\", "/"),
            "recovery_history_jsonl": str(args.recovery_history_jsonl).replace("\\", "/"),
            "hold_streak_threshold": int(args.hold_streak_threshold),
            "cooldown_minutes": int(args.cooldown_minutes),
            "recovery_task_name": args.recovery_task_name,
        },
        "current": {
            "hold_streak": hold_streak,
            "should_recover": should_recover,
            "in_cooldown": in_cooldown,
            "last_recovery_ts_utc": last_recovery_ts.strftime("%Y-%m-%dT%H:%M:%SZ") if last_recovery_ts else None,
        },
        "recovery": {
            "attempted": attempted,
            "exit_code": recovery_exit_code,
            "note": recovery_note,
        },
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    rec_row = {
        "schema": "genius_governance_scheduler_auto_recovery_history_row_v1",
        "ts_utc": _iso_now(),
        "hold_streak": hold_streak,
        "should_recover": should_recover,
        "in_cooldown": in_cooldown,
        "attempted": attempted,
        "recovery_note": recovery_note,
        "recovery_exit_code": recovery_exit_code,
    }
    args.recovery_history_jsonl.parent.mkdir(parents=True, exist_ok=True)
    with args.recovery_history_jsonl.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec_row, ensure_ascii=False) + "\n")

    print(json.dumps({"ok": True, "output_json": str(args.output_json).replace("\\", "/"), "attempted": attempted, "note": recovery_note}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
