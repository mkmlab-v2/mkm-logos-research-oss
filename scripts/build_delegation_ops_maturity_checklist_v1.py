#!/usr/bin/env python3
"""Build delegation-style ops maturity checklist from disk SSOT artifacts."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
OUT_DEFAULT = ROOT / "reports/delegation_ops_maturity_checklist_v1_latest.json"

POINTERS = {
    "parallel_passive_loop": ROOT / "reports/parallel_passive_loop_v1_latest.json",
    "parallel_passive_approval": ROOT
    / "reports/delegation_parallel_passive_loop_approval_map_v1_latest.json",
    "nextgen_noop": ROOT / "reports/ng40_golden40_frozen_tie_noop_v1_latest.json",
    "nextgen_approval": ROOT / "reports/delegation_nextgen_engine_approval_map_v1_latest.json",
    "ms340_gate": ROOT / "reports/kstartup_startup_package_ai_submission_gate_latest.json",
    "ms340_verify": ROOT / "reports/kstartup_startup_package_ai_filled_plan_verify_latest.json",
}


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (json.JSONDecodeError, OSError):
        return None


def _level(*, pass_: bool, partial: bool = False) -> str:
    if pass_:
        return "mature"
    if partial:
        return "emerging"
    return "blocked"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out-json", type=Path, default=OUT_DEFAULT)
    args = ap.parse_args()

    loop = _load(POINTERS["parallel_passive_loop"]) or {}
    loop_map = _load(POINTERS["parallel_passive_approval"]) or {}
    noop = _load(POINTERS["nextgen_noop"]) or {}
    ng_map = _load(POINTERS["nextgen_approval"]) or {}
    ms_gate = _load(POINTERS["ms340_gate"]) or {}
    ms_verify = _load(POINTERS["ms340_verify"]) or {}

    loop_ok = bool(loop.get("loop_ok"))
    nebius_stop = loop.get("web_ops_included") is False
    lanes = loop.get("lanes") if isinstance(loop.get("lanes"), list) else []
    lane_exits = {
        str(l.get("id")): l.get("exit_code")
        for l in lanes
        if isinstance(l, dict)
    }

    ms_upload = bool(ms_gate.get("upload_ok"))
    ms_verify_ok = bool(ms_verify.get("ok"))

    noop_final = (noop.get("final_action") or "").upper() == "WATCH"
    strict_beat_missing = noop.get("apply_active_recommended") is False

    dimensions = [
        {
            "id": "D1_evidence_ssot",
            "name": "증거 SSOT·exit code",
            "level": _level(pass_=loop_ok and ms_gate.get("blockers_failed") == []),
            "approval": "AUTO",
            "evidence": [
                str(POINTERS["parallel_passive_loop"].relative_to(ROOT)).replace("\\", "/"),
                str(POINTERS["ms340_gate"].relative_to(ROOT)).replace("\\", "/"),
            ],
            "note_ko": "loop_ok·submission_gate blockers 없음",
        },
        {
            "id": "D2_stop_lanes",
            "name": "STOP 레인·격벽",
            "level": _level(pass_=nebius_stop and strict_beat_missing),
            "approval": "STOP",
            "evidence": [
                str(POINTERS["nextgen_noop"].relative_to(ROOT)).replace("\\", "/"),
            ],
            "note_ko": "Nebius 미터치·ACTIVE apply noop",
        },
        {
            "id": "D3_resume_triggers",
            "name": "재개 트리거·페르소나",
            "level": _level(
                pass_=bool(loop_map.get("ssot", {}).get("persona")),
                partial=loop_map.get("delegation_status") == "auto_complete",
            ),
            "approval": "AUTO",
            "evidence": ["scripts/Invoke-ParallelPassiveLoop_v1.ps1"],
            "note_ko": "병렬 패시브·MISSION_LOG 트리거 고정",
        },
        {
            "id": "D4_human_gates",
            "name": "human 게이트 분리",
            "level": _level(pass_=ms_upload and ms_verify_ok, partial=ms_upload),
            "approval": "STOP",
            "evidence": [str(POINTERS["ms340_verify"].relative_to(ROOT)).replace("\\", "/")],
            "note_ko": "제출·G6·live는 human; 문서 게이트는 자동",
        },
        {
            "id": "D5_promotion_truth",
            "name": "승격·헤드라인 정직성",
            "level": _level(pass_=noop_final and ng_map.get("track_a_active_write") is False),
            "approval": "STOP",
            "evidence": [str(POINTERS["nextgen_noop"].relative_to(ROOT)).replace("\\", "/")],
            "note_ko": "strict beat 없으면 WATCH·MS headline 합선 금지",
        },
    ]

    mature_count = sum(1 for d in dimensions if d["level"] == "mature")
    overall = "mature" if mature_count >= 4 else ("emerging" if mature_count >= 2 else "blocked")

    out: dict[str, Any] = {
        "schema": "delegation_ops_maturity_checklist_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypo_label": "[HYPO]",
        "track_a_active_write": False,
        "delegation_status": overall,
        "maturity_score": f"{mature_count}/{len(dimensions)}",
        "verdict_ko": (
            "위임형 자동진행은 운영·증거·게이트 레인에서 성숙. "
            "상용 승격·PMS 제출은 human STOP 유지가 정상."
        ),
        "ssot": {
            "mission_log_pointer": "MISSION_LOG.md §병렬 패시브 루프",
            "builder": "scripts/build_delegation_ops_maturity_checklist_v1.py",
            "refresh": "py scripts/build_delegation_ops_maturity_checklist_v1.py",
        },
        "global_stop_rules": [
            "apply-active without strict dual-axis beat",
            "live trading ON",
            "PMS 제출완료 without human",
            "Nebius/web_ops until GPU approval",
            "MS/Oracle headline merge from B-track uplift",
        ],
        "dimensions": dimensions,
        "lanes_snapshot": {
            "parallel_passive": {
                "loop_ok": loop_ok,
                "generated_at_utc": loop.get("generated_at_utc"),
                "lane_exit_codes": lane_exits,
                "nebius_lane_default": loop.get("nebius_lane_default"),
            },
            "nextgen": {
                "final_action": noop.get("final_action"),
                "apply_active_recommended": noop.get("apply_active_recommended"),
            },
            "ms340": {
                "upload_ok": ms_upload,
                "filled_verify_ok": ms_verify_ok,
                "draft_mode": ms_gate.get("draft_mode"),
            },
        },
        "next_actions": [
            {
                "owner": "AUTO",
                "action": "MKM_ParallelPassiveLoop_Daily 09:15 (등록됨; Verify-ParallelPassiveLoopDailyTaskReadiness_v1.ps1)",
            },
            {
                "owner": "human",
                "action": "MS340 PMS 20461210 제출 6/12 18:00 → Run-Kstartup340PostSubmitAttest_v1.ps1",
            },
            {
                "owner": "WATCH",
                "action": "차세대 strict beat 없음 — noop 유지",
            },
        ],
    }

    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {"wrote": str(args.out_json), "delegation_status": overall, "score": out["maturity_score"]},
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
