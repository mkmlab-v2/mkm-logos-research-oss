#!/usr/bin/env python3
"""Emit default A-track governance JSON artifacts when files are missing (local bootstrap).

These files are human-governed; defaults are placeholders for pipeline wiring and CI.
Replace with signed-off content before any production claim.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Tuple

ROOT = Path(__file__).resolve().parent.parent
ART_DIR = ROOT / "docs" / "final" / "artifacts"


def _now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _write(path: Path, obj: Dict[str, Any], force: bool) -> str:
    if path.is_file() and not force:
        return "skipped"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")
    return "wrote"


SPEC: List[Tuple[str, Callable[[], Dict[str, Any]]]] = [
    (
        str(ART_DIR / "a_track_price_output_unlock_policy_v1_latest.json"),
        lambda: {
            "schema": "a_track_price_output_unlock_policy_v1",
            "generated_at_utc": _now_utc(),
            "status": "READY_FOR_SIGNOFF",
            "notes_ko": [
                "기본 산출물입니다. 실전 전 수치 기준과 서명 프로세스를 확정하세요.",
            ],
            "criteria": {
                "chronos_holdout_direction_match_rate_min_pct": 50.0,
                "relock_on_regression_signals_max": 2,
            },
        },
    ),
    (
        str(ART_DIR / "a_track_high_reliability_release_plan_v1_latest.json"),
        lambda: {
            "schema": "a_track_high_reliability_release_plan_v1",
            "generated_at_utc": _now_utc(),
            "status": "READY_FOR_SIGNOFF",
            "notes_ko": ["기본 산출물입니다. HOLD 해제 조건을 운영자와 정합하세요."],
            "requirements": {
                "required_consecutive_cycles_non_hold": 3,
                "max_allowed_regression_signals": 1,
            },
        },
    ),
    (
        str(ART_DIR / "a_track_operator_approval_protocol_v1_latest.json"),
        lambda: {
            "schema": "a_track_operator_approval_protocol_v1",
            "generated_at_utc": _now_utc(),
            "status": "READY_FOR_SIGNOFF",
            "notes_ko": ["승인자·근거 파일·롤백 트리거를 확정한 뒤 서명하세요."],
            "stages": ["S2_PAPER_STRICT", "S3_PAPER_SCALED", "S4_LIMITED_LIVE"],
        },
    ),
    (
        str(ART_DIR / "a_track_policy_floor_governance_decision_v1_latest.json"),
        lambda: {
            "schema": "a_track_policy_floor_governance_decision_v1",
            "generated_at_utc": _now_utc(),
            "status": "APPROVED",
            "decision": "KEEP_POLICY_FLOOR_049_HOLD_BASELINE",
            "notes_ko": ["Track A policy floor 거버넌스 기본값; 변경 시 본 아티팩트를 갱신하세요."],
        },
    ),
    (
        str(ART_DIR / "track_a_policy_floor_decision_v1.json"),
        lambda: {
            "schema": "track_a_policy_floor_decision_v1",
            "generated_at_utc": _now_utc(),
            "decision": "DECISION_KEEP_POLICY_FLOOR_049_HOLD_BASELINE",
            "notes_ko": ["체크리스트 입력용 policy floor 포인터."],
        },
    ),
]


def main() -> int:
    ap = argparse.ArgumentParser(description="Emit default A-track governance JSON artifacts.")
    ap.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing files.",
    )
    args = ap.parse_args()

    wrote = 0
    skipped = 0
    for rel, factory in SPEC:
        path = Path(rel)
        status = _write(path, factory(), args.force)
        print(f"{status.upper()}: {path}")
        if status == "wrote":
            wrote += 1
        else:
            skipped += 1

    print(f"summary: wrote={wrote}, skipped={skipped}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
