#!/usr/bin/env python3
"""Build daily action pack from pure-real planning artifacts."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"

DEFAULT_PROGRESS = ART / "logos_pure_real_progress_report_latest.json"
DEFAULT_MIN_INTAKE = ART / "logos_pure_real_minimum_intake_plan_latest.json"
DEFAULT_STATUS = ART / "logos_pure_real_daily_execution_status_latest.json"
DEFAULT_CATCHUP = ART / "logos_pure_real_catchup_target_latest.json"
DEFAULT_OUT = ART / "logos_pure_real_action_pack_latest.json"


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    ap = argparse.ArgumentParser(description="Build pure-real daily action pack.")
    ap.add_argument("--progress-json", type=Path, default=DEFAULT_PROGRESS)
    ap.add_argument("--minimum-intake-json", type=Path, default=DEFAULT_MIN_INTAKE)
    ap.add_argument("--status-json", type=Path, default=DEFAULT_STATUS)
    ap.add_argument("--catchup-json", type=Path, default=DEFAULT_CATCHUP)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    progress = _load_json(args.progress_json)
    min_intake = _load_json(args.minimum_intake_json)
    status = _load_json(args.status_json)
    catchup = _load_json(args.catchup_json)

    progress_cp = progress.get("checkpoint") or {}
    status_ref = catchup.get("status_ref") or {}
    catchup_target = catchup.get("today_catchup_target") or {}
    recommended = min_intake.get("recommended_daily_minimum") or {}

    gap = int(progress_cp.get("gap_unique_days") or 0)
    state = str(status.get("status") or "")

    if state == "PASS_TARGET_REACHED":
        priority = "MAINTAIN_AND_VERIFY_DELTA_GATE"
    elif state == "ON_TRACK":
        priority = "EXECUTE_BASE_DAILY_TARGET"
    else:
        priority = "EXECUTE_CATCHUP_TODAY"

    recommended_total_rows_today = int(catchup_target.get("recommended_total_rows_today") or 0)
    recommended_base_rows = int(recommended.get("required_new_source_rows_per_day") or 0)
    deficit = int(status_ref.get("deficit_vs_plan") or 0)

    run_cmd = (
        "powershell -NoProfile -ExecutionPolicy Bypass -File "
        "scripts/Run-LogosPureRealDay30CheckpointChain-v1.ps1"
    )

    out = {
        "schema": "logos_pure_real_action_pack_v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "source_track": "B",
        "research_only": True,
        "auto_bind_to_atrack_forbidden": True,
        "status": {
            "today_utc": status.get("today_utc"),
            "execution_status": state,
            "priority": priority,
        },
        "checkpoint": {
            "current_unique_days": int(progress_cp.get("current_unique_days") or 0),
            "target_unique_days": int(progress_cp.get("target_unique_days") or 30),
            "gap_unique_days": gap,
        },
        "today_targets": {
            "base_rows": recommended_base_rows,
            "deficit_vs_plan": deficit,
            "recommended_total_rows_today": recommended_total_rows_today,
        },
        "next_actions": [
            f"Collect at least {recommended_total_rows_today} pure-real rows today.",
            "Use previously unseen as_of dates to reduce backfill dependence.",
            "Run day30 checkpoint chain and verify gate/delta artifacts.",
        ],
        "recommended_command": run_cmd,
    }

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "output_json": str(args.output_json),
                "priority": priority,
                "recommended_total_rows_today": recommended_total_rows_today,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

