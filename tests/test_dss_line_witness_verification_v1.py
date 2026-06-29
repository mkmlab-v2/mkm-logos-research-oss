from __future__ import annotations

import json
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
SCAN = _ROOT / "reports/dss_line_witness_verification_scan_v1_latest.json"
SIDECAR = _ROOT / "reports/cross_ref_entry_12_13_evidence_sidecar_v1_latest.json"
GATE = _ROOT / "docs/final/artifacts/dss_line_witness_promotion_gate_v1_latest.json"
BOARD = _ROOT / "reports/dss_line_witness_verification_operator_board_v1_latest.json"
CROSS_REF = _ROOT / "docs/final/artifacts/CROSS_REF_DSS_TO_STATES_DRAFT.json"


def test_verification_scan_honest_zero_auto_verified() -> None:
    if not SCAN.is_file():
        pytest.skip("scan not built")
    doc = json.loads(SCAN.read_text(encoding="utf-8-sig"))
    assert doc.get("schema") == "dss_line_witness_verification_scan_v1"
    sm = doc.get("summary") or {}
    assert int(sm.get("entries_scanned") or 0) >= 2
    # Local ETCBC cannot verify Ps.4.6/Ps.5.2 line mapping today.
    assert int(sm.get("auto_verified_total") or 0) == 0


def test_promotion_gate_and_sidecar_isolation() -> None:
    if not GATE.is_file():
        pytest.skip("gate not built")
    gate = json.loads(GATE.read_text(encoding="utf-8-sig"))
    assert gate.get("gate_ok") is True
    if gate.get("promotion_ok") is True:
        assert len(gate.get("manual_promotions") or []) >= 1
    else:
        assert gate.get("promotion_pending_external") is True
        assert gate.get("promotion_ok") is False
    if SIDECAR.is_file():
        sidecar = json.loads(SIDECAR.read_text(encoding="utf-8-sig"))
        tw = sidecar.get("track_wall") or {}
        assert tw.get("cross_ref_draft_mutation_forbidden") is True
    if BOARD.is_file():
        board = json.loads(BOARD.read_text(encoding="utf-8-sig"))
        assert board.get("infrastructure_gate_ok") is True


def test_cross_ref_draft_unmutated() -> None:
    if not CROSS_REF.is_file():
        pytest.skip("cross ref missing")
    doc = json.loads(CROSS_REF.read_text(encoding="utf-8-sig"))
    by_id = {e["entry_id"]: e for e in doc.get("entries") or []}
    for eid in ("ENTRY_12", "ENTRY_13"):
        ref = str(by_id[eid].get("satellite_ref") or "")
        assert "partial_anchor_verified" in ref
        assert "TBD" in ref or "remains TBD" in ref
