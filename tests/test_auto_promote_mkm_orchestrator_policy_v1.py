from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _write_json(path: Path, doc: dict) -> None:
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")


def test_auto_promote_applies_target_after_min_streak(tmp_path: Path) -> None:
    stability = {
        "schema": "mkm_orchestrator_go_stability_v1",
        "transition": "GO->GO",
        "down_transition_detected": False,
        "go_stable": True,
    }
    policy = {
        "schema": "mkm_global_orchestrator_policy_v1",
        "decision_policy": {
            "go_confidence_cut": 0.70,
            "go_direction_abs_cut": 0.25,
            "hold_confidence_cut": 0.35,
            "hold_direction_abs_cut": 0.1,
            "fail_closed_action": "HOLD",
        },
    }
    streak = {
        "schema": "mkm_orchestrator_go_streak_v1",
        "go_streak": 2,
    }
    stability_path = tmp_path / "stability.json"
    policy_path = tmp_path / "policy.json"
    streak_path = tmp_path / "streak.json"
    out_path = tmp_path / "out.json"
    _write_json(stability_path, stability)
    _write_json(policy_path, policy)
    _write_json(streak_path, streak)

    cp = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "auto_promote_mkm_orchestrator_policy_v1.py"),
            "--stability-json",
            str(stability_path),
            "--policy-json",
            str(policy_path),
            "--streak-json",
            str(streak_path),
            "--output-json",
            str(out_path),
            "--min-go-streak",
            "3",
            "--target-profile",
            "prod_conditional_go",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert cp.returncode == 0
    out = json.loads(out_path.read_text(encoding="utf-8"))
    assert out["current_go_streak"] == 3
    assert out["promotion_applied"] is True
    assert out["action"] == "apply_profile"

    applied_policy = json.loads(policy_path.read_text(encoding="utf-8"))
    dp = applied_policy["decision_policy"]
    assert dp["go_confidence_cut"] == 0.53
    assert dp["go_direction_abs_cut"] == 0.14


def test_auto_promote_resets_streak_on_down_transition(tmp_path: Path) -> None:
    stability = {
        "schema": "mkm_orchestrator_go_stability_v1",
        "transition": "GO->WATCH",
        "down_transition_detected": True,
        "go_stable": False,
    }
    policy = {"schema": "mkm_global_orchestrator_policy_v1", "decision_policy": {"go_confidence_cut": 0.53}}
    streak = {"schema": "mkm_orchestrator_go_streak_v1", "go_streak": 5}
    stability_path = tmp_path / "stability.json"
    policy_path = tmp_path / "policy.json"
    streak_path = tmp_path / "streak.json"
    out_path = tmp_path / "out.json"
    _write_json(stability_path, stability)
    _write_json(policy_path, policy)
    _write_json(streak_path, streak)

    cp = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "auto_promote_mkm_orchestrator_policy_v1.py"),
            "--stability-json",
            str(stability_path),
            "--policy-json",
            str(policy_path),
            "--streak-json",
            str(streak_path),
            "--output-json",
            str(out_path),
            "--min-go-streak",
            "3",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert cp.returncode == 0
    out = json.loads(out_path.read_text(encoding="utf-8"))
    assert out["current_go_streak"] == 0
    assert out["promotion_applied"] is False
    assert out["action"] == "none"
