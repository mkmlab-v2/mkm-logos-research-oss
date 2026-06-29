"""Per-lens Tier2 KOSPI four-lens builders."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable


def test_sasang_veto_derives_force_hold():
    from scripts.build_sasang_lens_veto_tier2_v1 import build_sasang_tier2

    lens = {
        "scores": {"confidence": 0.71, "direction_score": 0.17},
        "sasang_stream_outputs": {
            "regime_hypothesis": "phase_transition",
            "machine_readables": {"heat_proxy": 0.585, "volatility_rarefaction_proxy": 0.48},
        },
    }
    doc = build_sasang_tier2(lens=lens, fusion=None)
    assert doc["force_hold"] is True
    assert doc["band_widen_only"] is True
    assert doc["tier2_role"] == "short_horizon_veto_band_only"


def test_field_tier2_reads_band_wf():
    from scripts.build_field_lens_vol_band_tier2_v1 import build_field_tier2

    band_wf = {
        "band_policy": {"direction_unchanged": True, "vol_band_k": 1.5, "vol_window": 5},
        "holdout_pooled": {
            "band_active": {"band_hit_rate": 0.25},
            "band_conflict_vol_widen": {"band_hit_rate": 0.4167, "direction_soft_hit_rate": 0.625},
        },
        "comparison": {"delta_conflict_vol_widen_minus_active_band_holdout": 0.1667},
        "promotion_candidate": True,
    }
    doc = build_field_tier2(band_wf=band_wf, field_graph={"node_count": 10})
    assert doc["gating_eligible"] is True
    assert doc["holdout_metrics"]["delta_vol_widen_minus_active"] == 0.1667


def test_logos_tier2_non_gating():
    from scripts.build_logos_lens_conflict_digest_tier2_v1 import build_logos_tier2

    doc = build_logos_tier2(
        graphrag={"paths": [{"path_id": "p1", "match_score": 2, "steps": ["Job.20.22"], "note_ko": "x"}]},
        crosswalk={"schema": "x"},
        fusion={"fusion_resolution": {"conflict_ids": ["field_bear_vs_lens_bull_majority"]}, "lenses": {"logos": {}}},
        lens={"scores": {"direction_score": -0.3, "confidence": 0.2}},
    )
    assert doc["non_gating"] is True
    assert doc["gating_weight"] == 0.0
    assert len(doc["excess_unwind_routes"]) == 1


@pytest.mark.skipif(
    not (ROOT / "reports/kospi_four_lens_conflict_band_coverage_wf_v1_latest.json").is_file(),
    reason="band wf artifact missing",
)
def test_per_lens_tier2_chain_exit_zero():
    cp = subprocess.run(
        [PY, "scripts/run_kospi_four_lens_per_lens_tier2_chain_v1.py", "--skip-premium"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=180,
    )
    assert cp.returncode == 0, cp.stderr + cp.stdout
    fusion = json.loads((ROOT / "reports/kospi_four_lens_graphrag_fusion_v1_latest.json").read_text(encoding="utf-8-sig"))
    assert "tier2" in fusion.get("field", {}) or "tier2" in (fusion.get("lenses") or {}).get("logos", {})
