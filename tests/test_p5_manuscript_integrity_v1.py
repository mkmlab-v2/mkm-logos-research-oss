from __future__ import annotations

import json
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
GATE = _ROOT / "docs/final/artifacts/p5_manuscript_integrity_gate_v1_latest.json"
AUDIT = _ROOT / "reports/manuscript_integrity_audit_11q5_psalms_commander_v1_latest.json"
MT = _ROOT / "reports/cross_ref_entry_12_mt_only_sidecar_v1_latest.json"
MAP4Q = _ROOT / "reports/dss_4q_ps5_line_witness_map_v1_latest.json"
CANON = _ROOT / "reports/constitution/btrack_pilot/logos_verse_4d_v1_latest.jsonl"
PROMO = _ROOT / "docs/final/artifacts/dss_line_witness_promotion_gate_v1_latest.json"


def test_p5_gate_and_audit() -> None:
    if not GATE.is_file():
        pytest.skip("p5 gate not built")
    gate = json.loads(GATE.read_text(encoding="utf-8-sig"))
    assert gate.get("gate_ok") is True
    if AUDIT.is_file():
        audit = json.loads(AUDIT.read_text(encoding="utf-8-sig"))
        assert audit.get("audit_only") is True
        assert audit.get("send_gate") == "HOLD"
    if MT.is_file():
        mt = json.loads(MT.read_text(encoding="utf-8-sig"))
        assert mt.get("witness_rail") == "mt_only"
        assert mt.get("eleven_q5_bench_status") == "hypothesis_retired"


def test_mainline_and_promotion_lock() -> None:
    if PROMO.is_file():
        promo = json.loads(PROMO.read_text(encoding="utf-8-sig"))
        assert promo.get("gate_ok") is True
    if CANON.is_file():
        for line in CANON.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            vid = str(row.get("verse_id") or "")
            assert not vid.startswith("dss:")
    if MAP4Q.is_file():
        m = json.loads(MAP4Q.read_text(encoding="utf-8-sig"))
        assert int((m.get("summary") or {}).get("witness_rows") or 0) >= 4
