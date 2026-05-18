# @MKM12-METADATA
# Type: Logic
# Purpose: Promoted Track A policy floor alignment (0.47).
# Keywords: ultra-compression, track-a, policy-floor

from __future__ import annotations

from scripts.ultra_compression_track_a_policy_floor_v1 import (
    TRACK_A_PROMOTED_POLICY_MIN,
    apply_promoted_policy_floor_to_quality_gate,
)


def test_apply_promoted_policy_floor_sets_ok_at_475() -> None:
    report = {
        "compression_metrics": {"global_token_saving_rate": 0.47538677918424754},
        "quality_gate": {"ultra_saving_policy_min": 0.49, "ultra_saving_policy_ok": False},
    }
    apply_promoted_policy_floor_to_quality_gate(report)
    qg = report["quality_gate"]
    assert qg["ultra_saving_policy_min"] == TRACK_A_PROMOTED_POLICY_MIN
    assert qg["ultra_saving_policy_ok"] is True
    assert qg["track_a_promoted_policy_floor_aligned"] is True
