"""Smoke test for bench TUI demo transcript capture."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TRANSCRIPT = ROOT / "docs/final/artifacts/mkm_bench_tui_demo_transcript_v1.txt"
OUT = ROOT / "reports/mkm_bench_tui_demo_capture_v1_latest.json"
ORCH = ROOT / "reports/mkm_ltm_orchestration_bench_v1_latest.json"


@pytest.mark.skipif(not ORCH.is_file(), reason="orchestration bench artifact missing")
def test_mkm_bench_tui_demo_capture_exit_zero() -> None:
    proc = subprocess.run(
        [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(ROOT / "scripts/Invoke-MkmBenchTuiDemoCapture_v1.ps1"),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
        timeout=120,
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    assert TRANSCRIPT.is_file()
    text = TRANSCRIPT.read_text(encoding="utf-8")
    assert "99.6%" in text or "99.7%" in text
    assert "33." in text
    doc = json.loads(OUT.read_text(encoding="utf-8-sig"))
    assert doc["ok"] is True
