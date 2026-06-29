from __future__ import annotations

import json
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
GATE = _ROOT / "docs/final/artifacts/sasang_rail_p2_gate_v1_latest.json"
CHAIN = _ROOT / "reports/sasang_rail_p2_chain_v1_latest.json"
INTERPRETIVE = _ROOT / "docs/final/artifacts/sasang_interpretive_insight_bundle_v1_latest.json"


def test_p2_gate() -> None:
    if not GATE.is_file():
        pytest.skip("p2 gate missing")
    gate = json.loads(GATE.read_text(encoding="utf-8-sig"))
    assert gate.get("gate_ok") is True
    assert gate.get("sasang_rail_p2_status") == "enrichment_ok"
    assert gate.get("send_gate") == "HOLD"


def test_interpretive_bundle_upstream_flags() -> None:
    if not INTERPRETIVE.is_file():
        pytest.skip("interpretive bundle missing")
    doc = json.loads(INTERPRETIVE.read_text(encoding="utf-8-sig"))
    up = doc.get("upstream_snapshot") or {}
    assert up.get("sasang_independent_lens_latest", {}).get("present") is True


def test_p2_chain_scripts_ok() -> None:
    if not CHAIN.is_file():
        pytest.skip("p2 chain missing")
    chain = json.loads(CHAIN.read_text(encoding="utf-8-sig"))
    step_ok = [s for s in chain.get("steps") or [] if not str(s.get("name", "")).startswith("pytest")]
    assert all(s.get("ok") for s in step_ok)
    assert chain.get("p2_gate_ok") is True
