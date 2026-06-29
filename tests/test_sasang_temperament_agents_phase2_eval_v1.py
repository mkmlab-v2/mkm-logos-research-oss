"""RQ-026 phase-2 eval separation gate and pathology dominance."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PHASE2 = ROOT / "scripts/build_sasang_temperament_agents_phase2_eval_v1.py"
SIM = ROOT / "reports/sasang_temperament_agents_sim_v1_latest.json"
CONTRACT = ROOT / "experiments/sasang_temperament_agents_v1/specs/temperament_eval_axes_contract_v1.json"


def test_eval_axes_contract_shape() -> None:
    doc = json.loads(CONTRACT.read_text(encoding="utf-8"))
    assert doc.get("schema") == "sasang_temperament_eval_axes_contract_v1"
    assert "temperament_consistency" in doc.get("allowed_eval_axis_ids", [])
    assert "price_directional_hit_rate" in doc.get("forbidden_metric_keys", [])


def test_phase2_eval_builder_strict_passes(tmp_path: Path) -> None:
    if not SIM.is_file():
        pytest.skip("sim report missing")
    out = tmp_path / "phase2.json"
    proc = subprocess.run(
        [sys.executable, str(PHASE2), "--out", str(out), "--strict"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc.get("eval_separation_ok") is True
    assert "constitution_pathology_dominance" in doc.get("eval_axes", {})
    assert doc.get("checks", {}).get("forbidden_metric_keys_in_sim") == []
