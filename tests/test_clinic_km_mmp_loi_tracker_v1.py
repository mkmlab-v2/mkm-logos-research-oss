"""Tests for clinic LOI tracker build + validate."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "scripts" / "build_clinic_km_mmp_loi_tracker_v1.py"
CHECK = ROOT / "scripts" / "check_clinic_km_mmp_loi_tracker_v1.py"
TRACKER = ROOT / "docs/final/artifacts/clinic_km_mmp_loi_tracker_v1_latest.json"


def test_tracker_build_and_check_exit_zero() -> None:
    cp = subprocess.run(
        [sys.executable, str(BUILD)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert cp.returncode == 0, cp.stderr or cp.stdout
    out = json.loads(cp.stdout.strip())
    assert out["ok"] is True

    doc = json.loads(TRACKER.read_text(encoding="utf-8"))
    assert doc["schema"] == "clinic_km_mmp_loi_tracker_v1"
    assert doc["send_gate"] == "HOLD"
    assert doc["ready_for_external_send"] is False
    readiness = doc["readiness"]
    assert readiness["external_send_blocked"] is True
    assert readiness["commander_unfreeze_required"] is True
    assert "figma_token_map" in doc

    cp2 = subprocess.run(
        [sys.executable, str(CHECK)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert cp2.returncode == 0, cp2.stderr or cp2.stdout
