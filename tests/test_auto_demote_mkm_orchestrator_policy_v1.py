from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _write_json(path: Path, doc: dict) -> None:
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")


def test_auto_demote_applies_research_profile_on_down_transition(tmp_path: Path) -> None:
    stability = {
        "schema": "mkm_orchestrator_go_stability_v1",
        "transition": "GO->WATCH",
        "down_transition_detected": True,
    }
    policy = {
        "schema": "mkm_global_orchestrator_policy_v1",
        "decision_policy": {
            "go_confidence_cut": 0.53,
            "go_direction_abs_cut": 0.14,
            "hold_confidence_cut": 0.35,
            "hold_direction_abs_cut": 0.1,
            "fail_closed_action": "HOLD",
        },
    }
    stability_path = tmp_path / "stability.json"
    policy_path = tmp_path / "policy.json"
    out_path = tmp_path / "out.json"
    _write_json(stability_path, stability)
    _write_json(policy_path, policy)

    cp = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "auto_demote_mkm_orchestrator_policy_v1.py"),
            "--stability-json",
            str(stability_path),
            "--policy-json",
            str(policy_path),
            "--output-json",
            str(out_path),
            "--target-profile",
            "research",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert cp.returncode == 0
    out = json.loads(out_path.read_text(encoding="utf-8"))
    assert out["down_transition_detected"] is True
    assert out["demotion_applied"] is True
    assert out["action"] == "apply_profile"

    applied_policy = json.loads(policy_path.read_text(encoding="utf-8"))
    dp = applied_policy["decision_policy"]
    assert dp["go_confidence_cut"] == 0.70
    assert dp["go_direction_abs_cut"] == 0.25


def test_auto_demote_noop_when_no_down_transition(tmp_path: Path) -> None:
    stability = {
        "schema": "mkm_orchestrator_go_stability_v1",
        "transition": "GO->GO",
        "down_transition_detected": False,
    }
    policy = {
        "schema": "mkm_global_orchestrator_policy_v1",
        "decision_policy": {
            "go_confidence_cut": 0.53,
            "go_direction_abs_cut": 0.14,
            "hold_confidence_cut": 0.35,
            "hold_direction_abs_cut": 0.1,
            "fail_closed_action": "HOLD",
        },
    }
    stability_path = tmp_path / "stability.json"
    policy_path = tmp_path / "policy.json"
    out_path = tmp_path / "out.json"
    _write_json(stability_path, stability)
    _write_json(policy_path, policy)

    cp = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "auto_demote_mkm_orchestrator_policy_v1.py"),
            "--stability-json",
            str(stability_path),
            "--policy-json",
            str(policy_path),
            "--output-json",
            str(out_path),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert cp.returncode == 0
    out = json.loads(out_path.read_text(encoding="utf-8"))
    assert out["down_transition_detected"] is False
    assert out["demotion_applied"] is False
    assert out["action"] == "none"
