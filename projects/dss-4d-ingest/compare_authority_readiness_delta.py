#!/usr/bin/env python3
"""Compare current authority readiness vs pinned baseline ([HYPO])."""

from __future__ import annotations

import argparse
from pathlib import Path

from _frontline_legacy_common import ROOT, load_json, research_meta, utc_now, write_json


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--tag", required=True)
    ap.add_argument("--current-json", type=Path, default=None)
    ap.add_argument("--baseline-json", type=Path, default=None)
    ap.add_argument("--out-json", type=Path, default=None)
    args = ap.parse_args()

    current_path = args.current_json or ROOT / "outputs" / f"authority_readiness_{args.tag}.json"
    baseline_path = args.baseline_json or ROOT / "outputs" / "authority_readiness_command_center_followup_20260327_h_ext3.json"
    out_path = args.out_json or ROOT / "outputs" / f"authority_readiness_delta_{args.tag}.json"

    current = load_json(current_path)
    baseline = load_json(baseline_path)
    cur_status = str(current.get("status") or "UNKNOWN")
    base_status = str(baseline.get("status") or "UNKNOWN")
    cur_metrics = current.get("metrics") if isinstance(current.get("metrics"), dict) else {}
    base_metrics = baseline.get("metrics") if isinstance(baseline.get("metrics"), dict) else {}

    payload = {
        "schema": "authority_readiness_delta_v1",
        "generated_at_utc": utc_now(),
        "tag": args.tag,
        "current_status": cur_status,
        "baseline_status": base_status,
        "status_changed": cur_status != base_status,
        "metric_deltas": {
            "hebrew_primary_tokens": int(cur_metrics.get("hebrew_primary_tokens") or 0)
            - int(base_metrics.get("hebrew_primary_tokens") or 0),
            "fusion_overlap_ratio_dss": round(
                float(cur_metrics.get("fusion_overlap_ratio_dss") or 0)
                - float(base_metrics.get("fusion_overlap_ratio_dss") or 0),
                6,
            ),
        },
        "inputs": {"current_json": str(current_path), "baseline_json": str(baseline_path)},
        **research_meta(),
    }
    write_json(out_path, payload)
    print(f"status_delta={cur_status}->{base_status}\njson={out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
