from __future__ import annotations

import json
import os
import subprocess
import urllib.error
import urllib.request
from urllib.parse import urlparse
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


CORE_TASKS = [
    "MKM_AIV2_DailyReadiness",
    "MKM-TrackC-MacroDailyFusion",
    "MKM-PreNews-Shadow-Daily",
    "MKM-PreNews-Shadow-Health-Daily",
]


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _task_snapshot(task_name: str) -> dict[str, Any]:
    cmd = rf"""
$t = Get-ScheduledTask -TaskName "{task_name}" -ErrorAction SilentlyContinue
if ($null -eq $t) {{
  [PSCustomObject]@{{ exists=$false; task_name="{task_name}" }} | ConvertTo-Json -Compress
  exit 0
}}
$i = Get-ScheduledTaskInfo -TaskName "{task_name}"
[PSCustomObject]@{{
  exists=$true
  task_name=$t.TaskName
  state=[string]$t.State
  last_run_time=[string]$i.LastRunTime
  next_run_time=[string]$i.NextRunTime
  last_task_result=[int64]$i.LastTaskResult
}} | ConvertTo-Json -Compress
"""
    proc = subprocess.run(
        ["powershell", "-NoProfile", "-Command", cmd],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    if proc.returncode != 0:
        return {"exists": False, "task_name": task_name, "error": proc.stderr.strip()}
    raw = (proc.stdout or "").strip()
    if not raw:
        return {"exists": False, "task_name": task_name, "error": "empty_output"}
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"exists": False, "task_name": task_name, "error": "json_decode_error", "raw": raw}


def _category(code: int) -> str:
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


def _truthy(v: str | None) -> bool:
    if v is None:
        return False
    return v.strip().lower() in {"1", "true", "yes", "on"}


def _parse_iso_utc(v: str | None) -> datetime | None:
    if v is None:
        return None
    s = str(v).strip()
    if not s:
        return None
    try:
        if s.endswith("Z"):
            return datetime.fromisoformat(s.replace("Z", "+00:00"))
        return datetime.fromisoformat(s)
    except ValueError:
        return None


def _offender_signature(payload: dict[str, Any]) -> str:
    offenders = payload.get("offenders", []) or []
    compact = []
    for o in offenders:
        compact.append(
            {
                "task_name": o.get("task_name"),
                "recent_categories": o.get("recent_categories"),
                "recent_codes": o.get("recent_codes"),
            }
        )
    compact.sort(key=lambda x: str(x.get("task_name")))
    return json.dumps(compact, ensure_ascii=False, sort_keys=True)


def _send_webhook_if_needed(payload: dict[str, Any], notify_decision: dict[str, Any]) -> dict[str, Any]:
    """
    Safe-by-default webhook delivery:
    - only when status=CRITICAL
    - and CORE_TASK_ALERT_WEBHOOK_ENABLED is truthy
    - URL priority: CORE_TASK_ALERT_WEBHOOK_URL -> OPS_ALARM_WEBHOOK_URL
    """
    status = str(payload.get("status", "")).upper()
    enabled = _truthy(os.getenv("CORE_TASK_ALERT_WEBHOOK_ENABLED"))
    url = os.getenv("CORE_TASK_ALERT_WEBHOOK_URL") or os.getenv("OPS_ALARM_WEBHOOK_URL")

    if status != "CRITICAL":
        return {"attempted": False, "sent": False, "reason": "status_not_critical", "notify_decision": notify_decision}
    if not bool(notify_decision.get("notify")):
        return {"attempted": False, "sent": False, "reason": "suppressed_by_transition_or_cooldown", "notify_decision": notify_decision}
    if not enabled:
        return {"attempted": False, "sent": False, "reason": "webhook_disabled", "notify_decision": notify_decision}
    if not url:
        return {"attempted": False, "sent": False, "reason": "webhook_url_missing", "notify_decision": notify_decision}

    host = ""
    try:
        host = (urlparse(url).hostname or "").lower()
    except Exception:  # noqa: BLE001
        host = ""

    webhook_payload: dict[str, Any] = {
        "schema": "core_task_consecutive_failure_alert_webhook_v1",
        "generated_at_utc": payload.get("generated_at_utc"),
        "status": payload.get("status"),
        "offenders": payload.get("offenders", []),
        "consecutive_fail_threshold": payload.get("consecutive_fail_threshold"),
    }

    # Discord-friendly message while keeping JSON metadata for other receivers.
    if "discord.com" in host or "discordapp.com" in host:
        offenders = payload.get("offenders", []) or []
        if offenders:
            offender_lines = []
            for o in offenders:
                offender_lines.append(
                    f"- {o.get('task_name')}: {o.get('recent_categories')} / {o.get('recent_codes')}"
                )
            offender_text = "\n".join(offender_lines)
        else:
            offender_text = "- none"
        webhook_payload["content"] = (
            "🚨 **MKM Core Integrity Alert**\n"
            f"status: `{payload.get('status')}`\n"
            f"threshold: `{payload.get('consecutive_fail_threshold')}`\n"
            f"generated_at_utc: `{payload.get('generated_at_utc')}`\n"
            f"offenders:\n{offender_text}"
        )

    body = json.dumps(webhook_payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            code = int(getattr(resp, "status", 200))
        return {
            "attempted": True,
            "sent": True,
            "reason": "ok",
            "http_status": code,
            "notify_decision": notify_decision,
        }
    except urllib.error.HTTPError as e:
        return {
            "attempted": True,
            "sent": False,
            "reason": "http_error",
            "http_status": int(e.code),
            "notify_decision": notify_decision,
        }
    except Exception as e:  # noqa: BLE001
        return {
            "attempted": True,
            "sent": False,
            "reason": "exception",
            "error": str(e),
            "notify_decision": notify_decision,
        }


def main() -> int:
    root = Path("C:/workspace")
    reports = root / "reports"
    artifacts = root / "docs" / "final" / "artifacts"
    reports.mkdir(parents=True, exist_ok=True)
    artifacts.mkdir(parents=True, exist_ok=True)

    history_path = reports / "core_task_health_history_v1.jsonl"
    alert_json = artifacts / "core_task_consecutive_failure_alert_latest.json"
    alert_md = artifacts / "core_task_consecutive_failure_alert_latest.md"
    notify_state_json = artifacts / "core_task_consecutive_failure_notify_state_latest.json"

    now = _utc_now()
    rows: list[dict[str, Any]] = []
    for name in CORE_TASKS:
        snap = _task_snapshot(name)
        last = int(snap.get("last_task_result") or 0) if snap.get("exists") else -1
        cat = _category(last) if snap.get("exists") else "MISSING"
        row = {
            "ts_utc": now,
            "task_name": name,
            "exists": bool(snap.get("exists")),
            "state": snap.get("state"),
            "last_run_time": snap.get("last_run_time"),
            "last_task_result": last,
            "result_category": cat,
        }
        rows.append(row)

    with history_path.open("a", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    # Evaluate consecutive failures from the last two records per task.
    history: list[dict[str, Any]] = []
    if history_path.exists():
        for line in history_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                history.append(json.loads(line))
            except json.JSONDecodeError:
                continue

    by_task: dict[str, list[dict[str, Any]]] = {}
    for h in history:
        by_task.setdefault(h.get("task_name", ""), []).append(h)

    offenders: list[dict[str, Any]] = []
    for task in CORE_TASKS:
        arr = by_task.get(task, [])
        if len(arr) < 2:
            continue
        last_two = arr[-2:]
        non_ok = [x for x in last_two if x.get("result_category") != "OK"]
        if len(non_ok) == 2:
            offenders.append(
                {
                    "task_name": task,
                    "recent_categories": [x.get("result_category") for x in last_two],
                    "recent_codes": [x.get("last_task_result") for x in last_two],
                }
            )

    payload = {
        "schema": "core_task_consecutive_failure_alert_v1",
        "generated_at_utc": now,
        "core_tasks": CORE_TASKS,
        "status": "CRITICAL" if offenders else "PASS",
        "consecutive_fail_threshold": 2,
        "offenders": offenders,
        "history_path": str(history_path),
    }

    prev_state: dict[str, Any] = {}
    if notify_state_json.exists():
        try:
            prev_state = json.loads(notify_state_json.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            prev_state = {}

    current_sig = _offender_signature(payload)
    prev_sig = str(prev_state.get("last_offender_signature") or "")
    prev_status = str(prev_state.get("last_status") or "UNKNOWN").upper()
    now_dt = _parse_iso_utc(now) or datetime.now(timezone.utc)
    prev_sent_dt = _parse_iso_utc(prev_state.get("last_sent_at_utc"))
    cooldown_minutes = int(os.getenv("CORE_TASK_ALERT_COOLDOWN_MINUTES", "30"))
    in_cooldown = bool(
        prev_sent_dt is not None and now_dt - prev_sent_dt < timedelta(minutes=cooldown_minutes)
    )
    notify = bool(
        payload["status"] == "CRITICAL"
        and (prev_status != "CRITICAL" or prev_sig != current_sig)
        and not in_cooldown
    )
    notify_decision = {
        "notify": notify,
        "reason": (
            "transition_or_signature_changed"
            if notify
            else ("cooldown_active" if in_cooldown else "no_transition_or_same_signature")
        ),
        "cooldown_minutes": cooldown_minutes,
        "previous_status": prev_status,
        "previous_signature_equals_current": prev_sig == current_sig,
    }

    payload["webhook_delivery"] = _send_webhook_if_needed(payload, notify_decision)
    alert_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    new_state = {
        "schema": "core_task_consecutive_failure_notify_state_v1",
        "updated_at_utc": now,
        "last_status": payload["status"],
        "last_offender_signature": current_sig,
        "last_notify_decision": notify_decision,
    }
    if payload["webhook_delivery"].get("sent"):
        new_state["last_sent_at_utc"] = now
    else:
        new_state["last_sent_at_utc"] = prev_state.get("last_sent_at_utc")
    notify_state_json.write_text(json.dumps(new_state, ensure_ascii=False, indent=2), encoding="utf-8")

    md = [
        "# Core Task Consecutive Failure Alert",
        "",
        f"- generated_at_utc: `{now}`",
        f"- status: `{payload['status']}`",
        f"- threshold: `2`",
        f"- offender_count: `{len(offenders)}`",
        f"- history_path: `{history_path}`",
        f"- notify_decision: `{notify_decision}`",
    ]
    if offenders:
        md.append("")
        md.append("## Offenders")
        for o in offenders:
            md.append(
                f"- `{o['task_name']}` categories={o['recent_categories']} codes={o['recent_codes']}"
            )
    alert_md.write_text("\n".join(md) + "\n", encoding="utf-8")
    print(f"wrote: {alert_json}")
    print(f"wrote: {alert_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

