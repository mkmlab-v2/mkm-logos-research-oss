"""Daily mainline unified adapter chain smoke."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAINLINE_OUT = ROOT / "reports/sasang_dynamics_unified_v1_latest.json"
PY = sys.executable


def test_run_adapter_mainline_profile_exit_zero():
    proc = subprocess.run(
        [PY, "scripts/run_sasang_dynamics_unified_adapter_v1.py", "--profile", "mainline"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    assert MAINLINE_OUT.is_file()


def test_mainline_unified_output_contract():
    proc = subprocess.run(
        [PY, "scripts/run_sasang_dynamics_unified_adapter_v1.py", "--profile", "mainline"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0
    doc = json.loads(MAINLINE_OUT.read_text(encoding="utf-8"))
    assert doc["schema"] == "sasang_dynamics_unified_v1"
    assert doc["send_gate"] == "HOLD"
    assert doc["promotion_to_a_track_allowed"] is False
    assert isinstance(doc["stress_v1"], (int, float))
    assert doc["pathology_stage_v1"]["pathology_stage_id"] in ("anjeong", "cho", "jung", "mal")
    prov = doc.get("input_provenance") or {}
    assert prov.get("profile") == "mainline"


def test_daily_chain_skip_lens_refresh_exit_zero():
    proc = subprocess.run(
        [
            PY,
            "scripts/run_sasang_unified_adapter_daily_chain_v1.py",
            "--skip-lens-refresh",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    chain_report = ROOT / "reports/sasang_unified_adapter_daily_chain_v1_latest.json"
    assert chain_report.is_file()
    report = json.loads(chain_report.read_text(encoding="utf-8"))
    assert report.get("ok") is True
    assert report.get("send_gate") == "HOLD"
