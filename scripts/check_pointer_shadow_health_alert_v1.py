#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
ART = ROOT / "docs" / "final" / "artifacts"
REPORT_DEFAULT = ART / "pointer_hash_snapping_router_shadow_daily_report_latest.json"
OUT_DEFAULT = ART / "pointer_hash_snapping_router_shadow_alert_latest.json"


def _now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--daily-report", type=Path, default=REPORT_DEFAULT)
    ap.add_argument("--min-sample-count", type=int, default=3)
    ap.add_argument("--candidate-ok-rate-min", type=float, default=0.4)
    ap.add_argument("--max-unresolved-per-run", type=float, default=8.0)
    ap.add_argument("--apply-row-ratio-min", type=float, default=0.15)
    ap.add_argument("--apply-max-unresolved-per-run", type=float, default=6.0)
    ap.add_argument("--caution-row-ratio-max", type=float, default=0.35)
    ap.add_argument("--caution-max-unresolved-per-run", type=float, default=2.0)
    ap.add_argument("--out", type=Path, default=OUT_DEFAULT)
    args = ap.parse_args()

    report_path = args.daily_report if args.daily_report.is_absolute() else ROOT / args.daily_report
    rep = _read_json(report_path)
    ws = rep.get("window_stats", {})
    sample_count = int(ws.get("sample_count", 0))
    ok_rate = float(ws.get("avg_pointer_candidate_ok_rate", 0.0))
    unresolved = float(ws.get("avg_unresolved_token_per_run", 0.0))
    policy_ratio = ws.get("path_policy_avg_row_ratio", {})
    policy_unresolved = ws.get("path_policy_avg_unresolved_per_run", {})
    apply_ratio = float(policy_ratio.get("apply", 0.0))
    caution_ratio = float(policy_ratio.get("caution", 0.0))
    apply_unresolved = float(policy_unresolved.get("apply", 0.0))
    caution_unresolved = float(policy_unresolved.get("caution", 0.0))

    reasons: list[str] = []
    if sample_count >= args.min_sample_count and ok_rate < args.candidate_ok_rate_min:
        reasons.append("low_candidate_ok_rate")
    if sample_count >= args.min_sample_count and unresolved > args.max_unresolved_per_run:
        reasons.append("high_unresolved_tokens")
    if sample_count >= args.min_sample_count and apply_ratio < args.apply_row_ratio_min:
        reasons.append("low_apply_coverage")
    if sample_count >= args.min_sample_count and apply_unresolved > args.apply_max_unresolved_per_run:
        reasons.append("high_apply_unresolved_tokens")
    if sample_count >= args.min_sample_count and caution_ratio > args.caution_row_ratio_max:
        reasons.append("high_caution_coverage")
    if sample_count >= args.min_sample_count and caution_unresolved > args.caution_max_unresolved_per_run:
        reasons.append("high_caution_unresolved_tokens")

    should_alert = len(reasons) > 0
    severity = "none"
    if should_alert and "low_candidate_ok_rate" in reasons and "high_unresolved_tokens" in reasons:
        severity = "high"
    elif should_alert:
        severity = "medium"

    out_doc = {
        "schema": "pointer_hash_snapping_router_shadow_alert_v1",
        "generated_at_utc": _now_utc(),
        "research_only": True,
        "source_track": "B",
        "inputs": {
            "daily_report": str(report_path),
            "min_sample_count": args.min_sample_count,
            "candidate_ok_rate_min": args.candidate_ok_rate_min,
            "max_unresolved_per_run": args.max_unresolved_per_run,
            "apply_row_ratio_min": args.apply_row_ratio_min,
            "apply_max_unresolved_per_run": args.apply_max_unresolved_per_run,
            "caution_row_ratio_max": args.caution_row_ratio_max,
            "caution_max_unresolved_per_run": args.caution_max_unresolved_per_run,
        },
        "window_stats": {
            "sample_count": sample_count,
            "avg_pointer_candidate_ok_rate": ok_rate,
            "avg_unresolved_token_per_run": unresolved,
            "path_policy_avg_row_ratio": {
                "apply": apply_ratio,
                "caution": caution_ratio,
            },
            "path_policy_avg_unresolved_per_run": {
                "apply": apply_unresolved,
                "caution": caution_unresolved,
            },
        },
        "should_alert": should_alert,
        "severity": severity,
        "reasons": reasons,
    }

    out_path = args.out if args.out.is_absolute() else ROOT / args.out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(out_path), "should_alert": should_alert, "severity": severity}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
