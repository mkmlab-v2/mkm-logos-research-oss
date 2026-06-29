from __future__ import annotations

import json
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
SIDECAR = _ROOT / "reports/cross_ref_entry_12_13_evidence_sidecar_v1_latest.json"
BOARD = _ROOT / "reports/dss_line_witness_verification_operator_board_v1_latest.json"
DIGEST = _ROOT / "reports/logos_track_b_commander_dual_theme_digest_latest.md"
CLOSURE = _ROOT / "reports/logos_track_b_integration_closure_v1_latest.json"
PROMO = _ROOT / "docs/final/artifacts/dss_line_witness_promotion_gate_v1_latest.json"


def test_p6_evidence_sidecar_p5_aligned() -> None:
    if not SIDECAR.is_file():
        pytest.skip("evidence sidecar not built")
    doc = json.loads(SIDECAR.read_text(encoding="utf-8-sig"))
    assert doc.get("p5_manuscript_integrity_gate_ok") is True
    entries = {e["entry_id"]: e for e in doc.get("entries") or []}
    assert entries["ENTRY_12"]["witness_rail"] == "mt_only"
    assert entries["ENTRY_12"]["bench_status"] == "hypothesis_retired"
    assert "4Q" in str(entries["ENTRY_13"]["witness_rail"])


def test_p6_operator_board_and_promotion_lock() -> None:
    if not BOARD.is_file():
        pytest.skip("operator board not built")
    board = json.loads(BOARD.read_text(encoding="utf-8-sig"))
    assert board.get("eleven_q5_bench_status") == "hypothesis_retired"
    assert board.get("p5_manuscript_integrity_gate_ok") is True
    if PROMO.is_file():
        promo = json.loads(PROMO.read_text(encoding="utf-8-sig"))
        assert promo.get("gate_ok") is True
    if CLOSURE.is_file():
        closure = json.loads(CLOSURE.read_text(encoding="utf-8-sig"))
        assert closure.get("gates", {}).get("p5_manuscript_integrity_ok") is True
    if DIGEST.is_file():
        text = DIGEST.read_text(encoding="utf-8")
        assert "원고 무결성" in text
        assert "hypothesis_retired" in text or "mt_only" in text
