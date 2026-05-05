#!/usr/bin/env python3
"""Build final checklist before enabling live trading for prophecy track."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"

DEFAULT_RELEASE_PACKET = ART / "prophecy_release_signoff_packet_v1_latest.json"
DEFAULT_HUMAN_SIGNOFF = ART / "prophecy_release_human_signoff_v1_latest.json"
DEFAULT_LIVE_AB = ART / "prophecy_live_ab_summary_v1_latest.json"
DEFAULT_LIVE_EVENT = ART / "prophecy_live_enable_event_v1_latest.json"
DEFAULT_ROLLBACK_POLICY = ART / "prophecy_live_rollback_policy_v1_latest.json"
DEFAULT_OUT = ART / "prophecy_live_enable_checklist_v1_latest.json"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return obj if isinstance(obj, dict) else {}


def _task(task_id: str, title: str, done: bool, action: str) -> dict[str, Any]:
    return {
        "id": task_id,
        "required": True,
        "title": title,
        "done": done,
        "action": action,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--release-packet", type=Path, default=DEFAULT_RELEASE_PACKET)
    ap.add_argument("--human-signoff", type=Path, default=DEFAULT_HUMAN_SIGNOFF)
    ap.add_argument("--live-ab-summary", type=Path, default=DEFAULT_LIVE_AB)
    ap.add_argument("--live-enable-event", type=Path, default=DEFAULT_LIVE_EVENT)
    ap.add_argument("--rollback-policy", type=Path, default=DEFAULT_ROLLBACK_POLICY)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    packet = _load(args.release_packet)
    signoff = _load(args.human_signoff)
    live_ab = _load(args.live_ab_summary)
    live_event = _load(args.live_enable_event)
    rollback = _load(args.rollback_policy)

    packet_ready = str(packet.get("status") or "") == "READY_FOR_RELEASE_SIGNOFF"
    signoff_approved = str(signoff.get("decision") or "").upper() == "APPROVED"
    live_ab_ready = str(live_ab.get("status") or "") == "READY"
    live_event_approved = str(live_event.get("decision") or "").upper() == "APPROVED"
    rollback_defined = str(rollback.get("schema") or "") == "prophecy_live_rollback_policy_v1"

    tasks = [
        _task(
            "live-01",
            "릴리즈 패킷 READY 확인",
            packet_ready,
            "prophecy_release_signoff_packet_v1_latest.json 상태가 READY_FOR_RELEASE_SIGNOFF인지 확인",
        ),
        _task(
            "live-02",
            "운영자 human sign-off 승인 확인",
            signoff_approved,
            "prophecy_release_human_signoff_v1_latest.json decision=APPROVED 확인",
        ),
        _task(
            "live-03",
            "운영 A/B 상태 READY 확인",
            live_ab_ready,
            "prophecy_live_ab_summary_v1_latest.json status=READY 확인",
        ),
        _task(
            "live-04",
            "live enable 별도 승인 이벤트 기록",
            live_event_approved,
            "실매매 반영 승인자/승인시각/근거/롤백 트리거를 별도 live-enable 이벤트로 기록",
        ),
        _task(
            "live-05",
            "롤백 조건 사전 고정",
            rollback_defined,
            "손실 임계/게이트 실패/데이터 결손 발생 시 즉시 live disable 및 이전 설정으로 복귀 절차 고정",
        ),
    ]

    required_total = len(tasks)
    completed_total = sum(1 for t in tasks if t["done"])
    ready_to_enable_live = required_total == completed_total

    out = {
        "schema": "prophecy_live_enable_checklist_v1",
        "generated_at_utc": _now(),
        "track": "prophecy",
        "research_only": True,
        "inputs": {
            "release_packet": str(args.release_packet).replace("\\", "/"),
            "human_signoff": str(args.human_signoff).replace("\\", "/"),
            "live_ab_summary": str(args.live_ab_summary).replace("\\", "/"),
            "live_enable_event": str(args.live_enable_event).replace("\\", "/"),
            "rollback_policy": str(args.rollback_policy).replace("\\", "/"),
        },
        "current_status": {
            "release_packet_status": packet.get("status") or "MISSING",
            "human_signoff_decision": signoff.get("decision") or "MISSING",
            "live_ab_status": live_ab.get("status") or "MISSING",
            "live_enable_event_decision": live_event.get("decision") or "MISSING",
            "rollback_policy_schema": rollback.get("schema") or "MISSING",
        },
        "checklist": tasks,
        "summary": {
            "required_total": required_total,
            "completed_total": completed_total,
            "ready_to_enable_live": ready_to_enable_live,
            "next_action": "live-04/live-05 승인 이벤트 및 롤백 조건 기록 후 재평가",
        },
        "constraints": {
            "auto_enable_live": False,
            "human_approval_mandatory": True,
        },
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.out}")
    print(f"ready_to_enable_live={ready_to_enable_live}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
