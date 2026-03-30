# @MKM12-METADATA
# Type: Logic
# Purpose: Validate ENTRY_16 promotion gate JSON contract.
# Keywords: entry16, source-hunt, promotion, gate

from __future__ import annotations

import json
from pathlib import Path


_ROOT = Path(__file__).resolve().parents[1]
_SUMMARY = _ROOT / "docs" / "final" / "artifacts" / "entry16_source_hunt_summary.json"
_GATE = _ROOT / "docs" / "final" / "artifacts" / "entry16_promotion_gate.json"


def test_entry16_promotion_gate_contract() -> None:
    assert _SUMMARY.is_file(), f"missing source-hunt summary: {_SUMMARY}"
    assert _GATE.is_file(), f"missing promotion gate report: {_GATE}"

    summary = json.loads(_SUMMARY.read_text(encoding="utf-8"))
    gate = json.loads(_GATE.read_text(encoding="utf-8"))

    assert gate.get("schema") == "entry16_promotion_gate_v1"
    assert gate.get("source_summary") == "docs/final/artifacts/entry16_source_hunt_summary.json"
    assert gate.get("decision") in {"promote_candidate", "promote_proxy_candidate_manual", "keep_locked"}
    assert gate.get("status") in {
        "candidate_ready_for_manual_review",
        "proxy_candidate_ready_for_manual_review",
        "missing_anchor_until_source_update",
    }
    assert isinstance(gate.get("has_direct_witness"), bool)
    assert isinstance(gate.get("witness_yes_count"), int)
    assert isinstance(gate.get("proxy_anchor_candidate_count"), int)
    assert isinstance(gate.get("required_evidence"), list)
    assert gate.get("required_evidence"), "required_evidence must not be empty"
    assert isinstance(gate.get("rationale"), str) and gate["rationale"].strip()

    has_yes = int(summary.get("witness_counts", {}).get("yes", 0)) > 0
    assert gate.get("has_direct_witness") == has_yes
    assert gate.get("witness_yes_count") == int(summary.get("witness_counts", {}).get("yes", 0))


def test_entry16_promotion_gate_decision_consistency() -> None:
    summary = json.loads(_SUMMARY.read_text(encoding="utf-8"))
    gate = json.loads(_GATE.read_text(encoding="utf-8"))
    has_yes = int(summary.get("witness_counts", {}).get("yes", 0)) > 0
    proxy_count = int(summary.get("proxy_anchor_candidate_count", 0))
    if has_yes:
        assert gate.get("decision") == "promote_candidate"
        assert gate.get("status") == "candidate_ready_for_manual_review"
    elif proxy_count > 0:
        assert gate.get("decision") == "promote_proxy_candidate_manual"
        assert gate.get("status") == "proxy_candidate_ready_for_manual_review"
    else:
        assert gate.get("decision") == "keep_locked"
        assert gate.get("status") == "missing_anchor_until_source_update"
