from __future__ import annotations

import json
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
P6_GATE = _ROOT / "docs/final/artifacts/sasang_rail_p6_gate_v1_latest.json"
UNIFIED = _ROOT / "docs/final/artifacts/sasang_curated_joint_unified_gate_v1_latest.json"
CHAIN = _ROOT / "reports/sasang_rail_p6_chain_v1_latest.json"


def test_p6_gate() -> None:
    if not P6_GATE.is_file():
        pytest.skip("p6 gate missing")
    gate = json.loads(P6_GATE.read_text(encoding="utf-8-sig"))
    assert gate.get("gate_ok") is True
    assert gate.get("sasang_rail_p6_status") == "curated_ingest_ok"
    assert gate.get("send_gate") == "HOLD"


def test_curated_unified_linked() -> None:
    if not UNIFIED.is_file():
        pytest.skip("unified curated gate missing")
    doc = json.loads(UNIFIED.read_text(encoding="utf-8-sig"))
    assert doc.get("gate_ok") is True


def test_p6_chain_ok() -> None:
    if not CHAIN.is_file():
        pytest.skip("p6 chain missing")
    chain = json.loads(CHAIN.read_text(encoding="utf-8-sig"))
    core = [s for s in chain.get("steps") or [] if s.get("name") in ("curated_promote_drill", "p6_gate")]
    assert all(s.get("ok") for s in core)
