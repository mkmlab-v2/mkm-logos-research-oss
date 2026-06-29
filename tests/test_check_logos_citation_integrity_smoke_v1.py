"""Regression: Logos Citation Integrity smoke chain."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/check_logos_citation_integrity_smoke_v1.py"


def test_logos_citation_integrity_smoke_exit_zero() -> None:
    r = subprocess.run(
        [sys.executable, str(SCRIPT), "--stdout-only"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stderr
    doc = json.loads(r.stdout.strip().splitlines()[-1])
    assert doc["ok"] is True
