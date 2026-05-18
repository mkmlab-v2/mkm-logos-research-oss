"""Smoke tests for MS-active matched compare."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/run_btrack_active_day_matched_compare_v1.py"
OUT = ROOT / "reports/btrack_active_day_matched_compare_v1_latest.json"


def test_build_compare_smoke() -> None:
    from scripts.run_btrack_active_day_matched_compare_v1 import build_compare

    anchor = ROOT / "reports/btrack_prophecy_score_30d_frozen_kpi_a_v1.json"
    v1 = ROOT / "reports/btrack_prophecy_score_v1_prod_perdate_30d_v1.json"
    ms = ROOT / "reports/btrack_lens_combo_ms_per_date_anchor_v1.json"
    if not all(p.is_file() for p in (anchor, v1, ms)):
        return
    doc = build_compare(anchor_score=anchor, v1_score=v1, ms_per_date=ms)
    assert doc["schema"] == "btrack_active_day_matched_compare_v1"
    assert doc["panel"]["n_panel_days"] == 30
    assert doc["panel"]["ms_active_days"] == 13
    ms_lane = doc["lanes"]["ms_on_ms_active"]
    assert ms_lane["n_days"] == 13
    assert ms_lane["directional_hit_rate"] == 0.692308


def test_cli_writes_json() -> None:
    if not SCRIPT.is_file():
        return
    cp = subprocess.run(
        [sys.executable, str(SCRIPT)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert cp.returncode == 0, cp.stderr or cp.stdout
    assert OUT.is_file()
    doc = json.loads(OUT.read_text(encoding="utf-8"))
    assert doc.get("research_only") is True
