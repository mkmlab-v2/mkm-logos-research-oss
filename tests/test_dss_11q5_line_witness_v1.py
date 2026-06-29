from __future__ import annotations

import json
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
WITNESS_MAP = _ROOT / "reports/dss_11q5_line_witness_map_v1_latest.json"
REGISTRY = _ROOT / "reports/shadow_line_witness_registry_v1_latest.json"
AUDIT = _ROOT / "reports/shadow_cross_lane_gematria_audit_v1_latest.json"
GATE = _ROOT / "docs/final/artifacts/shadow_cross_lane_gematria_gate_v1_latest.json"
CANON = _ROOT / "reports/constitution/btrack_pilot/logos_verse_4d_v1_latest.jsonl"


def test_witness_map_and_registry() -> None:
    if not WITNESS_MAP.is_file():
        pytest.skip("witness map not built")
    wmap = json.loads(WITNESS_MAP.read_text(encoding="utf-8-sig"))
    assert wmap.get("schema") == "dss_11q5_line_witness_map_v1"
    entries = {e["entry_id"]: e for e in wmap.get("entries") or []}
    assert "ENTRY_12" in entries and "ENTRY_13" in entries
    assert entries["ENTRY_12"]["canon_verse_id"] == "Ps.4.6"
    assert len(entries["ENTRY_12"]["witnesses"]) >= 3
    if REGISTRY.is_file():
        reg = json.loads(REGISTRY.read_text(encoding="utf-8-sig"))
        sm = reg.get("summary") or {}
        assert int(sm.get("numeric_comparison_eligible_rows") or 0) >= 4


def test_cross_lane_line_witness_audit_and_isolation() -> None:
    if not AUDIT.is_file():
        pytest.skip("audit not built")
    audit = json.loads(AUDIT.read_text(encoding="utf-8-sig"))
    sm = audit.get("summary") or {}
    assert int(sm.get("line_witness_numeric_eligible_samples") or 0) >= 4
    ps46 = next(a for a in audit.get("audits") or [] if a.get("canon_verse_id") == "Ps.4.6")
    assert ps46.get("audit_interpretation") == "line_witness_lexical_proximity"
    assert int(ps46.get("line_witness_numeric_eligible_count") or 0) >= 2
    if GATE.is_file():
        gate = json.loads(GATE.read_text(encoding="utf-8-sig"))
        assert gate.get("gate_ok") is True
    if CANON.is_file():
        for line in CANON.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            vid = str(row.get("verse_id") or "")
            assert not vid.startswith("dss:")
