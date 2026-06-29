#!/usr/bin/env python3
"""Deactivate n8n workflows that contain Telegram nodes (local or VPS SQLite SSOT).

Default local DB: ~/.n8n/database.sqlite
VPS mode (--vps): /var/lib/docker/volumes/n8n_final/_data/database.sqlite on MKM VPS.
"""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = Path.home() / ".n8n" / "database.sqlite"
DEFAULT_OUT = ROOT / "reports" / "n8n_telegram_mute_latest.json"
VPS_DB = "/var/lib/docker/volumes/n8n_final/_data/database.sqlite"
DEFAULT_ALLOW_NAMES = ("compression-pilot-audit-lead-webhook",)

TELEGRAM_NODE_HINTS = (
    "n8n-nodes-base.telegram",
    "n8n-nodes-base.telegramTrigger",
    "telegram",
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _workflow_has_telegram(nodes_blob: str | None) -> bool:
    if not nodes_blob:
        return False
    try:
        nodes = json.loads(nodes_blob)
    except json.JSONDecodeError:
        return "telegram" in nodes_blob.lower()
    if not isinstance(nodes, list):
        return False
    for node in nodes:
        if not isinstance(node, dict):
            continue
        ntype = str(node.get("type") or "").lower()
        name = str(node.get("name") or "").lower()
        if any(h in ntype for h in TELEGRAM_NODE_HINTS):
            return True
        if "telegram" in name and "n8n-nodes" in ntype:
            return True
    return False


def mute_database(
    db_path: str,
    *,
    dry_run: bool,
    include_inactive: bool,
    allow_names: set[str],
) -> tuple[list[dict], list[dict]]:
    con = sqlite3.connect(db_path)
    try:
        rows = con.execute(
            "SELECT id, name, active, nodes FROM workflow_entity ORDER BY name"
        ).fetchall()
    except sqlite3.Error as exc:
        raise RuntimeError(f"sqlite read failed: {exc}") from exc

    hits: list[dict] = []
    for row in rows:
        wf_id, name, active, nodes = row[0], row[1], bool(row[2]), row[3]
        if name in allow_names:
            continue
        if not include_inactive and not active:
            continue
        if not _workflow_has_telegram(nodes):
            continue
        hits.append({"id": wf_id, "name": name, "was_active": active})

    muted: list[dict] = []
    if not dry_run:
        for hit in hits:
            if not hit["was_active"]:
                muted.append({**hit, "action": "already_inactive"})
                continue
            con.execute(
                "UPDATE workflow_entity SET active = 0, updatedAt = ? WHERE id = ?",
                (_utc_now(), hit["id"]),
            )
            muted.append({**hit, "action": "deactivated"})
        con.commit()
    else:
        muted = [{**h, "action": "dry_run"} for h in hits]
    return hits, muted


def _read_workspace_env(key: str) -> str:
    env_path = ROOT / ".env"
    if not env_path.is_file():
        return ""
    prefix = f"{key}="
    for line in env_path.read_text(encoding="utf-8", errors="replace").splitlines():
        if line.startswith(prefix):
            return line[len(prefix) :].strip().strip('"').strip("'")
    return ""


def _ssh_command(remote: str, *remote_args: str) -> list[str]:
    cmd = ["ssh", "-o", "BatchMode=yes"]
    key = (
        os.environ.get("MKM_VPS_SSH_KEY_PATH", "").strip()
        or _read_workspace_env("MKM_VPS_SSH_KEY_PATH")
    )
    if key:
        cmd.extend(["-i", key])
    extra = (
        os.environ.get("MKM_VPS_SCP_EXTRA_ARGS", "").strip()
        or _read_workspace_env("MKM_VPS_SCP_EXTRA_ARGS")
    )
    if extra:
        cmd.extend(extra.split())
    cmd.append(remote)
    cmd.extend(remote_args)
    return cmd


def _run_vps_mute(
    *,
    host: str,
    user: str,
    dry_run: bool,
    include_inactive: bool,
    allow_names: set[str],
    restart_n8n: bool,
) -> tuple[list[dict], list[dict]]:
    allow_json = json.dumps(sorted(allow_names), ensure_ascii=False)
    remote_py = f"""
import json, sqlite3
DB = {VPS_DB!r}
ALLOW = set(json.loads({allow_json!r}))
con = sqlite3.connect(DB)
rows = con.execute("SELECT id, name, active, nodes FROM workflow_entity ORDER BY name").fetchall()
hits = []
for wf_id, name, active, nodes in rows:
    if name in ALLOW:
        continue
    if not {int(include_inactive)} and not active:
        continue
    blob = (nodes or "").lower()
    if "telegram" not in blob:
        continue
    hits.append({{"id": wf_id, "name": name, "was_active": bool(active)}})
muted = []
dry = {int(dry_run)}
if not dry:
    for hit in hits:
        if not hit["was_active"]:
            muted.append({{**hit, "action": "already_inactive"}})
            continue
        con.execute("UPDATE workflow_entity SET active = 0 WHERE id = ?", (hit["id"],))
        muted.append({{**hit, "action": "deactivated"}})
    con.commit()
else:
    muted = [{{**h, "action": "dry_run"}} for h in hits]
print(json.dumps({{"hits": hits, "muted": muted}}, ensure_ascii=False))
"""
    remote = f"{user}@{host}"
    proc = subprocess.run(
        _ssh_command(remote, "python3", "-"),
        input=remote_py,
        text=True,
        capture_output=True,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            f"VPS mute failed exit {proc.returncode}: {proc.stderr.strip() or proc.stdout.strip()}"
        )
    try:
        payload = json.loads(proc.stdout.strip().splitlines()[-1])
    except (json.JSONDecodeError, IndexError) as exc:
        raise RuntimeError(f"VPS mute parse failed: {proc.stdout[:500]}") from exc

    if restart_n8n and not dry_run and any(m.get("action") == "deactivated" for m in payload["muted"]):
        restart = subprocess.run(
            _ssh_command(remote, "docker", "restart", "n8n"),
            capture_output=True,
            text=True,
            check=False,
        )
        if restart.returncode != 0:
            raise RuntimeError(f"n8n restart failed: {restart.stderr.strip()}")

    return payload["hits"], payload["muted"]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--db", type=Path, default=DEFAULT_DB)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--dry-run", action="store_true", help="Report only; do not deactivate")
    ap.add_argument("--include-inactive", action="store_true")
    ap.add_argument(
        "--allow-names",
        default=",".join(DEFAULT_ALLOW_NAMES),
        help="Comma-separated workflow names to keep active even if they contain Telegram nodes",
    )
    ap.add_argument("--vps", action="store_true", help="Mute VPS docker n8n DB via SSH")
    ap.add_argument("--vps-host", default=os.environ.get("MKM_VPS_HOST") or _read_workspace_env("MKM_VPS_HOST") or "vps-mkmlife")
    ap.add_argument("--vps-user", default=os.environ.get("MKM_VPS_USER") or _read_workspace_env("MKM_VPS_USER") or "root")
    ap.add_argument(
        "--restart-n8n",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Restart n8n docker container after VPS deactivations (default: true)",
    )
    args = ap.parse_args()

    allow_names = {n.strip() for n in args.allow_names.split(",") if n.strip()}

    try:
        if args.vps:
            hits, muted = _run_vps_mute(
                host=args.vps_host,
                user=args.vps_user,
                dry_run=args.dry_run,
                include_inactive=args.include_inactive,
                allow_names=allow_names,
                restart_n8n=args.restart_n8n,
            )
            db_label = f"ssh://{args.vps_user}@{args.vps_host}:{VPS_DB}"
        else:
            if not args.db.is_file():
                print(f"SKIP: n8n database missing: {args.db}")
                out = {
                    "schema": "n8n_telegram_mute_v1",
                    "checked_at_utc": _utc_now(),
                    "ok": False,
                    "reason": "database_missing",
                    "db": str(args.db),
                }
                args.out_json.parent.mkdir(parents=True, exist_ok=True)
                args.out_json.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
                return 0
            hits, muted = mute_database(
                str(args.db),
                dry_run=args.dry_run,
                include_inactive=args.include_inactive,
                allow_names=allow_names,
            )
            db_label = str(args.db)
    except RuntimeError as exc:
        print(f"FAIL: {exc}")
        return 1

    out = {
        "schema": "n8n_telegram_mute_v1",
        "checked_at_utc": _utc_now(),
        "ok": True,
        "dry_run": bool(args.dry_run),
        "db": db_label,
        "allow_names": sorted(allow_names),
        "telegram_workflows_found": len(hits),
        "workflows": muted,
    }
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(out, ensure_ascii=False, indent=2))
    print(f"WROTE: {args.out_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
