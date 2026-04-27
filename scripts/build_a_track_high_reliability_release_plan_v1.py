# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.9, L:0.8, K:0.3, M:0.5}
# Balance: 92
# Purpose: Build high-reliability HOLD release plan artifact for Track A.
# Keywords: track_a, high_reliability, release_plan, hold
#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
OUT_DEFAULT = ROOT / "docs" / "final" / "artifacts" / "a_track_high_reliability_release_plan_v1_latest.json"


def _now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def build(go_nogo: dict[str, Any]) -> dict[str, Any]:
    snapshot = go_nogo.get("snapshot") or {}
    failed = set((go_nogo.get("result") or {}).get("failed_reasons") or [])
    is_hold = "high_reliability_decision_is_hold" in failed
    return {
        "schema": "a_track_high_reliability_release_plan_v1",
        "generated_at_utc": _now_utc(),
        "status": "READY_FOR_SIGNOFF",
        "current": {
            "high_reliability_decision": snapshot.get("high_reliability_decision"),
            "is_hold_blocker_present": is_hold,
        },
        "release_conditions": {
            "required_consecutive_cycles_non_hold": 2,
            "required_mode_gate_pass": True,
            "max_allowed_regression_signals": 0,
        },
        "rollback_triggers": [
            "high_reliability_decision_back_to_hold",
            "mode_gate_fail",
            "integrity_warning",
        ],
        "notes_ko": [
            "high reliability HOLD 해제는 연속성(2사이클) 기준으로 판단한다.",
            "단일 개선 샘플로는 해제하지 않는다.",
        ],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Build high reliability release plan for Track A.")
    ap.add_argument(
        "--go-nogo",
        type=Path,
        default=ROOT / "docs" / "final" / "artifacts" / "a_track_go_nogo_status_latest.json",
    )
    ap.add_argument("--out", type=Path, default=OUT_DEFAULT)
    args = ap.parse_args()

    out = args.out if args.out.is_absolute() else ROOT / args.out
    go_nogo = _load(args.go_nogo if args.go_nogo.is_absolute() else ROOT / args.go_nogo)
    payload = build(go_nogo)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {out}")
    print(f"status: {payload['status']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
