"""Regression: integrated governance builder attaches M31/RAG advisory digest without changing fusion."""

from __future__ import annotations

from scripts.build_integrated_governance_v1 import build_payload


def _minimal_cfg() -> dict:
    return {
        "_path": "inline_minimal_v1",
        "weights": {"biblical_core": 0.34, "myeongri_v4_1": 0.33, "sasang_strict": 0.33},
        "policy": {"require_biblical_stability": False},
    }


def _hold_engines() -> tuple[dict, dict, dict]:
    bib = {"precommercial_ready": False, "_path": "bib.json"}
    mye = {"standalone_commercial_ready": False, "_path": "mye.json"}
    sas = {"commercial_ready": False, "_path": "sas.json"}
    return bib, mye, sas


def test_digest_absent_inputs_still_emits_digest_block() -> None:
    bib, mye, sas = _hold_engines()
    p = build_payload(_minimal_cfg(), bib, mye, sas)
    d = p.get("lens_music_m31_operational_digest_v1") or {}
    assert d.get("schema") == "lens_music_m31_operational_digest_v1"
    assert d.get("present") is False


def test_digest_reflects_trend_and_gate_advisory_fields() -> None:
    bib, mye, sas = _hold_engines()
    trend = {
        "schema": "lens_music_hormone_trend_v1",
        "state": "WATCH",
        "high_stress_rate": 0.4,
        "max_consecutive_high_stress": 2,
        "non_biological_notice": "metaphor_only_advisory_controller",
        "audit_digest_summary": {
            "mean_rag_metabolism_bounded_drift_0_1": 0.12,
            "rows_with_rag_drift": 3,
        },
    }
    gate = {
        "schema": "lens_music_symbolic_audio_promotion_gate_v1",
        "decision": "GO",
        "m31_hormone_guard": {"passed": True, "reason": "ok"},
    }
    p = build_payload(_minimal_cfg(), bib, mye, sas, lens_music_hormone_trend=trend, lens_music_promotion_gate=gate)
    d = p["lens_music_m31_operational_digest_v1"]
    assert d["present"] is True
    assert d["trend_state"] == "WATCH"
    assert d["trend_high_stress_rate"] == 0.4
    assert d["trend_mean_rag_metabolism_bounded_drift_0_1"] == 0.12
    assert d["trend_rows_with_rag_drift"] == 3
    assert d["promotion_decision"] == "GO"
    assert d["m31_hormone_guard_passed"] is True


def test_digest_does_not_change_three_engine_hold() -> None:
    bib, mye, sas = _hold_engines()
    base = build_payload(_minimal_cfg(), bib, mye, sas)
    trend = {
        "schema": "lens_music_hormone_trend_v1",
        "state": "WATCH",
        "high_stress_rate": 0.99,
        "audit_digest_summary": {"mean_rag_metabolism_bounded_drift_0_1": 0.2},
    }
    gate = {"decision": "HOLD_M31_HORMONE_GUARD", "m31_hormone_guard": {"passed": False, "reason": "threshold"}}
    rich = build_payload(_minimal_cfg(), bib, mye, sas, lens_music_hormone_trend=trend, lens_music_promotion_gate=gate)
    for k in ("final_regime", "final_action_allowed", "final_score", "veto_reason_codes", "engine_status"):
        assert base[k] == rich[k]
