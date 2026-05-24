#!/usr/bin/env python3
"""COMP-ANCHOR-02: re-run pointer PoC chain + refresh feasibility (strict + relaxed hit metrics)."""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PILOT = ROOT / "reports" / "constitution" / "btrack_pilot"


def _run(script: str) -> int:
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / script)],
        cwd=str(ROOT),
        check=False,
    )
    return int(proc.returncode)


def _partial_hit_counts(per_case: list[dict]) -> dict[str, int]:
    partial = 0
    any_resolved = 0
    for row in per_case:
        tc = int(row.get("token_count") or 0)
        unr = int(row.get("unresolved_count") or 0)
        if tc <= 0:
            continue
        if unr < tc:
            any_resolved += 1
        if unr > 0 and unr < tc:
            partial += 1
        elif unr == 0:
            partial += 1
            any_resolved += 1
    return {"cases_any_token_resolved": any_resolved, "cases_partial_coverage": partial}


def main() -> int:
    steps = [
        "comp_atom02_expanded_lexicon_codebook_poc_v1.py",
        "comp_atom02_genesis_pointer_sentence_poc_v1.py",
        "comp_atom02_pointer_feasibility_summary_v1.py",
    ]
    exits: dict[str, int] = {}
    for s in steps:
        exits[s] = _run(s)

    expanded = json.loads((PILOT / "comp_atom02_expanded_lexicon_codebook_poc_v1.json").read_text(encoding="utf-8"))
    sentence = json.loads((PILOT / "comp_atom02_genesis_pointer_sentence_poc_v1.json").read_text(encoding="utf-8"))
    feas_path = PILOT / "comp_atom02_pointer_feasibility_summary_v1.json"
    feas = json.loads(feas_path.read_text(encoding="utf-8"))

    partial = _partial_hit_counts(expanded.get("per_case") or [])
    strict40 = int(expanded.get("per_case_all_tokens_in_vocab") or 0)
    feas["t2_refresh"] = {
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "refresh_script": "scripts/comp_atom02_pointer_hit_refresh_v1.py",
        "step_exits": exits,
        "strict_full_sentence_ok_40": strict40,
        "pointer_candidate_ok_no_snap": (sentence.get("summary") or {}).get("pointer_candidate_ok_no_snap"),
        "pointer_candidate_ok_with_snap": (sentence.get("summary") or {}).get("pointer_candidate_ok_with_snap"),
        "pointer_unicode_strip_punct_ok": expanded.get("pointer_unicode_strip_punct_ok"),
        "pointer_whitespace_router_ok": expanded.get("pointer_whitespace_router_ok"),
        **partial,
        "goal_strict_gt_0_40_met": strict40 > 0,
        "note": (
            "Strict genesis closed-dict full-sentence OK remains 0/40 on V2 bench; "
            "relaxed metrics count partial token coverage (bench∩41k expanded codebook)."
        ),
    }
    feas_path.write_text(json.dumps(feas, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    out = {
        "wrote": feas_path.name,
        "strict_full_sentence_ok_40": strict40,
        **partial,
        "exits": exits,
    }
    print(json.dumps(out, ensure_ascii=False))
    return 0 if all(v == 0 for v in exits.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
