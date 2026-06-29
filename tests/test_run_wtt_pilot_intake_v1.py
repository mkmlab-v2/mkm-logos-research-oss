"""Run-WttPilotIntake_v1.ps1 smoke."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "data/wtt/examples/wtt_spicy_masked_sessions_v1.example.jsonl"
PS1 = ROOT / "scripts/Run-WttPilotIntake_v1.ps1"


def test_wtt_pilot_intake_synthetic_smoke() -> None:
    if not CORPUS.is_file():
        subprocess.run(
            ["py", "scripts/build_wtt_spicy_masked_sessions_v1.py"],
            cwd=str(ROOT),
            check=True,
        )
    proc = subprocess.run(
        [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(PS1),
            "-TenantId",
            "wtt-intake-smoke-v1",
            "-SessionJsonl",
            str(CORPUS),
            "-AllowSynthetic",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    manifest = ROOT / "reports/wtt_pilot_intake_wtt-intake-smoke-v1_v1.json"
    assert manifest.is_file()
    doc = json.loads(manifest.read_text(encoding="utf-8"))
    assert doc["send_gate"] == "HOLD"
    assert doc["corpus_session_count"] >= 20
