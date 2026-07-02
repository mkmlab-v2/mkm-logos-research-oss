"""Narrative stress fixture — synthetic failures hit expected axes and registry."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable
STRESS = ROOT / "scripts/run_logos_ask_narrative_stress_v1.py"
OUT = ROOT / "reports/logos_ask_narrative_stress_v1_latest.json"
REG = ROOT / "reports/mkm_agent_mistake_registry_v1.jsonl"


def test_narrative_stress_all_fail_and_record(tmp_path: Path) -> None:
    reg = tmp_path / "reg.jsonl"
    proc = subprocess.run(
        [PY, str(STRESS), "--out", str(tmp_path / "stress.json"), "--no-record-mistakes"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    doc = json.loads((tmp_path / "stress.json").read_text(encoding="utf-8"))
    assert doc["stress_ok"] is True
    assert doc["items_failed"] == doc["items_total"]
    assert not doc["failure_axis_miss"]


def test_narrative_stress_registry_integration(tmp_path: Path) -> None:
    reg = tmp_path / "reg.jsonl"
    proc = subprocess.run(
        [
            PY,
            str(STRESS),
            "--out",
            str(tmp_path / "stress.json"),
            "--registry",
            str(reg),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    doc = json.loads((tmp_path / "stress.json").read_text(encoding="utf-8"))
    assert doc["mistakes_recorded"] >= 6
    lines = reg.read_text(encoding="utf-8").splitlines()
    assert len(lines) >= 6
    assert any("logos_ask_narrative_stress_v1" in ln for ln in lines)
    assert any("stress_666_job_preset_leak" in ln for ln in lines)
