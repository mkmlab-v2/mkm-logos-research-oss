"""ingest_magic_orb_path_feedback_to_ledger_v1 — feedback JSONL → path ledger."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.ingest_magic_orb_path_feedback_to_ledger_v1 import (
    ingest_feedback_rows,
    router_matches_feedback,
    validate_feedback_row,
)
from scripts.logos_query_path_ledger_v1 import _query_hash16

ROOT = Path(__file__).resolve().parents[1]


def _router() -> dict:
    return {
        "query": "위기 가운데 언약의 안정과 신실",
        "paths": [
            {
                "path_id": "path_hesed_covenant",
                "steps": ["concept:x", "Ps.89.28"],
                "rank_score": 5100.0,
            },
            {
                "path_id": "path_new_covenant",
                "steps": ["concept:x", "Jer.31.33"],
                "rank_score": 5000.0,
            },
        ],
    }


def _feedback(vote: str = "UP", path_id: str | None = None) -> dict:
    q = "위기 가운데 언약의 안정과 신실"
    row = {
        "schema": "magic_orb_path_feedback_v1",
        "event_id": f"mopf_test_{vote.lower()}",
        "ts_utc": "2026-06-22T08:00:00Z",
        "vote": vote,
        "query_hash": _query_hash16(q),
        "query_redacted": q,
        "query_id": "q01",
        "surface": "magic_orb_report",
        "hypothesis_tier": "B",
        "research_only": True,
        "non_gating": True,
        "preview_only": True,
        "user_id": "test-user",
    }
    if path_id:
        row["selected_path_id"] = path_id
    return row


def test_feedback_row_validates() -> None:
    assert validate_feedback_row(_feedback()) == []


def test_router_matches_feedback_by_hash() -> None:
    router = _router()
    fb = _feedback()
    assert router_matches_feedback(router, fb) is True
    fb_bad = {**fb, "query_hash": "0" * 16}
    assert router_matches_feedback(router, fb_bad) is False


def test_ingest_appends_up_vote(tmp_path: Path) -> None:
    state = {"processed_event_ids": []}
    result = ingest_feedback_rows(
        feedback_rows=[_feedback("UP")],
        router_doc=_router(),
        router_path=tmp_path / "router.json",
        chain_path=None,
        insight_path=None,
        state=state,
        workspace_root=tmp_path,
        dry_run=False,
    )
    assert result["appended_count"] == 1
    latest = tmp_path / "reports/logos_query_path_ledger_v1_latest.jsonl"
    assert latest.is_file()
    row = json.loads(latest.read_text(encoding="utf-8").strip())
    assert row["feedback"]["vote"] == "UP"
    assert row["retrieval"]["selected_path_id"] == "path_hesed_covenant"


def test_ingest_honors_selected_path_id(tmp_path: Path) -> None:
    state = {"processed_event_ids": []}
    ingest_feedback_rows(
        feedback_rows=[_feedback("DOWN", path_id="path_new_covenant")],
        router_doc=_router(),
        router_path=tmp_path / "router.json",
        chain_path=None,
        insight_path=None,
        state=state,
        workspace_root=tmp_path,
        dry_run=False,
    )
    latest = tmp_path / "reports/logos_query_path_ledger_v1_latest.jsonl"
    row = json.loads(latest.read_text(encoding="utf-8").strip())
    assert row["feedback"]["vote"] == "DOWN"
    assert row["retrieval"]["selected_path_id"] == "path_new_covenant"
