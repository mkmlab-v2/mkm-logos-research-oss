#!/usr/bin/env python3
"""Build D+7 stability checklist for pure-real maintenance mode."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"

DEFAULT_PROGRESS = ART / "logos_pure_real_progress_report_latest.json"
DEFAULT_GO_NOGO = ART / "logos_pure_real_daily_go_nogo_latest.json"
DEFAULT_GATE_WEEKLY = ART / "logos_pure_real_execution_gate_weekly_alert_latest.json"
DEFAULT_BACKFILL_MONITOR = ART / "logos_backfill_dependence_monitor_latest.json"
DEFAULT_OUT = ART / "logos_pure_real_d7_stability_checklist_latest.json"


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    ap = argparse.ArgumentParser(description="Build D+7 stability checklist.")
    ap.add_argument("--progress-json", type=Path, default=DEFAULT_PROGRESS)
    ap.add_argument("--go-nogo-json", type=Path, default=DEFAULT_GO_NOGO)
    ap.add_argument("--weekly-alert-json", type=Path, default=DEFAULT_GATE_WEEKLY)
    ap.add_argument("--backfill-monitor-json", type=Path, default=DEFAULT_BACKFILL_MONITOR)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    progress = _load_json(args.progress_json)
    go_nogo = _load_json(args.go_nogo_json)
    weekly = _load_json(args.weekly_alert_json)
    monitor = _load_json(args.backfill_monitor_json)

    cp = progress.get("checkpoint") or {}
    current_unique_days = int(cp.get("current_unique_days") or 0)
    target_unique_days = int(cp.get("target_unique_days") or 30)
    go_decision = str(go_nogo.get("decision") or "")
    weekly_alert = bool(weekly.get("is_alert", False))
    delta_status = str(monitor.get("status") or "MISSING")
    delta_value = (monitor.get("metrics") or {}).get("delta_mixed_minus_pure")

    check_day30_maintained = current_unique_days >= target_unique_days
    check_today_go = go_decision == "GO"
    check_weekly_alert_stable = not weekly_alert
    check_delta_verified = delta_status == "PASS_LOW_BACKFILL_DEPENDENCE"

    checklist = [
        {
            "id": "day30_maintained",
            "label": "Day30 unique-day target is maintained",
            "status": "PASS" if check_day30_maintained else "FAIL",
            "evidence": {"current_unique_days": current_unique_days, "target_unique_days": target_unique_days},
        },
        {
            "id": "daily_go",
            "label": "Daily GO/NO_GO is GO",
            "status": "PASS" if check_today_go else "FAIL",
            "evidence": {"decision": go_decision},
        },
        {
            "id": "weekly_alert_stable",
            "label": "Weekly execution-gate alert is not active",
            "status": "PASS" if check_weekly_alert_stable else "FAIL",
            "evidence": {"is_alert": weekly_alert},
        },
        {
            "id": "delta_verified",
            "label": "Backfill delta is verified with PASS status",
            "status": "PASS" if check_delta_verified else "WARN",
            "evidence": {"backfill_dependence_status": delta_status, "delta_mixed_minus_pure": delta_value},
        },
    ]

    pass_count = sum(1 for x in checklist if x["status"] == "PASS")
    fail_count = sum(1 for x in checklist if x["status"] == "FAIL")
    warn_count = sum(1 for x in checklist if x["status"] == "WARN")

    if fail_count > 0:
        overall = "FAIL_NOT_STABLE_YET"
    elif warn_count > 0:
        overall = "WARN_PARTIAL_STABILITY"
    else:
        overall = "PASS_STABLE_D7_READY"

    out = {
        "schema": "logos_pure_real_d7_stability_checklist_v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "source_track": "B",
        "research_only": True,
        "auto_bind_to_atrack_forbidden": True,
        "summary": {
            "overall_status": overall,
            "pass_count": pass_count,
            "warn_count": warn_count,
            "fail_count": fail_count,
        },
        "checklist": checklist,
    }

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {"ok": True, "output_json": str(args.output_json), "overall_status": overall},
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

