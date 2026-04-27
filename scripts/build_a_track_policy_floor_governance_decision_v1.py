# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.9, L:0.8, K:0.2, M:0.6}
# Balance: 91
# Purpose: Emit explicit governance decision artifact for Track A policy floor.
# Keywords: track_a, policy_floor, governance, decision
#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT_DEFAULT = ROOT / "docs" / "final" / "artifacts" / "a_track_policy_floor_governance_decision_v1_latest.json"


def _now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def build() -> dict:
    return {
        "schema": "a_track_policy_floor_governance_decision_v1",
        "generated_at_utc": _now_utc(),
        "status": "APPROVED",
        "decision": "KEEP_POLICY_FLOOR_0_49",
        "effective_policy_floor": 0.49,
        "change_requested": False,
        "rationale": "Commercialization floor remains unchanged until runtime saving evidence exceeds policy floor.",
        "notes_ko": [
            "정책 바닥선 0.49 유지 결정을 명시적으로 확정한다.",
            "변경 요청은 별도 거버넌스 승인 아티팩트로만 허용한다.",
        ],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Build Track A policy floor governance decision artifact.")
    ap.add_argument("--out", type=Path, default=OUT_DEFAULT)
    args = ap.parse_args()
    out = args.out if args.out.is_absolute() else ROOT / args.out
    payload = build()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {out}")
    print(f"status: {payload['status']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
