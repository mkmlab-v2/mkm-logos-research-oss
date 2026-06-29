#!/usr/bin/env python3
"""RQ-029: evaluate A-code promotion checklist mechanical readiness ([HYPO])."""
from __future__ import annotations

import argparse
import importlib.util
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CHECKLIST = ROOT / "experiments/a_code_12ai_v2/specs/a_code_promotion_checklist_v1.json"
DEFAULT_EVIDENCE = ROOT / "reports/a_code_governor_evidence_pack_v1_latest.json"
DEFAULT_GATE = ROOT / "reports/a_code_governor_promotion_gate_v1_latest.json"
DEFAULT_REPLAY = ROOT / "reports/a_code_governor_knob_multiday_replay_v1_latest.json"
DEFAULT_OUT = ROOT / "reports/a_code_promotion_checklist_readiness_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _import_validate_profile():
    path = ROOT / "scripts/validate_commander_profile_v1.py"
    spec = importlib.util.spec_from_file_location("validate_commander_profile", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _import_signoff_modules():
    resolve_path = ROOT / "scripts/a_code_commander_signoff_resolve_v1.py"
    validate_path = ROOT / "scripts/validate_commander_a_code_signoff_v1.py"
    spec_r = importlib.util.spec_from_file_location("a_code_signoff_resolve", resolve_path)
    spec_v = importlib.util.spec_from_file_location("validate_commander_a_code_signoff", validate_path)
    assert spec_r and spec_r.loader and spec_v and spec_v.loader
    resolver = importlib.util.module_from_spec(spec_r)
    validator = importlib.util.module_from_spec(spec_v)
    spec_r.loader.exec_module(resolver)
    spec_v.loader.exec_module(validator)
    return resolver, validator


def _manual_item_status(item_id: str, signoff_info: dict[str, Any]) -> str:
    if not signoff_info.get("present"):
        return "MANUAL"
    if not signoff_info.get("ok"):
        return "FAIL"
    attest = signoff_info.get("attestations") or {}
    if item_id == "human_commander_signoff":
        if signoff_info.get("approved") and attest.get("human_commander_signoff") is True:
            return "PASS"
        return "PENDING" if signoff_info.get("present") else "MANUAL"
    if item_id in {"separate_rq_from_rq026_closed", "no_track_a_live_auto_merge"}:
        return "PASS" if attest.get(item_id) is True else "PENDING"
    return "MANUAL"


def _matrix_validate_ok() -> bool:
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts/validate_a_code_12ai_matrix_v2.py")],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    return proc.returncode == 0


def _pytest_a_code_ok() -> bool | None:
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/test_a_code_12ai_matrix_v2.py", "-q", "--tb=no"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    return proc.returncode == 0


def evaluate_readiness(
    *,
    checklist: dict[str, Any],
    evidence: dict[str, Any],
    gate: dict[str, Any],
    replay: dict[str, Any],
    run_pytest: bool = False,
) -> dict[str, Any]:
    validator = _import_validate_profile()
    resolver_path = ROOT / "scripts/a_code_commander_profile_resolve_v1.py"
    spec = importlib.util.spec_from_file_location("a_code_profile_resolve", resolver_path)
    assert spec and spec.loader
    resolver = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(resolver)
    profile_path, profile_source = resolver.resolve_commander_profile_path(None)
    profile_doc = _read(profile_path)
    profile_errors = validator.validate_profile_doc(profile_doc)

    signoff_resolver, signoff_validator = _import_signoff_modules()
    signoff_path, signoff_source = signoff_resolver.resolve_commander_a_code_signoff_path(None)
    if signoff_path is None:
        signoff_info: dict[str, Any] = {
            "present": False,
            "ok": True,
            "approved": False,
            "source": signoff_source,
            "human_signoff_status": "ABSENT",
            "attestations": {},
        }
    else:
        signoff_doc = _read(signoff_path)
        signoff_errors = signoff_validator.validate_signoff_doc(signoff_doc)
        signoff_info = {
            "present": True,
            "source": signoff_source,
            "signoff_path": str(signoff_path.relative_to(ROOT)).replace("\\", "/"),
            **signoff_validator.signoff_summary(signoff_doc, errors=signoff_errors),
        }

    holdout_cons = (
        (replay.get("eval_axes") or {}).get("orchestration_consistency") or {}
    ).get("holdout")
    gate_summary = gate.get("summary") or {}

    auto_results = {
        "profile_schema_valid": not profile_errors,
        "matrix_validate_green": _matrix_validate_ok(),
        "multiday_holdout_consistency": float(holdout_cons or 0) >= 1.0,
        "governor_gate_watch_continue": gate_summary.get("decision") == "WATCH_CONTINUE",
        "evidence_pack_status_watch": evidence.get("status") == "WATCH",
        "pytest_a_code_suite_green": _pytest_a_code_ok() if run_pytest else None,
    }

    items_out: list[dict[str, Any]] = []
    required_ids = [
        str(it.get("id"))
        for it in checklist.get("items") or []
        if isinstance(it, dict) and it.get("required_for_mechanical_watch")
    ]
    for item in checklist.get("items") or []:
        if not isinstance(item, dict):
            continue
        item_id = str(item.get("id") or "")
        auto = bool(item.get("auto_verifiable"))
        if auto:
            actual = auto_results.get(item_id)
            status = "PASS" if actual is True else ("SKIP" if actual is None else "FAIL")
        else:
            status = _manual_item_status(item_id, signoff_info)
        items_out.append(
            {
                "id": item_id,
                "label_ko": item.get("label_ko"),
                "auto_verifiable": auto,
                "required_for_mechanical_watch": item.get("required_for_mechanical_watch"),
                "status": status,
            }
        )

    required_pass = all(
        next((i["status"] for i in items_out if i["id"] == rid), "FAIL") == "PASS"
        for rid in required_ids
    )
    mechanical_ready = required_pass and gate_summary.get("decision") == "WATCH_CONTINUE"
    manual_pass_ids = {
        "human_commander_signoff",
        "separate_rq_from_rq026_closed",
        "no_track_a_live_auto_merge",
    }
    manual_all_pass = all(
        next((i["status"] for i in items_out if i["id"] == mid), "MANUAL") == "PASS"
        for mid in manual_pass_ids
    )
    promotion_discussion_eligible = mechanical_ready and signoff_info.get("approved") is True and manual_all_pass

    return {
        "schema": "a_code_promotion_checklist_readiness_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "rq_id": checklist.get("rq_id") or "RQ-029",
        "parent_rq": checklist.get("parent_rq") or "RQ-028",
        "hypothesis_tier": "B",
        "research_only": True,
        "human_sign_off_required": True,
        "profile_source": profile_source,
        "signoff": signoff_info,
        "summary": {
            "mechanical_ready": mechanical_ready,
            "required_auto_pass": required_pass,
            "gate_decision": gate_summary.get("decision"),
            "evidence_status": evidence.get("status"),
            "human_signoff_status": signoff_info.get("human_signoff_status"),
            "promotion_discussion_eligible": promotion_discussion_eligible,
            "outcome_class": "watch_candidate" if mechanical_ready else "hold_research",
            "operator_hint_ko": (
                "기계 준비+human sign-off 완료 — 별 RQ 승격 토의만 가능 [HYPO·non-gating]"
                if promotion_discussion_eligible
                else (
                    "mechanical_ready 관측 — human sign-off·별 RQ 없이 승격 금지 [HYPO]"
                    if mechanical_ready
                    else "A-code governor 연구 게이트 미충족 — 번들 재실행 [HYPO]"
                )
            ),
        },
        "items": items_out,
        "track_wall": {
            "track_a_auto_promotion": False,
            "live_trading_auto_trigger": False,
            "note_ko": "mechanical_ready=true여도 human sign-off·별 RQ 없이 승격 금지",
        },
        "sources": {
            "checklist": str(DEFAULT_CHECKLIST.relative_to(ROOT)).replace("\\", "/"),
            "evidence_pack": str(DEFAULT_EVIDENCE.relative_to(ROOT)).replace("\\", "/"),
            "promotion_gate": str(DEFAULT_GATE.relative_to(ROOT)).replace("\\", "/"),
            "multiday_replay": str(DEFAULT_REPLAY.relative_to(ROOT)).replace("\\", "/"),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="A-code promotion checklist readiness")
    parser.add_argument("--checklist", type=Path, default=DEFAULT_CHECKLIST)
    parser.add_argument("--evidence", type=Path, default=DEFAULT_EVIDENCE)
    parser.add_argument("--gate", type=Path, default=DEFAULT_GATE)
    parser.add_argument("--replay", type=Path, default=DEFAULT_REPLAY)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--run-pytest", action="store_true")
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()

    checklist = _read(args.checklist)
    if checklist.get("schema") != "a_code_promotion_checklist_v1":
        raise SystemExit(f"invalid checklist: {args.checklist}")

    report = evaluate_readiness(
        checklist=checklist,
        evidence=_read(args.evidence),
        gate=_read(args.gate),
        replay=_read(args.replay),
        run_pytest=args.run_pytest,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    ready = report["summary"]["mechanical_ready"]
    print(f"OK: {args.out} mechanical_ready={ready}")
    if args.strict and not ready:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
