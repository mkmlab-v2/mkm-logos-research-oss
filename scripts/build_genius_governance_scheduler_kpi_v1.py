#!/usr/bin/env python3
# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.9, L:0.8, K:0.4, M:0.9}
# Balance: 91
# Purpose: Build 24h/7d KPI report for scheduler governance reliability.
# Keywords: kpi, mttr, hold recurrence, pass ratio, scheduler
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
DEFAULT_OUT = ART / "genius_governance_scheduler_kpi_latest.json"


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
    for ln in path.read_text(encoding="utf-8-sig").splitlines():
        if not ln.strip():
            continue
        try:
            obj = json.loads(ln)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            rows.append(obj)
    return rows


def _window_rows(rows: list[dict[str, Any]], hours: int) -> list[tuple[datetime, dict[str, Any]]]:
    cut = datetime.now(timezone.utc) - timedelta(hours=hours)
    out: list[tuple[datetime, dict[str, Any]]] = []
    for row in rows:
        dt = _parse_utc(str(row.get("ts_utc") or ""))
        if dt is None or dt < cut:
            continue
        out.append((dt, row))
    out.sort(key=lambda x: x[0])
    return out


def _compute_mttr_minutes(window_health: list[tuple[datetime, dict[str, Any]]]) -> float | None:
    # MTTR approximation: time from HOLD start to next PASS.
    hold_start = None
    durations = []
    for dt, row in window_health:
        status = str(row.get("health_status") or "UNKNOWN").upper()
        if status == "HOLD" and hold_start is None:
            hold_start = dt
        elif status == "PASS" and hold_start is not None:
            durations.append((dt - hold_start).total_seconds() / 60.0)
            hold_start = None
    if not durations:
        return None
    return round(sum(durations) / len(durations), 3)


def _metrics_for_hours(health_rows: list[tuple[datetime, dict[str, Any]]], recovery_rows: list[tuple[datetime, dict[str, Any]]]) -> dict[str, Any]:
    statuses = [str(r.get("health_status") or "UNKNOWN").upper() for _, r in health_rows]
    total = len(statuses)
    pass_count = sum(1 for s in statuses if s == "PASS")
    hold_count = sum(1 for s in statuses if s == "HOLD")
    pass_ratio = (pass_count / total) if total > 0 else 0.0
    hold_recurrence_rate = (hold_count / total) if total > 0 else 0.0
    recovery_attempts = sum(1 for _, r in recovery_rows if bool(r.get("attempted")))
    mttr_minutes = _compute_mttr_minutes(health_rows)
    return {
        "window_rows": total,
        "pass_count": pass_count,
        "hold_count": hold_count,
        "pass_ratio": round(pass_ratio, 4),
        "hold_recurrence_rate": round(hold_recurrence_rate, 4),
        "recovery_attempts": recovery_attempts,
        "mttr_minutes": mttr_minutes,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--health-history-jsonl", type=Path, default=DEFAULT_HEALTH_HISTORY)
    ap.add_argument("--recovery-history-jsonl", type=Path, default=DEFAULT_RECOVERY_HISTORY)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    health = _read_jsonl(args.health_history_jsonl)
    recovery = _read_jsonl(args.recovery_history_jsonl)
    health_24h = _window_rows(health, 24)
    health_7d = _window_rows(health, 24 * 7)
    recovery_24h = _window_rows(recovery, 24)
    recovery_7d = _window_rows(recovery, 24 * 7)

    out = {
        "schema": "genius_governance_scheduler_kpi_v1",
        "generated_at_utc": _iso_now(),
        "inputs": {
            "health_history_jsonl": str(args.health_history_jsonl).replace("\\", "/"),
            "recovery_history_jsonl": str(args.recovery_history_jsonl).replace("\\", "/"),
        },
        "kpi": {
            "last_24h": _metrics_for_hours(health_24h, recovery_24h),
            "last_7d": _metrics_for_hours(health_7d, recovery_7d),
        },
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "output_json": str(args.output_json).replace("\\", "/")}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
