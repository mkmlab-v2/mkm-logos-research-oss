from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


CORE_TASKS = [
    "MKM_AIV2_DailyReadiness",
    "MKM-TrackC-MacroDailyFusion",
    "MKM-PreNews-Shadow-Daily",
    "MKM-PreNews-Shadow-Health-Daily",
]


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _iso_z(dt: datetime) -> str:
    return dt.isoformat().replace("+00:00", "Z")


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.exists():
        return rows
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            rows.append(obj)
    return rows


def _parse_ts(value: Any) -> datetime | None:
    if value is None:
        return None
    s = str(value).strip()
    if not s:
        return None
    try:
        if s.endswith("Z"):
            return datetime.fromisoformat(s.replace("Z", "+00:00"))
        return datetime.fromisoformat(s)
    except ValueError:
        return None


def _is_success_category(cat: str) -> bool:
    return cat in {"OK", "SchedulerInfo"}


def build() -> int:
    root = Path("C:/workspace")
    reports = root / "reports"
    art = root / "docs" / "final" / "artifacts"
    art.mkdir(parents=True, exist_ok=True)

    now = _utc_now()
    window_start = now - timedelta(days=7)

    history_rows = _read_jsonl(reports / "core_task_health_history_v1.jsonl")
    history_rows = [
        r
        for r in history_rows
        if (_parse_ts(r.get("ts_utc")) or datetime.min.replace(tzinfo=timezone.utc)) >= window_start
    ]

    by_task: dict[str, list[dict[str, Any]]] = {t: [] for t in CORE_TASKS}
    for row in history_rows:
        t = str(row.get("task_name", ""))
        if t in by_task:
            by_task[t].append(row)

    per_task: dict[str, Any] = {}
    all_total = 0
    all_success = 0
    for task in CORE_TASKS:
        rows = by_task.get(task, [])
        total = len(rows)
        success = sum(1 for r in rows if _is_success_category(str(r.get("result_category", ""))))
        fail = total - success
        rate = round((success / total) * 100.0, 2) if total > 0 else None
        per_task[task] = {
            "total_samples_7d": total,
            "success_samples_7d": success,
            "failed_samples_7d": fail,
            "success_rate_percent_7d": rate,
        }
        all_total += total
        all_success += success

    overall_rate = round((all_success / all_total) * 100.0, 2) if all_total > 0 else None

    core_alert = _read_json(art / "core_task_consecutive_failure_alert_latest.json")
    fusion_diag = _read_json(art / "trackc_macro_fusion_failure_diagnosis_latest.json")
    trackc_dash = _read_json(art / "mkm_trackc_ops_dashboard_latest.json")

    baseline = {
        "schema": "cursor_performance_weekly_baseline_v1",
        "generated_at_utc": _iso_z(now),
        "window": {
            "start_utc": _iso_z(window_start),
            "end_utc": _iso_z(now),
            "days": 7,
        },
        "kpi": {
            "core_task_success_rate_percent_7d": overall_rate,
            "core_task_total_samples_7d": all_total,
            "core_task_success_samples_7d": all_success,
            "core_task_failed_samples_7d": all_total - all_success,
            "core_consecutive_alert_status": core_alert.get("status", "UNKNOWN"),
            "trackc_macro_fusion_result_category": ((fusion_diag.get("task") or {}).get("result_category")),
            "trackc_macro_fusion_diagnosis_status": ((fusion_diag.get("diagnosis") or {}).get("status")),
            "trackc_forward_pipeline_health": (((trackc_dash.get("trackc") or {}).get("forward_pipeline_health") or {}).get("status")),
        },
        "per_task": per_task,
        "evidence": {
            "core_history_jsonl": "reports/core_task_health_history_v1.jsonl",
            "core_alert_latest": "docs/final/artifacts/core_task_consecutive_failure_alert_latest.json",
            "trackc_fusion_diag_latest": "docs/final/artifacts/trackc_macro_fusion_failure_diagnosis_latest.json",
            "trackc_dashboard_latest": "docs/final/artifacts/mkm_trackc_ops_dashboard_latest.json",
        },
    }

    out_json = art / "cursor_performance_baseline_weekly_latest.json"
    out_md = art / "cursor_performance_baseline_weekly_latest.md"
    out_json.write_text(json.dumps(baseline, ensure_ascii=False, indent=2), encoding="utf-8")

    md_lines = [
        "# Cursor Performance Weekly Baseline",
        "",
        f"- generated_at_utc: `{baseline['generated_at_utc']}`",
        f"- window: `{baseline['window']['start_utc']} -> {baseline['window']['end_utc']}`",
        f"- core_task_success_rate_percent_7d: `{baseline['kpi']['core_task_success_rate_percent_7d']}`",
        f"- core_task_samples_7d: `{baseline['kpi']['core_task_total_samples_7d']}`",
        f"- core_consecutive_alert_status: `{baseline['kpi']['core_consecutive_alert_status']}`",
        f"- trackc_macro_fusion_result_category: `{baseline['kpi']['trackc_macro_fusion_result_category']}`",
        f"- trackc_macro_fusion_diagnosis_status: `{baseline['kpi']['trackc_macro_fusion_diagnosis_status']}`",
        f"- trackc_forward_pipeline_health: `{baseline['kpi']['trackc_forward_pipeline_health']}`",
        "",
        "## Core Task Breakdown",
    ]
    for task in CORE_TASKS:
        t = per_task[task]
        md_lines.append(
            f"- `{task}`: samples={t['total_samples_7d']}, success={t['success_samples_7d']}, "
            f"fail={t['failed_samples_7d']}, success_rate={t['success_rate_percent_7d']}"
        )
    out_md.write_text("\n".join(md_lines) + "\n", encoding="utf-8")

    print(f"wrote: {out_json}")
    print(f"wrote: {out_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(build())

