"""Coordinate envelope v1 check script smoke."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "scripts/build_jema_os_coordinate_envelope_v1.py"
CHECK = ROOT / "scripts/check_jema_os_coordinate_envelope_v1.py"


def test_check_coordinate_envelope_exit_zero():
    proc = subprocess.run(
        [sys.executable, str(BUILDER), "--read-depth", "skim", "--lane", "oracle"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    proc2 = subprocess.run(
        [sys.executable, str(CHECK)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc2.returncode == 0, proc2.stderr or proc2.stdout
    report = json.loads(
        (ROOT / "reports/jema_os_coordinate_envelope_v1_check_v1_latest.json").read_text(
            encoding="utf-8"
        )
    )
    assert report["ok"] is True
    assert report["a2a_peer_ok"] is True
