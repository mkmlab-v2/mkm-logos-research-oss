#!/usr/bin/env python3
"""Delete legacy English n8n Telegram workflows on VPS (keep allow-list) and restart n8n."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports" / "n8n_telegram_archive_legacy_v1_latest.json"
VPS_DB = "/var/lib/docker/volumes/n8n_final/_data/database.sqlite"
ALLOW = {"compression-pilot-audit-lead-webhook"}


def _read_workspace_env(key: str) -> str:
    env_path = ROOT / ".env"
    if not env_path.is_file():
        return ""
    prefix = f"{key}="
    for line in env_path.read_text(encoding="utf-8", errors="replace").splitlines():
        if line.startswith(prefix):
            return line[len(prefix) :].strip().strip('"').strip("'")
    return ""


def _ssh_cmd(remote: str, *args: str) -> list[str]:
    cmd = ["ssh", "-o", "BatchMode=yes"]
    key = os.environ.get("MKM_VPS_SSH_KEY_PATH") or _read_workspace_env("MKM_VPS_SSH_KEY_PATH")
    if key:
        cmd.extend(["-i", key])
    cmd.append(remote)
    cmd.extend(args)
    return cmd


def main() -> int:
    host = os.environ.get("MKM_VPS_HOST") or _read_workspace_env("MKM_VPS_HOST") or "srv1101456.hstgr.cloud"
    user = os.environ.get("MKM_VPS_USER") or _read_workspace_env("MKM_VPS_USER") or "root"
    remote = f"{user}@{host}"
    allow_json = json.dumps(sorted(ALLOW), ensure_ascii=False)
    remote_py = f"""
import sqlite3, json
DB = {VPS_DB!r}
ALLOW = set(json.loads({allow_json!r}))
con = sqlite3.connect(DB)
rows = con.execute("SELECT id, name, active, isArchived, nodes FROM workflow_entity").fetchall()
deleted = []
for wf_id, name, active, is_archived, nodes in rows:
    if name in ALLOW:
        continue
    blob = (nodes or "").lower()
    if "telegram" not in blob:
        continue
    con.execute("DELETE FROM webhook_entity WHERE workflowId = ?", (wf_id,))
    con.execute("DELETE FROM shared_workflow WHERE workflowId = ?", (wf_id,))
    con.execute("DELETE FROM workflow_entity WHERE id = ?", (wf_id,))
    deleted.append({{
        "id": wf_id,
        "name": name,
        "was_active": bool(active),
        "was_archived": bool(is_archived),
    }})
con.commit()
remaining_observe = [
    r[0] for r in con.execute(
        "SELECT webhookPath FROM webhook_entity WHERE webhookPath = 'btc-phase1-observe-alert'"
    ).fetchall()
]
print(json.dumps({{"deleted": deleted, "observe_alert_webhooks_remaining": remaining_observe}}, ensure_ascii=False))
"""
    proc = subprocess.run(
        _ssh_cmd(remote, "python3", "-"),
        input=remote_py,
        text=True,
        capture_output=True,
        check=False,
    )
    if proc.returncode != 0:
        print(proc.stderr or proc.stdout, file=sys.stderr)
        return proc.returncode
    payload = json.loads(proc.stdout.strip().splitlines()[-1])
    restart = subprocess.run(
        _ssh_cmd(remote, "docker", "restart", "n8n"),
        capture_output=True,
        text=True,
        check=False,
    )
    out = {
        "schema": "n8n_telegram_archive_legacy_v1",
        "checked_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "ok": restart.returncode == 0,
        "deleted_count": len(payload.get("deleted") or []),
        "deleted": payload.get("deleted") or [],
        "observe_alert_webhooks_remaining": payload.get("observe_alert_webhooks_remaining") or [],
        "n8n_restart_exit": restart.returncode,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0 if out["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
