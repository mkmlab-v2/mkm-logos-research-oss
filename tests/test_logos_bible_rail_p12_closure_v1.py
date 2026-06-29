from __future__ import annotations

import json
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
WQ_GATE = _ROOT / "docs/final/artifacts/cross_ref_waiting_queue_consolidated_gate_v1_latest.json"
CHAIN = _ROOT / "reports/logos_bible_rail_p12_closure_chain_v1_latest.json"


def test_waiting_queue_consolidated_gate() -> None:
    if not WQ_GATE.is_file():
        pytest.skip("waiting queue gate missing")
    gate = json.loads(WQ_GATE.read_text(encoding="utf-8-sig"))
    assert gate.get("gate_ok") is True
    assert gate.get("waiting_queue_status") == "documented_hold"
    assert gate.get("send_gate") == "HOLD"
    e16 = gate.get("entries", {}).get("ENTRY_16", {})
    assert e16.get("missing_anchor_lock") is True


def test_p12_chain_ok() -> None:
    if not CHAIN.is_file():
        pytest.skip("p12 chain missing")
    chain = json.loads(CHAIN.read_text(encoding="utf-8-sig"))
    assert chain.get("waiting_queue_gate_ok") is True
    step_ok = [s for s in chain.get("steps") or [] if not str(s.get("name", "")).startswith("pytest")]
    assert all(s.get("ok") for s in step_ok)
