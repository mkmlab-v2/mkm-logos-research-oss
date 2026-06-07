#!/usr/bin/env python3
"""Top-N fusion overlap highlights from fusion join report ([HYPO])."""

from __future__ import annotations

import argparse
from pathlib import Path

from _frontline_legacy_common import ROOT, load_json, research_meta, utc_now, write_json


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--tag", required=True)
    ap.add_argument("--fusion-json", type=Path, default=None)
    ap.add_argument("--top-n", type=int, default=5)
    ap.add_argument("--out-json", type=Path, default=None)
    args = ap.parse_args()

    fusion_path = args.fusion_json or ROOT / "outputs" / f"fusion_join_quality_{args.tag}.json"
    out_path = args.out_json or ROOT / "outputs" / f"fusion_insight_topn_{args.tag}.json"
    fusion = load_json(fusion_path)

    highlights = []
    for key in ("overlap_work_keys_sample", "overlap_tier_script_sample", "fail_reasons"):
        val = fusion.get(key)
        if isinstance(val, list) and val:
            highlights.append({"field": key, "values": val[: args.top_n]})

    if not highlights:
        highlights = [
            {
                "field": "summary",
                "values": [
                    f"status={fusion.get('status')}",
                    f"overlap_ratio_dss={fusion.get('overlap_ratio_dss')}",
                    f"overlap_token_estimate={fusion.get('overlap_token_estimate')}",
                ],
            }
        ]

    payload = {
        "schema": "fusion_insight_topn_v1",
        "generated_at_utc": utc_now(),
        "tag": args.tag,
        "fusion_json": str(fusion_path),
        "top_n": args.top_n,
        "highlights": highlights[: args.top_n],
        **research_meta(),
    }
    write_json(out_path, payload)
    print(f"highlights={len(payload['highlights'])}\njson={out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
