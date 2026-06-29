from __future__ import annotations

import json
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
STACK_GATE = _ROOT / "docs/final/artifacts/sasang_rail_stack_gate_v1_latest.json"
STACK_CHAIN = _ROOT / "reports/sasang_rail_stack_chain_v1_latest.json"
UNIFIED = _ROOT / "docs/final/artifacts/sasang_rail_unified_gate_v1_latest.json"


def test_stack_gate() -> None:
    if not STACK_GATE.is_file():
        pytest.skip("stack gate missing")
    gate = json.loads(STACK_GATE.read_text(encoding="utf-8-sig"))
    assert gate.get("gate_ok") is True
    assert gate.get("sasang_rail_stack_status") == "stack_ok"
    assert gate.get("send_gate") == "HOLD"


def test_stack_chain_ok() -> None:
    if not STACK_CHAIN.is_file():
        pytest.skip("stack chain missing")
    chain = json.loads(STACK_CHAIN.read_text(encoding="utf-8-sig"))
    phase_ok = [s for s in chain.get("steps") or [] if s.get("name") in ("containment", "p2_enrichment", "p3_ablation_literature")]
    assert all(s.get("ok") for s in phase_ok)
    gate = json.loads(STACK_GATE.read_text(encoding="utf-8-sig"))
    assert gate.get("gate_ok") is True


def test_unified_aligns_with_stack() -> None:
    if not UNIFIED.is_file() or not STACK_GATE.is_file():
        pytest.skip("gates missing")
    unified = json.loads(UNIFIED.read_text(encoding="utf-8-sig"))
    stack = json.loads(STACK_GATE.read_text(encoding="utf-8-sig"))
    assert unified.get("sasang_rail_stack_status") == stack.get("sasang_rail_stack_status")
