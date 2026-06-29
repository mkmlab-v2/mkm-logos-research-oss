"""Smoke tests for Track C B2B disclaimer integrity scan."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/check_track_c_b2b_disclaimer_integrity_v1.py"


def test_disclaimer_integrity_scan_writes_report():
    out = ROOT / "reports/_tmp_track_c_b2b_disclaimer_integrity_test.json"
    if out.is_file():
        out.unlink()
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--out-json", str(out)],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert proc.returncode in (0, 1)
    assert out.is_file()
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == "track_c_b2b_disclaimer_integrity_v1"
    assert doc["ready_for_external_send"] is False
    assert len(doc["files"]) == 8
