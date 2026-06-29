from __future__ import annotations

import json
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
P5_GATE = _ROOT / "docs/final/artifacts/sasang_rail_p5_gate_v1_latest.json"
PROMOTE_GATE = _ROOT / "docs/final/artifacts/sasang_literature_curated_promote_gate_v1_latest.json"
ABLATION = _ROOT / "reports/sasang_4agent_protocol_ablation_v1_latest.json"
CHAIN = _ROOT / "reports/sasang_rail_p5_chain_v1_latest.json"


def test_p5_gate() -> None:
    if not P5_GATE.is_file():
        pytest.skip("p5 gate missing")
    gate = json.loads(P5_GATE.read_text(encoding="utf-8-sig"))
    assert gate.get("gate_ok") is True
    assert gate.get("sasang_rail_p5_status") == "literature_ablation_ok"
    assert gate.get("send_gate") == "HOLD"


def test_ablation_full_bootstrap() -> None:
    if not ABLATION.is_file():
        pytest.skip("ablation missing")
    doc = json.loads(ABLATION.read_text(encoding="utf-8-sig"))
    assert int((doc.get("experiment") or {}).get("bootstrap_trials") or 0) >= 200
    assert (doc.get("track_wall") or {}).get("track_a_promotion") is False


def test_promote_gate_linked() -> None:
    if not PROMOTE_GATE.is_file():
        pytest.skip("promote gate missing")
    doc = json.loads(PROMOTE_GATE.read_text(encoding="utf-8-sig"))
    assert doc.get("gate_ok") is True


def test_p5_chain_ok() -> None:
    if not CHAIN.is_file():
        pytest.skip("p5 chain missing")
    chain = json.loads(CHAIN.read_text(encoding="utf-8-sig"))
    core = [
        s
        for s in chain.get("steps") or []
        if s.get("name")
        in (
            "review_queue_from_catalog",
            "literature_curated_promote_gate",
            "ablation_full_bootstrap",
            "p5_gate",
        )
    ]
    assert all(s.get("ok") for s in core)
