"""Wire-first dialogue mock smoke."""

from __future__ import annotations


def test_wire_first_dialogue_trading_ok():
    from scripts.run_mkm_inter_agent_dialogue_wire_first_v1 import run_dialogue

    doc = run_dialogue(turns=2, scenario="trading")
    assert doc.get("all_ok") is True
    assert doc.get("schema") == "mkm_inter_agent_dialogue_wire_first_v1"
    assert len(doc.get("transcript") or []) == 2
