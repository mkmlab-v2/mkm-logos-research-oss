#!/usr/bin/env python3
"""Score fusion rule candidates against fusion report ([HYPO])."""

from __future__ import annotations

import argparse
from pathlib import Path

from _frontline_legacy_common import ROOT, load_json, research_meta, utc_now, write_json


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--tag", required=True)
    ap.add_argument("--candidates-json", type=Path, default=None)
    ap.add_argument("--fusion-json", type=Path, default=None)
    ap.add_argument("--out-json", type=Path, default=None)
    args = ap.parse_args()

    cand_path = args.candidates_json or ROOT / "outputs" / f"fusion_rule_candidates_{args.tag}.json"
    fusion_path = args.fusion_json or ROOT / "outputs" / f"fusion_join_quality_{args.tag}.json"
    out_path = args.out_json or ROOT / "outputs" / f"fusion_rule_scores_{args.tag}.json"

    candidates_doc = load_json(cand_path)
    fusion = load_json(fusion_path)
    fusion_pass = str(fusion.get("status") or "").upper() == "PASS"
    ratio = float(fusion.get("overlap_ratio_dss") or 0.0)

    scored = []
    for cand in candidates_doc.get("candidates") or []:
        if not isinstance(cand, dict):
            continue
        enabled = bool(cand.get("enabled"))
        score = round((0.6 if fusion_pass else 0.2) + min(ratio, 0.4), 4) if enabled else 0.1
        scored.append({**cand, "score": score, "fusion_pass": fusion_pass})

    payload = {
        "schema": "fusion_rule_scores_v1",
        "generated_at_utc": utc_now(),
        "tag": args.tag,
        "candidates_json": str(cand_path),
        "fusion_json": str(fusion_path),
        "scored": scored,
        "best_rule_id": max(scored, key=lambda x: x.get("score", 0))["rule_id"] if scored else None,
        **research_meta(),
    }
    write_json(out_path, payload)
    print(f"scored={len(scored)}\njson={out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
