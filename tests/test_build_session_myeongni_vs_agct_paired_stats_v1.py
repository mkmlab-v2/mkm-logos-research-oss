"""Smoke tests for paired AGCT vs hybrid stats builder."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def test_mcnemar_exact_symmetric() -> None:
    from scripts.build_session_myeongni_vs_agct_paired_stats_v1 import _mcnemar_exact

    m = _mcnemar_exact(50, 50)
    assert m["p_value_two_sided"] == pytest.approx(1.0, abs=1e-6)


def test_paired_stats_build_if_scores_present() -> None:
    agct = ROOT / "reports/btrack_prophecy_score_agct_market_psych_252d.json"
    hyb = ROOT / "reports/btrack_prophecy_score_hybrid_session_kospi_252d_v1.json"
    if not agct.is_file() or not hyb.is_file():
        pytest.skip("252d score JSONs not on disk")
    from scripts.build_session_myeongni_vs_agct_paired_stats_v1 import build

    doc = build(n_boot=500, seed=1)
    assert doc["schema"] == "session_myeongni_vs_agct_paired_stats_v1"
    assert doc["paired_kospi_252d"]["n_paired_days"] >= 30
    assert "p_value_two_sided" in doc["mcnemar"]
    assert doc["bootstrap_delta_hit_rate_pp"]["n_bootstrap"] == 500
