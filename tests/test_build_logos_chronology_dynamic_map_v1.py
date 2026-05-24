"""Smoke tests for logos chronology dynamic map v1."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/build_logos_chronology_dynamic_map_v1.py"
CHRONO = ROOT / "docs/final/artifacts/fixtures/logos_chronology_v1.example.json"
MACRO = ROOT / "docs/final/artifacts/trackc_macro_risk_morning_briefing_latest.json"


def test_dynamic_map_runs_on_fixture_chronology(tmp_path: Path) -> None:
    if not CHRONO.is_file() or not MACRO.is_file():
        return
    out = tmp_path / "dynamic_map.json"
    cp = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--chronology-json",
            str(CHRONO),
            "--macro-json",
            str(MACRO),
            "--output-json",
            str(out),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert cp.returncode == 0, cp.stderr or cp.stdout
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == "logos_chronology_dynamic_map_v1"
    assert doc["hypothesis_tier"] == "[HYPO]"
    assert doc["policy"]["non_gating"] is True
    assert doc["era_ranking"]
    assert doc["primary_match"]["era_id"]


def test_dynamic_map_latest_artifact_if_present() -> None:
    latest = ROOT / "docs/final/artifacts/logos_chronology_dynamic_map_v1_latest.json"
    if not latest.is_file():
        return
    doc = json.loads(latest.read_text(encoding="utf-8"))
    assert doc["schema"] == "logos_chronology_dynamic_map_v1"
    line = doc["primary_match"]["operator_line_ko"]
    assert "[HYPO" in line and "NON_GATING" in line
