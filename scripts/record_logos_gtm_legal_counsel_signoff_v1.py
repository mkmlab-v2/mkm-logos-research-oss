#!/usr/bin/env python3
"""Record Logos GTM legal counsel sign-off (human gate — real counsel reference required)."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SIGNOFF = ROOT / "docs/final/artifacts/logos_track_l_external_send_signoff_v1_latest.json"
BUNDLE = ROOT / "reports/logos_gtm_counsel_handoff_bundle_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--counsel-reference", required=True)
    ap.add_argument("--reviewer-id", default="external_counsel")
    ap.add_argument("--notes", default="")
    ap.add_argument(
        "--ready-for-external-send",
        action="store_true",
        help="Only when counsel explicitly scopes external send GO",
    )
    ap.add_argument("--apply-signoff", action="store_true")
    args = ap.parse_args()

    ref = args.counsel_reference.strip()
    if not ref:
        print("FAIL: counsel_reference required", file=sys.stderr)
        return 1

    if not SIGNOFF.is_file():
        print(f"FAIL: missing {SIGNOFF}", file=sys.stderr)
        return 1

    doc = json.loads(SIGNOFF.read_text(encoding="utf-8-sig"))
    doc["generated_at_utc"] = _utc()
    doc["legal_counsel_signoff"] = {
        "present": True,
        "reviewer_id": args.reviewer_id.strip(),
        "signoff_utc": _utc(),
        "counsel_reference": ref,
        "notes": args.notes.strip(),
    }
    if args.ready_for_external_send:
        doc["ready_for_external_send"] = True
    else:
        doc["ready_for_external_send"] = False

    if args.apply_signoff:
        SIGNOFF.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if BUNDLE.is_file() and args.apply_signoff:
        bundle = json.loads(BUNDLE.read_text(encoding="utf-8-sig"))
        bundle["counsel_signoff_present"] = True
        bundle["generated_at_utc"] = _utc()
        BUNDLE.write_text(json.dumps(bundle, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(
        json.dumps(
            {
                "ok": True,
                "counsel_reference": ref,
                "ready_for_external_send": doc["ready_for_external_send"],
                "send_gate": "HOLD" if not doc["ready_for_external_send"] else "REVIEW",
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
