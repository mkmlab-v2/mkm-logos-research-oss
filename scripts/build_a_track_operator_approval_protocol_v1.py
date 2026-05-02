# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.9, L:0.8, K:0.3, M:0.6}
# Balance: 93
# Purpose: Build operator approval protocol artifact for Track A stage promotion.
# Keywords: track_a, operator, approval, protocol, governance
#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT_DEFAULT = ROOT / "docs" / "final" / "artifacts" / "a_track_operator_approval_protocol_v1_latest.json"


def _now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def build_payload() -> dict:
    return {
        "schema": "a_track_operator_approval_protocol_v1",
        "generated_at_utc": _now_utc(),
        "status": "READY_FOR_SIGNOFF",
        "promotion_stages": [
            {
                "from_stage": "S1_SHADOW",
                "to_stage": "S2_PAPER_STRICT",
                "approval_required": True,
                "required_artifacts": [
                    "docs/final/artifacts/a_track_go_nogo_status_latest.json",
                    "docs/final/artifacts/a_track_price_output_unlock_policy_v1_latest.json",
                ],
            },
            {
                "from_stage": "S2_PAPER_STRICT",
                "to_stage": "S3_PAPER_SCALED",
                "approval_required": True,
                "required_artifacts": [
                    "docs/final/artifacts/a_track_go_nogo_status_latest.json",
                    "docs/final/artifacts/a_track_hold_release_checklist_v1_latest.json",
                ],
            },
            {
                "from_stage": "S3_PAPER_SCALED",
                "to_stage": "S4_LIMITED_LIVE",
                "approval_required": True,
                "required_artifacts": [
                    "docs/final/artifacts/a_track_go_nogo_status_latest.json",
                    "docs/final/artifacts/track_a_policy_floor_decision_v1.json",
                ],
            },
        ],
        "rollback_policy": {
            "auto_rollback_stage": "S1_SHADOW",
            "triggers": [
                "gate_fail",
                "daily_loss_cap_breach",
                "integrity_warning",
                "operator_stop_command",
            ],
        },
        "notes_ko": [
            "운영자 명시 승인 전에는 어떤 단계도 자동 승급하지 않는다.",
            "S4는 승인 + 롤백 체인 점검 완료가 모두 필요하다.",
        ],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Build Track A operator approval protocol artifact.")
    ap.add_argument("--out", type=Path, default=OUT_DEFAULT)
    args = ap.parse_args()

    out_path = args.out if args.out.is_absolute() else ROOT / args.out
    payload = build_payload()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {out_path}")
    print(f"status: {payload['status']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
