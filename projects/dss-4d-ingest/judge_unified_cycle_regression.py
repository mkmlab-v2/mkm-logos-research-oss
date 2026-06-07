#!/usr/bin/env python3
"""Regression judge: current cycle vs prior PASS report ([HYPO] · non-gating)."""

from __future__ import annotations

import argparse
from pathlib import Path

from _frontline_legacy_common import ROOT, load_json, latest_glob, research_meta, utc_now, write_json


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--tag", required=True)
    ap.add_argument("--current-report-json", type=Path, default=None)
    ap.add_argument("--baseline-report-json", type=Path, default=None)
    ap.add_argument("--out-json", type=Path, default=None)
    args = ap.parse_args()

    current_path = args.current_report_json or ROOT / "outputs" / f"unified_frontline_cycle_report_{args.tag}.json"
    baseline_path = args.baseline_report_json or latest_glob("unified_frontline_cycle_report_*.json")
    out_path = args.out_json or ROOT / "outputs" / f"unified_cycle_regression_{args.tag}.json"

    current = load_json(current_path)
    baseline = load_json(baseline_path) if baseline_path and baseline_path != current_path else {}

    cur_status = str(current.get("overall_status") or "UNKNOWN")
    base_status = str(baseline.get("overall_status") or cur_status)
    cur_auth = (current.get("notes") or {}).get("authority_readiness_status")
    base_auth = (baseline.get("notes") or {}).get("authority_readiness_status")

    regressions = []
    if base_status == "PASS" and cur_status != "PASS":
        regressions.append("overall_status_regressed")
    if base_auth == "READY" and cur_auth and cur_auth != "READY":
        regressions.append("authority_readiness_regressed")

    status = "PASS" if not regressions else "FAIL"
    payload = {
        "schema": "unified_cycle_regression_v1",
        "generated_at_utc": utc_now(),
        "tag": args.tag,
        "status": status,
        "regressions": regressions,
        "current": {"overall_status": cur_status, "authority_readiness_status": cur_auth},
        "baseline": {"overall_status": base_status, "authority_readiness_status": base_auth},
        "inputs": {"current_report": str(current_path), "baseline_report": str(baseline_path) if baseline_path else None},
        **research_meta(),
    }
    write_json(out_path, payload)
    print(f"status={status}\njson={out_path}")
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
