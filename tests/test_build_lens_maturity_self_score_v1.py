"""Lens maturity self-score builder."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from build_lens_maturity_self_score_v1 import build_lens_maturity_self_score, write_lens_maturity_self_score  # noqa: E402
from build_telegram_four_lens_reports_v1 import build_synthesis_report  # noqa: E402


def test_build_lens_maturity_schema_and_composites(tmp_path: Path) -> None:
    art = tmp_path / "docs" / "final" / "artifacts"
    art.mkdir(parents=True, exist_ok=True)
    (art / "myeongni_stage2_realset_gate_latest.json").write_text(
        json.dumps({"pass": True}), encoding="utf-8"
    )
    (art / "independent_lens_shadow_gate_latest.json").write_text(
        json.dumps({"decision": "KEEP_OBSERVATION_ONLY"}), encoding="utf-8"
    )
    (art / "logos_independent_lens_latest.json").write_text(
        json.dumps({"provenance": {"input_path": "sample.json"}}), encoding="utf-8"
    )
    (art / "logos_rag_btrack_promotion_gate_v1_latest.json").write_text(
        json.dumps({"tiers": {"L2_track_c_shadow_ingest": {"passed": True}}}), encoding="utf-8"
    )
    (art / "prophecy_logos_revalidation_oos_gate_latest.json").write_text(
        json.dumps({"gate": {"go": True}, "oos_metrics": {"directional_hit_rate_active": 0.53}}),
        encoding="utf-8",
    )
    (art / "sasang12_promotion_candidate_gate_latest.json").write_text(
        json.dumps({"status": "PASS"}), encoding="utf-8"
    )
    (art / "sasang_4agent_promotion_gate_latest.json").write_text(
        json.dumps({"decision": "HOLD", "checks": {"fusion_gate_pass": False}}), encoding="utf-8"
    )
    (art / "sasang_high_reliability_gate_latest.json").write_text(
        json.dumps({"decision": "PASS"}), encoding="utf-8"
    )
    (tmp_path / "reports").mkdir(parents=True, exist_ok=True)
    (tmp_path / "reports" / "myeongni_lens_observation_report_v1_latest.json").write_text(
        json.dumps(
            {
                "schema": "myeongni_lens_observation_report_v1",
                "separation_contract_ok": True,
                "not_hit_rate_proof": True,
                "gates": {"stage2_realset_pass": True, "promotion_status": "PASS"},
                "snapshots": {"market_direction_score": 0.0},
                "warnings": [],
            }
        ),
        encoding="utf-8",
    )
    doc = build_lens_maturity_self_score(tmp_path)
    assert doc["schema"] == "lens_maturity_self_score_v2"
    assert doc["research_only"] is True
    assert set(doc["lenses"].keys()) == {"myeongni", "logos", "sasang"}
    assert doc["lenses"]["myeongni"]["axes"]["D_validation"] >= 7.0
    assert doc["lenses"]["logos"]["composite_10"] == 8.0
    assert "렌즈 고도화" in doc["telegram_synthesis_block_ko"]


def test_synthesis_includes_maturity_block(tmp_path: Path) -> None:
    write_lens_maturity_self_score(tmp_path)
    for name in (
        "global_market_overnight_signals_v1_latest.json",
        "btrack_hypothesis_prophecy_latest.json",
        "trading_go_no_go_latest.json",
        "myeongni_independent_lens_latest.json",
        "logos_independent_lens_latest.json",
        "sasang_independent_lens_latest.json",
        "independent_lens_shadow_gate_latest.json",
    ):
        p = tmp_path / "docs" / "final" / "artifacts" / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("{}", encoding="utf-8")
    text = build_synthesis_report(tmp_path)
    assert "렌즈 고도화" in text
    assert "명리" in text and "성경" in text and "사상" in text
