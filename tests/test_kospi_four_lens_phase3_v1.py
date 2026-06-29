"""Phase-3 KOSPI four-lens GraphRAG: shock ablation · science merge · myeongni router."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable


def test_shock_ablation_schema_and_arms():
    from scripts.run_kospi_four_lens_shock_conditional_ablation_v1 import run_shock_ablation

    eval_doc = {
        "rows": [
            {
                "session_date": "2026-06-23",
                "actual_direction": "bear",
                "predicted_direction": "neutral",
                "daily_return_pct": -7.18,
                "outcome": "MISS",
            },
            {
                "session_date": "2026-06-16",
                "actual_direction": "bull",
                "predicted_direction": "bull",
                "daily_return_pct": 0.5,
                "outcome": "HIT",
            },
        ]
    }
    fusion = {
        "field": {"direction_sign": "bear", "daily_return_pct": -7.18},
        "lenses": {"logos": {"direction_sign": "bear"}},
        "fusion_resolution": {"conflict_ids": ["field_bear_vs_lens_bull_majority"]},
    }
    doc = run_shock_ablation(eval_doc, fusion, shock_return_pct=5.0, prior_shock_pct=-6.0)
    assert doc["schema"] == "kospi_four_lens_shock_conditional_ablation_v1"
    assert "active" in doc["arms"]
    assert "fusion_shock_only" in doc["arms"]
    assert doc["arms"]["fusion_shock_only"]["shock_days"] >= 1


def test_myeongni_corpus_router_builds_paths():
    from scripts.build_myeongni_corpus_graphrag_router_v1 import build_router

    doc = build_router(
        query="코스피 급락 명리 중기",
        chunk_table=ROOT / "data/corpus/ijeoma/_inventory/IJEOMA_CHUNK_TABLE_2026-03-29.jsonl",
        state_probe=ROOT / "data/myeongni/16_STATE_MASTER_PROBE_v1.json",
        myeongni_lens=ROOT / "docs/final/artifacts/myeongni_independent_lens_latest.json",
        top_k=3,
    )
    assert doc["lens_id"] == "myeongni"
    assert len(doc["paths"]) >= 1
    assert doc["policy"]["send_gate"] == "HOLD"
    chunk_paths = [p for p in doc["paths"] if p.get("chunk_id")]
    assert chunk_paths, "expected corpus chunk paths"
    assert all(p.get("match_score", 0) > 0 for p in chunk_paths)
    top_chunk = chunk_paths[0].get("chunk_id", "")
    assert "XM" in top_chunk or "xingming" in str(chunk_paths[0].get("steps", []))


def test_myeongni_corpus_router_cjk_query_terms():
    from scripts.build_myeongni_corpus_graphrag_router_v1 import build_router

    doc = build_router(
        query="天時 世會 人倫 중기 관측",
        chunk_table=ROOT / "data/corpus/ijeoma/_inventory/IJEOMA_CHUNK_TABLE_2026-03-29.jsonl",
        state_probe=ROOT / "data/myeongni/16_STATE_MASTER_PROBE_v1.json",
        myeongni_lens=ROOT / "docs/final/artifacts/myeongni_independent_lens_latest.json",
        top_k=5,
    )
    chunk_paths = [p for p in doc["paths"] if p.get("chunk_id")]
    assert chunk_paths
    assert max(p["match_score"] for p in chunk_paths) >= 2


def test_render_shock_ablation_md_table():
    from scripts.build_premium_btrack_multilens_report_v1 import render_shock_ablation_md

    doc = {
        "arms": {
            "active": {"n_scored": 10, "shock_days": 2, "soft_hit_rate": 0.5},
            "fusion_always": {"n_scored": 10, "shock_days": 2, "soft_hit_rate": 0.4},
            "fusion_shock_only": {"n_scored": 10, "shock_days": 2, "soft_hit_rate": 0.55},
        },
        "comparison": {"delta_shock_only_minus_active": 0.05},
        "promotion_candidate": True,
        "verdict_ko": "test",
        "shock_thresholds": {"abs_return_pct": 5.0, "prior_kospi_pct": -6.0},
    }
    md = render_shock_ablation_md(doc)
    assert "## Shock-conditional fusion ablation" not in md  # section header is in render_package_md
    assert "| `active` |" in md
    assert "| `fusion_shock_only` |" in md
    assert "0.5500" in md


def test_fusion_myeongni_graphrag_router_pointer():
    from scripts.build_kospi_four_lens_graphrag_fusion_v1 import build_pack

    pack = build_pack(
        logos_graphrag=ROOT / "reports/logos_graphrag_kospi9000_excess_v1_latest.json",
        logos_crosswalk=ROOT / "reports/kospi_june2026_logos_anchor_crosswalk_v1_latest.json",
        logos_lens=ROOT / "docs/final/artifacts/logos_independent_lens_latest.json",
        myeongni_lens=ROOT / "docs/final/artifacts/myeongni_independent_lens_latest.json",
        sasang_lens=ROOT / "docs/final/artifacts/sasang_independent_lens_latest.json",
        overnight=ROOT / "docs/final/artifacts/global_market_overnight_signals_v1_latest.json",
        eval_json=ROOT / "reports/kospi_june2026_daily_prophecy_eval_latest.json",
        calendar_json=ROOT / "reports/kospi_202606_daily_prophecy_calendar_v1.json",
        cross_fusion=ROOT / "docs/final/artifacts/cross_lens_rag_fusion_latest.json",
        seed_my=ROOT / "data/btrack/lens_graphrag/kospi_tail_myeongni_hypo_v1.seed.json",
        seed_sa=ROOT / "data/btrack/lens_graphrag/kospi_tail_sasang_hypo_v1.seed.json",
        seed_fi=ROOT / "data/btrack/lens_graphrag/kospi_tail_field_events_hypo_v1.seed.json",
        myeongni_corpus_router=ROOT / "reports/btrack_lens_graphrag_myeongni_corpus_v1_latest.json",
    )
    my = pack["lenses"]["myeongni"]
    router = my.get("graphrag_router")
    if (ROOT / "reports/btrack_lens_graphrag_myeongni_corpus_v1_latest.json").is_file():
        assert router is not None
        assert "pointer" in router
        assert router.get("send_gate") == "HOLD"
    else:
        assert router is None


@pytest.mark.skipif(
    not (ROOT / "reports/kospi_june2026_daily_prophecy_eval_latest.json").is_file(),
    reason="eval artifact missing",
)
def test_shock_ablation_cli_exit_zero():
    cp = subprocess.run(
        [PY, "scripts/run_kospi_four_lens_shock_conditional_ablation_v1.py"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=60,
    )
    assert cp.returncode == 0
    out = ROOT / "reports/kospi_four_lens_shock_conditional_ablation_v1_latest.json"
    assert out.is_file()
    doc = json.loads(out.read_text(encoding="utf-8-sig"))
    assert "comparison" in doc
