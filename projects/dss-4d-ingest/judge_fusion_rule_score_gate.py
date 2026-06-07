#!/usr/bin/env python3
"""Gate fusion rule scores — PASS if best score >= threshold ([HYPO])."""

from __future__ import annotations

import argparse
from pathlib import Path

from _frontline_legacy_common import ROOT, load_json, research_meta, utc_now, write_json


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--tag", required=True)
    ap.add_argument("--scores-json", type=Path, default=None)
    ap.add_argument("--min-best-score", type=float, default=0.5)
    ap.add_argument("--out-json", type=Path, default=None)
    args = ap.parse_args()

    scores_path = args.scores_json or ROOT / "outputs" / f"fusion_rule_scores_{args.tag}.json"
    out_path = args.out_json or ROOT / "outputs" / f"fusion_rule_score_gate_{args.tag}.json"
    scores_doc = load_json(scores_path)
    scored = scores_doc.get("scored") if isinstance(scores_doc.get("scored"), list) else []
    best = max((float(x.get("score") or 0) for x in scored if isinstance(x, dict)), default=0.0)
    status = "PASS" if best >= args.min_best_score else "FAIL"

    payload = {
        "schema": "fusion_rule_score_gate_v1",
        "generated_at_utc": utc_now(),
        "tag": args.tag,
        "status": status,
        "best_score": best,
        "min_best_score": args.min_best_score,
        "scores_json": str(scores_path),
        **research_meta(),
    }
    write_json(out_path, payload)
    print(f"status={status}\njson={out_path}")
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
