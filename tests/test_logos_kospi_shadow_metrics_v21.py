# -*- coding: utf-8 -*-
"""Regression: v21 precrash precision vs warning_precision; schema keys."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_logos_kospi_shadow_test.py"
SAMPLE = ROOT / "research" / "market_data" / "kospi_crash_samples.json"


@pytest.mark.skipif(not SAMPLE.is_file(), reason="kospi_crash_samples.json missing")
def test_warning_precision_matches_precrash_zone_precision():
    cmd = [
        sys.executable,
        str(SCRIPT),
        "--input-json",
        str(SAMPLE),
        "--out-dir",
        str(ROOT / "reports" / "research" / "logos_shadow_v1"),
        "--min-rows",
        "40",
    ]
    cp = subprocess.run(cmd, capture_output=True, text=True, cwd=str(ROOT))
    assert cp.returncode == 0, cp.stderr or cp.stdout
    out = json.loads(cp.stdout)
    m = out["metrics"]
    assert m["warning_precision"] == m["precrash_zone_precision"]
    assert "recent_era_precrash_zone_precision" in m
    assert "warning_false_positive_ratio" in m


@pytest.mark.skipif(not SCRIPT.is_file(), reason="shadow script missing")
def test_payload_schema_v1_1():
    cmd = [
        sys.executable,
        str(SCRIPT),
        "--input-json",
        str(SAMPLE),
        "--out-dir",
        str(ROOT / "reports" / "research" / "logos_shadow_v1"),
        "--min-rows",
        "40",
    ]
    cp = subprocess.run(cmd, capture_output=True, text=True, cwd=str(ROOT))
    assert cp.returncode == 0
    latest = ROOT / "reports" / "research" / "logos_shadow_v1" / "logos_kospi_shadow_202003_v1_latest.json"
    assert latest.is_file()
    payload = json.loads(latest.read_text(encoding="utf-8"))
    assert payload.get("schema") == "logos_kospi_shadow_v1_1"
    assert "metrics_note" in payload
