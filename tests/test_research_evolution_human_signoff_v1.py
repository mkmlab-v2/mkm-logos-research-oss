"""R-IBL human sign-off and evolution apply."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.research_evolution_human_signoff_v1 import (
    build_signoff_record,
    proposal_id,
    validate_signoff,
    write_signoff,
)
from scripts.run_commander_briefing_evolution_v1 import apply_approved_proposals, run_evolution


def test_proposal_id_branch_and_lens() -> None:
    assert proposal_id({"branch_id": "x", "action": "boost"}) == "branch:x:boost"
    assert proposal_id({"lens": "logos", "kind": "graphrag_path_hit", "action": "demote"}) == (
        "lens:logos:graphrag_path_hit:demote"
    )


def test_validate_signoff_approved(tmp_path: Path) -> None:
    doc = build_signoff_record(
        decision="APPROVED",
        actor="commander",
        approved_proposal_ids=["branch:a:boost_confidence_cap"],
    )
    path = write_signoff(doc, tmp_path / "signoff.json")
    assert validate_signoff(path) == []


def test_apply_approved_proposals_writes_rules(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    rules = tmp_path / "rules.json"
    rules.write_text(
        json.dumps(
            {
                "schema": "commander_briefing_evolution_rules_v1",
                "max_delta_per_week": 0.05,
                "branch_confidence_adjustments": {},
                "lens_kind_adjustments": {},
            }
        ),
        encoding="utf-8",
    )
    signoff = build_signoff_record(
        decision="APPROVED",
        actor="commander",
        approved_proposal_ids=["lens:logos:graphrag_path_hit:boost_logos_graphrag_path_hit"],
    )
    signoff_path = write_signoff(signoff, tmp_path / "signoff.json")

    evolution = {
        "proposals": [
            {
                "proposal_id": "lens:logos:graphrag_path_hit:boost_logos_graphrag_path_hit",
                "lens": "logos",
                "kind": "graphrag_path_hit",
                "action": "boost_logos_graphrag_path_hit",
                "proposed_delta": 0.05,
            }
        ]
    }
    report = apply_approved_proposals(evolution, signoff_path, rules_path=rules)
    assert report["applied_count"] == 1
    saved = json.loads(rules.read_text(encoding="utf-8"))
    assert saved["lens_kind_adjustments"]["logos:graphrag_path_hit"] == 0.05
