#!/usr/bin/env python3
"""Record external counsel sign-off (human gate — do not run without real approval)."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "docs/final/artifacts/mkm_inter_agent_legal_counsel_signoff_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def build(*, counsel_reference: str, approver: str) -> dict[str, Any]:
    ref = counsel_reference.strip()
    if not ref:
        raise ValueError("counsel_reference required (ticket/email/log id)")
    return {
        "schema": "mkm_inter_agent_legal_counsel_signoff_v1",
        "generated_at_utc": _utc_now(),
        "classification": "INTERNAL_ONLY",
        "counsel_signoff": True,
        "legal_review_status": "COUNSEL_SIGNED",
        "signed_at_utc": _utc_now(),
        "counsel_reference": ref,
        "approver_label": approver.strip() or "external_counsel",
        "rq_019_checklist_item_7_met": True,
        "boundary_ack": (
            "Counsel sign-off recorded. Commander must still agree RQ-019 CLOSED and promotion path."
        ),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--counsel-reference", required=True)
    ap.add_argument("--approver", default="external_counsel")
    args = ap.parse_args()
    doc = build(counsel_reference=args.counsel_reference, approver=args.approver)
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "output": str(args.out_json)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
