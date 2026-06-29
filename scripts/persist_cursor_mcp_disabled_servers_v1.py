#!/usr/bin/env python3
"""Export / restore / sync Cursor disabledMcpServers (M-ticket · Reload regression)."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from cursor_mcp_disabled_servers_v1_lib import (
    DEFAULT_SNAPSHOT,
    PLUGIN_SERVERS_TO_DISABLE,
    build_sync_payload,
    default_db_path,
    load_application_user,
    merge_disabled,
    save_application_user,
)

def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def cmd_export(snapshot_path: Path) -> int:
    try:
        _, data = load_application_user()
    except FileNotFoundError as e:
        print(f"SKIP: {e}")
        return 0
    disabled = list(data.get("disabledMcpServers") or [])
    payload = {
        "schema": "cursor_mcp_disabled_servers_snapshot_v1",
        "generated_at_utc": _utc(),
        "disabled_mcp_servers": disabled,
        "plugin_servers_ssot": list(PLUGIN_SERVERS_TO_DISABLE),
        "source": "export",
    }
    snapshot_path.parent.mkdir(parents=True, exist_ok=True)
    snapshot_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "action": "export", "count": len(disabled), "out": str(snapshot_path)}))
    return 0


def _load_snapshot(snapshot_path: Path) -> list[str]:
    if not snapshot_path.is_file():
        return list(PLUGIN_SERVERS_TO_DISABLE)
    doc = json.loads(snapshot_path.read_text(encoding="utf-8"))
    snap = list(doc.get("disabled_mcp_servers") or [])
    ssot = list(doc.get("plugin_servers_ssot") or PLUGIN_SERVERS_TO_DISABLE)
    return list(dict.fromkeys(snap + ssot))


def cmd_restore(snapshot_path: Path, *, apply: bool) -> int:
    try:
        storage_key, data = load_application_user()
    except FileNotFoundError as e:
        print(f"SKIP: {e}")
        return 0
    to_merge = _load_snapshot(snapshot_path)
    before = list(data.get("disabledMcpServers") or [])
    merged = merge_disabled(before, to_merge)
    added = [s for s in merged if s not in before]
    report = {
        "schema": "cursor_mcp_disabled_servers_restore_v1",
        "generated_at_utc": _utc(),
        "apply": apply,
        "disabled_before_count": len(before),
        "disabled_after_count": len(merged),
        "newly_merged": added,
        "snapshot": str(snapshot_path),
    }
    if apply:
        cmd_export(snapshot_path.with_name(snapshot_path.stem + "_pre_restore_backup.json"))
        new_data = dict(data)
        new_data["disabledMcpServers"] = merged
        new_data["lastBrowserConnectionMode"] = "editor"
        new_data["browserChipManuallyDisabled"] = False
        save_application_user(storage_key, new_data, apply=True)
        report["note"] = "applied to state.vscdb; Reload Window recommended"
    else:
        report["note"] = "dry-run only; pass --apply to write"
    out = ROOT / "reports" / "cursor_mcp_disabled_servers_restore_v1_latest.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "action": "restore", "apply": apply, "out": str(out)}))
    return 0


def cmd_sync(snapshot_path: Path, *, apply: bool) -> int:
    try:
        storage_key, data = load_application_user()
    except FileNotFoundError as e:
        print(f"SKIP: {e}")
        return 0
    snap_extra = _load_snapshot(snapshot_path) if snapshot_path.is_file() else []
    plugins = list(dict.fromkeys(list(PLUGIN_SERVERS_TO_DISABLE) + snap_extra))
    before = list(data.get("disabledMcpServers") or [])
    new_data = build_sync_payload(data, plugins)
    merged = list(new_data.get("disabledMcpServers") or [])
    added = [s for s in merged if s not in before]
    if apply:
        save_application_user(storage_key, new_data, apply=True)
        cmd_export(snapshot_path)
    report = {
        "schema": "cursor_mcp_disabled_servers_sync_v1",
        "generated_at_utc": _utc(),
        "apply": apply,
        "disabled_before_count": len(before),
        "disabled_after_count": len(merged),
        "newly_merged": added,
    }
    out = ROOT / "reports" / "cursor_mcp_disabled_servers_sync_v1_latest.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "action": "sync", "apply": apply, "out": str(out)}))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("command", choices=["export", "restore", "sync"])
    ap.add_argument("--snapshot", type=Path, default=DEFAULT_SNAPSHOT)
    ap.add_argument("--apply", action="store_true", help="Write state.vscdb (default dry-run for restore/sync)")
    args = ap.parse_args()
    if args.command == "export":
        return cmd_export(args.snapshot)
    if args.command == "restore":
        return cmd_restore(args.snapshot, apply=args.apply)
    return cmd_sync(args.snapshot, apply=args.apply)


if __name__ == "__main__":
    raise SystemExit(main())
