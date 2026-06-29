from __future__ import annotations

import json
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
GATE = _ROOT / "docs/final/artifacts/logos_bible_rail_completion_gate_v1_latest.json"
REPORT = _ROOT / "reports/logos_bible_rail_completion_commander_report_v1_latest.json"
RELABEL = _ROOT / "reports/cross_ref_entry_13_shadow_verse_relabel_sidecar_v1_latest.json"
AUDIT = _ROOT / "reports/psalms_entry_12_13_cross_lane_audit_v1_latest.json"
CHAIN = _ROOT / "reports/logos_bible_rail_p9_closure_chain_v1_latest.json"


def test_completion_gate_closed_p9_final() -> None:
    if not GATE.is_file():
        pytest.skip("completion gate not built")
    gate = json.loads(GATE.read_text(encoding="utf-8-sig"))
    assert gate.get("gate_ok") is True
    assert gate.get("bible_rail_status") == "closed_p9_final"
    assert gate.get("send_gate") == "HOLD"
    checks = gate.get("checks") or {}
    assert checks.get("verified_anchor_not_claimed", {}).get("passed") is True
    assert checks.get("canon_31k_clean", {}).get("passed") is True
    assert checks.get("cross_ref_entry_12_13_applied", {}).get("passed") is True


def test_completion_artifacts() -> None:
    if not RELABEL.is_file():
        pytest.skip("relabel sidecar missing")
    relabel = json.loads(RELABEL.read_text(encoding="utf-8-sig"))
    assert relabel.get("shadow_verse_anchor") == "Ps.5.8-9"
    tw = relabel.get("track_wall") or {}
    assert tw.get("cross_ref_draft_mutation_forbidden") is True
    if AUDIT.is_file():
        audit = json.loads(AUDIT.read_text(encoding="utf-8-sig"))
        assert audit.get("audit_ok") is True
        assert audit.get("verified_anchor_achieved") is False
        assert len(audit.get("verses") or []) == 2
    if REPORT.is_file():
        rep = json.loads(REPORT.read_text(encoding="utf-8-sig"))
        assert rep.get("completion_gate_ok") is True
        assert rep.get("cross_ref_entry_12_13_applied") is True
        assert rep.get("verified_anchor_achieved") is False


def test_chain_summary() -> None:
    if not CHAIN.is_file():
        pytest.skip("chain log missing")
    chain = json.loads(CHAIN.read_text(encoding="utf-8-sig"))
    assert chain.get("completion_gate_ok") is True
    assert chain.get("bible_rail_status") == "closed_p9_final"
    step_ok = [s for s in chain.get("steps") or [] if s.get("name") != "pytest"]
    assert all(s.get("ok") for s in step_ok)
