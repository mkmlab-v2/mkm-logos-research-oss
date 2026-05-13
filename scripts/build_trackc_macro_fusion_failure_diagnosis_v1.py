from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _to_iso_utc(dt_str: str) -> str | None:
    s = (dt_str or "").strip()
    if not s:
        return None
    # PowerShell emits locale datetime strings; keep raw if parsing fails.
    try:
        parsed = datetime.fromisoformat(s.replace("Z", "+00:00"))
        return parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    except ValueError:
        return s


def _ps_json(command: str) -> dict[str, Any]:
    proc = subprocess.run(
        [
            "powershell",
            "-NoProfile",
            "-Command",
            command,
        ],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if proc.returncode != 0:
        return {"_error": proc.stderr.strip() or proc.stdout.strip(), "_returncode": proc.returncode}
    raw = (proc.stdout or "").strip()
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"_raw": raw}


def _task_snapshot(task_name: str) -> dict[str, Any]:
    cmd = rf"""
$t = Get-ScheduledTask -TaskName "{task_name}" -ErrorAction SilentlyContinue
if ($null -eq $t) {{
  [PSCustomObject]@{{ exists=$false }} | ConvertTo-Json -Compress
  exit 0
}}
$i = Get-ScheduledTaskInfo -TaskName "{task_name}"
$a = $t.Actions | Select-Object -First 1
[PSCustomObject]@{{
  exists=$true
  task_name=$t.TaskName
  state=[string]$t.State
  last_run_time=[string]$i.LastRunTime
  next_run_time=[string]$i.NextRunTime
  last_task_result=[int64]$i.LastTaskResult
  action_execute=[string]$a.Execute
  action_arguments=[string]$a.Arguments
}} | ConvertTo-Json -Compress
"""
    return _ps_json(cmd)


def _result_category(code: int) -> str:
    u = code & 0xFFFFFFFF
    if u == 0:
        return "OK"
    if 0x41300 <= u <= 0x4130F:
        return "SchedulerInfo"
    if u == 4294770688:
        return "Unclear_NotRecorded"
    if (u & 0xF0000000) == 0x80000000:
        return "HRESULT"
    if u == 1:
        return "ExitCode_1"
    if u == 2:
        return "ExitCode_2"
    return "OtherNonZero"


def _artifact_health(workspace: Path) -> dict[str, Any]:
    art = workspace / "docs" / "final" / "artifacts"
    targets = {
        "fragility_daily": workspace / "reports" / "fragility_macro_risk_daily_latest.json",
        "forward_log": art / "macro_risk_forward_log_latest.json",
        "logos_4d": art / "logos_4d_state_v1_latest.json",
        "logos_insight_bundle": art / "logos_insight_bundle_v1_latest.json",
        "ops_dashboard": art / "mkm_trackc_ops_dashboard_latest.json",
    }
    now = datetime.now(timezone.utc)
    out: dict[str, Any] = {}
    for key, path in targets.items():
        exists = path.exists()
        if exists:
            mtime = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
            age_h = round((now - mtime).total_seconds() / 3600, 2)
            out[key] = {
                "exists": True,
                "path": str(path),
                "mtime_utc": mtime.isoformat().replace("+00:00", "Z"),
                "age_hours": age_h,
                "stale_over_48h": age_h > 48,
            }
        else:
            out[key] = {"exists": False, "path": str(path)}
    return out


def main() -> int:
    workspace = Path("C:/workspace")
    task_name = "MKM-TrackC-MacroDailyFusion"
    script_path = workspace / "scripts" / "Invoke-TrackCMacroDailyFusion_v1.ps1"
    out_json = workspace / "docs" / "final" / "artifacts" / "trackc_macro_fusion_failure_diagnosis_latest.json"
    out_md = workspace / "docs" / "final" / "artifacts" / "trackc_macro_fusion_failure_diagnosis_latest.md"

    snap = _task_snapshot(task_name)
    exists = bool(snap.get("exists"))
    last_result = int(snap.get("last_task_result") or 0) if exists else None
    category = _result_category(last_result) if last_result is not None else "MISSING"
    script_exists = script_path.exists()
    artifacts = _artifact_health(workspace)

    reason_codes: list[str] = []
    if not exists:
        reason_codes.append("task_missing")
    else:
        if category != "OK":
            reason_codes.append(f"task_last_result_{category.lower()}")
        if not script_exists:
            reason_codes.append("fusion_runner_missing")
        for key, info in artifacts.items():
            if not info.get("exists"):
                reason_codes.append(f"artifact_missing_{key}")
            elif info.get("stale_over_48h"):
                reason_codes.append(f"artifact_stale_{key}")

    diagnosis = {
        "schema": "trackc_macro_fusion_failure_diagnosis_v1",
        "generated_at_utc": _utc_now(),
        "task": {
            "name": task_name,
            "exists": exists,
            "state": snap.get("state"),
            "last_run_time": _to_iso_utc(str(snap.get("last_run_time", ""))),
            "next_run_time": _to_iso_utc(str(snap.get("next_run_time", ""))),
            "last_task_result": last_result,
            "result_category": category,
            "action_execute": snap.get("action_execute"),
            "action_arguments": snap.get("action_arguments"),
        },
        "runner": {
            "path": str(script_path),
            "exists": script_exists,
        },
        "artifacts": artifacts,
        "operator_hints": [
            "Scheduled task re-register (same -TaskName overwrites): scripts/Register-TrackCMacroDailyFusionTask.ps1 -SkipLogosInsightBundle when Aramaic/morphology inputs are absent on this host.",
            "Health fusion smoke only: scripts/run_workspace_automation_health.ps1 -IncludeTrackCMacroFusionSmoke or -TrackCMacroFusionSmokeOnly; add -SkipLogosInsightBundle or set User env MKM_HEALTH_FUSION_SKIP_LOGOS_INSIGHT_BUNDLE truthy (1,true,yes,on). SSOT: CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md §1.3.1.",
            "Verify task action: scripts/Verify-TrackCMacroDailyFusionScheduledTask_v1.ps1",
        ],
        "diagnosis": {
            "status": "PASS" if category == "OK" and script_exists else "FAIL",
            "reason_codes": reason_codes,
        },
    }

    out_json.write_text(json.dumps(diagnosis, ensure_ascii=False, indent=2), encoding="utf-8")
    md = [
        "# TrackC Macro Fusion Failure Diagnosis",
        "",
        f"- generated_at_utc: `{diagnosis['generated_at_utc']}`",
        f"- task: `{task_name}`",
        f"- status: `{diagnosis['diagnosis']['status']}`",
        f"- result_category: `{category}`",
        f"- last_task_result: `{last_result}`",
        f"- reason_codes: `{reason_codes}`",
        "",
        "## Operator hints",
        *(f"- {h}" for h in diagnosis["operator_hints"]),
        "",
        "## Artifact Health",
        *(f"- {k}: exists=`{v.get('exists')}`, stale_over_48h=`{v.get('stale_over_48h', False)}`" for k, v in artifacts.items()),
    ]
    out_md.write_text("\n".join(md) + "\n", encoding="utf-8")
    print(f"wrote: {out_json}")
    print(f"wrote: {out_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

