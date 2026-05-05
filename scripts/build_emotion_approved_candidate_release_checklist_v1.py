#!/usr/bin/env python3
"""Build release checklist for emotion-state APPROVED_CANDIDATE governance."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"

DEFAULT_CANDIDATE = ART / "emotion_state_track_a_candidate_latest.json"
DEFAULT_LOCK = ART / "emotion_state_manual_promotion_decision_lock_latest.json"
DEFAULT_GATE = ART / "emotion_state_promotion_gate_latest.json"
DEFAULT_HUMAN_SIGNOFF = ART / "emotion_state_release_human_signoff_latest.json"
DEFAULT_OUT = ART / "emotion_state_approved_candidate_release_checklist_latest.json"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        obj = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return {}
    return obj if isinstance(obj, dict) else {}


def _task(task_id: str, title: str, required: bool, done: bool, action: str) -> dict[str, Any]:
    return {"id": task_id, "title": title, "required": required, "done": done, "action": action}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--candidate", type=Path, default=DEFAULT_CANDIDATE)
    ap.add_argument("--manual-lock", type=Path, default=DEFAULT_LOCK)
    ap.add_argument("--promotion-gate", type=Path, default=DEFAULT_GATE)
    ap.add_argument("--human-signoff", type=Path, default=DEFAULT_HUMAN_SIGNOFF)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    candidate = _load_json(args.candidate)
    lock = _load_json(args.manual_lock)
    gate = _load_json(args.promotion_gate)
    signoff = _load_json(args.human_signoff)

    candidate_ok = str(candidate.get("status") or "") == "APPROVED_CANDIDATE"
    lock_ok = str(lock.get("final_decision") or "") == "approved"
    constraints = lock.get("constraints") if isinstance(lock.get("constraints"), dict) else {}
    bulkhead_ok = (
        constraints.get("track_b_to_a_auto_bridge") is False
        and constraints.get("live_trigger_auto_enabled") is False
    )
    gate_ok = str(gate.get("decision") or "") == "PROMOTION_CANDIDATE"
    signoff_ok = str(signoff.get("decision") or "").upper() == "APPROVED"

    tasks = [
        _task("candidate-01", "APPROVED_CANDIDATE 상태 확인", True, candidate_ok, "candidate status 확인"),
        _task("lock-01", "수동 승인 잠금 확인", True, lock_ok, "manual lock final_decision=approved 확인"),
        _task("bulkhead-01", "자동 브리지/라이브 금지 유지", True, bulkhead_ok, "constraints false 유지"),
        _task("gate-01", "승격 게이트 후보 상태 확인", True, gate_ok, "promotion gate decision 확인"),
        _task("human-01", "릴리즈별 human signoff 기록", True, signoff_ok, "release human signoff APPROVED 기록"),
    ]

    required_total = sum(1 for t in tasks if t["required"])
    completed_total = sum(1 for t in tasks if t["required"] and t["done"])
    ready = required_total == completed_total

    out = {
        "schema": "emotion_state_approved_candidate_release_checklist_v1",
        "generated_at_utc": _now(),
        "track": "emotion_state_control",
        "inputs": {
            "candidate": str(args.candidate).replace("\\", "/"),
            "manual_lock": str(args.manual_lock).replace("\\", "/"),
            "promotion_gate": str(args.promotion_gate).replace("\\", "/"),
            "human_signoff": str(args.human_signoff).replace("\\", "/"),
        },
        "checklist": tasks,
        "summary": {
            "required_total": required_total,
            "completed_total": completed_total,
            "ready_for_release_signoff": ready,
        },
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "output_json": str(args.out), "ready_for_release_signoff": ready}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
