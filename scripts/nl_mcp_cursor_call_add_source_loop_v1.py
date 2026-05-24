#!/usr/bin/env python3
"""Load nl_mcp_payload index and print add_source args as one JSON line (for agent CallMcpTool)."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PILOT = Path(__file__).resolve().parents[1] / "reports" / "constitution" / "btrack_pilot"
NOTEBOOK_ID = "mkm-core-intelligence-fact-foc"
DEFAULT_SESSION = "00e4c8db"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("index", type=int)
    ap.add_argument("--session-id", default=DEFAULT_SESSION)
    ap.add_argument("--out", default="", help="write args JSON to file instead of stdout")
    args = ap.parse_args()
    data = json.loads((PILOT / f"nl_mcp_payload_{args.index}.json").read_text(encoding="utf-8"))
    out = {
        "type": "text",
        "title": data["title"],
        "content": data["content"],
        "notebook_id": NOTEBOOK_ID,
    }
    if args.session_id:
        out["session_id"] = args.session_id
    text = json.dumps(out, ensure_ascii=False)
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
    else:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
