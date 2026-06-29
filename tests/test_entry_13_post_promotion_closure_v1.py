from __future__ import annotations

import json
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
GATE = _ROOT / "docs/final/artifacts/entry_13_post_promotion_gate_v1_latest.json"
REPORT = _ROOT / "reports/entry_13_post_promotion_commander_report_v1_latest.json"
REGISTRY = _ROOT / "reports/shadow_4q_ps5_witness_registry_v1_latest.json"
CANON = _ROOT / "reports/constitution/btrack_pilot/logos_verse_4d_v1_latest.jsonl"
PROMO = _ROOT / "docs/final/artifacts/dss_line_witness_promotion_gate_v1_latest.json"


def test_post_promotion_gate() -> None:
    if not GATE.is_file():
        pytest.skip("post promotion gate not built")
    gate = json.loads(GATE.read_text(encoding="utf-8-sig"))
    assert gate.get("gate_ok") is True
    assert gate.get("checks", {}).get("auto_scan_honest_zero", {}).get("passed") is True


def test_registry_and_report_integrity() -> None:
    if not REGISTRY.is_file():
        pytest.skip("registry missing")
    reg = json.loads(REGISTRY.read_text(encoding="utf-8-sig"))
    sm = reg.get("summary") or {}
    assert int(sm.get("commander_verified_rows") or 0) >= 1
    promoted = [r for r in reg.get("rows") or [] if r.get("commander_promoted")]
    assert promoted[0].get("shadow_verse_anchor") == "Ps.5.8-9"
    if REPORT.is_file():
        rep = json.loads(REPORT.read_text(encoding="utf-8-sig"))
        assert rep.get("canon_31k_clean") is True
        assert rep.get("cross_ref_draft_mutated") is False
    if PROMO.is_file():
        promo = json.loads(PROMO.read_text(encoding="utf-8-sig"))
        assert promo.get("promotion_ok") is True
    if CANON.is_file():
        for line in CANON.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            assert not str(row.get("verse_id") or "").startswith("dss:")
