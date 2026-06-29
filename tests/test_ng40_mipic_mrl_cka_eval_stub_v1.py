"""Smoke tests for MIPIC MRL+CKA eval stub arm."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/run_ng40_mipic_mrl_cka_eval_stub_v1.py"
OUT = (
    ROOT
    / "experiments/nextgen_clean_slate_cpu_v1/results/ng40_mipic_mrl_cka_eval_stub_v1_latest.json"
)


def test_linear_cka_identity():
    from scripts.run_ng40_mipic_mrl_cka_eval_stub_v1 import _linear_cka

    mat = [[1.0, 2.0], [2.0, 3.0], [3.0, 4.0]]
    assert _linear_cka(mat, mat) >= 0.99


def test_mipic_stub_runner_exit_zero():
    proc = subprocess.run(
        [sys.executable, str(SCRIPT)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert proc.returncode == 0, proc.stderr[-500:]
    assert OUT.is_file()
    doc = json.loads(OUT.read_text(encoding="utf-8"))
    assert doc["schema"] == "ng40_mipic_mrl_cka_eval_stub_v1"
    assert doc["apply_forbidden"] is True
    assert "beat_check" in doc
    assert doc["aggregate"]["mean_linear_cka_at_selected"] >= 0.0
