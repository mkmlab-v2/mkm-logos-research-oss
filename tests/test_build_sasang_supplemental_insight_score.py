from __future__ import annotations

import json
from pathlib import Path

from scripts import build_sasang_supplemental_insight_score as mod


def _write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def test_build_supplemental_score_non_gating(tmp_path: Path, monkeypatch) -> None:
    dna = tmp_path / "dna.json"
    sentiment = tmp_path / "sentiment.json"
    gem = tmp_path / "gem.json"
    out = tmp_path / "score.json"

    _write(
        dna,
        {
            "approval_status": "APPROVED",
            "scope": {
                "promotion_level": "CANDIDATE_READY_CONFIRMED",
                "operational_constraint": "human_review_required_for_any_live_promotion",
            },
        },
    )
    _write(
        sentiment,
        {
            "decision": "HOLD",
            "week_contract": {"signals": {"sentiment": {"value": "safe", "quality_flag": "ok"}}},
            "risk_signals": {"high_reliability_decision": "PASS"},
        },
    )
    _write(
        gem,
        {
            "research_only": True,
            "summary": {
                "point_count": 5,
                "mean_coupling_strength": 0.7,
                "execution_policy": "analysis_only_non_trigger",
            },
        },
    )

    monkeypatch.setattr(
        "sys.argv",
        [
            "build_sasang_supplemental_insight_score.py",
            "--dna",
            str(dna),
            "--market-sentiment",
            str(sentiment),
            "--gematria-4d",
            str(gem),
            "--out",
            str(out),
        ],
    )
    assert mod.main() == 0
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["non_gating_policy"] is True
    assert float(doc["supplemental_score"]["value"]) > 0.7
    assert doc["supplemental_score"]["impact_on_go_no_go"] == "none_non_gating"
