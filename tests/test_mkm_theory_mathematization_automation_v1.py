"""Smoke tests for MKM theory mathematization automation chain."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_formula_ssot_has_75_named_slots() -> None:
    path = ROOT / "docs/final/artifacts/mkm12_75_formulas_ssot_v1_latest.json"
    doc = json.loads(path.read_text(encoding="utf-8"))
    assert doc["total_slots"] == 75
    assert doc["unrecovered_slots"] == 0
    assert len(doc["formulas"]) == 75
    assert doc.get("documented_with_expr", 0) == 75


def test_promotion_registry_blocks_track_a() -> None:
    path = ROOT / "docs/final/artifacts/mkm_theory_formula_promotion_registry_v1_latest.json"
    doc = json.loads(path.read_text(encoding="utf-8"))
    assert doc["promotion_to_a_track_allowed"] is False
    assert len(doc["entries"]) == 75
    assert doc["lane_counts"].get("forbidden", 0) >= 0


def test_gap_map_l3_complete() -> None:
    path = ROOT / "reports/theory_reflection_gap_map_v1_latest.json"
    doc = json.loads(path.read_text(encoding="utf-8"))
    l3 = doc["lanes"]["L3_unrecovered_formula_slots"]
    assert l3["status"] == "complete"
    assert l3["count"] == 0
    l4 = doc["lanes"]["L4_worldview_full_constitution"]
    assert l4["status"] == "implemented_pointer"


def test_mirror_script_exit_zero() -> None:
    r = subprocess.run(
        [sys.executable, "scripts/mirror_mkm12_math_vault_to_workspace_v1.py"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stderr or r.stdout
