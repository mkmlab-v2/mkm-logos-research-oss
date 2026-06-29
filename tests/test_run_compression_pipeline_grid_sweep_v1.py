#!/usr/bin/env python3
"""Smoke tests for compression pipeline grid sweep (dry-run + schema)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_compression_pipeline_grid_sweep_v1.py"
MANIFEST = ROOT / "experiments" / "compression_pipeline_grid_sweep_v1" / "grid_manifest_v1.json"


def test_manifest_schema_fields() -> None:
    doc = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert doc.get("schema") == "compression_pipeline_grid_manifest_v1"
    assert doc.get("track_a_active_write") is False
    assert doc.get("research_only") is True
    assert "universal" in (doc.get("sla_track_modes") or [])


def test_dry_run_exit_zero() -> None:
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--dry-run"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
