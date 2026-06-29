"""sasang_dynamics_unified_adapter_v1 smoke."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "experiments/sasang-head-btrack/artifacts/sasang_dynamics_unified_ablation_v1.json"


def test_run_adapter_exit_zero():
    proc = subprocess.run(
        [sys.executable, "scripts/run_sasang_dynamics_unified_adapter_v1.py"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout


def test_unified_output_contract():
    doc = json.loads(OUT.read_text(encoding="utf-8"))
    assert doc["schema"] == "sasang_dynamics_unified_ablation_v1"
    assert doc["send_gate"] == "HOLD"
    assert doc["promotion_to_a_track_allowed"] is False
    assert isinstance(doc["stress_v1"], (int, float))
    assert doc["pathology_stage_v1"]["pathology_stage_id"] in (
        "anjeong",
        "cho",
        "jung",
        "mal",
    )
    assert "threshold" in doc["geumhwa_gate_v1"]
    assert "provenance" in doc["geumhwa_gate_v1"]
