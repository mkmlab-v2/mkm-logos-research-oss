#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _resolve(path_str: str) -> Path:
    p = Path(path_str)
    return p if p.is_absolute() else ROOT / p


def _read_json(path: Path) -> dict[str, Any]:
    obj = json.loads(path.read_text(encoding="utf-8"))
    return obj if isinstance(obj, dict) else {}


def _set_from_ruleset(doc: dict[str, Any]) -> set[str]:
    s: set[str] = set()
    clusters = doc.get("universal_precursor_clusters")
    if not isinstance(clusters, list):
        return s
    for c in clusters:
        if not isinstance(c, dict):
            continue
        ids = c.get("sample_verse_ids")
        if isinstance(ids, list):
            for x in ids:
                v = str(x).strip()
                if v:
                    s.add(v)
    return s


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 1.0
    inter = len(a & b)
    uni = len(a | b)
    return inter / max(1, uni)


def main() -> int:
    ap = argparse.ArgumentParser(description="Evaluate sufficiency of universal precursor insight pipeline.")
    ap.add_argument("--r5000", default="docs/final/artifacts/universal_precursor_ruleset_top5000_v1_latest.json")
    ap.add_argument("--r6866", default="docs/final/artifacts/universal_precursor_ruleset_top6866_v1_latest.json")
    ap.add_argument("--r9000", default="docs/final/artifacts/universal_precursor_ruleset_top9000_v1_latest.json")
    ap.add_argument(
        "--output-json",
        default="docs/final/artifacts/universal_precursor_sufficiency_eval_v1_latest.json",
    )
    args = ap.parse_args()

    d5000 = _read_json(_resolve(args.r5000))
    d6866 = _read_json(_resolve(args.r6866))
    d9000 = _read_json(_resolve(args.r9000))

    s5000 = _set_from_ruleset(d5000)
    s6866 = _set_from_ruleset(d6866)
    s9000 = _set_from_ruleset(d9000)

    g5000 = (d5000.get("gate") or {}).get("decision")
    g6866 = (d6866.get("gate") or {}).get("decision")
    g9000 = (d9000.get("gate") or {}).get("decision")

    j_6866_9000 = _jaccard(s6866, s9000)
    j_5000_6866 = _jaccard(s5000, s6866)
    j_5000_9000 = _jaccard(s5000, s9000)

    # Sufficiency criteria for "continue to validation stage":
    # 1) mid/high top-k both GO
    # 2) mid/high overlap not collapsing (jaccard >= 0.25)
    # 3) candidate volume meaningful at mid top-k (>= 500)
    c6866 = int(((d6866.get("gate") or {}).get("score") or {}).get("count_relaxed_gate") or 0)
    pass_1 = g6866 == "GO_RESEARCH" and g9000 == "GO_RESEARCH"
    pass_2 = j_6866_9000 >= 0.25
    pass_3 = c6866 >= 500
    sufficient = bool(pass_1 and pass_2 and pass_3)

    out = {
        "schema": "universal_precursor_sufficiency_eval_v1",
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "a_track_binding_forbidden": True,
        "inputs": {
            "ruleset_top5000": str(_resolve(args.r5000)),
            "ruleset_top6866": str(_resolve(args.r6866)),
            "ruleset_top9000": str(_resolve(args.r9000)),
        },
        "metrics": {
            "gate_decisions": {"top5000": g5000, "top6866": g6866, "top9000": g9000},
            "candidate_counts": {
                "top5000": int(((d5000.get("gate") or {}).get("score") or {}).get("count_relaxed_gate") or 0),
                "top6866": c6866,
                "top9000": int(((d9000.get("gate") or {}).get("score") or {}).get("count_relaxed_gate") or 0),
            },
            "jaccard_overlap": {
                "top5000_vs_top6866": round(j_5000_6866, 6),
                "top6866_vs_top9000": round(j_6866_9000, 6),
                "top5000_vs_top9000": round(j_5000_9000, 6),
            },
        },
        "thresholds": {
            "top6866_gate_must_be_go": True,
            "top9000_gate_must_be_go": True,
            "min_top6866_candidate_count": 500,
            "min_jaccard_top6866_vs_top9000": 0.25,
        },
        "checks": {
            "gate_stability_mid_high": pass_1,
            "overlap_stability_mid_high": pass_2,
            "candidate_volume_mid": pass_3,
        },
        "decision": {
            "sufficient_for_next_validation_stage": sufficient,
            "label": "SUFFICIENT_CONTINUE_VALIDATION" if sufficient else "NOT_YET_SUFFICIENT",
        },
        "note": "Sufficiency here means enough insight to proceed to OOT/robustness validation, not production readiness.",
    }

    out_path = _resolve(args.output_json)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {out_path}")
    print(json.dumps(out["decision"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
