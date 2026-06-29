"""Smoke tests for Track C B2B counsel copy scan."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/check_track_c_b2b_counsel_copy_scan_v1.py"


def test_counsel_copy_scan_runs_and_writes_report():
    out = ROOT / "reports/_tmp_track_c_b2b_counsel_copy_scan_test.json"
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
    assert doc["schema"] == "track_c_b2b_counsel_copy_scan_v1"
    assert "ready_for_external_send" in doc
    assert doc["ready_for_external_send"] is False
