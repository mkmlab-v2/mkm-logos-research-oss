"""Tests for MKM parallel advisory brief v1."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable


@pytest.fixture
def fusion_minimal() -> dict:
    return {
        "session_anchor": "2026-06-23",
        "field": {"direction_sign": "bear", "layer": "field"},
        "lenses": {
            "sasang": {"lens_id": "sasang", "direction_sign": "bull", "non_gating": True},
            "myeongni": {"lens_id": "myeongni", "direction_sign": "bull", "non_gating": True},
            "logos": {"lens_id": "logos", "direction_sign": "bear", "non_gating": True},
        },
        "fusion_resolution": {"conflict_ids": ["field_bear_vs_lens_bull_majority"]},
    }


def test_resolve_active_lenses_exclude():
    from scripts.mkm_parallel_advisory_lens_v1 import load_manifest, resolve_active_lenses

    manifest = load_manifest()
    active, excluded = resolve_active_lenses(manifest, domain_id="finance", exclude_lenses=["logos"])
    assert "logos" not in active
    assert any(e.get("lens_id") == "logos" for e in excluded)


def test_build_parallel_advisory_brief_schema(fusion_minimal):
    from scripts.mkm_parallel_advisory_lens_v1 import build_parallel_advisory_brief, load_manifest

    brief = build_parallel_advisory_brief(
        manifest=load_manifest(),
        fusion=fusion_minimal,
        domain_id="finance",
    )
    assert brief["schema"] == "mkm_parallel_advisory_brief_v1"
    assert brief.get("schema_rev") == "1.1"
    assert brief["send_gate"] == "HOLD"
    assert brief["track_a_go"] is False
    assert "science" in brief["parallel_lens_slices"]
    assert brief["balance_doctrine"]["no_lens_supremacy"] is True
    assert "merged_trade_direction" in (brief.get("forbidden") or [])
    assert brief.get("epistemic_wiring_ok") is True
    assert "execution_plane" in brief
    assert "in_sample_narrative" in brief
    assert brief["in_sample_narrative"]["gating_eligible"] is False
    assert "epistemic_moat" in brief
    assert "MKM_LENS_ONTOLOGY_CONSTITUTION_V1.md" in brief["epistemic_moat"].get("ontology", "")


def test_humanist_slices_non_gating(fusion_minimal):
    from scripts.mkm_parallel_advisory_lens_v1 import build_parallel_advisory_brief, load_manifest

    brief = build_parallel_advisory_brief(manifest=load_manifest(), fusion=fusion_minimal)
    for lid in ("sasang", "myeongni", "logos"):
        sl = brief["parallel_lens_slices"][lid]
        assert sl["in_sample_narrative"] is True
        assert sl["gating_eligible"] is False
        assert sl["non_gating"] is True
    ep = brief["execution_plane"]
    assert ep["field_signal"]["gating_eligible"] is True
    assert ep["science_signal"]["gating_eligible"] is False


def test_sasang_interpretive_bundle_enrichment_on_brief(fusion_minimal):
    from scripts.mkm_parallel_advisory_lens_v1 import build_parallel_advisory_brief, load_manifest

    bundle_path = ROOT / "docs/final/artifacts/sasang_interpretive_insight_bundle_v1_latest.json"
    if not bundle_path.is_file():
        pytest.skip("sasang interpretive bundle missing on disk")

    brief = build_parallel_advisory_brief(manifest=load_manifest(), fusion=fusion_minimal)
    sasang = brief["parallel_lens_slices"]["sasang"]
    enrichment = sasang.get("interpretive_bundle_enrichment")
    assert isinstance(enrichment, dict)
    assert enrichment.get("schema") == "sasang_interpretive_advisory_enrichment_v1"
    assert enrichment.get("send_gate") == "HOLD"
    assert enrichment.get("gating_eligible") is False
    syn = enrichment.get("synthesis_v1") or {}
    assert syn.get("forbidden_synthesis_ko")
    assert brief["interpretive_bundle_pointers"]["sasang"]
    assert brief["upstream_pointers"]["sasang_interpretive_bundle"]


def test_build_sasang_interpretive_advisory_enrichment_minimal():
    from scripts.mkm_parallel_advisory_lens_v1 import build_sasang_interpretive_advisory_enrichment

    out = build_sasang_interpretive_advisory_enrichment(
        {
            "version": "1.7.0",
            "rail": "B_TRACK",
            "decision_authority": "human_only",
            "synthesis_v1": {"forbidden_synthesis_ko": "test forbidden"},
            "sections": [
                {
                    "pyobyeong_dr_pointer_v1": {
                        "highlight_card_ids": ["IC-08", "IC-09"],
                        "send_gate": "HOLD",
                    }
                }
            ],
        }
    )
    assert out is not None
    assert out["pyobyeong_dr_pointer_v1"]["highlight_card_ids"] == ["IC-08", "IC-09"]


def test_validate_epistemic_wiring_catches_gating_leak():
    from scripts.mkm_parallel_advisory_lens_v1 import validate_epistemic_wiring

    bad = {
        "in_sample_narrative": {"gating_eligible": True},
        "execution_plane": {"science_signal": {"gating_eligible": True}},
        "parallel_lens_slices": {"sasang": {"gating_eligible": True}},
    }
    errs = validate_epistemic_wiring(bad)
    assert len(errs) >= 2


def test_build_parallel_advisory_honest_conflict(fusion_minimal):
    from scripts.mkm_parallel_advisory_lens_v1 import build_parallel_advisory_brief, load_manifest

    brief = build_parallel_advisory_brief(manifest=load_manifest(), fusion=fusion_minimal)
    cs = brief["conflict_surface"]
    assert cs["perspectives_disagree"] is True
    assert "옳은" in cs["verdict_ko"] or "불일치" in cs["verdict_ko"]


def test_physics_corpus_seed_includes_science_slice():
    from scripts.mkm_parallel_advisory_lens_v1 import build_parallel_advisory_brief, load_manifest

    fusion = {"session_anchor": "2026-01-01", "field": {}, "lenses": {"logos": {"direction_sign": "neutral"}}}
    brief = build_parallel_advisory_brief(
        manifest=load_manifest(), fusion=fusion, domain_id="physics"
    )
    science = brief.get("parallel_lens_slices", {}).get("science")
    assert science is not None
    assert science.get("status") == "corpus_seed_v1"
    assert int(science.get("anchor_count") or 0) >= 2
    reasons = [e.get("reason") for e in brief.get("excluded_lenses", [])]
    assert "science_pack_stub_hold" not in reasons


@pytest.mark.skipif(
    not (ROOT / "reports/kospi_four_lens_graphrag_fusion_v1_latest.json").is_file(),
    reason="fusion artifact missing",
)
def test_run_parallel_advisory_chain_exit_zero():
    r = subprocess.run(
        [PY, "scripts/run_mkm_parallel_advisory_chain_v1.py", "--skip-fusion"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stderr
    out = ROOT / "reports/mkm_parallel_advisory_brief_v1_latest.json"
    doc = json.loads(out.read_text(encoding="utf-8-sig"))
    assert doc["schema"] == "mkm_parallel_advisory_brief_v1"
    assert doc["domain_id"] == "finance"
