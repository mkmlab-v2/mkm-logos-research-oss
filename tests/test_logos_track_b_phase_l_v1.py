from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]


def test_phase_l_skip_ollama_exit0() -> None:
    cp = subprocess.run(
        [
            sys.executable,
            str(_ROOT / "scripts/run_logos_track_b_phase_l_v1.py"),
            "--skip-ollama",
            "--skip-phase-j",
        ],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        timeout=600,
    )
    assert cp.returncode == 0, cp.stderr + cp.stdout
    doc = json.loads((_ROOT / "reports/logos_track_b_phase_l_v1_latest.json").read_text(encoding="utf-8"))
    assert doc.get("ok") is True
    assert doc.get("deep_push_ok") is None
    assert doc.get("phase_k_ok") is True


def test_phase_l_manifest_schema() -> None:
    doc = json.loads((_ROOT / "reports/logos_track_b_phase_l_v1_latest.json").read_text(encoding="utf-8"))
    assert doc.get("schema") == "logos_track_b_phase_l_v1"
    assert doc.get("lane") == "track_b_hypo"
    assert doc.get("non_gating") is True
