"""Promotion packet path-A product signoff flags."""
from __future__ import annotations

from scripts.build_btrack_nextgen_promotion_candidate_packet_v1 import (
    _path_a_product_lane_ready,
    _path_b_knee_lane_ready,
)


def test_path_a_product_lane_ready_when_artifacts_present() -> None:
    ready, meta = _path_a_product_lane_ready()
    assert meta.get("lane") == "path_a_hybrid_sidecar_preview"
    assert ready is True
    assert float(meta.get("byte_exact_subset_parity") or 0) >= 1.0


def test_path_b_knee_lane_ready_when_prior_eval_present() -> None:
    ready, meta = _path_b_knee_lane_ready()
    assert meta.get("arm_id")
    assert ready is True
