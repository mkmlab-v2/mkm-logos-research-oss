"""Smoke: MKM lane registry v0.1 schema + pointers."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_lane_registry_check_exit_zero():
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "check_mkm_lane_registry_v1.py")],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout


def test_lane_registry_has_clinician_ui_hardener():
    import json

    data = json.loads((ROOT / "docs/final/artifacts/MKM_LANE_REGISTRY_V1.json").read_text(encoding="utf-8"))
    ids = {lane["lane_id"] for lane in data["lanes"]}
    assert "clinician-ui-hardener" in ids
    assert "infra-ops" in ids
