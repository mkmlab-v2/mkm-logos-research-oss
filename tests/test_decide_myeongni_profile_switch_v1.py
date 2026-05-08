from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "decide_myeongni_profile_switch_v1.py"


def _run(summary: dict, policy: dict, tmp_path: Path) -> dict:
    summary_path = tmp_path / "summary.json"
    policy_path = tmp_path / "policy.json"
    out_path = tmp_path / "out.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    policy_path.write_text(json.dumps(policy, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    cp = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--summary-json",
            str(summary_path),
            "--policy-json",
            str(policy_path),
            "--output-json",
            str(out_path),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert cp.returncode == 0, cp.stderr + cp.stdout
    return json.loads(out_path.read_text(encoding="utf-8"))


def _policy() -> dict:
    return {
        "defaults": {"current_profile": "balanced", "target_profile_on_tie": "balanced"},
        "promote_to_attack_if": {
            "attack_direction_margin_gte": 0.0,
            "attack_confidence_margin_gte": 0.08,
            "require_attack_decision": "REDUCE",
            "require_balanced_not_reduce": True,
        },
        "demote_to_balanced_if": {
            "attack_direction_margin_lt": -0.03,
            "attack_confidence_margin_lt": 0.0,
            "or_attack_decision_not_reduce": True,
        },
    }


def test_decide_promotes_to_attack(tmp_path: Path):
    summary = {
        "mode": "both",
        "snapshot": {"decision_balanced": "WATCH", "decision_attack": "REDUCE"},
        "margins": {
            "balanced": {"direction_minus_reduce_cut": -0.19, "confidence_minus_reduce_cut": -0.04},
            "attack": {"direction_minus_reduce_cut": 0.01, "confidence_minus_reduce_cut": 0.11},
        },
    }
    out = _run(summary, _policy(), tmp_path)
    assert out["state"]["recommended_profile"] == "attack"
    assert out["state"]["action"] == "PROMOTE_TO_ATTACK"


def test_decide_demotes_to_balanced(tmp_path: Path):
    summary = {
        "mode": "attack",
        "snapshot": {"decision_balanced": None, "decision_attack": "WATCH"},
        "margins": {
            "balanced": None,
            "attack": {"direction_minus_reduce_cut": -0.05, "confidence_minus_reduce_cut": -0.01},
        },
    }
    out = _run(summary, _policy(), tmp_path)
    assert out["state"]["recommended_profile"] == "balanced"
    assert out["state"]["action"] == "DEMOTE_TO_BALANCED"
