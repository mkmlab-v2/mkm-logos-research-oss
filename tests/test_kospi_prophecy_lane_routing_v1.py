"""KOSPI prophecy lane routing — briefing vs scoring separation."""

from __future__ import annotations

from scripts.kospi_prophecy_lane_routing_v1 import (
    BRIEFING_LANE_ID,
    SCORING_LANE_ID,
    attach_lane_routing_metadata,
    build_routing_manifest,
    lane_routing_block,
)


def test_lane_routing_block_ids():
    block = lane_routing_block()
    assert block["briefing_primary"]["lane_id"] == BRIEFING_LANE_ID
    assert block["scoring_shadow"]["lane_id"] == SCORING_LANE_ID
    assert block["briefing_primary"]["direction_merge_forbidden"] is True


def test_attach_calendar_metadata():
    doc = attach_lane_routing_metadata({"schema": "test"}, context="calendar")
    assert doc["prophecy_lane"] == SCORING_LANE_ID
    assert doc["prophecy_lane_role"] == "scoring_shadow"
    assert "do_not_confuse_ko" in doc


def test_attach_eval_metadata():
    doc = attach_lane_routing_metadata({"schema": "test"}, context="eval")
    assert doc["prophecy_lane_role"] == "scoring_shadow"
    assert doc["briefing_primary_pointer"] == "reports/mkm_parallel_advisory_brief_v1_latest.json"


def test_build_routing_manifest_schema():
    doc = build_routing_manifest(session_date="2026-06-26")
    assert doc["schema"] == "kospi_prophecy_lane_routing_v1"
    assert doc["send_gate"] == "HOLD"
    assert "artifact_pointers" in doc
