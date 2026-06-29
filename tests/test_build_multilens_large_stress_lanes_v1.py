"""Large stress lane builder — B-track only."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_build_stress_lanes_smoke():
    proc = subprocess.run(
        [
            sys.executable,
            "scripts/build_multilens_large_stress_lanes_v1.py",
            "--per-lane",
            "5",
            "--jsonl-max",
            "0",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr
    line = proc.stdout.strip().splitlines()[-1]
    data = json.loads(line)
    assert data["total_cases"] == 15
    ptr = ROOT / "docs/final/artifacts/universal_compression_bench_lane_server_log_stress_v1.json"
    assert ptr.is_file()
    doc = json.loads(ptr.read_text(encoding="utf-8"))
    assert doc["research_only"] is True
    assert len(doc["compression_cases"]) == 5
