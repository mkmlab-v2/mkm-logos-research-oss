#!/usr/bin/env python3
"""Build progress dashboard for the 2-week GPU training plan."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"

DEFAULT_PLAN = ART / "gpu_two_week_training_plan_v1_latest.json"
DEFAULT_SHADOW = ART / "gpu_shadow_runtime_score_v1_latest.json"
DEFAULT_RESWEEP = ART / "gpu_universal_precursor_resweep_v1_latest.json"
DEFAULT_DRILL = ART / "prophecy_live_rollback_drill_v1_latest.json"
DEFAULT_UNIFIED = ART / "live_gpu_unified_status_dashboard_v1_latest.json"
DEFAULT_OUT = ART / "gpu_two_week_training_dashboard_v1_latest.json"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return {}


def _is_completed(focus: str, shadow: dict[str, Any], resweep: dict[str, Any], drill: dict[str, Any], unified: dict[str, Any]) -> bool:
    if focus == "gpu_shadow_calibration":
        return bool((shadow.get("shadow") or {}).get("runtime_score_0_1") is not None)
    if focus == "regime_threshold_retune":
        return str(resweep.get("status") or "") in {"go_research_robust", "hold_research"}
    if focus == "rollback_drill_scoring":
        return str(drill.get("drill_result") or "") in {"PASS", "FAIL"}
    if focus == "weekly_review":
        return str((unified.get("live") or {}).get("health_result") or "") in {"PASS", "FAIL"}
    return False


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--plan-json", type=Path, default=DEFAULT_PLAN)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    plan = _load(args.plan_json)
    shadow = _load(DEFAULT_SHADOW)
    resweep = _load(DEFAULT_RESWEEP)
    drill = _load(DEFAULT_DRILL)
    unified = _load(DEFAULT_UNIFIED)

    schedule = plan.get("schedule") if isinstance(plan.get("schedule"), list) else []
    today = _now().date()

    rows: list[dict[str, Any]] = []
    completed_count = 0
    delayed_count = 0
    for item in schedule:
        focus = str(item.get("focus") or "")
        date_s = str(item.get("date_utc") or "")
        try:
            due_date = datetime.strptime(date_s, "%Y-%m-%d").date()
        except ValueError:
            due_date = today
        done = _is_completed(focus, shadow, resweep, drill, unified)
        delayed = (due_date < today) and (not done)
        if done:
            completed_count += 1
        if delayed:
            delayed_count += 1
        rows.append(
            {
                "day_index": item.get("day_index"),
                "date_utc": date_s,
                "focus": focus,
                "done": done,
                "delayed": delayed,
            }
        )

    total = len(rows)
    completion_rate = (completed_count / total) if total > 0 else 0.0
    risk_level = "low" if delayed_count == 0 else ("medium" if delayed_count <= 2 else "high")

    out = {
        "schema": "gpu_two_week_training_dashboard_v1",
        "generated_at_utc": _now().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "inputs": {
            "plan_json": str(args.plan_json).replace("\\", "/"),
        },
        "progress": {
            "total_days": total,
            "completed_days": completed_count,
            "delayed_days": delayed_count,
            "completion_rate_0_1": round(completion_rate, 6),
            "risk_level": risk_level,
        },
        "schedule_status": rows,
        "constraints": {
            "no_auto_live_binding": True,
            "human_review_required_for_live_switch": True,
        },
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.out}")
    print(f"completion_rate={out['progress']['completion_rate_0_1']}")
    print(f"risk_level={out['progress']['risk_level']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
