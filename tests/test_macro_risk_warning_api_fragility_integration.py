from __future__ import annotations

import json

from scripts import macro_risk_warning_api_stub as stub


def test_macro_risk_uses_fragility_gate(tmp_path) -> None:
    fragility = {
        "gate": "RED",
        "score": {"scaled_0_100": 78.5},
        "z_scores": {"move": 2.5, "vix": 1.7, "hy_oas": 2.1, "dxy_vol": 1.2},
        "gate_details": {
            "hard_trigger": True,
            "fragility_cluster": True,
            "stress_persistence": False,
        },
    }
    fragility_path = tmp_path / "fragility.json"
    fragility_path.write_text(json.dumps(fragility), encoding="utf-8")

    original_fragility = stub.FRAGILITY_ARTIFACT
    try:
        stub.FRAGILITY_ARTIFACT = fragility_path
        req = stub.MacroRiskWarningRequest(
            client_request_id="t1",
            asset_scope="BTC-USD",
            include_evidence_ref=False,
        )
        resp = stub.build_macro_risk_warning_response(req)
    finally:
        stub.FRAGILITY_ARTIFACT = original_fragility

    assert resp.decision_state == "FORCE_HOLD"
    assert resp.risk_warning_level == "critical"
    assert resp.fragility_composite is not None
    assert resp.fragility_composite.gate == "RED"
    assert resp.non_gating_narrative is not None
    assert resp.non_gating_narrative.policy_tag == "[NON_GATING]"
    assert resp.non_gating_narrative.stage == "late_babel_to_exodus_transition"
    assert resp.non_gating_narrative.quaternion_signal in {"phase_shift_assumed_high", "phase_shift_high"}
    assert "stress" in resp.non_gating_narrative.state_4d
