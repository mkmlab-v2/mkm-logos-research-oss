#!/usr/bin/env python3
"""RQ-028/029/031 close candidate gate ([HYPO] · rq_close_allowed false unless human env)."""
from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONDITIONS = ROOT / "experiments/a_code_12ai_v2/specs/a_code_rq_close_conditions_v1.json"
DEFAULT_ARCHIVE = ROOT / "reports/a_code_governor_signoff_archive_pack_v1_latest.json"
DEFAULT_LANE_GATE = ROOT / "reports/a_code_operator_assist_lane_gate_v1_latest.json"
DEFAULT_POINTER = ROOT / "reports/a_code_constitution_pointer_row_check_v1_latest.json"
DEFAULT_SMOKE = ROOT / "scripts/Invoke-ACodeGovernorSmoke_v1.ps1"
DEFAULT_OUT = ROOT / "reports/a_code_rq_close_gate_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _human_close_approved() -> bool:
    raw = os.getenv("MKM_ACODE_RQ_CLOSE_HUMAN_APPROVED", "").strip().lower()
    return raw in ("1", "true", "yes", "on")


def evaluate_gate(
    *,
    archive: dict[str, Any],
    lane_gate: dict[str, Any],
    pointer: dict[str, Any],
    smoke_script_exists: bool,
    human_close_approved: bool,
) -> dict[str, Any]:
    checks = {
        "conditions_spec_present": True,
        "archive_ready": archive.get("archive_ready") is True,
        "archive_rq_close_blocked": archive.get("rq_close_allowed") is False,
        "operator_lane_gate_pass": (lane_gate.get("summary") or {}).get("decision") == "PASS_OPERATOR_ASSIST",
        "pointer_row_pass": (pointer.get("summary") or {}).get("decision") == "PASS_POINTER_ROW",
        "smoke_script_present": smoke_script_exists,
        "track_wall_no_auto_promotion": archive.get("track_a_auto_promotion") is False,
    }
    pass_count = sum(1 for v in checks.values() if v)
    total = len(checks)

    mechanical_close_candidate = all(checks.values())
    rq_close_allowed = mechanical_close_candidate and human_close_approved

    if rq_close_allowed:
        decision = "CLOSE_CANDIDATE_HUMAN_APPROVED"
    elif mechanical_close_candidate:
        decision = "CLOSE_CANDIDATE_AWAIT_HUMAN"
    else:
        decision = "HOLD_RESEARCH"

    return {
        "schema": "a_code_rq_close_gate_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "rq_ids": ["RQ-028", "RQ-029", "RQ-031"],
        "hypothesis_tier": "B",
        "research_only": True,
        "summary": {
            "decision": decision,
            "pass_count": pass_count,
            "total": total,
            "mechanical_close_candidate": mechanical_close_candidate,
            "rq_close_allowed": rq_close_allowed,
            "human_close_approved": human_close_approved,
        },
        "checks": checks,
        "track_wall": {
            "track_a_auto_promotion": False,
            "live_trading_auto_trigger": False,
            "agent_auto_rq_closed_forbidden": True,
        },
        "conditions_spec": str(DEFAULT_CONDITIONS.relative_to(ROOT)).replace("\\", "/"),
        "operator_hint_ko": (
            "기계적 CLOSED 후보 충족 — 지휘관 RQ 이관 승인·RESEARCH 수동 갱신 필요 [HYPO]"
            if decision == "CLOSE_CANDIDATE_AWAIT_HUMAN"
            else (
                "RQ CLOSED human gate 통과 — RESEARCH 수동 이관만 허용 [HYPO]"
                if decision == "CLOSE_CANDIDATE_HUMAN_APPROVED"
                else "RQ CLOSED 후보 미충족 — 연구 샌드박스 유지 [HYPO]"
            )
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--conditions", type=Path, default=DEFAULT_CONDITIONS)
    parser.add_argument("--archive", type=Path, default=DEFAULT_ARCHIVE)
    parser.add_argument("--lane-gate", type=Path, default=DEFAULT_LANE_GATE)
    parser.add_argument("--pointer", type=Path, default=DEFAULT_POINTER)
    parser.add_argument("--smoke-script", type=Path, default=DEFAULT_SMOKE)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--strict", action="store_true", help="exit 1 unless mechanical_close_candidate")
    args = parser.parse_args()

    if not args.conditions.is_file():
        raise SystemExit(f"missing conditions spec: {args.conditions}")

    report = evaluate_gate(
        archive=_read(args.archive),
        lane_gate=_read(args.lane_gate),
        pointer=_read(args.pointer),
        smoke_script_exists=args.smoke_script.is_file(),
        human_close_approved=_human_close_approved(),
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    s = report["summary"]
    print(
        f"OK: {args.out} decision={s['decision']} "
        f"mechanical={s['mechanical_close_candidate']} rq_close_allowed={s['rq_close_allowed']}"
    )
    if args.strict and not s["mechanical_close_candidate"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
