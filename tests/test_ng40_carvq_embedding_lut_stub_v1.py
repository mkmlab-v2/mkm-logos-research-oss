"""Smoke tests for CARVQ embedding LUT stub arm."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/run_ng40_carvq_embedding_lut_stub_v1.py"
OUT = (
    ROOT
    / "experiments/nextgen_clean_slate_cpu_v1/results/ng40_carvq_embedding_lut_stub_v1_latest.json"
)


def test_rvq_roundtrip_cosine_positive():
    from scripts.run_ng40_carvq_embedding_lut_stub_v1 import _cosine, _feature_vec, _rvq_encode

    vec = _feature_vec("clinical sasang note with bible anchor")
    _, recon = _rvq_encode(vec)
    assert _cosine(vec, recon) > 0.0


def test_carvq_stub_runner_exit_zero():
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
    assert doc["schema"] == "ng40_carvq_embedding_lut_stub_v1"
    assert doc["apply_forbidden"] is True
    assert "beat_check" in doc
