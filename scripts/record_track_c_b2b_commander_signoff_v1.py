#!/usr/bin/env python3
"""Record commander sign-off for Track C B2B pack (human gate — does not replace counsel)."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs/final/artifacts"
DEFAULT_OUT = ART / "track_c_b2b_commander_signoff_v1_latest.json"
HANDOFF = ART / "track_c_b2b_legal_counsel_handoff_v1_latest.json"

VALID_SCOPES = frozenset(
    {
        "internal_rehearsal_complete",
        "counsel_submission",
        "external_send",
    }
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def build(*, reference: str, scope: str, notes: str) -> dict[str, Any]:
    ref = reference.strip()
    if not ref:
        raise ValueError("reference required (chat id / ticket / date stamp)")
    if scope not in VALID_SCOPES:
        raise ValueError(f"scope must be one of {sorted(VALID_SCOPES)}")
    return {
        "schema": "track_c_b2b_commander_signoff_v1",
        "recorded_at_utc": _utc_now(),
        "commander_reference": ref,
        "scope": scope,
        "notes": (notes or "").strip() or None,
        "status": "COMMANDER_SIGNED",
        "ready_for_external_send": scope == "external_send",
        "boundary_ack": (
            "Commander sign-off does not replace counsel review unless scope=external_send "
            "and counsel signoff also records ready_for_external_send."
        ),
    }


def _apply_handoff(signoff: dict[str, Any]) -> None:
    if not HANDOFF.is_file():
        return
    handoff = json.loads(HANDOFF.read_text(encoding="utf-8"))
    handoff["commander_signoff"] = signoff
    handoff["commander_signoff_recorded"] = True
    if signoff.get("scope") == "counsel_submission":
        handoff["legal_posture_status"] = "COMMANDER_PREFLIGHT_OK_PENDING_COUNSEL"
    HANDOFF.write_text(json.dumps(handoff, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--reference", required=True, help="Commander approval id (e.g. chat date)")
    ap.add_argument(
        "--scope",
        default="counsel_submission",
        choices=sorted(VALID_SCOPES),
        help="internal_rehearsal_complete | counsel_submission | external_send",
    )
    ap.add_argument("--notes", default="")
    ap.add_argument("--apply-scope", action="store_true", help="Patch handoff JSON")
    args = ap.parse_args()
    doc = build(reference=args.reference, scope=args.scope, notes=args.notes)
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.apply_scope:
        _apply_handoff(doc)
    print(
        json.dumps(
            {
                "ok": True,
                "output": str(args.out_json),
                "scope": doc["scope"],
                "ready_for_external_send": doc["ready_for_external_send"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
