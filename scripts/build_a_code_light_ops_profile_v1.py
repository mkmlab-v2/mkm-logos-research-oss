#!/usr/bin/env python3
"""Build light-only weekly ops profile for A-code operator-assist lane ([HYPO])."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "docs/final/artifacts/a_code_light_ops_profile_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def build_profile() -> dict[str, Any]:
    return {
        "schema": "a_code_light_ops_profile_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "rq_id": "RQ-031",
        "hypothesis_tier": "B",
        "research_only": True,
        "profile_id": "operator_assist_light",
        "skip_governor_bundle": True,
        "skip_multiday_replay": True,
        "weekly_task_name": "MKM-ACode-OperatorAssistLane-Weekly-Light",
        "weekly_run_at_local": "09:18",
        "daily_persona": "OperatorAssistLane",
        "weekly_light_persona": "OperatorAssistLaneLight",
        "routine_script": "scripts/Run-ACodeOperatorAssistLaneLightRoutine_v1.ps1",
        "register_script": "scripts/Register-ACodeOperatorAssistLaneWeeklyTasks_v1.ps1",
        "verify_script": "scripts/Verify-ACodeOperatorAssistLaneReadiness_v1.ps1 -RequireBothWeeklyTasks",
        "included_steps": [
            "Run-ACodePromotionRqDiscussionBundle_v1.ps1 -SkipGovernorBundle",
            "build_a_code_operator_assist_lane_v1.py",
            "check_a_code_operator_assist_lane_gate_v1.py",
            "check_a_code_constitution_pointer_row_v1.py",
        ],
        "excluded_steps": [
            "Run-ACodeGovernorResearchBundle_v1.ps1",
            "run_a_code_governor_knob_multiday_replay_v1.py",
        ],
        "track_wall": {
            "track_a_auto_promotion": False,
            "live_trading_auto_trigger": False,
            "non_gating": True,
        },
        "operator_hint_ko": "일상·주간 light는 governor multiday 없이 operator lane만 갱신 [HYPO]",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()

    doc = build_profile()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"OK: {args.out} profile={doc.get('profile_id')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
