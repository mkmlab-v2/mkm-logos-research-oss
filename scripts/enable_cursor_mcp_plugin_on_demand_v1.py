#!/usr/bin/env python3
"""Remove one plugin id from Cursor disabledMcpServers (on-demand enable)."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from cursor_mcp_disabled_servers_v1_lib import (  # noqa: E402
    load_application_user,
    save_application_user,
)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--server-id", required=True)
    ap.add_argument("--what-if", action="store_true")
    args = ap.parse_args()

    storage_key, data = load_application_user()
    before = list(data.get("disabledMcpServers") or [])
    if args.server_id not in before:
        print(f"OK: {args.server_id} already enabled (not in disabled list)")
        return 0

    after = [s for s in before if s != args.server_id]
    data["disabledMcpServers"] = after

    if args.what_if:
        print(json.dumps({"what_if": True, "removed": args.server_id, "count": f"{len(before)}->{len(after)}"}))
        return 0

    save_application_user(storage_key, data, apply=True)
    report = {
        "schema": "cursor_mcp_plugin_enable_on_demand_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "enabled_server": args.server_id,
        "disabled_before_count": len(before),
        "disabled_after_count": len(after),
        "note": "Reload Window required",
    }
    out = ROOT / "reports" / "cursor_mcp_plugin_enable_on_demand_v1_latest.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "enabled": args.server_id, "out": str(out)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
