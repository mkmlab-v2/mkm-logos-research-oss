from __future__ import annotations

from pathlib import Path

from scripts.run_w3_resonance_compute import run_compute


ROOT = Path(__file__).resolve().parents[1]
IN_PATH = ROOT / "docs" / "final" / "artifacts" / "W3_PILOT_MIN_INPUT_V1.json"
SPEC_PATH = ROOT / "docs" / "final" / "artifacts" / "W3_RESONANCE_COMPUTE_SPEC_V1.json"
OUT_PATH = ROOT / "reports" / "constitution" / "btrack_pilot" / "_w3_aux_contract_out.json"


def test_w3_aux_adapter_present_and_non_gating_contract() -> None:
    out = run_compute(IN_PATH, SPEC_PATH, OUT_PATH)
    rm = out.get("run_meta") or {}
    assert rm.get("aux_adapter_version") == "w3_aux_adapter_v1"

    top = out.get("top_n_results") or []
    assert top, "top_n_results must not be empty"
    for row in top:
        aux = row.get("aux_non_gating") or {}
        assert isinstance(aux, dict)
        if row.get("lane") == "macro_lane":
            assert "geumhwa_aux_score" in aux
            assert "transition_pressure" in aux
        else:
            assert "bomyeong_guard_score" in aux
            assert "taeyang_risk_flag" in aux

    pg = out.get("promotion_gate") or {}
    # Adapter is metadata-only; gate contract still exists and is evaluated.
    assert "passed" in pg
    assert "false_equivalence_max_count" in pg
