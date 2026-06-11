"""Tests for prophecy contributions manifest check."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "data/prophecy/contributions/prophecy_contributions_manifest_v1.json"
SCRIPT = ROOT / "scripts/check_prophecy_contributions_manifest_v1.py"


def test_manifest_and_reference_validate() -> None:
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--manifest", str(MANIFEST), "--validate-reference"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
