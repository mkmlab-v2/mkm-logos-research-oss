"""MKM-UR-Bench-5K holdout chain smoke."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
CHAIN = REPO / "scripts/run_universal_root_bench_5k_holdout_chain_v1.py"
CHECK = REPO / "scripts/check_universal_root_bench_5k_v1.py"
PHASE1A = REPO / "reports/universal_root_bench_5k_holdout_phase1a_v1_latest.json"


def test_bench_5k_holdout_chain_and_gate():
    proc = subprocess.run([sys.executable, str(CHAIN)], cwd=str(REPO), capture_output=True, text=True)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    doc = json.loads(PHASE1A.read_text(encoding="utf-8-sig"))
    assert doc["schema"] == "universal_root_phase1a_baseline_compare_v1"
    assert int(doc.get("pair_count") or 0) >= 500
    ids = {m["id"] for m in doc["methods"]}
    assert "B0" in ids and "B3" in ids
    b3 = next(m for m in doc["methods"] if m["id"] == "B3")
    b0 = next(m for m in doc["methods"] if m["id"] == "B0")
    assert b3["primary_value"] is not None
    assert b0["primary_value"] is not None

    gate = subprocess.run([sys.executable, str(CHECK), "--strict"], cwd=str(REPO), capture_output=True, text=True)
    assert gate.returncode == 0, gate.stdout + gate.stderr
