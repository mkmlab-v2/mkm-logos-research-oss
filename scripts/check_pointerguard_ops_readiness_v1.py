#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
ART = ROOT / "docs" / "final" / "artifacts"
OUT_DEFAULT = ART / "pointerguard_ops_readiness_latest.json"
TASK_NAME = "MKM_PointerGuard_ControlChain_Daily"


def _now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _parse_dt(raw: str) -> datetime | None:
    try:
        return datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
    except Exception:
        return None


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _check_file(path: Path, schema: str) -> dict[str, Any]:
    if not path.exists():
        return {"ok": False, "path": str(path), "reason": "missing_file"}
    try:
        doc = _read_json(path)
    except Exception:
        return {"ok": False, "path": str(path), "reason": "invalid_json"}
    if str(doc.get("schema", "")) != schema:
        return {"ok": False, "path": str(path), "reason": "schema_mismatch"}
    return {"ok": True, "path": str(path), "reason": "ok"}


def _check_security_hardening(path: Path) -> dict[str, Any]:
    base = _check_file(path, "pointerguard_security_hardening_v1")
    if not base.get("ok", False):
        return base
    doc = _read_json(path)
    controls = doc.get("controls", {})
    required = [
        "C1_scope_guard",
        "C6_abuse_guard",
        "leaked_info_scanner",
        "p0_priority_inversion",
        "manual_promotion_lock",
    ]
    missing = [k for k in required if k not in controls]
    if missing:
        return {"ok": False, "path": str(path), "reason": "missing_controls", "missing_controls": missing}
    bad = [k for k in required if str(controls.get(k, {}).get("status")) != "PASS"]
    if bad:
        return {"ok": False, "path": str(path), "reason": "control_not_pass", "failed_controls": bad}
    if not bool(doc.get("all_ok", False)):
        return {"ok": False, "path": str(path), "reason": "hardening_all_ok_false"}
    return {"ok": True, "path": str(path), "reason": "ok"}


def _check_launch_checklist(path: Path) -> dict[str, Any]:
    base = _check_file(path, "a_codeai_public_benchmark_launch_checklist_v1")
    if not base.get("ok", False):
        return base
    doc = _read_json(path)
    decision = str(doc.get("summary", {}).get("decision", ""))
    allowed = {"READY_FOR_SHADOW_PUBLIC_BENCH", "READY_FOR_PUBLIC_OPEN_BENCH"}
    if decision not in allowed:
        return {"ok": False, "path": str(path), "reason": "launch_checklist_not_ready", "decision": decision}
    return {"ok": True, "path": str(path), "reason": "ok", "decision": decision}


def _check_manual_approval_log(path: Path) -> dict[str, Any]:
    base = _check_file(path, "pointerguard_manual_approval_log_v1")
    if not base.get("ok", False):
        return base
    doc = _read_json(path)
    policy = doc.get("policy", {})
    if not bool(policy.get("manual_promotion_lock", False)):
        return {"ok": False, "path": str(path), "reason": "manual_promotion_lock_disabled"}
    if not bool(policy.get("requires_two_person_review", False)):
        return {"ok": False, "path": str(path), "reason": "two_person_review_disabled"}
    if not bool(policy.get("approval_log_required", False)):
        return {"ok": False, "path": str(path), "reason": "approval_log_required_disabled"}
    return {"ok": True, "path": str(path), "reason": "ok"}


def _check_scheduler_arguments_evidence(path: Path) -> dict[str, Any]:
    base = _check_file(path, "pointerguard_scheduler_arguments_evidence_v1")
    if not base.get("ok", False):
        return base
    doc = _read_json(path)
    if not bool(doc.get("verified", False)):
        return {"ok": False, "path": str(path), "reason": "scheduler_evidence_not_verified"}
    if not bool(doc.get("contains_weekly_p0_drill_day_flag", False)):
        return {"ok": False, "path": str(path), "reason": "weekly_p0_drill_day_flag_missing"}
    return {"ok": True, "path": str(path), "reason": "ok"}


def _check_public_binding(path: Path) -> dict[str, Any]:
    base = _check_file(path, "a_codeai_public_binding_check_v1")
    if not base.get("ok", False):
        return base
    doc = _read_json(path)
    if not bool(doc.get("all_ok", False)):
        return {"ok": False, "path": str(path), "reason": "public_binding_not_active"}
    return {"ok": True, "path": str(path), "reason": "ok"}


def _check_monthly_live_p0_drill(history_path: Path, max_age_days: int = 40) -> dict[str, Any]:
    if not history_path.exists():
        return {"ok": False, "path": str(history_path), "reason": "missing_p0_drill_history"}
    rows: list[dict[str, Any]] = []
    for line in history_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(row, dict):
            rows.append(row)
    now = datetime.now(timezone.utc)
    threshold = now.timestamp() - (max_age_days * 86400)
    for row in reversed(rows):
        dt = _parse_dt(row.get("generated_at_utc"))
        if dt is None or dt.timestamp() < threshold:
            continue
        if bool(row.get("dry_run", True)):
            continue
        if bool(row.get("ok", False)):
            return {
                "ok": True,
                "path": str(history_path),
                "reason": "ok",
                "latest_live_ok_at_utc": row.get("generated_at_utc"),
            }
    return {"ok": False, "path": str(history_path), "reason": "monthly_live_p0_drill_missing_recent_success"}


def _check_task() -> dict[str, Any]:
    cp = subprocess.run(
        ["schtasks", "/Query", "/TN", TASK_NAME, "/FO", "LIST"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    if cp.returncode != 0:
        return {"ok": False, "reason": "task_not_found", "detail": cp.stderr.strip()}
    body = cp.stdout
    status = "Unknown"
    next_run = ""
    for line in body.splitlines():
        if line.startswith("Status:"):
            status = line.split(":", 1)[1].strip()
        elif line.startswith("Next Run Time:"):
            next_run = line.split(":", 1)[1].strip()
    return {"ok": status.lower() in {"ready", "running"}, "reason": "ok", "status": status, "next_run_time": next_run}


def _read_dotenv_keys(path: Path) -> dict[str, str]:
    if not path.is_file():
        return {}
    out: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        s = line.strip()
        if not s or s.startswith("#") or "=" not in s:
            continue
        key, val = s.split("=", 1)
        key = key.strip()
        val = val.strip().strip('"').strip("'")
        if key and val:
            out[key] = val
    return out


def _resolve_pointerguard_webhook() -> str:
    for key in (
        "POINTERGUARD_OPS_WEBHOOK_URL",
        "OPS_ALARM_WEBHOOK_URL",
        "N8N_WEBHOOK_URL",
        "SLACK_WEBHOOK_URL",
    ):
        val = os.getenv(key, "").strip()
        if val:
            return val
    dotenv = _read_dotenv_keys(ROOT / ".env")
    for key in (
        "POINTERGUARD_OPS_WEBHOOK_URL",
        "OPS_ALARM_WEBHOOK_URL",
        "N8N_WEBHOOK_URL",
        "SLACK_WEBHOOK_URL",
    ):
        val = dotenv.get(key, "").strip()
        if val:
            return val
    return ""


def main() -> int:
    checks = []
    checks.append(_check_file(ART / "genesis_pointer_routing_control_chain_latest.json", "genesis_pointer_routing_control_chain_v1"))
    checks.append(_check_file(ART / "pointerguard_operational_smoke_latest.json", "pointerguard_operational_smoke_v1"))
    checks.append(_check_file(ART / "pointerguard_two_tier_perf_scorecard_latest.json", "pointerguard_two_tier_perf_scorecard_v1"))
    checks.append(_check_security_hardening(ART / "pointerguard_security_hardening_latest.json"))
    checks.append(_check_launch_checklist(ART / "a_codeai_public_benchmark_launch_checklist_v1.json"))
    checks.append(_check_public_binding(ART / "a_codeai_public_binding_check_latest.json"))
    checks.append(_check_manual_approval_log(ART / "pointerguard_manual_approval_log_latest.json"))
    checks.append(_check_scheduler_arguments_evidence(ART / "pointerguard_scheduler_arguments_evidence_latest.json"))
    checks.append(_check_monthly_live_p0_drill(ART / "pointerguard_p0_alert_drill_history_v1.jsonl", max_age_days=40))
    task_check = _check_task()
    checks.append({"ok": task_check.get("ok", False), "path": f"task://{TASK_NAME}", "reason": task_check.get("reason"), "detail": task_check})

    webhook = _resolve_pointerguard_webhook()
    webhook_check = {
        "ok": bool(webhook),
        "path": "env://POINTERGUARD_OPS_WEBHOOK_URL|OPS_ALARM_WEBHOOK_URL",
        "reason": "ok" if webhook else "missing_webhook_env",
        "fallback_chain": [
            "POINTERGUARD_OPS_WEBHOOK_URL",
            "OPS_ALARM_WEBHOOK_URL",
            "N8N_WEBHOOK_URL",
            "SLACK_WEBHOOK_URL",
        ],
    }
    checks.append(webhook_check)

    all_ok = all(bool(c.get("ok", False)) for c in checks)
    out_doc = {
        "schema": "pointerguard_ops_readiness_v1",
        "generated_at_utc": _now_utc(),
        "all_ok": all_ok,
        "checks": checks,
    }
    OUT_DEFAULT.write_text(json.dumps(out_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "all_ok": all_ok, "out": str(OUT_DEFAULT)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
