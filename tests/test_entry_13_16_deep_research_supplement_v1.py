from __future__ import annotations

import json
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
E13 = _ROOT / "reports/deep_research_entry_13_ps5_8_9_shadow_supplement_v1_latest.json"
E16 = _ROOT / "reports/deep_research_entry_16_ezra_2_54_waiting_queue_plan_v1_latest.json"
CHAIN = _ROOT / "reports/entry_13_16_deep_research_supplement_chain_v1_latest.json"


def test_entry_13_supplement_mapping() -> None:
    if not E13.is_file():
        pytest.skip("entry13 supplement missing")
    doc = json.loads(E13.read_text(encoding="utf-8-sig"))
    assert doc.get("cross_ref_entry_id") == "ENTRY_13"
    assert doc.get("canonical_ref") == "Ps.5.2"
    assert doc.get("shadow_verse_anchor") == "Ps.5.8-9"
    assert doc.get("not_entry_16") is True
    assert doc.get("verified_anchor_achieved") is False
    assert doc.get("send_gate") == "HOLD"
    assert doc.get("writes_canon") is False


def test_entry_16_plan_not_psalm() -> None:
    if not E16.is_file():
        pytest.skip("entry16 plan missing")
    doc = json.loads(E16.read_text(encoding="utf-8-sig"))
    assert doc.get("cross_ref_entry_id") == "ENTRY_16"
    assert doc.get("canonical_ref") == "Ezra.2.54"
    assert doc.get("not_psalm_5") is True
    assert doc.get("satellite_status") == "missing_anchor_until_source_update"
    assert len(doc.get("research_steps") or []) == 8
    forbidden = " ".join(doc.get("forbidden") or [])
    assert "Ps.5" in forbidden


def test_supplement_chain_ok() -> None:
    if not CHAIN.is_file():
        pytest.skip("chain missing")
    chain = json.loads(CHAIN.read_text(encoding="utf-8-sig"))
    step_ok = [s for s in chain.get("steps") or [] if not str(s.get("name", "")).startswith("pytest")]
    assert all(s.get("ok") for s in step_ok)
    assert chain.get("entry_13_verified_anchor_achieved") is False
    assert chain.get("not_entry_16_psalm_confusion") is True
