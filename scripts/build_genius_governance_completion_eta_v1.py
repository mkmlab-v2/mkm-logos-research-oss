#!/usr/bin/env python3
"""Build non-invasive completion_ready transition watcher with 24h ETA."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"
DEFAULT_COMPLETION_GATE = ART / "genius_governance_completion_gate_latest.json"
DEFAULT_HISTORY = ART / "genius_governance_scheduler_health_history_log.jsonl"
DEFAULT_OUT = ART / "genius_governance_completion_eta_latest.json"


def _iso_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_utc(ts: str) -> datetime | None:
    try:
        return datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except Exception:
        return None


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        obj = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return {}
    return obj if isinstance(obj, dict) else {}


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    out: list[dict[str, Any]] = []
    for ln in path.read_text(encoding="utf-8-sig").splitlines():
        s = ln.strip()
        if not s:
            continue
        try:
            obj = json.loads(s)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            out.append(obj)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--completion-gate-json", type=Path, default=DEFAULT_COMPLETION_GATE)
    ap.add_argument("--health-history-jsonl", type=Path, default=DEFAULT_HISTORY)
    ap.add_argument("--required-hours", type=float, default=24.0)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    now = datetime.now(timezone.utc)
    completion = _read_json(args.completion_gate_json)
    completion_ready = bool(completion.get("completion_ready"))

    rows = _read_jsonl(args.health_history_jsonl)
    parsed: list[tuple[datetime, str]] = []
    for row in rows:
        dt = _parse_utc(str(row.get("ts_utc") or ""))
        if dt is None:
            continue
        parsed.append((dt, str(row.get("health_status") or "UNKNOWN").upper()))
    parsed.sort(key=lambda x: x[0])

    # continuous PASS streak from latest backwards
    streak_start: datetime | None = None
    last_ts: datetime | None = parsed[-1][0] if parsed else None
    for dt, status in reversed(parsed):
        if status == "PASS":
            streak_start = dt
            continue
        break

    streak_hours = 0.0
    if streak_start is not None and last_ts is not None:
        streak_hours = max(0.0, (last_ts - streak_start).total_seconds() / 3600.0)

    remaining_hours = max(0.0, float(args.required_hours) - streak_hours)
    eta_utc = (now + timedelta(hours=remaining_hours)).strftime("%Y-%m-%dT%H:%M:%SZ")
    status = "TRACKING"
    if completion_ready and streak_hours >= float(args.required_hours):
        status = "READY_24H_WINDOW_MET"
    elif not completion_ready:
        status = "WAIT_COMPLETION_READY"

    out = {
        "schema": "genius_governance_completion_eta_v1",
        "generated_at_utc": _iso_now(),
        "inputs": {
            "completion_gate_json": str(args.completion_gate_json).replace("\\", "/"),
            "health_history_jsonl": str(args.health_history_jsonl).replace("\\", "/"),
            "required_hours": float(args.required_hours),
        },
        "current": {
            "completion_ready": completion_ready,
            "pass_streak_start_utc": streak_start.strftime("%Y-%m-%dT%H:%M:%SZ") if streak_start else None,
            "pass_streak_hours": round(streak_hours, 3),
            "remaining_hours_to_24h": round(remaining_hours, 3),
            "estimated_24h_eta_utc": eta_utc,
        },
        "status": status,
    }

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "output_json": str(args.output_json).replace("\\", "/"), "status": status}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
