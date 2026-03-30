from __future__ import annotations

import json
from pathlib import Path

from scripts.run_w3_resonance_compute import run_compute


ROOT = Path(__file__).resolve().parents[1]
IN_PATH = ROOT / "docs" / "final" / "artifacts" / "W3_PILOT_MIN_INPUT_V1.json"
SPEC_PATH = ROOT / "docs" / "final" / "artifacts" / "W3_RESONANCE_COMPUTE_SPEC_V1.json"
OUT_PATH = ROOT / "reports" / "constitution" / "btrack_pilot" / "_w3_compute_test_out.json"


def test_w3_deterministic_compute_contract() -> None:
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    out = run_compute(IN_PATH, SPEC_PATH, OUT_PATH)
    assert out.get("schema") == "w3_resonance_result_v1"
    assert out.get("status") == "computed_pilot"
    rm = out.get("run_meta") or {}
    assert int(rm.get("top_n_count", 0)) >= 1
    top = out.get("top_n_results") or []
    assert len(top) == int(rm.get("top_n_count", 0))
    for row in top:
        assert "[HYPO]" in str(row.get("rationale", ""))
        rf = row.get("falsification_flags") or {}
        assert "false_equivalence_risk" in rf
    ga = out.get("guardrail_assertions") or {}
    assert ga.get("all_rationale_include_hypo") is True
    assert ga.get("geo_event_ref_participates_in_scoring") is False
    pg = out.get("promotion_gate") or {}
    assert "passed" in pg
    assert int(pg.get("false_equivalence_max_count", -1)) >= 0
    # persisted file shape
    persisted = json.loads(OUT_PATH.read_text(encoding="utf-8"))
    assert persisted.get("schema") == "w3_resonance_result_v1"
