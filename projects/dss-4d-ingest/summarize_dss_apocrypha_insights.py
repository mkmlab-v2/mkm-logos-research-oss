#!/usr/bin/env python3
"""One-line operator summary from latest insight brief ([HYPO] · research_only)."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from _frontline_legacy_common import ROOT, load_json, research_meta, utc_now, write_json


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--tag", required=True)
    ap.add_argument("--insight-brief-json", type=Path, default=None)
    ap.add_argument("--out-json", type=Path, default=None)
    args = ap.parse_args()

    brief_path = args.insight_brief_json or ROOT / "outputs" / f"dss_apocrypha_insight_brief_{args.tag}.json"
    out_path = args.out_json or ROOT / "outputs" / f"dss_apocrypha_insight_summary_{args.tag}.json"
    brief = load_json(brief_path)
    metrics = brief.get("metrics") if isinstance(brief.get("metrics"), dict) else {}

    summary = (
        f"hebrew={metrics.get('hebrew_primary_tokens', 0)} "
        f"fusion_overlap={metrics.get('fusion_overlap_ratio_dss', 0)} "
        f"pilot_ready={brief.get('pilot_insight_ready', False)}"
    )
    payload = {
        "schema": "dss_apocrypha_insight_summary_v1",
        "generated_at_utc": utc_now(),
        "tag": args.tag,
        "summary": summary,
        "insight_brief_json": str(brief_path),
        **research_meta(),
    }
    write_json(out_path, payload)
    print(summary)
    print(f"json={out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
