#!/usr/bin/env python3
"""Build rollback policy artifact for prophecy live enable."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"
DEFAULT_OUT = ART / "prophecy_live_rollback_policy_v1_latest.json"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--max-daily-loss-pct", type=float, default=2.5)
    ap.add_argument("--max-consecutive-gate-fails", type=int, default=1)
    ap.add_argument("--data-gap-minutes", type=int, default=30)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    payload = {
        "schema": "prophecy_live_rollback_policy_v1",
        "generated_at_utc": _now(),
        "track": "prophecy",
        "policy": {
            "max_daily_loss_pct": float(args.max_daily_loss_pct),
            "max_consecutive_gate_fails": int(args.max_consecutive_gate_fails),
            "max_data_gap_minutes": int(args.data_gap_minutes),
        },
        "actions_on_trigger": [
            "disable_live_trigger_immediately",
            "revert_to_previous_candidate_only_mode",
            "record_incident_and_request_human_review",
        ],
        "constraints": {
            "auto_reenable_live": False,
            "human_reapproval_required": True,
        },
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
