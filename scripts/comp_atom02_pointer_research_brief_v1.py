#!/usr/bin/env python3
"""Emit one-page pointer research brief JSON from feasibility + hit refresh (B-track)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PILOT = ROOT / "reports" / "constitution" / "btrack_pilot"
FEAS = PILOT / "comp_atom02_pointer_feasibility_summary_v1.json"
OUT = PILOT / "comp_atom02_pointer_research_brief_v1.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> int:
    feas = json.loads(FEAS.read_text(encoding="utf-8")) if FEAS.is_file() else {}
    t2 = feas.get("t2_refresh") or {}
    brief = {
        "schema": "comp_atom02_pointer_research_brief_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "track_a_frozen": feas.get("track_a_frozen"),
        "headline": feas.get("verdict"),
        "strict_metrics": {
            "full_sentence_ok_40": t2.get("strict_full_sentence_ok_40"),
            "pointer_candidate_ok_no_snap": t2.get("pointer_candidate_ok_no_snap"),
            "cases_any_token_resolved": t2.get("cases_any_token_resolved"),
            "cases_partial_coverage": t2.get("cases_partial_coverage"),
        },
        "closed_dict": feas.get("genesis_pointer_closed_dict"),
        "do_not_claim": [
            "per-sentence genesis pointer_primary on V2 bench",
            "71% or 55-70% saving without re-bench",
            "bridge ON without human approval and AB proof",
        ],
        "track_a_mechanism_ok": (
            "zone_router + master_codebook_lexicon_v1 must_keep; "
            "47.5% GO does not require pointer_candidate_ok per sentence."
        ),
        "sources": [
            "comp_atom02_pointer_feasibility_summary_v1.json",
            "comp_atom02_genesis_pointer_sentence_poc_v1.json",
            "comp_atom02_expanded_lexicon_codebook_poc_v1.json",
        ],
    }
    OUT.write_text(json.dumps(brief, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"wrote": OUT.name}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
