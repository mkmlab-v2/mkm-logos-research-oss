#!/usr/bin/env python3
"""Mark evolution radar candidate approved after commander sign-off (no auto_apply)."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RADAR = ROOT / "reports/mkm_evolution_radar_daily_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--radar-json", type=Path, default=DEFAULT_RADAR)
    ap.add_argument("--id", required=True, help="candidate id e.g. exa_mcp_permissions_review")
    ap.add_argument("--approved-by", default="commander_chat")
    ap.add_argument("--implementation-note", default="")
    args = ap.parse_args()

    if not args.radar_json.is_file():
        print(json.dumps({"ok": False, "error": "missing radar json"}))
        return 2

    doc = json.loads(args.radar_json.read_text(encoding="utf-8-sig"))
    found = False
    for c in doc.get("candidates") or []:
        if str(c.get("id")) == args.id:
            c["approval_status"] = "approved"
            c["approved_at_utc"] = _utc_now()
            c["approved_by"] = args.approved_by
            if args.implementation_note:
                c["implementation_note"] = args.implementation_note
            found = True
            break

    if not found:
        print(json.dumps({"ok": False, "error": f"candidate not found: {args.id}"}))
        return 1

    doc["generated_at_utc"] = _utc_now()
    args.radar_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "id": args.id, "approval_status": "approved"}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
