#!/usr/bin/env python3
"""Print add_source JSON args for one nl_mcp_payload index (stdout, one line)."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PILOT = Path(__file__).resolve().parents[1] / "reports" / "constitution" / "btrack_pilot"
NOTEBOOK_ID = "mkm-core-intelligence-fact-foc"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("index", type=int)
    ap.add_argument("--session-id", default="00e4c8db")
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
    sys.stdout.write(json.dumps(out, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
