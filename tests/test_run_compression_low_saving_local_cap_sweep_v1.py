"""Low-saving local cap sweep must not write Track A active report."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_compression_low_saving_local_cap_sweep_v1.py"
ACTIVE = ROOT / "docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json"
OUT = ROOT / "docs/final/artifacts/compression_low_saving_local_cap_sweep_v1_latest.json"


def test_refuses_track_a_active_as_out() -> None:
    cp = subprocess.run(
        [sys.executable, str(SCRIPT), "--out-json", str(ACTIVE)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert cp.returncode != 0
    assert "Refusing" in (cp.stderr or cp.stdout or "")


def test_dry_run_lists_variants() -> None:
    cp = subprocess.run(
        [sys.executable, str(SCRIPT), "--dry-run"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=True,
    )
    assert "compression_low_saving_local_cap_sweep_v1" in cp.stdout
    assert "ssot_relaxed_cap_0.50" in cp.stdout
    assert "top_n_low_saving" in cp.stdout
