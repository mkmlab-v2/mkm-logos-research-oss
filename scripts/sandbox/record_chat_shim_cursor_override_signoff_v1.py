#!/usr/bin/env python3
"""Record human signoff for Cursor BYOK override dogfood (B-track; local file)."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EXAMPLE = ROOT / "data/btrack/chat_shim_cursor_override_signoff_v1.example.json"
DEFAULT_OUT = ROOT / "data/btrack/chat_shim_cursor_override_signoff_v1.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out-json", default=str(DEFAULT_OUT))
    ap.add_argument("--reviewer", default="commander")
    ap.add_argument("--note", default="")
    ap.add_argument("--approve", action="store_true", help="Set cursor_override_dogfood_approved=true")
    ap.add_argument("--human-session-done", action="store_true")
    args = ap.parse_args()

    out = Path(args.out_json)
    if not out.is_absolute():
        out = ROOT / out

    if out.is_file():
        doc = json.loads(out.read_text(encoding="utf-8-sig"))
    elif EXAMPLE.is_file():
        doc = json.loads(EXAMPLE.read_text(encoding="utf-8-sig"))
    else:
        raise SystemExit(f"missing example: {EXAMPLE}")

    doc["approved_by"] = str(args.reviewer).strip() or "commander"
    doc["approved_at_utc"] = _utc()
    if args.note:
        doc["note"] = str(args.note).strip()
    if args.approve:
        doc["cursor_override_dogfood_approved"] = True
    if args.human_session_done:
        attest = doc.setdefault("attestations", {})
        if isinstance(attest, dict):
            attest["human_cursor_session_completed"] = True

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(out))
    print(f"cursor_override_dogfood_approved={doc.get('cursor_override_dogfood_approved')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
