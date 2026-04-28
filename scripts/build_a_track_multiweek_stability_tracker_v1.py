#!/usr/bin/env python3
"""Maintain multi-week stability evidence tracker for Track A S3 gate."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "a_track_multiweek_stability_tracker_v1_latest.json"


def _now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def build_payload(
    prior: dict[str, Any] | None,
    *,
    increment_week: bool,
    required_weeks: int,
) -> dict[str, Any]:
    req = int(required_weeks)
    if req < 1:
        req = 4

    if prior:
        base = dict(prior)
        summary = dict(base.get("summary") or {})
        requirements = dict(base.get("requirements") or {})
    else:
        base = {}
        summary = {}
        requirements = {
            "required_weeks": req,
            "minimum_stage": "S2_PAPER_STRICT",
            "required_metrics": [
                "weekly_mdd",
                "weekly_net_pnl",
                "cost_adjusted_return",
                "anomaly_count",
            ],
        }

    requirements.setdefault("required_weeks", req)
    rw = int(requirements.get("required_weeks") or req)
    if rw < 1:
        rw = req

    weeks_collected = int(summary.get("weeks_collected") or 0)
    if increment_week:
        weeks_collected += 1

    weeks_remaining = max(0, rw - weeks_collected)
    ready = weeks_collected >= rw

    summary["weeks_collected"] = weeks_collected
    summary["weeks_remaining"] = weeks_remaining
    summary["ready_for_s3_gate"] = ready

    base.update(
        {
            "schema": "a_track_multiweek_stability_tracker_v1",
            "generated_at_utc": _now_utc(),
            "status": "SATISFIED" if ready else "COLLECTING",
            "requirements": requirements,
            "summary": summary,
            "notes_ko": base.get("notes_ko")
            or [
                "S3는 다주간 안정성 증거가 필요하므로 즉시 완료 처리하지 않는다.",
                "주차 데이터가 누적되면 ready_for_s3_gate가 true로 전환된다.",
            ],
        }
    )
    return base


def main() -> int:
    ap = argparse.ArgumentParser(description="Update A-track multi-week stability tracker.")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument(
        "--increment-week",
        action="store_true",
        help="Add one week to weeks_collected (scheduled weekly rollup).",
    )
    ap.add_argument(
        "--required-weeks",
        type=int,
        default=0,
        help="Override requirements.required_weeks when > 0.",
    )
    args = ap.parse_args()

    out_path = args.out if args.out.is_absolute() else ROOT / args.out
    prior: dict[str, Any] | None = None
    if out_path.is_file():
        try:
            prior = _load(out_path)
        except Exception:
            prior = None

    req_weeks = args.required_weeks
    if req_weeks <= 0 and prior:
        req_weeks = int((prior.get("requirements") or {}).get("required_weeks") or 4)
    if req_weeks <= 0:
        req_weeks = 4

    payload = build_payload(prior, increment_week=args.increment_week, required_weeks=req_weeks)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"WROTE: {out_path}")
    print(f"ready_for_s3_gate: {payload.get('summary', {}).get('ready_for_s3_gate')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
