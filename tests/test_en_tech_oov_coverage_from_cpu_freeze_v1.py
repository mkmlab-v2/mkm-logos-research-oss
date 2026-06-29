"""P2 en_tech OOV coverage report contract."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "reports/constitution/btrack_pilot/comp_en_tech_oov_coverage_from_cpu_freeze_v1.json"


def test_en_tech_oov_coverage_report_contract() -> None:
    assert OUT.is_file(), "run build_en_tech_oov_coverage_from_cpu_freeze_v1.py first"
    doc = json.loads(OUT.read_text(encoding="utf-8-sig"))
    assert doc.get("research_only") is True
    assert doc.get("track_a_active_written") is False
    assert doc.get("lane_id") == "en_tech_spec_stress_v1"
    assert doc.get("case_count", 0) > 0
    agg = doc.get("aggregate") or {}
    assert "aggregate_oov_ratio" in agg
    assert doc.get("freeze_headline_cross_check", {}).get("jaccard_floor_gate_0_85_passed") is False
