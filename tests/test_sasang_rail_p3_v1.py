from __future__ import annotations

import json
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
P3_GATE = _ROOT / "docs/final/artifacts/sasang_rail_p3_gate_v1_latest.json"
UNIFIED = _ROOT / "docs/final/artifacts/sasang_rail_unified_gate_v1_latest.json"
CHAIN = _ROOT / "reports/sasang_rail_p3_chain_v1_latest.json"
INTERPRETIVE = _ROOT / "docs/final/artifacts/sasang_interpretive_insight_bundle_v1_latest.json"


def test_p3_gate() -> None:
    if not P3_GATE.is_file():
        pytest.skip("p3 gate missing")
    gate = json.loads(P3_GATE.read_text(encoding="utf-8-sig"))
    assert gate.get("gate_ok") is True
    assert gate.get("sasang_rail_p3_status") == "ablation_literature_ok"
    assert gate.get("send_gate") == "HOLD"


def test_unified_stack_gate() -> None:
    if not UNIFIED.is_file():
        pytest.skip("unified gate missing")
    gate = json.loads(UNIFIED.read_text(encoding="utf-8-sig"))
    assert gate.get("gate_ok") is True
    assert gate.get("sasang_rail_stack_status") == "stack_ok"
    phases = gate.get("phase_gates") or {}
    assert phases.get("containment") == "containment_ok"
    assert phases.get("p2") == "enrichment_ok"
    assert phases.get("p3") == "ablation_literature_ok"


def test_interpretive_has_rail_gate_section() -> None:
    if not INTERPRETIVE.is_file():
        pytest.skip("interpretive bundle missing")
    doc = json.loads(INTERPRETIVE.read_text(encoding="utf-8-sig"))
    ids = {s.get("axis_id") for s in doc.get("sections") or []}
    assert "sasang_rail_gates" in ids
    up = doc.get("upstream_snapshot") or {}
    assert up.get("sasang_rail_containment_gate", {}).get("present") is True


def test_p3_chain_scripts_ok() -> None:
    if not CHAIN.is_file():
        pytest.skip("p3 chain missing")
    chain = json.loads(CHAIN.read_text(encoding="utf-8-sig"))
    step_ok = [s for s in chain.get("steps") or [] if not str(s.get("name", "")).startswith("pytest")]
    assert all(s.get("ok") for s in step_ok)
    assert chain.get("unified_gate_ok") is True
