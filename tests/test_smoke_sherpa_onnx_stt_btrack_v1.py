"""smoke_sherpa_onnx_stt_btrack_v1 contract."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/smoke_sherpa_onnx_stt_btrack_v1.py"
WAV = ROOT / "reports/audio/supertonic_btrack_smoke_v1.wav"


def test_default_wav_or_skip() -> None:
    if not WAV.is_file():
        return
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--fixture-only"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr
    data = json.loads(proc.stdout)
    assert data["schema"] == "sherpa_onnx_stt_btrack_smoke_v1"
    assert data["status"] == "ok_fixture_audit"
    assert data["route"] == "local"


def test_smoke_skip_or_ok_schema() -> None:
    proc = subprocess.run(
        [sys.executable, str(SCRIPT)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    if not WAV.is_file():
        assert proc.returncode in (0, 1)
        return
    assert proc.returncode in (0, 1), proc.stderr
    raw = proc.stdout or proc.stderr
    data = json.loads(raw.strip().splitlines()[-1])
    assert data["schema"] == "sherpa_onnx_stt_btrack_smoke_v1"
    assert data["status"] in {"ok", "skip", "fail", "ok_fixture_audit"}
    if data["status"] == "ok":
        assert "char_accuracy" in data
        assert "char_accuracy_number_aware" in data
