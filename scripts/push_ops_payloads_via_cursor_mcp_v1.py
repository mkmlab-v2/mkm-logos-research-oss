#!/usr/bin/env python3
"""Load ops push cursor queue payloads; print progress JSONL for agent MCP bridge.

Agent reads each line, CallMcpTool add_source with printed arguments (stdout is metadata only).

Usage:
  py scripts/push_ops_payloads_via_cursor_mcp_v1.py --index 0
  py scripts/push_ops_payloads_via_cursor_mcp_v1.py --all-meta
"""
from __future__ import annotations

import argparse
import base64
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
Q = ROOT / "reports" / "notebooklm_ops_push_cursor_queue"
ORDER = [
    "00_ops_command_handoff_snippet.md.payload.json",
    "P0_COMMERCIALIZATION_TRACKER.md.payload.json",
    "AGENTS.md.payload.json",
    "NotebookLM_sources_manifest.md.payload.json",
    "CENTRAL_AGENT_MEMORY_V1.md__part1of2.payload.json",
    "CENTRAL_AGENT_MEMORY_V1.md__part2of2.payload.json",
]


def load_args(index: int) -> dict:
    path = Q / ORDER[index]
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload["arguments"]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--index", type=int, default=-1)
    ap.add_argument("--all-meta", action="store_true")
    ap.add_argument("--write-b64", action="store_true", help="write _active_b64.txt + _active_title.txt for index")
    args = ap.parse_args()
    if args.all_meta:
        for i, name in enumerate(ORDER):
            a = load_args(i)
            print(json.dumps({"index": i, "title": a["title"], "chars": len(a["content"])}, ensure_ascii=False))
        return 0
    if args.index < 0 or args.index >= len(ORDER):
        print(json.dumps({"error": "index required 0..5"}), file=sys.stderr)
        return 1
    a = load_args(args.index)
    if args.write_b64:
        (Q / "_active_title.txt").write_text(a["title"], encoding="utf-8")
        (Q / "_active_b64.txt").write_text(
            base64.b64encode(a["content"].encode("utf-8")).decode("ascii"), encoding="ascii"
        )
        print(json.dumps({"index": args.index, "title": a["title"], "chars": len(a["content"])}, ensure_ascii=False))
        return 0
    # full arguments for agent (may be large)
    sys.stdout.write(json.dumps(a, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
