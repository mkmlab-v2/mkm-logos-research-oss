"""R-IBL morning prediction registry builder."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import build_research_morning_prediction_registry_v1 as reg  # noqa: E402


def _write(path: Path, doc: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")


def test_build_registry_collects_lenses(tmp_path: Path) -> None:
    art = tmp_path / "docs" / "final" / "artifacts"
    art.mkdir(parents=True, exist_ok=True)
    rep = tmp_path / "reports"
    rep.mkdir(parents=True, exist_ok=True)

    _write(
        art / "logos_independent_lens_latest.json",
        {"scores": {"direction_score": -0.2, "confidence": 0.5}},
    )
    _write(
        art / "myeongni_independent_lens_latest.json",
        {"scores": {"direction_score": 0.1, "confidence": 0.6}},
    )
    _write(
        art / "sasang_independent_lens_latest.json",
        {
            "scores": {"direction_score": 0.17, "confidence": 0.7},
            "sasang_stream_outputs": {"regime_hypothesis": "phase_transition", "mapping_target": "sideways"},
        },
    )
    _write(
        art / "btrack_hypothesis_prophecy_latest.json",
        {"prediction": {"instrument": "kospi", "direction": "bull", "confidence": 0.71}},
    )
    _write(
        art / "internal_kospi_morning_brief_onepager_latest.json",
        {"today_action": "WATCH", "confidence_0_100": 40},
    )
    _write(
        rep / "commander_hypothesis_stream_latest.json",
        {
            "branches": [
                {
                    "branch_id": "test_branch",
                    "trigger_ko": "트리거",
                    "predicted_bias_ko": "바이어스",
                    "confidence": "mid",
                }
            ],
            "synthesis_ko": "합성 한 줄",
        },
    )
    _write(
        rep / "subgraph_router_replay_summary_latest.json",
        {
            "rows": [{"query_id": "q01", "pass": True, "bridges_matched": 2, "paths_count": 6, "out_json": "x.json"}]
        },
    )

    doc = reg.build_registry(tmp_path, calendar_kst="2026-06-01")
    assert doc["schema"] == "research_morning_prediction_registry_v1"
    assert doc["research_only"] is True
    assert doc["n_predictions"] >= 6
    lenses = {p["lens"] for p in doc["predictions"]}
    assert "logos" in lenses
    assert "myeongni" in lenses
    assert "sasang" in lenses
    assert "price_btrack" in lenses
    latest, seal = reg.write_registry(doc, tmp_path)
    assert latest.is_file()
    assert seal.name == "2026-06-01_research_seal_v1.json"
