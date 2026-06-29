"""logos_query_path_ledger_v1 — validate, build from router, append."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.logos_query_path_ledger_v1 import (
    append_logos_query_path_ledger_line,
    build_entry_from_router,
    validate_jsonl_file,
    validate_logos_query_path_ledger_record,
)

ROOT = Path(__file__).resolve().parents[1]
ROUTER_FIXTURE = ROOT / "reports/question_logos_subgraph_router_sidecar_v1_latest.json"
SAMPLE = ROOT / "reports/logos_query_path_ledger_v1.sample.jsonl"


def _minimal_router() -> dict:
    return {
        "schema": "logos_subgraph_graphrag_router_v1",
        "version": "2.0.2",
        "query": "위기 가운데 언약의 안정",
        "paths": [
            {
                "path_id": "path_hesed_covenant",
                "steps": [
                    "concept:covenant_stability_crisis",
                    "function:steadfast_love",
                    "lemma:hebrew:hesed_proxy",
                    "Ps.89.28",
                ],
                "rank_score": 5100.0,
            },
            {
                "path_id": "path_new_covenant",
                "steps": [
                    "concept:covenant_stability_crisis",
                    "function:new_covenant_heart",
                    "Jer.31.33",
                ],
                "rank_score": 5000.0,
            },
        ],
    }


def test_build_entry_from_router_path_centric() -> None:
    entry = build_entry_from_router(_minimal_router(), query_id="q_test")
    assert validate_logos_query_path_ledger_record(entry) == []
    assert entry["retrieval"]["selected_path_id"] == "path_hesed_covenant"
    assert entry["retrieval"]["selected_steps"][0].startswith("concept:")
    assert "Ps.89.28" in entry["retrieval"]["verse_ids"]
    assert entry["governance"]["send_gate"] == "HOLD"
    assert entry["feedback"]["vote"] == "NONE"


def test_build_entry_rejects_empty_paths() -> None:
    with pytest.raises(ValueError, match="paths empty"):
        build_entry_from_router({"query": "x", "paths": []})


def test_sample_jsonl_validates_when_present() -> None:
    if not SAMPLE.is_file():
        pytest.skip("sample not generated yet")
    assert validate_jsonl_file(SAMPLE) >= 1


def test_append_writes_daily_and_latest(tmp_path: Path) -> None:
    entry = build_entry_from_router(_minimal_router(), query_id="append_test")
    out = append_logos_query_path_ledger_line(tmp_path, entry)
    assert out.exists()
    assert out.name.startswith("logos_query_path_ledger_v1_")
    latest = tmp_path / "reports/logos_query_path_ledger_v1_latest.jsonl"
    assert latest.is_file()
    assert validate_jsonl_file(out) == 1


def test_real_router_fixture_builds_when_present() -> None:
    if not ROUTER_FIXTURE.is_file():
        pytest.skip("router sidecar missing")
    router = json.loads(ROUTER_FIXTURE.read_text(encoding="utf-8-sig"))
    entry = build_entry_from_router(router, query_id="fixture")
    assert validate_logos_query_path_ledger_record(entry) == []
    assert len(entry["retrieval"]["candidate_path_ids"]) >= 1


def test_contribution_scores_aggregate() -> None:
    from scripts.build_logos_path_contribution_scores_v1 import build_contribution_scores_doc

    up = build_entry_from_router(_minimal_router(), vote="UP")
    down = build_entry_from_router(_minimal_router(), vote="DOWN", selected_path_index=1)
    doc = build_contribution_scores_doc([up, down])
    assert doc["send_gate"] == "HOLD"
    assert doc["paths"]["path_hesed_covenant"]["up_votes"] == 1
    assert doc["paths"]["path_new_covenant"]["down_votes"] == 1
