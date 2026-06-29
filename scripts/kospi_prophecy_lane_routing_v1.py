#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""KOSPI prophecy lane routing SSOT — briefing vs scoring separation [HYPO]."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

ROUTING_ART = ROOT / "docs/final/artifacts/kospi_prophecy_lane_routing_v1_latest.json"
ROUTING_REPORT = ROOT / "reports/kospi_prophecy_lane_routing_v1_latest.json"

BRIEFING_HOOK = "scripts/run_kospi_evening_briefing_chain_v1.py"
PARALLEL_ADVISORY_HOOK = "scripts/run_mkm_parallel_advisory_chain_v1.py"
PREMIUM_HOOK = "scripts/build_premium_btrack_multilens_report_v1.py"
SCORING_CALENDAR_HOOK = "scripts/build_kospi_june2026_daily_prophecy_calendar_v1.py"
SCORING_EVAL_HOOK = "scripts/eval_kospi_june2026_daily_prophecy_v1.py"

BRIEFING_LANE_ID = "briefing_primary_parallel_advisory_graphrag"
SCORING_LANE_ID = "scoring_shadow_weighted_blend_v2"

DO_NOT_CONFUSE_KO = (
    "브리핑 본선=성경·명리·사상·Science GraphRAG 병렬 통찰(parallel_advisory). "
    "채점 그림자=가중 블렌드(v2_lens3_heavy) 방향 HR — 두 레일 혼동·direction merge 금지."
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def lane_routing_block() -> dict[str, Any]:
    return {
        "schema": "kospi_prophecy_lane_routing_v1",
        "briefing_primary": {
            "lane_id": BRIEFING_LANE_ID,
            "mode": "parallel_advisory_graphrag",
            "contract": "docs/final/MKM_PARALLEL_ADVISORY_LENS_CONTRACT_V1.md",
            "evening_hook": BRIEFING_HOOK,
            "parallel_advisory_hook": PARALLEL_ADVISORY_HOOK,
            "premium_multilens_hook": PREMIUM_HOOK,
            "outputs": {
                "parallel_advisory_brief": "reports/mkm_parallel_advisory_brief_v1_latest.json",
                "four_lens_fusion_md": "reports/kospi_four_lens_graphrag_fusion_v1_latest.md",
                "premium_report": "reports/premium_btrack_multilens_report_v1_latest.json",
                "evening_briefing_chain": "reports/kospi_evening_briefing_chain_v1_latest.json",
            },
            "direction_merge_forbidden": True,
            "send_gate": "HOLD",
            "note_ko": "지휘관 통찰 본선 — 렌즈별 GraphRAG slice + coordinator advisory_ko",
        },
        "scoring_shadow": {
            "lane_id": SCORING_LANE_ID,
            "mode": "weighted_blend_v2_lens3_heavy",
            "calendar_hook": SCORING_CALENDAR_HOOK,
            "eval_hook": SCORING_EVAL_HOOK,
            "active_arm": "v2_lens3_heavy",
            "outputs": {
                "calendar": "reports/kospi_{yyyymm}_daily_prophecy_calendar_v1.json",
                "eval": "reports/kospi_june2026_daily_prophecy_eval_latest.json",
            },
            "note_ko": "연구 채점·shadow KPI 전용 — 브리핑 본선 아님. apply·Track A 금지.",
        },
        "do_not_confuse_ko": DO_NOT_CONFUSE_KO,
    }


def attach_lane_routing_metadata(doc: dict[str, Any], *, context: str) -> dict[str, Any]:
    """Annotate calendar/eval artifacts so readers know which lane they belong to."""
    block = lane_routing_block()
    if context == "calendar":
        doc["prophecy_lane"] = SCORING_LANE_ID
        doc["prophecy_lane_role"] = "scoring_shadow"
        doc["briefing_primary_pointer"] = block["briefing_primary"]["outputs"]["parallel_advisory_brief"]
    elif context == "eval":
        doc["prophecy_lane"] = SCORING_LANE_ID
        doc["prophecy_lane_role"] = "scoring_shadow"
        doc["briefing_primary_pointer"] = block["briefing_primary"]["outputs"]["parallel_advisory_brief"]
    else:
        doc["prophecy_lane_role"] = context
    doc["lane_routing_contract"] = str(ROUTING_ART.relative_to(ROOT)).replace("\\", "/")
    doc["do_not_confuse_ko"] = DO_NOT_CONFUSE_KO
    return doc


def build_routing_manifest(
    *,
    session_date: str | None = None,
    evening_chain_doc: dict[str, Any] | None = None,
) -> dict[str, Any]:
    block = lane_routing_block()
    pointers: dict[str, Any] = {}
    for key, rel in block["briefing_primary"]["outputs"].items():
        p = ROOT / rel
        pointers[key] = {
            "path": rel,
            "exists": p.is_file(),
            "mtime_utc": datetime.fromtimestamp(p.stat().st_mtime, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            if p.is_file()
            else None,
        }
    return {
        **block,
        "generated_at_utc": _utc_now(),
        "session_date_kst": session_date,
        "hypothesis_tier": "B",
        "research_only": True,
        "send_gate": "HOLD",
        "auto_apply": False,
        "track_a_go": False,
        "artifact_pointers": pointers,
        "evening_chain_last": evening_chain_doc,
        "reproduce_evening": f"py {BRIEFING_HOOK} --session-date {session_date or 'YYYY-MM-DD'}",
        "reproduce_briefing_only": f"py {PARALLEL_ADVISORY_HOOK} --domain finance --session-date {session_date or 'YYYY-MM-DD'}",
    }
