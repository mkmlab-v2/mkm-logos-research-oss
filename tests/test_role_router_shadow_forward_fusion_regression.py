from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def test_revalidation_summary_selects_gate_pass_candidate() -> None:
    summary_path = ROOT / "docs" / "final" / "artifacts" / "prophecy_logos_revalidation_summary_latest.json"
    assert summary_path.is_file(), "Expected latest revalidation summary artifact to exist."

    summary = _read_json(summary_path)
    policy = ((summary.get("findings") or {}).get("router_selection_policy")) or {}
    assert policy.get("gate_pass_selected") is True
    assert policy.get("selection_mode") == "gate_pass_first_then_robustness"


def test_shadow_forward_decision_is_go_live_candidate() -> None:
    decision_path = ROOT / "reports" / "role_router_shadow_forward_validation_decision_latest.json"
    assert decision_path.is_file(), "Expected latest shadow-forward decision receipt to exist."

    decision = _read_json(decision_path)
    assert decision.get("checks_passed") is True
    assert decision.get("thresholds_passed") is True
    assert decision.get("final_decision") == "GO_LIVE_CANDIDATE"

