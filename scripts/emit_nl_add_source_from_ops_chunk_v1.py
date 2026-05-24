#!/usr/bin/env python3
"""Emit one-line JSON args for NotebookLM add_source from ops MCP chunk .txt files."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHUNKS = ROOT / "reports" / "notebooklm_ops_mcp_chunks"
DEFAULT_URL = "https://notebooklm.google.com/notebook/9bc26140-70c4-47d0-b9ea-bd3a394916a9"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("chunk_file", help="filename under notebooklm_ops_mcp_chunks")
    ap.add_argument("--title", required=True)
    ap.add_argument("--notebook-url", default=DEFAULT_URL)
    ap.add_argument("--out", default="", help="write JSON args to file instead of stdout")
    args = ap.parse_args()
    path = CHUNKS / args.chunk_file
    if not path.is_file():
        print(json.dumps({"error": f"missing {path}"}), file=sys.stderr)
        return 1
    out = {
        "type": "text",
        "title": args.title,
        "content": path.read_text(encoding="utf-8", errors="replace"),
        "notebook_url": args.notebook_url,
    }
    text = json.dumps(out, ensure_ascii=False)
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
        print(json.dumps({"out": args.out, "bytes": len(text), "title": args.title}))
    else:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
