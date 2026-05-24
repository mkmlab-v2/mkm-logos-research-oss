# -*- coding: utf-8 -*-
"""Showroom trust slice patient_intake_b_track_v0."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILD_SLICE = ROOT / "scripts" / "build_showroom_trust_visualization_slice_v1.py"
DASHBOARD = ROOT / "docs" / "final" / "artifacts" / "mkm_trackc_ops_dashboard_latest.json"
RATIONALE = ROOT / "reports" / "patient_intake_fusion_rationale_latest.json"


def test_build_slice_includes_patient_intake(tmp_path):
    if not DASHBOARD.is_file() or not RATIONALE.is_file():
        return
    out = tmp_path / "showroom_slice.json"
    cp = subprocess.run(
        [sys.executable, str(BUILD_SLICE), "--dashboard", str(DASHBOARD), "--out", str(out)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert cp.returncode == 0, cp.stderr + cp.stdout
    doc = json.loads(out.read_text(encoding="utf-8-sig"))
    pit = doc.get("patient_intake_b_track_v0") or {}
    assert doc.get("version") == "0.1.3"
    assert pit.get("state") in ("OK", "NODATA")
    assert pit.get("auto_prescription_forbidden") is True
    if pit.get("state") == "OK":
        assert pit.get("boundary_note_ko")
