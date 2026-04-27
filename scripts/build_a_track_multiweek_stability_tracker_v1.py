# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.8, L:0.8, K:0.4, M:0.8}
# Balance: 90
# Purpose: Maintain multi-week stability tracker artifact for Track A S3 evidence.
# Keywords: track_a, s3, stability, tracker, weekly
#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
OUT_DEFAULT = ROOT / "docs" / "final" / "artifacts" / "a_track_multiweek_stability_tracker_v1_latest.json"


def _now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def build(prev: dict[str, Any] | None = None, increment_week: bool = False) -> dict[str, Any]:
    prev = prev or {}
    samples = int((prev.get("summary") or {}).get("weeks_collected", 0))
    if increment_week:
        samples += 1
    required = 4
    return {
        "schema": "a_track_multiweek_stability_tracker_v1",
        "generated_at_utc": _now_utc(),
        "status": "COLLECTING",
        "requirements": {
            "required_weeks": required,
            "minimum_stage": "S2_PAPER_STRICT",
            "required_metrics": ["weekly_mdd", "weekly_net_pnl", "cost_adjusted_return", "anomaly_count"],
        },
        "summary": {
            "weeks_collected": samples,
            "weeks_remaining": max(required - samples, 0),
            "ready_for_s3_gate": samples >= required,
        },
        "notes_ko": [
            "S3는 다주간 안정성 증거가 필요하므로 즉시 완료 처리하지 않는다.",
            "주차 데이터가 누적되면 ready_for_s3_gate가 true로 전환된다.",
        ],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Build/refresh Track A multiweek stability tracker artifact.")
    ap.add_argument("--out", type=Path, default=OUT_DEFAULT)
    ap.add_argument(
        "--increment-week",
        action="store_true",
        help="Increment weeks_collected by 1 for weekly evidence rollup.",
    )
    args = ap.parse_args()
    out = args.out if args.out.is_absolute() else ROOT / args.out
    prev = _load(out) if out.is_file() else None
    payload = build(prev=prev, increment_week=args.increment_week)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {out}")
    print(f"weeks_collected: {payload['summary']['weeks_collected']}")
    print(f"ready_for_s3_gate: {payload['summary']['ready_for_s3_gate']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
