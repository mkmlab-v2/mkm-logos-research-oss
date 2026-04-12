# -*- coding: utf-8 -*-
"""Smoke: gematria+myeongri 4D blend spike exits 0 (B-track)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_spike_gematria_myeongri_blend_stdout_only() -> None:
    script = ROOT / "scripts" / "spike_gematria_myeongri_blend_v0.py"
    cp = subprocess.run(
        [sys.executable, str(script), "--stdout-only"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=120,
    )
    assert cp.returncode == 0, cp.stderr
    doc = json.loads(cp.stdout)
    assert doc.get("schema") == "gematria_myeongri_spike_blend_v0"
    assert doc.get("hypothesis_tier") == "B"
    assert doc.get("boundary_ack") is True
