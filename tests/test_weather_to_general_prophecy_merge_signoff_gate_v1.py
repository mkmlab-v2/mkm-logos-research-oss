#!/usr/bin/env python3
"""Smoke: weather→GP merge signoff gate defaults to HOLD (no mass merge)."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_weather_merge_signoff_gate_defaults_hold(tmp_path: Path) -> None:
    py = sys.executable
    out = tmp_path / "gate.json"
    readiness = tmp_path / "readiness.json"
    cp = subprocess.run(
        [
            py,
            str(ROOT / "scripts/check_weather_to_general_prophecy_merge_signoff_gate_v1.py"),
            "--out-json",
            str(out),
            "--report-json",
            str(readiness),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert cp.returncode == 0, cp.stderr
    gate = json.loads(out.read_text(encoding="utf-8"))
    assert gate["merge_decision"] == "HOLD"
    assert gate["merge_allowed"] is False
    assert gate["counts"]["would_add_if_full_merge"] >= 1
    assert gate["counts"]["class_b_scorable_not_in_main"] == 0
    ready = json.loads(readiness.read_text(encoding="utf-8"))
    assert ready["merge_decision"] == "HOLD"
    assert ready["merge_applied"] is False


def test_weather_merge_dry_run_blocked_without_signoff(tmp_path: Path) -> None:
    py = sys.executable
    report = tmp_path / "merge.json"
    cp = subprocess.run(
        [
            py,
            str(ROOT / "scripts/merge_weather_to_general_prophecy_v1.py"),
            "--dry-run",
            "--report-json",
            str(report),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert cp.returncode == 0, cp.stderr
    doc = json.loads(report.read_text(encoding="utf-8"))
    assert doc["merge_applied"] is False
    assert doc.get("blocked_reason") or doc.get("gate_merge_allowed") is False
