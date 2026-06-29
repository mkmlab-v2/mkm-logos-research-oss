from __future__ import annotations

import json
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
PACKET = _ROOT / "reports/entry_13_ps5_2_verified_anchor_evidence_packet_v1_latest.json"
GATE = _ROOT / "docs/final/artifacts/entry_13_ps5_2_verified_anchor_gate_v1_latest.json"


def test_evidence_packet_honest_gap() -> None:
    if not PACKET.is_file():
        pytest.skip("packet not built")
    pkt = json.loads(PACKET.read_text(encoding="utf-8-sig"))
    assert pkt.get("verified_anchor_achieved") is False
    assert pkt.get("bench_canonical_ref") == "Ps.5.2"
    sh = pkt.get("shadow_rail") or {}
    assert sh.get("shadow_verse_anchor") == "Ps.5.8-9"
    scan = pkt.get("witness_candidate_scan") or {}
    assert int(scan.get("direct_line_candidates") or 0) == 0
    assert int(scan.get("pool_rows") or 0) >= 1


def test_verified_anchor_gate() -> None:
    if not GATE.is_file():
        pytest.skip("gate not built")
    gate = json.loads(GATE.read_text(encoding="utf-8-sig"))
    assert gate.get("gate_ok") is True
    assert gate.get("verified_anchor_achieved") is False
    assert gate.get("checks", {}).get("gap_honestly_documented", {}).get("passed") is True
