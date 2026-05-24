"""B-track polar v4 spike — schema and golden_core non-write guard."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPIKE = ROOT / "reports/run_polar_coord_compression_hypo_v4_spike_v1.py"
ACTIVE = ROOT / "docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json"


def test_polar_v4_spike_runs_and_schema():
    before = ACTIVE.read_text(encoding="utf-8")
    proc = subprocess.run(
        [sys.executable, str(SPIKE)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert proc.returncode == 0, proc.stderr
    out = ROOT / "reports/polar_coord_compression_hypo_v4_spike_latest.json"
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == "polar_coord_compression_hypo_v4_spike_v1"
    assert doc["research_only"] is True
    assert doc["would_change_active"] is False
    assert "proceed_to_dryrun_hook" in doc
    assert ACTIVE.read_text(encoding="utf-8") == before
