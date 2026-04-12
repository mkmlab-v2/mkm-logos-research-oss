# -*- coding: utf-8 -*-
"""Smoke: 4-grid myeongri compression spike runs and emits schema."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_spike_4grid_schema_smoke() -> None:
    script = ROOT / "scripts" / "spike_4grid_myeongri_compression_v1.py"
    cp = subprocess.run(
        [sys.executable, str(script), "--samples", "5", "--seed", "1", "--stdout-only"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=120,
    )
    assert cp.returncode == 0, cp.stderr
    doc = json.loads(cp.stdout)
    assert doc.get("schema") == "spike_4grid_myeongri_compression_v1"
    assert doc.get("hypothesis_tier") == "B"
    assert doc.get("boundary_ack") is True
    assert len(doc.get("rows") or []) == 5
    for k in ("mean_ratio_baseline", "mean_ms_baseline", "corpus_source"):
        assert k in doc
    assert doc.get("corpus_source") == "synthetic"
