"""Prophecy lens lane ops board smoke."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def test_lane_ops_board_schema_and_lanes() -> None:
    out = ROOT / "reports/prophecy_lens_lane_ops_board_v1_latest.json"
    if not out.is_file():
        proc = subprocess.run(
            [sys.executable, str(ROOT / "scripts/build_prophecy_lens_lane_ops_board_v1.py")],
            cwd=str(ROOT),
            timeout=60,
        )
        assert proc.returncode == 0
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc.get("schema") == "prophecy_lens_lane_ops_board_v1"
    assert (doc.get("protocol_harmonization_phase1") or {}).get("present") is True
    assert doc.get("version") == "1.3.0"
    assert (doc.get("narrative_knowledge_map") or {}).get("present") is True
    assert (doc.get("personadiary_logos_sidebar") or {}).get("present") is True
    assert doc.get("ok") is True
    lanes = doc.get("lanes") or {}
    assert lanes.get("quant", {}).get("strategy_id") == "science+sasang"
    assert lanes.get("quant", {}).get("logos_vote_mode") == "omit"
    assert lanes.get("persona_diary", {}).get("prophecy_vote") == "off"
    assert lanes.get("fabba_sidecar", {}).get("vote_participation") == "none"
    assert lanes.get("oracle", {}).get("logos", {}).get("non_gating") is True
    avoid_ids = {a.get("id") for a in doc.get("avoid") or []}
    assert "science_logos_blend" in avoid_ids
    assert "e_dynamic_quant_promotion" in avoid_ids
