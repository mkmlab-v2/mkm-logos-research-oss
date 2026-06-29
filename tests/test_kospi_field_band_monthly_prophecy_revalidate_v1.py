"""Monthly prophecy band revalidate chain."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable


@pytest.mark.skipif(
    not (ROOT / "docs/final/artifacts/kospi_field_band_commander_l4_sign_v1_latest.json").is_file(),
    reason="L4 sign missing",
)
def test_monthly_revalidate_chain():
    cp = subprocess.run(
        [
            PY,
            "scripts/run_kospi_field_band_monthly_prophecy_revalidate_v1.py",
            "--skip-panel-build",
            "--skip-premium",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=600,
    )
    assert cp.returncode == 0, cp.stderr + cp.stdout
    doc = json.loads(
        (ROOT / "reports/kospi_field_band_monthly_prophecy_revalidate_v1_latest.json").read_text(encoding="utf-8-sig")
    )
    assert doc["monthly_ok"] is True
    assert doc["track_a_go"] is False
