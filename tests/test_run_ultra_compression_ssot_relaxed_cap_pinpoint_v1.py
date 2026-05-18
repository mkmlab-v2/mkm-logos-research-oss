"""Ssot relaxed-cap pinpoint must not write Track A active report."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_ultra_compression_ssot_relaxed_cap_pinpoint_v1.py"
ACTIVE = ROOT / "docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json"
PINPOINT = ROOT / "docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_SSOT_RELAXED_CAP_PINPOINT_V1.json"


def test_refuses_track_a_active_as_out() -> None:
    cp = subprocess.run(
        [sys.executable, str(SCRIPT), "--out-json", str(ACTIVE)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert cp.returncode != 0
    assert "Refusing" in (cp.stderr or cp.stdout or "")


def test_dry_run_default_out_is_ssot_pinpoint() -> None:
    cp = subprocess.run(
        [sys.executable, str(SCRIPT), "--dry-run"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=True,
    )
    assert "MULTILENS_ULTRA_COMPRESSION_SSOT_RELAXED_CAP_PINPOINT_V1.json" in cp.stdout
    assert "domain_relaxed_max_saving_overrides" in cp.stdout
