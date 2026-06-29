#!/usr/bin/env python3
"""Auto-fix: disable bloated plugin MCP servers in Cursor reactive storage."""
from __future__ import annotations

import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

STORAGE_KEY = (
    "src.vs.platform.reactivestorage.browser.reactiveStorageServiceImpl"
    ".persistentStorage.applicationUser"
)

PLUGIN_SERVERS_TO_DISABLE = [
    "plugin-postman-postman",
    "plugin-atlassian-atlassian",
    "plugin-slack-slack",
    "plugin-datadog-datadog",
    "plugin-sentry-sentry",
    "plugin-cloudflare-cloudflare-bindings",
    "plugin-cloudflare-cloudflare-docs",
    "plugin-cloudflare-cloudflare-builds",
    "plugin-cloudflare-cloudflare-observability",
    "plugin-exa-exa",
    "plugin-figma-figma",
    "plugin-linear-linear",
    "plugin-semgrep-plugin-semgrep",
    "plugin-sourcegraph-cursor-plugin-sourcegraph",
]

KEEP_SERVERS = {
    "project-0-workspace-filesystem",
    "project-0-workspace-athena-core",
    "project-0-workspace-sequential-thinking",
    "project-0-workspace-athena-manseryeok",
    "project-0-workspace-compression-server",
    "project-0-workspace-devops-mcp",
    "project-0-workspace-notebooklm",
    "cursor-ide-browser",
}


def main() -> int:
    db = Path.home() / "AppData/Roaming/Cursor/User/globalStorage/state.vscdb"
    if not db.is_file():
        print(f"FAIL: missing {db}")
        return 2

    conn = sqlite3.connect(db)
    cur = conn.cursor()
    cur.execute("SELECT key, value FROM ItemTable")
    rows = {k: v for k, v in cur.fetchall()}

    storage_key = None
    for k in rows:
        if "reactiveStorage" in k and "applicationUser" in k:
            storage_key = k
            break
    if not storage_key:
        print("FAIL: reactive storage key not found")
        return 2

    raw = rows[storage_key]
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8")
    data = json.loads(raw)

    before = list(data.get("disabledMcpServers") or [])
    merged = list(dict.fromkeys(before + PLUGIN_SERVERS_TO_DISABLE))
    data["disabledMcpServers"] = merged
    data["lastBrowserConnectionMode"] = "editor"
    data["browserChipManuallyDisabled"] = False

    new_raw = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    cur.execute("UPDATE ItemTable SET value = ? WHERE key = ?", (new_raw, storage_key))
    conn.commit()
    conn.close()

    added = [s for s in PLUGIN_SERVERS_TO_DISABLE if s not in before]
    report = {
        "schema": "cursor_mcp_plugin_diet_auto_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "disabled_before_count": len(before),
        "disabled_after_count": len(merged),
        "newly_disabled": added,
        "lastBrowserConnectionMode": "editor",
        "note": "Restart Cursor (Reload Window) required for MCP service to pick up disabledMcpServers",
    }
    out = Path("C:/workspace/reports/cursor_mcp_plugin_diet_auto_latest.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"OK: disabledMcpServers {len(before)} -> {len(merged)} (+{len(added)} plugins)")
    print(f"Wrote: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
