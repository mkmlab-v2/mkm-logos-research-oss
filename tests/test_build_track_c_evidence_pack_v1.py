from scripts.build_track_c_evidence_pack_v1 import build_payload


def test_build_payload_includes_key_contract_fields():
    payload = build_payload(
        governance={
            "final_regime": "ATTACK",
            "final_action_allowed": True,
            "is_fallback": False,
            "final_score": 0.7,
            "veto_reason_codes": [],
        },
        biblical_gate={
            "precommercial_ready": True,
            "stage": "precommercial_ready",
            "stability": {"stability_go": False, "current_ready_streak": 2, "streak_required": 3},
        },
        myeongri_gate={
            "standalone_commercial_ready": True,
            "stage": "상용 준비",
            "metrics": {"accuracy": 0.47, "abs_train_test_acc_gap": 0.002},
        },
        sasang_gate={
            "commercial_ready": True,
            "stage": "상용",
            "gates": {"G3_runtime_go_ratio": {"observed_ratio": 1.0}},
        },
    )
    assert payload["schema"] == "track_c_evidence_pack_v1"
    assert payload["governance"]["final_regime"] == "ATTACK"
    assert payload["engine_readiness"]["myeongri_v4_1"]["standalone_commercial_ready"] is True
    assert "not investment advice" in payload["commercial_scope"]["required_disclaimer"].lower()

