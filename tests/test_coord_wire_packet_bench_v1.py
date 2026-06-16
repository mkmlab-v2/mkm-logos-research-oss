"""COORD wire bench across rib55 manifest entries."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/build_coord_wire_packet_bench_v1.py"
OUT = ROOT / "docs/final/artifacts/coord_wire_packet_bench_v1_latest.json"


def test_build_coord_wire_packet_bench_two_entries():
    r = subprocess.run([sys.executable, str(SCRIPT)], cwd=ROOT, capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    doc = json.loads(OUT.read_text(encoding="utf-8"))
    assert doc["schema"] == "coord_wire_packet_bench_v1"
    assert doc["entry_count"] >= 3
    shas = {row["coord_wire_minimal"]["base_sha256"] for row in doc["entries"]}
    assert len(shas) >= 2, "multi-base bench expects distinct base_sha256"
    for row in doc["entries"]:
        assert row["coord_wire_tokens"] is not None
        assert row["coord_wire_tokens"] < 220
    assert doc["aggregate"]["token_delta_max_minus_min"] >= 0
