"""Contract tests for build_a_track_go_nogo_status.evaluate() merge logic."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import scripts.build_a_track_go_nogo_status as g


def _write(p: Path, obj: dict) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, ensure_ascii=False), encoding="utf-8")


def _minimal_workspace(root: Path) -> None:
    _write(
        root / "docs/final/artifacts/high_reliability_mode_gate_latest.json",
        {"decision": "PASS"},
    )
    _write(
        root / "docs/final/artifacts/trinity_track_quality_report_latest.json",
        {"summary": {"overall_decision": "PASS"}},
    )
    _write(
        root / "docs/final/artifacts/prophecy_2026_monthly_kospi_btc_fact_safe_v1.json",
        {"meta": {"high_reliability_decision": "HOLD", "price_output_locked": True}},
    )
    _write(
        root / "data/chronos_forward_training/holdout_2026_result.json",
        {"direction_match_rate": 55.0},
    )
    _write(
        root / "docs/final/artifacts/a_track_price_output_unlock_policy_v1_latest.json",
        {"status": "READY_FOR_SIGNOFF"},
    )
    _write(
        root / "docs/final/artifacts/a_track_high_reliability_release_plan_v1_latest.json",
        {"status": "READY_FOR_SIGNOFF"},
    )
    _write(
        root / "docs/final/artifacts/a_track_policy_floor_governance_decision_v1_latest.json",
        {"status": "APPROVED"},
    )


def test_s3_gate_passes_from_tracker_when_checklist_s3_false(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _minimal_workspace(tmp_path)
    _write(
        tmp_path / "docs/final/artifacts/a_track_hold_release_checklist_v1_latest.json",
        {
            "checklist": [
                {"id": "lock-01", "done": False},
                {"id": "s3-01", "done": False},
                {"id": "s4-01", "done": False},
                {"id": "hrm-01", "done": False},
                {"id": "policy-01", "done": False},
            ]
        },
    )
    _write(
        tmp_path / "docs/final/artifacts/a_track_multiweek_stability_tracker_v1_latest.json",
        {"summary": {"ready_for_s3_gate": True}},
    )
    _write(
        tmp_path / "docs/final/artifacts/a_track_operator_approval_protocol_v1_latest.json",
        {"status": "READY_FOR_SIGNOFF"},
    )
    _write(
        tmp_path / "reports/a_track_promotion_decision_latest.json",
        {
            "schema": "a_track_promotion_decision_v1",
            "action": "approve",
            "status": "accepted",
            "requested_stage": "S2_PAPER_STRICT",
            "generated_at": "2026-01-01T00:00:00Z",
            "approver": "test",
        },
    )

    monkeypatch.setattr(g, "ROOT", tmp_path)
    monkeypatch.setattr(
        g,
        "MULTIWEEK_TRACKER_PATH",
        tmp_path / "docs/final/artifacts/a_track_multiweek_stability_tracker_v1_latest.json",
    )
    monkeypatch.setattr(
        g,
        "OPERATOR_APPROVAL_PROTOCOL_PATH",
        tmp_path / "docs/final/artifacts/a_track_operator_approval_protocol_v1_latest.json",
    )
    monkeypatch.setattr(
        g,
        "POLICY_FLOOR_GOV_PATH",
        tmp_path / "docs/final/artifacts/a_track_policy_floor_governance_decision_v1_latest.json",
    )
    monkeypatch.setattr(
        g,
        "ATRACK_CLI_DECISION_PATH",
        tmp_path / "reports/a_track_promotion_decision_latest.json",
    )

    out = g.evaluate(on_system_error="no_go")
    assert out["checks"]["s3_multiweek_evidence_ready"] is True
    assert out["checks"]["s4_operator_checklist_ready"] is True
    assert out["checks"]["high_reliability_decision_not_hold"] is False
    assert out["checks"]["price_output_unlocked"] is False
    assert out["checks"]["high_reliability_release_plan_defined"] is True
    assert out["checks"]["price_unlock_policy_defined"] is True
    assert out["result"]["overall_go_no_go"] == "HOLD"
    assert out["result"]["recommended_stage"] == "S1_SHADOW"
