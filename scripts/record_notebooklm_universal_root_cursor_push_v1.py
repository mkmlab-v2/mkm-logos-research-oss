#!/usr/bin/env python3
"""Record NotebookLM push results from Cursor-injected MCP add_source calls."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "reports/notebooklm_universal_root_research_pack_push_v1_latest.json"
DEFAULT_MANIFEST = ROOT / "reports/notebooklm_universal_root_research_pack_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--results-json", type=Path, required=True, help="JSON list of push row dicts")
    ap.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    rows = json.loads(args.results_json.read_text(encoding="utf-8-sig"))
    if not isinstance(rows, list):
        raise SystemExit("results-json must be a JSON array")

    ok = sum(1 for r in rows if r.get("success"))
    fail = sum(1 for r in rows if not r.get("success"))
    doc = {
        "schema": "notebooklm_universal_root_research_pack_push_v1",
        "generated_at_utc": _utc(),
        "notebook_mcp_id": "14-universal-lexicon-dr",
        "manifest": str(args.manifest.relative_to(ROOT)).replace("\\", "/"),
        "method": "cursor_injected_notebooklm_mcp",
        "dry_run": False,
        "ok_count": ok,
        "fail_count": fail,
        "all_ok": fail == 0 and ok > 0,
        "rows": rows,
        "reproduce": "Cursor MCP add_source on 14-universal-lexicon-dr; record via scripts/record_notebooklm_universal_root_cursor_push_v1.py",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"out": str(args.out), "all_ok": doc["all_ok"], "ok_count": ok}, ensure_ascii=False))
    return 0 if doc["all_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
