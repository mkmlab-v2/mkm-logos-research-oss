"""Autonomous evolution loop draft v1 — commander_hypothesis rail smoke."""

from __future__ import annotations

import json
from pathlib import Path

import scripts.run_autonomous_evolution_loop_draft_v1 as evo

ROOT = Path(__file__).resolve().parents[1]


def test_autonomous_evolution_loop_draft_writes_schema(tmp_path: Path) -> None:
    scores = {
        "schema": "commander_hypothesis_branch_scores_v1",
        "hypothesis_calendar_kst": "2026-05-22",
        "market_direction": "down",
        "market_return_pct": -0.5,
        "summary": {"n_branches": 4, "aligned": 1, "partial": 1, "neutral": 2},
        "branch_scores": [],
    }
    scores_path = tmp_path / "scores.json"
    scores_path.write_text(json.dumps(scores), encoding="utf-8")
    out = tmp_path / "draft.json"

    doc = evo.run_loop(
        rail="commander_hypothesis",
        dry_run=True,
        gate_profile="none",
        scores_path=scores_path,
    )
    assert doc["schema"] == "autonomous_evolution_loop_draft_v1"
    assert doc["dry_run"] is True
    assert doc["rail"] == "commander_hypothesis"
    assert doc["rounds"][0]["step2_proposal"]["status"] == "skipped_v1_dry_run"


def test_score_branch_outcomes() -> None:
    import scripts.score_commander_hypothesis_branches_v1 as sc

    br = sc._score_branch(
        {"branch_id": "expr_vs_cautious_market", "collision_tags": []},
        market_direction="down",
        market_tone="caution",
    )
    assert br["outcome"] == "aligned"
