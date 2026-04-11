#!/usr/bin/env python3
"""Walk Cursor MCP tool descriptor JSONs and write a Fact-Lock inventory JSON.

Default mcps root: env MKM_MCP_DESCRIPTORS_ROOT, else common local path (Windows).

Example:
  py scripts/dump_mcp_tool_inventory.py --mcps-root "C:\\Users\\PRO\\.cursor\\projects\\c-workspace\\mcps"
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path


def _default_mcps_root() -> Path | None:
    env = os.environ.get("MKM_MCP_DESCRIPTORS_ROOT", "").strip()
    if env:
        return Path(env)
    win = Path(os.environ.get("USERPROFILE", "")) / ".cursor" / "projects" / "c-workspace" / "mcps"
    if win.is_dir():
        return win
    return None


def _truncate(s: str | None, n: int) -> str:
    if not s:
        return ""
    s = s.replace("\n", " ").strip()
    return s if len(s) <= n else s[: n - 3] + "..."


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--mcps-root",
        type=Path,
        default=None,
        help="Folder containing per-server subdirs with tools/*.json (default: env or USERPROFILE/.cursor/projects/c-workspace/mcps)",
    )
    ap.add_argument(
        "-o",
        "--out",
        type=Path,
        default=Path("docs/final/artifacts/mkm_mcp_tool_audit_v1.json"),
        help="Output JSON path (repo-relative to cwd)",
    )
    ns = ap.parse_args()
    root = ns.mcps_root or _default_mcps_root()
    if root is None or not root.is_dir():
        print("FAIL: mcps root not found. Set MKM_MCP_DESCRIPTORS_ROOT or pass --mcps-root.", file=sys.stderr)
        return 2

    servers: list[dict] = []
    for server_dir in sorted(root.iterdir()):
        if not server_dir.is_dir():
            continue
        tools_dir = server_dir / "tools"
        if not tools_dir.is_dir():
            continue
        tools: list[dict] = []
        for jf in sorted(tools_dir.glob("*.json")):
            try:
                raw = json.loads(jf.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            name = raw.get("name") or jf.stem
            desc = raw.get("description")
            tools.append(
                {
                    "name": name,
                    "descriptor_file": str(jf.relative_to(root)).replace("\\", "/"),
                    "description_excerpt": _truncate(desc if isinstance(desc, str) else None, 240),
                }
            )
        if tools:
            servers.append(
                {
                    "server_folder": server_dir.name,
                    "tool_count": len(tools),
                    "tools": tools,
                }
            )

    hub = {
        "schema": "mkm_mcp_tool_audit_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "mcps_root_resolved": str(root.resolve()),
        "server_count": len(servers),
        "total_tool_count": sum(s["tool_count"] for s in servers),
        "servers": servers,
        "integration_notes": {
            "compression_prophecy_locus": (
                "project-0-workspace-compression-server already exposes compress_text, restore_text, "
                "compress_file, compress_rules, acon_* — extend here for token-economy wrappers rather than "
                "a new MCP server unless isolation is required."
            ),
            "overlap_warning": (
                "project-0-workspace-local-rag (search_vault, reindex_vault) vs compression-server both "
                "feed context; unified MKM hub tools must not duplicate search_vault semantics — use distinct "
                "names (e.g. get_prophecy_registry_slice vs search_vault)."
            ),
            "prophecy_fact_lock": (
                "Read SSOT files via scripts or thin MCP tools that call the same paths as "
                "docs/final/CURRENT_OPS_SNAPSHOT.md (general_prophecy_latest.json, export chain) — avoid ad-hoc "
                "NotebookLM dumps as registry."
            ),
        },
    }

    out = ns.out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(hub, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"OK: {len(servers)} servers, {hub['total_tool_count']} tools -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
