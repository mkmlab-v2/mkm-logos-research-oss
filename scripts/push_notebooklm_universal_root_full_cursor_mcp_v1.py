#!/usr/bin/env python3
"""Emit add_source payloads for Cursor-injected MCP full pack upload [HYPO].

Stdio notebooklm-mcp fails when Cursor MCP holds chrome_profile. This script
writes one JSON line per pack file to stdout for agent CallMcpTool, or records
results when --results-json is passed after manual/agent MCP push.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARGS_DIR = ROOT / "reports/nl_mcp_payload/universal_root_research_v1"
DEFAULT_OUT = ROOT / "reports/notebooklm_universal_root_research_pack_push_v1_latest.json"
NOTEBOOK_MCP_ID = "14-universal-lexicon-dr"


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_payloads() -> list[dict]:
    rows: list[dict] = []
    for path in sorted(ARGS_DIR.glob("*.add_source.json")):
        args = json.loads(path.read_text(encoding="utf-8-sig"))
        args["notebook_id"] = NOTEBOOK_MCP_ID
        rows.append(
            {
                "args_file": str(path.relative_to(ROOT)).replace("\\", "/"),
                "title": args.get("title"),
                "chars": len(str(args.get("content") or "")),
                "add_source_args": args,
            }
        )
    return rows


def record_results(results_path: Path, *, out: Path) -> int:
    rows = json.loads(results_path.read_text(encoding="utf-8-sig"))
    if not isinstance(rows, list):
        print(json.dumps({"ok": False, "error": "results must be a JSON array"}), file=sys.stderr)
        return 2
    ok = sum(1 for r in rows if r.get("success"))
    fail = sum(1 for r in rows if not r.get("success"))
    doc = {
        "schema": "notebooklm_universal_root_research_pack_push_v1",
        "generated_at_utc": _utc(),
        "notebook_mcp_id": NOTEBOOK_MCP_ID,
        "method": "cursor_injected_mcp_full_pack",
        "full_content": True,
        "ok_count": ok,
        "fail_count": fail,
        "all_ok": fail == 0 and ok > 0,
        "rows": rows,
        "reproduce": "Cursor MCP add_source x7 from reports/nl_mcp_payload/universal_root_research_v1/",
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": doc["all_ok"], "ok_count": ok, "out": str(out)}, ensure_ascii=False))
    return 0 if doc["all_ok"] else 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--list", action="store_true", help="Print payload index JSON")
    ap.add_argument("--emit-index", type=int, default=None, help="Print one add_source args JSON line")
    ap.add_argument("--record-results", type=Path, default=None)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    if args.record_results:
        return record_results(args.record_results, out=args.out)

    payloads = load_payloads()
    if args.emit_index is not None:
        if args.emit_index < 0 or args.emit_index >= len(payloads):
            return 2
        print(json.dumps(payloads[args.emit_index]["add_source_args"], ensure_ascii=False))
        return 0

    if args.list:
        print(
            json.dumps(
                {
                    "count": len(payloads),
                    "notebook_mcp_id": NOTEBOOK_MCP_ID,
                    "payloads": [
                        {"index": i, "title": p["title"], "chars": p["chars"], "args_file": p["args_file"]}
                        for i, p in enumerate(payloads)
                    ],
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0

    print(json.dumps({"count": len(payloads), "hint": "use --list or --emit-index N"}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
