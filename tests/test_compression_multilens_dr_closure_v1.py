"""Smoke tests for compression multilens DR master closure."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CLOSURE = ROOT / "reports/compression_multilens_dr_closure_v1_latest.json"


def test_build_dr_closure_smoke() -> None:
    proc = subprocess.run(
        [sys.executable, "scripts/build_compression_multilens_dr_closure_v1.py"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    assert CLOSURE.is_file()
    doc = json.loads(CLOSURE.read_text(encoding="utf-8"))
    assert doc["schema"] == "compression_multilens_dr_closure_v1"
    assert doc["stack_closure_ok"] is True
    assert doc["apply_active_forbidden"] is True
    assert doc["pareto_signoff"]["beat_frozen"] is False


def test_phase7_master_closure_chain_smoke() -> None:
    proc = subprocess.run(
        [sys.executable, "scripts/run_ng40_dr_phase7_master_closure_chain_v1.py"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
        timeout=300,
    )
    assert proc.returncode == 0, proc.stderr
    chain_path = ROOT / "reports/ng40_dr_phase7_master_closure_chain_v1_latest.json"
    assert chain_path.is_file()
    doc = json.loads(chain_path.read_text(encoding="utf-8"))
    assert doc["chain_ok"] is True
    assert doc["stack_closure_ok"] is True
