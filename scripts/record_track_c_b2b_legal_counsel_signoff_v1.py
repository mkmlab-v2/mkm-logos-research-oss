#!/usr/bin/env python3
"""Record counsel sign-off for Track C B2B pack (human gate — real counsel reference required)."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs/final/artifacts"
DEFAULT_OUT = ART / "track_c_b2b_legal_counsel_signoff_v1_latest.json"
HANDOFF = ART / "track_c_b2b_legal_counsel_handoff_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def build(
    *,
    counsel_reference: str,
    reviewer: str,
    notes: str,
    ready_for_external_send: bool,
) -> dict[str, Any]:
    ref = counsel_reference.strip()
    if not ref:
        raise ValueError("counsel_reference required (ticket/email/log id)")
    return {
        "schema": "track_c_b2b_legal_counsel_signoff_v1",
        "recorded_at_utc": _utc_now(),
        "counsel_reference": ref,
        "reviewer": reviewer.strip() or "external_counsel",
        "notes": (notes or "").strip() or None,
        "status": "COUNSEL_REVIEWED",
        "ready_for_external_send": ready_for_external_send,
        "boundary_ack": (
            "Counsel review recorded; external send still requires commander scope=external_send "
            "when both gates apply."
        ),
    }


def _apply_handoff(signoff: dict[str, Any]) -> None:
    if not HANDOFF.is_file():
        return
    handoff = json.loads(HANDOFF.read_text(encoding="utf-8"))
    handoff["legal_posture_status"] = "COUNSEL_REVIEWED"
    handoff["counsel_signoff"] = signoff
    handoff["counsel_signoff_required"] = False
    handoff["ready_for_external_send"] = bool(signoff.get("ready_for_external_send"))
    HANDOFF.write_text(json.dumps(handoff, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--counsel-reference", required=True)
    ap.add_argument("--reviewer", default="external_counsel")
    ap.add_argument("--notes", default="")
    ap.add_argument(
        "--ready-for-external-send",
        action="store_true",
        help="Only set true when counsel explicitly scoped external send GO",
    )
    ap.add_argument("--apply-scope", action="store_true", help="Patch handoff JSON")
    args = ap.parse_args()
    doc = build(
        counsel_reference=args.counsel_reference,
        reviewer=args.reviewer,
        notes=args.notes,
        ready_for_external_send=args.ready_for_external_send,
    )
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.apply_scope:
        _apply_handoff(doc)
    print(
        json.dumps(
            {
                "ok": True,
                "output": str(args.out_json),
                "status": doc["status"],
                "ready_for_external_send": doc["ready_for_external_send"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
