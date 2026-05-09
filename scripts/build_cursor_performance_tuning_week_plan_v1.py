from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def build() -> int:
    root = Path("C:/workspace")
    art = root / "docs" / "final" / "artifacts"
    art.mkdir(parents=True, exist_ok=True)

    baseline = _read_json(art / "cursor_performance_baseline_weekly_latest.json")
    breakdown = _read_json(art / "trackc_macro_fusion_failure_breakdown_latest.json")
    memory_routing = _read_json(art / "memory_pruning_routing_status_latest.json")
    alert_quality = _read_json(art / "core_alert_quality_report_latest.json")
    trimetrics = _read_json(art / "compression_restore_trimetrics_gate_report_latest.json")
    rto_report = _read_json(art / "recovery_rto_drill_report_latest.json")
    promotion = _read_json(art / "cursor_tuning_promotion_decision_latest.json")
    core_rate = ((baseline.get("kpi") or {}).get("core_task_success_rate_percent_7d"))
    day2_status = "completed" if breakdown else "pending"
    day3_status = "completed" if memory_routing else "pending"
    day4_status = "completed" if alert_quality else "pending"
    day5_status = "completed" if trimetrics else "pending"
    day6_status = "completed" if rto_report else "pending"
    day7_status = "completed" if promotion else "pending"

    plan = {
        "schema": "cursor_performance_tuning_week_plan_v1",
        "generated_at_utc": _iso_now(),
        "goal": {
            "completion_time_improvement_percent": 20,
            "retry_rate_reduction_percent": 30,
            "core_success_rate_target_percent": 99,
            "fact_lock_ungrounded_claims_target": 0,
        },
        "baseline_ref": {
            "core_task_success_rate_percent_7d": core_rate,
            "baseline_json": "docs/final/artifacts/cursor_performance_baseline_weekly_latest.json",
        },
        "daily_plan": [
            {"day": 1, "focus": "Baseline measurement", "status": "completed"},
            {"day": 2, "focus": "Prompt/rule dedupe and execution-path slimming + TrackC failure breakdown", "status": day2_status},
            {"day": 3, "focus": "Memory routing optimization (Keep/Hold/Prune)", "status": day3_status},
            {"day": 4, "focus": "Alert quality upgrade and noise reduction", "status": day4_status},
            {"day": 5, "focus": "Compression/restore tri-metric gate hardening", "status": day5_status},
            {"day": 6, "focus": "Recovery drills and RTO measurement", "status": day6_status},
            {"day": 7, "focus": "Promotion decision and next-cycle policy", "status": day7_status},
        ],
        "evidence_outputs": [
            "docs/final/artifacts/cursor_performance_baseline_weekly_latest.json",
            "docs/final/artifacts/core_task_consecutive_failure_alert_latest.json",
            "docs/final/artifacts/mkm_trackc_ops_dashboard_latest.json",
            "docs/final/artifacts/trackc_macro_fusion_failure_diagnosis_latest.json",
        ],
    }

    out_json = art / "cursor_performance_tuning_week_plan_latest.json"
    out_md = art / "cursor_performance_tuning_week_plan_latest.md"
    out_json.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")

    md_lines = [
        "# Cursor Performance Tuning Week Plan",
        "",
        f"- generated_at_utc: `{plan['generated_at_utc']}`",
        f"- baseline_core_success_rate_percent_7d: `{core_rate}`",
        "",
        "## Goals",
        "- completion_time_improvement_percent: `20`",
        "- retry_rate_reduction_percent: `30`",
        "- core_success_rate_target_percent: `99`",
        "- fact_lock_ungrounded_claims_target: `0`",
        "",
        "## Daily Plan",
    ]
    for d in plan["daily_plan"]:
        md_lines.append(f"- Day {d['day']}: {d['focus']} (`{d['status']}`)")
    out_md.write_text("\n".join(md_lines) + "\n", encoding="utf-8")

    print(f"wrote: {out_json}")
    print(f"wrote: {out_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(build())

