#!/usr/bin/env python3
"""Feasibility: scoped other:: alignment vs full 117-row merge (Golden 40 six-case focus)."""

from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.core.master_codebook_lexicon_v1_bridge import unicode_word_tokens  # noqa: E402

PILOT = ROOT / "reports" / "constitution" / "btrack_pilot"
DIFF = PILOT / "master_codebook_41775_vs_41658_atom_diff_v1.json"
AB = PILOT / "master_codebook_golden40_lexicon_ab_v1.json"
INPUT_V2 = ROOT / "docs" / "final" / "artifacts" / "MULTILENS_PERFORMANCE_EVAL_INPUT_V2.json"
OUT = PILOT / "master_codebook_other_align_feasibility_v1.json"

_META_NOISE_HINTS = frozenset(
    {
        "btrack",
        "jsonl",
        "json",
        "ci",
        "checklist",
        "bundle",
        "hypo",
        "eval",
        "pipeline",
        "artifact",
        "docs",
        "draft",
        "gatestatus",
        "executionpolicy",
    }
)


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _atom_form(atom_id: str) -> str:
    if "::" in atom_id:
        return atom_id.split("::", 1)[1].lower()
    return atom_id.lower()


def _case_text(case: dict[str, Any]) -> str:
    for key in ("raw_text", "text", "source_text", "input_text"):
        v = case.get(key)
        if isinstance(v, str) and v.strip():
            return v
    return ""


def main() -> int:
    for p in (DIFF, AB, INPUT_V2):
        if not p.is_file():
            print(f"ERROR: missing {p}", file=sys.stderr)
            return 2

    diff = json.loads(DIFF.read_text(encoding="utf-8"))
    ab = json.loads(AB.read_text(encoding="utf-8"))
    src = json.loads(INPUT_V2.read_text(encoding="utf-8"))
    cases = list(src.get("compression_cases") or [])
    by_id = {str(c.get("id")): c for c in cases if c.get("id")}

    only775 = list(diff.get("only_in_41775") or [])
    only658 = list(diff.get("only_in_41658") or [])
    forms775 = {_atom_form(x): x for x in only775}
    forms658 = {_atom_form(x) for x in only658}

    delta_cases = [r["id"] for r in (ab.get("per_case_deltas_top10") or []) if r.get("id")]
    if not delta_cases:
        delta_cases = [
            r["id"]
            for r in (ab.get("per_case_deltas_top10") or [])
        ]

    all_tokens: set[str] = set()
    for c in cases:
        all_tokens |= unicode_word_tokens(_case_text(c))

    bench_hits_775 = sorted(f for f in forms775 if f in all_tokens)
    bench_hits_658_only = sorted(f for f in forms658 if f in all_tokens)
    meta_noise_775 = [f for f in bench_hits_775 if f in _META_NOISE_HINTS]
    non_noise_bench_775 = [f for f in bench_hits_775 if f not in _META_NOISE_HINTS]

    per_delta_case: list[dict[str, Any]] = []
    for cid in delta_cases:
        c = by_id.get(cid)
        if not c:
            continue
        toks = unicode_word_tokens(_case_text(c))
        hit775 = sorted(f for f in forms775 if f in toks)
        hit658 = sorted(f for f in forms658 if f in toks)
        per_delta_case.append(
            {
                "case_id": cid,
                "only_in_41775_forms_in_case_text": hit775,
                "only_in_41658_forms_in_case_text": hit658,
                "meta_noise_hits_41775": [f for f in hit775 if f in _META_NOISE_HINTS],
            }
        )

    pilot_3a_path = PILOT / "master_codebook_3a_overlay_pilot_v1.json"
    pilot_3a: dict[str, Any] | None = None
    if pilot_3a_path.is_file():
        pilot_3a = json.loads(pilot_3a_path.read_text(encoding="utf-8"))

    doc: dict[str, Any] = {
        "schema": "master_codebook_other_align_feasibility_v1",
        "verified_at_utc": _utc(),
        "inputs": {
            "diff": str(DIFF.relative_to(ROOT)).replace("\\", "/"),
            "golden40_ab": str(AB.relative_to(ROOT)).replace("\\", "/"),
        },
        "counts": {
            "only_in_41775": len(only775),
            "only_in_41658": len(only658),
            "net_row_gap": diff.get("net_row_delta"),
            "bench_text_hits_only_in_41775": len(bench_hits_775),
            "bench_text_hits_only_in_41658": len(bench_hits_658_only),
            "meta_noise_among_bench_hits_41775": len(meta_noise_775),
        },
        "golden40_ab_aggregate": {
            "metrics_41658": ab.get("metrics_41658_explicit_path"),
            "metrics_41775": ab.get("metrics_41775_archived_explicit_path"),
            "delta_41775_minus_41658": ab.get("delta_41775_minus_41658"),
        },
        "per_delta_case": per_delta_case,
        "bench_relevant_only_in_41775_sample": non_noise_bench_775[:40],
        "options": [
            {
                "id": "1_headline_refreeze_41658",
                "status": "ready",
                "note": "A/B proved KPI split; align ACTIVE + PROFILE_BENCH_SSOT to 41658 path.",
            },
            {
                "id": "3a_six_case_lexicon_union",
                "status": "pilot_done" if pilot_3a else "feasible_scoped",
                "note": (
                    f"Union only_in_41775 forms hitting 6 delta cases ({len(delta_cases)} ids) "
                    + (
                        f"pilot verdict={(pilot_3a or {}).get('verdict', '?')}."
                        if pilot_3a
                        else "re-run golden40_ab — jaccard recovery unverified until run."
                    )
                ),
                "pilot_artifact": str(pilot_3a_path.relative_to(ROOT)).replace("\\", "/")
                if pilot_3a
                else None,
            },
            {
                "id": "3b_full_other_remerge_152",
                "status": "high_risk",
                "note": (
                    f"Re-merge all {len(only775)} only_in_41775 rows — likely reintroduces pipeline/meta tokens; "
                    f"{len(meta_noise_775)} meta-noise forms already hit bench corpus text."
                ),
            },
            {
                "id": "3c_reexport_atoms_other_policy",
                "status": "confirm_needed",
                "note": "Re-run export_master_codebook from atoms with frozen other:: policy — engineering scope not sized in this artifact.",
            },
        ],
        "recommendation_conservative": (
            "track_3a_pilot_done; hold_3b; production_pointer_41658; MS_frozen_089_footnote_only"
            if pilot_3a
            else "parallel_track_1_now; track_3a_pilot_before_3b; hold_3b"
        ),
        "jaccard_0_89_recovery_guarantee": False,
        "pilot_3a_summary": pilot_3a,
    }

    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"OK: {OUT}")
    print(f"bench_hits_only_in_41775={len(bench_hits_775)} meta_noise={len(meta_noise_775)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
