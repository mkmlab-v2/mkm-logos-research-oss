# Keywords: compression board ms vps bench triplet

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_build_vps_triplet_from_runs() -> None:
    runs_dir = ROOT / "docs" / "final" / "artifacts" / "bench_runs"
    if not list(runs_dir.glob("bench_l1_api_load_vps_*.json")):
        return
    r = subprocess.run(
        [sys.executable, str(ROOT / "scripts/build_compression_board_ms_vps_bench_triplet_v1.py")],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stderr + r.stdout
    out = ROOT / "docs/final/artifacts/compression_board_ms_vps_bench_triplet_v1_latest.json"
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc.get("schema") == "compression_board_ms_vps_bench_triplet_v1"
    assert doc["derived"]["run_count"] >= 3
