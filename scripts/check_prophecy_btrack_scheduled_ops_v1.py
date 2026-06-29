#!/usr/bin/env python3
"""
Read-only B-track prophecy scheduled-ops probe (Windows Task Scheduler + artifact freshness).

Does not run run_btrack_daily_hypothesis_chain.ps1. For Amsaeng observe / Athena Fact-Lock tail.
B-track / research_only — no Track A or live-trading side effects.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA = "prophecy_btrack_scheduled_ops_v1"
DEFAULT_TASKS = (
    "MKM-BTrack-DailyHypothesis-Chain",
    "MKM-BTrack-Phase1-MicroLive-VpsSync",
    "MKM-Prophecy-Evolution-Watchdog",
    "MKM-Prophecy-Panel-24h-Alerts",
)

# 0x41303 = task has not yet run
WIN32_TASK_NEVER_RUN = 267011


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_utc(s: str | None) -> datetime | None:
    if not s or not isinstance(s, str):
        return None
    try:
        t = s.strip()
        if t.endswith("Z"):
            t = t[:-1] + "+00:00"
        dt = datetime.fromisoformat(t)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except ValueError:
        return None


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        doc = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return None
    return doc if isinstance(doc, dict) else None


def _artifact_age_hours(path: Path, *, ts_key: str = "generated_at_utc") -> dict[str, Any]:
    rel = str(path)
    if not path.is_file():
        return {"path": rel, "exists": False, "status": "missing"}
    doc = _read_json(path)
    ts = _parse_utc(doc.get(ts_key) if doc else None)
    if ts is None:
        mtime = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
        ts = mtime
        source = "mtime"
    else:
        source = ts_key
    age_h = (_utc_now() - ts).total_seconds() / 3600.0
    return {
        "path": rel,
        "exists": True,
        "status": "ok",
        "timestamp_source": source,
        "timestamp_utc": _iso(ts),
        "age_hours": round(age_h, 4),
    }


def _query_scheduled_tasks(names: tuple[str, ...]) -> list[dict[str, Any]]:
    if sys.platform != "win32":
        return [{"task_name": n, "registered": False, "state": "NON_WINDOWS", "note": "skip"} for n in names]
    name_list = ",".join(f"'{n}'" for n in names)
    ps = f"""
$names = @({name_list})
$rows = @()
foreach ($n in $names) {{
  $t = Get-ScheduledTask -TaskName $n -ErrorAction SilentlyContinue
  if (-not $t) {{
    $rows += [ordered]@{{
      task_name = $n
      registered = $false
      state = 'MISSING'
      last_task_result = $null
      last_run_time_local = $null
    }}
    continue
  }}
  $info = Get-ScheduledTaskInfo -TaskName $n -ErrorAction SilentlyContinue
  $rows += [ordered]@{{
    task_name = $n
    registered = $true
    state = [string]$t.State
    last_task_result = if ($info) {{ [int]$info.LastTaskResult }} else {{ $null }}
    last_run_time_local = if ($info -and $info.LastRunTime) {{
      $info.LastRunTime.ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')
    }} else {{ $null }}
  }}
}}
$rows | ConvertTo-Json -Compress -Depth 4
"""
    proc = subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0 or not (proc.stdout or "").strip():
        return [
            {
                "task_name": n,
                "registered": False,
                "state": "QUERY_FAILED",
                "last_task_result": None,
                "stderr": (proc.stderr or "")[:500],
            }
            for n in names
        ]
    raw = json.loads(proc.stdout.strip())
    if isinstance(raw, dict):
        return [raw]
    if isinstance(raw, list):
        return raw
    return []


def _coerce_int(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return None


def _enrich_task_row(row: dict[str, Any]) -> dict[str, Any]:
    out = dict(row)
    ltr = _coerce_int(out.get("last_task_result"))
    out["last_task_result"] = ltr
    if ltr is None:
        out["last_run_ok"] = None
        out["last_run_note"] = "never_run_or_unknown"
    elif ltr == 0:
        out["last_run_ok"] = True
        out["last_run_note"] = "success"
    elif ltr == WIN32_TASK_NEVER_RUN:
        out["last_run_ok"] = None
        out["last_run_note"] = "never_run"
    else:
        out["last_run_ok"] = False
        out["last_run_note"] = f"exit_code_{ltr}"
    return out


def build_report(
    root: Path,
    *,
    task_names: tuple[str, ...],
    max_hit_rate_age_hours: float,
    max_daily_chain_hours_since_run: float,
    skip_scheduled_tasks: bool,
) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    tasks_out: list[dict[str, Any]] = []

    if skip_scheduled_tasks:
        tasks_out = [{"task_name": n, "skipped": True} for n in task_names]
    else:
        for row in _query_scheduled_tasks(task_names):
            tasks_out.append(_enrich_task_row(row))

    daily = next((t for t in tasks_out if t.get("task_name") == "MKM-BTrack-DailyHypothesis-Chain"), None)
    daily_ok = True
    daily_notes: list[str] = []
    if daily and not daily.get("skipped"):
        if not daily.get("registered"):
            daily_ok = False
            daily_notes.append("daily_chain_task_not_registered")
        elif daily.get("last_run_ok") is False:
            daily_ok = False
            daily_notes.append(f"daily_chain_last_run_failed:{daily.get('last_run_note')}")
        elif daily.get("last_run_time_local"):
            lr = _parse_utc(str(daily.get("last_run_time_local")))
            if lr is not None:
                hours = (_utc_now() - lr).total_seconds() / 3600.0
                daily["hours_since_last_run"] = round(hours, 3)
                if hours > max_daily_chain_hours_since_run and daily.get("last_run_ok") is not True:
                    daily_ok = False
                    daily_notes.append("daily_chain_stale_or_never_ok")
    checks.append(
        {
            "id": "daily_hypothesis_chain_task",
            "ok": daily_ok,
            "notes": daily_notes,
            "task": daily,
        }
    )

    hit_path = root / "docs/final/artifacts/prophecy_hit_rate_eval_latest.json"
    hit = _artifact_age_hours(hit_path)
    hit_fresh = hit.get("exists") and float(hit.get("age_hours", 1e9)) <= max_hit_rate_age_hours
    checks.append(
        {
            "id": "btrack_hit_rate_eval_fresh",
            "ok": bool(hit_fresh),
            "artifact": hit,
            "max_age_hours": max_hit_rate_age_hours,
        }
    )

    artifacts = {
        "dual_per_date": _artifact_age_hours(root / "reports/btrack_ensemble_per_date_directions_dual_v1_latest.json"),
        "btrack_score": _artifact_age_hours(root / "docs/final/artifacts/btrack_prophecy_score_latest.json"),
        "morning_briefing": _artifact_age_hours(
            root / "reports/morning_prophecy_briefing_report_latest.json"
        ),
        "mkmlife_public_envelope": _artifact_age_hours(
            root / "projects/mkm/mkm-life/public/data/three_lens_sphere_envelope_public_v1.json",
            ts_key="ts_utc",
        ),
        "watchdog": _artifact_age_hours(root / "reports/prophecy_evolution_watchdog_latest.json"),
        "phase1_micro_live_readiness": _artifact_age_hours(
            root / "reports/btrack_phase1_micro_live_readiness_v1_latest.json"
        ),
        "phase1_engine_handoff": _artifact_age_hours(
            root / "docs/final/artifacts/btc_limited_live_engine_input_from_btrack_typea_v1_latest.json"
        ),
        "phase1_vps_health": _artifact_age_hours(
            root / "reports/btrack_phase1_micro_live_vps_health_v1_latest.json"
        ),
    }

    pipeline_ok = all(
        artifacts[k].get("exists")
        for k in ("dual_per_date", "btrack_score", "morning_briefing", "mkmlife_public_envelope")
    )
    checks.append(
        {
            "id": "btrack_pipeline_artifacts_present",
            "ok": pipeline_ok,
            "notes": [] if pipeline_ok else ["missing_one_or_more_pipeline_artifacts"],
            "artifact_keys": list(artifacts.keys()),
        }
    )

    overall_ok = all(c.get("ok") for c in checks)
    return {
        "schema": SCHEMA,
        "generated_at_utc": _iso(_utc_now()),
        "workspace_root": str(root),
        "research_only": True,
        "track_wall": "B-track observation; not Track A live trading",
        "scheduled_tasks": tasks_out,
        "artifacts": artifacts,
        "checks": checks,
        "overall_ok": overall_ok,
    }


def main() -> int:
    p = argparse.ArgumentParser(description="B-track prophecy scheduled ops observe probe (read-only).")
    p.add_argument("--workspace-root", type=Path, default=Path(__file__).resolve().parents[1])
    p.add_argument(
        "--out-json",
        type=Path,
        default=None,
        help="Default: <workspace>/reports/prophecy_btrack_scheduled_ops_latest.json",
    )
    p.add_argument("--max-hit-rate-age-hours", type=float, default=96.0)
    p.add_argument(
        "--max-daily-chain-hours-since-run",
        type=float,
        default=36.0,
        help="Warn/fail strict if daily chain has not succeeded within this window (when last run time known).",
    )
    p.add_argument("--skip-scheduled-tasks", action="store_true", help="Artifact checks only (tests/CI).")
    p.add_argument(
        "--strict",
        action="store_true",
        help="Exit 1 when overall_ok is false (default: always exit 0, write report).",
    )
    p.add_argument("--stdout-only", action="store_true", help="Print one-line summary to stdout.")
    args = p.parse_args()

    root = args.workspace_root.resolve()
    out = args.out_json or (root / "reports/prophecy_btrack_scheduled_ops_latest.json")
    report = build_report(
        root,
        task_names=DEFAULT_TASKS,
        max_hit_rate_age_hours=args.max_hit_rate_age_hours,
        max_daily_chain_hours_since_run=args.max_daily_chain_hours_since_run,
        skip_scheduled_tasks=args.skip_scheduled_tasks,
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if args.stdout_only:
        failed = [c["id"] for c in report["checks"] if not c.get("ok")]
        print(
            f"prophecy_btrack_scheduled_ops overall_ok={report['overall_ok']} "
            f"failed={','.join(failed) if failed else 'none'} path={out}"
        )
    else:
        print(f"WROTE: {out} overall_ok={report['overall_ok']}")

    if args.strict and not report["overall_ok"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
