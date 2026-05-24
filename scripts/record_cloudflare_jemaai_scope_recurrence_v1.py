#!/usr/bin/env python3
"""Append jemaai rulesets scope-mismatch events; emit recurrence summary for ops gates."""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOG_PATH = ROOT / "reports" / "cloudflare_jemaai_scope_recurrence_log.jsonl"
OUT_PATH = ROOT / "reports" / "cloudflare_jemaai_scope_recurrence_v1_latest.json"
CHECK_SCRIPT = ROOT / "scripts" / "check_jemaai_cloud_cf_rules_token_v1.py"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run_check() -> dict:
    proc = subprocess.run(
        [sys.executable, str(CHECK_SCRIPT)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    payload: dict = {}
    if proc.stdout.strip():
        try:
            payload = json.loads(proc.stdout)
        except json.JSONDecodeError:
            payload = {"parse_error": True, "stdout_tail": proc.stdout[-500:]}
    return {
        "exit_code": proc.returncode,
        "check": payload,
        "automation_ready": bool(payload.get("automation_ready")),
    }


def _load_log() -> list[dict]:
    if not LOG_PATH.exists():
        return []
    rows: list[dict] = []
    for line in LOG_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return rows


def _append_event(snapshot: dict) -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    row = {
        "schema": "cloudflare_jemaai_scope_recurrence_v1",
        "at_utc": _utc_now(),
        **snapshot,
    }
    with LOG_PATH.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def _counts(rows: list[dict], *, days: int = 7) -> dict:
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    total_blocked = sum(1 for r in rows if not r.get("automation_ready"))
    recent_blocked = 0
    for r in rows:
        if r.get("automation_ready"):
            continue
        at = r.get("at_utc", "")
        try:
            ts = datetime.strptime(at, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        except ValueError:
            continue
        if ts >= cutoff:
            recent_blocked += 1
    return {
        "total_events": len(rows),
        "total_blocked_events": total_blocked,
        f"blocked_last_{days}d": recent_blocked,
    }


def main() -> int:
    snap = _run_check()
    check = snap.get("check") or {}
    fingerprint = check.get("token_fingerprint", "")
    missing = check.get("missing_cf_ui_permissions") or check.get("next_if_blocked")

    if not snap["automation_ready"]:
        _append_event(
            {
                "automation_ready": False,
                "token_fingerprint": fingerprint,
                "token_source": check.get("token_source"),
                "missing_cf_ui_permissions": missing,
                "exit_code": snap["exit_code"],
            }
        )

    rows = _load_log()
    counts = _counts(rows)
    out = {
        "schema": "cloudflare_jemaai_scope_recurrence_v1",
        "generated_at_utc": _utc_now(),
        "automation_ready": snap["automation_ready"],
        "token_fingerprint": fingerprint,
        "missing_cf_ui_permissions": check.get("missing_cf_ui_permissions"),
        "recurrence": counts,
        "log_path": str(LOG_PATH.relative_to(ROOT)).replace("\\", "/"),
        "dashboard_ssot": "docs/final/JEMAAI_CLOUD_SHOWROOM_CF_EDGE_DASHBOARD_V1.md",
        "agent_never": [
            "say token expired when token_verify success=true and rulesets 403",
            "overwrite CLOUDFLARE_API_TOKEN for jemaai rulesets",
            "create new token daily",
        ],
        "commander_one_shot": (
            "CF API Tokens: edit SAME token → Zone WAF Edit + Cache Rules Edit on jemaai.cloud only "
            "(not Cache Settings, not mkmlife-analytics-only)."
        ),
        "verify_command": "py scripts/check_jemaai_cloud_cf_rules_token_v1.py",
    }
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0 if snap["automation_ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
