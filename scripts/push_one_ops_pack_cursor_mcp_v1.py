#!/usr/bin/env python3
"""Push one ops pack file via Cursor-injected NotebookLM MCP only.

Prints instruction JSON for agent CallMcpTool, or if --write-agent-tools writes
C:/Users/PRO/.cursor/projects/c-workspace/agent-tools/mcp_ops_push_<safe>.json

Usage:
  py scripts/push_one_ops_pack_cursor_mcp_v1.py AGENTS.md --write-agent-tools
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / "reports" / "notebooklm_ops_command_sync_pack_v1"
OPS_URL = "https://notebooklm.google.com/notebook/9bc26140-70c4-47d0-b9ea-bd3a394916a9"
AGENT_TOOLS = Path(r"C:\Users\PRO\.cursor\projects\c-workspace\agent-tools")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("filename")
    ap.add_argument("--notebook-url", default=OPS_URL)
    ap.add_argument("--write-agent-tools", action="store_true")
    args = ap.parse_args()
    path = PACK / args.filename
    if not path.is_file():
        print(json.dumps({"error": f"missing {path}"}), file=sys.stderr)
        return 1
    payload = {
        "server": "project-0-workspace-notebooklm",
        "toolName": "add_source",
        "arguments": {
            "type": "text",
            "title": args.filename,
            "content": path.read_text(encoding="utf-8", errors="replace"),
            "notebook_url": args.notebook_url,
        },
    }
    if args.write_agent_tools:
        AGENT_TOOLS.mkdir(parents=True, exist_ok=True)
        safe = re.sub(r"[^a-zA-Z0-9._-]+", "_", args.filename)[:80]
        out = AGENT_TOOLS / f"mcp_ops_push_{safe}.json"
        out.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        print(json.dumps({"written": str(out), "bytes": out.stat().st_size}, ensure_ascii=False))
    else:
        print(json.dumps({"bytes": len(payload["arguments"]["content"]), "title": args.filename}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
