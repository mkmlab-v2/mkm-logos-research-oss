#!/usr/bin/env python3
"""Record human sign-off for R-IBL briefing evolution apply (HITL)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.research_evolution_human_signoff_v1 import (  # noqa: E402
    build_signoff_record,
    proposal_id,
    validate_signoff,
    write_signoff,
)

DEFAULT_EVOLUTION = ROOT / "reports" / "commander_briefing_evolution_latest.json"
DEFAULT_OUT = ROOT / "reports" / "research_evolution_human_signoff_latest.json"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--decision", choices=("APPROVED", "REJECTED"), required=True)
    ap.add_argument("--actor", default="commander")
    ap.add_argument("--evolution-json", type=Path, default=DEFAULT_EVOLUTION)
    ap.add_argument(
        "--approve-all-proposals",
        action="store_true",
        help="When APPROVED, include all proposal ids from evolution JSON",
    )
    ap.add_argument("--proposal-id", action="append", default=[], dest="proposal_ids")
    ap.add_argument("--note-ko", default="")
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    approved: list[str] = list(args.proposal_ids)
    evo_path = str(args.evolution_json)
    if args.decision == "APPROVED" and args.approve_all_proposals and args.evolution_json.is_file():
        evo = json.loads(args.evolution_json.read_text(encoding="utf-8-sig"))
        for p in evo.get("proposals") or []:
            if isinstance(p, dict):
                approved.append(proposal_id(p))

    doc = build_signoff_record(
        decision=args.decision,
        actor=args.actor,
        approved_proposal_ids=sorted(set(approved)),
        evolution_source_path=evo_path,
        note_ko=args.note_ko,
    )
    out = write_signoff(doc, args.out_json)
    errs = validate_signoff(out) if args.decision == "APPROVED" else []
    if args.decision == "REJECTED":
        print(f"WROTE: {out} decision=REJECTED")
        return 0
    if errs:
        print(f"WARN: signoff validation: {errs}", file=sys.stderr)
    print(f"WROTE: {out} approved_ids={len(doc.get('approved_proposal_ids') or [])}")
    return 0 if not errs else 1


if __name__ == "__main__":
    raise SystemExit(main())
