#!/usr/bin/env python3
"""Emit add_source arguments JSON path for agent CallMcpTool (no stdio MCP)."""
import json
import sys
from pathlib import Path

p = Path(sys.argv[1])
args = json.loads(p.read_text(encoding="utf-8"))
# stdout: title + content length only; agent loads args file for CallMcpTool
print(json.dumps({"args_path": str(p), "title": args.get("title"), "content_len": len(args.get("content", ""))}, ensure_ascii=False))
