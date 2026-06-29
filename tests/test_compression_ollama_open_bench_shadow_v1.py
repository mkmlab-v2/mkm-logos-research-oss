"""Smoke for Ollama open-bench shadow dual-report."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable
OUT = ROOT / "reports/_test_compression_ollama_shadow_dual_report_v1.json"


def test_ollama_open_bench_shadow_exit_0() -> None:
    proc = subprocess.run(
        [
            PY,
            "scripts/run_compression_ollama_open_bench_shadow_v1.py",
            "--output",
            str(OUT.relative_to(ROOT)).replace("\\", "/"),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    doc = json.loads(OUT.read_text(encoding="utf-8"))
    assert doc["schema"] == "compression_ollama_shadow_dual_report_v1"
    assert doc["track_a_active_write"] is False
    assert "open_bench_cohorts" in doc
