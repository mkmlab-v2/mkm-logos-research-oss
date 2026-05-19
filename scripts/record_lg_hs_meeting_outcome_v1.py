#!/usr/bin/env python3
"""Record LG HS meeting outcome into lg_hs_meeting_followup_v1.json (internal SSOT)."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
FOLLOWUP = ROOT / "docs/final/artifacts/lg_hs_meeting_followup_v1.json"
VALID_OUTCOMES = frozenset({"pending", "pass", "follow_up", "hold", "reject"})


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--outcome-class",
        required=True,
        choices=sorted(VALID_OUTCOMES),
        help="LG feedback class (pending only for reset).",
    )
    ap.add_argument("--summary-one-line", default="", help="One-line summary for operators.")
    ap.add_argument("--lg-contact-role", default=None)
    ap.add_argument("--next-action", default=None)
    ap.add_argument("--evidence-path", action="append", default=[], help="Repeatable artifact path.")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if not FOLLOWUP.is_file():
        print(f"missing: {FOLLOWUP}", file=sys.stderr)
        return 2

    doc = json.loads(FOLLOWUP.read_text(encoding="utf-8"))
    tpl: dict[str, Any] = dict(doc.get("outcome_record_template") or {})
    tpl["received_at_utc"] = _utc_now() if args.outcome_class != "pending" else None
    tpl["outcome_class"] = args.outcome_class
    if args.summary_one_line:
        tpl["summary_one_line"] = args.summary_one_line.strip()
    if args.lg_contact_role:
        tpl["lg_contact_role"] = args.lg_contact_role.strip()
    if args.next_action:
        tpl["next_action"] = args.next_action.strip()
    if args.evidence_path:
        tpl["evidence_cited"] = [str(p).replace("\\", "/") for p in args.evidence_path]

    doc["outcome_record_template"] = tpl
    re = doc.get("result_expected") if isinstance(doc.get("result_expected"), dict) else {}
    if args.outcome_class != "pending":
        re["status"] = "received"
    doc["result_expected"] = re

    if args.dry_run:
        print(json.dumps({"would_write": str(FOLLOWUP), "outcome_record_template": tpl}, ensure_ascii=False, indent=2))
        return 0

    FOLLOWUP.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {FOLLOWUP}")
    if args.outcome_class in ("hold", "reject"):
        print("NOTE: run py scripts/check_lg_hs_fallback_two_week_pipeline_v1.py", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
