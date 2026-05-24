#!/usr/bin/env python3
"""Print one-line JSON per index for agent CallMcpTool add_source (args from agent-tools/mcp_call_{i}.json)."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

AGENT_TOOLS = Path(r"C:\Users\PRO\.cursor\projects\c-workspace\agent-tools")
OUT = Path(__file__).resolve().parents[1] / "reports" / "constitution" / "btrack_pilot"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--indices", default="0,1,2,3,4,5,6")
    ap.add_argument("--emit-results-template", action="store_true")
    args = ap.parse_args()
    indices = [int(x.strip()) for x in args.indices.split(",") if x.strip()]
    rows = []
    for i in indices:
        p = AGENT_TOOLS / f"mcp_call_{i}.json"
        a = json.loads(p.read_text(encoding="utf-8"))
        row = {"index": i, "title": a["title"], "mcp_args": a}
        rows.append(row)
        if args.emit_results_template:
            (OUT / f"nl_mcp_add_source_out_{i}.json").write_text(
                json.dumps(
                    {
                        "index": i,
                        "title": a["title"],
                        "success": None,
                        "sourceCountBefore": None,
                        "sourceCountAfter": None,
                        "error": "pending CallMcpTool",
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
        else:
            print(json.dumps(row, ensure_ascii=False), flush=True)
    if args.emit_results_template:
        (OUT / "nl_mcp_add_source_batch_pending.json").write_text(
            json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
