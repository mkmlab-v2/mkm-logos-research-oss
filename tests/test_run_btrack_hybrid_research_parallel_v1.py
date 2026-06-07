"""Smoke for parallel hybrid research bundle (offline)."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_hybrid_research_parallel_bundle_runs():
    script = ROOT / "scripts/run_btrack_hybrid_research_parallel_v1.py"
    assert script.is_file()
    proc = subprocess.run(
        [sys.executable, str(script)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert proc.returncode in (0, 1), proc.stderr[-500:]
    out = ROOT / "reports/btrack_hybrid_research_parallel_v1_latest.json"
    assert out.is_file()
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc.get("research_only") is True
    assert doc.get("auto_promote") is False
    assert len(doc.get("tasks") or []) >= 4
