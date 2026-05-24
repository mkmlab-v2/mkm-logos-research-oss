#!/usr/bin/env python3
"""COMP-ATOM-02: one-page pointer vs compression path feasibility (research)."""
from __future__ import annotations

import json
import statistics
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PILOT = ROOT / "reports" / "constitution" / "btrack_pilot"


def main() -> int:
    expanded = json.loads((PILOT / "comp_atom02_expanded_lexicon_codebook_poc_v1.json").read_text(encoding="utf-8"))
    vocab_cov = json.loads((PILOT / "comp_atom02_bench_genesis_vocab_coverage_v1.json").read_text(encoding="utf-8"))
    lex_mk = json.loads((PILOT / "comp_atom02_lexicon_must_keep_analysis_v1.json").read_text(encoding="utf-8"))
    ab = json.loads((PILOT / "comp_atom01_ab_summary_v1.json").read_text(encoding="utf-8"))

    per = expanded.get("per_case") or []
    ratios = []
    for row in per:
        tc = int(row.get("token_count") or 0)
        unr = int(row.get("unresolved_count") or 0)
        if tc:
            ratios.append((tc - unr) / tc)
    best = max(per, key=lambda r: (r.get("token_count", 0) - r.get("unresolved_count", 0)) / max(r.get("token_count", 1), 1))

    out = {
        "schema": "comp_atom02_pointer_feasibility_summary_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "research_only": true if False else True,
        "track_a_frozen": {
            "global_token_saving_rate": 0.475,
            "apply_gematria_4d_bridge_policy": False,
            "mechanism": "zone_router + master_codebook_lexicon_v1 must_keep (partial hits per sentence)",
        },
        "genesis_pointer_closed_dict": {
            "bench_unique_tokens": vocab_cov.get("bench_unique_tokens"),
            "bench_in_41k_lexicon": vocab_cov.get("bench_in_41k_lexicon"),
            "expanded_codebook_terms": expanded.get("term_count"),
            "full_sentence_ok_40": expanded.get("per_case_all_tokens_in_vocab"),
            "mean_token_vocab_coverage_ratio": round(statistics.mean(ratios), 4) if ratios else 0.0,
            "median_token_vocab_coverage_ratio": round(statistics.median(ratios), 4) if ratios else 0.0,
            "best_case_id": best.get("id"),
            "best_case_coverage_ratio": round(
                (best.get("token_count", 0) - best.get("unresolved_count", 0)) / max(best.get("token_count", 1), 1),
                4,
            ),
        },
        "bridge_ab_delta": ab.get("deltas_bridge_on_minus_control"),
        "lexicon_on_ablation": lex_mk.get("compression_ablation", {}).get("delta_on_minus_off"),
        "verdict": (
            "Genesis pointer_primary on V2 bench is infeasible without open-vocabulary or near-full English lexicon; "
            "Track A 47.5% does not require per-sentence pointer_candidate_ok."
        ),
    }
    out["research_only"] = True
    path = PILOT / "comp_atom02_pointer_feasibility_summary_v1.json"
    path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"wrote": path.name, "median_cov": out["genesis_pointer_closed_dict"]["median_token_vocab_coverage_ratio"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
