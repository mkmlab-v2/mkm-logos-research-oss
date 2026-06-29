"""Smoke for Path B knee summary builder."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable
SWEEP = (
    ROOT
    / "experiments/nextgen_clean_slate_cpu_v1/results/ng40_latent_eval_path_b_sweep_v1_latest.json"
)
OUT = ROOT / "reports/ng40_path_b_knee_summary_v1_latest.json"


def test_build_ng40_path_b_knee_summary_exit_0() -> None:
    if not SWEEP.is_file():
        return
    proc = subprocess.run(
        [PY, "scripts/build_ng40_path_b_knee_summary_v1.py"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    doc = json.loads(OUT.read_text(encoding="utf-8"))
    assert doc["schema"] == "ng40_path_b_knee_summary_v1"
    assert doc["sweep"]["combo_count"] == 320
    assert "knee_j_first" in doc
    assert "knee_saving_first" in doc
