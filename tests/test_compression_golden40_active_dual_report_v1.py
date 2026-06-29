"""Smoke for Golden-40 ACTIVE raw/repair_v2 dual report builder."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable
OUT = ROOT / "reports/compression_golden40_active_dual_report_v1_latest.json"
ACTIVE = ROOT / "docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json"


def test_build_golden40_active_dual_report_exit_0() -> None:
    if not ACTIVE.is_file():
        return
    proc = subprocess.run(
        [PY, "scripts/build_compression_golden40_active_dual_report_v1.py"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    assert OUT.is_file()
    doc = json.loads(OUT.read_text(encoding="utf-8"))
    assert doc["schema"] == "compression_golden40_active_dual_report_v1"
    assert doc["raw"]["rows"] == 40
    assert doc["repair_v2"]["rows"] == 40
    assert "alignment_pass_rate_delta_repair_v2_minus_raw" in doc["delta"]
    assert doc["track_a_promotion_primary"] == "raw"
