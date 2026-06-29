"""Smoke tests for Telegraph-English spine prestage arm."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/run_ng40_telegraph_english_spine_arm_v1.py"
OUT = (
    ROOT
    / "experiments/nextgen_clean_slate_cpu_v1/results/ng40_telegraph_english_spine_arm_v1_latest.json"
)


def test_telegraph_prestage_shortens_without_dropping_must_keep():
    from scripts.nextgen_telegraph_english_prestage_v1 import telegraph_prestage

    raw = "사상의학 and the very important clinical note for sasang"
    prestaged, _ = telegraph_prestage(raw)
    assert "사상의학" in prestaged
    assert "sasang" in prestaged
    assert len(prestaged) < len(raw)


def test_telegraph_spine_arm_runner_exit_zero():
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
    assert doc["schema"] == "ng40_telegraph_english_spine_arm_v1"
    assert doc["apply_forbidden"] is True
    assert "beat_check" in doc
