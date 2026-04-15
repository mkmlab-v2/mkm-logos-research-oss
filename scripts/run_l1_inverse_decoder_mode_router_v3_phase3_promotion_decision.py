# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.8, L:0.9, K:0.6, M:0.4}
# Balance: 90
# Purpose: Build phase-3 (100%) promotion decision from phase_2 canary window.
# Keywords: canary, promotion, phase3, decision, ops
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

DEFAULT_STATUS = ART / "l1_inverse_decoder_mode_router_v3_canary_status_latest.json"
DEFAULT_LOG = REPORTS / "l1_inverse_decoder_mode_router_v3_canary_log_v1.jsonl"
DEFAULT_OUT = ART / "l1_inverse_decoder_mode_router_v3_phase3_promotion_decision_v1.json"


def _now_utc() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def _parse_ts(raw: str) -> datetime:
    return datetime.fromisoformat(raw.replace("Z", "+00:00"))


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.exists():
        return rows
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        rows.append(json.loads(line))
    return rows


def _is_phase2_row(row: dict[str, Any]) -> bool:
    return row.get("phase") == "phase_2" or row.get("traffic_pct") == 30


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--status-artifact", type=Path, default=DEFAULT_STATUS)
    ap.add_argument("--canary-log", type=Path, default=DEFAULT_LOG)
    ap.add_argument("--window-hours", type=int, default=48)
    ap.add_argument("--min-observation-points", type=int, default=8)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    status = _read_json(args.status_artifact if args.status_artifact.is_absolute() else ROOT / args.status_artifact)
    logs = _read_jsonl(args.canary_log if args.canary_log.is_absolute() else ROOT / args.canary_log)

    now = _now_utc()
    window_start = now - timedelta(hours=args.window_hours)
    in_window: list[dict[str, Any]] = []
    for row in logs:
        ts = row.get("ts_utc")
        if not ts:
            continue
        try:
            dt = _parse_ts(ts)
        except ValueError:
            continue
        if dt >= window_start:
            in_window.append(row)

    phase2_rows = [r for r in in_window if _is_phase2_row(r)]
    total_points = len(phase2_rows)
    keep_points = sum(1 for r in phase2_rows if r.get("action") == "KEEP_CANARY")
    rollback_points = sum(1 for r in phase2_rows if r.get("action") == "ROLLBACK_TO_V4")

    latest_status_ok = bool(status.get("decision", {}).get("canary_ok", False))
    min_points_ok = total_points >= args.min_observation_points
    no_rollback_ok = rollback_points == 0
    keep_ratio = (keep_points / total_points) if total_points else 0.0
    keep_ratio_ok = keep_ratio >= 0.95

    if not min_points_ok:
        decision = "WAIT_MORE_OBSERVATION"
    elif latest_status_ok and no_rollback_ok and keep_ratio_ok:
        decision = "GO_PHASE3_100PCT"
    else:
        decision = "HOLD_PHASE2_OR_ROLLBACK"

    out_doc = {
        "schema": "l1_inverse_decoder_mode_router_v3_phase3_promotion_decision_v1",
        "generated_at_utc": now.isoformat(),
        "research_only": True,
        "inputs": {
            "status_artifact": str(args.status_artifact),
            "canary_log": str(args.canary_log),
            "window_hours": args.window_hours,
            "min_observation_points": args.min_observation_points,
            "phase_filter": "phase_2 or traffic_pct==30",
        },
        "window_summary": {
            "window_start_utc": window_start.isoformat(),
            "window_end_utc": now.isoformat(),
            "phase2_observation_points": total_points,
            "keep_points": keep_points,
            "rollback_points": rollback_points,
            "keep_ratio": keep_ratio,
        },
        "checks": {
            "latest_status_ok": latest_status_ok,
            "min_points_ok": min_points_ok,
            "no_rollback_ok": no_rollback_ok,
            "keep_ratio_ok": keep_ratio_ok,
        },
        "decision": decision,
        "next_action": (
            "Promote canary traffic to 100% with same rollback guard."
            if decision == "GO_PHASE3_100PCT"
            else (
                "Continue phase_2 monitoring until enough observation points."
                if decision == "WAIT_MORE_OBSERVATION"
                else "Keep phase_2 or rollback based on guard action."
            )
        ),
    }

    out_path = args.out if args.out.is_absolute() else ROOT / args.out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(out_path), "decision": decision, "phase2_points": total_points}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
