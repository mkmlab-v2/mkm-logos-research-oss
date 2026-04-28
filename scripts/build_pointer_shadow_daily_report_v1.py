#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
ART = ROOT / "docs" / "final" / "artifacts"
REPORTS = ROOT / "reports"

SHADOW_SNAPSHOT_DEFAULT = ART / "pointer_hash_snapping_router_shadow_latest.json"
LOG_DEFAULT = REPORTS / "pointer_hash_snapping_router_shadow_log_v1.jsonl"
OUT_DEFAULT = ART / "pointer_hash_snapping_router_shadow_daily_report_latest.json"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _append_jsonl(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def _read_recent(path: Path, since: datetime) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    out: list[dict[str, Any]] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        ts = row.get("ts_utc")
        if not isinstance(ts, str):
            continue
        try:
            dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        except ValueError:
            continue
        if dt >= since:
            out.append(row)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--shadow-snapshot", type=Path, default=SHADOW_SNAPSHOT_DEFAULT)
    ap.add_argument("--log-jsonl", type=Path, default=LOG_DEFAULT)
    ap.add_argument("--window-hours", type=int, default=24)
    ap.add_argument("--out", type=Path, default=OUT_DEFAULT)
    args = ap.parse_args()

    snap_path = args.shadow_snapshot if args.shadow_snapshot.is_absolute() else ROOT / args.shadow_snapshot
    log_path = args.log_jsonl if args.log_jsonl.is_absolute() else ROOT / args.log_jsonl
    out_path = args.out if args.out.is_absolute() else ROOT / args.out

    snap = _read_json(snap_path)
    rows = snap.get("rows", [])
    summary = snap.get("summary", {})

    # Log one snapshot summary point
    point = {
        "ts_utc": _now().replace(microsecond=0).isoformat(),
        "schema": "pointer_hash_snapping_router_shadow_log_v1",
        "input_count": int(snap.get("inputs", {}).get("input_count", len(rows))),
        "pointer_candidate_ok_count": int(summary.get("pointer_candidate_ok_count", 0)),
        "selected_pointer_count": int(summary.get("selected_pointer_count", 0)),
        "selected_track_a_count": int(summary.get("selected_track_a_count", 0)),
        "snap_event_count": int(sum(len(r.get("snap_events", [])) for r in rows if isinstance(r, dict))),
        "oov_unresolved_token_count": int(
            sum(len(r.get("unresolved_tokens", [])) for r in rows if isinstance(r, dict))
        ),
    }
    _append_jsonl(log_path, point)

    since = _now() - timedelta(hours=max(1, args.window_hours))
    recent = _read_recent(log_path, since)
    n = len(recent)
    agg = {
        "avg_input_count": 0.0,
        "avg_pointer_candidate_ok_rate": 0.0,
        "avg_snap_event_rate": 0.0,
        "avg_unresolved_token_per_run": 0.0,
    }
    if n > 0:
        total_inputs = sum(float(r.get("input_count", 0)) for r in recent)
        total_ok = sum(float(r.get("pointer_candidate_ok_count", 0)) for r in recent)
        total_snap = sum(float(r.get("snap_event_count", 0)) for r in recent)
        total_unresolved = sum(float(r.get("oov_unresolved_token_count", 0)) for r in recent)
        agg["avg_input_count"] = total_inputs / float(n)
        agg["avg_pointer_candidate_ok_rate"] = total_ok / float(max(1.0, total_inputs))
        agg["avg_snap_event_rate"] = total_snap / float(max(1.0, total_inputs))
        agg["avg_unresolved_token_per_run"] = total_unresolved / float(n)

    out_doc = {
        "schema": "pointer_hash_snapping_router_shadow_daily_report_v1",
        "generated_at_utc": _now().replace(microsecond=0).isoformat(),
        "research_only": True,
        "source_track": "B",
        "inputs": {
            "shadow_snapshot": str(snap_path),
            "log_jsonl": str(log_path),
            "window_hours": args.window_hours,
        },
        "latest_point": point,
        "window_stats": {
            "sample_count": n,
            **agg,
        },
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(out_path), "sample_count": n}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
