from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "sandbox" / "bench_pcie_adaptive_threshold_v1.py"


def test_bench_schema_output() -> None:
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--dry-run"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr
    data = json.loads(proc.stdout)
    assert data["schema"] == "pcie_adaptive_threshold_bench_v1"
    assert data["disclaimer"] == "research_only"
    assert data["track_a_preflight_binding"] is False
    assert data["recommendation"] == "sandbox_only_stop_before_preflight"
