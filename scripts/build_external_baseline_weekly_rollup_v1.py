#!/usr/bin/env python3
# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.7, L:0.8, K:0.3, M:0.7}
# Balance: 88
# Purpose: Build weekly one-file rollup for operator view.
# Keywords: weekly rollup, summary, operator
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def resolve(path_str: str) -> Path:
    p = Path(path_str)
    return p if p.is_absolute() else ROOT / p


def load_json(path: Path) -> dict:
    if not path.is_file():
        return {}
    obj = json.loads(path.read_text(encoding="utf-8"))
    return obj if isinstance(obj, dict) else {}


def main() -> int:
    ap = argparse.ArgumentParser(description="Build weekly rollup for external baseline operations.")
    ap.add_argument("--hint-json", default="docs/final/artifacts/external_bible_crossref_threshold_recalibration_hint_latest.json")
    ap.add_argument("--apply-log-summary-json", default="docs/final/artifacts/external_bible_crossref_threshold_apply_log_summary_latest.json")
    ap.add_argument("--health-check-json", default="docs/final/artifacts/external_bible_crossref_health_check_latest.json")
    ap.add_argument("--approval-expiry-warning-json", default="docs/final/artifacts/external_bible_crossref_approval_expiry_warning_latest.json")
    ap.add_argument("--watch-streak-cut", type=int, default=10)
    ap.add_argument("--output-json", default="docs/final/artifacts/external_bible_crossref_weekly_rollup_latest.json")
    args = ap.parse_args()

    hint = load_json(resolve(args.hint_json))
    log_summary = load_json(resolve(args.apply_log_summary_json))
    health = load_json(resolve(args.health_check_json))
    approval_warning = load_json(resolve(args.approval_expiry_warning_json))
    hint_active = bool(hint.get("hint_active", False))
    monitor_streak = int(hint.get("monitor_only_streak", 0) or 0)
    all_healthy = bool(health.get("all_healthy", False))
    watch_streak_cut = max(1, int(args.watch_streak_cut))
    renewal_due = bool(approval_warning.get("renewal_due", False))
    approval_expiring_soon = bool(approval_warning.get("expiring_soon", False))

    if not all_healthy:
        status = "hold"
        rationale = "health_check_not_green"
    elif renewal_due:
        status = "watch"
        rationale = "approval_renewal_due"
    elif hint_active and monitor_streak >= watch_streak_cut:
        status = "watch"
        rationale = "monitor_only_streak_high"
    elif hint_active:
        status = "watch"
        rationale = "hint_active"
    else:
        status = "go"
        rationale = "stable_green"

    out = {
        "schema": "external_bible_crossref_weekly_rollup_v1",
        "generated_at_utc": now_utc(),
        "research_only": True,
        "promotion_required": True,
        "source_track": "K",
        "operator_signal": {
            "status": status,
            "rationale": rationale,
        },
        "summary": {
            "hint_active": hint_active,
            "monitor_only_streak": monitor_streak,
            "apply_count_total": int(log_summary.get("apply_count_total", 0) or 0),
            "all_healthy": all_healthy,
            "approval_expiring_soon": approval_expiring_soon,
            "approval_renewal_due": renewal_due,
        },
    }
    out_path = resolve(args.output_json)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(out_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
