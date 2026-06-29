from __future__ import annotations

import os

from scripts.l1_inverse_decoder_decode_router_v1 import (
    active_decoder_path,
    decode_observation,
    is_hybrid_swap_typo_v3_only,
    is_mode_router_v3_force_disabled,
    run,
)


def test_active_decoder_path_defaults_to_hybrid(monkeypatch) -> None:
    monkeypatch.delenv("L1_INVERSE_DECODER_MODE_ROUTER_V3_FORCE_DISABLE", raising=False)
    monkeypatch.delenv("L1_INVERSE_DECODER_HYBRID_SWAP_TYPO_V3_ONLY", raising=False)
    assert active_decoder_path() == "hybrid_swap_typo_v3"
    assert is_hybrid_swap_typo_v3_only()


def test_force_disable_switches_to_v4(monkeypatch) -> None:
    monkeypatch.setenv("L1_INVERSE_DECODER_MODE_ROUTER_V3_FORCE_DISABLE", "1")
    assert active_decoder_path() == "objective_v4"
    assert is_mode_router_v3_force_disabled()


def test_forced_typo_uses_v4_under_hybrid(monkeypatch) -> None:
    monkeypatch.delenv("L1_INVERSE_DECODER_MODE_ROUTER_V3_FORCE_DISABLE", raising=False)
    monkeypatch.setenv("L1_INVERSE_DECODER_HYBRID_SWAP_TYPO_V3_ONLY", "1")
    report, _ = run(
        seed=701,
        samples=4,
        beam_size=4,
        noise_level=0.1,
        scoring_mode="enhanced",
        forced_noise_mode="typo",
    )
    assert report["decoder_path"] == "hybrid_v4_typo_oov"


def test_routed_run_reports_decoder_path(monkeypatch) -> None:
    monkeypatch.delenv("L1_INVERSE_DECODER_MODE_ROUTER_V3_FORCE_DISABLE", raising=False)
    monkeypatch.setenv("L1_INVERSE_DECODER_HYBRID_SWAP_TYPO_V3_ONLY", "0")
    report, _ = run(
        seed=701,
        samples=4,
        beam_size=4,
        noise_level=0.1,
        scoring_mode="enhanced",
        forced_noise_mode="swap_typo",
    )
    assert report["decoder_path"] == "mode_router_decoder_v3"


def test_hybrid_mixed_routes_both_arms(monkeypatch) -> None:
    monkeypatch.delenv("L1_INVERSE_DECODER_MODE_ROUTER_V3_FORCE_DISABLE", raising=False)
    monkeypatch.setenv("L1_INVERSE_DECODER_HYBRID_SWAP_TYPO_V3_ONLY", "1")
    report, _ = run(
        seed=701,
        samples=24,
        beam_size=4,
        noise_level=0.1,
        scoring_mode="enhanced",
        forced_noise_mode=None,
    )
    assert report["decoder_path"] == "hybrid_swap_typo_v3"
    routes = report.get("hybrid_route_counts") or {}
    assert routes.get("v3_swap_typo", 0) + routes.get("v4_other", 0) == 24
    assert report["exact_restore_rate"] >= 0.0


def test_decode_observation_hybrid_routes_non_order_only_to_v4(monkeypatch) -> None:
    monkeypatch.delenv("L1_INVERSE_DECODER_MODE_ROUTER_V3_FORCE_DISABLE", raising=False)
    monkeypatch.delenv("L1_INVERSE_DECODER_HYBRID_SWAP_TYPO_V3_ONLY", raising=False)
    out = decode_observation("alpha beta gamma delta", beam_size=4, seed=701)
    assert out["ok"] is True
    assert out["decoder_path"] in {"hybrid_v4_other", "hybrid_v3_swap_typo"}
    assert isinstance(out["decoded_text"], str)
