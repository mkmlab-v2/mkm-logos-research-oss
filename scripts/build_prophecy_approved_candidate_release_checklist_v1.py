#!/usr/bin/env python3
"""Build release checklist for prophecy APPROVED_CANDIDATE governance."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"

DEFAULT_CANDIDATE = ART / "prophecy_track_a_candidate_v1_latest.json"
DEFAULT_LOCK = ART / "prophecy_manual_promotion_decision_lock_v1_latest.json"
DEFAULT_GATE = ART / "prophecy_promotion_gates_v1_panel_calibrated_latest.json"
DEFAULT_LIVE_AB = ART / "prophecy_live_ab_summary_v1_latest.json"
DEFAULT_HUMAN_SIGNOFF = ART / "prophecy_release_human_signoff_v1_latest.json"
DEFAULT_OUT = ART / "prophecy_approved_candidate_release_checklist_v1_latest.json"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return obj if isinstance(obj, dict) else {}


def _task(task_id: str, title: str, required: bool, done: bool, action: str) -> dict[str, Any]:
    return {
        "id": task_id,
        "title": title,
        "required": required,
        "done": done,
        "action": action,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--candidate", type=Path, default=DEFAULT_CANDIDATE)
    ap.add_argument("--manual-lock", type=Path, default=DEFAULT_LOCK)
    ap.add_argument("--promotion-gate", type=Path, default=DEFAULT_GATE)
    ap.add_argument("--live-ab-summary", type=Path, default=DEFAULT_LIVE_AB)
    ap.add_argument("--human-signoff", type=Path, default=DEFAULT_HUMAN_SIGNOFF)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    candidate = _load_json(args.candidate)
    lock = _load_json(args.manual_lock)
    gate = _load_json(args.promotion_gate)
    live_ab = _load_json(args.live_ab_summary)
    human_signoff = _load_json(args.human_signoff)

    status = str(candidate.get("status") or "")
    lock_decision = str(lock.get("final_decision") or "")
    lock_constraints = lock.get("constraints") if isinstance(lock.get("constraints"), dict) else {}
    gate_ready = bool(gate.get("auto_promote_ready") is True)
    live_ab_ready = str(live_ab.get("status") or "") == "READY"
    human_signoff_ready = str(human_signoff.get("decision") or "").upper() == "APPROVED"

    tasks = [
        _task(
            "candidate-01",
            "APPROVED_CANDIDATE 상태 유지 확인",
            True,
            status == "APPROVED_CANDIDATE",
            "candidate 아티팩트 status를 APPROVED_CANDIDATE로 유지한다.",
        ),
        _task(
            "lock-01",
            "수동 승인 잠금 유효성 확인",
            True,
            lock_decision == "approved",
            "manual promotion lock final_decision=approved 및 reviewer/decision_note를 확인한다.",
        ),
        _task(
            "bulkhead-01",
            "자동 브리지/자동 라이브 금지 유지",
            True,
            (lock_constraints.get("track_b_to_a_auto_bridge") is False)
            and (lock_constraints.get("live_trigger_auto_enabled") is False),
            "constraints에서 auto_bridge/live_trigger를 false로 유지한다.",
        ),
        _task(
            "gate-01",
            "패널 게이트 스냅샷 유효성 점검",
            True,
            gate_ready,
            "promotion gate auto_promote_ready=true 스냅샷을 릴리즈 패킷에 첨부한다.",
        ),
        _task(
            "ops-01",
            "운영 A/B 요약 첨부",
            True,
            live_ab_ready,
            "live AB summary status=READY 및 최신 KPI 스냅샷 경로를 sign-off에 첨부한다.",
        ),
        _task(
            "human-01",
            "릴리즈별 human review 체크포인트",
            True,
            human_signoff_ready,
            "릴리즈마다 human reviewer, evidence bundle, rollback trigger를 기록한 승인 이벤트를 남긴다.",
        ),
    ]

    required_total = sum(1 for t in tasks if t["required"])
    completed_total = sum(1 for t in tasks if t["required"] and t["done"])
    ready_for_release_signoff = required_total == completed_total

    out = {
        "schema": "prophecy_approved_candidate_release_checklist_v1",
        "generated_at_utc": _now(),
        "research_only": True,
        "track": "prophecy",
        "inputs": {
            "candidate": str(args.candidate).replace("\\", "/"),
            "manual_lock": str(args.manual_lock).replace("\\", "/"),
            "promotion_gate": str(args.promotion_gate).replace("\\", "/"),
            "live_ab_summary": str(args.live_ab_summary).replace("\\", "/"),
            "human_signoff": str(args.human_signoff).replace("\\", "/"),
        },
        "current_status": {
            "candidate_status": status or "MISSING",
            "manual_lock_final_decision": lock_decision or "MISSING",
            "auto_promote_ready": gate.get("auto_promote_ready"),
            "live_ab_status": live_ab.get("status") or "MISSING",
            "human_signoff_decision": human_signoff.get("decision") or "MISSING",
        },
        "checklist": tasks,
        "summary": {
            "required_total": required_total,
            "completed_total": completed_total,
            "ready_for_release_signoff": ready_for_release_signoff,
            "next_action": "human-01 수행 후 release sign-off 이벤트 기록"
            if not ready_for_release_signoff
            else "release sign-off 가능",
        },
        "notes_ko": [
            "APPROVED_CANDIDATE는 운영 배포 자동승격 권한이 아니다.",
            "모든 릴리즈는 human review 이벤트를 별도 기록해야 한다.",
        ],
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.out}")
    print(f"ready_for_release_signoff={ready_for_release_signoff}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
