#!/usr/bin/env python3
"""RQ-028 P7: reproducible A-code governor research evidence pack ([HYPO])."""
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
DEFAULT_OUT = ROOT / "reports/a_code_governor_evidence_pack_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(path)


def _import_validate_profile():
    path = ROOT / "scripts/validate_commander_profile_v1.py"
    spec = importlib.util.spec_from_file_location("validate_commander_profile", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import profile validator: {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _pytest_a_code_pass() -> bool | None:
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "tests/test_a_code_12ai_matrix_v2.py",
            "tests/test_a_code_governor_knob_sim_stub_v1.py",
            "tests/test_a_code_governor_knob_multiday_replay_v1.py",
            "tests/test_a_code_commander_profile_resolve_v1.py",
            "tests/test_a_code_governor_knob_evening_observation_v1.py",
            "tests/test_a_code_governor_promotion_gate_v1.py",
            "tests/test_a_code_evening_briefing_append_v1.py",
            "-q",
            "--tb=no",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode == 0:
        return True
    return False


def build_pack(*, run_pytest: bool = False) -> dict[str, Any]:
    art = {
        "matrix_example": ROOT / "experiments/a_code_12ai_v2/specs/a_code_12ai_matrix_v2.example.json",
        "eval_contract": ROOT / "experiments/a_code_12ai_v2/specs/a_code_eval_axes_contract_v2.json",
        "gate_thresholds": ROOT / "experiments/a_code_12ai_v2/specs/a_code_governor_promotion_gate_thresholds_v1.json",
        "multiday_replay": ROOT / "reports/a_code_governor_knob_multiday_replay_v1_latest.json",
        "promotion_gate": ROOT / "reports/a_code_governor_promotion_gate_v1_latest.json",
        "evening_observation": ROOT / "reports/a_code_governor_knob_evening_observation_v1_latest.json",
        "governor_sim": ROOT / "reports/a_code_governor_knob_sim_v1_latest.json",
    }

    validator = _import_validate_profile()
    resolver_mod_path = ROOT / "scripts/a_code_commander_profile_resolve_v1.py"
    spec = importlib.util.spec_from_file_location("a_code_profile_resolve", resolver_mod_path)
    assert spec and spec.loader
    resolver = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(resolver)
    profile_path, profile_source = resolver.resolve_commander_profile_path(None)
    profile_doc = _read(profile_path)
    profile_errors = validator.validate_profile_doc(profile_doc)
    profile_validation = {
        "ok": not profile_errors,
        "profile_path": _rel(profile_path),
        "profile_source": profile_source,
        "errors": profile_errors,
    }

    gate = _read(art["promotion_gate"])
    replay = _read(art["multiday_replay"])
    obs = _read(art["evening_observation"])
    gate_summary = gate.get("summary") or {}
    pytest_pass = _pytest_a_code_pass() if run_pytest else None

    mechanical_ok = (
        profile_validation["ok"]
        and gate_summary.get("decision") == "WATCH_CONTINUE"
        and bool(replay.get("research_only"))
    )

    return {
        "schema": "a_code_governor_evidence_pack_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "rq_id": "RQ-028",
        "hypothesis_tier": "B",
        "research_only": True,
        "human_sign_off_required": True,
        "track_a_auto_promotion": False,
        "live_trading_auto_trigger": False,
        "status": "WATCH" if mechanical_ok else "HOLD_RESEARCH",
        "gate_decision": gate_summary.get("decision"),
        "gate_pass_count": gate_summary.get("pass_count"),
        "gate_total": gate_summary.get("total"),
        "profile_validation": profile_validation,
        "pytest_a_code_suite_pass": pytest_pass,
        "artifacts": {
            **{key: _rel(path) for key, path in art.items()},
            "promotion_checklist": "experiments/a_code_12ai_v2/specs/a_code_promotion_checklist_v1.json",
            "checklist_readiness": "reports/a_code_promotion_checklist_readiness_v1_latest.json",
            "promotion_rq_readiness": "reports/a_code_promotion_rq_readiness_v1_latest.json",
            "operator_assist_lane": "docs/final/artifacts/a_code_operator_assist_lane_v1_latest.json",
            "operator_assist_lane_gate": "reports/a_code_operator_assist_lane_gate_v1_latest.json",
            "constitution_migration_draft": "docs/final/artifacts/a_code_constitution_worklist_migration_draft_v1.json",
            "trackc_ops_dashboard": "docs/final/artifacts/mkm_trackc_ops_dashboard_latest.json",
        },
        "rq031_operator_lane": {
            "rq_id": "RQ-031",
            "lane_artifact": "docs/final/artifacts/a_code_operator_assist_lane_v1_latest.json",
            "routine": "scripts/Run-ACodeOperatorAssistLaneRoutine_v1.ps1",
            "research_only": True,
            "non_gating": True,
        },
        "evidence_snapshot": {
            "n_session_days": replay.get("n_session_days"),
            "n_holdout_days": len(replay.get("holdout_dates") or []),
            "orchestration_consistency_holdout": (replay.get("eval_axes") or {})
            .get("orchestration_consistency", {})
            .get("holdout"),
            "evening_append_line": obs.get("evening_append_line"),
            "adjusted_knobs": obs.get("adjusted_knobs"),
        },
        "reproduction_commands": [
            "py scripts/validate_commander_profile_v1.py",
            "py scripts/validate_a_code_12ai_matrix_v2.py",
            "py scripts/build_a_code_governor_knob_multiday_replay_v1.py",
            "py scripts/check_a_code_governor_promotion_gate_v1.py",
            "py scripts/build_a_code_governor_knob_evening_observation_v1.py --session-date YYYY-MM-DD",
            "pwsh -File scripts/Run-ACodeGovernorResearchBundle_v1.ps1",
            "py -m pytest tests/test_a_code_*.py -q",
        ],
        "policy_pointers": {
            "operating_spec": "docs/final/protocols/A_CODE_12AI_AUTONOMOUS_OPERATING_SPEC_V2.md",
            "eval_contract": _rel(art["eval_contract"]),
            "public_facing": "docs/final/PUBLIC_FACING_SECURITY_AND_IP_COPY_CHECKLIST_V1.md",
        },
        "track_wall": {
            "note_ko": "evidence pack은 연구 증거 묶음. Track A·실매매·MS 승격 근거 아님.",
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Build A-code governor evidence pack v1")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--run-pytest", action="store_true", help="Run A-code pytest subset (slower)")
    args = parser.parse_args()

    pack = build_pack(run_pytest=args.run_pytest)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(pack, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"OK: {args.out} status={pack.get('status')} gate={pack.get('gate_decision')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
