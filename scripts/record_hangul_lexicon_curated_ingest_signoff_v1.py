#!/usr/bin/env python3
"""Record commander sign-off for Hangul curated ingest pilot ([HYPO], no production SSOT swap)."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

OUT = ROOT / "reports/hangul_lexicon_curated_ingest_signoff_v1_latest.json"
PILOT = ROOT / "reports/lexicon_hangul_curated_pilot_v1_latest.json"
MANIFEST = ROOT / "docs/final/artifacts/hangul_lexicon_curated_lemma_manifest_v1.json"
OVERLAY = (
    ROOT
    / "reports/constitution/btrack_pilot/master_codebook_lexicon_v1_41658_hangul_curated_overlay.json"
)


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--commander-approve",
        action="store_true",
        help="Set approved=true (requires pilot both_pass).",
    )
    ap.add_argument("--reviewer", default="commander")
    ap.add_argument("--note", default="")
    args = ap.parse_args()

    if not PILOT.is_file():
        print("ABORT: missing pilot", PILOT)
        return 1
    pilot = json.loads(PILOT.read_text(encoding="utf-8"))
    both_pass = bool((pilot.get("double_gate") or {}).get("both_pass"))

    if args.commander_approve and not both_pass:
        print("ABORT: pilot double_gate.both_pass is false — cannot approve")
        return 1

    doc = {
        "schema": "hangul_lexicon_curated_ingest_signoff_v1",
        "recorded_at_utc": _utc(),
        "reviewer": str(args.reviewer),
        "approved": bool(args.commander_approve),
        "decision": "APPROVED" if args.commander_approve else "PENDING",
        "scope": {
            "research_only": True,
            "track_a_active_write": False,
            "production_ssot_swap": False,
            "live_trading": False,
            "curated_overlay_ingest_research": True,
            "note": "Authorizes B-track ingest pipeline steps only — not MULTILENS active or 41658_rows_latest overwrite.",
        },
        "evidence": {
            "pilot": str(PILOT.relative_to(ROOT)).replace("\\", "/"),
            "manifest": str(MANIFEST.relative_to(ROOT)).replace("\\", "/")
            if MANIFEST.is_file()
            else None,
            "overlay": str(OVERLAY.relative_to(ROOT)).replace("\\", "/")
            if OVERLAY.is_file()
            else None,
            "double_gate": pilot.get("double_gate"),
        },
        "commander_note": str(args.note).strip() or None,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"wrote": str(OUT), "approved": doc["approved"], "decision": doc["decision"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
