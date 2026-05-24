#!/usr/bin/env python3
"""Print one-line JSON args for NotebookLM MCP add_source from ops pack file."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / "reports" / "notebooklm_ops_command_sync_pack_v1"
DEFAULT_URL = "https://notebooklm.google.com/notebook/9bc26140-70c4-47d0-b9ea-bd3a394916a9"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("filename", help="basename under ops pack dir")
    ap.add_argument("--notebook-url", default=DEFAULT_URL)
    args = ap.parse_args()
    path = PACK / args.filename
    if not path.is_file():
        print(json.dumps({"error": f"missing {path}"}), file=sys.stderr)
        return 1
    out = {
        "type": "text",
        "title": args.filename,
        "content": path.read_text(encoding="utf-8", errors="replace"),
        "notebook_url": args.notebook_url,
    }
    sys.stdout.write(json.dumps(out, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
