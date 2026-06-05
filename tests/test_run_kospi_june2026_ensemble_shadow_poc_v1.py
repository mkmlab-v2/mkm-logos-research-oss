"""Tests for KOSPI June ensemble shadow PoC [HYPO]."""

from __future__ import annotations

from scripts.run_kospi_june2026_ensemble_shadow_poc_v1 import _weights_with_ensemble


def test_weights_with_ensemble_scales_and_adds_mass() -> None:
    base = {
        "session_myeongni": 0.3,
        "myeongni_independent": 0.22,
        "sasang": 0.24,
        "macro": 0.24,
        "ensemble_kospi_causal": 0.0,
    }
    w = _weights_with_ensemble(base, 0.10)
    assert abs(w["ensemble_kospi_causal"] - 0.10) < 1e-6
    total = sum(w.values())
    assert abs(total - 1.0) < 0.02


def test_weights_with_zero_ensemble_unchanged_mass() -> None:
    base = {"session_myeongni": 0.5, "macro": 0.5, "ensemble_kospi_causal": 0.0}
    w = _weights_with_ensemble(base, 0.0)
    assert w["ensemble_kospi_causal"] == 0.0
    assert w["session_myeongni"] == 0.5
