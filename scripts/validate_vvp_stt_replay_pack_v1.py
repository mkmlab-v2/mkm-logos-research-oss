#!/usr/bin/env python3
"""Validate VVP-STT gate policy example and replay test pack consistency."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_POLICY = ROOT / "docs/final/artifacts/vvp_stt_gate_policy_v1.example.json"
DEFAULT_REPLAY = ROOT / "docs/final/artifacts/vvp_stt_replay_test_pack_v1.draft.json"
DEFAULT_REASON = ROOT / "docs/final/artifacts/vvp_stt_reason_codes_v1.draft.json"
DEFAULT_OUT = ROOT / "reports/vvp_stt_replay_validation_v1_latest.json"

ALLOWED_DECISIONS = {"ALLOW", "STEP_UP", "BLOCK", "HOLD_REVIEW"}
ALLOWED_EXITS = {0, 1, 2}


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        obj = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return {}
    return obj if isinstance(obj, dict) else {}


def _get_reason_code_set(reason_doc: dict[str, Any]) -> set[str]:
    codes: set[str] = set()
    for row in (reason_doc.get("reason_codes") or []):
        if isinstance(row, dict):
            code = row.get("code")
            if isinstance(code, str) and code.strip():
                codes.add(code.strip())
    return codes


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--policy-json", type=Path, default=DEFAULT_POLICY)
    ap.add_argument("--replay-json", type=Path, default=DEFAULT_REPLAY)
    ap.add_argument("--reason-json", type=Path, default=DEFAULT_REASON)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    policy = _read_json(args.policy_json)
    replay = _read_json(args.replay_json)
    reason = _read_json(args.reason_json)
    reason_codes = _get_reason_code_set(reason)

    checks: dict[str, bool] = {}
    issues: list[str] = []

    # Policy-level checks
    checks["policy_schema_ok"] = policy.get("schema") == "vvp_stt_gate_policy_v1"
    checks["policy_track_wall_ok"] = policy.get("track_wall") == "FAIL-COMP-004"
    checks["policy_research_only_true"] = bool(((policy.get("governance") or {}).get("research_only"))) is True
    checks["policy_no_auto_bridge"] = bool(((policy.get("governance") or {}).get("allow_track_a_auto_bridge"))) is False

    decisions = set((((policy.get("decision_contract") or {}).get("allowed_decisions")) or []))
    checks["policy_decision_set_complete"] = decisions == ALLOWED_DECISIONS

    exit_obj = ((policy.get("decision_contract") or {}).get("exit_codes")) or {}
    checks["policy_exit_contract_ok"] = (
        exit_obj.get("pass") == 0
        and exit_obj.get("deny") == 1
        and exit_obj.get("governance_invalid") == 2
    )

    anomaly = policy.get("anomaly_policy") or {}
    step_up = anomaly.get("step_up_threshold")
    block = anomaly.get("block_threshold")
    checks["policy_threshold_order_ok"] = isinstance(step_up, (int, float)) and isinstance(block, (int, float)) and block > step_up
    if not checks["policy_threshold_order_ok"]:
        issues.append("anomaly_policy.block_threshold must be greater than step_up_threshold")

    # Replay pack checks
    checks["replay_schema_ok"] = replay.get("schema") == "vvp_stt_replay_test_pack_v1"
    checks["replay_track_wall_ok"] = replay.get("track_wall") == "FAIL-COMP-004"
    cases = replay.get("cases") or []
    checks["replay_cases_non_empty"] = isinstance(cases, list) and len(cases) > 0

    case_errors: list[dict[str, Any]] = []
    if isinstance(cases, list):
        for row in cases:
            if not isinstance(row, dict):
                case_errors.append({"case_id": None, "error": "case is not an object"})
                continue
            case_id = row.get("case_id")
            exp = row.get("expected") or {}
            decision = exp.get("decision")
            reason_code = exp.get("reason_code")
            gate_exit = exp.get("gate_exit_code")

            if decision not in ALLOWED_DECISIONS:
                case_errors.append({"case_id": case_id, "error": f"invalid decision: {decision}"})
            if gate_exit not in ALLOWED_EXITS:
                case_errors.append({"case_id": case_id, "error": f"invalid gate_exit_code: {gate_exit}"})

            if decision == "ALLOW":
                # allow path can omit reason_code in this draft contract
                if reason_code is not None and reason_code not in reason_codes:
                    case_errors.append({"case_id": case_id, "error": f"unknown allow reason_code: {reason_code}"})
            else:
                if not isinstance(reason_code, str) or not reason_code.strip():
                    case_errors.append({"case_id": case_id, "error": "missing reason_code for non-ALLOW case"})
                elif reason_code not in reason_codes:
                    case_errors.append({"case_id": case_id, "error": f"unknown reason_code: {reason_code}"})

    checks["replay_case_contract_ok"] = len(case_errors) == 0
    if case_errors:
        issues.append(f"replay case contract errors: {len(case_errors)}")

    ok = all(checks.values())
    out_doc = {
        "schema": "vvp_stt_replay_validation_v1",
        "ok": ok,
        "inputs": {
            "policy_json": str(args.policy_json),
            "replay_json": str(args.replay_json),
            "reason_json": str(args.reason_json),
        },
        "checks": checks,
        "summary": {
            "case_count": len(cases) if isinstance(cases, list) else 0,
            "known_reason_code_count": len(reason_codes),
            "case_error_count": len(case_errors),
        },
        "case_errors": case_errors,
        "issues": issues,
    }
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(out_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": ok, "out": str(args.out_json)}, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

