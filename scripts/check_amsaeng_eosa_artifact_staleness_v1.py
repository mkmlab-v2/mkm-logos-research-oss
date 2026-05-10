"""
Meta-watchdog: heartbeat / bundle-cycle JSON freshness (runs outside successful bundle tail).

Exit codes: 0 OK, 1 stale/degraded, 2 missing heartbeat (critical).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _parse_iso(ts: str | None) -> datetime | None:
    if not ts or not isinstance(ts, str):
        return None
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone(timezone.utc)
    except ValueError:
        return None


def main() -> int:
    p = argparse.ArgumentParser(description="Check Amsaeng-Eosa artifact staleness (heartbeat / bundle cycle JSON).")
    p.add_argument("--workspace-root", default="C:/workspace")
    p.add_argument(
        "--heartbeat-max-age-minutes",
        type=float,
        default=float(os.environ.get("AMSENG_HEARTBEAT_MAX_AGE_MINUTES", "130")),
        help="Max age for reports/amsaeng_eosa_monitoring_heartbeat_latest.json generated_at_utc (default 130).",
    )
    p.add_argument(
        "--bundle-cycle-max-age-minutes",
        type=float,
        default=float(os.environ.get("AMSENG_BUNDLE_CYCLE_MAX_AGE_MINUTES", "130")),
        help="Max age for reports/amsaeng_eosa_bundle_cycle_latest.json completed_at_utc if present.",
    )
    p.add_argument(
        "--out-json",
        default="",
        help="Override output path (default: reports/amsaeng_eosa_staleness_probe_latest.json under workspace).",
    )
    args = p.parse_args()
    root = Path(args.workspace_root)
    out_path = Path(args.out_json) if args.out_json else root / "reports" / "amsaeng_eosa_staleness_probe_latest.json"

    hb_path = root / "reports" / "amsaeng_eosa_monitoring_heartbeat_latest.json"
    bc_path = root / "reports" / "amsaeng_eosa_bundle_cycle_latest.json"

    now = datetime.now(timezone.utc)
    worst = 0
    payload: dict[str, Any] = {
        "schema": "amsaeng_eosa_staleness_probe_v1",
        "generated_at_utc": now.isoformat(),
        "workspace_root": str(root),
        "heartbeat_path": str(hb_path),
        "bundle_cycle_path": str(bc_path),
        "heartbeat_max_age_minutes": args.heartbeat_max_age_minutes,
        "bundle_cycle_max_age_minutes": args.bundle_cycle_max_age_minutes,
        "heartbeat": {},
        "bundle_cycle": {},
        "worst_exit": 0,
    }

    if not hb_path.exists():
        worst = max(worst, 2)
        payload["heartbeat"] = {"status": "missing"}
    else:
        try:
            hb = json.loads(hb_path.read_text(encoding="utf-8-sig"))
        except json.JSONDecodeError:
            worst = max(worst, 2)
            payload["heartbeat"] = {"status": "invalid_json"}
        else:
            ts = _parse_iso(hb.get("generated_at_utc"))
            if ts is None:
                worst = max(worst, 2)
                payload["heartbeat"] = {"status": "no_timestamp"}
            else:
                age_min = (now - ts).total_seconds() / 60.0
                stale = age_min > args.heartbeat_max_age_minutes
                if stale:
                    worst = max(worst, 1)
                payload["heartbeat"] = {
                    "status": "stale" if stale else "ok",
                    "age_minutes": round(age_min, 3),
                    "threshold_minutes": args.heartbeat_max_age_minutes,
                }

    if bc_path.exists():
        try:
            bc = json.loads(bc_path.read_text(encoding="utf-8-sig"))
        except json.JSONDecodeError:
            worst = max(worst, 1)
            payload["bundle_cycle"] = {"status": "invalid_json"}
        else:
            ts = _parse_iso(bc.get("completed_at_utc"))
            if ts is None:
                worst = max(worst, 1)
                payload["bundle_cycle"] = {"status": "no_completed_at"}
            else:
                age_min = (now - ts).total_seconds() / 60.0
                stale = age_min > args.bundle_cycle_max_age_minutes
                if stale:
                    worst = max(worst, 1)
                payload["bundle_cycle"] = {
                    "status": "stale" if stale else "ok",
                    "age_minutes": round(age_min, 3),
                    "threshold_minutes": args.bundle_cycle_max_age_minutes,
                    "overall_status": bc.get("overall_status"),
                }
    else:
        payload["bundle_cycle"] = {"status": "missing_file"}

    payload["worst_exit"] = worst
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"amsaeng_eosa_staleness_probe_written={out_path} worst_exit={worst}")
    return worst


if __name__ == "__main__":
    raise SystemExit(main())
