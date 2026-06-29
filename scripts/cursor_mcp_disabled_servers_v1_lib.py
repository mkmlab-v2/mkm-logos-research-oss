"""Read/write Cursor disabledMcpServers in state.vscdb (reactive storage)."""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

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

DEFAULT_DB = Path.home() / "AppData/Roaming/Cursor/User/globalStorage/state.vscdb"
DEFAULT_SNAPSHOT = Path("C:/workspace/reports/cursor_mcp_disabled_servers_snapshot_v1_latest.json")


def default_db_path() -> Path:
    return DEFAULT_DB


def find_storage_key(keys: list[str]) -> str | None:
    for k in keys:
        if "reactiveStorage" in k and "applicationUser" in k:
            return k
    return None


def load_application_user(db_path: Path | None = None) -> tuple[str, dict[str, Any]]:
    db = db_path or default_db_path()
    if not db.is_file():
        raise FileNotFoundError(f"missing {db}")
    conn = sqlite3.connect(db)
    cur = conn.cursor()
    cur.execute("SELECT key, value FROM ItemTable")
    rows = {k: v for k, v in cur.fetchall()}
    conn.close()
    storage_key = find_storage_key(list(rows.keys()))
    if not storage_key:
        raise RuntimeError("reactive storage key not found")
    raw = rows[storage_key]
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8")
    return storage_key, json.loads(raw)


def merge_disabled(current: list[str] | None, extra: list[str]) -> list[str]:
    base = list(current or [])
    return list(dict.fromkeys(base + list(extra)))


def save_application_user(
    storage_key: str,
    data: dict[str, Any],
    *,
    db_path: Path | None = None,
    apply: bool = True,
) -> None:
    if not apply:
        return
    db = db_path or default_db_path()
    new_raw = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    conn = sqlite3.connect(db)
    cur = conn.cursor()
    cur.execute("UPDATE ItemTable SET value = ? WHERE key = ?", (new_raw, storage_key))
    conn.commit()
    conn.close()


def build_sync_payload(data: dict[str, Any], plugin_list: list[str] | None = None) -> dict[str, Any]:
    plugins = plugin_list if plugin_list is not None else PLUGIN_SERVERS_TO_DISABLE
    out = dict(data)
    before = list(out.get("disabledMcpServers") or [])
    merged = merge_disabled(before, plugins)
    out["disabledMcpServers"] = merged
    out["lastBrowserConnectionMode"] = "editor"
    out["browserChipManuallyDisabled"] = False
    return out
