#!/usr/bin/env python3
"""Generate fusion rule candidates from overlap metadata ([HYPO] · no live trading)."""

from __future__ import annotations

import argparse
from pathlib import Path

from _frontline_legacy_common import ROOT, load_json, research_meta, utc_now, write_json


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--tag", required=True)
    ap.add_argument("--fusion-json", type=Path, default=None)
    ap.add_argument("--out-json", type=Path, default=None)
    args = ap.parse_args()

    fusion_path = args.fusion_json or ROOT / "outputs" / f"fusion_join_quality_{args.tag}.json"
    out_path = args.out_json or ROOT / "outputs" / f"fusion_rule_candidates_{args.tag}.json"
    fusion = load_json(fusion_path)
    ratio = float(fusion.get("overlap_ratio_dss") or 0.0)

    candidates = [
        {
            "rule_id": "fusion_overlap_watch",
            "condition": "overlap_ratio_dss >= 0.02",
            "action": "WATCH",
            "enabled": ratio >= 0.02,
        },
        {
            "rule_id": "fusion_overlap_hold",
            "condition": "overlap_ratio_dss < 0.02",
            "action": "HOLD",
            "enabled": ratio < 0.02,
        },
    ]

    payload = {
        "schema": "fusion_rule_candidates_v1",
        "generated_at_utc": utc_now(),
        "tag": args.tag,
        "fusion_json": str(fusion_path),
        "candidate_count": len(candidates),
        "candidates": candidates,
        **research_meta(),
    }
    write_json(out_path, payload)
    print(f"candidates={len(candidates)}\njson={out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
