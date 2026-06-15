#!/usr/bin/env python3
"""Record commander human sign-off for tri-vertical deep pack research envelopes.

Patches child promotion signoff envelopes (ZF_MASK / BIZ_MASK / CS_MASK).
Does NOT authorize Track A ACTIVE swap or SEND unlock.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DEFAULT_TEMPLATE = ROOT / "reports/compression_deep_pack_tri_vertical_human_signoff_v1.template.json"
DEFAULT_OUT = ROOT / "reports/compression_deep_pack_tri_vertical_human_signoff_latest.json"
TRI_CHECKLIST = ROOT / "docs/final/artifacts/compression_deep_pack_tri_vertical_signoff_checklist_v1_latest.json"
CHILD_ENVELOPES = [
    ROOT / "docs/final/artifacts/compression_coding_deep_pack_promotion_signoff_envelope_v1_latest.json",
    ROOT / "docs/final/artifacts/compression_en_business_deep_pack_promotion_signoff_envelope_v1_latest.json",
    ROOT / "docs/final/artifacts/compression_ko_premium_cs_deep_pack_promotion_signoff_envelope_v1_latest.json",
]


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    doc = json.loads(path.read_text(encoding="utf-8-sig"))
    return doc if isinstance(doc, dict) else {}


def _tri_checklist_ready() -> tuple[bool, str]:
    if not TRI_CHECKLIST.is_file():
        return False, "missing_tri_checklist"
    doc = _read(TRI_CHECKLIST)
    if not doc.get("all_green"):
        return False, "tri_checklist_not_all_green"
    if doc.get("decision") != "READY_FOR_COMMANDER_SIGNOFF":
        return False, f"tri_decision={doc.get('decision')}"
    return True, "ok"


def _patch_child_envelopes(*, reviewer: str, note: str | None, approved_at: str) -> list[str]:
    patched: list[str] = []
    for path in CHILD_ENVELOPES:
        if not path.is_file():
            continue
        doc = _read(path)
        hs = dict(doc.get("human_signoff") or {})
        hs["reviewer"] = reviewer
        hs["approved_at_utc"] = approved_at
        if note:
            hs["note"] = note
        doc["human_signoff"] = hs
        doc["envelope_status"] = "commander_signed_research_envelope"
        path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        patched.append(str(path))
    return patched


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--template", type=Path, default=DEFAULT_TEMPLATE)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--reviewer", type=str, required=False, default="")
    ap.add_argument("--note", type=str, default="")
    ap.add_argument(
        "--acknowledge-research-envelope-only",
        action="store_true",
        help="Required: confirms signoff is research envelope only (no ACTIVE/SEND).",
    )
    ap.add_argument("--revoke", action="store_true")
    ap.add_argument("--skip-tri-checklist-gate", action="store_true")
    args = ap.parse_args()

    if args.revoke:
        doc = _read(args.out_json) or _read(args.template)
        doc = dict(doc)
        doc["approved"] = False
        doc["decision"] = "REVOKED"
        doc["research_envelope_only_acknowledged"] = False
        doc["recorded_at_utc"] = _utc_now()
    else:
        if not args.reviewer.strip():
            print("DENIED: --reviewer required", file=sys.stderr)
            return 2
        if not args.acknowledge_research_envelope_only:
            print("DENIED: --acknowledge-research-envelope-only required", file=sys.stderr)
            return 2
        if not args.skip_tri_checklist_gate:
            ok, reason = _tri_checklist_ready()
            if not ok:
                print(f"DENIED: tri checklist gate failed: {reason}", file=sys.stderr)
                return 2
        doc = _read(args.template)
        if not doc:
            raise SystemExit(f"missing template: {args.template}")
        approved_at = _utc_now()
        doc = dict(doc)
        doc["approved"] = True
        doc["decision"] = "APPROVED_RESEARCH_ENVELOPE_ONLY"
        doc["research_envelope_only_acknowledged"] = True
        doc["reviewer"] = args.reviewer.strip()
        doc["approved_at_utc"] = approved_at
        doc["recorded_at_utc"] = approved_at
        if args.note:
            doc["note"] = args.note
        patched = _patch_child_envelopes(reviewer=args.reviewer.strip(), note=args.note or None, approved_at=approved_at)
        doc["patched_child_envelopes"] = patched

    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.out_json}")
    print(f"approved={doc.get('approved')} decision={doc.get('decision')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
