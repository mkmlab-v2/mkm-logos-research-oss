#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path("C:/workspace")
ART = ROOT / "docs" / "final" / "artifacts"
AUDIT_LOG = ROOT / "reports" / "agent_decisions_log.jsonl"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _append_audit(row: dict[str, Any]) -> None:
    AUDIT_LOG.parent.mkdir(parents=True, exist_ok=True)
    with AUDIT_LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def _verify_token(token: Path, action: str, risk_level: str) -> tuple[bool, str]:
    cmd = [
        sys.executable,
        str(ROOT / "scripts" / "verify_commander_approval_token_v1.py"),
        "--token",
        str(token),
        "--action",
        action,
        "--risk-level",
        risk_level,
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", check=False)
    ok = proc.returncode == 0
    msg = ((proc.stdout or "") + (proc.stderr or "")).strip()
    return ok, msg


def _mark_token_used(token: Path, action: str) -> tuple[bool, str]:
    try:
        doc = json.loads(token.read_text(encoding="utf-8-sig"))
    except Exception as exc:  # noqa: BLE001
        return False, f"token_mark_used_read_fail: {exc}"
    doc["used"] = True
    doc["used_at_utc"] = _now_iso()
    doc["used_action_id"] = action
    try:
        token.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    except Exception as exc:  # noqa: BLE001
        return False, f"token_mark_used_write_fail: {exc}"
    return True, "token_marked_used"


def _run_retry_scheduled_task(task_name: str) -> tuple[bool, str]:
    ps = f"Start-ScheduledTask -TaskName '{task_name}' -ErrorAction Stop; Write-Output 'started'"
    proc = subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    if proc.returncode != 0:
        return False, ((proc.stdout or "") + (proc.stderr or "")).strip()
    return True, (proc.stdout or "started").strip()


def _run_ip_fortress_scrubber() -> tuple[bool, str]:
    cmd = [sys.executable, str(ROOT / "scripts" / "background_jobs" / "ip_fortress_scrubber_v1.py")]
    proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", check=False)
    msg = ((proc.stdout or "") + (proc.stderr or "")).strip()
    return proc.returncode == 0, msg


def _preview_python_cache_cleanup() -> tuple[bool, str]:
    ps = (
        "Set-Location 'C:\\workspace'; "
        "$items=Get-ChildItem -Recurse -Directory -Force -ErrorAction SilentlyContinue | "
        "Where-Object { $_.Name -in @('__pycache__','.pytest_cache') }; "
        "$count=($items|Measure-Object).Count; "
        "Write-Output (\"preview_cache_dirs=\" + $count); "
        "$items | Select-Object -First 20 -ExpandProperty FullName"
    )
    proc = subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    msg = ((proc.stdout or "") + (proc.stderr or "")).strip()
    return proc.returncode == 0, msg


def main() -> int:
    ap = argparse.ArgumentParser(description="Run inspector action with L-level approval gate.")
    ap.add_argument(
        "--action-id",
        required=True,
        choices=[
            "retry_scheduled_task",
            "run_ip_fortress_scrubber",
            "preview_python_cache_cleanup",
        ],
    )
    ap.add_argument("--level", required=True, choices=["L1", "L2", "L3"])
    ap.add_argument("--task-name", default="", help="Required for retry_scheduled_task")
    ap.add_argument("--approval-token", default="", help="Required for L2/L3")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if args.action_id == "retry_scheduled_task" and not args.task_name.strip():
        print("missing --task-name for retry_scheduled_task")
        return 2

    if args.level in {"L2", "L3"}:
        if not args.approval_token.strip():
            print("approval_token_required_for_L2_L3")
            return 3
        token_path = Path(args.approval_token)
        ok, detail = _verify_token(token_path, args.action_id, args.level)
        if not ok:
            print("approval_token_invalid")
            if detail:
                print(detail)
            return 3
    else:
        token_path = None

    if args.dry_run:
        print(f"dry_run_ok action={args.action_id} level={args.level}")
        return 0

    if args.action_id == "retry_scheduled_task":
        ok, detail = _run_retry_scheduled_task(args.task_name.strip())
        token_mark_detail = ""
        if ok and token_path is not None:
            m_ok, m_msg = _mark_token_used(token_path, args.action_id)
            token_mark_detail = m_msg
            if not m_ok:
                ok = False
                detail = f"{detail}\n{m_msg}".strip()
        _append_audit(
            {
                "timestamp": _now_iso(),
                "mission_id": "mkm_internal_inspector_v1",
                "stage": "action_gate",
                "decision": "execute_retry_scheduled_task",
                "evidence_path": str(ART / "sentinel_realtime_alert_latest.json").replace("\\", "/"),
                "actor": "Operator",
                "risk_level": args.level,
                "note": {
                    "task_name": args.task_name,
                    "ok": ok,
                    "detail": detail[:1000],
                    "token_mark": token_mark_detail,
                },
            }
        )
        print("action_ok" if ok else "action_failed")
        if detail:
            print(detail)
        return 0 if ok else 4
    if args.action_id == "run_ip_fortress_scrubber":
        ok, detail = _run_ip_fortress_scrubber()
        token_mark_detail = ""
        if ok and token_path is not None:
            m_ok, m_msg = _mark_token_used(token_path, args.action_id)
            token_mark_detail = m_msg
            if not m_ok:
                ok = False
                detail = f"{detail}\n{m_msg}".strip()
        _append_audit(
            {
                "timestamp": _now_iso(),
                "mission_id": "mkm_internal_inspector_v1",
                "stage": "action_gate",
                "decision": "execute_run_ip_fortress_scrubber",
                "evidence_path": str(ART / "sentinel_realtime_alert_latest.json").replace("\\", "/"),
                "actor": "Guardian",
                "risk_level": args.level,
                "note": {"ok": ok, "detail": detail[:1000], "token_mark": token_mark_detail},
            }
        )
        print("action_ok" if ok else "action_failed")
        if detail:
            print(detail)
        return 0 if ok else 4
    if args.action_id == "preview_python_cache_cleanup":
        ok, detail = _preview_python_cache_cleanup()
        token_mark_detail = ""
        if ok and token_path is not None:
            m_ok, m_msg = _mark_token_used(token_path, args.action_id)
            token_mark_detail = m_msg
            if not m_ok:
                ok = False
                detail = f"{detail}\n{m_msg}".strip()
        _append_audit(
            {
                "timestamp": _now_iso(),
                "mission_id": "mkm_internal_inspector_v1",
                "stage": "action_gate",
                "decision": "execute_preview_python_cache_cleanup",
                "evidence_path": str(ART / "sentinel_realtime_alert_latest.json").replace("\\", "/"),
                "actor": "Operator",
                "risk_level": args.level,
                "note": {"ok": ok, "detail": detail[:1000], "token_mark": token_mark_detail},
            }
        )
        print("action_ok" if ok else "action_failed")
        if detail:
            print(detail)
        return 0 if ok else 4

    return 2


if __name__ == "__main__":
    raise SystemExit(main())

