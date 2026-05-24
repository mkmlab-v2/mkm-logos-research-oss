#!/usr/bin/env python3
import json
from pathlib import Path

OPS = "https://notebooklm.google.com/notebook/9bc26140-70c4-47d0-b9ea-bd3a394916a9"
BASE = Path(r"c:\workspace\reports\notebooklm_ops_mcp_chunks\_mcp_call_queue")
OUT = Path(r"C:\Users\PRO\.cursor\projects\c-workspace\agent-tools")

items = [
    ("01_P0_COMMERCIALIZATION_TRACKER.md.args.json", "P0_COMMERCIALIZATION_TRACKER.md"),
    ("02_NotebookLM_sources_manifest.md.args.json", "NotebookLM_sources_manifest.md"),
    ("03_AGENTS.md.args.json", "AGENTS.md"),
    ("04_CENTRAL_AGENT_MEMORY_V1.md.args.json", "CENTRAL_AGENT_MEMORY_V1.md"),
]
for fn, title in items:
    a = json.loads((BASE / fn).read_text(encoding="utf-8"))
    safe = title.replace(".", "_")
    path = OUT / f"mcp_ops_push_{safe}.json"
    path.write_text(
        json.dumps(
            {
                "server": "project-0-workspace-notebooklm",
                "toolName": "add_source",
                "arguments": a,
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    print(title, len(a["content"]), path.stat().st_size)
